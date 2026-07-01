"""Unit tests for NORMALIZATION-0003 (Capture Normalization Observations).

Mirrors the NORMALIZATION-0001/0002 test style. Covers identity/metadata,
ownership (writes observations only), the malformed-representation observation on
an absent structure, zero observations on a recovered structure, facts-vs-
exceptions, provider independence, ``LLMResponse`` immutability, the ordering
guard, append discipline, and end-to-end composition with 0001 → 0002 → 0003
through the coordinator.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.models.normalization_observation import (
    OBSERVATION_MALFORMED_REPRESENTATION,
    NormalizationObservation,
)
from requirement_intelligence.normalization.response.assembly import (
    AssemblyState,
    CaptureNormalizationObservations,
    DetermineNormalizationOutcome,
    NormalizationStageCoordinator,
    ObservationCaptureError,
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


def _state_after_0001_0002(structure: dict | None) -> AssemblyState:
    """An Assembly State as if 0001 (structure) then 0002 (outcome) had both run."""
    state = _state_with_structure(structure)
    state.record_normalization_outcome(
        NormalizationOutcome.NORMALIZED
        if structure is not None
        else NormalizationOutcome.MALFORMED
    )
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
        stage = CaptureNormalizationObservations()
        assert stage.stage_id == "NORMALIZATION-0003"
        assert stage.stage_name == "Capture Normalization Observations"
        assert stage.order == 3
        assert stage.enabled is True

    def test_documentation_reference_points_at_architecture(self) -> None:
        stage = CaptureNormalizationObservations()
        assert stage.metadata.documentation_reference is not None
        assert "normalization-assembly-contract" in (
            stage.metadata.documentation_reference
        )

    def test_no_injected_dependency(self) -> None:
        # Like 0002, 0003 needs no collaborator — a no-arg constructor.
        assert CaptureNormalizationObservations() is not None


# ---------------------------------------------------------------------------
# Observation capture — facts about the run
# ---------------------------------------------------------------------------


class TestObservationCapture:
    def test_absent_structure_records_malformed_observation(self) -> None:
        state = _state_after_0001_0002(None)  # malformed
        CaptureNormalizationObservations().execute(_response(), state)

        assert len(state.observations) == 1
        obs = state.observations[0]
        assert obs.observation_type == OBSERVATION_MALFORMED_REPRESENTATION
        assert obs.observation_id == (
            f"NORMALIZATION-0003:{OBSERVATION_MALFORMED_REPRESENTATION}"
        )
        # Corroborating evidence is the determined outcome value — a fact.
        assert obs.evidence == NormalizationOutcome.MALFORMED.value

    def test_recovered_structure_records_zero_observations(self) -> None:
        # Nothing a structural view would lose is derivable from the recovered
        # structure alone at this stage — zero observations is a SUCCESS.
        state = _state_after_0001_0002({"doc": {"items": [1, 2]}})
        CaptureNormalizationObservations().execute(_response(), state)
        assert state.observations == ()

    def test_empty_structure_is_recovered_so_zero_observations(self) -> None:
        # An empty dict is a *recovered* (present) structure, not an absence.
        state = _state_after_0001_0002({})
        CaptureNormalizationObservations().execute(_response(), state)
        assert state.observations == ()

    def test_observation_is_a_fact_not_a_judgment(self) -> None:
        state = _state_after_0001_0002(None)
        CaptureNormalizationObservations().execute(_response(), state)
        obs = state.observations[0]
        # No severity, verdict, recommendation, or blocking indicator exists on the
        # model at all — an observation is a fact, never a judgment (Contract §10).
        assert not hasattr(obs, "severity")
        assert not hasattr(obs, "verdict")
        assert not hasattr(obs, "recommendation")
        assert not hasattr(obs, "blocking")

    def test_zero_observations_is_success_not_an_exception(self) -> None:
        # The NORMALIZED path records nothing and must not raise.
        state = _state_after_0001_0002({"a": 1})
        CaptureNormalizationObservations().execute(_response(), state)  # no raise
        assert state.observations == ()

    def test_malformed_observation_records_without_the_outcome_present(self) -> None:
        # 0003's decision derives from 0001's absent structure, not from 0002.
        # With only 0001 run (no outcome yet), it still records the fact, with no
        # evidence — never raising.
        state = _state_with_structure(None)  # 0001 only
        CaptureNormalizationObservations().execute(_response(), state)
        assert len(state.observations) == 1
        assert state.observations[0].evidence is None

    def test_provider_independence(self) -> None:
        for provider in ("gemini", "anthropic", "openai", "azure_openai"):
            state = _state_after_0001_0002(None)
            CaptureNormalizationObservations().execute(
                _response(provider=provider), state
            )
            assert len(state.observations) == 1
            assert state.observations[0].observation_type == (
                OBSERVATION_MALFORMED_REPRESENTATION
            )


# ---------------------------------------------------------------------------
# Ownership / immutability
# ---------------------------------------------------------------------------


class TestOwnership:
    def test_writes_only_observations(self) -> None:
        structure = None
        state = _state_after_0001_0002(structure)
        outcome_before = state.normalization_outcome
        CaptureNormalizationObservations().execute(_response(), state)
        # Observations written; every other fact untouched.
        assert len(state.observations) == 1
        assert state.normalized_structure == structure  # unchanged (absent)
        assert state.normalization_outcome is outcome_before  # unchanged
        assert state.source_reference is None
        assert state.source_reference_recorded is False

    def test_does_not_modify_structure(self) -> None:
        structure = {"a": 1}
        state = _state_after_0001_0002(structure)
        CaptureNormalizationObservations().execute(_response(), state)
        assert state.normalized_structure == {"a": 1}
        assert structure == {"a": 1}

    def test_does_not_modify_outcome(self) -> None:
        state = _state_after_0001_0002(None)
        CaptureNormalizationObservations().execute(_response(), state)
        assert state.normalization_outcome is NormalizationOutcome.MALFORMED

    def test_does_not_create_source_reference(self) -> None:
        state = _state_after_0001_0002(None)
        CaptureNormalizationObservations().execute(_response(), state)
        assert state.source_reference is None
        assert state.source_reference_recorded is False

    def test_does_not_assemble_parsed_response(self) -> None:
        # 0003 has no ParsedResponse to touch; it only ever appends observations.
        state = _state_after_0001_0002({"a": 1})
        result = CaptureNormalizationObservations().execute(_response(), state)
        assert result is None  # stages communicate via the Assembly State

    def test_does_not_mutate_llm_response(self) -> None:
        response = _response("original")
        CaptureNormalizationObservations().execute(
            response, _state_after_0001_0002(None)
        )
        assert response.generated_text == "original"


# ---------------------------------------------------------------------------
# Append discipline
# ---------------------------------------------------------------------------


class TestAppendDiscipline:
    def test_appends_without_disturbing_existing_observations(self) -> None:
        state = _state_after_0001_0002(None)
        preexisting = NormalizationObservation(
            observation_id="pre-1",
            observation_type="encoding_observation",
            detail="pre-existing fact",
            created_at=datetime(2026, 7, 1, tzinfo=UTC),
        )
        state.add_observation(preexisting)

        CaptureNormalizationObservations().execute(_response(), state)

        # The pre-existing observation is preserved; 0003 only appends.
        assert len(state.observations) == 2
        assert state.observations[0] is preexisting
        assert state.observations[1].observation_type == (
            OBSERVATION_MALFORMED_REPRESENTATION
        )

    def test_snapshot_is_an_immutable_tuple(self) -> None:
        state = _state_after_0001_0002(None)
        CaptureNormalizationObservations().execute(_response(), state)
        assert isinstance(state.observations, tuple)


# ---------------------------------------------------------------------------
# Ordering guard (infrastructure failure, not a fact)
# ---------------------------------------------------------------------------


class TestOrderingGuard:
    def test_raises_when_structure_not_recorded(self) -> None:
        # 0003 invoked before 0001 recorded a structure — a coordination error.
        state = AssemblyState()  # nothing recorded yet
        with pytest.raises(ObservationCaptureError, match="NORMALIZATION-0001"):
            CaptureNormalizationObservations().execute(_response(), state)

    def test_guard_records_no_observation(self) -> None:
        state = AssemblyState()
        with pytest.raises(ObservationCaptureError):
            CaptureNormalizationObservations().execute(_response(), state)
        assert state.observations == ()


# ---------------------------------------------------------------------------
# End-to-end composition: 0001 → 0002 → 0003 through the coordinator
# ---------------------------------------------------------------------------


class TestComposition:
    def test_normalized_chain_yields_no_observations(self) -> None:
        stages = [
            RecoverCanonicalStructure(_FixedRecoverer({"doc": {}})),
            DetermineNormalizationOutcome(),
            CaptureNormalizationObservations(),
        ]
        state = NormalizationStageCoordinator(stages).coordinate(
            _response(), lambda s: s
        )
        assert state.normalization_outcome is NormalizationOutcome.NORMALIZED
        assert state.observations == ()

    def test_malformed_chain_yields_one_malformed_observation(self) -> None:
        stages = [
            RecoverCanonicalStructure(_FixedRecoverer(None)),  # no structure
            DetermineNormalizationOutcome(),
            CaptureNormalizationObservations(),
        ]
        state = NormalizationStageCoordinator(stages).coordinate(
            _response(), lambda s: s
        )
        assert state.normalized_structure is None
        assert state.normalization_outcome is NormalizationOutcome.MALFORMED
        assert len(state.observations) == 1
        obs = state.observations[0]
        assert obs.observation_type == OBSERVATION_MALFORMED_REPRESENTATION
        assert obs.evidence == NormalizationOutcome.MALFORMED.value

    def test_chain_extracts_observations_for_the_result(self) -> None:
        # The coordinator's consumer is the in-boundary seam that hands the
        # observations to the NormalizationResult (0003 never touches the result).
        stages = [
            RecoverCanonicalStructure(_FixedRecoverer(None)),
            DetermineNormalizationOutcome(),
            CaptureNormalizationObservations(),
        ]
        observations = NormalizationStageCoordinator(stages).coordinate(
            _response(), lambda s: s.observations
        )
        assert len(observations) == 1
