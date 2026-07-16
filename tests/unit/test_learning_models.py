"""Architecture-only tests for the Learning Framework's canonical models
(CAP-086A, ADR-0029).

Covers construction, immutability, camelCase serialization, and the
"references exist / ids resolve" validators each model carries. No behaviour
is exercised — nothing is proposed, validated, or retired; these models are
assembly targets only (ADR-0029 Stage 3).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.learning.identity import (
    LearningCandidateId,
    LearningConfidenceId,
    LearningId,
    LearningLifecycleId,
    LearningPolicyId,
    LearningPolicyVersion,
    LearningValidationId,
)
from requirement_intelligence.learning.models import (
    Learning,
    LearningCandidate,
    LearningConfidence,
    LearningConfidenceLevel,
    LearningLifecycle,
    LearningMaturity,
    LearningMetrics,
    LearningSummary,
    LearningValidation,
    LearningValidationGate,
)

_NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _candidate(**overrides: object) -> LearningCandidate:
    defaults: dict[str, object] = dict(
        candidate_id=LearningCandidateId.for_source("bp-1"),
        source_best_practice_ids=("bp-1",),
        proposed_change="Adopt the practice organization-wide.",
        confidence=LearningConfidenceLevel.LOW,
    )
    defaults.update(overrides)
    return LearningCandidate(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestLearningCandidate:
    def test_constructs_with_valid_fields(self) -> None:
        candidate = _candidate()
        assert candidate.source_best_practice_ids == ("bp-1",)

    def test_is_immutable(self) -> None:
        candidate = _candidate()
        with pytest.raises(ValidationError):
            candidate.proposed_change = "mutated"  # type: ignore[misc]

    def test_rejects_zero_source_best_practices(self) -> None:
        with pytest.raises(ValidationError):
            _candidate(source_best_practice_ids=())

    def test_rejects_empty_proposed_change(self) -> None:
        with pytest.raises(ValidationError):
            _candidate(proposed_change="")

    def test_serializes_camel_case(self) -> None:
        dumped = _candidate().model_dump(mode="json", by_alias=True)
        assert "sourceBestPracticeIds" in dumped
        assert "proposedChange" in dumped

    def test_round_trips(self) -> None:
        candidate = _candidate()
        dumped = candidate.model_dump(mode="json", by_alias=True)
        assert LearningCandidate.model_validate(dumped) == candidate


@pytest.mark.unit
class TestLearningValidation:
    def _validation(self, **overrides: object) -> LearningValidation:
        defaults: dict[str, object] = dict(
            validation_id=LearningValidationId.for_ordinal("lr-test", 0),
            candidate_id=LearningCandidateId.for_source("bp-1"),
            gates_cleared=(
                LearningValidationGate.SUFFICIENT_ORGANIZATIONAL_KNOWLEDGE,
                LearningValidationGate.VALIDATED_EVIDENCE,
            ),
            rationale="Cleared the governed floor.",
            validated_at=_NOW,
            confidence=LearningConfidenceLevel.MEDIUM,
            policy_version=LearningPolicyVersion(1, 0, 0),
        )
        defaults.update(overrides)
        return LearningValidation(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_fields(self) -> None:
        validation = self._validation()
        assert len(validation.gates_cleared) == 2

    def test_rejects_zero_gates_cleared(self) -> None:
        with pytest.raises(ValidationError):
            self._validation(gates_cleared=())

    def test_is_immutable(self) -> None:
        validation = self._validation()
        with pytest.raises(ValidationError):
            validation.rationale = "mutated"  # type: ignore[misc]

    def test_rejects_empty_rationale(self) -> None:
        with pytest.raises(ValidationError):
            self._validation(rationale="")

    def test_accepts_all_six_gates(self) -> None:
        validation = self._validation(gates_cleared=tuple(LearningValidationGate))
        assert len(validation.gates_cleared) == 6

    def test_round_trips(self) -> None:
        validation = self._validation()
        dumped = validation.model_dump(mode="json", by_alias=True)
        assert LearningValidation.model_validate(dumped) == validation

    def test_serializes_camel_case(self) -> None:
        dumped = self._validation().model_dump(mode="json", by_alias=True)
        assert "gatesCleared" in dumped
        assert "validatedAt" in dumped
        assert "policyVersion" in dumped


@pytest.mark.unit
class TestLearningConfidence:
    def _confidence(self, **overrides: object) -> LearningConfidence:
        defaults: dict[str, object] = dict(
            confidence_id=LearningConfidenceId.for_ordinal("lr-test", 0),
            subject_id="lc-1",
            level=LearningConfidenceLevel.LOW,
            evidence_count=2,
            rationale="Two corroborating best practices.",
            recorded_at=_NOW,
        )
        defaults.update(overrides)
        return LearningConfidence(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_fields(self) -> None:
        confidence = self._confidence()
        assert confidence.level == LearningConfidenceLevel.LOW

    def test_supersedes_confidence_id_defaults_to_none(self) -> None:
        confidence = self._confidence()
        assert confidence.supersedes_confidence_id is None

    def test_accepts_a_superseding_reference(self) -> None:
        confidence = self._confidence(supersedes_confidence_id="lf-prior")
        assert confidence.supersedes_confidence_id == "lf-prior"

    def test_rejects_empty_subject_id(self) -> None:
        with pytest.raises(ValidationError):
            self._confidence(subject_id="")

    def test_rejects_negative_evidence_count(self) -> None:
        with pytest.raises(ValidationError):
            self._confidence(evidence_count=-1)

    def test_rejects_empty_rationale(self) -> None:
        with pytest.raises(ValidationError):
            self._confidence(rationale="")

    def test_is_immutable(self) -> None:
        confidence = self._confidence()
        with pytest.raises(ValidationError):
            confidence.level = LearningConfidenceLevel.HIGH  # type: ignore[misc]

    def test_round_trips(self) -> None:
        confidence = self._confidence()
        dumped = confidence.model_dump(mode="json", by_alias=True)
        assert LearningConfidence.model_validate(dumped) == confidence


@pytest.mark.unit
class TestLearning:
    def _learning(self, **overrides: object) -> Learning:
        defaults: dict[str, object] = dict(
            learning_id=LearningId.for_ordinal("lr-test", 0),
            candidate_id=LearningCandidateId.for_source("bp-1"),
            validation_id=LearningValidationId.for_ordinal("lr-test", 0),
            message="Adopt the practice organization-wide.",
            maturity=LearningMaturity.VALIDATED,
            confidence=LearningConfidenceLevel.VERIFIED,
        )
        defaults.update(overrides)
        return Learning(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_fields(self) -> None:
        learning = self._learning()
        assert learning.maturity == LearningMaturity.VALIDATED

    def test_is_immutable(self) -> None:
        learning = self._learning()
        with pytest.raises(ValidationError):
            learning.message = "mutated"  # type: ignore[misc]

    def test_rejects_empty_message(self) -> None:
        with pytest.raises(ValidationError):
            self._learning(message="")

    @pytest.mark.parametrize("maturity", list(LearningMaturity))
    def test_accepts_every_governed_maturity(self, maturity: LearningMaturity) -> None:
        learning = self._learning(maturity=maturity)
        assert learning.maturity == maturity

    def test_round_trips(self) -> None:
        learning = self._learning()
        dumped = learning.model_dump(mode="json", by_alias=True)
        assert Learning.model_validate(dumped) == learning

    def test_serializes_camel_case(self) -> None:
        dumped = self._learning().model_dump(mode="json", by_alias=True)
        assert "candidateId" in dumped
        assert "validationId" in dumped


@pytest.mark.unit
class TestLearningLifecycle:
    def _lifecycle(self, **overrides: object) -> LearningLifecycle:
        defaults: dict[str, object] = dict(
            lifecycle_id=LearningLifecycleId.for_ordinal("lr-test", 0),
            subject_id="lg-1",
            maturity=LearningMaturity.OBSERVED,
            maturity_reason="newly observed",
        )
        defaults.update(overrides)
        return LearningLifecycle(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_fields(self) -> None:
        lifecycle = self._lifecycle()
        assert lifecycle.maturity == LearningMaturity.OBSERVED

    def test_rejects_empty_subject_id(self) -> None:
        with pytest.raises(ValidationError):
            self._lifecycle(subject_id="")

    def test_rejects_empty_maturity_reason(self) -> None:
        with pytest.raises(ValidationError):
            self._lifecycle(maturity_reason="")

    def test_is_immutable(self) -> None:
        lifecycle = self._lifecycle()
        with pytest.raises(ValidationError):
            lifecycle.maturity = LearningMaturity.RETIRED  # type: ignore[misc]

    @pytest.mark.parametrize("maturity", list(LearningMaturity))
    def test_accepts_every_governed_maturity(self, maturity: LearningMaturity) -> None:
        lifecycle = self._lifecycle(maturity=maturity)
        assert lifecycle.maturity == maturity

    def test_round_trips(self) -> None:
        lifecycle = self._lifecycle()
        dumped = lifecycle.model_dump(mode="json", by_alias=True)
        assert LearningLifecycle.model_validate(dumped) == lifecycle


@pytest.mark.unit
class TestLearningSummary:
    def _summary(self, **overrides: object) -> LearningSummary:
        defaults: dict[str, object] = dict(
            policy_id=LearningPolicyId("default-learning-policy"),
            policy_version=LearningPolicyVersion(1, 0, 0),
            total_candidates=0,
            total_learnings=0,
            total_validations=0,
            headline="0 candidates, 0 learnings.",
        )
        defaults.update(overrides)
        return LearningSummary(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_fields(self) -> None:
        summary = self._summary()
        assert summary.total_candidates == 0

    def test_rejects_negative_counts(self) -> None:
        with pytest.raises(ValidationError):
            self._summary(total_candidates=-1)

    def test_rejects_empty_headline(self) -> None:
        with pytest.raises(ValidationError):
            self._summary(headline="")

    def test_is_immutable(self) -> None:
        summary = self._summary()
        with pytest.raises(ValidationError):
            summary.total_learnings = 5  # type: ignore[misc]

    def test_only_version_field_is_policy_version(self) -> None:
        version_fields = {
            name for name in LearningSummary.model_fields if "version" in name.lower()
        }
        assert version_fields == {"policy_version"}


@pytest.mark.unit
class TestLearningMetrics:
    def _metrics(self, **overrides: object) -> LearningMetrics:
        defaults: dict[str, object] = dict(
            candidate_count=0,
            learning_count=0,
            validation_count=0,
            observed_count=0,
            validated_count=0,
            trusted_count=0,
            institutional_count=0,
            standard_count=0,
            retired_count=0,
        )
        defaults.update(overrides)
        return LearningMetrics(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_fields(self) -> None:
        metrics = self._metrics(candidate_count=3)
        assert metrics.candidate_count == 3

    def test_rejects_negative_counts(self) -> None:
        with pytest.raises(ValidationError):
            self._metrics(learning_count=-1)

    def test_is_immutable(self) -> None:
        metrics = self._metrics()
        with pytest.raises(ValidationError):
            metrics.validation_count = 5  # type: ignore[misc]

    def test_has_no_dedicated_version_field(self) -> None:
        version_fields = {
            name for name in LearningMetrics.model_fields if "version" in name.lower()
        }
        assert version_fields == set()

    def test_round_trips(self) -> None:
        metrics = self._metrics()
        dumped = metrics.model_dump(mode="json", by_alias=True)
        assert LearningMetrics.model_validate(dumped) == metrics


@pytest.mark.unit
class TestGovernedVocabularies:
    def test_maturity_has_exactly_seven_members(self) -> None:
        assert {member.value for member in LearningMaturity} == {
            "candidate",
            "observed",
            "validated",
            "trusted",
            "institutional",
            "standard",
            "retired",
        }

    def test_confidence_has_exactly_four_members(self) -> None:
        assert {member.value for member in LearningConfidenceLevel} == {
            "low",
            "medium",
            "high",
            "verified",
        }

    def test_validation_gate_has_exactly_six_members(self) -> None:
        assert {member.value for member in LearningValidationGate} == {
            "sufficient_organizational_knowledge",
            "validated_evidence",
            "repeatability",
            "organizational_confidence",
            "organizational_usefulness",
            "complete_explainability",
        }
