"""Contract and architecture-boundary tests for ContinuousImprovementService (CAP-083A).

ADR-0022 froze the service boundary — abstract contract, dormant implementation,
PlatformContext registration. These tests assert the permanent contract, the
``PlatformContext`` composition root, and the containment/dependency invariants
(ADR-0022 §D6), mirroring ``test_recommendation_service.py`` (ADR-0019 §D6) as it
stood at CAP-082A, before CAP-082B implemented the engine.

Unlike Recommendation (a Layer 1 peer consumer of five Layer 1 results),
Continuous Improvement is the first Layer 2 capability (ADR-0020) and consumes
Historical Truth only (ADR-0021 §Stage 8) — it imports **no** Layer 1 subsystem
at all, a stricter boundary than any Layer 1 subsystem imposes on its peers.
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.continuous_improvement.continuous_improvement_service import (
    ContinuousImprovementService,
    DormantContinuousImprovementService,
)
from requirement_intelligence.continuous_improvement.policy import (
    ImprovementPolicy,
    default_improvement_policy,
)
from requirement_intelligence.platform.platform_context import PlatformContext

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTINUOUS_IMPROVEMENT_PKG = _REPO_ROOT / "requirement_intelligence" / "continuous_improvement"

#: Every Layer 1 subsystem Continuous Improvement must never import — a stricter
#: boundary than any Layer 1 subsystem imposes on its own peers (ADR-0021 §Stage 8).
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


@pytest.mark.unit
class TestServiceContract:
    def test_service_contract_is_abstract(self) -> None:
        assert issubclass(ContinuousImprovementService, ABC)
        with pytest.raises(TypeError):
            ContinuousImprovementService()  # type: ignore[abstract]

    def test_dormant_service_is_a_continuous_improvement_service(self) -> None:
        service = DormantContinuousImprovementService(policy=default_improvement_policy())
        assert isinstance(service, ContinuousImprovementService)


@pytest.mark.unit
class TestDormantService:
    def test_improve_raises_not_implemented(self) -> None:
        service = PlatformContext().create_continuous_improvement_service()
        with pytest.raises(NotImplementedError):
            service.improve(None)  # type: ignore[arg-type]

    def test_dormant_service_stores_the_policy(self) -> None:
        policy = PlatformContext().create_improvement_policy()
        service = DormantContinuousImprovementService(policy=policy)
        assert service._policy is policy


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_improvement_policy_returns_policy(self) -> None:
        policy = PlatformContext().create_improvement_policy()
        assert isinstance(policy, ImprovementPolicy)

    def test_create_continuous_improvement_service_returns_dormant_service(self) -> None:
        service = PlatformContext().create_continuous_improvement_service()
        assert isinstance(service, ContinuousImprovementService)
        assert isinstance(service, DormantContinuousImprovementService)

    def test_repeated_calls_return_independent_but_equal_policies(self) -> None:
        ctx = PlatformContext()
        assert ctx.create_improvement_policy() == ctx.create_improvement_policy()


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_sanctioned_wiring_points_name_the_service_externally(self) -> None:
        """Outside the continuous_improvement package, only PlatformContext may name it.

        CAP-083A registers the composition root only; no CLI phase, execution
        builder, manifest, or serializer may reference the runtime service, so a
        future dependency cannot appear silently (mirroring ADR-0019 §D6's
        containment test for Recommendation, before its own CAP-082B activation).
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "ContinuousImprovementService"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external_consumers: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_CONTINUOUS_IMPROVEMENT_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external_consumers.add(path.relative_to(_REPO_ROOT))
        assert external_consumers == permitted


@pytest.mark.unit
class TestDependencyBoundaries:
    def test_models_policy_identity_are_self_contained(self) -> None:
        """Canonical models, policy, and identity depend on no other subsystem."""
        data_dirs = ("models", "policy", "identity")
        for sub in data_dirs:
            for path in (_CONTINUOUS_IMPROVEMENT_PKG / sub).rglob("*.py"):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith(("import ", "from ")):
                        for token in _LAYER_1_SUBSYSTEMS:
                            assert token not in line, f"{path.name} imports {token}"

    def test_subsystem_imports_no_layer_1_subsystem_at_all(self) -> None:
        """The entire package imports no Layer 1 subsystem — Historical Truth only.

        Unlike Recommendation (a Layer 1 peer, whose service module legitimately
        imports the five upstream result contracts it consumes), Continuous
        Improvement's only upstream concept is ``HistoricalDatasetReference`` — a
        model defined entirely inside this package. No file anywhere in
        ``continuous_improvement`` may import any Layer 1 subsystem (ADR-0021
        §Stage 8).
        """
        for path in _CONTINUOUS_IMPROVEMENT_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in _LAYER_1_SUBSYSTEMS:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_subsystem_imports_no_upstream_implementation_classes(self) -> None:
        """The package *imports* no upstream implementation or service class.

        Consumer-only means it never touches engines, orchestrators, builders, or
        services of any Layer 1 subsystem. Docstrings may still name analog
        classes for explanation; this guard watches imports.
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
        )
        for path in _CONTINUOUS_IMPROVEMENT_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_impl:
                        assert token not in line, f"{path.name} imports {token}"

    def test_service_consumes_only_the_historical_dataset_reference(self) -> None:
        """The service imports HistoricalDatasetReference and nothing heavier."""
        source = (_CONTINUOUS_IMPROVEMENT_PKG / "continuous_improvement_service.py").read_text(
            encoding="utf-8"
        )
        assert "HistoricalDatasetReference" in source

    def test_no_execution_package_or_pipeline_dependency(self) -> None:
        """The Continuous Improvement Framework never imports the Execution Package or CLI.

        CAP-083A adds no execution artifact and no pipeline wiring (Stage 1
        scope) — this is the structural guarantee that holds until a deliberate
        future milestone changes it.
        """
        forbidden = ("requirement_intelligence.execution", "scripts.run_requirement_analysis")
        for path in _CONTINUOUS_IMPROVEMENT_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}"

    def test_no_serializer_module_exists_yet(self) -> None:
        """CAP-083A introduces no serialization module."""
        assert not (_CONTINUOUS_IMPROVEMENT_PKG / "serialization").exists()

    def test_no_historical_dataset_implementation_exists_yet(self) -> None:
        """CAP-083A introduces no Historical Dataset storage — reference only.

        ``HistoricalDatasetReference`` names a dataset; it never implements one.
        The Historical Dataset's ordering/lineage/retention/indexing/search
        (ADR-0021 §Stage 6) has no owner in this package.
        """
        forbidden_names = ("historical_dataset.py", "historical_dataset_store.py")
        existing = {path.name for path in _CONTINUOUS_IMPROVEMENT_PKG.rglob("*.py")}
        for name in forbidden_names:
            assert name not in existing
