"""Canonical, immutable rule models for the governed Matching Policy.

These are **governed data**, not algorithms: thresholds a match must clear, weights
a matcher applies per evidence field, the ranking keys, and the tie-breaker. No model
computes anything; a :class:`GroundingStrategy` reads them and implements the maths.

Every model is a frozen :class:`~shared.contracts.base.Schema` with tuple-backed
collections and camelCase serialisation.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.matching.enums import MatchRankingKey, MatchTieBreaker
from shared.contracts.base import Schema


class MatchingThresholds(Schema):
    """The minimum bars a candidate link must clear to count as a match."""

    model_config = ConfigDict(alias_generator=to_camel)

    minimum_match_score: int = Field(
        default=0, ge=0, le=100, description="Lowest 0-100 score that still counts as a match."
    )
    minimum_token_overlap: int = Field(
        default=0, ge=0, description="Lowest number of overlapping tokens to count as a match."
    )
    minimum_exact_terms: int = Field(
        default=0, ge=0, description="Lowest number of exact-term matches to count as a match."
    )


class MatchingWeights(Schema):
    """Per-field and per-kind weights a matcher applies when scoring a match.

    Governed integers only. The matcher decides how to combine them; the policy only
    states their values, so tuning is a versioned data change, never a code change.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    title_weight: int = Field(default=0, ge=0, description="Weight for a match in the title.")
    description_weight: int = Field(default=0, ge=0, description="Weight for a description match.")
    rule_key_weight: int = Field(default=0, ge=0, description="Weight for a rule-key match.")
    tag_weight: int = Field(default=0, ge=0, description="Weight for a tag match.")
    component_weight: int = Field(default=0, ge=0, description="Weight for a component match.")
    endpoint_weight: int = Field(default=0, ge=0, description="Weight for an endpoint match.")
    exact_token_bonus: int = Field(default=0, ge=0, description="Bonus for an exact token match.")
    partial_token_bonus: int = Field(
        default=0, ge=0, description="Bonus for a partial token match."
    )
    cross_source_bonus: int = Field(
        default=0, ge=0, description="Bonus when evidence spans multiple source systems (future)."
    )


class MatchingRanking(Schema):
    """The ordered keys a matcher ranks competing evidence links by."""

    model_config = ConfigDict(alias_generator=to_camel)

    keys: tuple[MatchRankingKey, ...] = Field(
        ..., min_length=1, description="Ranking keys, in priority order."
    )


class MatchingTieBreaker(Schema):
    """The final, total-order key applied when ranking keys tie."""

    model_config = ConfigDict(alias_generator=to_camel)

    key: MatchTieBreaker = Field(..., description="The tie-breaking key.")
    ascending: bool = Field(default=True, description="Whether the tie-breaker sorts ascending.")
