"""The :class:`Lesson` — one explainable conclusion promoted from Experiences.

A ``Lesson`` gives an explicit, explainable conclusion — "when X recurs, Y
follows" — built from one or more :class:`~requirement_intelligence.
organizational_memory.models.experience.Experience` records it references by
id only (ADR-0026 §Stage 2/6/9). It is still scoped to the evidence that
produced it — a Lesson does not yet claim to generalize; that is
:class:`~requirement_intelligence.organizational_memory.models.best_practice.
BestPractice`'s own, later promotion.

No lesson is promoted here — a future engine (CAP-085B, reserved) populates
this model from already-captured Experiences under a governed promotion
policy; this milestone only shapes the contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.organizational_memory.identity import ExperienceId, LessonId
from requirement_intelligence.organizational_memory.models.enums import (
    OrganizationalMemoryConfidence,
)
from shared.contracts.base import Schema


class Lesson(Schema):
    """One explainable conclusion — data only, never a probabilistic judgement.

    ``source_experience_ids`` names every Experience this lesson was promoted
    from, by id only — never by embedding that experience's content
    (Recommendation 2/3 of ADR-0027).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    lesson_id: LessonId = Field(..., description="Deterministic identity of this lesson.")
    source_experience_ids: tuple[ExperienceId, ...] = Field(
        default=(), description="Experiences this lesson was promoted from (reference only)."
    )
    message: str = Field(
        ..., min_length=1, description="Human-readable, explainable conclusion."
    )
    confidence: OrganizationalMemoryConfidence = Field(
        ..., description="Governed confidence in this lesson (metadata, never truth)."
    )

    @model_validator(mode="after")
    def _validate_lesson(self) -> Lesson:
        """A lesson must be explainable from at least one source experience."""
        if not self.source_experience_ids:
            raise ValueError(
                f"Lesson {self.lesson_id!r} must reference at least one source experience — "
                f"a lesson with no traceable evidence is not explainable."
            )
        return self
