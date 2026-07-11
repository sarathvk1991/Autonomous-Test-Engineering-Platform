"""Canonical confidence models: :class:`ConfidenceExplanation` and
:class:`ConfidenceAssessment`.

``ConfidenceAssessment`` is the **internal** canonical output of the Confidence
subsystem — the complete confidence evaluation for one requirement, independent of
``GroundedRequirement``. It is *not* an execution artifact and is *not* exposed outside
Grounding. ``ConfidenceExplanation`` is its structured, deterministic explanation —
machine-readable data (positive/negative factors, applied policy rules, score
breakdown, recommendations), never generated prose.

Pipeline position::

    MatchResult → ClassificationResult → ConfidenceAssessment → GroundedRequirement

Keeping this as a distinct model isolates the confidence calculation (CAP-077D):
``GroundedRequirement`` carries a completed confidence, but no component *creates* it
except the Confidence subsystem.

Immutability & determinism
--------------------------
Frozen :class:`~shared.contracts.base.Schema` models with tuple-backed collections and
camelCase serialisation. No timestamps, UUIDs, or runtime objects. A calculator is a
pure function of its input, so equal inputs yield equal assessments.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity import ConfidenceVersion, GroundedRequirementId
from requirement_intelligence.grounding.models.confidence import ConfidenceComponent
from requirement_intelligence.grounding.models.enums import ConfidenceBand
from shared.contracts.base import Schema

#: Version of the ``ConfidenceAssessment`` schema (not the policy). Advances
#: additively; a shape change a prior consumer could misread is MAJOR.
CONFIDENCE_VERSION = ConfidenceVersion(1, 0, 0)


class ConfidenceExplanation(Schema):
    """Structured, deterministic explanation of one confidence assessment.

    Machine-readable data only — reusable by reports and governance dashboards. No
    generated prose, no AI-generated text. The permanent explanation contract for the
    Confidence subsystem.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    summary: str = Field(
        default="", description="Short, factual confidence summary (may be empty)."
    )
    positive_factors: tuple[str, ...] = Field(
        default=(), description="Factors that raised the score."
    )
    negative_factors: tuple[str, ...] = Field(
        default=(), description="Factors that lowered the score."
    )
    applied_policy_rules: tuple[str, ...] = Field(
        default=(), description="Governed policy rules that applied."
    )
    score_breakdown: tuple[ConfidenceComponent, ...] = Field(
        default=(), description="Signed contributions that reconstruct the score."
    )
    recommendations: tuple[str, ...] = Field(
        default=(), description="Suggested next actions (deterministic, not prose)."
    )


class ConfidenceAssessment(Schema):
    """The complete confidence evaluation for one requirement.

    Internal to Grounding. Built by a :class:`ConfidenceCalculator` from a
    ``ClassificationResult`` (CAP-077D); consumed by the ``GroundedRequirementBuilder``.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    requirement_id: GroundedRequirementId = Field(..., description="The assessed requirement.")
    confidence_score: int = Field(..., ge=0, le=100, description="Deterministic 0-100 confidence.")
    confidence_band: ConfidenceBand = Field(..., description="Coarse band the score falls into.")
    confidence_components: tuple[ConfidenceComponent, ...] = Field(
        default=(), description="Signed contributions that reconstruct the score."
    )
    confidence_explanation: ConfidenceExplanation = Field(
        ..., description="Structured explanation of the assessment."
    )
    confidence_version: ConfidenceVersion = Field(
        default=CONFIDENCE_VERSION, description="Version of the ConfidenceAssessment schema."
    )
