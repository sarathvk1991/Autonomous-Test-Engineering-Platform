"""QualityRuleEvaluator — the single owner of governance rule evaluation.

Architecture (ADR-0017 D17-D20, §D25)
-------------------------------------
The ``QualityRuleEvaluator`` owns **behaviour**; the ``QualityGovernanceService``
owns **sequencing**. This is the deliberate split frozen by CAP-080A.1:

    GroundingResult ┐
    ValidationResult├─▶ QualityRuleEvaluator.evaluate ─▶ RuleEvaluationResult
    CP1Result       ┘                                          │
                                                               ▼
                              QualityGovernanceService.evaluate ─▶ QualityGovernanceResult

The evaluator reads the three completed peer results and the governed
:class:`QualityPolicy`, evaluates each governed rule in the
:class:`QualityRuleCatalog` (threshold comparison, mandatory-gate evaluation), and
produces a :class:`RuleEvaluationResult` of pure observations. It owns **only** that.

Rule catalogue, not embedded rules (frozen, ADR-0017 §D25)
    The evaluator iterates the governed :class:`QualityRuleCatalog` — it hard-codes no
    rule and no threshold. Each rule *names* the quantity it observes
    (:class:`QualityMetric`), how it compares (:class:`RuleComparator`), and which
    governed :class:`QualityPolicy` value bounds it (:class:`QualityThresholdRef`). The
    evaluator owns three generic mechanisms — metric extraction, threshold resolution,
    and comparison — invoked per rule; it contains no per-rule ``if`` branch. Adding a
    rule is a catalogue change, never an evaluator change (Recommendation 2).

Explainability (frozen, ADR-0017 Recommendation 3)
    Every :class:`RuleEvaluation` records the expected value, the observed value, the
    governed threshold, the governing rule, and a deterministic reason — no generated
    prose, no AI. A governance decision is reconstructable from the
    ``RuleEvaluationResult`` alone, with no need to re-run the evaluator or inspect the
    policy.

Consumer only (frozen, ADR-0017 Recommendation 1/5)
    ``evaluate`` consumes only ``GroundingResult`` / ``ValidationResult`` /
    ``CP1Result`` — never re-running the subsystems that produce them and never
    importing an upstream *implementation* class.

One contract, many future evaluators (frozen, ADR-0017 Recommendation 5)
    The signature ``evaluate(grounding_result, validation_result, cp1_result) ->
    RuleEvaluationResult`` is permanent. This deterministic evaluator (CAP-080B) and
    every future statistical, organization-specific, regulatory, risk-weighted, or
    AI-assisted evaluator implement it unchanged.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass

from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.grounding.models import GroundingResult
from requirement_intelligence.quality_governance.evaluation.models import (
    RuleCategory,
    RuleCategoryCount,
    RuleEvaluation,
    RuleEvaluationResult,
    RuleEvaluationStatistics,
    RuleEvaluationStatus,
    RuleEvaluationSummary,
    RuleSeverityCount,
)
from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityRuleEvaluatorVersion,
    RuleEvaluationId,
    RuleEvaluationResultId,
)
from requirement_intelligence.quality_governance.models.enums import QualitySeverity
from requirement_intelligence.quality_governance.policy import QualityPolicy
from requirement_intelligence.quality_governance.rules import (
    QualityMetric,
    QualityReleaseToggle,
    QualityRule,
    QualityRuleCatalog,
    QualityThresholdRef,
    RuleComparator,
    default_quality_rule_catalog,
)
from requirement_intelligence.validation.models.validation_enums import (
    ValidationVerdict as ValidationSubsystemVerdict,
)
from requirement_intelligence.validation.models.validation_result import ValidationResult
from shared.enums.base import ValidationVerdict as CP1Verdict

#: The stable identity of the deterministic evaluator (CAP-080B). Recorded on every
#: ``RuleEvaluationResult`` it produces, independent of the policy and schema versions.
RULE_EVALUATOR_NAME = "deterministic_quality_rule_v1"

#: The version of the deterministic evaluator implementation (CAP-080B).
RULE_EVALUATOR_VERSION = QualityRuleEvaluatorVersion(1, 0, 0)

#: Verdicts that count as a *failing* Validation outcome (the four-state vocabulary).
_VALIDATION_FAILING = frozenset(
    {ValidationSubsystemVerdict.FAILED, ValidationSubsystemVerdict.BLOCKED}
)
#: Verdicts that count as a *passing* Validation outcome.
_VALIDATION_PASSING = frozenset(
    {ValidationSubsystemVerdict.PASSED, ValidationSubsystemVerdict.PASSED_WITH_WARNINGS}
)


class QualityRuleEvaluator(ABC):
    """The permanent contract for evaluating governed quality rules over one run.

    A single public method, ``evaluate``, judges the completed upstream results against
    the governed :class:`QualityPolicy` and returns a :class:`RuleEvaluationResult` of
    pure observations. Implementations own rule evaluation only; they make no release
    decision, compute no quality score, and own no orchestration.
    """

    @abstractmethod
    def evaluate(
        self,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
    ) -> RuleEvaluationResult:
        """Evaluate the governed rules over the completed *grounding*/*validation*/*cp1* results.

        Parameters
        ----------
        grounding_result:
            The completed grounding assessment for the run.
        validation_result:
            The completed structural/reasoning validation verdict for the run.
        cp1_result:
            The completed engineering-readiness verdict for the run.

        Returns
        -------
        RuleEvaluationResult
            The self-contained record of every evaluated rule — observations only, no
            score and no decision.
        """
        raise NotImplementedError


@dataclass(frozen=True)
class _Observation:
    """One deterministic reading of a governed metric — the *actual* value.

    ``numeric`` carries the value for a numeric comparator; ``flag`` carries the
    boolean condition for a ``MUST_NOT_HOLD`` rule; ``display`` is the canonical
    rendering recorded on the evaluation. ``present`` is ``False`` when the metric could
    not be read, which yields a ``SKIPPED`` evaluation.
    """

    present: bool
    display: str
    numeric: float | None = None
    flag: bool | None = None


@dataclass(frozen=True)
class _Threshold:
    """One resolved governed bound — the *threshold*/*expected* value.

    ``numeric`` is the policy value a numeric comparator compares against; ``display``
    is its canonical rendering. A ``MUST_NOT_HOLD`` rule resolves to ``numeric=None``.
    """

    numeric: float | None
    display: str


class DeterministicQualityRuleEvaluator(QualityRuleEvaluator):
    """The first real rule evaluator (CAP-080B): pure, deterministic, catalogue-driven.

    Constructed with the governed :class:`QualityPolicy` (the source of every threshold)
    and the governed :class:`QualityRuleCatalog` (the source of every rule). It iterates
    the catalogue's enabled rules in canonical order and, for each, extracts the observed
    metric, resolves the governed threshold, and applies the named comparator — producing
    one :class:`RuleEvaluation` per rule. It computes no score and makes no decision.

    Determinism
        No randomness, no UUID, no timestamp, no unordered iteration. Ids are pure
        functions of the run and rule; distributions are emitted in a fixed enum order.
        The same inputs always yield an identical, byte-stable ``RuleEvaluationResult``.
    """

    def __init__(self, policy: QualityPolicy, catalog: QualityRuleCatalog | None = None) -> None:
        """Store the governed *policy* and rule *catalog* (default: the framework catalogue)."""
        self._policy = policy
        self._catalog = catalog if catalog is not None else default_quality_rule_catalog()

    @property
    def policy(self) -> QualityPolicy:
        """The governed quality policy — the source of every threshold."""
        return self._policy

    @property
    def catalog(self) -> QualityRuleCatalog:
        """The governed rule catalogue this evaluator iterates."""
        return self._catalog

    def evaluate(
        self,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
    ) -> RuleEvaluationResult:
        """Evaluate every enabled governed rule and assemble the ``RuleEvaluationResult``."""
        result_id = RuleEvaluationResultId.for_run(
            grounding_result.analysis_id, grounding_result.execution_id
        )
        evaluations = tuple(
            self._evaluate_rule(rule, result_id, grounding_result, validation_result, cp1_result)
            for rule in self._catalog.enabled_rules()
        )
        return RuleEvaluationResult(
            result_id=result_id,
            analysis_id=grounding_result.analysis_id,
            execution_id=grounding_result.execution_id,
            evaluations=evaluations,
            summary=self._summarise(evaluations),
            statistics=self._statistics(evaluations),
            policy_version=self._policy.policy_version,
            evaluator_name=RULE_EVALUATOR_NAME,
            evaluator_version=RULE_EVALUATOR_VERSION,
        )

    # -- per-rule evaluation --------------------------------------------------

    def _evaluate_rule(
        self,
        rule: QualityRule,
        result_id: RuleEvaluationResultId,
        grounding: GroundingResult,
        validation: ValidationResult,
        cp1: CP1Result,
    ) -> RuleEvaluation:
        """Evaluate one governed rule into a self-contained :class:`RuleEvaluation`."""
        evaluation_id = RuleEvaluationId.for_rule(str(result_id), rule.rule_id)

        # A mandatory gate whose governing toggle is disabled is not enforced: SKIPPED.
        if rule.governing_toggle is not None and not self._toggle_enabled(rule.governing_toggle):
            return self._build(
                rule,
                evaluation_id,
                status=RuleEvaluationStatus.SKIPPED,
                reason=(
                    f"{rule.rule_name}: not enforced by policy "
                    f"({rule.governing_toggle} disabled)."
                ),
            )

        observation = self._observe(rule.metric, grounding, validation, cp1)
        if not observation.present:
            return self._build(
                rule,
                evaluation_id,
                status=RuleEvaluationStatus.SKIPPED,
                reason=f"{rule.rule_name}: {rule.metric} is not available for this run.",
            )

        if rule.comparator == RuleComparator.MUST_NOT_HOLD:
            return self._evaluate_condition(rule, evaluation_id, observation)
        return self._evaluate_threshold(rule, evaluation_id, observation)

    def _evaluate_condition(
        self, rule: QualityRule, evaluation_id: RuleEvaluationId, observation: _Observation
    ) -> RuleEvaluation:
        """Evaluate a boolean ``MUST_NOT_HOLD`` rule — PASS when the condition is absent."""
        violated = bool(observation.flag)
        status = RuleEvaluationStatus.FAIL if violated else RuleEvaluationStatus.PASS
        verb = "holds" if violated else "does not hold"
        return self._build(
            rule,
            evaluation_id,
            status=status,
            expected_value="condition must not hold",
            actual_value=observation.display,
            reason=f"{rule.rule_name}: the flagged condition {verb} ({observation.display}).",
        )

    def _evaluate_threshold(
        self, rule: QualityRule, evaluation_id: RuleEvaluationId, observation: _Observation
    ) -> RuleEvaluation:
        """Evaluate a numeric ``AT_LEAST`` / ``AT_MOST`` rule against its governed threshold."""
        threshold = self._resolve_threshold(rule.threshold_ref)
        actual = observation.numeric
        bound = threshold.numeric
        assert actual is not None and bound is not None
        if rule.comparator == RuleComparator.AT_LEAST:
            passed = actual >= bound
            expected = f">= {threshold.display}"
        else:  # AT_MOST
            passed = actual <= bound
            expected = f"<= {threshold.display}"
        status = RuleEvaluationStatus.PASS if passed else RuleEvaluationStatus.FAIL
        verb = "meets" if passed else "violates"
        return self._build(
            rule,
            evaluation_id,
            status=status,
            expected_value=expected,
            actual_value=observation.display,
            threshold=threshold.display,
            reason=f"{rule.rule_name}: observed {observation.display} {verb} {expected}.",
        )

    @staticmethod
    def _build(
        rule: QualityRule,
        evaluation_id: RuleEvaluationId,
        *,
        status: RuleEvaluationStatus,
        reason: str,
        expected_value: str | None = None,
        actual_value: str | None = None,
        threshold: str | None = None,
    ) -> RuleEvaluation:
        """Assemble one :class:`RuleEvaluation` from a rule's metadata and the outcome."""
        return RuleEvaluation(
            evaluation_id=evaluation_id,
            rule_id=rule.rule_id,
            rule_name=rule.rule_name,
            category=RuleCategory(rule.category),
            severity=QualitySeverity(rule.severity),
            status=status,
            expected_value=expected_value,
            actual_value=actual_value,
            threshold=threshold,
            reason=reason,
        )

    # -- metric extraction (the actual) ---------------------------------------

    def _observe(
        self,
        metric: QualityMetric,
        grounding: GroundingResult,
        validation: ValidationResult,
        cp1: CP1Result,
    ) -> _Observation:
        """Read the governed *metric* deterministically from the completed results."""
        assessment = grounding.assessment
        metrics = assessment.metrics
        summary = validation.validation_summary

        if metric == QualityMetric.GROUNDING_SCORE:
            score = assessment.summary.grounding_score
            return _Observation(present=True, display=str(score), numeric=float(score))
        if metric == QualityMetric.HALLUCINATION_RATE:
            rate = metrics.hallucination_rate
            return _Observation(present=True, display=_fmt_rate(rate), numeric=rate)
        if metric == QualityMetric.AVERAGE_CONFIDENCE:
            conf = metrics.average_confidence
            return _Observation(present=True, display=_fmt_score(conf), numeric=conf)
        if metric == QualityMetric.EVIDENCE_COVERAGE:
            cov = metrics.evidence_coverage
            return _Observation(present=True, display=_fmt_rate(cov), numeric=cov)

        if metric == QualityMetric.VALIDATION_CRITICAL_COUNT:
            return _count_observation(summary.critical_count)
        if metric == QualityMetric.VALIDATION_ERROR_COUNT:
            return _count_observation(summary.error_count)
        if metric == QualityMetric.VALIDATION_WARNING_COUNT:
            return _count_observation(summary.warning_count)
        if metric == QualityMetric.VALIDATION_INFO_COUNT:
            return _count_observation(summary.info_count)
        if metric == QualityMetric.VALIDATION_FAILING_VERDICT:
            verdict = validation.overall_verdict
            return _Observation(
                present=True, display=f"verdict={verdict}", flag=verdict in _VALIDATION_FAILING
            )

        if metric == QualityMetric.CP1_BLOCKING_FINDINGS:
            return _count_observation(_cp1_count(cp1, CP1Verdict.FAIL))
        if metric == QualityMetric.CP1_WARN_FINDINGS:
            return _count_observation(_cp1_count(cp1, CP1Verdict.WARN))
        if metric == QualityMetric.CP1_FAILING_VERDICT:
            verdict = cp1.overall_verdict
            return _Observation(
                present=True, display=f"verdict={verdict}", flag=verdict == CP1Verdict.FAIL
            )
        if metric == QualityMetric.ENGINEERING_NOT_READY:
            verdict = cp1.overall_verdict
            return _Observation(
                present=True, display=f"verdict={verdict}", flag=verdict != CP1Verdict.PASS
            )

        if metric == QualityMetric.CROSS_VALIDATION_PASS_GROUNDING_FAIL:
            anomaly = (
                validation.overall_verdict in _VALIDATION_PASSING
                and self._grounding_failed(grounding)
            )
            return _Observation(
                present=True,
                display=(
                    f"validation={validation.overall_verdict}, "
                    f"groundingScore={assessment.summary.grounding_score}"
                ),
                flag=anomaly,
            )
        if metric == QualityMetric.CROSS_CP1_PASS_GROUNDING_FAIL:
            anomaly = cp1.overall_verdict == CP1Verdict.PASS and self._grounding_failed(grounding)
            return _Observation(
                present=True,
                display=(
                    f"cp1={cp1.overall_verdict}, "
                    f"groundingScore={assessment.summary.grounding_score}"
                ),
                flag=anomaly,
            )

        # Defensive: an unmapped metric is treated as unavailable (a SKIP), never a crash.
        return _Observation(present=False, display="unavailable")

    def _grounding_failed(self, grounding: GroundingResult) -> bool:
        """Whether the grounding score is below the governed failure minimum."""
        return (
            grounding.assessment.summary.grounding_score
            < self._policy.failure_thresholds.minimum_grounding_score
        )

    # -- threshold resolution (the governed bound) ----------------------------

    def _resolve_threshold(self, ref: QualityThresholdRef) -> _Threshold:
        """Resolve *ref* to its governed :class:`QualityPolicy` value and canonical display."""
        failure = self._policy.failure_thresholds
        warning = self._policy.warning_thresholds
        validation = self._policy.validation_severity_thresholds
        cp1 = self._policy.cp1_severity_thresholds

        if ref == QualityThresholdRef.FAILURE_MIN_GROUNDING_SCORE:
            return _score_threshold(failure.minimum_grounding_score)
        if ref == QualityThresholdRef.WARNING_MIN_GROUNDING_SCORE:
            return _score_threshold(warning.minimum_grounding_score)
        if ref == QualityThresholdRef.FAILURE_MAX_HALLUCINATION_RATE:
            return _rate_threshold(failure.maximum_hallucination_rate)
        if ref == QualityThresholdRef.WARNING_MAX_HALLUCINATION_RATE:
            return _rate_threshold(warning.maximum_hallucination_rate)
        if ref == QualityThresholdRef.FAILURE_MIN_CONFIDENCE:
            return _score_threshold(failure.minimum_confidence)
        if ref == QualityThresholdRef.FAILURE_MIN_EVIDENCE_COVERAGE:
            return _rate_threshold(failure.minimum_evidence_coverage)
        if ref == QualityThresholdRef.WARNING_MIN_EVIDENCE_COVERAGE:
            return _rate_threshold(warning.minimum_evidence_coverage)
        if ref == QualityThresholdRef.VALIDATION_MAX_CRITICAL:
            return _count_threshold(validation.max_critical)
        if ref == QualityThresholdRef.VALIDATION_MAX_HIGH:
            return _count_threshold(validation.max_high)
        if ref == QualityThresholdRef.VALIDATION_MAX_MEDIUM:
            return _count_threshold(validation.max_medium)
        if ref == QualityThresholdRef.VALIDATION_MAX_LOW:
            return _count_threshold(validation.max_low)
        if ref == QualityThresholdRef.CP1_MAX_CRITICAL:
            return _count_threshold(cp1.max_critical)
        if ref == QualityThresholdRef.CP1_MAX_HIGH:
            return _count_threshold(cp1.max_high)
        # QualityThresholdRef.NONE — no numeric bound (a MUST_NOT_HOLD rule).
        return _Threshold(numeric=None, display="n/a")

    def _toggle_enabled(self, toggle: QualityReleaseToggle) -> bool:
        """Whether the governed release *toggle* is enabled in the policy."""
        rules = self._policy.release_rules
        return {
            QualityReleaseToggle.BLOCK_ON_HALLUCINATION: rules.block_on_hallucination,
            QualityReleaseToggle.BLOCK_ON_VALIDATION_FAILURE: rules.block_on_validation_failure,
            QualityReleaseToggle.BLOCK_ON_CP1_FAILURE: rules.block_on_cp1_failure,
            QualityReleaseToggle.REQUIRE_ENGINEERING_READINESS: rules.require_engineering_readiness,
        }[toggle]

    # -- roll-ups (assembled, never scored) -----------------------------------

    @staticmethod
    def _summarise(evaluations: tuple[RuleEvaluation, ...]) -> RuleEvaluationSummary:
        """Assemble the headline summary — counts only, no score."""
        passed = sum(1 for e in evaluations if e.status == RuleEvaluationStatus.PASS)
        failed = sum(1 for e in evaluations if e.status == RuleEvaluationStatus.FAIL)
        skipped = sum(1 for e in evaluations if e.status == RuleEvaluationStatus.SKIPPED)
        return RuleEvaluationSummary(
            total_rules=len(evaluations),
            passed=passed,
            failed=failed,
            skipped=skipped,
            verdict=(
                f"{len(evaluations)} rules evaluated: "
                f"{passed} passed, {failed} failed, {skipped} skipped."
            ),
        )

    @staticmethod
    def _statistics(evaluations: tuple[RuleEvaluation, ...]) -> RuleEvaluationStatistics:
        """Assemble the deterministic distributions — emitted in fixed enum order."""
        category_counts: Counter[str] = Counter(e.category for e in evaluations)
        severity_counts: Counter[str] = Counter(e.severity for e in evaluations)
        return RuleEvaluationStatistics(
            mandatory_rules_evaluated=category_counts.get(RuleCategory.MANDATORY_RELEASE, 0),
            advisory_rules_evaluated=category_counts.get(RuleCategory.ADVISORY, 0),
            category_distribution=tuple(
                RuleCategoryCount(category=category, count=category_counts[category])
                for category in RuleCategory
                if category_counts.get(category, 0) > 0
            ),
            severity_distribution=tuple(
                RuleSeverityCount(severity=severity, count=severity_counts[severity])
                for severity in QualitySeverity
                if severity_counts.get(severity, 0) > 0
            ),
        )


def _fmt_rate(value: float) -> str:
    """Canonical, deterministic rendering of a 0-1 rate."""
    return f"{value:.4f}"


def _fmt_score(value: float) -> str:
    """Canonical, deterministic rendering of a 0-100 score/confidence."""
    return f"{value:.2f}"


def _count_observation(count: int) -> _Observation:
    """A numeric observation over an integer finding count."""
    return _Observation(present=True, display=str(count), numeric=float(count))


def _score_threshold(value: int) -> _Threshold:
    """A governed integer score/confidence threshold."""
    return _Threshold(numeric=float(value), display=str(value))


def _count_threshold(value: int) -> _Threshold:
    """A governed integer count threshold."""
    return _Threshold(numeric=float(value), display=str(value))


def _rate_threshold(value: float) -> _Threshold:
    """A governed 0-1 rate threshold."""
    return _Threshold(numeric=value, display=_fmt_rate(value))


def _cp1_count(cp1: CP1Result, verdict: CP1Verdict) -> int:
    """Count CP1 findings whose verdict contribution equals *verdict*."""
    return sum(1 for finding in cp1.findings if finding.verdict_contribution == verdict)
