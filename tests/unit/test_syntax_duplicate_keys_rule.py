"""Unit tests for SYNTAX-0002 DuplicateKeysRule.

Covers
------
* Metadata & rule identity — matches the catalog entry exactly.
* No duplicate observations — yields no findings.
* Duplicate observations — yields exactly one finding.
* Multiple duplicate observations — still exactly one aggregated finding.
* ValidationIssue contents — severity, blocking, recommendation, message, etc.
* Reads ONLY the observations — never the ParsedResponse, normalized_structure,
  generated_text, or provider output.
* Filters by observation type — a non-duplicate observation does not trigger it.
* Immutability — the issue is frozen; the ValidationInput and NormalizationResult
  are never mutated.
* Determinism & idempotency — repeated calls yield identical finding content.
* Facts, not exceptions — duplicates are a finding, never a raise.
* Infrastructure failure path — a missing NormalizationResult raises
  ValidationRuleError.
* Registry registration, Pipeline execution, Response Validator integration.

Design constraints
------------------
* No mocking of rule logic; the rule is exercised directly.
* Per ADR-0003 the rule receives a ``ValidationInput``.  A real
  ``ResponseNormalizer`` produces the ``NormalizationResult``; duplicate-identifier
  observations are attached with ``model_copy`` because normalization does not emit
  them today (an additive, normalization-owned capability — the rule is written
  against the frozen observation contract, not against current emission).
* A duck-typed spy is used only to prove the rule never touches the ParsedResponse,
  the generated text, or provider output.
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
from requirement_intelligence.normalization.models.normalization_observation import (
    OBSERVATION_DUPLICATE_IDENTIFIER,
    OBSERVATION_ENCODING,
    NormalizationObservation,
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
    DuplicateKeysRule,
    register_syntax_rules,
)
from requirement_intelligence.validation.validation_exceptions import ValidationRuleError
from requirement_intelligence.validation.validation_rule_metadata import DEFAULT_RULE_VERSION

_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)

_NORMALIZED_JSON = '{"doc": {"items": [1, 2]}, "summary": "s"}'

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
        llm_response=LLMResponse(provider="gemini", model="model", generated_text=_NORMALIZED_JSON),
    )


def _normalization_result(analysis: AnalysisResult) -> Any:
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return normalizer.normalize(analysis.llm_response)


def _duplicate_observation(observation_id: str = "obs-dup-1") -> NormalizationObservation:
    return NormalizationObservation(
        observation_id=observation_id,
        observation_type=OBSERVATION_DUPLICATE_IDENTIFIER,
        detail="A field identifier was duplicated within a structural object.",
        location="doc",
        created_at=_TS,
    )


def _encoding_observation() -> NormalizationObservation:
    return NormalizationObservation(
        observation_id="obs-enc-1",
        observation_type=OBSERVATION_ENCODING,
        detail="An encoding fact unrelated to duplicate identifiers.",
        created_at=_TS,
    )


def _input(
    observations: tuple[NormalizationObservation, ...] = (),
    *,
    execution_id: str = "EX-1",
) -> ValidationInput:
    """A real ``ValidationInput`` carrying the given normalization observations."""
    analysis = _analysis_result(execution_id)
    normalization_result = _normalization_result(analysis).model_copy(
        update={"observations": tuple(observations)}
    )
    return ValidationInput(analysis_result=analysis, normalization_result=normalization_result)


def _content(issue: Any) -> tuple[Any, ...]:
    return tuple(getattr(issue, field) for field in _CONTENT_FIELDS)


# ---------------------------------------------------------------------------
# Spy input — proves the rule reads ONLY the observations
# ---------------------------------------------------------------------------


class _SpyNormalizationResult:
    """A NormalizationResult stand-in: observations are readable, but touching
    ``parsed_response`` fails the test."""

    def __init__(self, observations: tuple[NormalizationObservation, ...]) -> None:
        self._observations = observations

    @property
    def observations(self) -> tuple[NormalizationObservation, ...]:
        return self._observations

    @property
    def parsed_response(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SYNTAX-0002 must not inspect parsed_response")


class _SpyAnalysisResult:
    """An AnalysisResult stand-in: execution_id is readable, but touching
    ``llm_response`` (generated_text / provider output) fails the test."""

    def __init__(self, execution_id: str = "EX-1") -> None:
        self.execution_id = execution_id

    @property
    def llm_response(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SYNTAX-0002 must not inspect llm_response/generated_text/provider")


def _spy_input(
    observations: tuple[NormalizationObservation, ...], execution_id: str = "EX-1"
) -> Any:
    """A duck-typed ValidationInput that raises if forbidden fields are read."""
    return SimpleNamespace(
        normalization_result=_SpyNormalizationResult(observations),
        analysis_result=_SpyAnalysisResult(execution_id),
    )


# ---------------------------------------------------------------------------
# 1. Metadata & identity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetadata:
    def test_is_a_validation_rule(self) -> None:
        assert isinstance(DuplicateKeysRule(), ValidationRule)

    def test_rule_id(self) -> None:
        assert DuplicateKeysRule().rule_id == "SYNTAX-0002"

    def test_rule_name(self) -> None:
        assert DuplicateKeysRule().rule_name == "Duplicate Keys"

    def test_layer(self) -> None:
        assert DuplicateKeysRule().validation_layer == ValidationLayer.SYNTAX

    def test_rule_version_is_default(self) -> None:
        assert DuplicateKeysRule().rule_version == DEFAULT_RULE_VERSION

    def test_enabled_by_default(self) -> None:
        assert DuplicateKeysRule().enabled is True

    def test_metadata_is_stable_across_access(self) -> None:
        rule = DuplicateKeysRule()
        assert rule.metadata is rule.metadata


# ---------------------------------------------------------------------------
# 2. No duplicate observations — success
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoDuplicates:
    def test_no_observations_yields_no_issues(self) -> None:
        assert DuplicateKeysRule().validate(_input(())) == []

    def test_only_non_duplicate_observation_yields_no_issues(self) -> None:
        # A non-duplicate observation (encoding) must not trigger this rule.
        assert DuplicateKeysRule().validate(_input((_encoding_observation(),))) == []

    def test_success_returns_empty_list_type(self) -> None:
        result = DuplicateKeysRule().validate(_input(()))
        assert isinstance(result, list)
        assert len(result) == 0

    def test_no_duplicates_via_spy_yields_no_issues(self) -> None:
        assert DuplicateKeysRule().validate(_spy_input((_encoding_observation(),))) == []


# ---------------------------------------------------------------------------
# 3. Duplicate observations & issue contents
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDuplicates:
    def test_one_duplicate_yields_one_issue(self) -> None:
        assert len(DuplicateKeysRule().validate(_input((_duplicate_observation(),)))) == 1

    def test_multiple_duplicates_still_yield_one_issue(self) -> None:
        observations = (
            _duplicate_observation("obs-dup-1"),
            _duplicate_observation("obs-dup-2"),
            _duplicate_observation("obs-dup-3"),
        )
        issues = DuplicateKeysRule().validate(_input(observations))
        assert len(issues) == 1

    def test_mixed_observations_aggregate_only_duplicates(self) -> None:
        observations = (
            _encoding_observation(),
            _duplicate_observation("obs-dup-1"),
            _duplicate_observation("obs-dup-2"),
        )
        issues = DuplicateKeysRule().validate(_input(observations))
        assert len(issues) == 1
        assert "2 duplicate" in issues[0].evidence

    def test_issue_severity_is_critical(self) -> None:
        issue = DuplicateKeysRule().validate(_input((_duplicate_observation(),)))[0]
        assert issue.severity == ValidationSeverity.CRITICAL

    def test_issue_is_blocking(self) -> None:
        issue = DuplicateKeysRule().validate(_input((_duplicate_observation(),)))[0]
        assert issue.blocking is True

    def test_issue_layer_and_category(self) -> None:
        issue = DuplicateKeysRule().validate(_input((_duplicate_observation(),)))[0]
        # ``ValidationIssue`` stores enum fields by value (Schema use_enum_values).
        assert issue.validation_layer == ValidationLayer.SYNTAX.value
        assert issue.category == "syntax"

    def test_issue_identity_fields(self) -> None:
        issue = DuplicateKeysRule().validate(_input((_duplicate_observation(),)))[0]
        assert issue.rule_id == "SYNTAX-0002"
        assert issue.rule_version == DEFAULT_RULE_VERSION
        assert issue.issue_id == "SYNTAX-0002:duplicate_identifier"
        assert issue.location == "$"

    def test_issue_message(self) -> None:
        issue = DuplicateKeysRule().validate(_input((_duplicate_observation(),)))[0]
        assert issue.message == (
            "One or more field identifiers are duplicated within a structural object."
        )

    def test_issue_recommendation(self) -> None:
        issue = DuplicateKeysRule().validate(_input((_duplicate_observation(),)))[0]
        assert issue.recommendation == (
            "Regenerate the AI response so that each field identifier is unique "
            "within its structural object."
        )

    def test_issue_evidence_reports_count(self) -> None:
        issue = DuplicateKeysRule().validate(_input((_duplicate_observation(),)))[0]
        assert issue.evidence == (
            "1 duplicate field identifier observation(s) reported during normalization."
        )

    def test_issue_correlation_from_execution_id(self) -> None:
        issue = DuplicateKeysRule().validate(
            _input((_duplicate_observation(),), execution_id="EX-77")
        )[0]
        assert issue.correlation_id == "EX-77"

    def test_issue_created_at_populated(self) -> None:
        issue = DuplicateKeysRule().validate(_input((_duplicate_observation(),)))[0]
        assert isinstance(issue.created_at, datetime)

    def test_duplicate_via_spy_yields_one_issue(self) -> None:
        assert len(DuplicateKeysRule().validate(_spy_input((_duplicate_observation(),)))) == 1


# ---------------------------------------------------------------------------
# 4. Reads ONLY the observations
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadsOnlyObservations:
    def test_does_not_inspect_parsed_response_on_duplicate(self) -> None:
        # The spy raises if ``parsed_response`` is accessed; a clean run proves the
        # rule never touched it (and therefore never touched normalized_structure).
        assert len(DuplicateKeysRule().validate(_spy_input((_duplicate_observation(),)))) == 1

    def test_does_not_inspect_parsed_response_on_no_duplicate(self) -> None:
        assert DuplicateKeysRule().validate(_spy_input(())) == []

    def test_does_not_inspect_generated_text_or_provider(self) -> None:
        # The spy raises if ``llm_response`` (generated_text / provider) is accessed.
        assert len(DuplicateKeysRule().validate(_spy_input((_duplicate_observation(),)))) == 1
        assert DuplicateKeysRule().validate(_spy_input((_encoding_observation(),))) == []


# ---------------------------------------------------------------------------
# 5. Immutability, determinism, idempotency, purity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleIndependence:
    def test_issue_is_immutable(self) -> None:
        issue = DuplicateKeysRule().validate(_input((_duplicate_observation(),)))[0]
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_does_not_mutate_validation_input(self) -> None:
        rule = DuplicateKeysRule()
        validation_input = _input((_duplicate_observation(),))
        before = validation_input.model_copy(deep=True)
        rule.validate(validation_input)
        assert validation_input == before

    def test_does_not_mutate_normalization_result(self) -> None:
        rule = DuplicateKeysRule()
        validation_input = _input((_duplicate_observation(),))
        normalization_before = validation_input.normalization_result.model_copy(deep=True)
        rule.validate(validation_input)
        assert validation_input.normalization_result == normalization_before

    def test_deterministic_finding_content(self) -> None:
        rule = DuplicateKeysRule()
        validation_input = _input((_duplicate_observation(),))
        first = rule.validate(validation_input)[0]
        second = rule.validate(validation_input)[0]
        assert _content(first) == _content(second)

    def test_idempotent_no_cumulative_effect(self) -> None:
        rule = DuplicateKeysRule()
        with_duplicate = _input((_duplicate_observation(),))
        assert len(rule.validate(with_duplicate)) == 1
        assert len(rule.validate(with_duplicate)) == 1
        without = _input(())
        assert rule.validate(without) == []
        assert rule.validate(without) == []


# ---------------------------------------------------------------------------
# 6. Facts vs exceptions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFactsNotExceptions:
    def test_duplicates_are_a_finding_not_an_exception(self) -> None:
        issues = DuplicateKeysRule().validate(_input((_duplicate_observation(),)))
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.CRITICAL

    def test_missing_normalization_result_raises_infrastructure_error(self) -> None:
        # A structurally broken ValidationInput (no NormalizationResult) is an
        # infrastructure failure, raised as ValidationRuleError — never a finding.
        broken = SimpleNamespace(
            normalization_result=None,
            analysis_result=SimpleNamespace(execution_id="EX-1"),
        )
        with pytest.raises(ValidationRuleError):
            DuplicateKeysRule().validate(broken)


# ---------------------------------------------------------------------------
# 7. Registry registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_register_syntax_rules_includes_this_rule(self) -> None:
        registry = ValidationRegistry()
        register_syntax_rules(registry)
        assert "SYNTAX-0002" in registry.list_rule_ids()

    def test_registered_after_syntax_0001(self) -> None:
        # Catalog order within the Syntax layer: SYNTAX-0001 → SYNTAX-0002.
        registry = ValidationRegistry()
        register_syntax_rules(registry)
        ids = registry.list_rule_ids()
        assert ids.index("SYNTAX-0001") < ids.index("SYNTAX-0002")

    def test_rule_can_be_registered_directly(self) -> None:
        registry = ValidationRegistry()
        registry.register(DuplicateKeysRule())
        rules = registry.get_enabled_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], DuplicateKeysRule)


# ---------------------------------------------------------------------------
# 8. Pipeline & Response Validator integration (SYNTAX-0002 in isolation)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPipelineExecution:
    def _pipeline(self) -> ValidationPipeline:
        registry = ValidationRegistry()
        registry.register(DuplicateKeysRule())
        return ValidationPipeline(registry)

    def test_no_duplicates_passes(self) -> None:
        result = self._pipeline().run(_input(()))
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0

    def test_duplicates_are_blocked(self) -> None:
        result = self._pipeline().run(_input((_duplicate_observation(),)))
        # CRITICAL finding ⇒ BLOCKED under the frozen verdict model (never PASSED).
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert result.overall_verdict != ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 1

    def test_counts_rule_execution(self) -> None:
        result = self._pipeline().run(_input((_duplicate_observation(),)))
        assert result.validation_statistics.rules_executed == 1
        assert result.validation_statistics.rules_failed == 1


@pytest.mark.unit
class TestResponseValidatorIntegration:
    def _validator(self) -> ResponseValidator:
        registry = ValidationRegistry()
        registry.register(DuplicateKeysRule())
        pipeline = ValidationPipeline(registry)
        return ResponseValidator(registry, pipeline, ValidationConfiguration())

    def test_validator_passes_without_duplicates(self) -> None:
        result = self._validator().validate(_input(()))
        assert result.overall_verdict == ValidationVerdict.PASSED

    def test_validator_blocks_on_duplicates(self) -> None:
        result = self._validator().validate(_input((_duplicate_observation(),)))
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert [i.rule_id for i in result.validation_issues] == ["SYNTAX-0002"]
