"""Deterministic confidence recording (CAP-086B).

``ConfidenceRecorder`` is the **sole confidence authority**: it is the only
component that constructs :class:`LearningConfidence` instances. It consumes
**Learning only** (ADR-0029 D10) — never a candidate, never a validation
directly — and records the same governed confidence level
:class:`~requirement_intelligence.learning.engine.learning_generator.
LearningGenerator` already derived for that ``Learning``, via the identical
shared :func:`~requirement_intelligence.learning.engine._confidence.
confidence_for_evidence` computation, from the same evidence count. This is
a **recording** of an already-derived decision, never a re-guess: calling
the same pure function on the same inputs guarantees agreement by
construction (ADR-0029 D19/D20, Recommendation 28 — "Confidence is always
derived, never guessed").
"""

from __future__ import annotations

from datetime import datetime

from requirement_intelligence.learning.engine._confidence import confidence_for_evidence
from requirement_intelligence.learning.identity import LearningConfidenceId
from requirement_intelligence.learning.models.learning import Learning
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.models.learning_confidence import LearningConfidence
from requirement_intelligence.learning.policy.learning_policy import LearningPolicy


class ConfidenceRecorder:
    """Record governed confidence for already-generated Learning only."""

    def __init__(self, policy: LearningPolicy) -> None:
        """Store the governed policy this recorder reads. Construction only."""
        self._policy = policy

    def record(
        self,
        learnings: tuple[Learning, ...],
        candidates_by_id: dict[str, LearningCandidate],
        seed_id: str,
        recorded_at: datetime,
    ) -> tuple[LearningConfidence, ...]:
        """Deterministically record one confidence entry per generated Learning."""
        if not self._policy.capability_switches.enable_confidence_recording:
            return ()

        threshold = self._policy.thresholds.minimum_best_practices_for_candidate
        records: list[LearningConfidence] = []
        ordinal = 0
        for learning in learnings:
            candidate = candidates_by_id.get(str(learning.candidate_id))
            evidence_count = len(candidate.source_best_practice_ids) if candidate else 0
            level = confidence_for_evidence(evidence_count, threshold)
            records.append(
                LearningConfidence(
                    confidence_id=LearningConfidenceId.for_ordinal(seed_id, ordinal),
                    subject_id=str(learning.learning_id),
                    level=level,
                    evidence_count=evidence_count,
                    rationale=(
                        f"Derived from {evidence_count} referenced best practice(s) "
                        f"against the governed threshold."
                    ),
                    recorded_at=recorded_at,
                    supersedes_confidence_id=None,
                )
            )
            ordinal += 1
        return tuple(records)
