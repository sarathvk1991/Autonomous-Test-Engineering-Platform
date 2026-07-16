"""Execution writer — writes every artifact of an execution package.

The CLI hands an :class:`~requirement_intelligence.execution.execution_data.ExecutionData`
to :meth:`ExecutionWriter.write` and gets back a small result. All file-format
knowledge (which files, their content, the manifest) lives here and in the
per-file builders — never in the CLI.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from requirement_intelligence.continuous_improvement.serialization import (
    ContinuousImprovementSerializer,
)
from requirement_intelligence.enhancement.serialization import EnhancementSerializer
from requirement_intelligence.execution.baseline_metrics_builder import (
    BaselineMetricsBuilder,
)
from requirement_intelligence.execution.cp1_report_builder import CP1ReportBuilder
from requirement_intelligence.execution.engineering_context_artifact import (
    EngineeringContextArtifactBuilder,
)
from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.execution.execution_metrics import observe_response_counts
from requirement_intelligence.execution.execution_summary_builder import (
    ExecutionSummaryBuilder,
)
from requirement_intelligence.execution.manifest_builder import ManifestBuilder
from requirement_intelligence.execution.review_builder import ReviewBuilder
from requirement_intelligence.execution.validation_report_builder import (
    ValidationReportBuilder,
)
from requirement_intelligence.grounding.serialization import GroundingSerializer
from requirement_intelligence.knowledge_graph.serialization import KnowledgeGraphSerializer
from requirement_intelligence.quality_governance.serialization import (
    QualityGovernanceSerializer,
)
from requirement_intelligence.recommendation.serialization import RecommendationSerializer

_CORE_ARTIFACTS = (
    "consolidated_artifact.json",
    "engineering_context.json",
    "prompt.txt",
    "llm_request.json",
)
_RESULT_ARTIFACTS = (
    "analysis_result.json",
    "raw_llm_response.json",
    "execution_summary.md",
    "baseline_metrics.md",
    "review.md",
)


@dataclass(frozen=True)
class ExecutionWriteResult:
    """The outcome of writing an execution package."""

    target_dir: Path
    manifest: dict[str, Any]
    generated_artifacts: list[str]
    json_valid: bool | None


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _collect_generated(target_dir: Path, names: list[str]) -> list[dict[str, Any]]:
    generated: list[dict[str, Any]] = []
    for name in names:
        content = (target_dir / name).read_bytes()
        generated.append(
            {
                "name": name,
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return generated


class ExecutionWriter:
    """Write the full execution package for one run."""

    def __init__(self) -> None:
        """Wire the per-file builders."""
        self._manifest = ManifestBuilder()
        self._summary = ExecutionSummaryBuilder()
        self._metrics = BaselineMetricsBuilder()
        self._review = ReviewBuilder()
        self._validation_report = ValidationReportBuilder()
        self._cp1_report = CP1ReportBuilder()
        self._engineering_context = EngineeringContextArtifactBuilder()
        self._grounding = GroundingSerializer()
        self._quality_governance = QualityGovernanceSerializer()
        self._enhancement = EnhancementSerializer()
        self._recommendation = RecommendationSerializer()
        self._continuous_improvement = ContinuousImprovementSerializer()
        self._knowledge_graph = KnowledgeGraphSerializer()

    def write(self, target_dir: Path, data: ExecutionData) -> ExecutionWriteResult:
        """Write every artifact for *data* into *target_dir* and the manifest."""
        names = list(self._write_core(target_dir, data))
        json_valid: bool | None = None
        if not data.dry_run:
            names += list(self._write_result(target_dir, data))
            json_valid = observe_response_counts(data.generated_text)["json_valid"]

        started, completed = self._timestamps(data)
        manifest = self._manifest.build(
            data,
            started_timestamp=started,
            completed_timestamp=completed,
            generated_artifacts=_collect_generated(target_dir, names),
        )
        _write_json(target_dir / "manifest.json", manifest)

        return ExecutionWriteResult(
            target_dir=target_dir,
            manifest=manifest,
            generated_artifacts=names,
            json_valid=json_valid,
        )

    # -- internal ----------------------------------------------------------

    def _write_core(self, target_dir: Path, data: ExecutionData) -> tuple[str, ...]:
        """Write the four artifacts produced for every run (incl. dry runs).

        ``engineering_context.json`` records the orchestration decision — which
        groups were considered, which contributed, and under which policy — that
        the prompt in ``prompt.txt`` is the rendering of. The writer serialises
        the context it is handed; it composes nothing and re-decides nothing.
        """
        _write_json(
            target_dir / "consolidated_artifact.json",
            data.selected.model_dump(mode="json", by_alias=True),
        )
        _write_json(
            target_dir / "engineering_context.json",
            self._engineering_context.build(data.engineering_context),
        )
        prompt_txt = (
            "===== SYSTEM PROMPT =====\n"
            f"{data.prompt_request.system_prompt}\n\n"
            "===== USER PROMPT =====\n"
            f"{data.prompt_request.user_prompt}\n"
        )
        (target_dir / "prompt.txt").write_text(prompt_txt, encoding="utf-8")
        _write_json(
            target_dir / "llm_request.json",
            data.llm_request.model_dump(mode="json"),
        )
        return _CORE_ARTIFACTS

    def _write_result(self, target_dir: Path, data: ExecutionData) -> tuple[str, ...]:
        """Write the analysis result artifacts (live runs only).

        The optional ``validation_result.json`` (canonical persistence) and its
        human-readable twin ``validation_report.md`` are appended only when a
        ``ValidationResult`` was supplied (i.e. validation was executed). The optional
        ``cp1_report.md`` is appended only when a ``CP1Result`` was supplied (i.e. CP1
        was executed; the Validation → CP1 gate opened). The writer performs no
        validation, no CP1 evaluation, and no judgment — it serialises/renders the
        results as-is, so the execution package owns persistence and reporting while
        validation and CP1 stay read-only.
        """
        result = data.result
        _write_json(
            target_dir / "analysis_result.json",
            result.model_dump(mode="json", by_alias=True),
        )
        _write_json(
            target_dir / "raw_llm_response.json",
            result.llm_response.model_dump(mode="json"),
        )
        (target_dir / "execution_summary.md").write_text(
            self._summary.build(data), encoding="utf-8"
        )
        (target_dir / "baseline_metrics.md").write_text(self._metrics.build(data), encoding="utf-8")
        (target_dir / "review.md").write_text(self._review.build(data), encoding="utf-8")

        names: list[str] = list(_RESULT_ARTIFACTS)
        if data.validation_result is not None:
            _write_json(
                target_dir / "validation_result.json",
                data.validation_result.model_dump(mode="json", by_alias=True),
            )
            (target_dir / "validation_report.md").write_text(
                self._validation_report.build(data), encoding="utf-8"
            )
            names += ["validation_result.json", "validation_report.md"]
        # CP1 report (CAP-068): rendered only when CP1 was executed. Presentation only —
        # the CP1Result is transported, never re-evaluated or transformed here.
        if data.cp1_result is not None:
            (target_dir / "cp1_report.md").write_text(
                self._cp1_report.build(data), encoding="utf-8"
            )
            names.append("cp1_report.md")
        # Grounding artifacts (CAP-077F.1): appended only when a GroundingResult was
        # produced. Pure projection — the GroundingResult is serialised/rendered as-is,
        # nothing is matched, classified, scored, or recomputed.
        if data.grounding_result is not None:
            _write_json(
                target_dir / "grounding_result.json",
                self._grounding.render_json(data.grounding_result),
            )
            (target_dir / "grounding_report.md").write_text(
                self._grounding.render_report(data.grounding_result), encoding="utf-8"
            )
            (target_dir / "grounding_metrics.md").write_text(
                self._grounding.render_metrics(data.grounding_result), encoding="utf-8"
            )
            names += ["grounding_result.json", "grounding_report.md", "grounding_metrics.md"]
        # Quality Governance artifacts (CAP-080D): appended only when a
        # QualityGovernanceResult was produced — the terminal release authority. Pure
        # projection — the QualityGovernanceResult is serialised/rendered as-is; no rule is
        # evaluated, no assessment or decision is made, and the recorded QualityDecision is
        # never reinterpreted or overridden here.
        if data.quality_governance_result is not None:
            _write_json(
                target_dir / "quality_governance_result.json",
                self._quality_governance.render_json(data.quality_governance_result),
            )
            (target_dir / "quality_governance_report.md").write_text(
                self._quality_governance.render_report(data.quality_governance_result),
                encoding="utf-8",
            )
            (target_dir / "quality_governance_summary.md").write_text(
                self._quality_governance.render_summary(data.quality_governance_result),
                encoding="utf-8",
            )
            names += [
                "quality_governance_result.json",
                "quality_governance_report.md",
                "quality_governance_summary.md",
            ]
        # Requirement Enhancement artifacts (CAP-081C): appended only when a
        # RequirementEnhancementResult was produced. Pure projection — the result is
        # serialised/rendered as-is; nothing is re-enriched, re-related, re-observed,
        # or recomputed here.
        if data.requirement_enhancement_result is not None:
            _write_json(
                target_dir / "requirement_enhancement_result.json",
                self._enhancement.render_json(data.requirement_enhancement_result),
            )
            (target_dir / "requirement_enhancement_report.md").write_text(
                self._enhancement.render_report(data.requirement_enhancement_result),
                encoding="utf-8",
            )
            (target_dir / "requirement_enhancement_metrics.md").write_text(
                self._enhancement.render_metrics(data.requirement_enhancement_result),
                encoding="utf-8",
            )
            names += [
                "requirement_enhancement_result.json",
                "requirement_enhancement_report.md",
                "requirement_enhancement_metrics.md",
            ]
        # Recommendation artifacts (CAP-082C): appended only when a
        # RecommendationResult was produced — immediately after Quality Governance,
        # at the permanently frozen end of the pipeline. Pure projection — the
        # RecommendationResult is serialised/rendered as-is; no recommendation is
        # generated, prioritized, grouped, or scored here.
        if data.recommendation_result is not None:
            _write_json(
                target_dir / "recommendation_result.json",
                self._recommendation.render_json(data.recommendation_result),
            )
            (target_dir / "recommendation_report.md").write_text(
                self._recommendation.render_report(data.recommendation_result),
                encoding="utf-8",
            )
            (target_dir / "recommendation_metrics.md").write_text(
                self._recommendation.render_metrics(data.recommendation_result),
                encoding="utf-8",
            )
            names += [
                "recommendation_result.json",
                "recommendation_report.md",
                "recommendation_metrics.md",
            ]
        # Continuous Improvement artifacts (CAP-083C): appended only when a
        # ContinuousImprovementResult was produced — Layer 2's first capability,
        # immediately after Recommendation, at the permanently frozen end of the
        # pipeline. Pure projection — the ContinuousImprovementResult is
        # serialised/rendered as-is; no finding is observed, no trend is detected,
        # no opportunity is generated or scored here.
        if data.continuous_improvement_result is not None:
            _write_json(
                target_dir / "continuous_improvement_result.json",
                self._continuous_improvement.render_json(data.continuous_improvement_result),
            )
            (target_dir / "continuous_improvement_report.md").write_text(
                self._continuous_improvement.render_report(data.continuous_improvement_result),
                encoding="utf-8",
            )
            (target_dir / "continuous_improvement_metrics.md").write_text(
                self._continuous_improvement.render_metrics(data.continuous_improvement_result),
                encoding="utf-8",
            )
            names += [
                "continuous_improvement_result.json",
                "continuous_improvement_report.md",
                "continuous_improvement_metrics.md",
            ]
        # Knowledge Graph artifacts (CAP-084C): appended only when a
        # KnowledgeGraphResult was produced — Layer 2's second capability,
        # immediately after Continuous Improvement, at the permanently frozen end
        # of the pipeline. Pure projection — the KnowledgeGraphResult is
        # serialised/rendered as-is; no node is projected, no edge is projected,
        # no subgraph is partitioned, no observation is recorded, no finding is
        # detected here.
        if data.knowledge_graph_result is not None:
            _write_json(
                target_dir / "knowledge_graph_result.json",
                self._knowledge_graph.render_json(data.knowledge_graph_result),
            )
            (target_dir / "knowledge_graph_report.md").write_text(
                self._knowledge_graph.render_report(data.knowledge_graph_result),
                encoding="utf-8",
            )
            (target_dir / "knowledge_graph_metrics.md").write_text(
                self._knowledge_graph.render_metrics(data.knowledge_graph_result),
                encoding="utf-8",
            )
            names += [
                "knowledge_graph_result.json",
                "knowledge_graph_report.md",
                "knowledge_graph_metrics.md",
            ]
        return tuple(names)

    @staticmethod
    def _timestamps(data: ExecutionData) -> tuple[str, str]:
        """Return ``(started, completed)`` ISO timestamps for the manifest."""
        if data.result is not None:
            return data.result.started_at.isoformat(), data.result.completed_at.isoformat()
        now = datetime.now(UTC).isoformat()
        return now, now
