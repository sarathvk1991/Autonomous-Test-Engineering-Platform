"""Tests for requirement_intelligence.testable_requirement.emitter (ADR-0032
carve-out 1, ADR-0034, ADR-0042 Decision 1).

Uses the golden pipeline fixture (deterministic stub provider, no network) so
these tests run offline and fast, exactly like the productization suite's own
tests over the same fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.context_orchestration.models.engineering_context import (
    ContextEvidence,
)
from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.testable_requirement import (
    TestableRequirementEmissionError,
    emit_testable_requirement_set,
    gate_permits_emission,
)
from tests.productization.conftest import _run_golden_pipeline


def _with_decision(governance_result: object, decision: str) -> object:
    """Return a copy of *governance_result* with its assessment.decision replaced.

    Both QualityGovernanceResult and QualityAssessment are frozen; model_copy
    produces a new instance rather than mutating either.
    """
    new_assessment = governance_result.assessment.model_copy(update={"decision": decision})  # type: ignore[attr-defined]
    return governance_result.model_copy(update={"assessment": new_assessment})  # type: ignore[attr-defined]


@pytest.mark.unit
class TestGatePermitsEmission:
    def test_pass_permits(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.quality_governance_result is not None
        assert gate_permits_emission(pipeline.quality_governance_result)

    def test_pass_with_warnings_permits(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.quality_governance_result is not None
        warned = _with_decision(pipeline.quality_governance_result, "pass_with_warnings")
        assert gate_permits_emission(warned)  # type: ignore[arg-type]

    def test_fail_does_not_permit(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.quality_governance_result is not None
        failed = _with_decision(pipeline.quality_governance_result, "fail")
        assert not gate_permits_emission(failed)  # type: ignore[arg-type]


@pytest.mark.unit
class TestEmitTestableRequirementSet:
    def test_emits_a_set_for_a_passing_run(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        context = PlatformContext()
        result = emit_testable_requirement_set(
            run_id=pipeline.analysis_result.execution_id,
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=pipeline.quality_governance_result,
            prompt_registry=context.prompt_registry,
        )
        assert result is not None
        assert result.run_id == pipeline.analysis_result.execution_id
        assert len(result.requirements) == 8  # 3 functional + 3 security + 2 quality
        assert len(result.risks) > 0

    def test_every_requirement_has_a_content_addressed_id(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        context = PlatformContext()
        result = emit_testable_requirement_set(
            run_id="run-1",
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=pipeline.quality_governance_result,
            prompt_registry=context.prompt_registry,
        )
        assert result is not None
        ids = [r.requirement_id for r in result.requirements]
        assert len(ids) == len(set(ids))  # no collisions
        assert all(rid.startswith("REQ-") for rid in ids)

    def test_every_requirement_traces_to_at_least_one_source(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        context = PlatformContext()
        result = emit_testable_requirement_set(
            run_id="run-1",
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=pipeline.quality_governance_result,
            prompt_registry=context.prompt_registry,
        )
        assert result is not None
        for requirement in result.requirements:
            assert len(requirement.traces_to) > 0

    def test_acceptance_criterion_category_matches_source_array(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        context = PlatformContext()
        result = emit_testable_requirement_set(
            run_id="run-1",
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=pipeline.quality_governance_result,
            prompt_registry=context.prompt_registry,
        )
        assert result is not None
        categories = {r.acceptance_criteria[0].category for r in result.requirements}
        assert categories == {"functional", "security", "quality"}

    def test_acceptance_criterion_traces_to_is_always_empty(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        context = PlatformContext()
        result = emit_testable_requirement_set(
            run_id="run-1",
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=pipeline.quality_governance_result,
            prompt_registry=context.prompt_registry,
        )
        assert result is not None
        for requirement in result.requirements:
            assert requirement.acceptance_criteria[0].traces_to == ()

    def test_priority_and_risk_category_are_none(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        context = PlatformContext()
        result = emit_testable_requirement_set(
            run_id="run-1",
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=pipeline.quality_governance_result,
            prompt_registry=context.prompt_registry,
        )
        assert result is not None
        assert all(r.priority is None for r in result.requirements)
        assert all(risk.category is None for risk in result.risks)

    def test_requirement_risks_field_is_always_empty(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        context = PlatformContext()
        result = emit_testable_requirement_set(
            run_id="run-1",
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=pipeline.quality_governance_result,
            prompt_registry=context.prompt_registry,
        )
        assert result is not None
        assert all(r.risks == () for r in result.requirements)

    def test_provenance_matches_the_run(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        context = PlatformContext()
        result = emit_testable_requirement_set(
            run_id="run-1",
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=pipeline.quality_governance_result,
            prompt_registry=context.prompt_registry,
        )
        assert result is not None
        assert result.provenance.prompt_version == pipeline.analysis_result.prompt_version
        assert result.provenance.provider == "gemini"
        assert result.provenance.model == pipeline.analysis_result.model
        assert result.provenance.requirement_quality_governance_decision == "pass"
        assert result.provenance.governance_report_ref == "quality_governance_report.md"

    def test_determinism_same_inputs_yield_same_ids_and_traces_to_order(
        self, tmp_path: Path
    ) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        context = PlatformContext()
        kwargs = dict(
            run_id="run-1",
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=pipeline.quality_governance_result,
            prompt_registry=context.prompt_registry,
        )
        first = emit_testable_requirement_set(**kwargs)
        second = emit_testable_requirement_set(**kwargs)
        assert first is not None
        assert second is not None
        assert [r.requirement_id for r in first.requirements] == [
            r.requirement_id for r in second.requirements
        ]
        assert [ref.external_id for ref in first.requirements[0].traces_to] == [
            ref.external_id for ref in second.requirements[0].traces_to
        ]

    def test_traces_to_is_deduplicated_and_sorted(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        context = PlatformContext()
        result = emit_testable_requirement_set(
            run_id="run-1",
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=pipeline.quality_governance_result,
            prompt_registry=context.prompt_registry,
        )
        assert result is not None
        keys = [(ref.system, ref.external_id) for ref in result.requirements[0].traces_to]
        assert len(keys) == len(set(keys))
        assert keys == sorted(keys)

    def test_returns_none_for_a_failing_run(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.quality_governance_result is not None
        failed = _with_decision(pipeline.quality_governance_result, "fail")
        context = PlatformContext()
        result = emit_testable_requirement_set(
            run_id="run-1",
            analysis_result=pipeline.analysis_result,
            engineering_context=pipeline.engineering_context,
            consolidated_artifact=pipeline.selected,
            governance_result=failed,  # type: ignore[arg-type]
            prompt_registry=context.prompt_registry,
        )
        assert result is None

    def test_raises_on_invalid_json_response(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.quality_governance_result is not None
        broken_llm_response = pipeline.analysis_result.llm_response.model_copy(
            update={"generated_text": "not valid json"}
        )
        broken_result = pipeline.analysis_result.model_copy(
            update={"llm_response": broken_llm_response}
        )
        context = PlatformContext()
        with pytest.raises(TestableRequirementEmissionError):
            emit_testable_requirement_set(
                run_id="run-1",
                analysis_result=broken_result,
                engineering_context=pipeline.engineering_context,
                consolidated_artifact=pipeline.selected,
                governance_result=pipeline.quality_governance_result,
                prompt_registry=context.prompt_registry,
            )

    def test_raises_on_empty_evidence(self, tmp_path: Path) -> None:
        pipeline = _run_golden_pipeline(tmp_path)
        assert pipeline.quality_governance_result is not None
        empty_context = pipeline.engineering_context.model_copy(
            update={"evidence": ContextEvidence()}
        )
        context = PlatformContext()
        with pytest.raises(TestableRequirementEmissionError):
            emit_testable_requirement_set(
                run_id="run-1",
                analysis_result=pipeline.analysis_result,
                engineering_context=empty_context,
                consolidated_artifact=pipeline.selected,
                governance_result=pipeline.quality_governance_result,
                prompt_registry=context.prompt_registry,
            )
