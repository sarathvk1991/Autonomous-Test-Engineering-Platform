"""Unit tests for the Quality Governance canonical models (CAP-080A).

These assert the models' shape, immutability, camelCase serialization, tuple
collections, deterministic round-tripping, and the cross-referential/explainability
validator invariants — never any computation, because the models compute nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.quality_governance.identity import (
    QualityAssessmentId,
    QualityGovernanceResultId,
    QualityGovernanceVersion,
    QualityPolicyId,
    QualityPolicyVersion,
)
from requirement_intelligence.quality_governance.models import (
    ConsumedResultReference,
    QualityAssessment,
    QualityDecision,
    QualityFinding,
    QualityFindingCategory,
    QualityFindingCategoryCount,
    QualityGovernanceResult,
    QualityInputSource,
    QualitySeverity,
    QualitySummary,
)

_PID = QualityPolicyId("default-quality-policy")
_PVER = QualityPolicyVersion(1, 0, 0)
_FVER = QualityGovernanceVersion(1, 0, 0)


def _summary(
    decision: QualityDecision,
    *,
    score: int = 90,
    total: int = 0,
    warnings: int = 0,
    failures: int = 0,
) -> QualitySummary:
    return QualitySummary(
        decision=decision,
        overall_quality_score=score,
        policy_id=_PID,
        policy_version=_PVER,
        total_findings=total,
        warning_count=warnings,
        failure_count=failures,
        verdict="Test verdict.",
    )


def _finding(severity: QualitySeverity, fid: str = "f1") -> QualityFinding:
    return QualityFinding(
        finding_id=fid,
        category=QualityFindingCategory.RELEASE_POLICY_VIOLATION,
        severity=severity,
        source=QualityInputSource.GROUNDING,
        message="Test finding.",
    )


def _assessment(
    decision: QualityDecision,
    findings: tuple[QualityFinding, ...],
    summary: QualitySummary,
) -> QualityAssessment:
    return QualityAssessment(
        assessment_id=QualityAssessmentId.for_run("an-1", "ex-1"),
        analysis_id="an-1",
        execution_id="ex-1",
        decision=decision,
        findings=findings,
        summary=summary,
        policy_id=_PID,
        policy_version=_PVER,
        framework_version=_FVER,
    )


@pytest.mark.unit
class TestFindingAndSummary:
    def test_finding_serialises_camelcase(self) -> None:
        dumped = _finding(QualitySeverity.WARNING).model_dump(mode="json", by_alias=True)
        assert dumped["findingId"] == "f1"
        assert dumped["severity"] == "warning"
        assert dumped["source"] == "grounding"

    def test_summary_distribution_is_a_tuple(self) -> None:
        s = QualitySummary(
            decision=QualityDecision.PASS,
            overall_quality_score=100,
            policy_id=_PID,
            policy_version=_PVER,
            total_findings=0,
            warning_count=0,
            failure_count=0,
            category_distribution=(
                QualityFindingCategoryCount(
                    category=QualityFindingCategory.HALLUCINATION_RATE_EXCEEDED, count=0
                ),
            ),
            verdict="ok",
        )
        assert isinstance(s.category_distribution, tuple)

    def test_models_are_frozen(self) -> None:
        s = _summary(QualityDecision.PASS)
        with pytest.raises(ValidationError):
            s.overall_quality_score = 1  # type: ignore[misc]

    def test_score_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            _summary(QualityDecision.PASS, score=101)


@pytest.mark.unit
class TestAssessmentInvariants:
    def test_clean_pass_is_valid(self) -> None:
        a = _assessment(QualityDecision.PASS, (), _summary(QualityDecision.PASS))
        assert a.decision == QualityDecision.PASS

    def test_pass_with_warnings_requires_warning_findings(self) -> None:
        summ = _summary(QualityDecision.PASS_WITH_WARNINGS, total=1, warnings=1)
        a = _assessment(
            QualityDecision.PASS_WITH_WARNINGS, (_finding(QualitySeverity.WARNING),), summ
        )
        assert a.summary.warning_count == 1

    def test_fail_requires_a_failure_finding(self) -> None:
        summ = _summary(QualityDecision.FAIL, total=0)
        with pytest.raises(ValidationError):
            _assessment(QualityDecision.FAIL, (), summ)

    def test_pass_cannot_carry_warning_findings(self) -> None:
        summ = _summary(QualityDecision.PASS, total=1, warnings=1)
        with pytest.raises(ValidationError):
            _assessment(QualityDecision.PASS, (_finding(QualitySeverity.WARNING),), summ)

    def test_summary_counts_must_match_findings(self) -> None:
        # Decision says FAIL, one failure finding, but summary miscounts.
        summ = _summary(QualityDecision.FAIL, total=1, failures=0, warnings=0)
        with pytest.raises(ValidationError):
            _assessment(QualityDecision.FAIL, (_finding(QualitySeverity.FAILURE),), summ)

    def test_summary_decision_must_match_assessment(self) -> None:
        with pytest.raises(ValidationError):
            _assessment(QualityDecision.PASS, (), _summary(QualityDecision.FAIL, failures=1))


@pytest.mark.unit
class TestGovernanceResult:
    def _result(self) -> QualityGovernanceResult:
        a = _assessment(QualityDecision.PASS, (), _summary(QualityDecision.PASS))
        return QualityGovernanceResult(
            result_id=QualityGovernanceResultId.for_assessment(str(a.assessment_id)),
            analysis_id="an-1",
            execution_id="ex-1",
            assessment=a,
            consumed_inputs=(
                ConsumedResultReference(
                    source=QualityInputSource.GROUNDING, result_id="g1", result_version="1.0.0"
                ),
                ConsumedResultReference(
                    source=QualityInputSource.VALIDATION, result_id="v1", result_version="1.0.0"
                ),
            ),
            policy_id=_PID,
            policy_version=_PVER,
            framework_version=_FVER,
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, tzinfo=UTC),
        )

    def test_round_trips_deterministically(self) -> None:
        res = self._result()
        dumped = res.model_dump(mode="json", by_alias=True)
        assert QualityGovernanceResult.model_validate(dumped) == res
        assert dumped["resultVersion"] == "1.0.0"

    def test_completed_before_started_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QualityGovernanceResult(
                result_id=QualityGovernanceResultId("qg-x"),
                analysis_id="an-1",
                execution_id="ex-1",
                assessment=_assessment(QualityDecision.PASS, (), _summary(QualityDecision.PASS)),
                policy_id=_PID,
                policy_version=_PVER,
                framework_version=_FVER,
                started_at=datetime(2026, 1, 2, tzinfo=UTC),
                completed_at=datetime(2026, 1, 1, tzinfo=UTC),
            )

    def test_duplicate_consumed_source_rejected(self) -> None:
        a = _assessment(QualityDecision.PASS, (), _summary(QualityDecision.PASS))
        with pytest.raises(ValidationError):
            QualityGovernanceResult(
                result_id=QualityGovernanceResultId("qg-x"),
                analysis_id="an-1",
                execution_id="ex-1",
                assessment=a,
                consumed_inputs=(
                    ConsumedResultReference(
                        source=QualityInputSource.CP1, result_id="c1", result_version="1.1"
                    ),
                    ConsumedResultReference(
                        source=QualityInputSource.CP1, result_id="c2", result_version="1.1"
                    ),
                ),
                policy_id=_PID,
                policy_version=_PVER,
                framework_version=_FVER,
                started_at=datetime(2026, 1, 1, tzinfo=UTC),
                completed_at=datetime(2026, 1, 1, tzinfo=UTC),
            )

    def test_assessment_provenance_must_agree_with_result(self) -> None:
        a = _assessment(QualityDecision.PASS, (), _summary(QualityDecision.PASS))
        with pytest.raises(ValidationError):
            QualityGovernanceResult(
                result_id=QualityGovernanceResultId("qg-x"),
                analysis_id="MISMATCH",
                execution_id="ex-1",
                assessment=a,
                policy_id=_PID,
                policy_version=_PVER,
                framework_version=_FVER,
                started_at=datetime(2026, 1, 1, tzinfo=UTC),
                completed_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
