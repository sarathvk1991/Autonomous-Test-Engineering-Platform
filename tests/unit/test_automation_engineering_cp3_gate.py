"""CP3's combined verdict (ADR-0044 D5): PASS only if BOTH the deterministic
coverage gate AND the SonarQube quality gate pass. Proves the full 2x2
matrix -- coverage-only failure, Sonar-only failure, both failing, both
passing -- with the per-criterion breakdown intact in every case, entirely
against `StubSonarQualityGateAdapter` (no live Sonar server, no network
call anywhere in this module).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import httpx
import pytest

from automation_engineering.cp3.gate import Cp3SonarInput, evaluate_cp3
from automation_engineering.cp3.models import (
    CRITERION_SONAR_QUALITY_GATE,
    CRITERION_STEP_COVERAGE,
    Cp3CoverageInput,
    Cp3FeatureInput,
)
from automation_engineering.cp3.sonar.models import (
    SonarMeasuresResult,
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
    CP3 from an independent Sonar failure -- each of the seven criteria
    fails CP3 independently (D5)."""
    from automation_engineering.cp3.architecture import CRITERION_DIRECT_WEBDRIVER_ACTION

    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=False))
    result = evaluate_cp3(_covering_input(), _SONAR_INPUT, adapter, generated_classes=[])

    assert result.overall_verdict == ValidationVerdict.FAIL
    assert result.criterion(CRITERION_DIRECT_WEBDRIVER_ACTION).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_SONAR_QUALITY_GATE).verdict == ValidationVerdict.FAIL


def _over_limit_method_source(package: str, class_name: str, method_name: str) -> str:
    body = "\n".join(f'        System.out.println("line {i}");' for i in range(39))
    return (
        f"package {package};\n\n"
        f"public class {class_name} {{\n\n"
        f"    public void {method_name}() {{\n"
        f"{body}\n"
        f"    }}\n"
        f"}}\n"
    )


def test_coverage_sonar_webdriver_pass_but_long_method_fails_yields_cp3_fail() -> None:
    """ADR-0044 D5's third revision (2026-08-05): long_method is a HARD
    seventh criterion -- a clean coverage gate, a passing Sonar scan (now
    generic-quality-only), and a clean direct-webdriver-action check do not
    rescue CP3 from a >40-line generated method."""
    from automation_engineering.cp3.architecture import (
        CRITERION_DIRECT_WEBDRIVER_ACTION,
        CRITERION_LONG_METHOD,
        Cp3GeneratedClassInput,
    )

    long_page_object = Cp3GeneratedClassInput(
        class_name="OverLimitPage",
        java_source=_over_limit_method_source(
            "com.automation.pages", "OverLimitPage", "overLimit"
        ),
    )
    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=True))
    result = evaluate_cp3(
        _covering_input(), _SONAR_INPUT, adapter, generated_classes=[long_page_object]
    )

    assert result.overall_verdict == ValidationVerdict.FAIL
    assert result.criterion(CRITERION_STEP_COVERAGE).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_SONAR_QUALITY_GATE).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_DIRECT_WEBDRIVER_ACTION).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_LONG_METHOD).verdict == ValidationVerdict.FAIL


def test_long_method_pass_does_not_rescue_an_independent_direct_webdriver_action_failure() -> (
    None
):
    """The converse: a clean long_method check does not rescue CP3 from an
    independent direct_webdriver_action failure -- each static criterion
    fails CP3 independently."""
    from automation_engineering.cp3.architecture import (
        CRITERION_DIRECT_WEBDRIVER_ACTION,
        CRITERION_LONG_METHOD,
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
    assert result.criterion(CRITERION_LONG_METHOD).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_DIRECT_WEBDRIVER_ACTION).verdict == ValidationVerdict.FAIL


def test_all_seven_criteria_clean_yields_cp3_pass() -> None:
    """The converse of the composite-fail proofs above: coverage, Sonar,
    direct-webdriver-action, AND long-method all clean together yields an
    overall CP3 PASS."""
    from automation_engineering.cp3.architecture import (
        CRITERION_DIRECT_WEBDRIVER_ACTION,
        CRITERION_LONG_METHOD,
        Cp3GeneratedClassInput,
    )

    clean_step_def = Cp3GeneratedClassInput(
        class_name="LoginSteps",
        java_source=(
            "package com.automation.steps;\n\n"
            "public class LoginSteps {\n\n"
            "    public void iLogInAs() {\n"
            '        System.out.println("clean");\n'
            "    }\n"
            "}\n"
        ),
    )
    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=True))
    result = evaluate_cp3(
        _covering_input(), _SONAR_INPUT, adapter, generated_classes=[clean_step_def]
    )

    assert result.overall_verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_STEP_COVERAGE).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_SONAR_QUALITY_GATE).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_DIRECT_WEBDRIVER_ACTION).verdict == ValidationVerdict.PASS
    assert result.criterion(CRITERION_LONG_METHOD).verdict == ValidationVerdict.PASS


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


class _HttpErrorRaisingSonarAdapter:
    """A minimal stand-in whose `poll_for_completion` raises a raw
    `httpx.HTTPError` -- the shape of a genuine mid-poll transport failure
    or non-2xx response propagating unwrapped out of `LiveSonarQualityGateAdapter`
    (its own `poll_for_completion`/`fetch_quality_gate_result` call
    `response.raise_for_status()` unguarded). `StubSonarQualityGateAdapter`
    cannot script this directly (`poll_error` is typed `SonarScanError |
    None`), so this local fake exists purely to prove CP3's own httpx
    catch, mirroring the `_RaisingEmbeddingProvider` local-fake convention
    `tests/unit/test_suite_quality_governance_stage.py` already
    establishes for the identical kind of proof one component over."""

    def submit_scan(self, project_root: Path, project_key: str) -> str:
        return "stub-scan-1"

    def poll_for_completion(self, task_id: str) -> None:
        raise httpx.HTTPError("connection reset mid-poll")

    def fetch_quality_gate_result(self, project_key: str) -> SonarQualityGateResult:
        raise AssertionError("unreachable: poll_for_completion always raises first")

    def fetch_measures(
        self, project_key: str, metric_keys: Sequence[str]
    ) -> SonarMeasuresResult:
        raise AssertionError("fetch_measures is never called by CP3's own gate")


def test_an_httpx_http_error_fails_the_sonar_criterion_cleanly_not_a_crash() -> None:
    """The gap this fixes: a raw `httpx.HTTPError` escaping the live
    adapter used to propagate straight out of `_evaluate_sonar_gate`
    uncaught, crashing CP3 instead of degrading it -- mirrors
    `suite_quality_governance.stage.runner._fetch_cp7_report_outcome`'s own
    `except (SonarScanError, httpx.HTTPError)` catch at the identical kind
    of boundary."""
    adapter = _HttpErrorRaisingSonarAdapter()

    result = evaluate_cp3(_covering_input(), _SONAR_INPUT, adapter)

    assert result.overall_verdict == ValidationVerdict.FAIL
    sonar_criterion = result.criterion(CRITERION_SONAR_QUALITY_GATE)
    assert sonar_criterion.verdict == ValidationVerdict.FAIL
    assert "connection reset mid-poll" in sonar_criterion.messages[0]


def test_sonar_scan_error_and_httpx_http_error_degrade_identically() -> None:
    """Parity: whichever exception the adapter raises, CP3's own Sonar
    criterion lands on the SAME degraded outcome -- a FAIL criterion
    carrying the exception's own message, never a crash, and never a
    different verdict depending on which failure mode fired."""
    from automation_engineering.cp3.sonar.adapter import SonarScanError

    scan_error_adapter = StubSonarQualityGateAdapter(
        poll_error=SonarScanError("scan failed")
    )
    http_error_adapter = _HttpErrorRaisingSonarAdapter()

    scan_error_result = evaluate_cp3(_covering_input(), _SONAR_INPUT, scan_error_adapter)
    http_error_result = evaluate_cp3(_covering_input(), _SONAR_INPUT, http_error_adapter)

    scan_error_criterion = scan_error_result.criterion(CRITERION_SONAR_QUALITY_GATE)
    http_error_criterion = http_error_result.criterion(CRITERION_SONAR_QUALITY_GATE)
    assert scan_error_result.overall_verdict == http_error_result.overall_verdict
    assert scan_error_criterion.verdict == http_error_criterion.verdict == ValidationVerdict.FAIL
    assert len(scan_error_criterion.messages) == len(http_error_criterion.messages) == 1


def test_unknown_criterion_name_raises_key_error() -> None:
    adapter = StubSonarQualityGateAdapter(result=SonarQualityGateResult(passed=True))
    result = evaluate_cp3(_covering_input(), _SONAR_INPUT, adapter)
    with pytest.raises(KeyError):
        result.criterion("not_a_real_criterion")
