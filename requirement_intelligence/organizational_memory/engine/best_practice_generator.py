"""Deterministic best practice generation (CAP-085B).

``BestPracticeGenerator`` is the **sole Best Practice authority**: it is the
only component that constructs :class:`BestPractice` instances, and it
generates them **only from Lessons** — never directly from Experiences,
never bypassing the governed hierarchy (ADR-0027 §D10, OM-BP-002).

Lessons are grouped by the governed source layer their own contributing
Experiences share — resolved by looking up each Lesson's
``source_experience_ids`` against the already-produced Experience tuple
(this pipeline's own earlier output, never a raw Layer 2 result reached into
directly). A Best Practice is generated only once a group reaches the
governed ``OrganizationalMemoryThresholds.minimum_lessons_for_best_practice``
floor (OM-BP-001) — the same conservative-floor discipline
:class:`~requirement_intelligence.organizational_memory.engine.
lesson_generator.LessonGenerator` already applies one tier down.
"""

from __future__ import annotations

from collections import defaultdict

from requirement_intelligence.organizational_memory.engine._confidence import (
    confidence_for_evidence,
)
from requirement_intelligence.organizational_memory.identity import (
    BestPracticeId,
    ExperienceId,
)
from requirement_intelligence.organizational_memory.models.best_practice import BestPractice
from requirement_intelligence.organizational_memory.models.experience import Experience
from requirement_intelligence.organizational_memory.models.lesson import Lesson
from requirement_intelligence.organizational_memory.policy.organizational_memory_policy import (
    OrganizationalMemoryPolicy,
)


class BestPracticeGenerator:
    """Generate governed Best Practices from qualifying Lesson groups only."""

    def __init__(self, policy: OrganizationalMemoryPolicy) -> None:
        """Store the governed policy this generator reads. Construction only."""
        self._policy = policy

    def generate(
        self,
        lessons: tuple[Lesson, ...],
        experiences: tuple[Experience, ...],
        memory_id: str,
    ) -> tuple[BestPractice, ...]:
        """Deterministically generate one BestPractice per lesson group clearing the floor."""
        if not self._policy.capability_switches.enable_best_practice_promotion:
            return ()
        if not lessons:
            return ()

        layer_by_experience_id = {
            experience.experience_id: str(experience.source_layer) for experience in experiences
        }

        groups: dict[str, list[Lesson]] = defaultdict(list)
        for lesson in lessons:
            layer = self._resolve_layer(lesson, layer_by_experience_id)
            if layer is not None:
                groups[layer].append(lesson)

        threshold = self._policy.thresholds.minimum_lessons_for_best_practice
        best_practices: list[BestPractice] = []
        ordinal = 0
        for layer in sorted(groups):
            group = sorted(groups[layer], key=lambda lesson: str(lesson.lesson_id))
            if len(group) < threshold:
                continue
            source_lesson_ids = tuple(lesson.lesson_id for lesson in group)
            best_practices.append(
                BestPractice(
                    best_practice_id=BestPracticeId.for_ordinal(memory_id, ordinal),
                    source_lesson_ids=source_lesson_ids,
                    title=f"Institutionalized pattern from {layer}",
                    description=self._description(group, layer),
                    confidence=confidence_for_evidence(len(group), threshold),
                )
            )
            ordinal += 1
        return tuple(best_practices)

    @staticmethod
    def _resolve_layer(
        lesson: Lesson, layer_by_experience_id: dict[ExperienceId, str]
    ) -> str | None:
        """Resolve the governed source layer every one of *lesson*'s experiences share."""
        if not lesson.source_experience_ids:
            return None
        return layer_by_experience_id.get(lesson.source_experience_ids[0])

    @staticmethod
    def _description(group: list[Lesson], layer: str) -> str:
        """A deterministic, explainable description naming the group's own evidence."""
        return f"{len(group)} lesson(s) consolidated from {layer}: {group[0].message}"
