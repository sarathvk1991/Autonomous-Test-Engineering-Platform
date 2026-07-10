"""Unit tests for the Engineering Context Orchestration identity value objects.

Covers the four guarantees the identity model exists to provide: immutability,
well-defined (type-safe) equality, validation at construction, and plain-string
serialization that keeps the platform's JSON contract shape unchanged.
"""

from __future__ import annotations

import dataclasses

import pytest
from pydantic import ValidationError

from requirement_intelligence.context_orchestration.models.context_identity import (
    EngineeringContextId,
    OrchestrationPolicyId,
    PolicyVersion,
)
from shared.contracts.base import Schema

_ID_TYPES = (EngineeringContextId, OrchestrationPolicyId)


class _IdHolder(Schema):
    """Minimal model used to exercise pydantic integration."""

    context_id: EngineeringContextId
    policy_id: OrchestrationPolicyId
    policy_version: PolicyVersion


# ---------------------------------------------------------------------------
# Construction & validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("id_type", _ID_TYPES)
@pytest.mark.parametrize("value", ["coverage", "ctx-auth-4f2a1c9b7e05", "a", "a.b:c_d-e", "x9"])
def test_valid_identifier_round_trips(id_type: type, value: str) -> None:
    assert str(id_type(value)) == value
    assert id_type.parse(value) == id_type(value)


@pytest.mark.unit
@pytest.mark.parametrize("id_type", _ID_TYPES)
@pytest.mark.parametrize(
    "value",
    ["", " ", "Ctx-Auth", "has space", "-leading", "trailing-", "under_score-", "emoji-✨"],
)
def test_invalid_identifier_rejected(id_type: type, value: str) -> None:
    with pytest.raises(ValueError):
        id_type(value)


@pytest.mark.unit
@pytest.mark.parametrize("id_type", _ID_TYPES)
def test_parse_strips_surrounding_whitespace(id_type: type) -> None:
    assert id_type.parse("  coverage  ") == id_type("coverage")


@pytest.mark.unit
@pytest.mark.parametrize("id_type", _ID_TYPES)
def test_parse_rejects_non_string(id_type: type) -> None:
    with pytest.raises(ValueError):
        id_type.parse(7)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Immutability & equality
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("id_type", _ID_TYPES)
def test_identifier_is_immutable(id_type: type) -> None:
    identifier = id_type("coverage")
    with pytest.raises(dataclasses.FrozenInstanceError):
        identifier.value = "other"  # type: ignore[misc]


@pytest.mark.unit
@pytest.mark.parametrize("id_type", _ID_TYPES)
def test_identifier_is_hashable(id_type: type) -> None:
    assert len({id_type("a"), id_type("a"), id_type("b")}) == 2


@pytest.mark.unit
def test_equality_is_type_safe_across_identifier_types() -> None:
    """The whole point of typing: an id of one kind never equals another kind."""
    assert EngineeringContextId("x") != OrchestrationPolicyId("x")
    assert EngineeringContextId("x") == EngineeringContextId("x")
    assert OrchestrationPolicyId("x") == OrchestrationPolicyId("x")


@pytest.mark.unit
def test_distinct_identifier_types_do_not_collide_in_a_set() -> None:
    assert len({EngineeringContextId("x"), OrchestrationPolicyId("x")}) == 2


# ---------------------------------------------------------------------------
# PolicyVersion
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_policy_version_parses_and_round_trips() -> None:
    version = PolicyVersion.parse(" 1.2.3 ")
    assert (version.major, version.minor, version.patch) == (1, 2, 3)
    assert str(version) == "1.2.3"


@pytest.mark.unit
@pytest.mark.parametrize("raw", ["1.0", "1.0.0.0", "v1.0.0", "1.0.x", "", "-1.0.0"])
def test_policy_version_rejects_malformed(raw: str) -> None:
    with pytest.raises(ValueError):
        PolicyVersion.parse(raw)


@pytest.mark.unit
def test_policy_version_rejects_negative_components() -> None:
    with pytest.raises(ValueError):
        PolicyVersion(-1, 0, 0)


@pytest.mark.unit
def test_policy_version_is_ordered() -> None:
    assert PolicyVersion(1, 0, 0) < PolicyVersion(1, 1, 0) < PolicyVersion(2, 0, 0)


@pytest.mark.unit
def test_policy_version_compatibility_is_major_version_equality() -> None:
    assert PolicyVersion(1, 9, 9).is_compatible_with(PolicyVersion(1, 0, 0))
    assert not PolicyVersion(2, 0, 0).is_compatible_with(PolicyVersion(1, 0, 0))


@pytest.mark.unit
def test_policy_version_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        PolicyVersion(1, 0, 0).major = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Serialization (pydantic integration)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_identifiers_serialise_as_plain_strings() -> None:
    """Identifiers must never serialise as nested objects — the JSON contract is strings."""
    holder = _IdHolder(context_id="ctx-a-1", policy_id="coverage", policy_version="1.0.0")
    assert holder.model_dump(mode="json") == {
        "context_id": "ctx-a-1",
        "policy_id": "coverage",
        "policy_version": "1.0.0",
    }


@pytest.mark.unit
def test_identifiers_validate_from_strings_and_from_instances() -> None:
    from_strings = _IdHolder(context_id="ctx-a-1", policy_id="coverage", policy_version="1.0.0")
    from_instances = _IdHolder(
        context_id=EngineeringContextId("ctx-a-1"),
        policy_id=OrchestrationPolicyId("coverage"),
        policy_version=PolicyVersion(1, 0, 0),
    )
    assert from_strings == from_instances
    assert isinstance(from_strings.context_id, EngineeringContextId)


@pytest.mark.unit
def test_identifiers_survive_a_json_round_trip() -> None:
    holder = _IdHolder(context_id="ctx-a-1", policy_id="coverage", policy_version="1.0.0")
    assert _IdHolder.model_validate_json(holder.model_dump_json()) == holder


@pytest.mark.unit
def test_invalid_identifier_rejected_at_model_boundary() -> None:
    with pytest.raises(ValidationError):
        _IdHolder(context_id="NOT VALID", policy_id="coverage", policy_version="1.0.0")
