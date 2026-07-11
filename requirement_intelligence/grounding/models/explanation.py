"""Structured grounding explanation model.

The explanation is **data, not pre-rendered prose**, so a report, a dashboard
tile, and an API field can each render the same canonical source, and so the
fields can be asserted in tests. It is assembled from a requirement's links and
confidence components; no explanation logic lives here (construction only).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.models.confidence import ConfidenceComponent
from requirement_intelligence.grounding.models.evidence import EvidenceReference
from shared.contracts.base import Schema


class GroundingExplanation(Schema):
    """The structured "why" behind one grounded requirement."""

    model_config = ConfigDict(alias_generator=to_camel)

    summary: str = Field(..., min_length=1, description="One-line, classification-aware summary.")
    supporting_evidence: tuple[EvidenceReference, ...] = Field(
        default=(), description="Evidence that supports the requirement."
    )
    missing_evidence: tuple[str, ...] = Field(
        default=(), description="What was expected but not found, or the unmatched qualifier."
    )
    conflicting_evidence: tuple[EvidenceReference, ...] = Field(
        default=(), description="Evidence that argues against the requirement."
    )
    confidence_breakdown: tuple[ConfidenceComponent, ...] = Field(
        default=(), description="The signed confidence contributions, for display."
    )
    recommendations: tuple[str, ...] = Field(
        default=(), description="Suggested next actions (e.g. accept, corroborate, quarantine)."
    )
