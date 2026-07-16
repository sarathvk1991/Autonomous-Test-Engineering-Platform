"""Deterministic summary assembly (CAP-085B).

``SummaryBuilder`` computes the build's :class:`OrganizationalMemorySummary`
**exactly once**, from already-finished collaborator output. It tallies
already-recorded rows by counting them — it never captures an experience,
never generates a lesson, never institutionalizes a best practice
(ADR-0027 §D12: "SummaryBuilder never computes knowledge").
"""

from __future__ import annotations

from requirement_intelligence.organizational_memory.identity import (
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
)
from requirement_intelligence.organizational_memory.models.best_practice import BestPractice
from requirement_intelligence.organizational_memory.models.experience import Experience
from requirement_intelligence.organizational_memory.models.knowledge_promotion import (
    KnowledgePromotion,
)
from requirement_intelligence.organizational_memory.models.lesson import Lesson
from requirement_intelligence.organizational_memory.models.summary import (
    OrganizationalMemorySummary,
)


class SummaryBuilder:
    """Compute the governed build summary exactly once. Never computes knowledge."""

    def build(
        self,
        policy_id: OrganizationalMemoryPolicyId,
        policy_version: OrganizationalMemoryPolicyVersion,
        experiences: tuple[Experience, ...],
        lessons: tuple[Lesson, ...],
        best_practices: tuple[BestPractice, ...],
        promotions: tuple[KnowledgePromotion, ...],
    ) -> OrganizationalMemorySummary:
        """Tally already-produced collaborator output into one headline summary."""
        return OrganizationalMemorySummary(
            policy_id=policy_id,
            policy_version=policy_version,
            total_experiences=len(experiences),
            total_lessons=len(lessons),
            total_best_practices=len(best_practices),
            total_promotions=len(promotions),
            headline=(
                f"{len(experiences)} experience(s), {len(lessons)} lesson(s), "
                f"{len(best_practices)} best practice(s)."
            ),
        )
