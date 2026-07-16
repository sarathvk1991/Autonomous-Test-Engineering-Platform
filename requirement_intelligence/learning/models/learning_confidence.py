"""The :class:`LearningConfidence` — one governed record of a confidence
determination for a candidate or a learning.

A ``LearningConfidence`` **records** how strongly the referenced evidence
supports its subject at the moment it was recorded (ADR-0028 §Stage 9).
Confidence is metadata, never truth, and is tracked on an axis independent of
maturity (:class:`~requirement_intelligence.learning.models.
learning_lifecycle.LearningLifecycle`). Confidence may rise as more
corroborating Organizational Knowledge accumulates — this is never a
mutation of an existing record; it is the production of a **new**
``LearningConfidence`` object, which may reference the record it supersedes
(ADR-0028 §Stage 9).

No confidence is determined here — a future engine (CAP-086B, reserved)
computes ``evidence_count`` and ``level`` from already-captured Organizational
Knowledge; this milestone only shapes the contract.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.learning.identity import LearningConfidenceId
from requirement_intelligence.learning.models.enums import LearningConfidenceLevel
from shared.contracts.base import Schema


class LearningConfidence(Schema):
    """One governed confidence record — data only, never a mutation of its subject.

    ``subject_id`` names the ``LearningCandidate`` or ``Learning`` this
    record concerns, by id only — never by embedding that subject's content.
    ``supersedes_confidence_id`` optionally names the prior confidence
    record this one replaces (append-only evolution, ADR-0028 §Stage 9/11)
    — ``None`` for a subject's first recorded confidence.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    confidence_id: LearningConfidenceId = Field(
        ..., description="Deterministic identity of this confidence record."
    )
    subject_id: str = Field(
        ...,
        min_length=1,
        description="Id of the LearningCandidate or Learning this record concerns.",
    )
    level: LearningConfidenceLevel = Field(
        ..., description="The governed confidence level recorded for this subject."
    )
    evidence_count: int = Field(
        ..., ge=0, description="Count of corroborating Organizational Knowledge items."
    )
    rationale: str = Field(
        ..., min_length=1, description="Human-readable reason this confidence was recorded."
    )
    recorded_at: datetime = Field(..., description="When this confidence was recorded.")
    supersedes_confidence_id: str | None = Field(
        default=None,
        description="Id of the prior confidence record this one supersedes, if any.",
    )
