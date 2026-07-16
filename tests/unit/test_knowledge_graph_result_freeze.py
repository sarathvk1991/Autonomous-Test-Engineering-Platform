"""Architecture-only tests for the CAP-084B.1 KnowledgeGraphResult freeze.

These assert the *runtime contract* invariants — not behaviour (behaviour lives in
``test_knowledge_graph_deterministic_engine.py``). They cover the independent
runtime-contract version, serialization round-trip / immutability / equality, the
explainability invariant (the result is self-contained), and the frozen runtime
boundary (ADR-0023 §D11), mirroring ``test_continuous_improvement_result_freeze.py``
(ADR-0022 §D10), ``test_recommendation_result_freeze.py`` (ADR-0019 §D9),
``test_enhancement_result_freeze.py`` (ADR-0018 §D8), and
``test_quality_assessment_result_freeze.py`` (ADR-0017 §D27).

No runtime behaviour changes with this milestone: these tests exercise the engine
exactly as ``test_knowledge_graph_deterministic_engine.py`` already does, only
through the lens of contract certification rather than dispatch behaviour. Unlike
its CAP-084A predecessor, ``_result()`` now builds through
``DeterministicKnowledgeGraphEngine`` rather than hand-constructing the model,
mirroring how CAP-083B.1 updated Continuous Improvement's own freeze test once its
engine existed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.knowledge_graph.engine import DeterministicKnowledgeGraphEngine
from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeVersion,
    KnowledgeGraphFrameworkVersion,
    KnowledgeGraphResultVersion,
    KnowledgeGraphRuleCatalogVersion,
    KnowledgeGraphRuleVersion,
    KnowledgeNodeVersion,
    KnowledgeObservationVersion,
    KnowledgePolicyVersion,
)
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.result import (
    KNOWLEDGE_GRAPH_RESULT_VERSION,
    KnowledgeGraphResult,
)
from requirement_intelligence.knowledge_graph.policy import default_knowledge_graph_policy
from requirement_intelligence.knowledge_graph.rules import default_knowledge_graph_rule_catalog

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KNOWLEDGE_GRAPH_PKG = _REPO_ROOT / "requirement_intelligence" / "knowledge_graph"
_CONTINUOUS_IMPROVEMENT_PKG = _REPO_ROOT / "requirement_intelligence" / "continuous_improvement"
_FIXED_CLOCK = lambda: datetime(2026, 7, 16, tzinfo=UTC)  # noqa: E731


def _version_field_names(model: type) -> set[str]:
    return {name for name in model.model_fields if "version" in name.lower()}


def _reference(**overrides: object) -> HistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-freeze",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-25",
        execution_count=25,
        history_window=25,
        generated_at=datetime(2026, 7, 16, tzinfo=UTC),
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _result() -> KnowledgeGraphResult:
    engine = DeterministicKnowledgeGraphEngine(
        policy=default_knowledge_graph_policy(),
        rule_catalog=default_knowledge_graph_rule_catalog(),
        clock=_FIXED_CLOCK,
    )
    return engine.build(_reference())


@pytest.mark.unit
class TestRuntimeContractVersion:
    def test_result_version_defaults_to_the_contract_version(self) -> None:
        assert _result().result_version == KNOWLEDGE_GRAPH_RESULT_VERSION

    def test_result_version_is_its_own_type(self) -> None:
        assert isinstance(KNOWLEDGE_GRAPH_RESULT_VERSION, KnowledgeGraphResultVersion)

    def test_runtime_version_is_independent_of_every_other_axis(self) -> None:
        """The runtime-contract version is a distinct type from every other axis."""
        other_axes = (
            KnowledgeGraphFrameworkVersion,
            KnowledgePolicyVersion,
            KnowledgeGraphRuleVersion,
            KnowledgeGraphRuleCatalogVersion,
            KnowledgeNodeVersion,
            KnowledgeEdgeVersion,
            KnowledgeObservationVersion,
        )
        for axis in other_axes:
            assert not issubclass(KnowledgeGraphResultVersion, axis)
            assert not issubclass(axis, KnowledgeGraphResultVersion)
        # Eight distinct types in total (the seven above plus the result version).
        assert len({KnowledgeGraphResultVersion, *other_axes}) == 8

    def test_result_and_policy_versions_are_carried_independently(self) -> None:
        result = _result()
        policy = default_knowledge_graph_policy()
        assert result.result_version == KNOWLEDGE_GRAPH_RESULT_VERSION
        assert result.policy_version == policy.policy_version

    def test_subgraph_has_no_dedicated_version_field(self) -> None:
        """KnowledgeSubgraph carries no version-typed field (by design, not a gap)."""
        from requirement_intelligence.knowledge_graph.models.subgraph import KnowledgeSubgraph

        assert _version_field_names(KnowledgeSubgraph) == set()

    def test_finding_has_no_dedicated_version_field(self) -> None:
        """KnowledgeFinding carries no version-typed field (by design, not a gap)."""
        from requirement_intelligence.knowledge_graph.models.finding import KnowledgeFinding

        assert _version_field_names(KnowledgeFinding) == set()

    def test_metrics_has_no_dedicated_version_field(self) -> None:
        """KnowledgeMetrics carries no version-typed field (by design, not a gap)."""
        from requirement_intelligence.knowledge_graph.models.summary import KnowledgeMetrics

        assert _version_field_names(KnowledgeMetrics) == set()

    def test_summary_carries_only_the_governing_policy_version(self) -> None:
        """KnowledgeSummary's only version field is the policy it was governed by."""
        from requirement_intelligence.knowledge_graph.models.summary import KnowledgeSummary

        assert _version_field_names(KnowledgeSummary) == {"policy_version"}


@pytest.mark.unit
class TestSelfContainedContract:
    def test_round_trips_from_serialization_alone(self) -> None:
        result = _result()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert KnowledgeGraphResult.model_validate(dumped) == result

    def test_deterministic_equality_with_a_fixed_clock(self) -> None:
        assert _result() == _result()

    def test_is_immutable(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.result_id = "other"  # type: ignore[misc]

    def test_explainable_from_the_content_fields_alone(self) -> None:
        """The result carries every field an explanation needs — nothing external."""
        fields = set(KnowledgeGraphResult.model_fields)
        assert {
            "nodes",
            "edges",
            "subgraphs",
            "observations",
            "findings",
            "summary",
            "metrics",
            "historical_dataset",
            "policy_id",
            "policy_version",
        } <= fields

    def test_findings_are_explainable_from_category_severity_subjects_and_message(self) -> None:
        result = _result()
        assert result.findings, "expected the fixed dataset to yield at least one finding"
        for finding in result.findings:
            assert finding.category
            assert finding.severity
            assert finding.subject_node_ids or finding.subject_edge_ids
            assert finding.message

    def test_observations_are_explainable_from_category_subjects_and_description(self) -> None:
        result = _result()
        assert result.observations, "expected the fixed dataset to yield at least one observation"
        for observation in result.observations:
            assert observation.category
            assert observation.subject_node_ids or observation.subject_edge_ids
            assert observation.description

    def test_edges_reference_only_known_nodes(self) -> None:
        result = _result()
        assert result.edges, "expected the fixed dataset to yield at least one edge"
        known_node_ids = {node.node_id for node in result.nodes}
        for edge in result.edges:
            assert edge.source_node_id in known_node_ids
            assert edge.target_node_id in known_node_ids

    def test_subgraphs_reference_only_known_nodes_and_edges(self) -> None:
        result = _result()
        known_node_ids = {node.node_id for node in result.nodes}
        known_edge_ids = {edge.edge_id for edge in result.edges}
        for subgraph in result.subgraphs:
            assert set(subgraph.node_ids) <= known_node_ids
            assert set(subgraph.edge_ids) <= known_edge_ids

    def test_carries_no_report_renderer_or_serialization_fields(self) -> None:
        """It is not a report, Markdown, a renderer, or a serializer (Stage 1 'is not' list)."""
        fields = set(KnowledgeGraphResult.model_fields)
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
        fields = set(KnowledgeGraphResult.model_fields)
        forbidden = {"manifest", "generated_artifacts", "checksums", "cli_args", "command_line"}
        assert not (forbidden & fields)

    def test_carries_no_historical_dataset_storage_fields(self) -> None:
        """It is not the Historical Dataset itself (Stage 1 'is not' list, ADR-0021 §Stage 6)."""
        fields = set(KnowledgeGraphResult.model_fields)
        forbidden = {"executions", "historical_records", "dataset_rows", "raw_dataset"}
        assert not (forbidden & fields)

    def test_carries_no_graph_database_or_query_fields(self) -> None:
        """It is not a graph database or a query surface (Recommendation 12, ADR-0023)."""
        fields = set(KnowledgeGraphResult.model_fields)
        forbidden = {"connection", "query", "cypher", "sparql", "session", "driver"}
        assert not (forbidden & fields)


@pytest.mark.unit
class TestRuntimeBoundary:
    def test_result_model_imports_no_execution_package_or_cli(self) -> None:
        """The runtime contract module never depends on the Execution Package or CLI."""
        source = (_KNOWLEDGE_GRAPH_PKG / "models" / "result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "execution_writer" not in line.lower()
                assert "manifest_builder" not in line.lower()
                assert "scripts" not in line.lower()

    def test_result_model_imports_no_engine_service_provider_rule_or_platform_context(
        self,
    ) -> None:
        """The KnowledgeGraphResult model imports none of its collaborators."""
        source = (_KNOWLEDGE_GRAPH_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "DeterministicKnowledgeGraphEngine",
            "DeterministicKnowledgeGraphService",
            "KnowledgeGraphService",
            "HistoricalDatasetProvider",
            "KnowledgeGraphRuleCatalog",
            "KnowledgeGraphRuleBuilder",
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
        part of this contract (§D11) — that is documentation, not a dependency.
        """
        source = (_KNOWLEDGE_GRAPH_PKG / "models" / "result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "HistoricalDatasetProvider" not in line, (
                    f"result.py imports HistoricalDatasetProvider: {line!r}"
                )

    def test_no_module_outside_the_package_names_the_engine(self) -> None:
        """The engine is named only inside the knowledge_graph package.

        Guards the serialization invariant (§D11) before any Knowledge Graph
        renderer exists: nothing outside the subsystem re-runs node projection,
        edge projection, subgraph detection, observation generation, or finding
        detection.
        """
        needle = "DeterministicKnowledgeGraphEngine"
        permitted: set[Path] = set()
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if "tests" in path.parts or path.is_relative_to(_KNOWLEDGE_GRAPH_PKG):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted

    def test_no_module_outside_the_package_names_the_provider(self) -> None:
        """HistoricalDatasetProvider stays private to the knowledge_graph package.

        ``continuous_improvement/`` is also excluded: that subsystem independently
        defines its own, unrelated private class of the identical, generic name
        ``HistoricalDatasetProvider`` — the same Historical Dataset Resolution
        Principle pattern (ADR-0022 §D9), deliberately replicated per Layer 2
        subsystem, never imported across them (ADR-0023 §D10, mirrored by
        ``test_continuous_improvement_result_freeze.py``'s own symmetric
        exclusion of ``knowledge_graph/``). This guard still catches a real leak:
        an accidental import of *this* package's provider anywhere outside it
        (Continuous Improvement included).
        """
        needle = "HistoricalDatasetProvider"
        permitted: set[Path] = set()
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if (
                "tests" in path.parts
                or path.is_relative_to(_KNOWLEDGE_GRAPH_PKG)
                or path.is_relative_to(_CONTINUOUS_IMPROVEMENT_PKG)
            ):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted

    def test_serializer_honours_the_frozen_projection_only_invariant(self) -> None:
        """CAP-084C's serializer honours the boundary CAP-084B.1 froze before it existed.

        The ``serialization/`` package did not exist when this milestone froze the
        invariant in advance; CAP-084C introduces the serializer and this test
        confirms it computes nothing and imports no runtime implementation.
        """
        serializer_dir = _KNOWLEDGE_GRAPH_PKG / "serialization"
        assert serializer_dir.exists()
        forbidden = (
            "DeterministicKnowledgeGraphEngine",
            "DeterministicKnowledgeGraphService",
            "KnowledgeGraphRuleCatalog",
            "KnowledgeGraphPolicy",
            "HistoricalDatasetProvider",
            "PlatformContext",
        )
        for path in serializer_dir.rglob("*.py"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{path.name} imports {token}: {line!r}"

    def test_platform_context_remains_the_sole_composition_root(self) -> None:
        """Only PlatformContext constructs the framework's governed collaborators externally."""
        needle = "KnowledgeGraphRuleCatalog"
        permitted = {
            Path("requirement_intelligence/platform/platform_context.py"),
        }
        external: set[Path] = set()
        for path in (_REPO_ROOT / "requirement_intelligence").rglob("*.py"):
            if "tests" in path.parts or path.is_relative_to(_KNOWLEDGE_GRAPH_PKG):
                continue
            if needle in path.read_text(encoding="utf-8"):
                external.add(path.relative_to(_REPO_ROOT))
        assert external == permitted


@pytest.mark.unit
class TestNoRuntimeBehaviourChange:
    def test_platform_version_unchanged(self) -> None:
        from requirement_intelligence.platform import platform_metadata

        assert platform_metadata.PLATFORM_VERSION == "1.0.0"

    def test_knowledge_graph_framework_version_unchanged_by_this_milestone(self) -> None:
        from requirement_intelligence.knowledge_graph.version import (
            KNOWLEDGE_GRAPH_FRAMEWORK_VERSION,
        )

        assert str(KNOWLEDGE_GRAPH_FRAMEWORK_VERSION) == "1.0.0"

    def test_knowledge_graph_result_version_unchanged_by_this_milestone(self) -> None:
        assert str(KNOWLEDGE_GRAPH_RESULT_VERSION) == "1.0.0"
