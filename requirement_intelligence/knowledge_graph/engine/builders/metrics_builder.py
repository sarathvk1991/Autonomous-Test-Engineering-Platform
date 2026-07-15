"""Deterministic :class:`KnowledgeMetrics` assembly (CAP-084B).

``MetricsBuilder`` computes the metrics **exactly once** per build, from
already-finished nodes, edges, and subgraphs. It recomputes nothing those
collections already recorded — it only counts and derives simple, deterministic
statistics (arithmetic only, no AI, no estimation).
"""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.identity import KnowledgeNodeId
from requirement_intelligence.knowledge_graph.models.edge import KnowledgeEdge
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.subgraph import KnowledgeSubgraph
from requirement_intelligence.knowledge_graph.models.summary import KnowledgeMetrics


class MetricsBuilder:
    """Assemble the one :class:`KnowledgeMetrics` for a build. Computed once."""

    def build(
        self,
        nodes: tuple[KnowledgeNode, ...],
        edges: tuple[KnowledgeEdge, ...],
        subgraphs: tuple[KnowledgeSubgraph, ...],
    ) -> KnowledgeMetrics:
        """Return the deterministic numeric roll-up for this build."""
        node_count = len(nodes)
        edge_count = len(edges)

        degree: dict[KnowledgeNodeId, int] = dict.fromkeys((node.node_id for node in nodes), 0)
        for edge in edges:
            degree[edge.source_node_id] = degree.get(edge.source_node_id, 0) + 1
            degree[edge.target_node_id] = degree.get(edge.target_node_id, 0) + 1

        average_degree = (2 * edge_count / node_count) if node_count else 0.0
        orphan_node_count = sum(1 for value in degree.values() if value == 0)

        return KnowledgeMetrics(
            node_count=node_count,
            edge_count=edge_count,
            subgraph_count=len(subgraphs),
            connected_component_count=len(subgraphs),
            average_degree=average_degree,
            orphan_node_count=orphan_node_count,
        )
