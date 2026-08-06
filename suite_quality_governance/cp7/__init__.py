"""CP7 -- whole-suite Sonar quality governance (ADR-0047 D1-D6).

Report-only at launch (ADR-0047 D3/D4/D5): reads the tracked baseline's own
accumulated Sonar measures and reports them, gates nothing yet.
"""

from __future__ import annotations

from suite_quality_governance.cp7.measures import fetch_whole_suite_quality_report
from suite_quality_governance.cp7.models import (
    ALL_CP7_METRICS,
    COVERAGE_AND_DUPLICATION_METRICS,
    GENERIC_QUALITY_METRICS,
    SECURITY_METRICS,
    Cp7MeasureFinding,
    Cp7WholeSuiteQualityReport,
)

__all__ = [
    "ALL_CP7_METRICS",
    "COVERAGE_AND_DUPLICATION_METRICS",
    "GENERIC_QUALITY_METRICS",
    "SECURITY_METRICS",
    "Cp7MeasureFinding",
    "Cp7WholeSuiteQualityReport",
    "fetch_whole_suite_quality_report",
]
