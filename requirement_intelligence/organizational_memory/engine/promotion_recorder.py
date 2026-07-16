"""Deterministic promotion recording (CAP-085B).

``PromotionRecorder`` is the **sole promotion authority**: it is the only
component that constructs :class:`KnowledgePromotion` instances. It
consumes **Lessons and Best Practices only** (ADR-0027 §D12) — never an
Experience directly, and it records history, it never performs a promotion
(ADR-0026 §Stage 6, ADR-0027 §D11).

Every promotion names its source ids, its target id, a deterministic
rationale, the governing policy version, the confidence recorded at the
moment of promotion, and when it occurred — no inference, exactly the
provenance ADR-0027 §D11/Recommendation 5 requires.
"""

from __future__ import annotations

from datetime import datetime

from requirement_intelligence.organizational_memory.identity import KnowledgePromotionId
from requirement_intelligence.organizational_memory.models.best_practice import BestPractice
from requirement_intelligence.organizational_memory.models.knowledge_promotion import (
    KnowledgePromotion,
)
from requirement_intelligence.organizational_memory.models.lesson import Lesson
from requirement_intelligence.organizational_memory.policy.organizational_memory_policy import (
    OrganizationalMemoryPolicy,
)


class PromotionRecorder:
    """Record governed promotion history for already-generated knowledge only."""

    def __init__(self, policy: OrganizationalMemoryPolicy) -> None:
        """Store the governed policy this recorder reads. Construction only."""
        self._policy = policy

    def record(
        self,
        lessons: tuple[Lesson, ...],
        best_practices: tuple[BestPractice, ...],
        memory_id: str,
        completed_at: datetime,
    ) -> tuple[KnowledgePromotion, ...]:
        """Deterministically record one promotion per Lesson and per BestPractice."""
        promotions: list[KnowledgePromotion] = []
        ordinal = 0
        for lesson in lessons:
            promotions.append(
                KnowledgePromotion(
                    promotion_id=KnowledgePromotionId.for_ordinal(memory_id, ordinal),
                    source_ids=tuple(str(eid) for eid in lesson.source_experience_ids),
                    target_ids=(str(lesson.lesson_id),),
                    rationale=(
                        f"{len(lesson.source_experience_ids)} experience(s) cleared the "
                        f"governed minimum-experiences floor."
                    ),
                    promoted_at=completed_at,
                    confidence=lesson.confidence,
                    policy_version=self._policy.policy_version,
                )
            )
            ordinal += 1
        for best_practice in best_practices:
            promotions.append(
                KnowledgePromotion(
                    promotion_id=KnowledgePromotionId.for_ordinal(memory_id, ordinal),
                    source_ids=tuple(str(lid) for lid in best_practice.source_lesson_ids),
                    target_ids=(str(best_practice.best_practice_id),),
                    rationale=(
                        f"{len(best_practice.source_lesson_ids)} lesson(s) cleared the "
                        f"governed minimum-lessons floor."
                    ),
                    promoted_at=completed_at,
                    confidence=best_practice.confidence,
                    policy_version=self._policy.policy_version,
                )
            )
            ordinal += 1
        return tuple(promotions)
