"""Architecture-only tests for the CAP-085A OrganizationalMemoryResult freeze.

These assert the *runtime contract* invariants — not behaviour (no engine
exists yet, so there is no behaviour to test). They cover cross-referential
integrity (lessons/best-practices/promotions/lifecycles must resolve among the
result's own experiences/lessons/best-practices), immutability, serialization
round-trip, the explainability invariant, and the frozen runtime boundary
(ADR-0027 §D3/§D4/§D9), mirroring ``test_knowledge_graph_result_freeze.py``
(ADR-0023 §D3/§D4) as it stood before CAP-084B introduced an engine, and
``test_continuous_improvement_result_freeze.py`` (ADR-0022 §D3/§D4) at the
same pre-engine stage.

Because no engine exists yet, every ``OrganizationalMemoryResult`` in these
tests is hand-built directly — the same discipline every sibling subsystem's
own CAP-0XXA freeze test used before its own engine existed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.organizational_memory.identity import (
    BestPracticeId,
    BestPracticeVersion,
    ExperienceId,
    KnowledgeLifecycleId,
    KnowledgeLifecycleVersion,
    KnowledgePromotionId,
    LessonId,
    LessonVersion,
    OrganizationalMemoryFrameworkVersion,
    OrganizationalMemoryId,
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
    OrganizationalMemoryResultId,
    OrganizationalMemoryResultVersion,
)
from requirement_intelligence.organizational_memory.models import (
    BestPractice,
    Experience,
    KnowledgeLifecycle,
    KnowledgeLifecycleState,
    KnowledgePromotion,
    Lesson,
    OrganizationalMemoryConfidence,
    OrganizationalMemoryMetrics,
    OrganizationalMemoryResult,
    OrganizationalMemorySourceLayer,
    OrganizationalMemorySummary,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ORGANIZATIONAL_MEMORY_PKG = _REPO_ROOT / "requirement_intelligence" / "organizational_memory"
_NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _version_field_names(model: type) -> set[str]:
    return {name for name in model.model_fields if "version" in name.lower()}


def _result() -> OrganizationalMemoryResult:
    experience = Experience(
        experience_id=ExperienceId.for_source("knowledge_graph", "kg-finding-1"),
        source_layer=OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH,
        source_reference_id="kg-finding-1",
        description="A structural issue recurred.",
        confidence=OrganizationalMemoryConfidence.LOW,
    )
    lesson = Lesson(
        lesson_id=LessonId.for_ordinal("om-freeze", 0),
        source_experience_ids=(experience.experience_id,),
        message="When X recurs, Y follows.",
        confidence=OrganizationalMemoryConfidence.MEDIUM,
    )
    best_practice = BestPractice(
        best_practice_id=BestPracticeId.for_ordinal("om-freeze", 0),
        source_lesson_ids=(lesson.lesson_id,),
        title="Always check X",
        description="Generalized recommendation.",
        confidence=OrganizationalMemoryConfidence.VERIFIED,
    )
    promotion = KnowledgePromotion(
        promotion_id=KnowledgePromotionId.for_ordinal("om-freeze", 0),
        source_ids=(str(experience.experience_id),),
        target_ids=(str(lesson.lesson_id),),
        rationale="Promoted after threshold met.",
        promoted_at=_NOW,
        confidence=OrganizationalMemoryConfidence.MEDIUM,
        policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
    )
    lifecycle = KnowledgeLifecycle(
        lifecycle_id=KnowledgeLifecycleId.for_ordinal("om-freeze", 0),
        subject_id=str(best_practice.best_practice_id),
        state=KnowledgeLifecycleState.ACTIVE,
        state_reason="newly institutionalized",
    )
    return OrganizationalMemoryResult(
        result_id=OrganizationalMemoryResultId.for_memory("om-freeze"),
        memory_id=OrganizationalMemoryId.for_inputs("ci-result-1", "kg-result-1"),
        continuous_improvement_result_id="ci-result-1",
        knowledge_graph_result_id="kg-result-1",
        experiences=(experience,),
        lessons=(lesson,),
        best_practices=(best_practice,),
        promotions=(promotion,),
        lifecycles=(lifecycle,),
        summary=OrganizationalMemorySummary(
            policy_id=OrganizationalMemoryPolicyId("default-organizational-memory-policy"),
            policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
            total_experiences=1,
            total_lessons=1,
            total_best_practices=1,
            total_promotions=1,
            headline="1 experience, 1 lesson, 1 best practice.",
        ),
        metrics=OrganizationalMemoryMetrics(
            experience_count=1,
            lesson_count=1,
            best_practice_count=1,
            promotion_count=1,
            active_count=1,
            deprecated_count=0,
            historical_count=0,
            archived_count=0,
        ),
        policy_id=OrganizationalMemoryPolicyId("default-organizational-memory-policy"),
        policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
        framework_version=OrganizationalMemoryFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


@pytest.mark.unit
class TestRuntimeContractVersion:
    def test_result_version_is_its_own_type(self) -> None:
        assert isinstance(_result().result_version, OrganizationalMemoryResultVersion)

    def test_runtime_version_is_independent_of_every_other_axis(self) -> None:
        other_axes = (
            OrganizationalMemoryFrameworkVersion,
            OrganizationalMemoryPolicyVersion,
            LessonVersion,
            BestPracticeVersion,
            KnowledgeLifecycleVersion,
        )
        for axis in other_axes:
            assert not issubclass(OrganizationalMemoryResultVersion, axis)
            assert not issubclass(axis, OrganizationalMemoryResultVersion)
        assert len({OrganizationalMemoryResultVersion, *other_axes}) == 6

    def test_experience_has_no_dedicated_version_field(self) -> None:
        assert _version_field_names(Experience) == set()

    def test_promotion_has_no_dedicated_schema_version_field(self) -> None:
        """KnowledgePromotion carries only the governing policy_version (a policy
        reference, not a schema-version axis of its own)."""
        assert _version_field_names(KnowledgePromotion) == {"policy_version"}


@pytest.mark.unit
class TestSelfContainedContract:
    def test_round_trips_from_serialization_alone(self) -> None:
        result = _result()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert OrganizationalMemoryResult.model_validate(dumped) == result

    def test_deterministic_equality(self) -> None:
        assert _result() == _result()

    def test_is_immutable(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.result_id = "other"  # type: ignore[misc]

    def test_rejects_completed_before_started(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{**result.model_dump(), "started_at": _NOW.replace(hour=23)}
            )

    def test_rejects_duplicate_experience_ids(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{
                    **result.model_dump(),
                    "experiences": (result.experiences[0], result.experiences[0]),
                }
            )

    def test_rejects_lesson_referencing_unknown_experience(self) -> None:
        result = _result()
        bogus_lesson = Lesson(
            lesson_id=LessonId.for_ordinal("om-freeze", 1),
            source_experience_ids=(ExperienceId.for_source("continuous_improvement", "ghost"),),
            message="orphaned",
            confidence=OrganizationalMemoryConfidence.LOW,
        )
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{**result.model_dump(), "lessons": (*result.lessons, bogus_lesson)}
            )

    def test_rejects_best_practice_referencing_unknown_lesson(self) -> None:
        result = _result()
        bogus_bp = BestPractice(
            best_practice_id=BestPracticeId.for_ordinal("om-freeze", 1),
            source_lesson_ids=(LessonId.for_ordinal("om-freeze", 99),),
            title="orphaned",
            description="orphaned",
            confidence=OrganizationalMemoryConfidence.LOW,
        )
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{**result.model_dump(), "best_practices": (*result.best_practices, bogus_bp)}
            )

    def test_rejects_promotion_referencing_unknown_source(self) -> None:
        result = _result()
        bogus_promotion = KnowledgePromotion(
            promotion_id=KnowledgePromotionId.for_ordinal("om-freeze", 1),
            source_ids=("ghost-id",),
            target_ids=(str(result.lessons[0].lesson_id),),
            rationale="bogus",
            promoted_at=_NOW,
            confidence=OrganizationalMemoryConfidence.LOW,
            policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
        )
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{**result.model_dump(), "promotions": (*result.promotions, bogus_promotion)}
            )

    def test_rejects_lifecycle_referencing_unknown_subject(self) -> None:
        result = _result()
        bogus_lifecycle = KnowledgeLifecycle(
            lifecycle_id=KnowledgeLifecycleId.for_ordinal("om-freeze", 1),
            subject_id="ghost-id",
            state=KnowledgeLifecycleState.ACTIVE,
            state_reason="bogus",
        )
        with pytest.raises(ValidationError):
            OrganizationalMemoryResult(
                **{**result.model_dump(), "lifecycles": (*result.lifecycles, bogus_lifecycle)}
            )

    def test_explainable_from_the_content_fields_alone(self) -> None:
        fields = set(OrganizationalMemoryResult.model_fields)
        assert {
            "experiences",
            "lessons",
            "best_practices",
            "promotions",
            "lifecycles",
            "summary",
            "metrics",
            "continuous_improvement_result_id",
            "knowledge_graph_result_id",
            "policy_id",
            "policy_version",
        } <= fields

    def test_carries_no_report_renderer_or_serialization_fields(self) -> None:
        fields = set(OrganizationalMemoryResult.model_fields)
        forbidden = {"report", "markdown", "html", "rendered_report", "json_text", "serialized"}
        assert not (forbidden & fields)

    def test_carries_no_execution_package_manifest_or_cli_fields(self) -> None:
        fields = set(OrganizationalMemoryResult.model_fields)
        forbidden = {"manifest", "generated_artifacts", "checksums", "cli_args"}
        assert not (forbidden & fields)

    def test_never_embeds_the_full_consumed_peer_results(self) -> None:
        """Reference, never copy (Recommendation 2 of ADR-0027) — only the two ids."""
        fields = set(OrganizationalMemoryResult.model_fields)
        forbidden = {"continuous_improvement_result", "knowledge_graph_result"}
        assert not (forbidden & fields)


@pytest.mark.unit
class TestRuntimeBoundary:
    def test_result_model_imports_no_execution_package_or_cli(self) -> None:
        source = (_ORGANIZATIONAL_MEMORY_PKG / "models" / "result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "execution_writer" not in line.lower()
                assert "manifest_builder" not in line.lower()
                assert "scripts" not in line.lower()

    def test_result_model_imports_no_service_or_platform_context(self) -> None:
        source = (_ORGANIZATIONAL_MEMORY_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "OrganizationalMemoryService",
            "DeterministicOrganizationalMemoryService",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"

    def test_result_model_imports_no_layer_1_or_peer_implementation(self) -> None:
        source = (_ORGANIZATIONAL_MEMORY_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "requirement_intelligence.enhancement",
            "requirement_intelligence.grounding",
            "requirement_intelligence.continuous_improvement.continuous_improvement_service",
            "requirement_intelligence.knowledge_graph.knowledge_graph_service",
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

    def test_organizational_memory_framework_version_is_the_cap_085a_foundation(self) -> None:
        from requirement_intelligence.organizational_memory.version import (
            ORGANIZATIONAL_MEMORY_FRAMEWORK_VERSION,
        )

        assert str(ORGANIZATIONAL_MEMORY_FRAMEWORK_VERSION) == "1.0.0"

    def test_organizational_memory_result_version_is_the_cap_085a_foundation(self) -> None:
        from requirement_intelligence.organizational_memory.models.result import (
            ORGANIZATIONAL_MEMORY_RESULT_VERSION,
        )

        assert str(ORGANIZATIONAL_MEMORY_RESULT_VERSION) == "1.0.0"
