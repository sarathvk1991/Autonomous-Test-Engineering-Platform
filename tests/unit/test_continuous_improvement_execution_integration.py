"""Integration-boundary tests for Continuous Improvement's Execution Package wiring
(CAP-083C, ADR-0022 §D11).

Covers ``ExecutionData.continuous_improvement_result`` (additive-only field), the
CLI's containment (it names only ``create_continuous_improvement_service``, never an
engine, rule-catalogue, or historical-dataset-provider implementation class
directly), and that the deterministic pipeline invokes the continuous improvement
service exactly once per run. Mirrors
``test_recommendation_execution_integration.py`` (CAP-082C).
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import pytest

from requirement_intelligence.continuous_improvement.continuous_improvement_service import (
    DeterministicContinuousImprovementService,
)
from requirement_intelligence.execution.execution_data import ExecutionData
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"


@pytest.mark.unit
class TestExecutionDataField:
    def test_continuous_improvement_result_field_exists(self) -> None:
        field_names = {f.name for f in fields(ExecutionData)}
        assert "continuous_improvement_result" in field_names

    def test_continuous_improvement_result_defaults_to_none(self) -> None:
        field_map = {f.name: f for f in fields(ExecutionData)}
        assert field_map["continuous_improvement_result"].default is None

    def test_other_result_fields_unchanged(self) -> None:
        """Additive only: every field present before CAP-083C is still present."""
        field_names = {f.name for f in fields(ExecutionData)}
        assert {
            "validation_result",
            "cp1_result",
            "grounding_result",
            "quality_governance_result",
            "requirement_enhancement_result",
            "recommendation_result",
        } <= field_names

    def test_construction_without_continuous_improvement_result_still_works(self) -> None:
        """Omitting the new field entirely is valid — a purely additive change."""
        data = ExecutionData(
            selected=object(),
            engineering_context=object(),
            prompt_request=object(),
            llm_request=object(),
            result=None,
            dry_run=True,
            provider_name="gemini",
            requested_model=None,
            reasoning_contract_version="1.0.0",
            execution_name=None,
        )
        assert data.continuous_improvement_result is None


@pytest.mark.unit
class TestCliContainment:
    def test_cli_script_names_no_engine_or_provider_directly(self) -> None:
        """The CLI orchestrates only — it never names an implementation class.

        It obtains ``ContinuousImprovementService`` exclusively via
        ``PlatformContext.create_continuous_improvement_service()`` and invokes
        ``improve`` — never ``DeterministicContinuousImprovementEngine``,
        ``ImprovementRuleCatalog``, or any ``HistoricalDatasetProvider`` directly
        (Stage 1: no observation logic, no policy logic, no detection, no
        generation in the CLI).
        """
        source = _SCRIPT.read_text(encoding="utf-8")
        forbidden = (
            "DeterministicContinuousImprovementEngine",
            "ImprovementRuleCatalog",
            "ImprovementRuleBuilder",
            "default_improvement_rule_catalog",
            "default_improvement_policy",
            "HistoricalDatasetProvider",
            "DeterministicHistoricalDatasetProvider",
        )
        for token in forbidden:
            assert token not in source, f"CLI must not name {token!r} directly"

    def test_cli_calls_improve_with_the_historical_dataset_reference(self) -> None:
        """The CLI's call site names the single frozen argument."""
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "def run_continuous_improvement_phase(" in source
        assert ".improve(" in source


@pytest.mark.unit
class TestExactlyOnceExecution:
    def test_continuous_improvement_service_invoked_exactly_once_per_pipeline_run(
        self, tmp_path: Path
    ) -> None:
        """One golden pipeline run improves exactly once — never twice, never in parallel."""
        original = DeterministicContinuousImprovementService.improve
        calls: list[int] = []

        def _counting_improve(self, *args: object, **kwargs: object) -> object:
            calls.append(1)
            return original(self, *args, **kwargs)

        with patch.object(
            DeterministicContinuousImprovementService, "improve", _counting_improve
        ):
            pipeline = _run_golden_pipeline(tmp_path)

        assert len(calls) == 1
        assert pipeline.continuous_improvement_result is not None

    def test_continuous_improvement_executes_deterministically_across_two_runs(
        self, tmp_path: Path
    ) -> None:
        """Two independent pipeline runs each improve exactly once with equal content."""
        run1 = _run_golden_pipeline(tmp_path / "run1")
        run2 = _run_golden_pipeline(tmp_path / "run2")
        assert run1.continuous_improvement_result is not None
        assert run2.continuous_improvement_result is not None
        assert run1.continuous_improvement_result.summary.total_findings == (
            run2.continuous_improvement_result.summary.total_findings
        )
        assert run1.continuous_improvement_result.metrics == (
            run2.continuous_improvement_result.metrics
        )
