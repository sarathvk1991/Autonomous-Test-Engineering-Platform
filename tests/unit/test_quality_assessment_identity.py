"""Unit tests for the Quality Assessment typed identities (CAP-080A.2).

Deterministic, string-backed value objects with independent version axes — no UUIDs,
no timestamps, no randomness. Also asserts the CAP-080A collision was avoided.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import BaseModel, ValidationError

from requirement_intelligence.quality_governance.identity import (
    AssessmentOutcomeVersion,
    AssessmentPolicyId,
    AssessmentPolicyVersion,
    QualityAssessmentResultId,
    QualityAssessmentResultVersion,
    QualityAssessmentVersion,
)


@pytest.mark.unit
class TestAssessmentPolicyId:
    def test_valid_round_trips(self) -> None:
        pid = AssessmentPolicyId("default-assessment-policy")
        assert str(pid) == "default-assessment-policy"
        assert AssessmentPolicyId.parse("  default-assessment-policy ") == pid

    @pytest.mark.parametrize("bad", ["", "Upper", "-x", "x-", "a b"])
    def test_invalid_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            AssessmentPolicyId(bad)

    def test_frozen(self) -> None:
        pid = AssessmentPolicyId("p")
        with pytest.raises(FrozenInstanceError):
            pid.value = "q"  # type: ignore[misc]


@pytest.mark.unit
class TestQualityAssessmentResultId:
    def test_deterministic_from_evaluation(self) -> None:
        a = QualityAssessmentResultId.for_evaluation("revr-x")
        assert a == QualityAssessmentResultId.for_evaluation("revr-x")
        assert a != QualityAssessmentResultId.for_evaluation("revr-y")
        assert str(a).startswith("qar-")

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            QualityAssessmentResultId.for_evaluation("   ")

    def test_equality(self) -> None:
        assert QualityAssessmentResultId("qar-x") == QualityAssessmentResultId("qar-x")
        assert QualityAssessmentResultId("qar-x") != QualityAssessmentResultId("qar-y")


@pytest.mark.unit
class TestVersions:
    def test_parse_round_trip_and_order(self) -> None:
        assert str(AssessmentPolicyVersion.parse("2.1.0")) == "2.1.0"
        assert QualityAssessmentResultVersion(1, 0, 0) < QualityAssessmentResultVersion(1, 1, 0)

    def test_compatibility_is_major_only(self) -> None:
        assert AssessmentPolicyVersion(1, 9, 9).is_compatible_with(AssessmentPolicyVersion(1, 0, 0))
        assert not AssessmentOutcomeVersion(2, 0, 0).is_compatible_with(
            AssessmentOutcomeVersion(1, 0, 0)
        )

    @pytest.mark.parametrize("bad", ["1.0", "a.b.c", "-1.0.0"])
    def test_invalid_version_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            AssessmentPolicyVersion.parse(bad)

    def test_the_three_new_axes_are_distinct_types(self) -> None:
        assert (
            len({AssessmentPolicyVersion, AssessmentOutcomeVersion, QualityAssessmentResultVersion})
            == 3
        )

    def test_outcome_version_is_not_the_governance_assessment_version(self) -> None:
        # CAP-080A's QualityAssessmentVersion is a different model's axis; the assessment
        # subsystem uses AssessmentOutcomeVersion to avoid the collision (ADR-0017 D21).
        assert AssessmentOutcomeVersion is not QualityAssessmentVersion

    def test_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            pid: AssessmentPolicyId
            ver: QualityAssessmentResultVersion

        m = M(pid=AssessmentPolicyId("p"), ver=QualityAssessmentResultVersion(1, 0, 0))
        assert m.model_dump(mode="json") == {"pid": "p", "ver": "1.0.0"}
        assert M.model_validate({"pid": "p", "ver": "1.0.0"}) == m

    def test_bad_identity_string_raises(self) -> None:
        class M(BaseModel):
            pid: AssessmentPolicyId

        with pytest.raises(ValidationError):
            M.model_validate({"pid": "Bad Id"})
