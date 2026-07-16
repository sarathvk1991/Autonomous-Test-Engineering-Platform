"""Deterministic Learning generation (CAP-086B).

``LearningGenerator`` is the **sole Learning authority**: it is the only
component that constructs :class:`Learning` instances, and it generates them
**only for a candidate that already has a** :class:`LearningValidation`
(ADR-0029 D9/D17, Stage 0 Constitutional Correction) — never for an
unvalidated candidate, and never bypassing the governed hierarchy (ADR-0029
D11, no skip-level promotion).

Every generated ``Learning`` starts at ``LearningMaturity.VALIDATED`` — by
construction, only a validated candidate reaches this collaborator, so there
is no lower maturity a freshly generated ``Learning`` could honestly claim.
Whether it later becomes ``INSTITUTIONAL`` is a separate, later decision
(:class:`~requirement_intelligence.learning.engine.
institutionalization_evaluator.InstitutionalizationEvaluator`, recorded by
:class:`~requirement_intelligence.learning.engine.lifecycle_recorder.
LifecycleRecorder` as an additional, append-only lifecycle entry for the
same subject — never a mutation of this object's own frozen ``maturity``
field, ADR-0028 §Stage 8).
"""

from __future__ import annotations

from requirement_intelligence.learning.engine._confidence import confidence_for_evidence
from requirement_intelligence.learning.identity import LearningId
from requirement_intelligence.learning.models.enums import LearningMaturity
from requirement_intelligence.learning.models.learning import Learning
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.models.learning_validation import LearningValidation
from requirement_intelligence.learning.policy.learning_policy import LearningPolicy


class LearningGenerator:
    """Generate governed Learning only from already-validated candidates."""

    def __init__(self, policy: LearningPolicy) -> None:
        """Store the governed policy this generator reads. Construction only."""
        self._policy = policy

    def generate(
        self,
        candidates: tuple[LearningCandidate, ...],
        validations: tuple[LearningValidation, ...],
        seed_id: str,
    ) -> tuple[Learning, ...]:
        """Deterministically generate one Learning per validated candidate."""
        candidates_by_id = {candidate.candidate_id: candidate for candidate in candidates}
        threshold = self._policy.thresholds.minimum_best_practices_for_candidate

        learnings: list[Learning] = []
        ordinal = 0
        for validation in validations:
            candidate = candidates_by_id.get(validation.candidate_id)
            if candidate is None:
                continue
            evidence_count = len(candidate.source_best_practice_ids)
            confidence = confidence_for_evidence(evidence_count, threshold)
            learnings.append(
                Learning(
                    learning_id=LearningId.for_ordinal(seed_id, ordinal),
                    candidate_id=candidate.candidate_id,
                    validation_id=validation.validation_id,
                    message=candidate.proposed_change,
                    maturity=LearningMaturity.VALIDATED,
                    confidence=confidence,
                )
            )
            ordinal += 1
        return tuple(learnings)
