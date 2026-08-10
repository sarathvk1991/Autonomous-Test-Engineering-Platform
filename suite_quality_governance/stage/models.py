"""Structured contracts for stage 16's own persisted state (ADR-0036,
ADR-0046, ADR-0047).

Mirrors :mod:`automation_engineering.stage.models` deliberately -- one
report artifact per control point, plus a stage-result wrapper the run-state
wiring (:mod:`.runner`) persists, the same "per-need bookkeeping distinct
from the subsystem's own per-call outcome shapes" split stage 15's own
``AutomationEngineeringStageResult`` already establishes for stage 14's
``FeatureEngineeringPackage``.

Stage 16 is Layer 4's own one run-state stage (ADR-0036's own reservation) --
CP5, CP7, and CP8 all join it (ADR-0047's own "one Layer 4 stage, not new
stages" framing). CP5 produces exactly ONE verdict per invocation
(``Cp5PromotionWrapResult``, `suite_quality_governance.cp5.models`); CP8
mirrors that shape (``Cp8Result``, gates, ADR-0047 D9); CP7 is MIXED
(ADR-0047 D3's own amendment note, 2026-08-10): its whole-suite measures
report (``Cp7WholeSuiteQualityReport``) still carries no verdict at all --
wrapped here in ``Cp7ReportOutcome`` so its own "measures obtained, or
honestly unavailable" state has somewhere to live -- but its own two rating
metrics (``reliability_rating``/``sqale_rating``) now gate via a SEPARATE,
additive result, ``Cp7RatingGateResult`` (`suite_quality_governance.cp7
.models`/`.rating_gate`), composed into the stage's own ``overall_verdict``
alongside CP5/CP8 (`.runner`'s own module docstring). This module adds only
the persistence contract around all three: report filenames, a markdown
summary, and the stage-result wrapper
``execute_suite_quality_governance_stage`` returns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from shared.enums.base import ValidationVerdict
from suite_quality_governance.cp5.models import Cp5PromotionWrapResult
from suite_quality_governance.cp7.models import Cp7RatingGateResult, Cp7WholeSuiteQualityReport
from suite_quality_governance.cp8.models import Cp8Result

#: This package's own contract version -- independent of
#: `automation_engineering.stage.models.CONTRACT_VERSION` (stage 15's own,
#: separate contract) and `requirement_intelligence.run_state`'s own
#: run/stage state contract.
CONTRACT_VERSION = "1.0.0"

CP5_REPORT_FILENAME = "cp5_report.json"
CP7_REPORT_FILENAME = "cp7_report.json"
CP8_REPORT_FILENAME = "cp8_report.json"
SUITE_QUALITY_GOVERNANCE_REPORT_FILENAME = "suite_quality_governance_report.md"


@dataclass(frozen=True, slots=True)
class Cp7ReportOutcome:
    """CP7's own report-only outcome for one stage run (ADR-0047 D3):
    either the whole-suite quality report itself, or an honest
    "unavailable" state when the live Sonar fetch could not be completed at
    all -- no adapter configured for this stage run, or a genuine
    transport/scan failure. Carried ALONGSIDE the stage's own composed
    verdict, never inside it, because CP7 never gates (`.runner`'s own
    module docstring).

    Mirrors ``Cp7MeasureFinding.value=None``'s own "absent, never faked"
    discipline one level up: there, one metric may be unmeasured; here, the
    whole report may be unobtainable -- both are honest, distinct-from-
    measured states, never silently dropped or defaulted to "clean."
    """

    report: Cp7WholeSuiteQualityReport | None
    unavailable_reason: str | None

    @property
    def available(self) -> bool:
        return self.report is not None


@dataclass(frozen=True, slots=True)
class SuiteQualityGovernanceStageResult:
    """Everything the stage-16 wiring (`.runner.execute_suite_quality_governance_stage`)
    needs to record the stage's own run-state outcome.

    ``result`` is CP5's own, unchanged field (kept as-is, not renamed, so
    every existing CP5-wiring caller/test keeps working verbatim). ``overall_
    verdict`` is the STAGE's own composed verdict -- ``PASS`` iff CP5's
    ``result.overall_verdict`` AND CP8's ``cp8_result.overall_verdict`` are
    both ``PASS`` AND CP7's own ``cp7_rating_result.overall_verdict`` is not
    ``FAIL`` (ADR-0047 D8/D9 for CP5/CP8; D3's amendment note, 2026-08-10,
    for CP7's rating-gate half -- an unmeasured rating is ``WARN``, which
    composes as non-blocking, never as a stage failure). ``cp7_outcome``
    (the whole-suite measures report, or its own honest absence) remains
    entirely report-only and never itself enters this composition -- only
    ``cp7_rating_result``, computed FROM ``cp7_outcome.report``, does."""

    result: Cp5PromotionWrapResult
    cp8_result: Cp8Result
    cp7_outcome: Cp7ReportOutcome
    cp7_rating_result: Cp7RatingGateResult
    overall_verdict: ValidationVerdict
    cp5_report_path: Path
    cp8_report_path: Path
    cp7_report_path: Path
    report_path: Path

    @property
    def passed(self) -> bool:
        return self.overall_verdict == ValidationVerdict.PASS

    @property
    def all_output_paths(self) -> tuple[Path, ...]:
        return (
            self.cp5_report_path,
            self.cp8_report_path,
            self.cp7_report_path,
            self.report_path,
        )


__all__ = [
    "CONTRACT_VERSION",
    "CP5_REPORT_FILENAME",
    "CP7_REPORT_FILENAME",
    "CP8_REPORT_FILENAME",
    "SUITE_QUALITY_GOVERNANCE_REPORT_FILENAME",
    "Cp7ReportOutcome",
    "SuiteQualityGovernanceStageResult",
]
