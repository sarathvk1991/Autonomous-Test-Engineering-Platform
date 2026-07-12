"""Canonical, immutable models for Quality Rule Evaluation (CAP-080A.1).

Rule Evaluation is the layer *between* the governed ``QualityPolicy`` and the
governance decision: it evaluates each governed rule against the completed upstream
results and records **observations only** — never a quality score, a release
decision, or a governance summary (ADR-0017 Recommendation 4 / D18).

Two canonical models carry it:

* :class:`RuleEvaluation` — one evaluated governance rule (its status and the values
  that explain it).
* :class:`RuleEvaluationResult` — the frozen **runtime contract** between the
  ``QualityRuleEvaluator`` and the ``QualityGovernanceService`` (ADR-0017 D19).

All models follow the repository conventions: immutable, ``frozen``,
``extra="forbid"``, camelCase-serialised, tuple-backed, ``Schema`` base, and free of
timestamps/UUIDs on the value objects. They **compute nothing** — the future
evaluator populates them; the only logic here is validator *invariants*.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityPolicyVersion,
    QualityRuleEvaluatorVersion,
    RuleEvaluationId,
    RuleEvaluationResultId,
    RuleEvaluationResultVersion,
    RuleEvaluationVersion,
)
from requirement_intelligence.quality_governance.models.enums import QualitySeverity
from shared.contracts.base import Schema

#: Version of the ``RuleEvaluation`` schema (CAP-080A.1 foundation).
RULE_EVALUATION_VERSION = RuleEvaluationVersion(1, 0, 0)

#: Version of the ``RuleEvaluationResult`` runtime-contract schema. Advanced additively
#: to 1.1.0 by CAP-080B: the boundary now records the evaluator identity
#: (``evaluator_name`` / ``evaluator_version``) that produced it. The addition is
#: backwards-compatible — both fields default — so every CAP-080A.1 construction and
#: serialization remains valid.
RULE_EVALUATION_RESULT_VERSION = RuleEvaluationResultVersion(1, 1, 0)

#: The default evaluator identity carried by a result. Populated by the evaluator that
#: produced it (CAP-080B ships ``deterministic_quality_rule_v1``); defaults keep the
#: CAP-080A.1 constructions valid and let a result name its producer independently of
#: the policy and schema versions (ADR-0017 Recommendation 5).
DEFAULT_RULE_EVALUATOR_NAME = "deterministic_quality_rule_v1"
DEFAULT_RULE_EVALUATOR_VERSION = QualityRuleEvaluatorVersion(1, 0, 0)


class RuleCategory(StrEnum):
    """The governed category of a quality rule (frozen, ADR-0017 Recommendation 1).

    Future policies **extend** these categories rather than invent new evaluation
    mechanisms. Each category names *which relationship* a rule governs; it implies no
    calculation.
    """

    GROUNDING = "grounding"
    VALIDATION = "validation"
    CP1 = "cp1"
    CROSS_SUBSYSTEM = "cross_subsystem"
    MANDATORY_RELEASE = "mandatory_release"
    ADVISORY = "advisory"


class RuleEvaluationStatus(StrEnum):
    """The outcome of evaluating one governance rule.

    ``PASS`` — the rule's condition is satisfied. ``FAIL`` — it is violated.
    ``SKIPPED`` — the rule could not be evaluated (e.g. the input it governs was
    absent); a skip is distinct from a fail, exactly as grounding's ``UNKNOWN`` is
    distinct from ``UNSUPPORTED``.
    """

    PASS = "pass"  # noqa: S105 — an evaluation status, not a secret
    FAIL = "fail"
    SKIPPED = "skipped"


class RuleCategoryCount(Schema):
    """The count of evaluated rules in one category — a distribution entry."""

    model_config = ConfigDict(alias_generator=to_camel)

    category: RuleCategory = Field(..., description="The rule category.")
    count: int = Field(..., ge=0, description="Rules evaluated in this category.")


class RuleSeverityCount(Schema):
    """The count of evaluated rules at one severity — a distribution entry."""

    model_config = ConfigDict(alias_generator=to_camel)

    severity: QualitySeverity = Field(..., description="The rule severity.")
    count: int = Field(..., ge=0, description="Rules evaluated at this severity.")


class RuleEvaluation(Schema):
    """One evaluated governance rule — its status and the values that explain it.

    An observation record: the future evaluator records what the rule expected, what
    it observed, the governed threshold, and a one-line reason. It computes no score
    and makes no decision. ``expected_value`` / ``actual_value`` / ``threshold`` are
    canonical string renderings so the model stays type-agnostic across numeric,
    rate, and verdict rules and serialises deterministically; they are ``None`` when a
    rule (e.g. a ``SKIPPED`` one) has no such value.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    evaluation_id: RuleEvaluationId = Field(..., description="Deterministic per-rule identity.")
    rule_id: str = Field(..., min_length=1, description="Stable identity of the governed rule.")
    rule_name: str = Field(..., min_length=1, description="Human-readable rule name.")
    category: RuleCategory = Field(..., description="The governed rule category.")
    severity: QualitySeverity = Field(..., description="Severity a violation carries.")
    status: RuleEvaluationStatus = Field(..., description="The evaluation outcome.")
    expected_value: str | None = Field(
        default=None, description="What the rule expected (canonical string), if any."
    )
    actual_value: str | None = Field(
        default=None, description="What was observed (canonical string), if any."
    )
    threshold: str | None = Field(
        default=None, description="The governed bound compared against (canonical string), if any."
    )
    reason: str = Field(..., min_length=1, description="One-line explanation of the outcome.")
    evaluation_version: RuleEvaluationVersion = Field(
        default=RULE_EVALUATION_VERSION, description="Version of the RuleEvaluation schema."
    )


class RuleEvaluationSummary(Schema):
    """The headline counts for one evaluation run. Data only — assembled, not computed."""

    model_config = ConfigDict(alias_generator=to_camel)

    total_rules: int = Field(..., ge=0, description="Total rules evaluated.")
    passed: int = Field(..., ge=0, description="Rules with status PASS.")
    failed: int = Field(..., ge=0, description="Rules with status FAIL.")
    skipped: int = Field(..., ge=0, description="Rules with status SKIPPED.")
    verdict: str = Field(..., min_length=1, description="One-line evaluation-run verdict.")


class RuleEvaluationStatistics(Schema):
    """Distributions over the evaluated rules. Data only — assembled, not computed."""

    model_config = ConfigDict(alias_generator=to_camel)

    mandatory_rules_evaluated: int = Field(..., ge=0, description="Mandatory-release rules seen.")
    advisory_rules_evaluated: int = Field(..., ge=0, description="Advisory rules seen.")
    category_distribution: tuple[RuleCategoryCount, ...] = Field(
        default=(), description="Evaluated-rule counts by category."
    )
    severity_distribution: tuple[RuleSeverityCount, ...] = Field(
        default=(), description="Evaluated-rule counts by severity."
    )


class RuleEvaluationResult(Schema):
    """The frozen runtime contract between Rule Evaluation and Quality Governance.

    ``RuleEvaluationResult`` is the canonical, self-contained record of one evaluation
    run — every :class:`RuleEvaluation`, the headline summary, the statistics, and the
    governing policy version. It is the **permanent evaluation boundary** (ADR-0017
    D19): the ``QualityGovernanceService`` consumes only this, and every future
    governance decision must be explainable from it alone — with no need to re-run
    evaluation or inspect a policy, runtime service, Grounding, Validation, or CP1
    (ADR-0017 Recommendation 3 / D20).

    It is **not** an execution artifact, and it carries **no** quality score, release
    decision, or governance summary — those belong to later layers (ADR-0017
    Recommendation 4). Deterministic, versioned independently, and round-trips.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    result_id: RuleEvaluationResultId = Field(..., description="Deterministic evaluation-run id.")
    analysis_id: str = Field(..., min_length=1, description="The analysis this evaluates.")
    execution_id: str = Field(..., min_length=1, description="The AI invocation this evaluates.")
    evaluations: tuple[RuleEvaluation, ...] = Field(
        default=(), description="Every governance rule evaluated for this run."
    )
    summary: RuleEvaluationSummary = Field(..., description="The headline evaluation summary.")
    statistics: RuleEvaluationStatistics = Field(..., description="Evaluation distributions.")
    policy_version: QualityPolicyVersion = Field(
        ..., description="Version of the QualityPolicy whose rules were evaluated."
    )
    evaluator_name: str = Field(
        default=DEFAULT_RULE_EVALUATOR_NAME,
        min_length=1,
        description="Stable name of the evaluator that produced this result.",
    )
    evaluator_version: QualityRuleEvaluatorVersion = Field(
        default=DEFAULT_RULE_EVALUATOR_VERSION,
        description="Version of the evaluator that produced this result.",
    )
    result_version: RuleEvaluationResultVersion = Field(
        default=RULE_EVALUATION_RESULT_VERSION,
        description="Version of the RuleEvaluationResult runtime-contract schema.",
    )

    @model_validator(mode="after")
    def _validate_result(self) -> RuleEvaluationResult:
        """Summary counts and evaluation identities must agree with the evaluations.

        A consistency invariant only — no value is computed. It guarantees a
        governance decision is auditable from this record alone (ADR-0017 Rec 3).
        """
        ids = [str(e.evaluation_id) for e in self.evaluations]
        if len(ids) != len(set(ids)):
            raise ValueError("Evaluations must have unique evaluation ids.")

        passed = sum(1 for e in self.evaluations if e.status == RuleEvaluationStatus.PASS)
        failed = sum(1 for e in self.evaluations if e.status == RuleEvaluationStatus.FAIL)
        skipped = sum(1 for e in self.evaluations if e.status == RuleEvaluationStatus.SKIPPED)
        if self.summary.total_rules != len(self.evaluations):
            raise ValueError(
                f"Summary total_rules {self.summary.total_rules} does not match "
                f"{len(self.evaluations)} evaluations."
            )
        if (self.summary.passed, self.summary.failed, self.summary.skipped) != (
            passed,
            failed,
            skipped,
        ):
            raise ValueError(
                "Summary pass/fail/skip counts do not match the evaluations' statuses: "
                f"passed={passed}, failed={failed}, skipped={skipped}."
            )
        return self
