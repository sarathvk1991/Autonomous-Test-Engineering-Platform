"""Deterministic institutionalization evaluation (CAP-086B).

``InstitutionalizationEvaluator`` is the **sole institutional-readiness
authority**: it is the only component that decides whether a freshly
generated :class:`Learning` is organizationally ready for institutional
adoption. It answers exactly one question — *is this Learning organizationally
ready?* — and never the technical-validity question
:class:`~requirement_intelligence.learning.engine.learning_validator.
LearningValidator` already answered (ADR-0029 D12, Recommendation 16).

It never constructs a ``Learning`` (D9 already moved generation earlier in
the pipeline), never mutates a ``LearningValidation``, and never records
lifecycle state itself — its decision is consumed by
:class:`~requirement_intelligence.learning.engine.lifecycle_recorder.
LifecycleRecorder`, which alone constructs the resulting
:class:`LearningLifecycle` entry (ADR-0029 D10).

The decision is a deterministic function of the ``Learning``'s own already-
derived ``confidence`` field alone — no hidden state, no re-reading of the
consumed ``OrganizationalMemoryResult`` (D18/D20): a ``Learning`` is
institutionally ready exactly when its confidence has already reached the
top of the governed ladder, ``VERIFIED``.
"""

from __future__ import annotations

from requirement_intelligence.learning.identity import LearningId
from requirement_intelligence.learning.models.enums import LearningConfidenceLevel
from requirement_intelligence.learning.models.learning import Learning


class InstitutionalizationEvaluator:
    """Decide organizational readiness for freshly generated Learning only."""

    def evaluate(self, learnings: tuple[Learning, ...]) -> frozenset[LearningId]:
        """Deterministically return the ids of every institutionally ready Learning."""
        return frozenset(
            learning.learning_id
            for learning in learnings
            if learning.confidence == LearningConfidenceLevel.VERIFIED
        )
