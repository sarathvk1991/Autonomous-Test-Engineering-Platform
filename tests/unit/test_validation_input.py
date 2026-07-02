"""Unit tests for the ValidationInput Core Canonical Model (ADR-0003).

Covers
------
* Construction & version — the model builds and stamps its shape version.
* Ownership — it references, and never copies, the AnalysisResult and the
  NormalizationResult (identity preserved).
* Reachability — the shared ParsedResponse and the observations are reachable
  through the NormalizationResult, not duplicated on the ValidationInput.
* Execution integrity — the same-execution binding invariant (ADR-0003 §6):
  a matching correlation binds; a mismatched correlation is rejected; an absent
  correlation is tolerated.
* Immutability — the aggregate is frozen; it cannot be rebound or mutated.
* Strict mode — unknown fields are rejected.
* Metadata — free-form metadata is carried verbatim and defaults independently.

Design constraints
------------------
* No mocking of the normalizer; a real ``ResponseNormalizer`` produces a real
  ``NormalizationResult`` (and therefore a real ``ParsedResponse``), mirroring the
  handoff seam exactly.
* No real AI provider calls; inputs are built in-memory.
"""

from __future__ import annotations

from datetime import UTC, datetime

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
from requirement_intelligence.normalization.models.normalization_result import (
    NormalizationResult,
)
from requirement_intelligence.normalization.response import ResponseNormalizer
from requirement_intelligence.validation import VALIDATION_INPUT_VERSION, ValidationInput
from shared.enums.base import NormalizationOutcome

_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)
_JSON = '{"doc": {"items": [1, 2]}, "summary": "s"}'


def _analysis_result(execution_id: str = "EX-1", generated_text: str = _JSON) -> AnalysisResult:
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
        llm_response=LLMResponse(provider="gemini", model="model", generated_text=generated_text),
    )


def _normalization_result(analysis: AnalysisResult) -> NormalizationResult:
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return normalizer.normalize(analysis.llm_response)


# ---------------------------------------------------------------------------
# 1. Construction & version
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConstruction:
    def test_builds_from_analysis_and_normalization(self) -> None:
        analysis = _analysis_result()
        vi = ValidationInput(
            analysis_result=analysis,
            normalization_result=_normalization_result(analysis),
        )
        assert isinstance(vi, ValidationInput)

    def test_stamps_shape_version(self) -> None:
        analysis = _analysis_result()
        vi = ValidationInput(
            analysis_result=analysis,
            normalization_result=_normalization_result(analysis),
        )
        assert vi.validation_input_version == VALIDATION_INPUT_VERSION

    def test_camel_case_serialization(self) -> None:
        analysis = _analysis_result()
        vi = ValidationInput(
            analysis_result=analysis,
            normalization_result=_normalization_result(analysis),
        )
        keys = set(vi.model_dump(by_alias=True).keys())
        expected = {"validationInputVersion", "analysisResult", "normalizationResult", "metadata"}
        assert expected <= keys


# ---------------------------------------------------------------------------
# 2. Ownership — references, never copies
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOwnership:
    def test_analysis_result_is_referenced_not_copied(self) -> None:
        analysis = _analysis_result()
        nr = _normalization_result(analysis)
        vi = ValidationInput(analysis_result=analysis, normalization_result=nr)
        assert vi.analysis_result is analysis

    def test_normalization_result_is_referenced_not_copied(self) -> None:
        analysis = _analysis_result()
        nr = _normalization_result(analysis)
        vi = ValidationInput(analysis_result=analysis, normalization_result=nr)
        assert vi.normalization_result is nr

    def test_owns_only_the_binding(self) -> None:
        # The ValidationInput exposes exactly the binding + version + metadata —
        # it never grows a copy of the ParsedResponse or the observations.
        analysis = _analysis_result()
        vi = ValidationInput(
            analysis_result=analysis, normalization_result=_normalization_result(analysis)
        )
        assert set(vi.model_dump().keys()) == {
            "validation_input_version",
            "analysis_result",
            "normalization_result",
            "metadata",
        }


# ---------------------------------------------------------------------------
# 3. Reachability — ParsedResponse & observations via the NormalizationResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReachability:
    def test_parsed_response_reachable_via_normalization_result(self) -> None:
        analysis = _analysis_result()
        nr = _normalization_result(analysis)
        vi = ValidationInput(analysis_result=analysis, normalization_result=nr)
        parsed = vi.normalization_result.parsed_response
        # The shared ParsedResponse is the exact instance the NormalizationResult owns.
        assert parsed is nr.parsed_response
        assert parsed.normalization_outcome == NormalizationOutcome.NORMALIZED

    def test_syntax_outcome_readable(self) -> None:
        # SYNTAX-0001 reads the Normalization Outcome (a fact, not a verdict).
        analysis = _analysis_result(generated_text="}{ not json")
        vi = ValidationInput(
            analysis_result=analysis, normalization_result=_normalization_result(analysis)
        )
        assert vi.normalization_result.parsed_response.normalization_outcome == (
            NormalizationOutcome.MALFORMED
        )

    def test_observations_reachable_via_normalization_result(self) -> None:
        # SYNTAX-0002 / SYNTAX-0003 read observations from the NormalizationResult —
        # never from the ParsedResponse (single-owner rule).
        analysis = _analysis_result()
        nr = _normalization_result(analysis)
        vi = ValidationInput(analysis_result=analysis, normalization_result=nr)
        assert vi.normalization_result.observations is nr.observations
        assert isinstance(vi.normalization_result.observations, tuple)


# ---------------------------------------------------------------------------
# 4. Execution integrity — same-execution binding (ADR-0003 §6)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExecutionIntegrity:
    def test_matching_correlation_binds(self) -> None:
        analysis = _analysis_result(execution_id="EX-42")
        nr = _normalization_result(analysis).model_copy(update={"correlation_id": "EX-42"})
        vi = ValidationInput(analysis_result=analysis, normalization_result=nr)
        assert vi.normalization_result.correlation_id == "EX-42"

    def test_mismatched_correlation_is_rejected(self) -> None:
        analysis = _analysis_result(execution_id="EX-1")
        nr = _normalization_result(analysis).model_copy(update={"correlation_id": "OTHER"})
        with pytest.raises(ValidationError, match="same execution"):
            ValidationInput(analysis_result=analysis, normalization_result=nr)

    def test_absent_correlation_is_tolerated(self) -> None:
        # normalize() sets no correlation; the seam owns correlation when present.
        analysis = _analysis_result(execution_id="EX-1")
        nr = _normalization_result(analysis)
        assert nr.correlation_id is None
        vi = ValidationInput(analysis_result=analysis, normalization_result=nr)
        assert vi.analysis_result.execution_id == "EX-1"


# ---------------------------------------------------------------------------
# 5. Immutability & strict mode
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImmutability:
    def test_cannot_rebind_analysis_result(self) -> None:
        analysis = _analysis_result()
        vi = ValidationInput(
            analysis_result=analysis, normalization_result=_normalization_result(analysis)
        )
        with pytest.raises(ValidationError):
            vi.analysis_result = _analysis_result("EX-9")  # type: ignore[misc]

    def test_cannot_rebind_normalization_result(self) -> None:
        analysis = _analysis_result()
        vi = ValidationInput(
            analysis_result=analysis, normalization_result=_normalization_result(analysis)
        )
        with pytest.raises(ValidationError):
            vi.normalization_result = _normalization_result(analysis)  # type: ignore[misc]

    def test_cannot_mutate_metadata_attribute(self) -> None:
        analysis = _analysis_result()
        vi = ValidationInput(
            analysis_result=analysis, normalization_result=_normalization_result(analysis)
        )
        with pytest.raises(ValidationError):
            vi.metadata = {"x": 1}  # type: ignore[misc]

    def test_rejects_unknown_fields(self) -> None:
        analysis = _analysis_result()
        with pytest.raises(ValidationError):
            ValidationInput(
                analysis_result=analysis,
                normalization_result=_normalization_result(analysis),
                surprise="nope",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# 6. Metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetadata:
    def test_metadata_defaults_empty(self) -> None:
        analysis = _analysis_result()
        vi = ValidationInput(
            analysis_result=analysis, normalization_result=_normalization_result(analysis)
        )
        assert vi.metadata == {}

    def test_metadata_carried_verbatim(self) -> None:
        analysis = _analysis_result()
        vi = ValidationInput(
            analysis_result=analysis,
            normalization_result=_normalization_result(analysis),
            metadata={"trace": "abc"},
        )
        assert vi.metadata == {"trace": "abc"}

    def test_metadata_instances_are_independent(self) -> None:
        analysis = _analysis_result()
        first = ValidationInput(
            analysis_result=analysis, normalization_result=_normalization_result(analysis)
        )
        second = ValidationInput(
            analysis_result=analysis, normalization_result=_normalization_result(analysis)
        )
        assert first.metadata is not second.metadata
