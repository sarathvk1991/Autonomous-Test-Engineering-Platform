"""CP3's combined verdict (ADR-0044 D5): PASS only if BOTH the deterministic
coverage gate AND the SonarQube quality gate pass. Proves the full 2x2
matrix -- coverage-only failure, Sonar-only failure, both failing, both
passing -- with the per-criterion breakdown intact in every case, entirely
against `StubSonarQualityGateAdapter` (no live Sonar server, no network
call anywhere in this module).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from automation_engineering.cp3.gate import Cp3SonarInput, evaluate_cp3
from automation_engineering.cp3.models import (
    CRITERION_SONAR_QUALITY_GATE,
    CRITERION_STEP_COVERAGE,
    Cp3CoverageInput,
    Cp3FeatureInput,
)
from automation_engineering.cp3.sonar.models import (
    SonarQualityGateCondition,
    SonarQualityGateResult,
)
from automation_engineering.cp3.sonar.stub_adapter import StubSonarQualityGateAdapter
from automation_engineering.generation.models import GeneratedStepDefinition
from automation_engineering.reuse.models import GherkinStepNeed
from shared.enums.base import ValidationVerdict

pytestmark = pytest.mark.unit

_FULLY_COVERED_FEATURE = """Feature: Checkout

  @SCN-001
  Scenario: Successful checkout
    Given I am logged in
"""


def _need(text: str) -> GherkinStepNeed:
    return GherkinStepNeed(text=text, step_type="Given")


def _generated(text: str) -> GeneratedStepDefinition:
    return GeneratedStepDefinition(
        need=_need(text), java_source="// generated", target_package="com.automation.steps"
    )


def _covering_input() -> Cp3CoverageInput:
    feature = Cp3FeatureInput(
        content=_FULLY_COVERED_FEATURE,
        file_path=Path("checkout.feature"),
        outcomes=(_generated("I am logged in"),),
    )
    return Cp3CoverageInput(features=(feature,))


def _uncovered_input() -> Cp3CoverageInput:
    feature = Cp3FeatureInput(
        content=_FULLY_COVERED_FEATURE, file_path=Path("checkout.feature"), outcomes=()
    )
    return Cp3CoverageInput(features=(feature,))


_SONAR_INPUT = Cp3SonarInput(
    project_root=Path("/workspace/test-suite-baseline"), project_key="demo"
)


def test_coverage_pass_and_sonar_pass_yields_cp3_pass() -> None:
    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=True))
    result = evaluate_cp3(_covering_input(), _SONAR_INPUT, adapter)

    assert result.overall_verdict == ValidationVerdict.PASS
    assert result.passed is True
    assert result.criterion(CRITERION_STEP_COVERAGE).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_SONAR_QUALITY_GATE).verdict == ValidationVerdict.PASS


def test_coverage_fail_and_sonar_pass_yields_cp3_fail() -> None:
    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=True))
    result = evaluate_cp3(_uncovered_input(), _SONAR_INPUT, adapter)

    assert result.overall_verdict == ValidationVerdict.FAIL
    assert result.criterion(CRITERION_STEP_COVERAGE).verdict == ValidationVerdict.FAIL
    assert result.criterion(CRITERION_SONAR_QUALITY_GATE).verdict == ValidationVerdict.PASS


def test_coverage_pass_and_sonar_fail_yields_cp3_fail() -> None:
    """A clean coverage gate does not save CP3 from a Sonar failure -- the
    Sonar gate is HARD (D5), not advisory."""
    adapter = StubSonarQualityGateAdapter(
        result=SonarQualityGateResult(
            passed=False,
            conditions=(
                SonarQualityGateCondition(
                    metric_key="customqa:direct-webdriver-action",
                    status="ERROR",
                    actual_value="2",
                    error_threshold="0",
                ),
            ),
        )
    )
    result = evaluate_cp3(_covering_input(), _SONAR_INPUT, adapter)

    assert result.overall_verdict == ValidationVerdict.FAIL
    assert result.criterion(CRITERION_STEP_COVERAGE).verdict == ValidationVerdict.PASS
    sonar_criterion = result.criterion(CRITERION_SONAR_QUALITY_GATE)
    assert sonar_criterion.verdict == ValidationVerdict.FAIL
    assert "customqa:direct-webdriver-action" in sonar_criterion.messages[0]


def test_coverage_fail_and_sonar_fail_yields_cp3_fail() -> None:
    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=False))
    result = evaluate_cp3(_uncovered_input(), _SONAR_INPUT, adapter)

    assert result.overall_verdict == ValidationVerdict.FAIL
    assert result.criterion(CRITERION_STEP_COVERAGE).verdict == ValidationVerdict.FAIL
    assert result.criterion(CRITERION_SONAR_QUALITY_GATE).verdict == ValidationVerdict.FAIL


def test_coverage_pass_and_sonar_pass_and_direct_webdriver_action_fail_yields_cp3_fail() -> None:
    """ADR-0044 D5 revision (2026-08-04): the static architectural check is
    a HARD sixth criterion, not advisory -- a clean coverage gate and a
    passing Sonar scan do not rescue CP3 from a step-definition class that
    calls WebDriver directly."""
    from automation_engineering.cp3.architecture import (
        CRITERION_DIRECT_WEBDRIVER_ACTION,
        Cp3GeneratedClassInput,
    )

    violating_step_def = Cp3GeneratedClassInput(
        class_name="LoginSteps",
        java_source=(
            "package com.automation.steps;\n"
            "import org.openqa.selenium.WebDriver;\n"
            "public class LoginSteps {\n"
            "    private WebDriver driver;\n"
            "    public void doLogin() { driver.click(); }\n"
            "}\n"
        ),
    )
    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=True))
    result = evaluate_cp3(
        _covering_input(), _SONAR_INPUT, adapter, generated_classes=[violating_step_def]
    )

    assert result.overall_verdict == ValidationVerdict.FAIL
    assert result.criterion(CRITERION_STEP_COVERAGE).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_SONAR_QUALITY_GATE).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_DIRECT_WEBDRIVER_ACTION).verdict == ValidationVerdict.FAIL


def test_direct_webdriver_action_pass_does_not_rescue_a_sonar_failure() -> None:
    """The converse: a clean static architectural check does not rescue
    CP3 from an independent Sonar failure -- each of the six criteria
    fails CP3 independently (D5)."""
    from automation_engineering.cp3.architecture import CRITERION_DIRECT_WEBDRIVER_ACTION

    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=False))
    result = evaluate_cp3(_covering_input(), _SONAR_INPUT, adapter, generated_classes=[])

    assert result.overall_verdict == ValidationVerdict.FAIL
    assert result.criterion(CRITERION_DIRECT_WEBDRIVER_ACTION).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_SONAR_QUALITY_GATE).verdict == ValidationVerdict.FAIL


def test_a_scan_error_fails_the_sonar_criterion_cleanly_not_a_crash() -> None:
    from automation_engineering.cp3.sonar.adapter import SonarScanError

    adapter = StubSonarQualityGateAdapter(
        poll_error=SonarScanError("no SonarQube server reachable")
    )
    result = evaluate_cp3(_covering_input(), _SONAR_INPUT, adapter)

    assert result.overall_verdict == ValidationVerdict.FAIL
    sonar_criterion = result.criterion(CRITERION_SONAR_QUALITY_GATE)
    assert sonar_criterion.verdict == ValidationVerdict.FAIL
    assert "no SonarQube server reachable" in sonar_criterion.messages[0]


def test_unknown_criterion_name_raises_key_error() -> None:
    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=True))
    result = evaluate_cp3(_covering_input(), _SONAR_INPUT, adapter)
    with pytest.raises(KeyError):
        result.criterion("not_a_real_criterion")
