"""Contract and architecture-boundary tests for LearningService (CAP-086A,
ADR-0029).

ADR-0029 froze the service boundary (CAP-086A: abstract contract, dormant
implementation, PlatformContext registration). These tests assert the
permanent contract, the ``PlatformContext`` composition root, and the
containment/dependency invariants (ADR-0029 §D2/§D6/§D7) — including the
deliberate **single-input boundary** (ADR-0028 §Stage 12): unlike
``test_organizational_memory_service.py``, this service must never import
``ContinuousImprovementResult`` or ``KnowledgeGraphResult`` — only
``OrganizationalMemoryResult``, and never that subsystem's own service,
engine, policy, or rule catalogue.

Learning is the fourth and final Layer 2 capability (ADR-0020) and consumes
Organizational Knowledge only (ADR-0028 §Stage 12) — it imports no Layer 1
subsystem, and it never touches a ``HistoricalDatasetReference`` or a
``HistoricalDatasetProvider`` directly, nor either of Organizational Memory's
own Layer 2 peers (Continuous Improvement, Knowledge Graph) directly
(Recommendation 6/7 of ADR-0029).
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.learning.learning_service import (
    DormantLearningService,
    LearningService,
)
from requirement_intelligence.learning.policy import default_learning_policy
from requirement_intelligence.platform.platform_context import PlatformContext

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LEARNING_PKG = _REPO_ROOT / "requirement_intelligence" / "learning"

#: Every Layer 1 subsystem Learning must never import — the same stricter
#: boundary Continuous Improvement, Knowledge Graph, and Organizational
#: Memory already impose on themselves (ADR-0021 §Stage 8).
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

#: Implementation classes Learning may never import directly — it may import
#: the consumed peer's *result model* only, never its engine, service,
#: policy, or rule catalogue, and never either of Organizational Memory's own
#: consumed Layer 2 peers (ADR-0029 §D2/D6).
_FORBIDDEN_PEER_IMPLEMENTATION_TOKENS = (
    "DeterministicOrganizationalMemoryEngine",
    "DeterministicOrganizationalMemoryService",
    "OrganizationalMemoryService",
    "OrganizationalMemoryPolicy",
    "PromotionRuleCatalog",
    "ContinuousImprovementResult",
    "KnowledgeGraphResult",
    "HistoricalDatasetProvider",
    "HistoricalDatasetReference",
)


@pytest.mark.unit
class TestServiceContract:
    def test_service_contract_is_abstract(self) -> None:
        assert issubclass(LearningService, ABC)
        with pytest.raises(TypeError):
            LearningService()  # type: ignore[abstract]

    def test_build_signature_has_exactly_one_parameter(self) -> None:
        import inspect

        signature = inspect.signature(LearningService.build)
        params = [p for p in signature.parameters if p != "self"]
        assert params == ["organizational_memory_result"]


@pytest.mark.unit
class TestDormantService:
    def test_dormant_service_is_constructible(self) -> None:
        service = DormantLearningService()
        assert isinstance(service, LearningService)

    def test_dormant_service_raises_on_build(self) -> None:
        service = DormantLearningService()
        with pytest.raises(NotImplementedError):
            service.build(None)  # type: ignore[arg-type]

    def test_dormant_service_raises_with_explanatory_message(self) -> None:
        service = DormantLearningService()
        with pytest.raises(NotImplementedError, match="architecture-only"):
            service.build(None)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_learning_policy_returns_policy(self) -> None:
        from requirement_intelligence.learning.policy import LearningPolicy

        policy = PlatformContext().create_learning_policy()
        assert isinstance(policy, LearningPolicy)

    def test_create_learning_service_returns_dormant_service(self) -> None:
        service = PlatformContext().create_learning_service()
        assert isinstance(service, LearningService)
        assert isinstance(service, DormantLearningService)

    def test_repeated_calls_return_independent_but_equal_policies(self) -> None:
        ctx = PlatformContext()
        assert ctx.create_learning_policy() == ctx.create_learning_policy()

    def test_platform_context_policy_matches_default(self) -> None:
        assert PlatformContext().create_learning_policy() == default_learning_policy()


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_sanctioned_wiring_points_name_the_service_externally(self) -> None:
        """Outside the learning package, only PlatformContext may name it.

        CAP-086A registers the dormant implementation, but the subsystem
        remains unwired: no CLI phase, execution builder, manifest, or
        serializer may reference the runtime service, so a future dependency
        cannot appear silently (mirroring ADR-0022 §D6/ADR-0023 §D6/ADR-0027
        §D7's containment test, before any of their own runtime activation).
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "LearningService"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external_consumers: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_LEARNING_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external_consumers.add(path.relative_to(_REPO_ROOT))
        assert external_consumers == permitted

    def test_no_serializer_execution_package_or_cli_integration_exists_yet(self) -> None:
        """CAP-086A introduces no serializer or Execution Package integration (Stage 1 scope)."""
        assert not (_LEARNING_PKG / "serialization").exists()
        assert not any(
            "learning" in path.read_text(encoding="utf-8").lower()
            for path in (_REPO_ROOT / "requirement_intelligence" / "execution").rglob("*.py")
        )
        script = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"
        assert "requirement_intelligence.learning" not in script.read_text(encoding="utf-8")


@pytest.mark.unit
class TestDependencyBoundaries:
    def test_subsystem_imports_no_layer_1_subsystem_at_all(self) -> None:
        """Learning's only upstream concept is one Organizational Memory result.

        No file anywhere in ``learning`` may import any Layer 1 subsystem
        (ADR-0021 §Stage 8, ADR-0029 Recommendation 6/7).
        """
        for path in _LEARNING_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in _LAYER_1_SUBSYSTEMS:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_subsystem_never_imports_the_historical_dataset_directly(self) -> None:
        """No HistoricalDatasetReference or HistoricalDatasetProvider is ever imported.

        Learning never resolves a Historical Dataset reference itself, and
        never touches either of Organizational Memory's own consumed Layer 2
        peers — it reaches Historical Truth and Derived Knowledge only
        indirectly, through the one Organizational Knowledge result it
        consumes. Checked over import statements only: prose may
        legitimately *name* these terms to document their absence (e.g. this
        service module's own docstring) — that is documentation, not a
        dependency.
        """
        for path in _LEARNING_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert "HistoricalDatasetReference" not in line, (
                        f"{path.name} imports HistoricalDatasetReference: {line!r}"
                    )
                    assert "HistoricalDatasetProvider" not in line, (
                        f"{path.name} imports HistoricalDatasetProvider: {line!r}"
                    )

    def test_service_imports_no_peer_implementation_class(self) -> None:
        """The service module imports the consumed peer's result *model* only —
        never its engine, service, policy, or rule catalogue, and never
        either of Organizational Memory's own consumed Layer 2 peers."""
        source = (_LEARNING_PKG / "learning_service.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in _FORBIDDEN_PEER_IMPLEMENTATION_TOKENS:
                    assert token not in line, f"service imports {token}: {line!r}"

    def test_service_does_legitimately_import_the_organizational_memory_result_model(
        self,
    ) -> None:
        source = (_LEARNING_PKG / "learning_service.py").read_text(encoding="utf-8")
        assert "OrganizationalMemoryResult" in source

    def test_models_and_policy_are_self_contained(self) -> None:
        """Canonical models, policy, and identity depend on no Layer 1 subsystem
        and no peer implementation class."""
        for sub in ("policy", "identity"):
            for path in (_LEARNING_PKG / sub).rglob("*.py"):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith(("import ", "from ")):
                        for token in _LAYER_1_SUBSYSTEMS + _FORBIDDEN_PEER_IMPLEMENTATION_TOKENS:
                            assert token not in line, f"{path.name} imports {token}"

    def test_models_import_no_layer_1_subsystem_or_forbidden_peer_engine(self) -> None:
        """Every model file except result.py, which legitimately documents (never
        imports) OrganizationalMemoryResult in prose only — result.py itself
        never imports the peer's implementation classes, checked separately
        by TestRuntimeBoundary in test_learning_result_freeze.py."""
        forbidden_tokens = (
            *_LAYER_1_SUBSYSTEMS,
            "OrganizationalMemoryService",
            "DeterministicOrganizationalMemoryEngine",
            "OrganizationalMemoryPolicy",
            "PromotionRuleCatalog",
            "ContinuousImprovementResult",
            "KnowledgeGraphResult",
            "HistoricalDatasetProvider",
            "HistoricalDatasetReference",
        )
        for path in (_LEARNING_PKG / "models").rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_tokens:
                        assert token not in line, f"{path.name} imports {token}"

    def test_identity_module_imports_no_sibling_subsystem_identity(self) -> None:
        """The identity module stays self-contained (ADR-0015 §C precedent)."""
        source = (_LEARNING_PKG / "identity" / "learning_identity.py").read_text(
            encoding="utf-8"
        )
        for token in (
            "continuous_improvement.identity",
            "knowledge_graph.identity",
            "organizational_memory.identity",
        ):
            assert token not in source
