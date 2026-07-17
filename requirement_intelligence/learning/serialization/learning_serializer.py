"""The :class:`LearningSerializer` — a pure projection of a ``LearningResult``.

It renders a completed ``LearningResult`` into the three execution artifacts —
``learning_result.json`` (canonical serialization), ``learning_report.md``, and
``learning_metrics.md`` (human-readable projections). It **computes nothing**
(ADR-0029 §D28): it never calls the Learning engine, ``LearningService``,
``PlatformContext``, collects a candidate, clusters candidates, validates a
candidate, generates a Learning, evaluates institutionalization or stability,
records confidence, records a promotion, or records a lifecycle transition.
Everything it renders already exists inside the ``LearningResult`` — the
frozen serialization invariant CAP-086B.1 certified. Given the same result, it
produces byte-identical output, exactly mirroring the Organizational Memory
serializer's boundary (ADR-0027 §D18/§D19), the Knowledge Graph serializer's
boundary (ADR-0023 §D11), and every other subsystem serializer's boundary in
this platform.

Tallying already-recorded rows by a field they already carry (e.g. counting
lifecycles per already-recorded ``maturity``) is presentation only — it
derives no new candidate, validation, learning, confidence, or lifecycle
record, and reads no field the result does not already carry.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from requirement_intelligence.learning.models.result import LearningResult


class LearningSerializer:
    """Render a ``LearningResult`` into execution artifacts. Projection only."""

    def render_json(self, result: LearningResult) -> dict[str, Any]:
        """Return the canonical ``learning_result.json`` dict.

        A straight ``model_dump`` — camelCase, tuple ordering preserved, version
        fields intact, no derived fields. Round-trips:
        ``LearningResult.model_validate(dumped)`` equals the original.
        """
        return result.model_dump(mode="json", by_alias=True)

    def render_report(self, result: LearningResult) -> str:
        """Return the ``learning_report.md`` markdown — a result projection."""
        summary = result.summary
        lines: list[str] = [
            "# Learning Report",
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
            f"- Candidates: **{summary.total_candidates}**",
            f"- Learnings: {summary.total_learnings}",
            f"- Validations: {summary.total_validations}",
            "",
            "## Consumed Layer 2 Result",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Organizational Memory Result | `{result.organizational_memory_result_id}` |",
        ]

        lines += [
            "",
            "## Learning Candidates",
            "",
            "| Id | Source Best Practices | Confidence | Proposed Change |",
            "| --- | --- | --- | --- |",
        ]
        for candidate in result.candidates:
            lines.append(
                f"| `{candidate.candidate_id}` | {len(candidate.source_best_practice_ids)} "
                f"| {candidate.confidence} | {candidate.proposed_change} |"
            )
        if not result.candidates:
            lines.append("| _None_ | - | - | - |")

        lines += [
            "",
            "## Validations",
            "",
            "| Id | Candidate | Gates Cleared | Confidence | Rationale |",
            "| --- | --- | --- | --- | --- |",
        ]
        for validation in result.validations:
            lines.append(
                f"| `{validation.validation_id}` | `{validation.candidate_id}` "
                f"| {len(validation.gates_cleared)} | {validation.confidence} "
                f"| {validation.rationale} |"
            )
        if not result.validations:
            lines.append("| _None_ | - | - | - | - |")

        lines += [
            "",
            "## Learnings",
            "",
            "| Id | Candidate | Validation | Maturity | Confidence | Message |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for learning in result.learnings:
            lines.append(
                f"| `{learning.learning_id}` | `{learning.candidate_id}` "
                f"| `{learning.validation_id}` | {learning.maturity} | {learning.confidence} "
                f"| {learning.message} |"
            )
        if not result.learnings:
            lines.append("| _None_ | - | - | - | - | - |")

        lines += [
            "",
            "## Confidences",
            "",
            "| Id | Subject | Level | Evidence Count | Rationale |",
            "| --- | --- | --- | --- | --- |",
        ]
        for confidence in result.confidences:
            lines.append(
                f"| `{confidence.confidence_id}` | `{confidence.subject_id}` "
                f"| {confidence.level} | {confidence.evidence_count} | {confidence.rationale} |"
            )
        if not result.confidences:
            lines.append("| _None_ | - | - | - | - |")

        lines += [
            "",
            "## Lifecycles",
            "",
            "| Id | Subject | Maturity | Reason |",
            "| --- | --- | --- | --- |",
        ]
        for lifecycle in result.lifecycles:
            lines.append(
                f"| `{lifecycle.lifecycle_id}` | `{lifecycle.subject_id}` "
                f"| {lifecycle.maturity} | {lifecycle.maturity_reason} |"
            )
        if not result.lifecycles:
            lines.append("| _None_ | - | - | - |")

        return "\n".join(lines) + "\n"

    def render_metrics(self, result: LearningResult) -> str:
        """Return the ``learning_metrics.md`` markdown — a metrics projection."""
        metrics = result.metrics
        maturity_counts = self._lifecycle_maturity_counts(result)

        rows = [
            ("Candidates", str(metrics.candidate_count)),
            ("Learnings", str(metrics.learning_count)),
            ("Validations", str(metrics.validation_count)),
            ("Observed", str(metrics.observed_count)),
            ("Validated", str(metrics.validated_count)),
            ("Trusted", str(metrics.trusted_count)),
            ("Institutional", str(metrics.institutional_count)),
            ("Standard", str(metrics.standard_count)),
            ("Retired", str(metrics.retired_count)),
        ]
        lines = [
            "# Learning Metrics",
            "",
            "| Metric | Value |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {value} |" for name, value in rows]

        lines += [
            "",
            "## Lifecycle Maturity Distribution",
            "",
            "| Maturity | Count |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {count} |" for name, count in maturity_counts]
        if not maturity_counts:
            lines.append("| _None_ | 0 |")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _lifecycle_maturity_counts(result: LearningResult) -> list[tuple[str, int]]:
        """Tally already-recorded lifecycles by their recorded maturity. Presentation only."""
        counts = Counter(str(lifecycle.maturity) for lifecycle in result.lifecycles)
        return sorted(counts.items())
