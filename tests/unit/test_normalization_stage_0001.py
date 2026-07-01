"""Unit tests for the internal normalization-stage layer and NORMALIZATION-0001.

Covers
------
* NormalizationStageMetadata — immutability, defaults, equality, read-through.
* NormalizationStage — abstract; convenience wrappers read from metadata.
* AssemblyState — single-write discipline, ownership, snapshots.
* RecoverCanonicalStructure (NORMALIZATION-0001) — normal / empty / malformed /
  unexpected recovery, provider & format independence, immutability, ownership,
  exception translation, no duplicate writes, no downstream effects.

Design constraints
------------------
* No real parsing — recovery is exercised through injected test-double recoverers,
  which is exactly what proves the stage is provider- and format-independent.
* No ParsedResponse, no observation, no outcome is ever created by 0001.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from typing import Any

import pytest

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.models.normalization_observation import (
    NormalizationObservation,
)
from requirement_intelligence.normalization.response.assembly import (
    DEFAULT_STAGE_ORDER,
    DEFAULT_STAGE_VERSION,
    AssemblyState,
    AssemblyStateError,
    NormalizationStage,
    NormalizationStageMetadata,
    RecoverCanonicalStructure,
    StructureRecoveryError,
)
from shared.enums.base import NormalizationOutcome

_TS = datetime(2026, 7, 1, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FixedRecoverer:
    """A recoverer that returns a fixed structure and records the text it saw."""

    def __init__(self, structure: dict[str, Any] | None) -> None:
        self._structure = structure
        self.seen_text: str | None = None
        self.calls = 0

    def recover(self, text: str) -> dict[str, Any] | None:
        self.calls += 1
        self.seen_text = text
        return self._structure


class _RaisingRecoverer:
    """A recoverer whose mechanism fails for an infrastructure reason."""

    def recover(self, text: str) -> dict[str, Any] | None:
        raise RuntimeError("recovery mechanism exploded")


def _response(text: str, *, provider: str = "gemini") -> LLMResponse:
    return LLMResponse(provider=provider, model="model", generated_text=text)


# ---------------------------------------------------------------------------
# NormalizationStageMetadata
# ---------------------------------------------------------------------------


class TestNormalizationStageMetadata:
    def _meta(self, **overrides: object) -> NormalizationStageMetadata:
        kwargs: dict[str, object] = {
            "stage_id": "NORMALIZATION-0001",
            "stage_name": "Recover Canonical Structure",
        }
        kwargs.update(overrides)
        return NormalizationStageMetadata(**kwargs)  # type: ignore[arg-type]

    def test_is_frozen(self) -> None:
        meta = self._meta()
        with pytest.raises(dataclasses.FrozenInstanceError):
            meta.stage_id = "other"  # type: ignore[misc]

    def test_defaults(self) -> None:
        meta = self._meta()
        assert meta.stage_version == DEFAULT_STAGE_VERSION
        assert meta.order == DEFAULT_STAGE_ORDER
        assert meta.enabled is True
        assert meta.tags == ()
        assert meta.documentation_reference is None
        assert meta.responsibility_catalog_version is None

    def test_all_fields_set(self) -> None:
        meta = self._meta(
            stage_version="2.0.0",
            order=1,
            enabled=False,
            tags=("structure",),
            documentation_reference="doc",
            responsibility_catalog_version="1.0.0",
        )
        assert meta.stage_version == "2.0.0"
        assert meta.order == 1
        assert meta.enabled is False
        assert meta.tags == ("structure",)
        assert meta.documentation_reference == "doc"
        assert meta.responsibility_catalog_version == "1.0.0"

    def test_value_equality(self) -> None:
        assert self._meta(order=1) == self._meta(order=1)
        assert self._meta(order=1) != self._meta(order=2)


# ---------------------------------------------------------------------------
# NormalizationStage — abstract contract
# ---------------------------------------------------------------------------


class TestNormalizationStage:
    def test_cannot_instantiate_abstract_base(self) -> None:
        with pytest.raises(TypeError):
            NormalizationStage()  # type: ignore[abstract]

    def test_convenience_wrappers_read_metadata(self) -> None:
        stage = RecoverCanonicalStructure(_FixedRecoverer({"a": 1}))
        assert stage.stage_id == "NORMALIZATION-0001"
        assert stage.stage_name == "Recover Canonical Structure"
        assert stage.stage_version == DEFAULT_STAGE_VERSION
        assert stage.order == 1
        assert stage.enabled is True
        assert stage.stage_id == stage.metadata.stage_id


# ---------------------------------------------------------------------------
# AssemblyState — single-write discipline and ownership
# ---------------------------------------------------------------------------


class TestAssemblyState:
    def test_starts_empty(self) -> None:
        state = AssemblyState()
        assert state.normalized_structure is None
        assert state.normalized_structure_recorded is False
        assert state.normalization_outcome is None
        assert state.normalization_outcome_recorded is False
        assert state.source_reference is None
        assert state.source_reference_recorded is False
        assert state.observations == ()
        assert state.internal_metadata == {}

    def test_record_structure_once(self) -> None:
        state = AssemblyState()
        state.record_normalized_structure({"a": 1})
        assert state.normalized_structure == {"a": 1}
        assert state.normalized_structure_recorded is True

    def test_record_structure_absence_is_a_fact(self) -> None:
        state = AssemblyState()
        state.record_normalized_structure(None)
        assert state.normalized_structure is None
        assert state.normalized_structure_recorded is True  # recorded, not "unset"

    def test_duplicate_structure_write_raises(self) -> None:
        state = AssemblyState()
        state.record_normalized_structure({"a": 1})
        with pytest.raises(AssemblyStateError, match="already been recorded"):
            state.record_normalized_structure({"b": 2})

    def test_record_outcome_once_and_guard(self) -> None:
        state = AssemblyState()
        state.record_normalization_outcome(NormalizationOutcome.NORMALIZED)
        assert state.normalization_outcome is NormalizationOutcome.NORMALIZED
        assert state.normalization_outcome_recorded is True
        with pytest.raises(AssemblyStateError, match="already been recorded"):
            state.record_normalization_outcome(NormalizationOutcome.MALFORMED)

    def test_record_source_reference_once_and_guard(self) -> None:
        state = AssemblyState()
        state.record_source_reference("ref-1")
        assert state.source_reference == "ref-1"
        assert state.source_reference_recorded is True
        with pytest.raises(AssemblyStateError, match="already been recorded"):
            state.record_source_reference("ref-2")

    def test_observations_append_only_and_snapshot_immutable(self) -> None:
        state = AssemblyState()
        obs = NormalizationObservation(
            observation_id="o1",
            observation_type="duplicate_identifier",
            detail="fact",
            created_at=_TS,
        )
        state.add_observation(obs)
        snapshot = state.observations
        assert snapshot == (obs,)
        # Mutating the snapshot never affects the state.
        assert isinstance(snapshot, tuple)
        state.add_observation(obs)
        assert len(state.observations) == 2

    def test_internal_metadata_snapshot_is_a_copy(self) -> None:
        state = AssemblyState()
        state.set_internal_metadata("k", "v")
        snap = state.internal_metadata
        snap["k"] = "mutated"
        assert state.internal_metadata == {"k": "v"}


# ---------------------------------------------------------------------------
# NORMALIZATION-0001 — Recover Canonical Structure
# ---------------------------------------------------------------------------


class TestRecoverCanonicalStructure:
    def test_construction_requires_a_recoverer(self) -> None:
        with pytest.raises(StructureRecoveryError, match="CanonicalStructureRecoverer"):
            RecoverCanonicalStructure(object())  # type: ignore[arg-type]

    def test_identity(self) -> None:
        stage = RecoverCanonicalStructure(_FixedRecoverer(None))
        assert stage.stage_id == "NORMALIZATION-0001"
        assert stage.stage_name == "Recover Canonical Structure"
        assert stage.order == 1
        assert stage.enabled is True

    def test_normal_execution_records_recovered_structure(self) -> None:
        recoverer = _FixedRecoverer({"summary": {"title": "x"}, "items": [1, 2]})
        stage = RecoverCanonicalStructure(recoverer)
        state = AssemblyState()

        result = stage.execute(_response("<any representation>"), state)

        assert result is None  # stages communicate via the Assembly State
        assert recoverer.calls == 1
        assert recoverer.seen_text == "<any representation>"
        assert state.normalized_structure == {"summary": {"title": "x"}, "items": [1, 2]}
        assert state.normalized_structure_recorded is True

    def test_empty_response_records_absence_not_exception(self) -> None:
        recoverer = _FixedRecoverer(None)
        stage = RecoverCanonicalStructure(recoverer)
        state = AssemblyState()

        stage.execute(_response(""), state)

        assert recoverer.seen_text == ""
        assert state.normalized_structure is None
        assert state.normalized_structure_recorded is True  # absence is a fact

    def test_malformed_response_records_absence(self) -> None:
        # A recoverer returning None models "no well-formed structure" — a FACT.
        stage = RecoverCanonicalStructure(_FixedRecoverer(None))
        state = AssemblyState()
        stage.execute(_response("!!! not well-formed !!!"), state)
        assert state.normalized_structure is None
        assert state.normalized_structure_recorded is True

    def test_unexpected_structure_is_recorded_verbatim_without_judgment(self) -> None:
        # The stage records whatever structure is present; it never judges it.
        odd = {"unexpected": {"deeply": {"nested": [None, {"x": []}]}}}
        stage = RecoverCanonicalStructure(_FixedRecoverer(odd))
        state = AssemblyState()
        stage.execute(_response("weird"), state)
        assert state.normalized_structure == odd

    def test_provider_independence(self) -> None:
        structure = {"a": 1}
        stage = RecoverCanonicalStructure(_FixedRecoverer(structure))
        for provider in ("gemini", "anthropic", "openai", "azure_openai"):
            state = AssemblyState()
            stage.execute(_response("text", provider=provider), state)
            assert state.normalized_structure == structure

    def test_format_independence_via_injected_recoverers(self) -> None:
        # The same canonical structure recovered from two different "formats" by two
        # different recoverers — the stage is identical; only the injected mechanism
        # differs. This is exactly why the stage hardcodes no format.
        canonical = {"doc": {"kind": "requirements"}}
        for text in ('{"json": true}', "<xml/>", "# markdown"):
            state = AssemblyState()
            RecoverCanonicalStructure(_FixedRecoverer(canonical)).execute(
                _response(text), state
            )
            assert state.normalized_structure == canonical

    def test_does_not_mutate_llm_response(self) -> None:
        response = _response("original text")
        RecoverCanonicalStructure(_FixedRecoverer({"a": 1})).execute(
            response, AssemblyState()
        )
        assert response.generated_text == "original text"

    def test_writes_only_the_structure_fact(self) -> None:
        # Ownership: 0001 writes structure and NOTHING else.
        state = AssemblyState()
        RecoverCanonicalStructure(_FixedRecoverer({"a": 1})).execute(
            _response("t"), state
        )
        assert state.normalized_structure_recorded is True
        assert state.normalization_outcome is None
        assert state.normalization_outcome_recorded is False
        assert state.source_reference is None
        assert state.source_reference_recorded is False
        assert state.observations == ()

    def test_no_downstream_effects(self) -> None:
        # 0001 creates no outcome, no observation, no source reference — and
        # certainly no ParsedResponse (it has no way to; it only touches structure).
        state = AssemblyState()
        RecoverCanonicalStructure(_FixedRecoverer({"a": 1})).execute(
            _response("t"), state
        )
        assert state.observations == ()
        assert state.normalization_outcome is None
        assert state.source_reference is None

    def test_infrastructure_failure_is_translated_and_structure_not_recorded(
        self,
    ) -> None:
        stage = RecoverCanonicalStructure(_RaisingRecoverer())
        state = AssemblyState()
        with pytest.raises(StructureRecoveryError, match="recovery failed"):
            stage.execute(_response("t"), state)
        # On infrastructure failure, no fact is recorded.
        assert state.normalized_structure_recorded is False

    def test_no_duplicate_writes_when_executed_twice(self) -> None:
        stage = RecoverCanonicalStructure(_FixedRecoverer({"a": 1}))
        state = AssemblyState()
        stage.execute(_response("t"), state)
        with pytest.raises(AssemblyStateError, match="already been recorded"):
            stage.execute(_response("t"), state)
