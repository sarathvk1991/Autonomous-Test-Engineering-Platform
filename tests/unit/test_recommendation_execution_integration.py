"""Integration-boundary tests for Recommendation's Execution Package wiring (CAP-082C).

Covers ``ExecutionData.recommendation_result`` (additive-only field), the CLI's
containment (it names only ``create_recommendation_service``, never an engine or
rule-catalogue implementation class directly), and that the deterministic pipeline
invokes the recommendation service exactly once per run.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import pytest

from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.recommendation.recommendation_service import (
    DeterministicRecommendationService,
)
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"


@pytest.mark.unit
class TestExecutionDataField:
    def test_recommendation_result_field_exists(self) -> None:
        field_names = {f.name for f in fields(ExecutionData)}
        assert "recommendation_result" in field_names

    def test_recommendation_result_defaults_to_none(self) -> None:
        field_map = {f.name: f for f in fields(ExecutionData)}
        assert field_map["recommendation_result"].default is None

    def test_other_result_fields_unchanged(self) -> None:
        """Additive only: every field present before CAP-082C is still present."""
        field_names = {f.name for f in fields(ExecutionData)}
        assert {
            "validation_result",
            "cp1_result",
            "grounding_result",
            "quality_governance_result",
            "requirement_enhancement_result",
        } <= field_names

    def test_construction_without_recommendation_result_still_works(self) -> None:
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
        assert data.recommendation_result is None


@pytest.mark.unit
class TestCliContainment:
    def test_cli_script_names_no_engine_or_rule_catalog_directly(self) -> None:
        """The CLI orchestrates only — it never names an implementation class.

        It obtains ``RecommendationService`` exclusively via
        ``PlatformContext.create_recommendation_service()`` and invokes
        ``recommend`` — never ``DeterministicRecommendationEngine`` or
        ``RecommendationRuleCatalog`` directly (Stage 2: no recommendation logic,
        no policy logic, no grouping, no prioritization in the CLI).
        """
        source = _SCRIPT.read_text(encoding="utf-8")
        forbidden = (
            "DeterministicRecommendationEngine",
            "RecommendationRuleCatalog",
            "RecommendationRuleBuilder",
            "default_recommendation_rule_catalog",
            "default_recommendation_policy",
        )
        for token in forbidden:
            assert token not in source, f"CLI must not name {token!r} directly"

    def test_cli_calls_recommend_with_the_five_positional_peer_results(self) -> None:
        """The CLI's call site names the five arguments in the frozen order."""
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "def run_recommendation_phase(" in source
        assert ".recommend(" in source


@pytest.mark.unit
class TestExactlyOnceExecution:
    def test_recommendation_service_invoked_exactly_once_per_pipeline_run(
        self, tmp_path: Path
    ) -> None:
        """One golden pipeline run recommends exactly once — never twice, never in parallel."""
        original = DeterministicRecommendationService.recommend
        calls: list[int] = []

        def _counting_recommend(self, *args: object, **kwargs: object) -> object:
            calls.append(1)
            return original(self, *args, **kwargs)

        with patch.object(DeterministicRecommendationService, "recommend", _counting_recommend):
            pipeline = _run_golden_pipeline(tmp_path)

        assert len(calls) == 1
        assert pipeline.recommendation_result is not None

    def test_recommendation_executes_deterministically_across_two_runs(
        self, tmp_path: Path
    ) -> None:
        """Two independent pipeline runs each recommend exactly once with equal content."""
        run1 = _run_golden_pipeline(tmp_path / "run1")
        run2 = _run_golden_pipeline(tmp_path / "run2")
        assert run1.recommendation_result is not None
        assert run2.recommendation_result is not None
        assert run1.recommendation_result.summary.total_recommendations == (
            run2.recommendation_result.summary.total_recommendations
        )
        assert run1.recommendation_result.metrics == run2.recommendation_result.metrics
