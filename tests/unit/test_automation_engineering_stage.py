"""Stage 15 -- Automation Engineering as a resumable, persisted run/stage-
state stage (ADR-0036, ADR-0044) -- the orchestration that chains Layer 3's
six already-built subsystems (catalog, reuse, generation, CP3, CP4,
promotion) into one runnable stage, mirroring stage 14's own integration
proof (`tests/unit/test_feature_engineering_stage.py`).

Every test here uses a FAKE, per-test tracked baseline (a copy of the real
`test-suite-baseline/` under `tmp_path`) as `baseline_root` -- promotion
writes real files into `baseline_root` and stages them via `git add`
(`automation_engineering.promotion.mechanism`), so the real, tracked
`test-suite-baseline/` must never be passed as `baseline_root` in a test.

Proves: Gherkin -> step-need derivation (dedup across features, escalated
features excluded); the full deterministic chain on a fixture feature set
(catalog -> reuse -> generate -> write-to-workspace -> CP3 -> CP4 ->
promote), entirely against stubs (`StubSemanticMatcher`/
`StubStepDefinitionGenerator`/`StubTestDataGenerator`/
`StubSonarQualityGateAdapter`) -- no live call anywhere; workspace
materialization (assets land in the per-run workspace, the tracked baseline
is untouched except by promotion's own stage-for-review write); the
CP3/CP4-verdict-to-promotion batch association (a CP3 failure blocks
promotion even for an asset that itself generated cleanly); escalation
surfacing; the reuse-first loop closing THROUGH this real orchestration (a
promoted asset from run 1 is bound, not regenerated, in run 2); run-state
SUCCEEDED/SKIPPED/FAILED wiring; and determinism.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from automation_engineering.catalog.scanner import reconcile
from automation_engineering.cp3.sonar.models import SonarQualityGateResult
from automation_engineering.cp3.sonar.stub_adapter import StubSonarQualityGateAdapter
from automation_engineering.generation.step_definition_generator import (
    StubStepDefinitionGenerator,
)
from automation_engineering.generation.test_data_generator import StubTestDataGenerator
from automation_engineering.reuse.matcher import StubSemanticMatcher
from automation_engineering.reuse.models import MatchCandidate
from automation_engineering.stage.gherkin_needs import (
    derive_feature_step_needs,
    derive_unique_step_needs,
)
from automation_engineering.stage.models import AutomationEngineeringStageResult
from automation_engineering.stage.runner import (
    STAGE_ID,
    execute_automation_engineering_stage,
    run_automation_engineering_stage,
)
from feature_engineering.stage.models import FeatureEngineeringPackage, FeatureRecord
from feature_engineering.stage.test_data_spec import (
    TEST_DATA_SPECIFICATIONS_FILENAME,
    test_data_specifications_to_json,
)
from feature_engineering.stage.workspace import materialize_workspace
from requirement_intelligence.run_state.atomic_write import atomic_write_json
from requirement_intelligence.run_state.models import StageRecord
from requirement_intelligence.run_state.run_state_manager import RunStateManager

_RUN_STATE_CONTRACT_VERSION = "1.0.0"

_LOGIN_FEATURE = """Feature: Login

  @SCN-001
  Scenario: Successful login
    Given I am on the login page
    When I log in as "bob"
    Then I see the dashboard
"""

_CHECKOUT_FEATURE = """Feature: Checkout

  @SCN-002
  Scenario: Successful checkout
    Given I am on the login page
    When I check out
"""

_PARAMETERLESS_STEP_JAVA = """package com.automation.steps;

import io.cucumber.java.en.Given;

public class LoginPageSteps {

    @Given("I am on the login page")
    public void iAmOnTheLoginPage() {
        System.out.println("noop");
    }
}
"""


def _clean_java(class_name: str, method_name: str) -> str:
    return (
        "package com.automation.steps;\n\n"
        f"public class {class_name} {{\n\n"
        f"    public void {method_name}() {{\n"
        '        System.out.println("noop");\n'
        "    }\n"
        "}\n"
    )


def _passing_sonar_adapter() -> StubSonarQualityGateAdapter:
    return StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=True))


def _feature_record(
    requirement_id: str, feature_path: str, *, escalated: bool = False
) -> FeatureRecord:
    return FeatureRecord(
        requirement_id=requirement_id,
        content_hash=f"hash-{requirement_id}",
        req_tag=f"@{requirement_id}",
        feature_path=None if escalated else feature_path,
        scn_ids=(),
        ac_ids_covered=(),
        cp2_verdict="fail" if escalated else "pass",
        remediated=False,
        escalated=escalated,
        escalation_reason="upstream CP2 escalation" if escalated else None,
    )


def _package(records: tuple[FeatureRecord, ...], *, run_id: str = "run-smoke") -> (
    FeatureEngineeringPackage
):
    return FeatureEngineeringPackage(
        contract_version="1.0.0",
        run_id=run_id,
        requirement_set_run_id=run_id,
        generated_at=datetime.now(UTC).isoformat(),
        records=records,
    )


@pytest.fixture
def fake_baseline(tmp_path: Path) -> Path:
    """A real, git-ignorable COPY of `test-suite-baseline/` under `tmp_path`
    -- every test's own `baseline_root`, so promotion's real file writes and
    `git add` staging never touch the actual tracked baseline."""
    destination = tmp_path / "test-suite-baseline"
    shutil.copytree("test-suite-baseline", destination)
    return destination


@pytest.fixture
def repo_root(tmp_path: Path, fake_baseline: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    return tmp_path


def _write_feature(workspace_dir: Path, relative_path: str, content: str) -> None:
    path = workspace_dir / "src/test/resources/features" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Gherkin -> step-need derivation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGherkinNeedsDerivation:
    def test_one_need_per_step_in_document_order(self) -> None:
        result = derive_feature_step_needs(_LOGIN_FEATURE, file_path=Path("login.feature"))

        assert [n.text for n in result.needs] == [
            "I am on the login page",
            'I log in as "bob"',
            "I see the dashboard",
        ]
        assert [n.step_type for n in result.needs] == ["Given", "When", "Then"]

    def test_and_but_inherit_the_preceding_effective_type(self) -> None:
        content = """Feature: Demo

  Scenario: Multi-step
    Given I am on the login page
    And I accept cookies
    When I log in
    But I do not remember me
"""
        result = derive_feature_step_needs(content, file_path=Path("demo.feature"))

        types = {n.text: n.step_type for n in result.needs}
        assert types["I accept cookies"] == "Given"  # inherits the preceding Given
        assert types["I do not remember me"] == "When"  # inherits the preceding When

    def test_captures_always_empty(self) -> None:
        """Deliberate (ADR-0044 D4 defers capture-shape inference to a
        future generation-time task) -- every derived need's own captures
        stays `()`, never guessed from literal step text."""
        result = derive_feature_step_needs(_LOGIN_FEATURE, file_path=Path("login.feature"))

        assert all(n.captures == () for n in result.needs)

    def test_a_file_with_no_feature_line_yields_no_needs(self) -> None:
        result = derive_feature_step_needs("# not a feature file", file_path=Path("bad.feature"))

        assert result.needs == ()

    def test_dedup_across_features_keeps_first_seen_order(self) -> None:
        login = derive_feature_step_needs(_LOGIN_FEATURE, file_path=Path("login.feature"))
        checkout = derive_feature_step_needs(_CHECKOUT_FEATURE, file_path=Path("checkout.feature"))

        unique = derive_unique_step_needs((login, checkout))

        # "I am on the login page" appears in BOTH features -- exactly one
        # GherkinStepNeed for it, in the order the FIRST feature saw it.
        texts = [n.text for n in unique]
        assert texts.count("I am on the login page") == 1
        assert texts == [
            "I am on the login page",
            'I log in as "bob"',
            "I see the dashboard",
            "I check out",
        ]


# ---------------------------------------------------------------------------
# The full deterministic chain
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEndToEndChain:
    def test_full_chain_on_a_fixture_feature_set(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """catalog -> reuse (NoMatch) -> generate -> write-to-workspace ->
        CP3 -> CP4 -> promote, on two features sharing one step -- no live
        call anywhere (stub matcher/generators/Sonar)."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)
        _write_feature(workspace_dir, "checkout.feature", _CHECKOUT_FEATURE)

        package = _package(
            (
                _feature_record("REQ-1", "login.feature"),
                _feature_record("REQ-2", "checkout.feature"),
            )
        )
        matcher = StubSemanticMatcher(
            {
                "I am on the login page": (),
                'I log in as "bob"': (),
                "I see the dashboard": (),
                "I check out": (),
            }
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "I am on the login page": _clean_java("LoginPageSteps", "iAmOnTheLoginPage"),
                'I log in as "bob"': _clean_java("LoginActionSteps", "iLogInAsBob"),
                "I see the dashboard": _clean_java("DashboardSteps", "iSeeTheDashboard"),
                "I check out": _clean_java("CheckoutSteps", "iCheckOut"),
            }
        )

        result = run_automation_engineering_stage(
            package,
            (),
            workspace_dir=workspace_dir,
            matcher=matcher,
            step_definition_generator=step_gen,
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=_passing_sonar_adapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        # One unique-need record per distinct step text -- 4, not 5 (the
        # shared "I am on the login page" step counted once).
        assert len(result.package.records) == 4
        assert {r.outcome for r in result.package.records} == {"generated"}
        assert result.cp3_passed is True
        assert result.cp4_passed is True
        assert len(result.promoted_baseline_paths) == 4
        for path in result.promoted_baseline_paths:
            assert path.exists()
        # Every promoted path is staged (git add), never committed.
        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "LoginPageSteps.java" in staged
        # Staged, never committed (ADR-0045 D5) -- an empty repo has no HEAD
        # to log at all yet, itself proof nothing was ever committed.
        log = subprocess.run(
            ["git", "log", "--oneline"], cwd=repo_root, capture_output=True, text=True, check=False
        )
        assert log.returncode != 0
        assert "does not have any commits yet" in log.stderr

    def test_deterministic_same_input_same_result(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))

        def _run() -> tuple[str, ...]:
            matcher = StubSemanticMatcher(
                {
                    "I am on the login page": (),
                    'I log in as "bob"': (),
                    "I see the dashboard": (),
                }
            )
            step_gen = StubStepDefinitionGenerator(
                {
                    "I am on the login page": _clean_java("A", "a"),
                    'I log in as "bob"': _clean_java("B", "b"),
                    "I see the dashboard": _clean_java("C", "c"),
                }
            )
            result = run_automation_engineering_stage(
                package,
                (),
                workspace_dir=workspace_dir,
                matcher=matcher,
                step_definition_generator=step_gen,
                test_data_generator=StubTestDataGenerator({}),
                sonar_adapter=_passing_sonar_adapter(),
                baseline_root=fake_baseline,
                repo_root=repo_root,
            )
            return tuple(r.outcome for r in result.package.records)

        first = _run()
        second = _run()
        assert first == second


# ---------------------------------------------------------------------------
# Escalated features are excluded from step-need derivation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEligibility:
    def test_escalated_feature_records_contribute_no_step_needs(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)
        package = _package(
            (
                _feature_record("REQ-1", "login.feature"),
                _feature_record("REQ-2", "checkout.feature", escalated=True),
            )
        )
        matcher = StubSemanticMatcher(
            {
                "I am on the login page": (),
                'I log in as "bob"': (),
                "I see the dashboard": (),
            }
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "I am on the login page": _clean_java("A", "a"),
                'I log in as "bob"': _clean_java("B", "b"),
                "I see the dashboard": _clean_java("C", "c"),
            }
        )

        result = run_automation_engineering_stage(
            package,
            (),
            workspace_dir=workspace_dir,
            matcher=matcher,
            step_definition_generator=step_gen,
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=_passing_sonar_adapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        # Only login.feature's 3 steps -- "I check out" (checkout.feature,
        # escalated) never became a need at all.
        assert {r.need_text for r in result.package.records} == {
            "I am on the login page",
            'I log in as "bob"',
            "I see the dashboard",
        }


# ---------------------------------------------------------------------------
# Workspace materialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWorkspaceMaterialization:
    def test_generated_java_lands_in_the_workspace_not_the_tracked_baseline(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        steps_dir = fake_baseline / "src/test/java/com/automation/steps"
        baseline_files_before = set(steps_dir.glob("*.java")) if steps_dir.exists() else set()

        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))
        matcher = StubSemanticMatcher(
            {
                "I am on the login page": (),
                'I log in as "bob"': (),
                "I see the dashboard": (),
            }
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "I am on the login page": _clean_java("LoginPageSteps", "a"),
                'I log in as "bob"': _clean_java("LoginActionSteps", "b"),
                "I see the dashboard": _clean_java("DashboardSteps", "c"),
            }
        )
        # A CP3-failing Sonar result -- promotion never fires, so the ONLY
        # write this run performs is into the workspace.
        sonar = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=False))

        result = run_automation_engineering_stage(
            package,
            (),
            workspace_dir=workspace_dir,
            matcher=matcher,
            step_definition_generator=step_gen,
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=sonar,
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        assert result.cp3_passed is False
        assert result.promoted_baseline_paths == ()
        for path in result.workspace_java_paths:
            assert path.exists()
            assert workspace_dir in path.parents
        # The tracked baseline itself is untouched by THIS run -- exactly
        # the same files as before, no new ones added.
        baseline_files_after = set(steps_dir.glob("*.java"))
        assert baseline_files_after == baseline_files_before


# ---------------------------------------------------------------------------
# CP3/CP4-verdict-to-promotion association (batch granularity)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchVerdictGatesPromotion:
    def _run_with_sonar(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path, *, sonar_passed: bool
    ) -> AutomationEngineeringStageResult:
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))
        matcher = StubSemanticMatcher(
            {
                "I am on the login page": (),
                'I log in as "bob"': (),
                "I see the dashboard": (),
            }
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "I am on the login page": _clean_java("LoginPageSteps", "a"),
                'I log in as "bob"': _clean_java("LoginActionSteps", "b"),
                "I see the dashboard": _clean_java("DashboardSteps", "c"),
            }
        )
        return run_automation_engineering_stage(
            package,
            (),
            workspace_dir=workspace_dir,
            matcher=matcher,
            step_definition_generator=step_gen,
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=StubSonarQualityGateAdapter(
                result=SonarQualityGateResult(passed=sonar_passed)
            ),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

    def test_a_run_wide_cp3_failure_blocks_promotion_for_every_candidate(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """The whole-run CP3 verdict gates EVERY generated candidate's own
        promotion (`AssetGateOutcomes`'s own documented batch granularity)
        -- even though each class generated cleanly on its own, none
        promotes when the run's shared CP3 verdict is FAIL."""
        result = self._run_with_sonar(tmp_path, fake_baseline, repo_root, sonar_passed=False)

        assert result.cp3_passed is False
        assert result.promoted_baseline_paths == ()
        not_promotable = [r for r in result.package.records if r.promotion_status is not None]
        assert len(not_promotable) == 3
        assert all(r.promotion_status == "not_promotable" for r in not_promotable)
        assert all(r.promotion_detail is not None and "cp3_failed" in r.promotion_detail
                    for r in not_promotable)

    def test_a_run_wide_cp3_pass_promotes_every_clean_candidate(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        result = self._run_with_sonar(tmp_path, fake_baseline, repo_root, sonar_passed=True)

        assert result.cp3_passed is True
        assert len(result.promoted_baseline_paths) == 3
        assert all(r.promotion_status == "promoted" for r in result.package.records)


# ---------------------------------------------------------------------------
# Escalation surfacing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEscalationSurfacing:
    def test_a_low_confidence_match_escalates_and_is_recorded(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))
        matcher = StubSemanticMatcher(
            {
                "I am on the login page": (
                    MatchCandidate(
                        asset_id="some-asset", confidence=0.1, content_hash="whatever"
                    ),
                ),
                'I log in as "bob"': (),
                "I see the dashboard": (),
            }
        )
        step_gen = StubStepDefinitionGenerator(
            {
                'I log in as "bob"': _clean_java("LoginActionSteps", "b"),
                "I see the dashboard": _clean_java("DashboardSteps", "c"),
            }
        )

        result = run_automation_engineering_stage(
            package,
            (),
            workspace_dir=workspace_dir,
            matcher=matcher,
            step_definition_generator=step_gen,
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=_passing_sonar_adapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        assert result.has_escalations
        escalated = result.package.escalated_records
        assert len(escalated) == 1
        assert escalated[0].need_text == "I am on the login page"
        assert escalated[0].escalation_check == "confidence"
        assert escalated[0].outcome == "escalated"
        assert escalated[0].promotion_status is None  # nothing to promote


# ---------------------------------------------------------------------------
# The reuse-first loop closes THROUGH this real orchestration (capstone)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReuseLoopClosesThroughTheRealOrchestration:
    def test_a_promoted_asset_from_run_one_is_bound_not_regenerated_in_run_two(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """A parameterless step, deliberately (captures stays `()` in this
        wiring -- ADR-0044 D4's own deferral, this module's report) so
        signature-fit's own capture-COUNT check (0 == 0) genuinely passes.
        Run 1 generates and promotes a REAL, `@Given`-annotated step
        definition into the tracked baseline; run 2's own catalog
        reconciliation (from that now-updated baseline) finds it and the
        semantic matcher (scripted with the real, resolved asset_id/
        content_hash run 1 produced) resolves a TRUSTED_REUSE bind --
        proving the loop closes through the ACTUAL orchestration, not just
        the promotion package's own unit test.
        """
        # -- Run 1: generate + promote -------------------------------------
        run_dir_1 = tmp_path / "run-1"
        workspace_1 = materialize_workspace(run_dir_1, baseline_root=fake_baseline)
        _write_feature(workspace_1, "login.feature", _LOGIN_FEATURE)
        package_1 = _package((_feature_record("REQ-1", "login.feature"),), run_id="run-1")
        matcher_1 = StubSemanticMatcher(
            {
                "I am on the login page": (),  # NO_MATCH -- nothing catalogued yet
                'I log in as "bob"': (),
                "I see the dashboard": (),
            }
        )
        step_gen_1 = StubStepDefinitionGenerator(
            {
                "I am on the login page": _PARAMETERLESS_STEP_JAVA,
                'I log in as "bob"': _clean_java("LoginActionSteps", "b"),
                "I see the dashboard": _clean_java("DashboardSteps", "c"),
            }
        )

        run_automation_engineering_stage(
            package_1,
            (),
            workspace_dir=workspace_1,
            matcher=matcher_1,
            step_definition_generator=step_gen_1,
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=_passing_sonar_adapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        # Confirm promotion actually landed the real, tracked asset, and
        # read back its REAL, resolved identity -- not fabricated.
        promoted_catalog = reconcile(fake_baseline)
        promoted_asset = next(
            a
            for a in promoted_catalog.step_definitions
            if a.class_name == "com.automation.steps.LoginPageSteps"
        )
        assert promoted_asset.pattern == "I am on the login page"

        # -- Run 2: a DIFFERENT run_id, DIFFERENT run_dir -- only the
        # tracked baseline (now containing run 1's promoted class) carries
        # anything over, exactly as ADR-0044 D3's own reconciliation model
        # requires. --------------------------------------------------------
        run_dir_2 = tmp_path / "run-2"
        workspace_2 = materialize_workspace(run_dir_2, baseline_root=fake_baseline)
        _write_feature(workspace_2, "login.feature", _LOGIN_FEATURE)
        package_2 = _package((_feature_record("REQ-9", "login.feature"),), run_id="run-2")
        matcher_2 = StubSemanticMatcher(
            {
                "I am on the login page": (
                    MatchCandidate(
                        asset_id=promoted_asset.asset_id,
                        confidence=0.99,
                        content_hash=promoted_asset.content_hash,
                    ),
                ),
                'I log in as "bob"': (),
                "I see the dashboard": (),
            }
        )
        step_gen_2 = StubStepDefinitionGenerator(
            {
                # NOT "I am on the login page" -- if the reuse loop failed to
                # close, generation would be attempted for it and this stub
                # would raise KeyError, failing the test loudly.
                'I log in as "bob"': _clean_java("LoginActionSteps", "b"),
                "I see the dashboard": _clean_java("DashboardSteps", "c"),
            }
        )

        result_2 = run_automation_engineering_stage(
            package_2,
            (),
            workspace_dir=workspace_2,
            matcher=matcher_2,
            step_definition_generator=step_gen_2,
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=_passing_sonar_adapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        login_record = next(
            r for r in result_2.package.records if r.need_text == "I am on the login page"
        )
        assert login_record.outcome == "bound"
        assert login_record.class_name == "com.automation.steps.LoginPageSteps"
        assert login_record.promotion_status is None  # nothing new to promote
        # Bound, so no new file was written for it into run 2's own workspace.
        assert not any(
            "LoginPageSteps" in str(p) for p in result_2.workspace_java_paths
        )


# ---------------------------------------------------------------------------
# Run-state integration: SUCCEEDED / SKIPPED / FAILED
# ---------------------------------------------------------------------------


def _new_run_state_manager(run_dir: Path, *, run_id: str = "run-1") -> RunStateManager:
    return RunStateManager.create(
        run_dir, run_id=run_id, execution_name=None, contract_version=_RUN_STATE_CONTRACT_VERSION
    )


def _find_stage(run_state_mgr: RunStateManager, stage_id: str) -> StageRecord:
    return next(s for s in run_state_mgr.state.stages if s.stage_id == stage_id)


def _write_upstream_artifacts(run_dir: Path, package: FeatureEngineeringPackage) -> None:
    from feature_engineering.stage.models import FEATURE_ENGINEERING_PACKAGE_FILENAME

    atomic_write_json(run_dir / FEATURE_ENGINEERING_PACKAGE_FILENAME, package.to_json())
    atomic_write_json(
        run_dir / TEST_DATA_SPECIFICATIONS_FILENAME, test_data_specifications_to_json(())
    )


@pytest.mark.unit
class TestRunStateIntegration:
    def test_succeeds_and_records_correct_artifacts(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        run_dir = repo_root / "run"
        run_dir.mkdir()
        package = _package((_feature_record("REQ-1", "login.feature"),))
        _write_upstream_artifacts(run_dir, package)
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)

        run_state_mgr = _new_run_state_manager(run_dir)
        matcher = StubSemanticMatcher(
            {
                "I am on the login page": (),
                'I log in as "bob"': (),
                "I see the dashboard": (),
            }
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "I am on the login page": _clean_java("A", "a"),
                'I log in as "bob"': _clean_java("B", "b"),
                "I see the dashboard": _clean_java("C", "c"),
            }
        )

        result = execute_automation_engineering_stage(
            run_state_mgr,
            run_dir,
            matcher=matcher,
            step_definition_generator=step_gen,
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=_passing_sonar_adapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        assert result is not None
        stage = _find_stage(run_state_mgr, STAGE_ID)
        assert stage.status.value == "succeeded"
        for path in result.all_output_paths:
            assert str(path) in stage.output_artifacts
        on_disk = json.loads((run_dir / "run_state.json").read_text())
        record = next(s for s in on_disk["stages"] if s["stageId"] == STAGE_ID)
        assert record["status"] == "succeeded"

    def test_missing_upstream_package_fails_the_stage_not_the_process(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        run_dir = repo_root / "run"
        run_dir.mkdir()  # no feature_engineering_package.json written
        run_state_mgr = _new_run_state_manager(run_dir)

        result = execute_automation_engineering_stage(
            run_state_mgr,
            run_dir,
            matcher=StubSemanticMatcher({}),
            step_definition_generator=StubStepDefinitionGenerator({}),
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=_passing_sonar_adapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        assert result is None
        stage = _find_stage(run_state_mgr, STAGE_ID)
        assert stage.status.value == "failed"
        assert stage.error is not None

    def test_unchanged_rerun_is_skipped(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        run_dir = repo_root / "run"
        run_dir.mkdir()
        package = _package((_feature_record("REQ-1", "login.feature"),))
        _write_upstream_artifacts(run_dir, package)
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)

        run_state_mgr = _new_run_state_manager(run_dir)

        def _matcher() -> StubSemanticMatcher:
            return StubSemanticMatcher(
                {
                    "I am on the login page": (),
                    'I log in as "bob"': (),
                    "I see the dashboard": (),
                }
            )

        def _step_gen() -> StubStepDefinitionGenerator:
            return StubStepDefinitionGenerator(
                {
                    "I am on the login page": _clean_java("A", "a"),
                    'I log in as "bob"': _clean_java("B", "b"),
                    "I see the dashboard": _clean_java("C", "c"),
                }
            )

        first = execute_automation_engineering_stage(
            run_state_mgr,
            run_dir,
            matcher=_matcher(),
            step_definition_generator=_step_gen(),
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=_passing_sonar_adapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )
        assert first is not None

        # A second attempt, no upstream artifact changed -- a stub that
        # would raise KeyError if actually called proves SKIP genuinely
        # short-circuits before the chain runs again.
        second = execute_automation_engineering_stage(
            run_state_mgr,
            run_dir,
            matcher=StubSemanticMatcher({}),
            step_definition_generator=StubStepDefinitionGenerator({}),
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=StubSonarQualityGateAdapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        assert second is None
        stage = _find_stage(run_state_mgr, STAGE_ID)
        assert stage.status.value == "skipped"
