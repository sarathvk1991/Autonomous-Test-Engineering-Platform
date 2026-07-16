"""Deterministic lifecycle recording (CAP-085B).

``LifecycleRecorder`` is the **sole lifecycle authority**: it is the only
component that constructs :class:`KnowledgeLifecycle` instances. It consumes
**Organizational Knowledge only** (Experience, Lesson, BestPractice —
ADR-0027 §D12) and records the governed ``ACTIVE`` state for every object
freshly produced this build. It never predicts retirement and never ages
knowledge (Stage 3/D5/D15 of ADR-0027) — a future engine milestone that
deprecates, historicizes, or archives existing knowledge does so by
appending a *new* lifecycle record for that subject, never by editing or
removing this one (ADR-0026 §Stage 7: retirement is append-only).
"""

from __future__ import annotations

from requirement_intelligence.organizational_memory.identity import KnowledgeLifecycleId
from requirement_intelligence.organizational_memory.models.best_practice import BestPractice
from requirement_intelligence.organizational_memory.models.enums import (
    KnowledgeLifecycleState,
)
from requirement_intelligence.organizational_memory.models.experience import Experience
from requirement_intelligence.organizational_memory.models.knowledge_lifecycle import (
    KnowledgeLifecycle,
)
from requirement_intelligence.organizational_memory.models.lesson import Lesson
from requirement_intelligence.organizational_memory.policy.organizational_memory_policy import (
    OrganizationalMemoryPolicy,
)


class LifecycleRecorder:
    """Record the governed ACTIVE lifecycle state for freshly produced knowledge only."""

    def __init__(self, policy: OrganizationalMemoryPolicy) -> None:
        """Store the governed policy this recorder reads. Construction only."""
        self._policy = policy

    def record(
        self,
        experiences: tuple[Experience, ...],
        lessons: tuple[Lesson, ...],
        best_practices: tuple[BestPractice, ...],
        memory_id: str,
    ) -> tuple[KnowledgeLifecycle, ...]:
        """Deterministically record one ACTIVE lifecycle entry per knowledge object."""
        if not self._policy.capability_switches.enable_retirement:
            return ()

        records: list[KnowledgeLifecycle] = []
        ordinal = 0
        for experience in experiences:
            records.append(
                self._active(memory_id, ordinal, str(experience.experience_id), "captured")
            )
            ordinal += 1
        for lesson in lessons:
            records.append(self._active(memory_id, ordinal, str(lesson.lesson_id), "promoted"))
            ordinal += 1
        for best_practice in best_practices:
            records.append(
                self._active(
                    memory_id, ordinal, str(best_practice.best_practice_id), "institutionalized"
                )
            )
            ordinal += 1
        return tuple(records)

    @staticmethod
    def _active(memory_id: str, ordinal: int, subject_id: str, verb: str) -> KnowledgeLifecycle:
        return KnowledgeLifecycle(
            lifecycle_id=KnowledgeLifecycleId.for_ordinal(memory_id, ordinal),
            subject_id=subject_id,
            state=KnowledgeLifecycleState.ACTIVE,
            state_reason=f"newly {verb}",
        )
