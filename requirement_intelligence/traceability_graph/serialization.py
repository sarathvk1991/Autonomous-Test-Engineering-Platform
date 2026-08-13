"""Pure projections of a `TraceabilityGraph` / `CompletenessReport`.

Mirrors `KnowledgeGraphSerializer`'s own boundary (ADR-0023 §D11): computes
nothing, never re-derives a count or a coverage percentage, never calls the
projector or the completeness evaluator. Everything rendered here already
exists on the object it is given. Given the same input, output is
byte-identical.

Not wired into any execution pipeline or `ExecutionWriter` — this build is
architecture-plus-implementation only (mirrors ADR-0023's own CAP-084A/B
milestones, before CAP-084C's runtime integration), deliberately out of
scope here (see `docs/architecture/mentor-feedback-scoping.md` item #3's
"GRAPHS DESIGN SURFACED" note and this build's own scope discipline).
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from requirement_intelligence.traceability_graph.models import (
    BindingCompletenessReport,
    ChangeImpactReport,
    CompletenessReport,
    TraceabilityGraph,
)


def render_graph_json(graph: TraceabilityGraph) -> dict[str, Any]:
    """Return the canonical graph dict — a straight `model_dump`, camelCase, no derived fields."""
    return graph.model_dump(mode="json", by_alias=True)


def render_completeness_json(report: CompletenessReport) -> dict[str, Any]:
    """Return the canonical completeness-report dict — a straight `model_dump`."""
    return report.model_dump(mode="json", by_alias=True)


def render_completeness_report(report: CompletenessReport) -> str:
    """Return a human-readable Markdown rendering of *report*. Projection only."""
    lines: list[str] = [
        "# Traceability Completeness Report",
        "",
        f"- Graph: `{report.graph_id}`",
        "",
        "## Summary",
        "",
        f"- Total requirements: **{report.total_requirements}**",
        f"- Tested (requirement -> scenario -> step chain reachable): "
        f"**{report.tested_requirement_count}**",
        f"- Untested: **{report.untested_requirement_count}**",
        f"- Coverage: **{report.coverage_percentage:.2f}%**",
        "",
        "## Untested Requirements",
        "",
        "| Requirement | Reason |",
        "| --- | --- |",
    ]
    for uncovered in report.untested_requirements:
        lines.append(f"| `{uncovered.requirement_id}` | {uncovered.reason} |")
    if not report.untested_requirements:
        lines.append("| _None — full coverage_ | - |")

    return "\n".join(lines) + "\n"


def render_binding_completeness_json(report: BindingCompletenessReport) -> dict[str, Any]:
    """Return the canonical binding-completeness-report dict — a straight `model_dump`."""
    return report.model_dump(mode="json", by_alias=True)


def render_binding_completeness_report(report: BindingCompletenessReport) -> str:
    """Return a human-readable Markdown rendering of *report*. Projection only."""
    lines: list[str] = [
        "# Traceability Binding Completeness Report",
        "",
        f"- Graph: `{report.graph_id}`",
        "",
        "## Summary",
        "",
        f"- Total steps: **{report.total_steps}**",
        f"- Bound (resolved step definition): **{report.bound_step_count}**",
        f"- Unbound: **{report.unbound_step_count}**",
        f"- Coverage: **{report.coverage_percentage:.2f}%**",
        "",
        "## Unbound Steps",
        "",
        "| Step | Reason |",
        "| --- | --- |",
    ]
    for unbound in report.unbound_steps:
        lines.append(f"| `{unbound.step_text}` | {unbound.reason} |")
    if not report.unbound_steps:
        lines.append("| _None — full binding coverage_ | - |")

    return "\n".join(lines) + "\n"


def render_change_impact_json(report: ChangeImpactReport) -> dict[str, Any]:
    """Return the canonical change-impact-report dict — a straight `model_dump`."""
    return report.model_dump(mode="json", by_alias=True)


def render_change_impact_report(report: ChangeImpactReport) -> str:
    """Return a human-readable Markdown rendering of *report*. Projection only."""
    lines: list[str] = [
        "# Traceability Change-Impact Report",
        "",
        f"- Graph: `{report.graph_id}`",
        "",
        "## Summary",
        "",
        f"- Total page-object methods tracked: **{report.total_methods}**",
        "",
        "## Method Impact",
        "",
        "| Method | Affected Scenarios | Count |",
        "| --- | --- | --- |",
    ]
    for impact in report.method_impacts:
        scenarios = ", ".join(f"`{s}`" for s in impact.affected_scenario_ids) or "_none_"
        lines.append(
            f"| `{impact.class_name}.{impact.method_name}` | {scenarios} | "
            f"{impact.affected_scenario_count} |"
        )
    if not report.method_impacts:
        lines.append("| _None tracked_ | - | 0 |")

    return "\n".join(lines) + "\n"


def render_graph_report(graph: TraceabilityGraph) -> str:
    """Return a human-readable Markdown rendering of *graph*'s nodes/edges. Projection only."""
    node_type_counts = sorted(Counter(str(node.node_type) for node in graph.nodes).items())
    edge_type_counts = sorted(Counter(str(edge.edge_type) for edge in graph.edges).items())

    lines: list[str] = [
        "# Traceability Graph Report",
        "",
        f"- Graph: `{graph.graph_id}`",
        f"- Nodes: **{len(graph.nodes)}**",
        f"- Edges: **{len(graph.edges)}**",
        "",
        "## Node Type Distribution",
        "",
        "| Type | Count |",
        "| --- | --- |",
    ]
    lines += [f"| {name} | {count} |" for name, count in node_type_counts]
    if not node_type_counts:
        lines.append("| _None_ | 0 |")

    lines += [
        "",
        "## Edge Type Distribution",
        "",
        "| Type | Count |",
        "| --- | --- |",
    ]
    lines += [f"| {name} | {count} |" for name, count in edge_type_counts]
    if not edge_type_counts:
        lines.append("| _None_ | 0 |")

    return "\n".join(lines) + "\n"


__all__ = [
    "render_binding_completeness_json",
    "render_binding_completeness_report",
    "render_change_impact_json",
    "render_change_impact_report",
    "render_completeness_json",
    "render_completeness_report",
    "render_graph_json",
    "render_graph_report",
]
