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
)
from requirement_intelligence.grounding.models import (
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
    RequirementEvidenceLink,
    SupportClassification,
    SupportDistributionEntry,
)
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)

__all__ = [
    "GROUNDING_CONFIGURATION_VERSION",
    "GROUNDING_FRAMEWORK_VERSION",
    "ConfidenceBand",
    "ConfidenceComponent",
    "DefaultGroundingService",
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
    "RequirementEvidenceLink",
    "SupportClassification",
    "SupportDistributionEntry",
    "default_grounding_configuration",
]
