"""Contract and architecture-boundary tests for KnowledgeGraphService (CAP-084A).

ADR-0023 froze the service boundary: abstract contract, dormant implementation,
``PlatformContext`` registration. These tests assert the permanent contract, the
``PlatformContext`` composition root, and the containment/dependency invariants
(ADR-0023 §D6), mirroring ``test_continuous_improvement_service.py`` (ADR-0022
§D6) as it stood at CAP-083A.

Knowledge Graph is the second Layer 2 capability (ADR-0020) and consumes
Historical Truth only (ADR-0021 §Stage 8) — it imports **no** Layer 1 subsystem,
and — unlike a Layer 1 peer such as Recommendation — it also imports no other
Layer 2 capability (Continuous Improvement), a stricter boundary than any Layer 1
subsystem imposes on its peers.
"""

from __future__ import annotations

from abc import ABC
from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.knowledge_graph.knowledge_graph_service import (
    DormantKnowledgeGraphService,
    KnowledgeGraphService,
)
from requirement_intelligence.knowledge_graph.models import HistoricalDatasetReference
from requirement_intelligence.knowledge_graph.policy import (
    KnowledgeGraphPolicy,
)
from requirement_intelligence.platform.platform_context import PlatformContext

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KNOWLEDGE_GRAPH_PKG = _REPO_ROOT / "requirement_intelligence" / "knowledge_graph"

#: Every Layer 1 subsystem Knowledge Graph must never import — a stricter boundary
#: than any Layer 1 subsystem imposes on its own peers (ADR-0021 §Stage 8).
_LAYER_1_SUBSYSTEMS = (
    "requirement_intelligence.enhancement",
    "requirement_intelligence.grounding",
    "requirement_intelligence.validation",
    "requirement_intelligence.cp1",
    "requirement_intelligence.quality_governance",
    "requirement_intelligence.recommendation",
    "requirement_intelligence.analysis",
    "requirement_intelligence.context_orchestration",
)

#: Continuous Improvement is a Layer 2 peer, not an upstream Knowledge Graph may
#: consume (ADR-0023 §D3: two Layer 2 capabilities at the same Truth Hierarchy
#: level do not consume one another without a deliberate future ADR).
_LAYER_2_PEERS = ("requirement_intelligence.continuous_improvement",)


def _reference(**overrides: object) -> HistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-1",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-25",
        execution_count=25,
        history_window=25,
        generated_at=datetime(2026, 7, 15, tzinfo=UTC),
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestServiceContract:
    def test_service_contract_is_abstract(self) -> None:
        assert issubclass(KnowledgeGraphService, ABC)
        with pytest.raises(TypeError):
            KnowledgeGraphService()  # type: ignore[abstract]


@pytest.mark.unit
class TestDormantService:
    def test_dormant_service_raises_not_implemented(self) -> None:
        service = DormantKnowledgeGraphService()
        with pytest.raises(NotImplementedError):
            service.build(_reference())

    def test_platform_context_dormant_service_raises_not_implemented(self) -> None:
        service = PlatformContext().create_knowledge_graph_service()
        with pytest.raises(NotImplementedError):
            service.build(_reference())

    def test_dormant_service_is_a_knowledge_graph_service(self) -> None:
        assert isinstance(DormantKnowledgeGraphService(), KnowledgeGraphService)


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_knowledge_graph_policy_returns_policy(self) -> None:
        policy = PlatformContext().create_knowledge_graph_policy()
        assert isinstance(policy, KnowledgeGraphPolicy)

    def test_create_knowledge_graph_service_returns_dormant_service(self) -> None:
        service = PlatformContext().create_knowledge_graph_service()
        assert isinstance(service, KnowledgeGraphService)
        assert isinstance(service, DormantKnowledgeGraphService)

    def test_repeated_calls_return_independent_but_equal_policies(self) -> None:
        ctx = PlatformContext()
        assert ctx.create_knowledge_graph_policy() == ctx.create_knowledge_graph_policy()

    def test_repeated_calls_return_independent_service_instances(self) -> None:
        ctx = PlatformContext()
        assert ctx.create_knowledge_graph_service() is not ctx.create_knowledge_graph_service()


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_sanctioned_wiring_points_name_the_service_externally(self) -> None:
        """Outside the knowledge_graph package, only PlatformContext may name it.

        CAP-084A registers the dormant implementation, but the subsystem remains
        entirely unwired: no CLI phase, execution builder, manifest, or serializer
        may reference the runtime service, so a future dependency cannot appear
        silently (mirroring ADR-0022 §D6's containment test for Continuous
        Improvement, before its own CAP-083C activation).
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "KnowledgeGraphService"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external_consumers: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_KNOWLEDGE_GRAPH_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external_consumers.add(path.relative_to(_REPO_ROOT))
        assert external_consumers == permitted

    def test_dormant_service_is_not_named_outside_the_package(self) -> None:
        """``DormantKnowledgeGraphService`` is an internal implementation detail.

        Only the service module and ``PlatformContext`` construct it; no other
        module needs to know it exists.
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "DormantKnowledgeGraphService"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external_consumers: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_KNOWLEDGE_GRAPH_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external_consumers.add(path.relative_to(_REPO_ROOT))
        assert external_consumers == permitted


@pytest.mark.unit
class TestDependencyBoundaries:
    def test_models_policy_identity_are_self_contained(self) -> None:
        """Canonical models, policy, and identity depend on no Layer 1 subsystem."""
        data_dirs = ("models", "policy", "identity")
        for sub in data_dirs:
            for path in (_KNOWLEDGE_GRAPH_PKG / sub).rglob("*.py"):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith(("import ", "from ")):
                        for token in _LAYER_1_SUBSYSTEMS:
                            assert token not in line, f"{path.name} imports {token}"

    def test_subsystem_imports_no_layer_1_subsystem_at_all(self) -> None:
        """The entire package imports no Layer 1 subsystem — Historical Truth only.

        Knowledge Graph's only upstream concept is ``HistoricalDatasetReference`` —
        a model defined entirely inside this package. No file anywhere in
        ``knowledge_graph`` may import any Layer 1 subsystem (ADR-0021 §Stage 8).
        """
        for path in _KNOWLEDGE_GRAPH_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in _LAYER_1_SUBSYSTEMS:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_subsystem_imports_no_layer_2_peer(self) -> None:
        """Knowledge Graph never imports Continuous Improvement.

        Two Layer 2 capabilities at the same Truth Hierarchy level do not consume
        one another's Derived Knowledge without a deliberate future ADR
        (ADR-0023 §D3, ADR-0021 §Stage 3).
        """
        for path in _KNOWLEDGE_GRAPH_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in _LAYER_2_PEERS:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_subsystem_imports_no_upstream_implementation_classes(self) -> None:
        """The package *imports* no upstream implementation or service class.

        Consumer-only means it never touches engines, orchestrators, builders, or
        services of any Layer 1 subsystem, nor Continuous Improvement's own.
        Docstrings may still name analog classes for explanation; this guard
        watches imports.
        """
        forbidden_impl = (
            "DeterministicRequirementEnhancementEngine",
            "RequirementEnhancementService",
            "EngineeringContextOrchestrator",
            "EngineeringContextBuilder",
            "RequirementAnalysisService",
            "GroundingService",
            "QualityGovernanceService",
            "CP1Service",
            "ResponseValidator",
            "DeterministicRecommendationEngine",
            "DeterministicRecommendationService",
            "DeterministicContinuousImprovementEngine",
            "DeterministicContinuousImprovementService",
        )
        for path in _KNOWLEDGE_GRAPH_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_impl:
                        assert token not in line, f"{path.name} imports {token}"

    def test_service_consumes_only_the_historical_dataset_reference(self) -> None:
        """The service imports HistoricalDatasetReference and nothing heavier."""
        source = (_KNOWLEDGE_GRAPH_PKG / "knowledge_graph_service.py").read_text(encoding="utf-8")
        assert "HistoricalDatasetReference" in source

    def test_no_execution_package_or_pipeline_dependency(self) -> None:
        """The Knowledge Graph Framework never imports the Execution Package or CLI.

        CAP-084A adds no execution artifact and no pipeline wiring — this is the
        structural guarantee that holds until a deliberate future milestone
        changes it.
        """
        forbidden = ("requirement_intelligence.execution", "scripts.run_requirement_analysis")
        for path in _KNOWLEDGE_GRAPH_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}"

    def test_no_serializer_execution_package_or_cli_integration_exists_yet(self) -> None:
        """CAP-084A freezes the contract before any of these exist (Stage 1)."""
        assert not (_KNOWLEDGE_GRAPH_PKG / "serialization").exists()
        assert not any(
            "knowledge_graph" in path.read_text(encoding="utf-8")
            for path in (_REPO_ROOT / "requirement_intelligence" / "execution").rglob("*.py")
        )

    def test_no_engine_module_exists_yet(self) -> None:
        """CAP-084A introduces no engine — the service is abstract and dormant only."""
        assert not (_KNOWLEDGE_GRAPH_PKG / "engine.py").exists()

    def test_no_rules_module_exists_yet(self) -> None:
        """CAP-084A introduces no governed rule catalogue — that is engine-adjacent,
        reserved for a future implementation milestone (mirrors how
        continuous_improvement/rules/ was added only in CAP-083B, not CAP-083A)."""
        assert not (_KNOWLEDGE_GRAPH_PKG / "rules").exists()

    def test_no_historical_dataset_storage_implementation_exists(self) -> None:
        """CAP-084A introduces no Historical Dataset storage of any kind.

        No dedicated storage module exists; ``HistoricalDatasetReference`` remains
        provenance only (ADR-0021 §Stage 6).
        """
        forbidden_names = (
            "historical_dataset_store.py",
            "historical_dataset_repository.py",
            "historical_dataset_provider.py",
        )
        existing = {path.name for path in _KNOWLEDGE_GRAPH_PKG.rglob("*.py")}
        for name in forbidden_names:
            assert name not in existing

    def test_no_graph_storage_implementation_exists(self) -> None:
        """CAP-084A introduces no graph database or query surface (Recommendation 5)."""
        forbidden_names = ("graph_store.py", "graph_database.py", "graph_query.py")
        existing = {path.name for path in _KNOWLEDGE_GRAPH_PKG.rglob("*.py")}
        for name in forbidden_names:
            assert name not in existing
