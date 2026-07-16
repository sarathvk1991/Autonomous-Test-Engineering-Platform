"""Behavioural tests for the deterministic Learning engine and its twelve
collaborators (CAP-086B, ADR-0029 D9-D26).

Exercises real collection, clustering, validation, generation,
institutionalization, stability, confidence, promotion, lifecycle, summary,
metrics, and result-assembly logic — determinism, explainability, and
policy-gating throughout. No ML, no LLM, no randomness anywhere (ADR-0029
D18, Stage 4 of the CAP-086B brief).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from requirement_intelligence.learning.engine import (
    ConfidenceRecorder,
    DeterministicLearningEngine,
    InstitutionalizationEvaluator,
    LearningCandidateClusterer,
    LearningCandidateCollector,
    LearningGenerator,
    LearningValidator,
    LifecycleRecorder,
    MetricsBuilder,
    PromotionRecorder,
    ResultBuilder,
    StabilityEvaluator,
    SummaryBuilder,
)
from requirement_intelligence.learning.engine._confidence import confidence_for_evidence
from requirement_intelligence.learning.identity import LearningPolicyId
from requirement_intelligence.learning.models.enums import (
    LearningConfidenceLevel,
    LearningMaturity,
    LearningValidationGate,
)
from requirement_intelligence.learning.policy import (
    LearningCapabilitySwitches,
    LearningPolicy,
    LearningPolicyBuilder,
    LearningThresholds,
    default_learning_policy,
)
from requirement_intelligence.learning.version import LEARNING_POLICY_VERSION
from requirement_intelligence.organizational_memory.identity import (
    BestPracticeId,
    ExperienceId,
    LessonId,
    OrganizationalMemoryFrameworkVersion,
    OrganizationalMemoryId,
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
    OrganizationalMemoryResultId,
)
from requirement_intelligence.organizational_memory.models import (
    BestPractice,
    Experience,
    OrganizationalMemoryConfidence,
    OrganizationalMemoryMetrics,
    OrganizationalMemoryResult,
    OrganizationalMemorySourceLayer,
    OrganizationalMemorySummary,
)
from requirement_intelligence.organizational_memory.models.lesson import Lesson

_NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _best_practice_bundle(
    seed: str, ordinal: int, description: str
) -> tuple[Experience, Lesson, BestPractice]:
    experience = Experience(
        experience_id=ExperienceId.for_source("knowledge_graph", f"{seed}-kg-{ordinal}"),
        source_layer=OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH,
        source_reference_id=f"{seed}-kg-{ordinal}",
        description=description,
        confidence=OrganizationalMemoryConfidence.LOW,
    )
    lesson = Lesson(
        lesson_id=LessonId.for_ordinal(seed, ordinal),
        source_experience_ids=(experience.experience_id,),
        message=description,
        confidence=OrganizationalMemoryConfidence.MEDIUM,
    )
    best_practice = BestPractice(
        best_practice_id=BestPracticeId.for_ordinal(seed, ordinal),
        source_lesson_ids=(lesson.lesson_id,),
        title=f"practice {ordinal}",
        description=description,
        confidence=OrganizationalMemoryConfidence.VERIFIED,
    )
    return experience, lesson, best_practice


def _organizational_memory_result(
    descriptions: list[str], *, seed: str = "om-engine-test"
) -> OrganizationalMemoryResult:
    """Build a hand-constructed, fully self-consistent OrganizationalMemoryResult
    with one Experience/Lesson/BestPractice bundle per entry in *descriptions*.
    Only the BestPractice objects matter to the Learning engine itself; the
    Experience/Lesson tuples exist solely to satisfy OrganizationalMemoryResult's
    own cross-referential validator."""
    bundles = [
        _best_practice_bundle(seed, i, description) for i, description in enumerate(descriptions)
    ]
    experiences = tuple(bundle[0] for bundle in bundles)
    lessons = tuple(bundle[1] for bundle in bundles)
    best_practices = tuple(bundle[2] for bundle in bundles)
    return OrganizationalMemoryResult(
        result_id=OrganizationalMemoryResultId.for_memory(seed),
        memory_id=OrganizationalMemoryId.for_inputs("ci-1", "kg-1"),
        continuous_improvement_result_id="ci-1",
        knowledge_graph_result_id="kg-1",
        experiences=experiences,
        lessons=lessons,
        best_practices=best_practices,
        promotions=(),
        lifecycles=(),
        summary=OrganizationalMemorySummary(
            policy_id=OrganizationalMemoryPolicyId("default-organizational-memory-policy"),
            policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
            total_experiences=len(experiences),
            total_lessons=len(lessons),
            total_best_practices=len(best_practices),
            total_promotions=0,
            headline="test fixture",
        ),
        metrics=OrganizationalMemoryMetrics(
            experience_count=len(experiences),
            lesson_count=len(lessons),
            best_practice_count=len(best_practices),
            promotion_count=0,
            active_count=0,
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


def _policy(**threshold_overrides: object) -> LearningPolicy:
    defaults: dict[str, object] = dict(
        minimum_best_practices_for_candidate=2,
        minimum_validation_gates_for_learning=6,
        minimum_confidence_for_learning=3,
    )
    defaults.update(threshold_overrides)
    return LearningPolicy(
        policy_id=LearningPolicyId("default-learning-policy"),
        policy_version=LEARNING_POLICY_VERSION,
        description="test policy",
        capability_switches=LearningCapabilitySwitches(),
        thresholds=LearningThresholds(**defaults),  # type: ignore[arg-type]
    )


@pytest.mark.unit
class TestConfidenceHelper:
    def test_below_threshold_is_low(self) -> None:
        assert confidence_for_evidence(1, 2) == LearningConfidenceLevel.LOW

    def test_exactly_one_multiple_is_medium(self) -> None:
        assert confidence_for_evidence(2, 2) == LearningConfidenceLevel.MEDIUM

    def test_exactly_two_multiples_is_high(self) -> None:
        assert confidence_for_evidence(4, 2) == LearningConfidenceLevel.HIGH

    def test_three_or_more_multiples_is_verified(self) -> None:
        assert confidence_for_evidence(6, 2) == LearningConfidenceLevel.VERIFIED
        assert confidence_for_evidence(60, 2) == LearningConfidenceLevel.VERIFIED

    def test_non_positive_threshold_falls_back_to_low(self) -> None:
        assert confidence_for_evidence(10, 0) == LearningConfidenceLevel.LOW
        assert confidence_for_evidence(10, -1) == LearningConfidenceLevel.LOW


@pytest.mark.unit
class TestLearningCandidateCollector:
    def test_collects_one_candidate_per_best_practice(self) -> None:
        result = _organizational_memory_result(["a", "b", "c"])
        candidates = LearningCandidateCollector(_policy()).collect(result)
        assert len(candidates) == 3

    def test_below_corpus_floor_collects_nothing(self) -> None:
        result = _organizational_memory_result(["only one"])
        candidates = LearningCandidateCollector(_policy()).collect(result)
        assert candidates == ()

    def test_at_corpus_floor_collects(self) -> None:
        result = _organizational_memory_result(["a", "b"])
        candidates = LearningCandidateCollector(_policy()).collect(result)
        assert len(candidates) == 2

    def test_disabled_switch_collects_nothing(self) -> None:
        policy = _policy()
        disabled = policy.model_copy(
            update={
                "capability_switches": policy.capability_switches.model_copy(
                    update={"enable_candidate_proposal": False}
                )
            }
        )
        result = _organizational_memory_result(["a", "b", "c"])
        assert LearningCandidateCollector(disabled).collect(result) == ()

    def test_candidate_references_its_source_best_practice_verbatim(self) -> None:
        result = _organizational_memory_result(["a", "b"])
        candidates = LearningCandidateCollector(_policy()).collect(result)
        source_ids = {c.source_best_practice_ids[0] for c in candidates}
        assert source_ids == {str(bp.best_practice_id) for bp in result.best_practices}

    def test_starts_at_low_confidence(self) -> None:
        result = _organizational_memory_result(["a", "b"])
        candidates = LearningCandidateCollector(_policy()).collect(result)
        assert all(c.confidence == LearningConfidenceLevel.LOW for c in candidates)

    def test_is_deterministic(self) -> None:
        result = _organizational_memory_result(["a", "b", "c"])
        collector = LearningCandidateCollector(_policy())
        assert collector.collect(result) == collector.collect(result)


@pytest.mark.unit
class TestLearningCandidateClusterer:
    def test_distinct_descriptions_remain_separate(self) -> None:
        result = _organizational_memory_result(["a", "b"])
        candidates = LearningCandidateCollector(_policy()).collect(result)
        clustered = LearningCandidateClusterer().cluster(candidates)
        assert len(clustered) == 2

    def test_identical_descriptions_are_merged(self) -> None:
        result = _organizational_memory_result(["same", "same", "same"])
        candidates = LearningCandidateCollector(_policy()).collect(result)
        clustered = LearningCandidateClusterer().cluster(candidates)
        assert len(clustered) == 1
        assert len(clustered[0].source_best_practice_ids) == 3

    def test_merge_unions_source_best_practice_ids_without_duplication(self) -> None:
        result = _organizational_memory_result(["same", "same"])
        candidates = LearningCandidateCollector(_policy()).collect(result)
        clustered = LearningCandidateClusterer().cluster(candidates)
        assert len(set(clustered[0].source_best_practice_ids)) == 2

    def test_survivor_keeps_the_lowest_candidate_id(self) -> None:
        result = _organizational_memory_result(["same", "same"])
        candidates = LearningCandidateCollector(_policy()).collect(result)
        expected_survivor_id = min(str(c.candidate_id) for c in candidates)
        clustered = LearningCandidateClusterer().cluster(candidates)
        assert str(clustered[0].candidate_id) == expected_survivor_id

    def test_output_is_deterministically_ordered(self) -> None:
        result = _organizational_memory_result(["z", "a", "m"])
        candidates = LearningCandidateCollector(_policy()).collect(result)
        clustered_once = LearningCandidateClusterer().cluster(candidates)
        clustered_again = LearningCandidateClusterer().cluster(tuple(reversed(candidates)))
        assert clustered_once == clustered_again

    def test_empty_input_yields_empty_output(self) -> None:
        assert LearningCandidateClusterer().cluster(()) == ()


@pytest.mark.unit
class TestLearningValidator:
    def test_validates_candidate_clearing_confidence_floor(self) -> None:
        # 6 identical descriptions -> one merged candidate with 6 references,
        # 6 // 2 == 3 == VERIFIED ordinal, clears the default floor of 3.
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        assert len(validations) == 1
        assert validations[0].confidence == LearningConfidenceLevel.VERIFIED

    def test_skips_candidate_below_confidence_floor(self) -> None:
        result = _organizational_memory_result(["a", "b"])
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        assert validations == ()

    def test_all_six_gates_cleared_by_default_policy(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        assert validations[0].gates_cleared == tuple(LearningValidationGate)

    def test_partial_gate_count_is_respected(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy(minimum_validation_gates_for_learning=2)
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        assert len(validations[0].gates_cleared) == 2

    def test_disabled_switch_validates_nothing(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        disabled = policy.model_copy(
            update={
                "capability_switches": policy.capability_switches.model_copy(
                    update={"enable_validation": False}
                )
            }
        )
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        assert LearningValidator(disabled).validate(candidates, "seed", _NOW) == ()

    def test_validation_references_the_candidate_it_concerns(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        assert validations[0].candidate_id == candidates[0].candidate_id


@pytest.mark.unit
class TestLearningGenerator:
    def test_generates_only_for_validated_candidates(self) -> None:
        result = _organizational_memory_result(["same"] * 6 + ["lonely"])
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        assert len(learnings) == 1

    def test_no_validations_generates_nothing(self) -> None:
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(
                _organizational_memory_result(["a", "b"])
            )
        )
        assert LearningGenerator(policy).generate(candidates, (), "seed") == ()

    def test_generated_learning_starts_at_validated_maturity(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        assert learnings[0].maturity == LearningMaturity.VALIDATED

    def test_generated_learning_references_its_candidate_and_validation(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        assert learnings[0].candidate_id == candidates[0].candidate_id
        assert learnings[0].validation_id == validations[0].validation_id

    def test_message_is_copied_from_the_candidate_verbatim(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        assert learnings[0].message == candidates[0].proposed_change


@pytest.mark.unit
class TestInstitutionalizationEvaluator:
    def test_verified_confidence_is_institutionally_ready(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        ready = InstitutionalizationEvaluator().evaluate(learnings)
        assert ready == {learnings[0].learning_id}

    def test_empty_input_yields_empty_set(self) -> None:
        assert InstitutionalizationEvaluator().evaluate(()) == frozenset()


@pytest.mark.unit
class TestStabilityEvaluator:
    def test_stable_iff_institutionalized(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        ready = InstitutionalizationEvaluator().evaluate(learnings)
        stable = StabilityEvaluator().evaluate(learnings, ready)
        assert stable == ready

    def test_no_institutionalization_yields_no_stability(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        assert StabilityEvaluator().evaluate(learnings, frozenset()) == frozenset()


@pytest.mark.unit
class TestConfidenceRecorder:
    def test_records_one_entry_per_learning(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        candidates_by_id = {str(c.candidate_id): c for c in candidates}
        confidences = ConfidenceRecorder(policy).record(learnings, candidates_by_id, "seed", _NOW)
        assert len(confidences) == 1

    def test_agrees_with_the_generators_own_confidence(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        candidates_by_id = {str(c.candidate_id): c for c in candidates}
        confidences = ConfidenceRecorder(policy).record(learnings, candidates_by_id, "seed", _NOW)
        assert confidences[0].level == learnings[0].confidence

    def test_disabled_switch_records_nothing(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        disabled = policy.model_copy(
            update={
                "capability_switches": policy.capability_switches.model_copy(
                    update={"enable_confidence_recording": False}
                )
            }
        )
        candidates_by_id = {str(c.candidate_id): c for c in candidates}
        assert ConfidenceRecorder(disabled).record(learnings, candidates_by_id, "seed", _NOW) == ()

    def test_subject_id_references_the_learning(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        candidates_by_id = {str(c.candidate_id): c for c in candidates}
        confidences = ConfidenceRecorder(policy).record(learnings, candidates_by_id, "seed", _NOW)
        assert confidences[0].subject_id == str(learnings[0].learning_id)


@pytest.mark.unit
class TestPromotionRecorder:
    def test_records_one_event_per_learning(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        events = PromotionRecorder().record(learnings, _NOW)
        assert len(events) == 1
        assert events[0].learning_id == learnings[0].learning_id
        assert events[0].candidate_id == learnings[0].candidate_id

    def test_empty_input_yields_no_events(self) -> None:
        assert PromotionRecorder().record((), _NOW) == ()


@pytest.mark.unit
class TestLifecycleRecorder:
    def test_records_candidate_entry_for_every_candidate(self) -> None:
        result = _organizational_memory_result(["a", "b"])
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        lifecycles = LifecycleRecorder(policy).record(candidates, (), frozenset(), "seed")
        assert len(lifecycles) == 2
        assert all(entry.maturity == LearningMaturity.CANDIDATE for entry in lifecycles)

    def test_validated_learning_gets_validated_and_institutional_entries(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        ready = InstitutionalizationEvaluator().evaluate(learnings)
        lifecycles = LifecycleRecorder(policy).record(candidates, learnings, ready, "seed")
        learning_subject_id = str(learnings[0].learning_id)
        subject_maturities = [
            entry.maturity for entry in lifecycles if entry.subject_id == learning_subject_id
        ]
        assert LearningMaturity.VALIDATED in subject_maturities
        assert LearningMaturity.INSTITUTIONAL in subject_maturities

    def test_disabled_switch_records_nothing(self) -> None:
        result = _organizational_memory_result(["a", "b"])
        policy = _policy()
        disabled = policy.model_copy(
            update={
                "capability_switches": policy.capability_switches.model_copy(
                    update={"enable_lifecycle_recording": False}
                )
            }
        )
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        assert LifecycleRecorder(disabled).record(candidates, (), frozenset(), "seed") == ()

    def test_lifecycle_entries_are_never_deleted_only_appended(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        ready = InstitutionalizationEvaluator().evaluate(learnings)
        lifecycles = LifecycleRecorder(policy).record(candidates, learnings, ready, "seed")
        # one CANDIDATE + one VALIDATED + one INSTITUTIONAL = 3 total for one candidate/learning
        assert len(lifecycles) == 3
        assert len({entry.lifecycle_id for entry in lifecycles}) == 3


@pytest.mark.unit
class TestSummaryAndMetricsBuilders:
    def test_summary_tallies_counts(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        summary = SummaryBuilder().build(
            policy.policy_id, policy.policy_version, candidates, learnings, validations
        )
        assert summary.total_candidates == 1
        assert summary.total_learnings == 1
        assert summary.total_validations == 1

    def test_metrics_tally_maturity_distribution(self) -> None:
        result = _organizational_memory_result(["same"] * 6)
        policy = _policy()
        candidates = LearningCandidateClusterer().cluster(
            LearningCandidateCollector(policy).collect(result)
        )
        validations = LearningValidator(policy).validate(candidates, "seed", _NOW)
        learnings = LearningGenerator(policy).generate(candidates, validations, "seed")
        ready = InstitutionalizationEvaluator().evaluate(learnings)
        lifecycles = LifecycleRecorder(policy).record(candidates, learnings, ready, "seed")
        metrics = MetricsBuilder().build(candidates, learnings, validations, lifecycles)
        assert metrics.candidate_count == 1
        assert metrics.learning_count == 1
        assert metrics.validated_count == 1
        assert metrics.institutional_count == 1
        assert metrics.observed_count == 0
        assert metrics.trusted_count == 0
        assert metrics.standard_count == 0
        assert metrics.retired_count == 0


@pytest.mark.unit
class TestResultBuilder:
    def _build(self, source_id: str = "omr-fixed"):
        from requirement_intelligence.learning.identity import LearningFrameworkVersion

        policy = _policy()
        summary = SummaryBuilder().build(policy.policy_id, policy.policy_version, (), (), ())
        metrics = MetricsBuilder().build((), (), (), ())
        return ResultBuilder().build(
            organizational_memory_result_id=source_id,
            candidates=(),
            learnings=(),
            validations=(),
            confidences=(),
            lifecycles=(),
            summary=summary,
            metrics=metrics,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            framework_version=LearningFrameworkVersion(1, 0, 0),
            started_at=_NOW,
            completed_at=_NOW,
        )

    def test_mints_a_deterministic_result_id_from_the_source(self) -> None:
        result = self._build("omr-fixed")
        assert result.organizational_memory_result_id == "omr-fixed"

    def test_same_source_id_mints_the_same_result_id(self) -> None:
        assert self._build("omr-fixed").result_id == self._build("omr-fixed").result_id

    def test_different_source_ids_mint_different_result_ids(self) -> None:
        assert self._build("omr-a").result_id != self._build("omr-b").result_id


@pytest.mark.unit
class TestDeterministicEngineEndToEnd:
    def test_below_corpus_floor_produces_an_empty_but_valid_result(self) -> None:
        engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
        result = engine.build(_organizational_memory_result(["only one"], seed="om-e2e-1"))
        assert result.candidates == ()
        assert result.learnings == ()

    def test_qualifying_evidence_produces_one_institutional_learning(self) -> None:
        engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
        result = engine.build(
            _organizational_memory_result(["shared practice"] * 6, seed="om-e2e-2")
        )
        assert len(result.learnings) == 1
        assert result.learnings[0].maturity == LearningMaturity.VALIDATED
        assert result.metrics.institutional_count == 1

    def test_engine_is_deterministic_across_repeated_builds(self) -> None:
        engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
        source = _organizational_memory_result(["shared practice"] * 6, seed="om-e2e-3")
        assert engine.build(source) == engine.build(source)

    def test_policy_disabled_candidate_proposal_short_circuits(self) -> None:
        policy = LearningPolicyBuilder().build()
        disabled = policy.model_copy(
            update={
                "capability_switches": policy.capability_switches.model_copy(
                    update={"enable_candidate_proposal": False}
                )
            }
        )
        engine = DeterministicLearningEngine(policy=disabled, clock=lambda: _NOW)
        result = engine.build(
            _organizational_memory_result(["shared practice"] * 6, seed="om-e2e-4")
        )
        assert result.candidates == ()
        assert result.summary.headline.startswith("Learning is disabled by policy")

    def test_result_id_is_a_pure_function_of_the_consumed_result_id(self) -> None:
        engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
        source = _organizational_memory_result(["a", "b"], seed="om-e2e-5")
        result = engine.build(source)
        assert str(result.result_id).startswith("lr-")
        assert result.organizational_memory_result_id == str(source.result_id)


@pytest.mark.unit
class TestExplainabilityChain:
    """Every Learning object must reconstruct its full lineage (ADR-0029 D14)."""

    def _built_result(self) -> OrganizationalMemoryResult:
        return _organizational_memory_result(["shared practice"] * 6, seed="om-explain")

    def test_every_learning_candidate_id_resolves(self) -> None:
        engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
        result = engine.build(self._built_result())
        known_candidate_ids = {c.candidate_id for c in result.candidates}
        assert all(learning.candidate_id in known_candidate_ids for learning in result.learnings)

    def test_every_learning_validation_id_resolves(self) -> None:
        engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
        result = engine.build(self._built_result())
        known_validation_ids = {v.validation_id for v in result.validations}
        assert all(learning.validation_id in known_validation_ids for learning in result.learnings)

    def test_every_validation_candidate_id_resolves(self) -> None:
        engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
        result = engine.build(self._built_result())
        known_candidate_ids = {c.candidate_id for c in result.candidates}
        assert all(v.candidate_id in known_candidate_ids for v in result.validations)

    def test_every_confidence_subject_id_resolves(self) -> None:
        engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
        result = engine.build(self._built_result())
        known_subject_ids = {str(c.candidate_id) for c in result.candidates} | {
            str(learning.learning_id) for learning in result.learnings
        }
        assert all(c.subject_id in known_subject_ids for c in result.confidences)

    def test_every_lifecycle_subject_id_resolves(self) -> None:
        engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
        result = engine.build(self._built_result())
        known_subject_ids = {str(c.candidate_id) for c in result.candidates} | {
            str(learning.learning_id) for learning in result.learnings
        }
        assert all(entry.subject_id in known_subject_ids for entry in result.lifecycles)

    def test_every_candidate_source_best_practice_id_is_a_real_reference(self) -> None:
        engine = DeterministicLearningEngine(policy=default_learning_policy(), clock=lambda: _NOW)
        source = self._built_result()
        result = engine.build(source)
        known_bp_ids = {str(bp.best_practice_id) for bp in source.best_practices}
        for candidate in result.candidates:
            for bp_id in candidate.source_best_practice_ids:
                assert bp_id in known_bp_ids
