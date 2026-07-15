"""The :class:`ImprovementFinding` — a recurring issue observed across many executions.

An ``ImprovementFinding`` represents a recurring issue — a repeated validation
failure, a repeated grounding contradiction, a repeated governance failure, a
repeated recommendation. It **never** represents something observed in one
execution (that is the corresponding Layer 1 subsystem's own finding/issue model —
``ValidationIssue``, ``GroundingFinding``, ``QualityFinding``, ``Recommendation``);
it is **always historical**, referencing by id the multiple executions the
recurrence was observed across (reference, never copy — the same discipline every
prior subsystem's finding model already applies, e.g. ``EnhancementFinding``
referencing a ``RequirementObservation``).

No finding is derived here — a future engine (CAP-083B) populates this model from
a completed Historical Dataset; this milestone only shapes the contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.continuous_improvement.identity import (
    ImprovementFindingId,
)
from requirement_intelligence.continuous_improvement.models.enums import (
    ImprovementFindingCategory,
    ImprovementSeverity,
    ImprovementSourceLayer,
)
from shared.contracts.base import Schema


class ImprovementFinding(Schema):
    """One deterministic, historical recurrence — data only, never one execution.

    ``contributing_execution_ids`` names every execution the recurrence was
    observed in, by id only — never by embedding that execution's Runtime Truth
    (Recommendation 6 of ADR-0022: explainable through Historical Dataset →
    Runtime Truth → Execution Inputs, without copying any of it here).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    finding_id: ImprovementFindingId = Field(
        ..., description="Deterministic identity of this finding."
    )
    category: ImprovementFindingCategory = Field(
        ..., description="The governed recurring pattern this finding names."
    )
    source: ImprovementSourceLayer = Field(
        ..., description="Which Layer 1 subsystem this recurrence concerns."
    )
    severity: ImprovementSeverity = Field(..., description="The finding's recorded severity.")
    occurrence_count: int = Field(
        ..., ge=1, description="How many executions this recurrence was observed in."
    )
    contributing_execution_ids: tuple[str, ...] = Field(
        default=(),
        description="The execution ids this recurrence was observed across (reference only).",
    )
    message: str = Field(..., min_length=1, description="Human-readable description.")

    @model_validator(mode="after")
    def _validate_finding(self) -> ImprovementFinding:
        """occurrence_count must match the number of contributing executions named."""
        if len(self.contributing_execution_ids) != self.occurrence_count:
            raise ValueError(
                f"ImprovementFinding {self.finding_id!r} has occurrence_count "
                f"{self.occurrence_count} but names {len(self.contributing_execution_ids)} "
                f"contributing execution id(s) — they must match."
            )
        if len(set(self.contributing_execution_ids)) != len(self.contributing_execution_ids):
            raise ValueError(
                f"ImprovementFinding {self.finding_id!r} must not name the same "
                f"contributing execution id twice."
            )
        return self
