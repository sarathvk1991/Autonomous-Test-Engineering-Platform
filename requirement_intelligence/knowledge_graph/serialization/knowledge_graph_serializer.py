"""The :class:`KnowledgeGraphSerializer` — a pure projection of a
``KnowledgeGraphResult``.

It renders a completed ``KnowledgeGraphResult`` into the three execution
artifacts — ``knowledge_graph_result.json`` (canonical serialization),
``knowledge_graph_report.md``, and ``knowledge_graph_metrics.md``
(human-readable projections). It **computes nothing** (ADR-0023 §D11): it never
calls the Knowledge Graph engine, a ``HistoricalDatasetProvider``,
``PlatformContext``, projects a node, projects an edge, partitions a subgraph,
records an observation, detects a finding, computes a metric, or invokes a
policy. Everything it renders already exists inside the ``KnowledgeGraphResult``
— the frozen serialization invariant CAP-084B.1 certified. Given the same
result, it produces byte-identical output, exactly mirroring the Continuous
Improvement serializer's boundary (ADR-0022 §D8/§D10), the Recommendation
serializer's boundary (ADR-0019 §D8/§D9), and every other subsystem serializer's
boundary in this platform.

Tallying already-recorded rows by a field they already carry (e.g. counting
nodes per already-recorded ``node_type``) is presentation only — it derives no
new node, edge, subgraph, observation, or finding, and reads no field the
result does not already carry.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult


class KnowledgeGraphSerializer:
    """Render a ``KnowledgeGraphResult`` into execution artifacts. Projection only."""

    def render_json(self, result: KnowledgeGraphResult) -> dict[str, Any]:
        """Return the canonical ``knowledge_graph_result.json`` dict.

        A straight ``model_dump`` — camelCase, tuple ordering preserved, version
        fields intact, no derived fields. Round-trips:
        ``KnowledgeGraphResult.model_validate(dumped)`` equals the original.
        """
        return result.model_dump(mode="json", by_alias=True)

    def render_report(self, result: KnowledgeGraphResult) -> str:
        """Return the ``knowledge_graph_report.md`` markdown — a result projection."""
        summary = result.summary
        dataset = result.historical_dataset
        lines: list[str] = [
            "# Knowledge Graph Report",
            "",
            f"- Result: `{result.result_id}`",
            f"- Graph: `{result.graph_id}`",
            f"- Result version: {result.result_version}",
            f"- Framework version: {result.framework_version}",
            f"- Policy: `{result.policy_id}` (version {result.policy_version})",
            "",
            "## Summary",
            "",
            f"{summary.headline}",
            "",
            f"- Nodes: **{summary.total_nodes}**",
            f"- Edges: {summary.total_edges}",
            f"- Subgraphs: {summary.total_subgraphs}",
            f"- Observations: {summary.total_observations}",
            f"- Findings: {summary.total_findings}",
            "",
            "## Historical Dataset",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Dataset Id | `{dataset.dataset_id}` |",
            f"| Dataset Version | {dataset.dataset_version} |",
            f"| First Execution | `{dataset.first_execution_id}` |",
            f"| Last Execution | `{dataset.last_execution_id}` |",
            f"| Execution Count | {dataset.execution_count} |",
            f"| History Window | {dataset.history_window} |",
            f"| Generated At | {dataset.generated_at.isoformat()} |",
        ]

        lines += [
            "",
            "## Nodes",
            "",
            "| Id | Type | Referenced Id | Label |",
            "| --- | --- | --- | --- |",
        ]
        for node in result.nodes:
            lines.append(
                f"| `{node.node_id}` | {node.node_type} | `{node.referenced_id}` | {node.label} |"
            )
        if not result.nodes:
            lines.append("| _None_ | - | - | - |")

        lines += [
            "",
            "## Edges",
            "",
            "| Id | Type | Source | Target | Rationale |",
            "| --- | --- | --- | --- | --- |",
        ]
        for edge in result.edges:
            lines.append(
                f"| `{edge.edge_id}` | {edge.edge_type} | `{edge.source_node_id}` "
                f"| `{edge.target_node_id}` | {edge.rationale} |"
            )
        if not result.edges:
            lines.append("| _None_ | - | - | - | - |")

        lines += [
            "",
            "## Subgraphs",
            "",
            "| Id | Label | Nodes | Edges |",
            "| --- | --- | --- | --- |",
        ]
        for subgraph in result.subgraphs:
            lines.append(
                f"| `{subgraph.subgraph_id}` | {subgraph.label} "
                f"| {len(subgraph.node_ids)} | {len(subgraph.edge_ids)} |"
            )
        if not result.subgraphs:
            lines.append("| _None_ | - | - | - |")

        lines += [
            "",
            "## Observations",
            "",
            "| Id | Category | Nodes | Edges | Description |",
            "| --- | --- | --- | --- | --- |",
        ]
        for observation in result.observations:
            lines.append(
                f"| `{observation.observation_id}` | {observation.category} "
                f"| {len(observation.subject_node_ids)} | {len(observation.subject_edge_ids)} "
                f"| {observation.description} |"
            )
        if not result.observations:
            lines.append("| _None_ | - | - | - | - |")

        lines += [
            "",
            "## Findings",
            "",
            "| Id | Category | Severity | Nodes | Edges | Message |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for finding in result.findings:
            lines.append(
                f"| `{finding.finding_id}` | {finding.category} | {finding.severity} "
                f"| {len(finding.subject_node_ids)} | {len(finding.subject_edge_ids)} "
                f"| {finding.message} |"
            )
        if not result.findings:
            lines.append("| _None_ | - | - | - | - | - |")

        return "\n".join(lines) + "\n"

    def render_metrics(self, result: KnowledgeGraphResult) -> str:
        """Return the ``knowledge_graph_metrics.md`` markdown — a metrics projection."""
        metrics = result.metrics
        summary = result.summary
        node_type_counts = self._node_type_counts(result)
        edge_type_counts = self._edge_type_counts(result)
        finding_category_counts = self._finding_category_counts(result)

        rows = [
            ("Nodes", str(summary.total_nodes)),
            ("Edges", str(summary.total_edges)),
            ("Subgraphs", str(summary.total_subgraphs)),
            ("Observations", str(summary.total_observations)),
            ("Findings", str(summary.total_findings)),
            ("Connected components", str(metrics.connected_component_count)),
            ("Average degree", f"{metrics.average_degree:.3f}"),
            ("Orphan nodes", str(metrics.orphan_node_count)),
        ]
        lines = [
            "# Knowledge Graph Metrics",
            "",
            "| Metric | Value |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {value} |" for name, value in rows]

        lines += [
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

        lines += [
            "",
            "## Finding Category Distribution",
            "",
            "| Category | Count |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {count} |" for name, count in finding_category_counts]
        if not finding_category_counts:
            lines.append("| _None_ | 0 |")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _node_type_counts(result: KnowledgeGraphResult) -> list[tuple[str, int]]:
        """Tally already-recorded nodes by their recorded type. Presentation only."""
        counts = Counter(str(node.node_type) for node in result.nodes)
        return sorted(counts.items())

    @staticmethod
    def _edge_type_counts(result: KnowledgeGraphResult) -> list[tuple[str, int]]:
        """Tally already-recorded edges by their recorded type. Presentation only."""
        counts = Counter(str(edge.edge_type) for edge in result.edges)
        return sorted(counts.items())

    @staticmethod
    def _finding_category_counts(result: KnowledgeGraphResult) -> list[tuple[str, int]]:
        """Tally already-recorded findings by their recorded category. Presentation only."""
        counts = Counter(str(finding.category) for finding in result.findings)
        return sorted(counts.items())
