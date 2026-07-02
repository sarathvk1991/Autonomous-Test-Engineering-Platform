"""Unit tests for the Validation Canonical Models.

Covers the implementation-independent information model defined in
``docs/architecture/validation-canonical-models.md``:

* immutability (frozen models reject mutation)
* strict mode (unknown fields are rejected)
* camelCase serialization
* enum serialization (severity / verdict / health serialise to string values)
* relationship ownership (ValidationResult owns / references / contains)
* default factories (metadata, category_counts, issue collection)
* metadata isolation (independent dict instances per model)
* timestamps
* framework metadata provenance
* an empty ValidationResult is a valid execution
* ValidationPipeline always returns a valid ValidationResult
* ValidationSummary derived state
* ValidationStatistics telemetry

Design constraints
------------------
* No validation rules.
* No JSON-schema validation.
* No real AI responses (a minimal AnalysisResult carrier is constructed locally).
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
from requirement_intelligence.normalization.response import ResponseNormalizer
from requirement_intelligence.validation import (
    ValidationInput,
    ValidationPipeline,
    ValidationRegistry,
    ValidationRule,
    ValidationRuleMetadata,
)
from requirement_intelligence.validation.models import (
    DEFAULT_VALIDATION_CONTRACT_VERSION,
    FRAMEWORK_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    ValidationConfiguration,
    ValidationFrameworkMetadata,
    ValidationHealth,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStatistics,
    ValidationSummary,
    ValidationVerdict,
)
from requirement_intelligence.validation.validation_rule_layer import LAYER_ORDER, ValidationLayer

_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Local builders — no rules, no AI
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


def _validation_input_for(analysis: AnalysisResult) -> ValidationInput:
    """Bind *analysis* to a real ``NormalizationResult`` (the pipeline input; ADR-0003)."""
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return ValidationInput(
        analysis_result=analysis,
        normalization_result=normalizer.normalize(analysis.llm_response),
    )


def _input(execution_id: str = "EX-1", analysis_id: str = "AN-1") -> ValidationInput:
    return _validation_input_for(_analysis_result(execution_id, analysis_id))


def _issue(
    issue_id: str = "ISS-1",
    *,
    severity: ValidationSeverity = ValidationSeverity.ERROR,
    layer: ValidationLayer = ValidationLayer.EVIDENCE,
    blocking: bool = False,
    category: str = "evidence",
) -> ValidationIssue:
    return ValidationIssue(
        issue_id=issue_id,
        category=category,
        severity=severity,
        validation_layer=layer,
        rule_id="EVIDENCE-0001",
        rule_version="1.0.0",
        message="finding",
        location="$",
        recommendation="fix it",
        blocking=blocking,
        correlation_id="EX-1",
        created_at=_TS,
    )


def _summary(**overrides: object) -> ValidationSummary:
    base: dict[str, object] = {
        "total_issues": 0,
        "info_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "critical_count": 0,
        "blocking_issue_count": 0,
        "overall_health": ValidationHealth.HEALTHY,
    }
    base.update(overrides)
    return ValidationSummary(**base)  # type: ignore[arg-type]


def _statistics() -> ValidationStatistics:
    return ValidationStatistics(
        validation_duration_ms=1.5,
        rules_executed=2,
        rules_passed=1,
        rules_failed=1,
        started_at=_TS,
        completed_at=_TS,
        validator_version=FRAMEWORK_VERSION,
        validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
        execution_id="EX-1",
    )


def _framework_metadata() -> ValidationFrameworkMetadata:
    return ValidationFrameworkMetadata(
        framework_version=FRAMEWORK_VERSION,
        validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
        pipeline_version=PIPELINE_VERSION,
        registry_version=REGISTRY_VERSION,
    )


def _result(**overrides: object) -> ValidationResult:
    base: dict[str, object] = {
        "validation_id": "VAL-1",
        "execution_id": "EX-1",
        "analysis_id": "AN-1",
        "analysis_result": _analysis_result(),
        "validation_summary": _summary(),
        "validation_statistics": _statistics(),
        "validation_configuration": ValidationConfiguration(),
        "validation_framework_metadata": _framework_metadata(),
        "overall_verdict": ValidationVerdict.PASSED,
        "started_at": _TS,
        "completed_at": _TS,
    }
    base.update(overrides)
    return ValidationResult(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. Enumerations
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnums:
    def test_severity_values(self) -> None:
        assert {s.value for s in ValidationSeverity} == {"info", "warning", "error", "critical"}

    def test_verdict_values(self) -> None:
        assert {v.value for v in ValidationVerdict} == {
            "passed",
            "passed_with_warnings",
            "failed",
            "blocked",
        }

    def test_health_values(self) -> None:
        assert {h.value for h in ValidationHealth} == {
            "healthy",
            "warning",
            "degraded",
            "critical",
        }


# ---------------------------------------------------------------------------
# 2. Immutability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImmutability:
    def test_issue_is_frozen(self) -> None:
        issue = _issue()
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_summary_is_frozen(self) -> None:
        summary = _summary()
        with pytest.raises(ValidationError):
            summary.total_issues = 5  # type: ignore[misc]

    def test_statistics_is_frozen(self) -> None:
        stats = _statistics()
        with pytest.raises(ValidationError):
            stats.rules_executed = 99  # type: ignore[misc]

    def test_configuration_is_frozen(self) -> None:
        config = ValidationConfiguration()
        with pytest.raises(ValidationError):
            config.collect_statistics = False  # type: ignore[misc]

    def test_framework_metadata_is_frozen(self) -> None:
        meta = _framework_metadata()
        with pytest.raises(ValidationError):
            meta.framework_version = "9.9.9"  # type: ignore[misc]

    def test_result_is_frozen(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.overall_verdict = ValidationVerdict.FAILED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 3. Strict mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStrictMode:
    def test_issue_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            ValidationIssue(  # type: ignore[call-arg]
                issue_id="X",
                category="c",
                severity=ValidationSeverity.INFO,
                validation_layer=ValidationLayer.SYNTAX,
                rule_id="SYNTAX-0001",
                rule_version="1.0.0",
                message="m",
                location="l",
                recommendation="r",
                blocking=False,
                correlation_id="EX-1",
                created_at=_TS,
                unexpected="nope",
            )

    def test_configuration_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            ValidationConfiguration(unexpected="nope")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 4. camelCase + enum serialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSerialization:
    def test_issue_camel_case_keys(self) -> None:
        dumped = _issue().model_dump(by_alias=True, mode="json")
        assert "issueId" in dumped
        assert "ruleVersion" in dumped
        assert "correlationId" in dumped
        assert "validationLayer" in dumped
        # snake_case keys must NOT be present under by_alias.
        assert "issue_id" not in dumped

    def test_issue_enum_serializes_to_value(self) -> None:
        dumped = _issue(severity=ValidationSeverity.CRITICAL).model_dump(by_alias=True, mode="json")
        assert dumped["severity"] == "critical"
        assert dumped["validationLayer"] == "evidence"

    def test_statistics_camel_case_keys(self) -> None:
        dumped = _statistics().model_dump(by_alias=True, mode="json")
        assert "validationDurationMs" in dumped
        assert "rulesExecuted" in dumped
        assert "validatorVersion" in dumped
        assert "validationContractVersion" in dumped

    def test_result_verdict_serializes_to_value(self) -> None:
        dumped = _result(overall_verdict=ValidationVerdict.BLOCKED).model_dump(
            by_alias=True, mode="json"
        )
        assert dumped["overallVerdict"] == "blocked"

    def test_summary_health_serializes_to_value(self) -> None:
        dumped = _summary(overall_health=ValidationHealth.DEGRADED).model_dump(
            by_alias=True, mode="json"
        )
        assert dumped["overallHealth"] == "degraded"

    def test_configuration_enabled_layers_serialize_to_values(self) -> None:
        dumped = ValidationConfiguration().model_dump(by_alias=True, mode="json")
        assert dumped["enabledLayers"][0] == "transport"
        assert dumped["minimumSeverity"] == "info"


# ---------------------------------------------------------------------------
# 5. Default factories + metadata isolation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDefaults:
    def test_issue_metadata_defaults_to_empty_dict(self) -> None:
        assert _issue().metadata == {}

    def test_issue_evidence_optional(self) -> None:
        assert _issue().evidence is None

    def test_summary_category_counts_defaults_to_empty_dict(self) -> None:
        assert _summary().category_counts == {}

    def test_result_issue_collection_defaults_to_empty_tuple(self) -> None:
        assert _result().validation_issues == ()

    def test_configuration_defaults_to_all_layers(self) -> None:
        config = ValidationConfiguration()
        assert tuple(config.enabled_layers) == tuple(LAYER_ORDER)
        assert config.validation_contract_version == DEFAULT_VALIDATION_CONTRACT_VERSION
        assert config.collect_statistics is True
        assert config.collect_metadata is True

    def test_metadata_is_isolated_per_instance(self) -> None:
        a = _issue("A")
        b = _issue("B")
        # Default-factory dicts must be distinct objects, not a shared default.
        assert a.metadata is not b.metadata


# ---------------------------------------------------------------------------
# 6. Timestamps
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTimestamps:
    def test_issue_created_at_preserved(self) -> None:
        assert _issue().created_at == _TS

    def test_result_timestamps_preserved(self) -> None:
        result = _result()
        assert result.started_at == _TS
        assert result.completed_at == _TS

    def test_statistics_timestamps_preserved(self) -> None:
        stats = _statistics()
        assert stats.started_at == _TS
        assert stats.completed_at == _TS


# ---------------------------------------------------------------------------
# 7. Relationship ownership / reference / containment
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRelationships:
    def test_result_owns_summary_and_statistics(self) -> None:
        summary = _summary(total_issues=1, error_count=1)
        stats = _statistics()
        result = _result(validation_summary=summary, validation_statistics=stats)
        assert result.validation_summary == summary
        assert result.validation_statistics == stats

    def test_result_owns_issue_collection(self) -> None:
        issues = (_issue("A"), _issue("B"))
        result = _result(validation_issues=issues)
        assert result.validation_issues == issues
        assert isinstance(result.validation_issues, tuple)

    def test_result_references_configuration_and_framework_metadata(self) -> None:
        config = ValidationConfiguration()
        meta = _framework_metadata()
        result = _result(validation_configuration=config, validation_framework_metadata=meta)
        assert result.validation_configuration == config
        assert result.validation_framework_metadata == meta

    def test_result_contains_original_analysis_result(self) -> None:
        analysis = _analysis_result()
        result = _result(analysis_result=analysis)
        assert result.analysis_result == analysis

    def test_summary_contains_no_issue_objects(self) -> None:
        """Summary holds counts only — never ValidationIssue instances."""
        summary = _summary(total_issues=3, error_count=3, category_counts={"evidence": 3})
        dumped = summary.model_dump()
        for value in dumped.values():
            assert not isinstance(value, ValidationIssue)


# ---------------------------------------------------------------------------
# 8. ValidationFrameworkMetadata provenance
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFrameworkMetadata:
    def test_carries_four_versions(self) -> None:
        meta = _framework_metadata()
        assert meta.framework_version == FRAMEWORK_VERSION
        assert meta.pipeline_version == PIPELINE_VERSION
        assert meta.registry_version == REGISTRY_VERSION
        assert meta.validation_contract_version == DEFAULT_VALIDATION_CONTRACT_VERSION

    def test_camel_case_keys(self) -> None:
        dumped = _framework_metadata().model_dump(by_alias=True, mode="json")
        assert set(dumped) >= {
            "frameworkVersion",
            "validationContractVersion",
            "pipelineVersion",
            "registryVersion",
        }


# ---------------------------------------------------------------------------
# 9. ValidationResult as the framework output (via the pipeline)
# ---------------------------------------------------------------------------


class _IssuingRule(ValidationRule):
    """Local rule that emits a fixed set of issues — for pipeline output tests."""

    def __init__(self, rule_id: str, layer: ValidationLayer, issues: list[ValidationIssue]) -> None:
        self._metadata = ValidationRuleMetadata(rule_id, rule_id, layer)
        self._issues = issues

    @property
    def metadata(self) -> ValidationRuleMetadata:
        return self._metadata

    def validate(self, response: object) -> list[ValidationIssue]:
        return list(self._issues)


@pytest.mark.unit
class TestPipelineReturnsValidationResult:
    def test_empty_pipeline_returns_valid_passed_result(self) -> None:
        pipeline = ValidationPipeline(ValidationRegistry())
        result = pipeline.run(_input())
        assert isinstance(result, ValidationResult)
        assert result.validation_issues == ()
        assert result.overall_verdict == ValidationVerdict.PASSED

    def test_empty_result_still_populates_owned_models(self) -> None:
        result = ValidationPipeline(ValidationRegistry()).run(_input())
        # Summary, statistics, framework metadata are all populated — not None.
        assert result.validation_summary.total_issues == 0
        assert result.validation_summary.overall_health == ValidationHealth.HEALTHY
        assert result.validation_statistics.rules_executed == 0
        assert result.validation_framework_metadata.framework_version == FRAMEWORK_VERSION

    def test_result_preserves_analysis_identity(self) -> None:
        analysis = _analysis_result(execution_id="EX-77", analysis_id="AN-77")
        result = ValidationPipeline(ValidationRegistry()).run(_validation_input_for(analysis))
        assert result.execution_id == "EX-77"
        assert result.analysis_id == "AN-77"
        assert result.analysis_result is analysis

    def test_verdict_blocked_when_critical_present(self) -> None:
        registry = ValidationRegistry()
        registry.register(
            _IssuingRule(
                "SYNTAX-0001",
                ValidationLayer.SYNTAX,
                [_issue("C1", severity=ValidationSeverity.CRITICAL, layer=ValidationLayer.SYNTAX)],
            )
        )
        result = ValidationPipeline(registry).run(_input())
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert result.validation_summary.overall_health == ValidationHealth.CRITICAL

    def test_verdict_passed_with_warnings(self) -> None:
        registry = ValidationRegistry()
        registry.register(
            _IssuingRule(
                "CONTENT-0001",
                ValidationLayer.CONTENT,
                [_issue("W1", severity=ValidationSeverity.WARNING, layer=ValidationLayer.CONTENT)],
            )
        )
        result = ValidationPipeline(registry).run(_input())
        assert result.overall_verdict == ValidationVerdict.PASSED_WITH_WARNINGS
        assert result.validation_summary.overall_health == ValidationHealth.WARNING


# ---------------------------------------------------------------------------
# 10. Derived summary + telemetry through the pipeline
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDerivedSummaryAndStatistics:
    def _result_with_mixed_issues(self) -> ValidationResult:
        registry = ValidationRegistry()
        registry.register(
            _IssuingRule(
                "EVIDENCE-0001",
                ValidationLayer.EVIDENCE,
                [
                    _issue("E1", severity=ValidationSeverity.ERROR, blocking=True),
                    _issue("I1", severity=ValidationSeverity.INFO),
                ],
            )
        )
        registry.register(
            _IssuingRule(
                "REASONING-0001",
                ValidationLayer.REASONING,
                [
                    _issue(
                        "W1",
                        severity=ValidationSeverity.WARNING,
                        layer=ValidationLayer.REASONING,
                        category="reasoning",
                    )
                ],
            )
        )
        return ValidationPipeline(registry).run(_input())

    def test_summary_counts_are_derived(self) -> None:
        summary = self._result_with_mixed_issues().validation_summary
        assert summary.total_issues == 3
        assert summary.info_count == 1
        assert summary.warning_count == 1
        assert summary.error_count == 1
        assert summary.critical_count == 0
        assert summary.blocking_issue_count == 1

    def test_summary_category_counts_are_derived(self) -> None:
        summary = self._result_with_mixed_issues().validation_summary
        assert summary.category_counts == {"evidence": 2, "reasoning": 1}

    def test_verdict_failed_when_error_present(self) -> None:
        result = self._result_with_mixed_issues()
        assert result.overall_verdict == ValidationVerdict.FAILED
        assert result.validation_summary.overall_health == ValidationHealth.DEGRADED

    def test_statistics_record_rule_outcomes(self) -> None:
        result = self._result_with_mixed_issues()
        stats = result.validation_statistics
        assert stats.rules_executed == 2
        assert stats.rules_failed == 2  # both rules produced at least one issue
        assert stats.rules_passed == 0
        assert stats.validation_duration_ms >= 0.0
        assert stats.execution_id == "EX-1"

    def test_statistics_passed_rule_counts(self) -> None:
        registry = ValidationRegistry()
        registry.register(_IssuingRule("SYNTAX-0001", ValidationLayer.SYNTAX, []))
        result = ValidationPipeline(registry).run(_input())
        assert result.validation_statistics.rules_executed == 1
        assert result.validation_statistics.rules_passed == 1
        assert result.validation_statistics.rules_failed == 0
