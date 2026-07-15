"""The :class:`ImprovementOpportunity` — what should receive attention. Never
what the optimal plan is.

An ``ImprovementOpportunity`` names a deterministic opportunity derived from one
or more :class:`~requirement_intelligence.continuous_improvement.models.finding.
ImprovementFinding` / :class:`~requirement_intelligence.continuous_improvement.
models.trend.ImprovementTrend` entries — a recurring documentation gap, a
recurring architecture weakness, a recurring quality issue, a recurring
recommendation category. **Observation only**: it describes *what should receive
attention*, never *the optimal plan* (Recommendation 3 of ADR-0022) — choosing the
plan is Layer 5's job (Optimization, ADR-0020).

No opportunity is generated here — a future engine (CAP-083B) populates this model
by reference from already-recorded findings/trends; this milestone only shapes
the contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.continuous_improvement.identity import (
    ImprovementFindingId,
    ImprovementOpportunityId,
    ImprovementTrendId,
)
from requirement_intelligence.continuous_improvement.models.enums import (
    ImprovementOpportunityCategory,
)
from shared.contracts.base import Schema


class ImprovementOpportunity(Schema):
    """One deterministic, historical opportunity — data only, never an optimization.

    References the findings and/or trends it was derived from by id only — never
    by copying their content (Recommendation 6 of ADR-0022: explainable through
    Historical Dataset → Runtime Truth → Execution Inputs).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    opportunity_id: ImprovementOpportunityId = Field(
        ..., description="Deterministic identity of this opportunity."
    )
    category: ImprovementOpportunityCategory = Field(
        ..., description="The governed recurring pattern this opportunity names."
    )
    source_finding_ids: tuple[ImprovementFindingId, ...] = Field(
        default=(), description="The findings this opportunity was derived from (reference only)."
    )
    source_trend_ids: tuple[ImprovementTrendId, ...] = Field(
        default=(), description="The trends this opportunity was derived from (reference only)."
    )
    occurrence_count: int = Field(
        ..., ge=1, description="How many times the underlying pattern recurred."
    )
    description: str = Field(..., min_length=1, description="What should receive attention.")

    @model_validator(mode="after")
    def _validate_opportunity(self) -> ImprovementOpportunity:
        """An opportunity must be explainable from at least one finding or trend."""
        if not self.source_finding_ids and not self.source_trend_ids:
            raise ValueError(
                f"ImprovementOpportunity {self.opportunity_id!r} must reference at least one "
                f"finding or trend — an opportunity with no traceable evidence is not "
                f"explainable."
            )
        return self
