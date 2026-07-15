"""Deterministic connected-component detection (CAP-084B).

``SubgraphDetector`` is the **sole subgraph authority**: it is the only
component that partitions the graph's nodes and edges into
:class:`KnowledgeSubgraph` entries. It performs pure graph partitioning only —
no observation, no finding, no metric. Edges are treated as undirected for
connectivity purposes: two nodes belong to the same subgraph whenever any
governed edge connects them, regardless of the edge's own direction.
"""

from __future__ import annotations

from collections import deque

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeId,
    KnowledgeNodeId,
    KnowledgeSubgraphId,
)
from requirement_intelligence.knowledge_graph.models.edge import KnowledgeEdge
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.subgraph import KnowledgeSubgraph
from requirement_intelligence.knowledge_graph.policy import KnowledgeGraphPolicy


def _undirected_adjacency(
    edges: tuple[KnowledgeEdge, ...],
) -> dict[KnowledgeNodeId, list[KnowledgeNodeId]]:
    """Build a deterministic adjacency list — insertion order follows *edges*'s own order."""
    adjacency: dict[KnowledgeNodeId, list[KnowledgeNodeId]] = {}
    for edge in edges:
        adjacency.setdefault(edge.source_node_id, []).append(edge.target_node_id)
        adjacency.setdefault(edge.target_node_id, []).append(edge.source_node_id)
    return adjacency


class SubgraphDetector:
    """Partition nodes/edges into connected components. Pure partitioning only."""

    def __init__(self, policy: KnowledgeGraphPolicy) -> None:
        """Store the governed policy this detector reads. Construction only."""
        self._policy = policy

    def detect(
        self,
        graph_id: str,
        nodes: tuple[KnowledgeNode, ...],
        edges: tuple[KnowledgeEdge, ...],
    ) -> tuple[KnowledgeSubgraph, ...]:
        """Deterministically partition *nodes*/*edges* into connected components."""
        if not self._policy.capability_switches.enable_subgraph_partitioning:
            return ()

        adjacency = _undirected_adjacency(edges)
        edge_by_pair: dict[frozenset[KnowledgeNodeId], list[KnowledgeEdgeId]] = {}
        for edge in edges:
            key = frozenset({edge.source_node_id, edge.target_node_id})
            edge_by_pair.setdefault(key, []).append(edge.edge_id)

        visited: set[KnowledgeNodeId] = set()
        subgraphs: list[KnowledgeSubgraph] = []
        ordinal = 0

        for node in nodes:
            if node.node_id in visited:
                continue
            component: list[KnowledgeNodeId] = []
            queue: deque[KnowledgeNodeId] = deque([node.node_id])
            visited.add(node.node_id)
            while queue:
                current = queue.popleft()
                component.append(current)
                for neighbor in adjacency.get(current, ()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            component_set = frozenset(component)
            component_edge_ids: list[KnowledgeEdgeId] = []
            for pair, edge_ids in edge_by_pair.items():
                if pair <= component_set:
                    component_edge_ids.extend(edge_ids)

            subgraphs.append(
                KnowledgeSubgraph(
                    subgraph_id=KnowledgeSubgraphId.for_ordinal(graph_id, ordinal),
                    label=f"Connected component of {len(component)} node(s)",
                    node_ids=tuple(component),
                    edge_ids=tuple(component_edge_ids),
                )
            )
            ordinal += 1

        return tuple(subgraphs)
