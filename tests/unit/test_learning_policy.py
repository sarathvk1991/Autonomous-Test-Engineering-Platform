"""Architecture-only tests for the governed :class:`LearningPolicy`
(CAP-086A, ADR-0029).

Covers the builder, the default policy, capability switches, and threshold
validation. No algorithm reads this policy yet — it is data only (Stage 6
of the CAP-086A brief).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.learning.identity import LearningPolicyId, LearningPolicyVersion
from requirement_intelligence.learning.policy import (
    DEFAULT_LEARNING_POLICY_ID,
    LearningCapabilitySwitches,
    LearningPolicy,
    LearningPolicyBuilder,
    LearningThresholds,
    default_learning_policy,
)


@pytest.mark.unit
class TestLearningCapabilitySwitches:
    def test_defaults_enable_the_four_governed_capabilities(self) -> None:
        switches = LearningCapabilitySwitches()
        assert switches.enable_candidate_proposal is True
        assert switches.enable_validation is True
        assert switches.enable_confidence_recording is True
        assert switches.enable_lifecycle_recording is True

    def test_defaults_reserve_every_future_engine_family_off(self) -> None:
        switches = LearningCapabilitySwitches()
        assert switches.enable_deterministic_engine is False
        assert switches.enable_ml_engine is False
        assert switches.enable_llm_engine is False
        assert switches.enable_reinforcement_learning_engine is False
        assert switches.enable_neuro_symbolic_engine is False

    def test_is_immutable(self) -> None:
        switches = LearningCapabilitySwitches()
        with pytest.raises(ValidationError):
            switches.enable_validation = False  # type: ignore[misc]

    def test_round_trips(self) -> None:
        switches = LearningCapabilitySwitches()
        dumped = switches.model_dump(mode="json", by_alias=True)
        assert LearningCapabilitySwitches.model_validate(dumped) == switches


@pytest.mark.unit
class TestLearningThresholds:
    def _thresholds(self, **overrides: object) -> LearningThresholds:
        defaults: dict[str, object] = dict(
            minimum_best_practices_for_candidate=2,
            minimum_validation_gates_for_learning=6,
            minimum_confidence_for_learning=3,
        )
        defaults.update(overrides)
        return LearningThresholds(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_valid_bounds(self) -> None:
        thresholds = self._thresholds()
        assert thresholds.minimum_best_practices_for_candidate == 2

    def test_rejects_zero_minimum_best_practices(self) -> None:
        with pytest.raises(ValidationError):
            self._thresholds(minimum_best_practices_for_candidate=0)

    def test_rejects_zero_minimum_validation_gates(self) -> None:
        with pytest.raises(ValidationError):
            self._thresholds(minimum_validation_gates_for_learning=0)

    def test_rejects_more_than_six_validation_gates(self) -> None:
        with pytest.raises(ValidationError):
            self._thresholds(minimum_validation_gates_for_learning=7)

    def test_rejects_confidence_ordinal_out_of_bounds(self) -> None:
        with pytest.raises(ValidationError):
            self._thresholds(minimum_confidence_for_learning=4)

    def test_accepts_confidence_ordinal_zero(self) -> None:
        thresholds = self._thresholds(minimum_confidence_for_learning=0)
        assert thresholds.minimum_confidence_for_learning == 0

    def test_is_immutable(self) -> None:
        thresholds = self._thresholds()
        with pytest.raises(ValidationError):
            thresholds.minimum_best_practices_for_candidate = 10  # type: ignore[misc]


@pytest.mark.unit
class TestLearningPolicy:
    def test_constructs_with_governed_fields(self) -> None:
        policy = LearningPolicy(
            policy_id=LearningPolicyId("test-policy"),
            policy_version=LearningPolicyVersion(1, 0, 0),
            description="A test policy.",
            capability_switches=LearningCapabilitySwitches(),
            thresholds=LearningThresholds(
                minimum_best_practices_for_candidate=1,
                minimum_validation_gates_for_learning=1,
                minimum_confidence_for_learning=0,
            ),
        )
        assert policy.policy_id == LearningPolicyId("test-policy")

    def test_rejects_empty_description(self) -> None:
        with pytest.raises(ValidationError):
            LearningPolicy(
                policy_id=LearningPolicyId("test-policy"),
                policy_version=LearningPolicyVersion(1, 0, 0),
                description="",
                capability_switches=LearningCapabilitySwitches(),
                thresholds=LearningThresholds(
                    minimum_best_practices_for_candidate=1,
                    minimum_validation_gates_for_learning=1,
                    minimum_confidence_for_learning=0,
                ),
            )

    def test_is_immutable(self) -> None:
        policy = default_learning_policy()
        with pytest.raises(ValidationError):
            policy.description = "mutated"  # type: ignore[misc]


@pytest.mark.unit
class TestLearningPolicyBuilder:
    def test_builds_the_default_policy(self) -> None:
        policy = LearningPolicyBuilder().build()
        assert policy.policy_id == DEFAULT_LEARNING_POLICY_ID

    def test_default_policy_version_is_1_0_0(self) -> None:
        policy = LearningPolicyBuilder().build()
        assert str(policy.policy_version) == "1.0.0"

    def test_default_policy_deterministic_engine_is_reserved_off(self) -> None:
        policy = LearningPolicyBuilder().build()
        assert policy.capability_switches.enable_deterministic_engine is False

    def test_default_policy_curation_switches_are_on(self) -> None:
        policy = LearningPolicyBuilder().build()
        assert policy.capability_switches.enable_candidate_proposal is True
        assert policy.capability_switches.enable_validation is True
        assert policy.capability_switches.enable_confidence_recording is True
        assert policy.capability_switches.enable_lifecycle_recording is True

    def test_default_policy_requires_all_six_gates(self) -> None:
        """ADR-0028 §Stage 6 requires all six gates before Candidate → Learning."""
        policy = LearningPolicyBuilder().build()
        assert policy.thresholds.minimum_validation_gates_for_learning == 6

    def test_default_policy_requires_more_than_one_best_practice(self) -> None:
        """ADR-0028 §Stage 6: "a single Best Practice, in isolation, is not enough"."""
        policy = LearningPolicyBuilder().build()
        assert policy.thresholds.minimum_best_practices_for_candidate >= 2

    def test_module_level_helper_matches_builder(self) -> None:
        assert default_learning_policy() == LearningPolicyBuilder().build()

    def test_repeated_calls_return_equal_but_independent_policies(self) -> None:
        a = default_learning_policy()
        b = default_learning_policy()
        assert a == b
        assert a is not b
