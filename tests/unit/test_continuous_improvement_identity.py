"""Unit tests for the Continuous Improvement Framework typed identities (CAP-083A).

The identities follow the ADR-0015/ADR-0016/ADR-0017/ADR-0018/ADR-0019 precedent:
immutable, string-backed, deterministic value objects that serialise to and
validate from a plain string. No UUIDs, no timestamps, no randomness.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import BaseModel, ValidationError

from requirement_intelligence.continuous_improvement.identity import (
    ContinuousImprovementFrameworkVersion,
    ContinuousImprovementResultId,
    ContinuousImprovementResultVersion,
    ImprovementAssessmentId,
    ImprovementAssessmentVersion,
    ImprovementFindingId,
    ImprovementOpportunityId,
    ImprovementPolicyId,
    ImprovementPolicyVersion,
    ImprovementTrendId,
    ImprovementTrendVersion,
)


@pytest.mark.unit
class TestStringIdentifiers:
    def test_valid_policy_id_round_trips(self) -> None:
        pid = ImprovementPolicyId("default-improvement-policy")
        assert str(pid) == "default-improvement-policy"
        assert ImprovementPolicyId.parse("  default-improvement-policy  ") == pid

    @pytest.mark.parametrize("bad", ["", "Upper", "-leading", "trailing-", "has space"])
    def test_invalid_identifier_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            ImprovementPolicyId(bad)

    def test_identifiers_are_frozen(self) -> None:
        pid = ImprovementPolicyId("p")
        with pytest.raises(FrozenInstanceError):
            pid.value = "q"  # type: ignore[misc]

    def test_different_identity_types_are_not_interchangeable(self) -> None:
        # ImprovementFindingId and ImprovementTrendId are distinct types even
        # though both are string identifiers with the same shape rules.
        assert ImprovementFindingId("if-1") != ImprovementTrendId("if-1")


@pytest.mark.unit
class TestDeterministicIds:
    def test_finding_id_is_pure_function_of_inputs(self) -> None:
        a = ImprovementFindingId.for_ordinal("ds-1", 0)
        b = ImprovementFindingId.for_ordinal("ds-1", 0)
        assert a == b
        assert str(a).startswith("if-")

    def test_finding_id_varies_with_ordinal(self) -> None:
        assert ImprovementFindingId.for_ordinal("ds-1", 0) != ImprovementFindingId.for_ordinal(
            "ds-1", 1
        )

    def test_finding_id_varies_with_dataset(self) -> None:
        assert ImprovementFindingId.for_ordinal("ds-1", 0) != ImprovementFindingId.for_ordinal(
            "ds-2", 0
        )

    def test_trend_id_is_pure_function_of_inputs(self) -> None:
        a = ImprovementTrendId.for_ordinal("ds-1", 0)
        b = ImprovementTrendId.for_ordinal("ds-1", 0)
        assert a == b
        assert str(a).startswith("it-")

    def test_trend_id_varies_with_ordinal(self) -> None:
        assert ImprovementTrendId.for_ordinal("ds-1", 0) != ImprovementTrendId.for_ordinal(
            "ds-1", 1
        )

    def test_opportunity_id_is_pure_function_of_inputs(self) -> None:
        a = ImprovementOpportunityId.for_ordinal("ds-1", 0)
        b = ImprovementOpportunityId.for_ordinal("ds-1", 0)
        assert a == b
        assert str(a).startswith("io-")

    def test_opportunity_id_varies_with_ordinal(self) -> None:
        assert ImprovementOpportunityId.for_ordinal(
            "ds-1", 0
        ) != ImprovementOpportunityId.for_ordinal("ds-1", 1)

    def test_assessment_id_is_pure_function_of_inputs(self) -> None:
        a = ImprovementAssessmentId.for_ordinal("ds-1", 0)
        b = ImprovementAssessmentId.for_ordinal("ds-1", 0)
        assert a == b
        assert str(a).startswith("ia-")

    def test_result_id_is_pure_function_of_dataset(self) -> None:
        r = ContinuousImprovementResultId.for_dataset("ds-1")
        assert r == ContinuousImprovementResultId.for_dataset("ds-1")
        assert str(r).startswith("cir-")

    def test_result_id_varies_with_dataset(self) -> None:
        assert ContinuousImprovementResultId.for_dataset(
            "ds-1"
        ) != ContinuousImprovementResultId.for_dataset("ds-2")

    @pytest.mark.parametrize(
        "factory",
        [
            lambda: ImprovementFindingId.for_ordinal("", 0),
            lambda: ImprovementFindingId.for_ordinal("ds-1", -1),
            lambda: ImprovementTrendId.for_ordinal("", 0),
            lambda: ImprovementTrendId.for_ordinal("ds-1", -1),
            lambda: ImprovementOpportunityId.for_ordinal("", 0),
            lambda: ImprovementOpportunityId.for_ordinal("ds-1", -1),
            lambda: ContinuousImprovementResultId.for_dataset(""),
            lambda: ContinuousImprovementResultId.for_dataset("   "),
        ],
    )
    def test_invalid_inputs_rejected(self, factory) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ValueError):
            factory()


@pytest.mark.unit
class TestSemanticVersions:
    def test_parse_and_str_round_trip(self) -> None:
        assert str(ContinuousImprovementFrameworkVersion.parse("1.2.3")) == "1.2.3"

    def test_versions_are_ordered(self) -> None:
        assert ImprovementPolicyVersion(1, 0, 0) < ImprovementPolicyVersion(1, 1, 0)

    def test_compatibility_is_major_only(self) -> None:
        assert ImprovementPolicyVersion(1, 4, 0).is_compatible_with(
            ImprovementPolicyVersion(1, 0, 9)
        )
        assert not ImprovementPolicyVersion(2, 0, 0).is_compatible_with(
            ImprovementPolicyVersion(1, 0, 0)
        )

    @pytest.mark.parametrize("bad", ["1.0", "x.y.z", "-1.0.0"])
    def test_invalid_version_string_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            ContinuousImprovementFrameworkVersion.parse(bad)

    def test_negative_components_rejected(self) -> None:
        with pytest.raises(ValueError):
            ContinuousImprovementResultVersion(1, -1, 0)

    def test_the_five_version_axes_are_distinct_types(self) -> None:
        # Framework, policy, trend-schema, assessment-schema, and result-contract
        # versions evolve independently; they are distinct value-object types.
        types = {
            ContinuousImprovementFrameworkVersion,
            ImprovementPolicyVersion,
            ImprovementTrendVersion,
            ImprovementAssessmentVersion,
            ContinuousImprovementResultVersion,
        }
        assert len(types) == 5


@pytest.mark.unit
class TestPydanticSerialization:
    def test_identity_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            pid: ImprovementPolicyId
            ver: ImprovementPolicyVersion

        m = M(pid=ImprovementPolicyId("p"), ver=ImprovementPolicyVersion(1, 0, 0))
        assert m.model_dump(mode="json") == {"pid": "p", "ver": "1.0.0"}
        assert M.model_validate({"pid": "p", "ver": "1.0.0"}) == m

    def test_bad_identity_string_raises_validation_error(self) -> None:
        class M(BaseModel):
            pid: ImprovementPolicyId

        with pytest.raises(ValidationError):
            M.model_validate({"pid": "Bad Id"})

    def test_result_id_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            rid: ContinuousImprovementResultId

        m = M(rid=ContinuousImprovementResultId.for_dataset("ds-1"))
        dumped = m.model_dump(mode="json")
        assert dumped["rid"] == str(ContinuousImprovementResultId.for_dataset("ds-1"))
        assert M.model_validate(dumped) == m
