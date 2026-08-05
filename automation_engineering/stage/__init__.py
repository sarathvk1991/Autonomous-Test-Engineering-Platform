"""Stage 15 -- Automation Engineering (ADR-0036, ADR-0044): the orchestration
that chains Layer 3's six already-built, independently-tested subsystems
(catalog, reuse, generation, CP3, CP4, promotion) into one runnable,
resumable run-state stage, mirroring stage 14's own integration shape
(:mod:`feature_engineering.stage`).
"""

from __future__ import annotations

from automation_engineering.stage.models import (
    AssetRecord,
    AutomationEngineeringPackage,
    AutomationEngineeringStageResult,
)
from automation_engineering.stage.runner import (
    STAGE_ID,
    execute_automation_engineering_stage,
    run_automation_engineering_stage,
)

__all__ = [
    "STAGE_ID",
    "AssetRecord",
    "AutomationEngineeringPackage",
    "AutomationEngineeringStageResult",
    "execute_automation_engineering_stage",
    "run_automation_engineering_stage",
]
