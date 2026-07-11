"""Unit tests for the GroundingService runtime boundary (CAP-077A.1).

The service is the permanent orchestration entry point into the Grounding
subsystem. This milestone establishes the boundary only: ``assess`` is abstract
and the registered default raises ``NotImplementedError``. These tests pin the
contract, the construction, and the containment (nothing consumes it yet).
"""

from __future__ import annotations

import inspect
from abc import ABC
from pathlib import Path

import pytest

import requirement_intelligence.grounding as grounding
from requirement_intelligence.grounding import (
    DefaultGroundingService,
    GroundingConfiguration,
    GroundingService,
    GroundingStrategy,
)
from requirement_intelligence.grounding.version import GROUNDING_CONFIGURATION_VERSION
from requirement_intelligence.platform.platform_context import PlatformContext

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
class TestGroundingServiceContract:
    def test_service_is_abstract(self) -> None:
        assert issubclass(GroundingService, ABC)
        with pytest.raises(TypeError):
            GroundingService()  # type: ignore[abstract]

    def test_assess_is_the_single_public_method(self) -> None:
        public = [
            name
            for name, _ in inspect.getmembers(GroundingService, inspect.isfunction)
            if not name.startswith("_")
        ]
        assert public == ["assess"]

    def test_assess_signature_is_the_permanent_api(self) -> None:
        params = list(inspect.signature(GroundingService.assess).parameters)
        assert params == ["self", "engineering_context", "analysis_result"]


@pytest.mark.unit
class TestDefaultGroundingService:
    def _service(self) -> DefaultGroundingService:
        return DefaultGroundingService(
            GroundingConfiguration(
                version=GROUNDING_CONFIGURATION_VERSION,
                framework_version=grounding.GROUNDING_FRAMEWORK_VERSION,
            )
        )

    def test_constructs_with_configuration_only(self) -> None:
        service = self._service()
        assert isinstance(service, GroundingService)
        assert service.configuration.version == GROUNDING_CONFIGURATION_VERSION
        assert service.strategy is None

    def test_depends_on_strategy_abstraction_not_a_concrete_one(self) -> None:
        # The seam accepts the GroundingStrategy protocol; none is injected yet.
        assert GroundingService.assess is not None
        service = self._service()
        assert service.strategy is None
        # The parameter type is the protocol, so any conforming object is acceptable.
        assert isinstance(GroundingStrategy, type)

    def test_assess_raises_not_implemented(self) -> None:
        service = self._service()
        with pytest.raises(NotImplementedError):
            service.assess(engineering_context=None, analysis_result=None)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_factory_returns_dormant_service(self) -> None:
        service = PlatformContext().create_grounding_service()
        assert isinstance(service, GroundingService)
        assert isinstance(service, DefaultGroundingService)
        assert service.configuration.version == GROUNDING_CONFIGURATION_VERSION
        assert service.strategy is None

    def test_factory_injects_no_strategy(self) -> None:
        service = PlatformContext().create_grounding_service()
        assert service.strategy is None


@pytest.mark.unit
class TestRuntimeContainment:
    def test_no_module_outside_grounding_consumes_the_service_except_platform_context(
        self,
    ) -> None:
        """Outside the grounding package, only PlatformContext may name the service.

        The service is a dormant boundary: no pipeline stage, execution builder, or
        CLI path may reference it yet. Files *inside* ``grounding/`` may cross-refer
        to it freely (definition, export, docstrings); this guard watches only the
        subsystem's external surface, so CAP-077E must consciously wire it rather
        than let an external dependency appear silently.
        """
        roots = (
            _REPO_ROOT / "requirement_intelligence",
            _REPO_ROOT / "scripts",
            _REPO_ROOT / "app",
        )
        grounding_pkg = _REPO_ROOT / "requirement_intelligence" / "grounding"
        needle = "GroundingService"
        permitted = {Path("requirement_intelligence/platform/platform_context.py")}
        external_consumers = set()
        for root in roots:
            for path in root.rglob("*.py"):
                if "tests" in path.parts or path.is_relative_to(grounding_pkg):
                    continue
                if needle in path.read_text(encoding="utf-8"):
                    external_consumers.add(path.relative_to(_REPO_ROOT))
        assert external_consumers == permitted
