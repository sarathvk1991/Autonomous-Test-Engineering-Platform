"""Canonical, immutable models for the Recommendation Framework."""

from __future__ import annotations

from requirement_intelligence.recommendation.models.enums import (
    RecommendationEffort,
    RecommendationPriority,
    RecommendationSource,
    RecommendationType,
)
from requirement_intelligence.recommendation.models.group import RecommendationGroup
from requirement_intelligence.recommendation.models.recommendation import (
    Recommendation,
    RecommendationReference,
)
from requirement_intelligence.recommendation.models.result import (
    RECOMMENDATION_RESULT_VERSION,
    RecommendationInputReference,
    RecommendationResult,
)
from requirement_intelligence.recommendation.models.summary import (
    RecommendationMetrics,
    RecommendationPriorityCount,
    RecommendationSummary,
)

__all__ = [
    "RECOMMENDATION_RESULT_VERSION",
    "Recommendation",
    "RecommendationEffort",
    "RecommendationGroup",
    "RecommendationInputReference",
    "RecommendationMetrics",
    "RecommendationPriority",
    "RecommendationPriorityCount",
    "RecommendationReference",
    "RecommendationResult",
    "RecommendationSource",
    "RecommendationSummary",
    "RecommendationType",
]
