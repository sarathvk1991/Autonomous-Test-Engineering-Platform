"""The governed :class:`ConfidencePolicy` and its builder.

A ``ConfidencePolicy`` defines **how confident a verdict should make us** — the base
scores per support classification, the bonuses and penalties, the maximum, and the band
thresholds. Like ``MatchingPolicy`` / ``ClassificationPolicy`` / ``OrchestrationPolicy``
it is immutable, declarative, governed **data** with no executable logic; a
:class:`ConfidenceCalculator` reads it and computes.

CAP-077C.1 ships the governed shape and defaults; **no calculator applies them yet**
(the deterministic calculator lands in CAP-077D). Tuning confidence is a versioned
policy change, never a calculator code change.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity import (
    ConfidencePolicyId,
    ConfidencePolicyVersion,
)
from shared.contracts.base import Schema

#: Version of the governed confidence policy shape / default.
CONFIDENCE_POLICY_VERSION = ConfidencePolicyVersion(1, 0, 0)

#: Identity of the framework's default governed confidence policy.
DEFAULT_CONFIDENCE_POLICY_ID = ConfidencePolicyId("default-confidence-policy")


class ConfidenceBaseScores(Schema):
    """The base confidence each support classification starts from."""

    model_config = ConfigDict(alias_generator=to_camel)

    supported: int = Field(default=80, ge=0, le=100)
    partially_supported: int = Field(default=55, ge=0, le=100)
    weakly_supported: int = Field(default=30, ge=0, le=100)
    unsupported: int = Field(default=0, ge=0, le=100)
    contradicted: int = Field(default=0, ge=0, le=100)
    unknown: int = Field(default=0, ge=0, le=100)


class ConfidenceBonuses(Schema):
    """Governed bonuses a calculator may add. Values only — no logic."""

    model_config = ConfigDict(alias_generator=to_camel)

    support_bonus: int = Field(default=0, ge=0, description="Per additional supporting link.")
    cross_source_bonus: int = Field(default=0, ge=0, description="Evidence spans multiple systems.")
    evidence_count_bonus: int = Field(default=0, ge=0, description="Per additional evidence item.")


class ConfidencePenalties(Schema):
    """Governed penalties a calculator may subtract. Values only — no logic."""

    model_config = ConfigDict(alias_generator=to_camel)

    conflict_penalty: int = Field(default=0, ge=0, description="Per conflicting link.")
    unknown_penalty: int = Field(default=0, ge=0, description="Applied to an UNKNOWN verdict.")


class ConfidenceBandThresholds(Schema):
    """The score boundaries between HIGH / MEDIUM / LOW confidence bands."""

    model_config = ConfigDict(alias_generator=to_camel)

    high_min: int = Field(default=75, ge=0, le=100, description="Lowest score that is HIGH.")
    medium_min: int = Field(default=40, ge=0, le=100, description="Lowest score that is MEDIUM.")


class ConfidencePolicy(Schema):
    """An immutable, declarative, governed rule set for confidence scoring."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: ConfidencePolicyId = Field(..., description="Governed policy identity.")
    policy_version: ConfidencePolicyVersion = Field(..., description="Semantic policy version.")
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    base_scores: ConfidenceBaseScores = Field(..., description="Base score per classification.")
    bonuses: ConfidenceBonuses = Field(..., description="Governed bonuses.")
    penalties: ConfidencePenalties = Field(..., description="Governed penalties.")
    band_thresholds: ConfidenceBandThresholds = Field(..., description="Band boundaries.")
    max_score: int = Field(default=100, ge=0, le=100, description="Confidence ceiling.")


class ConfidencePolicyBuilder:
    """Assemble the governed default :class:`ConfidencePolicy`."""

    def build(self) -> ConfidencePolicy:
        """Return the framework's default governed confidence policy."""
        return ConfidencePolicy(
            policy_id=DEFAULT_CONFIDENCE_POLICY_ID,
            policy_version=CONFIDENCE_POLICY_VERSION,
            description="Default confidence policy (CAP-077C.1): governed scoring foundation.",
            base_scores=ConfidenceBaseScores(),
            bonuses=ConfidenceBonuses(),
            penalties=ConfidencePenalties(),
            band_thresholds=ConfidenceBandThresholds(),
        )


def default_confidence_policy() -> ConfidencePolicy:
    """Return the framework's default governed confidence policy."""
    return ConfidencePolicyBuilder().build()
