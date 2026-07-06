"""Unit tests for the CP1 composition root (CAP-066).

Covers the explicit, deterministic assembly of the CP1 service:

* empty-registry assembly (zero governed criteria — the architecture-correct state)
* deterministic construction (equivalent services per build)
* pipeline + engine correctly wired (behavioural)
* the assembled service executes with zero criteria → CP1Result
* PASS verdict from the empty finding set
* framework metadata preserved
* CP1Input preserved
* repeated executions deterministic
* thread safety (stateless service under concurrency)

Design constraints
------------------
* The composition root introduces no criterion, threshold, heuristic, or policy —
  only assembly.  The catalog is intentionally empty (ADR-0012).
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.cp1.models import CP1FrameworkMetadata, CP1Input, CP1Result
from requirement_intelligence.cp1.response import CP1Service, build_cp1_service
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

# The composed service now runs the registered CP1-0001; a valid response carrying at
# least one requirement makes it PASS (engineering input exists).
_VALID_RESPONSE = json.dumps(
    {
        "summary": "s",
        "functional_requirements": ["do X"],
        "security_requirements": [],
        "quality_requirements": [],
        "recommendations": [],
        "risks": [],
    }
)


# ---------------------------------------------------------------------------
# CP1Input builder
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
        llm_response=LLMResponse(
            provider="gemini", model="model", generated_text=_VALID_RESPONSE
        ),
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


# ---------------------------------------------------------------------------
# 1. Assembly
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAssembly:
    def test_build_returns_a_service(self) -> None:
        assert isinstance(build_cp1_service(), CP1Service)

    def test_empty_registry_service_executes(self) -> None:
        result = build_cp1_service().run(_cp1_input())
        assert isinstance(result, CP1Result)

    def test_valid_input_yields_pass_and_no_findings(self) -> None:
        # The composed service runs CP1-0001; a response with a requirement PASSes.
        result = build_cp1_service().run(_cp1_input())
        assert result.overall_verdict == ValidationVerdict.PASS
        assert result.findings == ()

    def test_pipeline_and_engine_are_wired(self) -> None:
        # Behavioural evidence: a CP1Result with framework provenance (pipeline ran)
        # and an aggregated verdict (engine ran).
        result = build_cp1_service().run(_cp1_input())
        assert isinstance(result.framework_metadata, CP1FrameworkMetadata)
        assert result.overall_verdict == ValidationVerdict.PASS


# ---------------------------------------------------------------------------
# 2. Preservation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPreservation:
    def test_framework_metadata_preserved(self) -> None:
        result = build_cp1_service().run(_cp1_input())
        assert result.framework_metadata.framework_version == "1.0.0"
        assert result.framework_metadata.pipeline_version == "1.0.0"
        assert result.framework_metadata.registry_version == "1.0.0"

    def test_cp1_input_preserved(self) -> None:
        cp1_input = _cp1_input()
        result = build_cp1_service().run(cp1_input)
        assert result.cp1_input is cp1_input

    def test_correlation_identities_carried(self) -> None:
        result = build_cp1_service().run(_cp1_input("EX-77"))
        assert result.execution_id == "EX-77"
        assert result.validation_id == "VAL-1"


# ---------------------------------------------------------------------------
# 3. Determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeterminism:
    def test_multiple_builds_produce_equivalent_services(self) -> None:
        cp1_input = _cp1_input()
        a = build_cp1_service().run(cp1_input)
        b = build_cp1_service().run(cp1_input)
        assert a.overall_verdict == b.overall_verdict == ValidationVerdict.PASS
        assert a.findings == b.findings == ()
        assert a.framework_metadata == b.framework_metadata

    def test_repeated_executions_deterministic(self) -> None:
        service = build_cp1_service()
        cp1_input = _cp1_input()
        r1 = service.run(cp1_input)
        r2 = service.run(cp1_input)
        assert r1.overall_verdict == r2.overall_verdict
        assert r1.findings == r2.findings
        assert r1.framework_metadata == r2.framework_metadata

    def test_run_identity_is_per_run(self) -> None:
        service = build_cp1_service()
        cp1_input = _cp1_input()
        assert service.run(cp1_input).cp1_id != service.run(cp1_input).cp1_id


# ---------------------------------------------------------------------------
# 4. Thread safety (stateless service under concurrency)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestThreadSafety:
    def test_concurrent_runs_on_shared_service(self) -> None:
        service = build_cp1_service()
        inputs = [_cp1_input(f"EX-{i}") for i in range(24)]

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(service.run, inputs))

        assert all(r.overall_verdict == ValidationVerdict.PASS for r in results)
        for cp1_input, result in zip(inputs, results, strict=True):
            assert result.cp1_input is cp1_input
            assert result.findings == ()
