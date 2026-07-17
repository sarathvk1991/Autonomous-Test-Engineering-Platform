"""Integration-boundary tests for Learning's Execution Package wiring
(CAP-086C, ADR-0029 §D29).

Covers ``ExecutionData.learning_result`` (additive-only field), the CLI's
containment (it names only ``create_learning_service``, never an engine,
policy, or rule-catalogue implementation class directly), and that the
deterministic pipeline invokes the Learning service exactly once per run.
Mirrors ``test_organizational_memory_execution_integration.py`` (CAP-085C) —
with one structural difference: Learning consumes exactly one already-
completed Layer 2 tier, never a two-peer fan-in (ADR-0028 §Stage 12,
ADR-0029 §D2), so there is no fan-in-argument test.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import pytest

from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.learning.learning_service import DeterministicLearningService
from tests.productization.conftest import _run_golden_pipeline

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "run_requirement_analysis.py"


@pytest.mark.unit
class TestExecutionDataField:
    def test_learning_result_field_exists(self) -> None:
        field_names = {f.name for f in fields(ExecutionData)}
        assert "learning_result" in field_names

    def test_learning_result_defaults_to_none(self) -> None:
        field_map = {f.name: f for f in fields(ExecutionData)}
        assert field_map["learning_result"].default is None

    def test_other_result_fields_unchanged(self) -> None:
        """Additive only: every field present before CAP-086C is still present."""
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
            "organizational_memory_result",
        } <= field_names

    def test_construction_without_learning_result_still_works(self) -> None:
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
        assert data.learning_result is None


@pytest.mark.unit
class TestCliContainment:
    def test_cli_script_names_no_engine_or_policy_directly(self) -> None:
        """The CLI orchestrates only — it never names an implementation class.

        It obtains ``LearningService`` exclusively via
        ``PlatformContext.create_learning_service()`` and invokes ``build`` —
        never ``DeterministicLearningEngine``, ``LearningRuleCatalog``, or
        ``LearningPolicy`` directly (Stage 1: no collection logic, no
        validation logic, no generation, no lifecycle recording in the CLI).
        """
        source = _SCRIPT.read_text(encoding="utf-8")
        forbidden = (
            "DeterministicLearningEngine",
            "LearningRuleCatalog",
            "LearningRuleBuilder",
            "default_learning_rule_catalog",
            "default_learning_policy",
        )
        for token in forbidden:
            assert token not in source, f"CLI must not name {token!r} directly"

    def test_cli_calls_build_with_the_one_consumed_result(self) -> None:
        """The CLI's call site names the one frozen argument — no fan-in."""
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "def run_learning_phase(" in source
        assert (
            "context.create_learning_service().build(organizational_memory_result)" in source
        )

    def test_no_historical_dataset_reference_is_minted_for_learning(self) -> None:
        """Learning mints no reference of its own.

        ADR-0028 §Stage 12, ADR-0029 §D2: it consumes the one already-
        completed Layer 2 tier immediately beneath it directly, never a
        ``HistoricalDatasetReference`` — so no minting helper exists.
        """
        source = _SCRIPT.read_text(encoding="utf-8")
        assert "_historical_dataset_reference_for_execution(" in source
        assert "_knowledge_graph_historical_dataset_reference_for_execution(" in source
        assert "_learning_historical_dataset_reference_for_execution(" not in source

    def test_learning_phase_is_wired_after_organizational_memory(self) -> None:
        """The CLI orchestrates Learning strictly after Organizational Memory."""
        source = _SCRIPT.read_text(encoding="utf-8")
        om_call = source.index("run_organizational_memory_phase(\n")
        learning_call = source.index("run_learning_phase(\n")
        assert om_call < learning_call, "Learning must be wired after Organizational Memory"


@pytest.mark.unit
class TestExactlyOnceExecution:
    def test_learning_service_invoked_exactly_once_per_pipeline_run(self, tmp_path: Path) -> None:
        """One golden pipeline run builds exactly once — never twice, never in parallel."""
        original = DeterministicLearningService.build
        calls: list[int] = []

        def _counting_build(self, *args: object, **kwargs: object) -> object:
            calls.append(1)
            return original(self, *args, **kwargs)

        with patch.object(DeterministicLearningService, "build", _counting_build):
            pipeline = _run_golden_pipeline(tmp_path)

        assert len(calls) == 1
        assert pipeline.learning_result is not None

    def test_learning_executes_deterministically_for_a_fixed_consumed_result(
        self, tmp_path: Path
    ) -> None:
        """The same consumed Organizational Memory result, built twice, yields the
        same content."""
        from requirement_intelligence.platform.platform_context import PlatformContext

        pipeline = _run_golden_pipeline(tmp_path)
        r1 = pipeline.learning_result
        assert r1 is not None
        r2 = (
            PlatformContext()
            .create_learning_service()
            .build(pipeline.organizational_memory_result)
        )
        assert r1.candidates == r2.candidates
        assert r1.learnings == r2.learnings
        assert r1.metrics == r2.metrics
