"""CP7 -- whole-suite Sonar quality governance (ADR-0047 D1-D6).

Reads the tracked baseline's own ALREADY-ACCUMULATED, server-side Sonar
project measures and reports them -- REPORT-ONLY (ADR-0047 D3/D4/D5), no
gating, no baseline mutation, no scan submission of its own. Distinct from
CP3's per-run quality gate (`automation_engineering.cp3.gate`), which
scans and gates a single run's own freshly-generated Java; CP7 governs
what the whole accumulated SUITE has become (ADR-0047 D1's own table:
"CP7 governs what the suite HAS BECOME, distinct from CP3's
per-generation-batch gate").

**Reuses the adapter Protocol's own new `fetch_measures` method
(ADR-0047 D6) -- builds no second mechanism.** This module is GLUE, the
same "sequences the calls, invents nothing new" posture stage 15's own
runner already establishes one layer down: every HTTP call, every
parsing decision, lives in `automation_engineering.cp3.sonar
.live_adapter.LiveSonarQualityGateAdapter`/`.stub_adapter
.StubSonarQualityGateAdapter`; this module only asks for the D3+D4+D5
metric keys, groups the response into CP7's own three named families, and
returns the report. It performs no HTTP call, no subprocess call, and no
filesystem write of any kind -- `fetch_whole_suite_quality_report`'s own
signature takes an already-constructed adapter and a project key, nothing
else.
"""

from __future__ import annotations

from automation_engineering.cp3.sonar.adapter import SonarQualityGateAdapter
from suite_quality_governance.cp7.models import (
    ALL_CP7_METRICS,
    COVERAGE_AND_DUPLICATION_METRICS,
    GENERIC_QUALITY_METRICS,
    SECURITY_METRICS,
    Cp7MeasureFinding,
    Cp7WholeSuiteQualityReport,
)


def fetch_whole_suite_quality_report(
    adapter: SonarQualityGateAdapter, project_key: str
) -> Cp7WholeSuiteQualityReport:
    """CP7's own capstone (ADR-0047 D1-D5). One `adapter.fetch_measures`
    call for the full D3+D4+D5 metric set, grouped into CP7's own three
    named families -- never one call per family. Read-only end to end: no
    scan is submitted, no file is written, no baseline is touched.
    """
    raw = adapter.fetch_measures(project_key, ALL_CP7_METRICS)
    value_by_key = {measure.metric_key: measure.value for measure in raw.measures}

    def _findings(metric_keys: tuple[str, ...]) -> tuple[Cp7MeasureFinding, ...]:
        return tuple(
            Cp7MeasureFinding(metric_key=key, value=value_by_key.get(key)) for key in metric_keys
        )

    return Cp7WholeSuiteQualityReport(
        project_key=project_key,
        generic_quality=_findings(GENERIC_QUALITY_METRICS),
        security=_findings(SECURITY_METRICS),
        coverage_and_duplication=_findings(COVERAGE_AND_DUPLICATION_METRICS),
    )


__all__ = ["fetch_whole_suite_quality_report"]
