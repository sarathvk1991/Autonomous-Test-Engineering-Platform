"""Canonical, immutable models for Quality Decision (CAP-080A.3).

Decision is the final governed layer before Governance: it derives the release
decision (``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL``) from a completed
:class:`QualityAssessmentResult` under a governed :class:`DecisionPolicy`. It is the
**sole owner** of the release decision (ADR-0017 §D23, Recommendation 2): Assessment
stays observational and the ``QualityGovernanceService`` only assembles.

Two boundaries meet here:

* :class:`QualityAssessmentResult` — the frozen input (the only thing Decision reads).
* :class:`QualityDecisionResult` — the frozen **runtime contract** between the
  ``QualityDecisionEngine`` and the ``QualityGovernanceService``.

All models follow the repository conventions: immutable, ``frozen``,
``extra="forbid"``, camelCase-serialised, tuple-backed, ``Schema`` base, free of
timestamps/UUIDs. They **compute nothing** — the future engine populates them; the
only logic here is validator *invariants*.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.assessment.models import AssessmentLevel
from requirement_intelligence.quality_governance.identity.quality_identity import (
    DecisionPolicyId,
    DecisionPolicyVersion,
    DecisionVersion,
    QualityAssessmentResultId,
    QualityDecisionResultId,
    QualityDecisionResultVersion,
)
from requirement_intelligence.quality_governance.models.enums import QualityDecision
from shared.contracts.base import Schema

#: Version of the ``DecisionExplanation`` schema (CAP-080A.3 foundation).
DECISION_VERSION = DecisionVersion(1, 0, 0)

#: Version of the ``QualityDecisionResult`` runtime-contract schema (CAP-080A.3).
QUALITY_DECISION_RESULT_VERSION = QualityDecisionResultVersion(1, 0, 0)


class DecisionSummary(Schema):
    """The headline for one release decision. Data only — assembled, not computed.

    ``verdict`` is a one-line statement of the decision; the ``assessment_level`` is the
    observed :class:`AssessmentLevel` the decision was derived from (recorded for audit,
    never re-derived here).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    decision: QualityDecision = Field(..., description="The governed release decision.")
    assessment_level: AssessmentLevel = Field(
        ..., description="The observed assessment level this decision was derived from."
    )
    verdict: str = Field(..., min_length=1, description="One-line statement of the decision.")


class DecisionStatistics(Schema):
    """The numeric breakdown that informed the decision. Data only — assembled."""

    model_config = ConfigDict(alias_generator=to_camel)

    rules_considered: int = Field(..., ge=0, description="Rules the assessment considered.")
    mandatory_failures: int = Field(..., ge=0, description="Failing mandatory-release rules.")
    blocking_failures: int = Field(..., ge=0, description="Failing blocking (severity/mandatory).")
    warnings: int = Field(..., ge=0, description="Warning-severity observations.")
    advisories: int = Field(..., ge=0, description="Advisory observations.")


class DecisionExplanation(Schema):
    """The structured, machine-readable reasoning behind one release decision.

    Deterministic observations only, never generated prose: the primary reason, the
    contributing factors, the governed decision-policy rules that fired, and any
    recommendations. It is the permanent explanation contract for the subsystem —
    together with the result, it makes every decision reconstructable without re-running
    the engine or inspecting any upstream stage (ADR-0017 §D23, Recommendation 3).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    primary_reason: str = Field(
        ..., min_length=1, description="The decisive reason for the outcome."
    )
    contributing_factors: tuple[str, ...] = Field(
        default=(), description="Additional factors that informed the decision."
    )
    applied_rules: tuple[str, ...] = Field(
        default=(), description="Governed decision-policy rules that fired, in order."
    )
    recommendations: tuple[str, ...] = Field(
        default=(), description="Governed recommendations attached to the decision."
    )
    decision_version: DecisionVersion = Field(
        default=DECISION_VERSION, description="Version of the DecisionExplanation schema."
    )


class QualityDecisionResult(Schema):
    """The frozen runtime contract between Quality Decision and Quality Governance.

    ``QualityDecisionResult`` is the canonical, self-contained release decision for one
    run — the ``QualityDecision``, its summary, statistics, structured explanation, and
    the governing policy identity/version, tied to the assessment it decided from. It is
    the **permanent decision boundary** (ADR-0017 §D23): the ``QualityGovernanceService``
    assembles the final ``QualityGovernanceResult`` from it and never re-derives the
    decision.

    Every future ``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL`` must be reconstructable
    from this object alone — no re-running the engine, and no inspecting the policy,
    Assessment, Rule Evaluation, Grounding, Validation, or CP1 (Recommendation 3).

    Deterministic, versioned independently, and round-trips. It is **not** an execution
    artifact, a report, or a governance result.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    decision_id: QualityDecisionResultId = Field(..., description="Deterministic decision id.")
    assessment_id: QualityAssessmentResultId = Field(
        ..., description="Id of the QualityAssessmentResult this decides from."
    )
    analysis_id: str = Field(..., min_length=1, description="The analysis this decides.")
    execution_id: str = Field(..., min_length=1, description="The AI invocation this decides.")
    decision: QualityDecision = Field(..., description="The governed release decision.")
    summary: DecisionSummary = Field(..., description="The headline decision summary.")
    statistics: DecisionStatistics = Field(..., description="The numeric breakdown.")
    explanation: DecisionExplanation = Field(..., description="The structured decision reasoning.")
    policy_id: DecisionPolicyId = Field(..., description="Identity of the governing policy.")
    policy_version: DecisionPolicyVersion = Field(
        ..., description="Version of the governing decision policy."
    )
    result_version: QualityDecisionResultVersion = Field(
        default=QUALITY_DECISION_RESULT_VERSION,
        description="Version of the QualityDecisionResult runtime-contract schema.",
    )

    @model_validator(mode="after")
    def _validate_result(self) -> QualityDecisionResult:
        """The summary decision must match the result's — a consistency invariant only."""
        if self.summary.decision != self.decision:
            raise ValueError(
                f"Summary decision '{self.summary.decision}' does not match result "
                f"decision '{self.decision}'."
            )
        return self
