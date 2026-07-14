"""The :class:`RecommendationGroup` — ordering and categorization only.

Recommendation 6 (ADR-0019): groups own ordering and categorization of
recommendations that already exist. A group never mints, mutates, or duplicates a
:class:`~requirement_intelligence.recommendation.models.recommendation.Recommendation`
— it names, by id, an ordered subset already present in the
:class:`~requirement_intelligence.recommendation.models.result.RecommendationResult`
it belongs to. This mirrors ``RelationshipGraph``'s reference-only edges over
requirement ids (ADR-0018) and ``EnhancementSummary``'s distribution-by-reference
convention.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.recommendation.identity.recommendation_identity import (
    RecommendationGroupId,
    RecommendationId,
)
from requirement_intelligence.recommendation.models.enums import RecommendationType
from shared.contracts.base import Schema


class RecommendationGroup(Schema):
    """An ordered, categorized subset of recommendations. Data only.

    ``category`` classifies the group using the same governed
    :class:`RecommendationType` vocabulary a recommendation itself carries — a group
    never invents a second categorization axis. ``recommendation_ids`` is the
    group's ordering: the sequence in which its member recommendations should be
    presented. The group carries no title text, no computed count, and no
    recommendation content — those remain owned by
    :class:`~requirement_intelligence.recommendation.models.recommendation.Recommendation`
    and
    :class:`~requirement_intelligence.recommendation.models.summary.RecommendationSummary`.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    group_id: RecommendationGroupId = Field(..., description="Deterministic group identity.")
    category: RecommendationType = Field(
        ..., description="The governed recommendation type this group is categorized under."
    )
    label: str = Field(..., min_length=1, description="Human-readable group label.")
    recommendation_ids: tuple[RecommendationId, ...] = Field(
        default=(), description="The group's ordering — member recommendation ids, in order."
    )

    @model_validator(mode="after")
    def _validate_group(self) -> RecommendationGroup:
        """A group must not name the same recommendation twice."""
        if len(self.recommendation_ids) != len(set(self.recommendation_ids)):
            raise ValueError("RecommendationGroup must not contain duplicate recommendation ids.")
        return self
