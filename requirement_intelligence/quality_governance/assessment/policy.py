"""The canonical governed :class:`AssessmentPolicy`.

An ``AssessmentPolicy`` defines **how a completed rule evaluation is interpreted** —
the interpretation precedence, how mandatory / failure / warning / advisory rules and
conflicts are handled, the assessment weighting, and whether recommendations are
emitted. It is the Quality Assessment counterpart to the ``QualityPolicy`` and the
grounding ``MatchingPolicy``: an immutable, declarative, governed rule set that
contains **no executable logic**. The engine reads a policy and interprets; the policy
computes nothing.

Policy vs engine (frozen, ADR-0017 §D21)
----------------------------------------
* ``AssessmentPolicy`` — the governed interpretation rules (this file). Data only.
* The future ``QualityAssessmentEngine`` — the behaviour that applies them to a
  ``RuleEvaluationResult``.

Tuning interpretation is a *versioned policy change* under the golden re-baseline
procedure, never an engine code change, and it must never force a change to
``QualityAssessmentResult`` or the engine contract (ADR-0017 Recommendation 4).

Interpretation, never decision (frozen, ADR-0017 Recommendation 1)
------------------------------------------------------------------
An ``AssessmentPolicy`` governs how observations are *interpreted*, never how a
release is *decided*. It carries no ``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL``
mapping — that governed mapping belongs to the future Decision layer's policy
(ADR-0017 §D22).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.evaluation.models import RuleCategory
from requirement_intelligence.quality_governance.identity.quality_identity import (
    AssessmentPolicyId,
    AssessmentPolicyVersion,
)
from shared.contracts.base import Schema

#: Version of the governed assessment policy shape / default (CAP-080A.2 foundation).
ASSESSMENT_POLICY_VERSION = AssessmentPolicyVersion(1, 0, 0)

#: The identity of the framework's default governed assessment policy.
DEFAULT_ASSESSMENT_POLICY_ID = AssessmentPolicyId("default-assessment-policy")


class AssessmentConflictPolicy(StrEnum):
    """How the interpretation resolves rules that disagree across dimensions.

    ``MANDATORY_WINS`` — a failing mandatory-release rule dominates any other signal.
    ``SEVERITY_WINS`` — the highest severity present dominates. ``PRECEDENCE_WINS`` —
    the first category in :attr:`AssessmentPolicy.precedence` dominates. Data only; the
    engine applies it, the policy declares it.
    """

    MANDATORY_WINS = "mandatory_wins"
    SEVERITY_WINS = "severity_wins"
    PRECEDENCE_WINS = "precedence_wins"


class AssessmentWeights(Schema):
    """Governed relative weights for the assessment roll-up. Data only.

    Weights the future engine may use when composing an observed level; the policy
    performs no arithmetic. They are governed integers, tuned as a versioned policy
    change.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    mandatory_weight: int = Field(..., ge=0, description="Weight of a mandatory-rule failure.")
    failure_weight: int = Field(..., ge=0, description="Weight of a failure-severity failure.")
    warning_weight: int = Field(..., ge=0, description="Weight of a warning-severity failure.")
    advisory_weight: int = Field(..., ge=0, description="Weight of an advisory failure.")


class AssessmentPolicy(Schema):
    """An immutable, declarative, governed rule set for interpreting a rule evaluation."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: AssessmentPolicyId = Field(..., description="Governed policy identity.")
    policy_version: AssessmentPolicyVersion = Field(..., description="Semantic policy version.")
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    precedence: tuple[RuleCategory, ...] = Field(
        ..., description="Interpretation precedence over rule categories (governed order)."
    )
    conflict_resolution: AssessmentConflictPolicy = Field(
        ..., description="How disagreeing signals are resolved."
    )
    weights: AssessmentWeights = Field(..., description="Governed roll-up weights.")

    mandatory_failure_is_blocking: bool = Field(
        default=True,
        description="Treat a failing mandatory-release rule as a blocking observation.",
    )
    failure_severity_is_blocking: bool = Field(
        default=True, description="Treat a failing failure-severity rule as a blocking observation."
    )
    treat_advisory_as_warning: bool = Field(
        default=False, description="Interpret a failing advisory rule as a warning observation."
    )
    include_skipped_as_warning: bool = Field(
        default=False, description="Interpret a skipped rule as a warning observation."
    )
    emit_recommendations: bool = Field(
        default=True, description="Whether the assessment attaches recommendations."
    )
