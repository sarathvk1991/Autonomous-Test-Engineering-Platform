"""Canonical Data Model for the Requirement Intelligence Layer.

Re-exports the domain models and enums so callers can import from the package
root, e.g. ``from requirement_intelligence.models import SourceArtifact``.
"""

from __future__ import annotations

from requirement_intelligence.models.canonical_requirement import (
    CanonicalRequirement,
    SourceRef,
)
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import (
    RiskLevel,
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.parsed_response import (
    PARSED_RESPONSE_VERSION,
    ParsedResponse,
)
from requirement_intelligence.models.requirement_package import RequirementPackage
from requirement_intelligence.models.source_artifact import SourceArtifact

__all__ = [
    "PARSED_RESPONSE_VERSION",
    "CanonicalRequirement",
    "ConsolidatedArtifact",
    "ParsedResponse",
    "RequirementPackage",
    "RiskLevel",
    "SourceArtifact",
    "SourceCategory",
    "SourceRef",
    "SourceSystem",
    "SourceType",
]
