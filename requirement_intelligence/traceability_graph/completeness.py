"""Corpus-completeness queries over a `TraceabilityGraph`.

This is the payoff mentor item #3 / both mentors' independently-named #1
strategic risk exists for: turning "is the requirement corpus incomplete"
from a qualitative worry into a queryable answer — "requirements without
tests, uncovered behaviors" (`docs/architecture/mentor-feedback-scoping.md`
item #3, "GRAPHS DESIGN SURFACED" note, and Nitin's own traceability-graph
clarification it records).

Report-only, deliberately: this module answers "is a full requirement ->
scenario -> step chain reachable," never "should this run pass or fail."
No threshold, no gate, no fail logic exists anywhere here — scores-first,
per this build's own scope. `CompletenessReport`'s shape (`models.py`) is
gate-ready; nothing in this module evaluates it against a bound.
"""

from __future__ import annotations

from requirement_intelligence.traceability_graph.models import (
    CompletenessReport,
    TraceabilityGraph,
    TraceabilityNodeType,
    UncoveredRequirement,
)
from requirement_intelligence.traceability_graph.traversal import (
    build_directed_adjacency,
    reachable_from,
)


def evaluate_completeness(graph: TraceabilityGraph) -> CompletenessReport:
    """Traverse *graph* and report which REQUIREMENT nodes reach a STEP node.

    A requirement counts as tested when at least one STEP node is reachable
    from it via `HAS_SCENARIO` -> `HAS_STEP` edges. Everything else is
    untested, with a reason: `"no_scenario"` (nothing reachable at all) or
    `"scenario_without_steps"` (a SCENARIO is reachable, but no STEP is).
    """
    adjacency = build_directed_adjacency(graph.edges)
    nodes_by_id = {node.node_id: node for node in graph.nodes}
    requirement_nodes = [
        node for node in graph.nodes if node.node_type == TraceabilityNodeType.REQUIREMENT
    ]

    untested: list[UncoveredRequirement] = []
    tested_count = 0
    for requirement in requirement_nodes:
        reachable = reachable_from(adjacency, requirement.node_id) - {requirement.node_id}
        reached_types = {
            nodes_by_id[node_id].node_type for node_id in reachable if node_id in nodes_by_id
        }
        if TraceabilityNodeType.STEP in reached_types:
            tested_count += 1
            continue
        reason = (
            "scenario_without_steps"
            if TraceabilityNodeType.SCENARIO in reached_types
            else "no_scenario"
        )
        untested.append(
            UncoveredRequirement(requirement_id=requirement.referenced_id, reason=reason)
        )

    total = len(requirement_nodes)
    coverage = (tested_count / total * 100.0) if total else 0.0

    return CompletenessReport(
        graph_id=graph.graph_id,
        total_requirements=total,
        tested_requirement_count=tested_count,
        untested_requirement_count=len(untested),
        coverage_percentage=round(coverage, 2),
        untested_requirements=tuple(untested),
    )


__all__ = ["evaluate_completeness"]
