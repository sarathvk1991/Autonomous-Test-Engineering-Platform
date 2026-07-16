"""Deterministic learning-candidate collection (CAP-086B).

``LearningCandidateCollector`` is the **sole candidate authority**: it is
the only component that constructs :class:`LearningCandidate` instances, and
it does so directly from the one completed ``OrganizationalMemoryResult``
:class:`~requirement_intelligence.learning.learning_service.LearningService.
build` receives. It performs **no inference, no AI, no heuristics** — every
candidate it emits is a direct, governed reference to a Best Practice the
consumed result already names (mirrors Recommendation 2 of ADR-0027,
extended one tier: candidates reference Best Practices, they never duplicate
them).

Candidate proposal itself is gated at the **corpus level**: ADR-0028 §Stage 6
requires "sufficient Organizational Knowledge — a single Best Practice, in
isolation, is not enough." If the consumed result's `best_practices` tuple
does not already clear the governed
``LearningThresholds.minimum_best_practices_for_candidate`` floor, no
candidate is proposed at all this build — never a partial attempt.
"""

from __future__ import annotations

from requirement_intelligence.learning.identity import LearningCandidateId
from requirement_intelligence.learning.models.enums import LearningConfidenceLevel
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.policy.learning_policy import LearningPolicy
from requirement_intelligence.organizational_memory.models.result import (
    OrganizationalMemoryResult,
)

#: Every newly proposed candidate starts at the bottom of the confidence
#: ladder (ADR-0028 §Stage 9) — it may only rise through governed validation
#: and generation (ADR-0028 §Stage 5/6), never at proposal time.
_INITIAL_CONFIDENCE = LearningConfidenceLevel.LOW


class LearningCandidateCollector:
    """Propose governed Learning Candidates from one completed Organizational
    Memory result.

    The sole candidate authority (Recommendation 1 of ADR-0029: Learning
    owns platform validation). Deduplicates by :class:`LearningCandidateId`
    — the same referenced Best Practice, seen more than once, yields exactly
    one candidate.
    """

    def __init__(self, policy: LearningPolicy) -> None:
        """Store the governed policy this collector reads. Construction only."""
        self._policy = policy

    def collect(
        self, organizational_memory_result: OrganizationalMemoryResult
    ) -> tuple[LearningCandidate, ...]:
        """Deterministically propose one candidate per governed Best Practice."""
        if not self._policy.capability_switches.enable_candidate_proposal:
            return ()

        best_practices = organizational_memory_result.best_practices
        threshold = self._policy.thresholds.minimum_best_practices_for_candidate
        if len(best_practices) < threshold:
            return ()

        candidates: dict[LearningCandidateId, LearningCandidate] = {}
        for best_practice in best_practices:
            self._add(candidates, str(best_practice.best_practice_id), best_practice.description)
        return tuple(candidates.values())

    @staticmethod
    def _add(
        candidates: dict[LearningCandidateId, LearningCandidate],
        source_best_practice_id: str,
        description: str,
    ) -> None:
        """Insert the candidate for *source_best_practice_id* if not already present."""
        candidate_id = LearningCandidateId.for_source(source_best_practice_id)
        if candidate_id in candidates:
            return
        candidates[candidate_id] = LearningCandidate(
            candidate_id=candidate_id,
            source_best_practice_ids=(source_best_practice_id,),
            proposed_change=f"Adopt best practice: {description}",
            confidence=_INITIAL_CONFIDENCE,
        )
