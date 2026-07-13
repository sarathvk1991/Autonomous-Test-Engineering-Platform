"""Architecture-only tests for the CAP-081B.1 RequirementEnhancementResult freeze.

These assert the *runtime contract* invariants — not behaviour (behaviour lives in
``test_enhancement_engine.py``). They cover the independent runtime-contract version,
serialization round-trip / immutability / equality, the explainability invariant (the
result is self-contained), and the frozen runtime vs Execution-Package boundary
(ADR-0018 §D8), mirroring ``test_quality_assessment_result_freeze.py`` (ADR-0017 §D27)
and the ``GroundingResult`` freeze (ADR-0016 §D16).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from requirement_intelligence.enhancement.engine import DeterministicRequirementEnhancementEngine
from requirement_intelligence.enhancement.identity.enhancement_identity import (
    EnhancementEngineVersion,
    EnhancementFrameworkVersion,
    EnhancementPolicyVersion,
    EnhancementResultVersion,
    EnhancementRuleCatalogVersion,
    EnhancementRuleVersion,
    ObservationVersion,
    RelationshipVersion,
)
from requirement_intelligence.enhancement.models.result import (
    ENHANCEMENT_RESULT_VERSION,
    RequirementEnhancementResult,
)
from requirement_intelligence.enhancement.policy import default_enhancement_policy
from requirement_intelligence.enhancement.rules import default_enhancement_rule_catalog
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENHANCEMENT_PKG = _REPO_ROOT / "requirement_intelligence" / "enhancement"
_FIXED_CLOCK = lambda: datetime(2026, 1, 1, tzinfo=UTC)  # noqa: E731


@pytest.fixture(scope="module")
def golden_pipeline(tmp_path_factory: pytest.TempPathFactory) -> Any:
    return _run_golden_pipeline(tmp_path_factory.mktemp("golden-enhancement-freeze"))


def _result(golden_pipeline: Any) -> RequirementEnhancementResult:
    engine = DeterministicRequirementEnhancementEngine(
        policy=default_enhancement_policy(),
        rule_catalog=default_enhancement_rule_catalog(),
        clock=_FIXED_CLOCK,
    )
    return engine.enhance(golden_pipeline.engineering_context, golden_pipeline.analysis_result)


@pytest.mark.unit
class TestRuntimeContractVersion:
    def test_result_version_defaults_to_the_contract_version(self, golden_pipeline: Any) -> None:
        assert _result(golden_pipeline).result_version == ENHANCEMENT_RESULT_VERSION

    def test_result_version_is_its_own_type(self) -> None:
        assert isinstance(ENHANCEMENT_RESULT_VERSION, EnhancementResultVersion)

    def test_runtime_version_is_independent_of_every_other_axis(self) -> None:
        """The runtime-contract version is a distinct type from every other axis."""
        other_axes = (
            EnhancementFrameworkVersion,
            EnhancementPolicyVersion,
            EnhancementRuleVersion,
            EnhancementRuleCatalogVersion,
            EnhancementEngineVersion,
            RelationshipVersion,
            ObservationVersion,
        )
        for axis in other_axes:
            assert not issubclass(EnhancementResultVersion, axis)
            assert not issubclass(axis, EnhancementResultVersion)
        # Eight distinct types in total (the seven above plus the result version).
        assert len({EnhancementResultVersion, *other_axes}) == 8

    def test_result_and_policy_versions_are_carried_independently(
        self, golden_pipeline: Any
    ) -> None:
        result = _result(golden_pipeline)
        policy = default_enhancement_policy()
        assert result.result_version == ENHANCEMENT_RESULT_VERSION
        assert result.policy_version == policy.policy_version


@pytest.mark.unit
class TestSelfContainedContract:
    def test_round_trips_from_serialization_alone(self, golden_pipeline: Any) -> None:
        result = _result(golden_pipeline)
        dumped = result.model_dump(mode="json", by_alias=True)
        assert RequirementEnhancementResult.model_validate(dumped) == result

    def test_deterministic_equality_with_a_fixed_clock(self, golden_pipeline: Any) -> None:
        assert _result(golden_pipeline) == _result(golden_pipeline)

    def test_is_immutable(self, golden_pipeline: Any) -> None:
        result = _result(golden_pipeline)
        with pytest.raises(ValidationError):
            result.analysis_id = "other"  # type: ignore[misc]

    def test_explainable_from_the_six_content_fields_alone(self) -> None:
        """The result carries every field an explanation needs — nothing external."""
        fields = set(RequirementEnhancementResult.model_fields)
        assert {
            "enhanced_requirements",
            "relationship_graph",
            "observations",
            "findings",
            "metrics",
            "summary",
        } <= fields

    def test_carries_no_report_renderer_or_serialization_fields(self) -> None:
        """It is not a report, Markdown, a renderer, or a serializer (Stage 1 'is not' list)."""
        fields = set(RequirementEnhancementResult.model_fields)
        forbidden = {
            "report",
            "markdown",
            "rendered_report",
            "rendered_summary",
            "json_text",
            "serialized",
        }
        assert not (forbidden & fields)

    def test_carries_no_execution_package_or_manifest_fields(self) -> None:
        """It is not an Execution Package object (Stage 1 'is not' list)."""
        fields = set(RequirementEnhancementResult.model_fields)
        assert "manifest" not in fields
        assert "generated_artifacts" not in fields
        assert "checksums" not in fields


@pytest.mark.unit
class TestRuntimeAndExecutionPackageBoundary:
    def test_result_model_imports_no_execution_package(self) -> None:
        """The runtime contract module never depends on the Execution Package."""
        source = (_ENHANCEMENT_PKG / "models" / "result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "execution" not in line.lower(), f"result.py imports execution: {line!r}"

    def test_result_model_imports_no_engine_service_or_policy_builder(self) -> None:
        """The RequirementEnhancementResult model imports no engine, service, or builder."""
        source = (_ENHANCEMENT_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "DeterministicRequirementEnhancementEngine",
            "DeterministicRequirementEnhancementService",
            "RequirementEnhancementService",
            "EnhancementRuleCatalog",
            "EnhancementRuleBuilder",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"

    def test_no_module_outside_the_package_names_the_engine(self) -> None:
        """The engine is named only inside the enhancement package — no serializer exists yet.

        Guards the serialization invariant (§D8) before any Requirement Enhancement
        renderer exists: nothing outside the subsystem re-runs enhancement.
        """
        needle = "DeterministicRequirementEnhancementEngine"
        permitted: set[Path] = set()
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if "tests" in path.parts or path.is_relative_to(_ENHANCEMENT_PKG):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted

    def test_no_serializer_module_exists_yet(self) -> None:
        """No `serialization/` package exists in `enhancement/` — reserved for a later milestone."""
        assert not (_ENHANCEMENT_PKG / "serialization").exists()

    def test_platform_context_remains_the_sole_composition_root(self) -> None:
        """Only PlatformContext constructs the engine's governed collaborators externally."""
        needle = "EnhancementRuleCatalog"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if "tests" in path.parts or path.is_relative_to(_ENHANCEMENT_PKG):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted
