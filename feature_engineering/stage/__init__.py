"""Stage 14 -- Feature Engineering (ADR-0036, ADR-0043 D8).

Wraps the already-built generate -> CP2 -> D5 remediate unit
(`feature_engineering.generation`/`.cp2`/`.remediation`) as a resumable,
persisted run/stage-state stage. See `.runner` for the full design note.
"""

from __future__ import annotations

from feature_engineering.stage.models import (
    CONTRACT_VERSION,
    FEATURE_ENGINEERING_PACKAGE_FILENAME,
    FEATURE_ENGINEERING_REPORT_FILENAME,
    FeatureEngineeringPackage,
    FeatureEngineeringStageResult,
    FeatureRecord,
)
from feature_engineering.stage.runner import (
    STAGE_ID,
    execute_feature_engineering_stage,
    run_feature_engineering_stage,
)
from feature_engineering.stage.traceability import TRACEABILITY_FILENAME, build_traceability_index
from feature_engineering.stage.workspace import (
    DEFAULT_BASELINE_ROOT,
    FEATURES_SUBPATH,
    features_root_for,
    materialize_workspace,
)

__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_BASELINE_ROOT",
    "FEATURES_SUBPATH",
    "FEATURE_ENGINEERING_PACKAGE_FILENAME",
    "FEATURE_ENGINEERING_REPORT_FILENAME",
    "STAGE_ID",
    "TRACEABILITY_FILENAME",
    "FeatureEngineeringPackage",
    "FeatureEngineeringStageResult",
    "FeatureRecord",
    "build_traceability_index",
    "execute_feature_engineering_stage",
    "features_root_for",
    "materialize_workspace",
    "run_feature_engineering_stage",
]
