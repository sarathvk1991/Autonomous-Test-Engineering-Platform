"""Canonical, immutable models for the Continuous Improvement Framework."""

from __future__ import annotations

from requirement_intelligence.continuous_improvement.models.enums import (
    ImprovementFindingCategory,
    ImprovementOpportunityCategory,
    ImprovementSeverity,
    ImprovementSourceLayer,
    ImprovementTrendDirection,
)
from requirement_intelligence.continuous_improvement.models.finding import ImprovementFinding
from requirement_intelligence.continuous_improvement.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.continuous_improvement.models.opportunity import (
    ImprovementOpportunity,
)
from requirement_intelligence.continuous_improvement.models.result import (
    CONTINUOUS_IMPROVEMENT_RESULT_VERSION,
    ContinuousImprovementResult,
)
from requirement_intelligence.continuous_improvement.models.summary import (
    ImprovementMetrics,
    ImprovementSummary,
)
from requirement_intelligence.continuous_improvement.models.trend import ImprovementTrend

__all__ = [
    "CONTINUOUS_IMPROVEMENT_RESULT_VERSION",
    "ContinuousImprovementResult",
    "HistoricalDatasetReference",
    "ImprovementFinding",
    "ImprovementFindingCategory",
    "ImprovementMetrics",
    "ImprovementOpportunity",
    "ImprovementOpportunityCategory",
    "ImprovementSeverity",
    "ImprovementSourceLayer",
    "ImprovementSummary",
    "ImprovementTrend",
    "ImprovementTrendDirection",
]
