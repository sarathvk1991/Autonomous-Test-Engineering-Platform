"""End-to-end integration tests for the fully-wired Response Normalization subsystem.

These exercise the **real** subsystem — a real ``NormalizationRegistry``, a real
``NormalizationPipeline``, and the internal stage chain
(``NORMALIZATION-0001…0005``) coordinated inside the ``ResponseNormalizer`` boundary
— with no stubs. They verify the complete wiring:

* the NORMALIZED and MALFORMED flows end to end;
* the ``ParsedResponse`` is assembled and attached to the ``NormalizationResult``;
* observations are attached to the result (never to the ``ParsedResponse``);
* framework telemetry (statistics, framework metadata, configuration) is populated
  and describes the framework pass (decision: it is not reinterpreted for stages);
* provider independence, immutability, and single-execution behaviour;
* the ``AssemblyState`` never escapes the boundary.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.models.parsed_response import (
    PARSED_RESPONSE_VERSION,
    ParsedResponse,
)
from requirement_intelligence.normalization.framework import (
    NormalizationPipeline,
    NormalizationRegistry,
)
from requirement_intelligence.normalization.models import (
    NormalizationConfiguration,
    NormalizationFrameworkMetadata,
    NormalizationResult,
    NormalizationStatistics,
)
from requirement_intelligence.normalization.models.normalization_observation import (
    OBSERVATION_MALFORMED_REPRESENTATION,
)
from requirement_intelligence.normalization.response import ResponseNormalizer
from shared.enums.base import NormalizationOutcome

_NORMALIZED_JSON = '{"doc": {"items": [1, 2]}, "summary": "s"}'


def _llm_response(text: str, *, provider: str = "gemini") -> LLMResponse:
    return LLMResponse(provider=provider, model="model", generated_text=text)


def _normalizer(
    *, configuration: NormalizationConfiguration | None = None
) -> ResponseNormalizer:
    """A fully real Response Normalizer — real registry, real pipeline, no stubs."""
    registry = NormalizationRegistry()
    pipeline = NormalizationPipeline(registry)
    return ResponseNormalizer(
        registry, pipeline, configuration or NormalizationConfiguration()
    )


# ---------------------------------------------------------------------------
# NORMALIZED flow
# ---------------------------------------------------------------------------


class TestNormalizedFlow:
    def test_normalized_json_produces_parsed_response(self) -> None:
        result = _normalizer().normalize(_llm_response(_NORMALIZED_JSON))
        assert isinstance(result, NormalizationResult)
        parsed = result.parsed_response
        assert isinstance(parsed, ParsedResponse)
        assert parsed.normalization_outcome == NormalizationOutcome.NORMALIZED
        assert parsed.normalized_structure == {"doc": {"items": [1, 2]}, "summary": "s"}
        assert parsed.source_reference is not None
        assert parsed.source_reference.startswith("sha256:")
        assert parsed.parsed_response_version == PARSED_RESPONSE_VERSION

    def test_normalized_flow_records_no_observations(self) -> None:
        result = _normalizer().normalize(_llm_response(_NORMALIZED_JSON))
        assert result.observations == ()

    def test_non_object_json_is_malformed(self) -> None:
        # Valid JSON, but an array is not a structural document → MALFORMED.
        result = _normalizer().normalize(_llm_response("[1, 2, 3]"))
        assert result.parsed_response.normalization_outcome == (
            NormalizationOutcome.MALFORMED
        )
        assert result.parsed_response.normalized_structure is None


# ---------------------------------------------------------------------------
# MALFORMED flow
# ---------------------------------------------------------------------------


class TestMalformedFlow:
    def test_malformed_text_still_produces_parsed_response(self) -> None:
        result = _normalizer().normalize(_llm_response("not json at all"))
        parsed = result.parsed_response
        assert isinstance(parsed, ParsedResponse)
        assert parsed.normalization_outcome == NormalizationOutcome.MALFORMED
        assert parsed.normalized_structure is None
        assert parsed.source_reference is not None  # reference still created

    def test_malformed_flow_records_one_observation(self) -> None:
        result = _normalizer().normalize(_llm_response("}{ broken"))
        assert len(result.observations) == 1
        assert result.observations[0].observation_type == (
            OBSERVATION_MALFORMED_REPRESENTATION
        )

    def test_empty_response_is_malformed(self) -> None:
        result = _normalizer().normalize(_llm_response(""))
        assert result.parsed_response.normalization_outcome == (
            NormalizationOutcome.MALFORMED
        )
        assert len(result.observations) == 1


# ---------------------------------------------------------------------------
# Ownership boundaries — no duplicated ownership
# ---------------------------------------------------------------------------


class TestOwnershipBoundaries:
    def test_parsed_response_carries_only_representation_fields(self) -> None:
        parsed = _normalizer().normalize(_llm_response(_NORMALIZED_JSON)).parsed_response
        # outcome + structure + source reference; never observations.
        assert not hasattr(parsed, "observations")
        assert parsed.normalization_outcome is not None
        assert parsed.source_reference is not None

    def test_observations_owned_by_result_not_parsed_response(self) -> None:
        result = _normalizer().normalize(_llm_response("broken"))
        # Observations live on the result; the ParsedResponse never carries them.
        assert len(result.observations) == 1
        assert not hasattr(result.parsed_response, "observations")

    def test_assembly_state_never_escapes(self) -> None:
        # The returned result is a NormalizationResult carrying a ParsedResponse;
        # no AssemblyState leaks into either.
        result = _normalizer().normalize(_llm_response(_NORMALIZED_JSON))
        assert type(result).__name__ == "NormalizationResult"
        assert type(result.parsed_response).__name__ == "ParsedResponse"
        assert "AssemblyState" not in repr(type(result.parsed_response))


# ---------------------------------------------------------------------------
# Framework telemetry populated (and unchanged for the framework pass)
# ---------------------------------------------------------------------------


class TestFrameworkTelemetry:
    def test_statistics_populated(self) -> None:
        result = _normalizer().normalize(_llm_response(_NORMALIZED_JSON))
        stats = result.normalization_statistics
        assert isinstance(stats, NormalizationStatistics)
        # Framework telemetry describes the framework pass (no framework
        # responsibilities registered), not the internal stages.
        assert stats.responsibilities_executed == 0
        assert stats.observations_recorded == 0

    def test_framework_metadata_populated(self) -> None:
        result = _normalizer().normalize(_llm_response(_NORMALIZED_JSON))
        assert isinstance(
            result.normalization_framework_metadata, NormalizationFrameworkMetadata
        )

    def test_configuration_preserved(self) -> None:
        config = NormalizationConfiguration(normalization_contract_version="3.1")
        result = _normalizer(configuration=config).normalize(
            _llm_response(_NORMALIZED_JSON)
        )
        assert result.normalization_configuration is config

    def test_execution_context_created(self) -> None:
        normalizer = _normalizer()
        normalizer.normalize(_llm_response(_NORMALIZED_JSON))
        ctx = normalizer.last_execution_context
        assert ctx is not None
        assert ctx.normalization_id
        assert ctx.framework_version


# ---------------------------------------------------------------------------
# Provider independence, immutability, single execution
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_provider_independence(self) -> None:
        structures = []
        references = []
        for provider in ("gemini", "anthropic", "openai", "azure_openai"):
            result = _normalizer().normalize(
                _llm_response(_NORMALIZED_JSON, provider=provider)
            )
            structures.append(result.parsed_response.normalized_structure)
            references.append(result.parsed_response.source_reference)
        assert all(s == structures[0] for s in structures)
        assert len(set(references)) == 1  # reference depends only on the text

    def test_parsed_response_is_immutable(self) -> None:
        parsed = _normalizer().normalize(_llm_response(_NORMALIZED_JSON)).parsed_response
        with pytest.raises(ValidationError):
            parsed.normalization_outcome = NormalizationOutcome.MALFORMED  # type: ignore[misc]

    def test_each_stage_runs_once_per_normalize(self) -> None:
        # If any stage ran twice, a malformed response would record two
        # observations; exactly one proves the chain ran once.
        result = _normalizer().normalize(_llm_response("broken"))
        assert len(result.observations) == 1

    def test_repeated_normalize_is_independent(self) -> None:
        normalizer = _normalizer()
        first = normalizer.normalize(_llm_response(_NORMALIZED_JSON))
        second = normalizer.normalize(_llm_response("broken"))
        # Each run produces its own coherent result; no state bleeds across runs.
        assert first.parsed_response.normalization_outcome == (
            NormalizationOutcome.NORMALIZED
        )
        assert second.parsed_response.normalization_outcome == (
            NormalizationOutcome.MALFORMED
        )
        assert first.observations == ()
        assert len(second.observations) == 1

    def test_does_not_mutate_llm_response(self) -> None:
        response = _llm_response(_NORMALIZED_JSON)
        _normalizer().normalize(response)
        assert response.generated_text == _NORMALIZED_JSON
