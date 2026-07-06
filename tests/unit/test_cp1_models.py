"""Unit tests for the CP1 Canonical Models (CAP-062).

Covers the immutable, implementation-independent information models introduced by
ADR-0011 (CP1 Validation Engine & the Validation → CP1 Handoff):

* construction (all three models, with and without defaults)
* immutability (frozen models reject mutation)
* strict mode (unknown fields rejected)
* required-field validation (missing fields rejected)
* camelCase serialization + JSON round-trip
* enum-by-value serialization (verdict serialises to its string value)
* equality (value semantics) and inequality
* version constants + defaulted version fields
* default factories (metadata, findings) and metadata isolation
* the CP1Input same-execution structural-integrity invariant (match / absent / mismatch)
* reference-not-copy binding (``is`` identity preserved)
* ownership: CP1Result owns findings and preserves its CP1Input unaltered

Design constraints
------------------
* No engine, registry, pipeline, criterion, or readiness policy is exercised —
  these are information models only.
* Real ``ValidationResult`` / ``NormalizationResult`` carriers are constructed
  locally with the same builders the Validation model tests use.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.analysis.analysis_models import AnalysisResult
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
)
from requirement_intelligence.validation.models import (
    ValidationVerdict as ValidationSubsystemVerdict,
)
from requirement_intelligence.validators.models import (
    CP1_FINDING_VERSION,
    CP1_INPUT_VERSION,
    CP1_RESULT_VERSION,
    CP1Finding,
    CP1Input,
    CP1Result,
)
from shared.enums.base import ValidationVerdict  # CP1's PASS / FAIL / WARN vocabulary

_TS = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Local builders — no rules, no engine, no AI
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
    """A real ``NormalizationResult`` (``correlation_id`` is ``None`` as produced)."""
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return normalizer.normalize(analysis.llm_response)


def _validation_summary() -> ValidationSummary:
    return ValidationSummary(
        total_issues=0,
        info_count=0,
        warning_count=0,
        error_count=0,
        critical_count=0,
        blocking_issue_count=0,
        overall_health=ValidationHealth.HEALTHY,
    )


def _validation_statistics() -> ValidationStatistics:
    return ValidationStatistics(
        validation_duration_ms=1.5,
        rules_executed=1,
        rules_passed=1,
        rules_failed=0,
        started_at=_TS,
        completed_at=_TS,
        validator_version=FRAMEWORK_VERSION,
        validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
        execution_id="EX-1",
    )


def _validation_framework_metadata() -> ValidationFrameworkMetadata:
    return ValidationFrameworkMetadata(
        framework_version=FRAMEWORK_VERSION,
        validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
        pipeline_version=PIPELINE_VERSION,
        registry_version=REGISTRY_VERSION,
    )


def _validation_result(
    execution_id: str = "EX-1",
    analysis_id: str = "AN-1",
    validation_id: str = "VAL-1",
    verdict: ValidationSubsystemVerdict = ValidationSubsystemVerdict.PASSED,
) -> ValidationResult:
    return ValidationResult(
        validation_id=validation_id,
        execution_id=execution_id,
        analysis_id=analysis_id,
        analysis_result=_analysis_result(execution_id, analysis_id),
        validation_summary=_validation_summary(),
        validation_statistics=_validation_statistics(),
        validation_configuration=ValidationConfiguration(),
        validation_framework_metadata=_validation_framework_metadata(),
        overall_verdict=verdict,
        started_at=_TS,
        completed_at=_TS,
    )


def _cp1_input(execution_id: str = "EX-1") -> CP1Input:
    analysis = _analysis_result(execution_id)
    return CP1Input(
        validation_result=_validation_result(execution_id),
        normalization_result=_normalization_result(analysis),
    )


def _cp1_finding(
    finding_id: str = "CP1F-1",
    *,
    verdict: ValidationVerdict = ValidationVerdict.WARN,
    criterion_id: str = "CP1-0001",
) -> CP1Finding:
    return CP1Finding(
        finding_id=finding_id,
        criterion_id=criterion_id,
        criterion_version="1.0",
        verdict_contribution=verdict,
        message="requirement is not engineering-ready",
        location="functionalRequirements[0]",
        recommendation="make the requirement atomic and testable",
        correlation_id="EX-1",
        created_at=_TS,
    )


def _cp1_result(**overrides: object) -> CP1Result:
    base: dict[str, object] = {
        "cp1_id": "CP1-RUN-1",
        "validation_id": "VAL-1",
        "execution_id": "EX-1",
        "analysis_id": "AN-1",
        "cp1_input": _cp1_input(),
        "overall_verdict": ValidationVerdict.PASS,
        "started_at": _TS,
        "completed_at": _TS,
    }
    base.update(overrides)
    return CP1Result(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. Version constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVersionConstants:
    def test_version_values(self) -> None:
        assert CP1_INPUT_VERSION == "1.0"
        assert CP1_RESULT_VERSION == "1.0"
        assert CP1_FINDING_VERSION == "1.0"

    def test_default_version_fields(self) -> None:
        assert _cp1_input().cp1_input_version == CP1_INPUT_VERSION
        assert _cp1_result().cp1_result_version == CP1_RESULT_VERSION
        assert _cp1_finding().cp1_finding_version == CP1_FINDING_VERSION

    def test_version_field_is_overridable(self) -> None:
        finding = _cp1_finding().model_copy(update={"cp1_finding_version": "9.9"})
        assert finding.cp1_finding_version == "9.9"


# ---------------------------------------------------------------------------
# 2. Construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConstruction:
    def test_finding_constructs_with_all_fields(self) -> None:
        finding = _cp1_finding()
        assert finding.finding_id == "CP1F-1"
        assert finding.criterion_id == "CP1-0001"
        assert finding.criterion_version == "1.0"
        assert finding.verdict_contribution == ValidationVerdict.WARN
        assert finding.evidence is None
        assert finding.metadata == {}

    def test_finding_evidence_is_optional(self) -> None:
        finding = _cp1_finding().model_copy(update={"evidence": "observed value"})
        assert finding.evidence == "observed value"

    def test_input_binds_both_artifacts(self) -> None:
        cp1_input = _cp1_input()
        assert isinstance(cp1_input.validation_result, ValidationResult)
        assert isinstance(cp1_input.normalization_result, NormalizationResult)
        assert cp1_input.metadata == {}

    def test_result_constructs_and_defaults_empty_findings(self) -> None:
        result = _cp1_result()
        assert result.cp1_id == "CP1-RUN-1"
        assert result.findings == ()
        assert result.overall_verdict == ValidationVerdict.PASS

    def test_result_carries_findings(self) -> None:
        result = _cp1_result(findings=(_cp1_finding(), _cp1_finding("CP1F-2")))
        assert len(result.findings) == 2
        assert result.findings[0].finding_id == "CP1F-1"


# ---------------------------------------------------------------------------
# 3. Immutability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImmutability:
    def test_finding_is_frozen(self) -> None:
        finding = _cp1_finding()
        with pytest.raises(ValidationError):
            finding.message = "mutated"  # type: ignore[misc]

    def test_input_is_frozen(self) -> None:
        cp1_input = _cp1_input()
        with pytest.raises(ValidationError):
            cp1_input.metadata = {"x": "y"}  # type: ignore[misc]

    def test_result_is_frozen(self) -> None:
        result = _cp1_result()
        with pytest.raises(ValidationError):
            result.overall_verdict = ValidationVerdict.FAIL  # type: ignore[misc]

    def test_findings_tuple_is_immutable(self) -> None:
        result = _cp1_result(findings=(_cp1_finding(),))
        assert isinstance(result.findings, tuple)
        with pytest.raises(TypeError):
            result.findings[0] = _cp1_finding("CP1F-9")  # type: ignore[index]


# ---------------------------------------------------------------------------
# 4. Strict schema behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStrictSchema:
    def test_finding_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            CP1Finding(  # type: ignore[call-arg]
                finding_id="F",
                criterion_id="CP1-0001",
                criterion_version="1.0",
                verdict_contribution=ValidationVerdict.WARN,
                message="m",
                location="l",
                recommendation="r",
                correlation_id="EX-1",
                created_at=_TS,
                unexpected="nope",
            )

    def test_finding_rejects_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            CP1Finding(  # type: ignore[call-arg]
                finding_id="F",
                criterion_id="CP1-0001",
                criterion_version="1.0",
                verdict_contribution=ValidationVerdict.WARN,
                message="m",
                location="l",
                recommendation="r",
                created_at=_TS,
            )

    def test_finding_rejects_invalid_verdict(self) -> None:
        with pytest.raises(ValidationError):
            CP1Finding(  # type: ignore[arg-type]
                finding_id="F",
                criterion_id="CP1-0001",
                criterion_version="1.0",
                verdict_contribution="not_a_verdict",
                message="m",
                location="l",
                recommendation="r",
                correlation_id="EX-1",
                created_at=_TS,
            )

    def test_input_rejects_extra_fields(self) -> None:
        analysis = _analysis_result()
        with pytest.raises(ValidationError):
            CP1Input(  # type: ignore[call-arg]
                validation_result=_validation_result(),
                normalization_result=_normalization_result(analysis),
                unexpected="nope",
            )

    def test_result_rejects_missing_required_field(self) -> None:
        with pytest.raises(ValidationError):
            CP1Result(  # type: ignore[call-arg]
                cp1_id="CP1-RUN-1",
                validation_id="VAL-1",
                execution_id="EX-1",
                analysis_id="AN-1",
                overall_verdict=ValidationVerdict.PASS,
                started_at=_TS,
                completed_at=_TS,
            )


# ---------------------------------------------------------------------------
# 5. Same-execution integrity invariant (CP1Input)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSameExecutionInvariant:
    def test_absent_correlation_is_accepted(self) -> None:
        # As produced, the NormalizationResult carries correlation_id=None.
        cp1_input = _cp1_input("EX-1")
        assert cp1_input.normalization_result.correlation_id is None

    def test_matching_correlation_is_accepted(self) -> None:
        analysis = _analysis_result("EX-7")
        norm = _normalization_result(analysis).model_copy(update={"correlation_id": "EX-7"})
        cp1_input = CP1Input(
            validation_result=_validation_result("EX-7"),
            normalization_result=norm,
        )
        assert cp1_input.normalization_result.correlation_id == "EX-7"

    def test_mismatched_correlation_is_rejected(self) -> None:
        analysis = _analysis_result("EX-7")
        norm = _normalization_result(analysis).model_copy(update={"correlation_id": "OTHER"})
        with pytest.raises(ValidationError):
            CP1Input(
                validation_result=_validation_result("EX-7"),
                normalization_result=norm,
            )


# ---------------------------------------------------------------------------
# 6. Reference-not-copy binding & ownership
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBindingAndOwnership:
    def test_input_references_are_the_same_instances(self) -> None:
        analysis = _analysis_result()
        validation_result = _validation_result()
        norm = _normalization_result(analysis)
        cp1_input = CP1Input(validation_result=validation_result, normalization_result=norm)
        assert cp1_input.validation_result is validation_result
        assert cp1_input.normalization_result is norm

    def test_result_preserves_its_input_instance(self) -> None:
        cp1_input = _cp1_input()
        result = _cp1_result(cp1_input=cp1_input)
        assert result.cp1_input is cp1_input

    def test_result_owns_findings_instances(self) -> None:
        finding = _cp1_finding()
        result = _cp1_result(findings=(finding,))
        assert result.findings[0] is finding


# ---------------------------------------------------------------------------
# 7. Serialization (camelCase + JSON round-trip + enum-by-value)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSerialization:
    def test_finding_serializes_to_camel(self) -> None:
        dumped = _cp1_finding().model_dump(by_alias=True)
        assert "findingId" in dumped
        assert "criterionId" in dumped
        assert "verdictContribution" in dumped
        assert "cp1FindingVersion" in dumped
        assert "finding_id" not in dumped

    def test_verdict_serializes_to_string_value(self) -> None:
        dumped = _cp1_finding(verdict=ValidationVerdict.FAIL).model_dump(by_alias=True)
        assert dumped["verdictContribution"] == "fail"

    def test_result_verdict_serializes_to_string_value(self) -> None:
        dumped = _cp1_result(overall_verdict=ValidationVerdict.WARN).model_dump(by_alias=True)
        assert dumped["overallVerdict"] == "warn"

    def test_finding_json_roundtrip(self) -> None:
        original = _cp1_finding()
        restored = CP1Finding.model_validate_json(original.model_dump_json(by_alias=True))
        assert restored == original

    def test_finding_roundtrip_by_field_name(self) -> None:
        # populate_by_name=True: snake_case input is also accepted.
        original = _cp1_finding()
        restored = CP1Finding.model_validate(original.model_dump())
        assert restored == original

    def test_result_json_roundtrip(self) -> None:
        # CP1Result contains a NormalizationResult whose ``parsed_response`` is an
        # ``Any``-typed nested model; it reloads as a plain dict, so the round-trip
        # is verified on the serialized form (the meaningful, deterministic check).
        original = _cp1_result(findings=(_cp1_finding(),))
        restored = CP1Result.model_validate_json(original.model_dump_json(by_alias=True))
        assert restored.model_dump(by_alias=True, mode="json") == original.model_dump(
            by_alias=True, mode="json"
        )

    def test_input_json_roundtrip(self) -> None:
        original = _cp1_input()
        restored = CP1Input.model_validate_json(original.model_dump_json(by_alias=True))
        assert restored.model_dump(by_alias=True, mode="json") == original.model_dump(
            by_alias=True, mode="json"
        )

    def test_datetime_roundtrips_to_iso8601(self) -> None:
        dumped = _cp1_finding().model_dump(by_alias=True, mode="json")
        assert dumped["createdAt"].startswith("2026-07-06T12:00:00")


# ---------------------------------------------------------------------------
# 8. Equality (value semantics)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEquality:
    def test_findings_with_same_values_are_equal(self) -> None:
        assert _cp1_finding() == _cp1_finding()

    def test_findings_with_different_values_differ(self) -> None:
        assert _cp1_finding() != _cp1_finding("CP1F-2")
        assert _cp1_finding(verdict=ValidationVerdict.WARN) != _cp1_finding(
            verdict=ValidationVerdict.FAIL
        )

    def test_results_with_same_values_are_equal(self) -> None:
        # Share the same CP1Input instance so equality reflects the CP1Result's own
        # value semantics (the NormalizationResult carries a fresh id per build).
        cp1_input = _cp1_input()
        assert _cp1_result(cp1_input=cp1_input) == _cp1_result(cp1_input=cp1_input)

    def test_inputs_with_same_values_are_equal(self) -> None:
        validation_result = _validation_result()
        norm = _normalization_result(_analysis_result())
        assert CP1Input(
            validation_result=validation_result, normalization_result=norm
        ) == CP1Input(validation_result=validation_result, normalization_result=norm)


# ---------------------------------------------------------------------------
# 9. Default factories & metadata isolation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDefaults:
    def test_metadata_defaults_are_independent_instances(self) -> None:
        a = _cp1_finding()
        b = _cp1_finding("CP1F-2")
        assert a.metadata == {} == b.metadata
        assert a.metadata is not b.metadata

    def test_findings_default_is_empty_tuple(self) -> None:
        assert _cp1_result().findings == ()

    def test_metadata_is_preserved_verbatim(self) -> None:
        finding = _cp1_finding().model_copy(update={"metadata": {"k": "v"}})
        assert finding.metadata == {"k": "v"}


# ---------------------------------------------------------------------------
# 10. Determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeterminism:
    def test_serialization_is_deterministic(self) -> None:
        finding = _cp1_finding()
        assert finding.model_dump_json(by_alias=True) == finding.model_dump_json(by_alias=True)

    def test_repeated_construction_is_equal(self) -> None:
        cp1_input = _cp1_input()
        assert _cp1_result(cp1_input=cp1_input) == _cp1_result(cp1_input=cp1_input)
