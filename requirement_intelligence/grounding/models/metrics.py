"""Grounding metrics models — data containers only.

This milestone builds the *shape* of the metrics, not the calculation. Rates are
constrained to ``[0.0, 1.0]`` and the score to ``[0, 100]`` so an invalid metrics
object cannot be constructed, but nothing here computes a value; a later milestone
supplies them.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.models.enums import SupportClassification
from shared.contracts.base import Schema


class SupportDistributionEntry(Schema):
    """The count of requirements assigned one support classification."""

    model_config = ConfigDict(alias_generator=to_camel)

    classification: SupportClassification = Field(..., description="The support classification.")
    count: int = Field(..., ge=0, description="Requirements in this classification.")


class GroundingMetrics(Schema):
    """The governed grounding metrics for one run.

    A pure data container: every field is supplied by the assembler. Ratios are
    fractions in ``[0, 1]``; ``grounding_score`` is a 0-100 roll-up.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    total_requirements: int = Field(..., ge=0)
    grounded_requirements: int = Field(..., ge=0)
    unsupported_requirements: int = Field(..., ge=0)

    grounding_coverage: float = Field(..., ge=0.0, le=1.0)
    evidence_coverage: float = Field(..., ge=0.0, le=1.0)
    requirement_coverage: float = Field(..., ge=0.0, le=1.0)
    evidence_utilization: float = Field(..., ge=0.0, le=1.0)
    traceability_completeness: float = Field(..., ge=0.0, le=1.0)

    average_confidence: float = Field(..., ge=0.0, le=100.0)
    cross_source_support: float = Field(..., ge=0.0, le=1.0)
    single_source_support: float = Field(..., ge=0.0, le=1.0)
    unsupported_rate: float = Field(..., ge=0.0, le=1.0)
    hallucination_rate: float = Field(..., ge=0.0, le=1.0)

    average_evidence_per_requirement: float = Field(..., ge=0.0)
    average_sources_per_requirement: float = Field(..., ge=0.0)
    evidence_reuse_ratio: float = Field(..., ge=0.0)

    grounding_score: int = Field(..., ge=0, le=100)

    support_distribution: tuple[SupportDistributionEntry, ...] = Field(
        default=(), description="Count of requirements per support classification."
    )
