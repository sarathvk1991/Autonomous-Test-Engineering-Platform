"""CP3's deterministic coverage gate (ADR-0044 D5) -- static, no infra.

Proves, deterministically and without any network call: full coverage
passes all four criteria; an unmapped step fails step_coverage,
scenario_coverage, and unmapped_steps ONLY (duplicate_steps stays
independent); an escalated step counts as unmapped the same way; a
duplicate pattern in the post-run catalog fails duplicate_steps ONLY
(coverage stays independent); reuse percentage is computed correctly and
NEVER causes a FAIL, including the 0%-reuse bootstrap case where every
step was freshly generated; and the whole computation is deterministic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.catalog.alignment import correlate
from automation_engineering.catalog.models import JavaParameter, StepDefinitionAsset
from automation_engineering.cp3.coverage import evaluate_coverage
from automation_engineering.cp3.models import (
    CRITERION_DUPLICATE_STEPS,
    CRITERION_SCENARIO_COVERAGE,
    CRITERION_STEP_COVERAGE,
    CRITERION_UNMAPPED_STEPS,
    Cp3CoverageInput,
    Cp3FeatureInput,
)
from automation_engineering.generation.models import (
    BoundStepDefinition,
    EscalatedStepNeed,
    GeneratedStepDefinition,
    StepDefinitionOutcome,
)
from automation_engineering.reuse.models import (
    Escalation,
    EscalationCheck,
    GherkinStepNeed,
    MatchCandidate,
)
from shared.enums.base import ValidationVerdict

_FEATURE_TEMPLATE = """Feature: Checkout

  @SCN-001
  Scenario: Successful checkout
    Given I am logged in
    When I add an item to the cart
    Then I see the order confirmation
"""

_TWO_SCENARIO_FEATURE = """Feature: Checkout

  @SCN-001
  Scenario: Successful checkout
    Given I am logged in
    When I add an item to the cart

  @SCN-002
  Scenario: Failed checkout
    Given I am logged in
    When I use an expired card
"""


def _need(text: str) -> GherkinStepNeed:
    return GherkinStepNeed(text=text, step_type="Given")


def _generated(text: str) -> GeneratedStepDefinition:
    return GeneratedStepDefinition(
        need=_need(text), java_source="// generated", target_package="com.automation.steps"
    )


def _bound(text: str, asset: StepDefinitionAsset) -> BoundStepDefinition:
    return BoundStepDefinition(need=_need(text), asset=asset)


def _escalated(text: str) -> EscalatedStepNeed:
    need = _need(text)
    return EscalatedStepNeed(
        need=need,
        escalation=Escalation(
            need=need,
            check=EscalationCheck.CONFIDENCE,
            candidate=MatchCandidate(asset_id="STEP-x", confidence=0.2, content_hash="h"),
            detail="confidence below threshold",
        ),
    )


def _asset(pattern: str, asset_id: str) -> StepDefinitionAsset:
    parameters: tuple[JavaParameter, ...] = ()
    return StepDefinitionAsset(
        asset_id=asset_id,
        class_name="com.automation.steps.CheckoutSteps",
        method_name="handle",
        step_type="Given",
        pattern=pattern,
        parameters=parameters,
        return_type="void",
        source_file="com/automation/steps/CheckoutSteps.java",
        content_hash="hash-1",
        signature_alignment=correlate(pattern, parameters),
    )


def _input(
    content: str,
    outcomes: tuple[StepDefinitionOutcome, ...],
    assets: tuple[StepDefinitionAsset, ...] = (),
) -> Cp3CoverageInput:
    feature = Cp3FeatureInput(
        content=content, file_path=Path("checkout.feature"), outcomes=outcomes
    )
    return Cp3CoverageInput(features=(feature,), step_definition_assets=assets)


def test_full_coverage_all_steps_bound_or_generated_passes() -> None:
    outcomes = (
        _bound("I am logged in", _asset("I am logged in", "STEP-1")),
        _generated("I add an item to the cart"),
        _generated("I see the order confirmation"),
    )
    criteria, reuse = evaluate_coverage(_input(_FEATURE_TEMPLATE, outcomes))

    by_name = {c.criterion: c for c in criteria}
    assert by_name[CRITERION_STEP_COVERAGE].verdict == ValidationVerdict.PASS
    assert by_name[CRITERION_SCENARIO_COVERAGE].verdict == ValidationVerdict.PASS
    assert by_name[CRITERION_UNMAPPED_STEPS].verdict == ValidationVerdict.PASS
    assert by_name[CRITERION_DUPLICATE_STEPS].verdict == ValidationVerdict.PASS
    assert reuse.reused == 1
    assert reuse.generated == 2


def test_unmapped_step_fails_only_coverage_criteria_not_duplicate() -> None:
    # "I see the order confirmation" never got an outcome at all.
    outcomes = (
        _bound("I am logged in", _asset("I am logged in", "STEP-1")),
        _generated("I add an item to the cart"),
    )
    criteria, _ = evaluate_coverage(_input(_FEATURE_TEMPLATE, outcomes))
    by_name = {c.criterion: c for c in criteria}

    assert by_name[CRITERION_STEP_COVERAGE].verdict == ValidationVerdict.FAIL
    assert by_name[CRITERION_SCENARIO_COVERAGE].verdict == ValidationVerdict.FAIL
    assert by_name[CRITERION_UNMAPPED_STEPS].verdict == ValidationVerdict.FAIL
    unmapped_messages = by_name[CRITERION_UNMAPPED_STEPS].messages
    assert any("I see the order confirmation" in m for m in unmapped_messages)
    # Duplicate detection is unaffected by an unmapped step.
    assert by_name[CRITERION_DUPLICATE_STEPS].verdict == ValidationVerdict.PASS


def test_escalated_step_counts_as_unmapped() -> None:
    outcomes = (
        _bound("I am logged in", _asset("I am logged in", "STEP-1")),
        _generated("I add an item to the cart"),
        _escalated("I see the order confirmation"),
    )
    criteria, reuse = evaluate_coverage(_input(_FEATURE_TEMPLATE, outcomes))
    by_name = {c.criterion: c for c in criteria}

    assert by_name[CRITERION_STEP_COVERAGE].verdict == ValidationVerdict.FAIL
    assert by_name[CRITERION_UNMAPPED_STEPS].verdict == ValidationVerdict.FAIL
    assert any("escalated" in m for m in by_name[CRITERION_UNMAPPED_STEPS].messages)
    # An escalation is neither a reuse nor a generation.
    assert reuse.escalated == 1
    assert reuse.reused == 1
    assert reuse.generated == 1


def test_duplicate_pattern_fails_only_duplicate_steps_criterion() -> None:
    outcomes = (
        _bound("I am logged in", _asset("I am logged in", "STEP-1")),
        _generated("I add an item to the cart"),
        _generated("I see the order confirmation"),
    )
    colliding_assets = (
        _asset("I am logged in", "STEP-1"),
        _asset("I am logged in", "STEP-2"),
    )
    criteria, _ = evaluate_coverage(_input(_FEATURE_TEMPLATE, outcomes, colliding_assets))
    by_name = {c.criterion: c for c in criteria}

    assert by_name[CRITERION_DUPLICATE_STEPS].verdict == ValidationVerdict.FAIL
    assert "STEP-1" in by_name[CRITERION_DUPLICATE_STEPS].messages[0]
    assert "STEP-2" in by_name[CRITERION_DUPLICATE_STEPS].messages[0]
    # Coverage is unaffected by a catalog-level pattern collision.
    assert by_name[CRITERION_STEP_COVERAGE].verdict == ValidationVerdict.PASS
    assert by_name[CRITERION_SCENARIO_COVERAGE].verdict == ValidationVerdict.PASS
    assert by_name[CRITERION_UNMAPPED_STEPS].verdict == ValidationVerdict.PASS


def test_reuse_percentage_zero_on_bootstrap_never_fails_coverage() -> None:
    """Every step freshly generated (0 reuse) -- 0% reuse, correctly, and
    coverage still PASSES: reuse% never gates (D5)."""
    outcomes = (
        _generated("I am logged in"),
        _generated("I add an item to the cart"),
        _generated("I see the order confirmation"),
    )
    criteria, reuse = evaluate_coverage(_input(_FEATURE_TEMPLATE, outcomes))
    by_name = {c.criterion: c for c in criteria}

    assert reuse.reuse_percentage == 0.0
    assert reuse.reused == 0
    assert reuse.generated == 3
    assert by_name[CRITERION_STEP_COVERAGE].verdict == ValidationVerdict.PASS
    assert by_name[CRITERION_SCENARIO_COVERAGE].verdict == ValidationVerdict.PASS
    assert by_name[CRITERION_UNMAPPED_STEPS].verdict == ValidationVerdict.PASS


def test_reuse_percentage_computed_correctly_for_a_mixed_run() -> None:
    outcomes = (
        _bound("I am logged in", _asset("I am logged in", "STEP-1")),
        _bound("I add an item to the cart", _asset("I add an item to the cart", "STEP-2")),
        _generated("I see the order confirmation"),
    )
    _, reuse = evaluate_coverage(_input(_FEATURE_TEMPLATE, outcomes))
    assert reuse.reused == 2
    assert reuse.generated == 1
    assert reuse.reuse_percentage == pytest.approx(66.6667, abs=0.01)


def test_two_scenarios_each_fail_or_pass_scenario_coverage_independently() -> None:
    outcomes = (
        _bound("I am logged in", _asset("I am logged in", "STEP-1")),
        _generated("I add an item to the cart"),
        # "I use an expired card" is left unmapped -- only SCN-002 should fail.
    )
    criteria, _ = evaluate_coverage(_input(_TWO_SCENARIO_FEATURE, outcomes))
    by_name = {c.criterion: c for c in criteria}

    assert by_name[CRITERION_SCENARIO_COVERAGE].verdict == ValidationVerdict.FAIL
    (message,) = by_name[CRITERION_SCENARIO_COVERAGE].messages
    assert "SCN-002" in message
    assert "SCN-001" not in message


def test_evaluate_coverage_is_deterministic() -> None:
    outcomes = (
        _bound("I am logged in", _asset("I am logged in", "STEP-1")),
        _generated("I add an item to the cart"),
        _generated("I see the order confirmation"),
    )
    coverage_input = _input(_FEATURE_TEMPLATE, outcomes)
    result_one = evaluate_coverage(coverage_input)
    result_two = evaluate_coverage(coverage_input)
    assert result_one == result_two
