"""Unit tests for the canonical Knowledge Graph Framework models (CAP-084A).

All models are frozen, tuple-backed, camelCase, and compute nothing — every value
in these tests is supplied directly, never derived, because no engine exists yet.
The tests assert immutability, serialization round-trips, and the
cross-referential and explainability invariants the validators enforce (ADR-0023
§D4/§D7).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeId,
    KnowledgeFindingId,
    KnowledgeGraphFrameworkVersion,
    KnowledgeGraphId,
    KnowledgeGraphResultId,
    KnowledgeNodeId,
    KnowledgeObservationId,
    KnowledgePolicyId,
    KnowledgePolicyVersion,
    KnowledgeSubgraphId,
)
from requirement_intelligence.knowledge_graph.models import (
    HistoricalDatasetReference,
    KnowledgeEdge,
    KnowledgeEdgeType,
    KnowledgeFinding,
    KnowledgeFindingCategory,
    KnowledgeGraphResult,
    KnowledgeMetrics,
    KnowledgeNode,
    KnowledgeNodeType,
    KnowledgeObservation,
    KnowledgeObservationCategory,
    KnowledgeSeverity,
    KnowledgeSubgraph,
    KnowledgeSummary,
)

_NOW = datetime(2026, 7, 15, tzinfo=UTC)


def _dataset_ref(**overrides: object) -> HistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-1",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-10",
        execution_count=10,
        history_window=25,
        generated_at=_NOW,
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _node(node_id: KnowledgeNodeId | None = None, referenced_id: str = "req-1") -> KnowledgeNode:
    return KnowledgeNode(
        node_id=node_id or KnowledgeNodeId.for_entity("requirement", referenced_id),
        node_type=KnowledgeNodeType.REQUIREMENT,
        referenced_id=referenced_id,
        label=f"Requirement {referenced_id}",
    )


def _edge(source: KnowledgeNode, target: KnowledgeNode) -> KnowledgeEdge:
    return KnowledgeEdge(
        edge_id=KnowledgeEdgeId.for_relationship(
            "depends_on", str(source.node_id), str(target.node_id)
        ),
        edge_type=KnowledgeEdgeType.DEPENDS_ON,
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        rationale="one requirement depends on the other",
    )


def _subgraph(
    nodes: tuple[KnowledgeNode, ...] = (), edges: tuple[KnowledgeEdge, ...] = ()
) -> KnowledgeSubgraph:
    return KnowledgeSubgraph(
        subgraph_id=KnowledgeSubgraphId.for_ordinal("kg-1", 0),
        label="component partition",
        node_ids=tuple(node.node_id for node in nodes),
        edge_ids=tuple(edge.edge_id for edge in edges),
    )


def _observation(
    subject_node_ids: tuple[KnowledgeNodeId, ...] = (),
    subject_edge_ids: tuple[KnowledgeEdgeId, ...] = (),
) -> KnowledgeObservation:
    return KnowledgeObservation(
        observation_id=KnowledgeObservationId.for_ordinal("kg-1", 0),
        category=KnowledgeObservationCategory.NODE_COVERAGE,
        subject_node_ids=subject_node_ids,
        subject_edge_ids=subject_edge_ids,
        description="every requirement node has at least one edge",
    )


def _finding(
    subject_node_ids: tuple[KnowledgeNodeId, ...] = (),
    subject_edge_ids: tuple[KnowledgeEdgeId, ...] = (),
) -> KnowledgeFinding:
    return KnowledgeFinding(
        finding_id=KnowledgeFindingId.for_ordinal("kg-1", 0),
        category=KnowledgeFindingCategory.ISOLATED_NODE,
        severity=KnowledgeSeverity.WARNING,
        subject_node_ids=subject_node_ids,
        subject_edge_ids=subject_edge_ids,
        message="node has no incident edges",
    )


def _summary(**overrides: object) -> KnowledgeSummary:
    defaults: dict[str, object] = dict(
        policy_id=KnowledgePolicyId("default-knowledge-graph-policy"),
        policy_version=KnowledgePolicyVersion(1, 0, 0),
        total_nodes=1,
        total_edges=0,
        total_subgraphs=0,
        total_observations=0,
        total_findings=1,
        headline="1 node, 0 edges, 1 finding.",
    )
    defaults.update(overrides)
    return KnowledgeSummary(**defaults)  # type: ignore[arg-type]


def _metrics() -> KnowledgeMetrics:
    return KnowledgeMetrics(
        node_count=1,
        edge_count=0,
        subgraph_count=0,
        connected_component_count=1,
        average_degree=0.0,
        orphan_node_count=1,
    )


@pytest.mark.unit
class TestHistoricalDatasetReference:
    def test_valid_reference_constructs(self) -> None:
        ref = _dataset_ref()
        assert ref.dataset_id == "ds-1"

    def test_is_immutable(self) -> None:
        ref = _dataset_ref()
        with pytest.raises(ValidationError):
            ref.dataset_id = "ds-2"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        ref = _dataset_ref()
        dumped = ref.model_dump(mode="json", by_alias=True)
        assert HistoricalDatasetReference.model_validate(dumped) == ref

    def test_execution_count_exceeding_window_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _dataset_ref(execution_count=30, history_window=25)

    def test_execution_count_equal_to_window_accepted(self) -> None:
        ref = _dataset_ref(execution_count=25, history_window=25)
        assert ref.execution_count == 25

    def test_empty_dataset_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _dataset_ref(dataset_id="")

    def test_zero_execution_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _dataset_ref(execution_count=0)


@pytest.mark.unit
class TestKnowledgeNode:
    def test_valid_node_constructs(self) -> None:
        node = _node()
        assert node.referenced_id == "req-1"

    def test_is_immutable(self) -> None:
        node = _node()
        with pytest.raises(ValidationError):
            node.label = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        node = _node()
        dumped = node.model_dump(mode="json", by_alias=True)
        assert KnowledgeNode.model_validate(dumped) == node

    def test_empty_referenced_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            KnowledgeNode(
                node_id=KnowledgeNodeId.for_entity("requirement", "req-1"),
                node_type=KnowledgeNodeType.REQUIREMENT,
                referenced_id="",
                label="Req 1",
            )

    def test_all_nine_node_types_are_governed(self) -> None:
        assert {t.value for t in KnowledgeNodeType} == {
            "requirement",
            "module",
            "component",
            "execution",
            "finding",
            "recommendation",
            "capability",
            "dataset",
            "document",
        }


@pytest.mark.unit
class TestKnowledgeEdge:
    def test_valid_edge_constructs(self) -> None:
        source, target = _node(referenced_id="req-1"), _node(referenced_id="req-2")
        edge = _edge(source, target)
        assert edge.source_node_id == source.node_id
        assert edge.target_node_id == target.node_id

    def test_is_immutable(self) -> None:
        source, target = _node(referenced_id="req-1"), _node(referenced_id="req-2")
        edge = _edge(source, target)
        with pytest.raises(ValidationError):
            edge.rationale = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        source, target = _node(referenced_id="req-1"), _node(referenced_id="req-2")
        edge = _edge(source, target)
        dumped = edge.model_dump(mode="json", by_alias=True)
        assert KnowledgeEdge.model_validate(dumped) == edge

    def test_all_nine_edge_types_are_governed(self) -> None:
        assert {t.value for t in KnowledgeEdgeType} == {
            "depends_on",
            "implements",
            "generated_by",
            "references",
            "traceable_to",
            "derived_from",
            "related_to",
            "belongs_to",
            "uses",
        }


@pytest.mark.unit
class TestKnowledgeSubgraph:
    def test_valid_subgraph_constructs(self) -> None:
        node = _node()
        subgraph = _subgraph(nodes=(node,))
        assert subgraph.node_ids == (node.node_id,)

    def test_is_immutable(self) -> None:
        subgraph = _subgraph()
        with pytest.raises(ValidationError):
            subgraph.label = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        node = _node()
        subgraph = _subgraph(nodes=(node,))
        dumped = subgraph.model_dump(mode="json", by_alias=True)
        assert KnowledgeSubgraph.model_validate(dumped) == subgraph

    def test_empty_subgraph_is_valid(self) -> None:
        subgraph = _subgraph()
        assert subgraph.node_ids == ()
        assert subgraph.edge_ids == ()

    def test_duplicate_node_ids_rejected(self) -> None:
        node = _node()
        with pytest.raises(ValidationError):
            KnowledgeSubgraph(
                subgraph_id=KnowledgeSubgraphId.for_ordinal("kg-1", 0),
                label="dup",
                node_ids=(node.node_id, node.node_id),
                edge_ids=(),
            )

    def test_duplicate_edge_ids_rejected(self) -> None:
        source, target = _node(referenced_id="req-1"), _node(referenced_id="req-2")
        edge = _edge(source, target)
        with pytest.raises(ValidationError):
            KnowledgeSubgraph(
                subgraph_id=KnowledgeSubgraphId.for_ordinal("kg-1", 0),
                label="dup",
                node_ids=(),
                edge_ids=(edge.edge_id, edge.edge_id),
            )


@pytest.mark.unit
class TestKnowledgeObservation:
    def test_valid_observation_constructs(self) -> None:
        node = _node()
        observation = _observation(subject_node_ids=(node.node_id,))
        assert observation.subject_node_ids == (node.node_id,)

    def test_is_immutable(self) -> None:
        observation = _observation()
        with pytest.raises(ValidationError):
            observation.description = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        node = _node()
        observation = _observation(subject_node_ids=(node.node_id,))
        dumped = observation.model_dump(mode="json", by_alias=True)
        assert KnowledgeObservation.model_validate(dumped) == observation

    def test_empty_subjects_is_valid(self) -> None:
        # An observation may concern the whole graph, not a specific node/edge.
        observation = _observation()
        assert observation.subject_node_ids == ()
        assert observation.subject_edge_ids == ()

    def test_all_four_observation_categories_are_governed(self) -> None:
        assert {c.value for c in KnowledgeObservationCategory} == {
            "node_coverage",
            "edge_coverage",
            "lineage_depth",
            "structural_consistency",
        }


@pytest.mark.unit
class TestKnowledgeFinding:
    def test_valid_finding_with_node_reference_constructs(self) -> None:
        node = _node()
        finding = _finding(subject_node_ids=(node.node_id,))
        assert finding.subject_node_ids == (node.node_id,)

    def test_valid_finding_with_edge_reference_constructs(self) -> None:
        source, target = _node(referenced_id="req-1"), _node(referenced_id="req-2")
        edge = _edge(source, target)
        finding = _finding(subject_edge_ids=(edge.edge_id,))
        assert finding.subject_edge_ids == (edge.edge_id,)

    def test_is_immutable(self) -> None:
        node = _node()
        finding = _finding(subject_node_ids=(node.node_id,))
        with pytest.raises(ValidationError):
            finding.message = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        node = _node()
        finding = _finding(subject_node_ids=(node.node_id,))
        dumped = finding.model_dump(mode="json", by_alias=True)
        assert KnowledgeFinding.model_validate(dumped) == finding

    def test_zero_references_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _finding()

    def test_all_six_finding_categories_are_governed(self) -> None:
        assert {c.value for c in KnowledgeFindingCategory} == {
            "isolated_node",
            "broken_lineage",
            "duplicate_edge",
            "orphan_graph",
            "missing_relationship",
            "cycle",
        }

    def test_all_three_severities_are_governed(self) -> None:
        assert {s.value for s in KnowledgeSeverity} == {"info", "warning", "critical"}


@pytest.mark.unit
class TestSummaryAndMetrics:
    def test_summary_round_trips(self) -> None:
        summary = _summary()
        dumped = summary.model_dump(mode="json", by_alias=True)
        assert KnowledgeSummary.model_validate(dumped) == summary

    def test_metrics_round_trips(self) -> None:
        metrics = _metrics()
        dumped = metrics.model_dump(mode="json", by_alias=True)
        assert KnowledgeMetrics.model_validate(dumped) == metrics

    def test_negative_average_degree_rejected(self) -> None:
        with pytest.raises(ValidationError):
            KnowledgeMetrics(
                node_count=1,
                edge_count=0,
                subgraph_count=0,
                connected_component_count=1,
                average_degree=-1.0,
                orphan_node_count=1,
            )

    def test_negative_total_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _summary(total_findings=-1)


@pytest.mark.unit
class TestKnowledgeGraphResult:
    def _build(self, **overrides: object) -> KnowledgeGraphResult:
        node = overrides.pop("_node", None) or _node()
        finding = overrides.pop("_finding", None) or _finding(subject_node_ids=(node.node_id,))
        defaults: dict[str, object] = dict(
            result_id=KnowledgeGraphResultId.for_graph("kg-1"),
            graph_id=KnowledgeGraphId.for_dataset("ds-1"),
            historical_dataset=_dataset_ref(),
            nodes=(node,),
            edges=(),
            subgraphs=(),
            observations=(),
            findings=(finding,),
            summary=_summary(),
            metrics=_metrics(),
            policy_id=KnowledgePolicyId("default-knowledge-graph-policy"),
            policy_version=KnowledgePolicyVersion(1, 0, 0),
            framework_version=KnowledgeGraphFrameworkVersion(1, 0, 0),
            started_at=_NOW,
            completed_at=_NOW,
        )
        defaults.update(overrides)
        return KnowledgeGraphResult(**defaults)  # type: ignore[arg-type]

    def test_valid_result_constructs(self) -> None:
        result = self._build()
        assert result.historical_dataset.dataset_id == "ds-1"

    def test_is_immutable(self) -> None:
        result = self._build()
        with pytest.raises(ValidationError):
            result.result_id = KnowledgeGraphResultId.for_graph("kg-2")  # type: ignore[misc]

    def test_round_trips(self) -> None:
        result = self._build()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert KnowledgeGraphResult.model_validate(dumped) == result

    def test_completed_before_started_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._build(started_at=_NOW, completed_at=_NOW - timedelta(seconds=1))

    def test_empty_result_is_valid(self) -> None:
        result = self._build(
            nodes=(),
            edges=(),
            subgraphs=(),
            observations=(),
            findings=(),
            summary=_summary(
                total_nodes=0,
                total_edges=0,
                total_subgraphs=0,
                total_observations=0,
                total_findings=0,
                headline="Nothing built.",
            ),
        )
        assert result.nodes == ()
        assert result.findings == ()

    def test_duplicate_node_ids_rejected(self) -> None:
        node = _node()
        with pytest.raises(ValidationError):
            self._build(nodes=(node, node), findings=())

    def test_duplicate_edge_ids_rejected(self) -> None:
        source, target = _node(referenced_id="req-1"), _node(referenced_id="req-2")
        edge = _edge(source, target)
        with pytest.raises(ValidationError):
            self._build(nodes=(source, target), edges=(edge, edge), findings=())

    def test_edge_referencing_unknown_source_node_rejected(self) -> None:
        target = _node(referenced_id="req-2")
        stray_edge = KnowledgeEdge(
            edge_id=KnowledgeEdgeId.for_relationship(
                "depends_on", "kn-unknown", str(target.node_id)
            ),
            edge_type=KnowledgeEdgeType.DEPENDS_ON,
            source_node_id=KnowledgeNodeId.for_entity("requirement", "req-unknown"),
            target_node_id=target.node_id,
            rationale="dangling source",
        )
        with pytest.raises(ValidationError):
            self._build(nodes=(target,), edges=(stray_edge,), findings=())

    def test_edge_referencing_unknown_target_node_rejected(self) -> None:
        source = _node(referenced_id="req-1")
        stray_edge = KnowledgeEdge(
            edge_id=KnowledgeEdgeId.for_relationship(
                "depends_on", str(source.node_id), "kn-unknown"
            ),
            edge_type=KnowledgeEdgeType.DEPENDS_ON,
            source_node_id=source.node_id,
            target_node_id=KnowledgeNodeId.for_entity("requirement", "req-unknown"),
            rationale="dangling target",
        )
        with pytest.raises(ValidationError):
            self._build(nodes=(source,), edges=(stray_edge,), findings=())

    def test_subgraph_referencing_unknown_node_rejected(self) -> None:
        stray_subgraph = KnowledgeSubgraph(
            subgraph_id=KnowledgeSubgraphId.for_ordinal("kg-1", 0),
            label="stray",
            node_ids=(KnowledgeNodeId.for_entity("requirement", "req-unknown"),),
            edge_ids=(),
        )
        with pytest.raises(ValidationError):
            self._build(subgraphs=(stray_subgraph,), findings=())

    def test_subgraph_referencing_known_node_accepted(self) -> None:
        node = _node()
        subgraph = _subgraph(nodes=(node,))
        result = self._build(nodes=(node,), subgraphs=(subgraph,), findings=())
        assert result.subgraphs[0].node_ids == (node.node_id,)

    def test_observation_referencing_unknown_node_rejected(self) -> None:
        stray_observation = _observation(
            subject_node_ids=(KnowledgeNodeId.for_entity("requirement", "req-unknown"),)
        )
        with pytest.raises(ValidationError):
            self._build(observations=(stray_observation,), findings=())

    def test_observation_referencing_known_node_accepted(self) -> None:
        node = _node()
        observation = _observation(subject_node_ids=(node.node_id,))
        result = self._build(nodes=(node,), observations=(observation,), findings=())
        assert result.observations[0].subject_node_ids == (node.node_id,)

    def test_finding_referencing_unknown_edge_rejected(self) -> None:
        stray_finding = _finding(
            subject_edge_ids=(
                KnowledgeEdgeId.for_relationship("depends_on", "kn-a", "kn-b"),
            )
        )
        with pytest.raises(ValidationError):
            self._build(findings=(stray_finding,))

    def test_duplicate_subgraph_ids_rejected(self) -> None:
        subgraph = _subgraph()
        with pytest.raises(ValidationError):
            self._build(subgraphs=(subgraph, subgraph), findings=())

    def test_duplicate_observation_ids_rejected(self) -> None:
        observation = _observation()
        with pytest.raises(ValidationError):
            self._build(observations=(observation, observation), findings=())

    def test_duplicate_finding_ids_rejected(self) -> None:
        node = _node()
        finding = _finding(subject_node_ids=(node.node_id,))
        with pytest.raises(ValidationError):
            self._build(nodes=(node,), findings=(finding, finding))
