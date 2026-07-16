"""Architecture-only tests for the Organizational Memory Framework's canonical
models (CAP-085A, ADR-0027).

Covers construction, immutability, camelCase serialization, and the
"references exist / ids resolve / lifecycle consistency" validators each
model carries. No behaviour is exercised — nothing is captured, promoted, or
retired; these models are assembly targets only (ADR-0027 Stage 2).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.organizational_memory.identity import (
    BestPracticeId,
    ExperienceId,
    KnowledgeLifecycleId,
    KnowledgePromotionId,
    LessonId,
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
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
    OrganizationalMemorySourceLayer,
    OrganizationalMemorySummary,
)

_NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _experience(**overrides: object) -> Experience:
    defaults: dict[str, object] = dict(
        experience_id=ExperienceId.for_source("knowledge_graph", "kg-finding-1"),
        source_layer=OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH,
        source_reference_id="kg-finding-1",
        description="A structural issue recurred across builds.",
        confidence=OrganizationalMemoryConfidence.LOW,
    )
    defaults.update(overrides)
    return Experience(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestExperience:
    def test_constructs_with_valid_fields(self) -> None:
        experience = _experience()
        assert experience.source_layer == OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH

    def test_is_immutable(self) -> None:
        experience = _experience()
        with pytest.raises(ValidationError):
            experience.description = "mutated"  # type: ignore[misc]

    def test_rejects_empty_source_reference_id(self) -> None:
        with pytest.raises(ValidationError):
            _experience(source_reference_id="")

    def test_rejects_empty_description(self) -> None:
        with pytest.raises(ValidationError):
            _experience(description="")

    def test_serializes_camel_case(self) -> None:
        dumped = _experience().model_dump(mode="json", by_alias=True)
        assert "sourceLayer" in dumped
        assert "sourceReferenceId" in dumped

    def test_round_trips(self) -> None:
        experience = _experience()
        dumped = experience.model_dump(mode="json", by_alias=True)
        assert Experience.model_validate(dumped) == experience


@pytest.mark.unit
class TestLesson:
    def test_constructs_with_at_least_one_source_experience(self) -> None:
        experience = _experience()
        lesson = Lesson(
            lesson_id=LessonId.for_ordinal("om-test", 0),
            source_experience_ids=(experience.experience_id,),
            message="When X recurs, Y follows.",
            confidence=OrganizationalMemoryConfidence.MEDIUM,
        )
        assert lesson.source_experience_ids == (experience.experience_id,)

    def test_rejects_zero_source_experiences(self) -> None:
        with pytest.raises(ValidationError):
            Lesson(
                lesson_id=LessonId.for_ordinal("om-test", 0),
                source_experience_ids=(),
                message="Unexplainable lesson.",
                confidence=OrganizationalMemoryConfidence.LOW,
            )

    def test_is_immutable(self) -> None:
        lesson = Lesson(
            lesson_id=LessonId.for_ordinal("om-test", 0),
            source_experience_ids=(_experience().experience_id,),
            message="msg",
            confidence=OrganizationalMemoryConfidence.LOW,
        )
        with pytest.raises(ValidationError):
            lesson.message = "mutated"  # type: ignore[misc]

    def test_rejects_empty_message(self) -> None:
        with pytest.raises(ValidationError):
            Lesson(
                lesson_id=LessonId.for_ordinal("om-test", 0),
                source_experience_ids=(_experience().experience_id,),
                message="",
                confidence=OrganizationalMemoryConfidence.LOW,
            )

    def test_round_trips(self) -> None:
        lesson = Lesson(
            lesson_id=LessonId.for_ordinal("om-test", 0),
            source_experience_ids=(_experience().experience_id,),
            message="msg",
            confidence=OrganizationalMemoryConfidence.LOW,
        )
        dumped = lesson.model_dump(mode="json", by_alias=True)
        assert Lesson.model_validate(dumped) == lesson


@pytest.mark.unit
class TestBestPractice:
    def test_constructs_with_at_least_one_source_lesson(self) -> None:
        lesson_id = LessonId.for_ordinal("om-test", 0)
        best_practice = BestPractice(
            best_practice_id=BestPracticeId.for_ordinal("om-test", 0),
            source_lesson_ids=(lesson_id,),
            title="Always check X",
            description="Generalized recommendation.",
            confidence=OrganizationalMemoryConfidence.VERIFIED,
        )
        assert best_practice.source_lesson_ids == (lesson_id,)

    def test_rejects_zero_source_lessons(self) -> None:
        with pytest.raises(ValidationError):
            BestPractice(
                best_practice_id=BestPracticeId.for_ordinal("om-test", 0),
                source_lesson_ids=(),
                title="Unexplainable practice",
                description="desc",
                confidence=OrganizationalMemoryConfidence.LOW,
            )

    def test_is_immutable(self) -> None:
        best_practice = BestPractice(
            best_practice_id=BestPracticeId.for_ordinal("om-test", 0),
            source_lesson_ids=(LessonId.for_ordinal("om-test", 0),),
            title="title",
            description="desc",
            confidence=OrganizationalMemoryConfidence.HIGH,
        )
        with pytest.raises(ValidationError):
            best_practice.title = "mutated"  # type: ignore[misc]

    def test_rejects_empty_title(self) -> None:
        with pytest.raises(ValidationError):
            BestPractice(
                best_practice_id=BestPracticeId.for_ordinal("om-test", 0),
                source_lesson_ids=(LessonId.for_ordinal("om-test", 0),),
                title="",
                description="desc",
                confidence=OrganizationalMemoryConfidence.HIGH,
            )

    def test_round_trips(self) -> None:
        best_practice = BestPractice(
            best_practice_id=BestPracticeId.for_ordinal("om-test", 0),
            source_lesson_ids=(LessonId.for_ordinal("om-test", 0),),
            title="title",
            description="desc",
            confidence=OrganizationalMemoryConfidence.HIGH,
        )
        dumped = best_practice.model_dump(mode="json", by_alias=True)
        assert BestPractice.model_validate(dumped) == best_practice


@pytest.mark.unit
class TestKnowledgePromotion:
    def _promotion(self, **overrides: object) -> KnowledgePromotion:
        defaults: dict[str, object] = dict(
            promotion_id=KnowledgePromotionId.for_ordinal("om-test", 0),
            source_ids=("ex-1",),
            target_ids=("ls-1",),
            rationale="Promoted after threshold met.",
            promoted_at=_NOW,
            confidence=OrganizationalMemoryConfidence.MEDIUM,
            policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
        )
        defaults.update(overrides)
        return KnowledgePromotion(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_fields(self) -> None:
        promotion = self._promotion()
        assert promotion.source_ids == ("ex-1",)
        assert promotion.target_ids == ("ls-1",)

    def test_rejects_zero_source_ids(self) -> None:
        with pytest.raises(ValidationError):
            self._promotion(source_ids=())

    def test_rejects_zero_target_ids(self) -> None:
        with pytest.raises(ValidationError):
            self._promotion(target_ids=())

    def test_is_immutable(self) -> None:
        promotion = self._promotion()
        with pytest.raises(ValidationError):
            promotion.rationale = "mutated"  # type: ignore[misc]

    def test_rejects_empty_rationale(self) -> None:
        with pytest.raises(ValidationError):
            self._promotion(rationale="")

    def test_round_trips(self) -> None:
        promotion = self._promotion()
        dumped = promotion.model_dump(mode="json", by_alias=True)
        assert KnowledgePromotion.model_validate(dumped) == promotion

    def test_serializes_camel_case(self) -> None:
        dumped = self._promotion().model_dump(mode="json", by_alias=True)
        assert "sourceIds" in dumped
        assert "targetIds" in dumped
        assert "promotedAt" in dumped
        assert "policyVersion" in dumped


@pytest.mark.unit
class TestKnowledgeLifecycle:
    def _lifecycle(self, **overrides: object) -> KnowledgeLifecycle:
        defaults: dict[str, object] = dict(
            lifecycle_id=KnowledgeLifecycleId.for_ordinal("om-test", 0),
            subject_id="bp-1",
            state=KnowledgeLifecycleState.ACTIVE,
            state_reason="newly institutionalized",
        )
        defaults.update(overrides)
        return KnowledgeLifecycle(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_fields(self) -> None:
        lifecycle = self._lifecycle()
        assert lifecycle.state == KnowledgeLifecycleState.ACTIVE

    def test_rejects_empty_subject_id(self) -> None:
        with pytest.raises(ValidationError):
            self._lifecycle(subject_id="")

    def test_rejects_empty_state_reason(self) -> None:
        with pytest.raises(ValidationError):
            self._lifecycle(state_reason="")

    def test_is_immutable(self) -> None:
        lifecycle = self._lifecycle()
        with pytest.raises(ValidationError):
            lifecycle.state = KnowledgeLifecycleState.ARCHIVED  # type: ignore[misc]

    @pytest.mark.parametrize(
        "state",
        [
            KnowledgeLifecycleState.ACTIVE,
            KnowledgeLifecycleState.DEPRECATED,
            KnowledgeLifecycleState.HISTORICAL,
            KnowledgeLifecycleState.ARCHIVED,
        ],
    )
    def test_accepts_every_governed_state(self, state: KnowledgeLifecycleState) -> None:
        lifecycle = self._lifecycle(state=state)
        assert lifecycle.state == state

    def test_round_trips(self) -> None:
        lifecycle = self._lifecycle()
        dumped = lifecycle.model_dump(mode="json", by_alias=True)
        assert KnowledgeLifecycle.model_validate(dumped) == lifecycle


@pytest.mark.unit
class TestOrganizationalMemorySummary:
    def _summary(self, **overrides: object) -> OrganizationalMemorySummary:
        defaults: dict[str, object] = dict(
            policy_id=OrganizationalMemoryPolicyId("default-organizational-memory-policy"),
            policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
            total_experiences=0,
            total_lessons=0,
            total_best_practices=0,
            total_promotions=0,
            headline="0 experiences, 0 lessons, 0 best practices.",
        )
        defaults.update(overrides)
        return OrganizationalMemorySummary(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_fields(self) -> None:
        summary = self._summary()
        assert summary.total_experiences == 0

    def test_rejects_negative_counts(self) -> None:
        with pytest.raises(ValidationError):
            self._summary(total_experiences=-1)

    def test_rejects_empty_headline(self) -> None:
        with pytest.raises(ValidationError):
            self._summary(headline="")

    def test_is_immutable(self) -> None:
        summary = self._summary()
        with pytest.raises(ValidationError):
            summary.total_lessons = 5  # type: ignore[misc]

    def test_only_version_field_is_policy_version(self) -> None:
        version_fields = {
            name for name in OrganizationalMemorySummary.model_fields if "version" in name.lower()
        }
        assert version_fields == {"policy_version"}


@pytest.mark.unit
class TestOrganizationalMemoryMetrics:
    def _metrics(self, **overrides: object) -> OrganizationalMemoryMetrics:
        defaults: dict[str, object] = dict(
            experience_count=0,
            lesson_count=0,
            best_practice_count=0,
            promotion_count=0,
            active_count=0,
            deprecated_count=0,
            historical_count=0,
            archived_count=0,
        )
        defaults.update(overrides)
        return OrganizationalMemoryMetrics(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_fields(self) -> None:
        metrics = self._metrics(experience_count=3)
        assert metrics.experience_count == 3

    def test_rejects_negative_counts(self) -> None:
        with pytest.raises(ValidationError):
            self._metrics(lesson_count=-1)

    def test_is_immutable(self) -> None:
        metrics = self._metrics()
        with pytest.raises(ValidationError):
            metrics.promotion_count = 5  # type: ignore[misc]

    def test_has_no_dedicated_version_field(self) -> None:
        version_fields = {
            name for name in OrganizationalMemoryMetrics.model_fields if "version" in name.lower()
        }
        assert version_fields == set()

    def test_round_trips(self) -> None:
        metrics = self._metrics()
        dumped = metrics.model_dump(mode="json", by_alias=True)
        assert OrganizationalMemoryMetrics.model_validate(dumped) == metrics


@pytest.mark.unit
class TestGovernedVocabularies:
    def test_source_layer_has_exactly_two_members(self) -> None:
        assert {member.value for member in OrganizationalMemorySourceLayer} == {
            "continuous_improvement",
            "knowledge_graph",
        }

    def test_confidence_has_exactly_four_members(self) -> None:
        assert {member.value for member in OrganizationalMemoryConfidence} == {
            "low",
            "medium",
            "high",
            "verified",
        }

    def test_lifecycle_state_has_exactly_four_members(self) -> None:
        assert {member.value for member in KnowledgeLifecycleState} == {
            "active",
            "deprecated",
            "historical",
            "archived",
        }
