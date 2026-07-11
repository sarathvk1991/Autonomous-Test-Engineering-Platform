"""Unit tests for the Grounding serialization layer (CAP-077F.1).

Covers the JSON round-trip invariant, deterministic Markdown rendering, the ExecutionWriter
integration (conditional artifacts + manifest registration + absence when no GroundingResult),
and the frozen boundary (serializer imports no grounding runtime component).
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from requirement_intelligence.execution.execution_writer import ExecutionWriter
from requirement_intelligence.grounding import (
    GroundingAssessmentBuilder,
    GroundingMetricsBuilder,
    GroundingResult,
    GroundingResultBuilder,
    GroundingSerializer,
)
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXED = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)

_GROUNDING_ARTIFACTS = ("grounding_result.json", "grounding_report.md", "grounding_metrics.md")


def _grounding_result() -> GroundingResult:
    metrics = GroundingMetricsBuilder().build([], evidence_available=0)
    summary = GroundingMetricsBuilder().build_summary([], metrics)
    assessment = GroundingAssessmentBuilder().build(
        context_id="ctx-x", grounded_requirements=(), metrics=metrics, summary=summary
    )
    return GroundingResultBuilder().build(
        analysis_id="a-1",
        execution_id="e-1",
        assessment=assessment,
        started_at=_FIXED,
        completed_at=_FIXED,
    )


@pytest.mark.unit
class TestJsonProjection:
    def test_round_trip_equals_original(self) -> None:
        result = _grounding_result()
        dumped = GroundingSerializer().render_json(result)
        assert GroundingResult.model_validate(dumped) == result

    def test_json_is_camel_case_and_carries_versions(self) -> None:
        dumped = GroundingSerializer().render_json(_grounding_result())
        assert "resultVersion" in dumped
        assert dumped["analysisId"] == "a-1"

    def test_json_is_deterministic(self) -> None:
        serializer = GroundingSerializer()
        one = json.dumps(serializer.render_json(_grounding_result()))
        two = json.dumps(serializer.render_json(_grounding_result()))
        assert one == two


@pytest.mark.unit
class TestMarkdownProjection:
    def test_report_is_deterministic_and_has_sections(self) -> None:
        serializer = GroundingSerializer()
        report = serializer.render_report(_grounding_result())
        assert report == serializer.render_report(_grounding_result())
        for section in (
            "# Grounding Report",
            "## Summary",
            "## Classification Distribution",
            "## Requirements",
            "## Findings",
            "## Recommendations",
        ):
            assert section in report

    def test_metrics_is_deterministic_and_has_sections(self) -> None:
        serializer = GroundingSerializer()
        rendered = serializer.render_metrics(_grounding_result())
        assert rendered == serializer.render_metrics(_grounding_result())
        assert "# Grounding Metrics" in rendered
        assert "Hallucination rate" in rendered
        assert "Grounding score" in rendered


@pytest.mark.unit
class TestExecutionWriterIntegration:
    def test_no_grounding_result_produces_no_artifacts(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        data = replace(pipeline.execution_data, grounding_result=None)
        target = tmp_path / "no_grounding"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _GROUNDING_ARTIFACTS:
            assert not (target / name).exists()
        assert all("grounding" not in n for n in write_result.generated_artifacts)
        manifest_names = {a["name"] for a in write_result.manifest["generatedArtifacts"]}
        assert not any("grounding" in n for n in manifest_names)

    def test_grounding_result_produces_three_artifacts_registered_in_manifest(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        data = replace(pipeline.execution_data, grounding_result=_grounding_result())
        target = tmp_path / "with_grounding"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _GROUNDING_ARTIFACTS:
            assert (target / name).exists()
            assert name in write_result.generated_artifacts
        manifest_names = {a["name"] for a in write_result.manifest["generatedArtifacts"]}
        assert set(_GROUNDING_ARTIFACTS) <= manifest_names

    def test_artifacts_are_reproducible_from_grounding_result_alone(self, tmp_path: Path) -> None:
        # The written files match a direct projection of the same GroundingResult.
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = _grounding_result()
        data = replace(pipeline.execution_data, grounding_result=result)
        target = tmp_path / "repro"
        target.mkdir()
        ExecutionWriter().write(target, data)
        serializer = GroundingSerializer()
        assert (target / "grounding_report.md").read_text(encoding="utf-8") == (
            serializer.render_report(result)
        )
        assert (target / "grounding_metrics.md").read_text(encoding="utf-8") == (
            serializer.render_metrics(result)
        )
        assert json.loads((target / "grounding_result.json").read_text(encoding="utf-8")) == (
            serializer.render_json(result)
        )


@pytest.mark.unit
class TestSerializationBoundary:
    def test_serializer_imports_no_runtime(self) -> None:
        source = (
            _REPO_ROOT
            / "requirement_intelligence"
            / "grounding"
            / "serialization"
            / "grounding_serializer.py"
        ).read_text(encoding="utf-8")
        forbidden = (
            "grounding.strategies",
            "grounding.normalization",
            "grounding.matching",
            "grounding.classification",
            "grounding.confidence",
            "grounding.pipeline",
            "grounding.metrics_builder",
            "grounding.grounding_service",
            "GroundingPipeline",
            "SupportClassificationEngine",
            "ConfidenceCalculator",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line
