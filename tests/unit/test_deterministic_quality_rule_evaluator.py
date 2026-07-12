"""Behaviour, explainability, and determinism tests for the deterministic evaluator (CAP-080B).

Exercises :class:`DeterministicQualityRuleEvaluator` end-to-end over synthetic
``GroundingResult`` / ``ValidationResult`` / ``CP1Result`` carriers: evaluator identity,
governed thresholds, the three statuses (PASS / FAIL / SKIPPED), statistics and
distributions, explainability, and byte-stable determinism (ADR-0017 §D25,
Recommendation 3/5).
"""

from __future__ import annotations

import pytest

from requirement_intelligence.quality_governance.evaluation import (
    RULE_EVALUATOR_NAME,
    RULE_EVALUATOR_VERSION,
    DeterministicQualityRuleEvaluator,
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


def _evaluator(policy=None, catalog=None) -> DeterministicQualityRuleEvaluator:
    return DeterministicQualityRuleEvaluator(
        policy=policy or default_quality_policy(),
        catalog=catalog or default_quality_rule_catalog(),
    )


def _clean_run() -> RuleEvaluationResult:
    return _evaluator().evaluate(
        make_grounding_result(
            grounding_score=95, hallucination_rate=0.0, average_confidence=90, evidence_coverage=0.9
        ),
        make_validation_result(verdict=ValidationSubsystemVerdict.PASSED),
        make_cp1_result(verdict=CP1Verdict.PASS),
    )


def _find(result: RuleEvaluationResult, rule_id: str):  # type: ignore[no-untyped-def]
    return next(e for e in result.evaluations if e.rule_id == rule_id)


@pytest.mark.unit
class TestEvaluatorIdentity:
    def test_result_carries_evaluator_name_and_version(self) -> None:
        result = _clean_run()
        assert result.evaluator_name == RULE_EVALUATOR_NAME
        assert result.evaluator_version == RULE_EVALUATOR_VERSION

    def test_evaluator_name_is_the_frozen_identity(self) -> None:
        assert RULE_EVALUATOR_NAME == "deterministic_quality_rule_v1"
        assert str(RULE_EVALUATOR_VERSION) == "1.0.0"

    def test_evaluator_identity_independent_of_policy_version(self) -> None:
        result = _clean_run()
        assert result.policy_version == default_quality_policy().policy_version
        assert result.evaluator_version != result.policy_version  # distinct axes


@pytest.mark.unit
class TestPassAndFail:
    def test_clean_run_all_pass(self) -> None:
        result = _clean_run()
        assert result.summary.failed == 0
        assert result.summary.skipped == 0
        assert result.summary.passed == len(result.evaluations)

    def test_low_grounding_score_fails_failure_rule(self) -> None:
        result = _evaluator().evaluate(
            make_grounding_result(grounding_score=40),
            make_validation_result(),
            make_cp1_result(),
        )
        assert _find(result, "QG-GRD-001").status == RuleEvaluationStatus.FAIL

    def test_high_hallucination_fails_mandatory_gate(self) -> None:
        result = _evaluator().evaluate(
            make_grounding_result(hallucination_rate=0.5),
            make_validation_result(),
            make_cp1_result(),
        )
        assert _find(result, "QG-REL-001").status == RuleEvaluationStatus.FAIL

    def test_validation_failure_fails_mandatory_verdict_gate(self) -> None:
        result = _evaluator().evaluate(
            make_grounding_result(),
            make_validation_result(verdict=ValidationSubsystemVerdict.FAILED),
            make_cp1_result(),
        )
        assert _find(result, "QG-REL-002").status == RuleEvaluationStatus.FAIL

    def test_cp1_failure_fails_readiness_and_verdict_gates(self) -> None:
        result = _evaluator().evaluate(
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(verdict=CP1Verdict.FAIL),
        )
        assert _find(result, "QG-REL-003").status == RuleEvaluationStatus.FAIL
        assert _find(result, "QG-REL-004").status == RuleEvaluationStatus.FAIL

    def test_cross_layer_anomaly_flagged(self) -> None:
        """Validation and CP1 pass while grounding fails → both cross-layer rules FAIL."""
        result = _evaluator().evaluate(
            make_grounding_result(grounding_score=40),
            make_validation_result(verdict=ValidationSubsystemVerdict.PASSED),
            make_cp1_result(verdict=CP1Verdict.PASS),
        )
        assert _find(result, "QG-XSS-001").status == RuleEvaluationStatus.FAIL
        assert _find(result, "QG-XSS-002").status == RuleEvaluationStatus.FAIL

    def test_validation_counts_over_budget_fail(self) -> None:
        result = _evaluator().evaluate(
            make_grounding_result(),
            make_validation_result(critical=2, error=1, warning=9),
            make_cp1_result(),
        )
        assert _find(result, "QG-VAL-001").status == RuleEvaluationStatus.FAIL
        assert _find(result, "QG-VAL-002").status == RuleEvaluationStatus.FAIL
        assert _find(result, "QG-VAL-003").status == RuleEvaluationStatus.FAIL

    def test_cp1_blocking_findings_over_budget_fail(self) -> None:
        result = _evaluator().evaluate(
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(blocking_findings=3),
        )
        assert _find(result, "QG-CP1-001").status == RuleEvaluationStatus.FAIL


@pytest.mark.unit
class TestSkipped:
    def test_disabled_release_toggle_skips_mandatory_rule(self) -> None:
        policy = default_quality_policy().model_copy(
            update={
                "release_rules": QualityReleaseRules(
                    block_on_hallucination=False,
                    block_on_validation_failure=False,
                    block_on_cp1_failure=False,
                    require_engineering_readiness=False,
                )
            }
        )
        result = _evaluator(policy=policy).evaluate(
            make_grounding_result(hallucination_rate=0.9),
            make_validation_result(verdict=ValidationSubsystemVerdict.FAILED),
            make_cp1_result(verdict=CP1Verdict.FAIL),
        )
        for rule_id in ("QG-REL-001", "QG-REL-002", "QG-REL-003", "QG-REL-004"):
            assert _find(result, rule_id).status == RuleEvaluationStatus.SKIPPED
        assert result.summary.skipped == 4

    def test_disabled_rule_not_evaluated_at_all(self) -> None:
        catalog = default_quality_rule_catalog()
        disabled = catalog.rules[0].model_copy(update={"enabled": False})
        trimmed = catalog.model_copy(update={"rules": (disabled, *catalog.rules[1:])})
        result = _evaluator(catalog=trimmed).evaluate(
            make_grounding_result(), make_validation_result(), make_cp1_result()
        )
        assert all(e.rule_id != disabled.rule_id for e in result.evaluations)
        assert len(result.evaluations) == len(catalog.rules) - 1


@pytest.mark.unit
class TestGovernedThresholds:
    def test_threshold_comes_from_policy_not_hard_coded(self) -> None:
        """Retuning the policy threshold flips the outcome — no number is hard-coded."""
        strict = default_quality_policy()
        lenient_thresholds = strict.failure_thresholds.model_copy(
            update={"minimum_grounding_score": 30}
        )
        lenient = strict.model_copy(update={"failure_thresholds": lenient_thresholds})

        grounding = make_grounding_result(grounding_score=40)
        strict_result = _evaluator(policy=strict).evaluate(
            grounding, make_validation_result(), make_cp1_result()
        )
        lenient_result = _evaluator(policy=lenient).evaluate(
            grounding, make_validation_result(), make_cp1_result()
        )
        assert _find(strict_result, "QG-GRD-001").status == RuleEvaluationStatus.FAIL
        assert _find(lenient_result, "QG-GRD-001").status == RuleEvaluationStatus.PASS

    def test_threshold_string_matches_policy_value(self) -> None:
        result = _clean_run()
        expected = str(default_quality_policy().failure_thresholds.minimum_grounding_score)
        assert _find(result, "QG-GRD-001").threshold == expected


@pytest.mark.unit
class TestStatisticsAndSummary:
    def test_summary_counts_match_evaluations(self) -> None:
        result = _clean_run()
        passed = sum(1 for e in result.evaluations if e.status == RuleEvaluationStatus.PASS)
        assert result.summary.total_rules == len(result.evaluations)
        assert result.summary.passed == passed

    def test_category_distribution_covers_all_rules(self) -> None:
        result = _clean_run()
        total = sum(c.count for c in result.statistics.category_distribution)
        assert total == len(result.evaluations)

    def test_severity_distribution_covers_all_rules(self) -> None:
        result = _clean_run()
        total = sum(s.count for s in result.statistics.severity_distribution)
        assert total == len(result.evaluations)

    def test_mandatory_and_advisory_counts(self) -> None:
        result = _clean_run()
        assert result.statistics.mandatory_rules_evaluated == 4
        assert result.statistics.advisory_rules_evaluated == 1


@pytest.mark.unit
class TestExplainability:
    def test_every_numeric_evaluation_records_expected_actual_threshold_reason(self) -> None:
        result = _evaluator().evaluate(
            make_grounding_result(grounding_score=40),
            make_validation_result(),
            make_cp1_result(),
        )
        ev = _find(result, "QG-GRD-001")
        assert ev.expected_value == ">= 60"
        assert ev.actual_value == "40"
        assert ev.threshold == "60"
        assert ev.reason
        assert ev.rule_id == "QG-GRD-001"
        assert ev.rule_name

    def test_condition_rule_records_expected_and_actual(self) -> None:
        result = _evaluator().evaluate(
            make_grounding_result(),
            make_validation_result(verdict=ValidationSubsystemVerdict.FAILED),
            make_cp1_result(),
        )
        ev = _find(result, "QG-REL-002")
        assert ev.expected_value == "condition must not hold"
        assert "failed" in ev.actual_value
        assert ev.threshold is None
        assert ev.reason

    def test_result_reconstructs_from_serialization_alone(self) -> None:
        result = _clean_run()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert RuleEvaluationResult.model_validate(dumped) == result


@pytest.mark.unit
class TestDeterminism:
    def test_same_inputs_yield_identical_result(self) -> None:
        first = _clean_run()
        second = _clean_run()
        assert first == second

    def test_serialization_is_byte_stable(self) -> None:
        import json

        first = json.dumps(_clean_run().model_dump(mode="json", by_alias=True), sort_keys=False)
        second = json.dumps(_clean_run().model_dump(mode="json", by_alias=True), sort_keys=False)
        assert first == second

    def test_evaluation_ids_are_unique_and_deterministic(self) -> None:
        result = _clean_run()
        ids = [str(e.evaluation_id) for e in result.evaluations]
        assert len(ids) == len(set(ids))
        assert ids == [str(e.evaluation_id) for e in _clean_run().evaluations]
