"""Unit tests for TRANSPORT-0002 EmptyResponseRule.

Covers
------
* Metadata & rule identity — matches the catalog entry exactly.
* Valid response — usable content yields no findings.
* Empty string & whitespace-only — each yields exactly one finding.
* ValidationIssue contents — severity, blocking, recommendation, message, etc.
* Immutability, determinism, idempotency, non-mutation.
* Registry registration — TRANSPORT-0001 and TRANSPORT-0002 both register.
* Pipeline & Response Validator integration — both rules execute naturally.
* Empty-content end-to-end — TRANSPORT-0001 passes, TRANSPORT-0002 fails.

Design constraints
------------------
* No mocking of rule logic; the rule is exercised directly.
* A real ``AnalysisResult`` is used throughout — ``generated_text=""`` is a valid
  (empty) string, so the empty/whitespace cases need no stand-in.  A
  ``SimpleNamespace`` is used only for the "no llm_response" defer case.

Note on verdict
---------------
The TRANSPORT-0002 issue is ``CRITICAL`` (per the catalog), and the frozen
verdict model maps any ``CRITICAL`` finding to ``BLOCKED`` (not ``FAILED``).  The
empty-content end-to-end tests therefore assert ``BLOCKED`` — the response is
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
    ValidationConfiguration,
    ValidationInput,
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


def _analysis_result(generated_text: str, execution_id: str = "EX-1") -> AnalysisResult:
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
        llm_response=LLMResponse(provider="gemini", model="model", generated_text=generated_text),
    )


def _validation_input_for(analysis: AnalysisResult) -> ValidationInput:
    """Bind *analysis* to a real ``NormalizationResult`` (ADR-0003 handoff)."""
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return ValidationInput(
        analysis_result=analysis,
        normalization_result=normalizer.normalize(analysis.llm_response),
    )


def _input(generated_text: str, execution_id: str = "EX-1") -> ValidationInput:
    return _validation_input_for(_analysis_result(generated_text, execution_id))


def _missing_response(execution_id: str = "EX-1") -> Any:
    """A duck-typed ``ValidationInput`` whose analysed response has no LLM response."""
    return SimpleNamespace(
        analysis_result=SimpleNamespace(llm_response=None, execution_id=execution_id)
    )


def _content(issue: Any) -> tuple[Any, ...]:
    return tuple(getattr(issue, field) for field in _CONTENT_FIELDS)


# ---------------------------------------------------------------------------
# 1. Metadata & identity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetadata:
    def test_is_a_validation_rule(self) -> None:
        assert isinstance(EmptyResponseRule(), ValidationRule)

    def test_rule_id(self) -> None:
        assert EmptyResponseRule().rule_id == "TRANSPORT-0002"

    def test_rule_name(self) -> None:
        assert EmptyResponseRule().rule_name == "Empty Response"

    def test_layer(self) -> None:
        assert EmptyResponseRule().validation_layer == ValidationLayer.TRANSPORT

    def test_rule_version(self) -> None:
        assert EmptyResponseRule().rule_version == "1.0.0"

    def test_enabled_by_default(self) -> None:
        assert EmptyResponseRule().enabled is True

    def test_metadata_is_stable_across_access(self) -> None:
        rule = EmptyResponseRule()
        assert rule.metadata is rule.metadata


# ---------------------------------------------------------------------------
# 2. Valid response
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidResponse:
    def test_usable_content_yields_no_issues(self) -> None:
        assert EmptyResponseRule().validate(_input("a verdict")) == []

    def test_content_with_surrounding_whitespace_passes(self) -> None:
        assert EmptyResponseRule().validate(_input("  real content  ")) == []

    def test_defers_when_llm_response_absent(self) -> None:
        # Existence is TRANSPORT-0001's concern; this rule defers (no findings).
        assert EmptyResponseRule().validate(_missing_response()) == []


# ---------------------------------------------------------------------------
# 3. Empty & whitespace-only content
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEmptyContent:
    def test_empty_string_yields_one_issue(self) -> None:
        assert len(EmptyResponseRule().validate(_input(""))) == 1

    def test_whitespace_only_yields_one_issue(self) -> None:
        assert len(EmptyResponseRule().validate(_input("   \n\t "))) == 1

    def test_issue_severity_is_critical(self) -> None:
        issue = EmptyResponseRule().validate(_input(""))[0]
        assert issue.severity == ValidationSeverity.CRITICAL

    def test_issue_is_blocking(self) -> None:
        issue = EmptyResponseRule().validate(_input(""))[0]
        assert issue.blocking is True

    def test_issue_layer_and_category(self) -> None:
        issue = EmptyResponseRule().validate(_input(""))[0]
        # ``ValidationIssue`` stores enum fields by value (Schema use_enum_values).
        assert issue.validation_layer == ValidationLayer.TRANSPORT.value
        assert issue.category == "transport"

    def test_issue_identity_fields(self) -> None:
        issue = EmptyResponseRule().validate(_input(""))[0]
        assert issue.rule_id == "TRANSPORT-0002"
        assert issue.rule_version == "1.0.0"
        assert issue.issue_id == "TRANSPORT-0002:generated_text"
        assert issue.location == "generated_text"

    def test_issue_message(self) -> None:
        issue = EmptyResponseRule().validate(_input(""))[0]
        assert issue.message == "The LLM response contains no generated content."

    def test_issue_recommendation(self) -> None:
        issue = EmptyResponseRule().validate(_input(""))[0]
        assert issue.recommendation == "Regenerate the AI response before continuing."

    def test_issue_evidence_is_none(self) -> None:
        issue = EmptyResponseRule().validate(_input(""))[0]
        assert issue.evidence is None

    def test_issue_correlation_from_response(self) -> None:
        issue = EmptyResponseRule().validate(_input("", "EX-88"))[0]
        assert issue.correlation_id == "EX-88"

    def test_issue_created_at_populated(self) -> None:
        issue = EmptyResponseRule().validate(_input(""))[0]
        assert isinstance(issue.created_at, datetime)


# ---------------------------------------------------------------------------
# 4. Immutability, determinism, idempotency, purity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleIndependence:
    def test_issue_is_immutable(self) -> None:
        issue = EmptyResponseRule().validate(_input(""))[0]
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_does_not_mutate_validation_input(self) -> None:
        rule = EmptyResponseRule()
        validation_input = _input("")
        before = validation_input.model_copy(deep=True)
        rule.validate(validation_input)
        assert validation_input == before

    def test_deterministic_finding_content(self) -> None:
        rule = EmptyResponseRule()
        validation_input = _input("")
        first = rule.validate(validation_input)[0]
        second = rule.validate(validation_input)[0]
        assert _content(first) == _content(second)

    def test_idempotent_no_cumulative_effect(self) -> None:
        rule = EmptyResponseRule()
        empty = _input("")
        assert len(rule.validate(empty)) == 1
        assert len(rule.validate(empty)) == 1
        full = _input("content")
        assert rule.validate(full) == []
        assert rule.validate(full) == []


# ---------------------------------------------------------------------------
# 5. Registry registration (both transport rules)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_both_transport_rules_registered_in_order(self) -> None:
        # ``register_transport_rules`` registers the whole Transport set; assert
        # membership and the relative order of these two (not the exact set, which
        # grows as new Transport rules are added).
        registry = ValidationRegistry()
        register_transport_rules(registry)
        ids = registry.list_rule_ids()
        assert "TRANSPORT-0001" in ids
        assert "TRANSPORT-0002" in ids
        assert ids.index("TRANSPORT-0001") < ids.index("TRANSPORT-0002")

    def test_registered_rule_types(self) -> None:
        registry = ValidationRegistry()
        register_transport_rules(registry)
        rules = registry.get_enabled_rules()
        assert isinstance(rules[0], ResponseExistsRule)
        assert isinstance(rules[1], EmptyResponseRule)


# ---------------------------------------------------------------------------
# 6. Pipeline & Response Validator integration
# ---------------------------------------------------------------------------


def _validator() -> ResponseValidator:
    # Isolate the TRANSPORT-0001 + TRANSPORT-0002 interaction so these counts stay
    # stable as the Transport rule set grows; the full set is covered by the
    # newest rule's suite.
    registry = ValidationRegistry()
    registry.register(ResponseExistsRule())
    registry.register(EmptyResponseRule())
    pipeline = ValidationPipeline(registry)
    return ResponseValidator(registry, pipeline, ValidationConfiguration())


@pytest.mark.unit
class TestIntegrationPass:
    def test_both_rules_execute_and_pass(self) -> None:
        result = _validator().validate(_input("usable content"))
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0
        assert result.validation_statistics.rules_executed == 2

    def test_pipeline_executes_both_rules(self) -> None:
        registry = ValidationRegistry()
        registry.register(ResponseExistsRule())
        registry.register(EmptyResponseRule())
        result = ValidationPipeline(registry).run(_input("content"))
        assert result.validation_statistics.rules_executed == 2
        assert result.validation_statistics.rules_passed == 2
        assert result.validation_summary.total_issues == 0


# ---------------------------------------------------------------------------
# 7. Empty-content end-to-end — 0001 passes, 0002 fails
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIntegrationEmptyContent:
    def test_transport_0001_passes_and_transport_0002_fails(self) -> None:
        result = _validator().validate(_input(""))
        failing_ids = [issue.rule_id for issue in result.validation_issues]
        # TRANSPORT-0001 contributes no issue (response exists); only 0002 fails.
        assert failing_ids == ["TRANSPORT-0002"]
        assert result.validation_summary.total_issues == 1

    def test_empty_content_is_rejected_not_passed(self) -> None:
        result = _validator().validate(_input(""))
        # CRITICAL finding ⇒ BLOCKED under the frozen verdict model (never PASSED).
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert result.overall_verdict != ValidationVerdict.PASSED

    def test_empty_content_counts_one_rule_failed(self) -> None:
        result = _validator().validate(_input(""))
        stats = result.validation_statistics
        assert stats.rules_executed == 2
        assert stats.rules_passed == 1
        assert stats.rules_failed == 1
