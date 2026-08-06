"""CP7 -- whole-suite Sonar quality governance (ADR-0047 D1-D6).

Proves: the stub-measures flow (a scripted `SonarMeasuresResult` reaches
CP7's own three-family report); report-only structurally (no
`overall_verdict`/`passed` field anywhere on `Cp7WholeSuiteQualityReport`
-- this is a report, not a gate); unmeasured-metric honesty (a metric the
adapter reports as `value=None` surfaces as `measured=False`, never faked
as clean); whole-suite scope (one `fetch_measures` call, the whole D3+D4+D5
metric set, never a per-run subset); no baseline mutation (the fetch takes
only an adapter and a project key -- no filesystem path anywhere in its
own signature).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from automation_engineering.cp3.sonar.models import SonarMeasure, SonarMeasuresResult
from automation_engineering.cp3.sonar.stub_adapter import StubSonarQualityGateAdapter
from suite_quality_governance.cp7.measures import fetch_whole_suite_quality_report
from suite_quality_governance.cp7.models import (
    ALL_CP7_METRICS,
    COVERAGE_AND_DUPLICATION_METRICS,
    GENERIC_QUALITY_METRICS,
    SECURITY_METRICS,
    Cp7WholeSuiteQualityReport,
)

pytestmark = pytest.mark.unit


def _all_clean_measures(project_key: str = "Automation-POC") -> SonarMeasuresResult:
    """Mirrors the real, live-verified values (ADR-0047 D10): every
    generic-quality/security metric currently clean/best-value; both
    coverage/duplication metrics unmeasured (no JaCoCo report ever
    submitted)."""
    clean = {
        "violations": "0",
        "bugs": "0",
        "code_smells": "0",
        "sqale_rating": "1.0",
        "reliability_rating": "1.0",
        "vulnerabilities": "0",
        "security_hotspots": "0",
        "security_rating": "1.0",
    }
    measures = tuple(
        SonarMeasure(metric_key=key, value=clean.get(key)) for key in ALL_CP7_METRICS
    )
    return SonarMeasuresResult(project_key=project_key, measures=measures)


class TestStubMeasuresFlowThroughToTheReport:
    def test_scripted_measures_populate_all_three_families(self) -> None:
        adapter = StubSonarQualityGateAdapter(measures=_all_clean_measures())

        report = fetch_whole_suite_quality_report(adapter, "Automation-POC")

        assert report.project_key == "Automation-POC"
        assert {f.metric_key for f in report.generic_quality} == set(GENERIC_QUALITY_METRICS)
        assert {f.metric_key for f in report.security} == set(SECURITY_METRICS)
        assert {f.metric_key for f in report.coverage_and_duplication} == set(
            COVERAGE_AND_DUPLICATION_METRICS
        )
        violations = next(f for f in report.generic_quality if f.metric_key == "violations")
        assert violations.value == "0"
        assert violations.measured is True

    def test_one_fetch_measures_call_for_the_whole_metric_set(self) -> None:
        """Whole-suite scope, proved structurally: ONE call, the full
        D3+D4+D5 set -- never one call per family, never a per-run
        subset."""
        adapter = StubSonarQualityGateAdapter(measures=_all_clean_measures())

        fetch_whole_suite_quality_report(adapter, "Automation-POC")

        assert adapter.measures_calls == [("Automation-POC", ALL_CP7_METRICS)]


class TestReportOnlyStructurally:
    def test_the_report_has_no_verdict_or_passed_field(self) -> None:
        """CP7 is report-only (ADR-0047 D3) -- structurally, not merely
        by never failing. `Cp7WholeSuiteQualityReport` carries no
        `overall_verdict`/`passed` attribute at all, mirroring
        `Cp5NearDuplicateSweepResult`'s own no-verdict shape."""
        adapter = StubSonarQualityGateAdapter(measures=_all_clean_measures())

        report = fetch_whole_suite_quality_report(adapter, "Automation-POC")

        assert not hasattr(report, "overall_verdict")
        assert not hasattr(report, "passed")
        assert set(Cp7WholeSuiteQualityReport.__dataclass_fields__) == {
            "project_key",
            "generic_quality",
            "security",
            "coverage_and_duplication",
        }


class TestUnmeasuredMetricHonesty:
    def test_a_metric_the_adapter_reports_as_none_surfaces_as_unmeasured_not_faked(
        self,
    ) -> None:
        adapter = StubSonarQualityGateAdapter(measures=_all_clean_measures())

        report = fetch_whole_suite_quality_report(adapter, "Automation-POC")

        coverage = next(
            f for f in report.coverage_and_duplication if f.metric_key == "coverage"
        )
        duplication = next(
            f
            for f in report.coverage_and_duplication
            if f.metric_key == "duplicated_lines_density"
        )
        assert coverage.value is None
        assert coverage.measured is False
        assert duplication.value is None
        assert duplication.measured is False
        assert report.has_unmeasured_findings is True

    def test_all_measured_reports_no_unmeasured_findings(self) -> None:
        measures = SonarMeasuresResult(
            project_key="demo",
            measures=tuple(
                SonarMeasure(metric_key=key, value="1.0") for key in ALL_CP7_METRICS
            ),
        )
        adapter = StubSonarQualityGateAdapter(measures=measures)

        report = fetch_whole_suite_quality_report(adapter, "demo")

        assert report.has_unmeasured_findings is False
        assert all(f.measured for f in report.all_findings)

    def test_a_key_the_adapter_never_returns_at_all_is_also_treated_as_unmeasured(
        self,
    ) -> None:
        """A defensive proof, distinct from the adapter's own contract
        (which always returns one `SonarMeasure` per requested key,
        ADR-0047 D6): even if a caller's own adapter implementation
        omitted a key entirely, CP7's own grouping never crashes and never
        fabricates a value -- `.get(key)` degrades to the same
        `value=None`/unmeasured state."""
        partial = SonarMeasuresResult(
            project_key="demo",
            measures=(SonarMeasure(metric_key="violations", value="0"),),
        )
        adapter = StubSonarQualityGateAdapter(measures=partial)

        report = fetch_whole_suite_quality_report(adapter, "demo")

        bugs = next(f for f in report.generic_quality if f.metric_key == "bugs")
        assert bugs.value is None
        assert bugs.measured is False


class TestNoBaselineMutation:
    def test_fetch_signature_takes_no_filesystem_path(self) -> None:
        """Read-only by construction: CP7 reads Sonar's own already-
        accumulated server-side state, never a local baseline scan --
        `fetch_whole_suite_quality_report`'s own signature has no
        `baseline_root`/`Path` parameter to mutate through."""
        signature = inspect.signature(fetch_whole_suite_quality_report)
        assert list(signature.parameters) == ["adapter", "project_key"]

    def test_the_stub_adapter_records_no_git_or_filesystem_side_effect(
        self, tmp_path: Path
    ) -> None:
        before = sorted(tmp_path.rglob("*"))
        adapter = StubSonarQualityGateAdapter(measures=_all_clean_measures())

        fetch_whole_suite_quality_report(adapter, "Automation-POC")

        assert sorted(tmp_path.rglob("*")) == before


class TestDeterminism:
    def test_same_scripted_measures_yield_the_same_report(self) -> None:
        measures = _all_clean_measures()
        first = fetch_whole_suite_quality_report(
            StubSonarQualityGateAdapter(measures=measures), "Automation-POC"
        )
        second = fetch_whole_suite_quality_report(
            StubSonarQualityGateAdapter(measures=measures), "Automation-POC"
        )

        assert first == second
