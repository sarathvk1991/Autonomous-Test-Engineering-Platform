"""Deterministic lifecycle recording (CAP-086B).

``LifecycleRecorder`` is the **sole lifecycle authority**: it is the only
component that constructs :class:`LearningLifecycle` instances. It consumes
**Learned Knowledge only** (Learning Candidate, Learning — ADR-0029 D10) and
records the governed maturity state for every object freshly produced this
build. It never predicts retirement and never ages knowledge (ADR-0028
§Stage 8) — a future engine milestone that trusts, standardizes, or retires
existing Learning does so by appending a *new* lifecycle record for that
subject, never by editing or removing this one (ADR-0028 §Stage 8: maturity
evolves upward only, and never in place).

Every candidate receives exactly one ``CANDIDATE`` lifecycle entry at
proposal time. Every generated ``Learning`` receives exactly one
``VALIDATED`` lifecycle entry — and, when
:class:`~requirement_intelligence.learning.engine.
institutionalization_evaluator.InstitutionalizationEvaluator` deemed it
institutionally ready, a **second**, later ``INSTITUTIONAL`` lifecycle entry
for the same subject id. This is not a mutation of the first entry — it is
the append-only progression the maturity axis exists to record (ADR-0028
§Stage 8): the ``Learning`` object's own frozen ``maturity`` field always
reads ``VALIDATED`` (set once, at generation, by
:class:`~requirement_intelligence.learning.engine.learning_generator.
LearningGenerator`); the lifecycle ledger is where its subsequent
progression is recorded.
"""

from __future__ import annotations

from requirement_intelligence.learning.identity import LearningLifecycleId
from requirement_intelligence.learning.models.enums import LearningMaturity
from requirement_intelligence.learning.models.learning import Learning
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.models.learning_lifecycle import LearningLifecycle
from requirement_intelligence.learning.policy.learning_policy import LearningPolicy


class LifecycleRecorder:
    """Record the governed maturity ladder for freshly produced knowledge only."""

    def __init__(self, policy: LearningPolicy) -> None:
        """Store the governed policy this recorder reads. Construction only."""
        self._policy = policy

    def record(
        self,
        candidates: tuple[LearningCandidate, ...],
        learnings: tuple[Learning, ...],
        institutionalized_ids: frozenset,
        seed_id: str,
    ) -> tuple[LearningLifecycle, ...]:
        """Deterministically record maturity entries for every candidate and learning."""
        if not self._policy.capability_switches.enable_lifecycle_recording:
            return ()

        records: list[LearningLifecycle] = []
        ordinal = 0
        for candidate in candidates:
            records.append(
                self._entry(
                    seed_id,
                    ordinal,
                    str(candidate.candidate_id),
                    LearningMaturity.CANDIDATE,
                    "newly proposed",
                )
            )
            ordinal += 1
        for learning in learnings:
            records.append(
                self._entry(
                    seed_id,
                    ordinal,
                    str(learning.learning_id),
                    LearningMaturity.VALIDATED,
                    "newly validated",
                )
            )
            ordinal += 1
            if learning.learning_id in institutionalized_ids:
                records.append(
                    self._entry(
                        seed_id,
                        ordinal,
                        str(learning.learning_id),
                        LearningMaturity.INSTITUTIONAL,
                        "institutionally ready",
                    )
                )
                ordinal += 1
        return tuple(records)

    @staticmethod
    def _entry(
        seed_id: str,
        ordinal: int,
        subject_id: str,
        maturity: LearningMaturity,
        reason: str,
    ) -> LearningLifecycle:
        return LearningLifecycle(
            lifecycle_id=LearningLifecycleId.for_ordinal(seed_id, ordinal),
            subject_id=subject_id,
            maturity=maturity,
            maturity_reason=reason,
        )
