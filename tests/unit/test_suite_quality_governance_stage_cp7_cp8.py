"""Stage 16 -- Suite Quality Governance (ADR-0036, ADR-0046, ADR-0047): CP7
and CP8 joining CP5 in the SAME stage (`suite_quality_governance.stage
.runner`), proving the wiring this build adds -- CP5's own wiring proof
stays in `test_suite_quality_governance_stage.py`, untouched.

Covers: all three control points run in one stage invocation; CP8's own
static-readiness gate composes into the stage's own verdict alongside CP5
(ADR-0047 D9) -- a suite that fails CP8 fails the stage even when CP5
alone would have passed; CP7's own RATING metrics (`reliability_rating`/
`sqale_rating`) now gate the stage too (ADR-0047 D3's own amendment note,
2026-08-10) at an A-or-B floor, while CP7's OTHER measures (raw counts,
security, coverage/duplication) stay report-only, surfaced regardless of
content; CP7's own live Sonar dependence degrades to an honest
"unavailable" outcome (no adapter configured, or a genuine fetch failure)
without failing the stage -- the rating-gate itself degrades to `WARN`,
never `FAIL`, on the same unavailable report; the stage's own composition
matrix (CP5 x CP8 x CP7-rating-gate -> overall_verdict); and every test
here uses ONLY stub Sonar adapters / stub compiler / stub embeddings -- no
live dependency.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from automation_engineering.cp3.sonar.models import SonarMeasure, SonarMeasuresResult
from automation_engineering.cp3.sonar.stub_adapter import StubSonarQualityGateAdapter
from automation_engineering.stage.models import (
    AUTOMATION_ENGINEERING_PACKAGE_FILENAME,
    PROMOTION_REPORT_FILENAME,
)
from automation_engineering.stage.runner import DEFAULT_SONAR_PROJECT_KEY
from feature_engineering.stage.workspace import FEATURES_SUBPATH
from requirement_intelligence.run_state.models import StageRecord
from requirement_intelligence.run_state.run_state_manager import RunStateManager
from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.compile_check import StubCompileChecker
from suite_quality_governance.cp5.models import CompileResult
from suite_quality_governance.cp7.models import (
    ALL_CP7_METRICS,
    CRITERION_RELIABILITY_RATING_GATE,
    CRITERION_SQALE_RATING_GATE,
)
from suite_quality_governance.cp8.models import CRITERION_GLUE_PACKAGE_RESOLVES
from suite_quality_governance.stage.runner import (
    STAGE_ID,
    execute_suite_quality_governance_stage,
    run_suite_quality_governance_stage,
)

pytestmark = pytest.mark.unit

_RUN_STATE_CONTRACT_VERSION = "1.0.0"

_VALID_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.automation</groupId>
    <artifactId>test-suite-baseline</artifactId>
    <version>1.0-SNAPSHOT</version>
    <dependencies>
        <dependency>
            <groupId>io.cucumber</groupId>
            <artifactId>cucumber-java</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
"""

_RUNNER_JAVA = """package com.automation.runners;

import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
public class RunCucumberTest {
}
"""


class _StubEmbeddingProvider:
    """Deterministic, fixture-driven stand-in -- mirrors CP5's own
    `_StubEmbeddingProvider` discipline exactly (`tests/unit/
    test_suite_quality_governance_stage.py`)."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]]) -> None:
        self._vectors = vectors_by_text

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._vectors[text] for text in texts)


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
    file_path = (
        baseline_root
        / "src/test/java/com/automation/steps"
        / f"{class_name}.java"
    )
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


def _write_cp8_ready_config(baseline_root: Path, *, glue: str = "com.automation.steps") -> None:
    """Writes the three config/asset files CP8 needs beyond features/step-
    defs (which callers write separately via `_write_step_def`/
    `_write_feature`, so CP5 and CP8 fixtures can be varied independently)
    -- `pom.xml`, `junit-platform.properties`, and the runner class."""
    (baseline_root / "pom.xml").write_text(_VALID_POM, encoding="utf-8")

    properties_path = baseline_root / "src/test/resources/junit-platform.properties"
    properties_path.parent.mkdir(parents=True, exist_ok=True)
    properties_path.write_text(f"cucumber.glue={glue}\n", encoding="utf-8")

    runner_path = baseline_root / "src/test/java/com/automation/runners/RunCucumberTest.java"
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    runner_path.write_text(_RUNNER_JAVA, encoding="utf-8")


def _write_promotion_report(run_dir: Path, promoted_baseline_relative_paths: list[str]) -> None:
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


_RATING_METRIC_KEYS = frozenset({"reliability_rating", "sqale_rating"})


def _clean_measures(project_key: str = DEFAULT_SONAR_PROJECT_KEY) -> SonarMeasuresResult:
    """Every CP7 metric at its own "clean" value -- `"1.0"` (Sonar's own A
    rating) for the two metrics the rating-gate reads, `"0"` for every
    other (report-only) count, so this fixture's own name stays true now
    that a real gate exists over the two rating metrics specifically."""
    return SonarMeasuresResult(
        project_key=project_key,
        measures=tuple(
            SonarMeasure(metric_key=k, value="1.0" if k in _RATING_METRIC_KEYS else "0")
            for k in ALL_CP7_METRICS
        ),
    )


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


def _clean_cp5_and_cp8_fixture(baseline_root: Path) -> None:
    """A feature matched by exactly one step -- CP5's orphan/cohesion gates
    both PASS -- plus a fully valid CP8 config (pom/properties/runner)."""
    _write_feature(
        baseline_root,
        "login.feature",
        "Feature: Login\n\n  Scenario: Log in\n    Given user logs in\n",
    )
    _write_step_def(baseline_root, "LoginSteps", "userLogsIn", "user logs in")
    _write_cp8_ready_config(baseline_root)


class TestAllThreeControlPointsRunInTheStage:
    def test_cp5_cp7_cp8_all_produce_results_in_one_stage_call(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _clean_cp5_and_cp8_fixture(baseline_root)

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
            sonar_adapter=StubSonarQualityGateAdapter(measures=_clean_measures()),
        )

        # CP5.
        assert result.result.overall_verdict == ValidationVerdict.PASS
        # CP8: all six criteria evaluated.
        assert len(result.cp8_result.criteria) == 6
        assert result.cp8_result.overall_verdict == ValidationVerdict.PASS
        # CP7: measures obtained, full metric set present.
        assert result.cp7_outcome.available is True
        assert result.cp7_outcome.report is not None
        assert {f.metric_key for f in result.cp7_outcome.report.all_findings} == set(
            ALL_CP7_METRICS
        )
        # CP7's own rating-gate: clean (A/A) measures pass it.
        assert result.cp7_rating_result.overall_verdict == ValidationVerdict.PASS
        assert result.overall_verdict == ValidationVerdict.PASS
        # The stage report/JSON artifacts for all three exist.
        assert result.cp5_report_path.exists()
        assert result.cp8_report_path.exists()
        assert result.cp7_report_path.exists()
        report_text = result.report_path.read_text(encoding="utf-8")
        assert "CP8 static-readiness verdict" in report_text
        assert "CP7 rating gate" in report_text
        assert "CP7 whole-suite Sonar measures" in report_text
        cp7_report_json = json.loads(result.cp7_report_path.read_text(encoding="utf-8"))
        assert cp7_report_json["ratingGate"]["overallVerdict"] == "pass"


class TestCp8GatesTheStage:
    def test_cp8_fail_fails_the_stage_even_though_cp5_alone_would_pass(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _write_feature(
            baseline_root,
            "login.feature",
            "Feature: Login\n\n  Scenario: Log in\n    Given user logs in\n",
        )
        _write_step_def(baseline_root, "LoginSteps", "userLogsIn", "user logs in")
        # CP8's own distinctive catch (ADR-0047 D8): glue points at a
        # package with no real classes -- CP5-cohesion has no concept of
        # this at all, so CP5 alone stays clean.
        _write_cp8_ready_config(baseline_root, glue="com.totally.made.up.package")

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
        )

        assert result.result.overall_verdict == ValidationVerdict.PASS  # CP5 alone: clean
        assert result.cp8_result.overall_verdict == ValidationVerdict.FAIL
        assert (
            result.cp8_result.criterion(CRITERION_GLUE_PACKAGE_RESOLVES).verdict
            == ValidationVerdict.FAIL
        )
        assert result.overall_verdict == ValidationVerdict.FAIL  # the STAGE fails
        assert result.passed is False

        report_text = result.report_path.read_text(encoding="utf-8")
        assert "Suite-level reject" in report_text
        assert CRITERION_GLUE_PACKAGE_RESOLVES in report_text


class TestCp7ReportOnlyMetricsNeverGateTheStage:
    """`violations`/`bugs`/`code_smells`' own raw counts, security, and
    coverage/duplication stay report-only (D3/D4/D5, unchanged by the
    amendment note) -- only `reliability_rating`/`sqale_rating` gate
    (`TestCp7RatingGateComposesIntoTheStage`, below)."""

    def test_bad_report_only_measures_with_clean_ratings_stage_still_passes(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _clean_cp5_and_cp8_fixture(baseline_root)
        # Deliberately "bad-looking" report-only measures (bugs,
        # vulnerabilities, violations, code_smells, security_hotspots) --
        # never gates, regardless of content -- paired with CLEAN ratings
        # (A) so this test isolates the report-only half from the new
        # rating-gate half (covered separately, below).
        concerning_measures = SonarMeasuresResult(
            project_key=DEFAULT_SONAR_PROJECT_KEY,
            measures=tuple(
                SonarMeasure(
                    metric_key=k,
                    value=(
                        "1.0"
                        if k in ("reliability_rating", "sqale_rating")
                        else "10"
                        if k in ("bugs", "vulnerabilities")
                        else "3.0"
                    ),
                )
                for k in ALL_CP7_METRICS
            ),
        )

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
            sonar_adapter=StubSonarQualityGateAdapter(measures=concerning_measures),
        )

        assert result.cp7_outcome.available is True
        report = result.cp7_outcome.report
        assert report is not None
        bugs = next(f for f in report.all_findings if f.metric_key == "bugs")
        assert bugs.value == "10"
        assert result.cp7_rating_result.overall_verdict == ValidationVerdict.PASS
        assert result.overall_verdict == ValidationVerdict.PASS  # report-only content never gates


class TestCp7RatingGateComposesIntoTheStage:
    """`reliability_rating`/`sqale_rating` GATE the stage now (ADR-0047
    D3's own amendment note, 2026-08-10) -- PASS at A-or-B, FAIL worse
    than B, and an unmeasured/unavailable rating is `WARN`, never `FAIL`
    (never blocks)."""

    def test_a_or_b_ratings_pass_the_gate(self, baseline_root: Path, run_dir: Path) -> None:
        _clean_cp5_and_cp8_fixture(baseline_root)
        b_rating_measures = SonarMeasuresResult(
            project_key=DEFAULT_SONAR_PROJECT_KEY,
            measures=tuple(
                SonarMeasure(
                    metric_key=k,
                    value="2.0" if k in ("reliability_rating", "sqale_rating") else "0",
                )
                for k in ALL_CP7_METRICS
            ),
        )

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
            sonar_adapter=StubSonarQualityGateAdapter(measures=b_rating_measures),
        )

        assert result.cp7_rating_result.overall_verdict == ValidationVerdict.PASS
        assert (
            result.cp7_rating_result.criterion(CRITERION_RELIABILITY_RATING_GATE).verdict
            == ValidationVerdict.PASS
        )
        assert (
            result.cp7_rating_result.criterion(CRITERION_SQALE_RATING_GATE).verdict
            == ValidationVerdict.PASS
        )
        assert result.overall_verdict == ValidationVerdict.PASS

    def test_a_c_rating_fails_the_gate_and_the_stage_even_though_cp5_and_cp8_pass(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _clean_cp5_and_cp8_fixture(baseline_root)
        c_reliability_measures = SonarMeasuresResult(
            project_key=DEFAULT_SONAR_PROJECT_KEY,
            measures=tuple(
                SonarMeasure(
                    metric_key=k,
                    value=(
                        "3.0"
                        if k == "reliability_rating"
                        else "1.0"
                        if k == "sqale_rating"
                        else "0"
                    ),
                )
                for k in ALL_CP7_METRICS
            ),
        )

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
            sonar_adapter=StubSonarQualityGateAdapter(measures=c_reliability_measures),
        )

        assert result.result.overall_verdict == ValidationVerdict.PASS  # CP5 alone: clean
        assert result.cp8_result.overall_verdict == ValidationVerdict.PASS  # CP8 alone: clean
        assert (
            result.cp7_rating_result.criterion(CRITERION_RELIABILITY_RATING_GATE).verdict
            == ValidationVerdict.FAIL
        )
        assert (
            result.cp7_rating_result.criterion(CRITERION_SQALE_RATING_GATE).verdict
            == ValidationVerdict.PASS
        )
        assert result.cp7_rating_result.overall_verdict == ValidationVerdict.FAIL
        assert result.overall_verdict == ValidationVerdict.FAIL  # the STAGE fails
        assert result.passed is False

        report_text = result.report_path.read_text(encoding="utf-8")
        assert "Suite-level reject" in report_text
        assert CRITERION_RELIABILITY_RATING_GATE in report_text

    def test_an_unmeasured_rating_warns_but_does_not_fail_the_gate_or_the_stage(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _clean_cp5_and_cp8_fixture(baseline_root)
        # reliability_rating is absent from the scripted response entirely
        # -- the same "server has no value" shape ADR-0047 D5 already
        # establishes for coverage/duplication, reused here.
        missing_rating_measures = SonarMeasuresResult(
            project_key=DEFAULT_SONAR_PROJECT_KEY,
            measures=tuple(
                SonarMeasure(metric_key=k, value="1.0" if k == "sqale_rating" else "0")
                for k in ALL_CP7_METRICS
                if k != "reliability_rating"
            ),
        )

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
            sonar_adapter=StubSonarQualityGateAdapter(measures=missing_rating_measures),
        )

        reliability_criterion = result.cp7_rating_result.criterion(
            CRITERION_RELIABILITY_RATING_GATE
        )
        assert reliability_criterion.verdict == ValidationVerdict.WARN
        assert reliability_criterion.value is None
        assert result.cp7_rating_result.overall_verdict == ValidationVerdict.WARN
        assert result.cp7_rating_result.passed is True  # WARN never blocks
        assert result.overall_verdict == ValidationVerdict.PASS  # unmeasured != FAIL


class TestCp7SonarUnavailableDegradesHonestly:
    def test_no_adapter_configured_is_unavailable_but_does_not_fail_the_stage(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _clean_cp5_and_cp8_fixture(baseline_root)

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
            # sonar_adapter omitted entirely -- the default.
        )

        assert result.cp7_outcome.available is False
        assert result.cp7_outcome.report is None
        assert "no Sonar adapter" in (result.cp7_outcome.unavailable_reason or "")
        # The rating-gate itself degrades to WARN (unmeasured), never FAIL.
        assert result.cp7_rating_result.overall_verdict == ValidationVerdict.WARN
        assert result.overall_verdict == ValidationVerdict.PASS  # gating parts unaffected

    def test_a_genuine_sonar_fetch_failure_is_unavailable_but_does_not_fail_the_stage(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _clean_cp5_and_cp8_fixture(baseline_root)
        # No scripted measures -- StubSonarQualityGateAdapter.fetch_measures
        # raises SonarScanError, the same domain exception CP3's own gate
        # catches for submit/poll failures (`automation_engineering.cp3
        # .gate._evaluate_sonar_gate`).
        failing_adapter = StubSonarQualityGateAdapter()

        run_state_mgr = _new_run_state_manager(run_dir)
        _write_placeholder_automation_package(run_dir)
        _write_promotion_report(run_dir, [])

        result = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
            sonar_adapter=failing_adapter,
        )

        assert result is not None
        assert result.cp7_outcome.available is False
        assert result.cp7_outcome.unavailable_reason is not None
        # The rating-gate itself degrades to WARN (unmeasured), never FAIL.
        assert result.cp7_rating_result.overall_verdict == ValidationVerdict.WARN
        # The gating parts still produced a real verdict -- CP7's absence
        # is surfaced, never fatal to the stage's own run-state outcome.
        assert result.overall_verdict == ValidationVerdict.PASS
        stage = _find_stage(run_state_mgr, STAGE_ID)
        assert stage.status.value == "succeeded"


class TestCompositionMatrix:
    """The stage's own verdict = CP5.overall_verdict AND CP8.overall_verdict
    -- proven across all four PASS/FAIL combinations (ADR-0047 D8/D9). No
    `sonar_adapter` is configured in any scenario here, so CP7's own
    rating-gate is `WARN` throughout (unmeasured, never blocking) --
    exercising the CP5 x CP8 matrix in isolation from CP7's own gating
    half, which gets its own dedicated composition proof
    (`TestCp7RatingGateComposesIntoTheStage`, above)."""

    def test_cp5_pass_and_cp8_pass_yields_stage_pass(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _clean_cp5_and_cp8_fixture(baseline_root)

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
        )

        assert result.result.overall_verdict == ValidationVerdict.PASS
        assert result.cp8_result.overall_verdict == ValidationVerdict.PASS
        assert result.overall_verdict == ValidationVerdict.PASS

    def test_cp5_fail_and_cp8_pass_yields_stage_fail(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        # A feature matched by ITS OWN step, plus a SECOND, orphaned step
        # that matches nothing -- fails CP5's own orphaned-glue gate, while
        # CP8's own config stays fully valid (a real feature file exists,
        # and the orphan step itself still makes `com.automation.steps`
        # real for CP8's own glue-resolution check).
        from automation_engineering.catalog.scanner import reconcile
        from automation_engineering.reuse.live_matcher import step_definition_embedding_text

        _write_feature(
            baseline_root,
            "login.feature",
            "Feature: Login\n\n  Scenario: Log in\n    Given user logs in\n",
        )
        _write_step_def(baseline_root, "LoginSteps", "userLogsIn", "user logs in")
        _write_step_def(baseline_root, "OrphanSteps", "doOrphan", "do an orphan thing")
        _write_cp8_ready_config(baseline_root)

        # The orphan's own semantic-hint embedding needs a scripted vector
        # for its own text plus every current need's text (`orphaned_glue
        # ._semantic_hints`'s own one-batched-call shape) -- built from the
        # real catalog/needs, mirroring `test_suite_quality_governance_stage
        # .py`'s own fixture discipline, rather than guessing the exact
        # `step_definition_embedding_text` output.
        real_assets = reconcile(baseline_root).step_definitions
        vectors: dict[str, tuple[float, ...]] = {
            step_definition_embedding_text(asset): (1.0, float(i))
            for i, asset in enumerate(real_assets)
        }
        vectors["user logs in"] = (1.0, 0.0)

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider(vectors),
            baseline_root=baseline_root,
        )

        assert result.result.overall_verdict == ValidationVerdict.FAIL
        assert result.cp8_result.overall_verdict == ValidationVerdict.PASS
        assert result.overall_verdict == ValidationVerdict.FAIL

    def test_cp5_pass_and_cp8_fail_yields_stage_fail(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _write_feature(
            baseline_root,
            "login.feature",
            "Feature: Login\n\n  Scenario: Log in\n    Given user logs in\n",
        )
        _write_step_def(baseline_root, "LoginSteps", "userLogsIn", "user logs in")
        _write_cp8_ready_config(baseline_root)
        # Break CP8 only: delete the runner CP8 requires.
        (baseline_root / "src/test/java/com/automation/runners/RunCucumberTest.java").unlink()

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
        )

        assert result.result.overall_verdict == ValidationVerdict.PASS
        assert result.cp8_result.overall_verdict == ValidationVerdict.FAIL
        assert result.overall_verdict == ValidationVerdict.FAIL

    def test_cp5_fail_and_cp8_fail_yields_stage_fail(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _write_step_def(baseline_root, "OrphanSteps", "doOrphan", "do an orphan thing")
        # No CP8 config written at all -- everything CP8 needs is missing.

        result = run_suite_quality_governance_stage(
            run_dir,
            (),
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
        )

        assert result.result.overall_verdict == ValidationVerdict.FAIL
        assert result.cp8_result.overall_verdict == ValidationVerdict.FAIL
        assert result.overall_verdict == ValidationVerdict.FAIL


class TestRunStateIntegrationWithCp7Cp8:
    def test_output_artifacts_include_cp7_and_cp8_reports(
        self, baseline_root: Path, run_dir: Path
    ) -> None:
        _clean_cp5_and_cp8_fixture(baseline_root)
        _write_placeholder_automation_package(run_dir)
        _write_promotion_report(run_dir, [])
        run_state_mgr = _new_run_state_manager(run_dir)

        result = execute_suite_quality_governance_stage(
            run_state_mgr,
            run_dir,
            compile_checker=StubCompileChecker(result=CompileResult(passed=True)),
            embedding_provider=_StubEmbeddingProvider({}),
            baseline_root=baseline_root,
            sonar_adapter=StubSonarQualityGateAdapter(measures=_clean_measures()),
        )

        assert result is not None
        stage = _find_stage(run_state_mgr, STAGE_ID)
        assert stage.status.value == "succeeded"
        for path in result.all_output_paths:
            assert str(path) in stage.output_artifacts
        assert result.cp7_report_path.name == "cp7_report.json"
        assert result.cp8_report_path.name == "cp8_report.json"
