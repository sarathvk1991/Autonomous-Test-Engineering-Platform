"""Proves CP5's orphaned-glue component (ADR-0046 D2/D6):
`suite_quality_governance.cp5.orphaned_glue.detect_orphaned_glue`.

Covers: the deterministic gate (matched -> not orphaned, unmatched ->
orphaned, including a Cucumber-Expression-shaped pattern); the semantic
advisory hint never changing the verdict; the action being flag-only
(never a baseline mutation, proven against a real filesystem scan); and
determinism.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

import pytest

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset
from automation_engineering.catalog.scanner import reconcile
from automation_engineering.reuse.models import GherkinStepNeed
from automation_engineering.stage.gherkin_needs import (
    derive_feature_step_needs,
    derive_unique_step_needs,
)
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.models import SemanticOrphanHint
from suite_quality_governance.cp5.orphaned_glue import (
    DEFAULT_SEMANTIC_HINT_FLOOR,
    detect_orphaned_glue,
)


def _step_asset(
    *,
    asset_id: str,
    class_name: str,
    method_name: str,
    pattern: str,
    semantic_tags: tuple[str, ...] = (),
) -> StepDefinitionAsset:
    """Build a real, self-consistent `StepDefinitionAsset` fixture --
    `signature_alignment` is computed by the real `correlate`, never
    hand-faked, so a fixture with a Cucumber-Expression pattern carries a
    genuinely aligned signature the same way a real catalog scan would."""
    return StepDefinitionAsset(
        asset_id=asset_id,
        class_name=class_name,
        method_name=method_name,
        step_type="Given",
        pattern=pattern,
        parameters=(),
        return_type="void",
        source_file=f"{class_name.replace('.', '/')}.java",
        content_hash=f"hash-{asset_id}",
        signature_alignment=correlate(pattern, ()),
        semantic_tags=semantic_tags,
    )


class _StubEmbeddingProvider:
    """Deterministic, fixture-driven stand-in for a live embedding
    provider (mirrors `automation_engineering.reuse.matcher.
    StubSemanticMatcher`'s own "test/dev scaffolding only" discipline) --
    returns a pre-authored vector per text, keyed by exact text, so a test
    can script exactly which cosine-similarity score results."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]]) -> None:
        self._vectors = vectors_by_text

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._vectors[text] for text in texts)


class TestDeterministicGate:
    def test_asset_referenced_by_a_current_need_is_not_orphaned(self) -> None:
        asset = _step_asset(
            asset_id="STEP-1",
            class_name="com.automation.steps.LoginSteps",
            method_name="userIsOnLoginPage",
            pattern="user is on the login page",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(asset,))
        needs = (GherkinStepNeed(text="user is on the login page", step_type="Given"),)

        result = detect_orphaned_glue(catalog, needs)

        assert result.overall_verdict == ValidationVerdict.PASS
        assert result.findings == ()
        assert result.passed is True

    def test_asset_referenced_by_no_current_need_is_orphaned(self) -> None:
        asset = _step_asset(
            asset_id="STEP-2",
            class_name="com.automation.steps.LegacySteps",
            method_name="userDoesSomethingOld",
            pattern="user does something old",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(asset,))
        needs = (GherkinStepNeed(text="user logs in", step_type="When"),)

        result = detect_orphaned_glue(catalog, needs)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.passed is False
        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.asset_id == "STEP-2"
        assert finding.class_name == "com.automation.steps.LegacySteps"
        assert finding.method_name == "userDoesSomethingOld"
        assert finding.pattern == "user does something old"
        assert finding.semantic_hint is None

    def test_empty_needs_orphans_every_asset(self) -> None:
        asset = _step_asset(
            asset_id="STEP-3",
            class_name="com.automation.steps.AnySteps",
            method_name="anyStep",
            pattern="anything at all",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(asset,))

        result = detect_orphaned_glue(catalog, ())

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert {f.asset_id for f in result.findings} == {"STEP-3"}

    def test_empty_catalog_orphans_nothing(self) -> None:
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=())
        needs = (GherkinStepNeed(text="user logs in", step_type="When"),)

        result = detect_orphaned_glue(catalog, needs)

        assert result.overall_verdict == ValidationVerdict.PASS
        assert result.findings == ()

    def test_deterministic_matcher_is_actually_reused_not_reimplemented(self) -> None:
        """A Cucumber-Expression-shaped pattern is bound correctly, proving
        `pattern_matches_text` -- not a naive substring/equality check --
        drives the gate."""
        asset = _step_asset(
            asset_id="STEP-4",
            class_name="com.automation.steps.CredentialSteps",
            method_name="userSubmitsCredentials",
            pattern="user submits {string} and {string}",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(asset,))

        matching_needs = (
            GherkinStepNeed(text='user submits "alice" and "secret"', step_type="When"),
        )
        assert detect_orphaned_glue(catalog, matching_needs).overall_verdict == (
            ValidationVerdict.PASS
        )

        non_matching_needs = (GherkinStepNeed(text="user submits credentials", step_type="When"),)
        result = detect_orphaned_glue(catalog, non_matching_needs)
        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.findings[0].asset_id == "STEP-4"

    def test_multiple_assets_evaluated_independently(self) -> None:
        referenced = _step_asset(
            asset_id="STEP-5",
            class_name="com.automation.steps.LoginSteps",
            method_name="userLogsIn",
            pattern="user logs in",
        )
        orphaned = _step_asset(
            asset_id="STEP-6",
            class_name="com.automation.steps.DeadSteps",
            method_name="userDoesDeadThing",
            pattern="user does a dead thing",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(referenced, orphaned))
        needs = (GherkinStepNeed(text="user logs in", step_type="Given"),)

        result = detect_orphaned_glue(catalog, needs)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert [f.asset_id for f in result.findings] == ["STEP-6"]


class TestSemanticAdvisoryNeverGates:
    def _orphaned_catalog_and_needs(self) -> tuple[AssetCatalog, tuple[GherkinStepNeed, ...]]:
        asset = _step_asset(
            asset_id="STEP-7",
            class_name="com.automation.steps.RenamedSteps",
            method_name="userSignsIn",
            pattern="user signs in",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(asset,))
        # Reworded step: no longer matches the pattern deterministically,
        # but is semantically close.
        needs = (GherkinStepNeed(text="user authenticates", step_type="Given"),)
        return catalog, needs

    def test_hint_attached_when_a_need_scores_above_the_floor(self) -> None:
        catalog, needs = self._orphaned_catalog_and_needs()
        provider = _StubEmbeddingProvider(
            {
                "user signs in": (1.0, 0.0),
                "user authenticates": (0.9, 0.436),  # cosine ~0.9, above the 0.70 floor
            }
        )

        result = detect_orphaned_glue(catalog, needs, embedding_provider=provider)

        assert result.overall_verdict == ValidationVerdict.FAIL  # still orphaned
        hint = result.findings[0].semantic_hint
        assert hint is not None
        assert isinstance(hint, SemanticOrphanHint)
        assert hint.closest_need_text == "user authenticates"
        assert hint.confidence == pytest.approx(0.9, abs=0.05)

    def test_no_hint_when_nothing_clears_the_floor(self) -> None:
        catalog, needs = self._orphaned_catalog_and_needs()
        provider = _StubEmbeddingProvider(
            {
                "user signs in": (1.0, 0.0),
                "user authenticates": (0.0, 1.0),  # cosine 0.0, far below the floor
            }
        )

        result = detect_orphaned_glue(catalog, needs, embedding_provider=provider)

        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.findings[0].semantic_hint is None

    def test_hint_presence_or_absence_never_changes_the_verdict_or_the_orphan_set(self) -> None:
        """The load-bearing proof (ADR-0046 D6): the deterministic gate's
        own findings are identical whether or not a semantic hint is
        computed -- only the `semantic_hint` field differs."""
        catalog, needs = self._orphaned_catalog_and_needs()

        without_hint = detect_orphaned_glue(catalog, needs, embedding_provider=None)

        provider_with_hint = _StubEmbeddingProvider(
            {"user signs in": (1.0, 0.0), "user authenticates": (0.9, 0.436)}
        )
        with_hint = detect_orphaned_glue(catalog, needs, embedding_provider=provider_with_hint)

        provider_without_hint = _StubEmbeddingProvider(
            {"user signs in": (1.0, 0.0), "user authenticates": (0.0, 1.0)}
        )
        with_provider_but_no_hint = detect_orphaned_glue(
            catalog, needs, embedding_provider=provider_without_hint
        )

        # Same verdict, same orphaned asset set, regardless of the hint.
        assert (
            without_hint.overall_verdict
            == with_hint.overall_verdict
            == with_provider_but_no_hint.overall_verdict
            == ValidationVerdict.FAIL
        )
        assert (
            {f.asset_id for f in without_hint.findings}
            == {f.asset_id for f in with_hint.findings}
            == {f.asset_id for f in with_provider_but_no_hint.findings}
            == {"STEP-7"}
        )
        # Only the hint field differs.
        assert without_hint.findings[0].semantic_hint is None
        assert with_hint.findings[0].semantic_hint is not None
        assert with_provider_but_no_hint.findings[0].semantic_hint is None

    def test_semantic_hint_floor_reuses_the_reuse_engines_own_calibrated_floor(self) -> None:
        assert DEFAULT_SEMANTIC_HINT_FLOOR == pytest.approx(0.70)

    def test_one_batched_embed_call_for_the_whole_detection_not_one_per_asset(self) -> None:
        first_asset = _step_asset(
            asset_id="STEP-8",
            class_name="com.automation.steps.A",
            method_name="a",
            pattern="a orphaned step",
        )
        second_asset = _step_asset(
            asset_id="STEP-9",
            class_name="com.automation.steps.B",
            method_name="b",
            pattern="b orphaned step",
        )
        catalog = AssetCatalog(
            baseline_root="/fake", step_definitions=(first_asset, second_asset)
        )
        needs = (GherkinStepNeed(text="unrelated need", step_type="Given"),)

        calls: list[list[str]] = []

        class _CountingProvider:
            def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
                calls.append(list(texts))
                return tuple((1.0, 0.0) for _ in texts)

        result = detect_orphaned_glue(catalog, needs, embedding_provider=_CountingProvider())

        assert len(result.findings) == 2
        assert len(calls) == 1  # exactly one batched call, not one per orphaned asset
        assert len(calls[0]) == 3  # 2 asset texts + 1 need text, all in that one call


class TestActionIsFlagOnlyNeverAMutation:
    def test_no_baseline_file_is_written_or_modified(self, tmp_path: Path) -> None:
        """End-to-end against a REAL filesystem scan (not a hand-built
        catalog): reconciles a real tracked-baseline layout, derives needs
        from a real `.feature` file, runs detection, then proves every
        baseline file's content and mtime are byte-for-byte unchanged and
        no new file was created -- the strongest available proof that
        detection never mutates the baseline (ADR-0046 D2: "flag for
        review, never auto-remove")."""
        java_dir = tmp_path / "src" / "test" / "java" / "com" / "automation" / "steps"
        java_dir.mkdir(parents=True)
        step_def_file = java_dir / "LoginSteps.java"
        step_def_file.write_text(
            "package com.automation.steps;\n\n"
            "import io.cucumber.java.en.Given;\n\n"
            "public class LoginSteps {\n"
            '    @Given("user is on the login page")\n'
            "    public void userIsOnLoginPage() {\n"
            "    }\n\n"
            '    @Given("user does something orphaned")\n'
            "    public void userDoesSomethingOrphaned() {\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )

        feature_file = tmp_path / "Login.feature"
        feature_file.write_text(
            "Feature: Login\n\n"
            "  Scenario: Successful login\n"
            "    Given user is on the login page\n",
            encoding="utf-8",
        )

        before_content = step_def_file.read_text(encoding="utf-8")
        before_mtime = os.stat(step_def_file).st_mtime_ns
        before_tree = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

        catalog = reconcile(tmp_path)
        feature_needs = derive_feature_step_needs(
            feature_file.read_text(encoding="utf-8"), file_path=feature_file
        )
        current_needs = derive_unique_step_needs((feature_needs,))

        result = detect_orphaned_glue(catalog, current_needs)

        # The orphan is correctly found (proves the read side actually
        # worked, not merely "nothing happened").
        assert result.overall_verdict == ValidationVerdict.FAIL
        assert len(result.findings) == 1
        assert result.findings[0].method_name == "userDoesSomethingOrphaned"

        after_content = step_def_file.read_text(encoding="utf-8")
        after_mtime = os.stat(step_def_file).st_mtime_ns
        after_tree = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

        assert after_content == before_content
        assert after_mtime == before_mtime
        assert after_tree == before_tree  # no file created, moved, or deleted


class TestDeterminism:
    def test_same_inputs_yield_the_same_result_every_time(self) -> None:
        referenced = _step_asset(
            asset_id="STEP-10",
            class_name="com.automation.steps.LoginSteps",
            method_name="userLogsIn",
            pattern="user logs in",
        )
        orphaned = _step_asset(
            asset_id="STEP-11",
            class_name="com.automation.steps.DeadSteps",
            method_name="deadStep",
            pattern="a step nothing references",
        )
        catalog = AssetCatalog(baseline_root="/fake", step_definitions=(referenced, orphaned))
        needs = (GherkinStepNeed(text="user logs in", step_type="Given"),)

        first = detect_orphaned_glue(catalog, needs)
        second = detect_orphaned_glue(catalog, needs)

        assert first == second
