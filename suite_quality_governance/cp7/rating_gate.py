"""CP7's rating-gate evaluation (ADR-0047 D3's own amendment note,
2026-08-10): the deferred trigger is met (suite compiles + real,
calibratable scores), so `reliability_rating`/`sqale_rating` now gate at an
A-or-B floor.

**GLUE, invents no new fetch mechanism -- consumes an already-fetched
report.** Mirrors `.measures.fetch_whole_suite_quality_report`'s own "one
call, no HTTP/subprocess of its own" posture: this module performs no
network call. It is handed a `Cp7WholeSuiteQualityReport` already obtained
by `.measures.fetch_whole_suite_quality_report` (or `None`, when CP7's own
measures were unobtainable this run -- `suite_quality_governance.stage
.runner.Cp7ReportOutcome.report`) and computes a verdict purely from the two
rating values it already carries.
"""

from __future__ import annotations

from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp7.models import (
    CRITERION_RELIABILITY_RATING_GATE,
    CRITERION_SQALE_RATING_GATE,
    RATING_GATE_MAX_VALUE,
    Cp7RatingGateCriterionResult,
    Cp7RatingGateResult,
    Cp7WholeSuiteQualityReport,
)

#: (criterion name, metric key) pairs, in report order.
_RATING_GATE_CRITERIA: tuple[tuple[str, str], ...] = (
    (CRITERION_RELIABILITY_RATING_GATE, "reliability_rating"),
    (CRITERION_SQALE_RATING_GATE, "sqale_rating"),
)


def _evaluate_one_rating(
    criterion: str, metric_key: str, value: str | None
) -> Cp7RatingGateCriterionResult:
    if value is None:
        return Cp7RatingGateCriterionResult(
            criterion=criterion,
            metric_key=metric_key,
            verdict=ValidationVerdict.WARN,
            value=None,
            detail=f"{metric_key} was not measured (Sonar unavailable, or no value returned)",
        )
    try:
        numeric_value = float(value)
    except ValueError:
        return Cp7RatingGateCriterionResult(
            criterion=criterion,
            metric_key=metric_key,
            verdict=ValidationVerdict.WARN,
            value=value,
            detail=f"{metric_key} returned an unrecognized rating value {value!r}",
        )
    if numeric_value <= RATING_GATE_MAX_VALUE:
        return Cp7RatingGateCriterionResult(
            criterion=criterion,
            metric_key=metric_key,
            verdict=ValidationVerdict.PASS,
            value=value,
            detail=f"{metric_key}={value} (A or B)",
        )
    return Cp7RatingGateCriterionResult(
        criterion=criterion,
        metric_key=metric_key,
        verdict=ValidationVerdict.FAIL,
        value=value,
        detail=f"{metric_key}={value} (worse than B)",
    )


def evaluate_rating_gate(report: Cp7WholeSuiteQualityReport | None) -> Cp7RatingGateResult:
    """CP7's own rating gate (ADR-0047 D3's amendment note). `report` is
    `None` exactly when CP7's own measures fetch was unavailable this run
    (`suite_quality_governance.stage.runner.Cp7ReportOutcome.report`) -- an
    unavailable report degrades every criterion to `WARN`, the identical
    "unmeasured, never a fabricated FAIL" treatment a report with a missing
    individual metric value already gets (`Cp7MeasureFinding.value=None`,
    ADR-0047 D5's own discipline, reused here rather than a second rule).

    `overall_verdict`: `FAIL` iff any criterion is `FAIL`; else `WARN` iff
    any criterion is `WARN`; else `PASS` -- the same governed aggregation
    `requirement_intelligence.cp1.engine.cp1_engine._derive_verdict`
    already establishes (ADR-0012 §8).
    """
    value_by_key: dict[str, str | None] = (
        {finding.metric_key: finding.value for finding in report.generic_quality}
        if report is not None
        else {}
    )
    criteria = tuple(
        _evaluate_one_rating(criterion, metric_key, value_by_key.get(metric_key))
        for criterion, metric_key in _RATING_GATE_CRITERIA
    )
    if any(c.verdict == ValidationVerdict.FAIL for c in criteria):
        overall_verdict = ValidationVerdict.FAIL
    elif any(c.verdict == ValidationVerdict.WARN for c in criteria):
        overall_verdict = ValidationVerdict.WARN
    else:
        overall_verdict = ValidationVerdict.PASS
    return Cp7RatingGateResult(overall_verdict=overall_verdict, criteria=criteria)


__all__ = ["evaluate_rating_gate"]
