"""Unit tests for the Recommendation Framework typed identities (CAP-082A).

The identities follow the ADR-0015/ADR-0016/ADR-0017/ADR-0018 precedent: immutable,
string-backed, deterministic value objects that serialise to and validate from a
plain string. No UUIDs, no timestamps, no randomness.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import BaseModel, ValidationError

from requirement_intelligence.recommendation.identity import (
    RecommendationFrameworkVersion,
    RecommendationGroupId,
    RecommendationId,
    RecommendationPolicyId,
    RecommendationPolicyVersion,
    RecommendationResultId,
    RecommendationResultVersion,
    RecommendationVersion,
)


@pytest.mark.unit
class TestStringIdentifiers:
    def test_valid_policy_id_round_trips(self) -> None:
        pid = RecommendationPolicyId("default-recommendation-policy")
        assert str(pid) == "default-recommendation-policy"
        assert RecommendationPolicyId.parse("  default-recommendation-policy  ") == pid

    @pytest.mark.parametrize("bad", ["", "Upper", "-leading", "trailing-", "has space"])
    def test_invalid_identifier_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            RecommendationPolicyId(bad)

    def test_identifiers_are_frozen(self) -> None:
        pid = RecommendationPolicyId("p")
        with pytest.raises(FrozenInstanceError):
            pid.value = "q"  # type: ignore[misc]

    def test_different_identity_types_are_not_interchangeable(self) -> None:
        # RecommendationId and RecommendationGroupId are distinct types even though
        # both are string identifiers with the same shape rules.
        assert RecommendationId("rc-1") != RecommendationGroupId("rc-1")


@pytest.mark.unit
class TestDeterministicIds:
    def test_recommendation_id_is_pure_function_of_inputs(self) -> None:
        a = RecommendationId.for_ordinal("ex-1", 0)
        b = RecommendationId.for_ordinal("ex-1", 0)
        assert a == b
        assert str(a).startswith("rc-")

    def test_recommendation_id_varies_with_ordinal(self) -> None:
        assert RecommendationId.for_ordinal("ex-1", 0) != RecommendationId.for_ordinal("ex-1", 1)

    def test_recommendation_id_varies_with_execution(self) -> None:
        assert RecommendationId.for_ordinal("ex-1", 0) != RecommendationId.for_ordinal("ex-2", 0)

    def test_group_id_is_pure_function_of_inputs(self) -> None:
        a = RecommendationGroupId.for_ordinal("ex-1", 0)
        b = RecommendationGroupId.for_ordinal("ex-1", 0)
        assert a == b
        assert str(a).startswith("rg-")

    def test_group_id_varies_with_ordinal(self) -> None:
        assert RecommendationGroupId.for_ordinal(
            "ex-1", 0
        ) != RecommendationGroupId.for_ordinal("ex-1", 1)

    def test_result_id_is_pure_function_of_execution(self) -> None:
        r = RecommendationResultId.for_execution("ex-1")
        assert r == RecommendationResultId.for_execution("ex-1")
        assert str(r).startswith("rr-")

    def test_result_id_varies_with_execution(self) -> None:
        assert RecommendationResultId.for_execution("ex-1") != RecommendationResultId.for_execution(
            "ex-2"
        )

    @pytest.mark.parametrize(
        "factory",
        [
            lambda: RecommendationId.for_ordinal("", 0),
            lambda: RecommendationId.for_ordinal("ex-1", -1),
            lambda: RecommendationGroupId.for_ordinal("", 0),
            lambda: RecommendationGroupId.for_ordinal("ex-1", -1),
            lambda: RecommendationResultId.for_execution(""),
            lambda: RecommendationResultId.for_execution("   "),
        ],
    )
    def test_invalid_inputs_rejected(self, factory) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ValueError):
            factory()


@pytest.mark.unit
class TestSemanticVersions:
    def test_parse_and_str_round_trip(self) -> None:
        assert str(RecommendationFrameworkVersion.parse("1.2.3")) == "1.2.3"

    def test_versions_are_ordered(self) -> None:
        assert RecommendationPolicyVersion(1, 0, 0) < RecommendationPolicyVersion(1, 1, 0)

    def test_compatibility_is_major_only(self) -> None:
        assert RecommendationPolicyVersion(1, 4, 0).is_compatible_with(
            RecommendationPolicyVersion(1, 0, 9)
        )
        assert not RecommendationPolicyVersion(2, 0, 0).is_compatible_with(
            RecommendationPolicyVersion(1, 0, 0)
        )

    @pytest.mark.parametrize("bad", ["1.0", "x.y.z", "-1.0.0"])
    def test_invalid_version_string_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            RecommendationFrameworkVersion.parse(bad)

    def test_negative_components_rejected(self) -> None:
        with pytest.raises(ValueError):
            RecommendationResultVersion(1, -1, 0)

    def test_the_four_version_axes_are_distinct_types(self) -> None:
        # Framework, policy, recommendation-schema, and result-contract versions
        # evolve independently; they are distinct value-object types (Recommendation 5).
        types = {
            RecommendationFrameworkVersion,
            RecommendationPolicyVersion,
            RecommendationVersion,
            RecommendationResultVersion,
        }
        assert len(types) == 4


@pytest.mark.unit
class TestPydanticSerialization:
    def test_identity_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            pid: RecommendationPolicyId
            ver: RecommendationPolicyVersion

        m = M(pid=RecommendationPolicyId("p"), ver=RecommendationPolicyVersion(1, 0, 0))
        assert m.model_dump(mode="json") == {"pid": "p", "ver": "1.0.0"}
        assert M.model_validate({"pid": "p", "ver": "1.0.0"}) == m

    def test_bad_identity_string_raises_validation_error(self) -> None:
        class M(BaseModel):
            pid: RecommendationPolicyId

        with pytest.raises(ValidationError):
            M.model_validate({"pid": "Bad Id"})

    def test_result_id_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            rid: RecommendationResultId

        m = M(rid=RecommendationResultId.for_execution("ex-1"))
        dumped = m.model_dump(mode="json")
        assert dumped["rid"] == str(RecommendationResultId.for_execution("ex-1"))
        assert M.model_validate(dumped) == m
