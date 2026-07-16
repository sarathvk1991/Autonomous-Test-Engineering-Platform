"""The :class:`OrganizationalMemorySerializer` — a pure projection of an
``OrganizationalMemoryResult``.

It renders a completed ``OrganizationalMemoryResult`` into the three execution
artifacts — ``organizational_memory_result.json`` (canonical serialization),
``organizational_memory_report.md``, and ``organizational_memory_metrics.md``
(human-readable projections). It **computes nothing** (ADR-0027 §D18): it never
calls the Organizational Memory engine, ``OrganizationalMemoryService``,
``PlatformContext``, captures an experience, promotes a lesson, institutionalizes
a best practice, records a promotion, or records a lifecycle transition.
Everything it renders already exists inside the ``OrganizationalMemoryResult``
— the frozen serialization invariant CAP-085B.1 certified. Given the same
result, it produces byte-identical output, exactly mirroring the Knowledge
Graph serializer's boundary (ADR-0023 §D11), the Continuous Improvement
serializer's boundary (ADR-0022 §D8/§D10), and every other subsystem
serializer's boundary in this platform.

Tallying already-recorded rows by a field they already carry (e.g. counting
experiences per already-recorded ``source_layer``) is presentation only — it
derives no new experience, lesson, best practice, promotion, or lifecycle
record, and reads no field the result does not already carry.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from requirement_intelligence.organizational_memory.models.result import OrganizationalMemoryResult


class OrganizationalMemorySerializer:
    """Render an ``OrganizationalMemoryResult`` into execution artifacts. Projection only."""

    def render_json(self, result: OrganizationalMemoryResult) -> dict[str, Any]:
        """Return the canonical ``organizational_memory_result.json`` dict.

        A straight ``model_dump`` — camelCase, tuple ordering preserved, version
        fields intact, no derived fields. Round-trips:
        ``OrganizationalMemoryResult.model_validate(dumped)`` equals the original.
        """
        return result.model_dump(mode="json", by_alias=True)

    def render_report(self, result: OrganizationalMemoryResult) -> str:
        """Return the ``organizational_memory_report.md`` markdown — a result projection."""
        summary = result.summary
        lines: list[str] = [
            "# Organizational Memory Report",
            "",
            f"- Result: `{result.result_id}`",
            f"- Memory: `{result.memory_id}`",
            f"- Result version: {result.result_version}",
            f"- Framework version: {result.framework_version}",
            f"- Policy: `{result.policy_id}` (version {result.policy_version})",
            "",
            "## Summary",
            "",
            f"{summary.headline}",
            "",
            f"- Experiences: **{summary.total_experiences}**",
            f"- Lessons: {summary.total_lessons}",
            f"- Best Practices: {summary.total_best_practices}",
            f"- Promotions: {summary.total_promotions}",
            "",
            "## Consumed Layer 2 Results",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Continuous Improvement Result | `{result.continuous_improvement_result_id}` |",
            f"| Knowledge Graph Result | `{result.knowledge_graph_result_id}` |",
        ]

        lines += [
            "",
            "## Experiences",
            "",
            "| Id | Source Layer | Source Reference | Confidence | Description |",
            "| --- | --- | --- | --- | --- |",
        ]
        for experience in result.experiences:
            lines.append(
                f"| `{experience.experience_id}` | {experience.source_layer} "
                f"| `{experience.source_reference_id}` | {experience.confidence} "
                f"| {experience.description} |"
            )
        if not result.experiences:
            lines.append("| _None_ | - | - | - | - |")

        lines += [
            "",
            "## Lessons",
            "",
            "| Id | Source Experiences | Confidence | Message |",
            "| --- | --- | --- | --- |",
        ]
        for lesson in result.lessons:
            lines.append(
                f"| `{lesson.lesson_id}` | {len(lesson.source_experience_ids)} "
                f"| {lesson.confidence} | {lesson.message} |"
            )
        if not result.lessons:
            lines.append("| _None_ | - | - | - |")

        lines += [
            "",
            "## Best Practices",
            "",
            "| Id | Source Lessons | Confidence | Title |",
            "| --- | --- | --- | --- |",
        ]
        for best_practice in result.best_practices:
            lines.append(
                f"| `{best_practice.best_practice_id}` | {len(best_practice.source_lesson_ids)} "
                f"| {best_practice.confidence} | {best_practice.title} |"
            )
        if not result.best_practices:
            lines.append("| _None_ | - | - | - |")

        lines += [
            "",
            "## Promotions",
            "",
            "| Id | Sources | Targets | Confidence | Rationale |",
            "| --- | --- | --- | --- | --- |",
        ]
        for promotion in result.promotions:
            lines.append(
                f"| `{promotion.promotion_id}` | {len(promotion.source_ids)} "
                f"| {len(promotion.target_ids)} | {promotion.confidence} | {promotion.rationale} |"
            )
        if not result.promotions:
            lines.append("| _None_ | - | - | - | - |")

        lines += [
            "",
            "## Lifecycles",
            "",
            "| Id | Subject | State | Reason |",
            "| --- | --- | --- | --- |",
        ]
        for lifecycle in result.lifecycles:
            lines.append(
                f"| `{lifecycle.lifecycle_id}` | `{lifecycle.subject_id}` "
                f"| {lifecycle.state} | {lifecycle.state_reason} |"
            )
        if not result.lifecycles:
            lines.append("| _None_ | - | - | - |")

        return "\n".join(lines) + "\n"

    def render_metrics(self, result: OrganizationalMemoryResult) -> str:
        """Return the ``organizational_memory_metrics.md`` markdown — a metrics projection."""
        metrics = result.metrics
        source_layer_counts = self._source_layer_counts(result)
        lifecycle_state_counts = self._lifecycle_state_counts(result)

        rows = [
            ("Experiences", str(metrics.experience_count)),
            ("Lessons", str(metrics.lesson_count)),
            ("Best Practices", str(metrics.best_practice_count)),
            ("Promotions", str(metrics.promotion_count)),
            ("Active", str(metrics.active_count)),
            ("Deprecated", str(metrics.deprecated_count)),
            ("Historical", str(metrics.historical_count)),
            ("Archived", str(metrics.archived_count)),
        ]
        lines = [
            "# Organizational Memory Metrics",
            "",
            "| Metric | Value |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {value} |" for name, value in rows]

        lines += [
            "",
            "## Source Layer Distribution",
            "",
            "| Layer | Count |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {count} |" for name, count in source_layer_counts]
        if not source_layer_counts:
            lines.append("| _None_ | 0 |")

        lines += [
            "",
            "## Lifecycle State Distribution",
            "",
            "| State | Count |",
            "| --- | --- |",
        ]
        lines += [f"| {name} | {count} |" for name, count in lifecycle_state_counts]
        if not lifecycle_state_counts:
            lines.append("| _None_ | 0 |")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _source_layer_counts(result: OrganizationalMemoryResult) -> list[tuple[str, int]]:
        """Tally already-recorded experiences by their recorded source layer. Presentation only."""
        counts = Counter(str(experience.source_layer) for experience in result.experiences)
        return sorted(counts.items())

    @staticmethod
    def _lifecycle_state_counts(result: OrganizationalMemoryResult) -> list[tuple[str, int]]:
        """Tally already-recorded lifecycles by their recorded state. Presentation only."""
        counts = Counter(str(lifecycle.state) for lifecycle in result.lifecycles)
        return sorted(counts.items())
