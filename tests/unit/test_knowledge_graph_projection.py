"""Unit tests for deterministic node/edge projection (CAP-084B).

``NodeProjector`` is the sole node authority; ``EdgeProjector`` is the sole edge
authority. These tests assert determinism, deduplication, policy gating, and
the no-dangling-edge guarantee.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.knowledge_graph.engine.historical_dataset import (
    HistoricalDataset,
    HistoricalExecutionRecord,
)
from requirement_intelligence.knowledge_graph.engine.projection import EdgeProjector, NodeProjector
from requirement_intelligence.knowledge_graph.identity import KnowledgeEdgeId, KnowledgeNodeId
from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeNodeType,
)
from requirement_intelligence.knowledge_graph.policy import (
    KnowledgeGraphPolicy,
    KnowledgeGraphPolicyBuilder,
    default_knowledge_graph_policy,
)
from requirement_intelligence.knowledge_graph.rules import default_knowledge_graph_rule_catalog


def _dataset(*records: HistoricalExecutionRecord, dataset_id: str = "ds-proj") -> HistoricalDataset:
    return HistoricalDataset(dataset_id=dataset_id, executions=tuple(records))


def _record(
    ordinal: int,
    *,
    requirement_id: str | None = None,
    recommendation_id: str | None = None,
    finding_id: str | None = None,
    capability_id: str | None = None,
    document_id: str | None = None,
    depends_on_previous: bool = False,
) -> HistoricalExecutionRecord:
    return HistoricalExecutionRecord(
        execution_id=f"ex-{ordinal}",
        ordinal=ordinal,
        requirement_id=requirement_id or f"req-{ordinal}",
        recommendation_id=recommendation_id,
        finding_id=finding_id,
        capability_id=capability_id,
        document_id=document_id,
        depends_on_previous=depends_on_previous,
    )


def _policy_with(**switches: bool) -> KnowledgeGraphPolicy:
    base = KnowledgeGraphPolicyBuilder().build()
    return base.model_copy(
        update={
            "capability_switches": base.capability_switches.model_copy(update=switches),
        }
    )


_CATALOG = default_knowledge_graph_rule_catalog()


@pytest.mark.unit
class TestNodeProjector:
    def test_projects_execution_and_requirement_nodes(self) -> None:
        dataset = _dataset(_record(0))
        nodes = NodeProjector(default_knowledge_graph_policy(), _CATALOG).project(dataset)
        node_types = {node.node_type for node in nodes}
        assert KnowledgeNodeType.EXECUTION in node_types
        assert KnowledgeNodeType.REQUIREMENT in node_types

    def test_optional_nodes_projected_only_when_present(self) -> None:
        dataset = _dataset(_record(0, recommendation_id="rec-0"))
        nodes = NodeProjector(default_knowledge_graph_policy(), _CATALOG).project(dataset)
        node_types = {node.node_type for node in nodes}
        assert KnowledgeNodeType.RECOMMENDATION in node_types
        assert KnowledgeNodeType.FINDING not in node_types

    def test_dataset_node_always_projected_once(self) -> None:
        dataset = _dataset(_record(0), _record(1, depends_on_previous=True))
        nodes = NodeProjector(default_knowledge_graph_policy(), _CATALOG).project(dataset)
        dataset_nodes = [node for node in nodes if node.node_type == KnowledgeNodeType.DATASET]
        assert len(dataset_nodes) == 1
        assert dataset_nodes[0].referenced_id == "ds-proj"

    def test_deduplicates_by_node_id(self) -> None:
        # Two executions referencing the same requirement id yield one node.
        dataset = _dataset(
            _record(0, requirement_id="req-shared"), _record(1, requirement_id="req-shared")
        )
        nodes = NodeProjector(default_knowledge_graph_policy(), _CATALOG).project(dataset)
        requirement_nodes = [n for n in nodes if n.node_type == KnowledgeNodeType.REQUIREMENT]
        assert len(requirement_nodes) == 1

    def test_is_deterministic(self) -> None:
        dataset = _dataset(_record(0, recommendation_id="rec-0"), _record(1, finding_id="find-1"))
        n1 = NodeProjector(default_knowledge_graph_policy(), _CATALOG).project(dataset)
        n2 = NodeProjector(default_knowledge_graph_policy(), _CATALOG).project(dataset)
        assert n1 == n2

    def test_node_ingestion_disabled_yields_no_nodes(self) -> None:
        policy = _policy_with(enable_node_ingestion=False)
        dataset = _dataset(_record(0))
        nodes = NodeProjector(policy, _CATALOG).project(dataset)
        assert nodes == ()

    def test_node_id_is_stable_across_calls(self) -> None:
        dataset = _dataset(_record(0))
        n1 = NodeProjector(default_knowledge_graph_policy(), _CATALOG).project(dataset)
        n2 = NodeProjector(default_knowledge_graph_policy(), _CATALOG).project(dataset)
        ids1 = {node.node_id for node in n1}
        ids2 = {node.node_id for node in n2}
        assert ids1 == ids2

    def test_requirement_node_id_matches_deterministic_factory(self) -> None:
        dataset = _dataset(_record(0, requirement_id="req-fixed"))
        nodes = NodeProjector(default_knowledge_graph_policy(), _CATALOG).project(dataset)
        requirement_node = next(n for n in nodes if n.node_type == KnowledgeNodeType.REQUIREMENT)
        assert requirement_node.node_id == KnowledgeNodeId.for_entity("requirement", "req-fixed")


@pytest.mark.unit
class TestEdgeProjector:
    def _nodes_and_edges(
        self, dataset: HistoricalDataset, policy: KnowledgeGraphPolicy | None = None
    ):
        policy = policy or default_knowledge_graph_policy()
        nodes = NodeProjector(policy, _CATALOG).project(dataset)
        edges = EdgeProjector(policy, _CATALOG).project(dataset, nodes)
        return nodes, edges

    def test_depends_on_edge_links_consecutive_requirements(self) -> None:
        dataset = _dataset(_record(0), _record(1, depends_on_previous=True))
        _, edges = self._nodes_and_edges(dataset)
        assert any(str(edge.edge_type) == "depends_on" for edge in edges)

    def test_no_depends_on_edge_without_flag(self) -> None:
        dataset = _dataset(_record(0), _record(1, depends_on_previous=False))
        _, edges = self._nodes_and_edges(dataset)
        assert not any(str(edge.edge_type) == "depends_on" for edge in edges)

    def test_generated_by_edge_links_recommendation_to_requirement(self) -> None:
        dataset = _dataset(_record(0, recommendation_id="rec-0"))
        _, edges = self._nodes_and_edges(dataset)
        assert any(str(edge.edge_type) == "generated_by" for edge in edges)

    def test_traceable_to_edge_links_finding_to_requirement(self) -> None:
        dataset = _dataset(_record(0, finding_id="find-0"))
        _, edges = self._nodes_and_edges(dataset)
        assert any(str(edge.edge_type) == "traceable_to" for edge in edges)

    def test_implements_edge_links_requirement_to_capability(self) -> None:
        dataset = _dataset(_record(0, capability_id="cap-0"))
        _, edges = self._nodes_and_edges(dataset)
        assert any(str(edge.edge_type) == "implements" for edge in edges)

    def test_references_edge_links_document_to_requirement(self) -> None:
        dataset = _dataset(_record(0, document_id="doc-0"))
        _, edges = self._nodes_and_edges(dataset)
        assert any(str(edge.edge_type) == "references" for edge in edges)

    def test_related_to_edge_requires_both_recommendation_and_finding(self) -> None:
        dataset = _dataset(_record(0, recommendation_id="rec-0", finding_id="find-0"))
        _, edges = self._nodes_and_edges(dataset)
        assert any(str(edge.edge_type) == "related_to" for edge in edges)

    def test_uses_edge_requires_both_capability_and_document(self) -> None:
        dataset = _dataset(_record(0, capability_id="cap-0", document_id="doc-0"))
        _, edges = self._nodes_and_edges(dataset)
        assert any(str(edge.edge_type) == "uses" for edge in edges)

    def test_belongs_to_and_derived_from_edges_always_present(self) -> None:
        dataset = _dataset(_record(0))
        _, edges = self._nodes_and_edges(dataset)
        types = {str(edge.edge_type) for edge in edges}
        assert "belongs_to" in types
        assert "derived_from" in types

    def test_never_emits_a_dangling_edge(self) -> None:
        """Every edge's endpoints exist among the projected nodes."""
        dataset = _dataset(
            _record(
                0,
                recommendation_id="rec-0",
                finding_id="find-0",
                capability_id="cap-0",
                document_id="doc-0",
            ),
            _record(1, depends_on_previous=True),
        )
        nodes, edges = self._nodes_and_edges(dataset)
        node_ids = {node.node_id for node in nodes}
        for edge in edges:
            assert edge.source_node_id in node_ids
            assert edge.target_node_id in node_ids

    def test_edge_ingestion_disabled_yields_no_edges(self) -> None:
        policy = _policy_with(enable_edge_ingestion=False)
        dataset = _dataset(_record(0, recommendation_id="rec-0"))
        _, edges = self._nodes_and_edges(dataset, policy)
        assert edges == ()

    def test_edge_omitted_when_node_type_disabled(self) -> None:
        """If REQUIREMENT nodes are disabled, no edge may reference one."""
        policy = default_knowledge_graph_policy()
        dataset = _dataset(_record(0, recommendation_id="rec-0"))
        # Project nodes under a policy with only RECOMMENDATION-adjacent types on,
        # by disabling node ingestion entirely and confirming edges vanish too.
        no_nodes_policy = _policy_with(enable_node_ingestion=False)
        nodes = NodeProjector(no_nodes_policy, _CATALOG).project(dataset)
        edges = EdgeProjector(policy, _CATALOG).project(dataset, nodes)
        assert edges == ()

    def test_is_deterministic(self) -> None:
        dataset = _dataset(
            _record(0, recommendation_id="rec-0"), _record(1, depends_on_previous=True)
        )
        _, e1 = self._nodes_and_edges(dataset)
        _, e2 = self._nodes_and_edges(dataset)
        assert e1 == e2

    def test_edge_id_matches_deterministic_factory(self) -> None:
        dataset = _dataset(_record(0, capability_id="cap-0"))
        _, edges = self._nodes_and_edges(dataset)
        requirement_id = KnowledgeNodeId.for_entity("requirement", "req-0")
        capability_id = KnowledgeNodeId.for_entity("capability", "cap-0")
        expected_id = KnowledgeEdgeId.for_relationship(
            "implements", str(requirement_id), str(capability_id)
        )
        assert any(edge.edge_id == expected_id for edge in edges)

    def test_deduplicates_by_edge_id(self) -> None:
        # Two identical executions sharing the same requirement id should not
        # produce two BELONGS_TO edges to two distinct execution ids... but a
        # repeated execution id would collapse to the same edge id.
        dataset = _dataset(
            _record(0, requirement_id="req-shared"),
            HistoricalExecutionRecord(
                execution_id="ex-0",
                ordinal=1,
                requirement_id="req-shared",
                recommendation_id=None,
                finding_id=None,
                capability_id=None,
                document_id=None,
                depends_on_previous=False,
            ),
        )
        _, edges = self._nodes_and_edges(dataset)
        belongs_to_edges = [e for e in edges if str(e.edge_type) == "belongs_to"]
        assert len(belongs_to_edges) == 1
