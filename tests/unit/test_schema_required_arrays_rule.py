"""Unit tests for SCHEMA-0004 RequiredArraysRule.

Covers metadata/identity, happy path, missing-collection findings, the per-occurrence
(one-issue-per-missing-collection) behaviour, read-only ownership (spy-proven), input
immutability, determinism/idempotency, facts-vs-exceptions, deferral on an absent
structure, and registration / pipeline / validator integration.

Design constraints
------------------
* No mocking of rule logic; the rule is exercised directly.
* Per ADR-0003 the rule receives a ``ValidationInput``; per ADR-0004 it owns
  existence of the required **collections** (``functional_requirements``,
  ``security_requirements``, ``quality_requirements``, ``risks``, ``recommendations``).
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
    RequiredArraysRule,
    register_schema_rules,
)
from requirement_intelligence.validation.validation_exceptions import ValidationRuleError
from requirement_intelligence.validation.validation_rule_metadata import DEFAULT_RULE_VERSION

_TS = datetime(2026, 7, 2, 12, 0, 0, tzinfo=UTC)

# The governed schema declares five required collections (ADR-0004).
_ALL_COLLECTIONS = (
    '{"functional_requirements": [], "security_requirements": [], '
    '"quality_requirements": [], "risks": [], "recommendations": []}'
)
# Present but missing "risks".
_MISSING_RISKS = (
    '{"functional_requirements": [], "security_requirements": [], '
    '"quality_requirements": [], "recommendations": []}'
)
# Only summary present → all five collections missing.
_ONLY_SUMMARY = '{"summary": "s"}'
_MALFORMED = "not json at all"

_ALL_COLLECTION_NAMES = (
    "functional_requirements",
    "security_requirements",
    "quality_requirements",
    "risks",
    "recommendations",
)

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
        raise AssertionError("SCHEMA-0004 must not inspect the normalization outcome")

    @property
    def source_reference(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SCHEMA-0004 must not inspect source_reference")

    @property
    def metadata(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SCHEMA-0004 must not inspect ParsedResponse metadata")


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
        raise AssertionError("SCHEMA-0004 must not inspect observations")


class _SpyAnalysisResult:
    """An AnalysisResult stand-in: execution_id is readable; llm_response
    (generated_text / provider) fails the test if read."""

    def __init__(self, execution_id: str = "EX-1") -> None:
        self.execution_id = execution_id

    @property
    def llm_response(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SCHEMA-0004 must not inspect llm_response/generated_text/provider")


def _spy_input(structure: dict[str, Any] | None, execution_id: str = "EX-1") -> Any:
    return SimpleNamespace(
        normalization_result=_SpyNormalizationResult(_SpyParsedResponse(structure)),
        analysis_result=_SpyAnalysisResult(execution_id),
    )


def _all_present_structure() -> dict[str, Any]:
    return {name: [] for name in _ALL_COLLECTION_NAMES}


# ---------------------------------------------------------------------------
# 1. Metadata & identity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetadata:
    def test_is_a_validation_rule(self) -> None:
        assert isinstance(RequiredArraysRule(), ValidationRule)

    def test_rule_id(self) -> None:
        assert RequiredArraysRule().rule_id == "SCHEMA-0004"

    def test_rule_name(self) -> None:
        assert RequiredArraysRule().rule_name == "Required Arrays"

    def test_layer(self) -> None:
        assert RequiredArraysRule().validation_layer == ValidationLayer.SCHEMA

    def test_rule_version_is_default(self) -> None:
        assert RequiredArraysRule().rule_version == DEFAULT_RULE_VERSION

    def test_enabled_by_default(self) -> None:
        assert RequiredArraysRule().enabled is True

    def test_metadata_is_stable_across_access(self) -> None:
        rule = RequiredArraysRule()
        assert rule.metadata is rule.metadata

    def test_severity_and_blocking_from_catalog(self) -> None:
        # Catalog §14: a missing required collection is ERROR (→ FAILED), not
        # CRITICAL/BLOCKED, so the finding is non-blocking (§15).
        issue = RequiredArraysRule().validate(_input(_MISSING_RISKS))[0]
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.blocking is False


# ---------------------------------------------------------------------------
# 2. Happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHappyPath:
    def test_all_collections_present_yields_no_issues(self) -> None:
        assert RequiredArraysRule().validate(_input(_ALL_COLLECTIONS)) == []

    def test_success_returns_empty_list_type(self) -> None:
        result = RequiredArraysRule().validate(_input(_ALL_COLLECTIONS))
        assert isinstance(result, list)
        assert len(result) == 0

    def test_present_via_spy_yields_no_issues(self) -> None:
        assert RequiredArraysRule().validate(_spy_input(_all_present_structure())) == []

    def test_presence_only_extra_keys_ignored(self) -> None:
        # Extra keys and a present-but-non-list value do not matter to this rule —
        # existence only; the type of a present collection is SCHEMA-0002's concern.
        structure = _all_present_structure()
        structure["risks"] = "not-a-list"  # present ⇒ existence satisfied
        structure["unexpected"] = 1
        assert RequiredArraysRule().validate(_spy_input(structure)) == []


# ---------------------------------------------------------------------------
# 3. Missing collection & issue contents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMissingCollection:
    def test_missing_collection_yields_one_issue(self) -> None:
        assert len(RequiredArraysRule().validate(_input(_MISSING_RISKS))) == 1

    def test_issue_identity_fields(self) -> None:
        issue = RequiredArraysRule().validate(_input(_MISSING_RISKS))[0]
        assert issue.rule_id == "SCHEMA-0004"
        assert issue.rule_version == DEFAULT_RULE_VERSION
        assert issue.issue_id == "SCHEMA-0004:risks"
        assert issue.location == "risks"

    def test_issue_layer_and_category(self) -> None:
        issue = RequiredArraysRule().validate(_input(_MISSING_RISKS))[0]
        assert issue.validation_layer == ValidationLayer.SCHEMA.value
        assert issue.category == "schema"

    def test_issue_message_and_recommendation(self) -> None:
        issue = RequiredArraysRule().validate(_input(_MISSING_RISKS))[0]
        assert issue.message == "The required collection 'risks' is missing from the response."
        assert issue.recommendation == "Include the required 'risks' collection in the response."

    def test_issue_evidence_is_none(self) -> None:
        issue = RequiredArraysRule().validate(_input(_MISSING_RISKS))[0]
        assert issue.evidence is None

    def test_issue_correlation_from_execution_id(self) -> None:
        issue = RequiredArraysRule().validate(_input(_MISSING_RISKS, execution_id="EX-9"))[0]
        assert issue.correlation_id == "EX-9"

    def test_issue_created_at_populated(self) -> None:
        issue = RequiredArraysRule().validate(_input(_MISSING_RISKS))[0]
        assert isinstance(issue.created_at, datetime)

    @pytest.mark.parametrize("missing", _ALL_COLLECTION_NAMES)
    def test_each_collection_missing_individually(self, missing: str) -> None:
        structure = _all_present_structure()
        del structure[missing]
        issues = RequiredArraysRule().validate(_spy_input(structure))
        assert len(issues) == 1
        assert issues[0].location == missing


# ---------------------------------------------------------------------------
# 4. Per-occurrence behaviour (one issue per missing collection, no aggregation)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPerOccurrence:
    def test_all_missing_yields_one_issue_each(self) -> None:
        issues = RequiredArraysRule().validate(_input(_ONLY_SUMMARY))
        assert len(issues) == 5
        assert {i.location for i in issues} == set(_ALL_COLLECTION_NAMES)

    def test_only_missing_collections_reported(self) -> None:
        # Two present, three missing.
        structure = {"functional_requirements": [], "risks": []}
        issues = RequiredArraysRule().validate(_spy_input(structure))
        assert {i.location for i in issues} == {
            "security_requirements",
            "quality_requirements",
            "recommendations",
        }

    def test_issues_in_governed_order(self) -> None:
        issues = RequiredArraysRule().validate(_input(_ONLY_SUMMARY))
        assert [i.location for i in issues] == list(_ALL_COLLECTION_NAMES)


# ---------------------------------------------------------------------------
# 5. Reads only the normalized structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadsOnlyStructure:
    def test_does_not_inspect_forbidden_fields_on_pass(self) -> None:
        assert RequiredArraysRule().validate(_spy_input(_all_present_structure())) == []

    def test_does_not_inspect_forbidden_fields_on_finding(self) -> None:
        assert len(RequiredArraysRule().validate(_spy_input({}))) == 5


# ---------------------------------------------------------------------------
# 6. Immutability, determinism, idempotency
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleIndependence:
    def test_issue_is_immutable(self) -> None:
        issue = RequiredArraysRule().validate(_input(_MISSING_RISKS))[0]
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_does_not_mutate_validation_input(self) -> None:
        rule = RequiredArraysRule()
        validation_input = _input(_MISSING_RISKS)
        before = validation_input.model_copy(deep=True)
        rule.validate(validation_input)
        assert validation_input == before

    def test_does_not_mutate_parsed_response_or_structure(self) -> None:
        rule = RequiredArraysRule()
        validation_input = _input(_MISSING_RISKS)
        parsed = validation_input.normalization_result.parsed_response
        parsed_before = parsed.model_copy(deep=True)
        structure_before = dict(parsed.normalized_structure)
        rule.validate(validation_input)
        assert parsed == parsed_before
        assert parsed.normalized_structure == structure_before

    def test_deterministic_finding_content(self) -> None:
        rule = RequiredArraysRule()
        validation_input = _input(_MISSING_RISKS)
        first = rule.validate(validation_input)[0]
        second = rule.validate(validation_input)[0]
        assert _content(first) == _content(second)

    def test_idempotent_no_cumulative_effect(self) -> None:
        rule = RequiredArraysRule()
        missing = _input(_MISSING_RISKS)
        assert len(rule.validate(missing)) == 1
        assert len(rule.validate(missing)) == 1
        present = _input(_ALL_COLLECTIONS)
        assert rule.validate(present) == []
        assert rule.validate(present) == []


# ---------------------------------------------------------------------------
# 7. Facts vs exceptions & deferral
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFactsNotExceptions:
    def test_missing_collection_is_a_finding_not_an_exception(self) -> None:
        issues = RequiredArraysRule().validate(_input(_MISSING_RISKS))
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.ERROR

    def test_defers_on_absent_structure(self) -> None:
        # MALFORMED response → no normalized structure → defer (Syntax owns
        # well-formedness). Never re-report; never raise.
        assert RequiredArraysRule().validate(_input(_MALFORMED)) == []

    def test_missing_parsed_response_raises_infrastructure_error(self) -> None:
        analysis = _analysis_result()
        broken = _normalization_result(analysis, _ALL_COLLECTIONS).model_copy(
            update={"parsed_response": None}
        )
        validation_input = ValidationInput(analysis_result=analysis, normalization_result=broken)
        with pytest.raises(ValidationRuleError):
            RequiredArraysRule().validate(validation_input)


# ---------------------------------------------------------------------------
# 8. Registration, pipeline, validator integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_register_schema_rules_includes_this_rule(self) -> None:
        registry = ValidationRegistry()
        register_schema_rules(registry)
        assert "SCHEMA-0004" in registry.list_rule_ids()

    def test_register_schema_rules_excludes_deferred_enumerations(self) -> None:
        # SCHEMA-0003 is deferred (ADR-0005) and must not be registered.
        registry = ValidationRegistry()
        register_schema_rules(registry)
        assert "SCHEMA-0003" not in registry.list_rule_ids()

    def test_rule_can_be_registered_directly(self) -> None:
        registry = ValidationRegistry()
        registry.register(RequiredArraysRule())
        rules = registry.get_enabled_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], RequiredArraysRule)


@pytest.mark.unit
class TestPipelineAndValidator:
    def _pipeline(self) -> ValidationPipeline:
        registry = ValidationRegistry()
        registry.register(RequiredArraysRule())
        return ValidationPipeline(registry)

    def test_present_passes(self) -> None:
        result = self._pipeline().run(_input(_ALL_COLLECTIONS))
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0

    def test_missing_collection_fails(self) -> None:
        result = self._pipeline().run(_input(_MISSING_RISKS))
        # ERROR finding ⇒ FAILED under the frozen verdict model (not BLOCKED).
        assert result.overall_verdict == ValidationVerdict.FAILED
        assert result.validation_summary.total_issues == 1

    def test_validator_fails_on_missing_collection(self) -> None:
        registry = ValidationRegistry()
        registry.register(RequiredArraysRule())
        validator = ResponseValidator(
            registry, ValidationPipeline(registry), ValidationConfiguration()
        )
        result = validator.validate(_input(_MISSING_RISKS))
        assert result.overall_verdict == ValidationVerdict.FAILED
        assert [i.rule_id for i in result.validation_issues] == ["SCHEMA-0004"]
