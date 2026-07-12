"""Canonical, immutable models for Quality Assessment (CAP-080A.2).

Assessment is the layer *between* Rule Evaluation and Quality Governance: it
interprets a completed :class:`RuleEvaluationResult` into an
:class:`QualityAssessmentResult` of **observations only** — never a release decision
(``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL``), which is reserved for the future
Decision layer (ADR-0017 §D21/D22, Recommendation 1).

Two boundaries meet here:

* :class:`RuleEvaluationResult` — the frozen input (the only thing assessment reads).
* :class:`QualityAssessmentResult` — the frozen **runtime contract** between the
  ``QualityAssessmentEngine`` and the ``QualityGovernanceService``.

All models follow the repository conventions: immutable, ``frozen``,
``extra="forbid"``, camelCase-serialised, tuple-backed, ``Schema`` base, free of
timestamps/UUIDs. They **compute nothing** — the future engine populates them; the
only logic here is validator *invariants*.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.evaluation.models import RuleEvaluationStatus
from requirement_intelligence.quality_governance.identity.quality_identity import (
    AssessmentOutcomeVersion,
    AssessmentPolicyId,
    AssessmentPolicyVersion,
    QualityAssessmentResultId,
    QualityAssessmentResultVersion,
    RuleEvaluationId,
    RuleEvaluationResultId,
)
from requirement_intelligence.quality_governance.models.enums import QualitySeverity
from shared.contracts.base import Schema

#: Version of the ``AssessmentOutcome`` schema (CAP-080A.2 foundation).
ASSESSMENT_OUTCOME_VERSION = AssessmentOutcomeVersion(1, 0, 0)

#: Version of the ``QualityAssessmentResult`` runtime-contract schema (CAP-080A.2).
QUALITY_ASSESSMENT_RESULT_VERSION = QualityAssessmentResultVersion(1, 0, 0)


class AssessmentLevel(StrEnum):
    """The observed state of one run's rule evaluations — **not** a release decision.

    A level describes *what the evaluations look like*, never *what to do about it*.
    Mapping a level (plus policy) to a ``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL``
    decision is the future Decision layer's job (ADR-0017 §D22, Recommendation 2): a
    ``FAILURES_PRESENT`` level may still be released if the failed rules are advisory,
    and a ``CLEAN`` level is not itself a ``PASS``.

    ``CLEAN`` — no failing rule of any severity. ``ADVISORY_ONLY`` — the only failing
    rules are advisory. ``WARNINGS_PRESENT`` — warning-severity rules failed but no
    blocking rule did. ``FAILURES_PRESENT`` — at least one blocking (failure-severity
    or mandatory) rule failed.
    """

    CLEAN = "clean"
    ADVISORY_ONLY = "advisory_only"
    WARNINGS_PRESENT = "warnings_present"
    FAILURES_PRESENT = "failures_present"


class AssessmentDistributionEntry(Schema):
    """One labelled count in an assessment distribution — a generic (label, count) pair."""

    model_config = ConfigDict(alias_generator=to_camel)

    label: str = Field(..., min_length=1, description="The dimension value being counted.")
    count: int = Field(..., ge=0, description="Rules observed for this label.")


class AssessmentFindingReference(Schema):
    """A reference from the assessment to one evaluated rule that informed it.

    A *reference*, not a copy: it points at a :class:`RuleEvaluation` by its
    deterministic id and carries just enough (rule id, severity, status, a note) to
    explain why the assessment cited it, without duplicating the evaluation. The full
    evaluation remains in the consumed ``RuleEvaluationResult``.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    evaluation_id: RuleEvaluationId = Field(
        ..., description="Id of the referenced rule evaluation."
    )
    rule_id: str = Field(..., min_length=1, description="Stable id of the referenced rule.")
    severity: QualitySeverity = Field(..., description="Severity the referenced rule carries.")
    status: RuleEvaluationStatus = Field(..., description="Outcome of the referenced rule.")
    note: str = Field(..., min_length=1, description="Why the assessment references this rule.")


class AssessmentSummary(Schema):
    """The headline counts for one assessment. Data only — assembled, not computed.

    ``verdict`` is a one-line *observation* of the evaluation state, never a release
    decision (Recommendation 1).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    total_rules: int = Field(..., ge=0, description="Rules considered by the assessment.")
    passed: int = Field(..., ge=0, description="Rules observed passing.")
    failed: int = Field(..., ge=0, description="Rules observed failing.")
    skipped: int = Field(..., ge=0, description="Rules observed skipped.")
    mandatory_failures: int = Field(..., ge=0, description="Failing mandatory-release rules.")
    warnings: int = Field(..., ge=0, description="Failing warning-severity rules.")
    advisories: int = Field(..., ge=0, description="Failing advisory rules.")
    verdict: str = Field(..., min_length=1, description="One-line observation (not a decision).")


class AssessmentStatistics(Schema):
    """Distributions over the assessed rules. Data only — assembled, not computed."""

    model_config = ConfigDict(alias_generator=to_camel)

    category_distribution: tuple[AssessmentDistributionEntry, ...] = Field(
        default=(), description="Assessed-rule counts by category."
    )
    severity_distribution: tuple[AssessmentDistributionEntry, ...] = Field(
        default=(), description="Assessed-rule counts by severity."
    )
    status_distribution: tuple[AssessmentDistributionEntry, ...] = Field(
        default=(), description="Assessed-rule counts by evaluation status."
    )


class AssessmentOutcome(Schema):
    """The overall interpreted observation for one run — **not** a release decision.

    Carries the observed :class:`AssessmentLevel`, whether a blocking rule failed, the
    mandatory-failure count, and a one-line observation. It records *what was observed*
    so the future Decision layer can derive a release decision from it and the policy
    (ADR-0017 §D22).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    level: AssessmentLevel = Field(..., description="Observed state of the evaluations.")
    has_blocking_failure: bool = Field(
        ..., description="Whether any blocking (failure-severity or mandatory) rule failed."
    )
    mandatory_failure_count: int = Field(..., ge=0, description="Failing mandatory-release rules.")
    summary_text: str = Field(
        ..., min_length=1, description="One-line observation (not a decision)."
    )
    outcome_version: AssessmentOutcomeVersion = Field(
        default=ASSESSMENT_OUTCOME_VERSION, description="Version of the AssessmentOutcome schema."
    )

    @model_validator(mode="after")
    def _validate_outcome(self) -> AssessmentOutcome:
        """The observed level must be consistent with the blocking-failure observation."""
        if self.mandatory_failure_count > 0 and not self.has_blocking_failure:
            raise ValueError("A mandatory failure implies has_blocking_failure is True.")
        if self.has_blocking_failure and AssessmentLevel(self.level) is not (
            AssessmentLevel.FAILURES_PRESENT
        ):
            raise ValueError("A blocking failure requires level FAILURES_PRESENT.")
        return self


class QualityAssessmentResult(Schema):
    """The frozen runtime contract between Quality Assessment and Quality Governance.

    ``QualityAssessmentResult`` is the canonical, self-contained interpretation of one
    :class:`RuleEvaluationResult` — the overall outcome, the summary, statistics, and
    references to the rules that informed it. It is the **permanent assessment
    boundary** (ADR-0017 §D21): the ``QualityGovernanceService`` consumes it (via the
    future Decision layer), and it carries **no** release decision, quality score, or
    governance summary — those belong to later layers (Recommendation 1/4).

    Deterministic, versioned independently, and round-trips. It is **not** an execution
    artifact, a report, or a governance result.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    assessment_id: QualityAssessmentResultId = Field(
        ..., description="Deterministic assessment id."
    )
    rule_evaluation_result_id: RuleEvaluationResultId = Field(
        ..., description="Id of the RuleEvaluationResult this interprets."
    )
    analysis_id: str = Field(..., min_length=1, description="The analysis this assesses.")
    execution_id: str = Field(..., min_length=1, description="The AI invocation this assesses.")
    references: tuple[AssessmentFindingReference, ...] = Field(
        default=(), description="References to the evaluated rules that informed the assessment."
    )
    assessment_summary: AssessmentSummary = Field(..., description="The headline summary.")
    assessment_statistics: AssessmentStatistics = Field(
        ..., description="Assessment distributions."
    )
    overall_assessment: AssessmentOutcome = Field(
        ..., description="The overall interpreted outcome."
    )
    policy_id: AssessmentPolicyId = Field(..., description="Identity of the governing policy.")
    policy_version: AssessmentPolicyVersion = Field(
        ..., description="Version of the governing assessment policy."
    )
    result_version: QualityAssessmentResultVersion = Field(
        default=QUALITY_ASSESSMENT_RESULT_VERSION,
        description="Version of the QualityAssessmentResult runtime-contract schema.",
    )

    @model_validator(mode="after")
    def _validate_result(self) -> QualityAssessmentResult:
        """Summary internal consistency and unique references — no value is computed."""
        if self.assessment_summary.total_rules != (
            self.assessment_summary.passed
            + self.assessment_summary.failed
            + self.assessment_summary.skipped
        ):
            raise ValueError("Summary passed+failed+skipped must equal total_rules.")
        ids = [str(ref.evaluation_id) for ref in self.references]
        if len(ids) != len(set(ids)):
            raise ValueError("Assessment references must have unique evaluation ids.")
        if (
            self.overall_assessment.mandatory_failure_count
            != self.assessment_summary.mandatory_failures
        ):
            raise ValueError(
                "Outcome mandatory_failure_count must match summary mandatory_failures."
            )
        return self
