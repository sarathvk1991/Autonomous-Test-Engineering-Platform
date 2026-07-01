"""Unit tests for NORMALIZATION-0005 (Assemble ParsedResponse).

Mirrors the NORMALIZATION-0001..0004 test style. Covers identity/metadata, the
NORMALIZED and MALFORMED assembly paths, correct version/outcome/structure/source
reference, metadata preservation, Assembly-State immutability (nothing written
back), observations never read, ParsedResponse immutability, the ordering guard,
the write-loop ``execute`` misuse guard, provider independence, and end-to-end
composition 0001 -> 0002 -> 0003 -> 0004 -> 0005 through the coordinator's consumer
seam.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.models.parsed_response import (
    PARSED_RESPONSE_VERSION,
    ParsedResponse,
)
from requirement_intelligence.normalization.models.normalization_observation import (
    NormalizationObservation,
)
from requirement_intelligence.normalization.response.assembly import (
    AssembleParsedResponse,
    AssemblyState,
    CaptureNormalizationObservations,
    CreateSourceReference,
    DetermineNormalizationOutcome,
    NormalizationStageCoordinator,
    ParsedResponseAssemblyError,
    RecoverCanonicalStructure,
)
from shared.enums.base import NormalizationOutcome

_REF = "sha256:deadbeef"


def _response(text: str = "payload", *, provider: str = "gemini") -> LLMResponse:
    return LLMResponse(provider=provider, model="model", generated_text=text)


def _completed_state(
    structure: dict | None, *, source_reference: str = _REF
) -> AssemblyState:
    """An Assembly State as if 0001, 0002, and 0004 had all run."""
    state = AssemblyState()
    state.record_normalized_structure(structure)
    state.record_normalization_outcome(
        NormalizationOutcome.NORMALIZED
        if structure is not None
        else NormalizationOutcome.MALFORMED
    )
    state.record_source_reference(source_reference)
    return state


class _FixedRecoverer:
    def __init__(self, structure: dict | None) -> None:
        self._structure = structure

    def recover(self, text: str) -> dict | None:
        return self._structure


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_metadata(self) -> None:
        stage = AssembleParsedResponse()
        assert stage.stage_id == "NORMALIZATION-0005"
        assert stage.stage_name == "Assemble ParsedResponse"
        assert stage.order == 5
        assert stage.enabled is True

    def test_documentation_reference_points_at_architecture(self) -> None:
        stage = AssembleParsedResponse()
        assert stage.metadata.documentation_reference is not None
        assert "normalization-assembly-contract" in (
            stage.metadata.documentation_reference
        )

    def test_no_injected_dependency(self) -> None:
        assert AssembleParsedResponse() is not None


# ---------------------------------------------------------------------------
# Assembly — NORMALIZED path
# ---------------------------------------------------------------------------


class TestNormalizedPath:
    def test_builds_parsed_response(self) -> None:
        structure = {"doc": {"items": [1, 2]}}
        parsed = AssembleParsedResponse().assemble(_completed_state(structure))
        assert isinstance(parsed, ParsedResponse)
        assert parsed.normalization_outcome == NormalizationOutcome.NORMALIZED
        assert parsed.normalized_structure == structure
        assert parsed.source_reference == _REF

    def test_uses_the_canonical_version(self) -> None:
        parsed = AssembleParsedResponse().assemble(_completed_state({"a": 1}))
        assert parsed.parsed_response_version == PARSED_RESPONSE_VERSION

    def test_metadata_is_the_canonical_default(self) -> None:
        # No representation metadata is produced by the chain; boundary-local
        # internal metadata must never leak (Assembly Contract §4).
        parsed = AssembleParsedResponse().assemble(_completed_state({"a": 1}))
        assert parsed.metadata == {}


# ---------------------------------------------------------------------------
# Assembly — MALFORMED path (a fact, never an exception)
# ---------------------------------------------------------------------------


class TestMalformedPath:
    def test_still_assembles_a_parsed_response(self) -> None:
        parsed = AssembleParsedResponse().assemble(_completed_state(None))
        assert parsed.normalization_outcome == NormalizationOutcome.MALFORMED
        assert parsed.normalized_structure is None
        assert parsed.source_reference == _REF

    def test_malformed_is_not_an_exception(self) -> None:
        # Assembling a malformed response must never raise.
        AssembleParsedResponse().assemble(_completed_state(None))  # no raise


# ---------------------------------------------------------------------------
# Ownership / Assembly-State immutability — nothing written back
# ---------------------------------------------------------------------------


class TestAssemblyStateUnchanged:
    def test_assemble_writes_nothing_back(self) -> None:
        structure = {"a": 1}
        state = _completed_state(structure)
        AssembleParsedResponse().assemble(state)
        # Every fact is exactly as it was; no recorder was called.
        assert state.normalized_structure == structure
        assert state.normalization_outcome is NormalizationOutcome.NORMALIZED
        assert state.source_reference == _REF
        assert state.observations == ()

    def test_assemble_does_not_read_or_carry_observations(self) -> None:
        state = _completed_state(None)
        state.add_observation(
            NormalizationObservation(
                observation_id="o1",
                observation_type="malformed_representation",
                detail="fact",
                created_at=datetime(2026, 7, 1, tzinfo=UTC),
            )
        )
        parsed = AssembleParsedResponse().assemble(state)
        # Observations remain owned by the state (for the NormalizationResult);
        # ParsedResponse has no observations attribute at all.
        assert len(state.observations) == 1
        assert not hasattr(parsed, "observations")

    def test_does_not_mutate_llm_response_through_the_chain(self) -> None:
        response = _response("original")
        stages = _chain({"a": 1})
        NormalizationStageCoordinator(stages).coordinate(
            response, AssembleParsedResponse().assemble
        )
        assert response.generated_text == "original"


# ---------------------------------------------------------------------------
# ParsedResponse immutability
# ---------------------------------------------------------------------------


class TestParsedResponseImmutable:
    def test_cannot_mutate_after_construction(self) -> None:
        parsed = AssembleParsedResponse().assemble(_completed_state({"a": 1}))
        with pytest.raises(ValidationError):
            parsed.normalization_outcome = NormalizationOutcome.MALFORMED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Ordering guard (infrastructure failure, not a fact)
# ---------------------------------------------------------------------------


class TestOrderingGuard:
    def test_raises_without_structure(self) -> None:
        state = AssemblyState()  # nothing recorded
        with pytest.raises(ParsedResponseAssemblyError, match="NORMALIZATION-0001"):
            AssembleParsedResponse().assemble(state)

    def test_raises_without_outcome(self) -> None:
        state = AssemblyState()
        state.record_normalized_structure({"a": 1})
        with pytest.raises(ParsedResponseAssemblyError, match="NORMALIZATION-0002"):
            AssembleParsedResponse().assemble(state)

    def test_raises_without_source_reference(self) -> None:
        state = AssemblyState()
        state.record_normalized_structure({"a": 1})
        state.record_normalization_outcome(NormalizationOutcome.NORMALIZED)
        with pytest.raises(ParsedResponseAssemblyError, match="NORMALIZATION-0004"):
            AssembleParsedResponse().assemble(state)


# ---------------------------------------------------------------------------
# execute is not the assembling stage's path (misuse guard)
# ---------------------------------------------------------------------------


class TestExecuteMisuseGuard:
    def test_execute_raises(self) -> None:
        state = _completed_state({"a": 1})
        with pytest.raises(ParsedResponseAssemblyError, match="consumer seam"):
            AssembleParsedResponse().execute(_response(), state)


# ---------------------------------------------------------------------------
# Determinism / provider independence / exactly-once purity
# ---------------------------------------------------------------------------


class TestPurity:
    def test_assemble_is_pure_and_repeatable(self) -> None:
        # Assemble reads only; calling it twice yields equal results and leaves the
        # state untouched (safe under the coordinator's exactly-once consumer call).
        state = _completed_state({"a": 1})
        stage = AssembleParsedResponse()
        first = stage.assemble(state)
        second = stage.assemble(state)
        assert first == second
        assert state.normalized_structure == {"a": 1}

    def test_provider_independence(self) -> None:
        results = []
        for provider in ("gemini", "anthropic", "openai", "azure_openai"):
            state = NormalizationStageCoordinator(_chain({"a": 1})).coordinate(
                _response("same", provider=provider), lambda s: s
            )
            results.append(AssembleParsedResponse().assemble(state))
        # Identical structure/outcome/source reference regardless of provider.
        assert all(r == results[0] for r in results)


# ---------------------------------------------------------------------------
# Coordinator composition: 0001 -> 0002 -> 0003 -> 0004 -> 0005 (consumer seam)
# ---------------------------------------------------------------------------


def _chain(structure: dict | None) -> list:
    """The four writing stages; 0005 assembles via the coordinator consumer seam."""
    return [
        RecoverCanonicalStructure(_FixedRecoverer(structure)),
        DetermineNormalizationOutcome(),
        CaptureNormalizationObservations(),
        CreateSourceReference(),
    ]


class TestComposition:
    def test_full_chain_normalized(self) -> None:
        parsed = NormalizationStageCoordinator(_chain({"doc": {}})).coordinate(
            _response("payload"), AssembleParsedResponse().assemble
        )
        assert isinstance(parsed, ParsedResponse)
        assert parsed.normalization_outcome == NormalizationOutcome.NORMALIZED
        assert parsed.normalized_structure == {"doc": {}}
        assert parsed.source_reference is not None
        assert parsed.source_reference.startswith("sha256:")

    def test_full_chain_malformed(self) -> None:
        parsed = NormalizationStageCoordinator(_chain(None)).coordinate(
            _response("payload"), AssembleParsedResponse().assemble
        )
        assert parsed.normalization_outcome == NormalizationOutcome.MALFORMED
        assert parsed.normalized_structure is None
        assert parsed.source_reference is not None

    def test_consumer_extraction_returns_the_parsed_response(self) -> None:
        # The coordinator hands the completed state to the 0005 consumer, which
        # returns the ParsedResponse out of the boundary (Assembly Contract §9).
        result = NormalizationStageCoordinator(_chain({"a": 1})).coordinate(
            _response("payload"), AssembleParsedResponse().assemble
        )
        assert isinstance(result, ParsedResponse)
