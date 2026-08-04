"""CP3's combined verdict (ADR-0044 D5, revised 2026-08-04): the
deterministic coverage gate, the hard SonarQube quality gate, AND the
static direct-webdriver-action check, ALL required to PASS -- "CP3 does not
pass unless a running SonarQube server scans the generated Java and its
quality gate ... passes" is additive to the four coverage criteria, never a
replacement for them; the static check is additive again, for the
customqa:* half Sonar cannot express (the F4 discovery's Path A).

:func:`evaluate_cp3` is a pure function once its adapter's own calls
return: no code in this module decides pass/fail from anything other than
:func:`~.coverage.evaluate_coverage`'s four criteria, the Sonar adapter's
own quality-gate verdict, and :func:`~.architecture.evaluate_direct_webdriver_action`'s
own static verdict (ADR-0040 Decision 2 -- deterministic evidence only, no
LLM judgment anywhere in this gate).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from automation_engineering.cp3.architecture import (
    Cp3GeneratedClassInput,
    evaluate_direct_webdriver_action,
)
from automation_engineering.cp3.coverage import evaluate_coverage
from automation_engineering.cp3.models import (
    CRITERION_SONAR_QUALITY_GATE,
    Cp3CoverageInput,
    Cp3CriterionResult,
    Cp3Result,
)
from automation_engineering.cp3.sonar.adapter import (
    SonarQualityGateAdapter,
    SonarScanError,
    run_quality_gate,
)
from shared.enums.base import ValidationVerdict


@dataclass(frozen=True, slots=True)
class Cp3SonarInput:
    """The Sonar gate's own two inputs: the already-on-disk Maven project
    to scan, and the SonarQube project key it was analyzed under."""

    project_root: Path
    project_key: str


def evaluate_cp3(
    coverage_input: Cp3CoverageInput,
    sonar_input: Cp3SonarInput,
    sonar_adapter: SonarQualityGateAdapter,
    generated_classes: Sequence[Cp3GeneratedClassInput] = (),
) -> Cp3Result:
    """Evaluate CP3's six criteria -- four deterministic coverage checks,
    the hard Sonar gate, and the static direct-webdriver-action check --
    and combine them into one verdict.

    Parameters
    ----------
    coverage_input:
        Every feature this run touched plus the post-run step-definition
        asset catalog (:mod:`.coverage`'s own input).
    sonar_input:
        The Maven project root and project key to scan.
    sonar_adapter:
        Either :class:`~.sonar.stub_adapter.StubSonarQualityGateAdapter`
        (tests) or :class:`~.sonar.live_adapter.LiveSonarQualityGateAdapter`
        (production, where a SonarQube server exists) -- this function
        never constructs one itself, mirroring every other seam in this
        platform (constructor-injected, never selected here).
    generated_classes:
        Every generated class this run produced -- step definitions AND
        page objects alike, never pre-filtered by the caller
        (:mod:`.architecture` determines each one's own role from its own
        parsed ``package`` declaration). Defaults to empty, which passes
        vacuously -- the same convention
        :func:`automation_engineering.cp4.gate.evaluate_cp4` already
        establishes for an empty ``page_objects`` tuple.

    Returns
    -------
    Cp3Result
        ``overall_verdict`` is ``PASS`` iff all six named criteria are
        ``PASS`` -- coverage, Sonar, AND the static architectural check,
        all required (D5, revised 2026-08-04).
    """
    coverage_criteria, reuse_report = evaluate_coverage(coverage_input)
    sonar_criterion = _evaluate_sonar_gate(sonar_input, sonar_adapter)
    architecture_criterion = evaluate_direct_webdriver_action(generated_classes)
    criteria = (*coverage_criteria, sonar_criterion, architecture_criterion)
    overall = (
        ValidationVerdict.PASS
        if all(c.verdict == ValidationVerdict.PASS for c in criteria)
        else ValidationVerdict.FAIL
    )
    return Cp3Result(overall_verdict=overall, criteria=criteria, reuse=reuse_report)


def _evaluate_sonar_gate(
    sonar_input: Cp3SonarInput, adapter: SonarQualityGateAdapter
) -> Cp3CriterionResult:
    """A deterministic pass/fail on the server's own verdict (ADR-0040
    Decision 2) -- the server judges, this function only gates on the
    boolean it returned. A :class:`SonarScanError` (submission failure,
    poll timeout, an unreachable server) is caught here and turned into a
    FAIL criterion rather than propagating -- CP3 fails closed, it never
    crashes."""
    try:
        result = run_quality_gate(adapter, sonar_input.project_root, sonar_input.project_key)
    except SonarScanError as exc:
        return Cp3CriterionResult(
            criterion=CRITERION_SONAR_QUALITY_GATE,
            verdict=ValidationVerdict.FAIL,
            messages=(str(exc),),
        )
    if result.passed:
        return Cp3CriterionResult(
            criterion=CRITERION_SONAR_QUALITY_GATE, verdict=ValidationVerdict.PASS
        )
    failing = tuple(
        f"{condition.metric_key}: {condition.status} "
        f"(actual {condition.actual_value}, threshold {condition.error_threshold})"
        for condition in result.conditions
        if condition.status != "OK"
    )
    messages = failing or ("SonarQube quality gate failed (server reported ERROR).",)
    return Cp3CriterionResult(
        criterion=CRITERION_SONAR_QUALITY_GATE, verdict=ValidationVerdict.FAIL, messages=messages
    )


__all__ = ["Cp3SonarInput", "evaluate_cp3"]
