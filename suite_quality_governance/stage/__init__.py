"""Stage 16 -- Suite Quality Governance (ADR-0036, ADR-0046): CP5 wired as
a resumable run-state stage, mirroring stage 15's own package shape
(:mod:`automation_engineering.stage`).
"""

from __future__ import annotations

from suite_quality_governance.stage.models import (
    CONTRACT_VERSION,
    CP5_REPORT_FILENAME,
    SUITE_QUALITY_GOVERNANCE_REPORT_FILENAME,
    SuiteQualityGovernanceStageResult,
)
from suite_quality_governance.stage.runner import (
    STAGE_ID,
    execute_suite_quality_governance_stage,
    run_suite_quality_governance_stage,
)

__all__ = [
    "CONTRACT_VERSION",
    "CP5_REPORT_FILENAME",
    "STAGE_ID",
    "SUITE_QUALITY_GOVERNANCE_REPORT_FILENAME",
    "SuiteQualityGovernanceStageResult",
    "execute_suite_quality_governance_stage",
    "run_suite_quality_governance_stage",
]
