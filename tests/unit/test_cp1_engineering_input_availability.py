"""Unit tests for CP1-0001 — EngineeringInputAvailabilityCriterion (CAP-067A).

Governed by ADR-0013.  Covers:

* PASS with one functional / security / quality requirement
* PASS with multiple mixed requirements
* FAIL with all three collections empty
* exactly one finding on FAIL; zero findings on PASS
* pooled counting (union of the three governed collections)
* the exact recommendation / message / verdict on FAIL
* criterion metadata (CP1-0001)
* deterministic repeated execution
* thread safety (stateless criterion under concurrency)
* immutability of the produced finding
* no mutation of CP1Input
* engine aggregation (FAIL propagates to the CP1Result verdict)
* end-to-end execution through the composed CP1Service
* registration in the composition root

The criterion consumes only ``CP1Input``; test inputs are built by running the real
``ResponseNormalizer`` over crafted JSON so the normalized structure is realistic.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.cp1.criteria import EngineeringInputAvailabilityCriterion
from requirement_intelligence.cp1.engine import CP1Engine
from requirement_intelligence.cp1.framework import CP1CriterionPipeline, CP1CriterionRegistry
from requirement_intelligence.cp1.models import CP1Finding, CP1Input
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

_RECOMMENDATION = (
    "The validated response contains no engineering requirements. Add at least one "
    "functional, security, or quality requirement before downstream engineering can begin."
)


# ---------------------------------------------------------------------------
# Builders — a real CP1Input whose normalized structure is controlled by JSON
# ---------------------------------------------------------------------------


def _response_json(
    *,
    functional: list[str] | None = None,
    security: list[str] | None = None,
    quality: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "summary": "s",
            "functional_requirements": functional or [],
            "security_requirements": security or [],
            "quality_requirements": quality or [],
            "recommendations": [],
            "risks": [],
        }
    )


def _analysis_result(generated_text: str, execution_id: str = "EX-1") -> AnalysisResult:
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
        llm_response=LLMResponse(provider="gemini", model="model", generated_text=generated_text),
    )


def _validation_result(execution_id: str = "EX-1") -> ValidationResult:
    return ValidationResult(
        validation_id="VAL-1",
        execution_id=execution_id,
        analysis_id="AN-1",
        analysis_result=_analysis_result("{}", execution_id),
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


def _cp1_input(generated_text: str, execution_id: str = "EX-1") -> CP1Input:
    """A real CP1Input whose normalized structure is the normalizer's view of *generated_text*."""
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    normalization_result = normalizer.normalize(
        _analysis_result(generated_text, execution_id).llm_response
    )
    return CP1Input(
        validation_result=_validation_result(execution_id),
        normalization_result=normalization_result,
    )


def _criterion() -> EngineeringInputAvailabilityCriterion:
    return EngineeringInputAvailabilityCriterion()


# ---------------------------------------------------------------------------
# 1. PASS — engineering input exists
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPass:
    def test_pass_with_one_functional_requirement(self) -> None:
        findings = _criterion().evaluate(_cp1_input(_response_json(functional=["do X"])))
        assert findings == []

    def test_pass_with_one_security_requirement(self) -> None:
        findings = _criterion().evaluate(_cp1_input(_response_json(security=["scan Y"])))
        assert findings == []

    def test_pass_with_one_quality_requirement(self) -> None:
        findings = _criterion().evaluate(_cp1_input(_response_json(quality=["measure Z"])))
        assert findings == []

    def test_pass_with_multiple_mixed_requirements(self) -> None:
        cp1_input = _cp1_input(
            _response_json(functional=["a", "b"], security=["c"], quality=["d"])
        )
        assert _criterion().evaluate(cp1_input) == []


# ---------------------------------------------------------------------------
# 2. FAIL — no engineering input
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFail:
    def test_fail_with_all_collections_empty(self) -> None:
        findings = _criterion().evaluate(_cp1_input(_response_json()))
        assert len(findings) == 1

    def test_fail_finding_shape(self) -> None:
        (finding,) = _criterion().evaluate(_cp1_input(_response_json(), execution_id="EX-9"))
        assert isinstance(finding, CP1Finding)
        assert finding.criterion_id == "CP1-0001"
        assert finding.criterion_version == "1.0.0"
        assert finding.verdict_contribution == ValidationVerdict.FAIL
        assert finding.recommendation == _RECOMMENDATION
        assert finding.correlation_id == "EX-9"
        assert "no engineering input" in finding.message.lower()

    def test_recommendations_and_risks_are_not_requirements(self) -> None:
        # Only functional/security/quality count; recommendations/risks/summary do not.
        payload = json.dumps(
            {
                "summary": "s",
                "functional_requirements": [],
                "security_requirements": [],
                "quality_requirements": [],
                "recommendations": ["r1", "r2"],
                "risks": ["risk1"],
            }
        )
        assert len(_criterion().evaluate(_cp1_input(payload))) == 1

    def test_malformed_response_has_no_engineering_input(self) -> None:
        # Non-JSON → MALFORMED → no normalized structure → count 0 → FAIL.
        assert len(_criterion().evaluate(_cp1_input("not json"))) == 1

    def test_absent_parsed_response_has_no_engineering_input(self) -> None:
        # Defensive: a NormalizationResult with no ParsedResponse → no structure → FAIL.
        base = _cp1_input(_response_json(functional=["x"]))
        broken = base.normalization_result.model_copy(update={"parsed_response": None})
        cp1_input = CP1Input(
            validation_result=base.validation_result, normalization_result=broken
        )
        assert len(_criterion().evaluate(cp1_input)) == 1


# ---------------------------------------------------------------------------
# 3. Pooled counting
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPooledCounting:
    def test_one_across_the_union_is_enough(self) -> None:
        # Zero functional + zero security + one quality → pooled ≥ 1 → PASS.
        assert _criterion().evaluate(_cp1_input(_response_json(quality=["only one"]))) == []


# ---------------------------------------------------------------------------
# 4. Metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetadata:
    def test_metadata(self) -> None:
        meta = _criterion().metadata
        assert meta.criterion_id == "CP1-0001"
        assert meta.criterion_name == "EngineeringInputAvailabilityCriterion"
        assert meta.criterion_version == "1.0.0"
        assert meta.enabled is True

    def test_convenience_wrappers(self) -> None:
        criterion = _criterion()
        assert criterion.criterion_id == "CP1-0001"
        assert criterion.criterion_version == "1.0.0"


# ---------------------------------------------------------------------------
# 5. Determinism, statelessness, thread safety
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeterminism:
    def test_repeated_execution_deterministic(self) -> None:
        criterion = _criterion()
        cp1_input = _cp1_input(_response_json())
        a = criterion.evaluate(cp1_input)
        b = criterion.evaluate(cp1_input)
        # Same verdict, count, and stable finding identity (created_at is provenance).
        assert [f.finding_id for f in a] == [f.finding_id for f in b]
        assert [f.verdict_contribution for f in a] == [f.verdict_contribution for f in b]

    def test_stateless_across_pass_then_fail(self) -> None:
        criterion = _criterion()
        assert criterion.evaluate(_cp1_input(_response_json(functional=["x"]))) == []
        assert len(criterion.evaluate(_cp1_input(_response_json()))) == 1

    def test_thread_safety(self) -> None:
        criterion = _criterion()
        pass_input = _cp1_input(_response_json(functional=["x"]))
        fail_input = _cp1_input(_response_json())
        cases = [pass_input, fail_input] * 12

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(criterion.evaluate, cases))

        for case, findings in zip(cases, results, strict=True):
            assert (findings == []) is (case is pass_input)


# ---------------------------------------------------------------------------
# 6. Immutability & no mutation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImmutabilityAndNoMutation:
    def test_finding_is_immutable(self) -> None:
        (finding,) = _criterion().evaluate(_cp1_input(_response_json()))
        with pytest.raises(ValidationError):
            finding.message = "mutated"  # type: ignore[misc]

    def test_does_not_mutate_cp1_input(self) -> None:
        cp1_input = _cp1_input(_response_json())
        before = cp1_input.model_dump()
        _criterion().evaluate(cp1_input)
        assert cp1_input.model_dump() == before


# ---------------------------------------------------------------------------
# 7. Engine aggregation & registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEngineAndRegistration:
    def test_engine_aggregates_fail(self) -> None:
        registry = CP1CriterionRegistry()
        registry.register(_criterion())
        result = CP1Engine().run(_cp1_input(_response_json()), CP1CriterionPipeline(registry))
        assert result.overall_verdict == ValidationVerdict.FAIL
        assert len(result.findings) == 1

    def test_engine_aggregates_pass(self) -> None:
        registry = CP1CriterionRegistry()
        registry.register(_criterion())
        result = CP1Engine().run(
            _cp1_input(_response_json(functional=["x"])), CP1CriterionPipeline(registry)
        )
        assert result.overall_verdict == ValidationVerdict.PASS
        assert result.findings == ()

    def test_registered_in_composition_root(self) -> None:
        service = build_cp1_service()
        assert isinstance(service, CP1Service)
        # PASS end-to-end when engineering input exists.
        passed = service.run(_cp1_input(_response_json(functional=["do X"])))
        assert passed.overall_verdict == ValidationVerdict.PASS
        # FAIL end-to-end when it does not.
        failed = service.run(_cp1_input(_response_json()))
        assert failed.overall_verdict == ValidationVerdict.FAIL
        assert failed.findings[0].criterion_id == "CP1-0001"
