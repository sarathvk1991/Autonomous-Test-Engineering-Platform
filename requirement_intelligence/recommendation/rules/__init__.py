"""The governed :class:`RecommendationRuleCatalog` and its rules (CAP-082B)."""

from __future__ import annotations

from requirement_intelligence.recommendation.rules.recommendation_rule import (
    RECOMMENDATION_RULE_VERSION,
    RecommendationPolicyToggle,
    RecommendationRule,
    RecommendationRuleCategory,
)
from requirement_intelligence.recommendation.rules.recommendation_rule_builder import (
    RecommendationRuleBuilder,
    default_recommendation_rule_catalog,
)
from requirement_intelligence.recommendation.rules.recommendation_rule_catalog import (
    RECOMMENDATION_RULE_CATALOG_VERSION,
    RecommendationRuleCatalog,
)

__all__ = [
    "RECOMMENDATION_RULE_CATALOG_VERSION",
    "RECOMMENDATION_RULE_VERSION",
    "RecommendationPolicyToggle",
    "RecommendationRule",
    "RecommendationRuleBuilder",
    "RecommendationRuleCatalog",
    "RecommendationRuleCategory",
    "default_recommendation_rule_catalog",
]
