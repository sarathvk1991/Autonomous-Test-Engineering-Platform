"""Deterministic lesson generation (CAP-085B).

``LessonGenerator`` is the **sole Lesson authority**: it is the only
component that constructs :class:`Lesson` instances. It consumes
**Experience clusters only** (ADR-0027 §D12) — never a raw
``ContinuousImprovementResult`` or ``KnowledgeGraphResult`` directly, and
never generates a Best Practice itself.

A Lesson is generated from a cluster only once the cluster reaches the
governed ``OrganizationalMemoryThresholds.minimum_experiences_for_lesson``
floor (OM-LES-001/OM-LES-002) — the same "conservative default, no finding
below the floor" discipline every prior deterministic engine in this
platform already applies (ADR-0022 §D9, ADR-0023 §D10). Every Lesson
references every contributing Experience — no Lesson without provenance
(Recommendation 17 of ADR-0027).
"""

from __future__ import annotations

from requirement_intelligence.organizational_memory.engine._confidence import (
    confidence_for_evidence,
)
from requirement_intelligence.organizational_memory.identity import LessonId
from requirement_intelligence.organizational_memory.models.experience import Experience
from requirement_intelligence.organizational_memory.models.lesson import Lesson
from requirement_intelligence.organizational_memory.policy.organizational_memory_policy import (
    OrganizationalMemoryPolicy,
)


class LessonGenerator:
    """Generate governed Lessons from qualifying Experience clusters only."""

    def __init__(self, policy: OrganizationalMemoryPolicy) -> None:
        """Store the governed policy this generator reads. Construction only."""
        self._policy = policy

    def generate(
        self, clusters: tuple[tuple[Experience, ...], ...], memory_id: str
    ) -> tuple[Lesson, ...]:
        """Deterministically generate one Lesson per cluster clearing the floor."""
        if not self._policy.capability_switches.enable_lesson_promotion:
            return ()

        threshold = self._policy.thresholds.minimum_experiences_for_lesson
        lessons: list[Lesson] = []
        ordinal = 0
        for cluster in clusters:
            if len(cluster) < threshold:
                continue
            source_experience_ids = tuple(experience.experience_id for experience in cluster)
            lessons.append(
                Lesson(
                    lesson_id=LessonId.for_ordinal(memory_id, ordinal),
                    source_experience_ids=source_experience_ids,
                    message=self._message(cluster),
                    confidence=confidence_for_evidence(len(cluster), threshold),
                )
            )
            ordinal += 1
        return tuple(lessons)

    @staticmethod
    def _message(cluster: tuple[Experience, ...]) -> str:
        """A deterministic, explainable message naming the cluster's own evidence."""
        representative = cluster[0].description
        return f"Recurring pattern across {len(cluster)} experience(s): {representative}"
