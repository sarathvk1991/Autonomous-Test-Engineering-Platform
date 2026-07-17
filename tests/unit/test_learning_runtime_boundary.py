"""Runtime-boundary tests for Learning's CAP-086C activation (ADR-0029 §D29).

Covers the frozen pipeline order documented in the CLI, round-trip stability
across more than one result shape, the composition-root discipline the
Execution Package must observe post-activation, and self-containment of the
new serializer package. Complements
``test_learning_execution_integration.py``,
``test_learning_manifest_purity_boundary.py``, and
``test_learning_serialization.py`` rather than duplicating them. Unlike
``test_organizational_memory_runtime_boundary.py``, there is no two-peer
fan-in section here: Learning consumes exactly the one already-completed
Layer 2 tier immediately beneath it (ADR-0028 §Stage 12, ADR-0029 §D2), so
there is nothing of that shape to isolate or unit-test.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.learning.learning_service import DeterministicLearningService
from requirement_intelligence.learning.models.result import LearningResult
from requirement_intelligence.learning.serialization import LearningSerializer
from requirement_intelligence.platform.platform_context import PlatformContext
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"
_LEARNING_PKG = _REPO_ROOT / "requirement_intelligence" / "learning"
_EXECUTION_PKG = _REPO_ROOT / "requirement_intelligence" / "execution"


@pytest.mark.unit
class TestPipelineOrderDocumentation:
    def test_cli_module_docstring_and_phase_reflect_the_frozen_order(self) -> None:
        """The CLI documents Learning immediately after Organizational Memory."""
        source = _SCRIPT.read_text(encoding="utf-8")
        phase_doc_start = source.index("def run_learning_phase(")
        phase_doc = source[phase_doc_start : phase_doc_start + 900]
        om_pos = phase_doc.index("Organizational Memory")
        learning_pos = phase_doc.index("Learning", om_pos)
        ep_pos = phase_doc.index("Execution Package", learning_pos)
        assert om_pos < learning_pos < ep_pos

    def test_run_learning_phase_docstring_names_the_frozen_position(self) -> None:
        source = _SCRIPT.read_text(encoding="utf-8")
        start = source.index("def run_learning_phase(")
        end = source.index('"""', source.index('"""', start) + 3)
        docstring = source[start:end]
        assert "CAP-086C" in docstring
        assert "Organizational Memory" in docstring


@pytest.mark.unit
class TestEngineIsolationAcrossRoots:
    def test_learning_engine_never_named_in_execution_package(self) -> None:
        """The deterministic engine never crosses into the Execution Package."""
        needle = "DeterministicLearningEngine"
        offenders: list[Path] = []
        for path in _EXECUTION_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")) and needle in line:
                    offenders.append(path.relative_to(_REPO_ROOT))
        assert offenders == []

    def test_learning_engine_never_named_in_the_cli_script(self) -> None:
        """The CLI orchestrates through the service only, never the engine directly."""
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "DeterministicLearningEngine" not in source


@pytest.mark.unit
class TestServiceCompositionRootPostActivation:
    def test_cli_obtains_the_service_only_from_platform_context(self) -> None:
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "context.create_learning_service()" in source

    def test_platform_context_still_returns_the_deterministic_service(self) -> None:
        """CAP-086C activates the pipeline; it does not change what PlatformContext builds."""
        service = PlatformContext().create_learning_service()
        assert isinstance(service, DeterministicLearningService)


@pytest.mark.unit
class TestRoundTripAcrossResultShapes:
    def test_golden_result_round_trips_through_the_serializer_and_the_model(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        result = pipeline.learning_result
        assert result is not None
        dumped = LearningSerializer().render_json(result)
        assert LearningResult.model_validate(dumped) == result

    def test_disabled_policy_result_round_trips_too(self) -> None:
        """The policy-disabled empty-result path (engine's own short-circuit) round-trips.

        Exercises the same serializer/model round-trip invariant against the
        engine's ``_empty_result`` path (``enable_candidate_proposal=False``),
        never just the ordinary corpus-floor-gated path — the projection-only
        invariant must hold for every shape the engine can produce.
        """
        from requirement_intelligence.learning.engine import DeterministicLearningEngine
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

        now = datetime(2026, 7, 16, tzinfo=UTC)
        experience = Experience(
            experience_id=ExperienceId.for_source("knowledge_graph", "disabled-kg-0"),
            source_layer=OrganizationalMemorySourceLayer.KNOWLEDGE_GRAPH,
            source_reference_id="disabled-kg-0",
            description="A structural issue recurred.",
            confidence=OrganizationalMemoryConfidence.LOW,
        )
        lesson = Lesson(
            lesson_id=LessonId.for_ordinal("disabled", 0),
            source_experience_ids=(experience.experience_id,),
            message="When X recurs, Y follows.",
            confidence=OrganizationalMemoryConfidence.MEDIUM,
        )
        best_practice = BestPractice(
            best_practice_id=BestPracticeId.for_ordinal("disabled", 0),
            source_lesson_ids=(lesson.lesson_id,),
            title="Always check X",
            description="Generalized recommendation.",
            confidence=OrganizationalMemoryConfidence.VERIFIED,
        )
        om_result = OrganizationalMemoryResult(
            result_id=OrganizationalMemoryResultId.for_memory("disabled"),
            memory_id=OrganizationalMemoryId.for_inputs("ci-1", "kg-1"),
            continuous_improvement_result_id="ci-1",
            knowledge_graph_result_id="kg-1",
            experiences=(experience,),
            lessons=(lesson,),
            best_practices=(best_practice,),
            promotions=(),
            lifecycles=(),
            summary=OrganizationalMemorySummary(
                policy_id=OrganizationalMemoryPolicyId("default-organizational-memory-policy"),
                policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
                total_experiences=1,
                total_lessons=1,
                total_best_practices=1,
                total_promotions=0,
                headline="test fixture",
            ),
            metrics=OrganizationalMemoryMetrics(
                experience_count=1,
                lesson_count=1,
                best_practice_count=1,
                promotion_count=0,
                active_count=0,
                deprecated_count=0,
                historical_count=0,
                archived_count=0,
            ),
            policy_id=OrganizationalMemoryPolicyId("default-organizational-memory-policy"),
            policy_version=OrganizationalMemoryPolicyVersion(1, 0, 0),
            framework_version=OrganizationalMemoryFrameworkVersion(1, 0, 0),
            started_at=now,
            completed_at=now,
        )

        from requirement_intelligence.learning.policy import default_learning_policy

        base_policy = default_learning_policy()
        disabled_policy = base_policy.model_copy(
            update={
                "capability_switches": base_policy.capability_switches.model_copy(
                    update={"enable_candidate_proposal": False}
                )
            }
        )
        engine = DeterministicLearningEngine(policy=disabled_policy, clock=lambda: now)
        result = engine.build(om_result)
        assert result.candidates == ()
        dumped = LearningSerializer().render_json(result)
        assert LearningResult.model_validate(dumped) == result
        # The disabled-policy shape still renders valid, non-empty artifacts.
        report = LearningSerializer().render_report(result)
        metrics = LearningSerializer().render_metrics(result)
        assert report
        assert metrics


@pytest.mark.unit
class TestSerializationPackageIsSelfContained:
    def test_serialization_package_imports_no_layer_1_subsystem(self) -> None:
        layer_1 = (
            "requirement_intelligence.enhancement",
            "requirement_intelligence.grounding",
            "requirement_intelligence.validation",
            "requirement_intelligence.cp1",
            "requirement_intelligence.quality_governance",
            "requirement_intelligence.recommendation",
            "requirement_intelligence.analysis",
            "requirement_intelligence.context_orchestration",
        )
        for path in (_LEARNING_PKG / "serialization").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in layer_1:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_serialization_package_imports_no_organizational_memory_or_earlier_peer(
        self,
    ) -> None:
        """The serializer projects the result only — it never re-imports the
        consumed Organizational Memory result's own models, nor any earlier
        Layer 2 peer's."""
        for path in (_LEARNING_PKG / "serialization").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "organizational_memory" not in line, (
                        f"{path.name} imports organizational_memory: {line!r}"
                    )
                    assert "continuous_improvement" not in line, (
                        f"{path.name} imports continuous_improvement: {line!r}"
                    )
                    assert "knowledge_graph" not in line, (
                        f"{path.name} imports knowledge_graph: {line!r}"
                    )

    def test_serialization_package_exports_only_the_serializer(self) -> None:
        import requirement_intelligence.learning.serialization as pkg

        assert pkg.__all__ == ["LearningSerializer"]


@pytest.mark.unit
class TestManifestArtifactInventoryConsistency:
    def test_generated_artifacts_list_includes_exactly_the_three_learning_files(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        names = {
            entry["name"]
            for entry in pipeline.write_result.manifest["generatedArtifacts"]
            if entry["name"].startswith("learning")
        }
        assert names == {
            "learning_result.json",
            "learning_report.md",
            "learning_metrics.md",
        }

    def test_every_learning_artifact_has_a_positive_byte_count(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        entries = {
            entry["name"]: entry for entry in pipeline.write_result.manifest["generatedArtifacts"]
        }
        for name in (
            "learning_result.json",
            "learning_report.md",
            "learning_metrics.md",
        ):
            assert entries[name]["bytes"] > 0
