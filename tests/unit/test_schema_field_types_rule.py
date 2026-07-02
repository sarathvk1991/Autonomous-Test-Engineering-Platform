"""Unit tests for SCHEMA-0002 FieldTypesRule.

Covers metadata/identity, happy path, wrong-type findings (string and array), the
per-occurrence (one-issue-per-wrong-field) behaviour, the existence boundary (an
absent field is *not* this rule's concern), read-only ownership (spy-proven), input
immutability, determinism/idempotency, facts-vs-exceptions, deferral on an absent
structure, and registration / pipeline / validator integration.

Design constraints
------------------
* No mocking of rule logic; the rule is exercised directly.
* Per ADR-0003 the rule receives a ``ValidationInput``; per the Rule Catalog §9.3 it
  owns the **type** of each governed field that is present (``summary`` → string; the
  five requirement/risk/recommendation collections → array).
* A real ``ResponseNormalizer`` produces the ``NormalizationResult`` (and thus a real
  ``ParsedResponse``) so the normalized structure under test is genuine.
* A duck-typed spy proves the rule never reads the outcome, observations, generated
  text, provider, source reference, or metadata.
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
from requirement_intelligence.validation.rules.schema import (
    FieldTypesRule,
    register_schema_rules,
)
from requirement_intelligence.validation.validation_exceptions import ValidationRuleError
from requirement_intelligence.validation.validation_rule_metadata import DEFAULT_RULE_VERSION

_TS = datetime(2026, 7, 2, 12, 0, 0, tzinfo=UTC)

# Every governed field present with the correct type.
_ALL_CORRECT = (
    '{"summary": "s", "functional_requirements": [], "security_requirements": [], '
    '"quality_requirements": [], "risks": [], "recommendations": []}'
)
# summary present but an array (wrong type); risks present but a string (wrong type).
_SUMMARY_WRONG = '{"summary": []}'
_RISKS_WRONG = '{"risks": "oops"}'
_TWO_WRONG = '{"summary": [], "risks": "oops"}'
# An empty object: nothing present, so nothing to type-check (existence is elsewhere).
_EMPTY = "{}"
_MALFORMED = "not json at all"

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


def _response(text: str, *, provider: str = "gemini") -> LLMResponse:
    return LLMResponse(provider=provider, model="model", generated_text=text)


def _analysis_result(execution_id: str = "EX-1") -> AnalysisResult:
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
        llm_response=_response(text="{}"),
    )


def _normalization_result(analysis: AnalysisResult, text: str) -> Any:
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return normalizer.normalize(_response(text))


def _input(text: str, *, execution_id: str = "EX-1") -> ValidationInput:
    """A real ``ValidationInput`` whose normalized structure comes from *text*."""
    analysis = _analysis_result(execution_id)
    return ValidationInput(
        analysis_result=analysis,
        normalization_result=_normalization_result(analysis, text),
    )


def _content(issue: Any) -> tuple[Any, ...]:
    return tuple(getattr(issue, field) for field in _CONTENT_FIELDS)


# ---------------------------------------------------------------------------
# Spy input — proves the rule reads ONLY the normalized structure
# ---------------------------------------------------------------------------


class _SpyParsedResponse:
    """A ParsedResponse stand-in: normalized_structure is readable; the outcome,
    source reference, and metadata fail the test if read."""

    def __init__(self, structure: dict[str, Any] | None) -> None:
        self._structure = structure

    @property
    def normalized_structure(self) -> dict[str, Any] | None:
        return self._structure

    @property
    def normalization_outcome(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SCHEMA-0002 must not inspect the normalization outcome")

    @property
    def source_reference(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SCHEMA-0002 must not inspect source_reference")

    @property
    def metadata(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SCHEMA-0002 must not inspect ParsedResponse metadata")


class _SpyNormalizationResult:
    """A NormalizationResult stand-in: parsed_response is readable; observations fail
    the test if read."""

    def __init__(self, parsed_response: _SpyParsedResponse) -> None:
        self._parsed_response = parsed_response

    @property
    def parsed_response(self) -> _SpyParsedResponse:
        return self._parsed_response

    @property
    def observations(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SCHEMA-0002 must not inspect observations")


class _SpyAnalysisResult:
    """An AnalysisResult stand-in: execution_id is readable; llm_response
    (generated_text / provider) fails the test if read."""

    def __init__(self, execution_id: str = "EX-1") -> None:
        self.execution_id = execution_id

    @property
    def llm_response(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SCHEMA-0002 must not inspect llm_response/generated_text/provider")


def _spy_input(structure: dict[str, Any] | None, execution_id: str = "EX-1") -> Any:
    return SimpleNamespace(
        normalization_result=_SpyNormalizationResult(_SpyParsedResponse(structure)),
        analysis_result=_SpyAnalysisResult(execution_id),
    )


# ---------------------------------------------------------------------------
# 1. Metadata & identity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetadata:
    def test_is_a_validation_rule(self) -> None:
        assert isinstance(FieldTypesRule(), ValidationRule)

    def test_rule_id(self) -> None:
        assert FieldTypesRule().rule_id == "SCHEMA-0002"

    def test_rule_name(self) -> None:
        assert FieldTypesRule().rule_name == "Field Types"

    def test_layer(self) -> None:
        assert FieldTypesRule().validation_layer == ValidationLayer.SCHEMA

    def test_rule_version_is_default(self) -> None:
        assert FieldTypesRule().rule_version == DEFAULT_RULE_VERSION

    def test_enabled_by_default(self) -> None:
        assert FieldTypesRule().enabled is True

    def test_metadata_is_stable_across_access(self) -> None:
        rule = FieldTypesRule()
        assert rule.metadata is rule.metadata

    def test_severity_and_blocking_from_catalog(self) -> None:
        # Catalog §14: a schema shape defect is ERROR (→ FAILED), not CRITICAL/BLOCKED,
        # so the finding is non-blocking (§15).
        issue = FieldTypesRule().validate(_input(_SUMMARY_WRONG))[0]
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.blocking is False


# ---------------------------------------------------------------------------
# 2. Happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHappyPath:
    def test_all_correct_types_yield_no_issues(self) -> None:
        assert FieldTypesRule().validate(_input(_ALL_CORRECT)) == []

    def test_success_returns_empty_list_type(self) -> None:
        result = FieldTypesRule().validate(_input(_ALL_CORRECT))
        assert isinstance(result, list)
        assert len(result) == 0

    def test_correct_types_via_spy_yield_no_issues(self) -> None:
        structure = {"summary": "s", "risks": [], "recommendations": ["a"]}
        assert FieldTypesRule().validate(_spy_input(structure)) == []

    def test_absent_fields_are_not_this_rules_concern(self) -> None:
        # An empty object has no governed field present, so there is nothing to
        # type-check; existence is owned by SCHEMA-0001 / SCHEMA-0004.
        assert FieldTypesRule().validate(_input(_EMPTY)) == []


# ---------------------------------------------------------------------------
# 3. Wrong type & issue contents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWrongType:
    def test_wrong_string_yields_one_issue(self) -> None:
        # summary present as an array where a string is expected.
        assert len(FieldTypesRule().validate(_input(_SUMMARY_WRONG))) == 1

    def test_wrong_array_yields_one_issue(self) -> None:
        # risks present as a string where an array is expected.
        assert len(FieldTypesRule().validate(_input(_RISKS_WRONG))) == 1

    def test_issue_identity_fields_for_wrong_string(self) -> None:
        issue = FieldTypesRule().validate(_input(_SUMMARY_WRONG))[0]
        assert issue.rule_id == "SCHEMA-0002"
        assert issue.rule_version == DEFAULT_RULE_VERSION
        assert issue.issue_id == "SCHEMA-0002:summary"
        assert issue.location == "summary"

    def test_issue_layer_and_category(self) -> None:
        issue = FieldTypesRule().validate(_input(_SUMMARY_WRONG))[0]
        assert issue.validation_layer == ValidationLayer.SCHEMA.value
        assert issue.category == "schema"

    def test_issue_message_and_recommendation_for_wrong_string(self) -> None:
        issue = FieldTypesRule().validate(_input(_SUMMARY_WRONG))[0]
        assert issue.message == (
            "The field 'summary' must be of type string, but a array was found."
        )
        assert issue.recommendation == "Provide the 'summary' field as a string."

    def test_issue_message_for_wrong_array(self) -> None:
        issue = FieldTypesRule().validate(_input(_RISKS_WRONG))[0]
        assert issue.message == ("The field 'risks' must be of type array, but a string was found.")
        assert issue.recommendation == "Provide the 'risks' field as a array."

    def test_issue_evidence_is_none(self) -> None:
        issue = FieldTypesRule().validate(_input(_SUMMARY_WRONG))[0]
        assert issue.evidence is None

    def test_issue_correlation_from_execution_id(self) -> None:
        issue = FieldTypesRule().validate(_input(_SUMMARY_WRONG, execution_id="EX-9"))[0]
        assert issue.correlation_id == "EX-9"

    def test_issue_created_at_populated(self) -> None:
        issue = FieldTypesRule().validate(_input(_SUMMARY_WRONG))[0]
        assert isinstance(issue.created_at, datetime)

    def test_null_valued_field_is_a_type_finding(self) -> None:
        # A present key whose value is null is present (existence satisfied) but of the
        # wrong type — a Schema type finding, described as 'null'.
        issue = FieldTypesRule().validate(_spy_input({"summary": None}))[0]
        assert issue.location == "summary"
        assert issue.message == (
            "The field 'summary' must be of type string, but a null was found."
        )

    def test_wrong_type_via_spy_yields_one_issue(self) -> None:
        assert len(FieldTypesRule().validate(_spy_input({"risks": 5}))) == 1


# ---------------------------------------------------------------------------
# 4. Per-occurrence behaviour (one issue per wrong field, no aggregation)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPerOccurrence:
    """One ``ValidationIssue`` per wrong-typed field (Implementation Contract §5 — per
    occurrence, not aggregated)."""

    def test_two_wrong_fields_yield_two_issues(self) -> None:
        issues = FieldTypesRule().validate(_input(_TWO_WRONG))
        assert len(issues) == 2
        assert {i.location for i in issues} == {"summary", "risks"}

    def test_only_wrong_fields_reported(self) -> None:
        # summary correct (string), risks wrong (string where array expected).
        structure = {"summary": "s", "risks": "oops"}
        issues = FieldTypesRule().validate(_spy_input(structure))
        assert [i.location for i in issues] == ["risks"]

    def test_one_issue_per_field_not_aggregated(self) -> None:
        # Every governed collection field present with the wrong type → one issue each.
        structure = {
            "functional_requirements": "x",
            "security_requirements": "x",
            "quality_requirements": "x",
            "risks": "x",
            "recommendations": "x",
        }
        issues = FieldTypesRule().validate(_spy_input(structure))
        assert len(issues) == 5


# ---------------------------------------------------------------------------
# 5. Reads only the normalized structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadsOnlyStructure:
    def test_does_not_inspect_forbidden_fields_on_pass(self) -> None:
        assert FieldTypesRule().validate(_spy_input({"summary": "s"})) == []

    def test_does_not_inspect_forbidden_fields_on_finding(self) -> None:
        assert len(FieldTypesRule().validate(_spy_input({"summary": []}))) == 1

    def test_does_not_inspect_forbidden_fields_when_nothing_present(self) -> None:
        assert FieldTypesRule().validate(_spy_input({})) == []


# ---------------------------------------------------------------------------
# 6. Immutability, determinism, idempotency
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleIndependence:
    def test_issue_is_immutable(self) -> None:
        issue = FieldTypesRule().validate(_input(_SUMMARY_WRONG))[0]
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_does_not_mutate_validation_input(self) -> None:
        rule = FieldTypesRule()
        validation_input = _input(_TWO_WRONG)
        before = validation_input.model_copy(deep=True)
        rule.validate(validation_input)
        assert validation_input == before

    def test_does_not_mutate_parsed_response_or_structure(self) -> None:
        rule = FieldTypesRule()
        validation_input = _input(_TWO_WRONG)
        parsed = validation_input.normalization_result.parsed_response
        parsed_before = parsed.model_copy(deep=True)
        structure_before = dict(parsed.normalized_structure)
        rule.validate(validation_input)
        assert parsed == parsed_before
        assert parsed.normalized_structure == structure_before

    def test_deterministic_finding_content(self) -> None:
        rule = FieldTypesRule()
        validation_input = _input(_SUMMARY_WRONG)
        first = rule.validate(validation_input)[0]
        second = rule.validate(validation_input)[0]
        assert _content(first) == _content(second)

    def test_idempotent_no_cumulative_effect(self) -> None:
        rule = FieldTypesRule()
        wrong = _input(_TWO_WRONG)
        assert len(rule.validate(wrong)) == 2
        assert len(rule.validate(wrong)) == 2
        correct = _input(_ALL_CORRECT)
        assert rule.validate(correct) == []
        assert rule.validate(correct) == []


# ---------------------------------------------------------------------------
# 7. Facts vs exceptions & deferral
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFactsNotExceptions:
    def test_wrong_type_is_a_finding_not_an_exception(self) -> None:
        issues = FieldTypesRule().validate(_input(_SUMMARY_WRONG))
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.ERROR

    def test_defers_on_absent_structure(self) -> None:
        # MALFORMED response → no normalized structure → defer (Syntax owns
        # well-formedness). Never re-report; never raise.
        assert FieldTypesRule().validate(_input(_MALFORMED)) == []

    def test_missing_parsed_response_raises_infrastructure_error(self) -> None:
        analysis = _analysis_result()
        broken = _normalization_result(analysis, _ALL_CORRECT).model_copy(
            update={"parsed_response": None}
        )
        validation_input = ValidationInput(analysis_result=analysis, normalization_result=broken)
        with pytest.raises(ValidationRuleError):
            FieldTypesRule().validate(validation_input)


# ---------------------------------------------------------------------------
# 8. Registration, pipeline, validator integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_register_schema_rules_includes_this_rule(self) -> None:
        registry = ValidationRegistry()
        register_schema_rules(registry)
        assert "SCHEMA-0002" in registry.list_rule_ids()

    def test_rule_can_be_registered_directly(self) -> None:
        registry = ValidationRegistry()
        registry.register(FieldTypesRule())
        rules = registry.get_enabled_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], FieldTypesRule)


@pytest.mark.unit
class TestPipelineAndValidator:
    def _pipeline(self) -> ValidationPipeline:
        registry = ValidationRegistry()
        registry.register(FieldTypesRule())
        return ValidationPipeline(registry)

    def test_correct_types_pass(self) -> None:
        result = self._pipeline().run(_input(_ALL_CORRECT))
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0

    def test_wrong_type_fails(self) -> None:
        result = self._pipeline().run(_input(_TWO_WRONG))
        # ERROR findings ⇒ FAILED under the frozen verdict model (not BLOCKED).
        assert result.overall_verdict == ValidationVerdict.FAILED
        assert result.validation_summary.total_issues == 2

    def test_validator_fails_on_wrong_type(self) -> None:
        registry = ValidationRegistry()
        registry.register(FieldTypesRule())
        validator = ResponseValidator(
            registry, ValidationPipeline(registry), ValidationConfiguration()
        )
        result = validator.validate(_input(_SUMMARY_WRONG))
        assert result.overall_verdict == ValidationVerdict.FAILED
        assert [i.rule_id for i in result.validation_issues] == ["SCHEMA-0002"]
