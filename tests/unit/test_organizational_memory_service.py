"""Contract and architecture-boundary tests for OrganizationalMemoryService
(CAP-085A, ADR-0027).

ADR-0027 froze the service boundary (CAP-085A: abstract contract, dormant
implementation, PlatformContext registration). These tests assert the
permanent contract, the ``PlatformContext`` composition root, and the
containment/dependency invariants (ADR-0027 §D2/§D6/§D7) — including the
deliberate **fan-in exception** (ADR-0025 §Stage 7/8): unlike
``test_continuous_improvement_service.py`` and ``test_knowledge_graph_service.
py``, this service legitimately imports both Continuous Improvement's and
Knowledge Graph's frozen result *models*, while still importing neither
subsystem's service, engine, policy, or rule catalogue.

Organizational Memory is the third Layer 2 capability (ADR-0020) and consumes
Derived Knowledge only (ADR-0025 §Stage 1) — it imports no Layer 1 subsystem,
and it never touches a ``HistoricalDatasetReference`` or a
``HistoricalDatasetProvider`` directly (Recommendation 7 of ADR-0027).
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.organizational_memory.organizational_memory_service import (
    DormantOrganizationalMemoryService,
    OrganizationalMemoryService,
)
from requirement_intelligence.organizational_memory.policy import (
    default_organizational_memory_policy,
)
from requirement_intelligence.platform.platform_context import PlatformContext

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ORGANIZATIONAL_MEMORY_PKG = _REPO_ROOT / "requirement_intelligence" / "organizational_memory"

#: Every Layer 1 subsystem Organizational Memory must never import — the same
#: stricter boundary Continuous Improvement and Knowledge Graph already
#: impose on themselves (ADR-0021 §Stage 8).
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

#: Implementation classes Organizational Memory may never import directly —
#: it may import the two peers' *result models*, but never their engines,
#: services, policies, or rule catalogues (ADR-0027 §D2/D6).
_FORBIDDEN_PEER_IMPLEMENTATION_TOKENS = (
    "DeterministicContinuousImprovementEngine",
    "DeterministicContinuousImprovementService",
    "ContinuousImprovementService",
    "ImprovementPolicy",
    "ImprovementRuleCatalog",
    "DeterministicKnowledgeGraphEngine",
    "DeterministicKnowledgeGraphService",
    "KnowledgeGraphService",
    "KnowledgeGraphPolicy",
    "KnowledgeGraphRuleCatalog",
    "HistoricalDatasetProvider",
    "HistoricalDatasetReference",
)


@pytest.mark.unit
class TestServiceContract:
    def test_service_contract_is_abstract(self) -> None:
        assert issubclass(OrganizationalMemoryService, ABC)
        with pytest.raises(TypeError):
            OrganizationalMemoryService()  # type: ignore[abstract]

    def test_build_signature_has_exactly_two_parameters(self) -> None:
        import inspect

        signature = inspect.signature(OrganizationalMemoryService.build)
        params = [p for p in signature.parameters if p != "self"]
        assert params == ["continuous_improvement_result", "knowledge_graph_result"]


@pytest.mark.unit
class TestDormantService:
    def test_dormant_service_is_constructible(self) -> None:
        service = DormantOrganizationalMemoryService()
        assert isinstance(service, OrganizationalMemoryService)

    def test_dormant_service_raises_on_build(self) -> None:
        service = DormantOrganizationalMemoryService()
        with pytest.raises(NotImplementedError):
            service.build(None, None)  # type: ignore[arg-type]

    def test_dormant_service_raises_with_explanatory_message(self) -> None:
        service = DormantOrganizationalMemoryService()
        with pytest.raises(NotImplementedError, match="architecture-only"):
            service.build(None, None)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_organizational_memory_policy_returns_policy(self) -> None:
        from requirement_intelligence.organizational_memory.policy import (
            OrganizationalMemoryPolicy,
        )

        policy = PlatformContext().create_organizational_memory_policy()
        assert isinstance(policy, OrganizationalMemoryPolicy)

    def test_create_organizational_memory_service_returns_dormant_service(self) -> None:
        service = PlatformContext().create_organizational_memory_service()
        assert isinstance(service, OrganizationalMemoryService)
        assert isinstance(service, DormantOrganizationalMemoryService)

    def test_repeated_calls_return_independent_but_equal_policies(self) -> None:
        ctx = PlatformContext()
        assert (
            ctx.create_organizational_memory_policy() == ctx.create_organizational_memory_policy()
        )

    def test_platform_context_policy_matches_default(self) -> None:
        assert PlatformContext().create_organizational_memory_policy() == (
            default_organizational_memory_policy()
        )


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_sanctioned_wiring_points_name_the_service_externally(self) -> None:
        """Outside the organizational_memory package, only PlatformContext may name it.

        CAP-085A registers the dormant implementation, but the subsystem
        remains unwired: no CLI phase, execution builder, manifest, or
        serializer may reference the runtime service, so a future dependency
        cannot appear silently (mirroring ADR-0022 §D6/ADR-0023 §D6's
        containment test, before either's own runtime activation).
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "OrganizationalMemoryService"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external_consumers: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_ORGANIZATIONAL_MEMORY_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external_consumers.add(path.relative_to(_REPO_ROOT))
        assert external_consumers == permitted

    def test_no_serializer_execution_package_or_cli_integration_exists_yet(self) -> None:
        """CAP-085A introduces no serializer or Execution Package integration (Stage 1 scope)."""
        assert not (_ORGANIZATIONAL_MEMORY_PKG / "serialization").exists()
        assert not any(
            "organizational_memory" in path.read_text(encoding="utf-8")
            for path in (_REPO_ROOT / "requirement_intelligence" / "execution").rglob("*.py")
        )
        script = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"
        assert "organizational_memory" not in script.read_text(encoding="utf-8")


@pytest.mark.unit
class TestDependencyBoundaries:
    def test_subsystem_imports_no_layer_1_subsystem_at_all(self) -> None:
        """Organizational Memory's only upstream concept is two Layer 2 results.

        No file anywhere in ``organizational_memory`` may import any Layer 1
        subsystem (ADR-0021 §Stage 8, ADR-0027 Recommendation 6/7).
        """
        for path in _ORGANIZATIONAL_MEMORY_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in _LAYER_1_SUBSYSTEMS:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_subsystem_never_imports_the_historical_dataset_directly(self) -> None:
        """No HistoricalDatasetReference or HistoricalDatasetProvider is ever imported.

        Unlike Continuous Improvement and Knowledge Graph, Organizational
        Memory never resolves a Historical Dataset reference itself
        (ADR-0027 §D2, Recommendation 7) — it reaches Historical Truth only
        indirectly, through the two Derived Knowledge results it consumes.
        Checked over import statements only: prose may legitimately *name*
        these terms to document their absence (e.g. this service module's own
        docstring) — that is documentation, not a dependency.
        """
        for path in _ORGANIZATIONAL_MEMORY_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "HistoricalDatasetReference" not in line, (
                        f"{path.name} imports HistoricalDatasetReference: {line!r}"
                    )
                    assert "HistoricalDatasetProvider" not in line, (
                        f"{path.name} imports HistoricalDatasetProvider: {line!r}"
                    )

    def test_service_imports_no_peer_implementation_class(self) -> None:
        """The service module imports the two peers' result *models* only — never
        their engines, services, policies, or rule catalogues."""
        source = (_ORGANIZATIONAL_MEMORY_PKG / "organizational_memory_service.py").read_text(
            encoding="utf-8"
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in _FORBIDDEN_PEER_IMPLEMENTATION_TOKENS:
                    assert token not in line, f"service imports {token}: {line!r}"

    def test_service_does_legitimately_import_both_peer_result_models(self) -> None:
        """The fan-in exception (ADR-0025 §Stage 7/8): both models, by name, are expected."""
        source = (_ORGANIZATIONAL_MEMORY_PKG / "organizational_memory_service.py").read_text(
            encoding="utf-8"
        )
        assert "ContinuousImprovementResult" in source
        assert "KnowledgeGraphResult" in source

    def test_models_and_policy_are_self_contained(self) -> None:
        """Canonical models, policy, and identity depend on no Layer 1 subsystem
        and no peer implementation class."""
        for sub in ("models", "policy", "identity"):
            for path in (_ORGANIZATIONAL_MEMORY_PKG / sub).rglob("*.py"):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith(("import ", "from ")):
                        for token in _LAYER_1_SUBSYSTEMS + _FORBIDDEN_PEER_IMPLEMENTATION_TOKENS:
                            assert token not in line, f"{path.name} imports {token}"

    def test_identity_module_imports_no_sibling_subsystem_identity(self) -> None:
        """The identity module stays self-contained (ADR-0015 §C precedent)."""
        source = (
            _ORGANIZATIONAL_MEMORY_PKG / "identity" / "organizational_memory_identity.py"
        ).read_text(encoding="utf-8")
        for token in ("continuous_improvement.identity", "knowledge_graph.identity"):
            assert token not in source
