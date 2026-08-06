"""Structured contracts for stage 16's own persisted state (ADR-0036,
ADR-0046).

Mirrors :mod:`automation_engineering.stage.models` deliberately -- one
report artifact per control point, plus a stage-result wrapper the run-state
wiring (:mod:`.runner`) persists, the same "per-need bookkeeping distinct
from the subsystem's own per-call outcome shapes" split stage 15's own
``AutomationEngineeringStageResult`` already establishes for stage 14's
``FeatureEngineeringPackage``.

Unlike stage 15 (one ``AssetRecord`` per need), CP5 produces exactly ONE
verdict per invocation -- ``Cp5PromotionWrapResult`` (`suite_quality_governance
.cp5.models`) already IS that record, composed from all three prior CP5
components. This module adds only the persistence contract around it: a
report filename, a markdown summary, and the stage-result wrapper
``execute_suite_quality_governance_stage`` returns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from suite_quality_governance.cp5.models import Cp5PromotionWrapResult

#: This package's own contract version -- independent of
#: `automation_engineering.stage.models.CONTRACT_VERSION` (stage 15's own,
#: separate contract) and `requirement_intelligence.run_state`'s own
#: run/stage state contract.
CONTRACT_VERSION = "1.0.0"

CP5_REPORT_FILENAME = "cp5_report.json"
SUITE_QUALITY_GOVERNANCE_REPORT_FILENAME = "suite_quality_governance_report.md"


@dataclass(frozen=True, slots=True)
class SuiteQualityGovernanceStageResult:
    """Everything the stage-16 wiring (`.runner.execute_suite_quality_governance_stage`)
    needs to record the stage's own run-state outcome."""

    result: Cp5PromotionWrapResult
    cp5_report_path: Path
    report_path: Path

    @property
    def all_output_paths(self) -> tuple[Path, ...]:
        return (self.cp5_report_path, self.report_path)


__all__ = [
    "CONTRACT_VERSION",
    "CP5_REPORT_FILENAME",
    "SUITE_QUALITY_GOVERNANCE_REPORT_FILENAME",
    "SuiteQualityGovernanceStageResult",
]
