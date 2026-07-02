"""Unit tests for SYNTAX-0001 ValidStructureRule.

Covers
------
* Metadata & rule identity — matches the catalog entry exactly.
* NORMALIZED outcome — a well-formed response yields no findings.
* MALFORMED outcome — yields exactly one finding.
* ValidationIssue contents — severity, blocking, recommendation, message, etc.
* Reads ONLY the Normalization Outcome — never the structure or the observations.
* Immutability — the issue is frozen; the ValidationInput and ParsedResponse are
  never mutated.
* Determinism & idempotency — repeated calls yield identical finding content.
* Facts, not exceptions — MALFORMED is a finding, never a raise.
* Infrastructure failure path — a missing ParsedResponse raises ValidationRuleError.
* Registry registration, Pipeline execution, Response Validator integration.

Design constraints
------------------
* No mocking of rule logic; the rule is exercised directly.
* Per ADR-0003 the rule receives a ``ValidationInput``.  A real
  ``ResponseNormalizer`` produces the ``NormalizationResult`` (and thus a real
  ``ParsedResponse``) so the outcome under test is genuine, not fabricated.
* A duck-typed spy is used only to prove the rule never touches
  ``normalized_structure`` or the observations.
* No real AI provider calls; inputs are built in-memory.
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
from requirement_intelligence.validation.rules.syntax import (
    ValidStructureRule,
    register_syntax_rules,
)
from requirement_intelligence.validation.validation_exceptions import ValidationRuleError
from requirement_intelligence.validation.validation_rule_metadata import DEFAULT_RULE_VERSION
from shared.enums.base import NormalizationOutcome

_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)

# A well-formed structured document (normalizes to NORMALIZED) and a malformed one.
_NORMALIZED_JSON = '{"doc": {"items": [1, 2]}, "summary": "s"}'
_MALFORMED_TEXT = "not json at all"

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


def _normalization_result(analysis: AnalysisResult) -> Any:
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return normalizer.normalize(analysis.llm_response)


def _input(generated_text: str, execution_id: str = "EX-1") -> ValidationInput:
    """A real ``ValidationInput`` whose Normalization Outcome is genuine."""
    analysis = _analysis_result(generated_text, execution_id)
    return ValidationInput(
        analysis_result=analysis,
        normalization_result=_normalization_result(analysis),
    )


def _content(issue: Any) -> tuple[Any, ...]:
    return tuple(getattr(issue, field) for field in _CONTENT_FIELDS)


# ---------------------------------------------------------------------------
# Spy input — proves the rule reads ONLY the Normalization Outcome
# ---------------------------------------------------------------------------


class _SpyParsedResponse:
    """A ParsedResponse stand-in: the outcome is readable, but touching
    ``normalized_structure`` fails the test."""

    def __init__(self, outcome: NormalizationOutcome) -> None:
        self.normalization_outcome = outcome

    @property
    def normalized_structure(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SYNTAX-0001 must not inspect normalized_structure")


class _SpyNormalizationResult:
    """A NormalizationResult stand-in: touching ``observations`` fails the test."""

    def __init__(self, parsed_response: _SpyParsedResponse) -> None:
        self.parsed_response = parsed_response

    @property
    def observations(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SYNTAX-0001 must not inspect observations")


def _spy_input(outcome: NormalizationOutcome, execution_id: str = "EX-1") -> Any:
    """A duck-typed ValidationInput that raises if structure/observations are read."""
    return SimpleNamespace(
        normalization_result=_SpyNormalizationResult(_SpyParsedResponse(outcome)),
        analysis_result=SimpleNamespace(execution_id=execution_id),
    )


# ---------------------------------------------------------------------------
# 1. Metadata & identity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetadata:
    def test_is_a_validation_rule(self) -> None:
        assert isinstance(ValidStructureRule(), ValidationRule)

    def test_rule_id(self) -> None:
        assert ValidStructureRule().rule_id == "SYNTAX-0001"

    def test_rule_name(self) -> None:
        assert ValidStructureRule().rule_name == "Valid Structure"

    def test_layer(self) -> None:
        assert ValidStructureRule().validation_layer == ValidationLayer.SYNTAX

    def test_rule_version_is_default(self) -> None:
        assert ValidStructureRule().rule_version == DEFAULT_RULE_VERSION

    def test_enabled_by_default(self) -> None:
        assert ValidStructureRule().enabled is True

    def test_metadata_is_stable_across_access(self) -> None:
        rule = ValidStructureRule()
        assert rule.metadata is rule.metadata


# ---------------------------------------------------------------------------
# 2. NORMALIZED outcome — success
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizedOutcome:
    def test_normalized_yields_no_issues(self) -> None:
        assert ValidStructureRule().validate(_input(_NORMALIZED_JSON)) == []

    def test_success_returns_empty_list_type(self) -> None:
        result = ValidStructureRule().validate(_input(_NORMALIZED_JSON))
        assert isinstance(result, list)
        assert len(result) == 0

    def test_normalized_via_spy_yields_no_issues(self) -> None:
        assert ValidStructureRule().validate(_spy_input(NormalizationOutcome.NORMALIZED)) == []


# ---------------------------------------------------------------------------
# 3. MALFORMED outcome & issue contents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMalformedOutcome:
    def test_malformed_yields_one_issue(self) -> None:
        assert len(ValidStructureRule().validate(_input(_MALFORMED_TEXT))) == 1

    def test_issue_severity_is_critical(self) -> None:
        issue = ValidStructureRule().validate(_input(_MALFORMED_TEXT))[0]
        assert issue.severity == ValidationSeverity.CRITICAL

    def test_issue_is_blocking(self) -> None:
        issue = ValidStructureRule().validate(_input(_MALFORMED_TEXT))[0]
        assert issue.blocking is True

    def test_issue_layer_and_category(self) -> None:
        issue = ValidStructureRule().validate(_input(_MALFORMED_TEXT))[0]
        # ``ValidationIssue`` stores enum fields by value (Schema use_enum_values).
        assert issue.validation_layer == ValidationLayer.SYNTAX.value
        assert issue.category == "syntax"

    def test_issue_identity_fields(self) -> None:
        issue = ValidStructureRule().validate(_input(_MALFORMED_TEXT))[0]
        assert issue.rule_id == "SYNTAX-0001"
        assert issue.rule_version == DEFAULT_RULE_VERSION
        assert issue.issue_id == "SYNTAX-0001:normalization_outcome"
        assert issue.location == "normalization_outcome"

    def test_issue_message(self) -> None:
        issue = ValidStructureRule().validate(_input(_MALFORMED_TEXT))[0]
        assert issue.message == (
            "The response could not be normalized into well-formed structured data."
        )

    def test_issue_recommendation(self) -> None:
        issue = ValidStructureRule().validate(_input(_MALFORMED_TEXT))[0]
        assert issue.recommendation == (
            "Regenerate the AI response so it returns well-formed structured data."
        )

    def test_issue_evidence_is_none(self) -> None:
        issue = ValidStructureRule().validate(_input(_MALFORMED_TEXT))[0]
        assert issue.evidence is None

    def test_issue_correlation_from_execution_id(self) -> None:
        issue = ValidStructureRule().validate(_input(_MALFORMED_TEXT, execution_id="EX-55"))[0]
        assert issue.correlation_id == "EX-55"

    def test_issue_created_at_populated(self) -> None:
        issue = ValidStructureRule().validate(_input(_MALFORMED_TEXT))[0]
        assert isinstance(issue.created_at, datetime)

    def test_malformed_via_spy_yields_one_issue(self) -> None:
        assert len(ValidStructureRule().validate(_spy_input(NormalizationOutcome.MALFORMED))) == 1


# ---------------------------------------------------------------------------
# 4. Reads ONLY the Normalization Outcome
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadsOnlyOutcome:
    def test_does_not_inspect_structure_on_malformed(self) -> None:
        # The spy raises if ``normalized_structure`` is accessed; a clean run proves
        # the rule never touched it.
        assert len(ValidStructureRule().validate(_spy_input(NormalizationOutcome.MALFORMED))) == 1

    def test_does_not_inspect_structure_on_normalized(self) -> None:
        assert ValidStructureRule().validate(_spy_input(NormalizationOutcome.NORMALIZED)) == []

    def test_does_not_inspect_observations(self) -> None:
        # The spy raises if ``observations`` is accessed; both paths must stay clean.
        assert len(ValidStructureRule().validate(_spy_input(NormalizationOutcome.MALFORMED))) == 1
        assert ValidStructureRule().validate(_spy_input(NormalizationOutcome.NORMALIZED)) == []


# ---------------------------------------------------------------------------
# 5. Immutability, determinism, idempotency, purity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleIndependence:
    def test_issue_is_immutable(self) -> None:
        issue = ValidStructureRule().validate(_input(_MALFORMED_TEXT))[0]
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_does_not_mutate_validation_input(self) -> None:
        rule = ValidStructureRule()
        validation_input = _input(_MALFORMED_TEXT)
        before = validation_input.model_copy(deep=True)
        rule.validate(validation_input)
        assert validation_input == before

    def test_does_not_mutate_parsed_response(self) -> None:
        rule = ValidStructureRule()
        validation_input = _input(_MALFORMED_TEXT)
        parsed_before = validation_input.normalization_result.parsed_response.model_copy(deep=True)
        rule.validate(validation_input)
        assert validation_input.normalization_result.parsed_response == parsed_before

    def test_deterministic_finding_content(self) -> None:
        rule = ValidStructureRule()
        validation_input = _input(_MALFORMED_TEXT)
        first = rule.validate(validation_input)[0]
        second = rule.validate(validation_input)[0]
        assert _content(first) == _content(second)

    def test_idempotent_no_cumulative_effect(self) -> None:
        rule = ValidStructureRule()
        malformed = _input(_MALFORMED_TEXT)
        assert len(rule.validate(malformed)) == 1
        assert len(rule.validate(malformed)) == 1
        normalized = _input(_NORMALIZED_JSON)
        assert rule.validate(normalized) == []
        assert rule.validate(normalized) == []


# ---------------------------------------------------------------------------
# 6. Facts vs exceptions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFactsNotExceptions:
    def test_malformed_is_a_finding_not_an_exception(self) -> None:
        # A malformed response must never raise — it is a returned ValidationIssue.
        issues = ValidStructureRule().validate(_input(_MALFORMED_TEXT))
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.CRITICAL

    def test_missing_parsed_response_raises_infrastructure_error(self) -> None:
        # A broken normalization handoff (no ParsedResponse) is an infrastructure
        # failure, raised as ValidationRuleError — never a finding.
        analysis = _analysis_result(_NORMALIZED_JSON)
        broken = _normalization_result(analysis).model_copy(update={"parsed_response": None})
        validation_input = ValidationInput(analysis_result=analysis, normalization_result=broken)
        with pytest.raises(ValidationRuleError):
            ValidStructureRule().validate(validation_input)


# ---------------------------------------------------------------------------
# 7. Registry registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_register_syntax_rules_includes_this_rule(self) -> None:
        registry = ValidationRegistry()
        register_syntax_rules(registry)
        assert "SYNTAX-0001" in registry.list_rule_ids()

    def test_rule_can_be_registered_directly(self) -> None:
        registry = ValidationRegistry()
        registry.register(ValidStructureRule())
        rules = registry.get_enabled_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], ValidStructureRule)


# ---------------------------------------------------------------------------
# 8. Pipeline & Response Validator integration (SYNTAX-0001 in isolation)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPipelineExecution:
    def _pipeline(self) -> ValidationPipeline:
        registry = ValidationRegistry()
        registry.register(ValidStructureRule())
        return ValidationPipeline(registry)

    def test_normalized_passes(self) -> None:
        result = self._pipeline().run(_input(_NORMALIZED_JSON))
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0

    def test_malformed_is_blocked(self) -> None:
        result = self._pipeline().run(_input(_MALFORMED_TEXT))
        # CRITICAL finding ⇒ BLOCKED under the frozen verdict model (never PASSED).
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert result.overall_verdict != ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 1

    def test_counts_rule_execution(self) -> None:
        result = self._pipeline().run(_input(_MALFORMED_TEXT))
        assert result.validation_statistics.rules_executed == 1
        assert result.validation_statistics.rules_failed == 1


@pytest.mark.unit
class TestResponseValidatorIntegration:
    def _validator(self) -> ResponseValidator:
        registry = ValidationRegistry()
        registry.register(ValidStructureRule())
        pipeline = ValidationPipeline(registry)
        return ResponseValidator(registry, pipeline, ValidationConfiguration())

    def test_validator_passes_normalized(self) -> None:
        result = self._validator().validate(_input(_NORMALIZED_JSON))
        assert result.overall_verdict == ValidationVerdict.PASSED

    def test_validator_blocks_malformed(self) -> None:
        result = self._validator().validate(_input(_MALFORMED_TEXT))
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert [i.rule_id for i in result.validation_issues] == ["SYNTAX-0001"]
