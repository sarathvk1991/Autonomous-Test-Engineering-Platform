"""Unit tests for NORMALIZATION-0002 (Determine Normalization Outcome).

Mirrors the NORMALIZATION-0001 test style. Covers the outcome facts
(``NORMALIZED`` / ``MALFORMED``), the empty-vs-missing structure distinction,
provider independence, ownership (writes only the outcome), single-write, facts
vs. exceptions, the ordering guard, and end-to-end composition with 0001 through
the coordinator.
"""

from __future__ import annotations

import pytest

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.response.assembly import (
    AssemblyState,
    AssemblyStateError,
    DetermineNormalizationOutcome,
    NormalizationStageCoordinator,
    OutcomeDeterminationError,
    RecoverCanonicalStructure,
)
from shared.enums.base import NormalizationOutcome


def _response(text: str = "text", *, provider: str = "gemini") -> LLMResponse:
    return LLMResponse(provider=provider, model="model", generated_text=text)


def _state_with_structure(structure: dict | None) -> AssemblyState:
    """An Assembly State as if 0001 had recorded *structure* (present or absent)."""
    state = AssemblyState()
    state.record_normalized_structure(structure)
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
        stage = DetermineNormalizationOutcome()
        assert stage.stage_id == "NORMALIZATION-0002"
        assert stage.stage_name == "Determine Normalization Outcome"
        assert stage.order == 2
        assert stage.enabled is True

    def test_no_injected_dependency(self) -> None:
        # Unlike 0001, 0002 needs no collaborator — a no-arg constructor.
        assert DetermineNormalizationOutcome() is not None


# ---------------------------------------------------------------------------
# Outcome determination
# ---------------------------------------------------------------------------


class TestOutcome:
    def test_recovered_structure_is_normalized(self) -> None:
        state = _state_with_structure({"doc": {"items": [1, 2]}})
        DetermineNormalizationOutcome().execute(_response(), state)
        assert state.normalization_outcome is NormalizationOutcome.NORMALIZED

    def test_missing_structure_is_malformed(self) -> None:
        state = _state_with_structure(None)  # 0001 recorded an absence
        DetermineNormalizationOutcome().execute(_response(), state)
        assert state.normalization_outcome is NormalizationOutcome.MALFORMED

    def test_empty_structure_is_normalized_not_judged(self) -> None:
        # An empty dict is a *recovered* (present) structure — 0002 records
        # NORMALIZED. Whether the structure is "good enough" is validation's
        # concern, never 0002's.
        state = _state_with_structure({})
        DetermineNormalizationOutcome().execute(_response(), state)
        assert state.normalization_outcome is NormalizationOutcome.NORMALIZED

    def test_unexpected_structure_is_normalized_without_judgment(self) -> None:
        odd = {"unexpected": {"deeply": {"nested": [None, {"x": []}]}}}
        state = _state_with_structure(odd)
        DetermineNormalizationOutcome().execute(_response(), state)
        assert state.normalization_outcome is NormalizationOutcome.NORMALIZED

    def test_outcome_is_a_fact_not_an_exception(self) -> None:
        # Both NORMALIZED and MALFORMED are recorded, never raised.
        for structure, expected in (
            ({"a": 1}, NormalizationOutcome.NORMALIZED),
            (None, NormalizationOutcome.MALFORMED),
        ):
            state = _state_with_structure(structure)
            DetermineNormalizationOutcome().execute(_response(), state)
            assert state.normalization_outcome is expected

    def test_provider_independence(self) -> None:
        for provider in ("gemini", "anthropic", "openai", "azure_openai"):
            state = _state_with_structure({"a": 1})
            DetermineNormalizationOutcome().execute(
                _response(provider=provider), state
            )
            assert state.normalization_outcome is NormalizationOutcome.NORMALIZED


# ---------------------------------------------------------------------------
# Ownership / immutability
# ---------------------------------------------------------------------------


class TestOwnership:
    def test_writes_only_the_outcome_fact(self) -> None:
        structure = {"a": 1}
        state = _state_with_structure(structure)
        DetermineNormalizationOutcome().execute(_response(), state)
        # Outcome written; nothing else touched.
        assert state.normalization_outcome_recorded is True
        assert state.normalized_structure == structure  # unchanged
        assert state.source_reference is None
        assert state.source_reference_recorded is False
        assert state.observations == ()

    def test_no_downstream_writes(self) -> None:
        state = _state_with_structure({"a": 1})
        DetermineNormalizationOutcome().execute(_response(), state)
        assert state.observations == ()
        assert state.source_reference is None

    def test_does_not_mutate_llm_response(self) -> None:
        response = _response("original")
        DetermineNormalizationOutcome().execute(
            response, _state_with_structure({"a": 1})
        )
        assert response.generated_text == "original"

    def test_does_not_mutate_recovered_structure(self) -> None:
        structure = {"a": 1}
        state = _state_with_structure(structure)
        DetermineNormalizationOutcome().execute(_response(), state)
        assert structure == {"a": 1}

    def test_single_write_guard(self) -> None:
        state = _state_with_structure({"a": 1})
        stage = DetermineNormalizationOutcome()
        stage.execute(_response(), state)
        with pytest.raises(AssemblyStateError, match="already been recorded"):
            stage.execute(_response(), state)


# ---------------------------------------------------------------------------
# Ordering guard (infrastructure failure, not a fact)
# ---------------------------------------------------------------------------


class TestOrderingGuard:
    def test_raises_when_structure_not_recorded(self) -> None:
        # 0002 invoked before 0001 recorded a structure — a coordination error.
        state = AssemblyState()  # nothing recorded yet
        with pytest.raises(OutcomeDeterminationError, match="NORMALIZATION-0001"):
            DetermineNormalizationOutcome().execute(_response(), state)

    def test_guard_does_not_record_any_outcome(self) -> None:
        state = AssemblyState()
        with pytest.raises(OutcomeDeterminationError):
            DetermineNormalizationOutcome().execute(_response(), state)
        assert state.normalization_outcome_recorded is False


# ---------------------------------------------------------------------------
# End-to-end composition with 0001 through the coordinator
# ---------------------------------------------------------------------------


class TestComposition:
    def test_0001_then_0002_yields_normalized(self) -> None:
        stages = [
            RecoverCanonicalStructure(_FixedRecoverer({"doc": {}})),
            DetermineNormalizationOutcome(),
        ]
        outcome = NormalizationStageCoordinator(stages).coordinate(
            _response(), lambda s: s.normalization_outcome
        )
        assert outcome is NormalizationOutcome.NORMALIZED

    def test_0001_then_0002_yields_malformed(self) -> None:
        stages = [
            RecoverCanonicalStructure(_FixedRecoverer(None)),  # no structure
            DetermineNormalizationOutcome(),
        ]
        state = NormalizationStageCoordinator(stages).coordinate(
            _response(), lambda s: s
        )
        assert state.normalized_structure is None
        assert state.normalization_outcome is NormalizationOutcome.MALFORMED
