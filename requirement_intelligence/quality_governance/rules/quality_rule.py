"""The canonical governed :class:`QualityRule` and its controlled vocabularies (CAP-080B).

A ``QualityRule`` is **metadata only** — the governed declaration of *what* a quality
rule evaluates, *which* governed threshold bounds it, and *how* a violation is
classified. It carries **no executable behaviour**: no lambda, no callable, no
comparison, no threshold value. The :class:`DeterministicQualityRuleEvaluator` owns the
behaviour; a rule only *names* it (ADR-0017 §D25, Recommendation 3/5).

The declaration is fully governed and deterministic:

* :class:`QualityMetric` — the governed quantity a rule observes (the *actual*), read
  from a completed ``GroundingResult`` / ``ValidationResult`` / ``CP1Result``.
* :class:`RuleComparator` — how the observed value is compared.
* :class:`QualityThresholdRef` — *which* governed :class:`QualityPolicy` value is the
  bound (the *threshold*/*expected*). A rule never carries a literal number; it names a
  policy field, so every threshold is governed data (ADR-0017 Recommendation 2).
* :class:`QualityReleaseToggle` — for a mandatory-release rule, the governed policy
  toggle that decides whether the gate is *enforced*; a disabled toggle makes the rule
  ``SKIPPED``, never ``FAIL``.

Because a rule is data, adding, removing, or retuning a rule is a versioned catalogue
change (a ``QualityRuleBuilder`` edit), never an evaluator code change — mirroring the
policy discipline (ADR-0017 Recommendation 2).

All conventions follow the repository: immutable, ``Schema`` base, ``extra="forbid"``,
camelCase-serialised, and free of timestamps/UUIDs. The model **computes nothing**; the
only logic here is validator *invariants*.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.evaluation.models import RuleCategory
from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityRuleVersion,
)
from requirement_intelligence.quality_governance.models.enums import QualitySeverity
from shared.contracts.base import Schema

#: Version of the governed ``QualityRule`` **schema** (CAP-080B foundation).
QUALITY_RULE_VERSION = QualityRuleVersion(1, 0, 0)


class RuleType(StrEnum):
    """The governed kind of a quality rule — descriptive metadata only.

    Classifies *how* a rule reasons, for grouping and explanation. It drives no
    dispatch (the evaluator dispatches on :class:`QualityMetric` / :class:`RuleComparator`);
    it names the rule's shape for a reader and future policy author.
    """

    THRESHOLD = "threshold"  # a numeric minimum/maximum bar
    COUNT = "count"  # a severity/finding count cap
    VERDICT = "verdict"  # an upstream pass/fail verdict gate
    CROSS_LAYER = "cross_layer"  # an anomaly across two subsystems
    MANDATORY_GATE = "mandatory_gate"  # a governed release gate
    ADVISORY = "advisory"  # a non-blocking observation


class QualityMetric(StrEnum):
    """The governed quantity a rule observes — the *actual* value.

    Each member names one deterministic reading from a completed upstream result. The
    evaluator owns the extraction; the rule only names which quantity it governs. New
    metrics are added additively as the governed catalogue grows.
    """

    # Grounding (read from GroundingResult.assessment).
    GROUNDING_SCORE = "grounding_score"
    HALLUCINATION_RATE = "hallucination_rate"
    AVERAGE_CONFIDENCE = "average_confidence"
    EVIDENCE_COVERAGE = "evidence_coverage"

    # Validation (read from ValidationResult.validation_summary / overall_verdict).
    VALIDATION_CRITICAL_COUNT = "validation_critical_count"
    VALIDATION_ERROR_COUNT = "validation_error_count"
    VALIDATION_WARNING_COUNT = "validation_warning_count"
    VALIDATION_INFO_COUNT = "validation_info_count"
    VALIDATION_FAILING_VERDICT = "validation_failing_verdict"

    # CP1 (read from CP1Result.findings / overall_verdict).
    CP1_BLOCKING_FINDINGS = "cp1_blocking_findings"
    CP1_WARN_FINDINGS = "cp1_warn_findings"
    CP1_FAILING_VERDICT = "cp1_failing_verdict"
    ENGINEERING_NOT_READY = "engineering_not_ready"

    # Cross-subsystem anomalies (read from two results at once).
    CROSS_VALIDATION_PASS_GROUNDING_FAIL = "cross_validation_pass_grounding_fail"  # noqa: S105 — a metric name, not a secret
    CROSS_CP1_PASS_GROUNDING_FAIL = "cross_cp1_pass_grounding_fail"  # noqa: S105 — a metric name, not a secret


class RuleComparator(StrEnum):
    """How an observed value is compared to its governed bound.

    ``AT_LEAST`` / ``AT_MOST`` compare a numeric metric to a numeric threshold resolved
    from the policy. ``MUST_NOT_HOLD`` evaluates a boolean condition (a failing verdict,
    an unmet-readiness flag, a cross-layer anomaly) that must be absent for a ``PASS``;
    it needs no numeric threshold.
    """

    AT_LEAST = "at_least"  # PASS when actual >= threshold
    AT_MOST = "at_most"  # PASS when actual <= threshold
    MUST_NOT_HOLD = "must_not_hold"  # PASS when the boolean condition is absent


class QualityThresholdRef(StrEnum):
    """*Which* governed :class:`QualityPolicy` value bounds a rule.

    A rule names a policy field rather than carrying a literal, so every numeric bound
    is governed data tuned by a versioned policy change (ADR-0017 Recommendation 2).
    ``NONE`` is used by boolean (``MUST_NOT_HOLD``) rules, whose acceptable condition is
    inherent to the rule rather than a tunable number.
    """

    NONE = "none"

    # failure_thresholds band.
    FAILURE_MIN_GROUNDING_SCORE = "failure_min_grounding_score"
    FAILURE_MAX_HALLUCINATION_RATE = "failure_max_hallucination_rate"
    FAILURE_MIN_CONFIDENCE = "failure_min_confidence"
    FAILURE_MIN_EVIDENCE_COVERAGE = "failure_min_evidence_coverage"

    # warning_thresholds band.
    WARNING_MIN_GROUNDING_SCORE = "warning_min_grounding_score"
    WARNING_MAX_HALLUCINATION_RATE = "warning_max_hallucination_rate"
    WARNING_MIN_EVIDENCE_COVERAGE = "warning_min_evidence_coverage"

    # validation_severity_thresholds.
    VALIDATION_MAX_CRITICAL = "validation_max_critical"
    VALIDATION_MAX_HIGH = "validation_max_high"
    VALIDATION_MAX_MEDIUM = "validation_max_medium"
    VALIDATION_MAX_LOW = "validation_max_low"

    # cp1_severity_thresholds.
    CP1_MAX_CRITICAL = "cp1_max_critical"
    CP1_MAX_HIGH = "cp1_max_high"


class QualityReleaseToggle(StrEnum):
    """A governed :class:`QualityReleaseRules` toggle that enforces a mandatory gate.

    A mandatory-release rule names the toggle that governs whether its gate is enforced.
    When the toggle is disabled in the policy, the evaluator records the rule as
    ``SKIPPED`` (not enforced by policy) rather than ``PASS`` or ``FAIL``.
    """

    BLOCK_ON_HALLUCINATION = "block_on_hallucination"
    BLOCK_ON_VALIDATION_FAILURE = "block_on_validation_failure"
    BLOCK_ON_CP1_FAILURE = "block_on_cp1_failure"
    REQUIRE_ENGINEERING_READINESS = "require_engineering_readiness"


class QualityMetricSubsystem(StrEnum):
    """The upstream subsystem whose completed result a rule reads.

    Names the input a rule depends on, for grouping and for the deterministic
    ``SKIPPED`` path when a governed input is absent. ``CROSS`` marks a rule that reads
    more than one subsystem at once.
    """

    GROUNDING = "grounding"
    VALIDATION = "validation"
    CP1 = "cp1"
    CROSS = "cross"


class QualityRule(Schema):
    """One governed quality rule — immutable metadata, no behaviour.

    A rule declares the governed *relationship* it evaluates: the quantity it observes
    (:attr:`metric`), how it is compared (:attr:`comparator`), the governed policy value
    that bounds it (:attr:`threshold_ref`), the severity a violation carries, and — for a
    mandatory gate — the toggle that enforces it (:attr:`governing_toggle`). It carries
    no threshold value and no comparison logic; the evaluator resolves both from the
    named policy field and applies the named comparator.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    rule_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Z0-9][A-Z0-9._:-]*$",
        description="Stable, governed rule identity (e.g. 'QG-GRD-001').",
    )
    rule_version: QualityRuleVersion = Field(
        default=QUALITY_RULE_VERSION, description="Version of this rule's definition."
    )
    rule_name: str = Field(..., min_length=1, description="Human-readable rule name.")
    category: RuleCategory = Field(..., description="The governed relationship this rule governs.")
    severity: QualitySeverity = Field(..., description="Severity a violation of this rule carries.")
    rule_type: RuleType = Field(..., description="Descriptive classification of the rule's shape.")
    description: str = Field(..., min_length=1, description="What the rule governs and why.")

    metric: QualityMetric = Field(..., description="The governed quantity observed (the actual).")
    comparator: RuleComparator = Field(..., description="How the observed value is compared.")
    threshold_ref: QualityThresholdRef = Field(
        ..., description="Which governed QualityPolicy value bounds the rule (the threshold)."
    )
    governing_toggle: QualityReleaseToggle | None = Field(
        default=None,
        description="For a mandatory gate, the policy toggle that enforces it; else None.",
    )

    mandatory: bool = Field(
        default=False, description="Whether this rule is a mandatory release gate."
    )
    enabled: bool = Field(default=True, description="Whether the catalogue evaluates this rule.")
    evaluation_order: int = Field(
        ..., ge=0, description="Deterministic ordering key within the catalogue."
    )
    recommendation: str = Field(
        ..., min_length=1, description="What a consumer should do when the rule is violated."
    )
    applicable_subsystem: QualityMetricSubsystem = Field(
        ..., description="The subsystem whose result the rule reads."
    )
    tags: tuple[str, ...] = Field(default=(), description="Governed classification tags.")

    @model_validator(mode="after")
    def _validate_rule(self) -> QualityRule:
        """Enforce the metadata invariants that keep evaluation deterministic.

        A boolean ``MUST_NOT_HOLD`` rule must name no numeric threshold; a numeric
        comparator must name one. A mandatory rule must name its governing toggle. No
        value is computed — these are shape invariants only.
        """
        if self.comparator == RuleComparator.MUST_NOT_HOLD:
            if self.threshold_ref != QualityThresholdRef.NONE:
                raise ValueError(
                    f"Rule '{self.rule_id}' uses MUST_NOT_HOLD but names a numeric "
                    f"threshold '{self.threshold_ref}'; it must be NONE."
                )
        elif self.threshold_ref == QualityThresholdRef.NONE:
            raise ValueError(
                f"Rule '{self.rule_id}' uses {self.comparator} but names no threshold; "
                f"a numeric comparator requires a governed threshold reference."
            )

        if self.mandatory and self.governing_toggle is None:
            raise ValueError(
                f"Mandatory rule '{self.rule_id}' must name the governing release toggle."
            )
        if self.governing_toggle is not None and not self.mandatory:
            raise ValueError(
                f"Rule '{self.rule_id}' names a governing toggle but is not mandatory."
            )
        return self
