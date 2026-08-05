"""CP3's combined verdict (ADR-0044 D5, revised 2026-08-05): the
deterministic coverage gate, the SonarQube quality gate (generic Java
quality only, as of this revision), AND two static customqa:* checks
(direct-webdriver-action, long-method), ALL required to PASS. Neither
customqa:* rule is Sonar-gated any longer: `long-method`'s own backing
rule, `java:S138`, is permanently `scope:MAIN` and structurally cannot
reach this platform's `src/test/java`-resident generated code (ADR-0037
Path A) -- the Sonar-config discovery this revision responds to. The Sonar
criterion stays a hard CP3 requirement (D5's own text is unchanged), it now
verifies only what the built-in profile's own generic-quality rules can
reach.

:func:`evaluate_cp3` is a pure function once its adapter's own calls
return: no code in this module decides pass/fail from anything other than
:func:`~.coverage.evaluate_coverage`'s four criteria, the Sonar adapter's
own quality-gate verdict, and :mod:`~.architecture`'s two static verdicts
(ADR-0040 Decision 2 -- deterministic evidence only, no LLM judgment
anywhere in this gate).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from automation_engineering.cp3.architecture import (
    Cp3GeneratedClassInput,
    evaluate_direct_webdriver_action,
    evaluate_long_method,
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
    """Evaluate CP3's seven criteria -- four deterministic coverage checks,
    the Sonar gate (generic Java quality), and the two static customqa:*
    checks (direct-webdriver-action, long-method) -- and combine them into
    one verdict.

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
        Every generated class this run produced -- step definitions, page
        objects, AND utilities alike, never pre-filtered by the caller
        (:mod:`.architecture` determines each one's own role, or applies no
        role filter at all, per criterion). Defaults to empty, which passes
        both static criteria vacuously -- the same convention
        :func:`automation_engineering.cp4.gate.evaluate_cp4` already
        establishes for an empty ``page_objects`` tuple.

    Returns
    -------
    Cp3Result
        ``overall_verdict`` is ``PASS`` iff all seven named criteria are
        ``PASS`` -- coverage, Sonar, AND both static architectural checks,
        all required (D5, revised 2026-08-05).
    """
    coverage_criteria, reuse_report = evaluate_coverage(coverage_input)
    sonar_criterion = _evaluate_sonar_gate(sonar_input, sonar_adapter)
    webdriver_criterion = evaluate_direct_webdriver_action(generated_classes)
    long_method_criterion = evaluate_long_method(generated_classes)
    criteria = (
        *coverage_criteria,
        sonar_criterion,
        webdriver_criterion,
        long_method_criterion,
    )
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
