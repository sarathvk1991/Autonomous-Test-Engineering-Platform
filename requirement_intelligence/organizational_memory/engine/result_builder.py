"""Deterministic result assembly (CAP-085B).

``ResultBuilder`` is the **only constructor** of :class:`OrganizationalMemoryResult`
anywhere in this engine (ADR-0027 §D16, Recommendation 15). Every other
collaborator produces intermediate immutable artifacts only; this is the
single point where they are assembled into the frozen runtime contract.
"""

from __future__ import annotations

from datetime import datetime

from requirement_intelligence.organizational_memory.identity import (
    OrganizationalMemoryFrameworkVersion,
    OrganizationalMemoryId,
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
    OrganizationalMemoryResultId,
)
from requirement_intelligence.organizational_memory.models.best_practice import BestPractice
from requirement_intelligence.organizational_memory.models.experience import Experience
from requirement_intelligence.organizational_memory.models.knowledge_lifecycle import (
    KnowledgeLifecycle,
)
from requirement_intelligence.organizational_memory.models.knowledge_promotion import (
    KnowledgePromotion,
)
from requirement_intelligence.organizational_memory.models.lesson import Lesson
from requirement_intelligence.organizational_memory.models.result import OrganizationalMemoryResult
from requirement_intelligence.organizational_memory.models.summary import (
    OrganizationalMemoryMetrics,
    OrganizationalMemorySummary,
)


class ResultBuilder:
    """Assemble the frozen :class:`OrganizationalMemoryResult`. The only constructor."""

    def build(
        self,
        *,
        memory_id: OrganizationalMemoryId,
        continuous_improvement_result_id: str,
        knowledge_graph_result_id: str,
        experiences: tuple[Experience, ...],
        lessons: tuple[Lesson, ...],
        best_practices: tuple[BestPractice, ...],
        promotions: tuple[KnowledgePromotion, ...],
        lifecycles: tuple[KnowledgeLifecycle, ...],
        summary: OrganizationalMemorySummary,
        metrics: OrganizationalMemoryMetrics,
        policy_id: OrganizationalMemoryPolicyId,
        policy_version: OrganizationalMemoryPolicyVersion,
        framework_version: OrganizationalMemoryFrameworkVersion,
        started_at: datetime,
        completed_at: datetime,
    ) -> OrganizationalMemoryResult:
        """Assemble the final result exactly once, from already-finished collaborators."""
        return OrganizationalMemoryResult(
            result_id=OrganizationalMemoryResultId.for_memory(str(memory_id)),
            memory_id=memory_id,
            continuous_improvement_result_id=continuous_improvement_result_id,
            knowledge_graph_result_id=knowledge_graph_result_id,
            experiences=experiences,
            lessons=lessons,
            best_practices=best_practices,
            promotions=promotions,
            lifecycles=lifecycles,
            summary=summary,
            metrics=metrics,
            policy_id=policy_id,
            policy_version=policy_version,
            framework_version=framework_version,
            started_at=started_at,
            completed_at=completed_at,
        )
