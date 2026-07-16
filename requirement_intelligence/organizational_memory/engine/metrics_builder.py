"""Deterministic metrics assembly (CAP-085B).

``MetricsBuilder`` computes the build's :class:`OrganizationalMemoryMetrics`
**exactly once**, from already-finished collaborator output. It tallies
already-recorded rows by a field they already carry — it never captures,
clusters, generates, promotes, or retires anything itself (ADR-0027 §D12:
"MetricsBuilder never computes knowledge").
"""

from __future__ import annotations

from collections import Counter

from requirement_intelligence.organizational_memory.models.best_practice import BestPractice
from requirement_intelligence.organizational_memory.models.enums import KnowledgeLifecycleState
from requirement_intelligence.organizational_memory.models.experience import Experience
from requirement_intelligence.organizational_memory.models.knowledge_lifecycle import (
    KnowledgeLifecycle,
)
from requirement_intelligence.organizational_memory.models.knowledge_promotion import (
    KnowledgePromotion,
)
from requirement_intelligence.organizational_memory.models.lesson import Lesson
from requirement_intelligence.organizational_memory.models.summary import (
    OrganizationalMemoryMetrics,
)


class MetricsBuilder:
    """Compute the governed numeric roll-up exactly once. Never computes knowledge."""

    def build(
        self,
        experiences: tuple[Experience, ...],
        lessons: tuple[Lesson, ...],
        best_practices: tuple[BestPractice, ...],
        promotions: tuple[KnowledgePromotion, ...],
        lifecycles: tuple[KnowledgeLifecycle, ...],
    ) -> OrganizationalMemoryMetrics:
        """Tally already-produced collaborator output into one deterministic roll-up."""
        counts = Counter(lifecycle.state for lifecycle in lifecycles)
        return OrganizationalMemoryMetrics(
            experience_count=len(experiences),
            lesson_count=len(lessons),
            best_practice_count=len(best_practices),
            promotion_count=len(promotions),
            active_count=counts[KnowledgeLifecycleState.ACTIVE],
            deprecated_count=counts[KnowledgeLifecycleState.DEPRECATED],
            historical_count=counts[KnowledgeLifecycleState.HISTORICAL],
            archived_count=counts[KnowledgeLifecycleState.ARCHIVED],
        )
