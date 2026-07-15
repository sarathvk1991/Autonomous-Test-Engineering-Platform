"""Recommendation Framework (CAP-082A architecture; CAP-082B deterministic engine).

The governed subsystem that owns deterministic-first recommendation generation over
the completed judgements of the Requirement Intelligence pipeline — Requirement
Enhancement, Grounding, Validation, CP1, and Quality Governance — produced **after**
all five of those subsystems have rendered their verdicts. It is a **consumer only**
of their five completed runtime contracts and owns none of Requirement Enhancement,
Grounding, Validation, CP1, Quality Governance, or the Execution Package upstream or
downstream of it (ADR-0019).

**Runtime status (CAP-082B):** ``DeterministicRecommendationEngine`` generates
recommendations, prioritizes, groups, scores confidence, and assembles metrics/summary
entirely from the governed ``RecommendationRuleCatalog`` and ``RecommendationPolicy`` —
deterministic, no AI, no heuristics beyond governed data. The subsystem is still **not
wired into** the Requirement Intelligence execution pipeline — nothing calls
``recommend`` at runtime — so runtime behaviour is byte-identical and the golden
baseline is unchanged. Governed by ADR-0019.
"""

from __future__ import annotations

from requirement_intelligence.recommendation.engine import DeterministicRecommendationEngine
from requirement_intelligence.recommendation.identity import (
    RecommendationEngineVersion,
    RecommendationFrameworkVersion,
    RecommendationGroupId,
    RecommendationId,
    RecommendationPolicyId,
    RecommendationPolicyVersion,
    RecommendationResultId,
    RecommendationResultVersion,
    RecommendationRuleCatalogVersion,
    RecommendationRuleVersion,
    RecommendationVersion,
)
from requirement_intelligence.recommendation.models import (
    RECOMMENDATION_RESULT_VERSION,
    Recommendation,
    RecommendationEffort,
    RecommendationGroup,
    RecommendationInputReference,
    RecommendationMetrics,
    RecommendationPriority,
    RecommendationPriorityCount,
    RecommendationReference,
    RecommendationResult,
    RecommendationSource,
    RecommendationSummary,
    RecommendationType,
)
from requirement_intelligence.recommendation.policy import (
    DEFAULT_RECOMMENDATION_POLICY_ID,
    ConfidenceRules,
    GroupingRules,
    PrioritizationRules,
    ProjectionRules,
    RecommendationCapabilitySwitches,
    RecommendationPolicy,
    RecommendationPolicyBuilder,
    default_recommendation_policy,
)
from requirement_intelligence.recommendation.recommendation_service import (
    DeterministicRecommendationService,
    RecommendationService,
)
from requirement_intelligence.recommendation.rules import (
    RECOMMENDATION_RULE_CATALOG_VERSION,
    RECOMMENDATION_RULE_VERSION,
    RecommendationPolicyToggle,
    RecommendationRule,
    RecommendationRuleBuilder,
    RecommendationRuleCatalog,
    RecommendationRuleCategory,
    default_recommendation_rule_catalog,
)
from requirement_intelligence.recommendation.version import (
    RECOMMENDATION_FRAMEWORK_VERSION,
    RECOMMENDATION_POLICY_VERSION,
)

__all__ = [
    "DEFAULT_RECOMMENDATION_POLICY_ID",
    "RECOMMENDATION_FRAMEWORK_VERSION",
    "RECOMMENDATION_POLICY_VERSION",
    "RECOMMENDATION_RESULT_VERSION",
    "RECOMMENDATION_RULE_CATALOG_VERSION",
    "RECOMMENDATION_RULE_VERSION",
    "ConfidenceRules",
    "DeterministicRecommendationEngine",
    "DeterministicRecommendationService",
    "GroupingRules",
    "PrioritizationRules",
    "ProjectionRules",
    "Recommendation",
    "RecommendationCapabilitySwitches",
    "RecommendationEffort",
    "RecommendationEngineVersion",
    "RecommendationFrameworkVersion",
    "RecommendationGroup",
    "RecommendationGroupId",
    "RecommendationId",
    "RecommendationInputReference",
    "RecommendationMetrics",
    "RecommendationPolicy",
    "RecommendationPolicyBuilder",
    "RecommendationPolicyId",
    "RecommendationPolicyToggle",
    "RecommendationPolicyVersion",
    "RecommendationPriority",
    "RecommendationPriorityCount",
    "RecommendationReference",
    "RecommendationResult",
    "RecommendationResultId",
    "RecommendationResultVersion",
    "RecommendationRule",
    "RecommendationRuleBuilder",
    "RecommendationRuleCatalog",
    "RecommendationRuleCatalogVersion",
    "RecommendationRuleCategory",
    "RecommendationRuleVersion",
    "RecommendationService",
    "RecommendationSource",
    "RecommendationSummary",
    "RecommendationType",
    "RecommendationVersion",
    "default_recommendation_policy",
    "default_recommendation_rule_catalog",
]
