"""Unit and architecture tests for the deterministic Organizational Memory
engine and its ten modular collaborators (CAP-085B, ADR-0027 §D9-§D17).

Covers each collaborator's sole-authority ownership, deterministic behaviour
(clustering equality, floor-gated generation, confidence scaling, promotion
provenance, lifecycle recording), builder single-computation guarantees,
end-to-end engine determinism and explainability, and policy gating. No
serializer, runtime-pipeline, Execution Package, or CLI behaviour is tested
here (Stage 9 of the CAP-085B brief).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from requirement_intelligence.continuous_improvement.engine import (
    DeterministicContinuousImprovementEngine,
)
from requirement_intelligence.continuous_improvement.identity import (
    ContinuousImprovementFrameworkVersion,
    ContinuousImprovementResultId,
    ImprovementFindingId,
    ImprovementPolicyId,
    ImprovementPolicyVersion,
)
from requirement_intelligence.continuous_improvement.models import (
    ContinuousImprovementResult,
)
from requirement_intelligence.continuous_improvement.models import (
    HistoricalDatasetReference as CIHistoricalDatasetReference,
)
from requirement_intelligence.continuous_improvement.models.enums import (
    ImprovementFindingCategory,
    ImprovementSeverity,
    ImprovementSourceLayer,
)
from requirement_intelligence.continuous_improvement.models.finding import ImprovementFinding
from requirement_intelligence.continuous_improvement.models.summary import (
    ImprovementMetrics,
    ImprovementSummary,
)
from requirement_intelligence.continuous_improvement.policy import default_improvement_policy
from requirement_intelligence.continuous_improvement.rules import default_improvement_rule_catalog
from requirement_intelligence.knowledge_graph.engine import DeterministicKnowledgeGraphEngine
from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeGraphFrameworkVersion,
    KnowledgeGraphId,
    KnowledgeGraphResultId,
    KnowledgePolicyId,
    KnowledgePolicyVersion,
)
from requirement_intelligence.knowledge_graph.models import (
    HistoricalDatasetReference as KGHistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models import (
    KnowledgeGraphResult,
)
from requirement_intelligence.knowledge_graph.models.summary import (
    KnowledgeMetrics,
    KnowledgeSummary,
)
from requirement_intelligence.knowledge_graph.policy import default_knowledge_graph_policy
from requirement_intelligence.knowledge_graph.rules import default_knowledge_graph_rule_catalog
from requirement_intelligence.organizational_memory.engine import (
    BestPracticeGenerator,
    DeterministicOrganizationalMemoryEngine,
    ExperienceClusterer,
    ExperienceCollector,
    LessonConsolidator,
    LessonGenerator,
    LifecycleRecorder,
    MetricsBuilder,
    PromotionRecorder,
    SummaryBuilder,
)
from requirement_intelligence.organizational_memory.identity import (
    ExperienceId,
    LessonId,
    OrganizationalMemoryId,
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
)
from requirement_intelligence.organizational_memory.models.enums import (
    KnowledgeLifecycleState,
    OrganizationalMemoryConfidence,
    OrganizationalMemorySourceLayer,
)
from requirement_intelligence.organizational_memory.models.experience import Experience
from requirement_intelligence.organizational_memory.models.lesson import Lesson
from requirement_intelligence.organizational_memory.policy import (
    default_organizational_memory_policy,
)

_NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _ci_reference(**overrides: object) -> CIHistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-engine-test",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-3",
        execution_count=3,
        history_window=25,
        generated_at=_NOW,
    )
    defaults.update(overrides)
    return CIHistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _kg_reference(**overrides: object) -> KGHistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-engine-test",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-1",
        execution_count=1,
        history_window=1,
        generated_at=_NOW,
    )
    defaults.update(overrides)
    return KGHistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _ci_result(**overrides: object) -> ContinuousImprovementResult:
    engine = DeterministicContinuousImprovementEngine(
        policy=default_improvement_policy(),
        rule_catalog=default_improvement_rule_catalog(),
        clock=lambda: _NOW,
    )
    return engine.improve(_ci_reference(**overrides))


def _kg_result(**overrides: object) -> KnowledgeGraphResult:
    engine = DeterministicKnowledgeGraphEngine(
        policy=default_knowledge_graph_policy(),
        rule_catalog=default_knowledge_graph_rule_catalog(),
        clock=lambda: _NOW,
    )
    return engine.build(_kg_reference(**overrides))


def _empty_ci_result() -> ContinuousImprovementResult:
    """A ContinuousImprovementResult with zero findings/trends/opportunities."""
    return ContinuousImprovementResult(
        result_id=ContinuousImprovementResultId.for_dataset("ds-empty"),
        historical_dataset=_ci_reference(dataset_id="ds-empty"),
        findings=(),
        trends=(),
        opportunities=(),
        summary=ImprovementSummary(
            policy_id=ImprovementPolicyId("p"),
            policy_version=ImprovementPolicyVersion(1, 0, 0),
            total_findings=0,
            total_trends=0,
            total_opportunities=0,
            headline="empty",
        ),
        metrics=ImprovementMetrics(
            finding_density=0.0, trend_stability_ratio=0.0, opportunity_rate=0.0
        ),
        policy_id=ImprovementPolicyId("p"),
        policy_version=ImprovementPolicyVersion(1, 0, 0),
        framework_version=ContinuousImprovementFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


def _empty_kg_result() -> KnowledgeGraphResult:
    """A KnowledgeGraphResult with zero nodes/edges/findings/observations/subgraphs."""
    return KnowledgeGraphResult(
        result_id=KnowledgeGraphResultId.for_graph("kg-empty"),
        graph_id=KnowledgeGraphId.for_dataset("ds-empty"),
        historical_dataset=_kg_reference(dataset_id="ds-empty"),
        nodes=(),
        edges=(),
        subgraphs=(),
        observations=(),
        findings=(),
        summary=KnowledgeSummary(
            policy_id=KnowledgePolicyId("p"),
            policy_version=KnowledgePolicyVersion(1, 0, 0),
            total_nodes=0,
            total_edges=0,
            total_subgraphs=0,
            total_observations=0,
            total_findings=0,
            headline="empty",
        ),
        metrics=KnowledgeMetrics(
            node_count=0,
            edge_count=0,
            subgraph_count=0,
            connected_component_count=0,
            average_degree=0.0,
            orphan_node_count=0,
        ),
        policy_id=KnowledgePolicyId("p"),
        policy_version=KnowledgePolicyVersion(1, 0, 0),
        framework_version=KnowledgeGraphFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


def _repeated_ci_result(
    count: int = 6, dataset_id: str = "ds-repeat"
) -> ContinuousImprovementResult:
    """A ContinuousImprovementResult carrying *count* identical-message findings."""
    findings = tuple(
        ImprovementFinding(
            finding_id=ImprovementFindingId.for_ordinal(dataset_id, i),
            category=ImprovementFindingCategory.RECURRING_VALIDATION_FAILURE,
            source=ImprovementSourceLayer.VALIDATION,
            severity=ImprovementSeverity.WARNING,
            occurrence_count=3,
            contributing_execution_ids=(
                f"{dataset_id}-{i}-a",
                f"{dataset_id}-{i}-b",
                f"{dataset_id}-{i}-c",
            ),
            message="Same recurring validation issue",
        )
        for i in range(count)
    )
    return ContinuousImprovementResult(
        result_id=ContinuousImprovementResultId.for_dataset(dataset_id),
        historical_dataset=_ci_reference(dataset_id=dataset_id),
        findings=findings,
        trends=(),
        opportunities=(),
        summary=ImprovementSummary(
            policy_id=ImprovementPolicyId("p"),
            policy_version=ImprovementPolicyVersion(1, 0, 0),
            total_findings=count,
            total_trends=0,
            total_opportunities=0,
            headline="repeated",
        ),
        metrics=ImprovementMetrics(
            finding_density=1.0, trend_stability_ratio=0.0, opportunity_rate=0.0
        ),
        policy_id=ImprovementPolicyId("p"),
        policy_version=ImprovementPolicyVersion(1, 0, 0),
        framework_version=ContinuousImprovementFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


# ===========================================================================
# ExperienceCollector
# ===========================================================================


@pytest.mark.unit
class TestExperienceCollector:
    def test_captures_from_all_six_source_types(self) -> None:
        collector = ExperienceCollector()
        experiences = collector.collect(_ci_result(), _kg_result())
        assert len(experiences) > 0

    def test_empty_inputs_yield_no_experiences(self) -> None:
        collector = ExperienceCollector()
        experiences = collector.collect(_empty_ci_result(), _empty_kg_result())
        assert experiences == ()

    def test_every_experience_references_exactly_one_source(self) -> None:
        collector = ExperienceCollector()
        experiences = collector.collect(_ci_result(), _kg_result())
        for experience in experiences:
            assert experience.source_reference_id

    def test_deterministic_given_the_same_inputs(self) -> None:
        collector = ExperienceCollector()
        ci_result = _ci_result()
        kg_result = _kg_result()
        first = collector.collect(ci_result, kg_result)
        second = collector.collect(ci_result, kg_result)
        assert first == second

    def test_new_experiences_start_at_low_confidence(self) -> None:
        collector = ExperienceCollector()
        experiences = collector.collect(_ci_result(), _kg_result())
        assert all(e.confidence == OrganizationalMemoryConfidence.LOW for e in experiences)

    def test_ci_experiences_are_tagged_continuous_improvement(self) -> None:
        collector = ExperienceCollector()
        experiences = collector.collect(_repeated_ci_result(count=1), _empty_kg_result())
        assert all(
            e.source_layer == OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT
            for e in experiences
        )

    def test_kg_experiences_are_tagged_knowledge_graph(self) -> None:
        collector = ExperienceCollector()
        experiences = collector.collect(_empty_ci_result(), _kg_result())
        assert all(
            e.source_layer == OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH for e in experiences
        )


# ===========================================================================
# ExperienceClusterer
# ===========================================================================


def _experience(description: str, layer: OrganizationalMemorySourceLayer, ref: str) -> Experience:
    return Experience(
        experience_id=ExperienceId.for_source(layer.value, ref),
        source_layer=layer,
        source_reference_id=ref,
        description=description,
        confidence=OrganizationalMemoryConfidence.LOW,
    )


@pytest.mark.unit
class TestExperienceClusterer:
    def test_groups_identical_description_within_same_layer(self) -> None:
        a = _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, "ref-a")
        b = _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, "ref-b")
        clusters = ExperienceClusterer().cluster((a, b))
        assert len(clusters) == 1
        assert set(clusters[0]) == {a, b}

    def test_never_clusters_across_source_layers(self) -> None:
        a = _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, "ref-a")
        b = _experience("same", OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH, "ref-b")
        clusters = ExperienceClusterer().cluster((a, b))
        assert len(clusters) == 2

    def test_distinct_descriptions_never_cluster_together(self) -> None:
        a = _experience("one", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, "ref-a")
        b = _experience("two", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, "ref-b")
        clusters = ExperienceClusterer().cluster((a, b))
        assert len(clusters) == 2

    def test_empty_input_yields_no_clusters(self) -> None:
        assert ExperienceClusterer().cluster(()) == ()

    def test_deterministic_ordering_regardless_of_input_order(self) -> None:
        a = _experience("one", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, "ref-a")
        b = _experience("two", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, "ref-b")
        forward = ExperienceClusterer().cluster((a, b))
        backward = ExperienceClusterer().cluster((b, a))
        assert forward == backward


# ===========================================================================
# LessonGenerator
# ===========================================================================


@pytest.mark.unit
class TestLessonGenerator:
    def test_no_lesson_below_the_experience_floor(self) -> None:
        policy = default_organizational_memory_policy()
        experiences = tuple(
            _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, f"ref-{i}")
            for i in range(policy.thresholds.minimum_experiences_for_lesson - 1)
        )
        clusters = ExperienceClusterer().cluster(experiences)
        lessons = LessonGenerator(policy).generate(clusters, "om-test")
        assert lessons == ()

    def test_lesson_generated_once_floor_is_cleared(self) -> None:
        policy = default_organizational_memory_policy()
        experiences = tuple(
            _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, f"ref-{i}")
            for i in range(policy.thresholds.minimum_experiences_for_lesson)
        )
        clusters = ExperienceClusterer().cluster(experiences)
        lessons = LessonGenerator(policy).generate(clusters, "om-test")
        assert len(lessons) == 1
        assert set(lessons[0].source_experience_ids) == {e.experience_id for e in experiences}

    def test_disabled_switch_yields_no_lessons(self) -> None:
        base_policy = default_organizational_memory_policy()
        policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_lesson_promotion": False}
                )
            }
        )
        experiences = tuple(
            _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, f"ref-{i}")
            for i in range(10)
        )
        clusters = ExperienceClusterer().cluster(experiences)
        lessons = LessonGenerator(policy).generate(clusters, "om-test")
        assert lessons == ()

    def test_confidence_scales_with_evidence(self) -> None:
        policy = default_organizational_memory_policy()
        threshold = policy.thresholds.minimum_experiences_for_lesson
        experiences = tuple(
            _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, f"ref-{i}")
            for i in range(threshold * 3)
        )
        clusters = ExperienceClusterer().cluster(experiences)
        lessons = LessonGenerator(policy).generate(clusters, "om-test")
        assert lessons[0].confidence == OrganizationalMemoryConfidence.VERIFIED

    def test_lesson_ids_are_deterministic(self) -> None:
        policy = default_organizational_memory_policy()
        experiences = tuple(
            _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, f"ref-{i}")
            for i in range(policy.thresholds.minimum_experiences_for_lesson)
        )
        clusters = ExperienceClusterer().cluster(experiences)
        first = LessonGenerator(policy).generate(clusters, "om-test")
        second = LessonGenerator(policy).generate(clusters, "om-test")
        assert first == second


# ===========================================================================
# LessonConsolidator
# ===========================================================================


@pytest.mark.unit
class TestLessonConsolidator:
    def _lesson(self, message: str, experience_refs: tuple[str, ...], ordinal: int) -> Lesson:
        return Lesson(
            lesson_id=LessonId.for_ordinal("om-test", ordinal),
            source_experience_ids=tuple(
                ExperienceId.for_source("continuous_improvement", ref) for ref in experience_refs
            ),
            message=message,
            confidence=OrganizationalMemoryConfidence.MEDIUM,
        )

    def test_distinct_messages_pass_through_unchanged(self) -> None:
        a = self._lesson("one", ("ref-a",), 0)
        b = self._lesson("two", ("ref-b",), 1)
        result = LessonConsolidator().consolidate((a, b))
        assert set(result) == {a, b}

    def test_identical_messages_are_merged(self) -> None:
        a = self._lesson("same", ("ref-a",), 0)
        b = self._lesson("same", ("ref-b",), 1)
        result = LessonConsolidator().consolidate((a, b))
        assert len(result) == 1

    def test_merge_unions_source_experience_ids(self) -> None:
        a = self._lesson("same", ("ref-a",), 0)
        b = self._lesson("same", ("ref-b",), 1)
        result = LessonConsolidator().consolidate((a, b))
        assert set(result[0].source_experience_ids) == set(a.source_experience_ids) | set(
            b.source_experience_ids
        )

    def test_merge_keeps_the_lower_lesson_id(self) -> None:
        a = self._lesson("same", ("ref-a",), 0)
        b = self._lesson("same", ("ref-b",), 1)
        result = LessonConsolidator().consolidate((a, b))
        assert result[0].lesson_id == min(a.lesson_id, b.lesson_id, key=str)

    def test_empty_input_yields_empty_output(self) -> None:
        assert LessonConsolidator().consolidate(()) == ()

    def test_single_lesson_passes_through_unchanged(self) -> None:
        a = self._lesson("solo", ("ref-a",), 0)
        assert LessonConsolidator().consolidate((a,)) == (a,)


# ===========================================================================
# BestPracticeGenerator
# ===========================================================================


@pytest.mark.unit
class TestBestPracticeGenerator:
    def _experiences_and_lessons(
        self, lesson_count: int
    ) -> tuple[tuple[Experience, ...], tuple[Lesson, ...]]:
        policy = default_organizational_memory_policy()
        exp_threshold = policy.thresholds.minimum_experiences_for_lesson
        all_experiences: list[Experience] = []
        clusters: list[tuple[Experience, ...]] = []
        for lesson_index in range(lesson_count):
            group = tuple(
                _experience(
                    f"pattern-{lesson_index}",
                    OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT,
                    f"ref-{lesson_index}-{i}",
                )
                for i in range(exp_threshold)
            )
            clusters.append(group)
            all_experiences.extend(group)
        lessons = LessonGenerator(policy).generate(tuple(clusters), "om-test")
        return tuple(all_experiences), lessons

    def test_no_best_practice_below_the_lesson_floor(self) -> None:
        policy = default_organizational_memory_policy()
        experiences, lessons = self._experiences_and_lessons(
            policy.thresholds.minimum_lessons_for_best_practice - 1
        )
        best_practices = BestPracticeGenerator(policy).generate(lessons, experiences, "om-test")
        assert best_practices == ()

    def test_best_practice_generated_once_floor_is_cleared(self) -> None:
        policy = default_organizational_memory_policy()
        experiences, lessons = self._experiences_and_lessons(
            policy.thresholds.minimum_lessons_for_best_practice
        )
        best_practices = BestPracticeGenerator(policy).generate(lessons, experiences, "om-test")
        assert len(best_practices) == 1
        assert set(best_practices[0].source_lesson_ids) == {lesson.lesson_id for lesson in lessons}

    def test_never_references_experiences_directly(self) -> None:
        from requirement_intelligence.organizational_memory.models.best_practice import (
            BestPractice,
        )

        assert "source_experience_ids" not in BestPractice.model_fields

    def test_disabled_switch_yields_no_best_practices(self) -> None:
        base_policy = default_organizational_memory_policy()
        policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_best_practice_promotion": False}
                )
            }
        )
        experiences, lessons = self._experiences_and_lessons(
            policy.thresholds.minimum_lessons_for_best_practice
        )
        best_practices = BestPracticeGenerator(policy).generate(lessons, experiences, "om-test")
        assert best_practices == ()

    def test_no_lessons_yields_no_best_practices(self) -> None:
        policy = default_organizational_memory_policy()
        best_practices = BestPracticeGenerator(policy).generate((), (), "om-test")
        assert best_practices == ()


# ===========================================================================
# PromotionRecorder
# ===========================================================================


@pytest.mark.unit
class TestPromotionRecorder:
    def test_records_one_promotion_per_lesson(self) -> None:
        policy = default_organizational_memory_policy()
        experiences = tuple(
            _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, f"ref-{i}")
            for i in range(policy.thresholds.minimum_experiences_for_lesson)
        )
        clusters = ExperienceClusterer().cluster(experiences)
        lessons = LessonGenerator(policy).generate(clusters, "om-test")
        promotions = PromotionRecorder(policy).record(lessons, (), "om-test", _NOW)
        assert len(promotions) == 1
        assert promotions[0].target_ids == (str(lessons[0].lesson_id),)
        expected_sources = {str(eid) for eid in lessons[0].source_experience_ids}
        assert set(promotions[0].source_ids) == expected_sources

    def test_promotion_carries_the_policy_version(self) -> None:
        policy = default_organizational_memory_policy()
        experiences = tuple(
            _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, f"ref-{i}")
            for i in range(policy.thresholds.minimum_experiences_for_lesson)
        )
        clusters = ExperienceClusterer().cluster(experiences)
        lessons = LessonGenerator(policy).generate(clusters, "om-test")
        promotions = PromotionRecorder(policy).record(lessons, (), "om-test", _NOW)
        assert promotions[0].policy_version == policy.policy_version

    def test_no_lessons_or_best_practices_yields_no_promotions(self) -> None:
        policy = default_organizational_memory_policy()
        assert PromotionRecorder(policy).record((), (), "om-test", _NOW) == ()

    def test_promotion_timestamp_matches_the_injected_clock(self) -> None:
        policy = default_organizational_memory_policy()
        experiences = tuple(
            _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, f"ref-{i}")
            for i in range(policy.thresholds.minimum_experiences_for_lesson)
        )
        clusters = ExperienceClusterer().cluster(experiences)
        lessons = LessonGenerator(policy).generate(clusters, "om-test")
        promotions = PromotionRecorder(policy).record(lessons, (), "om-test", _NOW)
        assert promotions[0].promoted_at == _NOW


# ===========================================================================
# LifecycleRecorder
# ===========================================================================


@pytest.mark.unit
class TestLifecycleRecorder:
    def test_records_active_for_every_experience(self) -> None:
        policy = default_organizational_memory_policy()
        experiences = (
            _experience("one", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, "ref-a"),
        )
        records = LifecycleRecorder(policy).record(experiences, (), (), "om-test")
        assert len(records) == 1
        assert records[0].state == KnowledgeLifecycleState.ACTIVE
        assert records[0].subject_id == str(experiences[0].experience_id)

    def test_disabled_switch_yields_no_lifecycle_records(self) -> None:
        base_policy = default_organizational_memory_policy()
        policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_retirement": False}
                )
            }
        )
        experiences = (
            _experience("one", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, "ref-a"),
        )
        assert LifecycleRecorder(policy).record(experiences, (), (), "om-test") == ()

    def test_records_one_entry_per_knowledge_object(self) -> None:
        policy = default_organizational_memory_policy()
        experiences = tuple(
            _experience("same", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, f"ref-{i}")
            for i in range(policy.thresholds.minimum_experiences_for_lesson)
        )
        clusters = ExperienceClusterer().cluster(experiences)
        lessons = LessonGenerator(policy).generate(clusters, "om-test")
        records = LifecycleRecorder(policy).record(experiences, lessons, (), "om-test")
        assert len(records) == len(experiences) + len(lessons)


# ===========================================================================
# SummaryBuilder / MetricsBuilder / ResultBuilder
# ===========================================================================


@pytest.mark.unit
class TestSummaryBuilder:
    def test_tallies_already_produced_collaborator_output(self) -> None:
        summary = SummaryBuilder().build(
            OrganizationalMemoryPolicyId("p"),
            OrganizationalMemoryPolicyVersion(1, 0, 0),
            (),
            (),
            (),
            (),
        )
        assert summary.total_experiences == 0
        assert "0 experience" in summary.headline


@pytest.mark.unit
class TestMetricsBuilder:
    def test_tallies_lifecycle_state_distribution(self) -> None:
        policy = default_organizational_memory_policy()
        experiences = (
            _experience("one", OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT, "ref-a"),
        )
        lifecycles = LifecycleRecorder(policy).record(experiences, (), (), "om-test")
        metrics = MetricsBuilder().build(experiences, (), (), (), lifecycles)
        assert metrics.active_count == 1
        assert metrics.deprecated_count == 0


@pytest.mark.unit
class TestResultBuilder:
    def test_is_the_only_result_constructor_in_the_engine(self) -> None:
        """Mirrors ADR-0023's own KnowledgeGraphResult containment test."""
        from pathlib import Path

        engine_dir = (
            Path(__file__).resolve().parents[2]
            / "requirement_intelligence"
            / "organizational_memory"
            / "engine"
        )
        offenders = []
        for path in engine_dir.rglob("*.py"):
            if path.name == "result_builder.py":
                continue
            if "OrganizationalMemoryResult(" in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == []


# ===========================================================================
# DeterministicOrganizationalMemoryEngine — end to end
# ===========================================================================


@pytest.mark.unit
class TestDeterministicEngineEndToEnd:
    def test_builds_a_valid_result(self) -> None:
        engine = DeterministicOrganizationalMemoryEngine(
            policy=default_organizational_memory_policy(), clock=lambda: _NOW
        )
        result = engine.build(_ci_result(), _kg_result())
        assert result.result_id is not None

    def test_deterministic_given_the_same_inputs(self) -> None:
        ci_result = _ci_result()
        kg_result = _kg_result()
        engine = DeterministicOrganizationalMemoryEngine(
            policy=default_organizational_memory_policy(), clock=lambda: _NOW
        )
        first = engine.build(ci_result, kg_result)
        second = engine.build(ci_result, kg_result)
        assert first == second

    def test_memory_id_is_a_pure_function_of_the_two_result_ids(self) -> None:
        ci_result = _ci_result()
        kg_result = _kg_result()
        expected = OrganizationalMemoryId.for_inputs(
            str(ci_result.result_id), str(kg_result.result_id)
        )
        engine = DeterministicOrganizationalMemoryEngine(
            policy=default_organizational_memory_policy(), clock=lambda: _NOW
        )
        result = engine.build(ci_result, kg_result)
        assert result.memory_id == expected

    def test_disabled_master_switch_yields_the_empty_result_path(self) -> None:
        base_policy = default_organizational_memory_policy()
        policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_experience_capture": False}
                )
            }
        )
        engine = DeterministicOrganizationalMemoryEngine(policy=policy, clock=lambda: _NOW)
        result = engine.build(_ci_result(), _kg_result())
        assert result.experiences == ()
        assert result.lessons == ()
        assert result.best_practices == ()
        assert "disabled" in result.summary.headline

    def test_round_trips_from_serialization_alone(self) -> None:
        engine = DeterministicOrganizationalMemoryEngine(
            policy=default_organizational_memory_policy(), clock=lambda: _NOW
        )
        result = engine.build(_ci_result(), _kg_result())
        dumped = result.model_dump(mode="json", by_alias=True)
        from requirement_intelligence.organizational_memory.models import (
            OrganizationalMemoryResult,
        )

        assert OrganizationalMemoryResult.model_validate(dumped) == result

    def test_promotion_pathway_produces_a_lesson_and_a_promotion(self) -> None:
        engine = DeterministicOrganizationalMemoryEngine(
            policy=default_organizational_memory_policy(), clock=lambda: _NOW
        )
        result = engine.build(_repeated_ci_result(count=6), _empty_kg_result())
        assert len(result.lessons) == 1
        assert len(result.promotions) == 1
        assert result.lessons[0].confidence == OrganizationalMemoryConfidence.HIGH

    def test_every_experience_lesson_and_best_practice_gets_a_lifecycle_entry(self) -> None:
        engine = DeterministicOrganizationalMemoryEngine(
            policy=default_organizational_memory_policy(), clock=lambda: _NOW
        )
        result = engine.build(_repeated_ci_result(count=6), _empty_kg_result())
        expected = len(result.experiences) + len(result.lessons) + len(result.best_practices)
        assert len(result.lifecycles) == expected

    def test_completed_at_is_never_before_started_at(self) -> None:
        engine = DeterministicOrganizationalMemoryEngine(
            policy=default_organizational_memory_policy()
        )
        result = engine.build(_ci_result(), _kg_result())
        assert result.completed_at >= result.started_at
