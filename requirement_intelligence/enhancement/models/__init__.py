"""Canonical, immutable models for the Requirement Intelligence Enhancement Framework."""

from __future__ import annotations

from requirement_intelligence.enhancement.models.enums import (
    EnhancementInputSource,
    EnhancementSeverity,
    ObservationCategory,
    RelationshipType,
)
from requirement_intelligence.enhancement.models.observations import (
    EnhancementFinding,
    RequirementObservation,
)
from requirement_intelligence.enhancement.models.relationships import (
    RelationshipGraph,
    RequirementRelationship,
)
from requirement_intelligence.enhancement.models.requirements import (
    EnhancedRequirement,
    EnhancementAttribute,
)
from requirement_intelligence.enhancement.models.result import (
    ENHANCEMENT_RESULT_VERSION,
    EnhancementInputReference,
    RequirementEnhancementResult,
)
from requirement_intelligence.enhancement.models.summary import (
    EnhancementMetrics,
    EnhancementSummary,
    ObservationCategoryCount,
)

__all__ = [
    "ENHANCEMENT_RESULT_VERSION",
    "EnhancedRequirement",
    "EnhancementAttribute",
    "EnhancementFinding",
    "EnhancementInputReference",
    "EnhancementInputSource",
    "EnhancementMetrics",
    "EnhancementSeverity",
    "EnhancementSummary",
    "ObservationCategory",
    "ObservationCategoryCount",
    "RelationshipGraph",
    "RelationshipType",
    "RequirementEnhancementResult",
    "RequirementObservation",
    "RequirementRelationship",
]
