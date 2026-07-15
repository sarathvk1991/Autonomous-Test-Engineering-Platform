"""Deterministic structural finding detection (CAP-084B).

``FindingEngine`` is the **sole finding authority**: it is the only component
that constructs :class:`KnowledgeFinding` instances. It detects deterministic
structural issues only — isolated nodes, duplicate relationships, an orphan
graph, missing expected relationships, broken lineage, and cycles (the
governed ``KnowledgeFindingCategory`` vocabulary) — **never** a probabilistic
judgement (Recommendation 7 of ADR-0023). Every finding is explainable entirely
from the graph: it references only nodes and edges the graph already contains
(Recommendation 8), computed directly from the already-projected nodes, edges,
and subgraphs.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeId,
    KnowledgeFindingId,
    KnowledgeNodeId,
)
from requirement_intelligence.knowledge_graph.models.edge import KnowledgeEdge
from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeFindingCategory,
    KnowledgeSeverity,
)
from requirement_intelligence.knowledge_graph.models.finding import KnowledgeFinding
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.subgraph import KnowledgeSubgraph
from requirement_intelligence.knowledge_graph.policy import KnowledgeGraphPolicy


def _degree_by_node(
    nodes: tuple[KnowledgeNode, ...], edges: tuple[KnowledgeEdge, ...]
) -> dict[KnowledgeNodeId, int]:
    degree: dict[KnowledgeNodeId, int] = {node.node_id: 0 for node in nodes}
    for edge in edges:
        degree[edge.source_node_id] = degree.get(edge.source_node_id, 0) + 1
        degree[edge.target_node_id] = degree.get(edge.target_node_id, 0) + 1
    return degree


def detect_cycle(edges: tuple[KnowledgeEdge, ...]) -> list[KnowledgeNodeId]:
    """Return the node ids forming one directed cycle, or ``[]`` when acyclic.

    Iterative depth-first search with the classic white/gray/black colouring —
    deterministic given *edges*'s own order, and safe against arbitrarily deep
    or malformed input (no recursion).
    """
    adjacency: dict[KnowledgeNodeId, list[KnowledgeNodeId]] = defaultdict(list)
    order: list[KnowledgeNodeId] = []
    seen: set[KnowledgeNodeId] = set()
    for edge in edges:
        adjacency[edge.source_node_id].append(edge.target_node_id)
        for node in (edge.source_node_id, edge.target_node_id):
            if node not in seen:
                seen.add(node)
                order.append(node)

    white, gray, black = 0, 1, 2
    color: dict[KnowledgeNodeId, int] = dict.fromkeys(order, white)
    parent: dict[KnowledgeNodeId, KnowledgeNodeId | None] = {}

    for start in order:
        if color[start] != white:
            continue
        color[start] = gray
        parent[start] = None
        stack: list[tuple[KnowledgeNodeId, Iterator[KnowledgeNodeId]]] = [
            (start, iter(adjacency.get(start, ())))
        ]
        while stack:
            node, neighbors = stack[-1]
            advanced = False
            for neighbor in neighbors:
                if color[neighbor] == white:
                    color[neighbor] = gray
                    parent[neighbor] = node
                    stack.append((neighbor, iter(adjacency.get(neighbor, ()))))
                    advanced = True
                    break
                if color[neighbor] == gray:
                    cycle = [neighbor]
                    current = node
                    while current != neighbor:
                        cycle.append(current)
                        current = parent[current]
                    cycle.append(neighbor)
                    cycle.reverse()
                    return cycle
            if not advanced:
                color[node] = black
                stack.pop()
    return []


class FindingEngine:
    """Detect deterministic structural issues. No AI, no probabilistic judgement."""

    def __init__(self, policy: KnowledgeGraphPolicy) -> None:
        """Store the governed policy this engine reads. Construction only."""
        self._policy = policy

    def detect(
        self,
        graph_id: str,
        nodes: tuple[KnowledgeNode, ...],
        edges: tuple[KnowledgeEdge, ...],
        subgraphs: tuple[KnowledgeSubgraph, ...],
    ) -> tuple[KnowledgeFinding, ...]:
        """Deterministically detect structural issues in *nodes*/*edges*/*subgraphs*."""
        if not self._policy.capability_switches.enable_finding_detection:
            return ()

        findings: list[KnowledgeFinding] = []
        ordinal = 0
        degree = _degree_by_node(nodes, edges)

        isolated = tuple(node.node_id for node in nodes if degree.get(node.node_id, 0) == 0)
        if isolated:
            findings.append(
                KnowledgeFinding(
                    finding_id=KnowledgeFindingId.for_ordinal(graph_id, ordinal),
                    category=KnowledgeFindingCategory.ISOLATED_NODE,
                    severity=KnowledgeSeverity.WARNING,
                    subject_node_ids=isolated,
                    subject_edge_ids=(),
                    message=f"{len(isolated)} node(s) have no incident edges.",
                )
            )
            ordinal += 1

        pair_edges: dict[frozenset[KnowledgeNodeId], list[KnowledgeEdgeId]] = defaultdict(list)
        for edge in edges:
            pair_edges[frozenset({edge.source_node_id, edge.target_node_id})].append(edge.edge_id)
        duplicate_edge_ids = tuple(
            edge_id for edge_ids in pair_edges.values() if len(edge_ids) > 1 for edge_id in edge_ids
        )
        if duplicate_edge_ids:
            findings.append(
                KnowledgeFinding(
                    finding_id=KnowledgeFindingId.for_ordinal(graph_id, ordinal),
                    category=KnowledgeFindingCategory.DUPLICATE_EDGE,
                    severity=KnowledgeSeverity.WARNING,
                    subject_node_ids=(),
                    subject_edge_ids=duplicate_edge_ids,
                    message=(
                        f"{len(duplicate_edge_ids)} edge(s) duplicate an existing "
                        f"node-pair relationship."
                    ),
                )
            )
            ordinal += 1

        if nodes and not edges:
            findings.append(
                KnowledgeFinding(
                    finding_id=KnowledgeFindingId.for_ordinal(graph_id, ordinal),
                    category=KnowledgeFindingCategory.ORPHAN_GRAPH,
                    severity=KnowledgeSeverity.CRITICAL,
                    subject_node_ids=tuple(node.node_id for node in nodes),
                    subject_edge_ids=(),
                    message="The graph has nodes but records no relationships at all.",
                )
            )
            ordinal += 1

        generated_by_sources = {
            edge.source_node_id for edge in edges if str(edge.edge_type) == "generated_by"
        }
        traceable_to_sources = {
            edge.source_node_id for edge in edges if str(edge.edge_type) == "traceable_to"
        }
        missing = tuple(
            node.node_id
            for node in nodes
            if (
                str(node.node_type) == "recommendation"
                and node.node_id not in generated_by_sources
            )
            or (str(node.node_type) == "finding" and node.node_id not in traceable_to_sources)
        )
        if missing:
            findings.append(
                KnowledgeFinding(
                    finding_id=KnowledgeFindingId.for_ordinal(graph_id, ordinal),
                    category=KnowledgeFindingCategory.MISSING_RELATIONSHIP,
                    severity=KnowledgeSeverity.WARNING,
                    subject_node_ids=missing,
                    subject_edge_ids=(),
                    message=(
                        f"{len(missing)} node(s) lack their expected governed relationship "
                        f"to a requirement."
                    ),
                )
            )
            ordinal += 1

        requirement_ids = {node.node_id for node in nodes if str(node.node_type) == "requirement"}
        broken = tuple(
            node_id
            for subgraph in subgraphs
            if len(subgraph.node_ids) > 1 and not (set(subgraph.node_ids) & requirement_ids)
            for node_id in subgraph.node_ids
        )
        if broken:
            findings.append(
                KnowledgeFinding(
                    finding_id=KnowledgeFindingId.for_ordinal(graph_id, ordinal),
                    category=KnowledgeFindingCategory.BROKEN_LINEAGE,
                    severity=KnowledgeSeverity.CRITICAL,
                    subject_node_ids=broken,
                    subject_edge_ids=(),
                    message=(
                        "A subgraph with more than one node contains no REQUIREMENT node."
                    ),
                )
            )
            ordinal += 1

        cycle_nodes = detect_cycle(edges)
        if cycle_nodes:
            findings.append(
                KnowledgeFinding(
                    finding_id=KnowledgeFindingId.for_ordinal(graph_id, ordinal),
                    category=KnowledgeFindingCategory.CYCLE,
                    severity=KnowledgeSeverity.CRITICAL,
                    subject_node_ids=tuple(cycle_nodes),
                    subject_edge_ids=(),
                    message=f"A directed cycle spans {len(cycle_nodes)} node(s).",
                )
            )
            ordinal += 1

        return tuple(findings)
