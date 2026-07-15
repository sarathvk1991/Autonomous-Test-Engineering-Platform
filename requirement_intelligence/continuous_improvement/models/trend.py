"""The :class:`ImprovementTrend` — an observed direction across many executions.

An ``ImprovementTrend`` records an observed direction — improving, degrading,
stable, volatile — for one governed metric across the historical dataset.
**Observation only, never prediction**: it records what the historical data
already shows, never an estimate of what a future execution will show (that is
Layer 4's job — Prediction & Insights, ADR-0020).

No trend is computed here — a future engine (CAP-083B) populates this model from
a completed Historical Dataset; this milestone only shapes the contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.continuous_improvement.identity import (
    ImprovementTrendId,
)
from requirement_intelligence.continuous_improvement.models.enums import (
    ImprovementSourceLayer,
    ImprovementTrendDirection,
)
from shared.contracts.base import Schema


class ImprovementTrend(Schema):
    """One deterministic, historical observation of direction — data only.

    ``contributing_execution_ids`` names every execution the trend's data points
    were drawn from, by id only — never by embedding that execution's Runtime
    Truth, exactly mirroring :class:`~requirement_intelligence.
    continuous_improvement.models.finding.ImprovementFinding`.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    trend_id: ImprovementTrendId = Field(..., description="Deterministic identity of this trend.")
    direction: ImprovementTrendDirection = Field(..., description="The observed direction.")
    source: ImprovementSourceLayer = Field(
        ..., description="Which Layer 1 subsystem this trend concerns."
    )
    metric_name: str = Field(
        ...,
        min_length=1,
        description="The governed metric this trend observes (e.g. 'groundingScore').",
    )
    observation_count: int = Field(
        ..., ge=2, description="How many executions contributed a data point to this trend."
    )
    contributing_execution_ids: tuple[str, ...] = Field(
        default=(),
        description="The execution ids this trend's data points were drawn from (reference only).",
    )
    message: str = Field(..., min_length=1, description="Human-readable description.")

    @model_validator(mode="after")
    def _validate_trend(self) -> ImprovementTrend:
        """observation_count must match the number of contributing executions named."""
        if len(self.contributing_execution_ids) != self.observation_count:
            raise ValueError(
                f"ImprovementTrend {self.trend_id!r} has observation_count "
                f"{self.observation_count} but names {len(self.contributing_execution_ids)} "
                f"contributing execution id(s) — they must match."
            )
        if len(set(self.contributing_execution_ids)) != len(self.contributing_execution_ids):
            raise ValueError(
                f"ImprovementTrend {self.trend_id!r} must not name the same "
                f"contributing execution id twice."
            )
        return self
