"""A shared, deterministic confidence-ordinal mapping (CAP-086B, engine-internal).

Not a collaborator — a pure helper function :class:`~requirement_intelligence.
learning.engine.learning_validator.LearningValidator`,
:class:`~requirement_intelligence.learning.engine.learning_generator.
LearningGenerator`, and :class:`~requirement_intelligence.learning.engine.
confidence_recorder.ConfidenceRecorder` all call to compute a governed
confidence level from an evidence count and a governed threshold. This is
the only "reasoning" CAP-086B applies to confidence: a deterministic ratio
of already-recorded counts to an already-governed policy threshold — never a
statistical estimate, never a probability, never an ML score (ADR-0028
§Stage 9: confidence is metadata, never truth; it may evolve, but only ever
as a pure function of already-explainable evidence volume).

Calling this helper from more than one collaborator with the *same* inputs
is deliberate, not duplication: it guarantees every collaborator that needs
a confidence value for the same evidence agrees on it by construction,
without any collaborator reading another's decision (D20's immutable-object-
only communication rule) — there is nothing to disagree about, because the
computation itself is the single source of truth, not any one collaborator's
memory of having computed it.
"""

from __future__ import annotations

from requirement_intelligence.learning.models.enums import LearningConfidenceLevel

_LEVELS = (
    LearningConfidenceLevel.LOW,
    LearningConfidenceLevel.MEDIUM,
    LearningConfidenceLevel.HIGH,
    LearningConfidenceLevel.VERIFIED,
)


def confidence_for_evidence(count: int, threshold: int) -> LearningConfidenceLevel:
    """Return the governed confidence level for *count* against *threshold*.

    ``count // threshold`` deterministically climbs the four-level ladder —
    clearing the floor once yields ``MEDIUM``, twice yields ``HIGH``, three
    times or more yields ``VERIFIED``. A non-positive threshold (never
    produced by the governed policy's own validator) falls back to the
    lowest level rather than dividing by zero.
    """
    if threshold <= 0:
        return _LEVELS[0]
    ordinal = min(len(_LEVELS) - 1, count // threshold)
    return _LEVELS[ordinal]


def confidence_ordinal(confidence: LearningConfidenceLevel) -> int:
    """Deterministic ordering key for the governed confidence vocabulary."""
    return _LEVELS.index(confidence)
