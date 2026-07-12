"""Unit tests for the Quality Governance Framework typed identities (CAP-080A).

The identities follow the ADR-0015/ADR-0016 precedent: immutable, string-backed,
deterministic value objects that serialise to and validate from a plain string. No
UUIDs, no timestamps, no randomness.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import BaseModel, ValidationError

from requirement_intelligence.quality_governance.identity import (
    QualityAssessmentId,
    QualityAssessmentVersion,
    QualityGovernanceResultId,
    QualityGovernanceResultVersion,
    QualityGovernanceVersion,
    QualityPolicyId,
    QualityPolicyVersion,
)


@pytest.mark.unit
class TestStringIdentifiers:
    def test_valid_policy_id_round_trips(self) -> None:
        pid = QualityPolicyId("default-quality-policy")
        assert str(pid) == "default-quality-policy"
        assert QualityPolicyId.parse("  default-quality-policy  ") == pid

    @pytest.mark.parametrize("bad", ["", "Upper", "-leading", "trailing-", "has space"])
    def test_invalid_identifier_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            QualityPolicyId(bad)

    def test_identifiers_are_frozen(self) -> None:
        pid = QualityPolicyId("p")
        with pytest.raises(FrozenInstanceError):
            pid.value = "q"  # type: ignore[misc]


@pytest.mark.unit
class TestDeterministicIds:
    def test_assessment_id_is_pure_function_of_inputs(self) -> None:
        a = QualityAssessmentId.for_run("an-1", "ex-1")
        b = QualityAssessmentId.for_run("an-1", "ex-1")
        assert a == b
        assert str(a).startswith("qa-")

    def test_assessment_id_varies_with_inputs(self) -> None:
        assert QualityAssessmentId.for_run("an-1", "ex-1") != QualityAssessmentId.for_run(
            "an-1", "ex-2"
        )

    def test_result_id_is_pure_function_of_assessment(self) -> None:
        r = QualityGovernanceResultId.for_assessment("qa-abc")
        assert r == QualityGovernanceResultId.for_assessment("qa-abc")
        assert str(r).startswith("qg-")

    @pytest.mark.parametrize(
        "factory",
        [
            lambda: QualityAssessmentId.for_run("", "ex"),
            lambda: QualityAssessmentId.for_run("an", ""),
            lambda: QualityGovernanceResultId.for_assessment("  "),
        ],
    )
    def test_empty_inputs_rejected(self, factory) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ValueError):
            factory()


@pytest.mark.unit
class TestSemanticVersions:
    def test_parse_and_str_round_trip(self) -> None:
        assert str(QualityGovernanceVersion.parse("1.2.3")) == "1.2.3"

    def test_versions_are_ordered(self) -> None:
        assert QualityPolicyVersion(1, 0, 0) < QualityPolicyVersion(1, 1, 0)

    def test_compatibility_is_major_only(self) -> None:
        assert QualityPolicyVersion(1, 4, 0).is_compatible_with(QualityPolicyVersion(1, 0, 9))
        assert not QualityPolicyVersion(2, 0, 0).is_compatible_with(QualityPolicyVersion(1, 0, 0))

    @pytest.mark.parametrize("bad", ["1.0", "x.y.z", "-1.0.0"])
    def test_invalid_version_string_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            QualityGovernanceVersion.parse(bad)

    def test_negative_components_rejected(self) -> None:
        with pytest.raises(ValueError):
            QualityAssessmentVersion(1, -1, 0)

    def test_the_four_version_axes_are_distinct_types(self) -> None:
        # Framework, policy, assessment, and result-contract versions evolve
        # independently; they are distinct value-object types (ADR-0017 Rec 2).
        types = {
            QualityGovernanceVersion,
            QualityPolicyVersion,
            QualityAssessmentVersion,
            QualityGovernanceResultVersion,
        }
        assert len(types) == 4


@pytest.mark.unit
class TestPydanticSerialization:
    def test_identity_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            pid: QualityPolicyId
            ver: QualityPolicyVersion

        m = M(pid=QualityPolicyId("p"), ver=QualityPolicyVersion(1, 0, 0))
        assert m.model_dump(mode="json") == {"pid": "p", "ver": "1.0.0"}
        assert M.model_validate({"pid": "p", "ver": "1.0.0"}) == m

    def test_bad_identity_string_raises_validation_error(self) -> None:
        class M(BaseModel):
            pid: QualityPolicyId

        with pytest.raises(ValidationError):
            M.model_validate({"pid": "Bad Id"})
