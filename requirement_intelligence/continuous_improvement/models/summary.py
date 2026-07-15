"""The :class:`ImprovementSummary` and :class:`ImprovementMetrics` — the headline
projections for one Continuous Improvement run.

Both are pure aggregation models: **assembly targets only**. Every field is
supplied by a future assembler; nothing here is computed (mirroring
``RecommendationSummary`` / ``RecommendationMetrics``, ADR-0019).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.continuous_improvement.identity import (
    ImprovementPolicyId,
    ImprovementPolicyVersion,
)
from shared.contracts.base import Schema


class ImprovementSummary(Schema):
    """The governed headline for one Continuous Improvement run. A pure data container.

    ``headline`` is a one-line, deterministic description of the run's shape
    (e.g. counts), analogous to ``RecommendationSummary.headline`` — Continuous
    Improvement renders **no optimization plan**: it is observation only, and owns
    no plan or decision (Recommendation 3 of ADR-0022; that judgement belongs to
    Layer 5, Optimization).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: ImprovementPolicyId = Field(..., description="Governing policy identity.")
    policy_version: ImprovementPolicyVersion = Field(..., description="Governing policy version.")

    total_findings: int = Field(..., ge=0, description="Total findings recorded.")
    total_trends: int = Field(..., ge=0, description="Total trends recorded.")
    total_opportunities: int = Field(..., ge=0, description="Total opportunities recorded.")

    headline: str = Field(..., min_length=1, description="One-line deterministic run summary.")


class ImprovementMetrics(Schema):
    """Deterministic numeric roll-ups for one Continuous Improvement run. Data only.

    Every ratio is recorded, never computed by this model — a future metrics
    assembler derives them from the findings/trends/opportunities, exactly as
    ``RecommendationMetrics`` are recorded values, not model-internal
    calculations.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    finding_density: float = Field(
        ..., ge=0.0, description="Average findings per execution in the historical window."
    )
    trend_stability_ratio: float = Field(
        ..., ge=0.0, le=1.0, description="Fraction of trends observed as STABLE."
    )
    opportunity_rate: float = Field(
        ..., ge=0.0, description="Average opportunities per finding and trend recorded."
    )
