"""Unit tests for the Quality Assessment canonical models and policy (CAP-080A.2).

Shape, immutability, camelCase serialization, tuple collections, deterministic
round-tripping, and the validator invariants — never a calculation and never a release
decision, because the models carry only observations (ADR-0017 Recommendation 1/4).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.quality_governance.assessment import (
    ASSESSMENT_OUTCOME_VERSION,
    ASSESSMENT_POLICY_VERSION,
    DEFAULT_ASSESSMENT_POLICY_ID,
    QUALITY_ASSESSMENT_RESULT_VERSION,
    AssessmentConflictPolicy,
    AssessmentDistributionEntry,
    AssessmentFindingReference,
    AssessmentLevel,
    AssessmentOutcome,
    AssessmentPolicy,
    AssessmentPolicyBuilder,
    AssessmentStatistics,
    AssessmentSummary,
    QualityAssessmentResult,
    default_assessment_policy,
)
from requirement_intelligence.quality_governance.evaluation import (
    RuleCategory,
    RuleEvaluationStatus,
)
from requirement_intelligence.quality_governance.identity import (
    AssessmentPolicyVersion,
    QualityAssessmentResultId,
    RuleEvaluationId,
    RuleEvaluationResultId,
)
from requirement_intelligence.quality_governance.models import QualitySeverity

_REVR = RuleEvaluationResultId.for_run("an-1", "ex-1")
_AID = QualityAssessmentResultId.for_evaluation(str(_REVR))
_POLICY = default_assessment_policy()


def _ref(
    rule_id: str = "r1", status: RuleEvaluationStatus = RuleEvaluationStatus.FAIL
) -> AssessmentFindingReference:
    return AssessmentFindingReference(
        evaluation_id=RuleEvaluationId.for_rule(str(_REVR), rule_id),
        rule_id=rule_id,
        severity=QualitySeverity.FAILURE,
        status=status,
        note="informs the assessment",
    )


def _outcome(
    level: AssessmentLevel = AssessmentLevel.CLEAN,
    *,
    blocking: bool = False,
    mandatory: int = 0,
) -> AssessmentOutcome:
    return AssessmentOutcome(
        level=level,
        has_blocking_failure=blocking,
        mandatory_failure_count=mandatory,
        summary_text="observed",
    )


def _summary(
    *, total: int = 0, passed: int = 0, failed: int = 0, skipped: int = 0, mandatory: int = 0
) -> AssessmentSummary:
    return AssessmentSummary(
        total_rules=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        mandatory_failures=mandatory,
        warnings=0,
        advisories=0,
        verdict="observation",
    )


def _result(
    *,
    references: tuple[AssessmentFindingReference, ...] = (),
    summary: AssessmentSummary | None = None,
    outcome: AssessmentOutcome | None = None,
) -> QualityAssessmentResult:
    return QualityAssessmentResult(
        assessment_id=_AID,
        rule_evaluation_result_id=_REVR,
        analysis_id="an-1",
        execution_id="ex-1",
        references=references,
        assessment_summary=summary or _summary(),
        assessment_statistics=AssessmentStatistics(),
        overall_assessment=outcome or _outcome(),
        policy_id=_POLICY.policy_id,
        policy_version=_POLICY.policy_version,
    )


@pytest.mark.unit
class TestOutcomeAndDistributions:
    def test_four_levels_present(self) -> None:
        assert {level.value for level in AssessmentLevel} == {
            "clean",
            "advisory_only",
            "warnings_present",
            "failures_present",
        }

    def test_outcome_serialises_camelcase_and_versioned(self) -> None:
        dumped = _outcome().model_dump(mode="json", by_alias=True)
        assert dumped["hasBlockingFailure"] is False
        assert dumped["outcomeVersion"] == str(ASSESSMENT_OUTCOME_VERSION)

    def test_mandatory_failure_implies_blocking(self) -> None:
        with pytest.raises(ValidationError):
            AssessmentOutcome(
                level=AssessmentLevel.FAILURES_PRESENT,
                has_blocking_failure=False,
                mandatory_failure_count=1,
                summary_text="x",
            )

    def test_blocking_requires_failures_present_level(self) -> None:
        with pytest.raises(ValidationError):
            AssessmentOutcome(
                level=AssessmentLevel.WARNINGS_PRESENT,
                has_blocking_failure=True,
                mandatory_failure_count=0,
                summary_text="x",
            )

    def test_distribution_entry_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AssessmentDistributionEntry(label="grounding", count=-1)

    def test_reference_is_frozen(self) -> None:
        ref = _ref()
        with pytest.raises(ValidationError):
            ref.rule_id = "changed"  # type: ignore[misc]


@pytest.mark.unit
class TestQualityAssessmentResult:
    def test_round_trips_deterministically(self) -> None:
        res = _result(references=(_ref(),))
        dumped = res.model_dump(mode="json", by_alias=True)
        assert QualityAssessmentResult.model_validate(dumped) == res
        assert dumped["resultVersion"] == str(QUALITY_ASSESSMENT_RESULT_VERSION)

    def test_references_are_a_tuple(self) -> None:
        assert isinstance(_result(references=(_ref(),)).references, tuple)

    def test_summary_totals_must_be_consistent(self) -> None:
        with pytest.raises(ValidationError):
            _result(summary=_summary(total=5, passed=1, failed=1, skipped=1))

    def test_duplicate_reference_ids_rejected(self) -> None:
        dup = _ref("same")
        with pytest.raises(ValidationError):
            _result(references=(dup, dup))

    def test_outcome_mandatory_must_match_summary(self) -> None:
        with pytest.raises(ValidationError):
            _result(
                summary=_summary(total=1, failed=1, mandatory=1),
                outcome=_outcome(AssessmentLevel.FAILURES_PRESENT, blocking=True, mandatory=0),
            )

    def test_consistent_failure_assessment_is_valid(self) -> None:
        res = _result(
            references=(_ref(),),
            summary=_summary(total=1, failed=1, mandatory=1),
            outcome=_outcome(AssessmentLevel.FAILURES_PRESENT, blocking=True, mandatory=1),
        )
        assert res.overall_assessment.level == AssessmentLevel.FAILURES_PRESENT

    def test_carries_no_decision_or_score(self) -> None:
        fields = set(QualityAssessmentResult.model_fields)
        assert "decision" not in fields
        assert "quality_score" not in fields
        assert "overall_quality_score" not in fields


@pytest.mark.unit
class TestAssessmentPolicy:
    def test_default_versioned_and_identified(self) -> None:
        assert _POLICY.policy_id == DEFAULT_ASSESSMENT_POLICY_ID
        assert _POLICY.policy_version == ASSESSMENT_POLICY_VERSION

    def test_builder_is_deterministic(self) -> None:
        assert AssessmentPolicyBuilder().build() == AssessmentPolicyBuilder().build()

    def test_policy_is_immutable(self) -> None:
        with pytest.raises(ValidationError):
            _POLICY.description = "changed"  # type: ignore[misc]

    def test_precedence_covers_all_categories(self) -> None:
        assert set(_POLICY.precedence) == set(RuleCategory)

    def test_precedence_is_a_tuple(self) -> None:
        assert isinstance(_POLICY.precedence, tuple)

    def test_conflict_resolution_governed(self) -> None:
        assert _POLICY.conflict_resolution == AssessmentConflictPolicy.MANDATORY_WINS

    def test_policy_round_trips(self) -> None:
        dumped = _POLICY.model_dump(mode="json", by_alias=True)
        assert AssessmentPolicy.model_validate(dumped) == _POLICY

    def test_weights_are_non_negative_data(self) -> None:
        assert _POLICY.weights.mandatory_weight >= _POLICY.weights.advisory_weight

    def test_policy_version_independent_type(self) -> None:
        assert isinstance(_POLICY.policy_version, AssessmentPolicyVersion)
