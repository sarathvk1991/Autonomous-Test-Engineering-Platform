"""Unit tests for deterministic summary, metrics, and result assembly (CAP-084B).

``SummaryBuilder`` and ``MetricsBuilder`` each compute their target exactly
once; ``ResultBuilder`` is the only constructor of ``KnowledgeGraphResult``
anywhere in the engine.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from requirement_intelligence.knowledge_graph.engine.builders import (
    MetricsBuilder,
    ResultBuilder,
    SummaryBuilder,
)
from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeId,
    KnowledgeFindingId,
    KnowledgeGraphId,
    KnowledgeGraphResultId,
    KnowledgeNodeId,
    KnowledgeSubgraphId,
)
from requirement_intelligence.knowledge_graph.models.edge import KnowledgeEdge
from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeEdgeType,
    KnowledgeFindingCategory,
    KnowledgeNodeType,
    KnowledgeSeverity,
)
from requirement_intelligence.knowledge_graph.models.finding import KnowledgeFinding
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.subgraph import KnowledgeSubgraph
from requirement_intelligence.knowledge_graph.policy import default_knowledge_graph_policy
from requirement_intelligence.knowledge_graph.version import KNOWLEDGE_GRAPH_FRAMEWORK_VERSION

_NOW = datetime(2026, 7, 15, tzinfo=UTC)


def _node(referenced_id: str) -> KnowledgeNode:
    return KnowledgeNode(
        node_id=KnowledgeNodeId.for_entity("requirement", referenced_id),
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
        rationale="test",
    )


def _finding(node: KnowledgeNode) -> KnowledgeFinding:
    return KnowledgeFinding(
        finding_id=KnowledgeFindingId.for_ordinal("kg-builders", 0),
        category=KnowledgeFindingCategory.ISOLATED_NODE,
        severity=KnowledgeSeverity.WARNING,
        subject_node_ids=(node.node_id,),
        subject_edge_ids=(),
        message="isolated",
    )


def _reference() -> HistoricalDatasetReference:
    return HistoricalDatasetReference(
        dataset_id="ds-builders",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-10",
        execution_count=10,
        history_window=25,
        generated_at=_NOW,
    )


@pytest.mark.unit
class TestSummaryBuilder:
    def test_counts_match_inputs(self) -> None:
        a, b = _node("a"), _node("b")
        edge = _edge(a, b)
        finding = _finding(a)
        summary = SummaryBuilder().build(
            default_knowledge_graph_policy(), (a, b), (edge,), (), (), (finding,)
        )
        assert summary.total_nodes == 2
        assert summary.total_edges == 1
        assert summary.total_subgraphs == 0
        assert summary.total_observations == 0
        assert summary.total_findings == 1

    def test_carries_the_policy_identity(self) -> None:
        policy = default_knowledge_graph_policy()
        summary = SummaryBuilder().build(policy, (), (), (), (), ())
        assert summary.policy_id == policy.policy_id
        assert summary.policy_version == policy.policy_version

    def test_headline_is_nonempty(self) -> None:
        summary = SummaryBuilder().build(default_knowledge_graph_policy(), (), (), (), (), ())
        assert summary.headline

    def test_is_deterministic(self) -> None:
        a = _node("a")
        s1 = SummaryBuilder().build(default_knowledge_graph_policy(), (a,), (), (), (), ())
        s2 = SummaryBuilder().build(default_knowledge_graph_policy(), (a,), (), (), (), ())
        assert s1 == s2


@pytest.mark.unit
class TestMetricsBuilder:
    def test_counts_match_inputs(self) -> None:
        a, b = _node("a"), _node("b")
        edge = _edge(a, b)
        metrics = MetricsBuilder().build((a, b), (edge,), ())
        assert metrics.node_count == 2
        assert metrics.edge_count == 1
        assert metrics.subgraph_count == 0

    def test_average_degree_is_zero_for_empty_graph(self) -> None:
        metrics = MetricsBuilder().build((), (), ())
        assert metrics.average_degree == 0.0

    def test_average_degree_computed_correctly(self) -> None:
        a, b = _node("a"), _node("b")
        edge = _edge(a, b)
        metrics = MetricsBuilder().build((a, b), (edge,), ())
        assert metrics.average_degree == pytest.approx(1.0)

    def test_orphan_node_count(self) -> None:
        a, b, isolated = _node("a"), _node("b"), _node("isolated")
        edge = _edge(a, b)
        metrics = MetricsBuilder().build((a, b, isolated), (edge,), ())
        assert metrics.orphan_node_count == 1

    def test_connected_component_count_matches_subgraph_count(self) -> None:
        a = _node("a")
        subgraph = KnowledgeSubgraph(
            subgraph_id=KnowledgeSubgraphId.for_ordinal("kg-builders", 0),
            label="component",
            node_ids=(a.node_id,),
            edge_ids=(),
        )
        metrics = MetricsBuilder().build((a,), (), (subgraph,))
        assert metrics.connected_component_count == metrics.subgraph_count == 1

    def test_is_deterministic(self) -> None:
        a, b = _node("a"), _node("b")
        edge = _edge(a, b)
        m1 = MetricsBuilder().build((a, b), (edge,), ())
        m2 = MetricsBuilder().build((a, b), (edge,), ())
        assert m1 == m2


@pytest.mark.unit
class TestResultBuilder:
    def test_mints_a_deterministic_graph_scoped_result_id(self) -> None:
        graph_id = KnowledgeGraphId.for_dataset("ds-builders")
        summary = SummaryBuilder().build(default_knowledge_graph_policy(), (), (), (), (), ())
        metrics = MetricsBuilder().build((), (), ())
        result = ResultBuilder().build(
            graph_id=graph_id,
            historical_dataset=_reference(),
            nodes=(),
            edges=(),
            subgraphs=(),
            observations=(),
            findings=(),
            summary=summary,
            metrics=metrics,
            policy=default_knowledge_graph_policy(),
            framework_version=KNOWLEDGE_GRAPH_FRAMEWORK_VERSION,
            started_at=_NOW,
            completed_at=_NOW,
        )
        assert result.result_id == KnowledgeGraphResultId.for_graph(str(graph_id))
        assert result.graph_id == graph_id

    def test_result_carries_all_collaborator_output_verbatim(self) -> None:
        a, b = _node("a"), _node("b")
        edge = _edge(a, b)
        finding = _finding(a)
        graph_id = KnowledgeGraphId.for_dataset("ds-builders")
        summary = SummaryBuilder().build(
            default_knowledge_graph_policy(), (a, b), (edge,), (), (), (finding,)
        )
        metrics = MetricsBuilder().build((a, b), (edge,), ())
        result = ResultBuilder().build(
            graph_id=graph_id,
            historical_dataset=_reference(),
            nodes=(a, b),
            edges=(edge,),
            subgraphs=(),
            observations=(),
            findings=(finding,),
            summary=summary,
            metrics=metrics,
            policy=default_knowledge_graph_policy(),
            framework_version=KNOWLEDGE_GRAPH_FRAMEWORK_VERSION,
            started_at=_NOW,
            completed_at=_NOW,
        )
        assert result.nodes == (a, b)
        assert result.edges == (edge,)
        assert result.findings == (finding,)
        assert result.summary == summary
        assert result.metrics == metrics

    def test_is_deterministic(self) -> None:
        graph_id = KnowledgeGraphId.for_dataset("ds-builders")
        summary = SummaryBuilder().build(default_knowledge_graph_policy(), (), (), (), (), ())
        metrics = MetricsBuilder().build((), (), ())
        kwargs = dict(
            graph_id=graph_id,
            historical_dataset=_reference(),
            nodes=(),
            edges=(),
            subgraphs=(),
            observations=(),
            findings=(),
            summary=summary,
            metrics=metrics,
            policy=default_knowledge_graph_policy(),
            framework_version=KNOWLEDGE_GRAPH_FRAMEWORK_VERSION,
            started_at=_NOW,
            completed_at=_NOW,
        )
        r1 = ResultBuilder().build(**kwargs)
        r2 = ResultBuilder().build(**kwargs)
        assert r1 == r2
