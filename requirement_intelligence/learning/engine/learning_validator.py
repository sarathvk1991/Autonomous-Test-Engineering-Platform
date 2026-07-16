"""Deterministic candidate validation (CAP-086B).

``LearningValidator`` is the **sole validation authority**: it is the only
component that constructs :class:`LearningValidation` instances. It consumes
**consolidated Learning Candidates only** (ADR-0029 D10/D19) — never a
``Learning`` (there is none yet: validation runs *before* generation, the
Stage 0 Constitutional Correction ADR-0029 D9/D16 records), never the raw
``OrganizationalMemoryResult``.

Validation answers exactly one question: *is this candidate's own evidence
technically sufficient?* (ADR-0029 D12). It is never heuristic and never
depends on hidden context — only the candidate's own referenced Best
Practices (``len(candidate.source_best_practice_ids)``) and the governed
policy thresholds (ADR-0029 D19/D20). A candidate whose evidence clears the
governed ``LearningThresholds.minimum_confidence_for_learning`` ordinal
floor is validated in full: every one of the governed
``minimum_validation_gates_for_learning`` Stage 6 gates (ADR-0028) is
recorded cleared, in canonical declaration order. A candidate that does not
clear the floor receives **no** ``LearningValidation`` at all — never a
partial, empty-gated record (the model's own "at least one gate" validator
forbids one, and this engine never attempts to construct one).
"""

from __future__ import annotations

from datetime import datetime

from requirement_intelligence.learning.engine._confidence import confidence_for_evidence
from requirement_intelligence.learning.engine._confidence import (
    confidence_ordinal as _confidence_ordinal,
)
from requirement_intelligence.learning.identity import LearningValidationId
from requirement_intelligence.learning.models.enums import LearningValidationGate
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.models.learning_validation import LearningValidation
from requirement_intelligence.learning.policy.learning_policy import LearningPolicy

#: Canonical, deterministic ordering of the six governed Stage 6 gates
#: (ADR-0028 §Stage 6) — the order in which a partial gate count (governed by
#: ``minimum_validation_gates_for_learning``) is filled.
_CANONICAL_GATE_ORDER = tuple(LearningValidationGate)


class LearningValidator:
    """Validate consolidated candidates against their own evidence only."""

    def __init__(self, policy: LearningPolicy) -> None:
        """Store the governed policy this validator reads. Construction only."""
        self._policy = policy

    def validate(
        self,
        candidates: tuple[LearningCandidate, ...],
        seed_id: str,
        validated_at: datetime,
    ) -> tuple[LearningValidation, ...]:
        """Deterministically validate every candidate clearing the governed floor."""
        if not self._policy.capability_switches.enable_validation:
            return ()

        threshold = self._policy.thresholds.minimum_best_practices_for_candidate
        confidence_floor = self._policy.thresholds.minimum_confidence_for_learning
        gate_count = self._policy.thresholds.minimum_validation_gates_for_learning

        validations: list[LearningValidation] = []
        ordinal = 0
        for candidate in candidates:
            evidence_count = len(candidate.source_best_practice_ids)
            confidence = confidence_for_evidence(evidence_count, threshold)
            if _confidence_ordinal(confidence) < confidence_floor:
                continue
            validations.append(
                LearningValidation(
                    validation_id=LearningValidationId.for_ordinal(seed_id, ordinal),
                    candidate_id=candidate.candidate_id,
                    gates_cleared=_CANONICAL_GATE_ORDER[:gate_count],
                    rationale=(
                        f"{evidence_count} best practice(s) cleared the governed "
                        f"confidence floor for validation."
                    ),
                    validated_at=validated_at,
                    confidence=confidence,
                    policy_version=self._policy.policy_version,
                )
            )
            ordinal += 1
        return tuple(validations)
