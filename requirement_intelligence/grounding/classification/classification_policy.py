"""The governed :class:`ClassificationPolicy` and its builder.

A ``ClassificationPolicy`` defines **what verdict the evidence warrants** — the score
thresholds, the relation-to-role mapping, the precedence order, conflict handling, and
unknown handling. Like ``MatchingPolicy`` / ``OrchestrationPolicy`` it is immutable,
declarative, governed **data** with no executable logic; the
:class:`SupportClassificationEngine` reads it and classifies.

Policy vs configuration vs algorithm
------------------------------------
* ``MatchingPolicy`` — what constitutes a *match* (matcher-scoped).
* ``ClassificationPolicy`` — what constitutes *support* (classifier-scoped).
* ``SupportClassificationEngine`` — the algorithm that applies the policy to a
  ``MatchResult``.

Tuning classification is a versioned policy change, never an engine code change.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity import (
    ClassificationPolicyId,
    ClassificationPolicyVersion,
)
from requirement_intelligence.grounding.models.enums import EvidenceRelation, SupportClassification
from shared.contracts.base import Schema

#: Version of the governed classification policy shape / default.
CLASSIFICATION_POLICY_VERSION = ClassificationPolicyVersion(1, 0, 0)

#: Identity of the framework's default governed classification policy.
DEFAULT_CLASSIFICATION_POLICY_ID = ClassificationPolicyId("default-classification-policy")

#: The default precedence: strongest verdict first, so the engine picks the highest
#: applicable classification. Mirrors the CAP-077A.5 support-classification ordering.
_DEFAULT_PRIORITY = (
    SupportClassification.CONTRADICTED,
    SupportClassification.SUPPORTED,
    SupportClassification.PARTIALLY_SUPPORTED,
    SupportClassification.WEAKLY_SUPPORTED,
    SupportClassification.UNKNOWN,
    SupportClassification.UNSUPPORTED,
)


class ClassificationThresholds(Schema):
    """The minimum top match scores each verdict requires."""

    model_config = ConfigDict(alias_generator=to_camel)

    supported_min_score: int = Field(
        default=10, ge=0, le=100, description="Top support score required for SUPPORTED."
    )
    partially_supported_min_score: int = Field(
        default=5, ge=0, le=100, description="Top support score required for PARTIALLY_SUPPORTED."
    )
    weakly_supported_min_score: int = Field(
        default=0, ge=0, le=100, description="Top support score required for WEAKLY_SUPPORTED."
    )
    contradiction_min_score: int = Field(
        default=1, ge=0, le=100, description="Top conflict score required for CONTRADICTED."
    )


class ClassificationPolicy(Schema):
    """An immutable, declarative, governed rule set for support classification."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: ClassificationPolicyId = Field(..., description="Governed policy identity.")
    policy_version: ClassificationPolicyVersion = Field(..., description="Semantic policy version.")
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    thresholds: ClassificationThresholds = Field(..., description="Per-verdict score thresholds.")

    strong_support_relations: tuple[EvidenceRelation, ...] = Field(
        default=(EvidenceRelation.DIRECT, EvidenceRelation.CORROBORATING),
        description="Relations counted as strong support.",
    )
    partial_support_relations: tuple[EvidenceRelation, ...] = Field(
        default=(EvidenceRelation.PARTIAL,), description="Relations counted as partial support."
    )
    weak_support_relations: tuple[EvidenceRelation, ...] = Field(
        default=(EvidenceRelation.DERIVED,), description="Relations counted as weak support."
    )
    conflict_relations: tuple[EvidenceRelation, ...] = Field(
        default=(EvidenceRelation.CONTRADICTING, EvidenceRelation.NEGATIVE),
        description="Relations counted as conflict.",
    )

    priority_ordering: tuple[SupportClassification, ...] = Field(
        default=_DEFAULT_PRIORITY, min_length=1, description="Verdict precedence, strongest first."
    )
    permitted_classifications: tuple[SupportClassification, ...] = Field(
        default=_DEFAULT_PRIORITY, min_length=1, description="Verdicts the engine may emit."
    )
    contradiction_overrides_support: bool = Field(
        default=True, description="Whether conflict outranks support when both are present."
    )
    treat_absent_evidence_as_unknown: bool = Field(
        default=True,
        description="Classify UNKNOWN (not UNSUPPORTED) when no evidence was examined.",
    )


class ClassificationPolicyBuilder:
    """Assemble the governed default :class:`ClassificationPolicy`."""

    def build(self) -> ClassificationPolicy:
        """Return the framework's default governed classification policy."""
        return ClassificationPolicy(
            policy_id=DEFAULT_CLASSIFICATION_POLICY_ID,
            policy_version=CLASSIFICATION_POLICY_VERSION,
            description="Default classification policy (CAP-077C): governed support verdicts.",
            thresholds=ClassificationThresholds(),
        )


def default_classification_policy() -> ClassificationPolicy:
    """Return the framework's default governed classification policy."""
    return ClassificationPolicyBuilder().build()
