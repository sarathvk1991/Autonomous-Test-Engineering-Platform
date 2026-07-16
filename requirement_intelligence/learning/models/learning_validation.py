"""The :class:`LearningValidation` — one governed record that a validation
event occurred against a :class:`~requirement_intelligence.learning.models.
learning_candidate.LearningCandidate`.

A ``LearningValidation`` **records** which of the six Learning Validation
gates (ADR-0028 §Stage 6: sufficiency, validated evidence, repeatability,
organizational confidence, organizational usefulness, complete
explainability) a validation event covered. It is history, not action: it
never performs validation, it only preserves complete provenance of a
validation that already happened (mirrors Recommendation 5 of ADR-0027).

No validation happens here — a future engine (CAP-086B, reserved) decides
when a candidate has cleared enough gates and constructs the resulting
``Learning`` object plus this record together; this milestone only shapes the
contract.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.learning.identity import (
    LearningCandidateId,
    LearningPolicyVersion,
    LearningValidationId,
)
from requirement_intelligence.learning.models.enums import (
    LearningConfidenceLevel,
    LearningValidationGate,
)
from shared.contracts.base import Schema


class LearningValidation(Schema):
    """One governed validation record — data only, never the act of validation itself.

    ``candidate_id`` names the :class:`~requirement_intelligence.learning.
    models.learning_candidate.LearningCandidate` this validation concerns, by
    id only. ``gates_cleared`` names which of the six governed Stage 6 gates
    this validation event covered — never a computation of *whether* a gate
    was actually satisfied (Stage 2 of ADR-0029: "validators only enforce
    references exist ... never perform reasoning").
    """

    model_config = ConfigDict(alias_generator=to_camel)

    validation_id: LearningValidationId = Field(
        ..., description="Deterministic identity of this validation record."
    )
    candidate_id: LearningCandidateId = Field(
        ..., description="The learning candidate this validation concerns (reference only)."
    )
    gates_cleared: tuple[LearningValidationGate, ...] = Field(
        default=(), description="Which of the six governed Stage 6 gates this event covered."
    )
    rationale: str = Field(
        ..., min_length=1, description="Human-readable reason this validation occurred."
    )
    validated_at: datetime = Field(..., description="When this validation occurred.")
    confidence: LearningConfidenceLevel = Field(
        ..., description="Governed confidence recorded at the moment of validation."
    )
    policy_version: LearningPolicyVersion = Field(
        ..., description="Version of the governing policy in force when this validation occurred."
    )

    @model_validator(mode="after")
    def _validate_validation(self) -> LearningValidation:
        """A validation record must name at least one cleared gate."""
        if not self.gates_cleared:
            raise ValueError(
                f"LearningValidation {self.validation_id!r} must name at least one "
                f"cleared gate — a validation that cleared nothing is not a validation."
            )
        return self
