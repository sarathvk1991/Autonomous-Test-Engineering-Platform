"""Contract and architecture-boundary tests for RecommendationService (CAP-082A).

ADR-0019 froze the service boundary — abstract contract, dormant implementation,
PlatformContext registration. These tests assert the permanent contract, the
``PlatformContext`` composition root, and the containment/dependency invariants
(ADR-0019 §D6), mirroring ``test_enhancement_service.py`` (ADR-0018 §D6).
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.recommendation.policy import (
    RecommendationPolicy,
    default_recommendation_policy,
)
from requirement_intelligence.recommendation.recommendation_service import (
    DormantRecommendationService,
    RecommendationService,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECOMMENDATION_PKG = _REPO_ROOT / "requirement_intelligence" / "recommendation"


@pytest.mark.unit
class TestServiceContract:
    def test_service_contract_is_abstract(self) -> None:
        assert issubclass(RecommendationService, ABC)
        with pytest.raises(TypeError):
            RecommendationService()  # type: ignore[abstract]

    def test_dormant_service_is_a_recommendation_service(self) -> None:
        service = DormantRecommendationService(policy=default_recommendation_policy())
        assert isinstance(service, RecommendationService)


@pytest.mark.unit
class TestDormantService:
    def test_recommend_raises_not_implemented(self) -> None:
        service = PlatformContext().create_recommendation_service()
        with pytest.raises(NotImplementedError):
            service.recommend(None, None, None, None, None)  # type: ignore[arg-type]

    def test_dormant_service_stores_the_policy(self) -> None:
        policy = PlatformContext().create_recommendation_policy()
        service = DormantRecommendationService(policy=policy)
        assert service._policy is policy


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_recommendation_policy_returns_policy(self) -> None:
        policy = PlatformContext().create_recommendation_policy()
        assert isinstance(policy, RecommendationPolicy)

    def test_create_recommendation_service_returns_dormant_service(self) -> None:
        service = PlatformContext().create_recommendation_service()
        assert isinstance(service, RecommendationService)
        assert isinstance(service, DormantRecommendationService)

    def test_repeated_calls_return_independent_but_equal_policies(self) -> None:
        ctx = PlatformContext()
        assert ctx.create_recommendation_policy() == ctx.create_recommendation_policy()


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_sanctioned_wiring_points_name_the_service_externally(self) -> None:
        """Outside the recommendation package, only PlatformContext may name the service.

        CAP-082A registers the composition root only; no CLI phase, execution
        builder, manifest, or serializer may reference the runtime service, so a
        future dependency cannot appear silently (mirroring ADR-0018 §D6's
        containment test for Requirement Enhancement, before its own CAP-081C
        activation added the CLI as a second permitted seam).
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "RecommendationService"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external_consumers: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_RECOMMENDATION_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external_consumers.add(path.relative_to(_REPO_ROOT))
        assert external_consumers == permitted


@pytest.mark.unit
class TestDependencyBoundaries:
    def test_models_policy_identity_are_self_contained(self) -> None:
        """Canonical models, policy, and identity depend on no other subsystem.

        The Recommendation Framework stays self-contained: its data layer imports
        nothing from Requirement Enhancement, Grounding, Validation, CP1, Quality
        Governance, Analysis, or Context Orchestration. Only the service module may
        reference the five upstream *contracts* it consumes.
        """
        forbidden_subsystems = (
            "requirement_intelligence.enhancement",
            "requirement_intelligence.grounding",
            "requirement_intelligence.validation",
            "requirement_intelligence.cp1",
            "requirement_intelligence.quality_governance",
            "requirement_intelligence.analysis",
            "requirement_intelligence.context_orchestration",
        )
        data_dirs = ("models", "policy", "identity")
        for sub in data_dirs:
            for path in (_RECOMMENDATION_PKG / sub).rglob("*.py"):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith(("import ", "from ")):
                        for token in forbidden_subsystems:
                            assert token not in line, f"{path.name} imports {token}"

    def test_subsystem_imports_no_upstream_implementation_classes(self) -> None:
        """The package *imports* no upstream implementation or service class.

        Consumer-only means it never touches engines, orchestrators, builders, or
        services of the subsystems it consumes (Recommendation 1). It may import
        only the five frozen result contracts. Docstrings may still name analog
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
        )
        for path in _RECOMMENDATION_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_impl:
                        assert token not in line, f"{path.name} imports {token}"

    def test_service_consumes_only_the_five_input_contracts(self) -> None:
        """The service imports the five upstream result contracts and nothing heavier."""
        source = (_RECOMMENDATION_PKG / "recommendation_service.py").read_text(encoding="utf-8")
        for needle in (
            "RequirementEnhancementResult",
            "GroundingResult",
            "ValidationResult",
            "CP1Result",
            "QualityGovernanceResult",
        ):
            assert needle in source

    def test_no_execution_package_or_pipeline_dependency(self) -> None:
        """The Recommendation Framework never imports the Execution Package or the CLI.

        CAP-082A adds no execution artifact and no pipeline wiring (Stage 1 scope)
        — this is the structural guarantee that holds until a deliberate future
        milestone changes it.
        """
        forbidden = ("requirement_intelligence.execution", "scripts.run_requirement_analysis")
        for path in _RECOMMENDATION_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}"

    def test_no_serializer_module_exists_yet(self) -> None:
        """CAP-082A introduces no serialization module (Recommendation 8)."""
        assert not (_RECOMMENDATION_PKG / "serialization").exists()
