"""The :class:`BestPractice` — one generally-recommended conclusion promoted
from verified Lessons.

A ``BestPractice`` is a :class:`~requirement_intelligence.organizational_memory.
models.lesson.Lesson` verified across enough independent Experiences that it is
recommended generally, not just where it was first observed (ADR-0026 §Stage
2/6). It is the top rung of this framework's concrete model hierarchy — the
tier :class:`~requirement_intelligence.organizational_memory.models.result.
OrganizationalMemoryResult` ultimately curates (ADR-0026 §Stage 1).

No best practice is promoted here — a future engine (CAP-085B, reserved)
populates this model from already-promoted Lessons under a governed promotion
policy; this milestone only shapes the contract. Whether a Lesson's own
``confidence`` must reach ``VERIFIED`` before promotion (ADR-0026 §Stage 3/
Recommendation 4) is a promotion *decision* a future engine makes — this model
enforces only that the reference chain exists, never the reasoning behind it
(Stage 2 of ADR-0027: "validators only enforce references exist ... never
perform reasoning").
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.organizational_memory.identity import BestPracticeId, LessonId
from requirement_intelligence.organizational_memory.models.enums import (
    OrganizationalMemoryConfidence,
)
from shared.contracts.base import Schema


class BestPractice(Schema):
    """One generally-recommended conclusion — data only, never a probabilistic judgement.

    ``source_lesson_ids`` names every Lesson this best practice was promoted
    from, by id only — never by embedding that lesson's content
    (Recommendation 2/3 of ADR-0027).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    best_practice_id: BestPracticeId = Field(
        ..., description="Deterministic identity of this best practice."
    )
    source_lesson_ids: tuple[LessonId, ...] = Field(
        default=(), description="Lessons this best practice was promoted from (reference only)."
    )
    title: str = Field(..., min_length=1, description="Short, human-readable title.")
    description: str = Field(
        ..., min_length=1, description="Human-readable, generally-applicable description."
    )
    confidence: OrganizationalMemoryConfidence = Field(
        ..., description="Governed confidence in this best practice (metadata, never truth)."
    )

    @model_validator(mode="after")
    def _validate_best_practice(self) -> BestPractice:
        """A best practice must be explainable from at least one source lesson."""
        if not self.source_lesson_ids:
            raise ValueError(
                f"BestPractice {self.best_practice_id!r} must reference at least one source "
                f"lesson — a best practice with no traceable evidence is not explainable."
            )
        return self
