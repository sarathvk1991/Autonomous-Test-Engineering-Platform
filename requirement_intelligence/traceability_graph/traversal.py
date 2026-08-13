"""Generic directed-graph traversal.

Reuses the ADR-0023 `SubgraphDetector`'s own adjacency-plus-BFS pattern
(`requirement_intelligence/knowledge_graph/engine/analysis/
subgraph_detector.py`), directed rather than undirected: completeness asks
"is a STEP node reachable *from* this requirement," not "are these two nodes
in the same connected component," so this walks edges in their own recorded
direction only. Type-agnostic — it knows nothing about `TraceabilityNode`
node types, only node ids — exactly the property that made the ADR-0023
original reusable as a pattern in the first place (see the "GRAPHS DESIGN
SURFACED" note, `docs/architecture/mentor-feedback-scoping.md` item #3).

Pure, no I/O, no randomness.
"""

from __future__ import annotations

from collections import deque

from requirement_intelligence.traceability_graph.models import TraceabilityEdge


def build_directed_adjacency(edges: tuple[TraceabilityEdge, ...]) -> dict[str, list[str]]:
    """Build a deterministic directed adjacency list — insertion order follows *edges*."""
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.source_node_id, []).append(edge.target_node_id)
    return adjacency


def build_reverse_directed_adjacency(edges: tuple[TraceabilityEdge, ...]) -> dict[str, list[str]]:
    """Build a deterministic REVERSE directed adjacency list — every edge
    walked target-to-source instead of source-to-target.

    Change-impact's own need (mentor item #3's "CHANGE-IMPACT GRAPH DESIGN
    SURFACED" note): given a changed `PAGE_OBJECT_METHOD` node, find every
    node that can reach it going FORWARD (its callers, their steps, their
    scenarios) — i.e. walk the graph backward from the method. Reuses
    `reachable_from` unchanged; only the adjacency direction differs.
    """
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        adjacency.setdefault(edge.target_node_id, []).append(edge.source_node_id)
    return adjacency


def reachable_from(adjacency: dict[str, list[str]], start_node_id: str) -> set[str]:
    """Return every node id reachable from *start_node_id*, including itself."""
    visited: set[str] = {start_node_id}
    queue: deque[str] = deque([start_node_id])
    while queue:
        current = queue.popleft()
        for neighbor in adjacency.get(current, ()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited


__all__ = ["build_directed_adjacency", "build_reverse_directed_adjacency", "reachable_from"]
