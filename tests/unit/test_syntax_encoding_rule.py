"""Unit tests for SYNTAX-0003 EncodingRule — and the normalization capability that
makes it operational.

Covers the rule (metadata, behaviour, ownership, immutability, determinism,
facts-vs-exceptions, integration) and the additive normalization emission that
surfaces ``encoding_observation`` facts end to end:

    recovery mechanism → NORMALIZATION-0001 (transient fact)
        → NORMALIZATION-0003 observation → NormalizationResult
        → SYNTAX-0003 → ValidationIssue

Existing NORMALIZATION-0001/0002/0003 and SYNTAX tests are untouched; the
enhancement is opt-in via an optional recovery-mechanism capability.
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
    OBSERVATION_MALFORMED_REPRESENTATION,
    NormalizationObservation,
)
from requirement_intelligence.normalization.response import ResponseNormalizer
from requirement_intelligence.normalization.response.assembly import (
    AssemblyState,
    CaptureNormalizationObservations,
    DetermineNormalizationOutcome,
    NormalizationStageCoordinator,
    RecoverCanonicalStructure,
)
from requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer import (
    EncodingIntegrityReporter,
)
from requirement_intelligence.normalization.response.assembly.json_canonical_structure_recoverer import (  # noqa: E501
    JsonCanonicalStructureRecoverer,
)
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
from requirement_intelligence.validation.rules.syntax import EncodingRule, register_syntax_rules
from requirement_intelligence.validation.validation_exceptions import ValidationRuleError
from requirement_intelligence.validation.validation_rule_metadata import DEFAULT_RULE_VERSION

_TS = datetime(2026, 7, 2, 12, 0, 0, tzinfo=UTC)

_REPLACEMENT = "�"
_INTACT = '{"a": 1, "b": "ok"}'
_CORRUPT = '{"a": "caf' + _REPLACEMENT + '"}'
_CORRUPT_MALFORMED = "caf" + _REPLACEMENT + " not json"

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
        llm_response=_response(_INTACT),
    )


def _normalizer() -> ResponseNormalizer:
    registry = NormalizationRegistry()
    return ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )


def _encoding_observation(observation_id: str = "obs-enc-1") -> NormalizationObservation:
    return NormalizationObservation(
        observation_id=observation_id,
        observation_type=OBSERVATION_ENCODING,
        detail="A Unicode replacement character indicates a lossy decode.",
        created_at=_TS,
    )


def _duplicate_observation() -> NormalizationObservation:
    return NormalizationObservation(
        observation_id="obs-dup-1",
        observation_type=OBSERVATION_DUPLICATE_IDENTIFIER,
        detail="unrelated",
        created_at=_TS,
    )


def _input(
    observations: tuple[NormalizationObservation, ...] = (),
    *,
    execution_id: str = "EX-1",
) -> ValidationInput:
    """A real ``ValidationInput`` carrying the given normalization observations."""
    analysis = _analysis_result(execution_id)
    normalization_result = _normalizer().normalize(analysis.llm_response)
    normalization_result = normalization_result.model_copy(
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
        raise AssertionError("SYNTAX-0003 must not inspect parsed_response")


class _SpyAnalysisResult:
    """An AnalysisResult stand-in: execution_id is readable, but touching
    ``llm_response`` (generated_text / provider) fails the test."""

    def __init__(self, execution_id: str = "EX-1") -> None:
        self.execution_id = execution_id

    @property
    def llm_response(self) -> Any:  # pragma: no cover - must never run
        raise AssertionError("SYNTAX-0003 must not inspect llm_response/generated_text/provider")


def _spy_input(
    observations: tuple[NormalizationObservation, ...], execution_id: str = "EX-1"
) -> Any:
    return SimpleNamespace(
        normalization_result=_SpyNormalizationResult(observations),
        analysis_result=_SpyAnalysisResult(execution_id),
    )


# ---------------------------------------------------------------------------
# 1. Rule metadata & identity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetadata:
    def test_is_a_validation_rule(self) -> None:
        assert isinstance(EncodingRule(), ValidationRule)

    def test_rule_id(self) -> None:
        assert EncodingRule().rule_id == "SYNTAX-0003"

    def test_rule_name(self) -> None:
        assert EncodingRule().rule_name == "Encoding"

    def test_layer(self) -> None:
        assert EncodingRule().validation_layer == ValidationLayer.SYNTAX

    def test_rule_version_is_default(self) -> None:
        assert EncodingRule().rule_version == DEFAULT_RULE_VERSION

    def test_enabled_by_default(self) -> None:
        assert EncodingRule().enabled is True

    def test_metadata_is_stable_across_access(self) -> None:
        rule = EncodingRule()
        assert rule.metadata is rule.metadata


# ---------------------------------------------------------------------------
# 2. Behaviour
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBehaviour:
    def test_no_encoding_observations_yields_no_issues(self) -> None:
        assert EncodingRule().validate(_input(())) == []

    def test_only_non_encoding_observation_yields_no_issues(self) -> None:
        assert EncodingRule().validate(_input((_duplicate_observation(),))) == []

    def test_one_encoding_observation_yields_one_issue(self) -> None:
        assert len(EncodingRule().validate(_input((_encoding_observation(),)))) == 1

    def test_multiple_encoding_observations_still_one_issue(self) -> None:
        observations = (
            _encoding_observation("obs-enc-1"),
            _encoding_observation("obs-enc-2"),
            _encoding_observation("obs-enc-3"),
        )
        assert len(EncodingRule().validate(_input(observations))) == 1

    def test_mixed_observations_consider_only_encoding(self) -> None:
        observations = (
            _duplicate_observation(),
            _encoding_observation("obs-enc-1"),
            _encoding_observation("obs-enc-2"),
        )
        issues = EncodingRule().validate(_input(observations))
        assert len(issues) == 1
        assert "2 encoding" in issues[0].evidence

    def test_issue_severity_is_critical(self) -> None:
        issue = EncodingRule().validate(_input((_encoding_observation(),)))[0]
        assert issue.severity == ValidationSeverity.CRITICAL

    def test_issue_is_blocking(self) -> None:
        issue = EncodingRule().validate(_input((_encoding_observation(),)))[0]
        assert issue.blocking is True

    def test_issue_layer_and_category(self) -> None:
        issue = EncodingRule().validate(_input((_encoding_observation(),)))[0]
        assert issue.validation_layer == ValidationLayer.SYNTAX.value
        assert issue.category == "syntax"

    def test_issue_identity_fields(self) -> None:
        issue = EncodingRule().validate(_input((_encoding_observation(),)))[0]
        assert issue.rule_id == "SYNTAX-0003"
        assert issue.rule_version == DEFAULT_RULE_VERSION
        assert issue.issue_id == "SYNTAX-0003:encoding"
        assert issue.location == "$"

    def test_issue_message(self) -> None:
        issue = EncodingRule().validate(_input((_encoding_observation(),)))[0]
        assert issue.message == "The response's character encoding is not intact."

    def test_issue_correlation_from_execution_id(self) -> None:
        issue = EncodingRule().validate(_input((_encoding_observation(),), execution_id="EX-88"))[0]
        assert issue.correlation_id == "EX-88"


# ---------------------------------------------------------------------------
# 3. Ownership — reads only observations (spy fails if forbidden fields accessed)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReadsOnlyObservations:
    def test_does_not_inspect_parsed_response_on_finding(self) -> None:
        assert len(EncodingRule().validate(_spy_input((_encoding_observation(),)))) == 1

    def test_does_not_inspect_parsed_response_on_pass(self) -> None:
        assert EncodingRule().validate(_spy_input(())) == []

    def test_does_not_inspect_generated_text_or_provider(self) -> None:
        assert len(EncodingRule().validate(_spy_input((_encoding_observation(),)))) == 1
        assert EncodingRule().validate(_spy_input((_duplicate_observation(),))) == []


# ---------------------------------------------------------------------------
# 4. Immutability, determinism, idempotency
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRuleIndependence:
    def test_issue_is_immutable(self) -> None:
        issue = EncodingRule().validate(_input((_encoding_observation(),)))[0]
        with pytest.raises(ValidationError):
            issue.severity = ValidationSeverity.INFO  # type: ignore[misc]

    def test_does_not_mutate_validation_input(self) -> None:
        rule = EncodingRule()
        validation_input = _input((_encoding_observation(),))
        before = validation_input.model_copy(deep=True)
        rule.validate(validation_input)
        assert validation_input == before

    def test_does_not_mutate_normalization_result_or_observations(self) -> None:
        rule = EncodingRule()
        validation_input = _input((_encoding_observation(),))
        normalization_before = validation_input.normalization_result.model_copy(deep=True)
        observations_before = validation_input.normalization_result.observations
        rule.validate(validation_input)
        assert validation_input.normalization_result == normalization_before
        assert validation_input.normalization_result.observations == observations_before

    def test_deterministic_finding_content(self) -> None:
        rule = EncodingRule()
        validation_input = _input((_encoding_observation(),))
        first = rule.validate(validation_input)[0]
        second = rule.validate(validation_input)[0]
        assert _content(first) == _content(second)

    def test_idempotent_no_cumulative_effect(self) -> None:
        rule = EncodingRule()
        with_encoding = _input((_encoding_observation(),))
        assert len(rule.validate(with_encoding)) == 1
        assert len(rule.validate(with_encoding)) == 1
        without = _input(())
        assert rule.validate(without) == []
        assert rule.validate(without) == []


# ---------------------------------------------------------------------------
# 5. Facts vs exceptions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFactsNotExceptions:
    def test_encoding_problem_is_a_finding_not_an_exception(self) -> None:
        issues = EncodingRule().validate(_input((_encoding_observation(),)))
        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.CRITICAL

    def test_missing_normalization_result_raises_infrastructure_error(self) -> None:
        broken = SimpleNamespace(
            normalization_result=None,
            analysis_result=SimpleNamespace(execution_id="EX-1"),
        )
        with pytest.raises(ValidationRuleError):
            EncodingRule().validate(broken)


# ---------------------------------------------------------------------------
# 6. Registration, pipeline, validator integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_register_syntax_rules_includes_this_rule(self) -> None:
        registry = ValidationRegistry()
        register_syntax_rules(registry)
        assert "SYNTAX-0003" in registry.list_rule_ids()

    def test_registered_in_catalog_order(self) -> None:
        registry = ValidationRegistry()
        register_syntax_rules(registry)
        ids = registry.list_rule_ids()
        assert ids.index("SYNTAX-0002") < ids.index("SYNTAX-0003")

    def test_rule_can_be_registered_directly(self) -> None:
        registry = ValidationRegistry()
        registry.register(EncodingRule())
        rules = registry.get_enabled_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], EncodingRule)


@pytest.mark.unit
class TestPipelineAndValidator:
    def _pipeline(self) -> ValidationPipeline:
        registry = ValidationRegistry()
        registry.register(EncodingRule())
        return ValidationPipeline(registry)

    def test_no_encoding_passes(self) -> None:
        result = self._pipeline().run(_input(()))
        assert result.overall_verdict == ValidationVerdict.PASSED

    def test_encoding_is_blocked(self) -> None:
        result = self._pipeline().run(_input((_encoding_observation(),)))
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert result.validation_summary.total_issues == 1

    def test_validator_blocks_on_encoding(self) -> None:
        registry = ValidationRegistry()
        registry.register(EncodingRule())
        validator = ResponseValidator(
            registry, ValidationPipeline(registry), ValidationConfiguration()
        )
        result = validator.validate(_input((_encoding_observation(),)))
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert [i.rule_id for i in result.validation_issues] == ["SYNTAX-0003"]


# ---------------------------------------------------------------------------
# 7. Normalization capability — recovery mechanism detects encoding facts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRecovererEncodingDetection:
    def test_recoverer_is_an_encoding_integrity_reporter(self) -> None:
        assert isinstance(JsonCanonicalStructureRecoverer(), EncodingIntegrityReporter)

    def test_intact_text_reports_nothing(self) -> None:
        assert JsonCanonicalStructureRecoverer().encoding_observations(_INTACT) == ()

    def test_corrupt_text_reports_a_fact(self) -> None:
        facts = JsonCanonicalStructureRecoverer().encoding_observations(_CORRUPT)
        assert len(facts) == 1
        assert "U+FFFD" in facts[0]

    def test_corrupt_even_when_malformed(self) -> None:
        # Encoding integrity is independent of well-formedness — reported regardless.
        assert JsonCanonicalStructureRecoverer().encoding_observations(_CORRUPT_MALFORMED) != ()

    def test_recover_structure_unaffected(self) -> None:
        # recover() still yields the object; encoding detection does not change it.
        assert JsonCanonicalStructureRecoverer().recover(_CORRUPT) == {"a": "caf" + _REPLACEMENT}

    def test_deterministic(self) -> None:
        recoverer = JsonCanonicalStructureRecoverer()
        first = recoverer.encoding_observations(_CORRUPT)
        second = recoverer.encoding_observations(_CORRUPT)
        assert first == second


# ---------------------------------------------------------------------------
# 8. NORMALIZATION-0001 forwarding & NORMALIZATION-0003 emission
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNormalizationStages:
    def test_0001_forwards_encoding_facts(self) -> None:
        from requirement_intelligence.normalization.response.assembly.assembly_state import (
            ENCODING_OBSERVATIONS_METADATA_KEY,
        )

        state = AssemblyState()
        RecoverCanonicalStructure(JsonCanonicalStructureRecoverer()).execute(
            _response(_CORRUPT), state
        )
        assert state.internal_metadata[ENCODING_OBSERVATIONS_METADATA_KEY] != ()

    def test_0001_no_encoding_fact_when_intact(self) -> None:
        state = AssemblyState()
        RecoverCanonicalStructure(JsonCanonicalStructureRecoverer()).execute(
            _response(_INTACT), state
        )
        assert state.internal_metadata == {}

    def test_chain_emits_encoding_observation(self) -> None:
        stages = [
            RecoverCanonicalStructure(JsonCanonicalStructureRecoverer()),
            DetermineNormalizationOutcome(),
            CaptureNormalizationObservations(),
        ]
        state = NormalizationStageCoordinator(stages).coordinate(_response(_CORRUPT), lambda s: s)
        types = [o.observation_type for o in state.observations]
        assert OBSERVATION_ENCODING in types

    def test_chain_intact_emits_no_encoding_observation(self) -> None:
        stages = [
            RecoverCanonicalStructure(JsonCanonicalStructureRecoverer()),
            DetermineNormalizationOutcome(),
            CaptureNormalizationObservations(),
        ]
        state = NormalizationStageCoordinator(stages).coordinate(_response(_INTACT), lambda s: s)
        assert state.observations == ()

    def test_malformed_still_only_malformed_when_encoding_intact(self) -> None:
        stages = [
            RecoverCanonicalStructure(JsonCanonicalStructureRecoverer()),
            DetermineNormalizationOutcome(),
            CaptureNormalizationObservations(),
        ]
        state = NormalizationStageCoordinator(stages).coordinate(
            _response("}{ not json"), lambda s: s
        )
        assert [o.observation_type for o in state.observations] == [
            OBSERVATION_MALFORMED_REPRESENTATION
        ]


# ---------------------------------------------------------------------------
# 9. End-to-end: ResponseNormalizer → SYNTAX-0003 → ValidationIssue
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEndToEnd:
    def _validate(self, text: str) -> object:
        analysis = _analysis_result()
        analysis = analysis.model_copy(update={"llm_response": _response(text)})
        normalization_result = _normalizer().normalize(analysis.llm_response)
        validation_input = ValidationInput(
            analysis_result=analysis, normalization_result=normalization_result
        )
        registry = ValidationRegistry()
        registry.register(EncodingRule())
        validator = ResponseValidator(
            registry, ValidationPipeline(registry), ValidationConfiguration()
        )
        return validator.validate(validation_input)

    def test_corrupt_response_produces_validation_issue(self) -> None:
        result = self._validate(_CORRUPT)
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert [i.rule_id for i in result.validation_issues] == ["SYNTAX-0003"]

    def test_intact_response_passes(self) -> None:
        result = self._validate(_INTACT)
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0

    def test_provider_independence(self) -> None:
        for provider in ("gemini", "anthropic", "openai", "azure_openai"):
            analysis = _analysis_result().model_copy(
                update={"llm_response": _response(_CORRUPT, provider=provider)}
            )
            normalization_result = _normalizer().normalize(analysis.llm_response)
            types = [o.observation_type for o in normalization_result.observations]
            assert OBSERVATION_ENCODING in types
