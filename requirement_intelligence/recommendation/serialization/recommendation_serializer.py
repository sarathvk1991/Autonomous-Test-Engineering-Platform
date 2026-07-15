"""The :class:`RecommendationSerializer` — a pure projection of a
``RecommendationResult``.

It renders a completed ``RecommendationResult`` into the three execution artifacts —
``recommendation_result.json`` (canonical serialization), ``recommendation_report.md``,
and ``recommendation_metrics.md`` (human-readable projections). It **computes
nothing** (ADR-0019 §D8/§D9): it never calls the recommendation engine, calls
``PlatformContext``, generates a recommendation, forms a group, computes a metric,
recomputes a summary, or invokes a policy. Everything it renders already exists
inside the ``RecommendationResult`` — the frozen serialization invariant CAP-082B.1
certified. Given the same result, it produces byte-identical output, exactly
mirroring the Requirement Enhancement serializer's boundary (ADR-0018 §D8/§D9), the
Grounding serializer's boundary (ADR-0016 §D16), and the Quality Governance
serializer's boundary (ADR-0017 §D30).

Tallying already-recorded rows by a field they already carry (e.g. counting
recommendations per already-recorded ``recommendationSource``) is presentation
only — it derives no new recommendation, priority, or group, and reads no field the
result does not already carry.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from requirement_intelligence.recommendation.models.result import RecommendationResult


class RecommendationSerializer:
    """Render a ``RecommendationResult`` into execution artifacts. Projection only."""

    def render_json(self, result: RecommendationResult) -> dict[str, Any]:
        """Return the canonical ``recommendation_result.json`` dict.

        A straight ``model_dump`` — camelCase, tuple ordering preserved, version
        fields intact, no derived fields. Round-trips:
        ``RecommendationResult.model_validate(dumped)`` equals the original.
        """
        return result.model_dump(mode="json", by_alias=True)

    def render_report(self, result: RecommendationResult) -> str:
        """Return the ``recommendation_report.md`` markdown — a result projection."""
        summary = result.summary
        lines: list[str] = [
            "# Recommendation Report",
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
            f"- Recommendations: **{summary.total_recommendations}**",
            f"- Groups: {summary.total_groups}",
            "",
            "## Priority Distribution",
            "",
            "| Priority | Count |",
            "| --- | --- |",
        ]
        for entry in summary.priority_distribution:
            lines.append(f"| {entry.priority} | {entry.count} |")
        if not summary.priority_distribution:
            lines.append("| _None_ | 0 |")

        lines += [
            "",
            "## Recommendations",
            "",
            "| Id | Source | Type | Priority | Effort | Confidence | Title | References |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for recommendation in result.recommendations:
            references = ", ".join(
                f"{reference.source}:`{reference.referenced_id}`"
                for reference in recommendation.references
            )
            lines.append(
                f"| `{recommendation.recommendation_id}` | {recommendation.recommendation_source} "
                f"| {recommendation.recommendation_type} | {recommendation.priority} | "
                f"{recommendation.effort} | {recommendation.confidence:.2f} | "
                f"{recommendation.title} | {references} |"
            )
        if not result.recommendations:
            lines.append("| _None_ | - | - | - | - | - | - | - |")

        lines += [
            "",
            "## Groups",
            "",
            "| Id | Category | Label | Members |",
            "| --- | --- | --- | --- |",
        ]
        for group in result.groups:
            members = ", ".join(f"`{member_id}`" for member_id in group.recommendation_ids)
            lines.append(f"| `{group.group_id}` | {group.category} | {group.label} | {members} |")
        if not result.groups:
            lines.append("| _None_ | - | - | - |")

        lines += [
            "",
            "## Consumed Inputs",
            "",
            "| Source | Input Id | Input Version |",
            "| --- | --- | --- |",
        ]
        for reference in result.consumed_inputs:
            lines.append(
                f"| {reference.source} | `{reference.input_id}` | {reference.input_version} |"
            )
        if not result.consumed_inputs:
            lines.append("| _None_ | - | - |")

        return "\n".join(lines) + "\n"

    def render_metrics(self, result: RecommendationResult) -> str:
        """Return the ``recommendation_metrics.md`` markdown — a metrics projection."""
        metrics = result.metrics
        summary = result.summary
        source_counts = self._source_counts(result)
        type_counts = self._type_counts(result)

        rows = [
            ("Recommendations", str(summary.total_recommendations)),
            ("Groups", str(summary.total_groups)),
            ("Recommendation density", f"{metrics.recommendation_density:.3f}"),
            ("Average confidence", f"{metrics.average_confidence:.3f}"),
            ("High priority ratio", f"{metrics.high_priority_ratio:.3f}"),
        ]
        lines = [
            "# Recommendation Metrics",
            "",
            "| Metric | Value |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {value} |" for name, value in rows]

        lines += [
            "",
            "## Priority Distribution",
            "",
            "| Priority | Count |",
            "| --- | --- |",
        ]
        lines += [
            f"| {entry.priority} | {entry.count} |" for entry in summary.priority_distribution
        ]
        if not summary.priority_distribution:
            lines.append("| _None_ | 0 |")

        lines += [
            "",
            "## Source Distribution",
            "",
            "| Source | Count |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {count} |" for name, count in source_counts]
        if not source_counts:
            lines.append("| _None_ | 0 |")

        lines += [
            "",
            "## Type Distribution",
            "",
            "| Type | Count |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {count} |" for name, count in type_counts]
        if not type_counts:
            lines.append("| _None_ | 0 |")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _source_counts(result: RecommendationResult) -> list[tuple[str, int]]:
        """Tally already-recorded recommendations by their recorded source. Presentation only."""
        counts = Counter(
            str(recommendation.recommendation_source) for recommendation in result.recommendations
        )
        return sorted(counts.items())

    @staticmethod
    def _type_counts(result: RecommendationResult) -> list[tuple[str, int]]:
        """Tally already-recorded recommendations by their recorded type. Presentation only."""
        counts = Counter(
            str(recommendation.recommendation_type) for recommendation in result.recommendations
        )
        return sorted(counts.items())
