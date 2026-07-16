"""Deterministic lesson consolidation (CAP-085B).

``LessonConsolidator`` is the **sole consolidation authority**: it is the
only component that merges :class:`Lesson` instances. It consumes **Lessons
only** (ADR-0027 §D12) — never an Experience, never a Best Practice.

Two Lessons are merged only when their ``message`` text is byte-identical —
deterministic equality only, never semantic merging (OM-LSC-001). This can
occur when two distinct Experience clusters (from different source layers,
ADR-0027 §D2's peer-source isolation) happen to describe the same underlying
pattern in identical words. Merging **unions** the two Lessons' source
Experience ids — no provenance reference is ever dropped (OM-LSC-002,
Recommendation 5 of ADR-0027) — and keeps the lower of the two Lesson ids as
the surviving identity, a deterministic, order-independent tie-break.
"""

from __future__ import annotations

from collections import defaultdict

from requirement_intelligence.organizational_memory.identity import ExperienceId
from requirement_intelligence.organizational_memory.models.enums import (
    OrganizationalMemoryConfidence,
)
from requirement_intelligence.organizational_memory.models.lesson import Lesson

_CONFIDENCE_ORDER = (
    OrganizationalMemoryConfidence.LOW,
    OrganizationalMemoryConfidence.MEDIUM,
    OrganizationalMemoryConfidence.HIGH,
    OrganizationalMemoryConfidence.VERIFIED,
)


class LessonConsolidator:
    """Merge only byte-identical-message Lessons. Equality only, never semantic."""

    def consolidate(self, lessons: tuple[Lesson, ...]) -> tuple[Lesson, ...]:
        """Deterministically merge Lessons sharing identical message text."""
        groups: dict[str, list[Lesson]] = defaultdict(list)
        for lesson in lessons:
            groups[lesson.message].append(lesson)

        consolidated: list[Lesson] = []
        for group in groups.values():
            if len(group) == 1:
                consolidated.append(group[0])
                continue
            ordered = sorted(group, key=lambda lesson: str(lesson.lesson_id))
            survivor = ordered[0]
            merged_experience_ids: list[ExperienceId] = []
            seen: set[ExperienceId] = set()
            for lesson in ordered:
                for experience_id in lesson.source_experience_ids:
                    if experience_id not in seen:
                        seen.add(experience_id)
                        merged_experience_ids.append(experience_id)
            highest_confidence = max(
                (lesson.confidence for lesson in ordered), key=_confidence_ordinal
            )
            consolidated.append(
                survivor.model_copy(
                    update={
                        "source_experience_ids": tuple(merged_experience_ids),
                        "confidence": highest_confidence,
                    }
                )
            )

        consolidated.sort(key=lambda lesson: str(lesson.lesson_id))
        return tuple(consolidated)


def _confidence_ordinal(confidence: OrganizationalMemoryConfidence) -> int:
    """Deterministic ordering key for the governed confidence vocabulary."""
    return _CONFIDENCE_ORDER.index(confidence)
