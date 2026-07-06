"""Unit tests for the CP1 Engine (CAP-065).

Covers the "Aggregate Result" orchestrator (ADR-0011 §D7; ADR-0012 §8):

* verdict aggregation — PASS / WARN / FAIL and the empty finding set
* ordering independence of aggregation
* deterministic findings + verdict across runs
* statelessness (independent runs)
* CP1Input preservation (referenced, never mutated)
* CP1FrameworkMetadata preservation
* immutable CP1Result
* pipeline executed exactly once
* serialization + round-trip
* error propagation (a criterion that raises)
* thread safety (stateless engine under concurrency)

Design constraints
------------------
* The engine performs no readiness judgement, no thresholds, no policy — only the
  governed aggregation.  Test-double criteria stand in for future criteria.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.cp1.engine import CP1Engine
from requirement_intelligence.cp1.framework import (
    CP1Criterion,
    CP1CriterionMetadata,
    CP1CriterionPipeline,
    CP1CriterionRegistry,
)
from requirement_intelligence.cp1.models import (
    CP1Finding,
    CP1FrameworkMetadata,
    CP1Input,
    CP1Result,
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
)
from requirement_intelligence.validation.models import (
    ValidationVerdict as ValidationSubsystemVerdict,
)
from shared.enums.base import ValidationVerdict

_TS = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Builders — CP1Input and test-double criteria/pipeline
# ---------------------------------------------------------------------------


def _analysis_result(execution_id: str = "EX-1") -> AnalysisResult:
    return AnalysisResult(
        analysis_id="AN-1",
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


def _validation_result(execution_id: str = "EX-1") -> ValidationResult:
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
        overall_verdict=ValidationSubsystemVerdict.PASSED,
        started_at=_TS,
        completed_at=_TS,
    )


def _normalization_result(execution_id: str = "EX-1") -> object:
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return normalizer.normalize(_analysis_result(execution_id).llm_response)


def _cp1_input(execution_id: str = "EX-1") -> CP1Input:
    return CP1Input(
        validation_result=_validation_result(execution_id),
        normalization_result=_normalization_result(execution_id),
    )


def _finding(finding_id: str, verdict: ValidationVerdict) -> CP1Finding:
    return CP1Finding(
        finding_id=finding_id,
        criterion_id="CP1-0001",
        criterion_version="1.0",
        verdict_contribution=verdict,
        message="m",
        location="l",
        recommendation="r",
        correlation_id="EX-1",
        created_at=_TS,
    )


class _Criterion(CP1Criterion):
    """Deterministic test-double criterion (no readiness logic)."""

    def __init__(
        self, criterion_id: str, findings: tuple[CP1Finding, ...], raises: Exception | None = None
    ) -> None:
        self._meta = CP1CriterionMetadata(criterion_id=criterion_id, criterion_name=criterion_id)
        self._findings = findings
        self._raises = raises
        self.calls = 0

    @property
    def metadata(self) -> CP1CriterionMetadata:
        return self._meta

    def evaluate(self, cp1_input: object) -> list[CP1Finding]:
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return list(self._findings)


def _pipeline(*criteria: _Criterion) -> CP1CriterionPipeline:
    registry = CP1CriterionRegistry()
    for c in criteria:
        registry.register(c)
    return CP1CriterionPipeline(registry)


def _one(verdict: ValidationVerdict, finding_id: str = "F1") -> CP1CriterionPipeline:
    """A pipeline with one criterion producing a single finding of *verdict*."""
    return _pipeline(_Criterion("CP1-0001", (_finding(finding_id, verdict),)))


# ---------------------------------------------------------------------------
# 1. Verdict aggregation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAggregation:
    def test_empty_finding_set_is_pass(self) -> None:
        result = CP1Engine().run(_cp1_input(), _pipeline())
        assert result.overall_verdict == ValidationVerdict.PASS
        assert result.findings == ()

    def test_all_pass_is_pass(self) -> None:
        pipeline = _pipeline(
            _Criterion("CP1-0001", (_finding("F1", ValidationVerdict.PASS),)),
            _Criterion("CP1-0002", (_finding("F2", ValidationVerdict.PASS),)),
        )
        assert CP1Engine().run(_cp1_input(), pipeline).overall_verdict == ValidationVerdict.PASS

    def test_any_warn_no_fail_is_warn(self) -> None:
        pipeline = _pipeline(
            _Criterion("CP1-0001", (_finding("F1", ValidationVerdict.PASS),)),
            _Criterion("CP1-0002", (_finding("F2", ValidationVerdict.WARN),)),
        )
        assert CP1Engine().run(_cp1_input(), pipeline).overall_verdict == ValidationVerdict.WARN

    def test_any_fail_is_fail(self) -> None:
        pipeline = _pipeline(
            _Criterion("CP1-0001", (_finding("F1", ValidationVerdict.WARN),)),
            _Criterion("CP1-0002", (_finding("F2", ValidationVerdict.FAIL),)),
        )
        assert CP1Engine().run(_cp1_input(), pipeline).overall_verdict == ValidationVerdict.FAIL

    def test_fail_dominates_pass_and_warn(self) -> None:
        pipeline = _pipeline(
            _Criterion(
                "CP1-0001",
                (
                    _finding("F1", ValidationVerdict.PASS),
                    _finding("F2", ValidationVerdict.WARN),
                    _finding("F3", ValidationVerdict.FAIL),
                ),
            ),
        )
        assert CP1Engine().run(_cp1_input(), pipeline).overall_verdict == ValidationVerdict.FAIL

    def test_aggregation_is_order_independent(self) -> None:
        forward = _pipeline(
            _Criterion("CP1-0001", (_finding("F1", ValidationVerdict.PASS),)),
            _Criterion("CP1-0002", (_finding("F2", ValidationVerdict.WARN),)),
        )
        reverse = _pipeline(
            _Criterion("CP1-0002", (_finding("F2", ValidationVerdict.WARN),)),
            _Criterion("CP1-0001", (_finding("F1", ValidationVerdict.PASS),)),
        )
        engine = CP1Engine()
        assert (
            engine.run(_cp1_input(), forward).overall_verdict
            == engine.run(_cp1_input(), reverse).overall_verdict
            == ValidationVerdict.WARN
        )


# ---------------------------------------------------------------------------
# 2. Findings collection & pipeline-executed-once
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecution:
    def test_collects_findings_in_order(self) -> None:
        pipeline = _pipeline(
            _Criterion("CP1-0001", (_finding("F1", ValidationVerdict.WARN),)),
            _Criterion("CP1-0002", (_finding("F2", ValidationVerdict.PASS),)),
        )
        result = CP1Engine().run(_cp1_input(), pipeline)
        assert [f.finding_id for f in result.findings] == ["F1", "F2"]
        assert isinstance(result.findings, tuple)

    def test_pipeline_executed_exactly_once(self) -> None:
        c1 = _Criterion("CP1-0001", (_finding("F1", ValidationVerdict.PASS),))
        c2 = _Criterion("CP1-0002", (_finding("F2", ValidationVerdict.WARN),))
        CP1Engine().run(_cp1_input(), _pipeline(c1, c2))
        assert c1.calls == 1
        assert c2.calls == 1


# ---------------------------------------------------------------------------
# 3. Preservation (input + framework metadata)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPreservation:
    def test_preserves_cp1_input_instance(self) -> None:
        cp1_input = _cp1_input()
        result = CP1Engine().run(cp1_input, _pipeline())
        assert result.cp1_input is cp1_input

    def test_does_not_mutate_cp1_input(self) -> None:
        cp1_input = _cp1_input()
        before = cp1_input.model_dump()
        CP1Engine().run(cp1_input, _pipeline())
        assert cp1_input.model_dump() == before

    def test_preserves_framework_metadata(self) -> None:
        pipeline = _pipeline()
        result = CP1Engine().run(_cp1_input(), pipeline)
        assert isinstance(result.framework_metadata, CP1FrameworkMetadata)
        assert result.framework_metadata == pipeline.framework_metadata()

    def test_carries_correlation_identities(self) -> None:
        result = CP1Engine().run(_cp1_input("EX-42"), _pipeline())
        assert result.execution_id == "EX-42"
        assert result.validation_id == "VAL-1"
        assert result.analysis_id == "AN-1"


# ---------------------------------------------------------------------------
# 4. Determinism & statelessness
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeterminismAndStatelessness:
    def test_findings_and_verdict_deterministic_across_runs(self) -> None:
        engine = CP1Engine()
        cp1_input = _cp1_input()
        r1 = engine.run(cp1_input, _one(ValidationVerdict.WARN))
        r2 = engine.run(cp1_input, _one(ValidationVerdict.WARN))
        assert r1.findings == r2.findings
        assert r1.overall_verdict == r2.overall_verdict

    def test_run_identity_is_unique_per_run(self) -> None:
        # cp1_id is per-run provenance, not part of the judgement.
        engine = CP1Engine()
        cp1_input = _cp1_input()
        first = engine.run(cp1_input, _pipeline())
        second = engine.run(cp1_input, _pipeline())
        assert first.cp1_id != second.cp1_id

    def test_engine_holds_no_state(self) -> None:
        engine = CP1Engine()
        fail = engine.run(_cp1_input(), _one(ValidationVerdict.FAIL))
        clean = engine.run(_cp1_input(), _pipeline())
        assert fail.overall_verdict == ValidationVerdict.FAIL
        assert clean.overall_verdict == ValidationVerdict.PASS


# ---------------------------------------------------------------------------
# 5. Immutability & serialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResultShape:
    def test_result_is_immutable(self) -> None:
        result = CP1Engine().run(_cp1_input(), _pipeline())
        assert isinstance(result, CP1Result)
        with pytest.raises(ValidationError):
            result.overall_verdict = ValidationVerdict.FAIL  # type: ignore[misc]

    def test_result_serializes_and_roundtrips(self) -> None:
        result = CP1Engine().run(_cp1_input(), _one(ValidationVerdict.WARN))
        dumped = result.model_dump(by_alias=True)
        assert dumped["overallVerdict"] == "warn"
        restored = CP1Result.model_validate_json(result.model_dump_json(by_alias=True))
        assert restored.model_dump(by_alias=True, mode="json") == result.model_dump(
            by_alias=True, mode="json"
        )


# ---------------------------------------------------------------------------
# 6. Error propagation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestErrorPropagation:
    def test_criterion_exception_propagates(self) -> None:
        pipeline = _pipeline(_Criterion("CP1-0001", (), raises=RuntimeError("boom")))
        with pytest.raises(RuntimeError, match="boom"):
            CP1Engine().run(_cp1_input(), pipeline)


# ---------------------------------------------------------------------------
# 7. Thread safety (stateless engine under concurrency)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestThreadSafety:
    def test_concurrent_runs_are_independent(self) -> None:
        engine = CP1Engine()
        verdicts = [ValidationVerdict.PASS, ValidationVerdict.WARN, ValidationVerdict.FAIL]

        def run(v: ValidationVerdict) -> CP1Result:
            return engine.run(
                _cp1_input(), _pipeline(_Criterion("CP1-0001", (_finding("F1", v),)))
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(run, verdicts * 8))

        # Each result's verdict matches the single finding it was given.
        for v, result in zip(verdicts * 8, results, strict=True):
            assert result.overall_verdict == v
