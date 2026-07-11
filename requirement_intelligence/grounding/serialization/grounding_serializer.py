"""The :class:`GroundingSerializer` — a pure projection of a ``GroundingResult``.

It renders a completed ``GroundingResult`` into the three execution artifacts —
``grounding_result.json`` (canonical serialization), ``grounding_report.md``, and
``grounding_metrics.md`` (human-readable projections). It **computes nothing**: it never
matches, classifies, scores confidence, computes metrics, summaries, or findings, and never
invokes a strategy, normalizer, policy, metrics builder, pipeline, or service. Everything it
renders already exists inside the ``GroundingResult`` (ADR-0016 §D16). Given the same result,
it produces byte-identical output.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.grounding.models.assessment import GroundingResult
from requirement_intelligence.grounding.models.enums import SupportClassification


class GroundingSerializer:
    """Render a ``GroundingResult`` into execution artifacts. Projection only."""

    def render_json(self, result: GroundingResult) -> dict[str, Any]:
        """Return the canonical ``grounding_result.json`` dict.

        A straight ``model_dump`` — camelCase, tuple ordering preserved, version fields
        intact, no derived fields. Round-trips: ``GroundingResult.model_validate(dumped)``
        equals the original.
        """
        return result.model_dump(mode="json", by_alias=True)

    def render_report(self, result: GroundingResult) -> str:
        """Return the ``grounding_report.md`` markdown — a projection of the result."""
        assessment = result.assessment
        summary = assessment.summary
        metrics = assessment.metrics
        lines: list[str] = [
            "# Grounding Report",
            "",
            f"- Analysis: `{result.analysis_id}`",
            f"- Execution: `{result.execution_id}`",
            f"- Result version: {result.result_version}",
            f"- Framework version: {result.framework_version}",
            "",
            "## Summary",
            "",
            f"{summary.verdict}",
            "",
            f"- Overall grounding score: **{summary.grounding_score}**",
            f"- Total requirements: {summary.total_requirements}",
            f"- Supported: {summary.supported}",
            f"- Partially supported: {summary.partially_supported}",
            f"- Unsupported: {summary.unsupported}",
            "",
            "## Classification Distribution",
            "",
            "| Classification | Count |",
            "| --- | --- |",
        ]
        for entry in metrics.support_distribution:
            lines.append(f"| {entry.classification} | {entry.count} |")

        lines += [
            "",
            "## Requirements",
            "",
            "| Requirement | Domain | Classification | Confidence | Band | Evidence |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for req in assessment.grounded_requirements:
            lines.append(
                f"| `{req.requirement_id}` | {req.domain} | {req.classification} | "
                f"{req.confidence.score} | {req.confidence.band} | {len(req.evidence_links)} |"
            )

        lines += ["", "## Findings", ""]
        if assessment.findings:
            lines += [
                "| Finding | Requirement | Classification | Severity | Message |",
                "| --- | --- | --- | --- | --- |",
            ]
            for finding in assessment.findings:
                lines.append(
                    f"| `{finding.finding_id}` | `{finding.requirement_id}` | "
                    f"{finding.classification} | {finding.severity} | {finding.message} |"
                )
        else:
            lines.append("_No findings._")

        lines += [
            "",
            "## Confidence Summary",
            "",
            f"- Average confidence: {metrics.average_confidence:.2f}",
            f"- Cross-source support: {metrics.cross_source_support:.2f}",
            f"- Single-source support: {metrics.single_source_support:.2f}",
            "",
            "## Recommendations",
            "",
        ]
        recommendations = self._recommendations(result)
        if recommendations:
            lines += [f"- {rec}" for rec in recommendations]
        else:
            lines.append("_No recommendations._")
        return "\n".join(lines) + "\n"

    def render_metrics(self, result: GroundingResult) -> str:
        """Return the ``grounding_metrics.md`` markdown — a projection of the metrics."""
        metrics = result.assessment.metrics
        rows = [
            ("Total requirements", str(metrics.total_requirements)),
            ("Grounded requirements", str(metrics.grounded_requirements)),
            ("Unsupported requirements", str(metrics.unsupported_requirements)),
            ("Grounding coverage", f"{metrics.grounding_coverage:.3f}"),
            ("Evidence coverage", f"{metrics.evidence_coverage:.3f}"),
            ("Requirement coverage", f"{metrics.requirement_coverage:.3f}"),
            ("Evidence utilization", f"{metrics.evidence_utilization:.3f}"),
            ("Evidence reuse ratio", f"{metrics.evidence_reuse_ratio:.3f}"),
            ("Traceability completeness", f"{metrics.traceability_completeness:.3f}"),
            ("Average confidence", f"{metrics.average_confidence:.2f}"),
            ("Cross-source support", f"{metrics.cross_source_support:.3f}"),
            ("Single-source support", f"{metrics.single_source_support:.3f}"),
            ("Unsupported rate", f"{metrics.unsupported_rate:.3f}"),
            ("Hallucination rate", f"{metrics.hallucination_rate:.3f}"),
            ("Average evidence / requirement", f"{metrics.average_evidence_per_requirement:.3f}"),
            ("Average sources / requirement", f"{metrics.average_sources_per_requirement:.3f}"),
            ("Grounding score", str(metrics.grounding_score)),
        ]
        lines = ["# Grounding Metrics", "", "| Metric | Value |", "| --- | --- |"]
        lines += [f"| {name} | {value} |" for name, value in rows]
        lines += [
            "",
            "## Support Distribution",
            "",
            "| Classification | Count |",
            "| --- | --- |",
        ]
        lines += [f"| {e.classification} | {e.count} |" for e in metrics.support_distribution]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _recommendations(result: GroundingResult) -> tuple[str, ...]:
        """Distinct recommendations carried on the grounded requirements, in order."""
        seen: set[str] = set()
        ordered: list[str] = []
        for req in result.assessment.grounded_requirements:
            for rec in req.explanation.recommendations:
                key = f"{SupportClassification(req.classification)}: {rec}"
                if key not in seen:
                    seen.add(key)
                    ordered.append(key)
        return tuple(ordered)
