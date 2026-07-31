"""SonarQube adapter seam for CP3's hard quality gate (ADR-0044 D5)."""

from __future__ import annotations

from automation_engineering.cp3.sonar.adapter import (
    SonarQualityGateAdapter,
    SonarScanError,
    run_quality_gate,
)
from automation_engineering.cp3.sonar.live_adapter import LiveSonarQualityGateAdapter
from automation_engineering.cp3.sonar.models import (
    SonarQualityGateCondition,
    SonarQualityGateResult,
)
from automation_engineering.cp3.sonar.stub_adapter import StubSonarQualityGateAdapter

__all__ = [
    "LiveSonarQualityGateAdapter",
    "SonarQualityGateAdapter",
    "SonarQualityGateCondition",
    "SonarQualityGateResult",
    "SonarScanError",
    "StubSonarQualityGateAdapter",
    "run_quality_gate",
]
