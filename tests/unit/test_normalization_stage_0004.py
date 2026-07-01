"""Unit tests for NORMALIZATION-0004 (Create Source Reference).

Mirrors the NORMALIZATION-0001/0002/0003 test style. Covers identity/metadata,
ownership (writes only the source reference), the reference-is-not-a-copy
guarantee, determinism, provider independence, ``LLMResponse`` immutability, facts
vs. exceptions, the single-write guard, stage independence (no ordering guard), and
end-to-end composition 0001 → 0002 → 0003 → 0004 through the coordinator on both
the NORMALIZED and MALFORMED paths.
"""

from __future__ import annotations

import hashlib

import pytest

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.response.assembly import (
    AssemblyState,
    AssemblyStateError,
    CaptureNormalizationObservations,
    CreateSourceReference,
    DetermineNormalizationOutcome,
    NormalizationStageCoordinator,
    RecoverCanonicalStructure,
)
from shared.enums.base import NormalizationOutcome


def _response(text: str = "text", *, provider: str = "gemini") -> LLMResponse:
    return LLMResponse(provider=provider, model="model", generated_text=text)


def _expected_reference(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


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
        stage = CreateSourceReference()
        assert stage.stage_id == "NORMALIZATION-0004"
        assert stage.stage_name == "Create Source Reference"
        assert stage.order == 4
        assert stage.enabled is True

    def test_documentation_reference_points_at_architecture(self) -> None:
        stage = CreateSourceReference()
        assert stage.metadata.documentation_reference is not None
        assert "normalization-assembly-contract" in (
            stage.metadata.documentation_reference
        )

    def test_no_injected_dependency(self) -> None:
        # Like 0002/0003, 0004 needs no collaborator — a no-arg constructor.
        assert CreateSourceReference() is not None


# ---------------------------------------------------------------------------
# Source reference creation — a fact about the original
# ---------------------------------------------------------------------------


class TestSourceReference:
    def test_records_content_addressed_reference(self) -> None:
        state = AssemblyState()
        CreateSourceReference().execute(_response("hello world"), state)
        assert state.source_reference == _expected_reference("hello world")
        assert state.source_reference_recorded is True

    def test_reference_is_not_the_generated_text(self) -> None:
        text = "the original response body"
        state = AssemblyState()
        CreateSourceReference().execute(_response(text), state)
        # A reference, never a copy: the text never appears in the reference.
        assert text not in state.source_reference
        assert state.source_reference.startswith("sha256:")

    def test_reference_is_deterministic(self) -> None:
        # Same generated_text -> same reference, every time (Stage Contract §4).
        first = AssemblyState()
        second = AssemblyState()
        CreateSourceReference().execute(_response("stable"), first)
        CreateSourceReference().execute(_response("stable"), second)
        assert first.source_reference == second.source_reference

    def test_different_text_yields_different_reference(self) -> None:
        a = AssemblyState()
        b = AssemblyState()
        CreateSourceReference().execute(_response("alpha"), a)
        CreateSourceReference().execute(_response("beta"), b)
        assert a.source_reference != b.source_reference

    def test_empty_response_still_yields_a_reference_not_an_exception(self) -> None:
        # Even an empty response has a well-defined, stable content reference.
        state = AssemblyState()
        CreateSourceReference().execute(_response(""), state)
        assert state.source_reference == _expected_reference("")
        assert state.source_reference_recorded is True

    def test_provider_independence(self) -> None:
        # The reference is a function of generated_text only — provider-agnostic.
        references = []
        for provider in ("gemini", "anthropic", "openai", "azure_openai"):
            state = AssemblyState()
            CreateSourceReference().execute(
                _response("same text", provider=provider), state
            )
            references.append(state.source_reference)
        assert len(set(references)) == 1  # identical across providers


# ---------------------------------------------------------------------------
# Ownership / immutability
# ---------------------------------------------------------------------------


class TestOwnership:
    def test_writes_only_the_source_reference(self) -> None:
        state = AssemblyState()
        CreateSourceReference().execute(_response("t"), state)
        # Source reference written; nothing else touched.
        assert state.source_reference_recorded is True
        assert state.normalized_structure is None
        assert state.normalized_structure_recorded is False
        assert state.normalization_outcome is None
        assert state.normalization_outcome_recorded is False
        assert state.observations == ()

    def test_does_not_modify_structure_outcome_or_observations(self) -> None:
        # Pre-seed the state as if 0001-0003 had run, then confirm 0004 leaves
        # every prior fact exactly as it was.
        state = AssemblyState()
        state.record_normalized_structure({"a": 1})
        state.record_normalization_outcome(NormalizationOutcome.NORMALIZED)

        CreateSourceReference().execute(_response("t"), state)

        assert state.normalized_structure == {"a": 1}
        assert state.normalization_outcome is NormalizationOutcome.NORMALIZED
        assert state.observations == ()

    def test_does_not_mutate_llm_response(self) -> None:
        response = _response("original")
        CreateSourceReference().execute(response, AssemblyState())
        assert response.generated_text == "original"

    def test_single_write_guard(self) -> None:
        state = AssemblyState()
        stage = CreateSourceReference()
        stage.execute(_response("t"), state)
        with pytest.raises(AssemblyStateError, match="already been recorded"):
            stage.execute(_response("t"), state)


# ---------------------------------------------------------------------------
# Stage independence — no ordering guard (independent of 0001-0003)
# ---------------------------------------------------------------------------


class TestIndependence:
    def test_runs_on_a_fresh_state_without_any_prior_fact(self) -> None:
        # 0004 depends on no earlier stage (Catalog §5): it succeeds even when
        # structure, outcome, and observations are all absent.
        state = AssemblyState()  # nothing recorded yet
        CreateSourceReference().execute(_response("t"), state)  # no raise
        assert state.source_reference_recorded is True


# ---------------------------------------------------------------------------
# End-to-end composition: 0001 -> 0002 -> 0003 -> 0004 through the coordinator
# ---------------------------------------------------------------------------


def _full_chain(structure: dict | None) -> list:
    return [
        RecoverCanonicalStructure(_FixedRecoverer(structure)),
        DetermineNormalizationOutcome(),
        CaptureNormalizationObservations(),
        CreateSourceReference(),
    ]


class TestComposition:
    def test_normalized_path(self) -> None:
        state = NormalizationStageCoordinator(_full_chain({"doc": {}})).coordinate(
            _response("payload"), lambda s: s
        )
        assert state.normalized_structure == {"doc": {}}
        assert state.normalization_outcome is NormalizationOutcome.NORMALIZED
        assert state.observations == ()
        assert state.source_reference == _expected_reference("payload")

    def test_malformed_path(self) -> None:
        state = NormalizationStageCoordinator(_full_chain(None)).coordinate(
            _response("payload"), lambda s: s
        )
        assert state.normalized_structure is None
        assert state.normalization_outcome is NormalizationOutcome.MALFORMED
        assert len(state.observations) == 1
        # The source reference is created regardless of the outcome — it references
        # the original, not the recovered structure.
        assert state.source_reference == _expected_reference("payload")

    def test_source_reference_extracted_via_consumer(self) -> None:
        reference = NormalizationStageCoordinator(_full_chain({"a": 1})).coordinate(
            _response("payload"), lambda s: s.source_reference
        )
        assert reference == _expected_reference("payload")
