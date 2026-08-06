"""Glue: dispatch generation's own outcome unions to a promotion decision.

Proves: a `Bound*` outcome (already reused from the baseline) never becomes
a promotion candidate at all (`None`); an `Escalated*` outcome (any of the
three asset kinds) is carried through unedited as `PromotionEscalated`,
joining the SAME reuse-engine escalation, never a second one; a `Generated*`
outcome (any of the three asset kinds) resolves to a real candidate and is
gated exactly as `gate.evaluate_promotion` decides; and `gates=None` for a
`Generated*` outcome raises, rather than silently skipping D2(a).
"""

from __future__ import annotations

import textwrap

import pytest

from automation_engineering.catalog.models import AssetCatalog, StepDefinitionAsset, UtilityAsset
from automation_engineering.cp3.models import (
    CP3_CRITERIA,
    Cp3CriterionResult,
    Cp3Result,
    Cp3ReuseReport,
)
from automation_engineering.generation.models import (
    BoundPageObjectMethod,
    BoundStepDefinition,
    BoundUtilityMethod,
    EscalatedPageObjectMethodNeed,
    EscalatedStepNeed,
    EscalatedUtilityMethodNeed,
    GeneratedPageObject,
    GeneratedStepDefinition,
    GeneratedUtility,
    PageObjectMethodNeed,
    UtilityMethodNeed,
)
from automation_engineering.promotion.models import (
    AssetGateOutcomes,
    NotPromotable,
    Promoted,
    PromotionEscalated,
)
from automation_engineering.promotion.outcomes import promote_outcome
from automation_engineering.reuse.models import Escalation, EscalationCheck, GherkinStepNeed
from shared.enums.base import ValidationVerdict

pytestmark = pytest.mark.unit

_STEP_NEED = GherkinStepNeed(text="I search for a product", step_type="When")

_STEP_SOURCE = textwrap.dedent(
    """\
    package com.automation.steps;

    import io.cucumber.java.en.When;

    public class SearchProductSteps {

        @When("I search for a product")
        public void iSearchForAProduct() {
        }
    }
    """
)

_PAGE_OBJECT_SOURCE = textwrap.dedent(
    """\
    package com.automation.pages;

    import com.automation.base.BasePage;
    import org.openqa.selenium.WebDriver;

    public class SearchPage extends BasePage {

        public SearchPage(WebDriver driver) {
            super(driver);
        }

        public void enterSearchTerm(String term) {
        }
    }
    """
)

_UTILITY_SOURCE = textwrap.dedent(
    """\
    package com.automation.utils;

    public class SearchConfig {

        public String defaultTerm() {
            return "shoes";
        }
    }
    """
)


def _all_pass_cp3_result() -> Cp3Result:
    criteria = tuple(
        Cp3CriterionResult(criterion=name, verdict=ValidationVerdict.PASS) for name in CP3_CRITERIA
    )
    return Cp3Result(
        overall_verdict=ValidationVerdict.PASS,
        criteria=criteria,
        reuse=Cp3ReuseReport(reused=0, generated=1, escalated=0, reuse_percentage=0.0),
    )


def _all_pass() -> AssetGateOutcomes:
    return AssetGateOutcomes(
        cp2_verdict=ValidationVerdict.PASS,
        cp3_result=_all_pass_cp3_result(),
        cp4_verdict=ValidationVerdict.PASS,
    )


def _empty_baseline() -> AssetCatalog:
    return AssetCatalog(baseline_root="test-suite-baseline")


def _dummy_asset() -> StepDefinitionAsset:
    from automation_engineering.catalog.alignment import correlate

    return StepDefinitionAsset(
        asset_id="STEP-existing",
        class_name="com.automation.steps.ExistingSteps",
        method_name="existing",
        step_type="When",
        pattern="I do something",
        parameters=(),
        return_type="void",
        source_file="com/automation/steps/ExistingSteps.java",
        content_hash="existing-hash",
        signature_alignment=correlate("I do something", ()),
    )


def _escalation() -> Escalation:
    from automation_engineering.reuse.models import MatchCandidate

    candidate = MatchCandidate(asset_id="STEP-x", confidence=0.1, content_hash="h")
    return Escalation(
        need=_STEP_NEED,
        check=EscalationCheck.CONFIDENCE,
        candidate=candidate,
        detail="low confidence",
    )


class TestBoundOutcomesAreNeverCandidates:
    def test_bound_step_definition_returns_none(self) -> None:
        outcome = BoundStepDefinition(need=_STEP_NEED, asset=_dummy_asset())

        assert promote_outcome(outcome, _all_pass(), _empty_baseline()) is None

    def test_bound_page_object_method_returns_none(self) -> None:
        method_need = PageObjectMethodNeed(need=_STEP_NEED, method_name="enterSearchTerm")
        outcome = BoundPageObjectMethod(method_need=method_need, asset=_dummy_asset())

        assert promote_outcome(outcome, None, _empty_baseline()) is None

    def test_bound_utility_method_returns_none(self) -> None:
        method_need = UtilityMethodNeed(need=_STEP_NEED, method_name="defaultTerm")
        outcome = BoundUtilityMethod(method_need=method_need, asset=_dummy_asset())

        assert promote_outcome(outcome, None, _empty_baseline()) is None


class TestEscalatedOutcomesJoinTheSharedQueue:
    def test_escalated_step_need_carries_the_same_escalation(self) -> None:
        escalation = _escalation()
        outcome = EscalatedStepNeed(need=_STEP_NEED, escalation=escalation)

        decision = promote_outcome(outcome, None, _empty_baseline())

        assert isinstance(decision, PromotionEscalated)
        assert decision.escalation is escalation

    def test_escalated_page_object_method_need_carries_the_same_escalation(self) -> None:
        escalation = _escalation()
        method_need = PageObjectMethodNeed(need=_STEP_NEED, method_name="enterSearchTerm")
        outcome = EscalatedPageObjectMethodNeed(method_need=method_need, escalation=escalation)

        decision = promote_outcome(outcome, None, _empty_baseline())

        assert isinstance(decision, PromotionEscalated)
        assert decision.escalation is escalation

    def test_escalated_utility_method_need_carries_the_same_escalation(self) -> None:
        escalation = _escalation()
        method_need = UtilityMethodNeed(need=_STEP_NEED, method_name="defaultTerm")
        outcome = EscalatedUtilityMethodNeed(method_need=method_need, escalation=escalation)

        decision = promote_outcome(outcome, None, _empty_baseline())

        assert isinstance(decision, PromotionEscalated)
        assert decision.escalation is escalation


class TestGeneratedOutcomesResolveAndGate:
    def test_generated_step_definition_promotes_against_empty_baseline(self) -> None:
        outcome = GeneratedStepDefinition(
            need=_STEP_NEED, java_source=_STEP_SOURCE, target_package="com.automation.steps"
        )

        decision = promote_outcome(outcome, _all_pass(), _empty_baseline())

        assert isinstance(decision, Promoted)
        assert isinstance(decision.candidate.asset, StepDefinitionAsset)

    def test_generated_page_object_promotes_against_empty_baseline(self) -> None:
        method_need = PageObjectMethodNeed(need=_STEP_NEED, method_name="enterSearchTerm")
        outcome = GeneratedPageObject(
            method_need=method_need,
            java_source=_PAGE_OBJECT_SOURCE,
            target_package="com.automation.pages",
            class_name="SearchPage",
        )

        decision = promote_outcome(outcome, _all_pass(), _empty_baseline())

        assert isinstance(decision, Promoted)

    def test_generated_utility_promotes_against_empty_baseline(self) -> None:
        method_need = UtilityMethodNeed(need=_STEP_NEED, method_name="defaultTerm")
        outcome = GeneratedUtility(
            method_need=method_need,
            java_source=_UTILITY_SOURCE,
            target_package="com.automation.utils",
            class_name="SearchConfig",
        )

        decision = promote_outcome(outcome, _all_pass(), _empty_baseline())

        assert isinstance(decision, Promoted)
        assert isinstance(decision.candidate.asset, UtilityAsset)

    def test_generated_outcome_blocked_by_failing_gate(self) -> None:
        failing_cp3 = Cp3Result(
            overall_verdict=ValidationVerdict.FAIL,
            criteria=tuple(
                Cp3CriterionResult(
                    criterion=name,
                    verdict=ValidationVerdict.FAIL
                    if name == "sonar_quality_gate"
                    else ValidationVerdict.PASS,
                    messages=("server reported ERROR",) if name == "sonar_quality_gate" else (),
                )
                for name in CP3_CRITERIA
            ),
            reuse=Cp3ReuseReport(reused=0, generated=1, escalated=0, reuse_percentage=0.0),
        )
        gates = AssetGateOutcomes(
            cp2_verdict=ValidationVerdict.PASS,
            cp3_result=failing_cp3,
            cp4_verdict=ValidationVerdict.PASS,
        )
        outcome = GeneratedStepDefinition(
            need=_STEP_NEED, java_source=_STEP_SOURCE, target_package="com.automation.steps"
        )

        decision = promote_outcome(outcome, gates, _empty_baseline())

        assert isinstance(decision, NotPromotable)

    def test_missing_gates_for_a_generated_outcome_raises(self) -> None:
        outcome = GeneratedStepDefinition(
            need=_STEP_NEED, java_source=_STEP_SOURCE, target_package="com.automation.steps"
        )

        with pytest.raises(ValueError, match="gates is required"):
            promote_outcome(outcome, None, _empty_baseline())
