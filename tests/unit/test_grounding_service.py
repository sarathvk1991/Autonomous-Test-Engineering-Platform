"""Unit tests for the GroundingService runtime boundary.

The service is the permanent orchestration entry point into the Grounding subsystem
(CAP-077A.1). Since CAP-077E it delegates ``assess`` to a private pipeline. These tests
pin the abstract contract, the delegation, and the containment (nothing consumes it at
runtime yet).
"""

from __future__ import annotations

import inspect
from abc import ABC
from pathlib import Path

import pytest

from requirement_intelligence.grounding import DefaultGroundingService, GroundingService
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
    def test_delegates_assess_to_its_pipeline(self) -> None:
        class _StubPipeline:
            def __init__(self) -> None:
                self.calls: list[tuple[object, object]] = []

            def execute(self, engineering_context: object, analysis_result: object) -> str:
                self.calls.append((engineering_context, analysis_result))
                return "grounding-result"

        pipeline = _StubPipeline()
        service = DefaultGroundingService(pipeline)  # type: ignore[arg-type]
        assert isinstance(service, GroundingService)
        result = service.assess(engineering_context="ctx", analysis_result="ar")  # type: ignore[arg-type]
        assert result == "grounding-result"
        assert pipeline.calls == [("ctx", "ar")]


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_factory_returns_wired_service(self) -> None:
        service = PlatformContext().create_grounding_service()
        assert isinstance(service, GroundingService)
        assert isinstance(service, DefaultGroundingService)


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
