"""The :class:`Recommendation` and the :class:`RecommendationReference` it carries.

Recommendation 2 (ADR-0019): a ``Recommendation`` never duplicates the runtime object
that grounded it. It carries a :class:`RecommendationReference` — the identity and
version of the upstream observation, finding, or issue it is derived from — never a
copy of that object's content. This mirrors ``EnhancementFinding``'s
reference-not-copy convention over ``RequirementObservation`` (ADR-0018) and
``AssessmentFindingReference`` (ADR-0017 §D26).

Neither model computes anything. A future recommendation engine populates
``Recommendation`` from the completed enhancement, grounding, validation, CP1, and
quality governance results; this milestone only shapes the contract (CAP-082A).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.recommendation.identity.recommendation_identity import (
    RecommendationId,
)
from requirement_intelligence.recommendation.models.enums import (
    RecommendationEffort,
    RecommendationPriority,
    RecommendationSource,
    RecommendationType,
)
from shared.contracts.base import Schema


class RecommendationReference(Schema):
    """A reference to the upstream runtime object that grounded a recommendation.

    Names *which* upstream result (:class:`RecommendationSource`), *which* item
    within it (``referenced_id`` — an observation id, finding id, issue id, or
    similar), and the contract version of the result it was drawn from. It never
    copies that item's content (Recommendation 2, Recommendation 7 explainability).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    source: RecommendationSource = Field(
        ..., description="Which upstream runtime contract this reference names."
    )
    referenced_id: str = Field(
        ..., min_length=1, description="Identity of the referenced upstream item."
    )
    referenced_version: str = Field(
        ..., min_length=1, description="Contract/schema version of the referenced result."
    )


class Recommendation(Schema):
    """One deterministic, explainable recommendation. Data only.

    Owns exactly one recommendation: a title, description, rationale, governed
    classification (``recommendation_type``, ``priority``, ``effort``,
    ``confidence``), the upstream subsystem it concerns (``recommendation_source``),
    and one or more :class:`RecommendationReference` entries naming the upstream
    evidence it was derived from. No recommendation is generated here — a future
    engine populates this model; it never computes a title, rationale, priority,
    effort, or confidence itself.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    recommendation_id: RecommendationId = Field(
        ..., description="Deterministic identity of this recommendation."
    )
    title: str = Field(..., min_length=1, description="One-line description of the action.")
    description: str = Field(..., min_length=1, description="What should be done.")
    rationale: str = Field(..., min_length=1, description="Why this recommendation was made.")
    recommendation_type: RecommendationType = Field(
        ..., description="The governed vocabulary of what action is suggested."
    )
    priority: RecommendationPriority = Field(..., description="Recorded urgency.")
    effort: RecommendationEffort = Field(..., description="Recorded estimated effort.")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Recorded confidence in this recommendation."
    )
    recommendation_source: RecommendationSource = Field(
        ..., description="Which upstream subsystem this recommendation concerns."
    )
    references: tuple[RecommendationReference, ...] = Field(
        default=(),
        description="The upstream evidence this recommendation was derived from (never copied).",
    )

    @model_validator(mode="after")
    def _validate_recommendation(self) -> Recommendation:
        """A recommendation must be explainable from at least one reference."""
        if not self.references:
            raise ValueError(
                "Recommendation must carry at least one RecommendationReference — a "
                "recommendation with no upstream evidence reference is not explainable "
                "(Recommendation 7)."
            )
        return self
