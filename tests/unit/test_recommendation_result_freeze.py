"""Architecture-only tests for the CAP-082B.1 RecommendationResult freeze.

These assert the *runtime contract* invariants — not behaviour (behaviour lives in
``test_recommendation_engine.py``). They cover the independent runtime-contract
version, serialization round-trip / immutability / equality, the explainability
invariant (the result is self-contained), and the frozen runtime vs.
Execution-Package boundary (ADR-0019 §D9), mirroring
``test_enhancement_result_freeze.py`` (ADR-0018 §D8) and
``test_quality_assessment_result_freeze.py`` (ADR-0017 §D27).

No runtime behaviour changes with this milestone: these tests exercise the engine
exactly as ``test_recommendation_engine.py`` already does, only through the lens of
contract certification rather than dispatch behaviour.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.enhancement.models.enums import ObservationCategory
from requirement_intelligence.recommendation.engine import DeterministicRecommendationEngine
from requirement_intelligence.recommendation.identity.recommendation_identity import (
    RecommendationEngineVersion,
    RecommendationFrameworkVersion,
    RecommendationPolicyVersion,
    RecommendationResultVersion,
    RecommendationRuleCatalogVersion,
    RecommendationRuleVersion,
    RecommendationVersion,
)
from requirement_intelligence.recommendation.models.result import (
    RECOMMENDATION_RESULT_VERSION,
    RecommendationResult,
)
from requirement_intelligence.recommendation.policy import default_recommendation_policy
from requirement_intelligence.recommendation.rules import default_recommendation_rule_catalog
from tests.unit.recommendation_helpers import (
    make_cp1_result,
    make_enhancement_finding,
    make_enhancement_result,
    make_grounding_result,
    make_quality_governance_result,
    make_validation_result,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECOMMENDATION_PKG = _REPO_ROOT / "requirement_intelligence" / "recommendation"
_FIXED_CLOCK = lambda: datetime(2026, 1, 1, tzinfo=UTC)  # noqa: E731


def _result() -> RecommendationResult:
    engine = DeterministicRecommendationEngine(
        policy=default_recommendation_policy(),
        rule_catalog=default_recommendation_rule_catalog(),
        clock=_FIXED_CLOCK,
    )
    finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
    return engine.recommend(
        make_enhancement_result(findings=(finding,)),
        make_grounding_result(),
        make_validation_result(),
        make_cp1_result(),
        make_quality_governance_result(),
    )


@pytest.mark.unit
class TestRuntimeContractVersion:
    def test_result_version_defaults_to_the_contract_version(self) -> None:
        assert _result().result_version == RECOMMENDATION_RESULT_VERSION

    def test_result_version_is_its_own_type(self) -> None:
        assert isinstance(RECOMMENDATION_RESULT_VERSION, RecommendationResultVersion)

    def test_runtime_version_is_independent_of_every_other_axis(self) -> None:
        """The runtime-contract version is a distinct type from every other axis."""
        other_axes = (
            RecommendationFrameworkVersion,
            RecommendationPolicyVersion,
            RecommendationRuleVersion,
            RecommendationRuleCatalogVersion,
            RecommendationVersion,
            RecommendationEngineVersion,
        )
        for axis in other_axes:
            assert not issubclass(RecommendationResultVersion, axis)
            assert not issubclass(axis, RecommendationResultVersion)
        # Seven distinct types in total (the six above plus the result version).
        assert len({RecommendationResultVersion, *other_axes}) == 7

    def test_result_and_policy_versions_are_carried_independently(self) -> None:
        result = _result()
        policy = default_recommendation_policy()
        assert result.result_version == RECOMMENDATION_RESULT_VERSION
        assert result.policy_version == policy.policy_version

    def test_recommendation_group_has_no_dedicated_version_field(self) -> None:
        """RecommendationGroup shares the reserved RecommendationVersion axis (by design).

        Confirmed, not newly introduced: no ``group_version`` (or similarly named)
        field exists on the model, and the class carries no version-typed field at
        all — it is versioned only as part of the shared, reserved
        ``RecommendationVersion`` axis (ADR-0019 §D5/§D9).
        """
        from requirement_intelligence.recommendation.models.group import RecommendationGroup

        version_fields = {
            name
            for name, field in RecommendationGroup.model_fields.items()
            if "version" in name.lower()
        }
        assert version_fields == set()

    def test_recommendation_reference_has_no_dedicated_schema_version_type(self) -> None:
        """RecommendationReference records only the *referenced* result's version.

        ``referenced_version`` is a plain string (provenance data), never a typed
        schema-version object of the reference's own shape — mirroring every sibling
        subsystem's atomic finding/issue model.
        """
        from requirement_intelligence.recommendation.models.recommendation import (
            RecommendationReference,
        )

        assert RecommendationReference.model_fields["referenced_version"].annotation is str


@pytest.mark.unit
class TestSelfContainedContract:
    def test_round_trips_from_serialization_alone(self) -> None:
        result = _result()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert RecommendationResult.model_validate(dumped) == result

    def test_deterministic_equality_with_a_fixed_clock(self) -> None:
        assert _result() == _result()

    def test_is_immutable(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.analysis_id = "other"  # type: ignore[misc]

    def test_explainable_from_the_content_fields_alone(self) -> None:
        """The result carries every field an explanation needs — nothing external."""
        fields = set(RecommendationResult.model_fields)
        assert {
            "recommendations",
            "groups",
            "summary",
            "metrics",
            "consumed_inputs",
            "policy_id",
            "policy_version",
        } <= fields

    def test_carries_no_report_renderer_or_serialization_fields(self) -> None:
        """It is not a report, Markdown, a renderer, or a serializer (Stage 1 'is not' list)."""
        fields = set(RecommendationResult.model_fields)
        forbidden = {
            "report",
            "markdown",
            "html",
            "pdf",
            "rendered_report",
            "rendered_summary",
            "json_text",
            "serialized",
        }
        assert not (forbidden & fields)

    def test_carries_no_execution_package_manifest_or_cli_fields(self) -> None:
        """It is not an Execution Package, manifest, or CLI object (Stage 1 'is not' list)."""
        fields = set(RecommendationResult.model_fields)
        forbidden = {"manifest", "generated_artifacts", "checksums", "cli_args", "command_line"}
        assert not (forbidden & fields)


@pytest.mark.unit
class TestRuntimeAndExecutionPackageBoundary:
    def test_result_model_imports_no_execution_package(self) -> None:
        """The runtime contract module never depends on the Execution Package."""
        source = (_RECOMMENDATION_PKG / "models" / "result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "execution" not in line.lower(), f"result.py imports execution: {line!r}"

    def test_result_model_imports_no_engine_service_rule_or_platform_context(self) -> None:
        """The RecommendationResult model imports no engine, service, rule, or context."""
        source = (_RECOMMENDATION_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "DeterministicRecommendationEngine",
            "DeterministicRecommendationService",
            "RecommendationService",
            "RecommendationRuleCatalog",
            "RecommendationRuleBuilder",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"

    def test_no_module_outside_the_package_names_the_engine(self) -> None:
        """The engine is named only inside the recommendation package.

        Guards the serialization invariant (§D9) before any Recommendation
        renderer exists: nothing outside the subsystem re-runs recommendation
        generation.
        """
        needle = "DeterministicRecommendationEngine"
        permitted: set[Path] = set()
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if "tests" in path.parts or path.is_relative_to(_RECOMMENDATION_PKG):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted

    def test_serializer_honours_the_frozen_projection_only_invariant(self) -> None:
        """CAP-082C's serializer honours the boundary CAP-082B.1 froze before it existed.

        The ``serialization/`` package did not exist when this milestone froze the
        invariant in advance; CAP-082C introduces the serializer and this test
        confirms it computes nothing and imports no runtime implementation.
        """
        serializer_dir = _RECOMMENDATION_PKG / "serialization"
        assert serializer_dir.exists()
        forbidden = (
            "DeterministicRecommendationEngine",
            "DeterministicRecommendationService",
            "RecommendationRuleCatalog",
            "RecommendationPolicy",
            "PlatformContext",
        )
        for path in serializer_dir.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_platform_context_remains_the_sole_composition_root(self) -> None:
        """Only PlatformContext constructs the engine's governed collaborators externally."""
        needle = "RecommendationRuleCatalog"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if "tests" in path.parts or path.is_relative_to(_RECOMMENDATION_PKG):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted


@pytest.mark.unit
class TestNoRuntimeBehaviourChange:
    def test_platform_version_unchanged(self) -> None:
        from requirement_intelligence.platform import platform_metadata

        assert platform_metadata.PLATFORM_VERSION == "1.0.0"

    def test_recommendation_framework_version_unchanged_by_this_milestone(self) -> None:
        from requirement_intelligence.recommendation.version import (
            RECOMMENDATION_FRAMEWORK_VERSION,
        )

        assert str(RECOMMENDATION_FRAMEWORK_VERSION) == "1.0.0"

    def test_recommendation_result_version_unchanged_by_this_milestone(self) -> None:
        assert str(RECOMMENDATION_RESULT_VERSION) == "1.0.0"
