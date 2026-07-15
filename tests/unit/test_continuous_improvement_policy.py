"""Unit tests for the governed ImprovementPolicy and its builder (CAP-083A).

The policy is governed data only — immutable, versioned, deterministic. The
builder constructs; it detects no finding, observes no trend, generates no
opportunity. These tests assert construction and shape, never a computation,
because no engine exists yet.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.continuous_improvement.policy import (
    DEFAULT_IMPROVEMENT_POLICY_ID,
    ImprovementCapabilitySwitches,
    ImprovementPolicy,
    ImprovementPolicyBuilder,
    ImprovementThresholds,
    default_improvement_policy,
)
from requirement_intelligence.continuous_improvement.version import IMPROVEMENT_POLICY_VERSION


@pytest.mark.unit
class TestDefaultPolicy:
    def test_default_is_versioned_and_identified(self) -> None:
        policy = default_improvement_policy()
        assert policy.policy_id == DEFAULT_IMPROVEMENT_POLICY_ID
        assert policy.policy_version == IMPROVEMENT_POLICY_VERSION

    def test_builder_is_deterministic(self) -> None:
        assert ImprovementPolicyBuilder().build() == ImprovementPolicyBuilder().build()

    def test_policy_is_immutable(self) -> None:
        policy = default_improvement_policy()
        with pytest.raises(ValidationError):
            policy.description = "changed"  # type: ignore[misc]

    def test_near_term_capabilities_enabled_engine_families_reserved_off(self) -> None:
        # Trend detection / recurring-finding detection / opportunity generation
        # are the CAP-083A-governed near-term capabilities; the deterministic/
        # ML/LLM engine families are reserved off by default until CAP-083B and
        # beyond implement them (mirrors ADR-0019 Recommendation 5).
        switches = default_improvement_policy().capability_switches
        assert switches.enable_trend_detection
        assert switches.enable_recurring_finding_detection
        assert switches.enable_opportunity_generation
        assert not switches.enable_deterministic_engine
        assert not switches.enable_ml_engine
        assert not switches.enable_llm_engine

    def test_default_thresholds(self) -> None:
        thresholds = default_improvement_policy().thresholds
        assert thresholds.minimum_occurrences == 3
        assert thresholds.history_window == 25

    def test_minimum_occurrences_does_not_exceed_history_window(self) -> None:
        thresholds = default_improvement_policy().thresholds
        assert thresholds.minimum_occurrences <= thresholds.history_window


@pytest.mark.unit
class TestPolicyValidation:
    def test_negative_minimum_occurrences_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementThresholds(minimum_occurrences=-1, history_window=25)

    def test_negative_history_window_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementThresholds(minimum_occurrences=3, history_window=-1)

    def test_minimum_occurrences_exceeding_window_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementThresholds(minimum_occurrences=30, history_window=25)

    def test_minimum_occurrences_equal_to_window_accepted(self) -> None:
        thresholds = ImprovementThresholds(minimum_occurrences=25, history_window=25)
        assert thresholds.minimum_occurrences == thresholds.history_window

    def test_policy_round_trips(self) -> None:
        policy = default_improvement_policy()
        dumped = policy.model_dump(mode="json", by_alias=True)
        assert ImprovementPolicy.model_validate(dumped) == policy

    def test_capability_switches_round_trip(self) -> None:
        switches = ImprovementCapabilitySwitches()
        dumped = switches.model_dump(mode="json", by_alias=True)
        assert ImprovementCapabilitySwitches.model_validate(dumped) == switches
