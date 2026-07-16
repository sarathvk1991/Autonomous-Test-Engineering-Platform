"""Deterministic result assembly (CAP-086B).

``ResultBuilder`` is the **only constructor** of :class:`LearningResult`
anywhere in this engine (ADR-0029 D17, Recommendation 20). Every other
collaborator produces intermediate immutable artifacts or internal decisions
only; this is the single point where they are assembled into the frozen
runtime contract.
"""

from __future__ import annotations

from datetime import datetime

from requirement_intelligence.learning.identity import (
    LearningFrameworkVersion,
    LearningPolicyId,
    LearningPolicyVersion,
    LearningResultId,
)
from requirement_intelligence.learning.models.learning import Learning
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.models.learning_confidence import LearningConfidence
from requirement_intelligence.learning.models.learning_lifecycle import LearningLifecycle
from requirement_intelligence.learning.models.learning_validation import LearningValidation
from requirement_intelligence.learning.models.result import LearningResult
from requirement_intelligence.learning.models.summary import LearningMetrics, LearningSummary


class ResultBuilder:
    """Assemble the frozen :class:`LearningResult`. The only constructor."""

    def build(
        self,
        *,
        organizational_memory_result_id: str,
        candidates: tuple[LearningCandidate, ...],
        learnings: tuple[Learning, ...],
        validations: tuple[LearningValidation, ...],
        confidences: tuple[LearningConfidence, ...],
        lifecycles: tuple[LearningLifecycle, ...],
        summary: LearningSummary,
        metrics: LearningMetrics,
        policy_id: LearningPolicyId,
        policy_version: LearningPolicyVersion,
        framework_version: LearningFrameworkVersion,
        started_at: datetime,
        completed_at: datetime,
    ) -> LearningResult:
        """Assemble the final result exactly once, from already-finished collaborators."""
        return LearningResult(
            result_id=LearningResultId.for_source(organizational_memory_result_id),
            organizational_memory_result_id=organizational_memory_result_id,
            candidates=candidates,
            learnings=learnings,
            validations=validations,
            confidences=confidences,
            lifecycles=lifecycles,
            summary=summary,
            metrics=metrics,
            policy_id=policy_id,
            policy_version=policy_version,
            framework_version=framework_version,
            started_at=started_at,
            completed_at=completed_at,
        )
