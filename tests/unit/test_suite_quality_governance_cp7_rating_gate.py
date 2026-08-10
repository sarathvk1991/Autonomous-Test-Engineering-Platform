"""CP7's rating-gate evaluation (ADR-0047 D3's own amendment note,
2026-08-10) -- `suite_quality_governance.cp7.rating_gate.evaluate_rating_gate`.

Proves: the A-or-B boundary (A and B pass, C fails) for BOTH gated ratings
(`reliability_rating`/`sqale_rating`); report-only metrics (violations,
bugs, code_smells, security, coverage/duplication) never influence the
gate at all -- only the two named ratings are read; an unmeasured/
unavailable rating (a `None` value, an absent report entirely, or an
unrecognized value) produces `WARN`, never `FAIL` -- "unmeasured" and
"a real regression" stay distinct states, mirroring
`Cp7MeasureFinding.value=None`'s own "absent, never faked" discipline one
level up; the overall-verdict aggregation (FAIL > WARN > PASS) mirrors
`requirement_intelligence.cp1.engine.cp1_engine._derive_verdict`
(ADR-0012 §8) exactly; determinism.
"""

from __future__ import annotations

from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp7.models import (
    CRITERION_RELIABILITY_RATING_GATE,
    CRITERION_SQALE_RATING_GATE,
    Cp7MeasureFinding,
    Cp7WholeSuiteQualityReport,
)
from suite_quality_governance.cp7.rating_gate import evaluate_rating_gate


def _report(
    *,
    reliability_rating: str | None = "1.0",
    sqale_rating: str | None = "1.0",
    reliability_present: bool = True,
    sqale_present: bool = True,
) -> Cp7WholeSuiteQualityReport:
    generic_quality: list[Cp7MeasureFinding] = [
        Cp7MeasureFinding(metric_key="violations", value="0"),
        Cp7MeasureFinding(metric_key="bugs", value="0"),
        Cp7MeasureFinding(metric_key="code_smells", value="0"),
    ]
    if reliability_present:
        generic_quality.append(
            Cp7MeasureFinding(metric_key="reliability_rating", value=reliability_rating)
        )
    if sqale_present:
        generic_quality.append(Cp7MeasureFinding(metric_key="sqale_rating", value=sqale_rating))
    return Cp7WholeSuiteQualityReport(
        project_key="Automation-POC",
        generic_quality=tuple(generic_quality),
        security=(
            Cp7MeasureFinding(metric_key="vulnerabilities", value="0"),
            Cp7MeasureFinding(metric_key="security_hotspots", value="0"),
            Cp7MeasureFinding(metric_key="security_rating", value="1.0"),
        ),
        coverage_and_duplication=(
            Cp7MeasureFinding(metric_key="coverage", value=None),
            Cp7MeasureFinding(metric_key="duplicated_lines_density", value="0.0"),
        ),
    )


class TestAOrBBoundary:
    def test_a_a_passes(self) -> None:
        result = evaluate_rating_gate(_report(reliability_rating="1.0", sqale_rating="1.0"))

        assert result.overall_verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_RELIABILITY_RATING_GATE).verdict == ValidationVerdict.PASS
        assert result.criterion(CRITERION_SQALE_RATING_GATE).verdict == ValidationVerdict.PASS

    def test_b_b_passes(self) -> None:
        result = evaluate_rating_gate(_report(reliability_rating="2.0", sqale_rating="2.0"))

        assert result.overall_verdict == ValidationVerdict.PASS

    def test_c_fails(self) -> None:
        result = evaluate_rating_gate(_report(reliability_rating="3.0", sqale_rating="1.0"))

        assert result.criterion(CRITERION_RELIABILITY_RATING_GATE).verdict == ValidationVerdict.FAIL
        assert result.overall_verdict == ValidationVerdict.FAIL

    def test_d_and_e_also_fail(self) -> None:
        assert (
            evaluate_rating_gate(_report(sqale_rating="4.0")).overall_verdict
            == ValidationVerdict.FAIL
        )
        assert (
            evaluate_rating_gate(_report(sqale_rating="5.0")).overall_verdict
            == ValidationVerdict.FAIL
        )

    def test_either_rating_alone_worse_than_b_fails_the_whole_gate(self) -> None:
        only_sqale_bad = evaluate_rating_gate(_report(reliability_rating="1.0", sqale_rating="3.0"))
        only_reliability_bad = evaluate_rating_gate(
            _report(reliability_rating="3.0", sqale_rating="1.0")
        )

        assert only_sqale_bad.overall_verdict == ValidationVerdict.FAIL
        assert only_reliability_bad.overall_verdict == ValidationVerdict.FAIL


class TestReportOnlyMetricsNeverInfluenceTheGate:
    def test_bad_counts_and_security_and_coverage_do_not_affect_a_clean_rating_gate(self) -> None:
        report = Cp7WholeSuiteQualityReport(
            project_key="Automation-POC",
            generic_quality=(
                Cp7MeasureFinding(metric_key="violations", value="999"),
                Cp7MeasureFinding(metric_key="bugs", value="42"),
                Cp7MeasureFinding(metric_key="code_smells", value="500"),
                Cp7MeasureFinding(metric_key="reliability_rating", value="1.0"),
                Cp7MeasureFinding(metric_key="sqale_rating", value="1.0"),
            ),
            security=(
                Cp7MeasureFinding(metric_key="vulnerabilities", value="99"),
                Cp7MeasureFinding(metric_key="security_hotspots", value="99"),
                Cp7MeasureFinding(metric_key="security_rating", value="5.0"),
            ),
            coverage_and_duplication=(
                Cp7MeasureFinding(metric_key="coverage", value="1.2"),
                Cp7MeasureFinding(metric_key="duplicated_lines_density", value="87.0"),
            ),
        )

        result = evaluate_rating_gate(report)

        assert result.overall_verdict == ValidationVerdict.PASS

    def test_only_the_two_named_metric_keys_are_ever_read(self) -> None:
        result = evaluate_rating_gate(_report())

        assert {c.metric_key for c in result.criteria} == {"reliability_rating", "sqale_rating"}


class TestUnmeasuredNeverFails:
    def test_a_none_value_for_one_rating_warns_the_gate_but_never_fails_it(self) -> None:
        result = evaluate_rating_gate(_report(reliability_rating=None, sqale_rating="1.0"))

        reliability = result.criterion(CRITERION_RELIABILITY_RATING_GATE)
        assert reliability.verdict == ValidationVerdict.WARN
        assert reliability.value is None
        assert result.overall_verdict == ValidationVerdict.WARN
        assert result.passed is True

    def test_a_metric_absent_from_the_report_entirely_also_warns(self) -> None:
        result = evaluate_rating_gate(
            _report(reliability_present=False, sqale_rating="1.0")
        )

        assert result.criterion(CRITERION_RELIABILITY_RATING_GATE).verdict == ValidationVerdict.WARN
        assert result.overall_verdict == ValidationVerdict.WARN

    def test_no_report_at_all_warns_both_criteria(self) -> None:
        result = evaluate_rating_gate(None)

        assert result.criterion(CRITERION_RELIABILITY_RATING_GATE).verdict == ValidationVerdict.WARN
        assert result.criterion(CRITERION_SQALE_RATING_GATE).verdict == ValidationVerdict.WARN
        assert result.overall_verdict == ValidationVerdict.WARN
        assert result.passed is True

    def test_an_unrecognized_value_warns_rather_than_crashing_or_faking_a_verdict(self) -> None:
        result = evaluate_rating_gate(
            _report(reliability_rating="not-a-rating", sqale_rating="1.0")
        )

        assert result.criterion(CRITERION_RELIABILITY_RATING_GATE).verdict == ValidationVerdict.WARN
        assert result.overall_verdict == ValidationVerdict.WARN

    def test_fail_beats_warn_beats_pass_when_mixed(self) -> None:
        """One rating unmeasured (WARN-worthy), the other a real
        regression (FAIL-worthy) -- FAIL wins, mirroring
        `_derive_verdict`'s own governed aggregation exactly."""
        result = evaluate_rating_gate(_report(reliability_rating=None, sqale_rating="4.0"))

        assert result.criterion(CRITERION_RELIABILITY_RATING_GATE).verdict == ValidationVerdict.WARN
        assert result.criterion(CRITERION_SQALE_RATING_GATE).verdict == ValidationVerdict.FAIL
        assert result.overall_verdict == ValidationVerdict.FAIL
        assert result.passed is False


class TestDeterminism:
    def test_same_report_yields_the_same_result(self) -> None:
        report = _report(reliability_rating="1.0", sqale_rating="2.0")

        first = evaluate_rating_gate(report)
        second = evaluate_rating_gate(report)

        assert first == second
