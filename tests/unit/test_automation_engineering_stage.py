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
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from automation_engineering.catalog.models import AssetCatalog
from automation_engineering.catalog.scanner import reconcile
from automation_engineering.cp3.sonar.models import SonarQualityGateResult
from automation_engineering.cp3.sonar.stub_adapter import StubSonarQualityGateAdapter
from automation_engineering.errors import TransportFailureError
from automation_engineering.generation.page_object_generator import StubPageObjectGenerator
from automation_engineering.generation.step_definition_generator import (
    StepDefinitionGenerationContext,
    StubStepDefinitionGenerator,
)
from automation_engineering.generation.test_data_generator import (
    StubTestDataGenerator,
    TestDataGenerationContext,
)
from automation_engineering.reuse.live_page_object_matcher import (
    LivePageObjectSemanticMatcher,
    page_object_embedding_text,
)
from automation_engineering.reuse.matcher import StubSemanticMatcher
from automation_engineering.reuse.models import GherkinStepNeed, MatchCandidate
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
from contracts.test_data_specification import TestDataSpecification
from feature_engineering.stage.models import FeatureEngineeringPackage, FeatureRecord
from feature_engineering.stage.test_data_spec import (
    TEST_DATA_SPECIFICATIONS_FILENAME,
    test_data_specifications_to_json,
)
from feature_engineering.stage.workspace import materialize_workspace
from requirement_intelligence.llm.generation_identity import GenerationIdentity
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

_COLLISION_FEATURE = """Feature: Login

  @SCN-101
  Scenario: Login collision
    Given the user attempts to login with valid credentials
    Then the system displays an error message
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


def _package(
    records: tuple[FeatureRecord, ...], *, run_id: str = "run-smoke"
) -> FeatureEngineeringPackage:
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
# The re-run/delta-scoped-regeneration cluster's own pinning foundation
# (2026-08-13) -- generation identity threaded all the way onto AssetRecord
# ---------------------------------------------------------------------------


class _IdentityCapturingStepGenerator:
    """A minimal hand-written double exposing exactly the `.generate`/
    `.last_identity` shape `LiveStepDefinitionGenerator` exposes -- see
    `test_automation_engineering_generation_orchestrator.py`'s own identical
    double."""

    def __init__(self, canned: dict[str, str], identity: GenerationIdentity) -> None:
        self._canned = canned
        self.last_identity = identity

    def generate(self, context: object) -> str:
        return self._canned[context.need.text]  # type: ignore[attr-defined]


@pytest.mark.unit
class TestGenerationIdentityThreadedOntoAssetRecord:
    """Purely additive: `StubStepDefinitionGenerator` (every other test in
    this file) has no `last_identity` attribute, degrading to `None` via
    `getattr` -- proven implicitly by `TestEndToEndChain` above still
    passing unchanged."""

    def test_generated_asset_records_carry_the_generators_own_identity(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
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
        identity = GenerationIdentity(
            prompt_id="generate_step_definitions",
            prompt_version="1.1.0",
            prompt_sha256="0" * 64,
            provider="gemini",
            model="fake-model",
        )
        step_gen = _IdentityCapturingStepGenerator(
            {
                "I am on the login page": _clean_java("LoginPageSteps", "iAmOnTheLoginPage"),
                'I log in as "bob"': _clean_java("LoginActionSteps", "iLogInAsBob"),
                "I see the dashboard": _clean_java("DashboardSteps", "iSeeTheDashboard"),
            },
            identity,
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

        assert result.package.records
        for record in result.package.records:
            assert record.outcome == "generated"
            assert record.generation_identity == identity


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
# CP3/CP4-verdict-to-promotion association
#
# Per-asset since the ADR-0045 D2 additive note (2026-08-06): the whole-
# project Sonar criterion still gates every candidate uniformly (no file/
# class attribution exists to decompose it by -- TestBatchVerdictGatesPromotion,
# below, still proves that case, renamed from its own pre-fix "batch
# granularity" framing only in this comment, not its assertions). Everything
# else -- coverage-family FAILs caused by an UNRELATED escalated need, in
# particular -- no longer blocks a clean candidate. TestPerAssetPromotion
# AcrossEscalations proves the confirming live run's own gap directly: a
# mixed batch (clean generates + an escalation) that used to promote 0
# clean assets because ONE unrelated need escalated now promotes every
# clean one.
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
        """A whole-project Sonar FAIL gates EVERY generated candidate's own
        promotion -- the one CP3 criterion that stays genuinely batch-wide
        under the per-asset design (ADR-0045 D2 additive note: Sonar's own
        `SonarQualityGateResult` carries no file/class attribution to
        decompose it by) -- even though each class generated cleanly on its
        own, none promotes when the run's shared Sonar verdict is FAIL."""
        result = self._run_with_sonar(tmp_path, fake_baseline, repo_root, sonar_passed=False)

        assert result.cp3_passed is False
        assert result.promoted_baseline_paths == ()
        not_promotable = [r for r in result.package.records if r.promotion_status is not None]
        assert len(not_promotable) == 3
        assert all(r.promotion_status == "not_promotable" for r in not_promotable)
        assert all(
            r.promotion_detail is not None and "cp3_failed" in r.promotion_detail
            for r in not_promotable
        )

    def test_a_run_wide_cp3_pass_promotes_every_clean_candidate(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        result = self._run_with_sonar(tmp_path, fake_baseline, repo_root, sonar_passed=True)

        assert result.cp3_passed is True
        assert len(result.promoted_baseline_paths) == 3
        assert all(r.promotion_status == "promoted" for r in result.package.records)


@pytest.mark.unit
class TestPerAssetPromotionAcrossEscalations:
    """THE CONFIRMING-RUN PROOF (Finding A, ADR-0045 D2 additive note,
    2026-08-06): the live run's own gap was 30 clean binds/generates
    promoting 0, because 30 OTHER needs in the SAME batch escalated, which
    failed CP3's whole-run coverage criteria, which -- under the OLD
    whole-run gate -- blocked EVERY candidate, clean ones included. This
    reproduces the mechanism directly: one need escalates (fails coverage
    for the WHOLE run's `Cp3Result`), two other needs generate cleanly in
    the SAME run. Under the per-asset gate, the two clean ones promote; the
    escalated one does not (correctly -- nothing was generated for it), and
    -- critically -- its escalation does NOT block the two clean ones."""

    def test_clean_generates_promote_despite_an_unrelated_escalation_in_the_same_batch(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))
        matcher = StubSemanticMatcher(
            {
                # Below the confidence threshold -- escalates. This is the
                # need that used to poison the WHOLE run's CP3 coverage
                # verdict and, with it, every other candidate's promotion.
                "I am on the login page": (
                    MatchCandidate(asset_id="some-asset", confidence=0.72, content_hash="whatever"),
                ),
                'I log in as "bob"': (),
                "I see the dashboard": (),
            }
        )
        step_gen = StubStepDefinitionGenerator(
            {
                # No entry for "I am on the login page" -- it escalates
                # before generation is ever attempted for it.
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

        # The whole-run CP3 verdict genuinely still FAILs -- coverage is
        # correctly reporting that one step is unmapped. This is the report,
        # not the promotion gate; the two clean generates are unaffected.
        assert result.cp3_passed is False

        by_need = {r.need_text: r for r in result.package.records}
        assert by_need["I am on the login page"].outcome == "escalated"
        assert by_need["I am on the login page"].promotion_status is None

        clean = [by_need['I log in as "bob"'], by_need["I see the dashboard"]]
        assert all(r.outcome == "generated" for r in clean)
        # THE KEY PROOF: both clean generates promoted, even though a THIRD,
        # unrelated need in the same batch escalated and failed the whole
        # run's own CP3 coverage criteria.
        assert all(r.promotion_status == "promoted" for r in clean)
        assert len(result.promoted_baseline_paths) == 2

    def test_a_per_class_static_check_failure_is_isolated_to_that_class(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """A class whose OWN static customqa check fails (a direct
        `WebDriver` reference in a step-definition class) is not promoted;
        a DIFFERENT, clean class generated in the SAME run still is."""
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
        _violating_java = (
            "package com.automation.steps;\n\n"
            "import org.openqa.selenium.WebDriver;\n\n"
            "public class LoginPageSteps {\n\n"
            "    private WebDriver driver;\n\n"
            "    public void iAmOnTheLoginPage() {\n"
            '        driver.get("https://example.com");\n'
            "    }\n"
            "}\n"
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "I am on the login page": _violating_java,
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

        assert result.cp3_passed is False  # direct_webdriver_action genuinely fails, batch-wide

        by_need = {r.need_text: r for r in result.package.records}
        violating = by_need["I am on the login page"]
        assert violating.promotion_status == "not_promotable"
        assert violating.promotion_detail is not None
        assert "cp3_failed" in violating.promotion_detail
        assert "LoginPageSteps" in violating.promotion_detail

        clean = [by_need['I log in as "bob"'], by_need["I see the dashboard"]]
        assert all(r.promotion_status == "promoted" for r in clean)
        assert len(result.promoted_baseline_paths) == 2


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
                # 0.72 -- inside the escalate band (generate_floor <= x <
                # confidence_threshold), not below the floor: this proves
                # confidence-escalation surfacing specifically, not the
                # (separately tested) NO_MATCH/generate floor.
                "I am on the login page": (
                    MatchCandidate(asset_id="some-asset", confidence=0.72, content_hash="whatever"),
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
        assert not any("LoginPageSteps" in str(p) for p in result_2.workspace_java_paths)


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


# ---------------------------------------------------------------------------
# FIX 2 (2026-08-05, the free-tier survivability build): a transport failure
# on one need/specification escalates THAT one and the stage continues --
# mirroring stage 14's own F1 proof (`test_feature_engineering_stage.py::
# TestTransportFailureEscalation`) at stage 15's own two need kinds.
# ---------------------------------------------------------------------------


class _RaisingSemanticMatcher:
    """`StubSemanticMatcher`-shaped, except `match()` raises
    `TransportFailureError` for one scripted need text -- a stand-in for a
    `LiveSemanticMatcher` whose embedding call was rate-limited."""

    def __init__(
        self,
        candidates_by_step_text: dict[str, tuple[MatchCandidate, ...]],
        *,
        fails_for: str,
    ) -> None:
        self._delegate = StubSemanticMatcher(candidates_by_step_text)
        self._fails_for = fails_for

    def prime(self, needs: object, catalog: object) -> None:
        return None

    def match(self, need: GherkinStepNeed, catalog: AssetCatalog) -> tuple[MatchCandidate, ...]:
        if need.text == self._fails_for:
            raise TransportFailureError(f"simulated embedding rate-limit for {need.text!r}")
        return self._delegate.match(need, catalog)


class _RaisingStepDefinitionGenerator:
    """`StubStepDefinitionGenerator`-shaped, except `generate()` raises
    `TransportFailureError` for one scripted need text -- a stand-in for a
    `LiveStepDefinitionGenerator` whose LLM call was rate-limited."""

    def __init__(self, java_by_text: dict[str, str], *, fails_for: str) -> None:
        self._delegate = StubStepDefinitionGenerator(java_by_text)
        self._fails_for = fails_for

    def generate(self, context: StepDefinitionGenerationContext) -> str:
        if context.need.text == self._fails_for:
            raise TransportFailureError(f"simulated LLM rate-limit for {context.need.text!r}")
        return self._delegate.generate(context)


class _RaisingTestDataGenerator:
    """`StubTestDataGenerator`-shaped, except `generate()` raises
    `TransportFailureError` for one scripted `requirement_id`."""

    def __init__(self, java_by_id: dict[str, str], *, fails_for: str) -> None:
        self._delegate = StubTestDataGenerator(java_by_id)
        self._fails_for = fails_for

    def generate(self, context: TestDataGenerationContext) -> str:
        if context.specification.requirement_id == self._fails_for:
            raise TransportFailureError(
                f"simulated LLM rate-limit for {context.specification.requirement_id!r}"
            )
        return self._delegate.generate(context)


@pytest.mark.unit
class TestTransportFailureIsolation:
    def test_generation_transport_failure_escalates_one_need_others_still_generate(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
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
        step_gen = _RaisingStepDefinitionGenerator(
            {
                "I am on the login page": _clean_java("LoginPageSteps", "a"),
                "I see the dashboard": _clean_java("DashboardSteps", "c"),
            },
            fails_for='I log in as "bob"',
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

        by_text = {r.need_text: r for r in result.package.records}
        assert len(result.package.records) == 3
        failed = by_text['I log in as "bob"']
        assert failed.outcome == "escalated"
        assert failed.escalated is True
        assert failed.escalation_check == "transport"
        assert failed.escalation_reason is not None
        assert "transport failure" in failed.escalation_reason
        # The other two needs were NOT aborted by the one transport failure.
        assert by_text["I am on the login page"].outcome == "generated"
        assert by_text["I see the dashboard"].outcome == "generated"

    def test_embedding_transport_failure_escalates_one_need_others_still_process(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))

        matcher = _RaisingSemanticMatcher(
            {
                "I am on the login page": (),
                "I see the dashboard": (),
            },
            fails_for='I log in as "bob"',
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "I am on the login page": _clean_java("LoginPageSteps", "a"),
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

        by_text = {r.need_text: r for r in result.package.records}
        failed = by_text['I log in as "bob"']
        assert failed.outcome == "escalated"
        assert failed.escalation_check == "transport"
        assert by_text["I am on the login page"].outcome == "generated"
        assert by_text["I see the dashboard"].outcome == "generated"

    def test_transport_escalation_is_distinguishable_from_a_deterministic_escalation(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """A genuine reuse-engine escalation (e.g. low confidence, ADR-0044
        D4) and a transport failure produce DIFFERENT `escalation_check`
        values -- a human reviewer can tell "the model call itself failed"
        apart from "a deterministic reuse check failed"."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))

        matcher = _RaisingSemanticMatcher(
            {
                # 0.72 -- inside the escalate band, not below the
                # NO_MATCH/generate floor (see test_automation_engineering_
                # reuse_engine.py for the floor's own dedicated tests).
                "I am on the login page": (
                    MatchCandidate(asset_id="STEP-x", confidence=0.72, content_hash="h"),
                ),
                "I see the dashboard": (),
            },
            fails_for='I log in as "bob"',
        )
        step_gen = StubStepDefinitionGenerator(
            {"I see the dashboard": _clean_java("DashboardSteps", "c")}
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

        by_text = {r.need_text: r for r in result.package.records}
        assert by_text['I log in as "bob"'].escalation_check == "transport"
        assert by_text["I am on the login page"].escalation_check == "confidence"
        assert by_text["I am on the login page"].escalation_check != "transport"

    def test_test_data_transport_failure_escalates_one_spec_others_still_generate(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        package = _package(())
        specs = (
            TestDataSpecification(requirement_id="REQ-1", fields=()),
            TestDataSpecification(requirement_id="REQ-2", fields=()),
        )
        generator = _RaisingTestDataGenerator(
            {"REQ-2": _clean_java("Req2TestData", "get")}, fails_for="REQ-1"
        )

        result = run_automation_engineering_stage(
            package,
            specs,
            workspace_dir=workspace_dir,
            matcher=StubSemanticMatcher({}),
            step_definition_generator=StubStepDefinitionGenerator({}),
            test_data_generator=generator,
            sonar_adapter=_passing_sonar_adapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        by_text = {r.need_text: r for r in result.package.records}
        assert by_text["REQ-1"].outcome == "escalated"
        assert by_text["REQ-1"].escalation_check == "transport"
        assert by_text["REQ-2"].outcome == "generated"

    def test_a_transport_failure_during_priming_is_swallowed_not_stage_fatal(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """The shared `prime()` warm-up call embeds several needs at once
        (FIX 1) -- if THAT call itself fails, it must not take the whole
        stage down (defeating FIX 2's own per-need isolation for every need
        at once). Swallowed; `match()` falls back to on-demand embedding,
        where the per-need loop escalates each individually."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _LOGIN_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))

        class _PrimeFailsThenMatchWorksMatcher:
            def __init__(self) -> None:
                self._delegate = StubSemanticMatcher(
                    {
                        "I am on the login page": (),
                        'I log in as "bob"': (),
                        "I see the dashboard": (),
                    }
                )

            def prime(self, needs: object, catalog: object) -> None:
                raise TransportFailureError("simulated priming-call rate-limit")

            def match(
                self, need: GherkinStepNeed, catalog: AssetCatalog
            ) -> tuple[MatchCandidate, ...]:
                return self._delegate.match(need, catalog)

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
            matcher=_PrimeFailsThenMatchWorksMatcher(),
            step_definition_generator=step_gen,
            test_data_generator=StubTestDataGenerator({}),
            sonar_adapter=_passing_sonar_adapter(),
            baseline_root=fake_baseline,
            repo_root=repo_root,
        )

        # The stage completed -- proof by itself, since a swallowed prime()
        # failure means run_automation_engineering_stage returned normally
        # rather than propagating -- and every need still generated, via
        # match()'s own on-demand fallback.
        assert {r.outcome for r in result.package.records} == {"generated"}

    def test_stage_stays_succeeded_when_only_transport_failures_occurred(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """The run-state proof: a transport failure never fails the whole
        stage (mirrors `test_feature_engineering_stage.py`'s own F1 proof).
        `execute_automation_engineering_stage` records `succeeded`, with the
        transport escalation visible in the package's own records."""
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
        step_gen = _RaisingStepDefinitionGenerator(
            {
                "I am on the login page": _clean_java("A", "a"),
                "I see the dashboard": _clean_java("C", "c"),
            },
            fails_for='I log in as "bob"',
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
        assert result.has_escalations is True
        stage = _find_stage(run_state_mgr, STAGE_ID)
        assert stage.status.value == "succeeded"  # never "failed"
        on_disk = json.loads((run_dir / "run_state.json").read_text())
        record = next(s for s in on_disk["stages"] if s["stageId"] == STAGE_ID)
        assert record["status"] == "succeeded"


# ---------------------------------------------------------------------------
# Class-name collision: the assembly-write gap a live regeneration run hit
# and fixed by hand (two independently generated needs both named
# "LoginSteps", silently overwritten on the first assembly pass, caught only
# by a catalog count mismatch). Proves the fix: DETECTED, merged
# deterministically -- never silently overwritten.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestClassNameCollision:
    def test_two_colliding_needs_merge_into_one_workspace_file(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """Two DIFFERENT step needs whose generated Java independently
        names the same class (`LoginSteps`) -- the generator derives a
        class name from "the step's own subject" with no visibility into
        any other need's own choice, so this is a real, not contrived,
        collision shape. Proves the collision is DETECTED and MERGED: one
        workspace file, both methods present -- never one silently
        clobbering the other (the old, pre-fix behavior)."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "collision.feature", _COLLISION_FEATURE)
        package = _package((_feature_record("REQ-1", "collision.feature"),))

        matcher = StubSemanticMatcher(
            {
                "the user attempts to login with valid credentials": (),
                "the system displays an error message": (),
            }
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "the user attempts to login with valid credentials": _clean_java(
                    "LoginSteps", "theUserAttemptsToLoginWithValidCredentials"
                ),
                "the system displays an error message": _clean_java(
                    "LoginSteps", "theSystemDisplaysAnErrorMessage"
                ),
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

        # Both needs generated -- neither silently dropped nor escalated.
        assert len(result.package.records) == 2
        assert {r.outcome for r in result.package.records} == {"generated"}
        assert {r.class_name for r in result.package.records} == {"com.automation.steps.LoginSteps"}
        # Both point at the exact SAME workspace file -- one class, not two.
        workspace_paths = {r.workspace_path for r in result.package.records}
        assert len(workspace_paths) == 1

        # ONE file on disk, containing BOTH methods -- nothing lost to a
        # silent overwrite (the pre-fix failure mode this proves is gone).
        login_files = list(workspace_dir.glob("src/test/java/**/LoginSteps.java"))
        assert len(login_files) == 1
        content = login_files[0].read_text(encoding="utf-8")
        assert "theUserAttemptsToLoginWithValidCredentials" in content
        assert "theSystemDisplaysAnErrorMessage" in content

        assert result.cp3_passed is True
        assert result.cp4_passed is True

    def test_merge_promotes_once_not_twice(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """A merged class is a single promotion candidate -- the SECOND
        (merged-away) need must not be independently promoted a second
        time through the same path (promotion's own identity mechanism,
        `resolve_candidate_identity`, requires exactly one asset per
        candidate, which a multi-method merged class is not)."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "collision.feature", _COLLISION_FEATURE)
        package = _package((_feature_record("REQ-1", "collision.feature"),))

        matcher = StubSemanticMatcher(
            {
                "the user attempts to login with valid credentials": (),
                "the system displays an error message": (),
            }
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "the user attempts to login with valid credentials": _clean_java(
                    "LoginSteps", "theUserAttemptsToLoginWithValidCredentials"
                ),
                "the system displays an error message": _clean_java(
                    "LoginSteps", "theSystemDisplaysAnErrorMessage"
                ),
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

        # The class promotes exactly once -- not once per contributing need.
        assert len(result.promoted_baseline_paths) == 1
        promotion_statuses = [r.promotion_status for r in result.package.records]
        assert promotion_statuses.count("promoted") == 1
        assert promotion_statuses.count(None) == 1

    def test_unsafe_collision_escalates_instead_of_overwriting(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """Two needs colliding on the SAME class name AND the SAME method
        name, with DIFFERENT bodies, cannot be merged without silently
        picking a winner -- the second need escalates instead, and the
        first need's own file is left untouched."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "collision.feature", _COLLISION_FEATURE)
        package = _package((_feature_record("REQ-1", "collision.feature"),))

        first_java = (
            "package com.automation.steps;\n\n"
            "public class LoginSteps {\n\n"
            "    public void theUserLogsIn() {\n"
            '        System.out.println("first");\n'
            "    }\n"
            "}\n"
        )
        conflicting_java = (
            "package com.automation.steps;\n\n"
            "public class LoginSteps {\n\n"
            "    public void theUserLogsIn() {\n"
            '        System.out.println("second, different body");\n'
            "    }\n"
            "}\n"
        )
        matcher = StubSemanticMatcher(
            {
                "the user attempts to login with valid credentials": (),
                "the system displays an error message": (),
            }
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "the user attempts to login with valid credentials": first_java,
                "the system displays an error message": conflicting_java,
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

        records_by_outcome = {r.need_text: r for r in result.package.records}
        first_record = records_by_outcome["the user attempts to login with valid credentials"]
        second_record = records_by_outcome["the system displays an error message"]

        assert first_record.outcome == "generated"
        assert second_record.outcome == "escalated"
        assert second_record.escalation_check == "class_name_collision"
        assert second_record.escalated is True

        # The first need's own file is intact -- untouched by the failed
        # merge attempt, never partially overwritten.
        login_files = list(workspace_dir.glob("src/test/java/**/LoginSteps.java"))
        assert len(login_files) == 1
        content = login_files[0].read_text(encoding="utf-8")
        assert "first" in content
        assert "second, different body" not in content


# ---------------------------------------------------------------------------
# Page-object co-generation (this build) -- `page_object_matcher`/
# `page_object_generator` supplied, wiring the proven
# `generate_step_definition_with_derived_page_objects` chain
# (:mod:`automation_engineering.generation.page_object_reference_derivation`)
# into this stage for the first time. Every test ABOVE this section never
# supplies either -- proving the pre-existing, step-def-only path is
# completely unchanged is exactly what those 28 tests already do; this
# section proves the NEW, additive path.
# ---------------------------------------------------------------------------

_PAGE_OBJECT_FEATURE = """Feature: Login

  @SCN-201
  Scenario: Login with a page object
    Given I am on the login page
"""

_STEP_JAVA_REFERENCING_A_PAGE_OBJECT = """package com.automation.steps;

import io.cucumber.java.en.Given;

public class LoginSteps {
    private LoginPage loginPage;

    @Given("I am on the login page")
    public void iAmOnTheLoginPage() {
        loginPage.open();
    }
}
"""

_CLEAN_GENERATED_PAGE_OBJECT_JAVA = """package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.WebDriver;

public class LoginPage extends BasePage {

    public LoginPage(WebDriver driver) {
        super(driver);
    }

    public void open() {
        driver.get("/login");
    }
}
"""

_STEP_JAVA_CALLING_AN_EXISTING_TRACKED_METHOD = """package com.automation.steps;

import io.cucumber.java.en.Given;

public class LoginSteps {
    private LoginPage loginPage;

    @Given("I am on the login page")
    public void iAmOnTheLoginPage() {
        loginPage.isErrorMessageDisplayed();
    }
}
"""

_DEFECTIVE_GENERATED_PAGE_OBJECT_JAVA = """package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

public class LoginPage extends BasePage {

    private final By usernameField = By.xpath("/html/body/div[1]/input");

    public LoginPage(WebDriver driver) {
        super(driver);
    }

    public void open() {
        driver.get("/login");
    }
}
"""

_CART_FEATURE = """Feature: Cart

  @SCN-202
  Scenario: Cart summary with a fresh page object
    Given I am on the cart summary page
"""

_STEP_JAVA_REFERENCING_A_FRESH_PAGE_OBJECT = """package com.automation.steps;

import io.cucumber.java.en.Given;

public class CartSummarySteps {
    private CartSummaryPage cartSummaryPage;

    @Given("I am on the cart summary page")
    public void iAmOnTheCartSummaryPage() {
        cartSummaryPage.open();
    }
}
"""

_CLEAN_GENERATED_FRESH_PAGE_OBJECT_JAVA = """package com.automation.pages;

import com.automation.base.BasePage;
import org.openqa.selenium.WebDriver;

public class CartSummaryPage extends BasePage {

    public CartSummaryPage(WebDriver driver) {
        super(driver);
    }

    public void open() {
        driver.get("/cart/summary");
    }
}
"""


class _FakeEmbeddingProvider:
    """Deterministic stand-in for `EmbeddingProvider` -- returns pre-authored
    vectors keyed by input text, no network call. Same discipline
    `test_automation_engineering_reuse_live_page_object_matcher.py`'s own
    fake uses."""

    def __init__(self, vectors_by_text: dict[str, tuple[float, ...]]) -> None:
        self._vectors_by_text = vectors_by_text

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._vectors_by_text[t] for t in texts)


class _IdentityCapturingPageObjectGenerator:
    """A minimal hand-written double exposing exactly the `.generate`/
    `.last_identity` shape `LivePageObjectGenerator` exposes -- the
    page-object-generator counterpart to `_IdentityCapturingStepGenerator`
    above."""

    def __init__(self, canned: dict[str, str], identity: GenerationIdentity) -> None:
        self._canned = canned
        self.last_identity = identity
        self.call_count = 0

    def generate(self, context: object) -> str:
        self.call_count += 1
        return self._canned[context.need.text]  # type: ignore[attr-defined]


@pytest.mark.unit
class TestPageObjectCoGeneration:
    def test_page_object_generated_and_promoted_alongside_its_step_def(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """The core proof: a step whose freshly generated body references a
        page object now ALSO produces a `GeneratedPageObject` -- CP4 is no
        longer vacuous, and the page object promotes through the SAME
        per-candidate gate the step-definition itself already uses."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _PAGE_OBJECT_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))

        matcher = StubSemanticMatcher({"I am on the login page": ()})
        step_gen = StubStepDefinitionGenerator(
            {"I am on the login page": _STEP_JAVA_REFERENCING_A_PAGE_OBJECT}
        )
        page_object_matcher = StubSemanticMatcher({"I am on the login page": ()})
        page_object_gen = StubPageObjectGenerator(
            {"I am on the login page": _CLEAN_GENERATED_PAGE_OBJECT_JAVA}
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
            page_object_matcher=page_object_matcher,
            page_object_generator=page_object_gen,
        )

        records_by_kind = {(r.need_kind, r.class_name): r for r in result.package.records}
        step_def_record = records_by_kind[("step_definition", "com.automation.steps.LoginSteps")]
        page_object_record = records_by_kind[("page_object", "com.automation.pages.LoginPage")]

        assert step_def_record.outcome == "generated"
        assert page_object_record.outcome == "generated"
        assert page_object_record.need_text == "I am on the login page"
        assert result.cp4_passed is True
        assert step_def_record.promotion_status == "promoted"
        assert page_object_record.promotion_status == "promoted"
        promoted_names = {p.name for p in result.promoted_baseline_paths}
        assert promoted_names == {"LoginSteps.java", "LoginPage.java"}
        for path in result.promoted_baseline_paths:
            assert path.exists()

    def test_co_generated_step_def_and_page_object_both_carry_their_own_identity(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """The gap the wiring flagged, closed: a CO-GENERATED step-def's own
        `AssetRecord.generation_identity` used to be `None` even though an
        LLM call happened (`CoGeneratedStepDefinition` dropped it); a
        generated page object had no identity field to carry one at all.
        Both are now populated, with their OWN distinct identity -- the
        step-def generator's and the page-object generator's `last_identity`
        are never confused with each other."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _PAGE_OBJECT_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))

        matcher = StubSemanticMatcher({"I am on the login page": ()})
        step_identity = GenerationIdentity(
            prompt_id="generate_step_definitions",
            prompt_version="1.1.0",
            prompt_sha256="1" * 64,
            provider="gemini",
            model="step-def-model",
        )
        step_gen = _IdentityCapturingStepGenerator(
            {"I am on the login page": _STEP_JAVA_REFERENCING_A_PAGE_OBJECT}, step_identity
        )
        page_object_matcher = StubSemanticMatcher({"I am on the login page": ()})
        page_object_identity = GenerationIdentity(
            prompt_id="generate_page_objects",
            prompt_version="1.3.0",
            prompt_sha256="2" * 64,
            provider="gemini",
            model="page-object-model",
        )
        page_object_gen = _IdentityCapturingPageObjectGenerator(
            {"I am on the login page": _CLEAN_GENERATED_PAGE_OBJECT_JAVA}, page_object_identity
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
            page_object_matcher=page_object_matcher,
            page_object_generator=page_object_gen,
        )

        records_by_kind = {(r.need_kind, r.class_name): r for r in result.package.records}
        step_def_record = records_by_kind[("step_definition", "com.automation.steps.LoginSteps")]
        page_object_record = records_by_kind[("page_object", "com.automation.pages.LoginPage")]

        assert step_def_record.generation_identity == step_identity
        assert page_object_record.generation_identity == page_object_identity
        assert step_def_record.generation_identity != page_object_record.generation_identity

    def test_default_wiring_unchanged_when_page_object_matcher_omitted(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """The live CLI's own current default (this build's own report): a
        step-def body that DOES reference a page object, but
        `page_object_matcher`/`page_object_generator` are both omitted --
        behavior matches this stage exactly as it was before this build, no
        page-object `AssetRecord`, CP4 stays vacuous."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _PAGE_OBJECT_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))

        matcher = StubSemanticMatcher({"I am on the login page": ()})
        step_gen = StubStepDefinitionGenerator(
            {"I am on the login page": _STEP_JAVA_REFERENCING_A_PAGE_OBJECT}
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

        assert {r.need_kind for r in result.package.records} == {"step_definition"}
        assert result.cp4_passed is True  # vacuous PASS, unchanged
        assert len(result.promoted_baseline_paths) == 1

    def test_cp4_non_vacuous_failure_blocks_the_whole_batchs_promotion(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """CP4 non-vacuous also means non-vacuously FAILING: a real
        absolute-XPath locator (ADR-0044 D6's own `dynamic_xpath` criterion)
        in the freshly generated page object now fails CP4, which -- the
        SAME whole-batch design `AssetGateOutcomes`'s own docstring already
        documents, unchanged by this build -- blocks promotion for every
        candidate in the run, including the step-definition, which has
        nothing wrong with it on its own."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _PAGE_OBJECT_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))

        matcher = StubSemanticMatcher({"I am on the login page": ()})
        step_gen = StubStepDefinitionGenerator(
            {"I am on the login page": _STEP_JAVA_REFERENCING_A_PAGE_OBJECT}
        )
        page_object_matcher = StubSemanticMatcher({"I am on the login page": ()})
        page_object_gen = StubPageObjectGenerator(
            {"I am on the login page": _DEFECTIVE_GENERATED_PAGE_OBJECT_JAVA}
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
            page_object_matcher=page_object_matcher,
            page_object_generator=page_object_gen,
        )

        assert result.cp4_passed is False
        records_by_kind = {(r.need_kind, r.class_name): r for r in result.package.records}
        page_object_record = records_by_kind[("page_object", "com.automation.pages.LoginPage")]
        step_def_record = records_by_kind[("step_definition", "com.automation.steps.LoginSteps")]
        assert page_object_record.promotion_status == "not_promotable"
        assert page_object_record.promotion_detail is not None
        assert "cp4_failed" in page_object_record.promotion_detail
        assert step_def_record.promotion_status == "not_promotable"
        assert step_def_record.promotion_detail is not None
        assert "cp4_failed" in step_def_record.promotion_detail
        assert result.promoted_baseline_paths == ()

    def test_bound_page_object_never_calls_the_generator(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """A page-object need the reuse engine trusts (TrustedReuse) binds
        to the catalog's own existing asset instead of generating -- the
        real, already-tracked `LoginPage` in `test-suite-baseline` (a smoke
        page object, ADR-0044 D3/D4) proves this: bind, not regenerate."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _PAGE_OBJECT_FEATURE)
        package = _package((_feature_record("REQ-1", "login.feature"),))

        tracked_catalog = reconcile(fake_baseline)
        existing_login_page = next(
            asset
            for asset in tracked_catalog.page_objects
            if asset.class_name == "com.automation.pages.LoginPage"
        )

        matcher = StubSemanticMatcher({"I am on the login page": ()})
        step_gen = StubStepDefinitionGenerator(
            {"I am on the login page": _STEP_JAVA_CALLING_AN_EXISTING_TRACKED_METHOD}
        )
        page_object_matcher = StubSemanticMatcher(
            {
                "I am on the login page": (
                    MatchCandidate(
                        asset_id=existing_login_page.asset_id,
                        confidence=0.99,
                        content_hash=existing_login_page.content_hash,
                    ),
                )
            }
        )
        page_object_gen = StubPageObjectGenerator({})

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
            page_object_matcher=page_object_matcher,
            page_object_generator=page_object_gen,
        )

        records_by_kind = {(r.need_kind, r.class_name): r for r in result.package.records}
        page_object_record = records_by_kind[("page_object", "com.automation.pages.LoginPage")]
        assert page_object_record.outcome == "bound"
        assert page_object_record.promotion_status is None
        assert page_object_gen.received_contexts == ()
        # A bound (reused) page object was never generated THIS run -- no
        # fresh GenerationIdentity is fabricated for it, the same discipline
        # a bound step-definition's own AssetRecord already follows.
        assert page_object_record.generation_identity is None
        # Nothing was WRITTEN for the bound page object -- the tracked
        # LoginPage.java is untouched, only the step-def is new.
        assert result.cp4_passed is True
        promoted_names = {p.name for p in result.promoted_baseline_paths}
        assert promoted_names == {"LoginSteps.java"}

    def test_end_to_end_with_the_real_live_page_object_matcher(
        self, tmp_path: Path, fake_baseline: Path, repo_root: Path
    ) -> None:
        """The blocker the wiring flagged, closed: `LivePageObjectSemanticMatcher`
        (not `StubSemanticMatcher`) supplied as `page_object_matcher`, driven
        by a deterministic fake `EmbeddingProvider` (no live LLM/network) --
        proves the reuse loop works for page objects through the REAL
        embeddings-backed matcher class, not just through a generic Protocol
        stand-in. One run, two needs: one BINDS against the real tracked
        `LoginPage.isErrorMessageDisplayed()`, the other has no plausible
        match and GENERATES fresh."""
        run_dir = tmp_path / "run"
        workspace_dir = materialize_workspace(run_dir, baseline_root=fake_baseline)
        _write_feature(workspace_dir, "login.feature", _PAGE_OBJECT_FEATURE)
        _write_feature(workspace_dir, "cart.feature", _CART_FEATURE)
        package = _package(
            (
                _feature_record("REQ-1", "login.feature"),
                _feature_record("REQ-2", "cart.feature"),
            )
        )

        tracked_catalog = reconcile(fake_baseline)
        existing_login_page = next(
            asset
            for asset in tracked_catalog.page_objects
            if asset.class_name == "com.automation.pages.LoginPage"
        )

        # Every real tracked page object's own embedding text gets an
        # orthogonal "no match" vector EXCEPT the real LoginPage, which gets
        # the SAME vector as the bind-need's own text -- deterministic
        # control over which need matches what, without hand-authoring 33
        # fixture tags.
        vectors: dict[str, tuple[float, ...]] = {}
        for asset in tracked_catalog.page_objects:
            text = page_object_embedding_text(asset)
            vectors[text] = (
                (1.0, 0.0) if asset.asset_id == existing_login_page.asset_id else (0.0, 1.0)
            )
        vectors["I am on the login page"] = (1.0, 0.0)
        vectors["I am on the cart summary page"] = (0.0, -1.0)  # opposite of every catalog asset
        provider = _FakeEmbeddingProvider(vectors)
        page_object_matcher = LivePageObjectSemanticMatcher(provider)

        matcher = StubSemanticMatcher(
            {"I am on the login page": (), "I am on the cart summary page": ()}
        )
        step_gen = StubStepDefinitionGenerator(
            {
                "I am on the login page": _STEP_JAVA_CALLING_AN_EXISTING_TRACKED_METHOD,
                "I am on the cart summary page": _STEP_JAVA_REFERENCING_A_FRESH_PAGE_OBJECT,
            }
        )
        page_object_gen = StubPageObjectGenerator(
            {"I am on the cart summary page": _CLEAN_GENERATED_FRESH_PAGE_OBJECT_JAVA}
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
            page_object_matcher=page_object_matcher,
            page_object_generator=page_object_gen,
        )

        records_by_kind = {(r.need_kind, r.class_name): r for r in result.package.records}
        bound_record = records_by_kind[("page_object", "com.automation.pages.LoginPage")]
        generated_record = records_by_kind[("page_object", "com.automation.pages.CartSummaryPage")]

        assert bound_record.outcome == "bound"
        assert page_object_gen.received_contexts[0].need.text == "I am on the cart summary page"
        assert generated_record.outcome == "generated"
        assert generated_record.promotion_status == "promoted"
        assert result.cp4_passed is True
