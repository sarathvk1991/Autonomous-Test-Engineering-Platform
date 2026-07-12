"""Behaviour, explainability, and determinism tests for the deterministic decision engine.

CAP-080B.2 exercises :class:`DeterministicQualityDecisionEngine` over real
``QualityAssessmentResult`` inputs (produced by the evaluator + assessment chain): the
governed level mapping, the mandatory/blocking ``FAIL`` gates, ``warn_on_advisory``, the
three decisions, structured explanation/summary/statistics, determinism, serialization,
and explainability (ADR-0017 §D28, Recommendation 2/3/5).
"""

from __future__ import annotations

import pytest

from requirement_intelligence.quality_governance.assessment import (
    AssessmentLevel,
    DeterministicQualityAssessmentEngine,
    QualityAssessmentResult,
    default_assessment_policy,
)
from requirement_intelligence.quality_governance.decision import (
    DecisionRule,
    DeterministicQualityDecisionEngine,
    QualityDecisionResult,
    default_decision_policy,
)
from requirement_intelligence.quality_governance.evaluation import (
    DeterministicQualityRuleEvaluator,
)
from requirement_intelligence.quality_governance.identity import DecisionPolicyVersion
from requirement_intelligence.quality_governance.models import QualityDecision
from requirement_intelligence.quality_governance.policy import default_quality_policy
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


def _assessment(
    *,
    grounding_score: int = 95,
    hallucination_rate: float = 0.0,
    average_confidence: float = 90.0,
    evidence_coverage: float = 0.9,
    validation_verdict: ValidationSubsystemVerdict = ValidationSubsystemVerdict.PASSED,
    info: int = 0,
    cp1_verdict: CP1Verdict = CP1Verdict.PASS,
) -> QualityAssessmentResult:
    evaluator = DeterministicQualityRuleEvaluator(
        policy=default_quality_policy(), catalog=default_quality_rule_catalog()
    )
    rule_result = evaluator.evaluate(
        make_grounding_result(
            grounding_score=grounding_score,
            hallucination_rate=hallucination_rate,
            average_confidence=average_confidence,
            evidence_coverage=evidence_coverage,
        ),
        make_validation_result(verdict=validation_verdict, info=info),
        make_cp1_result(verdict=cp1_verdict),
    )
    return DeterministicQualityAssessmentEngine(policy=default_assessment_policy()).assess(
        rule_result
    )


def _decide(assessment: QualityAssessmentResult, policy=None) -> QualityDecisionResult:
    return DeterministicQualityDecisionEngine(policy=policy or default_decision_policy()).decide(
        assessment
    )


def _clean() -> QualityAssessmentResult:
    return _assessment()


def _warn() -> QualityAssessmentResult:
    return _assessment(grounding_score=70, hallucination_rate=0.05)


def _advisory() -> QualityAssessmentResult:
    return _assessment(info=25)


def _failures() -> QualityAssessmentResult:
    return _assessment(grounding_score=40, cp1_verdict=CP1Verdict.FAIL)


@pytest.mark.unit
class TestGovernedMapping:
    def test_clean_maps_to_pass(self) -> None:
        assert _decide(_clean()).decision == QualityDecision.PASS

    def test_advisory_only_maps_to_pass(self) -> None:
        assert _decide(_advisory()).decision == QualityDecision.PASS

    def test_warnings_present_maps_to_pass_with_warnings(self) -> None:
        assert _decide(_warn()).decision == QualityDecision.PASS_WITH_WARNINGS

    def test_failures_present_maps_to_fail(self) -> None:
        assert _decide(_failures()).decision == QualityDecision.FAIL

    def test_summary_records_the_assessment_level(self) -> None:
        result = _decide(_warn())
        assert result.summary.assessment_level == AssessmentLevel.WARNINGS_PRESENT
        assert result.summary.decision == result.decision


@pytest.mark.unit
class TestPolicyGovernedGates:
    def test_mandatory_gate_overrides_a_lenient_base_mapping(self) -> None:
        """A policy mapping FAILURES_PRESENT→PASS_WITH_WARNINGS still FAILs on the gate."""
        lenient_mapping = (
            DecisionRule(level=AssessmentLevel.CLEAN, decision=QualityDecision.PASS, note="x"),
            DecisionRule(
                level=AssessmentLevel.ADVISORY_ONLY, decision=QualityDecision.PASS, note="x"
            ),
            DecisionRule(
                level=AssessmentLevel.WARNINGS_PRESENT,
                decision=QualityDecision.PASS_WITH_WARNINGS,
                note="x",
            ),
            DecisionRule(
                level=AssessmentLevel.FAILURES_PRESENT,
                decision=QualityDecision.PASS_WITH_WARNINGS,
                note="lenient base",
            ),
        )
        gated = default_decision_policy().model_copy(
            update={"level_mapping": lenient_mapping, "fail_on_mandatory_failure": True}
        )
        ungated = default_decision_policy().model_copy(
            update={
                "level_mapping": lenient_mapping,
                "fail_on_mandatory_failure": False,
                "fail_on_blocking_failure": False,
            }
        )
        assert _decide(_failures(), policy=gated).decision == QualityDecision.FAIL
        assert (
            _decide(_failures(), policy=ungated).decision == QualityDecision.PASS_WITH_WARNINGS
        )

    def test_warn_on_advisory_maps_advisory_to_warnings(self) -> None:
        policy = default_decision_policy().model_copy(update={"warn_on_advisory": True})
        assert _decide(_advisory(), policy=policy).decision == QualityDecision.PASS_WITH_WARNINGS
        assert _decide(_advisory()).decision == QualityDecision.PASS

    def test_applied_rules_record_the_gates_that_fired(self) -> None:
        result = _decide(_failures())
        assert "fail_on_mandatory_failure" in result.explanation.applied_rules
        assert "fail_on_blocking_failure" in result.explanation.applied_rules

    def test_recommendation_gated_by_policy(self) -> None:
        with_rec = _decide(_failures())
        without_rec = _decide(
            _failures(),
            policy=default_decision_policy().model_copy(update={"emit_recommendations": False}),
        )
        assert with_rec.explanation.recommendations
        assert without_rec.explanation.recommendations == ()


@pytest.mark.unit
class TestExplanationAndStatistics:
    def test_explanation_is_fully_populated_for_a_fail(self) -> None:
        result = _decide(_failures())
        assert result.explanation.primary_reason
        assert result.explanation.contributing_factors
        assert result.explanation.applied_rules
        assert result.explanation.recommendations

    def test_primary_reason_names_the_mandatory_gate(self) -> None:
        assert "Mandatory release gate" in _decide(_failures()).explanation.primary_reason

    def test_statistics_come_from_the_assessment(self) -> None:
        assessment = _failures()
        result = _decide(assessment)
        assert result.statistics.rules_considered == assessment.assessment_summary.total_rules
        assert (
            result.statistics.mandatory_failures
            == assessment.assessment_summary.mandatory_failures
        )
        assert result.statistics.blocking_failures >= 1

    def test_pass_carries_no_recommendation(self) -> None:
        assert _decide(_clean()).explanation.recommendations == ()


@pytest.mark.unit
class TestDeterminismAndContract:
    def test_same_assessment_yields_identical_decision(self) -> None:
        assessment = _failures()
        assert _decide(assessment) == _decide(assessment)

    def test_decision_id_is_deterministic_from_assessment(self) -> None:
        assessment = _warn()
        first = _decide(assessment)
        second = _decide(assessment)
        assert first.decision_id == second.decision_id
        assert str(first.assessment_id) == str(assessment.assessment_id)

    def test_round_trips_from_serialization_alone(self) -> None:
        result = _decide(_failures())
        dumped = result.model_dump(mode="json", by_alias=True)
        assert QualityDecisionResult.model_validate(dumped) == result

    def test_is_immutable(self) -> None:
        from pydantic import ValidationError

        result = _decide(_clean())
        with pytest.raises(ValidationError):
            result.decision = QualityDecision.FAIL  # type: ignore[misc]

    def test_version_independent_of_policy_version(self) -> None:
        result = _decide(_clean())
        assert result.policy_version == default_decision_policy().policy_version
        assert isinstance(result.policy_version, DecisionPolicyVersion)
        assert result.result_version != result.policy_version
