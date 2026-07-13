"""The :class:`QualityGovernanceSerializer` — a pure projection of a ``QualityGovernanceResult``.

It renders a completed ``QualityGovernanceResult`` into the three execution artifacts —
``quality_governance_result.json`` (canonical serialization), ``quality_governance_report.md``,
and ``quality_governance_summary.md`` (human-readable projections). It **computes nothing**
(ADR-0017 §D30, Recommendation 2): it never evaluates a rule, assesses, decides, computes a
metric or a summary, derives a finding, or invokes any engine, policy, builder, pipeline, or
service. Everything it renders already exists inside the ``QualityGovernanceResult`` — the
frozen serialization invariant of CAP-080A. Given the same result, it produces byte-identical
output, exactly mirroring the Grounding serializer's boundary (ADR-0016 §D16).
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.quality_governance.models.result import QualityGovernanceResult


class QualityGovernanceSerializer:
    """Render a ``QualityGovernanceResult`` into execution artifacts. Projection only."""

    def render_json(self, result: QualityGovernanceResult) -> dict[str, Any]:
        """Return the canonical ``quality_governance_result.json`` dict.

        A straight ``model_dump`` — camelCase, tuple ordering preserved, version fields
        intact, no derived fields. Round-trips:
        ``QualityGovernanceResult.model_validate(dumped)`` equals the original.
        """
        return result.model_dump(mode="json", by_alias=True)

    def render_report(self, result: QualityGovernanceResult) -> str:
        """Return the ``quality_governance_report.md`` markdown — a projection of the result."""
        assessment = result.assessment
        summary = assessment.summary
        lines: list[str] = [
            "# Quality Governance Report",
            "",
            f"- Analysis: `{result.analysis_id}`",
            f"- Execution: `{result.execution_id}`",
            f"- Result version: {result.result_version}",
            f"- Framework version: {result.framework_version}",
            f"- Policy: `{result.policy_id}` (version {result.policy_version})",
            "",
            "## Release Decision",
            "",
            f"**{assessment.decision.upper()}**",
            "",
            f"{summary.verdict}",
            "",
            f"- Overall quality score: **{summary.overall_quality_score}**",
            f"- Total findings: {summary.total_findings}",
            f"- Warnings: {summary.warning_count}",
            f"- Failures: {summary.failure_count}",
            "",
            "## Finding Distribution",
            "",
            "| Category | Count |",
            "| --- | --- |",
        ]
        for entry in summary.category_distribution:
            lines.append(f"| {entry.category} | {entry.count} |")
        if not summary.category_distribution:
            lines.append("| _None_ | 0 |")

        lines += [
            "",
            "## Findings",
            "",
        ]
        if assessment.findings:
            lines += [
                "| Finding | Category | Severity | Source | Message |",
                "| --- | --- | --- | --- | --- |",
            ]
            for finding in assessment.findings:
                lines.append(
                    f"| `{finding.finding_id}` | {finding.category} | {finding.severity} | "
                    f"{finding.source} | {finding.message} |"
                )
        else:
            lines.append("_No findings._")

        lines += [
            "",
            "## Consumed Results",
            "",
            "| Source | Result | Version |",
            "| --- | --- | --- |",
        ]
        for ref in result.consumed_inputs:
            lines.append(f"| {ref.source} | `{ref.result_id}` | {ref.result_version} |")
        if not result.consumed_inputs:
            lines.append("| _None_ | - | - |")
        return "\n".join(lines) + "\n"

    def render_summary(self, result: QualityGovernanceResult) -> str:
        """Return the ``quality_governance_summary.md`` markdown — the headline projection."""
        assessment = result.assessment
        summary = assessment.summary
        rows = [
            ("Release decision", assessment.decision.upper()),
            ("Overall quality score", str(summary.overall_quality_score)),
            ("Total findings", str(summary.total_findings)),
            ("Warnings", str(summary.warning_count)),
            ("Failures", str(summary.failure_count)),
            ("Policy", f"{result.policy_id} ({result.policy_version})"),
        ]
        lines = [
            "# Quality Governance Summary",
            "",
            f"{summary.verdict}",
            "",
            "| Field | Value |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {value} |" for name, value in rows]
        return "\n".join(lines) + "\n"
