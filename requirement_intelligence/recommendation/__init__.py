"""Recommendation Framework (CAP-082A).

The governed subsystem that will own deterministic-first recommendation generation
over the completed judgements of the Requirement Intelligence pipeline — Requirement
Enhancement, Grounding, Validation, CP1, and Quality Governance — produced **after**
all five of those subsystems have rendered their verdicts. It is a **consumer only**
of their five completed runtime contracts and owns none of Requirement Enhancement,
Grounding, Validation, CP1, Quality Governance, or the Execution Package upstream or
downstream of it (ADR-0019).

**Runtime status (CAP-082A):** architecture and governance freeze only. No
recommendation is generated, no heuristic runs, no scoring is performed, and nothing
is wired into a runtime path. ``DormantRecommendationService`` raises
``NotImplementedError`` on every call. The subsystem is not wired into the
Requirement Intelligence execution pipeline — nothing calls ``recommend`` at
runtime — so runtime behaviour is byte-identical and the golden baseline is
unchanged. Governed by ADR-0019.
"""

from __future__ import annotations

from requirement_intelligence.recommendation.identity import (
    RecommendationFrameworkVersion,
    RecommendationGroupId,
    RecommendationId,
    RecommendationPolicyId,
    RecommendationPolicyVersion,
    RecommendationResultId,
    RecommendationResultVersion,
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
    DormantRecommendationService,
    RecommendationService,
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
    "ConfidenceRules",
    "DormantRecommendationService",
    "GroupingRules",
    "PrioritizationRules",
    "ProjectionRules",
    "Recommendation",
    "RecommendationCapabilitySwitches",
    "RecommendationEffort",
    "RecommendationFrameworkVersion",
    "RecommendationGroup",
    "RecommendationGroupId",
    "RecommendationId",
    "RecommendationInputReference",
    "RecommendationMetrics",
    "RecommendationPolicy",
    "RecommendationPolicyBuilder",
    "RecommendationPolicyId",
    "RecommendationPolicyVersion",
    "RecommendationPriority",
    "RecommendationPriorityCount",
    "RecommendationReference",
    "RecommendationResult",
    "RecommendationResultId",
    "RecommendationResultVersion",
    "RecommendationService",
    "RecommendationSource",
    "RecommendationSummary",
    "RecommendationType",
    "RecommendationVersion",
    "default_recommendation_policy",
]
