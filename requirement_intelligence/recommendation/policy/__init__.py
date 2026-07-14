"""The governed :class:`RecommendationPolicy` and its builder."""

from __future__ import annotations

from requirement_intelligence.recommendation.policy.recommendation_policy import (
    ConfidenceRules,
    GroupingRules,
    PrioritizationRules,
    ProjectionRules,
    RecommendationCapabilitySwitches,
    RecommendationPolicy,
)
from requirement_intelligence.recommendation.policy.recommendation_policy_builder import (
    DEFAULT_RECOMMENDATION_POLICY_ID,
    RecommendationPolicyBuilder,
    default_recommendation_policy,
)

__all__ = [
    "DEFAULT_RECOMMENDATION_POLICY_ID",
    "ConfidenceRules",
    "GroupingRules",
    "PrioritizationRules",
    "ProjectionRules",
    "RecommendationCapabilitySwitches",
    "RecommendationPolicy",
    "RecommendationPolicyBuilder",
    "default_recommendation_policy",
]
