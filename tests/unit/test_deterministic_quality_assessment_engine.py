"""Behaviour, explainability, and determinism tests for the deterministic assessment engine.

CAP-080B.1 exercises :class:`DeterministicQualityAssessmentEngine` over real
``RuleEvaluationResult`` inputs (produced by the deterministic evaluator): the four
observed levels, policy-governed precedence, references-not-copies, statistics,
determinism, serialization, and explainability (ADR-0017 §D26, Recommendation 1/3/5).
"""

from __future__ import annotations

import pytest

from requirement_intelligence.quality_governance.assessment import (
    AssessmentConflictPolicy,
    AssessmentLevel,
    DeterministicQualityAssessmentEngine,
    QualityAssessmentResult,
    default_assessment_policy,
)
from requirement_intelligence.quality_governance.evaluation import (
    DeterministicQualityRuleEvaluator,
    RuleCategory,
    RuleEvaluationResult,
    RuleEvaluationStatus,
)
from requirement_intelligence.quality_governance.policy import (
    QualityReleaseRules,
    default_quality_policy,
)
from requirement_intelligence.quality_governance.rules import default_quality_rule_catalog
from requirement_intelligence.validation.models import (
    ValidationVerdict as ValidationSubsystemVerdict,
)
from shared.enums.base import ValidationVerdict as CP1Verdict
from tests.unit.quality_governance_helpers import (
    make_cp1_result,
    make_grounding_result,
    make_validation_result,
)


def _evaluation(
    *,
    grounding_score: int = 95,
    hallucination_rate: float = 0.0,
    average_confidence: float = 90.0,
    evidence_coverage: float = 0.9,
    validation_verdict: ValidationSubsystemVerdict = ValidationSubsystemVerdict.PASSED,
    critical: int = 0,
    error: int = 0,
    warning: int = 0,
    info: int = 0,
    cp1_verdict: CP1Verdict = CP1Verdict.PASS,
    cp1_blocking: int = 0,
    quality_policy=None,
) -> RuleEvaluationResult:
    evaluator = DeterministicQualityRuleEvaluator(
        policy=quality_policy or default_quality_policy(),
        catalog=default_quality_rule_catalog(),
    )
    return evaluator.evaluate(
        make_grounding_result(
            grounding_score=grounding_score,
            hallucination_rate=hallucination_rate,
            average_confidence=average_confidence,
            evidence_coverage=evidence_coverage,
        ),
        make_validation_result(
            verdict=validation_verdict, critical=critical, error=error, warning=warning, info=info
        ),
        make_cp1_result(verdict=cp1_verdict, blocking_findings=cp1_blocking),
    )


def _assess(rule_result: RuleEvaluationResult, policy=None) -> QualityAssessmentResult:
    return DeterministicQualityAssessmentEngine(
        policy=policy or default_assessment_policy()
    ).assess(rule_result)


@pytest.mark.unit
class TestObservedLevels:
    def test_clean(self) -> None:
        result = _assess(_evaluation())
        assert result.overall_assessment.level == AssessmentLevel.CLEAN
        assert result.overall_assessment.has_blocking_failure is False
        assert result.references == ()

    def test_failures_present(self) -> None:
        result = _assess(_evaluation(grounding_score=40, cp1_verdict=CP1Verdict.FAIL))
        assert result.overall_assessment.level == AssessmentLevel.FAILURES_PRESENT
        assert result.overall_assessment.has_blocking_failure is True
        assert result.overall_assessment.mandatory_failure_count >= 1

    def test_warnings_present(self) -> None:
        # Grounding score 70 clears the failure bar (60) but not the warning bar (80).
        result = _assess(_evaluation(grounding_score=70, hallucination_rate=0.05))
        assert result.overall_assessment.level == AssessmentLevel.WARNINGS_PRESENT
        assert result.overall_assessment.has_blocking_failure is False

    def test_advisory_only(self) -> None:
        # Only the advisory rule (validation info > 20) fails.
        result = _assess(_evaluation(info=25))
        assert result.overall_assessment.level == AssessmentLevel.ADVISORY_ONLY
        assert result.overall_assessment.has_blocking_failure is False
        assert result.assessment_summary.advisories == 1


@pytest.mark.unit
class TestPolicyGovernedInterpretation:
    def test_precedence_wins_differs_from_severity_wins(self) -> None:
        """A warning + an advisory failing: precedence order governs the observed level."""
        rule_result = _evaluation(grounding_score=70, info=25)  # GROUNDING warning + ADVISORY

        severity_policy = default_assessment_policy().model_copy(
            update={"conflict_resolution": AssessmentConflictPolicy.SEVERITY_WINS}
        )
        # Precedence that puts ADVISORY ahead of GROUNDING.
        precedence_policy = default_assessment_policy().model_copy(
            update={
                "conflict_resolution": AssessmentConflictPolicy.PRECEDENCE_WINS,
                "precedence": (
                    RuleCategory.ADVISORY,
                    RuleCategory.GROUNDING,
                    RuleCategory.VALIDATION,
                    RuleCategory.CP1,
                    RuleCategory.CROSS_SUBSYSTEM,
                    RuleCategory.MANDATORY_RELEASE,
                ),
            }
        )
        assert (
            _assess(rule_result, policy=severity_policy).overall_assessment.level
            == AssessmentLevel.WARNINGS_PRESENT
        )
        assert (
            _assess(rule_result, policy=precedence_policy).overall_assessment.level
            == AssessmentLevel.ADVISORY_ONLY
        )

    def test_treat_advisory_as_warning(self) -> None:
        rule_result = _evaluation(info=25)
        policy = default_assessment_policy().model_copy(update={"treat_advisory_as_warning": True})
        assert (
            _assess(rule_result, policy=policy).overall_assessment.level
            == AssessmentLevel.WARNINGS_PRESENT
        )

    def test_include_skipped_as_warning(self) -> None:
        """Disabled release toggles skip mandatory rules; policy governs their interpretation."""
        lenient = default_quality_policy().model_copy(
            update={
                "release_rules": QualityReleaseRules(
                    block_on_hallucination=False,
                    block_on_validation_failure=False,
                    block_on_cp1_failure=False,
                    require_engineering_readiness=False,
                )
            }
        )
        rule_result = _evaluation(quality_policy=lenient)  # clean but 4 mandatory rules SKIPPED
        assert rule_result.summary.skipped == 4

        default_result = _assess(rule_result)
        assert default_result.overall_assessment.level == AssessmentLevel.CLEAN

        warn_policy = default_assessment_policy().model_copy(
            update={"include_skipped_as_warning": True}
        )
        warn_result = _assess(rule_result, policy=warn_policy)
        assert warn_result.overall_assessment.level == AssessmentLevel.WARNINGS_PRESENT

    def test_recommendation_gated_by_policy(self) -> None:
        rule_result = _evaluation(grounding_score=40)
        with_rec = _assess(rule_result)
        without_rec = _assess(
            rule_result,
            policy=default_assessment_policy().model_copy(update={"emit_recommendations": False}),
        )
        assert "Recommended:" in with_rec.overall_assessment.summary_text
        assert "Recommended:" not in without_rec.overall_assessment.summary_text


@pytest.mark.unit
class TestReferencesAreReferences:
    def test_references_point_at_failing_evaluations_only(self) -> None:
        rule_result = _evaluation(grounding_score=40)
        result = _assess(rule_result)
        failing_ids = {
            str(e.evaluation_id)
            for e in rule_result.evaluations
            if e.status == RuleEvaluationStatus.FAIL
        }
        ref_ids = {str(r.evaluation_id) for r in result.references}
        assert ref_ids == failing_ids

    def test_reference_carries_no_duplicated_evaluation_payload(self) -> None:
        from requirement_intelligence.quality_governance.assessment import (
            AssessmentFindingReference,
        )

        result = _assess(_evaluation(grounding_score=40))
        assert result.references[0] is not None
        fields = set(AssessmentFindingReference.model_fields)
        # A reference, not a copy: no expected/actual/threshold/reason fields.
        assert "expected_value" not in fields
        assert "actual_value" not in fields
        assert "reason" not in fields
        assert {"evaluation_id", "rule_id", "severity", "status", "note"} <= fields

    def test_references_have_unique_ids(self) -> None:
        result = _assess(_evaluation(grounding_score=40, cp1_verdict=CP1Verdict.FAIL))
        ids = [str(r.evaluation_id) for r in result.references]
        assert len(ids) == len(set(ids))


@pytest.mark.unit
class TestSummaryAndStatistics:
    def test_summary_counts_are_consistent(self) -> None:
        rule_result = _evaluation(grounding_score=40)
        result = _assess(rule_result)
        s = result.assessment_summary
        assert s.total_rules == s.passed + s.failed + s.skipped
        assert s.total_rules == len(rule_result.evaluations)

    def test_outcome_mandatory_count_matches_summary(self) -> None:
        result = _assess(_evaluation(grounding_score=40, cp1_verdict=CP1Verdict.FAIL))
        assert (
            result.overall_assessment.mandatory_failure_count
            == result.assessment_summary.mandatory_failures
        )

    def test_distributions_cover_all_rules(self) -> None:
        rule_result = _evaluation()
        result = _assess(rule_result)
        total = len(rule_result.evaluations)
        assert sum(e.count for e in result.assessment_statistics.category_distribution) == total
        assert sum(e.count for e in result.assessment_statistics.severity_distribution) == total
        assert sum(e.count for e in result.assessment_statistics.status_distribution) == total


@pytest.mark.unit
class TestDeterminismAndExplainability:
    def test_same_input_yields_identical_result(self) -> None:
        rule_result = _evaluation(grounding_score=40)
        assert _assess(rule_result) == _assess(rule_result)

    def test_assessment_id_is_deterministic_from_evaluation(self) -> None:
        rule_result = _evaluation()
        first = _assess(rule_result)
        second = _assess(rule_result)
        assert first.assessment_id == second.assessment_id
        assert str(first.rule_evaluation_result_id) == str(rule_result.result_id)

    def test_round_trips_from_serialization_alone(self) -> None:
        result = _assess(_evaluation(grounding_score=40))
        dumped = result.model_dump(mode="json", by_alias=True)
        assert QualityAssessmentResult.model_validate(dumped) == result

    def test_is_immutable(self) -> None:
        from pydantic import ValidationError

        result = _assess(_evaluation())
        with pytest.raises(ValidationError):
            result.analysis_id = "other"  # type: ignore[misc]

    def test_carries_no_release_decision(self) -> None:
        fields = set(QualityAssessmentResult.model_fields)
        assert "decision" not in fields
        assert "quality_score" not in fields

    def test_version_independent_of_policy_version(self) -> None:
        result = _assess(_evaluation())
        assert result.policy_version == default_assessment_policy().policy_version
        assert result.result_version != result.policy_version
