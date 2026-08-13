"""Method-level change-impact — the second half of ADR-0048 §D4's
"Change-impact graph" (`docs/architecture/mentor-feedback-scoping.md` item
#3, "CHANGE-IMPACT GRAPH DESIGN SURFACED"): given a page-object method, which
scenarios are affected if it changes?

Extends the SAME `TraceabilityGraph` a `project_traceability_graph` call
already produced — never a new sibling graph — by adding `PAGE_OBJECT_METHOD`
nodes and `CALLS_METHOD` edges (`STEP -> PAGE_OBJECT_METHOD`) on top of the
existing `requirement -> scenario -> step` shape. Reuses two already-built,
already-tested pieces, never re-implementing either:

* the exact join `completeness.evaluate_binding_completeness` already uses
  (a `STEP` node's own `label`, matched against `AutomationEngineeringPackage`'s
  `need_kind == "step_definition"` records, by text) — to find which
  generated step-definition class a `STEP` node is bound to;
* `automation_engineering.generation.page_object_reference_derivation.
  derive_page_object_requests` — the platform's own, already-built,
  deterministic, `javalang`-based call-site derivation (ADR-0044 D4's own
  "the call site is the spec" principle) — to find which page-object
  class/method(s) that step-definition's own GENERATED body calls.

**Scope, honestly bounded (method-level only, per the design-surfacing
note this build follows):**

* Only `outcome == "generated"` step-definition records are covered — their
  own Java source is directly on disk, at `workspace_dir / record.
  workspace_path`, exactly where this run's own generation wrote it. A
  `"bound"` record (reused from the tracked baseline via the reuse engine)
  has no `workspace_path` — its own already-catalogued source lives outside
  the run's workspace entirely, and reading it would need a second root
  path this build does not add (a real, named boundary, not an oversight;
  see the design-surfacing note's own value analysis for why method-level
  scope is still worth building without it). An `"escalated"` record has no
  generated source at all.
* A `STEP` node whose text has no matching step-definition record, or whose
  matched record's own generated `.java` file is missing on disk, silently
  contributes no `PAGE_OBJECT_METHOD` node — mirrors
  `project_traceability_graph`'s own "a requirement with no feature content
  still gets a node, an absence is a signal, never a crash" discipline.
* Element/locator-level change-impact (a locator field's own value, as
  opposed to the method that uses it) is NOT built here — deferred, named
  explicitly in the design-surfacing note as the next, separate increment.
* This module never gates and never regenerates anything — it identifies
  the affected set; acting on it (delta-scoped regeneration) is Nitin's own
  separate, future caching cluster, not this build.
"""

from __future__ import annotations

from pathlib import Path

from automation_engineering.generation.page_object_reference_derivation import (
    derive_page_object_requests,
)
from automation_engineering.stage.models import AssetRecord, AutomationEngineeringPackage
from requirement_intelligence.traceability_graph.identity import edge_id_for, node_id_for
from requirement_intelligence.traceability_graph.models import (
    ChangeImpactReport,
    MethodImpact,
    TraceabilityEdge,
    TraceabilityEdgeType,
    TraceabilityGraph,
    TraceabilityNode,
    TraceabilityNodeType,
)
from requirement_intelligence.traceability_graph.traversal import (
    build_reverse_directed_adjacency,
    reachable_from,
)

_STEP_DEFINITION_NEED_KIND = "step_definition"


def _method_node_id(class_name: str, method_name: str) -> str:
    referenced_id = f"{class_name}.{method_name}"
    return node_id_for(TraceabilityNodeType.PAGE_OBJECT_METHOD.value, referenced_id)


def project_change_impact(
    graph: TraceabilityGraph,
    automation_package: AutomationEngineeringPackage,
    *,
    workspace_dir: Path,
) -> TraceabilityGraph:
    """Return a NEW `TraceabilityGraph` — *graph* plus `PAGE_OBJECT_METHOD`
    nodes and `CALLS_METHOD` edges for every `STEP` node whose bound
    step-definition was GENERATED this run (module docstring's own scope).

    Deterministic: the same graph + automation package + on-disk generated
    Java always produce the identical extension. Never mutates *graph* —
    `TraceabilityGraph` is frozen; this returns a distinct instance sharing
    *graph*'s own `graph_id` (the same run's own projection, extended, not a
    different graph's identity).
    """
    needs_by_text: dict[str, AssetRecord] = {}
    for record in automation_package.records:
        if record.need_kind != _STEP_DEFINITION_NEED_KIND:
            continue
        needs_by_text.setdefault(record.need_text, record)

    nodes: dict[str, TraceabilityNode] = {node.node_id: node for node in graph.nodes}
    edges: dict[str, TraceabilityEdge] = {edge.edge_id: edge for edge in graph.edges}

    step_nodes = [node for node in graph.nodes if node.node_type == TraceabilityNodeType.STEP]
    for step in step_nodes:
        matched_need = needs_by_text.get(step.label)
        if matched_need is None or matched_need.escalated:
            continue
        if matched_need.outcome != "generated" or not matched_need.workspace_path:
            continue

        java_path = workspace_dir / matched_need.workspace_path
        if not java_path.exists():
            continue

        java_source = java_path.read_text(encoding="utf-8")
        for request in derive_page_object_requests(java_source):
            for call in request.method_calls:
                method_node_id = _method_node_id(request.class_name, call.method_name)
                if method_node_id not in nodes:
                    nodes[method_node_id] = TraceabilityNode(
                        node_id=method_node_id,
                        node_type=TraceabilityNodeType.PAGE_OBJECT_METHOD,
                        referenced_id=f"{request.class_name}.{call.method_name}",
                        label=f"{request.class_name}.{call.method_name}(...)",
                    )
                edge_id = edge_id_for(
                    TraceabilityEdgeType.CALLS_METHOD.value, step.node_id, method_node_id
                )
                if edge_id not in edges:
                    edges[edge_id] = TraceabilityEdge(
                        edge_id=edge_id,
                        edge_type=TraceabilityEdgeType.CALLS_METHOD,
                        source_node_id=step.node_id,
                        target_node_id=method_node_id,
                        rationale=(
                            f"Step {step.referenced_id} is bound to a step-definition "
                            f"whose generated body calls {request.class_name}."
                            f"{call.method_name}."
                        ),
                    )

    return TraceabilityGraph(
        graph_id=graph.graph_id, nodes=tuple(nodes.values()), edges=tuple(edges.values())
    )


def change_impact_for_method(
    graph: TraceabilityGraph, class_name: str, method_name: str
) -> MethodImpact | None:
    """The scenarios affected if `class_name.method_name` changes — `None`
    if no `PAGE_OBJECT_METHOD` node names that method (nothing calls it, or
    `project_change_impact` was never run against this graph)."""
    method_node_id = _method_node_id(class_name, method_name)
    nodes_by_id = {node.node_id: node for node in graph.nodes}
    if method_node_id not in nodes_by_id:
        return None

    reverse_adjacency = build_reverse_directed_adjacency(graph.edges)
    reachable = reachable_from(reverse_adjacency, method_node_id) - {method_node_id}
    affected_scenario_ids = sorted(
        {
            nodes_by_id[node_id].referenced_id
            for node_id in reachable
            if node_id in nodes_by_id
            and nodes_by_id[node_id].node_type == TraceabilityNodeType.SCENARIO
        }
    )
    return MethodImpact(
        class_name=class_name,
        method_name=method_name,
        affected_scenario_count=len(affected_scenario_ids),
        affected_scenario_ids=tuple(affected_scenario_ids),
    )


def build_change_impact_report(graph: TraceabilityGraph) -> ChangeImpactReport:
    """The full method -> affected-scenarios map — one `MethodImpact` per
    `PAGE_OBJECT_METHOD` node in *graph*, sorted for determinism.

    A future delta-scoped-regeneration capability's own intended input
    (identify what a change reaches); nothing here decides what to do with
    that information.
    """
    method_nodes = sorted(
        (node for node in graph.nodes if node.node_type == TraceabilityNodeType.PAGE_OBJECT_METHOD),
        key=lambda node: node.referenced_id,
    )
    reverse_adjacency = build_reverse_directed_adjacency(graph.edges)
    nodes_by_id = {node.node_id: node for node in graph.nodes}

    impacts: list[MethodImpact] = []
    for method_node in method_nodes:
        class_name, _, method_name = method_node.referenced_id.rpartition(".")
        reachable = reachable_from(reverse_adjacency, method_node.node_id) - {method_node.node_id}
        affected_scenario_ids = sorted(
            {
                nodes_by_id[node_id].referenced_id
                for node_id in reachable
                if node_id in nodes_by_id
                and nodes_by_id[node_id].node_type == TraceabilityNodeType.SCENARIO
            }
        )
        impacts.append(
            MethodImpact(
                class_name=class_name,
                method_name=method_name,
                affected_scenario_count=len(affected_scenario_ids),
                affected_scenario_ids=tuple(affected_scenario_ids),
            )
        )

    return ChangeImpactReport(
        graph_id=graph.graph_id, total_methods=len(impacts), method_impacts=tuple(impacts)
    )


__all__ = ["build_change_impact_report", "change_impact_for_method", "project_change_impact"]
