"""Unit tests for TRANSPORT-0003 TimeoutRule.

Covers
------
* Metadata & rule identity — matches the catalog entry exactly.
* Successful execution — a completed execution yields no findings.
* Timed-out execution — yields exactly one finding.
* ValidationIssue contents — severity, blocking, recommendation, message, etc.
* Immutability, determinism, idempotency, non-mutation.
* Registry registration — all three Transport rules register, in order.
* Pipeline & Response Validator integration — all three rules execute naturally.
* Timeout end-to-end — TRANSPORT-0001 passes, TRANSPORT-0002 passes,
  TRANSPORT-0003 fails.

Design constraints
------------------
* No mocking of rule logic; the rule is exercised directly.
* A real ``AnalysisResult`` is used throughout; the normalized
  ``execution_status`` on its ``LLMResponse`` is the only field that matters.
* Provider-independent: the rule reads ``ExecutionStatus`` only — never a
  provider-specific timeout code.

Note on verdict
---------------
The TRANSPORT-0003 issue is ``CRITICAL`` (per the catalog), and the frozen
verdict model maps any ``CRITICAL`` finding to ``BLOCKED`` (not ``FAILED``).  The
timeout end-to-end tests therefore assert ``BLOCKED`` — the response is correctly
*rejected* (never ``PASSED``).
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
    EmptyResponseRule,
    ResponseExistsRule,
    TimeoutRule,
    register_transport_rules,
)
from shared.enums.base import ExecutionStatus

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


def _analysis_result(
    execution_status: ExecutionStatus = ExecutionStatus.COMPLETED,
    *,
    generated_text: str = "a verdict",
    execution_id: str = "EX-1",
) -> AnalysisResult:
    return AnalysisResult(
        analysis_id="AN-1",
        execution_id=execution_id,
        source_consolidated_id="C-1",
        prompt_version="p1",
        reasoning_contract_version="r1",
        provider="gemini",
        model="model",
        started_at=_TS,
        completed_at=_TS,
        duration_ms=1.0,
        llm_response=LLMResponse(
            provider="gemini",
            model="model",
            generated_text=generated_text,
            execution_status=execution_status,
        ),
    )


def _content(issue: Any) -> tuple[Any, ...]:
    return tuple(getattr(issue, field) for field in _CONTENT_FIELDS)


# ---------------------------------------------------------------------------
# 1. Metadata & identity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetadata:
    def test_is_a_validation_rule(self) -> None:
        assert isinstance(TimeoutRule(), ValidationRule)

    def test_rule_id(self) -> None:
        assert TimeoutRule().rule_id == "TRANSPORT-0003"

    def test_rule_name(self) -> None:
        assert TimeoutRule().rule_name == "Timeout"

    def test_layer(self) -> None:
        assert TimeoutRule().validation_layer == ValidationLayer.TRANSPORT

    def test_rule_version(self) -> None:
        assert TimeoutRule().rule_version == "1.0.0"

    def test_enabled_by_default(self) -> None:
        assert TimeoutRule().enabled is True

    def test_metadata_is_stable_across_access(self) -> None:
        rule = TimeoutRule()
        assert rule.metadata is rule.metadata


# ---------------------------------------------------------------------------
# 2. Successful execution
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSuccessfulExecution:
    def test_completed_execution_yields_no_issues(self) -> None:
        assert TimeoutRule().validate(_analysis_result(ExecutionStatus.COMPLETED)) == []

    def test_default_status_passes(self) -> None:
        # An LLMResponse constructed without an explicit status defaults to
        # COMPLETED — the rule must pass (backward compatibility).
        result = AnalysisResult(
            analysis_id="AN-1",
            execution_id="EX-1",
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
        assert TimeoutRule().validate(result) == []

    def test_defers_when_llm_response_absent(self) -> None:
        stand_in = SimpleNamespace(llm_response=None, execution_id="EX-1")
        assert TimeoutRule().validate(stand_in) == []

    def test_failed_status_passes_reserved_for_provider_failure(self) -> None:
        # TimeoutRule fails ONLY on TIMEOUT; a delivery-boundary FAILED outcome is
        # a sibling concern owned by the reserved TRANSPORT-0004 (ProviderFailure),
        # so TimeoutRule must not react to it. This confirms the outcomes are
        # orthogonal and the execution model is ready for TRANSPORT-0004.
        assert TimeoutRule().validate(_analysis_result(ExecutionStatus.FAILED)) == []


# ---------------------------------------------------------------------------
# 3. Timed-out execution & issue contents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTimeout:
    def test_timeout_yields_one_issue(self) -> None:
        assert len(TimeoutRule().validate(_analysis_result(ExecutionStatus.TIMEOUT))) == 1

    def test_issue_severity_is_critical(self) -> None:
        issue = TimeoutRule().validate(_analysis_result(ExecutionStatus.TIMEOUT))[0]
        assert issue.severity == ValidationSeverity.CRITICAL

    def test_issue_is_blocking(self) -> None:
        issue = TimeoutRule().validate(_analysis_result(ExecutionStatus.TIMEOUT))[0]
        assert issue.blocking is True

    def test_issue_layer_and_category(self) -> None:
        issue = TimeoutRule().validate(_analysis_result(ExecutionStatus.TIMEOUT))[0]
        # ``ValidationIssue`` stores enum fields by value (Schema use_enum_values).
        assert issue.validation_layer == ValidationLayer.TRANSPORT.value
        assert issue.category == "transport"

    def test_issue_identity_fields(self) -> None:
        issue = TimeoutRule().validate(_analysis_result(ExecutionStatus.TIMEOUT))[0]
        assert issue.rule_id == "TRANSPORT-0003"
        assert issue.rule_version == "1.0.0"
        assert issue.issue_id == "TRANSPORT-0003:timeout"
        assert issue.location == "execution"

    def test_issue_message(self) -> None:
        issue = TimeoutRule().validate(_analysis_result(ExecutionStatus.TIMEOUT))[0]
        assert issue.message == "The AI execution terminated because of a timeout."

    def test_issue_recommendation(self) -> None:
        issue = TimeoutRule().validate(_analysis_result(ExecutionStatus.TIMEOUT))[0]
        assert issue.recommendation == (
            "Retry the AI analysis or investigate execution timeout settings."
        )

    def test_issue_evidence_is_none(self) -> None:
        issue = TimeoutRule().validate(_analysis_result(ExecutionStatus.TIMEOUT))[0]
        assert issue.evidence is None

    def test_issue_correlation_from_response(self) -> None:
        issue = TimeoutRule().validate(
            _analysis_result(ExecutionStatus.TIMEOUT, execution_id="EX-99")
        )[0]
        assert issue.correlation_id == "EX-99"

    def test_issue_created_at_populated(self) -> None:
        issue = TimeoutRule().validate(_analysis_result(ExecutionStatus.TIMEOUT))[0]
        assert isinstance(issue.created_at, datetime)


# ---------------------------------------------------------------------------
# 4. Immutability, determinism, idempotency, purity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleIndependence:
    def test_issue_is_immutable(self) -> None:
        issue = TimeoutRule().validate(_analysis_result(ExecutionStatus.TIMEOUT))[0]
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_does_not_mutate_analysis_result(self) -> None:
        rule = TimeoutRule()
        analysis = _analysis_result(ExecutionStatus.TIMEOUT)
        before = analysis.model_copy(deep=True)
        rule.validate(analysis)
        assert analysis == before

    def test_deterministic_finding_content(self) -> None:
        rule = TimeoutRule()
        analysis = _analysis_result(ExecutionStatus.TIMEOUT)
        first = rule.validate(analysis)[0]
        second = rule.validate(analysis)[0]
        assert _content(first) == _content(second)

    def test_idempotent_no_cumulative_effect(self) -> None:
        rule = TimeoutRule()
        timed_out = _analysis_result(ExecutionStatus.TIMEOUT)
        assert len(rule.validate(timed_out)) == 1
        assert len(rule.validate(timed_out)) == 1
        completed = _analysis_result(ExecutionStatus.COMPLETED)
        assert rule.validate(completed) == []
        assert rule.validate(completed) == []


# ---------------------------------------------------------------------------
# 5. Registry registration (all three transport rules)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_all_three_transport_rules_registered_in_order(self) -> None:
        registry = ValidationRegistry()
        register_transport_rules(registry)
        assert registry.list_rule_ids() == [
            "TRANSPORT-0001",
            "TRANSPORT-0002",
            "TRANSPORT-0003",
        ]

    def test_registered_rule_types(self) -> None:
        registry = ValidationRegistry()
        register_transport_rules(registry)
        rules = registry.get_enabled_rules()
        assert isinstance(rules[0], ResponseExistsRule)
        assert isinstance(rules[1], EmptyResponseRule)
        assert isinstance(rules[2], TimeoutRule)


# ---------------------------------------------------------------------------
# 6. Pipeline & Response Validator integration
# ---------------------------------------------------------------------------


def _validator() -> ResponseValidator:
    registry = ValidationRegistry()
    register_transport_rules(registry)
    pipeline = ValidationPipeline(registry)
    return ResponseValidator(registry, pipeline, ValidationConfiguration())


@pytest.mark.unit
class TestIntegrationPass:
    def test_all_rules_execute_and_pass(self) -> None:
        result = _validator().validate(_analysis_result(ExecutionStatus.COMPLETED))
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0
        assert result.validation_statistics.rules_executed == 3

    def test_pipeline_executes_all_three_rules(self) -> None:
        registry = ValidationRegistry()
        register_transport_rules(registry)
        result = ValidationPipeline(registry).run(_analysis_result(ExecutionStatus.COMPLETED))
        assert result.validation_statistics.rules_executed == 3
        assert result.validation_statistics.rules_passed == 3
        assert result.validation_summary.total_issues == 0


# ---------------------------------------------------------------------------
# 7. Timeout end-to-end — 0001 passes, 0002 passes, 0003 fails
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIntegrationTimeout:
    def test_only_transport_0003_fails(self) -> None:
        result = _validator().validate(_analysis_result(ExecutionStatus.TIMEOUT))
        failing_ids = [issue.rule_id for issue in result.validation_issues]
        assert failing_ids == ["TRANSPORT-0003"]
        assert result.validation_summary.total_issues == 1

    def test_timeout_is_rejected_not_passed(self) -> None:
        result = _validator().validate(_analysis_result(ExecutionStatus.TIMEOUT))
        # CRITICAL finding ⇒ BLOCKED under the frozen verdict model (never PASSED).
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert result.overall_verdict != ValidationVerdict.PASSED

    def test_timeout_counts_one_rule_failed(self) -> None:
        result = _validator().validate(_analysis_result(ExecutionStatus.TIMEOUT))
        stats = result.validation_statistics
        assert stats.rules_executed == 3
        assert stats.rules_passed == 2
        assert stats.rules_failed == 1
