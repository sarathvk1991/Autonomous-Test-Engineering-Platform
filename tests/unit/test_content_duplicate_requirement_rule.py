"""Unit tests for CONTENT-0002 DuplicateRequirementRule.

Covers metadata/identity, happy path, duplicate findings and per-occurrence counting,
per-collection independence (cross-collection duplicates NOT reported, ADR-0007),
byte-exact / case-sensitive / whitespace-sensitive matching, the ownership boundary
(absent/non-list collections and non-string elements skipped), read-only ownership
(spy-proven), input immutability, determinism/idempotency, facts-vs-exceptions, deferral
on an absent structure, and registration / pipeline / validator integration.

Design constraints
------------------
* No mocking of rule logic; the rule is exercised directly.
* Per ADR-0003 the rule receives a ``ValidationInput``; per Rule Catalog §9.5 and
  ADR-0007 it owns **within-collection** duplication of the three requirement
  collections, evaluated independently and never pooled.
* A real ``ResponseNormalizer`` produces the ``NormalizationResult`` (and thus a real
  ``ParsedResponse``) so the normalized structure under test is genuine.
* A duck-typed spy proves the rule never reads the outcome, observations, generated
  text, provider, source reference, or metadata.
"""

from __future__ import annotations

import json
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
from requirement_intelligence.validation.rules.content import (
    DuplicateRequirementRule,
    register_content_rules,
)
from requirement_intelligence.validation.validation_exceptions import ValidationRuleError
from requirement_intelligence.validation.validation_rule_metadata import DEFAULT_RULE_VERSION

_TS = datetime(2026, 7, 2, 12, 0, 0, tzinfo=UTC)

_REQUIREMENT_COLLECTIONS = (
    "functional_requirements",
    "security_requirements",
    "quality_requirements",
)

_NO_DUP = json.dumps(
    {
        "summary": "s",
        "functional_requirements": ["A", "B", "C"],
        "security_requirements": ["A"],  # same "A" as functional → NOT pooled (ADR-0007)
        "quality_requirements": ["A"],  # same "A" again → still not a finding
        "risks": ["R", "R"],  # not a requirement → ignored
        "recommendations": ["Rec", "Rec"],  # not a requirement → ignored
    }
)
_ONE_DUP = json.dumps({"functional_requirements": ["A", "B", "A"]})
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
        raise AssertionError("CONTENT-0002 must not inspect the normalization outcome")

    @property
    def source_reference(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("CONTENT-0002 must not inspect source_reference")

    @property
    def metadata(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("CONTENT-0002 must not inspect ParsedResponse metadata")


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
        raise AssertionError("CONTENT-0002 must not inspect observations")


class _SpyAnalysisResult:
    """An AnalysisResult stand-in: execution_id is readable; llm_response
    (generated_text / provider) fails the test if read."""

    def __init__(self, execution_id: str = "EX-1") -> None:
        self.execution_id = execution_id

    @property
    def llm_response(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("CONTENT-0002 must not inspect llm_response/generated_text/provider")


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
        assert isinstance(DuplicateRequirementRule(), ValidationRule)

    def test_rule_id(self) -> None:
        assert DuplicateRequirementRule().rule_id == "CONTENT-0002"

    def test_rule_name(self) -> None:
        assert DuplicateRequirementRule().rule_name == "Duplicate Requirement"

    def test_layer(self) -> None:
        assert DuplicateRequirementRule().validation_layer == ValidationLayer.CONTENT

    def test_rule_version_is_default(self) -> None:
        assert DuplicateRequirementRule().rule_version == DEFAULT_RULE_VERSION

    def test_enabled_by_default(self) -> None:
        assert DuplicateRequirementRule().enabled is True

    def test_metadata_is_stable_across_access(self) -> None:
        rule = DuplicateRequirementRule()
        assert rule.metadata is rule.metadata

    def test_severity_and_blocking_from_catalog(self) -> None:
        # Catalog §14: a duplicate requirement is ERROR (→ FAILED); §15: Content is a
        # semantic layer that records and never blocks.
        issue = DuplicateRequirementRule().validate(_input(_ONE_DUP))[0]
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.blocking is False


# ---------------------------------------------------------------------------
# 2. Happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHappyPath:
    def test_no_duplicates_yields_no_issues(self) -> None:
        assert DuplicateRequirementRule().validate(_input(_NO_DUP)) == []

    def test_success_returns_empty_list_type(self) -> None:
        result = DuplicateRequirementRule().validate(_input(_NO_DUP))
        assert isinstance(result, list)
        assert len(result) == 0

    def test_no_requirement_collections_present_yields_no_issues(self) -> None:
        assert DuplicateRequirementRule().validate(_spy_input({"summary": "s"})) == []


# ---------------------------------------------------------------------------
# 3. Duplicate findings & issue contents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDuplicate:
    def test_single_duplicate_yields_one_issue(self) -> None:
        assert len(DuplicateRequirementRule().validate(_input(_ONE_DUP))) == 1

    def test_issue_identity_fields(self) -> None:
        # ["A","B","A"] → the second "A" at index 2 is the duplicate occurrence.
        issue = DuplicateRequirementRule().validate(_input(_ONE_DUP))[0]
        assert issue.rule_id == "CONTENT-0002"
        assert issue.rule_version == DEFAULT_RULE_VERSION
        assert issue.issue_id == "CONTENT-0002:functional_requirements[2]"
        assert issue.location == "functional_requirements[2]"

    def test_issue_layer_and_category(self) -> None:
        issue = DuplicateRequirementRule().validate(_input(_ONE_DUP))[0]
        assert issue.validation_layer == ValidationLayer.CONTENT.value
        assert issue.category == "content"

    def test_issue_message_and_recommendation(self) -> None:
        issue = DuplicateRequirementRule().validate(_input(_ONE_DUP))[0]
        assert issue.message == (
            "The requirement statement at functional_requirements[2] duplicates an "
            "earlier statement in 'functional_requirements'."
        )
        assert issue.recommendation == (
            "Remove the duplicate requirement statement at functional_requirements[2] "
            "or replace it with a distinct statement."
        )

    def test_issue_evidence_is_none(self) -> None:
        issue = DuplicateRequirementRule().validate(_input(_ONE_DUP))[0]
        assert issue.evidence is None

    def test_issue_correlation_from_execution_id(self) -> None:
        issue = DuplicateRequirementRule().validate(_input(_ONE_DUP, execution_id="EX-9"))[0]
        assert issue.correlation_id == "EX-9"

    def test_issue_created_at_populated(self) -> None:
        issue = DuplicateRequirementRule().validate(_input(_ONE_DUP))[0]
        assert isinstance(issue.created_at, datetime)

    @pytest.mark.parametrize("collection", _REQUIREMENT_COLLECTIONS)
    def test_each_requirement_collection_checked(self, collection: str) -> None:
        issues = DuplicateRequirementRule().validate(_spy_input({collection: ["A", "A"]}))
        assert len(issues) == 1
        assert issues[0].location == f"{collection}[1]"


# ---------------------------------------------------------------------------
# 4. Per-occurrence counting (one issue per duplicate occurrence)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPerOccurrence:
    def test_two_extra_occurrences_yield_two_issues(self) -> None:
        # ["A","B","A","A"] → the second and third "A" (indices 2 and 3) are findings;
        # the first "A" is never a finding.
        structure = {"functional_requirements": ["A", "B", "A", "A"]}
        issues = DuplicateRequirementRule().validate(_spy_input(structure))
        assert [i.location for i in issues] == [
            "functional_requirements[2]",
            "functional_requirements[3]",
        ]

    def test_first_occurrence_never_reported(self) -> None:
        structure = {"functional_requirements": ["A", "A"]}
        issues = DuplicateRequirementRule().validate(_spy_input(structure))
        assert [i.location for i in issues] == ["functional_requirements[1]"]

    def test_multiple_distinct_duplicates(self) -> None:
        structure = {"functional_requirements": ["A", "A", "B", "B"]}
        issues = DuplicateRequirementRule().validate(_spy_input(structure))
        assert [i.location for i in issues] == [
            "functional_requirements[1]",
            "functional_requirements[3]",
        ]


# ---------------------------------------------------------------------------
# 5. Per-collection independence (ADR-0007 — collections never pooled)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPerCollectionScope:
    def test_same_string_across_collections_not_reported(self) -> None:
        structure = {
            "functional_requirements": ["A"],
            "security_requirements": ["A"],
            "quality_requirements": ["A"],
        }
        assert DuplicateRequirementRule().validate(_spy_input(structure)) == []

    def test_duplicates_reported_independently_per_collection(self) -> None:
        structure = {
            "functional_requirements": ["A", "A"],
            "security_requirements": ["A", "A"],
        }
        issues = DuplicateRequirementRule().validate(_spy_input(structure))
        assert {i.location for i in issues} == {
            "functional_requirements[1]",
            "security_requirements[1]",
        }


# ---------------------------------------------------------------------------
# 6. Byte-exact, case-sensitive, whitespace-sensitive matching
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExactMatching:
    def test_case_sensitive_not_a_duplicate(self) -> None:
        assert (
            DuplicateRequirementRule().validate(_spy_input({"functional_requirements": ["A", "a"]}))
            == []
        )

    def test_whitespace_sensitive_not_a_duplicate(self) -> None:
        assert (
            DuplicateRequirementRule().validate(
                _spy_input({"functional_requirements": ["A", "A "]})
            )
            == []
        )

    def test_byte_exact_duplicate_is_reported(self) -> None:
        issues = DuplicateRequirementRule().validate(
            _spy_input({"functional_requirements": ["A A", "A A"]})
        )
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# 7. Ownership boundary — non-requirement sections & non-list/non-string skipped
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOwnershipBoundary:
    def test_summary_ignored(self) -> None:
        assert DuplicateRequirementRule().validate(_spy_input({"summary": "s"})) == []

    def test_risks_ignored(self) -> None:
        assert DuplicateRequirementRule().validate(_spy_input({"risks": ["R", "R"]})) == []

    def test_recommendations_ignored(self) -> None:
        assert (
            DuplicateRequirementRule().validate(_spy_input({"recommendations": ["Rec", "Rec"]}))
            == []
        )

    def test_absent_collection_skipped(self) -> None:
        assert DuplicateRequirementRule().validate(_spy_input({})) == []

    def test_empty_collection_skipped(self) -> None:
        assert (
            DuplicateRequirementRule().validate(_spy_input({"functional_requirements": []})) == []
        )

    def test_non_list_collection_skipped(self) -> None:
        # A present-but-non-list value is SCHEMA-0002's concern (type), not this rule's.
        assert (
            DuplicateRequirementRule().validate(_spy_input({"functional_requirements": "AA"})) == []
        )

    def test_non_string_elements_skipped(self) -> None:
        # Repeated non-string elements are not requirement statements → ignored.
        structure = {"functional_requirements": [1, 1, None, None, {"a": 1}, {"a": 1}]}
        assert DuplicateRequirementRule().validate(_spy_input(structure)) == []

    def test_non_string_duplicate_ignored_but_string_duplicate_found(self) -> None:
        structure = {"functional_requirements": [1, 1, "A", "A"]}
        issues = DuplicateRequirementRule().validate(_spy_input(structure))
        assert [i.location for i in issues] == ["functional_requirements[3]"]


# ---------------------------------------------------------------------------
# 8. Reads only the normalized structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadsOnlyStructure:
    def test_does_not_inspect_forbidden_fields_on_pass(self) -> None:
        assert (
            DuplicateRequirementRule().validate(_spy_input({"functional_requirements": ["A"]}))
            == []
        )

    def test_does_not_inspect_forbidden_fields_on_finding(self) -> None:
        assert (
            len(
                DuplicateRequirementRule().validate(
                    _spy_input({"functional_requirements": ["A", "A"]})
                )
            )
            == 1
        )


# ---------------------------------------------------------------------------
# 9. Immutability, determinism, idempotency
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleIndependence:
    def test_issue_is_immutable(self) -> None:
        issue = DuplicateRequirementRule().validate(_input(_ONE_DUP))[0]
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_does_not_mutate_validation_input(self) -> None:
        rule = DuplicateRequirementRule()
        validation_input = _input(_ONE_DUP)
        before = validation_input.model_copy(deep=True)
        rule.validate(validation_input)
        assert validation_input == before

    def test_does_not_mutate_parsed_response_or_structure(self) -> None:
        rule = DuplicateRequirementRule()
        validation_input = _input(_ONE_DUP)
        parsed = validation_input.normalization_result.parsed_response
        parsed_before = parsed.model_copy(deep=True)
        structure_before = dict(parsed.normalized_structure)
        rule.validate(validation_input)
        assert parsed == parsed_before
        assert parsed.normalized_structure == structure_before

    def test_deterministic_finding_content(self) -> None:
        rule = DuplicateRequirementRule()
        validation_input = _input(_ONE_DUP)
        first = rule.validate(validation_input)[0]
        second = rule.validate(validation_input)[0]
        assert _content(first) == _content(second)

    def test_idempotent_no_cumulative_effect(self) -> None:
        rule = DuplicateRequirementRule()
        dup = _input(_ONE_DUP)
        assert len(rule.validate(dup)) == 1
        assert len(rule.validate(dup)) == 1
        clean = _input(_NO_DUP)
        assert rule.validate(clean) == []
        assert rule.validate(clean) == []


# ---------------------------------------------------------------------------
# 10. Facts vs exceptions & deferral
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFactsNotExceptions:
    def test_duplicate_is_a_finding_not_an_exception(self) -> None:
        issues = DuplicateRequirementRule().validate(_input(_ONE_DUP))
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.ERROR

    def test_defers_on_absent_structure(self) -> None:
        # MALFORMED response → no normalized structure → defer (Syntax owns
        # well-formedness). Never re-report; never raise.
        assert DuplicateRequirementRule().validate(_input(_MALFORMED)) == []

    def test_missing_parsed_response_raises_infrastructure_error(self) -> None:
        analysis = _analysis_result()
        broken = _normalization_result(analysis, _NO_DUP).model_copy(
            update={"parsed_response": None}
        )
        validation_input = ValidationInput(analysis_result=analysis, normalization_result=broken)
        with pytest.raises(ValidationRuleError):
            DuplicateRequirementRule().validate(validation_input)


# ---------------------------------------------------------------------------
# 11. Registration, pipeline, validator integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_register_content_rules_includes_this_rule(self) -> None:
        registry = ValidationRegistry()
        register_content_rules(registry)
        assert "CONTENT-0002" in registry.list_rule_ids()

    def test_rule_can_be_registered_directly(self) -> None:
        registry = ValidationRegistry()
        registry.register(DuplicateRequirementRule())
        rules = registry.get_enabled_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], DuplicateRequirementRule)


@pytest.mark.unit
class TestPipelineAndValidator:
    def _pipeline(self) -> ValidationPipeline:
        registry = ValidationRegistry()
        registry.register(DuplicateRequirementRule())
        return ValidationPipeline(registry)

    def test_no_duplicates_passes(self) -> None:
        result = self._pipeline().run(_input(_NO_DUP))
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0

    def test_duplicate_fails(self) -> None:
        result = self._pipeline().run(_input(_ONE_DUP))
        # ERROR finding ⇒ FAILED under the frozen verdict model (semantic, non-blocking).
        assert result.overall_verdict == ValidationVerdict.FAILED
        assert result.validation_summary.total_issues == 1

    def test_validator_fails_on_duplicate(self) -> None:
        registry = ValidationRegistry()
        registry.register(DuplicateRequirementRule())
        validator = ResponseValidator(
            registry, ValidationPipeline(registry), ValidationConfiguration()
        )
        result = validator.validate(_input(_ONE_DUP))
        assert result.overall_verdict == ValidationVerdict.FAILED
        assert [i.rule_id for i in result.validation_issues] == ["CONTENT-0002"]
