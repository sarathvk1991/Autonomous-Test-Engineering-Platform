"""The :class:`RecommendationSummary` and :class:`RecommendationMetrics` — the
headline projections for one recommendation run.

Both are pure aggregation models: **assembly targets only**. Every field is supplied
by a future assembler; nothing here is computed (mirroring ``EnhancementSummary`` /
``EnhancementMetrics``, ADR-0018, and ``QualitySummary``, ADR-0017).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.recommendation.identity.recommendation_identity import (
    RecommendationPolicyId,
    RecommendationPolicyVersion,
)
from requirement_intelligence.recommendation.models.enums import RecommendationPriority
from shared.contracts.base import Schema


class RecommendationPriorityCount(Schema):
    """The count of recommendations at one priority — a distribution entry."""

    model_config = ConfigDict(alias_generator=to_camel)

    priority: RecommendationPriority = Field(..., description="The recommendation priority.")
    count: int = Field(..., ge=0, description="Recommendations at this priority.")


class RecommendationSummary(Schema):
    """The governed headline for one recommendation run. A pure data container.

    ``headline`` is a one-line, deterministic description of the run's shape (e.g.
    counts), analogous to ``EnhancementSummary.headline`` — the Recommendation
    Framework renders **no release verdict**: it is non-gating, and owns no release
    decision (Recommendation 1; that judgement belongs to Quality Governance alone).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: RecommendationPolicyId = Field(..., description="Governing policy identity.")
    policy_version: RecommendationPolicyVersion = Field(
        ..., description="Governing policy version."
    )

    total_recommendations: int = Field(..., ge=0, description="Total recommendations recorded.")
    total_groups: int = Field(..., ge=0, description="Total recommendation groups recorded.")

    priority_distribution: tuple[RecommendationPriorityCount, ...] = Field(
        default=(), description="Recommendation counts by priority."
    )
    headline: str = Field(..., min_length=1, description="One-line deterministic run summary.")


class RecommendationMetrics(Schema):
    """Deterministic numeric roll-ups for one recommendation run. Data only.

    Every ratio is recorded, never computed by this model — a future metrics
    assembler derives them from the recommendations and groups, exactly as
    ``EnhancementMetrics`` and ``GroundingMetrics`` are recorded values, not
    model-internal calculations.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    recommendation_density: float = Field(
        ..., ge=0.0, description="Average recommendations per group."
    )
    average_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Average recorded confidence across recommendations."
    )
    high_priority_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of recommendations at HIGH or CRITICAL priority."
    )
