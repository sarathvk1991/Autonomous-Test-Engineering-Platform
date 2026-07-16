"""Deterministic summary assembly (CAP-086B).

``SummaryBuilder`` computes the build's :class:`LearningSummary` **exactly
once**, from already-finished collaborator output. It tallies already-
recorded rows by counting them — it never proposes a candidate, never
validates evidence, never generates Learning (ADR-0029 D10/D22:
"SummaryBuilder never computes Learning").
"""

from __future__ import annotations

from requirement_intelligence.learning.identity import LearningPolicyId, LearningPolicyVersion
from requirement_intelligence.learning.models.learning import Learning
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.models.learning_validation import LearningValidation
from requirement_intelligence.learning.models.summary import LearningSummary


class SummaryBuilder:
    """Compute the governed build summary exactly once. Never computes Learning."""

    def build(
        self,
        policy_id: LearningPolicyId,
        policy_version: LearningPolicyVersion,
        candidates: tuple[LearningCandidate, ...],
        learnings: tuple[Learning, ...],
        validations: tuple[LearningValidation, ...],
    ) -> LearningSummary:
        """Tally already-produced collaborator output into one headline summary."""
        return LearningSummary(
            policy_id=policy_id,
            policy_version=policy_version,
            total_candidates=len(candidates),
            total_learnings=len(learnings),
            total_validations=len(validations),
            headline=(
                f"{len(candidates)} candidate(s), {len(learnings)} learning(s), "
                f"{len(validations)} validation(s)."
            ),
        )
