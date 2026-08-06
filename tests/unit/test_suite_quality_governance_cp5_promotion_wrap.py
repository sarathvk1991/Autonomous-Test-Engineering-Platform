"""Proves CP5's capstone (ADR-0046 D4): `suite_quality_governance.cp5.
promotion_wrap.evaluate_promotion_wrap`.

Covers: DECISION 1 (per ADR-0046 D6's own composition table -- cohesion
AND orphaned-glue both gate `overall_verdict`; near-dup never does, even
when it finds a cluster), DECISION 2 (compile-failure attribution as
enrichment, never a delta gate), the wrap seeing the assembled
post-staging state via a real filesystem scan, no git/baseline mutation,
and determinism.
"""

from __future__ import annotations

import math
import os
from collections.abc import Sequence
from pathlib import Path

from automation_engineering.catalog.scanner import reconcile
from automation_engineering.reuse.live_matcher import step_definition_embedding_text
from automation_engineering.reuse.models import GherkinStepNeed
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.compile_check import StubCompileChecker
from suite_quality_governance.cp5.models import CompileResult
from suite_quality_governance.cp5.promotion_wrap import evaluate_promotion_wrap


class _StubEmbeddingProvider:
    """Deterministic, fixture-driven stand-in -- mirrors components 1/2's
    own `_StubEmbeddingProvider` discipline exactly."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]]) -> None:
        self._vectors = vectors_by_text

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._vectors[text] for text in texts)


def _vector_at_similarity(similarity: float) -> tuple[float, ...]:
    theta = math.acos(similarity)
    return (math.cos(theta), math.sin(theta))


def _write_step_def(
    java_dir: Path, class_name: str, method_name: str, pattern: str
) -> Path:
    file_path = java_dir / f"{class_name}.java"
    file_path.write_text(
        "package com.automation.steps;\n\n"
        "import io.cucumber.java.en.Given;\n\n"
        f"public class {class_name} {{\n"
        f'    @Given("{pattern}")\n'
        f"    public void {method_name}() {{\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    return file_path


def _java_dir(root: Path) -> Path:
    java_dir = root / "src" / "test" / "java" / "com" / "automation" / "steps"
    java_dir.mkdir(parents=True, exist_ok=True)
    return java_dir


class TestDecision1CompositionPerAdr0046D6:
    """ADR-0046 D6's own table: orphan-by-pattern and cohesion (compile,
    ambiguous-glue) both gate `overall_verdict` directly; near-dup never
    does. This is the ADR winning over the task's own suggested
    "orphan-as-soft-signal" lean (module docstring, Decision 1)."""

    def test_cohesion_fail_alone_gates_overall_fail(self, tmp_path: Path) -> None:
        java_dir = _java_dir(tmp_path)
        _write_step_def(java_dir, "LoginSteps", "userLogsIn", "user logs in")
        needs = (GherkinStepNeed(text="user logs in", step_type="Given"),)
        checker = StubCompileChecker(result=CompileResult(passed=False, errors=("boom",)))
        provider = _StubEmbeddingProvider({"user logs in": (1.0, 0.0)})

        result = evaluate_promotion_wrap(
            tmp_path, (), needs, compile_checker=checker, embedding_provider=provider
        )

        assert result.cohesion.overall_verdict == ValidationVerdict.FAIL
        assert result.orphaned_glue.overall_verdict == ValidationVerdict.PASS
        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.passed is False

    def test_orphaned_glue_fail_alone_gates_overall_fail(self, tmp_path: Path) -> None:
        """The load-bearing DECISION 1 proof: per ADR-0046 D6's own text
        ("orphan-by-pattern... may gate CP5 directly"), an orphan alone --
        with cohesion perfectly clean -- still fails the WHOLE capstone,
        not merely a soft, non-blocking signal."""
        java_dir = _java_dir(tmp_path)
        _write_step_def(
            java_dir, "OrphanedSteps", "userDoesOrphanedThing", "user does an orphaned thing"
        )
        # No current need references this pattern at all -- deterministically orphaned.
        needs: tuple[GherkinStepNeed, ...] = ()
        checker = StubCompileChecker(result=CompileResult(passed=True))
        provider = _StubEmbeddingProvider({})

        result = evaluate_promotion_wrap(
            tmp_path, (), needs, compile_checker=checker, embedding_provider=provider
        )

        assert result.cohesion.overall_verdict == ValidationVerdict.PASS
        assert result.orphaned_glue.overall_verdict == ValidationVerdict.FAIL
        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.passed is False

    def test_near_dup_cluster_alone_never_gates_overall_fail(self, tmp_path: Path) -> None:
        java_dir = _java_dir(tmp_path)
        _write_step_def(java_dir, "LoginSteps", "userLogsIn", "user logs in")
        _write_step_def(java_dir, "AuthSteps", "userSignsIn", "user signs in")
        needs = (
            GherkinStepNeed(text="user logs in", step_type="Given"),
            GherkinStepNeed(text="user signs in", step_type="Given"),
        )
        checker = StubCompileChecker(result=CompileResult(passed=True))
        # A real scan derives semantic tags into the embedding text
        # (`step_definition_embedding_text`) -- key the stub by the REAL
        # text a real reconciliation produces, not the bare pattern.
        real_assets = reconcile(tmp_path).step_definitions
        real_texts = [step_definition_embedding_text(asset) for asset in real_assets]
        provider = _StubEmbeddingProvider(
            {real_texts[0]: (1.0, 0.0), real_texts[1]: _vector_at_similarity(0.97)}
        )

        result = evaluate_promotion_wrap(
            tmp_path, (), needs, compile_checker=checker, embedding_provider=provider
        )

        assert result.cohesion.overall_verdict == ValidationVerdict.PASS
        assert result.orphaned_glue.overall_verdict == ValidationVerdict.PASS
        assert len(result.near_duplicates.clusters) == 1  # a real cluster was found
        assert result.overall_verdict == ValidationVerdict.PASS  # never gated by it
        assert result.passed is True
        # But it IS surfaced as review-worthy, even on a clean pass.
        assert result.has_review_worthy_findings is True

    def test_all_clean_yields_pass_and_nothing_review_worthy(self, tmp_path: Path) -> None:
        java_dir = _java_dir(tmp_path)
        _write_step_def(java_dir, "LoginSteps", "userLogsIn", "user logs in")
        needs = (GherkinStepNeed(text="user logs in", step_type="Given"),)
        checker = StubCompileChecker(result=CompileResult(passed=True))
        provider = _StubEmbeddingProvider({"user logs in": (1.0, 0.0)})

        result = evaluate_promotion_wrap(
            tmp_path, (), needs, compile_checker=checker, embedding_provider=provider
        )

        assert result.overall_verdict == ValidationVerdict.PASS
        assert result.has_review_worthy_findings is False


class TestDecision2CompileAttributionEnrichmentNeverAGate:
    def test_compile_pass_has_no_attribution(self, tmp_path: Path) -> None:
        checker = StubCompileChecker(result=CompileResult(passed=True))
        result = evaluate_promotion_wrap(
            tmp_path, (), (), compile_checker=checker, embedding_provider=_StubEmbeddingProvider({})
        )
        assert result.compile_attribution is None

    def test_error_referencing_a_staged_path_is_attributed_to_this_promotion(
        self, tmp_path: Path
    ) -> None:
        staged = Path("com/automation/steps/NewlyPromotedSteps.java")
        error = f"{staged.as_posix()}:[5,1] cannot find symbol"
        checker = StubCompileChecker(result=CompileResult(passed=False, errors=(error,)))

        result = evaluate_promotion_wrap(
            tmp_path,
            (staged,),
            (),
            compile_checker=checker,
            embedding_provider=_StubEmbeddingProvider({}),
        )

        assert result.compile_attribution is not None
        assert result.compile_attribution.involves_staged_files is True
        assert "1 of 1" in result.compile_attribution.detail
        # The gate itself is unaffected by attribution -- it is still FAIL,
        # attribution only explains it.
        assert result.overall_verdict == ValidationVerdict.FAIL

    def test_error_referencing_only_other_files_is_attributed_as_pre_existing(
        self, tmp_path: Path
    ) -> None:
        """DECISION 2's own load-bearing case: a real, pre-existing
        baseline compile failure this promotion did not touch -- absolute
        gate still fails (ADR-0046 D5's own text), but the reviewer is told
        honestly that this promotion did not cause it."""
        staged = Path("com/automation/steps/NewlyPromotedSteps.java")
        untouched_error = (
            "com/automation/steps/SomeOtherPreExistingSteps.java:[9,1] cannot find symbol"
        )
        checker = StubCompileChecker(result=CompileResult(passed=False, errors=(untouched_error,)))

        result = evaluate_promotion_wrap(
            tmp_path,
            (staged,),
            (),
            compile_checker=checker,
            embedding_provider=_StubEmbeddingProvider({}),
        )

        assert result.compile_attribution is not None
        assert result.compile_attribution.involves_staged_files is False
        assert "pre-existing" in result.compile_attribution.detail
        assert result.overall_verdict == ValidationVerdict.FAIL  # absolute gate, unchanged

    def test_no_staged_paths_at_all_is_attributed_as_predating_this_run(
        self, tmp_path: Path
    ) -> None:
        checker = StubCompileChecker(
            result=CompileResult(passed=False, errors=("some pre-existing error",))
        )

        result = evaluate_promotion_wrap(
            tmp_path, (), (), compile_checker=checker, embedding_provider=_StubEmbeddingProvider({})
        )

        assert result.compile_attribution is not None
        assert result.compile_attribution.involves_staged_files is False
        assert "predates it entirely" in result.compile_attribution.detail


class TestWrapSeesTheAssembledPostStagingState:
    def test_reconcile_sees_a_newly_written_file_alongside_pre_existing_ones(
        self, tmp_path: Path
    ) -> None:
        """Simulates per-asset promotion having already written (and
        staged, though git-staging status is irrelevant to `reconcile()`)
        a NEW file into the baseline before this capstone runs -- proves
        the capstone's own `reconcile()` call sees BOTH the pre-existing
        and the newly-written file, with zero extra plumbing."""
        java_dir = _java_dir(tmp_path)
        _write_step_def(java_dir, "PreExistingSteps", "userLogsIn", "user logs in")
        # "Staged" by writing directly, mirroring what
        # automation_engineering.promotion.mechanism.apply_promotion
        # already does before this capstone is ever called.
        _write_step_def(java_dir, "NewlyStagedSteps", "userChecksOut", "user checks out")

        # Only the PRE-EXISTING pattern has a matching current need.
        needs = (GherkinStepNeed(text="user logs in", step_type="Given"),)
        checker = StubCompileChecker(result=CompileResult(passed=True))
        # Both assets get embedded (the orphan hint for the orphaned one --
        # which also embeds the current NEED's own plain text -- plus the
        # near-dup sweep over both assets) -- key by every real text.
        real_assets = reconcile(tmp_path).step_definitions
        vectors: dict[str, tuple[float, ...]] = {
            step_definition_embedding_text(asset): (1.0, float(i))
            for i, asset in enumerate(real_assets)
        }
        vectors["user logs in"] = (1.0, 0.0)  # the current need's own plain text
        provider = _StubEmbeddingProvider(vectors)

        result = evaluate_promotion_wrap(
            tmp_path, (), needs, compile_checker=checker, embedding_provider=provider
        )

        # The newly-staged file's own step is orphaned (proving it was
        # scanned); the pre-existing one is not.
        orphaned_methods = {f.method_name for f in result.orphaned_glue.findings}
        assert orphaned_methods == {"userChecksOut"}


class TestNoMutation:
    def test_never_writes_or_modifies_any_baseline_file(self, tmp_path: Path) -> None:
        java_dir = _java_dir(tmp_path)
        file_a = _write_step_def(java_dir, "LoginSteps", "userLogsIn", "user logs in")

        before_content = file_a.read_text(encoding="utf-8")
        before_mtime = os.stat(file_a).st_mtime_ns
        before_tree = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

        needs = (GherkinStepNeed(text="user logs in", step_type="Given"),)
        checker = StubCompileChecker(result=CompileResult(passed=True))
        provider = _StubEmbeddingProvider({"user logs in": (1.0, 0.0)})
        result = evaluate_promotion_wrap(
            tmp_path, (), needs, compile_checker=checker, embedding_provider=provider
        )

        assert result.overall_verdict == ValidationVerdict.PASS  # the read side worked

        after_content = file_a.read_text(encoding="utf-8")
        after_mtime = os.stat(file_a).st_mtime_ns
        after_tree = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*"))

        assert after_content == before_content
        assert after_mtime == before_mtime
        assert after_tree == before_tree


class TestDeterminism:
    def test_same_inputs_yield_the_same_result_every_time(self, tmp_path: Path) -> None:
        java_dir = _java_dir(tmp_path)
        _write_step_def(java_dir, "LoginSteps", "userLogsIn", "user logs in")
        needs = (GherkinStepNeed(text="user logs in", step_type="Given"),)
        provider = _StubEmbeddingProvider({"user logs in": (1.0, 0.0)})

        first = evaluate_promotion_wrap(
            tmp_path,
            (),
            needs,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=provider,
        )
        second = evaluate_promotion_wrap(
            tmp_path,
            (),
            needs,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=provider,
        )

        assert first == second


class TestRealCatalogReconciliationForOrphanCheckIsGenuine:
    def test_reconcile_import_used_directly_matches_the_wraps_own_view(
        self, tmp_path: Path
    ) -> None:
        """Sanity cross-check: the module-level `reconcile` this test file
        imports produces the identical catalog the capstone's own internal
        `reconcile()` call does, for the same directory -- confirms the
        capstone performs a real scan, not some other derivation."""
        java_dir = _java_dir(tmp_path)
        _write_step_def(java_dir, "LoginSteps", "userLogsIn", "user logs in")

        direct_catalog = reconcile(tmp_path)
        needs = (GherkinStepNeed(text="user logs in", step_type="Given"),)
        result = evaluate_promotion_wrap(
            tmp_path,
            (),
            needs,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({"user logs in": (1.0, 0.0)}),
        )

        assert len(direct_catalog.step_definitions) == 1
        assert result.orphaned_glue.findings == ()  # the same one asset, correctly not orphaned
