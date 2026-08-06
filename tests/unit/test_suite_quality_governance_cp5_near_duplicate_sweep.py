"""Proves CP5's cross-suite near-duplicate sweep (ADR-0046 D3/D6):
`suite_quality_governance.cp5.near_duplicate_sweep.sweep_near_duplicates`.

Covers: near-dups flagged above threshold, unrelated assets not flagged,
the distinction from ADR-0045 D2(b)'s exact content-hash check, threshold
configurability, transitive cluster formation (including a chain that
never fully connects pairwise), the one-batched-call cost shape, no
baseline mutation, and determinism.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

import pytest

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from automation_engineering.catalog.scanner import reconcile
from automation_engineering.reuse.embeddings import cosine_similarity
from automation_engineering.reuse.live_matcher import step_definition_embedding_text
from suite_quality_governance.cp5.near_duplicate_sweep import (
    DEFAULT_NEAR_DUPLICATE_THRESHOLD,
    sweep_near_duplicates,
)


def _step_asset(
    *,
    asset_id: str,
    class_name: str,
    method_name: str,
    pattern: str,
    content_hash: str | None = None,
) -> StepDefinitionAsset:
    """Build a real, self-consistent `StepDefinitionAsset` fixture --
    `signature_alignment` is computed by the real `correlate`, never
    hand-faked. `content_hash` defaults to a value DERIVED FROM `asset_id`
    so two differently-`asset_id`'d fixtures never accidentally collide on
    hash unless a test deliberately asks them to (the D2b-distinction
    tests pass distinct hashes explicitly)."""
    return StepDefinitionAsset(
        asset_id=asset_id,
        class_name=class_name,
        method_name=method_name,
        step_type="Given",
        pattern=pattern,
        parameters=(),
        return_type="void",
        source_file=f"{class_name.replace('.', '/')}.java",
        content_hash=content_hash or f"hash-{asset_id}",
        signature_alignment=correlate(pattern, ()),
    )


class _StubEmbeddingProvider:
    """Deterministic, fixture-driven stand-in for a live embedding
    provider (mirrors `automation_engineering.reuse.matcher.
    StubSemanticMatcher`'s own "test/dev scaffolding only" discipline) --
    returns a pre-authored vector per text, keyed by exact text."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]]) -> None:
        self._vectors = vectors_by_text

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._vectors[text] for text in texts)


class _CountingEmbeddingProvider:
    """Records every `embed()` call's own text batch, and its call count --
    the whole-catalog-one-call proof."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]]) -> None:
        self._vectors = vectors_by_text
        self.calls: list[list[str]] = []

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        self.calls.append(list(texts))
        return tuple(self._vectors[text] for text in texts)


class _NeverCalledEmbeddingProvider:
    """Fails the test if `embed()` is ever invoked -- proves the sweep
    short-circuits (fewer than 2 assets) without making any call at all."""

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        raise AssertionError("embed() must not be called when fewer than 2 assets exist")


# Near-identical unit vectors at a controlled cosine angle, reused across
# tests: (1.0, 0.0) vs (cos(theta), sin(theta)) has cosine similarity
# exactly cos(theta).
_ANCHOR = (1.0, 0.0)


def _vector_at_similarity(similarity: float) -> tuple[float, ...]:
    import math

    theta = math.acos(similarity)
    return (math.cos(theta), math.sin(theta))


class TestSweepFindsNearDuplicates:
    def test_paraphrase_level_pair_is_flagged(self) -> None:
        login = _step_asset(
            asset_id="STEP-1",
            class_name="com.automation.steps.LoginSteps",
            method_name="userLogsIn",
            pattern="user logs in",
        )
        signs_in = _step_asset(
            asset_id="STEP-2",
            class_name="com.automation.steps.AuthSteps",
            method_name="userSignsIn",
            pattern="user signs in",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(login, signs_in))
        provider = _StubEmbeddingProvider(
            {
                "user logs in": _ANCHOR,
                "user signs in": _vector_at_similarity(0.95),
            }
        )

        result = sweep_near_duplicates(catalog, embedding_provider=provider)

        assert len(result.clusters) == 1
        cluster = result.clusters[0]
        assert {m.asset_id for m in cluster.members} == {"STEP-1", "STEP-2"}
        assert len(cluster.pairwise_scores) == 1
        assert cluster.pairwise_scores[0].confidence == pytest.approx(0.95, abs=1e-9)

    def test_unrelated_pair_is_not_flagged(self) -> None:
        login = _step_asset(
            asset_id="STEP-3",
            class_name="com.automation.steps.LoginSteps",
            method_name="userLogsIn",
            pattern="user logs in",
        )
        checkout = _step_asset(
            asset_id="STEP-4",
            class_name="com.automation.steps.CheckoutSteps",
            method_name="userChecksOut",
            pattern="user completes checkout",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(login, checkout))
        provider = _StubEmbeddingProvider(
            {
                "user logs in": _ANCHOR,
                "user completes checkout": _vector_at_similarity(0.60),
            }
        )

        result = sweep_near_duplicates(catalog, embedding_provider=provider)

        assert result.clusters == ()

    def test_fewer_than_two_assets_short_circuits_without_any_embed_call(self) -> None:
        one_asset_catalog = AssetCatalog(
            baseline_root="/fake",
            step_definitions=(
                _step_asset(
                    asset_id="STEP-5",
                    class_name="com.automation.steps.Solo",
                    method_name="solo",
                    pattern="a lone step",
                ),
            ),
        )
        empty_catalog = AssetCatalog(baseline_root="/fake", step_definitions=())

        assert sweep_near_duplicates(
            one_asset_catalog, embedding_provider=_NeverCalledEmbeddingProvider()
        ).clusters == ()
        assert sweep_near_duplicates(
            empty_catalog, embedding_provider=_NeverCalledEmbeddingProvider()
        ).clusters == ()


class TestDistinctFromD2bContentHashCheck:
    def test_semantic_near_dups_with_different_content_hashes_are_caught_here_not_by_d2b(
        self,
    ) -> None:
        """The load-bearing distinction (module docstring): ADR-0045 D2(b)
        is an exact content-hash check -- two assets with DIFFERENT hashes
        are, by construction, invisible to it. This sweep catches them
        anyway, because it compares MEANING, not bytes."""
        asset_a = _step_asset(
            asset_id="STEP-6",
            class_name="com.automation.steps.LoginStepsV1",
            method_name="userLogsIn",
            pattern="user logs in",
            content_hash="hash-AAAA",
        )
        asset_b = _step_asset(
            asset_id="STEP-7",
            class_name="com.automation.steps.LoginStepsV2",
            method_name="userSignsIn",
            pattern="user signs in",
            content_hash="hash-BBBB",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(asset_a, asset_b))

        # Prove D2(b) genuinely would not catch this pair: an exact
        # content-hash lookup for one asset's hash never returns the other.
        assert catalog.by_content_hash(asset_a.content_hash) == (asset_a,)
        assert catalog.by_content_hash(asset_b.content_hash) == (asset_b,)
        assert asset_a.content_hash != asset_b.content_hash

        provider = _StubEmbeddingProvider(
            {"user logs in": _ANCHOR, "user signs in": _vector_at_similarity(0.93)}
        )

        # This sweep DOES catch it.
        result = sweep_near_duplicates(catalog, embedding_provider=provider)
        assert len(result.clusters) == 1
        assert {m.asset_id for m in result.clusters[0].members} == {"STEP-6", "STEP-7"}


class TestThresholdConfigurability:
    def _catalog_and_provider(self) -> tuple[AssetCatalog, _StubEmbeddingProvider]:
        a = _step_asset(
            asset_id="STEP-8", class_name="com.automation.steps.A", method_name="a", pattern="a"
        )
        b = _step_asset(
            asset_id="STEP-9", class_name="com.automation.steps.B", method_name="b", pattern="b"
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(a, b))
        provider = _StubEmbeddingProvider({"a": _ANCHOR, "b": _vector_at_similarity(0.92)})
        return catalog, provider

    def test_flagged_at_default_threshold(self) -> None:
        catalog, provider = self._catalog_and_provider()
        result = sweep_near_duplicates(catalog, embedding_provider=provider)
        assert DEFAULT_NEAR_DUPLICATE_THRESHOLD == pytest.approx(0.90)
        assert len(result.clusters) == 1

    def test_not_flagged_when_threshold_raised_above_the_score(self) -> None:
        catalog, provider = self._catalog_and_provider()
        result = sweep_near_duplicates(catalog, embedding_provider=provider, threshold=0.95)
        assert result.clusters == ()

    def test_flagged_when_threshold_lowered_below_the_score(self) -> None:
        catalog, provider = self._catalog_and_provider()
        result = sweep_near_duplicates(catalog, embedding_provider=provider, threshold=0.85)
        assert len(result.clusters) == 1


class TestClusterFormation:
    def test_three_mutually_near_dup_assets_form_one_cluster_not_three_pairs(self) -> None:
        a = _step_asset(
            asset_id="STEP-A", class_name="com.automation.steps.A", method_name="a", pattern="a"
        )
        b = _step_asset(
            asset_id="STEP-B", class_name="com.automation.steps.B", method_name="b", pattern="b"
        )
        c = _step_asset(
            asset_id="STEP-C", class_name="com.automation.steps.C", method_name="c", pattern="c"
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(a, b, c))
        # All three mutually score above threshold.
        provider = _StubEmbeddingProvider(
            {"a": (1.0, 0.0), "b": (0.99, 0.14107), "c": (0.98, 0.19867)}
        )

        result = sweep_near_duplicates(catalog, embedding_provider=provider)

        assert len(result.clusters) == 1
        assert {m.asset_id for m in result.clusters[0].members} == {"STEP-A", "STEP-B", "STEP-C"}
        assert len(result.clusters[0].pairwise_scores) == 3  # all 3 pairs independently qualified

    def test_transitive_chain_forms_one_cluster_even_when_the_endpoints_dont_qualify(self) -> None:
        """A near-dups B, B near-dups C, but A vs C scores below threshold
        -- still ONE cluster (transitive), and `pairwise_scores` lists only
        the two edges that actually qualified, never a fabricated A-C
        score."""
        a = _step_asset(
            asset_id="STEP-D", class_name="com.automation.steps.D", method_name="d", pattern="d"
        )
        b = _step_asset(
            asset_id="STEP-E", class_name="com.automation.steps.E", method_name="e", pattern="e"
        )
        c = _step_asset(
            asset_id="STEP-F", class_name="com.automation.steps.F", method_name="f", pattern="f"
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(a, b, c))

        # Three vectors on the unit circle: d at angle 0, e at angle
        # acos(0.95) (so d<->e cosine = 0.95, qualifies), f a further
        # acos(0.93) beyond e (so e<->f cosine = 0.93, qualifies) -- placing
        # d<->f's own angle at their SUM, whose cosine is well under 0.90,
        # so that pair does NOT independently qualify.
        import math

        theta_e = math.acos(0.95)
        theta_f = theta_e + math.acos(0.93)
        d_vec = (1.0, 0.0)
        e_vec = (math.cos(theta_e), math.sin(theta_e))
        f_vec = (math.cos(theta_f), math.sin(theta_f))
        assert cosine_similarity(d_vec, f_vec) < DEFAULT_NEAR_DUPLICATE_THRESHOLD
        provider = _StubEmbeddingProvider({"d": d_vec, "e": e_vec, "f": f_vec})

        result = sweep_near_duplicates(catalog, embedding_provider=provider)

        assert len(result.clusters) == 1
        cluster = result.clusters[0]
        assert {m.asset_id for m in cluster.members} == {"STEP-D", "STEP-E", "STEP-F"}
        # Only the qualifying edges are reported -- not all 3 possible pairs.
        qualifying_ids = {(p.asset_id_a, p.asset_id_b) for p in cluster.pairwise_scores}
        assert ("STEP-D", "STEP-F") not in qualifying_ids
        assert len(cluster.pairwise_scores) == 2

    def test_two_separate_clusters_stay_separate(self) -> None:
        login_a = _step_asset(
            asset_id="STEP-G", class_name="com.automation.steps.G", method_name="g", pattern="g"
        )
        login_b = _step_asset(
            asset_id="STEP-H", class_name="com.automation.steps.H", method_name="h", pattern="h"
        )
        checkout_a = _step_asset(
            asset_id="STEP-I", class_name="com.automation.steps.I", method_name="i", pattern="i"
        )
        checkout_b = _step_asset(
            asset_id="STEP-J", class_name="com.automation.steps.J", method_name="j", pattern="j"
        )
        catalog = AssetCatalog(
            baseline_root="/fake",
            step_definitions=(login_a, login_b, checkout_a, checkout_b),
        )
        provider = _StubEmbeddingProvider(
            {
                "g": (1.0, 0.0, 0.0),
                "h": (*_vector_at_similarity(0.95), 0.0),
                "i": (0.0, 0.0, 1.0),
                "j": (0.0, 0.05, 0.99875),  # close to (0,0,1), far from (1,0,0)
            }
        )

        result = sweep_near_duplicates(catalog, embedding_provider=provider)

        assert len(result.clusters) == 2
        member_sets = [{m.asset_id for m in c.members} for c in result.clusters]
        assert {"STEP-G", "STEP-H"} in member_sets
        assert {"STEP-I", "STEP-J"} in member_sets


class TestBatchingCostShape:
    def test_whole_catalog_embedded_in_exactly_one_call(self) -> None:
        assets = tuple(
            _step_asset(
                asset_id=f"STEP-{i}",
                class_name=f"com.automation.steps.C{i}",
                method_name=f"step{i}",
                pattern=f"pattern number {i}",
            )
            for i in range(5)
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=assets)
        vectors: dict[str, tuple[float, ...]] = {
            f"pattern number {i}": (float(i), 1.0) for i in range(5)
        }
        provider = _CountingEmbeddingProvider(vectors)

        sweep_near_duplicates(catalog, embedding_provider=provider)

        assert len(provider.calls) == 1
        assert len(provider.calls[0]) == 5  # every asset's text, in one call


class TestNoBaselineMutation:
    def test_sweep_never_writes_or_modifies_the_baseline(self, tmp_path: Path) -> None:
        """End-to-end against a REAL filesystem scan: reconciles a real
        tracked-baseline layout, sweeps it, then proves every file's
        content and mtime are byte-for-byte unchanged and no new file was
        created -- the same read-only proof component 1's own test suite
        established for orphan detection."""
        java_dir = tmp_path / "src" / "test" / "java" / "com" / "automation" / "steps"
        java_dir.mkdir(parents=True)
        step_def_file = java_dir / "LoginSteps.java"
        step_def_file.write_text(
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n\n"
            "public class LoginSteps {\n"
            '    @Given("user logs in")\n'
            "    public void userLogsIn() {\n"
            "    }\n\n"
            '    @Given("user signs in")\n'
            "    public void userSignsIn() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        before_content = step_def_file.read_text(encoding="utf-8")
        before_mtime = os.stat(step_def_file).st_mtime_ns
        before_tree = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

        catalog = reconcile(tmp_path)
        assert len(catalog.step_definitions) == 2
        # Key the stub by the REAL embedding text the real scan produces
        # (pattern + derived semantic tags, `step_definition_embedding_text`)
        # rather than assuming its exact shape.
        real_texts = [step_definition_embedding_text(asset) for asset in catalog.step_definitions]
        provider = _StubEmbeddingProvider(
            {real_texts[0]: _ANCHOR, real_texts[1]: _vector_at_similarity(0.95)}
        )
        result = sweep_near_duplicates(catalog, embedding_provider=provider)

        # The near-dup is correctly found (proves the read side worked).
        assert len(result.clusters) == 1

        after_content = step_def_file.read_text(encoding="utf-8")
        after_mtime = os.stat(step_def_file).st_mtime_ns
        after_tree = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

        assert after_content == before_content
        assert after_mtime == before_mtime
        assert after_tree == before_tree


class TestDeterminism:
    def test_same_inputs_yield_the_same_result_every_time(self) -> None:
        a = _step_asset(
            asset_id="STEP-K", class_name="com.automation.steps.K", method_name="k", pattern="k"
        )
        b = _step_asset(
            asset_id="STEP-L", class_name="com.automation.steps.L", method_name="l", pattern="l"
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(a, b))
        provider = _StubEmbeddingProvider({"k": _ANCHOR, "l": _vector_at_similarity(0.95)})

        first = sweep_near_duplicates(catalog, embedding_provider=provider)
        second = sweep_near_duplicates(catalog, embedding_provider=provider)

        assert first == second
