"""The :class:`QualitySummary` — the human-facing headline for one governance run.

A canonical aggregation model: the decision, the governing policy, and the
statistics/distributions a report or dashboard renders. It is an **assembly target
only** — every field is supplied by the future assembler; nothing here is computed.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityPolicyId,
    QualityPolicyVersion,
)
from requirement_intelligence.quality_governance.models.enums import (
    QualityDecision,
    QualityFindingCategory,
)
from shared.contracts.base import Schema


class QualityFindingCategoryCount(Schema):
    """The count of governance findings in one category — a distribution entry."""

    model_config = ConfigDict(alias_generator=to_camel)

    category: QualityFindingCategory = Field(..., description="The governance category.")
    count: int = Field(..., ge=0, description="Findings in this category.")


class QualitySummary(Schema):
    """The governed headline for one quality governance assessment.

    A pure data container assembled from the assessment. ``overall_quality_score`` is
    a recorded 0-100 roll-up; it is **not** what the decision is derived from
    (ADR-0017 Recommendation 7) — the decision comes from governed rule evaluation and
    is recorded here alongside the score.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    decision: QualityDecision = Field(..., description="The governed release decision.")
    overall_quality_score: int = Field(
        ..., ge=0, le=100, description="Recorded 0-100 quality roll-up (not the decision source)."
    )
    policy_id: QualityPolicyId = Field(..., description="Governing policy identity.")
    policy_version: QualityPolicyVersion = Field(..., description="Governing policy version.")

    total_findings: int = Field(..., ge=0, description="Total governance findings.")
    warning_count: int = Field(..., ge=0, description="WARNING-severity findings.")
    failure_count: int = Field(..., ge=0, description="FAILURE-severity findings.")

    category_distribution: tuple[QualityFindingCategoryCount, ...] = Field(
        default=(), description="Finding counts by governance category."
    )
    verdict: str = Field(..., min_length=1, description="One-line overall governance verdict.")
