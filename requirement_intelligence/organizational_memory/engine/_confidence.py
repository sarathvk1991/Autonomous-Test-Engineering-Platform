"""A shared, deterministic confidence-ordinal mapping (CAP-085B, engine-internal).

Not a collaborator — a pure helper function :class:`LessonGenerator` and
:class:`~requirement_intelligence.organizational_memory.engine.
best_practice_generator.BestPracticeGenerator` both call to compute a
governed confidence level from an evidence count and a governed threshold.
This is the only "reasoning" CAP-085B applies to confidence: a deterministic
ratio of already-recorded counts to an already-governed policy threshold —
never a statistical estimate, never a probability, never an ML score
(ADR-0026 §Stage 8: confidence is metadata, never truth; it may evolve, but
only ever as a pure function of already-explainable evidence volume).
"""

from __future__ import annotations

from requirement_intelligence.organizational_memory.models.enums import (
    OrganizationalMemoryConfidence,
)

_LEVELS = (
    OrganizationalMemoryConfidence.LOW,
    OrganizationalMemoryConfidence.MEDIUM,
    OrganizationalMemoryConfidence.HIGH,
    OrganizationalMemoryConfidence.VERIFIED,
)


def confidence_for_evidence(count: int, threshold: int) -> OrganizationalMemoryConfidence:
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
