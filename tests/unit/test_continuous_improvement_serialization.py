"""Unit tests for the Continuous Improvement serialization layer (CAP-083C).

Covers the JSON round-trip invariant, deterministic Markdown/metrics rendering, the
ExecutionWriter integration (conditional artifacts + manifest registration + absence
when no ContinuousImprovementResult), the manifest purity boundary (the manifest
references the continuous improvement artifacts but never duplicates their content,
ADR-0022 §D10/§D11), and the frozen boundaries (serializer imports no continuous
improvement runtime; the runtime contract imports no execution package). Mirrors
``test_recommendation_serialization.py`` (CAP-082C).
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from requirement_intelligence.continuous_improvement.continuous_improvement_service import (
    DeterministicContinuousImprovementService,
)
from requirement_intelligence.continuous_improvement.engine import (
    HistoricalDataset,
    HistoricalDatasetProvider,
    HistoricalExecutionRecord,
)
from requirement_intelligence.continuous_improvement.models import (
    ContinuousImprovementResult,
    HistoricalDatasetReference,
    ImprovementSourceLayer,
)
from requirement_intelligence.continuous_improvement.policy import default_improvement_policy
from requirement_intelligence.continuous_improvement.rules import default_improvement_rule_catalog
from requirement_intelligence.continuous_improvement.serialization import (
    ContinuousImprovementSerializer,
)
from requirement_intelligence.execution.execution_writer import ExecutionWriter
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]

_CONTINUOUS_IMPROVEMENT_ARTIFACTS = (
    "continuous_improvement_result.json",
    "continuous_improvement_report.md",
    "continuous_improvement_metrics.md",
)


class _FakeProvider(HistoricalDatasetProvider):
    """A controllable stub — hands the engine a fixed, hand-built dataset."""

    def __init__(self, dataset: HistoricalDataset) -> None:
        self._dataset = dataset

    def resolve(self, historical_dataset: HistoricalDatasetReference) -> HistoricalDataset:
        return self._dataset


def _reference(**overrides: object) -> HistoricalDatasetReference:
    from datetime import UTC, datetime

    defaults: dict[str, object] = dict(
        dataset_id="ds-serialization",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-3",
        execution_count=3,
        history_window=25,
        generated_at=datetime(2026, 7, 15, tzinfo=UTC),
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _dataset_with_recurring_validation_failure(dataset_id: str) -> HistoricalDataset:
    """Three executions all recurring on VALIDATION — enough to clear the default floor."""
    executions = tuple(
        HistoricalExecutionRecord(
            execution_id=f"{dataset_id}-ex-{ordinal}",
            ordinal=ordinal,
            recurrence_flags={ImprovementSourceLayer.VALIDATION: True},
            metric_values={},
        )
        for ordinal in range(3)
    )
    return HistoricalDataset(dataset_id=dataset_id, executions=executions)


def _empty_result() -> ContinuousImprovementResult:
    """A result over a dataset with no recurrence and no trend data — the empty case."""
    service = DeterministicContinuousImprovementService(
        policy=default_improvement_policy(), rule_catalog=default_improvement_rule_catalog()
    )
    return service.improve(_reference(execution_count=1, history_window=1))


def _with_a_finding() -> ContinuousImprovementResult:
    """A result carrying at least one finding, for report content assertions."""
    reference = _reference()
    provider = _FakeProvider(_dataset_with_recurring_validation_failure(reference.dataset_id))
    service = DeterministicContinuousImprovementService(
        policy=default_improvement_policy(),
        rule_catalog=default_improvement_rule_catalog(),
        provider=provider,
    )
    return service.improve(reference)


@pytest.mark.unit
class TestJsonProjection:
    def test_round_trip_equals_original(self) -> None:
        result = _with_a_finding()
        dumped = ContinuousImprovementSerializer().render_json(result)
        assert ContinuousImprovementResult.model_validate(dumped) == result

    def test_json_is_camel_case_and_carries_versions(self) -> None:
        dumped = ContinuousImprovementSerializer().render_json(_with_a_finding())
        assert "resultVersion" in dumped
        assert "frameworkVersion" in dumped
        assert "historicalDataset" in dumped
        assert "policyVersion" in dumped

    def test_json_is_deterministic_for_the_same_result(self) -> None:
        serializer = ContinuousImprovementSerializer()
        result = _with_a_finding()
        assert json.dumps(serializer.render_json(result)) == json.dumps(
            serializer.render_json(result)
        )


@pytest.mark.unit
class TestMarkdownProjection:
    def test_report_is_deterministic_and_has_sections(self) -> None:
        serializer = ContinuousImprovementSerializer()
        result = _with_a_finding()
        report = serializer.render_report(result)
        assert report == serializer.render_report(result)
        for section in (
            "# Continuous Improvement Report",
            "## Summary",
            "## Historical Dataset",
            "## Findings",
            "## Trends",
            "## Opportunities",
        ):
            assert section in report

    def test_metrics_is_deterministic_and_has_headline(self) -> None:
        serializer = ContinuousImprovementSerializer()
        result = _with_a_finding()
        rendered = serializer.render_metrics(result)
        assert rendered == serializer.render_metrics(result)
        assert "# Continuous Improvement Metrics" in rendered
        assert "Finding density" in rendered

    def test_report_surfaces_a_finding_verbatim(self) -> None:
        # The projection never derives a finding — it renders exactly what the
        # ContinuousImprovementResult already recorded.
        serializer = ContinuousImprovementSerializer()
        result = _with_a_finding()
        assert result.findings
        report = serializer.render_report(result)
        assert str(result.findings[0].finding_id) in report
        assert result.findings[0].message in report

    def test_empty_result_still_renders_valid_sections(self) -> None:
        serializer = ContinuousImprovementSerializer()
        result = _empty_result()
        assert result.findings == ()
        assert result.trends == ()
        assert result.opportunities == ()
        report = serializer.render_report(result)
        assert "_None_" in report
        metrics = serializer.render_metrics(result)
        assert "0.000" in metrics


@pytest.mark.unit
class TestExecutionWriterIntegration:
    def test_no_continuous_improvement_result_produces_no_artifacts(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        data = replace(pipeline.execution_data, continuous_improvement_result=None)
        target = tmp_path / "no_continuous_improvement"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _CONTINUOUS_IMPROVEMENT_ARTIFACTS:
            assert not (target / name).exists()
        assert all("continuous_improvement" not in n for n in write_result.generated_artifacts)
        manifest = write_result.manifest
        assert "continuousImprovementExecuted" not in manifest
        assert "continuousImprovementReport" not in manifest

    def test_continuous_improvement_result_produces_three_artifacts_and_manifest_entries(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = pipeline.continuous_improvement_result
        data = replace(pipeline.execution_data, continuous_improvement_result=result)
        target = tmp_path / "with_continuous_improvement"
        target.mkdir()
        write_result = ExecutionWriter().write(target, data)
        for name in _CONTINUOUS_IMPROVEMENT_ARTIFACTS:
            assert (target / name).exists()
            assert name in write_result.generated_artifacts
        manifest_names = {a["name"] for a in write_result.manifest["generatedArtifacts"]}
        assert set(_CONTINUOUS_IMPROVEMENT_ARTIFACTS) <= manifest_names
        # Manifest purity (ADR-0022 §D10/§D11): the manifest is package metadata
        # only — it names the artifact, it never carries continuous improvement
        # content. The canonical findings/trends/opportunities live exclusively in
        # continuous_improvement_result.json / ContinuousImprovementResult.
        assert write_result.manifest["continuousImprovementExecuted"] is True
        assert "continuousImprovementSummary" not in write_result.manifest
        assert "continuousImprovementFindings" not in write_result.manifest
        result_path = target / "continuous_improvement_result.json"
        on_disk = json.loads(result_path.read_text(encoding="utf-8"))
        assert on_disk["summary"]["totalFindings"] == result.summary.total_findings

    def test_artifacts_are_reproducible_from_continuous_improvement_result_alone(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path / "golden")
        result = pipeline.continuous_improvement_result
        data = replace(pipeline.execution_data, continuous_improvement_result=result)
        target = tmp_path / "repro"
        target.mkdir()
        ExecutionWriter().write(target, data)
        serializer = ContinuousImprovementSerializer()
        assert (target / "continuous_improvement_report.md").read_text(encoding="utf-8") == (
            serializer.render_report(result)
        )
        assert (target / "continuous_improvement_metrics.md").read_text(encoding="utf-8") == (
            serializer.render_metrics(result)
        )
        assert json.loads(
            (target / "continuous_improvement_result.json").read_text(encoding="utf-8")
        ) == serializer.render_json(result)


@pytest.mark.unit
class TestSerializationBoundary:
    def test_serializer_imports_no_continuous_improvement_runtime(self) -> None:
        source = (
            _REPO_ROOT
            / "requirement_intelligence"
            / "continuous_improvement"
            / "serialization"
            / "continuous_improvement_serializer.py"
        ).read_text(encoding="utf-8")
        forbidden = (
            "continuous_improvement.engine",
            "continuous_improvement_service",
            "continuous_improvement.policy",
            "continuous_improvement.rules",
            "DeterministicContinuousImprovementEngine",
            "DeterministicContinuousImprovementService",
            "ContinuousImprovementService",
            "ImprovementPolicy",
            "ImprovementRuleCatalog",
            "HistoricalDatasetProvider",
            "PlatformContext",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line, f"serializer must not import {token!r}"

    def test_runtime_contract_imports_no_execution_package(self) -> None:
        """ContinuousImprovementResult must never depend on the Execution Package."""
        source = (
            _REPO_ROOT
            / "requirement_intelligence"
            / "continuous_improvement"
            / "models"
            / "result.py"
        ).read_text(encoding="utf-8")
        assert "requirement_intelligence.execution" not in source
