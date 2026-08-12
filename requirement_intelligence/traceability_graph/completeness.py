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

`evaluate_binding_completeness` is a companion, not a replacement: it
answers a second, distinct completeness question over the SAME graph — does
a STEP node have a resolved step-definition? — by joining STEP labels
against the automation-engineering stage's own per-need binding outcomes
(ADR-0048 D5's own two-layer finding, now answered by one graph instead of
a manual CP3 cross-reference). Same report-only posture.
"""

from __future__ import annotations

from automation_engineering.stage.models import AssetRecord, AutomationEngineeringPackage
from requirement_intelligence.traceability_graph.models import (
    BindingCompletenessReport,
    CompletenessReport,
    TraceabilityGraph,
    TraceabilityNodeType,
    UnboundStep,
    UncoveredRequirement,
)
from requirement_intelligence.traceability_graph.traversal import (
    build_directed_adjacency,
    reachable_from,
)

_STEP_DEFINITION_NEED_KIND = "step_definition"


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


def evaluate_binding_completeness(
    graph: TraceabilityGraph, automation_package: AutomationEngineeringPackage
) -> BindingCompletenessReport:
    """Traverse *graph*'s STEP nodes and report step-definition-binding completeness.

    Joins each STEP node's own `label` (raw Gherkin step text, set by
    `project_traceability_graph` from the identical `.feature`-parser field
    stage 15's own `derive_unique_step_needs` reads) against
    *automation_package*'s `need_kind == "step_definition"` records, keyed
    by that same text, first-seen wins (mirrors `derive_unique_step_needs`'s
    own dedup rule).

    A step is **bound** when a matching record exists and is not
    `escalated`. It is **unbound** — with a reason — when the matching
    record IS `escalated` (a need was derived but the reuse engine could
    neither bind nor generate a step definition for it), or when no
    matching record exists at all (`"no_step_definition_need"`; not
    expected against a same-run automation package, since every real step's
    text also feeds stage 15's own need derivation, but never assumed).

    A step counted `tested` by `evaluate_completeness` may still be
    `unbound` here — the two distinct, both-real completeness layers
    ADR-0048 D5's first real measurement named (100% authoring, ~50%
    binding, on the identical step set).
    """
    needs_by_text: dict[str, AssetRecord] = {}
    for record in automation_package.records:
        if record.need_kind != _STEP_DEFINITION_NEED_KIND:
            continue
        needs_by_text.setdefault(record.need_text, record)

    step_nodes = [node for node in graph.nodes if node.node_type == TraceabilityNodeType.STEP]

    unbound: list[UnboundStep] = []
    bound_count = 0
    for step in step_nodes:
        matched_need = needs_by_text.get(step.label)
        if matched_need is None:
            unbound.append(
                UnboundStep(
                    step_id=step.referenced_id,
                    step_text=step.label,
                    reason="no_step_definition_need",
                )
            )
        elif matched_need.escalated:
            unbound.append(
                UnboundStep(step_id=step.referenced_id, step_text=step.label, reason="escalated")
            )
        else:
            bound_count += 1

    total = len(step_nodes)
    coverage = (bound_count / total * 100.0) if total else 0.0

    return BindingCompletenessReport(
        graph_id=graph.graph_id,
        total_steps=total,
        bound_step_count=bound_count,
        unbound_step_count=len(unbound),
        coverage_percentage=round(coverage, 2),
        unbound_steps=tuple(unbound),
    )


__all__ = ["evaluate_binding_completeness", "evaluate_completeness"]
