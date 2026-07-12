"""Unit tests for the Rule Evaluation typed identities (CAP-080A.1).

Deterministic, string-backed value objects with independent version axes — no UUIDs,
no timestamps, no randomness.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import BaseModel, ValidationError

from requirement_intelligence.quality_governance.identity import (
    RuleEvaluationId,
    RuleEvaluationResultId,
    RuleEvaluationResultVersion,
    RuleEvaluationVersion,
)


@pytest.mark.unit
class TestDeterministicIds:
    def test_result_id_is_pure_function_of_inputs(self) -> None:
        a = RuleEvaluationResultId.for_run("an-1", "ex-1")
        assert a == RuleEvaluationResultId.for_run("an-1", "ex-1")
        assert str(a).startswith("revr-")

    def test_result_id_varies_with_inputs(self) -> None:
        assert RuleEvaluationResultId.for_run("an-1", "ex-1") != RuleEvaluationResultId.for_run(
            "an-2", "ex-1"
        )

    def test_evaluation_id_is_pure_function_of_run_and_rule(self) -> None:
        a = RuleEvaluationId.for_rule("revr-x", "rule.a")
        assert a == RuleEvaluationId.for_rule("revr-x", "rule.a")
        assert a != RuleEvaluationId.for_rule("revr-x", "rule.b")
        assert str(a).startswith("rev-")

    @pytest.mark.parametrize(
        "factory",
        [
            lambda: RuleEvaluationResultId.for_run("", "ex"),
            lambda: RuleEvaluationResultId.for_run("an", ""),
            lambda: RuleEvaluationId.for_rule("", "rule"),
            lambda: RuleEvaluationId.for_rule("revr", "  "),
        ],
    )
    def test_empty_inputs_rejected(self, factory) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ValueError):
            factory()

    def test_ids_are_frozen(self) -> None:
        rid = RuleEvaluationResultId("revr-x")
        with pytest.raises(FrozenInstanceError):
            rid.value = "revr-y"  # type: ignore[misc]

    def test_id_equality(self) -> None:
        assert RuleEvaluationResultId("revr-x") == RuleEvaluationResultId("revr-x")
        assert RuleEvaluationResultId("revr-x") != RuleEvaluationResultId("revr-y")


@pytest.mark.unit
class TestVersions:
    def test_parse_round_trip_and_order(self) -> None:
        assert str(RuleEvaluationVersion.parse("1.2.3")) == "1.2.3"
        assert RuleEvaluationResultVersion(1, 0, 0) < RuleEvaluationResultVersion(2, 0, 0)

    def test_two_evaluation_version_axes_are_distinct(self) -> None:
        assert RuleEvaluationVersion is not RuleEvaluationResultVersion

    @pytest.mark.parametrize("bad", ["1.0", "a.b.c", "-1.0.0"])
    def test_invalid_version_string_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError):
            RuleEvaluationVersion.parse(bad)

    def test_serialises_to_plain_string(self) -> None:
        class M(BaseModel):
            rid: RuleEvaluationResultId
            ver: RuleEvaluationResultVersion

        m = M(rid=RuleEvaluationResultId("revr-x"), ver=RuleEvaluationResultVersion(1, 0, 0))
        assert m.model_dump(mode="json") == {"rid": "revr-x", "ver": "1.0.0"}
        assert M.model_validate({"rid": "revr-x", "ver": "1.0.0"}) == m

    def test_bad_identity_string_raises(self) -> None:
        class M(BaseModel):
            rid: RuleEvaluationResultId

        with pytest.raises(ValidationError):
            M.model_validate({"rid": "Bad Id"})
