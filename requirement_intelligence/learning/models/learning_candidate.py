"""The :class:`LearningCandidate` — one proposed conclusion drawn from
Organizational Knowledge, not yet validated.

A ``LearningCandidate`` names one or more ``BestPractice`` records from a
completed ``OrganizationalMemoryResult`` (ADR-0028 §Stage 7) and proposes what
should change as a result — still unvalidated, still not Learning (ADR-0028
§Stage 6). It is the bottom rung of this framework's own concrete model
hierarchy — never a copy of the Best Practice it names, only a governed
reference to it (mirrors Recommendation 2 of ADR-0027, extended one tier).

No candidate is proposed here — a future engine (CAP-086B, reserved)
populates this model by reference from an already-completed
``OrganizationalMemoryResult``; this milestone only shapes the contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.learning.identity import LearningCandidateId
from requirement_intelligence.learning.models.enums import LearningConfidenceLevel
from shared.contracts.base import Schema


class LearningCandidate(Schema):
    """One proposed, not-yet-validated conclusion — data only.

    ``source_best_practice_ids`` names every ``BestPractice`` (from the
    consumed ``OrganizationalMemoryResult``) this candidate was proposed
    from, by id only — never by embedding that best practice's content
    (mirrors Recommendation 2/3 of ADR-0027).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    candidate_id: LearningCandidateId = Field(
        ..., description="Deterministic identity of this learning candidate."
    )
    source_best_practice_ids: tuple[str, ...] = Field(
        default=(),
        description="Best practices (from OrganizationalMemoryResult) this candidate concerns.",
    )
    proposed_change: str = Field(
        ..., min_length=1, description="Human-readable statement of what should change."
    )
    confidence: LearningConfidenceLevel = Field(
        ..., description="Governed confidence in this candidate (metadata, never truth)."
    )

    @model_validator(mode="after")
    def _validate_candidate(self) -> LearningCandidate:
        """A candidate must be explainable from at least one source best practice."""
        if not self.source_best_practice_ids:
            raise ValueError(
                f"LearningCandidate {self.candidate_id!r} must reference at least one "
                f"source best practice — a candidate with no traceable evidence is not "
                f"explainable."
            )
        return self
