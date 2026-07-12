"""Unit tests for the Quality Decision canonical models and policy (CAP-080A.3).

Shape, immutability, camelCase serialization, tuple collections, deterministic
round-tripping, and the validator invariants. The Decision layer is the sole owner of
``PASS`` / ``PASS_WITH_WARNINGS`` / ``FAIL`` (ADR-0017 Recommendation 2); the models
carry the decision but compute nothing.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.quality_governance.assessment import AssessmentLevel
from requirement_intelligence.quality_governance.decision import (
    DECISION_VERSION,
    QUALITY_DECISION_RESULT_VERSION,
    DecisionExplanation,
    DecisionPolicy,
    DecisionPolicyBuilder,
    DecisionRule,
    DecisionStatistics,
    DecisionSummary,
    QualityDecisionResult,
    default_decision_policy,
)
from requirement_intelligence.quality_governance.decision.policy import (
    DECISION_POLICY_VERSION,
    DEFAULT_DECISION_POLICY_ID,
)
from requirement_intelligence.quality_governance.identity import (
    DecisionPolicyVersion,
    QualityAssessmentResultId,
    QualityDecisionResultId,
)
from requirement_intelligence.quality_governance.models import QualityDecision

_AID = QualityAssessmentResultId.for_evaluation("revr-x")
_DID = QualityDecisionResultId.for_assessment(str(_AID))
_POLICY = default_decision_policy()


def _summary(decision: QualityDecision = QualityDecision.PASS) -> DecisionSummary:
    return DecisionSummary(decision=decision, assessment_level=AssessmentLevel.CLEAN, verdict="ok")


def _stats() -> DecisionStatistics:
    return DecisionStatistics(
        rules_considered=3, mandatory_failures=0, blocking_failures=0, warnings=0, advisories=0
    )


def _explanation() -> DecisionExplanation:
    return DecisionExplanation(primary_reason="all governed rules satisfied")


def _result(decision: QualityDecision = QualityDecision.PASS) -> QualityDecisionResult:
    return QualityDecisionResult(
        decision_id=_DID,
        assessment_id=_AID,
        analysis_id="an-1",
        execution_id="ex-1",
        decision=decision,
        summary=_summary(decision),
        statistics=_stats(),
        explanation=_explanation(),
        policy_id=_POLICY.policy_id,
        policy_version=_POLICY.policy_version,
    )


@pytest.mark.unit
class TestDecisionModels:
    def test_result_round_trips_deterministically(self) -> None:
        res = _result(QualityDecision.FAIL)
        dumped = res.model_dump(mode="json", by_alias=True)
        assert QualityDecisionResult.model_validate(dumped) == res
        assert dumped["resultVersion"] == str(QUALITY_DECISION_RESULT_VERSION)

    def test_explanation_tuples_and_versioned(self) -> None:
        expl = DecisionExplanation(
            primary_reason="x",
            contributing_factors=("a", "b"),
            applied_rules=("fail_on_mandatory_failure",),
            recommendations=("re-ground",),
        )
        assert isinstance(expl.contributing_factors, tuple)
        assert expl.decision_version == DECISION_VERSION

    def test_result_is_frozen(self) -> None:
        res = _result()
        with pytest.raises(ValidationError):
            res.decision = QualityDecision.FAIL  # type: ignore[misc]

    def test_summary_decision_must_match_result(self) -> None:
        with pytest.raises(ValidationError):
            QualityDecisionResult(
                decision_id=_DID,
                assessment_id=_AID,
                analysis_id="an-1",
                execution_id="ex-1",
                decision=QualityDecision.FAIL,
                summary=_summary(QualityDecision.PASS),
                statistics=_stats(),
                explanation=_explanation(),
                policy_id=_POLICY.policy_id,
                policy_version=_POLICY.policy_version,
            )

    def test_statistics_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DecisionStatistics(
                rules_considered=-1,
                mandatory_failures=0,
                blocking_failures=0,
                warnings=0,
                advisories=0,
            )

    def test_carries_the_decision_but_no_score(self) -> None:
        fields = set(QualityDecisionResult.model_fields)
        assert "decision" in fields  # Decision owns the release status
        assert "quality_score" not in fields
        assert "overall_quality_score" not in fields

    def test_all_three_decisions_are_representable(self) -> None:
        for d in (QualityDecision.PASS, QualityDecision.PASS_WITH_WARNINGS, QualityDecision.FAIL):
            assert _result(d).decision == d


@pytest.mark.unit
class TestDecisionPolicy:
    def test_default_versioned_and_identified(self) -> None:
        assert _POLICY.policy_id == DEFAULT_DECISION_POLICY_ID
        assert _POLICY.policy_version == DECISION_POLICY_VERSION

    def test_builder_is_deterministic(self) -> None:
        assert DecisionPolicyBuilder().build() == DecisionPolicyBuilder().build()

    def test_policy_is_immutable(self) -> None:
        with pytest.raises(ValidationError):
            _POLICY.description = "changed"  # type: ignore[misc]

    def test_mapping_covers_every_level_once(self) -> None:
        levels = [AssessmentLevel(rule.level) for rule in _POLICY.level_mapping]
        assert set(levels) == set(AssessmentLevel)
        assert len(levels) == len(set(levels))

    def test_mapping_is_a_tuple(self) -> None:
        assert isinstance(_POLICY.level_mapping, tuple)

    def test_mandatory_gates_present(self) -> None:
        assert _POLICY.fail_on_blocking_failure
        assert _POLICY.fail_on_mandatory_failure

    def test_policy_round_trips(self) -> None:
        dumped = _POLICY.model_dump(mode="json", by_alias=True)
        assert DecisionPolicy.model_validate(dumped) == _POLICY

    def test_policy_rejects_incomplete_mapping(self) -> None:
        with pytest.raises(ValidationError):
            DecisionPolicy(
                policy_id=DEFAULT_DECISION_POLICY_ID,
                policy_version=DecisionPolicyVersion(1, 0, 0),
                description="incomplete",
                level_mapping=(
                    DecisionRule(
                        level=AssessmentLevel.CLEAN, decision=QualityDecision.PASS, note="x"
                    ),
                ),
            )

    def test_policy_rejects_duplicate_level(self) -> None:
        rule = DecisionRule(level=AssessmentLevel.CLEAN, decision=QualityDecision.PASS, note="x")
        with pytest.raises(ValidationError):
            DecisionPolicy(
                policy_id=DEFAULT_DECISION_POLICY_ID,
                policy_version=DecisionPolicyVersion(1, 0, 0),
                description="dup",
                level_mapping=(rule, rule),
            )
