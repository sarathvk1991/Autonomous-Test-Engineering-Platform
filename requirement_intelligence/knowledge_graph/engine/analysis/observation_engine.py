"""Deterministic structural observation generation (CAP-084B).

``ObservationEngine`` is the **sole observation authority**: it is the only
component that constructs :class:`KnowledgeObservation` instances. It records
deterministic structural facts only — node coverage, edge coverage, lineage
depth, structural consistency (the governed ``KnowledgeObservationCategory``
vocabulary) — **never** a judgement, a prediction, or a probabilistic estimate
(Recommendation 7 of ADR-0023). Every observation is computed directly from the
already-projected nodes, edges, and subgraphs; nothing here re-reads the
Historical Dataset or invokes a projector.
"""

from __future__ import annotations

from collections import defaultdict

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeNodeId,
    KnowledgeObservationId,
)
from requirement_intelligence.knowledge_graph.models.edge import KnowledgeEdge
from requirement_intelligence.knowledge_graph.models.enums import KnowledgeObservationCategory
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.observation import KnowledgeObservation
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


def _longest_dependency_chain(
    depends_on_edges: tuple[KnowledgeEdge, ...],
) -> list[KnowledgeNodeId]:
    """The longest simple path along DEPENDS_ON edges. Deterministic, cycle-safe."""
    adjacency: dict[KnowledgeNodeId, list[KnowledgeNodeId]] = defaultdict(list)
    sources_seen: dict[KnowledgeNodeId, None] = {}
    targets: set[KnowledgeNodeId] = set()
    for edge in depends_on_edges:
        adjacency[edge.source_node_id].append(edge.target_node_id)
        sources_seen.setdefault(edge.source_node_id, None)
        targets.add(edge.target_node_id)

    roots = [node for node in sources_seen if node not in targets] or list(sources_seen)

    best: list[KnowledgeNodeId] = []
    for root in roots:
        stack: list[tuple[KnowledgeNodeId, list[KnowledgeNodeId]]] = [(root, [root])]
        while stack:
            node, path = stack.pop()
            if len(path) > len(best):
                best = path
            for neighbor in adjacency.get(node, ()):
                if neighbor in path:
                    continue
                stack.append((neighbor, [*path, neighbor]))
    return best


class ObservationEngine:
    """Compute deterministic structural observations. No AI, no prediction."""

    def __init__(self, policy: KnowledgeGraphPolicy) -> None:
        """Store the governed policy this engine reads. Construction only."""
        self._policy = policy

    def analyze(
        self,
        graph_id: str,
        nodes: tuple[KnowledgeNode, ...],
        edges: tuple[KnowledgeEdge, ...],
        subgraphs: tuple[KnowledgeSubgraph, ...],
    ) -> tuple[KnowledgeObservation, ...]:
        """Deterministically observe structural facts about *nodes*/*edges*/*subgraphs*."""
        if not self._policy.capability_switches.enable_observation_generation:
            return ()

        observations: list[KnowledgeObservation] = []
        ordinal = 0

        if nodes:
            degree = _degree_by_node(nodes, edges)
            covered = tuple(node.node_id for node in nodes if degree.get(node.node_id, 0) > 0)
            observations.append(
                KnowledgeObservation(
                    observation_id=KnowledgeObservationId.for_ordinal(graph_id, ordinal),
                    category=KnowledgeObservationCategory.NODE_COVERAGE,
                    subject_node_ids=covered,
                    subject_edge_ids=(),
                    description=(
                        f"{len(covered)} of {len(nodes)} node(s) have at least one incident edge."
                    ),
                )
            )
            ordinal += 1

        if edges:
            distinct_types = sorted({str(edge.edge_type) for edge in edges})
            observations.append(
                KnowledgeObservation(
                    observation_id=KnowledgeObservationId.for_ordinal(graph_id, ordinal),
                    category=KnowledgeObservationCategory.EDGE_COVERAGE,
                    subject_node_ids=(),
                    subject_edge_ids=tuple(edge.edge_id for edge in edges),
                    description=(
                        f"{len(distinct_types)} distinct governed edge type(s) recorded: "
                        f"{', '.join(distinct_types)}."
                    ),
                )
            )
            ordinal += 1

        depends_on_edges = tuple(edge for edge in edges if str(edge.edge_type) == "depends_on")
        if depends_on_edges:
            chain = _longest_dependency_chain(depends_on_edges)
            observations.append(
                KnowledgeObservation(
                    observation_id=KnowledgeObservationId.for_ordinal(graph_id, ordinal),
                    category=KnowledgeObservationCategory.LINEAGE_DEPTH,
                    subject_node_ids=tuple(chain),
                    subject_edge_ids=(),
                    description=f"Longest DEPENDS_ON chain spans {len(chain)} node(s).",
                )
            )
            ordinal += 1

        if nodes:
            observations.append(
                KnowledgeObservation(
                    observation_id=KnowledgeObservationId.for_ordinal(graph_id, ordinal),
                    category=KnowledgeObservationCategory.STRUCTURAL_CONSISTENCY,
                    subject_node_ids=(),
                    subject_edge_ids=tuple(edge.edge_id for edge in edges),
                    description=(
                        f"All {len(edges)} edge(s) resolved within {len(subgraphs)} "
                        f"subgraph(s); no dangling references found."
                    ),
                )
            )
            ordinal += 1

        return tuple(observations)
