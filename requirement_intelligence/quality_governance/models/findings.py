"""The :class:`QualityFinding` — a surfaced governance problem.

A governance finding records that a governed :class:`QualityPolicy` rule is
violated by a completed upstream result. It is **not** a Grounding finding, a
Validation issue, or a CP1 finding — those live in and are owned by their own
subsystems (ADR-0017 Recommendation 1). This model carries information only; the
future decision engine mints findings, this model never derives one.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.models.enums import (
    QualityFindingCategory,
    QualityInputSource,
    QualitySeverity,
)
from shared.contracts.base import Schema


class QualityFinding(Schema):
    """A governance problem worth surfacing — a violated governed quality rule."""

    model_config = ConfigDict(alias_generator=to_camel)

    finding_id: str = Field(..., min_length=1, description="Identity of this finding.")
    category: QualityFindingCategory = Field(..., description="The kind of governance problem.")
    severity: QualitySeverity = Field(..., description="Governance severity of the finding.")
    source: QualityInputSource = Field(
        ..., description="Which consumed upstream result the governed rule judged."
    )
    message: str = Field(..., min_length=1, description="Human-readable description.")
