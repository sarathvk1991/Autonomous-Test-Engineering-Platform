"""Unit tests for the dormant QualityGovernanceService and its architecture boundaries.

CAP-080A is a pure architecture freeze: the service is dormant, registered but
unconsumed, and the subsystem is a **consumer only** of the three peer result
contracts. These tests assert the dormant contract, the PlatformContext
registration, and the containment/dependency invariants (ADR-0017).
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.quality_governance import (
    DormantQualityGovernanceService,
    QualityGovernanceService,
    QualityPolicy,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QG_PKG = _REPO_ROOT / "requirement_intelligence" / "quality_governance"


@pytest.mark.unit
class TestDormantService:
    def test_service_contract_is_abstract(self) -> None:
        assert issubclass(QualityGovernanceService, ABC)
        with pytest.raises(TypeError):
            QualityGovernanceService()  # type: ignore[abstract]

    def test_evaluate_is_dormant(self) -> None:
        service = DormantQualityGovernanceService(policy=PlatformContext().create_quality_policy())
        with pytest.raises(NotImplementedError):
            service.evaluate(None, None, None)  # type: ignore[arg-type]

    def test_service_carries_its_governed_policy(self) -> None:
        policy = PlatformContext().create_quality_policy()
        service = DormantQualityGovernanceService(policy=policy)
        assert service.policy == policy


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_quality_policy_returns_policy(self) -> None:
        policy = PlatformContext().create_quality_policy()
        assert isinstance(policy, QualityPolicy)

    def test_create_service_returns_dormant_service(self) -> None:
        service = PlatformContext().create_quality_governance_service()
        assert isinstance(service, QualityGovernanceService)
        assert isinstance(service, DormantQualityGovernanceService)


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_platform_context_names_the_service_externally(self) -> None:
        """Outside the quality_governance package, only PlatformContext may name it.

        The service is a dormant boundary — no pipeline stage, execution builder, or
        CLI path may reference it yet, so a later milestone must consciously wire it
        rather than let an external dependency appear silently.
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "QualityGovernanceService"
        permitted = {Path("requirement_intelligence/platform/platform_context.py")}
        external_consumers: set[Path] = set()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(_QG_PKG):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external_consumers.add(path.relative_to(_REPO_ROOT))
        assert external_consumers == permitted


@pytest.mark.unit
class TestDependencyBoundaries:
    def test_models_policy_identity_are_self_contained(self) -> None:
        """Canonical models, policy, and identity depend on no other subsystem.

        Quality Governance stays self-contained: its data layer imports nothing from
        Grounding, Validation, CP1, Analysis, or Context Orchestration. Only the
        service module may reference the three peer *result contracts* it consumes.
        """
        forbidden_subsystems = (
            "requirement_intelligence.grounding",
            "requirement_intelligence.validation",
            "requirement_intelligence.cp1",
            "requirement_intelligence.analysis",
            "requirement_intelligence.context_orchestration",
        )
        data_dirs = ("models", "policy", "identity")
        for sub in data_dirs:
            for path in (_QG_PKG / sub).rglob("*.py"):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith(("import ", "from ")):
                        for token in forbidden_subsystems:
                            assert token not in line, f"{path.name} imports {token}"

    def test_subsystem_imports_no_implementation_classes(self) -> None:
        """The package *imports* no upstream implementation class — only contracts.

        Consumer-only means it never touches strategies, engines, calculators,
        validators, services, or pipelines of the subsystems it consumes (ADR-0017
        Recommendation 1). It may import only the frozen result contracts. Docstrings
        may still name analog classes for explanation; this guard watches imports.
        """
        forbidden_impl = (
            "GroundingStrategy",
            "GroundingService",
            "GroundingPipeline",
            "SupportClassificationEngine",
            "ConfidenceCalculator",
            "GroundingMetricsBuilder",
            "ResponseValidator",
            "CP1Service",
            "EngineeringContextOrchestrator",
        )
        for path in _QG_PKG.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden_impl:
                        assert token not in line, f"{path.name} imports {token}"

    def test_service_consumes_only_the_three_result_contracts(self) -> None:
        """The service imports the three peer result contracts and nothing heavier."""
        source = (_QG_PKG / "quality_governance_service.py").read_text(encoding="utf-8")
        assert "GroundingResult" in source
        assert "ValidationResult" in source
        assert "CP1Result" in source
