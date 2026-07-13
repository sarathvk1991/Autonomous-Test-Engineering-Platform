"""Unit tests for the Requirement Enhancement Framework typed identities (CAP-081A).

The identities follow the ADR-0015/ADR-0016/ADR-0017 precedent: immutable,
string-backed, deterministic value objects that serialise to and validate from a
plain string. No UUIDs, no timestamps, no randomness.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import BaseModel, ValidationError

from requirement_intelligence.enhancement.identity import (
    EnhancedRequirementId,
    EnhancementFrameworkVersion,
    EnhancementPolicyId,
    EnhancementPolicyVersion,
    EnhancementResultVersion,
    ObservationVersion,
    RelationshipGraphId,
    RelationshipVersion,
    RequirementEnhancementId,
    RequirementEnhancementResultId,
    RequirementObservationId,
)


@pytest.mark.unit
class TestStringIdentifiers:
    def test_valid_policy_id_round_trips(self) -> None:
        pid = EnhancementPolicyId("default-enhancement-policy")
        assert str(pid) == "default-enhancement-policy"
        assert EnhancementPolicyId.parse("  default-enhancement-policy  ") == pid

    @pytest.mark.parametrize("bad", ["", "Upper", "-leading", "trailing-", "has space"])
    def test_invalid_identifier_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            EnhancementPolicyId(bad)

    def test_identifiers_are_frozen(self) -> None:
        pid = EnhancementPolicyId("p")
        with pytest.raises(FrozenInstanceError):
            pid.value = "q"  # type: ignore[misc]


@pytest.mark.unit
class TestDeterministicIds:
    def test_enhancement_id_is_pure_function_of_inputs(self) -> None:
        a = RequirementEnhancementId.for_run("an-1", "ex-1")
        b = RequirementEnhancementId.for_run("an-1", "ex-1")
        assert a == b
        assert str(a).startswith("re-")

    def test_enhancement_id_varies_with_inputs(self) -> None:
        assert RequirementEnhancementId.for_run(
            "an-1", "ex-1"
        ) != RequirementEnhancementId.for_run("an-1", "ex-2")

    def test_result_id_is_pure_function_of_enhancement(self) -> None:
        r = RequirementEnhancementResultId.for_enhancement("re-abc")
        assert r == RequirementEnhancementResultId.for_enhancement("re-abc")
        assert str(r).startswith("rer-")

    def test_enhanced_requirement_id_is_pure_function_of_inputs(self) -> None:
        a = EnhancedRequirementId.for_requirement("re-abc", "req-1")
        b = EnhancedRequirementId.for_requirement("re-abc", "req-1")
        assert a == b
        assert str(a).startswith("er-")
        assert a != EnhancedRequirementId.for_requirement("re-abc", "req-2")

    def test_relationship_graph_id_is_pure_function_of_enhancement(self) -> None:
        g = RelationshipGraphId.for_enhancement("re-abc")
        assert g == RelationshipGraphId.for_enhancement("re-abc")
        assert str(g).startswith("rg-")

    def test_observation_id_is_pure_function_of_ordinal(self) -> None:
        o1 = RequirementObservationId.for_ordinal("re-abc", 0)
        o2 = RequirementObservationId.for_ordinal("re-abc", 1)
        assert o1 == RequirementObservationId.for_ordinal("re-abc", 0)
        assert o1 != o2
        assert str(o1).startswith("ro-")

    @pytest.mark.parametrize(
        "factory",
        [
            lambda: RequirementEnhancementId.for_run("", "ex"),
            lambda: RequirementEnhancementId.for_run("an", ""),
            lambda: RequirementEnhancementResultId.for_enhancement("  "),
            lambda: EnhancedRequirementId.for_requirement("", "req-1"),
            lambda: EnhancedRequirementId.for_requirement("re-abc", ""),
            lambda: RelationshipGraphId.for_enhancement(""),
            lambda: RequirementObservationId.for_ordinal("", 0),
            lambda: RequirementObservationId.for_ordinal("re-abc", -1),
        ],
    )
    def test_invalid_inputs_rejected(self, factory) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ValueError):
            factory()


@pytest.mark.unit
class TestSemanticVersions:
    def test_parse_and_str_round_trip(self) -> None:
        assert str(EnhancementFrameworkVersion.parse("1.2.3")) == "1.2.3"

    def test_versions_are_ordered(self) -> None:
        assert EnhancementPolicyVersion(1, 0, 0) < EnhancementPolicyVersion(1, 1, 0)

    def test_compatibility_is_major_only(self) -> None:
        assert EnhancementPolicyVersion(1, 4, 0).is_compatible_with(
            EnhancementPolicyVersion(1, 0, 9)
        )
        assert not EnhancementPolicyVersion(2, 0, 0).is_compatible_with(
            EnhancementPolicyVersion(1, 0, 0)
        )

    @pytest.mark.parametrize("bad", ["1.0", "x.y.z", "-1.0.0"])
    def test_invalid_version_string_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            EnhancementFrameworkVersion.parse(bad)

    def test_negative_components_rejected(self) -> None:
        with pytest.raises(ValueError):
            EnhancementResultVersion(1, -1, 0)

    def test_the_five_version_axes_are_distinct_types(self) -> None:
        # Framework, policy, result-contract, relationship, and observation versions
        # evolve independently; they are distinct value-object types (Recommendation 4).
        types = {
            EnhancementFrameworkVersion,
            EnhancementPolicyVersion,
            EnhancementResultVersion,
            RelationshipVersion,
            ObservationVersion,
        }
        assert len(types) == 5


@pytest.mark.unit
class TestPydanticSerialization:
    def test_identity_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            pid: EnhancementPolicyId
            ver: EnhancementPolicyVersion

        m = M(pid=EnhancementPolicyId("p"), ver=EnhancementPolicyVersion(1, 0, 0))
        assert m.model_dump(mode="json") == {"pid": "p", "ver": "1.0.0"}
        assert M.model_validate({"pid": "p", "ver": "1.0.0"}) == m

    def test_bad_identity_string_raises_validation_error(self) -> None:
        class M(BaseModel):
            pid: EnhancementPolicyId

        with pytest.raises(ValidationError):
            M.model_validate({"pid": "Bad Id"})
