"""Architecture-only tests for the CAP-083B.1 ContinuousImprovementResult freeze.

These assert the *runtime contract* invariants — not behaviour (behaviour lives in
``test_continuous_improvement_engine.py``). They cover the independent runtime-contract
version, serialization round-trip / immutability / equality, the explainability
invariant (the result is self-contained), and the frozen runtime boundary
(ADR-0022 §D10), mirroring ``test_recommendation_result_freeze.py`` (ADR-0019 §D9),
``test_enhancement_result_freeze.py`` (ADR-0018 §D8), and
``test_quality_assessment_result_freeze.py`` (ADR-0017 §D27).

No runtime behaviour changes with this milestone: these tests exercise the engine
exactly as ``test_continuous_improvement_engine.py`` already does, only through the
lens of contract certification rather than dispatch behaviour.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.continuous_improvement.engine import (
    DeterministicContinuousImprovementEngine,
)
from requirement_intelligence.continuous_improvement.identity import (
    ContinuousImprovementFrameworkVersion,
    ContinuousImprovementResultVersion,
    ImprovementAssessmentVersion,
    ImprovementEngineVersion,
    ImprovementPolicyVersion,
    ImprovementRuleCatalogVersion,
    ImprovementRuleVersion,
    ImprovementTrendVersion,
)
from requirement_intelligence.continuous_improvement.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.continuous_improvement.models.result import (
    CONTINUOUS_IMPROVEMENT_RESULT_VERSION,
    ContinuousImprovementResult,
)
from requirement_intelligence.continuous_improvement.policy import default_improvement_policy
from requirement_intelligence.continuous_improvement.rules import default_improvement_rule_catalog

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CONTINUOUS_IMPROVEMENT_PKG = _REPO_ROOT / "requirement_intelligence" / "continuous_improvement"
_FIXED_CLOCK = lambda: datetime(2026, 7, 15, tzinfo=UTC)  # noqa: E731


def _reference(**overrides: object) -> HistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-freeze",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-25",
        execution_count=25,
        history_window=25,
        generated_at=datetime(2026, 7, 15, tzinfo=UTC),
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _result() -> ContinuousImprovementResult:
    engine = DeterministicContinuousImprovementEngine(
        policy=default_improvement_policy(),
        rule_catalog=default_improvement_rule_catalog(),
        clock=_FIXED_CLOCK,
    )
    return engine.improve(_reference())


@pytest.mark.unit
class TestRuntimeContractVersion:
    def test_result_version_defaults_to_the_contract_version(self) -> None:
        assert _result().result_version == CONTINUOUS_IMPROVEMENT_RESULT_VERSION

    def test_result_version_is_its_own_type(self) -> None:
        assert isinstance(CONTINUOUS_IMPROVEMENT_RESULT_VERSION, ContinuousImprovementResultVersion)

    def test_runtime_version_is_independent_of_every_other_axis(self) -> None:
        """The runtime-contract version is a distinct type from every other axis."""
        other_axes = (
            ContinuousImprovementFrameworkVersion,
            ImprovementPolicyVersion,
            ImprovementRuleVersion,
            ImprovementRuleCatalogVersion,
            ImprovementTrendVersion,
            ImprovementAssessmentVersion,
            ImprovementEngineVersion,
        )
        for axis in other_axes:
            assert not issubclass(ContinuousImprovementResultVersion, axis)
            assert not issubclass(axis, ContinuousImprovementResultVersion)
        # Eight distinct types in total (the seven above plus the result version).
        assert len({ContinuousImprovementResultVersion, *other_axes}) == 8

    def test_result_and_policy_versions_are_carried_independently(self) -> None:
        result = _result()
        policy = default_improvement_policy()
        assert result.result_version == CONTINUOUS_IMPROVEMENT_RESULT_VERSION
        assert result.policy_version == policy.policy_version

    def test_finding_has_no_dedicated_version_field(self) -> None:
        """ImprovementFinding carries no version-typed field (by design, not a gap)."""
        from requirement_intelligence.continuous_improvement.models.finding import (
            ImprovementFinding,
        )

        version_fields = {
            name
            for name, field in ImprovementFinding.model_fields.items()
            if "version" in name.lower()
        }
        assert version_fields == set()

    def test_trend_has_no_dedicated_schema_version_field(self) -> None:
        """ImprovementTrend shares the reserved ImprovementTrendVersion axis (by design).

        Confirmed, not newly introduced: no ``trend_version`` (or similarly named)
        field exists on the model — it is versioned only as part of the shared,
        reserved ``ImprovementTrendVersion`` axis (ADR-0022 §D5/§D10).
        """
        from requirement_intelligence.continuous_improvement.models.trend import ImprovementTrend

        version_fields = {
            name
            for name, field in ImprovementTrend.model_fields.items()
            if "version" in name.lower()
        }
        assert version_fields == set()

    def test_opportunity_has_no_dedicated_version_field(self) -> None:
        """ImprovementOpportunity carries no version-typed field (by design, not a gap)."""
        from requirement_intelligence.continuous_improvement.models.opportunity import (
            ImprovementOpportunity,
        )

        version_fields = {
            name
            for name, field in ImprovementOpportunity.model_fields.items()
            if "version" in name.lower()
        }
        assert version_fields == set()


@pytest.mark.unit
class TestSelfContainedContract:
    def test_round_trips_from_serialization_alone(self) -> None:
        result = _result()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert ContinuousImprovementResult.model_validate(dumped) == result

    def test_deterministic_equality_with_a_fixed_clock(self) -> None:
        assert _result() == _result()

    def test_is_immutable(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.result_id = "other"  # type: ignore[misc]

    def test_explainable_from_the_content_fields_alone(self) -> None:
        """The result carries every field an explanation needs — nothing external."""
        fields = set(ContinuousImprovementResult.model_fields)
        assert {
            "findings",
            "trends",
            "opportunities",
            "summary",
            "metrics",
            "historical_dataset",
            "policy_id",
            "policy_version",
        } <= fields

    def test_findings_are_explainable_from_category_severity_count_ids_and_message(self) -> None:
        result = _result()
        assert result.findings, "expected the fixed dataset to yield at least one finding"
        for finding in result.findings:
            assert finding.category
            assert finding.severity
            assert finding.occurrence_count >= 1
            assert len(finding.contributing_execution_ids) == finding.occurrence_count
            assert finding.message

    def test_trends_are_explainable_from_direction_metric_count_and_ids(self) -> None:
        result = _result()
        assert result.trends, "expected the fixed dataset to yield at least one trend"
        for trend in result.trends:
            assert trend.direction
            assert trend.metric_name
            assert trend.observation_count >= 2
            assert len(trend.contributing_execution_ids) == trend.observation_count

    def test_opportunities_reference_only_findings_or_trends(self) -> None:
        result = _result()
        for opportunity in result.opportunities:
            assert opportunity.source_finding_ids or opportunity.source_trend_ids
            known_finding_ids = {finding.finding_id for finding in result.findings}
            known_trend_ids = {trend.trend_id for trend in result.trends}
            assert set(opportunity.source_finding_ids) <= known_finding_ids
            assert set(opportunity.source_trend_ids) <= known_trend_ids

    def test_carries_no_report_renderer_or_serialization_fields(self) -> None:
        """It is not a report, Markdown, a renderer, or a serializer (Stage 1 'is not' list)."""
        fields = set(ContinuousImprovementResult.model_fields)
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
        fields = set(ContinuousImprovementResult.model_fields)
        forbidden = {"manifest", "generated_artifacts", "checksums", "cli_args", "command_line"}
        assert not (forbidden & fields)

    def test_carries_no_historical_dataset_storage_fields(self) -> None:
        """It is not the Historical Dataset itself (Stage 1 'is not' list, ADR-0021 §Stage 6)."""
        fields = set(ContinuousImprovementResult.model_fields)
        forbidden = {"executions", "historical_records", "dataset_rows", "raw_dataset"}
        assert not (forbidden & fields)


@pytest.mark.unit
class TestRuntimeBoundary:
    def test_result_model_imports_no_execution_package_or_cli(self) -> None:
        """The runtime contract module never depends on the Execution Package or CLI."""
        source = (_CONTINUOUS_IMPROVEMENT_PKG / "models" / "result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "execution_writer" not in line.lower()
                assert "manifest_builder" not in line.lower()
                assert "scripts" not in line.lower()

    def test_result_model_imports_no_engine_service_provider_rule_or_platform_context(
        self,
    ) -> None:
        """The ContinuousImprovementResult model imports none of its collaborators."""
        source = (_CONTINUOUS_IMPROVEMENT_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "DeterministicContinuousImprovementEngine",
            "DeterministicContinuousImprovementService",
            "ContinuousImprovementService",
            "HistoricalDatasetProvider",
            "ImprovementRuleCatalog",
            "ImprovementRuleBuilder",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"

    def test_historical_dataset_provider_is_not_imported_into_result(self) -> None:
        """HistoricalDatasetProvider must never cross into the runtime contract module.

        Checked over import statements only: the module's docstring legitimately
        *names* ``HistoricalDatasetProvider`` in prose to document that it is not
        part of this contract (§D10) — that is documentation, not a dependency.
        """
        source = (_CONTINUOUS_IMPROVEMENT_PKG / "models" / "result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "HistoricalDatasetProvider" not in line, (
                    f"result.py imports HistoricalDatasetProvider: {line!r}"
                )

    def test_no_module_outside_the_package_names_the_engine(self) -> None:
        """The engine is named only inside the continuous_improvement package.

        Guards the serialization invariant (§D10) before any Continuous
        Improvement renderer exists: nothing outside the subsystem re-runs
        recurrence detection, trend detection, or opportunity generation.
        """
        needle = "DeterministicContinuousImprovementEngine"
        permitted: set[Path] = set()
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if "tests" in path.parts or path.is_relative_to(_CONTINUOUS_IMPROVEMENT_PKG):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted

    def test_no_module_outside_the_package_names_the_provider(self) -> None:
        """HistoricalDatasetProvider stays private to the continuous_improvement package.

        ``knowledge_graph/`` is also excluded: CAP-084B independently reuses the
        identical, generic ``HistoricalDatasetProvider`` name for its own,
        unrelated private class — the same Historical Dataset Resolution
        Principle pattern (ADR-0022 §D9), deliberately replicated per Layer 2
        subsystem, never imported across them (ADR-0023 §D9). This guard still
        catches a real leak: an accidental import of *this* package's provider
        anywhere outside it (Knowledge Graph included).
        """
        needle = "HistoricalDatasetProvider"
        knowledge_graph_pkg = _REPO_ROOT / "requirement_intelligence" / "knowledge_graph"
        permitted: set[Path] = set()
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if (
                "tests" in path.parts
                or path.is_relative_to(_CONTINUOUS_IMPROVEMENT_PKG)
                or path.is_relative_to(knowledge_graph_pkg)
            ):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted

    def test_serializer_honours_the_frozen_projection_only_invariant(self) -> None:
        """CAP-083C's serializer honours the boundary CAP-083B.1 froze before it existed.

        The ``serialization/`` package did not exist when this milestone froze the
        invariant in advance; CAP-083C introduces the serializer and this test
        confirms it computes nothing and imports no runtime implementation.
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

    def test_platform_context_remains_the_sole_composition_root(self) -> None:
        """Only PlatformContext constructs the engine's governed collaborators externally."""
        needle = "ImprovementRuleCatalog"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if "tests" in path.parts or path.is_relative_to(_CONTINUOUS_IMPROVEMENT_PKG):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted


@pytest.mark.unit
class TestNoRuntimeBehaviourChange:
    def test_platform_version_unchanged(self) -> None:
        from requirement_intelligence.platform import platform_metadata

        assert platform_metadata.PLATFORM_VERSION == "1.0.0"

    def test_continuous_improvement_framework_version_unchanged_by_this_milestone(self) -> None:
        from requirement_intelligence.continuous_improvement.version import (
            CONTINUOUS_IMPROVEMENT_FRAMEWORK_VERSION,
        )

        assert str(CONTINUOUS_IMPROVEMENT_FRAMEWORK_VERSION) == "1.0.0"

    def test_continuous_improvement_result_version_unchanged_by_this_milestone(self) -> None:
        assert str(CONTINUOUS_IMPROVEMENT_RESULT_VERSION) == "1.0.0"
