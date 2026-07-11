"""Canonical, immutable models for the Grounding Framework."""

from __future__ import annotations

from requirement_intelligence.grounding.models.assessment import (
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
    "MatchingContext",
    "MatchingEvidence",
    "MatchingRequest",
    "MatchingRequirement",
    "RequirementEvidenceLink",
    "SupportClassification",
    "SupportDistributionEntry",
]
