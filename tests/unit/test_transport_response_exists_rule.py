"""Unit tests for TRANSPORT-0001 ResponseExistsRule.

Covers
------
* Metadata & rule identity — matches the catalog entry exactly.
* Successful validation — a response with an LLM response yields no findings.
* Missing response — exactly one fully-populated ValidationIssue.
* ValidationIssue contents — severity, blocking, recommendation, message, etc.
* Immutability — the issue is frozen; the AnalysisResult is never mutated.
* Determinism & idempotency — repeated calls yield identical finding content.
* Registry registration — the rule registers via the existing mechanism.
* Pipeline execution — the pipeline runs the rule and returns a ValidationResult.
* Response Validator integration — the Validator executes the rule naturally.

Design constraints
------------------
* No mocking of the rule's logic; it is exercised directly.
* The "missing response" case uses a lightweight stand-in object (a valid
  ``AnalysisResult`` cannot hold a ``None`` ``llm_response`` — the model requires
  it — which is exactly why the rule is the architectural guarantee).
* No real AI responses; inputs are built in-memory.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.validation import (
    ValidationConfiguration,
    ValidationLayer,
    ValidationPipeline,
    ValidationRegistry,
    ValidationRule,
    ValidationSeverity,
    ValidationVerdict,
)
from requirement_intelligence.validation.response import ResponseValidator
from requirement_intelligence.validation.rules.transport import (
    ResponseExistsRule,
    register_transport_rules,
)

_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)

# Issue fields compared for determinism/idempotency — everything except the
# observational ``created_at`` timestamp (the one inherently time-varying field).
_CONTENT_FIELDS = (
    "issue_id",
    "category",
    "severity",
    "validation_layer",
    "rule_id",
    "rule_version",
    "message",
    "location",
    "evidence",
    "recommendation",
    "blocking",
    "correlation_id",
)


def _analysis_result(execution_id: str = "EX-1", analysis_id: str = "AN-1") -> AnalysisResult:
    return AnalysisResult(
        analysis_id=analysis_id,
        execution_id=execution_id,
        source_consolidated_id="C-1",
        prompt_version="p1",
        reasoning_contract_version="r1",
        provider="gemini",
        model="model",
        started_at=_TS,
        completed_at=_TS,
        duration_ms=1.0,
        llm_response=LLMResponse(provider="gemini", model="model", generated_text="x"),
    )


def _missing_response(execution_id: str = "EX-1") -> Any:
    """A stand-in analysed response whose LLM response is absent."""
    return SimpleNamespace(llm_response=None, execution_id=execution_id)


def _content(issue: Any) -> tuple[Any, ...]:
    return tuple(getattr(issue, field) for field in _CONTENT_FIELDS)


# ---------------------------------------------------------------------------
# 1. Metadata & identity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetadata:
    def test_is_a_validation_rule(self) -> None:
        assert isinstance(ResponseExistsRule(), ValidationRule)

    def test_rule_id(self) -> None:
        assert ResponseExistsRule().rule_id == "TRANSPORT-0001"

    def test_rule_name(self) -> None:
        assert ResponseExistsRule().rule_name == "Response Exists"

    def test_layer(self) -> None:
        assert ResponseExistsRule().validation_layer == ValidationLayer.TRANSPORT

    def test_rule_version(self) -> None:
        assert ResponseExistsRule().rule_version == "1.0.0"

    def test_enabled_by_default(self) -> None:
        assert ResponseExistsRule().enabled is True

    def test_metadata_is_stable_across_access(self) -> None:
        rule = ResponseExistsRule()
        assert rule.metadata is rule.metadata


# ---------------------------------------------------------------------------
# 2. Successful validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSuccessfulValidation:
    def test_present_response_yields_no_issues(self) -> None:
        assert ResponseExistsRule().validate(_analysis_result()) == []

    def test_success_returns_empty_list_type(self) -> None:
        result = ResponseExistsRule().validate(_analysis_result())
        assert isinstance(result, list)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# 3. Missing response & issue contents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMissingResponse:
    def test_missing_response_yields_one_issue(self) -> None:
        issues = ResponseExistsRule().validate(_missing_response())
        assert len(issues) == 1

    def test_issue_severity_is_critical(self) -> None:
        issue = ResponseExistsRule().validate(_missing_response())[0]
        assert issue.severity == ValidationSeverity.CRITICAL

    def test_issue_is_blocking(self) -> None:
        issue = ResponseExistsRule().validate(_missing_response())[0]
        assert issue.blocking is True

    def test_issue_layer_and_category(self) -> None:
        issue = ResponseExistsRule().validate(_missing_response())[0]
        # ``ValidationIssue`` stores enum fields by value (Schema use_enum_values).
        assert issue.validation_layer == ValidationLayer.TRANSPORT.value
        assert issue.category == "transport"

    def test_issue_identity_fields(self) -> None:
        issue = ResponseExistsRule().validate(_missing_response())[0]
        assert issue.rule_id == "TRANSPORT-0001"
        assert issue.rule_version == "1.0.0"
        assert issue.issue_id == "TRANSPORT-0001:llm_response"
        assert issue.location == "llm_response"

    def test_issue_message(self) -> None:
        issue = ResponseExistsRule().validate(_missing_response())[0]
        assert issue.message == "The analysis result does not contain an LLM response."

    def test_issue_recommendation(self) -> None:
        issue = ResponseExistsRule().validate(_missing_response())[0]
        assert issue.recommendation == "Regenerate the AI response before continuing."

    def test_issue_evidence_is_none(self) -> None:
        issue = ResponseExistsRule().validate(_missing_response())[0]
        assert issue.evidence is None

    def test_issue_correlation_from_response(self) -> None:
        issue = ResponseExistsRule().validate(_missing_response("EX-77"))[0]
        assert issue.correlation_id == "EX-77"

    def test_issue_created_at_populated(self) -> None:
        issue = ResponseExistsRule().validate(_missing_response())[0]
        assert isinstance(issue.created_at, datetime)


# ---------------------------------------------------------------------------
# 4. Immutability, determinism, idempotency, purity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleIndependence:
    def test_issue_is_immutable(self) -> None:
        issue = ResponseExistsRule().validate(_missing_response())[0]
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_does_not_mutate_analysis_result(self) -> None:
        rule = ResponseExistsRule()
        analysis = _analysis_result()
        before = analysis.model_copy(deep=True)
        rule.validate(analysis)
        assert analysis == before

    def test_does_not_mutate_missing_response_input(self) -> None:
        rule = ResponseExistsRule()
        stand_in = _missing_response("EX-9")
        rule.validate(stand_in)
        assert stand_in.llm_response is None
        assert stand_in.execution_id == "EX-9"

    def test_deterministic_finding_content(self) -> None:
        rule = ResponseExistsRule()
        stand_in = _missing_response()
        first = rule.validate(stand_in)[0]
        second = rule.validate(stand_in)[0]
        assert _content(first) == _content(second)

    def test_idempotent_no_cumulative_effect(self) -> None:
        rule = ResponseExistsRule()
        stand_in = _missing_response()
        # Repeated evaluation always yields exactly one issue — no accumulation.
        assert len(rule.validate(stand_in)) == 1
        assert len(rule.validate(stand_in)) == 1
        # And the pass path stays empty across repeats.
        analysis = _analysis_result()
        assert rule.validate(analysis) == []
        assert rule.validate(analysis) == []


# ---------------------------------------------------------------------------
# 5. Registry registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_register_transport_rules_includes_this_rule(self) -> None:
        # ``register_transport_rules`` registers the whole Transport set; this
        # rule must be present (membership, not exclusivity, as the set grows).
        registry = ValidationRegistry()
        register_transport_rules(registry)
        assert "TRANSPORT-0001" in registry.list_rule_ids()

    def test_rule_can_be_registered_directly(self) -> None:
        registry = ValidationRegistry()
        registry.register(ResponseExistsRule())
        rules = registry.get_enabled_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], ResponseExistsRule)


# ---------------------------------------------------------------------------
# 6. Pipeline execution (TRANSPORT-0001 in isolation)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPipelineExecution:
    def _pipeline(self) -> ValidationPipeline:
        # Isolate TRANSPORT-0001 so these assertions stay stable as the Transport
        # rule set grows; the full-set behaviour is covered by the 0002 suite.
        registry = ValidationRegistry()
        registry.register(ResponseExistsRule())
        return ValidationPipeline(registry)

    def test_pipeline_executes_rule_and_passes(self) -> None:
        result = self._pipeline().run(_analysis_result())
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0

    def test_pipeline_counts_rule_execution(self) -> None:
        result = self._pipeline().run(_analysis_result())
        assert result.validation_statistics.rules_executed == 1
        assert result.validation_statistics.rules_passed == 1
        assert result.validation_statistics.rules_failed == 0

    def test_pipeline_preserves_analysis_result(self) -> None:
        analysis = _analysis_result()
        result = self._pipeline().run(analysis)
        assert result.analysis_result is analysis


# ---------------------------------------------------------------------------
# 7. Response Validator integration (TRANSPORT-0001 in isolation)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResponseValidatorIntegration:
    def _validator(self) -> ResponseValidator:
        registry = ValidationRegistry()
        registry.register(ResponseExistsRule())
        pipeline = ValidationPipeline(registry)
        return ResponseValidator(registry, pipeline, ValidationConfiguration())

    def test_validator_executes_rule_naturally(self) -> None:
        result = self._validator().validate(_analysis_result())
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0

    def test_validator_reports_rule_executed(self) -> None:
        result = self._validator().validate(_analysis_result())
        assert result.validation_statistics.rules_executed == 1
