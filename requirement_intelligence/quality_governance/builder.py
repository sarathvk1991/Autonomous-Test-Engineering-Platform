"""The :class:`QualityGovernanceResultBuilder` — the single assembly point (CAP-080C).

Construction only. It **assembles** the frozen :class:`QualityGovernanceResult` from the
canonical outputs the pipeline already produced — the completed release
:class:`QualityDecisionResult`, the failing rules recorded in the
:class:`RuleEvaluationResult`, and the provenance of the three consumed peer results. It
is the **only** place a ``QualityGovernanceResult`` (and its inner
:class:`QualityAssessment`) is constructed (ADR-0017 §D29, Recommendation 2).

It **computes nothing**: it evaluates no rule, interprets no assessment, derives no
decision (the decision comes from the ``QualityDecisionResult``), and calculates no
metric (``overall_quality_score`` is the grounding roll-up recorded upstream, never a
governance-specific calculation). Projecting each failing rule into a governance
:class:`QualityFinding` is a deterministic re-expression of the ``RuleEvaluationResult``,
not a re-evaluation — so every ``QualityGovernanceResult`` stays reconstructable from the
canonical outputs alone (Recommendation 3).
"""

from __future__ import annotations

from datetime import datetime

from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.grounding.models import GroundingResult
from requirement_intelligence.quality_governance.assessment.models import QualityAssessmentResult
from requirement_intelligence.quality_governance.decision.models import QualityDecisionResult
from requirement_intelligence.quality_governance.evaluation.models import (
    RuleCategory,
    RuleEvaluation,
    RuleEvaluationResult,
    RuleEvaluationStatus,
)
from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityAssessmentId,
    QualityGovernanceResultId,
    QualityPolicyId,
    QualityPolicyVersion,
)
from requirement_intelligence.quality_governance.models.assessment import QualityAssessment
from requirement_intelligence.quality_governance.models.enums import (
    QualityDecision,
    QualityFindingCategory,
    QualityInputSource,
    QualitySeverity,
)
from requirement_intelligence.quality_governance.models.findings import QualityFinding
from requirement_intelligence.quality_governance.models.result import (
    ConsumedResultReference,
    QualityGovernanceResult,
)
from requirement_intelligence.quality_governance.models.summary import (
    QualityFindingCategoryCount,
    QualitySummary,
)
from requirement_intelligence.quality_governance.version import (
    QUALITY_GOVERNANCE_FRAMEWORK_VERSION,
)
from requirement_intelligence.validation.models.validation_result import ValidationResult

#: The governed, deterministic projection of a failing rule's category onto the
#: governance ``(QualityFindingCategory, QualityInputSource)`` vocabulary. A fixed
#: translation table — never an evaluation. Cross-subsystem and mandatory-release rules
#: are attributed coarsely; the fine-grained subsystem attribution lives in the consumed
#: ``RuleEvaluationResult`` the governance result records as provenance.
_FINDING_BY_RULE_CATEGORY: dict[RuleCategory, tuple[QualityFindingCategory, QualityInputSource]] = {
    RuleCategory.GROUNDING: (
        QualityFindingCategory.GROUNDING_COVERAGE_BELOW_POLICY,
        QualityInputSource.GROUNDING,
    ),
    RuleCategory.VALIDATION: (
        QualityFindingCategory.VALIDATION_POLICY_VIOLATED,
        QualityInputSource.VALIDATION,
    ),
    RuleCategory.CP1: (
        QualityFindingCategory.CP1_POLICY_VIOLATED,
        QualityInputSource.CP1,
    ),
    RuleCategory.CROSS_SUBSYSTEM: (
        QualityFindingCategory.MIXED_QUALITY_EVIDENCE,
        QualityInputSource.GROUNDING,
    ),
    RuleCategory.MANDATORY_RELEASE: (
        QualityFindingCategory.RELEASE_POLICY_VIOLATION,
        QualityInputSource.GROUNDING,
    ),
    RuleCategory.ADVISORY: (
        QualityFindingCategory.VALIDATION_POLICY_VIOLATED,
        QualityInputSource.VALIDATION,
    ),
}

#: Severities that become a surfaced governance finding. Advisory/``INFO`` observations
#: are non-blocking and are not surfaced as governance findings (a ``PASS`` carries none).
_SURFACED_SEVERITIES = frozenset({QualitySeverity.WARNING, QualitySeverity.FAILURE})


class QualityGovernanceResultBuilder:
    """Assemble the frozen :class:`QualityGovernanceResult` — the single construction point."""

    def build(
        self,
        *,
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
        rule_evaluation_result: RuleEvaluationResult,
        quality_assessment_result: QualityAssessmentResult,
        quality_decision_result: QualityDecisionResult,
        policy_id: QualityPolicyId,
        policy_version: QualityPolicyVersion,
        started_at: datetime,
        completed_at: datetime,
    ) -> QualityGovernanceResult:
        """Assemble the governance verdict from the completed pipeline outputs."""
        analysis_id = quality_decision_result.analysis_id
        execution_id = quality_decision_result.execution_id
        decision = QualityDecision(quality_decision_result.decision)

        findings = self._findings(rule_evaluation_result)
        summary = self._summary(
            decision=decision,
            findings=findings,
            grounding_result=grounding_result,
            policy_id=policy_id,
            policy_version=policy_version,
            verdict=quality_decision_result.summary.verdict,
        )
        assessment_id = QualityAssessmentId.for_run(analysis_id, execution_id)
        assessment = QualityAssessment(
            assessment_id=assessment_id,
            analysis_id=analysis_id,
            execution_id=execution_id,
            decision=decision,
            findings=findings,
            summary=summary,
            policy_id=policy_id,
            policy_version=policy_version,
            framework_version=QUALITY_GOVERNANCE_FRAMEWORK_VERSION,
        )
        return QualityGovernanceResult(
            result_id=QualityGovernanceResultId.for_assessment(str(assessment_id)),
            analysis_id=analysis_id,
            execution_id=execution_id,
            assessment=assessment,
            consumed_inputs=self._consumed_inputs(
                grounding_result, validation_result, cp1_result
            ),
            policy_id=policy_id,
            policy_version=policy_version,
            framework_version=QUALITY_GOVERNANCE_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )

    @staticmethod
    def _findings(rule_evaluation_result: RuleEvaluationResult) -> tuple[QualityFinding, ...]:
        """Project each surfaced failing rule into a governance finding (assembly, not eval)."""
        findings: list[QualityFinding] = []
        for evaluation in rule_evaluation_result.evaluations:
            if evaluation.status != RuleEvaluationStatus.FAIL:
                continue
            severity = QualitySeverity(evaluation.severity)
            if severity not in _SURFACED_SEVERITIES:
                continue
            findings.append(_finding_for(evaluation, severity))
        return tuple(findings)

    @staticmethod
    def _summary(
        *,
        decision: QualityDecision,
        findings: tuple[QualityFinding, ...],
        grounding_result: GroundingResult,
        policy_id: QualityPolicyId,
        policy_version: QualityPolicyVersion,
        verdict: str,
    ) -> QualitySummary:
        """Assemble the headline summary — counts and the recorded grounding roll-up."""
        warning_count = sum(
            1 for f in findings if QualitySeverity(f.severity) is QualitySeverity.WARNING
        )
        failure_count = sum(
            1 for f in findings if QualitySeverity(f.severity) is QualitySeverity.FAILURE
        )
        category_counts: dict[str, int] = {}
        for finding in findings:
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1
        return QualitySummary(
            decision=decision,
            overall_quality_score=grounding_result.assessment.summary.grounding_score,
            policy_id=policy_id,
            policy_version=policy_version,
            total_findings=len(findings),
            warning_count=warning_count,
            failure_count=failure_count,
            category_distribution=tuple(
                QualityFindingCategoryCount(category=category, count=category_counts[category])
                for category in QualityFindingCategory
                if category_counts.get(category, 0) > 0
            ),
            verdict=verdict,
        )

    @staticmethod
    def _consumed_inputs(
        grounding_result: GroundingResult,
        validation_result: ValidationResult,
        cp1_result: CP1Result,
    ) -> tuple[ConsumedResultReference, ...]:
        """Record the identity and contract version of each consumed peer result (provenance)."""
        return (
            ConsumedResultReference(
                source=QualityInputSource.GROUNDING,
                result_id=str(grounding_result.assessment.assessment_id),
                result_version=str(grounding_result.result_version),
            ),
            ConsumedResultReference(
                source=QualityInputSource.VALIDATION,
                result_id=validation_result.validation_id,
                result_version=str(
                    validation_result.validation_framework_metadata.validation_contract_version
                ),
            ),
            ConsumedResultReference(
                source=QualityInputSource.CP1,
                result_id=cp1_result.cp1_id,
                result_version=cp1_result.cp1_result_version,
            ),
        )


def _finding_for(evaluation: RuleEvaluation, severity: QualitySeverity) -> QualityFinding:
    """Build one governance finding from one failing rule evaluation."""
    category, source = _FINDING_BY_RULE_CATEGORY[RuleCategory(evaluation.category)]
    return QualityFinding(
        finding_id=f"qgf-{evaluation.rule_id}",
        category=category,
        severity=severity,
        source=source,
        message=evaluation.reason,
    )
