"""Unit tests for the Organizational Memory serialization layer (CAP-085C).

Covers the JSON round-trip invariant, deterministic Markdown/metrics rendering, the
ExecutionWriter integration (conditional artifacts + manifest registration + absence
when no OrganizationalMemoryResult), the manifest purity boundary (the manifest
references the Organizational Memory artifacts but never duplicates their content,
ADR-0027 §D18/§D19), and the frozen boundaries (serializer imports no Organizational
Memory runtime; the runtime contract imports no execution package). Mirrors
``test_knowledge_graph_serialization.py`` (CAP-084C).
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.execution.execution_writer import ExecutionWriter
from requirement_intelligence.organizational_memory.identity import (
    BestPracticeId,
    ExperienceId,
    KnowledgeLifecycleId,
    KnowledgePromotionId,
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
from requirement_intelligence.organizational_memory.serialization import (
    OrganizationalMemorySerializer,
)
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]

_ORGANIZATIONAL_MEMORY_ARTIFACTS = (
    "organizational_memory_result.json",
    "organizational_memory_report.md",
    "organizational_memory_metrics.md",
)

_NOW = datetime(2026, 7, 16, tzinfo=UTC)


def _with_content() -> OrganizationalMemoryResult:
    """A hand-built result carrying one of every knowledge object, for report
    content assertions.

    Hand-building the result directly (the same discipline the CAP-085B.1
    freeze test used) keeps this test focused on rendering, not on the
    floor-gated promotion conditions the engine's own tests already cover.
    """
    experience = Experience(
        experience_id=ExperienceId.for_source("knowledge_graph", "kg-finding-1"),
        source_layer=OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH,
        source_reference_id="kg-finding-1",
        description="A structural issue recurred.",
        confidence=OrganizationalMemoryConfidence.LOW,
    )
    lesson = Lesson(
        lesson_id=LessonId.for_ordinal("om-serialization", 0),
        source_experience_ids=(experience.experience_id,),
        message="When X recurs, Y follows.",
        confidence=OrganizationalMemoryConfidence.MEDIUM,
    )
    best_practice = BestPractice(
        best_practice_id=BestPracticeId.for_ordinal("om-serialization", 0),
        source_lesson_ids=(lesson.lesson_id,),
        title="Always check X",
        description="Generalized recommendation.",
        confidence=OrganizationalMemoryConfidence.VERIFIED,
    )
    promotion = KnowledgePromotion(
        promotion_id=KnowledgePromotionId.for_ordinal("om-serialization", 0),
        source_ids=(str(experience.experience_id),),
        target_ids=(str(lesson.lesson_id),),
        rationale="Promoted after threshold met.",
        promoted_at=_NOW,
        confidence=OrganizationalMemoryConfidence.MEDIUM,
        policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
    )
    lifecycle = KnowledgeLifecycle(
        lifecycle_id=KnowledgeLifecycleId.for_ordinal("om-serialization", 0),
        subject_id=str(best_practice.best_practice_id),
        state=KnowledgeLifecycleState.ACTIVE,
        state_reason="newly institutionalized",
    )
    return OrganizationalMemoryResult(
        result_id=OrganizationalMemoryResultId.for_memory("om-serialization"),
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


def _empty_result() -> OrganizationalMemoryResult:
    """A result carrying no experiences, lessons, best practices, promotions,
    or lifecycles — the policy-disabled shape."""
    return OrganizationalMemoryResult(
        result_id=OrganizationalMemoryResultId.for_memory("om-serialization-empty"),
        memory_id=OrganizationalMemoryId.for_inputs("ci-result-2", "kg-result-2"),
        continuous_improvement_result_id="ci-result-2",
        knowledge_graph_result_id="kg-result-2",
        experiences=(),
        lessons=(),
        best_practices=(),
        promotions=(),
        lifecycles=(),
        summary=OrganizationalMemorySummary(
            policy_id=OrganizationalMemoryPolicyId("default-organizational-memory-policy"),
            policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
            total_experiences=0,
            total_lessons=0,
            total_best_practices=0,
            total_promotions=0,
            headline="Organizational Memory curation is disabled by policy.",
        ),
        metrics=OrganizationalMemoryMetrics(
            experience_count=0,
            lesson_count=0,
            best_practice_count=0,
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


@pytest.mark.unit
class TestJsonProjection:
    def test_round_trip_equals_original(self) -> None:
        result = _with_content()
        dumped = OrganizationalMemorySerializer().render_json(result)
        assert OrganizationalMemoryResult.model_validate(dumped) == result

    def test_json_is_camel_case_and_carries_versions(self) -> None:
        dumped = OrganizationalMemorySerializer().render_json(_with_content())
        assert "resultVersion" in dumped
        assert "frameworkVersion" in dumped
        assert "policyVersion" in dumped
        assert "continuousImprovementResultId" in dumped
        assert "knowledgeGraphResultId" in dumped

    def test_json_is_deterministic_for_the_same_result(self) -> None:
        serializer = OrganizationalMemorySerializer()
        result = _with_content()
        assert json.dumps(serializer.render_json(result)) == json.dumps(
            serializer.render_json(result)
        )


@pytest.mark.unit
class TestMarkdownProjection:
    def test_report_is_deterministic_and_has_sections(self) -> None:
        serializer = OrganizationalMemorySerializer()
        result = _with_content()
        report = serializer.render_report(result)
        assert report == serializer.render_report(result)
        for section in (
            "# Organizational Memory Report",
            "## Summary",
            "## Consumed Layer 2 Results",
            "## Experiences",
            "## Lessons",
            "## Best Practices",
            "## Promotions",
            "## Lifecycles",
        ):
            assert section in report

    def test_metrics_is_deterministic_and_has_headline(self) -> None:
        serializer = OrganizationalMemorySerializer()
        result = _with_content()
        rendered = serializer.render_metrics(result)
        assert rendered == serializer.render_metrics(result)
        assert "# Organizational Memory Metrics" in rendered
        assert "Source Layer Distribution" in rendered
        assert "Lifecycle State Distribution" in rendered

    def test_report_surfaces_a_lesson_verbatim(self) -> None:
        # The projection never derives a lesson — it renders exactly what the
        # OrganizationalMemoryResult already recorded.
        serializer = OrganizationalMemorySerializer()
        result = _with_content()
        assert result.lessons
        report = serializer.render_report(result)
        assert str(result.lessons[0].lesson_id) in report
        assert result.lessons[0].message in report

    def test_result_with_no_content_still_renders_valid_sections(self) -> None:
        serializer = OrganizationalMemorySerializer()
        result = _empty_result()
        assert result.experiences == ()
        report = serializer.render_report(result)
        assert "_None_" in report
        metrics = serializer.render_metrics(result)
        assert "_None_" in metrics or "0" in metrics


@pytest.mark.unit
class TestExecutionWriterIntegration:
    def test_no_organizational_memory_result_produces_no_artifacts(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        data = replace(pipeline.execution_data, organizational_memory_result=None)
        target = tmp_path / "no_organizational_memory"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _ORGANIZATIONAL_MEMORY_ARTIFACTS:
            assert not (target / name).exists()
        assert all("organizational_memory" not in n for n in write_result.generated_artifacts)
        manifest = write_result.manifest
        assert "organizationalMemoryExecuted" not in manifest
        assert "organizationalMemoryReport" not in manifest

    def test_organizational_memory_result_produces_three_artifacts_and_manifest_entries(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = pipeline.organizational_memory_result
        data = replace(pipeline.execution_data, organizational_memory_result=result)
        target = tmp_path / "with_organizational_memory"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _ORGANIZATIONAL_MEMORY_ARTIFACTS:
            assert (target / name).exists()
            assert name in write_result.generated_artifacts
        manifest_names = {a["name"] for a in write_result.manifest["generatedArtifacts"]}
        assert set(_ORGANIZATIONAL_MEMORY_ARTIFACTS) <= manifest_names
        # Manifest purity (ADR-0027 §D18/§D19): the manifest is package metadata
        # only — it names the artifact, it never carries Organizational Memory
        # content. The canonical experiences/lessons/best practices/promotions/
        # lifecycles live exclusively in organizational_memory_result.json /
        # OrganizationalMemoryResult.
        assert write_result.manifest["organizationalMemoryExecuted"] is True
        assert "organizationalMemorySummary" not in write_result.manifest
        assert "organizationalMemoryExperiences" not in write_result.manifest
        result_path = target / "organizational_memory_result.json"
        on_disk = json.loads(result_path.read_text(encoding="utf-8"))
        assert on_disk["summary"]["totalExperiences"] == result.summary.total_experiences

    def test_artifacts_are_reproducible_from_organizational_memory_result_alone(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = pipeline.organizational_memory_result
        data = replace(pipeline.execution_data, organizational_memory_result=result)
        target = tmp_path / "repro"
        target.mkdir()
        ExecutionWriter().write(target, data)
        serializer = OrganizationalMemorySerializer()
        assert (target / "organizational_memory_report.md").read_text(encoding="utf-8") == (
            serializer.render_report(result)
        )
        assert (target / "organizational_memory_metrics.md").read_text(encoding="utf-8") == (
            serializer.render_metrics(result)
        )
        assert json.loads(
            (target / "organizational_memory_result.json").read_text(encoding="utf-8")
        ) == serializer.render_json(result)


@pytest.mark.unit
class TestSerializationBoundary:
    def test_serializer_imports_no_organizational_memory_runtime(self) -> None:
        source = (
            _REPO_ROOT
            / "requirement_intelligence"
            / "organizational_memory"
            / "serialization"
            / "organizational_memory_serializer.py"
        ).read_text(encoding="utf-8")
        forbidden = (
            "organizational_memory.engine",
            "organizational_memory_service",
            "organizational_memory.policy",
            "organizational_memory.rules",
            "DeterministicOrganizationalMemoryEngine",
            "DeterministicOrganizationalMemoryService",
            "OrganizationalMemoryService",
            "OrganizationalMemoryPolicy",
            "PromotionRuleCatalog",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"serializer must not import {token!r}"

    def test_runtime_contract_imports_no_execution_package(self) -> None:
        """OrganizationalMemoryResult must never depend on the Execution Package."""
        source = (
            _REPO_ROOT
            / "requirement_intelligence"
            / "organizational_memory"
            / "models"
            / "result.py"
        ).read_text(encoding="utf-8")
        assert "requirement_intelligence.execution" not in source
