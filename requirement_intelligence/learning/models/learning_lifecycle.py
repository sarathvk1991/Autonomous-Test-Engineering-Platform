"""The :class:`LearningLifecycle` — one governed record of a subject's
current maturity state.

A ``LearningLifecycle`` **records** which governed maturity — ``CANDIDATE``
through ``RETIRED`` — one ``LearningCandidate`` or ``Learning`` currently
occupies (ADR-0028 §Stage 8). It is a record, never a transition: it never
moves a subject between maturity levels, it only preserves the current level
and why (mirrors Recommendation 4 of ADR-0027, lifted to the maturity axis).

No maturity transition happens here — a future engine (CAP-086B, reserved)
decides when to advance or retire a subject's maturity; this milestone only
shapes the contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.learning.identity import LearningLifecycleId
from requirement_intelligence.learning.models.enums import LearningMaturity
from shared.contracts.base import Schema


class LearningLifecycle(Schema):
    """One governed maturity-state record — data only, never a transition.

    ``subject_id`` names the ``LearningCandidate`` or ``Learning`` this
    record concerns, by id only — never by embedding that subject's content.
    Maturity evolves upward only, and a subject's history is never deleted
    (ADR-0028 §Stage 8).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    lifecycle_id: LearningLifecycleId = Field(
        ..., description="Deterministic identity of this lifecycle record."
    )
    subject_id: str = Field(
        ...,
        min_length=1,
        description="Id of the LearningCandidate or Learning this record concerns.",
    )
    maturity: LearningMaturity = Field(
        ..., description="The governed maturity level this subject currently occupies."
    )
    maturity_reason: str = Field(
        ..., min_length=1, description="Human-readable reason this maturity level was recorded."
    )
