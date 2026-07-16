"""The :class:`Learning` — one validated conclusion promoted from a
:class:`~requirement_intelligence.learning.models.learning_candidate.
LearningCandidate`.

A ``Learning`` is a ``LearningCandidate`` that has cleared Learning
Validation (ADR-0028 §Stage 6) and now carries a governed maturity level
(ADR-0028 §Stage 8: ``OBSERVED`` through ``RETIRED``) — reusable
organizational understanding, never merely descriptive (ADR-0028 §Stage 1).
It is the top rung of this framework's concrete model hierarchy — the tier
:class:`~requirement_intelligence.learning.models.result.LearningResult`
ultimately produces (ADR-0028 §Stage 2).

Promotion is adjacent only: a ``Learning`` references exactly the one
``LearningCandidate`` it was validated from, never skipping past it to name a
``BestPractice`` directly (mirrors the adjacent-promotion discipline ADR-0027
§D10 froze one tier below).

No learning is validated here — a future engine (CAP-086B, reserved)
populates this model from an already-validated candidate under a governed
validation policy; this milestone only shapes the contract. Whether a
candidate's own ``confidence`` must reach a governed floor before promotion
(ADR-0028 §Stage 6/Recommendation 15) is a validation *decision* a future
engine makes — this model enforces only that the reference chain exists,
never the reasoning behind it.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.learning.identity import (
    LearningCandidateId,
    LearningId,
    LearningValidationId,
)
from requirement_intelligence.learning.models.enums import (
    LearningConfidenceLevel,
    LearningMaturity,
)
from shared.contracts.base import Schema


class Learning(Schema):
    """One validated conclusion — data only, never a probabilistic judgement.

    ``candidate_id`` names the ``LearningCandidate`` this learning was
    promoted from; ``validation_id`` names the ``LearningValidation`` record
    that certified it — both by id only (adjacent promotion only, mirrors
    Recommendation 2/3 of ADR-0027).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    learning_id: LearningId = Field(..., description="Deterministic identity of this learning.")
    candidate_id: LearningCandidateId = Field(
        ..., description="The learning candidate this learning was promoted from (reference only)."
    )
    validation_id: LearningValidationId = Field(
        ..., description="The validation record that certified this learning (reference only)."
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable, explainable conclusion about what should change.",
    )
    maturity: LearningMaturity = Field(
        ..., description="Governed maturity level this learning currently occupies."
    )
    confidence: LearningConfidenceLevel = Field(
        ..., description="Governed confidence in this learning (metadata, never truth)."
    )
