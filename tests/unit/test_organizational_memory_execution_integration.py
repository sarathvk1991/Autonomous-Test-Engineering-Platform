"""Integration-boundary tests for Organizational Memory's Execution Package
wiring (CAP-085C, ADR-0027 §D19).

Covers ``ExecutionData.organizational_memory_result`` (additive-only field),
the CLI's containment (it names only ``create_organizational_memory_service``,
never an engine, policy, or rule-catalogue implementation class directly), and
that the deterministic pipeline invokes the Organizational Memory service
exactly once per run. Mirrors ``test_knowledge_graph_execution_integration.py``
(CAP-084C) — with one structural difference: Organizational Memory consumes no
``HistoricalDatasetReference`` and mints no minting-helper of its own (ADR-0025
§Stage 7/8's fan-in exception), so there is no minting-strategy-reuse test.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import pytest

from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.organizational_memory.organizational_memory_service import (
    DeterministicOrganizationalMemoryService,
)
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"


@pytest.mark.unit
class TestExecutionDataField:
    def test_organizational_memory_result_field_exists(self) -> None:
        field_names = {f.name for f in fields(ExecutionData)}
        assert "organizational_memory_result" in field_names

    def test_organizational_memory_result_defaults_to_none(self) -> None:
        field_map = {f.name: f for f in fields(ExecutionData)}
        assert field_map["organizational_memory_result"].default is None

    def test_other_result_fields_unchanged(self) -> None:
        """Additive only: every field present before CAP-085C is still present."""
        field_names = {f.name for f in fields(ExecutionData)}
        assert {
            "validation_result",
            "cp1_result",
            "grounding_result",
            "quality_governance_result",
            "requirement_enhancement_result",
            "recommendation_result",
            "continuous_improvement_result",
            "knowledge_graph_result",
        } <= field_names

    def test_construction_without_organizational_memory_result_still_works(self) -> None:
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
        assert data.organizational_memory_result is None


@pytest.mark.unit
class TestCliContainment:
    def test_cli_script_names_no_engine_or_policy_directly(self) -> None:
        """The CLI orchestrates only — it never names an implementation class.

        It obtains ``OrganizationalMemoryService`` exclusively via
        ``PlatformContext.create_organizational_memory_service()`` and invokes
        ``build`` — never ``DeterministicOrganizationalMemoryEngine``,
        ``PromotionRuleCatalog``, or ``OrganizationalMemoryPolicy`` directly
        (Stage 1: no curation logic, no policy logic, no promotion, no
        lifecycle recording in the CLI).
        """
        source = _SCRIPT.read_text(encoding="utf-8")
        forbidden = (
            "DeterministicOrganizationalMemoryEngine",
            "PromotionRuleCatalog",
            "PromotionRuleBuilder",
            "default_promotion_rule_catalog",
            "default_organizational_memory_policy",
        )
        for token in forbidden:
            assert token not in source, f"CLI must not name {token!r} directly"

    def test_cli_calls_build_with_the_two_peer_results(self) -> None:
        """The CLI's call site names the two frozen arguments — no HistoricalDatasetReference."""
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "def run_organizational_memory_phase(" in source
        assert (
            "context.create_organizational_memory_service().build(\n"
            "        continuous_improvement_result, knowledge_graph_result\n"
            "    )" in source
        )

    def test_no_historical_dataset_reference_is_minted_for_organizational_memory(self) -> None:
        """Unlike its two peers, Organizational Memory mints no reference of its own.

        ADR-0025 §Stage 7/8's fan-in exception: it consumes the two
        already-completed Layer 2 peer results directly, never a
        ``HistoricalDatasetReference`` — so no third minting helper exists.
        """
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "_historical_dataset_reference_for_execution(" in source
        assert "_knowledge_graph_historical_dataset_reference_for_execution(" in source
        assert "_organizational_memory_historical_dataset_reference_for_execution(" not in source

    def test_organizational_memory_phase_is_wired_after_knowledge_graph(self) -> None:
        """The CLI orchestrates Organizational Memory strictly after Knowledge Graph."""
        source = _SCRIPT.read_text(encoding="utf-8")
        kg_call = source.index("run_knowledge_graph_phase(\n")
        om_call = source.index("run_organizational_memory_phase(\n")
        assert kg_call < om_call, "Organizational Memory must be wired after Knowledge Graph"


@pytest.mark.unit
class TestExactlyOnceExecution:
    def test_organizational_memory_service_invoked_exactly_once_per_pipeline_run(
        self, tmp_path: Path
    ) -> None:
        """One golden pipeline run builds exactly once — never twice, never in parallel."""
        original = DeterministicOrganizationalMemoryService.build
        calls: list[int] = []

        def _counting_build(self, *args: object, **kwargs: object) -> object:
            calls.append(1)
            return original(self, *args, **kwargs)

        with patch.object(DeterministicOrganizationalMemoryService, "build", _counting_build):
            pipeline = _run_golden_pipeline(tmp_path)

        assert len(calls) == 1
        assert pipeline.organizational_memory_result is not None

    def test_organizational_memory_executes_deterministically_for_fixed_peer_results(
        self, tmp_path: Path
    ) -> None:
        """The same two consumed peer results, built twice, yield the same content."""
        from requirement_intelligence.platform.platform_context import PlatformContext

        pipeline = _run_golden_pipeline(tmp_path)
        r1 = pipeline.organizational_memory_result
        assert r1 is not None
        r2 = (
            PlatformContext()
            .create_organizational_memory_service()
            .build(pipeline.continuous_improvement_result, pipeline.knowledge_graph_result)
        )
        assert r1.experiences == r2.experiences
        assert r1.lessons == r2.lessons
        assert r1.metrics == r2.metrics
