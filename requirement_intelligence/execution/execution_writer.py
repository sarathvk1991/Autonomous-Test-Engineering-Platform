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

from requirement_intelligence.execution.baseline_metrics_builder import (
    BaselineMetricsBuilder,
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

_CORE_ARTIFACTS = ("consolidated_artifact.json", "prompt.txt", "llm_request.json")
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
        """Write the three artifacts produced for every run (incl. dry runs)."""
        _write_json(
            target_dir / "consolidated_artifact.json",
            data.selected.model_dump(mode="json", by_alias=True),
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
        ``ValidationResult`` was supplied (i.e. validation was executed). The writer
        performs no validation and no judgment — it serialises the result as-is and
        renders a presentation-only report from it, so the execution package owns
        persistence and reporting while validation stays read-only.
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
        (target_dir / "baseline_metrics.md").write_text(
            self._metrics.build(data), encoding="utf-8"
        )
        (target_dir / "review.md").write_text(self._review.build(data), encoding="utf-8")
        if data.validation_result is None:
            return _RESULT_ARTIFACTS
        _write_json(
            target_dir / "validation_result.json",
            data.validation_result.model_dump(mode="json", by_alias=True),
        )
        (target_dir / "validation_report.md").write_text(
            self._validation_report.build(data), encoding="utf-8"
        )
        return (*_RESULT_ARTIFACTS, "validation_result.json", "validation_report.md")

    @staticmethod
    def _timestamps(data: ExecutionData) -> tuple[str, str]:
        """Return ``(started, completed)`` ISO timestamps for the manifest."""
        if data.result is not None:
            return data.result.started_at.isoformat(), data.result.completed_at.isoformat()
        now = datetime.now(UTC).isoformat()
        return now, now
