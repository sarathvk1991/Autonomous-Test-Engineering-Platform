"""Containment, ownership, and PlatformContext wiring tests for the
Organizational Memory engine (CAP-085B, ADR-0027 §D9-§D17).

Verifies each of the ten collaborators is the sole authority for its stated
responsibility, that the deterministic engine module imports only its own
collaborators (never a peer Layer 2 implementation package, never
PlatformContext, never Layer 1), that the rules/engine packages never touch
HistoricalDataset directly, and that PlatformContext exposes exactly one
factory returning the real deterministic service. No serializer, runtime
pipeline, Execution Package, or CLI behaviour is exercised here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.organizational_memory.engine import (
    BestPracticeGenerator,
    ExperienceClusterer,
    ExperienceCollector,
    LessonConsolidator,
    LessonGenerator,
    LifecycleRecorder,
    MetricsBuilder,
    PromotionRecorder,
    ResultBuilder,
    SummaryBuilder,
)
from requirement_intelligence.organizational_memory.identity import (
    ExperienceId,
    OrganizationalMemoryFrameworkVersion,
    OrganizationalMemoryId,
)
from requirement_intelligence.organizational_memory.models.enums import (
    OrganizationalMemoryConfidence,
    OrganizationalMemorySourceLayer,
)
from requirement_intelligence.organizational_memory.models.experience import Experience
from requirement_intelligence.organizational_memory.organizational_memory_service import (
    DeterministicOrganizationalMemoryService,
)
from requirement_intelligence.organizational_memory.policy import (
    default_organizational_memory_policy,
)
from requirement_intelligence.platform.platform_context import PlatformContext

_OM_PKG = Path(__file__).resolve().parents[2] / "requirement_intelligence" / "organizational_memory"
_NOW = datetime(2026, 7, 16, tzinfo=UTC)

_FORBIDDEN_IMPORT_TOKENS = (
    "requirement_intelligence.enhancement",
    "requirement_intelligence.grounding",
    "requirement_intelligence.validation",
    "requirement_intelligence.cp1",
    "requirement_intelligence.quality_governance",
    "requirement_intelligence.recommendation",
    "requirement_intelligence.execution",
    "PlatformContext",
)


def _experience(description: str, ref: str) -> Experience:
    return Experience(
        experience_id=ExperienceId.for_source("continuous_improvement", ref),
        source_layer=OrganizationalMemorySourceLayer.CONTINUOUS_IMPROVEMENT,
        source_reference_id=ref,
        description=description,
        confidence=OrganizationalMemoryConfidence.LOW,
    )


# ===========================================================================
# Import containment
# ===========================================================================


@pytest.mark.unit
class TestEngineImportContainment:
    @pytest.mark.parametrize(
        "filename",
        [
            "deterministic_engine.py",
            "experience_collector.py",
            "experience_clusterer.py",
            "lesson_generator.py",
            "lesson_consolidator.py",
            "best_practice_generator.py",
            "promotion_recorder.py",
            "lifecycle_recorder.py",
            "summary_builder.py",
            "metrics_builder.py",
            "result_builder.py",
        ],
    )
    def test_no_engine_module_imports_a_forbidden_layer(self, filename: str) -> None:
        source = (_OM_PKG / "engine" / filename).read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in _FORBIDDEN_IMPORT_TOKENS:
                    assert token not in line, f"{filename} imports {token}: {line!r}"

    def test_no_engine_module_touches_historical_dataset_directly(self) -> None:
        engine_dir = _OM_PKG / "engine"
        for path in engine_dir.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for line in source.splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "HistoricalDataset" not in line, (
                        f"{path.name} imports HistoricalDataset directly: {line!r}"
                    )

    def test_rules_package_carries_no_engine_imports(self) -> None:
        rules_dir = _OM_PKG / "rules"
        for path in rules_dir.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            for line in source.splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "organizational_memory.engine" not in line, (
                        f"{path.name} imports the engine package: {line!r}"
                    )


# ===========================================================================
# Sole-authority ownership
# ===========================================================================


@pytest.mark.unit
class TestSoleAuthorityOwnership:
    """Each collaborator, and only that collaborator, constructs its model type."""

    @pytest.mark.parametrize(
        ("model_name", "owner_filename"),
        [
            ("Experience(", "experience_collector.py"),
            ("Lesson(", "lesson_generator.py"),
            ("BestPractice(", "best_practice_generator.py"),
            ("KnowledgePromotion(", "promotion_recorder.py"),
            ("KnowledgeLifecycle(", "lifecycle_recorder.py"),
            ("OrganizationalMemoryResult(", "result_builder.py"),
        ],
    )
    def test_model_is_constructed_only_by_its_owning_collaborator(
        self, model_name: str, owner_filename: str
    ) -> None:
        engine_dir = _OM_PKG / "engine"
        offenders = []
        for path in engine_dir.rglob("*.py"):
            if path.name in (owner_filename, "__init__.py"):
                continue
            if model_name in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == [], f"{model_name} constructed outside {owner_filename}: {offenders}"

    @pytest.mark.parametrize(
        ("model_name", "owner_filename"),
        [
            ("OrganizationalMemorySummary(", "summary_builder.py"),
            ("OrganizationalMemoryMetrics(", "metrics_builder.py"),
        ],
    )
    def test_summary_and_metrics_are_built_by_their_owner_or_the_engines_empty_path(
        self, model_name: str, owner_filename: str
    ) -> None:
        """The engine's policy-disabled empty-result short-circuit constructs these
        two directly, exactly as ``DeterministicKnowledgeGraphEngine`` did for
        ``KnowledgeSummary``/``KnowledgeMetrics`` in CAP-084B — every other module
        must still delegate to the owning builder."""
        engine_dir = _OM_PKG / "engine"
        offenders = []
        for path in engine_dir.rglob("*.py"):
            if path.name in (owner_filename, "deterministic_engine.py", "__init__.py"):
                continue
            if model_name in path.read_text(encoding="utf-8"):
                offenders.append(path.name)
        assert offenders == [], f"{model_name} constructed outside {owner_filename}: {offenders}"

    def test_lesson_consolidator_never_mints_new_lesson_ids(self) -> None:
        source = (_OM_PKG / "engine" / "lesson_consolidator.py").read_text(encoding="utf-8")
        assert "LessonId.for_ordinal" not in source
        assert "LessonId.for_source" not in source

    def test_experience_clusterer_produces_no_new_experience_identity(self) -> None:
        source = (_OM_PKG / "engine" / "experience_clusterer.py").read_text(encoding="utf-8")
        assert "ExperienceId(" not in source
        assert "ExperienceId.for_source" not in source


# ===========================================================================
# Summary / Metrics computed exactly once, immutability
# ===========================================================================


@pytest.mark.unit
class TestSingleComputationAndImmutability:
    def test_summary_builder_output_is_immutable(self) -> None:
        summary = SummaryBuilder().build(
            default_organizational_memory_policy().policy_id,
            default_organizational_memory_policy().policy_version,
            (),
            (),
            (),
            (),
        )
        with pytest.raises((TypeError, AttributeError, ValueError)):
            summary.total_experiences = 5  # type: ignore[misc]

    def test_metrics_builder_output_is_immutable(self) -> None:
        metrics = MetricsBuilder().build((), (), (), (), ())
        with pytest.raises((TypeError, AttributeError, ValueError)):
            metrics.active_count = 5  # type: ignore[misc]

    def test_result_builder_output_is_immutable(self) -> None:
        policy = default_organizational_memory_policy()
        summary = SummaryBuilder().build(policy.policy_id, policy.policy_version, (), (), (), ())
        metrics = MetricsBuilder().build((), (), (), (), ())
        result = ResultBuilder().build(
            memory_id=OrganizationalMemoryId.for_inputs("ci-result-id", "kg-result-id"),
            continuous_improvement_result_id="ci-result-id",
            knowledge_graph_result_id="kg-result-id",
            experiences=(),
            lessons=(),
            best_practices=(),
            promotions=(),
            lifecycles=(),
            summary=summary,
            metrics=metrics,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            framework_version=OrganizationalMemoryFrameworkVersion(1, 0, 0),
            started_at=_NOW,
            completed_at=_NOW,
        )
        with pytest.raises((TypeError, AttributeError, ValueError)):
            result.experiences = ()  # type: ignore[misc]

    def test_collectors_never_mutate_their_inputs(self) -> None:
        experiences = (_experience("one", "ref-a"), _experience("two", "ref-b"))
        before = tuple(experiences)
        ExperienceClusterer().cluster(experiences)
        assert experiences == before


# ===========================================================================
# Replaceability — every collaborator is independently constructible
# ===========================================================================


@pytest.mark.unit
class TestReplaceability:
    def test_every_collaborator_is_constructible_in_isolation(self) -> None:
        policy = default_organizational_memory_policy()
        assert ExperienceCollector() is not None
        assert ExperienceClusterer() is not None
        assert LessonGenerator(policy) is not None
        assert LessonConsolidator() is not None
        assert BestPracticeGenerator(policy) is not None
        assert PromotionRecorder(policy) is not None
        assert LifecycleRecorder(policy) is not None
        assert SummaryBuilder() is not None
        assert MetricsBuilder() is not None
        assert ResultBuilder() is not None

    def test_collaborators_carry_no_reference_to_the_engine(self) -> None:
        engine_dir = _OM_PKG / "engine"
        for path in engine_dir.rglob("*.py"):
            if path.name in ("deterministic_engine.py", "__init__.py"):
                continue
            assert "DeterministicOrganizationalMemoryEngine" not in path.read_text(
                encoding="utf-8"
            )


# ===========================================================================
# PlatformContext wiring
# ===========================================================================


@pytest.mark.unit
class TestPlatformContextWiring:
    def test_create_organizational_memory_service_returns_the_deterministic_service(self) -> None:
        context = PlatformContext()
        service = context.create_organizational_memory_service()
        assert isinstance(service, DeterministicOrganizationalMemoryService)

    def test_repeated_calls_return_independent_but_equivalent_services(self) -> None:
        context = PlatformContext()
        first = context.create_organizational_memory_service()
        second = context.create_organizational_memory_service()
        assert first is not second
        assert first._engine._result_builder is not None

    def test_service_module_never_imports_platform_context(self) -> None:
        """The service module may *name* PlatformContext in prose (it documents who
        is allowed to construct it) but must never import it — the dependency
        direction runs one way, from PlatformContext down to the service."""
        source = (
            Path(__file__).resolve().parents[2]
            / "requirement_intelligence"
            / "organizational_memory"
            / "organizational_memory_service.py"
        ).read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "PlatformContext" not in line, f"imports PlatformContext: {line!r}"
