"""End-to-end integration tests for the wired Response Validator.

Verifies the composition root (``register_all_rules`` + the validator factory) assembles
**only the implemented rules**, in Rule-Catalog layer order
(Transport → Syntax → Schema → Content → Reasoning), and that the assembled validator
runs end-to-end over a real ``ValidationInput`` producing the canonical
``ValidationResult``.

Design constraints
------------------
* No mocking; the real registry, pipeline, ResponseValidator, and rules are exercised.
* A real ``ResponseNormalizer`` produces the ``NormalizationResult`` so the normalized
  structure under test is genuine.
* Deferred rules (``SCHEMA-0003``, ``CONTENT-0003/0004``, ``REASONING-0001/0003``) and
  skipped layers (Structural, Evidence, Traceability, Business) must be absent.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

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
    ValidationInput,
    ValidationLayer,
    ValidationVerdict,
)
from requirement_intelligence.validation.response import (
    ResponseValidator,
    build_response_validator,
    build_validation_pipeline,
    build_validation_registry,
)
from requirement_intelligence.validation.validation_registry import RegistryState

_TS = datetime(2026, 7, 2, 12, 0, 0, tzinfo=UTC)

# The full set of implemented rules, in Rule-Catalog order.
_EXPECTED_RULE_IDS = [
    "TRANSPORT-0001",
    "TRANSPORT-0002",
    "TRANSPORT-0003",
    "TRANSPORT-0004",
    "SYNTAX-0001",
    "SYNTAX-0002",
    "SYNTAX-0003",
    "SCHEMA-0001",
    "SCHEMA-0002",
    "SCHEMA-0004",
    "CONTENT-0001",
    "CONTENT-0002",
    "REASONING-0002",
]

_DEFERRED_RULE_IDS = [
    "SCHEMA-0003",
    "CONTENT-0003",
    "CONTENT-0004",
    "REASONING-0001",
    "REASONING-0003",
]

_SKIPPED_LAYER_PREFIXES = ("STRUCTURE-", "EVIDENCE-", "TRACEABILITY-", "BUSINESS-")

_EXPECTED_LAYER_ORDER = [
    ValidationLayer.TRANSPORT,
    ValidationLayer.SYNTAX,
    ValidationLayer.SCHEMA,
    ValidationLayer.CONTENT,
    ValidationLayer.REASONING,
]

# A fully-conformant governed response — passes every implemented rule.
_VALID = json.dumps(
    {
        "summary": "s",
        "functional_requirements": ["fr"],
        "security_requirements": ["sr"],
        "quality_requirements": ["qr"],
        "risks": ["r"],
        "recommendations": ["rec"],
    }
)
# Missing summary (SCHEMA-0001), duplicate functional requirement (CONTENT-0002),
# duplicate recommendation (REASONING-0002).
_INVALID = json.dumps(
    {
        "functional_requirements": ["A", "A"],
        "security_requirements": [],
        "quality_requirements": [],
        "risks": [],
        "recommendations": ["X", "X"],
    }
)


def _response(text: str) -> LLMResponse:
    return LLMResponse(provider="gemini", model="model", generated_text=text)


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
        llm_response=_response("{}"),
    )


def _normalization_result(text: str) -> Any:
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return normalizer.normalize(_response(text))


def _input(text: str, *, execution_id: str = "EX-1") -> ValidationInput:
    return ValidationInput(
        analysis_result=_analysis_result(execution_id),
        normalization_result=_normalization_result(text),
    )


# ---------------------------------------------------------------------------
# 1. Registration — every implemented rule, nothing else
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistration:
    def test_registry_contains_exactly_the_implemented_rules(self) -> None:
        registry = build_validation_registry()
        assert registry.list_rule_ids() == _EXPECTED_RULE_IDS

    def test_registry_rule_count(self) -> None:
        assert build_validation_registry().rule_count() == len(_EXPECTED_RULE_IDS)

    def test_registry_starts_open(self) -> None:
        # The populated registry is not sealed until a pipeline is constructed from it.
        assert build_validation_registry().state is RegistryState.OPEN

    def test_no_duplicate_rule_ids(self) -> None:
        ids = build_validation_registry().list_rule_ids()
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# 2. Deferred rules & skipped layers are absent
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeferredAndSkippedAbsent:
    def test_deferred_rules_not_registered(self) -> None:
        ids = set(build_validation_registry().list_rule_ids())
        assert ids.isdisjoint(_DEFERRED_RULE_IDS)

    def test_skipped_layers_have_no_rules(self) -> None:
        ids = build_validation_registry().list_rule_ids()
        for rule_id in ids:
            assert not rule_id.startswith(_SKIPPED_LAYER_PREFIXES)

    def test_skipped_layers_empty_in_registry(self) -> None:
        registry = build_validation_registry()
        for layer in (
            ValidationLayer.STRUCTURAL,
            ValidationLayer.EVIDENCE,
            ValidationLayer.TRACEABILITY,
            ValidationLayer.BUSINESS_RULE,
        ):
            assert registry.get_rules_by_layer(layer) == []


# ---------------------------------------------------------------------------
# 3. Rule execution ordering (Transport → Syntax → Schema → Content → Reasoning)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOrdering:
    def test_ordered_rule_ids_match_catalog_order(self) -> None:
        pipeline = build_validation_pipeline()
        assert [r.rule_id for r in pipeline.get_ordered_rules()] == _EXPECTED_RULE_IDS

    def test_distinct_layer_sequence(self) -> None:
        pipeline = build_validation_pipeline()
        layers: list[ValidationLayer] = []
        for rule in pipeline.get_ordered_rules():
            if not layers or layers[-1] != rule.validation_layer:
                layers.append(rule.validation_layer)
        assert layers == _EXPECTED_LAYER_ORDER


# ---------------------------------------------------------------------------
# 4. Factory
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFactory:
    def test_build_response_validator_returns_validator(self) -> None:
        assert isinstance(build_response_validator(), ResponseValidator)

    def test_build_validation_pipeline_seals_its_registry(self) -> None:
        registry = build_validation_registry()
        build_validation_pipeline(registry)
        assert registry.is_sealed is True

    def test_factory_is_independent_per_call(self) -> None:
        # Each build produces its own registry instance (no shared state).
        assert build_validation_registry() is not build_validation_registry()


# ---------------------------------------------------------------------------
# 5. End-to-end validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEndToEnd:
    def test_valid_response_passes(self) -> None:
        result = build_response_validator().validate(_input(_VALID))
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0

    def test_valid_response_executes_all_rules(self) -> None:
        result = build_response_validator().validate(_input(_VALID))
        assert result.validation_statistics.rules_executed == len(_EXPECTED_RULE_IDS)

    def test_invalid_response_fails_with_expected_rules(self) -> None:
        result = build_response_validator().validate(_input(_INVALID))
        assert result.overall_verdict == ValidationVerdict.FAILED
        assert {i.rule_id for i in result.validation_issues} == {
            "SCHEMA-0001",
            "CONTENT-0002",
            "REASONING-0002",
        }

    def test_issues_ordered_by_layer(self) -> None:
        # Aggregated issues follow execution (layer) order: Schema before Content
        # before Reasoning.
        result = build_response_validator().validate(_input(_INVALID))
        rule_ids = [i.rule_id for i in result.validation_issues]
        assert rule_ids == ["SCHEMA-0001", "CONTENT-0002", "REASONING-0002"]

    def test_deterministic_across_runs(self) -> None:
        first = build_response_validator().validate(_input(_INVALID))
        second = build_response_validator().validate(_input(_INVALID))
        assert first.overall_verdict == second.overall_verdict
        assert [i.rule_id for i in first.validation_issues] == [
            i.rule_id for i in second.validation_issues
        ]

    def test_same_validator_idempotent(self) -> None:
        validator = build_response_validator()
        a = validator.validate(_input(_INVALID))
        b = validator.validate(_input(_INVALID))
        assert a.validation_summary.total_issues == b.validation_summary.total_issues

    def test_does_not_mutate_validation_input(self) -> None:
        validation_input = _input(_INVALID)
        before = validation_input.model_copy(deep=True)
        build_response_validator().validate(validation_input)
        assert validation_input == before

    def test_findings_are_returned_not_raised(self) -> None:
        # A response full of violations yields a populated result, never an exception.
        result = build_response_validator().validate(_input(_INVALID))
        assert result.validation_summary.total_issues >= 1

    def test_result_preserves_execution_identity(self) -> None:
        result = build_response_validator().validate(_input(_VALID, execution_id="EX-42"))
        assert result.execution_id == "EX-42"
