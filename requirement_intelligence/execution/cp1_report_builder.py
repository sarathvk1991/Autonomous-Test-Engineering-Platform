"""CP1 report builder — responsible only for ``cp1_report.md`` (CAP-068).

Renders a human-readable Markdown view of a ``CP1Result``. It is **pure
presentation**: every value it prints is read directly from the ``CP1Result`` the
execution package was handed. It never executes criteria, re-evaluates readiness,
aggregates findings, derives or changes a verdict, scores, thresholds, or computes
any engineering-readiness logic — it only formats what already exists.

This mirrors the sibling per-file builders (``ValidationReportBuilder``,
``ReviewBuilder``, ``ExecutionSummaryBuilder``, ``BaselineMetricsBuilder``): a
single ``build`` method turning :class:`ExecutionData` into Markdown text. The
report is written only when a ``CP1Result`` is present (i.e. CP1 was executed —
the Validation → CP1 gate opened; ADR-0011 §D5).

Ownership (unchanged by this milestone): CP1 owns the ``CP1Result``, its findings,
verdict, and recommendations; the execution package owns persistence and rendering
only. This builder embeds **no** engineering-readiness policy.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.execution.execution_data import ExecutionData

_NO_FINDINGS = "No engineering readiness findings."


def _enum_value(value: Any) -> str:
    """Return the serialised value of an enum (or the value itself if plain)."""
    return str(getattr(value, "value", value))


def _cell(value: Any) -> str:
    """Render a table cell safely: no newlines, escaped pipes. Deterministic."""
    text = "-" if value is None else str(value)
    return text.replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def _criteria_executed(findings: Any) -> list[str]:
    """Distinct criterion ids observed in *findings*, in first-appearance order.

    Presentation only: reads each finding's own ``criterion_id``. A criterion
    appears here when it produced a finding; passing criteria emit no findings
    (ADR-0013 §D4), so this lists the criteria that reported, never a derived total.
    """
    seen: list[str] = []
    for finding in findings:
        cid = finding.criterion_id
        if cid not in seen:
            seen.append(cid)
    return seen


class CP1ReportBuilder:
    """Render the human-readable CP1 engineering-readiness report (``cp1_report.md``)."""

    def build(self, data: ExecutionData) -> str:
        """Return the Markdown content of ``cp1_report.md``.

        Reads exclusively from ``data.cp1_result``; performs no CP1 evaluation,
        aggregation, or readiness logic.
        """
        result = data.cp1_result
        findings = result.findings
        framework = result.framework_metadata
        verdict = _enum_value(result.overall_verdict).upper()

        lines: list[str] = [
            "# CP1 Engineering Readiness Report",
            "",
            "> Presentation only. Generated entirely from the CP1Result; nothing was",
            "> re-evaluated, aggregated, scored, or altered.",
            "",
            "## Overall Verdict",
            "",
            f"**{verdict}**",
            "",
            "## Framework",
            "",
            "| Field | Value |",
            "| ----- | ----- |",
            f"| Framework Version | {_cell(framework.framework_version)} |",
            f"| Criteria Contract Version | {_cell(framework.criteria_contract_version)} |",
            f"| Pipeline Version | {_cell(framework.pipeline_version)} |",
            f"| Registry Version | {_cell(framework.registry_version)} |",
            "",
            "## Criteria Executed",
            "",
        ]

        criteria = _criteria_executed(findings)
        if not criteria:
            lines += [
                "_No criteria reported findings (passing criteria emit none)._",
                "",
            ]
        else:
            for cid in criteria:
                lines.append(f"- {_cell(cid)}")
            lines.append("")

        lines += ["## Findings", ""]
        if not findings:
            lines += [_NO_FINDINGS, ""]
        else:
            for finding in findings:
                contribution = _enum_value(finding.verdict_contribution).upper()
                lines += [
                    f"### {_cell(finding.criterion_id)} — {_cell(contribution)}",
                    "",
                    "| Field | Value |",
                    "| ----- | ----- |",
                    f"| Finding Id | {_cell(finding.finding_id)} |",
                    f"| Criterion Id | {_cell(finding.criterion_id)} |",
                    f"| Criterion Version | {_cell(finding.criterion_version)} |",
                    f"| Verdict Contribution | {_cell(contribution)} |",
                    f"| Location | {_cell(finding.location)} |",
                    f"| Message | {_cell(finding.message)} |",
                    f"| Recommendation | {_cell(finding.recommendation)} |",
                    f"| Evidence | {_cell(finding.evidence)} |",
                    f"| Correlation Id | {_cell(finding.correlation_id)} |",
                    f"| Created At | {_cell(finding.created_at.isoformat())} |",
                    "",
                ]

        lines += ["## Recommendations", ""]
        if not findings:
            lines += ["_No recommendations._", ""]
        else:
            for finding in findings:
                lines.append(f"- {_cell(finding.criterion_id)}: {_cell(finding.recommendation)}")
            lines.append("")

        lines += [
            "## Execution Metadata",
            "",
            "| Field | Value |",
            "| ----- | ----- |",
            f"| CP1 Id | {_cell(result.cp1_id)} |",
            f"| Validation Id | {_cell(result.validation_id)} |",
            f"| Execution Id | {_cell(result.execution_id)} |",
            f"| Analysis Id | {_cell(result.analysis_id)} |",
            f"| CP1 Result Version | {_cell(result.cp1_result_version)} |",
            f"| Findings | {len(findings)} |",
            f"| Started At | {_cell(result.started_at.isoformat())} |",
            f"| Completed At | {_cell(result.completed_at.isoformat())} |",
        ]

        return "\n".join(lines) + "\n"
