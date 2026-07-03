"""Validation report builder — responsible only for ``validation_report.md``.

Renders a human-readable Markdown view of a ``ValidationResult``. It is **pure
presentation**: every value it prints is read directly from the
``ValidationResult`` the execution package was handed. It never executes rules,
re-validates, normalizes, infers findings, changes a verdict, or computes any
validation logic — it only formats what already exists.

This mirrors the other per-file builders (``ReviewBuilder``,
``ExecutionSummaryBuilder``, ``BaselineMetricsBuilder``): a single ``build``
method turning :class:`ExecutionData` into Markdown text. The report is written
only when a ``ValidationResult`` is present (i.e. validation was executed).
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.execution.execution_data import ExecutionData

# The implemented validation layers, in Rule-Catalog order. Used only to lay out
# the per-layer roll-up; the counts themselves come entirely from the result's
# own issue collection (presentation, never derivation).
_LAYER_ROWS: tuple[tuple[str, str], ...] = (
    ("Transport", "transport"),
    ("Syntax", "syntax"),
    ("Schema", "schema"),
    ("Content", "content"),
    ("Reasoning", "reasoning"),
)


def _enum_value(value: Any) -> str:
    """Return the serialised value of an enum (or the value itself if plain)."""
    return str(getattr(value, "value", value))


def _cell(value: Any) -> str:
    """Render a table cell safely: no newlines, escaped pipes. Deterministic."""
    text = "-" if value is None else str(value)
    return text.replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def _counts_by_layer(issues: Any) -> dict[str, int]:
    """Count issues by their own ``validation_layer`` (data already in the result)."""
    counts: dict[str, int] = {}
    for issue in issues:
        key = _enum_value(issue.validation_layer)
        counts[key] = counts.get(key, 0) + 1
    return counts


class ValidationReportBuilder:
    """Render the human-readable validation report (``validation_report.md``)."""

    def build(self, data: ExecutionData) -> str:
        """Return the Markdown content of ``validation_report.md``.

        Reads exclusively from ``data.validation_result``; performs no validation.
        """
        result = data.validation_result
        summary = result.validation_summary
        statistics = result.validation_statistics
        issues = result.validation_issues

        verdict = _enum_value(result.overall_verdict).upper().replace("_", " ")
        profile = data.validation_profile
        profile_name = profile.name if profile is not None else "-"

        lines: list[str] = [
            "# Validation Report",
            "",
            "> Presentation only. Generated entirely from the ValidationResult; nothing",
            "> was re-validated, normalized, inferred, or altered.",
            "",
            "## Overall Verdict",
            "",
            f"**{verdict}**",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "| ------ | ----- |",
            f"| Validation Profile | {_cell(profile_name)} |",
            f"| Rules Executed | {statistics.rules_executed} |",
            f"| Issues Found | {summary.total_issues} |",
            f"| Validation Duration | {statistics.validation_duration_ms:.2f} ms |",
            f"| Overall Health | {_cell(_enum_value(summary.overall_health))} |",
            f"| Info | {summary.info_count} |",
            f"| Warning | {summary.warning_count} |",
            f"| Error | {summary.error_count} |",
            f"| Critical | {summary.critical_count} |",
            f"| Blocking | {summary.blocking_issue_count} |",
            "",
            "## Issues by Layer",
            "",
            "| Layer | Issues |",
            "| ----- | ------ |",
        ]

        by_layer = _counts_by_layer(issues)
        for display, key in _LAYER_ROWS:
            lines.append(f"| {display} | {by_layer.get(key, 0)} |")

        lines += ["", "## Issues", ""]
        if not issues:
            lines += ["_No issues found._", ""]
        else:
            for issue in issues:
                severity = _enum_value(issue.severity)
                layer = _enum_value(issue.validation_layer)
                lines += [
                    f"### {_cell(issue.rule_id)} — {_cell(severity)}",
                    "",
                    "| Field | Value |",
                    "| ----- | ----- |",
                    f"| Rule ID | {_cell(issue.rule_id)} |",
                    f"| Rule Version | {_cell(issue.rule_version)} |",
                    f"| Category | {_cell(issue.category)} |",
                    f"| Layer | {_cell(layer)} |",
                    f"| Severity | {_cell(severity)} |",
                    f"| Location | {_cell(issue.location)} |",
                    f"| Blocking | {_cell(issue.blocking)} |",
                    f"| Message | {_cell(issue.message)} |",
                    f"| Recommendation | {_cell(issue.recommendation)} |",
                    f"| Evidence | {_cell(issue.evidence)} |",
                    "",
                ]

        lines += [
            "## Execution Statistics",
            "",
            "| Field | Value |",
            "| ----- | ----- |",
            f"| Validation Id | {_cell(result.validation_id)} |",
            f"| Analysis Id | {_cell(result.analysis_id)} |",
            f"| Execution Id | {_cell(result.execution_id)} |",
            f"| Rules Executed | {statistics.rules_executed} |",
            f"| Rules Passed | {statistics.rules_passed} |",
            f"| Rules Failed | {statistics.rules_failed} |",
            f"| Validation Duration (ms) | {statistics.validation_duration_ms:.2f} |",
            f"| Started At | {_cell(statistics.started_at.isoformat())} |",
            f"| Completed At | {_cell(statistics.completed_at.isoformat())} |",
            f"| Validator Version | {_cell(statistics.validator_version)} |",
            f"| Validation Contract Version | {_cell(statistics.validation_contract_version)} |",
        ]

        return "\n".join(lines) + "\n"
