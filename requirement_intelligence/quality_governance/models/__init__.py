"""Canonical, immutable models for the Quality Governance Framework."""

from __future__ import annotations

from requirement_intelligence.quality_governance.models.assessment import (
    QUALITY_ASSESSMENT_VERSION,
    QualityAssessment,
)
from requirement_intelligence.quality_governance.models.enums import (
    DECISION_AFFECTING_SEVERITIES,
    QualityDecision,
    QualityFindingCategory,
    QualityInputSource,
    QualitySeverity,
)
from requirement_intelligence.quality_governance.models.findings import QualityFinding
from requirement_intelligence.quality_governance.models.result import (
    QUALITY_GOVERNANCE_RESULT_VERSION,
    ConsumedResultReference,
    QualityGovernanceResult,
)
from requirement_intelligence.quality_governance.models.summary import (
    QualityFindingCategoryCount,
    QualitySummary,
)

__all__ = [
    "DECISION_AFFECTING_SEVERITIES",
    "QUALITY_ASSESSMENT_VERSION",
    "QUALITY_GOVERNANCE_RESULT_VERSION",
    "ConsumedResultReference",
    "QualityAssessment",
    "QualityDecision",
    "QualityFinding",
    "QualityFindingCategory",
    "QualityFindingCategoryCount",
    "QualityGovernanceResult",
    "QualityInputSource",
    "QualitySeverity",
    "QualitySummary",
]
