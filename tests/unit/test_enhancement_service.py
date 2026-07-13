"""Contract and architecture-boundary tests for RequirementEnhancementService (CAP-081A).

CAP-081A freezes the service boundary only — abstract contract, dormant
implementation, PlatformContext registration. These tests assert the permanent
contract, the ``PlatformContext`` composition root, and the containment/dependency
invariants (ADR-0018 §D6), mirroring ``test_quality_governance_service.py``
(ADR-0017 §D6/§D29).
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.enhancement.policy import EnhancementPolicy
from requirement_intelligence.enhancement.requirement_enhancement_service import (
    DormantRequirementEnhancementService,
    RequirementEnhancementService,
)
from requirement_intelligence.platform.platform_context import PlatformContext

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENHANCEMENT_PKG = _REPO_ROOT / "requirement_intelligence" / "enhancement"


@pytest.mark.unit
class TestServiceContract:
    def test_service_contract_is_abstract(self) -> None:
        assert issubclass(RequirementEnhancementService, ABC)
        with pytest.raises(TypeError):
            RequirementEnhancementService()  # type: ignore[abstract]


@pytest.mark.unit
class TestDormantService:
    def test_dormant_service_raises_not_implemented(self) -> None:
        policy = PlatformContext().create_enhancement_policy()
        service = DormantRequirementEnhancementService(policy=policy)
        with pytest.raises(NotImplementedError):
            service.enhance(None, None)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_enhancement_policy_returns_policy(self) -> None:
        policy = PlatformContext().create_enhancement_policy()
        assert isinstance(policy, EnhancementPolicy)

    def test_create_service_returns_dormant_service(self) -> None:
        service = PlatformContext().create_requirement_enhancement_service()
        assert isinstance(service, RequirementEnhancementService)
        assert isinstance(service, DormantRequirementEnhancementService)


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_platform_context_names_the_service_externally(self) -> None:
        """Outside the enhancement package, only PlatformContext may name the service.

        CAP-081A is architecture-only: no CLI phase, execution builder, manifest, or
        serializer references the runtime service yet, so a future dependency cannot
        appear silently before runtime activation is a deliberate decision.
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "RequirementEnhancementService"
        permitted = {Path("requirement_intelligence/platform/platform_context.py")}
        external_consumers: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_ENHANCEMENT_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external_consumers.add(path.relative_to(_REPO_ROOT))
        assert external_consumers == permitted


@pytest.mark.unit
class TestDependencyBoundaries:
    def test_models_policy_identity_are_self_contained(self) -> None:
        """Canonical models, policy, and identity depend on no other subsystem.

        Requirement Enhancement stays self-contained: its data layer imports nothing
        from Grounding, Validation, CP1, Quality Governance, Analysis, or Context
        Orchestration. Only the service module may reference the two upstream
        *contracts* it consumes.
        """
        forbidden_subsystems = (
            "requirement_intelligence.grounding",
            "requirement_intelligence.validation",
            "requirement_intelligence.cp1",
            "requirement_intelligence.quality_governance",
            "requirement_intelligence.analysis",
            "requirement_intelligence.context_orchestration",
        )
        data_dirs = ("models", "policy", "identity")
        for sub in data_dirs:
            for path in (_ENHANCEMENT_PKG / sub).rglob("*.py"):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith(("import ", "from ")):
                        for token in forbidden_subsystems:
                            assert token not in line, f"{path.name} imports {token}"

    def test_subsystem_imports_no_upstream_implementation_classes(self) -> None:
        """The package *imports* no upstream implementation class — only contracts.

        Consumer-only means it never touches orchestrators, builders, or services of
        the subsystems it consumes (Recommendation 1). It may import only the frozen
        input contracts, ``EngineeringContext`` and ``AnalysisResult``. Docstrings may
        still name analog classes for explanation; this guard watches imports.
        """
        forbidden_impl = (
            "EngineeringContextOrchestrator",
            "EngineeringContextBuilder",
            "RequirementAnalysisService",
            "GroundingService",
            "QualityGovernanceService",
            "CP1Service",
            "ResponseValidator",
        )
        for path in _ENHANCEMENT_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_impl:
                        assert token not in line, f"{path.name} imports {token}"

    def test_service_consumes_only_the_two_input_contracts(self) -> None:
        """The service imports the two upstream input contracts and nothing heavier."""
        source = (_ENHANCEMENT_PKG / "requirement_enhancement_service.py").read_text(
            encoding="utf-8"
        )
        assert "EngineeringContext" in source
        assert "AnalysisResult" in source

    def test_no_execution_package_or_pipeline_dependency(self) -> None:
        """Requirement Enhancement never imports the Execution Package or the CLI.

        CAP-081A adds no execution artifact and no pipeline wiring (Stage 1 scope) —
        this is the structural guarantee that holds until a deliberate future
        milestone changes it.
        """
        forbidden = ("requirement_intelligence.execution", "scripts.run_requirement_analysis")
        for path in _ENHANCEMENT_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}"
