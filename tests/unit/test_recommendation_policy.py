"""Unit tests for the governed RecommendationPolicy and its builder (CAP-082A).

The policy is governed data only — immutable, versioned, deterministic. The builder
constructs; it generates no recommendation, prioritizes nothing, groups nothing.
These tests assert construction and shape, never a recommendation computation,
because no engine exists yet.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.recommendation.models.enums import (
    RecommendationPriority,
    RecommendationType,
)
from requirement_intelligence.recommendation.policy import (
    DEFAULT_RECOMMENDATION_POLICY_ID,
    ConfidenceRules,
    GroupingRules,
    PrioritizationRules,
    ProjectionRules,
    RecommendationPolicy,
    RecommendationPolicyBuilder,
    default_recommendation_policy,
)
from requirement_intelligence.recommendation.version import RECOMMENDATION_POLICY_VERSION


@pytest.mark.unit
class TestDefaultPolicy:
    def test_default_is_versioned_and_identified(self) -> None:
        policy = default_recommendation_policy()
        assert policy.policy_id == DEFAULT_RECOMMENDATION_POLICY_ID
        assert policy.policy_version == RECOMMENDATION_POLICY_VERSION

    def test_builder_is_deterministic(self) -> None:
        assert RecommendationPolicyBuilder().build() == RecommendationPolicyBuilder().build()

    def test_policy_is_immutable(self) -> None:
        policy = default_recommendation_policy()
        with pytest.raises(ValidationError):
            policy.description = "changed"  # type: ignore[misc]

    def test_near_term_capabilities_enabled_engine_families_reserved_off(self) -> None:
        # Prioritization/grouping/confidence-scoring are the CAP-082A-governed
        # near-term capabilities; the deterministic/ML/LLM engine families are
        # reserved off by default until CAP-082B and beyond implement them
        # (Recommendation 5).
        switches = default_recommendation_policy().capability_switches
        assert switches.enable_prioritization
        assert switches.enable_grouping
        assert switches.enable_confidence_scoring
        assert not switches.enable_deterministic_engine
        assert not switches.enable_ml_engine
        assert not switches.enable_llm_engine

    def test_prioritization_rules_cover_the_full_governed_vocabulary(self) -> None:
        policy = default_recommendation_policy()
        assert set(policy.prioritization_rules.enabled_priorities) == set(RecommendationPriority)

    def test_grouping_rules_cover_the_full_governed_vocabulary(self) -> None:
        policy = default_recommendation_policy()
        assert set(policy.grouping_rules.enabled_categories) == set(RecommendationType)

    def test_confidence_rules_thresholds_are_ordered(self) -> None:
        rules = default_recommendation_policy().confidence_rules
        assert rules.minimum_confidence_to_surface <= rules.high_confidence_threshold

    def test_projection_rules_default_excludes_low_priority(self) -> None:
        rules = default_recommendation_policy().projection_rules
        assert rules.include_low_priority_in_report is False


@pytest.mark.unit
class TestPolicyValidation:
    def test_negative_bound_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PrioritizationRules(max_recommendations_per_priority=-1)

    def test_negative_grouping_bound_rejected(self) -> None:
        with pytest.raises(ValidationError):
            GroupingRules(max_recommendations_per_group=-1)

    def test_confidence_threshold_out_of_bounds_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ConfidenceRules(minimum_confidence_to_surface=1.5, high_confidence_threshold=0.9)

    def test_inverted_confidence_thresholds_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ConfidenceRules(minimum_confidence_to_surface=0.9, high_confidence_threshold=0.5)

    def test_equal_confidence_thresholds_accepted(self) -> None:
        rules = ConfidenceRules(minimum_confidence_to_surface=0.5, high_confidence_threshold=0.5)
        assert rules.minimum_confidence_to_surface == rules.high_confidence_threshold

    def test_negative_projection_bound_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProjectionRules(max_recommendations_in_summary=-1)

    def test_policy_round_trips(self) -> None:
        policy = default_recommendation_policy()
        dumped = policy.model_dump(mode="json", by_alias=True)
        assert RecommendationPolicy.model_validate(dumped) == policy
