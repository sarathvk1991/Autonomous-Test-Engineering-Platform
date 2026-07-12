"""Unit tests for the Quality Decision typed identities (CAP-080A.3).

Deterministic, string-backed value objects with independent version axes — no UUIDs,
no timestamps, no randomness.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import BaseModel, ValidationError

from requirement_intelligence.quality_governance.identity import (
    DecisionPolicyId,
    DecisionPolicyVersion,
    DecisionVersion,
    QualityDecisionResultId,
    QualityDecisionResultVersion,
)


@pytest.mark.unit
class TestDecisionPolicyId:
    def test_valid_round_trips(self) -> None:
        pid = DecisionPolicyId("default-decision-policy")
        assert str(pid) == "default-decision-policy"
        assert DecisionPolicyId.parse("  default-decision-policy ") == pid

    @pytest.mark.parametrize("bad", ["", "Upper", "-x", "x-", "a b"])
    def test_invalid_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            DecisionPolicyId(bad)

    def test_frozen(self) -> None:
        pid = DecisionPolicyId("p")
        with pytest.raises(FrozenInstanceError):
            pid.value = "q"  # type: ignore[misc]


@pytest.mark.unit
class TestQualityDecisionResultId:
    def test_deterministic_from_assessment(self) -> None:
        a = QualityDecisionResultId.for_assessment("qar-x")
        assert a == QualityDecisionResultId.for_assessment("qar-x")
        assert a != QualityDecisionResultId.for_assessment("qar-y")
        assert str(a).startswith("qdr-")

    def test_empty_rejected(self) -> None:
        with pytest.raises(ValueError):
            QualityDecisionResultId.for_assessment("   ")

    def test_equality(self) -> None:
        assert QualityDecisionResultId("qdr-x") == QualityDecisionResultId("qdr-x")
        assert QualityDecisionResultId("qdr-x") != QualityDecisionResultId("qdr-y")


@pytest.mark.unit
class TestVersions:
    def test_parse_round_trip_and_order(self) -> None:
        assert str(DecisionPolicyVersion.parse("2.1.0")) == "2.1.0"
        assert QualityDecisionResultVersion(1, 0, 0) < QualityDecisionResultVersion(1, 1, 0)

    def test_compatibility_is_major_only(self) -> None:
        assert DecisionPolicyVersion(1, 9, 9).is_compatible_with(DecisionPolicyVersion(1, 0, 0))
        assert not DecisionVersion(2, 0, 0).is_compatible_with(DecisionVersion(1, 0, 0))

    @pytest.mark.parametrize("bad", ["1.0", "a.b.c", "-1.0.0"])
    def test_invalid_version_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            DecisionPolicyVersion.parse(bad)

    def test_three_new_axes_are_distinct_types(self) -> None:
        assert len({DecisionPolicyVersion, DecisionVersion, QualityDecisionResultVersion}) == 3

    def test_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            pid: DecisionPolicyId
            ver: QualityDecisionResultVersion

        m = M(pid=DecisionPolicyId("p"), ver=QualityDecisionResultVersion(1, 0, 0))
        assert m.model_dump(mode="json") == {"pid": "p", "ver": "1.0.0"}
        assert M.model_validate({"pid": "p", "ver": "1.0.0"}) == m

    def test_bad_identity_string_raises(self) -> None:
        class M(BaseModel):
            pid: DecisionPolicyId

        with pytest.raises(ValidationError):
            M.model_validate({"pid": "Bad Id"})
