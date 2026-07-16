"""Architecture-only tests for the CAP-086A LearningResult freeze.

These assert the *runtime contract* invariants — not behaviour (no engine
exists yet, so there is no behaviour to test). They cover cross-referential
integrity (learnings/validations/confidences/lifecycles must resolve among
the result's own candidates/learnings), immutability, serialization
round-trip, the explainability invariant, and the frozen runtime boundary
(ADR-0029 §D3/§D4), mirroring ``test_organizational_memory_result_freeze.py``
(ADR-0027 §D3/§D4) as it stood before CAP-085B introduced an engine.

Because no engine exists yet, every ``LearningResult`` in these tests is
hand-built directly — the same discipline every sibling subsystem's own
CAP-0XXA freeze test used before its own engine existed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.learning.identity import (
    LearningCandidateId,
    LearningConfidenceId,
    LearningFrameworkVersion,
    LearningId,
    LearningLifecycleId,
    LearningLifecycleVersion,
    LearningPolicyId,
    LearningPolicyVersion,
    LearningResultId,
    LearningResultVersion,
    LearningValidationId,
    LearningValidationVersion,
    LearningVersion,
)
from requirement_intelligence.learning.models import (
    Learning,
    LearningCandidate,
    LearningConfidence,
    LearningConfidenceLevel,
    LearningLifecycle,
    LearningMaturity,
    LearningMetrics,
    LearningResult,
    LearningSummary,
    LearningValidation,
    LearningValidationGate,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEARNING_PKG = _REPO_ROOT / "requirement_intelligence" / "learning"
_NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _version_field_names(model: type) -> set[str]:
    return {name for name in model.model_fields if "version" in name.lower()}


def _result() -> LearningResult:
    candidate = LearningCandidate(
        candidate_id=LearningCandidateId.for_source("bp-1"),
        source_best_practice_ids=("bp-1",),
        proposed_change="Adopt the practice organization-wide.",
        confidence=LearningConfidenceLevel.LOW,
    )
    validation = LearningValidation(
        validation_id=LearningValidationId.for_ordinal("lr-freeze", 0),
        candidate_id=candidate.candidate_id,
        gates_cleared=tuple(LearningValidationGate),
        rationale="Cleared every governed gate.",
        validated_at=_NOW,
        confidence=LearningConfidenceLevel.VERIFIED,
        policy_version=LearningPolicyVersion(1, 0, 0),
    )
    learning = Learning(
        learning_id=LearningId.for_ordinal("lr-freeze", 0),
        candidate_id=candidate.candidate_id,
        validation_id=validation.validation_id,
        message="Adopt the practice organization-wide.",
        maturity=LearningMaturity.VALIDATED,
        confidence=LearningConfidenceLevel.VERIFIED,
    )
    confidence = LearningConfidence(
        confidence_id=LearningConfidenceId.for_ordinal("lr-freeze", 0),
        subject_id=str(learning.learning_id),
        level=LearningConfidenceLevel.VERIFIED,
        evidence_count=2,
        rationale="Two corroborating best practices.",
        recorded_at=_NOW,
    )
    lifecycle = LearningLifecycle(
        lifecycle_id=LearningLifecycleId.for_ordinal("lr-freeze", 0),
        subject_id=str(learning.learning_id),
        maturity=LearningMaturity.VALIDATED,
        maturity_reason="newly validated",
    )
    return LearningResult(
        result_id=LearningResultId.for_source("omr-1"),
        organizational_memory_result_id="omr-1",
        candidates=(candidate,),
        learnings=(learning,),
        validations=(validation,),
        confidences=(confidence,),
        lifecycles=(lifecycle,),
        summary=LearningSummary(
            policy_id=LearningPolicyId("default-learning-policy"),
            policy_version=LearningPolicyVersion(1, 0, 0),
            total_candidates=1,
            total_learnings=1,
            total_validations=1,
            headline="1 candidate, 1 learning.",
        ),
        metrics=LearningMetrics(
            candidate_count=1,
            learning_count=1,
            validation_count=1,
            observed_count=0,
            validated_count=1,
            trusted_count=0,
            institutional_count=0,
            standard_count=0,
            retired_count=0,
        ),
        policy_id=LearningPolicyId("default-learning-policy"),
        policy_version=LearningPolicyVersion(1, 0, 0),
        framework_version=LearningFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


@pytest.mark.unit
class TestRuntimeContractVersion:
    def test_result_version_is_its_own_type(self) -> None:
        assert isinstance(_result().result_version, LearningResultVersion)

    def test_runtime_version_is_independent_of_every_other_axis(self) -> None:
        other_axes = (
            LearningFrameworkVersion,
            LearningPolicyVersion,
            LearningVersion,
            LearningLifecycleVersion,
            LearningValidationVersion,
        )
        for axis in other_axes:
            assert not issubclass(LearningResultVersion, axis)
            assert not issubclass(axis, LearningResultVersion)
        assert len({LearningResultVersion, *other_axes}) == 6

    def test_candidate_has_no_dedicated_version_field(self) -> None:
        assert _version_field_names(LearningCandidate) == set()

    def test_validation_has_no_dedicated_schema_version_field(self) -> None:
        """LearningValidation carries only the governing policy_version (a policy
        reference, not a schema-version axis of its own)."""
        assert _version_field_names(LearningValidation) == {"policy_version"}

    def test_confidence_has_no_dedicated_version_field(self) -> None:
        assert _version_field_names(LearningConfidence) == set()


@pytest.mark.unit
class TestSelfContainedContract:
    def test_round_trips_from_serialization_alone(self) -> None:
        result = _result()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert LearningResult.model_validate(dumped) == result

    def test_deterministic_equality(self) -> None:
        assert _result() == _result()

    def test_is_immutable(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.result_id = "other"  # type: ignore[misc]

    def test_rejects_completed_before_started(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            LearningResult(**{**result.model_dump(), "started_at": _NOW.replace(hour=23)})

    def test_rejects_duplicate_candidate_ids(self) -> None:
        result = _result()
        duplicated_candidates = (result.candidates[0], result.candidates[0])
        with pytest.raises(ValidationError):
            LearningResult(**{**result.model_dump(), "candidates": duplicated_candidates})

    def test_rejects_validation_referencing_unknown_candidate(self) -> None:
        result = _result()
        bogus_validation = LearningValidation(
            validation_id=LearningValidationId.for_ordinal("lr-freeze", 1),
            candidate_id=LearningCandidateId.for_source("ghost"),
            gates_cleared=(LearningValidationGate.VALIDATED_EVIDENCE,),
            rationale="orphaned",
            validated_at=_NOW,
            confidence=LearningConfidenceLevel.LOW,
            policy_version=LearningPolicyVersion(1, 0, 0),
        )
        with pytest.raises(ValidationError):
            LearningResult(
                **{**result.model_dump(), "validations": (*result.validations, bogus_validation)}
            )

    def test_rejects_learning_referencing_unknown_candidate(self) -> None:
        result = _result()
        bogus_learning = Learning(
            learning_id=LearningId.for_ordinal("lr-freeze", 1),
            candidate_id=LearningCandidateId.for_source("ghost"),
            validation_id=result.validations[0].validation_id,
            message="orphaned",
            maturity=LearningMaturity.OBSERVED,
            confidence=LearningConfidenceLevel.LOW,
        )
        with pytest.raises(ValidationError):
            LearningResult(
                **{**result.model_dump(), "learnings": (*result.learnings, bogus_learning)}
            )

    def test_rejects_learning_referencing_unknown_validation(self) -> None:
        result = _result()
        bogus_learning = Learning(
            learning_id=LearningId.for_ordinal("lr-freeze", 1),
            candidate_id=result.candidates[0].candidate_id,
            validation_id=LearningValidationId.for_ordinal("lr-freeze", 99),
            message="orphaned",
            maturity=LearningMaturity.OBSERVED,
            confidence=LearningConfidenceLevel.LOW,
        )
        with pytest.raises(ValidationError):
            LearningResult(
                **{**result.model_dump(), "learnings": (*result.learnings, bogus_learning)}
            )

    def test_rejects_confidence_referencing_unknown_subject(self) -> None:
        result = _result()
        bogus_confidence = LearningConfidence(
            confidence_id=LearningConfidenceId.for_ordinal("lr-freeze", 1),
            subject_id="ghost-id",
            level=LearningConfidenceLevel.LOW,
            evidence_count=0,
            rationale="bogus",
            recorded_at=_NOW,
        )
        with pytest.raises(ValidationError):
            LearningResult(
                **{**result.model_dump(), "confidences": (*result.confidences, bogus_confidence)}
            )

    def test_rejects_lifecycle_referencing_unknown_subject(self) -> None:
        result = _result()
        bogus_lifecycle = LearningLifecycle(
            lifecycle_id=LearningLifecycleId.for_ordinal("lr-freeze", 1),
            subject_id="ghost-id",
            maturity=LearningMaturity.OBSERVED,
            maturity_reason="bogus",
        )
        with pytest.raises(ValidationError):
            LearningResult(
                **{**result.model_dump(), "lifecycles": (*result.lifecycles, bogus_lifecycle)}
            )

    def test_explainable_from_the_content_fields_alone(self) -> None:
        fields = set(LearningResult.model_fields)
        assert {
            "candidates",
            "learnings",
            "validations",
            "confidences",
            "lifecycles",
            "summary",
            "metrics",
            "organizational_memory_result_id",
            "policy_id",
            "policy_version",
        } <= fields

    def test_carries_no_report_renderer_or_serialization_fields(self) -> None:
        fields = set(LearningResult.model_fields)
        forbidden = {"report", "markdown", "html", "rendered_report", "json_text", "serialized"}
        assert not (forbidden & fields)

    def test_carries_no_execution_package_manifest_or_cli_fields(self) -> None:
        fields = set(LearningResult.model_fields)
        forbidden = {"manifest", "generated_artifacts", "checksums", "cli_args"}
        assert not (forbidden & fields)

    def test_never_embeds_the_full_consumed_result(self) -> None:
        """Reference, never copy — only the one id."""
        fields = set(LearningResult.model_fields)
        assert "organizational_memory_result" not in fields


@pytest.mark.unit
class TestRuntimeBoundary:
    def test_result_model_imports_no_execution_package_or_cli(self) -> None:
        source = (_LEARNING_PKG / "models" / "result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "execution_writer" not in line.lower()
                assert "manifest_builder" not in line.lower()
                assert "scripts" not in line.lower()

    def test_result_model_imports_no_service_or_platform_context(self) -> None:
        source = (_LEARNING_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = ("LearningService", "DormantLearningService", "PlatformContext")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"

    def test_result_model_imports_no_layer_1_or_peer_implementation(self) -> None:
        source = (_LEARNING_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "requirement_intelligence.enhancement",
            "requirement_intelligence.grounding",
            "requirement_intelligence.organizational_memory.organizational_memory_service",
            "requirement_intelligence.continuous_improvement",
            "requirement_intelligence.knowledge_graph",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"


@pytest.mark.unit
class TestNoRuntimeBehaviourChange:
    def test_platform_version_unchanged(self) -> None:
        from requirement_intelligence.platform import platform_metadata

        assert platform_metadata.PLATFORM_VERSION == "1.0.0"

    def test_learning_framework_version_is_the_cap_086a_foundation(self) -> None:
        from requirement_intelligence.learning.version import LEARNING_FRAMEWORK_VERSION

        assert str(LEARNING_FRAMEWORK_VERSION) == "1.0.0"

    def test_learning_result_version_is_the_cap_086a_foundation(self) -> None:
        from requirement_intelligence.learning.models.result import LEARNING_RESULT_VERSION

        assert str(LEARNING_RESULT_VERSION) == "1.0.0"
