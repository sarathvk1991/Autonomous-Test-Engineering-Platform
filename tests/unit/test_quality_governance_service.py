"""Contract and architecture-boundary tests for the QualityGovernanceService (CAP-080C/D).

CAP-080C activated the service (:class:`DefaultQualityGovernanceService` delegating to a
private :class:`QualityGovernancePipeline`); CAP-080D wired it into the live runtime as the
terminal release authority. These tests assert the permanent contract, the ``PlatformContext``
registration, and the containment/dependency invariants (ADR-0017 §D29/§D30). Orchestration
behaviour is exercised in ``test_quality_governance_pipeline.py``.
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.quality_governance import (
    DefaultQualityGovernanceService,
    QualityGovernanceService,
    QualityPolicy,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_QG_PKG = _REPO_ROOT / "requirement_intelligence" / "quality_governance"


@pytest.mark.unit
class TestServiceContract:
    def test_service_contract_is_abstract(self) -> None:
        assert issubclass(QualityGovernanceService, ABC)
        with pytest.raises(TypeError):
            QualityGovernanceService()  # type: ignore[abstract]


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_create_quality_policy_returns_policy(self) -> None:
        policy = PlatformContext().create_quality_policy()
        assert isinstance(policy, QualityPolicy)

    def test_create_service_returns_default_service(self) -> None:
        service = PlatformContext().create_quality_governance_service()
        assert isinstance(service, QualityGovernanceService)
        assert isinstance(service, DefaultQualityGovernanceService)


@pytest.mark.unit
class TestRuntimeContainment:
    def test_only_sanctioned_wiring_points_name_the_service_externally(self) -> None:
        """Outside the quality_governance package, only the sanctioned seams may name it.

        CAP-080D consciously wires the service: the composition root
        (``PlatformContext``) constructs it, and the CLI orchestration
        (``run_requirement_analysis.py``) obtains it from there and calls ``evaluate``.
        No other module — no execution builder, manifest, serializer, or API route — may
        reference the runtime service, so a future dependency cannot appear silently.
        The Execution Package in particular stays free of the runtime class name
        (Recommendation 3): it transports and projects the ``QualityGovernanceResult``,
        never the service.
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        needle = "QualityGovernanceService"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
            Path("scripts/run_requirement_analysis.py"),
        }
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
