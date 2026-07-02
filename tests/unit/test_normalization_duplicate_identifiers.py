"""Duplicate-identifier detection & emission — making SYNTAX-0002 operational.

Covers the additive, purely-additive enhancement that lets the Response
Normalization subsystem surface ``duplicate_identifier`` observations, and proves
SYNTAX-0002 now produces a ``ValidationIssue`` end to end:

* Recovery mechanism (JsonCanonicalStructureRecoverer):
  - duplicate keys detected; nested duplicates; duplicates at multiple levels;
  - duplicate-free JSON; malformed JSON; duplicate + malformed interaction;
  - recovered canonical structure unchanged (last-value-wins); deterministic.
* NORMALIZATION-0001: forwards duplicate facts as a transient execution fact
  (only when a structure was recovered and duplicates exist).
* NORMALIZATION-0003: emits ``duplicate_identifier`` observations from the
  forwarded facts; malformed observations unchanged; no observation when none.
* AssemblyState immutability of the transient snapshot.
* ResponseNormalizer integration (provider independence, end-to-end observations).
* Validation integration proving SYNTAX-0002 blocks on duplicates end to end.

Existing NORMALIZATION-0001/0002/0003 tests are untouched and continue to pass; the
enhancement is opt-in via an optional recovery-mechanism capability.
"""

from __future__ import annotations

from datetime import UTC, datetime

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
from requirement_intelligence.normalization.models.normalization_observation import (
    OBSERVATION_DUPLICATE_IDENTIFIER,
    OBSERVATION_MALFORMED_REPRESENTATION,
)
from requirement_intelligence.normalization.response import ResponseNormalizer
from requirement_intelligence.normalization.response.assembly import (
    AssemblyState,
    CaptureNormalizationObservations,
    DetermineNormalizationOutcome,
    NormalizationStageCoordinator,
    RecoverCanonicalStructure,
)
from requirement_intelligence.normalization.response.assembly.assembly_state import (
    DUPLICATE_IDENTIFIERS_METADATA_KEY,
)
from requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer import (
    DuplicateIdentifierReporter,
)
from requirement_intelligence.normalization.response.assembly.json_canonical_structure_recoverer import (  # noqa: E501
    JsonCanonicalStructureRecoverer,
)
from requirement_intelligence.validation import (
    ValidationConfiguration,
    ValidationInput,
    ValidationPipeline,
    ValidationRegistry,
    ValidationVerdict,
)
from requirement_intelligence.validation.response import ResponseValidator
from requirement_intelligence.validation.rules.syntax import DuplicateKeysRule

_TS = datetime(2026, 7, 2, 12, 0, 0, tzinfo=UTC)

_DUP = '{"a": 1, "a": 2}'
_DUP_NESTED = '{"outer": {"c": 1, "c": 2}}'
_DUP_MULTI_LEVEL = '{"a": 1, "a": 2, "b": {"c": 1, "c": 2}}'
_DUP_FREE = '{"a": 1, "b": {"c": 3}}'
_MALFORMED = "}{ not json"
_MALFORMED_WITH_DUP = '{"a": 1, "a": 2'  # duplicate-looking but unterminated → malformed


def _response(text: str, *, provider: str = "gemini") -> LLMResponse:
    return LLMResponse(provider=provider, model="model", generated_text=text)


def _analysis_result(text: str, execution_id: str = "EX-1") -> AnalysisResult:
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
        llm_response=_response(text),
    )


def _normalizer() -> ResponseNormalizer:
    registry = NormalizationRegistry()
    return ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )


# ---------------------------------------------------------------------------
# 1. Recovery mechanism — duplicate detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRecovererDuplicateDetection:
    def test_recoverer_is_a_duplicate_identifier_reporter(self) -> None:
        assert isinstance(JsonCanonicalStructureRecoverer(), DuplicateIdentifierReporter)

    def test_duplicate_keys_detected(self) -> None:
        assert JsonCanonicalStructureRecoverer().duplicate_identifiers(_DUP) == ("a",)

    def test_nested_duplicate_keys_detected(self) -> None:
        assert JsonCanonicalStructureRecoverer().duplicate_identifiers(_DUP_NESTED) == ("c",)

    def test_duplicate_keys_at_multiple_levels(self) -> None:
        duplicates = JsonCanonicalStructureRecoverer().duplicate_identifiers(_DUP_MULTI_LEVEL)
        # One entry per (object, duplicated-identifier); both levels reported.
        assert set(duplicates) == {"a", "c"}
        assert len(duplicates) == 2

    def test_repeated_identifier_reported_once_per_object(self) -> None:
        # Three occurrences of "a" in one object is one duplicated identifier.
        assert JsonCanonicalStructureRecoverer().duplicate_identifiers('{"a":1,"a":2,"a":3}') == (
            "a",
        )

    def test_duplicate_free_json_reports_nothing(self) -> None:
        assert JsonCanonicalStructureRecoverer().duplicate_identifiers(_DUP_FREE) == ()

    def test_malformed_json_reports_nothing(self) -> None:
        assert JsonCanonicalStructureRecoverer().duplicate_identifiers(_MALFORMED) == ()

    def test_duplicate_plus_malformed_interaction_reports_nothing(self) -> None:
        # Unparseable text has no recoverable object; duplicates are moot.
        assert JsonCanonicalStructureRecoverer().duplicate_identifiers(_MALFORMED_WITH_DUP) == ()

    def test_deterministic(self) -> None:
        recoverer = JsonCanonicalStructureRecoverer()
        first = recoverer.duplicate_identifiers(_DUP_MULTI_LEVEL)
        second = recoverer.duplicate_identifiers(_DUP_MULTI_LEVEL)
        assert first == second


# ---------------------------------------------------------------------------
# 2. Recovery mechanism — structure unchanged (recover() unaffected)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRecoveredStructureUnchanged:
    def test_recovered_structure_is_last_value_wins(self) -> None:
        # Identical to standard json.loads — duplicate detection does not alter it.
        assert JsonCanonicalStructureRecoverer().recover(_DUP) == {"a": 2}

    def test_recover_unaffected_for_duplicate_free(self) -> None:
        assert JsonCanonicalStructureRecoverer().recover(_DUP_FREE) == {"a": 1, "b": {"c": 3}}

    def test_recover_still_records_absence_for_malformed(self) -> None:
        assert JsonCanonicalStructureRecoverer().recover(_MALFORMED) is None


# ---------------------------------------------------------------------------
# 3. NORMALIZATION-0001 — forwards duplicate facts as a transient execution fact
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStage0001Forwarding:
    def _run(self, text: str) -> AssemblyState:
        state = AssemblyState()
        RecoverCanonicalStructure(JsonCanonicalStructureRecoverer()).execute(_response(text), state)
        return state

    def test_forwards_duplicate_facts(self) -> None:
        state = self._run(_DUP)
        assert state.internal_metadata[DUPLICATE_IDENTIFIERS_METADATA_KEY] == ("a",)

    def test_owned_structure_fact_unchanged(self) -> None:
        state = self._run(_DUP)
        assert state.normalized_structure == {"a": 2}
        assert state.normalized_structure_recorded is True

    def test_no_transient_fact_when_duplicate_free(self) -> None:
        state = self._run(_DUP_FREE)
        assert state.internal_metadata == {}

    def test_no_transient_fact_when_malformed(self) -> None:
        # Malformed → absent structure → no object → no duplicate facts forwarded.
        state = self._run(_MALFORMED)
        assert state.normalized_structure is None
        assert state.internal_metadata == {}


# ---------------------------------------------------------------------------
# 4. NORMALIZATION-0003 — emits duplicate observations from forwarded facts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStage0003Emission:
    def _state(self, *, structure: dict | None, duplicates: tuple[str, ...]) -> AssemblyState:
        state = AssemblyState()
        state.record_normalized_structure(structure)
        if duplicates:
            state.set_internal_metadata(DUPLICATE_IDENTIFIERS_METADATA_KEY, duplicates)
        return state

    def test_emits_one_observation_per_duplicate_fact(self) -> None:
        state = self._state(structure={"a": 2}, duplicates=("a", "c"))
        CaptureNormalizationObservations().execute(_response(_DUP), state)
        duplicate_obs = [
            o for o in state.observations if o.observation_type == OBSERVATION_DUPLICATE_IDENTIFIER
        ]
        assert len(duplicate_obs) == 2
        assert {o.location for o in duplicate_obs} == {"a", "c"}

    def test_duplicate_observation_is_a_fact(self) -> None:
        state = self._state(structure={"a": 2}, duplicates=("a",))
        CaptureNormalizationObservations().execute(_response(_DUP), state)
        obs = state.observations[0]
        assert obs.observation_type == OBSERVATION_DUPLICATE_IDENTIFIER
        assert not hasattr(obs, "severity")
        assert not hasattr(obs, "verdict")

    def test_no_duplicate_observation_when_no_facts(self) -> None:
        state = self._state(structure={"a": 1}, duplicates=())
        CaptureNormalizationObservations().execute(_response(_DUP_FREE), state)
        assert state.observations == ()

    def test_malformed_observation_unchanged(self) -> None:
        # Absent structure still yields exactly the malformed observation, as before.
        state = AssemblyState()
        state.record_normalized_structure(None)
        CaptureNormalizationObservations().execute(_response(_MALFORMED), state)
        assert len(state.observations) == 1
        assert state.observations[0].observation_type == OBSERVATION_MALFORMED_REPRESENTATION

    def test_deterministic_emission(self) -> None:
        first = self._state(structure={"a": 2}, duplicates=("a",))
        CaptureNormalizationObservations().execute(_response(_DUP), first)
        second = self._state(structure={"a": 2}, duplicates=("a",))
        CaptureNormalizationObservations().execute(_response(_DUP), second)
        assert [o.observation_type for o in first.observations] == [
            o.observation_type for o in second.observations
        ]


# ---------------------------------------------------------------------------
# 5. AssemblyState immutability of the transient snapshot
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAssemblyStateImmutability:
    def test_internal_metadata_snapshot_is_a_copy(self) -> None:
        state = AssemblyState()
        state.set_internal_metadata(DUPLICATE_IDENTIFIERS_METADATA_KEY, ("a",))
        snapshot = state.internal_metadata
        snapshot[DUPLICATE_IDENTIFIERS_METADATA_KEY] = ("mutated",)
        assert state.internal_metadata[DUPLICATE_IDENTIFIERS_METADATA_KEY] == ("a",)


# ---------------------------------------------------------------------------
# 6. Coordinated chain: 0001 → 0002 → 0003
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCoordinatedChain:
    def _observations(self, text: str) -> list[str]:
        stages = [
            RecoverCanonicalStructure(JsonCanonicalStructureRecoverer()),
            DetermineNormalizationOutcome(),
            CaptureNormalizationObservations(),
        ]
        state = NormalizationStageCoordinator(stages).coordinate(_response(text), lambda s: s)
        return [o.observation_type for o in state.observations]

    def test_duplicate_chain_yields_duplicate_observation(self) -> None:
        assert self._observations(_DUP) == [OBSERVATION_DUPLICATE_IDENTIFIER]

    def test_duplicate_free_chain_yields_no_observation(self) -> None:
        assert self._observations(_DUP_FREE) == []

    def test_malformed_chain_yields_only_malformed(self) -> None:
        assert self._observations(_MALFORMED) == [OBSERVATION_MALFORMED_REPRESENTATION]


# ---------------------------------------------------------------------------
# 7. ResponseNormalizer integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResponseNormalizerIntegration:
    def test_normalize_emits_duplicate_observation(self) -> None:
        result = _normalizer().normalize(_response(_DUP))
        types = [o.observation_type for o in result.observations]
        assert OBSERVATION_DUPLICATE_IDENTIFIER in types

    def test_normalize_duplicate_free_has_no_duplicate_observation(self) -> None:
        result = _normalizer().normalize(_response(_DUP_FREE))
        assert result.observations == ()

    def test_normalize_malformed_has_only_malformed(self) -> None:
        result = _normalizer().normalize(_response(_MALFORMED))
        types = [o.observation_type for o in result.observations]
        assert types == [OBSERVATION_MALFORMED_REPRESENTATION]

    def test_provider_independence(self) -> None:
        for provider in ("gemini", "anthropic", "openai", "azure_openai"):
            result = _normalizer().normalize(_response(_DUP, provider=provider))
            types = [o.observation_type for o in result.observations]
            assert OBSERVATION_DUPLICATE_IDENTIFIER in types

    def test_recovered_structure_unchanged_through_normalizer(self) -> None:
        result = _normalizer().normalize(_response(_DUP))
        assert result.parsed_response.normalized_structure == {"a": 2}


# ---------------------------------------------------------------------------
# 8. Validation integration — SYNTAX-0002 now operational end to end
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyntax0002EndToEnd:
    def _validate(self, text: str) -> object:
        analysis = _analysis_result(text)
        normalization_result = _normalizer().normalize(analysis.llm_response)
        validation_input = ValidationInput(
            analysis_result=analysis, normalization_result=normalization_result
        )
        registry = ValidationRegistry()
        registry.register(DuplicateKeysRule())
        validator = ResponseValidator(
            registry, ValidationPipeline(registry), ValidationConfiguration()
        )
        return validator.validate(validation_input)

    def test_duplicate_response_produces_validation_issue(self) -> None:
        result = self._validate(_DUP)
        assert result.overall_verdict == ValidationVerdict.BLOCKED
        assert [i.rule_id for i in result.validation_issues] == ["SYNTAX-0002"]

    def test_duplicate_free_response_passes(self) -> None:
        result = self._validate(_DUP_FREE)
        assert result.overall_verdict == ValidationVerdict.PASSED
        assert result.validation_summary.total_issues == 0
