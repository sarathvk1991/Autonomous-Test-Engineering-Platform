"""Contract and architecture-boundary tests for ContinuousImprovementService (CAP-083B).

ADR-0022 froze the service boundary (CAP-083A: abstract contract, dormant
implementation, PlatformContext registration). CAP-083B replaces the dormant
implementation with ``DeterministicContinuousImprovementService``. These tests
assert the permanent contract, the ``PlatformContext`` composition root, and the
containment/dependency invariants (ADR-0022 §D6), mirroring
``test_recommendation_service.py`` (ADR-0019 §D6) as it stood at CAP-082B.

Unlike Recommendation (a Layer 1 peer consumer of five Layer 1 results),
Continuous Improvement is the first Layer 2 capability (ADR-0020) and consumes
Historical Truth only (ADR-0021 §Stage 8) — it imports **no** Layer 1 subsystem
at all, a stricter boundary than any Layer 1 subsystem imposes on its peers.
"""

from __future__ import annotations

from abc import ABC
from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.continuous_improvement.continuous_improvement_service import (
    ContinuousImprovementService,
    DeterministicContinuousImprovementService,
)
from requirement_intelligence.continuous_improvement.models import HistoricalDatasetReference
from requirement_intelligence.continuous_improvement.models.result import (
    ContinuousImprovementResult,
)
from requirement_intelligence.continuous_improvement.policy import (
    ImprovementPolicy,
    default_improvement_policy,
)
from requirement_intelligence.continuous_improvement.rules import default_improvement_rule_catalog
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
        assert issubclass(ContinuousImprovementService, ABC)
        with pytest.raises(TypeError):
            ContinuousImprovementService()  # type: ignore[abstract]


@pytest.mark.unit
class TestDeterministicService:
    def test_service_delegates_to_the_engine_and_returns_a_real_result(self) -> None:
        service = PlatformContext().create_continuous_improvement_service()
        result = service.improve(_reference())
        assert isinstance(result, ContinuousImprovementResult)
        assert result.historical_dataset.dataset_id == "ds-1"

    def test_service_accepts_an_explicit_rule_catalog(self) -> None:
        catalog = default_improvement_rule_catalog()
        service = DeterministicContinuousImprovementService(
            policy=default_improvement_policy(), rule_catalog=catalog
        )
        result = service.improve(_reference())
        assert isinstance(result, ContinuousImprovementResult)


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_improvement_policy_returns_policy(self) -> None:
        policy = PlatformContext().create_improvement_policy()
        assert isinstance(policy, ImprovementPolicy)

    def test_create_improvement_rule_catalog_returns_catalog(self) -> None:
        from requirement_intelligence.continuous_improvement.rules import ImprovementRuleCatalog

        catalog = PlatformContext().create_improvement_rule_catalog()
        assert isinstance(catalog, ImprovementRuleCatalog)

    def test_create_continuous_improvement_service_returns_deterministic_service(self) -> None:
        service = PlatformContext().create_continuous_improvement_service()
        assert isinstance(service, ContinuousImprovementService)
        assert isinstance(service, DeterministicContinuousImprovementService)

    def test_repeated_calls_return_independent_but_equal_policies(self) -> None:
        ctx = PlatformContext()
        assert ctx.create_improvement_policy() == ctx.create_improvement_policy()

    def test_repeated_calls_return_independent_but_equal_catalogs(self) -> None:
        ctx = PlatformContext()
        assert ctx.create_improvement_rule_catalog() == ctx.create_improvement_rule_catalog()


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_sanctioned_wiring_points_name_the_service_externally(self) -> None:
        """Outside the continuous_improvement package, only the sanctioned seams may name it.

        CAP-083C consciously wires the service: the composition root
        (``PlatformContext``) constructs it, and the CLI orchestration
        (``run_requirement_analysis.py``) obtains it from there and calls
        ``improve`` exactly once (mirroring the Recommendation activation, ADR-0019
        §D10). No other module — no execution builder, manifest, or serializer —
        may reference the runtime service, so a future dependency cannot appear
        silently. The Execution Package in particular stays free of the runtime
        class name: it transports and projects the ``ContinuousImprovementResult``,
        never the service.
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "ContinuousImprovementService"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
            Path("scripts/run_requirement_analysis.py"),
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

    def test_engine_is_not_named_outside_the_package(self) -> None:
        """``DeterministicContinuousImprovementEngine`` is an internal implementation detail.

        Only the service module may construct it; ``PlatformContext`` talks to
        the service, never the engine directly (mirrors the enhancement/
        quality-governance/recommendation service-over-engine seam).
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "DeterministicContinuousImprovementEngine"
        external_consumers: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_CONTINUOUS_IMPROVEMENT_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external_consumers.add(path.relative_to(_REPO_ROOT))
        assert external_consumers == set()


@pytest.mark.unit
class TestDependencyBoundaries:
    def test_models_policy_identity_rules_are_self_contained(self) -> None:
        """Canonical models, policy, identity, and rules depend on no other subsystem."""
        data_dirs = ("models", "policy", "identity", "rules")
        for sub in data_dirs:
            for path in (_CONTINUOUS_IMPROVEMENT_PKG / sub).rglob("*.py"):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith(("import ", "from ")):
                        for token in _LAYER_1_SUBSYSTEMS:
                            assert token not in line, f"{path.name} imports {token}"

    def test_subsystem_imports_no_layer_1_subsystem_at_all(self) -> None:
        """The entire package imports no Layer 1 subsystem — Historical Truth only.

        Unlike Recommendation (a Layer 1 peer, whose service/engine legitimately
        import the five upstream result contracts they consume), Continuous
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
        source = (
            _CONTINUOUS_IMPROVEMENT_PKG / "continuous_improvement_service.py"
        ).read_text(encoding="utf-8")
        assert "HistoricalDatasetReference" in source

    def test_engine_consumes_only_the_historical_dataset_reference(self) -> None:
        """The engine imports HistoricalDatasetReference and nothing heavier."""
        source = (_CONTINUOUS_IMPROVEMENT_PKG / "engine.py").read_text(encoding="utf-8")
        assert "HistoricalDatasetReference" in source

    def test_no_execution_package_or_pipeline_dependency(self) -> None:
        """The Continuous Improvement Framework never imports the Execution Package or CLI.

        CAP-083B adds no execution artifact and no pipeline wiring (Stage 1
        scope) — this is the structural guarantee that holds until a deliberate
        future milestone changes it.
        """
        forbidden = ("requirement_intelligence.execution", "scripts.run_requirement_analysis")
        for path in _CONTINUOUS_IMPROVEMENT_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}"

    def test_serializer_honours_the_frozen_projection_only_invariant(self) -> None:
        """CAP-083C's serializer (Recommendation 8's forward-looking invariant) computes nothing.

        The ``serialization/`` package did not exist when CAP-083B.1 froze this
        invariant in advance; CAP-083C introduces the serializer and this test
        confirms it honours the boundary frozen before it existed.
        """
        serializer_dir = _CONTINUOUS_IMPROVEMENT_PKG / "serialization"
        assert serializer_dir.exists()
        forbidden = (
            "DeterministicContinuousImprovementEngine",
            "DeterministicContinuousImprovementService",
            "ImprovementRuleCatalog",
            "ImprovementPolicy",
            "HistoricalDatasetProvider",
            "PlatformContext",
        )
        for path in serializer_dir.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_no_historical_dataset_storage_implementation_exists(self) -> None:
        """CAP-083B introduces no Historical Dataset storage — resolution only.

        The engine's internal ``HistoricalDataset`` / ``HistoricalExecutionRecord``
        are plain, unexported-as-contracts dataclasses resolved fresh on every
        call by ``HistoricalDatasetProvider`` — never persisted, never a runtime
        contract, never crossing this package's boundary (the Historical Dataset
        Resolution Principle, ADR-0022 §D9). No dedicated storage module exists.
        """
        forbidden_names = ("historical_dataset_store.py", "historical_dataset_repository.py")
        existing = {path.name for path in _CONTINUOUS_IMPROVEMENT_PKG.rglob("*.py")}
        for name in forbidden_names:
            assert name not in existing
