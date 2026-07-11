"""Unit tests for Grounding Framework typed identities and versions.

Covers determinism (pure-function ids), immutability, validation, type-safe
equality, and plain-string serialization.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import BaseModel

from requirement_intelligence.grounding.identity import (
    GroundedRequirementId,
    GroundingAssessmentId,
    GroundingConfigurationVersion,
    GroundingFrameworkVersion,
)
from requirement_intelligence.models.enums import SourceCategory


@pytest.mark.unit
class TestGroundedRequirementId:
    def test_is_deterministic_for_same_inputs(self) -> None:
        text = "The login page shall provide a mechanism to input a username."
        first = GroundedRequirementId.for_requirement(SourceCategory.FUNCTIONAL, text)
        second = GroundedRequirementId.for_requirement(SourceCategory.FUNCTIONAL, text)
        assert first == second
        assert str(first) == str(second)

    def test_normalises_whitespace_and_case(self) -> None:
        a = GroundedRequirementId.for_requirement(SourceCategory.SECURITY, "Set   nosniff HEADER")
        b = GroundedRequirementId.for_requirement(SourceCategory.SECURITY, "set nosniff header")
        assert a == b

    def test_domain_changes_the_id(self) -> None:
        text = "Same text, different domain."
        func = GroundedRequirementId.for_requirement(SourceCategory.FUNCTIONAL, text)
        qual = GroundedRequirementId.for_requirement(SourceCategory.QUALITY, text)
        assert func != qual

    def test_id_shape_is_slug_safe(self) -> None:
        rid = GroundedRequirementId.for_requirement(SourceCategory.QUALITY, "Adhere to naming.")
        assert str(rid).startswith("req-quality-")

    def test_empty_text_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            GroundedRequirementId.for_requirement(SourceCategory.FUNCTIONAL, "   ")

    def test_is_immutable(self) -> None:
        rid = GroundedRequirementId.for_requirement(SourceCategory.FUNCTIONAL, "text")
        with pytest.raises(FrozenInstanceError):
            rid.value = "req-functional-deadbeefdead"  # type: ignore[misc]

    def test_rejects_malformed_value(self) -> None:
        with pytest.raises(ValueError):
            GroundedRequirementId("Req With Spaces")


@pytest.mark.unit
class TestGroundingAssessmentId:
    def test_is_deterministic(self) -> None:
        a = GroundingAssessmentId.for_run("ctx-authentication-abc123", "content")
        b = GroundingAssessmentId.for_run("ctx-authentication-abc123", "content")
        assert a == b
        assert str(a).startswith("grnd-ctx-authentication-abc123-")

    def test_content_changes_the_id(self) -> None:
        a = GroundingAssessmentId.for_run("ctx-x", "one")
        b = GroundingAssessmentId.for_run("ctx-x", "two")
        assert a != b

    def test_empty_context_rejected(self) -> None:
        with pytest.raises(ValueError):
            GroundingAssessmentId.for_run("  ", "content")


@pytest.mark.unit
class TestGroundingVersions:
    def test_parse_and_str_round_trip(self) -> None:
        assert str(GroundingFrameworkVersion.parse("1.2.3")) == "1.2.3"

    def test_ordering(self) -> None:
        assert GroundingFrameworkVersion(1, 0, 0) < GroundingFrameworkVersion(1, 1, 0)

    def test_compatibility_is_major_equality(self) -> None:
        assert GroundingFrameworkVersion(1, 0, 0).is_compatible_with(
            GroundingFrameworkVersion(1, 9, 9)
        )
        assert not GroundingFrameworkVersion(2, 0, 0).is_compatible_with(
            GroundingFrameworkVersion(1, 0, 0)
        )

    def test_negative_component_rejected(self) -> None:
        with pytest.raises(ValueError):
            GroundingConfigurationVersion(-1, 0, 0)

    def test_type_safe_equality(self) -> None:
        # Same numbers, different identifier types must never compare equal.
        assert GroundingFrameworkVersion(1, 0, 0) != GroundingConfigurationVersion(1, 0, 0)

    def test_bad_string_rejected(self) -> None:
        with pytest.raises(ValueError):
            GroundingFrameworkVersion.parse("1.0")


@pytest.mark.unit
class TestIdentitySerialization:
    def test_ids_serialise_to_plain_strings(self) -> None:
        class Holder(BaseModel):
            rid: GroundedRequirementId
            version: GroundingFrameworkVersion

        rid = GroundedRequirementId.for_requirement(SourceCategory.FUNCTIONAL, "text")
        holder = Holder(rid=rid, version=GroundingFrameworkVersion(1, 0, 0))
        dumped = holder.model_dump(mode="json")
        assert dumped == {"rid": str(rid), "version": "1.0.0"}
        assert Holder.model_validate(dumped) == holder
