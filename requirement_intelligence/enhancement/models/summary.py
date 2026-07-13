"""The :class:`EnhancementSummary` and :class:`EnhancementMetrics` — the headline
projections for one enhancement run.

Both are pure aggregation models: **assembly targets only**. Every field is supplied
by a future assembler; nothing here is computed (mirroring ``QualitySummary``,
ADR-0017's ``models/summary.py``).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.enhancement.identity.enhancement_identity import (
    EnhancementPolicyId,
    EnhancementPolicyVersion,
)
from requirement_intelligence.enhancement.models.enums import ObservationCategory
from shared.contracts.base import Schema


class ObservationCategoryCount(Schema):
    """The count of observations in one category — a distribution entry."""

    model_config = ConfigDict(alias_generator=to_camel)

    category: ObservationCategory = Field(..., description="The observation category.")
    count: int = Field(..., ge=0, description="Observations in this category.")


class EnhancementSummary(Schema):
    """The governed headline for one enhancement run. A pure data container.

    ``headline`` is a one-line, deterministic description of the run's shape (e.g.
    counts), analogous to ``QualitySummary.verdict`` — but Requirement Enhancement
    renders **no verdict**: it is non-gating, and owns no release decision
    (Recommendation 3; that judgement, if any, belongs to a downstream consumer such
    as Quality Governance).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: EnhancementPolicyId = Field(..., description="Governing policy identity.")
    policy_version: EnhancementPolicyVersion = Field(..., description="Governing policy version.")

    total_requirements_enhanced: int = Field(..., ge=0, description="Enriched requirement count.")
    total_relationships: int = Field(..., ge=0, description="Relationship-graph edge count.")
    total_observations: int = Field(..., ge=0, description="Total observations recorded.")
    total_findings: int = Field(..., ge=0, description="Total surfaced findings.")

    observation_distribution: tuple[ObservationCategoryCount, ...] = Field(
        default=(), description="Observation counts by category."
    )
    headline: str = Field(..., min_length=1, description="One-line deterministic run summary.")


class EnhancementMetrics(Schema):
    """Deterministic numeric roll-ups for one enhancement run. Data only.

    Every ratio is recorded, never computed by this model — a future metrics
    assembler derives them from the enhanced requirements and the relationship graph,
    exactly as ``GroundingMetrics`` and ``QualitySummary.overall_quality_score`` are
    recorded values, not model-internal calculations.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    enrichment_coverage: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of source requirements that were enriched."
    )
    relationship_density: float = Field(
        ..., ge=0.0, description="Average relationships per enriched requirement."
    )
    observation_rate: float = Field(
        ..., ge=0.0, description="Average observations per enriched requirement."
    )
