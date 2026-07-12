"""The canonical governed :class:`DecisionPolicy`.

A ``DecisionPolicy`` defines **how a completed assessment becomes a release decision**
— the governed base mapping from an observed :class:`AssessmentLevel` to a
:class:`QualityDecision`, plus the mandatory gates that can force ``FAIL`` regardless
of that mapping. It is the Quality Decision counterpart to the ``AssessmentPolicy`` and
the ``QualityPolicy``: an immutable, declarative, governed rule set that contains **no
executable logic**. The engine reads a policy and decides; the policy computes nothing.

Decision behaviour is governed *entirely* by this policy (ADR-0017 Recommendation 4):
the future ``QualityDecisionEngine`` hard-codes no threshold and no mapping.

Rule-based, not a bare mapping (frozen, ADR-0017 §D23)
-----------------------------------------------------
The decision is not a simple ``AssessmentLevel → QualityDecision`` lookup. The
``level_mapping`` is the governed *base*, and the mandatory gates
(``fail_on_blocking_failure`` / ``fail_on_mandatory_failure``) can override it to
``FAIL`` — so a non-``FAILURES_PRESENT`` level can still ``FAIL`` on a mandatory gate,
and the governed mapping alone never becomes a percentage.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.assessment.models import AssessmentLevel
from requirement_intelligence.quality_governance.identity.quality_identity import (
    DecisionPolicyId,
    DecisionPolicyVersion,
)
from requirement_intelligence.quality_governance.models.enums import QualityDecision
from shared.contracts.base import Schema

#: Version of the governed decision policy shape / default (CAP-080A.3 foundation).
DECISION_POLICY_VERSION = DecisionPolicyVersion(1, 0, 0)

#: The identity of the framework's default governed decision policy.
DEFAULT_DECISION_POLICY_ID = DecisionPolicyId("default-decision-policy")


class DecisionRule(Schema):
    """One governed mapping from an observed assessment level to a base decision.

    Data only: it declares *what decision a level maps to*, before mandatory gates are
    applied. The engine reads it; the rule performs no evaluation.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    level: AssessmentLevel = Field(..., description="The observed assessment level.")
    decision: QualityDecision = Field(..., description="The base decision this level maps to.")
    note: str = Field(..., min_length=1, description="Rationale for the mapping.")


class DecisionPolicy(Schema):
    """An immutable, declarative, governed rule set for deriving a release decision."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: DecisionPolicyId = Field(..., description="Governed policy identity.")
    policy_version: DecisionPolicyVersion = Field(..., description="Semantic policy version.")
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    level_mapping: tuple[DecisionRule, ...] = Field(
        ..., description="Governed base mapping from assessment level to decision."
    )
    fail_on_blocking_failure: bool = Field(
        default=True, description="Force FAIL when a blocking (severity/mandatory) rule failed."
    )
    fail_on_mandatory_failure: bool = Field(
        default=True, description="Force FAIL when a mandatory-release rule failed."
    )
    warn_on_advisory: bool = Field(
        default=False, description="Map an advisory-only observation to PASS_WITH_WARNINGS."
    )
    emit_recommendations: bool = Field(
        default=True, description="Whether the decision attaches recommendations."
    )

    @model_validator(mode="after")
    def _validate_policy(self) -> DecisionPolicy:
        """The base mapping must cover each assessment level exactly once."""
        levels = [AssessmentLevel(rule.level) for rule in self.level_mapping]
        if len(levels) != len(set(levels)):
            raise ValueError("level_mapping must not map an assessment level twice.")
        if set(levels) != set(AssessmentLevel):
            raise ValueError("level_mapping must cover every AssessmentLevel exactly once.")
        return self
