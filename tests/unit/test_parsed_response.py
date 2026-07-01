"""Unit tests for the ParsedResponse Core Canonical Model.

Covers
------
* Construction, required/optional fields, and default values.
* Immutability (frozen) and strict construction (extra fields forbidden).
* camelCase serialisation aliases and round-trip.
* Field validation (outcome enum; structure/reference typing).
* Equality and backward compatibility (snake_case input, version default).
* Ownership: no forbidden information (execution / validation / provider /
  observation / statistics / framework / verdict) can be stored.
* Shared Platform Artifact semantics: a single immutable instance is shared and
  never mutated.

These tests run entirely in memory; no I/O, no parsing, no real responses.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.models import (
    PARSED_RESPONSE_VERSION,
    ParsedResponse,
)
from shared.enums.base import NormalizationOutcome

_STRUCTURE = {
    "executiveSummary": {"headline": "ok"},
    "requirements": [{"id": "R-1"}, {"id": "R-2"}],
    "risks": [],
}


def _normalized(**overrides: object) -> ParsedResponse:
    fields: dict[str, object] = {
        "normalization_outcome": NormalizationOutcome.NORMALIZED,
        "normalized_structure": dict(_STRUCTURE),
        "source_reference": "EX-77",
    }
    fields.update(overrides)
    return ParsedResponse(**fields)  # type: ignore[arg-type]


def _malformed(**overrides: object) -> ParsedResponse:
    fields: dict[str, object] = {"normalization_outcome": NormalizationOutcome.MALFORMED}
    fields.update(overrides)
    return ParsedResponse(**fields)  # type: ignore[arg-type]


@pytest.mark.unit
class TestConstruction:
    def test_normalized_construction(self) -> None:
        pr = _normalized()
        assert pr.normalization_outcome == NormalizationOutcome.NORMALIZED
        assert pr.normalized_structure == _STRUCTURE
        assert pr.source_reference == "EX-77"

    def test_malformed_has_no_structure(self) -> None:
        pr = _malformed()
        assert pr.normalization_outcome == NormalizationOutcome.MALFORMED
        assert pr.normalized_structure is None

    def test_outcome_is_required(self) -> None:
        with pytest.raises(ValidationError):
            ParsedResponse()  # type: ignore[call-arg]


@pytest.mark.unit
class TestDefaults:
    def test_version_defaults_to_constant(self) -> None:
        assert _malformed().parsed_response_version == PARSED_RESPONSE_VERSION

    def test_optional_fields_default(self) -> None:
        pr = _malformed()
        assert pr.normalized_structure is None
        assert pr.source_reference is None
        assert pr.metadata == {}

    def test_metadata_preserved_verbatim(self) -> None:
        pr = _malformed(metadata={"note": "kept"})
        assert pr.metadata == {"note": "kept"}


@pytest.mark.unit
class TestFieldValidation:
    def test_outcome_enum_coerces_from_value(self) -> None:
        pr = ParsedResponse(normalization_outcome="normalized")  # type: ignore[arg-type]
        assert pr.normalization_outcome == NormalizationOutcome.NORMALIZED

    def test_unknown_outcome_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ParsedResponse(normalization_outcome="partial")  # type: ignore[arg-type]

    def test_structure_must_be_object_not_scalar(self) -> None:
        with pytest.raises(ValidationError):
            _normalized(normalized_structure="not-a-dict")


@pytest.mark.unit
class TestImmutabilityAndStrictness:
    def test_is_frozen(self) -> None:
        pr = _normalized()
        with pytest.raises(ValidationError):
            pr.normalization_outcome = NormalizationOutcome.MALFORMED  # type: ignore[misc]

    def test_structure_cannot_be_reassigned(self) -> None:
        pr = _normalized()
        with pytest.raises(ValidationError):
            pr.normalized_structure = {}  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            _normalized(unexpected="x")  # type: ignore[call-arg]


@pytest.mark.unit
class TestOwnershipBoundaries:
    def test_owns_no_forbidden_information(self) -> None:
        # ParsedResponse owns ONLY the canonical representation. Every concern
        # below has a different owner and must never appear here.
        pr = _normalized()
        for forbidden in (
            # execution identity — NormalizationExecutionContext
            "normalization_id",
            "execution_id",
            "correlation_id",
            "started_at",
            # framework metadata — NormalizationFrameworkMetadata
            "framework_version",
            "pipeline_version",
            "responsibility_catalog_version",
            # statistics — NormalizationStatistics
            "normalization_duration_ms",
            "responsibilities_executed",
            # normalization observations — NormalizationResult (per this build)
            "observations",
            # validation — ValidationResult / ValidationIssue / ValidationSummary
            "overall_verdict",
            "verdict",
            "issues",
            "severity",
            "recommendation",
            # provider — LLMResponse
            "provider",
            "model",
            "raw_response",
            "finish_reason",
            "generated_text",
        ):
            assert not hasattr(pr, forbidden), forbidden

    def test_holds_reference_not_provider_text(self) -> None:
        # The source reference is a link, never a copy of the provider payload.
        pr = _normalized(source_reference="EX-77")
        assert pr.source_reference == "EX-77"
        assert not hasattr(pr, "generated_text")


@pytest.mark.unit
class TestSerialisation:
    def test_camelcase_aliases(self) -> None:
        dumped = _normalized().model_dump(by_alias=True)
        for key in (
            "parsedResponseVersion",
            "normalizationOutcome",
            "normalizedStructure",
            "sourceReference",
        ):
            assert key in dumped
        # Enum serialises by value.
        assert dumped["normalizationOutcome"] == "normalized"

    def test_round_trip_from_aliased_dump(self) -> None:
        original = _normalized(metadata={"k": "v"})
        restored = ParsedResponse.model_validate(original.model_dump(by_alias=True))
        assert restored == original

    def test_populate_by_name_accepts_snake_case(self) -> None:
        # Backward compatibility: snake_case input still validates.
        pr = ParsedResponse.model_validate(
            {
                "normalization_outcome": "malformed",
                "source_reference": "EX-9",
            }
        )
        assert pr.normalization_outcome == NormalizationOutcome.MALFORMED
        assert pr.source_reference == "EX-9"

    def test_version_absent_input_gets_default(self) -> None:
        # Backward compatibility: older payloads without the version validate.
        pr = ParsedResponse.model_validate({"normalization_outcome": "normalized"})
        assert pr.parsed_response_version == PARSED_RESPONSE_VERSION


@pytest.mark.unit
class TestEqualityAndSharing:
    def test_value_equality(self) -> None:
        assert _normalized() == _normalized()

    def test_inequality_on_outcome(self) -> None:
        assert _normalized() != _malformed()

    def test_shared_instance_is_immutable_across_consumers(self) -> None:
        # Shared Platform Artifact: one instance, read by many, mutated by none.
        shared = _normalized()
        first_reader = shared
        second_reader = shared
        assert first_reader is second_reader
        with pytest.raises(ValidationError):
            second_reader.source_reference = "tampered"  # type: ignore[misc]
        # The nested structure the instance exposes is unchanged for all readers.
        assert first_reader.normalized_structure == _STRUCTURE
