"""Contract and architecture-boundary tests for RequirementEnhancementService.

CAP-081A froze the service boundary — abstract contract, PlatformContext
registration. CAP-081B replaces the dormant implementation with
``DeterministicRequirementEnhancementService``. These tests assert the permanent
contract, the ``PlatformContext`` composition root, and the containment/dependency
invariants (ADR-0018 §D6), mirroring ``test_quality_governance_service.py``
(ADR-0017 §D6/§D29). Behavioural coverage of the engine itself lives in
``test_enhancement_engine.py``.
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.enhancement.models.result import RequirementEnhancementResult
from requirement_intelligence.enhancement.policy import EnhancementPolicy
from requirement_intelligence.enhancement.requirement_enhancement_service import (
    DeterministicRequirementEnhancementService,
    RequirementEnhancementService,
)
from requirement_intelligence.platform.platform_context import PlatformContext
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENHANCEMENT_PKG = _REPO_ROOT / "requirement_intelligence" / "enhancement"


@pytest.mark.unit
class TestServiceContract:
    def test_service_contract_is_abstract(self) -> None:
        assert issubclass(RequirementEnhancementService, ABC)
        with pytest.raises(TypeError):
            RequirementEnhancementService()  # type: ignore[abstract]


@pytest.mark.unit
class TestDeterministicService:
    def test_service_delegates_to_the_engine_and_returns_a_real_result(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        ctx = PlatformContext()
        service = ctx.create_requirement_enhancement_service()
        result = service.enhance(pipeline.engineering_context, pipeline.analysis_result)
        assert isinstance(result, RequirementEnhancementResult)
        assert result.analysis_id == pipeline.analysis_result.analysis_id


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_enhancement_policy_returns_policy(self) -> None:
        policy = PlatformContext().create_enhancement_policy()
        assert isinstance(policy, EnhancementPolicy)

    def test_create_service_returns_deterministic_service(self) -> None:
        service = PlatformContext().create_requirement_enhancement_service()
        assert isinstance(service, RequirementEnhancementService)
        assert isinstance(service, DeterministicRequirementEnhancementService)


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_sanctioned_wiring_points_name_the_service_externally(self) -> None:
        """Outside the enhancement package, only the sanctioned seams may name the service.

        CAP-081C consciously wires the service: the composition root
        (``PlatformContext``) constructs it, and the CLI orchestration
        (``run_requirement_analysis.py``) obtains it from there and calls ``enhance``
        (mirroring the Quality Governance activation, ADR-0017 §D30). No other module —
        no execution builder, manifest, or serializer — may reference the runtime
        service, so a future dependency cannot appear silently. The Execution Package
        in particular stays free of the runtime class name: it transports and projects
        the ``RequirementEnhancementResult``, never the service.
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "RequirementEnhancementService"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
            Path("scripts/run_requirement_analysis.py"),
        }
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
