"""Canonical, immutable models for the Grounding Framework."""

from __future__ import annotations

from requirement_intelligence.grounding.models.assessment import (
    GROUNDING_RESULT_VERSION,
    GroundingAssessment,
    GroundingResult,
    GroundingSummary,
)
from requirement_intelligence.grounding.models.confidence import (
    ConfidenceComponent,
    GroundingConfidence,
)
from requirement_intelligence.grounding.models.enums import (
    ConfidenceBand,
    EvidenceRelation,
    GroundingSeverity,
    SupportClassification,
)
from requirement_intelligence.grounding.models.evidence import (
    EvidenceReference,
    RequirementEvidenceLink,
)
from requirement_intelligence.grounding.models.explanation import GroundingExplanation
from requirement_intelligence.grounding.models.findings import GroundingFinding
from requirement_intelligence.grounding.models.grounded_requirement import GroundedRequirement
from requirement_intelligence.grounding.models.match_result import (
    MATCH_RESULT_VERSION,
    MatchEvaluationSummary,
    MatchExplanation,
    MatchResult,
    MatchStatistics,
)
from requirement_intelligence.grounding.models.matching import (
    MatchingContext,
    MatchingEvidence,
    MatchingRequest,
    MatchingRequirement,
)
from requirement_intelligence.grounding.models.metrics import (
    GroundingMetrics,
    SupportDistributionEntry,
)

__all__ = [
    "GROUNDING_RESULT_VERSION",
    "MATCH_RESULT_VERSION",
    "ConfidenceBand",
    "ConfidenceComponent",
    "EvidenceReference",
    "EvidenceRelation",
    "GroundedRequirement",
    "GroundingAssessment",
    "GroundingConfidence",
    "GroundingExplanation",
    "GroundingFinding",
    "GroundingMetrics",
    "GroundingResult",
    "GroundingSeverity",
    "GroundingSummary",
    "MatchEvaluationSummary",
    "MatchExplanation",
    "MatchResult",
    "MatchStatistics",
    "MatchingContext",
    "MatchingEvidence",
    "MatchingRequest",
    "MatchingRequirement",
    "RequirementEvidenceLink",
    "SupportClassification",
    "SupportDistributionEntry",
]
