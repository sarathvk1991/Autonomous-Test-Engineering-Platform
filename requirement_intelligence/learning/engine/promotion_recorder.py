"""Deterministic promotion recording (CAP-086B).

``PromotionRecorder`` is the **sole promotion authority**: it is the only
component that records that a Candidate-to-Learning promotion happened. It
consumes **already-generated Learning only** (ADR-0029 D10) — never a
candidate directly, and it records history, it never creates or validates a
``Learning`` (ADR-0028 §Stage 6/11, ADR-0029 D10).

**Reserved output (ADR-0029 D10).** Learning's CAP-086A brief introduced no
``LearningPromotion`` record type — unlike Organizational Memory, which
already ships a dedicated ``KnowledgePromotion`` model. This milestone
changes no model (Stage 15 verification of CAP-086B), so this collaborator's
output is an engine-internal :class:`PromotionEvent` — never threaded into
:class:`~requirement_intelligence.learning.models.result.LearningResult`.
No information is lost: promotion provenance is already fully
reconstructable from ``Learning.candidate_id`` and
``LearningValidation.candidate_id`` alone (ADR-0029 D11); a future
``LearningPromotion`` record, if ever introduced, would add convenience,
never a missing fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from requirement_intelligence.learning.identity import LearningCandidateId, LearningId
from requirement_intelligence.learning.models.learning import Learning


@dataclass(frozen=True)
class PromotionEvent:
    """An engine-internal, immutable record of one Candidate-to-Learning promotion.

    Never a runtime contract — not exported past this package, never a field
    on :class:`~requirement_intelligence.learning.models.result.LearningResult`
    (D10's reserved-output note). Exists so the promotion-recording algorithm
    (ADR-0029 Stage 4 of the CAP-086B brief) is genuinely computed and
    testable, not merely a documentation placeholder.
    """

    candidate_id: LearningCandidateId
    learning_id: LearningId
    rationale: str
    promoted_at: datetime


class PromotionRecorder:
    """Record governed promotion history for already-generated Learning only."""

    def record(
        self, learnings: tuple[Learning, ...], promoted_at: datetime
    ) -> tuple[PromotionEvent, ...]:
        """Deterministically record one promotion event per generated Learning."""
        return tuple(
            PromotionEvent(
                candidate_id=learning.candidate_id,
                learning_id=learning.learning_id,
                rationale="Candidate cleared validation and was generated into Learning.",
                promoted_at=promoted_at,
            )
            for learning in learnings
        )
