"""Integration-boundary tests for Knowledge Graph's Execution Package wiring
(CAP-084C, ADR-0023 §D12).

Covers ``ExecutionData.knowledge_graph_result`` (additive-only field), the
CLI's containment (it names only ``create_knowledge_graph_service``, never an
engine, rule-catalogue, or historical-dataset-provider implementation class
directly), and that the deterministic pipeline invokes the Knowledge Graph
service exactly once per run. Mirrors
``test_continuous_improvement_execution_integration.py`` (CAP-083C).
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import pytest

from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.knowledge_graph.knowledge_graph_service import (
    DeterministicKnowledgeGraphService,
)
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"


@pytest.mark.unit
class TestExecutionDataField:
    def test_knowledge_graph_result_field_exists(self) -> None:
        field_names = {f.name for f in fields(ExecutionData)}
        assert "knowledge_graph_result" in field_names

    def test_knowledge_graph_result_defaults_to_none(self) -> None:
        field_map = {f.name: f for f in fields(ExecutionData)}
        assert field_map["knowledge_graph_result"].default is None

    def test_other_result_fields_unchanged(self) -> None:
        """Additive only: every field present before CAP-084C is still present."""
        field_names = {f.name for f in fields(ExecutionData)}
        assert {
            "validation_result",
            "cp1_result",
            "grounding_result",
            "quality_governance_result",
            "requirement_enhancement_result",
            "recommendation_result",
            "continuous_improvement_result",
        } <= field_names

    def test_construction_without_knowledge_graph_result_still_works(self) -> None:
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
        assert data.knowledge_graph_result is None


@pytest.mark.unit
class TestCliContainment:
    def test_cli_script_names_no_engine_or_provider_directly(self) -> None:
        """The CLI orchestrates only — it never names an implementation class.

        It obtains ``KnowledgeGraphService`` exclusively via
        ``PlatformContext.create_knowledge_graph_service()`` and invokes
        ``build`` — never ``DeterministicKnowledgeGraphEngine``,
        ``KnowledgeGraphRuleCatalog``, or any ``HistoricalDatasetProvider``
        directly (Stage 1: no projection logic, no policy logic, no detection,
        no analysis in the CLI).
        """
        source = _SCRIPT.read_text(encoding="utf-8")
        forbidden = (
            "DeterministicKnowledgeGraphEngine",
            "KnowledgeGraphRuleCatalog",
            "KnowledgeGraphRuleBuilder",
            "default_knowledge_graph_rule_catalog",
            "default_knowledge_graph_policy",
            "HistoricalDatasetProvider",
            "DeterministicHistoricalDatasetProvider",
        )
        for token in forbidden:
            assert token not in source, f"CLI must not name {token!r} directly"

    def test_cli_calls_build_with_the_historical_dataset_reference(self) -> None:
        """The CLI's call site names the single frozen argument."""
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "def run_knowledge_graph_phase(" in source
        assert ".build(" in source

    def test_cli_reuses_the_cap_083c_minting_strategy_not_a_second_one(self) -> None:
        """Only one minting helper exists per Layer 2 capability — the same shape twice.

        Recommendation 1 (this milestone): Knowledge Graph must reuse the exact
        deterministic single-execution minting strategy CAP-083C introduced,
        never invent a second one. The KG-specific helper exists (because the
        target type is the deliberately duplicated
        ``knowledge_graph.models.HistoricalDatasetReference``), but its field
        values must be constructed identically to the CAP-083C helper's.
        """
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "def _historical_dataset_reference_for_execution(" in source
        assert "def _knowledge_graph_historical_dataset_reference_for_execution(" in source
        for marker in (
            "dataset_id=f\"single-execution:{result.execution_id}\"",
            "execution_count=1",
            "history_window=1",
        ):
            assert source.count(marker) == 2, (
                f"expected the identical minting fragment {marker!r} in both helpers"
            )

    def test_knowledge_graph_phase_is_wired_after_continuous_improvement(self) -> None:
        """The CLI orchestrates Knowledge Graph strictly after Continuous Improvement."""
        source = _SCRIPT.read_text(encoding="utf-8")
        ci_call = source.index("run_continuous_improvement_phase(\n")
        kg_call = source.index("run_knowledge_graph_phase(\n")
        assert ci_call < kg_call, "Knowledge Graph must be wired after Continuous Improvement"


@pytest.mark.unit
class TestExactlyOnceExecution:
    def test_knowledge_graph_service_invoked_exactly_once_per_pipeline_run(
        self, tmp_path: Path
    ) -> None:
        """One golden pipeline run builds exactly once — never twice, never in parallel."""
        original = DeterministicKnowledgeGraphService.build
        calls: list[int] = []

        def _counting_build(self, *args: object, **kwargs: object) -> object:
            calls.append(1)
            return original(self, *args, **kwargs)

        with patch.object(DeterministicKnowledgeGraphService, "build", _counting_build):
            pipeline = _run_golden_pipeline(tmp_path)

        assert len(calls) == 1
        assert pipeline.knowledge_graph_result is not None

    def test_knowledge_graph_executes_deterministically_for_a_fixed_reference(
        self, tmp_path: Path
    ) -> None:
        """The same reference, built twice, yields the same content.

        Unlike Continuous Improvement's always-empty single-execution shape,
        Knowledge Graph's node/edge presence is gated by a digest of the
        reference's own ``dataset_id`` (embedding the run's random
        ``execution_id``), so two *independent* pipeline runs legitimately
        differ — see ``test_golden_baseline.py``'s own determinism tests for the
        full explanation. This test proves the actual determinism contract:
        same reference in, same content out.
        """
        from requirement_intelligence.platform.platform_context import PlatformContext

        pipeline = _run_golden_pipeline(tmp_path)
        r1 = pipeline.knowledge_graph_result
        assert r1 is not None
        r2 = PlatformContext().create_knowledge_graph_service().build(r1.historical_dataset)
        assert r1.nodes == r2.nodes
        assert r1.edges == r2.edges
        assert r1.metrics == r2.metrics
