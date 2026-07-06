"""Unit tests for the Validation → CP1 handoff seam (CAP-064).

Covers the pure-orchestration seam governed by ADR-0011 §D4 (owned above both
boundaries) and §D5 (the Validation verdict gate):

* successful handoff (PASSED / PASSED_WITH_WARNINGS → CP1Input)
* gating (FAILED / BLOCKED → None; nothing constructed)
* reference identity (references, never copies)
* immutability of the produced CP1Input
* deterministic + idempotent behaviour (stateless seam)
* same-execution invariant (delegated to CP1Input; match / absent / mismatch)
* no mutation of either argument
* single construction per call
* error behaviour (mismatch propagates)
* the governed eligible-verdict set
* thread safety (stateless seam under concurrency)

Design constraints
------------------
* The seam performs no readiness judgement, no aggregation, no CP1 execution.
* Real ``ValidationResult`` / ``NormalizationResult`` carriers are built locally.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.cp1.models import CP1Input
from requirement_intelligence.cp1.response import (
    CP1_ELIGIBLE_VALIDATION_VERDICTS,
    ValidationToCP1Handoff,
)
from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.framework.normalization_pipeline import (
    NormalizationPipeline,
)
from requirement_intelligence.normalization.framework.normalization_registry import (
    NormalizationRegistry,
)
from requirement_intelligence.normalization.models.normalization_configuration import (
    NormalizationConfiguration,
)
from requirement_intelligence.normalization.models.normalization_result import (
    NormalizationResult,
)
from requirement_intelligence.normalization.response import ResponseNormalizer
from requirement_intelligence.validation.models import (
    DEFAULT_VALIDATION_CONTRACT_VERSION,
    FRAMEWORK_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    ValidationConfiguration,
    ValidationFrameworkMetadata,
    ValidationHealth,
    ValidationResult,
    ValidationStatistics,
    ValidationSummary,
    ValidationVerdict,
)

_TS = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Local builders
# ---------------------------------------------------------------------------


def _analysis_result(execution_id: str = "EX-1", analysis_id: str = "AN-1") -> AnalysisResult:
    return AnalysisResult(
        analysis_id=analysis_id,
        execution_id=execution_id,
        source_consolidated_id="C-1",
        prompt_version="1.0",
        reasoning_contract_version="1.0",
        provider="gemini",
        model="model",
        started_at=_TS,
        completed_at=_TS,
        duration_ms=1.0,
        llm_response=LLMResponse(provider="gemini", model="model", generated_text="x"),
    )


def _normalization_result(analysis: AnalysisResult) -> NormalizationResult:
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return normalizer.normalize(analysis.llm_response)


def _validation_result(
    execution_id: str = "EX-1",
    verdict: ValidationVerdict = ValidationVerdict.PASSED,
) -> ValidationResult:
    return ValidationResult(
        validation_id="VAL-1",
        execution_id=execution_id,
        analysis_id="AN-1",
        analysis_result=_analysis_result(execution_id),
        validation_summary=ValidationSummary(
            total_issues=0,
            info_count=0,
            warning_count=0,
            error_count=0,
            critical_count=0,
            blocking_issue_count=0,
            overall_health=ValidationHealth.HEALTHY,
        ),
        validation_statistics=ValidationStatistics(
            validation_duration_ms=1.5,
            rules_executed=1,
            rules_passed=1,
            rules_failed=0,
            started_at=_TS,
            completed_at=_TS,
            validator_version=FRAMEWORK_VERSION,
            validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
            execution_id=execution_id,
        ),
        validation_configuration=ValidationConfiguration(),
        validation_framework_metadata=ValidationFrameworkMetadata(
            framework_version=FRAMEWORK_VERSION,
            validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
            pipeline_version=PIPELINE_VERSION,
            registry_version=REGISTRY_VERSION,
        ),
        overall_verdict=verdict,
        started_at=_TS,
        completed_at=_TS,
    )


# ---------------------------------------------------------------------------
# 1. Successful handoff
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSuccessfulHandoff:
    def test_passed_produces_cp1_input(self) -> None:
        seam = ValidationToCP1Handoff()
        result = seam.hand_off(
            _validation_result(verdict=ValidationVerdict.PASSED),
            _normalization_result(_analysis_result()),
        )
        assert isinstance(result, CP1Input)

    def test_passed_with_warnings_produces_cp1_input(self) -> None:
        seam = ValidationToCP1Handoff()
        result = seam.hand_off(
            _validation_result(verdict=ValidationVerdict.PASSED_WITH_WARNINGS),
            _normalization_result(_analysis_result()),
        )
        assert isinstance(result, CP1Input)


# ---------------------------------------------------------------------------
# 2. Gating
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGating:
    @pytest.mark.parametrize(
        "verdict", [ValidationVerdict.FAILED, ValidationVerdict.BLOCKED]
    )
    def test_non_eligible_verdicts_produce_none(self, verdict: ValidationVerdict) -> None:
        seam = ValidationToCP1Handoff()
        assert seam.hand_off(
            _validation_result(verdict=verdict), _normalization_result(_analysis_result())
        ) is None

    @pytest.mark.parametrize(
        "verdict", [ValidationVerdict.PASSED, ValidationVerdict.PASSED_WITH_WARNINGS]
    )
    def test_eligible_verdicts_proceed(self, verdict: ValidationVerdict) -> None:
        seam = ValidationToCP1Handoff()
        assert seam.hand_off(
            _validation_result(verdict=verdict), _normalization_result(_analysis_result())
        ) is not None

    def test_eligible_verdict_set_is_exactly_the_two_governed_verdicts(self) -> None:
        assert CP1_ELIGIBLE_VALIDATION_VERDICTS == frozenset(
            {ValidationVerdict.PASSED, ValidationVerdict.PASSED_WITH_WARNINGS}
        )
        assert ValidationVerdict.FAILED not in CP1_ELIGIBLE_VALIDATION_VERDICTS
        assert ValidationVerdict.BLOCKED not in CP1_ELIGIBLE_VALIDATION_VERDICTS


# ---------------------------------------------------------------------------
# 3. Reference identity (references, never copies)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReferenceIdentity:
    def test_references_are_the_same_instances(self) -> None:
        validation_result = _validation_result()
        norm = _normalization_result(_analysis_result())
        cp1_input = ValidationToCP1Handoff().hand_off(validation_result, norm)
        assert cp1_input is not None
        assert cp1_input.validation_result is validation_result
        assert cp1_input.normalization_result is norm


# ---------------------------------------------------------------------------
# 4. Immutability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImmutability:
    def test_produced_cp1_input_is_frozen(self) -> None:
        cp1_input = ValidationToCP1Handoff().hand_off(
            _validation_result(), _normalization_result(_analysis_result())
        )
        assert cp1_input is not None
        with pytest.raises(ValidationError):
            cp1_input.metadata = {"x": "y"}  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 5. Determinism & idempotence (stateless seam)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeterminismAndIdempotence:
    def test_repeated_calls_same_inputs_are_equal(self) -> None:
        validation_result = _validation_result()
        norm = _normalization_result(_analysis_result())
        seam = ValidationToCP1Handoff()
        a = seam.hand_off(validation_result, norm)
        b = seam.hand_off(validation_result, norm)
        assert a == b

    def test_seam_holds_no_state_across_calls(self) -> None:
        seam = ValidationToCP1Handoff()
        # A gated-out call does not affect a subsequent eligible call.
        assert seam.hand_off(
            _validation_result(verdict=ValidationVerdict.FAILED),
            _normalization_result(_analysis_result()),
        ) is None
        assert seam.hand_off(
            _validation_result(verdict=ValidationVerdict.PASSED),
            _normalization_result(_analysis_result()),
        ) is not None

    def test_gated_out_constructs_nothing(self) -> None:
        # No exception, no object — the gate simply returns None.
        assert ValidationToCP1Handoff().hand_off(
            _validation_result(verdict=ValidationVerdict.BLOCKED),
            _normalization_result(_analysis_result()),
        ) is None


# ---------------------------------------------------------------------------
# 6. Same-execution invariant (delegated to CP1Input) & error behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSameExecutionInvariant:
    def test_absent_correlation_is_accepted(self) -> None:
        # As produced, the NormalizationResult carries correlation_id=None.
        cp1_input = ValidationToCP1Handoff().hand_off(
            _validation_result("EX-9"), _normalization_result(_analysis_result("EX-9"))
        )
        assert cp1_input is not None

    def test_matching_correlation_is_accepted(self) -> None:
        norm = _normalization_result(_analysis_result("EX-9")).model_copy(
            update={"correlation_id": "EX-9"}
        )
        cp1_input = ValidationToCP1Handoff().hand_off(_validation_result("EX-9"), norm)
        assert cp1_input is not None

    def test_mismatched_correlation_propagates_error(self) -> None:
        norm = _normalization_result(_analysis_result("EX-9")).model_copy(
            update={"correlation_id": "OTHER"}
        )
        with pytest.raises(ValidationError):
            ValidationToCP1Handoff().hand_off(_validation_result("EX-9"), norm)

    def test_gate_closed_skips_construction_even_with_mismatch(self) -> None:
        # FAILED gates out before construction, so a mismatch never surfaces.
        norm = _normalization_result(_analysis_result("EX-9")).model_copy(
            update={"correlation_id": "OTHER"}
        )
        assert ValidationToCP1Handoff().hand_off(
            _validation_result("EX-9", verdict=ValidationVerdict.FAILED), norm
        ) is None


# ---------------------------------------------------------------------------
# 7. No mutation of the arguments
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoMutation:
    def test_arguments_are_unchanged(self) -> None:
        validation_result = _validation_result()
        norm = _normalization_result(_analysis_result())
        before_vr = validation_result.model_dump()
        before_nr = norm.model_dump()
        ValidationToCP1Handoff().hand_off(validation_result, norm)
        assert validation_result.model_dump() == before_vr
        assert norm.model_dump() == before_nr


# ---------------------------------------------------------------------------
# 8. Thread safety (stateless seam under concurrency)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestThreadSafety:
    def test_concurrent_handoffs_are_independent(self) -> None:
        seam = ValidationToCP1Handoff()
        pairs = [
            (_validation_result(f"EX-{i}"), _normalization_result(_analysis_result(f"EX-{i}")))
            for i in range(16)
        ]

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda p: seam.hand_off(*p), pairs))

        assert all(r is not None for r in results)
        for (vr, nr), cp1_input in zip(pairs, results, strict=True):
            assert cp1_input is not None
            assert cp1_input.validation_result is vr
            assert cp1_input.normalization_result is nr
