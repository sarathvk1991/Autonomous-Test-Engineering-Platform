"""Unit tests for TRANSPORT-0004 ProviderFailureRule (the final Transport rule).

Covers
------
* Metadata & rule identity — matches the catalog entry exactly.
* Successful execution — a completed execution yields no findings.
* Failed execution — a FAILED execution yields exactly one finding.
* Orthogonality — a TIMEOUT execution does NOT trigger this rule.
* ValidationIssue contents — severity, blocking, recommendation, message, etc.
* Immutability, determinism, idempotency, non-mutation.
* Registry registration — all four Transport rules register, in catalog order.
* Pipeline & Response Validator integration — all four rules execute naturally.
* FAILED end-to-end — TRANSPORT-0001/0002/0003 pass, TRANSPORT-0004 fails.

Design constraints
------------------
* No mocking of rule logic; the rule is exercised directly.
* A real ``AnalysisResult`` is used throughout; the normalized
  ``execution_status`` on its ``LLMResponse`` is the only field that matters.
* Provider-independent: the rule reads ``ExecutionStatus`` only — never a
  provider-specific failure code.

Note on verdict
---------------
The TRANSPORT-0004 issue is ``CRITICAL`` (per the catalog), and the frozen verdict
model maps any ``CRITICAL`` finding to ``BLOCKED`` (not ``FAILED``).  The
provider-failure end-to-end tests therefore assert ``BLOCKED`` — the response is
correctly *rejected* (never ``PASSED``).
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
    ProviderFailureRule,
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
        assert isinstance(ProviderFailureRule(), ValidationRule)

    def test_rule_id(self) -> None:
        assert ProviderFailureRule().rule_id == "TRANSPORT-0004"

    def test_rule_name(self) -> None:
        assert ProviderFailureRule().rule_name == "Provider Failure"

    def test_layer(self) -> None:
        assert ProviderFailureRule().validation_layer == ValidationLayer.TRANSPORT

    def test_rule_version(self) -> None:
        assert ProviderFailureRule().rule_version == "1.0.0"

    def test_enabled_by_default(self) -> None:
        assert ProviderFailureRule().enabled is True

    def test_metadata_is_stable_across_access(self) -> None:
        rule = ProviderFailureRule()
        assert rule.metadata is rule.metadata


# ---------------------------------------------------------------------------
# 2. Successful execution & orthogonality
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSuccessfulExecution:
    def test_completed_execution_yields_no_issues(self) -> None:
        assert ProviderFailureRule().validate(_analysis_result(ExecutionStatus.COMPLETED)) == []

    def test_default_status_passes(self) -> None:
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
        assert ProviderFailureRule().validate(result) == []

    def test_timeout_does_not_trigger_provider_failure(self) -> None:
        # TIMEOUT and FAILED are sibling, disjoint outcomes: ProviderFailureRule
        # fails ONLY on FAILED.  A TIMEOUT is owned by TRANSPORT-0003 and must not
        # trigger this rule — proving the two rules remain orthogonal.
        assert ProviderFailureRule().validate(_analysis_result(ExecutionStatus.TIMEOUT)) == []

    def test_defers_when_llm_response_absent(self) -> None:
        stand_in = SimpleNamespace(llm_response=None, execution_id="EX-1")
        assert ProviderFailureRule().validate(stand_in) == []


# ---------------------------------------------------------------------------
# 3. Failed execution & issue contents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailedExecution:
    def test_failed_yields_one_issue(self) -> None:
        assert len(ProviderFailureRule().validate(_analysis_result(ExecutionStatus.FAILED))) == 1

    def test_issue_severity_is_critical(self) -> None:
        issue = ProviderFailureRule().validate(_analysis_result(ExecutionStatus.FAILED))[0]
        assert issue.severity == ValidationSeverity.CRITICAL

    def test_issue_is_blocking(self) -> None:
        issue = ProviderFailureRule().validate(_analysis_result(ExecutionStatus.FAILED))[0]
        assert issue.blocking is True

    def test_issue_layer_and_category(self) -> None:
        issue = ProviderFailureRule().validate(_analysis_result(ExecutionStatus.FAILED))[0]
        # ``ValidationIssue`` stores enum fields by value (Schema use_enum_values).
        assert issue.validation_layer == ValidationLayer.TRANSPORT.value
        assert issue.category == "transport"

    def test_issue_identity_fields(self) -> None:
        issue = ProviderFailureRule().validate(_analysis_result(ExecutionStatus.FAILED))[0]
        assert issue.rule_id == "TRANSPORT-0004"
        assert issue.rule_version == "1.0.0"
        assert issue.issue_id == "TRANSPORT-0004:provider_failure"
        assert issue.location == "execution"

    def test_issue_message(self) -> None:
        issue = ProviderFailureRule().validate(_analysis_result(ExecutionStatus.FAILED))[0]
        assert issue.message == "The AI execution failed at the provider delivery boundary."

    def test_issue_recommendation(self) -> None:
        issue = ProviderFailureRule().validate(_analysis_result(ExecutionStatus.FAILED))[0]
        assert issue.recommendation == (
            "Retry the AI request or investigate the provider failure before continuing."
        )

    def test_issue_evidence_is_none(self) -> None:
        issue = ProviderFailureRule().validate(_analysis_result(ExecutionStatus.FAILED))[0]
        assert issue.evidence is None

    def test_issue_correlation_from_response(self) -> None:
        issue = ProviderFailureRule().validate(
            _analysis_result(ExecutionStatus.FAILED, execution_id="EX-44")
        )[0]
        assert issue.correlation_id == "EX-44"

    def test_issue_created_at_populated(self) -> None:
        issue = ProviderFailureRule().validate(_analysis_result(ExecutionStatus.FAILED))[0]
        assert isinstance(issue.created_at, datetime)


# ---------------------------------------------------------------------------
# 4. Immutability, determinism, idempotency, purity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleIndependence:
    def test_issue_is_immutable(self) -> None:
        issue = ProviderFailureRule().validate(_analysis_result(ExecutionStatus.FAILED))[0]
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_does_not_mutate_analysis_result(self) -> None:
        rule = ProviderFailureRule()
        analysis = _analysis_result(ExecutionStatus.FAILED)
        before = analysis.model_copy(deep=True)
        rule.validate(analysis)
        assert analysis == before

    def test_deterministic_finding_content(self) -> None:
        rule = ProviderFailureRule()
        analysis = _analysis_result(ExecutionStatus.FAILED)
        first = rule.validate(analysis)[0]
        second = rule.validate(analysis)[0]
        assert _content(first) == _content(second)

    def test_idempotent_no_cumulative_effect(self) -> None:
        rule = ProviderFailureRule()
        failed = _analysis_result(ExecutionStatus.FAILED)
        assert len(rule.validate(failed)) == 1
        assert len(rule.validate(failed)) == 1
        completed = _analysis_result(ExecutionStatus.COMPLETED)
        assert rule.validate(completed) == []
        assert rule.validate(completed) == []


# ---------------------------------------------------------------------------
# 5. Registry registration (all four transport rules, catalog order)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_all_four_transport_rules_registered_in_order(self) -> None:
        registry = ValidationRegistry()
        register_transport_rules(registry)
        assert registry.list_rule_ids() == [
            "TRANSPORT-0001",
            "TRANSPORT-0002",
            "TRANSPORT-0003",
            "TRANSPORT-0004",
        ]

    def test_registered_rule_types(self) -> None:
        registry = ValidationRegistry()
        register_transport_rules(registry)
        rules = registry.get_enabled_rules()
        assert isinstance(rules[0], ResponseExistsRule)
        assert isinstance(rules[1], EmptyResponseRule)
        assert isinstance(rules[2], TimeoutRule)
        assert isinstance(rules[3], ProviderFailureRule)


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
        assert result.validation_statistics.rules_executed == 4

    def test_pipeline_executes_all_four_rules(self) -> None:
        registry = ValidationRegistry()
        register_transport_rules(registry)
        result = ValidationPipeline(registry).run(_analysis_result(ExecutionStatus.COMPLETED))
        assert result.validation_statistics.rules_executed == 4
        assert result.validation_statistics.rules_passed == 4
        assert result.validation_summary.total_issues == 0


# ---------------------------------------------------------------------------
# 7. FAILED end-to-end — 0001/0002/0003 pass, 0004 fails
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIntegrationFailed:
    def test_only_transport_0004_fails(self) -> None:
        result = _validator().validate(_analysis_result(ExecutionStatus.FAILED))
        failing_ids = [issue.rule_id for issue in result.validation_issues]
        assert failing_ids == ["TRANSPORT-0004"]
        assert result.validation_summary.total_issues == 1

    def test_failure_is_rejected_not_passed(self) -> None:
        result = _validator().validate(_analysis_result(ExecutionStatus.FAILED))
        # CRITICAL finding ⇒ BLOCKED under the frozen verdict model (never PASSED).
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert result.overall_verdict != ValidationVerdict.PASSED

    def test_failure_counts_one_rule_failed(self) -> None:
        result = _validator().validate(_analysis_result(ExecutionStatus.FAILED))
        stats = result.validation_statistics
        assert stats.rules_executed == 4
        assert stats.rules_passed == 3
        assert stats.rules_failed == 1
