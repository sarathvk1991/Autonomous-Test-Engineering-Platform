"""QualityDecisionEngine — the single owner of the release decision.

Architecture (ADR-0017 D23, §D28)
---------------------------------
The ``QualityDecisionEngine`` owns the **release decision** — deriving a
:class:`QualityDecision` (``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL``) from a
completed :class:`QualityAssessmentResult`. It is the final governed layer before
Governance:

    QualityAssessmentResult ─▶ QualityDecisionEngine.decide ─▶ QualityDecisionResult
                                                                     │
                                       QualityGovernanceService ─▶ QualityGovernanceResult

What the engine owns
    the release decision, governance decision explanation, and decision-policy
    interpretation — and nothing else.

What the engine does NOT own
    rule evaluation, assessment, orchestration, serialization, reporting, the execution
    package, and runtime wiring. The ``QualityGovernanceService`` orchestrates and
    assembles; it never derives ``PASS`` / ``FAIL`` (ADR-0017 Recommendation 6/7).

Consumes only ``QualityAssessmentResult`` (frozen, ADR-0017 §D23, Recommendation 1)
    The engine reads **only** the assessment result — never ``RuleEvaluationResult``,
    ``GroundingResult``, ``ValidationResult``, or ``CP1Result``, and no upstream
    *implementation* class. Those are already interpreted upstream. It never re-runs
    assessment or re-classifies failures.

Sole owner of the decision (frozen, ADR-0017 Recommendation 2)
    Only this engine derives ``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL``. Assessment
    stays observational; the service assembles.

Governed entirely by ``DecisionPolicy`` (frozen, §D28)
    The engine hard-codes no mapping and no gate: the governed base
    ``level_mapping`` (an ``AssessmentLevel`` → ``QualityDecision`` mapping) supplies the
    base decision, and the governed ``fail_on_mandatory_failure`` / ``fail_on_blocking_failure``
    gates (plus ``warn_on_advisory``) override it. Tuning the decision is a versioned
    policy change, never an engine change (Recommendation 2/4).

One contract, many future engines (frozen, ADR-0017 Recommendation 5)
    The signature ``decide(quality_assessment_result) -> QualityDecisionResult`` is
    permanent. This deterministic engine (CAP-080B.2) and every future statistical,
    regulatory, organization-specific, and AI-assisted engine implement it unchanged.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.quality_governance.assessment.models import (
    AssessmentLevel,
    QualityAssessmentResult,
)
from requirement_intelligence.quality_governance.decision.models import (
    DecisionExplanation,
    DecisionStatistics,
    DecisionSummary,
    QualityDecisionResult,
)
from requirement_intelligence.quality_governance.decision.policy import DecisionPolicy
from requirement_intelligence.quality_governance.evaluation.models import RuleEvaluationStatus
from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityDecisionResultId,
)
from requirement_intelligence.quality_governance.models.enums import (
    QualityDecision,
    QualitySeverity,
)


class QualityDecisionEngine(ABC):
    """The permanent contract for deciding one release from a completed assessment.

    A single public method, ``decide``, derives a :class:`QualityDecision` from a
    :class:`QualityAssessmentResult` under the governed :class:`DecisionPolicy` and
    returns a :class:`QualityDecisionResult`. Implementations own the decision only; they
    make no assessment, own no orchestration, and assemble no governance result.
    """

    @abstractmethod
    def decide(self, quality_assessment_result: QualityAssessmentResult) -> QualityDecisionResult:
        """Decide the release from *quality_assessment_result*.

        Parameters
        ----------
        quality_assessment_result:
            The completed, frozen output of the ``QualityAssessmentEngine`` — the only
            input the decision layer reads.

        Returns
        -------
        QualityDecisionResult
            The self-contained release decision, fully explainable on its own.
        """
        raise NotImplementedError


class DeterministicQualityDecisionEngine(QualityDecisionEngine):
    """The first real decision engine (CAP-080B.2): pure, deterministic, policy-governed.

    Constructed with the governed :class:`DecisionPolicy` — its only dependency. It
    derives the release decision from one :class:`QualityAssessmentResult`: it looks up
    the observed :class:`AssessmentLevel` in the policy's governed base ``level_mapping``,
    applies the governed ``warn_on_advisory`` interpretation, then the governed mandatory
    and blocking ``FAIL`` gates, and assembles a fully populated
    :class:`QualityDecisionResult`. It re-runs no assessment, re-classifies no failure,
    and hard-codes no mapping.

    Determinism
        No randomness, no UUID, no timestamp, no clock. The decision id is a pure
        function of the assessment it decides from; every string is assembled from the
        assessment and the policy. The same assessment always yields an identical decision.

    Explainability (frozen, Recommendation 3)
        Every ``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL`` is reconstructable from the
        ``QualityDecisionResult`` alone — its ``explanation`` (primary reason, contributing
        factors, applied governed rules, recommendations), ``summary``, and ``statistics`` —
        with no need to inspect the policy, the assessment engine, or any runtime.
    """

    def __init__(self, policy: DecisionPolicy) -> None:
        """Store the governed *policy* the engine decides under — its only dependency."""
        self._policy = policy

    @property
    def policy(self) -> DecisionPolicy:
        """The governed decision policy this engine decides under."""
        return self._policy

    def decide(self, quality_assessment_result: QualityAssessmentResult) -> QualityDecisionResult:
        """Derive the governed release decision from *quality_assessment_result*."""
        outcome = quality_assessment_result.overall_assessment
        summary = quality_assessment_result.assessment_summary
        level = outcome.level

        base_mapping = {
            str(rule.level): (QualityDecision(str(rule.decision)), rule.note)
            for rule in self._policy.level_mapping
        }
        base_decision, mapping_note = base_mapping[level]

        applied_rules: list[str] = [f"level_mapping[{level}] -> {base_decision}"]
        decision = base_decision

        advisory_override = (
            self._policy.warn_on_advisory and level == AssessmentLevel.ADVISORY_ONLY
        )
        if advisory_override:
            decision = QualityDecision.PASS_WITH_WARNINGS
            applied_rules.append("warn_on_advisory")

        mandatory_gate = (
            self._policy.fail_on_mandatory_failure and outcome.mandatory_failure_count > 0
        )
        blocking_gate = self._policy.fail_on_blocking_failure and outcome.has_blocking_failure
        if mandatory_gate:
            decision = QualityDecision.FAIL
            applied_rules.append("fail_on_mandatory_failure")
        if blocking_gate:
            decision = QualityDecision.FAIL
            applied_rules.append("fail_on_blocking_failure")

        blocking_failures = self._blocking_failures(quality_assessment_result)
        explanation = self._explanation(
            decision=decision,
            level=level,
            mapping_note=mapping_note,
            applied_rules=tuple(applied_rules),
            mandatory_gate=mandatory_gate,
            blocking_gate=blocking_gate,
            advisory_override=advisory_override,
            outcome_mandatory=outcome.mandatory_failure_count,
            blocking_failures=blocking_failures,
            warnings=summary.warnings,
            advisories=summary.advisories,
        )
        statistics = DecisionStatistics(
            rules_considered=summary.total_rules,
            mandatory_failures=summary.mandatory_failures,
            blocking_failures=blocking_failures,
            warnings=summary.warnings,
            advisories=summary.advisories,
        )
        decision_summary = DecisionSummary(
            decision=decision,
            assessment_level=level,
            verdict=f"Release decision: {decision} (assessment {level}).",
        )
        return QualityDecisionResult(
            decision_id=QualityDecisionResultId.for_assessment(
                str(quality_assessment_result.assessment_id)
            ),
            assessment_id=quality_assessment_result.assessment_id,
            analysis_id=quality_assessment_result.analysis_id,
            execution_id=quality_assessment_result.execution_id,
            decision=decision,
            summary=decision_summary,
            statistics=statistics,
            explanation=explanation,
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
        )

    @staticmethod
    def _blocking_failures(assessment: QualityAssessmentResult) -> int:
        """Count the failing rules recorded at ``FAILURE`` severity in the assessment.

        A pure projection of the assessment's own ``references`` — not a re-classification.
        A skipped rule referenced as a warning (status ``SKIPPED``) is excluded.
        """
        return sum(
            1
            for reference in assessment.references
            if reference.status == RuleEvaluationStatus.FAIL
            and reference.severity == QualitySeverity.FAILURE
        )

    def _explanation(
        self,
        *,
        decision: QualityDecision,
        level: str,
        mapping_note: str,
        applied_rules: tuple[str, ...],
        mandatory_gate: bool,
        blocking_gate: bool,
        advisory_override: bool,
        outcome_mandatory: int,
        blocking_failures: int,
        warnings: int,
        advisories: int,
    ) -> DecisionExplanation:
        """Assemble the structured, deterministic reasoning — no generated prose."""
        if mandatory_gate:
            primary_reason = (
                f"Mandatory release gate triggered: {outcome_mandatory} mandatory-release "
                f"rule(s) failed."
            )
        elif blocking_gate:
            primary_reason = "Blocking failure gate triggered: a blocking rule failed."
        elif advisory_override:
            primary_reason = (
                f"Assessment level '{level}' mapped to {decision} by the governed advisory rule."
            )
        else:
            primary_reason = (
                f"Assessment level '{level}' maps to {decision} under the governed policy: "
                f"{mapping_note}"
            )

        contributing_factors: list[str] = []
        if outcome_mandatory:
            contributing_factors.append(f"{outcome_mandatory} mandatory failure(s)")
        if blocking_failures:
            contributing_factors.append(f"{blocking_failures} blocking failure(s)")
        if warnings:
            contributing_factors.append(f"{warnings} warning observation(s)")
        if advisories:
            contributing_factors.append(f"{advisories} advisory observation(s)")
        contributing_factors.append(f"assessment level: {level}")

        recommendations: tuple[str, ...] = ()
        if self._policy.emit_recommendations:
            recommendations = _RECOMMENDATION_BY_DECISION.get(decision, ())

        return DecisionExplanation(
            primary_reason=primary_reason,
            contributing_factors=tuple(contributing_factors),
            applied_rules=applied_rules,
            recommendations=recommendations,
        )


#: Governed, deterministic recommendation clause(s) per final decision, gated by
#: ``DecisionPolicy.emit_recommendations``. A ``PASS`` carries no reservation.
_RECOMMENDATION_BY_DECISION: dict[QualityDecision, tuple[str, ...]] = {
    QualityDecision.FAIL: ("Resolve the blocking failures before release.",),
    QualityDecision.PASS_WITH_WARNINGS: ("Review the warning-level observations before release.",),
    QualityDecision.PASS: (),
}
