"""Architecture-only tests for the CAP-084A KnowledgeGraphResult freeze.

These assert the *runtime contract* invariants — not behaviour (no engine exists
yet, so there is no behaviour to test). They cover the independent runtime-contract
version, serialization round-trip / immutability / equality, the explainability
invariant (the result is self-contained), and the frozen runtime boundary
(ADR-0023 §D3/§D4/§D8), mirroring ``test_continuous_improvement_result_freeze.py``
(ADR-0022 §D10) as it stood before CAP-083B introduced an engine.

Because no engine exists yet, every ``KnowledgeGraphResult`` in these tests is
hand-built directly — the same discipline
``test_continuous_improvement_models.py`` used before CAP-083B existed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeVersion,
    KnowledgeFindingId,
    KnowledgeGraphFrameworkVersion,
    KnowledgeGraphId,
    KnowledgeGraphResultId,
    KnowledgeGraphResultVersion,
    KnowledgeNodeId,
    KnowledgeNodeVersion,
    KnowledgeObservationVersion,
    KnowledgePolicyId,
    KnowledgePolicyVersion,
)
from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeFindingCategory,
    KnowledgeNodeType,
    KnowledgeSeverity,
)
from requirement_intelligence.knowledge_graph.models.finding import KnowledgeFinding
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.result import (
    KNOWLEDGE_GRAPH_RESULT_VERSION,
    KnowledgeGraphResult,
)
from requirement_intelligence.knowledge_graph.models.summary import (
    KnowledgeMetrics,
    KnowledgeSummary,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KNOWLEDGE_GRAPH_PKG = _REPO_ROOT / "requirement_intelligence" / "knowledge_graph"
_NOW = datetime(2026, 7, 15, tzinfo=UTC)


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
        generated_at=_NOW,
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _result() -> KnowledgeGraphResult:
    node = KnowledgeNode(
        node_id=KnowledgeNodeId.for_entity("requirement", "req-1"),
        node_type=KnowledgeNodeType.REQUIREMENT,
        referenced_id="req-1",
        label="Requirement 1",
    )
    finding = KnowledgeFinding(
        finding_id=KnowledgeFindingId.for_ordinal("kg-freeze", 0),
        category=KnowledgeFindingCategory.ISOLATED_NODE,
        severity=KnowledgeSeverity.WARNING,
        subject_node_ids=(node.node_id,),
        subject_edge_ids=(),
        message="node has no incident edges",
    )
    return KnowledgeGraphResult(
        result_id=KnowledgeGraphResultId.for_graph("kg-freeze"),
        graph_id=KnowledgeGraphId.for_dataset("ds-freeze"),
        historical_dataset=_reference(),
        nodes=(node,),
        edges=(),
        subgraphs=(),
        observations=(),
        findings=(finding,),
        summary=KnowledgeSummary(
            policy_id=KnowledgePolicyId("default-knowledge-graph-policy"),
            policy_version=KnowledgePolicyVersion(1, 0, 0),
            total_nodes=1,
            total_edges=0,
            total_subgraphs=0,
            total_observations=0,
            total_findings=1,
            headline="1 node, 1 finding.",
        ),
        metrics=KnowledgeMetrics(
            node_count=1,
            edge_count=0,
            subgraph_count=0,
            connected_component_count=1,
            average_degree=0.0,
            orphan_node_count=1,
        ),
        policy_id=KnowledgePolicyId("default-knowledge-graph-policy"),
        policy_version=KnowledgePolicyVersion(1, 0, 0),
        framework_version=KnowledgeGraphFrameworkVersion(1, 0, 0),
        started_at=_NOW,
        completed_at=_NOW,
    )


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
            KnowledgeNodeVersion,
            KnowledgeEdgeVersion,
            KnowledgeObservationVersion,
        )
        for axis in other_axes:
            assert not issubclass(KnowledgeGraphResultVersion, axis)
            assert not issubclass(axis, KnowledgeGraphResultVersion)
        # Six distinct types in total (the five above plus the result version).
        assert len({KnowledgeGraphResultVersion, *other_axes}) == 6

    def test_result_and_policy_versions_are_carried_independently(self) -> None:
        result = _result()
        assert result.result_version == KNOWLEDGE_GRAPH_RESULT_VERSION
        assert result.policy_version == KnowledgePolicyVersion(1, 0, 0)

    def test_subgraph_has_no_dedicated_version_field(self) -> None:
        """KnowledgeSubgraph carries no version-typed field (by design, not a gap)."""
        from requirement_intelligence.knowledge_graph.models.subgraph import KnowledgeSubgraph

        assert _version_field_names(KnowledgeSubgraph) == set()

    def test_finding_has_no_dedicated_version_field(self) -> None:
        """KnowledgeFinding carries no version-typed field (by design, not a gap)."""
        assert _version_field_names(KnowledgeFinding) == set()

    def test_metrics_has_no_dedicated_version_field(self) -> None:
        """KnowledgeMetrics carries no version-typed field (by design, not a gap)."""
        assert _version_field_names(KnowledgeMetrics) == set()

    def test_summary_carries_only_the_governing_policy_version(self) -> None:
        """KnowledgeSummary's only version field is the policy it was governed by."""
        assert _version_field_names(KnowledgeSummary) == {"policy_version"}


@pytest.mark.unit
class TestSelfContainedContract:
    def test_round_trips_from_serialization_alone(self) -> None:
        result = _result()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert KnowledgeGraphResult.model_validate(dumped) == result

    def test_deterministic_equality(self) -> None:
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
        assert result.findings
        for finding in result.findings:
            assert finding.category
            assert finding.severity
            assert finding.subject_node_ids or finding.subject_edge_ids
            assert finding.message

    def test_edges_reference_only_known_nodes(self) -> None:
        result = _result()
        known_node_ids = {node.node_id for node in result.nodes}
        for edge in result.edges:
            assert edge.source_node_id in known_node_ids
            assert edge.target_node_id in known_node_ids

    def test_carries_no_report_renderer_or_serialization_fields(self) -> None:
        """It is not a report, Markdown, a renderer, or a serializer (Stage 3 'is not' list)."""
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
        """It is not an Execution Package, manifest, or CLI object (Stage 3 'is not' list)."""
        fields = set(KnowledgeGraphResult.model_fields)
        forbidden = {"manifest", "generated_artifacts", "checksums", "cli_args", "command_line"}
        assert not (forbidden & fields)

    def test_carries_no_historical_dataset_storage_fields(self) -> None:
        """It is not the Historical Dataset itself (Stage 3 'is not' list, ADR-0021 §Stage 6)."""
        fields = set(KnowledgeGraphResult.model_fields)
        forbidden = {"executions", "historical_records", "dataset_rows", "raw_dataset"}
        assert not (forbidden & fields)

    def test_carries_no_graph_database_or_query_fields(self) -> None:
        """It is not a graph database or a query surface (Recommendation 5, ADR-0023)."""
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

    def test_result_model_imports_no_service_or_platform_context(self) -> None:
        """The KnowledgeGraphResult model imports none of its collaborators."""
        source = (_KNOWLEDGE_GRAPH_PKG / "models" / "result.py").read_text(encoding="utf-8")
        forbidden = (
            "KnowledgeGraphService",
            "DormantKnowledgeGraphService",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"result.py imports {token}: {line!r}"

    def test_no_serializer_execution_package_or_cli_integration_exists_yet(self) -> None:
        """CAP-084A freezes the contract before any of these exist (Stage 3)."""
        assert not (_KNOWLEDGE_GRAPH_PKG / "serialization").exists()
        assert not any(
            "knowledge_graph" in path.read_text(encoding="utf-8")
            for path in (_REPO_ROOT / "requirement_intelligence" / "execution").rglob("*.py")
        )

    def test_platform_context_remains_the_sole_composition_root(self) -> None:
        """Only PlatformContext constructs the framework's governed policy externally."""
        needle = "KnowledgeGraphPolicy"
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

    def test_knowledge_graph_framework_version_is_the_cap_084a_foundation(self) -> None:
        from requirement_intelligence.knowledge_graph.version import (
            KNOWLEDGE_GRAPH_FRAMEWORK_VERSION,
        )

        assert str(KNOWLEDGE_GRAPH_FRAMEWORK_VERSION) == "1.0.0"

    def test_knowledge_graph_result_version_is_the_cap_084a_foundation(self) -> None:
        assert str(KNOWLEDGE_GRAPH_RESULT_VERSION) == "1.0.0"
