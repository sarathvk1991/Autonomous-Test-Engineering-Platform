"""Unit tests for the Rule Evaluation canonical models (CAP-080A.1).

Shape, immutability, camelCase serialization, tuple collections, deterministic
round-tripping, and the cross-referential validator invariants — never a calculation
or a decision, because the models carry only observations (ADR-0017 Recommendation 4).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.quality_governance.evaluation import (
    RULE_EVALUATION_RESULT_VERSION,
    RULE_EVALUATION_VERSION,
    RuleCategory,
    RuleCategoryCount,
    RuleEvaluation,
    RuleEvaluationResult,
    RuleEvaluationStatistics,
    RuleEvaluationStatus,
    RuleEvaluationSummary,
    RuleSeverityCount,
)
from requirement_intelligence.quality_governance.identity import (
    QualityPolicyVersion,
    RuleEvaluationId,
    RuleEvaluationResultId,
)
from requirement_intelligence.quality_governance.models import QualitySeverity

_RID = RuleEvaluationResultId.for_run("an-1", "ex-1")


def _evaluation(
    status: RuleEvaluationStatus,
    *,
    rule_id: str = "grounding.min_score",
    category: RuleCategory = RuleCategory.GROUNDING,
    severity: QualitySeverity = QualitySeverity.FAILURE,
) -> RuleEvaluation:
    return RuleEvaluation(
        evaluation_id=RuleEvaluationId.for_rule(str(_RID), rule_id),
        rule_id=rule_id,
        rule_name="Minimum grounding score",
        category=category,
        severity=severity,
        status=status,
        expected_value=">=80",
        actual_value="90",
        threshold="80",
        reason="observed 90 vs threshold 80",
    )


def _result(evaluations: tuple[RuleEvaluation, ...]) -> RuleEvaluationResult:
    passed = sum(1 for e in evaluations if e.status == RuleEvaluationStatus.PASS)
    failed = sum(1 for e in evaluations if e.status == RuleEvaluationStatus.FAIL)
    skipped = sum(1 for e in evaluations if e.status == RuleEvaluationStatus.SKIPPED)
    return RuleEvaluationResult(
        result_id=_RID,
        analysis_id="an-1",
        execution_id="ex-1",
        evaluations=evaluations,
        summary=RuleEvaluationSummary(
            total_rules=len(evaluations),
            passed=passed,
            failed=failed,
            skipped=skipped,
            verdict="evaluation complete",
        ),
        statistics=RuleEvaluationStatistics(
            mandatory_rules_evaluated=0,
            advisory_rules_evaluated=0,
        ),
        policy_version=QualityPolicyVersion(1, 0, 0),
    )


@pytest.mark.unit
class TestRuleEvaluation:
    def test_serialises_camelcase(self) -> None:
        dumped = _evaluation(RuleEvaluationStatus.PASS).model_dump(mode="json", by_alias=True)
        assert dumped["evaluationId"].startswith("rev-")
        assert dumped["ruleName"] == "Minimum grounding score"
        assert dumped["expectedValue"] == ">=80"
        assert dumped["evaluationVersion"] == str(RULE_EVALUATION_VERSION)

    def test_optional_values_default_to_none(self) -> None:
        ev = RuleEvaluation(
            evaluation_id=RuleEvaluationId.for_rule(str(_RID), "cp1.readiness"),
            rule_id="cp1.readiness",
            rule_name="CP1 readiness",
            category=RuleCategory.CP1,
            severity=QualitySeverity.FAILURE,
            status=RuleEvaluationStatus.SKIPPED,
            reason="no CP1 result available",
        )
        assert ev.expected_value is None
        assert ev.actual_value is None
        assert ev.threshold is None

    def test_is_frozen(self) -> None:
        ev = _evaluation(RuleEvaluationStatus.PASS)
        with pytest.raises(ValidationError):
            ev.status = RuleEvaluationStatus.FAIL  # type: ignore[misc]

    def test_blank_reason_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RuleEvaluation(
                evaluation_id=RuleEvaluationId.for_rule(str(_RID), "r"),
                rule_id="r",
                rule_name="r",
                category=RuleCategory.ADVISORY,
                severity=QualitySeverity.INFO,
                status=RuleEvaluationStatus.PASS,
                reason="",
            )

    def test_all_six_categories_present(self) -> None:
        assert {c.value for c in RuleCategory} == {
            "grounding",
            "validation",
            "cp1",
            "cross_subsystem",
            "mandatory_release",
            "advisory",
        }

    def test_three_statuses_present(self) -> None:
        assert {s.value for s in RuleEvaluationStatus} == {"pass", "fail", "skipped"}


@pytest.mark.unit
class TestDistributionEntries:
    def test_category_and_severity_counts(self) -> None:
        c = RuleCategoryCount(category=RuleCategory.VALIDATION, count=3)
        s = RuleSeverityCount(severity=QualitySeverity.WARNING, count=2)
        assert c.model_dump(by_alias=True) == {"category": "validation", "count": 3}
        assert s.model_dump(by_alias=True) == {"severity": "warning", "count": 2}

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RuleCategoryCount(category=RuleCategory.GROUNDING, count=-1)


@pytest.mark.unit
class TestRuleEvaluationResult:
    def test_round_trips_deterministically(self) -> None:
        res = _result((_evaluation(RuleEvaluationStatus.PASS),))
        dumped = res.model_dump(mode="json", by_alias=True)
        assert RuleEvaluationResult.model_validate(dumped) == res
        assert dumped["resultVersion"] == str(RULE_EVALUATION_RESULT_VERSION)

    def test_evaluations_are_a_tuple(self) -> None:
        res = _result((_evaluation(RuleEvaluationStatus.PASS),))
        assert isinstance(res.evaluations, tuple)

    def test_empty_evaluations_allowed(self) -> None:
        res = _result(())
        assert res.summary.total_rules == 0

    def test_summary_total_must_match_evaluations(self) -> None:
        with pytest.raises(ValidationError):
            RuleEvaluationResult(
                result_id=_RID,
                analysis_id="an-1",
                execution_id="ex-1",
                evaluations=(_evaluation(RuleEvaluationStatus.PASS),),
                summary=RuleEvaluationSummary(
                    total_rules=5, passed=1, failed=0, skipped=0, verdict="x"
                ),
                statistics=RuleEvaluationStatistics(
                    mandatory_rules_evaluated=0, advisory_rules_evaluated=0
                ),
                policy_version=QualityPolicyVersion(1, 0, 0),
            )

    def test_summary_status_counts_must_match(self) -> None:
        with pytest.raises(ValidationError):
            RuleEvaluationResult(
                result_id=_RID,
                analysis_id="an-1",
                execution_id="ex-1",
                evaluations=(_evaluation(RuleEvaluationStatus.FAIL),),
                summary=RuleEvaluationSummary(
                    total_rules=1, passed=1, failed=0, skipped=0, verdict="x"
                ),
                statistics=RuleEvaluationStatistics(
                    mandatory_rules_evaluated=0, advisory_rules_evaluated=0
                ),
                policy_version=QualityPolicyVersion(1, 0, 0),
            )

    def test_duplicate_evaluation_ids_rejected(self) -> None:
        dup = _evaluation(RuleEvaluationStatus.PASS)
        with pytest.raises(ValidationError):
            RuleEvaluationResult(
                result_id=_RID,
                analysis_id="an-1",
                execution_id="ex-1",
                evaluations=(dup, dup),
                summary=RuleEvaluationSummary(
                    total_rules=2, passed=2, failed=0, skipped=0, verdict="x"
                ),
                statistics=RuleEvaluationStatistics(
                    mandatory_rules_evaluated=0, advisory_rules_evaluated=0
                ),
                policy_version=QualityPolicyVersion(1, 0, 0),
            )

    def test_mixed_statuses_summary_is_valid(self) -> None:
        res = _result(
            (
                _evaluation(RuleEvaluationStatus.PASS, rule_id="a"),
                _evaluation(RuleEvaluationStatus.FAIL, rule_id="b"),
                _evaluation(RuleEvaluationStatus.SKIPPED, rule_id="c"),
            )
        )
        assert (res.summary.passed, res.summary.failed, res.summary.skipped) == (1, 1, 1)

    def test_carries_no_score_or_decision(self) -> None:
        # ADR-0017 Rec 4: the boundary is observations only.
        fields = set(RuleEvaluationResult.model_fields)
        assert "quality_score" not in fields
        assert "decision" not in fields
        assert "overall_quality_score" not in fields
