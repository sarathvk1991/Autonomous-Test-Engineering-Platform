"""The :class:`ContinuousImprovementSerializer` — a pure projection of a
``ContinuousImprovementResult``.

It renders a completed ``ContinuousImprovementResult`` into the three execution
artifacts — ``continuous_improvement_result.json`` (canonical serialization),
``continuous_improvement_report.md``, and ``continuous_improvement_metrics.md``
(human-readable projections). It **computes nothing** (ADR-0022 §D8/§D10): it never
calls the Continuous Improvement engine, a ``HistoricalDatasetProvider``,
``PlatformContext``, observes a finding, detects a trend, names an opportunity,
computes a metric, or invokes a policy. Everything it renders already exists inside
the ``ContinuousImprovementResult`` — the frozen serialization invariant CAP-083B.1
certified. Given the same result, it produces byte-identical output, exactly
mirroring the Recommendation serializer's boundary (ADR-0019 §D8/§D9), the
Requirement Enhancement serializer's boundary (ADR-0018 §D8/§D9), the Grounding
serializer's boundary (ADR-0016 §D16), and the Quality Governance serializer's
boundary (ADR-0017 §D30).

Tallying already-recorded rows by a field they already carry (e.g. counting
findings per already-recorded ``source``) is presentation only — it derives no new
finding, trend, or opportunity, and reads no field the result does not already
carry.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from requirement_intelligence.continuous_improvement.models.result import (
    ContinuousImprovementResult,
)


class ContinuousImprovementSerializer:
    """Render a ``ContinuousImprovementResult`` into execution artifacts. Projection only."""

    def render_json(self, result: ContinuousImprovementResult) -> dict[str, Any]:
        """Return the canonical ``continuous_improvement_result.json`` dict.

        A straight ``model_dump`` — camelCase, tuple ordering preserved, version
        fields intact, no derived fields. Round-trips:
        ``ContinuousImprovementResult.model_validate(dumped)`` equals the original.
        """
        return result.model_dump(mode="json", by_alias=True)

    def render_report(self, result: ContinuousImprovementResult) -> str:
        """Return the ``continuous_improvement_report.md`` markdown — a result projection."""
        summary = result.summary
        dataset = result.historical_dataset
        lines: list[str] = [
            "# Continuous Improvement Report",
            "",
            f"- Result: `{result.result_id}`",
            f"- Result version: {result.result_version}",
            f"- Framework version: {result.framework_version}",
            f"- Policy: `{result.policy_id}` (version {result.policy_version})",
            "",
            "## Summary",
            "",
            f"{summary.headline}",
            "",
            f"- Findings: **{summary.total_findings}**",
            f"- Trends: {summary.total_trends}",
            f"- Opportunities: {summary.total_opportunities}",
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
            "## Findings",
            "",
            "| Id | Category | Source | Severity | Occurrences | Message |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for finding in result.findings:
            lines.append(
                f"| `{finding.finding_id}` | {finding.category} | {finding.source} "
                f"| {finding.severity} | {finding.occurrence_count} | {finding.message} |"
            )
        if not result.findings:
            lines.append("| _None_ | - | - | - | - | - |")

        lines += [
            "",
            "## Trends",
            "",
            "| Id | Direction | Source | Metric | Observations | Message |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for trend in result.trends:
            lines.append(
                f"| `{trend.trend_id}` | {trend.direction} | {trend.source} "
                f"| {trend.metric_name} | {trend.observation_count} | {trend.message} |"
            )
        if not result.trends:
            lines.append("| _None_ | - | - | - | - | - |")

        lines += [
            "",
            "## Opportunities",
            "",
            "| Id | Category | Occurrences | Source Findings | Source Trends | Description |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for opportunity in result.opportunities:
            source_findings = ", ".join(f"`{fid}`" for fid in opportunity.source_finding_ids)
            source_trends = ", ".join(f"`{tid}`" for tid in opportunity.source_trend_ids)
            lines.append(
                f"| `{opportunity.opportunity_id}` | {opportunity.category} "
                f"| {opportunity.occurrence_count} | {source_findings} | {source_trends} "
                f"| {opportunity.description} |"
            )
        if not result.opportunities:
            lines.append("| _None_ | - | - | - | - | - |")

        return "\n".join(lines) + "\n"

    def render_metrics(self, result: ContinuousImprovementResult) -> str:
        """Return the ``continuous_improvement_metrics.md`` markdown — a metrics projection."""
        metrics = result.metrics
        summary = result.summary
        finding_source_counts = self._finding_source_counts(result)
        finding_category_counts = self._finding_category_counts(result)
        trend_direction_counts = self._trend_direction_counts(result)

        rows = [
            ("Findings", str(summary.total_findings)),
            ("Trends", str(summary.total_trends)),
            ("Opportunities", str(summary.total_opportunities)),
            ("Finding density", f"{metrics.finding_density:.3f}"),
            ("Trend stability ratio", f"{metrics.trend_stability_ratio:.3f}"),
            ("Opportunity rate", f"{metrics.opportunity_rate:.3f}"),
        ]
        lines = [
            "# Continuous Improvement Metrics",
            "",
            "| Metric | Value |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {value} |" for name, value in rows]

        lines += [
            "",
            "## Finding Source Distribution",
            "",
            "| Source | Count |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {count} |" for name, count in finding_source_counts]
        if not finding_source_counts:
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

        lines += [
            "",
            "## Trend Direction Distribution",
            "",
            "| Direction | Count |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {count} |" for name, count in trend_direction_counts]
        if not trend_direction_counts:
            lines.append("| _None_ | 0 |")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _finding_source_counts(result: ContinuousImprovementResult) -> list[tuple[str, int]]:
        """Tally already-recorded findings by their recorded source. Presentation only."""
        counts = Counter(str(finding.source) for finding in result.findings)
        return sorted(counts.items())

    @staticmethod
    def _finding_category_counts(result: ContinuousImprovementResult) -> list[tuple[str, int]]:
        """Tally already-recorded findings by their recorded category. Presentation only."""
        counts = Counter(str(finding.category) for finding in result.findings)
        return sorted(counts.items())

    @staticmethod
    def _trend_direction_counts(result: ContinuousImprovementResult) -> list[tuple[str, int]]:
        """Tally already-recorded trends by their recorded direction. Presentation only."""
        counts = Counter(str(trend.direction) for trend in result.trends)
        return sorted(counts.items())
