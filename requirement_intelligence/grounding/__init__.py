"""Evidence Grounding & Traceability Framework (CAP-077).

The governed subsystem that owns requirement-to-evidence traceability, support
classification, confidence, explainability, and grounding metrics.

**CAP-077A is the foundation only:** canonical models, typed identities,
enumerations, construction-only builders, a versioned configuration container,
and the ``GroundingStrategy`` contract. It performs no matching, no confidence
scoring, no classification, and no runtime wiring. Governed by ADR-0016.
"""

from __future__ import annotations

from requirement_intelligence.grounding.builders import (
    GroundedRequirementBuilder,
    GroundingAssessmentBuilder,
    GroundingResultBuilder,
    MatchingContextBuilder,
    MatchingContextConstructionError,
)
from requirement_intelligence.grounding.config import (
    GroundingConfiguration,
    default_grounding_configuration,
)
from requirement_intelligence.grounding.contracts import GroundingStrategy
from requirement_intelligence.grounding.grounding_service import (
    DefaultGroundingService,
    GroundingService,
)
from requirement_intelligence.grounding.identity import (
    GroundedRequirementId,
    GroundingAssessmentId,
    GroundingConfigurationVersion,
    GroundingFrameworkVersion,
    MatchingNormalizationVersion,
    MatchingPolicyId,
    MatchingPolicyVersion,
    MatchingStrategyVersion,
    MatchResultVersion,
)
from requirement_intelligence.grounding.matching import (
    MATCHING_POLICY_VERSION,
    MatchingPolicy,
    MatchingPolicyBuilder,
    MatchingRanking,
    MatchingThresholds,
    MatchingTieBreaker,
    MatchingWeights,
    default_matching_policy,
)
from requirement_intelligence.grounding.models import (
    MATCH_RESULT_VERSION,
    ConfidenceBand,
    ConfidenceComponent,
    EvidenceReference,
    EvidenceRelation,
    GroundedRequirement,
    GroundingAssessment,
    GroundingConfidence,
    GroundingExplanation,
    GroundingFinding,
    GroundingMetrics,
    GroundingResult,
    GroundingSeverity,
    GroundingSummary,
    MatchEvaluationSummary,
    MatchExplanation,
    MatchingContext,
    MatchingEvidence,
    MatchingRequest,
    MatchingRequirement,
    MatchResult,
    MatchStatistics,
    RequirementEvidenceLink,
    SupportClassification,
    SupportDistributionEntry,
)
from requirement_intelligence.grounding.normalization import (
    MATCHING_NORMALIZATION_VERSION,
    DefaultMatchingNormalizer,
    MatchingNormalizer,
    NormalizationConfiguration,
    NormalizationStatistics,
    NormalizedText,
    NormalizedToken,
    default_normalization_configuration,
)
from requirement_intelligence.grounding.strategies import DeterministicTextMatchingStrategy
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)

__all__ = [
    "GROUNDING_CONFIGURATION_VERSION",
    "GROUNDING_FRAMEWORK_VERSION",
    "MATCHING_NORMALIZATION_VERSION",
    "MATCHING_POLICY_VERSION",
    "MATCH_RESULT_VERSION",
    "ConfidenceBand",
    "ConfidenceComponent",
    "DefaultGroundingService",
    "DefaultMatchingNormalizer",
    "DeterministicTextMatchingStrategy",
    "EvidenceReference",
    "EvidenceRelation",
    "GroundedRequirement",
    "GroundedRequirementBuilder",
    "GroundedRequirementId",
    "GroundingAssessment",
    "GroundingAssessmentBuilder",
    "GroundingAssessmentId",
    "GroundingConfidence",
    "GroundingConfiguration",
    "GroundingConfigurationVersion",
    "GroundingExplanation",
    "GroundingFinding",
    "GroundingFrameworkVersion",
    "GroundingMetrics",
    "GroundingResult",
    "GroundingResultBuilder",
    "GroundingService",
    "GroundingSeverity",
    "GroundingStrategy",
    "GroundingSummary",
    "MatchEvaluationSummary",
    "MatchExplanation",
    "MatchResult",
    "MatchResultVersion",
    "MatchStatistics",
    "MatchingContext",
    "MatchingContextBuilder",
    "MatchingContextConstructionError",
    "MatchingEvidence",
    "MatchingNormalizationVersion",
    "MatchingNormalizer",
    "MatchingPolicy",
    "MatchingPolicyBuilder",
    "MatchingPolicyId",
    "MatchingPolicyVersion",
    "MatchingRanking",
    "MatchingRequest",
    "MatchingRequirement",
    "MatchingStrategyVersion",
    "MatchingThresholds",
    "MatchingTieBreaker",
    "MatchingWeights",
    "NormalizationConfiguration",
    "NormalizationStatistics",
    "NormalizedText",
    "NormalizedToken",
    "RequirementEvidenceLink",
    "SupportClassification",
    "SupportDistributionEntry",
    "default_grounding_configuration",
    "default_matching_policy",
    "default_normalization_configuration",
]
