"""Requirement Intelligence Enhancement Framework (CAP-081).

The governed subsystem that will own deterministic intelligence over generated
requirements — enrichment, relationships, and observations — produced **before**
downstream consumers (Grounding, Validation, CP1, and Quality Governance) consume
them. It is a **consumer only** of the two completed upstream inputs —
``EngineeringContext`` and ``AnalysisResult`` — and owns none of Engineering Context
Orchestration, Analysis, Grounding, Validation, CP1, Quality Governance, or the
Execution Package upstream or downstream of it (ADR-0018).

**Runtime status (CAP-081A):** architecture freeze only. Canonical models, typed
identities, independent version axes, the governed ``EnhancementPolicy`` and its
builder, and the dormant ``RequirementEnhancementService`` contract are frozen. No
enrichment, relationship detection, observation generation, consistency analysis,
completeness analysis, graph construction, recommendation, or runtime wiring exists
yet. The subsystem is **not wired into the Requirement Intelligence execution
pipeline** — nothing calls ``enhance`` at runtime — so runtime behaviour is
byte-identical and the golden baseline is unchanged. Governed by ADR-0018.
"""

from __future__ import annotations

from requirement_intelligence.enhancement.identity import (
    EnhancedRequirementId,
    EnhancementFrameworkVersion,
    EnhancementPolicyId,
    EnhancementPolicyVersion,
    EnhancementResultVersion,
    ObservationVersion,
    RelationshipGraphId,
    RelationshipVersion,
    RequirementEnhancementId,
    RequirementEnhancementResultId,
    RequirementObservationId,
)
from requirement_intelligence.enhancement.models import (
    ENHANCEMENT_RESULT_VERSION,
    EnhancedRequirement,
    EnhancementAttribute,
    EnhancementFinding,
    EnhancementInputReference,
    EnhancementInputSource,
    EnhancementMetrics,
    EnhancementSeverity,
    EnhancementSummary,
    ObservationCategory,
    ObservationCategoryCount,
    RelationshipGraph,
    RelationshipType,
    RequirementEnhancementResult,
    RequirementObservation,
    RequirementRelationship,
)
from requirement_intelligence.enhancement.policy import (
    DEFAULT_ENHANCEMENT_POLICY_ID,
    EnhancementCapabilitySwitches,
    EnhancementPolicy,
    EnhancementPolicyBuilder,
    EnrichmentRules,
    ObservationRules,
    RelationshipRules,
    default_enhancement_policy,
)
from requirement_intelligence.enhancement.requirement_enhancement_service import (
    DormantRequirementEnhancementService,
    RequirementEnhancementService,
)
from requirement_intelligence.enhancement.version import (
    ENHANCEMENT_FRAMEWORK_VERSION,
    ENHANCEMENT_POLICY_VERSION,
)

__all__ = [
    "DEFAULT_ENHANCEMENT_POLICY_ID",
    "ENHANCEMENT_FRAMEWORK_VERSION",
    "ENHANCEMENT_POLICY_VERSION",
    "ENHANCEMENT_RESULT_VERSION",
    "DormantRequirementEnhancementService",
    "EnhancedRequirement",
    "EnhancedRequirementId",
    "EnhancementAttribute",
    "EnhancementCapabilitySwitches",
    "EnhancementFinding",
    "EnhancementFrameworkVersion",
    "EnhancementInputReference",
    "EnhancementInputSource",
    "EnhancementMetrics",
    "EnhancementPolicy",
    "EnhancementPolicyBuilder",
    "EnhancementPolicyId",
    "EnhancementPolicyVersion",
    "EnhancementResultVersion",
    "EnhancementSeverity",
    "EnhancementSummary",
    "EnrichmentRules",
    "ObservationCategory",
    "ObservationCategoryCount",
    "ObservationRules",
    "ObservationVersion",
    "RelationshipGraph",
    "RelationshipGraphId",
    "RelationshipRules",
    "RelationshipType",
    "RelationshipVersion",
    "RequirementEnhancementId",
    "RequirementEnhancementResult",
    "RequirementEnhancementResultId",
    "RequirementEnhancementService",
    "RequirementObservation",
    "RequirementObservationId",
    "RequirementRelationship",
    "default_enhancement_policy",
]
