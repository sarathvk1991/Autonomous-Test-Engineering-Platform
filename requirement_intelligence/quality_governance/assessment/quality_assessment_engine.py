"""QualityAssessmentEngine — the single owner of quality assessment.

Architecture (ADR-0017 D21, §D26)
---------------------------------
The ``QualityAssessmentEngine`` owns **assessment** — interpreting a completed
:class:`RuleEvaluationResult` into a :class:`QualityAssessmentResult`. It sits between
Rule Evaluation and Governance:

    RuleEvaluationResult ─▶ QualityAssessmentEngine.assess ─▶ QualityAssessmentResult
                                                                     │
                                (future Decision layer, ADR-0017 §D22)│
                                                                     ▼
                                       QualityGovernanceService ─▶ QualityGovernanceResult

What the engine owns
    interpretation of a ``RuleEvaluationResult``, assessment logic, assessment
    explanation — and nothing else.

What the engine does NOT own
    rule evaluation, governance orchestration, the release decision (reserved for the
    future Decision layer, ADR-0017 §D22, Recommendation 1/2), serialization,
    reporting, the execution package, and runtime wiring.

Consumes only ``RuleEvaluationResult`` (frozen, ADR-0017 §D21)
    Unlike the rule evaluator, the assessment engine does **not** read
    ``GroundingResult`` / ``ValidationResult`` / ``CP1Result`` — those are already
    interpreted into the ``RuleEvaluationResult``. It re-runs nothing, inspects no
    upstream runtime, and imports no upstream *implementation* class.

Interpretation, never decision (frozen, ADR-0017 Recommendation 1)
    The engine emits an :class:`AssessmentOutcome` — an observed :class:`AssessmentLevel`
    plus a blocking-failure observation — never a ``PASS`` / ``PASS_WITH_WARNINGS`` /
    ``FAIL`` decision. A ``FAILURES_PRESENT`` level is an *observation*, not a release
    verdict; the Decision layer derives the verdict from this outcome and its policy.

Governed entirely by ``AssessmentPolicy`` (frozen, §D26)
    The engine hard-codes no precedence, no blocking semantics, and no conflict
    resolution: the governed :class:`AssessmentPolicy` supplies them. Tuning
    interpretation is a versioned policy change, never an engine change (Recommendation
    2/4).

One contract, many future engines (frozen, ADR-0017 Recommendation 5)
    The signature ``assess(rule_evaluation_result) -> QualityAssessmentResult`` is
    permanent. This deterministic engine (CAP-080B.1) and every future risk-weighted,
    statistical, regulatory, and AI-assisted engine implement it unchanged.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from enum import IntEnum

from requirement_intelligence.quality_governance.assessment.models import (
    AssessmentDistributionEntry,
    AssessmentFindingReference,
    AssessmentLevel,
    AssessmentOutcome,
    AssessmentStatistics,
    AssessmentSummary,
    QualityAssessmentResult,
)
from requirement_intelligence.quality_governance.assessment.policy import (
    AssessmentConflictPolicy,
    AssessmentPolicy,
)
from requirement_intelligence.quality_governance.evaluation.models import (
    RuleCategory,
    RuleEvaluation,
    RuleEvaluationResult,
    RuleEvaluationStatus,
)
from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityAssessmentResultId,
)
from requirement_intelligence.quality_governance.models.enums import QualitySeverity


class QualityAssessmentEngine(ABC):
    """The permanent contract for assessing one completed rule evaluation.

    A single public method, ``assess``, interprets a :class:`RuleEvaluationResult`
    under the governed :class:`AssessmentPolicy` and returns a
    :class:`QualityAssessmentResult` of pure observations. Implementations own
    assessment only; they make no release decision and own no orchestration.
    """

    @abstractmethod
    def assess(self, rule_evaluation_result: RuleEvaluationResult) -> QualityAssessmentResult:
        """Assess *rule_evaluation_result* into a :class:`QualityAssessmentResult`.

        Parameters
        ----------
        rule_evaluation_result:
            The completed, frozen output of the ``QualityRuleEvaluator`` — the only
            input the assessment layer reads.

        Returns
        -------
        QualityAssessmentResult
            The self-contained interpretation — observations only, no release decision.
        """
        raise NotImplementedError


class _Class(IntEnum):
    """The interpreted class of one failing (or skipped-as-warning) rule.

    Ordered so a higher value dominates a lower one when composing an observation.
    ``NONE`` marks a rule that contributes no failing signal.
    """

    NONE = 0
    ADVISORY = 1
    WARNING = 2
    BLOCKING = 3


@dataclass(frozen=True)
class _Interpretation:
    """The per-run tallies the outcome, summary, and references are assembled from."""

    references: tuple[AssessmentFindingReference, ...]
    mandatory_failures: int
    warnings: int
    advisories: int
    has_blocking_failure: bool
    level: AssessmentLevel


class DeterministicQualityAssessmentEngine(QualityAssessmentEngine):
    """The first real assessment engine (CAP-080B.1): pure, deterministic, policy-governed.

    Constructed with the governed :class:`AssessmentPolicy` — its only dependency. It
    interprets one :class:`RuleEvaluationResult` into a :class:`QualityAssessmentResult`
    of observations: it classifies each failing rule under the policy's blocking and
    advisory semantics, composes the observed :class:`AssessmentLevel` under the policy's
    conflict-resolution and precedence rules, references (never copies) the rules that
    informed the outcome, and assembles the summary and distributions.

    Determinism
        No randomness, no UUID, no timestamp, no unordered iteration. The assessment id
        is a pure function of the evaluation it interprets; distributions are emitted in
        a fixed enum order; references preserve the evaluation order. The same input
        yields a byte-identical ``QualityAssessmentResult``.

    Explainability (frozen, Recommendation 3)
        Every observation is reconstructable from the ``QualityAssessmentResult`` alone —
        no re-running Rule Evaluation, and no inspecting the policy, the evaluator, or any
        runtime.
    """

    def __init__(self, policy: AssessmentPolicy) -> None:
        """Store the governed *policy* the engine interprets under — its only dependency."""
        self._policy = policy

    @property
    def policy(self) -> AssessmentPolicy:
        """The governed assessment policy this engine interprets under."""
        return self._policy

    def assess(self, rule_evaluation_result: RuleEvaluationResult) -> QualityAssessmentResult:
        """Interpret *rule_evaluation_result* into a :class:`QualityAssessmentResult`."""
        evaluations = rule_evaluation_result.evaluations
        interpretation = self._interpret(evaluations)

        summary = self._summarise(evaluations, interpretation)
        statistics = self._statistics(evaluations)
        outcome = self._outcome(interpretation)

        result_id = QualityAssessmentResultId.for_evaluation(str(rule_evaluation_result.result_id))
        return QualityAssessmentResult(
            assessment_id=result_id,
            rule_evaluation_result_id=rule_evaluation_result.result_id,
            analysis_id=rule_evaluation_result.analysis_id,
            execution_id=rule_evaluation_result.execution_id,
            references=interpretation.references,
            assessment_summary=summary,
            assessment_statistics=statistics,
            overall_assessment=outcome,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
        )

    # -- interpretation -------------------------------------------------------

    def _interpret(self, evaluations: tuple[RuleEvaluation, ...]) -> _Interpretation:
        """Classify every failing rule under the policy and compose the observed level."""
        references: list[AssessmentFindingReference] = []
        category_signal: dict[str, _Class] = {}
        mandatory_failures = 0
        warnings = 0
        advisories = 0
        has_blocking_failure = False

        for evaluation in evaluations:
            if evaluation.status == RuleEvaluationStatus.FAIL:
                rule_class = self._classify(evaluation)
                references.append(self._reference(evaluation, rule_class))
                if evaluation.category == RuleCategory.MANDATORY_RELEASE:
                    mandatory_failures += 1
                if evaluation.severity == QualitySeverity.WARNING:
                    warnings += 1
                if (
                    evaluation.severity == QualitySeverity.INFO
                    or evaluation.category == RuleCategory.ADVISORY
                ):
                    advisories += 1
                if rule_class == _Class.BLOCKING:
                    has_blocking_failure = True
                else:
                    category_signal[evaluation.category] = max(
                        category_signal.get(evaluation.category, _Class.NONE), rule_class
                    )
            elif (
                evaluation.status == RuleEvaluationStatus.SKIPPED
                and self._policy.include_skipped_as_warning
            ):
                references.append(self._reference(evaluation, _Class.WARNING))
                category_signal[evaluation.category] = max(
                    category_signal.get(evaluation.category, _Class.NONE), _Class.WARNING
                )

        # A mandatory failure is inherently blocking (frozen AssessmentOutcome invariant):
        # guarantee the observation even under a pathological policy that disables both
        # blocking toggles, so the outcome never violates its own contract.
        if mandatory_failures > 0:
            has_blocking_failure = True

        level = self._level(has_blocking_failure, category_signal)
        return _Interpretation(
            references=tuple(references),
            mandatory_failures=mandatory_failures,
            warnings=warnings,
            advisories=advisories,
            has_blocking_failure=has_blocking_failure,
            level=level,
        )

    def _classify(self, evaluation: RuleEvaluation) -> _Class:
        """Classify one failing rule under the policy's blocking and advisory semantics."""
        is_mandatory = evaluation.category == RuleCategory.MANDATORY_RELEASE
        is_advisory = (
            evaluation.category == RuleCategory.ADVISORY
            or evaluation.severity == QualitySeverity.INFO
        )
        is_failure_severity = evaluation.severity == QualitySeverity.FAILURE

        if (is_mandatory and self._policy.mandatory_failure_is_blocking) or (
            is_failure_severity and self._policy.failure_severity_is_blocking
        ):
            return _Class.BLOCKING
        if evaluation.severity == QualitySeverity.WARNING:
            return _Class.WARNING
        if is_advisory:
            return _Class.WARNING if self._policy.treat_advisory_as_warning else _Class.ADVISORY
        # A non-blocking failure-severity rule (blocking toggle disabled) is a warning.
        return _Class.WARNING

    def _level(
        self, has_blocking_failure: bool, category_signal: dict[str, _Class]
    ) -> AssessmentLevel:
        """Compose the observed :class:`AssessmentLevel` under the policy's conflict rule."""
        if has_blocking_failure:
            return AssessmentLevel.FAILURES_PRESENT
        dominant = self._dominant_nonblocking(category_signal)
        if dominant == _Class.WARNING:
            return AssessmentLevel.WARNINGS_PRESENT
        if dominant == _Class.ADVISORY:
            return AssessmentLevel.ADVISORY_ONLY
        return AssessmentLevel.CLEAN

    def _dominant_nonblocking(self, category_signal: dict[str, _Class]) -> _Class:
        """The dominant non-blocking signal, resolved by the governed conflict policy."""
        if not category_signal:
            return _Class.NONE
        if self._policy.conflict_resolution == AssessmentConflictPolicy.PRECEDENCE_WINS:
            for category in self._policy.precedence:
                if category in category_signal:
                    return category_signal[category]
            # A signalling category outside the governed precedence falls back to severity.
        return max(category_signal.values())

    @staticmethod
    def _reference(evaluation: RuleEvaluation, rule_class: _Class) -> AssessmentFindingReference:
        """A reference (never a copy) to one rule that informed the assessment."""
        return AssessmentFindingReference(
            evaluation_id=evaluation.evaluation_id,
            rule_id=evaluation.rule_id,
            severity=QualitySeverity(evaluation.severity),
            status=RuleEvaluationStatus(evaluation.status),
            note=_NOTE_BY_CLASS[rule_class],
        )

    # -- assembly (data only) -------------------------------------------------

    def _summarise(
        self, evaluations: tuple[RuleEvaluation, ...], interpretation: _Interpretation
    ) -> AssessmentSummary:
        """Assemble the headline summary — counts and a one-line observation."""
        passed = sum(1 for e in evaluations if e.status == RuleEvaluationStatus.PASS)
        failed = sum(1 for e in evaluations if e.status == RuleEvaluationStatus.FAIL)
        skipped = sum(1 for e in evaluations if e.status == RuleEvaluationStatus.SKIPPED)
        verdict = (
            f"{len(evaluations)} rules assessed: {interpretation.level} "
            f"({interpretation.mandatory_failures} mandatory, {interpretation.warnings} warning, "
            f"{interpretation.advisories} advisory failing)."
        )
        return AssessmentSummary(
            total_rules=len(evaluations),
            passed=passed,
            failed=failed,
            skipped=skipped,
            mandatory_failures=interpretation.mandatory_failures,
            warnings=interpretation.warnings,
            advisories=interpretation.advisories,
            verdict=verdict,
        )

    @staticmethod
    def _statistics(evaluations: tuple[RuleEvaluation, ...]) -> AssessmentStatistics:
        """Assemble the deterministic distributions — emitted in fixed enum order."""
        category_counts: Counter[str] = Counter(e.category for e in evaluations)
        severity_counts: Counter[str] = Counter(e.severity for e in evaluations)
        status_counts: Counter[str] = Counter(e.status for e in evaluations)
        return AssessmentStatistics(
            category_distribution=tuple(
                AssessmentDistributionEntry(label=category, count=category_counts[category])
                for category in RuleCategory
                if category_counts.get(category, 0) > 0
            ),
            severity_distribution=tuple(
                AssessmentDistributionEntry(label=severity, count=severity_counts[severity])
                for severity in QualitySeverity
                if severity_counts.get(severity, 0) > 0
            ),
            status_distribution=tuple(
                AssessmentDistributionEntry(label=status, count=status_counts[status])
                for status in RuleEvaluationStatus
                if status_counts.get(status, 0) > 0
            ),
        )

    def _outcome(self, interpretation: _Interpretation) -> AssessmentOutcome:
        """Assemble the overall interpreted outcome — an observation, never a decision."""
        summary_text = _OBSERVATION_BY_LEVEL[interpretation.level]
        if self._policy.emit_recommendations and interpretation.level != AssessmentLevel.CLEAN:
            recommendation = _RECOMMENDATION_BY_LEVEL[interpretation.level]
            summary_text = f"{summary_text} Recommended: {recommendation}."
        return AssessmentOutcome(
            level=interpretation.level,
            has_blocking_failure=interpretation.has_blocking_failure,
            mandatory_failure_count=interpretation.mandatory_failures,
            summary_text=summary_text,
        )


#: Governed, deterministic classification note for a referenced rule (no free prose).
_NOTE_BY_CLASS: dict[_Class, str] = {
    _Class.BLOCKING: "blocking failure (mandatory or failure-severity).",
    _Class.WARNING: "warning-level failure.",
    _Class.ADVISORY: "advisory failure.",
    _Class.NONE: "informational reference.",
}

#: Governed, deterministic one-line observation per observed level (not a decision).
_OBSERVATION_BY_LEVEL: dict[AssessmentLevel, str] = {
    AssessmentLevel.CLEAN: "No failing rules observed.",
    AssessmentLevel.ADVISORY_ONLY: "Only advisory rules failed.",
    AssessmentLevel.WARNINGS_PRESENT: "Warning-level rules failed; no blocking failure.",
    AssessmentLevel.FAILURES_PRESENT: "At least one blocking rule failed.",
}

#: Governed, deterministic recommendation clause per level, gated by emit_recommendations.
_RECOMMENDATION_BY_LEVEL: dict[AssessmentLevel, str] = {
    AssessmentLevel.ADVISORY_ONLY: "review advisory observations; no blocking action required",
    AssessmentLevel.WARNINGS_PRESENT: "review the warning-level observations",
    AssessmentLevel.FAILURES_PRESENT: "resolve the blocking failures before release",
}
