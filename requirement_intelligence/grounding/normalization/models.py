"""Canonical text-normalization models for evidence matching.

These sit **below** ``GroundingStrategy``: they turn raw text (a requirement, an
evidence title/description) into a canonical :class:`NormalizedText` every strategy
can compare on equal terms. They are preprocessing only — no matching, no evidence,
no requirements, no scoring, no classification.

Not to be confused with the response-normalization subsystem
(``requirement_intelligence/normalization/``), which normalizes an AI *response's
structure* into a ``ParsedResponse``. These models normalize *free text into tokens*,
a different concern in a different package.

Immutability & determinism
--------------------------
Every model is a frozen :class:`~shared.contracts.base.Schema` with tuple-backed
collections, camelCase serialisation, and no timestamps, UUIDs, or runtime objects.
Normalising the same text twice yields an equal :class:`NormalizedText`.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity import MatchingNormalizationVersion
from shared.contracts.base import Schema


class NormalizedToken(Schema):
    """One canonical token produced by normalization (e.g. ``nosniff``)."""

    model_config = ConfigDict(alias_generator=to_camel)

    value: str = Field(..., min_length=1, description="The canonical token text.")


class NormalizationStatistics(Schema):
    """Pure, non-judgemental observations recorded during one normalization.

    Counts only — never scores, confidence, or matching decisions. They exist so a
    normalization is auditable without re-running it.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    tokens_produced: int = Field(..., ge=0, description="Canonical tokens produced.")
    punctuation_removed: int = Field(default=0, ge=0, description="Punctuation characters removed.")
    case_conversions: int = Field(
        default=0, ge=0, description="Characters changed by case folding."
    )
    separators_normalized: int = Field(default=0, ge=0, description="Separators normalized.")
    stop_words_removed: int = Field(default=0, ge=0, description="Stop words removed.")


class NormalizedText(Schema):
    """One normalized document: the original, its normalized form, and its tokens.

    ``version`` and ``statistics`` are the normalization metadata: which governed
    configuration version produced this, and what it observed doing so.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    original: str = Field(..., description="The raw input text, preserved verbatim.")
    normalized: str = Field(..., description="The normalized text form.")
    tokens: tuple[NormalizedToken, ...] = Field(
        default=(), description="Canonical tokens, in order of appearance."
    )
    statistics: NormalizationStatistics = Field(..., description="Observations from this run.")
    version: MatchingNormalizationVersion = Field(
        ..., description="Version of the normalization configuration that produced this."
    )

    @model_validator(mode="after")
    def _validate_normalized_text(self) -> NormalizedText:
        """The token count in the statistics must match the tokens actually carried."""
        if self.statistics.tokens_produced != len(self.tokens):
            raise ValueError(
                f"statistics.tokens_produced ({self.statistics.tokens_produced}) disagrees "
                f"with the {len(self.tokens)} token(s) carried."
            )
        return self
