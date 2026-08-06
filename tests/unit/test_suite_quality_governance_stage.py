"""Stage 16 -- Suite Quality Governance (ADR-0036, ADR-0046) as a resumable,
persisted run/stage-state stage -- the wiring that RUNS CP5's already-built
capstone (`suite_quality_governance.cp5.promotion_wrap.evaluate_promotion_wrap`)
immediately after stage 15's own per-asset promotion has staged its
candidates (`git add`, never `git commit`), mirroring stage 15's own
integration proof (`tests/unit/test_automation_engineering_stage.py`) and
CP5's own capstone proof (`tests/unit/test_suite_quality_governance_cp5_
promotion_wrap.py`).

Every test uses a REAL, per-test git repository as `baseline_root`/`repo_root`
(mirroring `test_automation_engineering_promotion_loop.py`'s own "loop-closing
proof" discipline) so the wrap-order claim -- CP5 sees whatever stage 15's own
`stage_promoted_assets` already staged, with zero extra plumbing -- is proven
against real git state, not merely asserted. Only the compile checker and the
embedding provider are stubbed (`StubCompileChecker`, a local
`_StubEmbeddingProvider`/`_RaisingEmbeddingProvider`) -- the ONE live-
infrastructure seam this stage's own module docstring names (a JDK/Maven
toolchain, a real embedding provider); every other piece (`reconcile`,
`evaluate_promotion_wrap`, `RunStateManager`) is real, unstubbed code.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from automation_engineering.catalog.scanner import JAVA_SOURCE_SUBPATH
from automation_engineering.promotion.mechanism import stage_promoted_assets
from automation_engineering.stage.models import (
    AUTOMATION_ENGINEERING_PACKAGE_FILENAME,
    PROMOTION_REPORT_FILENAME,
)
from feature_engineering.stage.workspace import FEATURES_SUBPATH
from requirement_intelligence.run_state.models import StageRecord
from requirement_intelligence.run_state.run_state_manager import RunStateManager
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.compile_check import StubCompileChecker
from suite_quality_governance.cp5.models import CompileResult
from suite_quality_governance.stage.models import CP5_REPORT_FILENAME
from suite_quality_governance.stage.runner import (
    STAGE_ID,
    execute_suite_quality_governance_stage,
    run_suite_quality_governance_stage,
)

pytestmark = pytest.mark.unit

_RUN_STATE_CONTRACT_VERSION = "1.0.0"


class _StubEmbeddingProvider:
    """Deterministic, fixture-driven stand-in -- mirrors CP5's own
    `_StubEmbeddingProvider` discipline exactly (`tests/unit/
    test_suite_quality_governance_cp5_promotion_wrap.py`)."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]]) -> None:
        self._vectors = vectors_by_text

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._vectors[text] for text in texts)


class _RaisingEmbeddingProvider:
    """A stand-in that always raises -- injects a genuine, uncaught failure
    (unlike a compile failure, which CP5's own cohesion gate catches and
    turns into a deterministic FAIL criterion, `cohesion.py`'s own "fails
    closed, never crashes" contract) so the stage's own FAILED transition
    can be proven against a real exception, not a scripted result."""

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        raise RuntimeError("embedding transport unavailable")


def _run_git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_git_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run_git("init", "--quiet", cwd=root)
    _run_git("config", "user.email", "test@example.com", cwd=root)
    _run_git("config", "user.name", "Test", cwd=root)
    (root / ".gitkeep").write_text("", encoding="utf-8")
    _run_git("add", ".gitkeep", cwd=root)
    _run_git("commit", "--quiet", "-m", "initial baseline", cwd=root)


def _write_step_def(baseline_root: Path, class_name: str, method_name: str, pattern: str) -> Path:
    file_path = baseline_root / JAVA_SOURCE_SUBPATH / "com/automation/steps" / f"{class_name}.java"
    file_path.parent.mkdir(parents=True, exist_ok=True)
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


def _write_feature(baseline_root: Path, relative_path: str, content: str) -> Path:
    file_path = baseline_root / FEATURES_SUBPATH / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _write_promotion_report(run_dir: Path, promoted_baseline_relative_paths: list[str]) -> None:
    """Mimics stage 15's own persisted `promotion_report.json`
    (`automation_engineering.stage.runner`'s own write, `promotedPaths`
    relative to `baseline_root`) -- stage 16 reads this artifact from disk,
    never the in-memory `AutomationEngineeringStageResult` (module
    docstring, ADR-0036 D2)."""
    (run_dir / PROMOTION_REPORT_FILENAME).write_text(
        json.dumps(
            {
                "promotedCount": len(promoted_baseline_relative_paths),
                "promotedPaths": promoted_baseline_relative_paths,
            }
        ),
        encoding="utf-8",
    )


def _write_placeholder_automation_package(run_dir: Path) -> None:
    (run_dir / AUTOMATION_ENGINEERING_PACKAGE_FILENAME).write_text("{}", encoding="utf-8")


def _new_run_state_manager(run_dir: Path, *, run_id: str = "run-1") -> RunStateManager:
    return RunStateManager.create(
        run_dir, run_id=run_id, execution_name=None, contract_version=_RUN_STATE_CONTRACT_VERSION
    )


def _find_stage(run_state_mgr: RunStateManager, stage_id: str) -> StageRecord:
    return next(s for s in run_state_mgr.state.stages if s.stage_id == stage_id)


@pytest.fixture
def baseline_root(tmp_path: Path) -> Path:
    root = tmp_path / "test-suite-baseline"
    _init_git_repo(root)
    return root


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    d = tmp_path / "run"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# The wrap runs at the right point: stage 15 stages (git add) -> stage 16's
# reconcile() sees the ASSEMBLED baseline-plus-staged state, with zero extra
# plumbing (ADR-0046 D4, this module's own docstring).
# ---------------------------------------------------------------------------


class TestWrapSeesTheAssembledStagedStateAndRunsAtTheRightPoint:
    def test_reads_whole_feature_corpus_and_sees_the_newly_staged_java_file(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        from automation_engineering.catalog.scanner import reconcile
        from automation_engineering.reuse.live_matcher import step_definition_embedding_text

        # Pre-existing, committed: one feature, one matching step definition.
        _write_feature(
            baseline_root,
            "search.feature",
            "Feature: Search\n\n  Scenario: Find a product\n"
            "    Given I search for a product\n",
        )
        _write_step_def(baseline_root, "SearchSteps", "iSearch", "I search for a product")
        _run_git("add", ".", cwd=baseline_root)
        _run_git("commit", "--quiet", "-m", "pre-existing", cwd=baseline_root)

        # A SECOND feature file, proving the WHOLE corpus is scanned, not
        # merely the first file found (ADR-0046 D2: "every .feature file the
        # tracked baseline carries").
        _write_feature(
            baseline_root,
            "checkout.feature",
            "Feature: Checkout\n\n  Scenario: Pay\n    Given I pay for my cart\n",
        )
        _run_git("add", ".", cwd=baseline_root)
        _run_git("commit", "--quiet", "-m", "second feature", cwd=baseline_root)

        # Simulates stage 15 having ALREADY promoted-and-staged a NEW step
        # definition this run, whose pattern matches NEITHER feature -- a
        # genuine orphan, deliberately, so its presence in the deterministic
        # orphan finding proves the newly-staged file was scanned at all.
        new_path = _write_step_def(
            baseline_root, "NewlyPromotedSteps", "userDoesSomethingNew", "user does something new"
        )
        stage_promoted_assets([new_path], baseline_root)
        status_before = _run_git("status", "--porcelain", cwd=baseline_root).stdout
        assert "A  src/test/java/com/automation/steps/NewlyPromotedSteps.java" in status_before

        _write_placeholder_automation_package(run_dir)
        _write_promotion_report(
            run_dir, ["src/test/java/com/automation/steps/NewlyPromotedSteps.java"]
        )

        # Both step-definition assets get embedded (the orphan's own
        # semantic hint, plus the near-dup sweep over both) -- key by every
        # real text a real reconciliation produces, mirroring CP5's own
        # `TestWrapSeesTheAssembledPostStagingState` fixture exactly.
        real_assets = reconcile(baseline_root).step_definitions
        vectors: dict[str, tuple[float, ...]] = {
            step_definition_embedding_text(asset): (1.0, float(i))
            for i, asset in enumerate(real_assets)
        }
        vectors["I search for a product"] = (1.0, 0.0)
        vectors["I pay for my cart"] = (1.0, 0.0)

        run_state_mgr = _new_run_state_manager(run_dir)
        result = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider(vectors),
            baseline_root=baseline_root,
        )

        assert result is not None
        cp5 = result.result
        # The pre-existing step is referenced by "search.feature" -- not
        # orphaned. The newly-staged one matches no feature at all -- it IS
        # orphaned, proving reconcile() saw the assembled, post-staging
        # state, and proving BOTH feature files (not just one) contributed
        # to the current-needs set.
        orphaned_methods = {f.method_name for f in cp5.orphaned_glue.findings}
        assert orphaned_methods == {"userDoesSomethingNew"}
        assert cp5.overall_verdict == ValidationVerdict.FAIL  # orphan-by-pattern gates (D6)

        # Read-only w.r.t. git: the staged diff stage 15 left is untouched --
        # never unstaged, never committed (ADR-0046 D4/D5).
        status_after = _run_git("status", "--porcelain", cwd=baseline_root).stdout
        assert status_after == status_before
        log = _run_git("log", "--oneline", cwd=baseline_root).stdout
        assert log.strip().count("\n") == 2  # still exactly the three prior commits, no new one

    def test_compile_attribution_uses_the_java_root_relative_staged_path(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        """`CompileAttribution` matches `Promoted.candidate.relative_path`'s
        own shape (relative to `JAVA_SOURCE_SUBPATH`) -- proves stage 16
        strips `promotion_report.json`'s `baseline_root`-relative
        `src/test/java/...` prefix before handing `staged_paths` to CP5's
        capstone, rather than passing the mismatched shape through."""
        _write_placeholder_automation_package(run_dir)
        staged_relative = "com/automation/steps/NewlyPromotedSteps.java"
        _write_promotion_report(run_dir, [f"src/test/java/{staged_relative}"])
        error = f"{staged_relative}:[5,1] cannot find symbol"

        run_state_mgr = _new_run_state_manager(run_dir)
        result = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(
                result=CompileResult(passed=False, errors=(error,))
            ),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
        )

        assert result is not None
        attribution = result.result.compile_attribution
        assert attribution is not None
        assert attribution.involves_staged_files is True


# ---------------------------------------------------------------------------
# Suite-reject: routed to review (a FAIL verdict, surfaced in the persisted
# report), staged diff left exactly as promotion left it, no commit.
# ---------------------------------------------------------------------------


class TestSuiteRejectRoutesToReviewAndLeavesStagedDiffUntouched:
    def test_cohesion_failure_fails_cp5_and_never_touches_git(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        promoted = _write_step_def(baseline_root, "OrphanSteps", "doOrphan", "do an orphan thing")
        stage_promoted_assets([promoted], baseline_root)
        status_before = _run_git("status", "--porcelain", cwd=baseline_root).stdout

        _write_placeholder_automation_package(run_dir)
        _write_promotion_report(run_dir, ["src/test/java/com/automation/steps/OrphanSteps.java"])

        run_state_mgr = _new_run_state_manager(run_dir)
        result = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(
                result=CompileResult(passed=False, errors=("boom",))
            ),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
        )

        assert result is not None
        assert result.result.overall_verdict == ValidationVerdict.FAIL
        assert result.result.passed is False

        # Persisted, so a human reviewer can act on it.
        report_text = result.report_path.read_text(encoding="utf-8")
        assert "shared human review queue" in report_text
        cp5_json = json.loads(result.cp5_report_path.read_text(encoding="utf-8"))
        assert cp5_json["overallVerdict"] == "fail"

        # Never unstaged, never committed.
        status_after = _run_git("status", "--porcelain", cwd=baseline_root).stdout
        assert status_after == status_before
        log = _run_git("log", "--oneline", cwd=baseline_root).stdout
        assert log.strip().count("\n") == 0  # still exactly the initial commit

        stage = _find_stage(run_state_mgr, STAGE_ID)
        assert stage.status.value == "succeeded"  # the STAGE ran to completion; the VERDICT failed


# ---------------------------------------------------------------------------
# Suite-pass: nothing blocks; no suite-level objection.
# ---------------------------------------------------------------------------


class TestSuitePassProceeds:
    def test_all_clean_yields_pass_and_no_review_worthy_findings(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _write_feature(
            baseline_root,
            "login.feature",
            "Feature: Login\n\n  Scenario: Log in\n    Given user logs in\n",
        )
        promoted = _write_step_def(baseline_root, "LoginSteps", "userLogsIn", "user logs in")
        stage_promoted_assets([promoted], baseline_root)

        _write_placeholder_automation_package(run_dir)
        _write_promotion_report(run_dir, ["src/test/java/com/automation/steps/LoginSteps.java"])

        run_state_mgr = _new_run_state_manager(run_dir)
        result = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({"user logs in": (1.0, 0.0)}),
            baseline_root=baseline_root,
        )

        assert result is not None
        assert result.result.overall_verdict == ValidationVerdict.PASS
        assert result.result.has_review_worthy_findings is False


# ---------------------------------------------------------------------------
# Near-dup advisory: flagged for review, never blocks (ADR-0046 D6).
# ---------------------------------------------------------------------------


class TestNearDuplicateAdvisoryNeverBlocks:
    def test_near_dup_cluster_is_surfaced_but_verdict_stays_pass(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        from automation_engineering.catalog.scanner import reconcile
        from automation_engineering.reuse.live_matcher import step_definition_embedding_text

        _write_feature(
            baseline_root,
            "auth.feature",
            "Feature: Auth\n\n  Scenario: A\n    Given user logs in\n"
            "  Scenario: B\n    Given user signs in\n",
        )
        promoted = _write_step_def(baseline_root, "LoginSteps", "userLogsIn", "user logs in")
        _write_step_def(baseline_root, "AuthSteps", "userSignsIn", "user signs in")
        stage_promoted_assets([promoted], baseline_root)

        _write_placeholder_automation_package(run_dir)
        _write_promotion_report(run_dir, ["src/test/java/com/automation/steps/LoginSteps.java"])

        real_assets = reconcile(baseline_root).step_definitions
        real_texts = [step_definition_embedding_text(a) for a in real_assets]
        # Both real texts pinned to the same vector -- cosine similarity 1.0,
        # comfortably above the 0.90 default threshold.
        provider = _StubEmbeddingProvider({text: (1.0, 0.0) for text in real_texts})

        run_state_mgr = _new_run_state_manager(run_dir)
        result = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=provider,
            baseline_root=baseline_root,
        )

        assert result is not None
        cp5 = result.result
        assert cp5.orphaned_glue.overall_verdict == ValidationVerdict.PASS
        assert cp5.cohesion.overall_verdict == ValidationVerdict.PASS
        assert len(cp5.near_duplicates.clusters) == 1
        assert cp5.overall_verdict == ValidationVerdict.PASS  # never gated by near-dup
        assert cp5.has_review_worthy_findings is True  # but still surfaced

        report_text = result.report_path.read_text(encoding="utf-8")
        assert "Near-duplicate clusters" in report_text


# ---------------------------------------------------------------------------
# Run-state integration: SUCCEEDED / FAILED / SKIPPED, mirroring stage 15's
# own three-test proof exactly.
# ---------------------------------------------------------------------------


class TestRunStateIntegration:
    def test_succeeds_and_records_correct_artifacts(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _write_placeholder_automation_package(run_dir)
        _write_promotion_report(run_dir, [])
        run_state_mgr = _new_run_state_manager(run_dir)

        result = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
        )

        assert result is not None
        stage = _find_stage(run_state_mgr, STAGE_ID)
        assert stage.status.value == "succeeded"
        for path in result.all_output_paths:
            assert str(path) in stage.output_artifacts
        assert result.cp5_report_path.exists()
        assert result.report_path.exists()

    def test_a_genuine_transport_failure_fails_the_stage_not_the_process(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        """Two step-definition assets are required so the near-dup sweep's
        own `embed()` call is genuinely reached (`sweep_near_duplicates`
        short-circuits below two assets, `near_duplicate_sweep.py`'s own
        `len(assets) < 2` guard) -- proving a REAL, uncaught exception (never
        a scripted compile failure, which CP5's own cohesion gate already
        catches and turns into a deterministic FAIL, not a crash) reaches
        `fail_stage`, exactly mirroring stage 15's own
        `test_missing_upstream_package_fails_the_stage_not_the_process`.
        """
        _write_step_def(baseline_root, "A", "aMethod", "pattern a")
        _write_step_def(baseline_root, "B", "bMethod", "pattern b")
        _write_placeholder_automation_package(run_dir)
        _write_promotion_report(run_dir, [])
        run_state_mgr = _new_run_state_manager(run_dir)

        result = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_RaisingEmbeddingProvider(),
            baseline_root=baseline_root,
        )

        assert result is None
        stage = _find_stage(run_state_mgr, STAGE_ID)
        assert stage.status.value == "failed"
        assert stage.error is not None

    def test_unchanged_rerun_is_skipped(self, baseline_root: Path, run_dir: Path) -> None:
        _write_placeholder_automation_package(run_dir)
        _write_promotion_report(run_dir, [])
        run_state_mgr = _new_run_state_manager(run_dir)

        first = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
        )
        assert first is not None

        # A second attempt, no upstream artifact changed -- a provider that
        # would raise if actually called proves SKIP genuinely
        # short-circuits before CP5 runs again.
        second = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(),  # no scripted outcome -- would raise if called
            embedding_provider=_RaisingEmbeddingProvider(),
            baseline_root=baseline_root,
        )

        assert second is None
        stage = _find_stage(run_state_mgr, STAGE_ID)
        assert stage.status.value == "skipped"


# ---------------------------------------------------------------------------
# The pure business-logic function, called directly (not through run-state) --
# mirrors stage 15's own split between `run_automation_engineering_stage` and
# `execute_automation_engineering_stage`.
# ---------------------------------------------------------------------------


class TestRunSuiteQualityGovernanceStageDirectly:
    def test_persists_cp5_report_and_markdown_report(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
        )

        assert result.cp5_report_path == run_dir / CP5_REPORT_FILENAME
        assert result.cp5_report_path.exists()
        assert result.report_path.exists()
        assert result.result.overall_verdict == ValidationVerdict.PASS
