"""The :class:`EnhancementSerializer` — a pure projection of a
``RequirementEnhancementResult``.

It renders a completed ``RequirementEnhancementResult`` into the three execution
artifacts — ``requirement_enhancement_result.json`` (canonical serialization),
``requirement_enhancement_report.md``, and ``requirement_enhancement_metrics.md``
(human-readable projections). It **computes nothing** (ADR-0018 §D8, §D9): it never
calls the enhancement engine, calls ``PlatformContext``, detects a relationship,
creates an observation, computes a metric, recomputes a finding, modifies the
summary, or invokes a policy. Everything it renders already exists inside the
``RequirementEnhancementResult`` — the frozen serialization invariant CAP-081B.1
established. Given the same result, it produces byte-identical output, exactly
mirroring the Grounding serializer's boundary (ADR-0016 §D16) and the Quality
Governance serializer's boundary (ADR-0017 §D30).

Grouping already-recorded rows by a field they already carry (e.g. tallying
relationship edges by their recorded ``relationship_type``) is presentation only —
the same category of work ``GroundingSerializer._recommendations`` already performs:
it derives no new relationship, observation, or finding, and reads no field the
result does not already carry.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from requirement_intelligence.enhancement.models.result import RequirementEnhancementResult


class EnhancementSerializer:
    """Render a ``RequirementEnhancementResult`` into execution artifacts. Projection only."""

    def render_json(self, result: RequirementEnhancementResult) -> dict[str, Any]:
        """Return the canonical ``requirement_enhancement_result.json`` dict.

        A straight ``model_dump`` — camelCase, tuple ordering preserved, version fields
        intact, no derived fields. Round-trips:
        ``RequirementEnhancementResult.model_validate(dumped)`` equals the original.
        """
        return result.model_dump(mode="json", by_alias=True)

    def render_report(self, result: RequirementEnhancementResult) -> str:
        """Return the ``requirement_enhancement_report.md`` markdown — a result projection."""
        summary = result.summary
        metrics = result.metrics
        graph = result.relationship_graph
        lines: list[str] = [
            "# Requirement Enhancement Report",
            "",
            f"- Analysis: `{result.analysis_id}`",
            f"- Execution: `{result.execution_id}`",
            f"- Result version: {result.result_version}",
            f"- Framework version: {result.framework_version}",
            f"- Policy: `{result.policy_id}` (version {result.policy_version})",
            "",
            "## Summary",
            "",
            f"{summary.headline}",
            "",
            f"- Requirements enhanced: **{summary.total_requirements_enhanced}**",
            f"- Relationships: {summary.total_relationships}",
            f"- Observations: {summary.total_observations}",
            f"- Findings: {summary.total_findings}",
            "",
            "## Enhancement Coverage",
            "",
            f"- Enrichment coverage: **{metrics.enrichment_coverage:.3f}**",
            f"- Relationship density: {metrics.relationship_density:.3f}",
            f"- Observation rate: {metrics.observation_rate:.3f}",
            "",
            "## Relationship Statistics",
            "",
            "| Relationship Type | Count |",
            "| --- | --- |",
        ]
        for relationship_type, count in self._relationship_type_counts(graph):
            lines.append(f"| {relationship_type} | {count} |")
        if not graph.relationships:
            lines.append("| _None_ | 0 |")

        lines += [
            "",
            "## Requirement Table",
            "",
            "| Requirement | Enhanced Id | Attributes | Relationships | Observations |",
            "| --- | --- | --- | --- | --- |",
        ]
        for enhanced in result.enhanced_requirements:
            lines.append(
                f"| `{enhanced.requirement_id}` | `{enhanced.enhanced_requirement_id}` | "
                f"{len(enhanced.attributes)} | {len(enhanced.relationship_ids)} | "
                f"{len(enhanced.observation_ids)} |"
            )
        if not result.enhanced_requirements:
            lines.append("| _None_ | - | 0 | 0 | 0 |")

        lines += [
            "",
            "## Relationship Graph Summary",
            "",
            f"- Graph: `{graph.graph_id}`",
            f"- Nodes: {len(graph.requirement_ids)}",
            f"- Edges: {len(graph.relationships)}",
            "",
            "| Source | Target | Type | Rationale |",
            "| --- | --- | --- | --- |",
        ]
        for edge in graph.relationships:
            lines.append(
                f"| `{edge.source_requirement_id}` | `{edge.target_requirement_id}` | "
                f"{edge.relationship_type} | {edge.rationale} |"
            )
        if not graph.relationships:
            lines.append("| _None_ | - | - | - |")

        lines += ["", "## Observations", ""]
        if result.observations:
            lines += [
                "| Observation | Category | Severity | Subjects | Message |",
                "| --- | --- | --- | --- | --- |",
            ]
            for observation in result.observations:
                subjects = ", ".join(f"`{s}`" for s in observation.subject_requirement_ids)
                lines.append(
                    f"| `{observation.observation_id}` | {observation.category} | "
                    f"{observation.severity} | {subjects or '_none_'} | {observation.message} |"
                )
        else:
            lines.append("_No observations._")

        lines += ["", "## Findings", ""]
        if result.findings:
            lines += [
                "| Finding | Observation | Category | Severity | Message |",
                "| --- | --- | --- | --- | --- |",
            ]
            for finding in result.findings:
                lines.append(
                    f"| `{finding.finding_id}` | `{finding.observation_id}` | "
                    f"{finding.category} | {finding.severity} | {finding.message} |"
                )
        else:
            lines.append("_No findings._")

        lines += [
            "",
            "## Recommendations",
            "",
            "_Not yet part of the runtime contract (a documented, reserved extension —_ "
            "_see ADR-0018 §D7)._",
        ]
        return "\n".join(lines) + "\n"

    def render_metrics(self, result: RequirementEnhancementResult) -> str:
        """Return the ``requirement_enhancement_metrics.md`` markdown — a metrics projection."""
        metrics = result.metrics
        summary = result.summary
        graph = result.relationship_graph
        relationship_counts = self._relationship_type_counts(graph)
        duplicate_count = next(
            (count for name, count in relationship_counts if name == "duplicates"), 0
        )
        dependency_count = next(
            (count for name, count in relationship_counts if name == "depends_on"), 0
        )

        rows = [
            ("Requirements enhanced", str(summary.total_requirements_enhanced)),
            ("Relationships", str(summary.total_relationships)),
            ("Observations", str(summary.total_observations)),
            ("Findings", str(summary.total_findings)),
            ("Enrichment coverage", f"{metrics.enrichment_coverage:.3f}"),
            ("Relationship density", f"{metrics.relationship_density:.3f}"),
            ("Observation rate", f"{metrics.observation_rate:.3f}"),
            ("Duplicate relationships", str(duplicate_count)),
            ("Dependency relationships", str(dependency_count)),
            ("Graph nodes", str(len(graph.requirement_ids))),
            ("Graph edges", str(len(graph.relationships))),
        ]
        lines = [
            "# Requirement Enhancement Metrics",
            "",
            "| Metric | Value |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {value} |" for name, value in rows]

        lines += [
            "",
            "## Relationship Distribution",
            "",
            "| Type | Count |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {count} |" for name, count in relationship_counts]
        if not relationship_counts:
            lines.append("| _None_ | 0 |")

        lines += [
            "",
            "## Observation Distribution",
            "",
            "| Category | Count |",
            "| --- | --- |",
        ]
        lines += [
            f"| {entry.category} | {entry.count} |" for entry in summary.observation_distribution
        ]
        if not summary.observation_distribution:
            lines.append("| _None_ | 0 |")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _relationship_type_counts(graph: Any) -> list[tuple[str, int]]:
        """Tally already-recorded edges by their recorded type. Presentation only."""
        counts = Counter(str(edge.relationship_type) for edge in graph.relationships)
        return sorted(counts.items())
