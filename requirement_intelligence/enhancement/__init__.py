"""Requirement Intelligence Enhancement Framework (CAP-081).

The governed subsystem that owns deterministic intelligence over generated
requirements — enrichment, relationships, and observations — produced **before**
downstream consumers (Grounding, Validation, CP1, and Quality Governance) consume
them. It is a **consumer only** of the two completed upstream inputs —
``EngineeringContext`` and ``AnalysisResult`` — and owns none of Engineering Context
Orchestration, Analysis, Grounding, Validation, CP1, Quality Governance, or the
Execution Package upstream or downstream of it (ADR-0018).

**Runtime status (CAP-081B):** the first deterministic implementation.
``DeterministicRequirementEnhancementService`` delegates to
``DeterministicRequirementEnhancementEngine``, which performs deterministic
enrichment, relationship construction (Recommendation 6's canonical
``RelationshipGraph``), observation generation, findings, metrics, and summary end to
end — behind the CAP-081A frozen contracts, with no architectural change. The governed
``EnhancementRuleCatalog`` (CAP-081B) declares the deterministic mechanisms the engine
applies. The subsystem is still **not wired into the Requirement Intelligence
execution pipeline** — nothing calls ``enhance`` at runtime — so runtime behaviour is
byte-identical and the golden baseline is unchanged. Governed by ADR-0018.
"""

from __future__ import annotations

from requirement_intelligence.enhancement.engine import (
    DeterministicRequirementEnhancementEngine,
    RequirementExtractionError,
)
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
    DeterministicRequirementEnhancementService,
    RequirementEnhancementService,
)
from requirement_intelligence.enhancement.rules import (
    ENHANCEMENT_RULE_CATALOG_VERSION,
    ENHANCEMENT_RULE_VERSION,
    EnhancementCapabilityToggle,
    EnhancementMechanism,
    EnhancementPolicyRef,
    EnhancementRule,
    EnhancementRuleBuilder,
    EnhancementRuleCatalog,
    EnhancementRuleCategory,
    default_enhancement_rule_catalog,
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
    "ENHANCEMENT_RULE_CATALOG_VERSION",
    "ENHANCEMENT_RULE_VERSION",
    "DeterministicRequirementEnhancementEngine",
    "DeterministicRequirementEnhancementService",
    "EnhancedRequirement",
    "EnhancedRequirementId",
    "EnhancementAttribute",
    "EnhancementCapabilitySwitches",
    "EnhancementCapabilityToggle",
    "EnhancementFinding",
    "EnhancementFrameworkVersion",
    "EnhancementInputReference",
    "EnhancementInputSource",
    "EnhancementMechanism",
    "EnhancementMetrics",
    "EnhancementPolicy",
    "EnhancementPolicyBuilder",
    "EnhancementPolicyId",
    "EnhancementPolicyRef",
    "EnhancementPolicyVersion",
    "EnhancementResultVersion",
    "EnhancementRule",
    "EnhancementRuleBuilder",
    "EnhancementRuleCatalog",
    "EnhancementRuleCategory",
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
    "RequirementExtractionError",
    "RequirementObservation",
    "RequirementObservationId",
    "RequirementRelationship",
    "default_enhancement_policy",
    "default_enhancement_rule_catalog",
]
