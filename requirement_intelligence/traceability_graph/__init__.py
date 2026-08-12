"""Traceability Graph — the minimal completeness mechanism (mentor item #3).

A new, standalone Layer-2 peer answering both mentors' independently-named
#1 strategic risk: "does this platform know when its own requirement corpus
is incomplete?" (`docs/architecture/mentor-feedback-scoping.md` item #3,
"The completeness thread" / "GRAPHS DESIGN SURFACED").

**Scope, deliberately minimal.** `requirement -> scenario -> step` only,
plus the step-definition-binding annotation over that same STEP layer
(`evaluate_binding_completeness`) — the binding-data half of ADR-0048 D4's
named "page-object hop" (D5: "the deferred page-object/step-definition
hop"). The step-definition's own internal call sites into page objects (the
other half of that named hop), the execution-result hop (blocked on L5,
unbuilt), change-impact, and state/flow remain additive, separately-scoped
later work, per the design-surfacing note this build follows. No gating:
this package answers "what is the coverage," never "should this run pass or
fail" — both `CompletenessReport` and `BindingCompletenessReport` are
gate-ready in shape, but nothing here evaluates either against a bound
(scores-first).

**Reuses the ADR-0023 Knowledge Graph pattern, never its code or its
service.** Typed node/edge models, deterministic SHA-256 identity minting,
and directed-adjacency BFS traversal all mirror
`requirement_intelligence.knowledge_graph`'s own shape. This package does
not import, call, or modify anything under `knowledge_graph/` — that
subsystem's own runtime entry point is frozen to consume Historical Truth
only (ADR-0023 D2/Recommendation 9), and this graph's real source data
(`TestableRequirementSet`, `.feature` files) is exactly the per-run Runtime
Truth that boundary forbids the existing service from consuming directly.
See the design-surfacing note for the full reasoning.

**Not wired into any execution pipeline.** Architecture-plus-implementation
only, mirroring ADR-0023's own CAP-084A/B milestones before CAP-084C's
runtime integration — a deliberate, separately-scoped follow-up, not part
of this build.
"""

from __future__ import annotations

from requirement_intelligence.traceability_graph.completeness import (
    evaluate_binding_completeness,
    evaluate_completeness,
)
from requirement_intelligence.traceability_graph.identity import (
    edge_id_for,
    graph_id_for,
    node_id_for,
)
from requirement_intelligence.traceability_graph.models import (
    BindingCompletenessReport,
    CompletenessReport,
    TraceabilityEdge,
    TraceabilityEdgeType,
    TraceabilityGraph,
    TraceabilityNode,
    TraceabilityNodeType,
    UnboundStep,
    UncoveredRequirement,
)
from requirement_intelligence.traceability_graph.projection import project_traceability_graph
from requirement_intelligence.traceability_graph.serialization import (
    render_binding_completeness_json,
    render_binding_completeness_report,
    render_completeness_json,
    render_completeness_report,
    render_graph_json,
    render_graph_report,
)
from requirement_intelligence.traceability_graph.traversal import (
    build_directed_adjacency,
    reachable_from,
)

__all__ = [
    "BindingCompletenessReport",
    "CompletenessReport",
    "TraceabilityEdge",
    "TraceabilityEdgeType",
    "TraceabilityGraph",
    "TraceabilityNode",
    "TraceabilityNodeType",
    "UnboundStep",
    "UncoveredRequirement",
    "build_directed_adjacency",
    "edge_id_for",
    "evaluate_binding_completeness",
    "evaluate_completeness",
    "graph_id_for",
    "node_id_for",
    "project_traceability_graph",
    "reachable_from",
    "render_binding_completeness_json",
    "render_binding_completeness_report",
    "render_completeness_json",
    "render_completeness_report",
    "render_graph_json",
    "render_graph_report",
]
