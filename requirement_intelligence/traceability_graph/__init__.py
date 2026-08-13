"""Traceability Graph — the minimal completeness mechanism, plus method-level
change-impact (mentor item #3).

A new, standalone Layer-2 peer answering both mentors' independently-named
#1 strategic risk: "does this platform know when its own requirement corpus
is incomplete?" (`docs/architecture/mentor-feedback-scoping.md` item #3,
"The completeness thread" / "GRAPHS DESIGN SURFACED"), and the direct
prerequisite for Nitin's own #2-prioritized graph, change-impact ("a
selector change should let you identify the 8 affected tests, not rerun
hundreds" — item #3's "CHANGE-IMPACT GRAPH DESIGN SURFACED" note).

**Scope.** `requirement -> scenario -> step` (the minimal completeness
slice), the step-definition-binding annotation over that same STEP layer
(`evaluate_binding_completeness`) — the binding-data half of ADR-0048 D4's
named "page-object hop" (D5: "the deferred page-object/step-definition
hop") — and now `PAGE_OBJECT_METHOD`/`CALLS_METHOD` (`project_change_impact`,
`change_impact_for_method`, `build_change_impact_report`): method-level
change-impact, the OTHER half of ADR-0048 D4's own separately-named
"change-impact graph," extending this SAME graph rather than a new sibling.
Element/locator-level change-impact (a locator field's own value) and the
execution-result/state-flow hops remain additive, separately-scoped later
work. No gating anywhere in this package: it answers "what is the coverage"
and "what is affected," never "should this run pass or fail," and never
regenerates anything — every report here is gate-ready in shape, but
nothing evaluates any of them against a bound (scores-first).

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

from requirement_intelligence.traceability_graph.change_impact import (
    build_change_impact_report,
    change_impact_for_method,
    project_change_impact,
)
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
    ChangeImpactReport,
    CompletenessReport,
    MethodImpact,
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
    render_change_impact_json,
    render_change_impact_report,
    render_completeness_json,
    render_completeness_report,
    render_graph_json,
    render_graph_report,
)
from requirement_intelligence.traceability_graph.traversal import (
    build_directed_adjacency,
    build_reverse_directed_adjacency,
    reachable_from,
)

__all__ = [
    "BindingCompletenessReport",
    "ChangeImpactReport",
    "CompletenessReport",
    "MethodImpact",
    "TraceabilityEdge",
    "TraceabilityEdgeType",
    "TraceabilityGraph",
    "TraceabilityNode",
    "TraceabilityNodeType",
    "UnboundStep",
    "UncoveredRequirement",
    "build_change_impact_report",
    "build_directed_adjacency",
    "build_reverse_directed_adjacency",
    "change_impact_for_method",
    "edge_id_for",
    "evaluate_binding_completeness",
    "evaluate_completeness",
    "graph_id_for",
    "node_id_for",
    "project_change_impact",
    "project_traceability_graph",
    "reachable_from",
    "render_binding_completeness_json",
    "render_binding_completeness_report",
    "render_change_impact_json",
    "render_change_impact_report",
    "render_completeness_json",
    "render_completeness_report",
    "render_graph_json",
    "render_graph_report",
]
