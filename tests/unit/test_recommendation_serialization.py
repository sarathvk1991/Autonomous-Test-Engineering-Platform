"""Unit tests for the Recommendation serialization layer (CAP-082C).

Covers the JSON round-trip invariant, deterministic Markdown/metrics rendering, the
ExecutionWriter integration (conditional artifacts + manifest registration + absence
when no RecommendationResult), the manifest purity boundary (the manifest references
the recommendation artifacts but never duplicates recommendation content, ADR-0019
§D9/§D10), and the frozen boundaries (serializer imports no recommendation runtime;
the runtime contract imports no execution package).
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from requirement_intelligence.enhancement.models.enums import (
    EnhancementSeverity,
    ObservationCategory,
)
from requirement_intelligence.execution.execution_writer import ExecutionWriter
from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.quality_governance.models.enums import QualityDecision
from requirement_intelligence.recommendation.models.result import RecommendationResult
from requirement_intelligence.recommendation.serialization import RecommendationSerializer
from tests.productization.conftest import _run_golden_pipeline
from tests.unit.recommendation_helpers import (
    make_cp1_result,
    make_enhancement_finding,
    make_enhancement_result,
    make_grounding_result,
    make_quality_finding,
    make_quality_governance_result,
    make_validation_result,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

_RECOMMENDATION_ARTIFACTS = (
    "recommendation_result.json",
    "recommendation_report.md",
    "recommendation_metrics.md",
)


def _recommendation_result(**kwargs: object) -> RecommendationResult:
    """Recommend from tunable peer results via the registered service (no runtime redesign).

    Uses the registered ``RecommendationService`` — the same composition root the
    runtime uses — so the serializer is exercised against a genuine runtime contract,
    never a hand-rolled stand-in. A single ``recommend`` call fixes the provenance
    timestamps, so the same object can be serialised twice for byte-for-byte
    determinism assertions.
    """
    service = PlatformContext().create_recommendation_service()
    return service.recommend(
        make_enhancement_result(**kwargs.get("enhancement", {})),  # type: ignore[arg-type]
        make_grounding_result(**kwargs.get("grounding", {})),  # type: ignore[arg-type]
        make_validation_result(**kwargs.get("validation", {})),  # type: ignore[arg-type]
        make_cp1_result(**kwargs.get("cp1", {})),  # type: ignore[arg-type]
        make_quality_governance_result(**kwargs.get("quality_governance", {})),  # type: ignore[arg-type]
    )


def _with_a_recommendation() -> RecommendationResult:
    """A result carrying at least one recommendation, for report content assertions."""
    finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
    return _recommendation_result(enhancement={"findings": (finding,)})


@pytest.mark.unit
class TestJsonProjection:
    def test_round_trip_equals_original(self) -> None:
        result = _with_a_recommendation()
        dumped = RecommendationSerializer().render_json(result)
        assert RecommendationResult.model_validate(dumped) == result

    def test_json_is_camel_case_and_carries_versions(self) -> None:
        dumped = RecommendationSerializer().render_json(_with_a_recommendation())
        assert "resultVersion" in dumped
        assert "frameworkVersion" in dumped
        assert "consumedInputs" in dumped
        assert "policyVersion" in dumped

    def test_json_is_deterministic_for_the_same_result(self) -> None:
        serializer = RecommendationSerializer()
        result = _with_a_recommendation()
        assert json.dumps(serializer.render_json(result)) == json.dumps(
            serializer.render_json(result)
        )


@pytest.mark.unit
class TestMarkdownProjection:
    def test_report_is_deterministic_and_has_sections(self) -> None:
        serializer = RecommendationSerializer()
        result = _with_a_recommendation()
        report = serializer.render_report(result)
        assert report == serializer.render_report(result)
        for section in (
            "# Recommendation Report",
            "## Summary",
            "## Priority Distribution",
            "## Recommendations",
            "## Groups",
            "## Consumed Inputs",
        ):
            assert section in report

    def test_metrics_is_deterministic_and_has_headline(self) -> None:
        serializer = RecommendationSerializer()
        result = _with_a_recommendation()
        rendered = serializer.render_metrics(result)
        assert rendered == serializer.render_metrics(result)
        assert "# Recommendation Metrics" in rendered
        assert "Recommendation density" in rendered

    def test_report_surfaces_a_recommendation_verbatim(self) -> None:
        # The projection never derives a recommendation — it renders exactly what
        # the RecommendationResult already recorded.
        serializer = RecommendationSerializer()
        result = _with_a_recommendation()
        assert result.recommendations
        report = serializer.render_report(result)
        assert str(result.recommendations[0].recommendation_id) in report
        assert result.recommendations[0].title in report

    def test_empty_result_still_renders_valid_sections(self) -> None:
        serializer = RecommendationSerializer()
        result = _recommendation_result()
        assert result.recommendations == ()
        report = serializer.render_report(result)
        assert "_None_" in report
        metrics = serializer.render_metrics(result)
        assert "0.000" in metrics

    def test_multiple_recommendations_each_appear_in_the_report(self) -> None:
        findings = (
            make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY),
            make_enhancement_finding(
                "ef-2",
                category=ObservationCategory.CONSISTENCY,
                severity=EnhancementSeverity.CRITICAL,
            ),
        )
        result = _recommendation_result(enhancement={"findings": findings})
        assert len(result.recommendations) == 2
        report = RecommendationSerializer().render_report(result)
        for recommendation in result.recommendations:
            assert str(recommendation.recommendation_id) in report

    def test_source_and_type_distribution_counts_sum_to_total(self) -> None:
        findings = (
            make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY),
            make_enhancement_finding("ef-2", category=ObservationCategory.DUPLICATION),
        )
        quality_finding = make_quality_finding("qf-1", severity="failure")
        result = _recommendation_result(
            enhancement={"findings": findings},
            quality_governance={"findings": (quality_finding,), "decision": QualityDecision.FAIL},
        )
        serializer = RecommendationSerializer()
        source_counts = serializer._source_counts(result)
        type_counts = serializer._type_counts(result)
        assert sum(count for _, count in source_counts) == len(result.recommendations)
        assert sum(count for _, count in type_counts) == len(result.recommendations)


@pytest.mark.unit
class TestExecutionWriterIntegration:
    def test_no_recommendation_result_produces_no_artifacts(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        data = replace(pipeline.execution_data, recommendation_result=None)
        target = tmp_path / "no_recommendation"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _RECOMMENDATION_ARTIFACTS:
            assert not (target / name).exists()
        assert all("recommendation" not in n for n in write_result.generated_artifacts)
        manifest = write_result.manifest
        assert "recommendationExecuted" not in manifest
        assert "recommendationReport" not in manifest

    def test_recommendation_result_produces_three_artifacts_and_manifest_entries(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = pipeline.recommendation_result
        data = replace(pipeline.execution_data, recommendation_result=result)
        target = tmp_path / "with_recommendation"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _RECOMMENDATION_ARTIFACTS:
            assert (target / name).exists()
            assert name in write_result.generated_artifacts
        manifest_names = {a["name"] for a in write_result.manifest["generatedArtifacts"]}
        assert set(_RECOMMENDATION_ARTIFACTS) <= manifest_names
        # Manifest purity (ADR-0019 §D9/§D10): the manifest is package metadata
        # only — it names the artifact, it never carries recommendation content. The
        # canonical recommendations live exclusively in recommendation_result.json /
        # RecommendationResult.
        assert write_result.manifest["recommendationExecuted"] is True
        assert "recommendationSummary" not in write_result.manifest
        assert "recommendationPriority" not in write_result.manifest
        result_path = target / "recommendation_result.json"
        on_disk = json.loads(result_path.read_text(encoding="utf-8"))
        assert on_disk["summary"]["totalRecommendations"] == result.summary.total_recommendations

    def test_artifacts_are_reproducible_from_recommendation_result_alone(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = pipeline.recommendation_result
        data = replace(pipeline.execution_data, recommendation_result=result)
        target = tmp_path / "repro"
        target.mkdir()
        ExecutionWriter().write(target, data)
        serializer = RecommendationSerializer()
        assert (target / "recommendation_report.md").read_text(encoding="utf-8") == (
            serializer.render_report(result)
        )
        assert (target / "recommendation_metrics.md").read_text(encoding="utf-8") == (
            serializer.render_metrics(result)
        )
        assert json.loads(
            (target / "recommendation_result.json").read_text(encoding="utf-8")
        ) == serializer.render_json(result)


@pytest.mark.unit
class TestSerializationBoundary:
    def test_serializer_imports_no_recommendation_runtime(self) -> None:
        source = (
            _REPO_ROOT
            / "requirement_intelligence"
            / "recommendation"
            / "serialization"
            / "recommendation_serializer.py"
        ).read_text(encoding="utf-8")
        forbidden = (
            "recommendation.engine",
            "recommendation.recommendation_service",
            "recommendation.policy",
            "recommendation.rules",
            "DeterministicRecommendationEngine",
            "DeterministicRecommendationService",
            "RecommendationService",
            "RecommendationPolicy",
            "RecommendationRuleCatalog",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"serializer must not import {token!r}"

    def test_runtime_contract_imports_no_execution_package(self) -> None:
        """RecommendationResult must never depend on the Execution Package."""
        source = (
            _REPO_ROOT / "requirement_intelligence" / "recommendation" / "models" / "result.py"
        ).read_text(encoding="utf-8")
        assert "requirement_intelligence.execution" not in source
