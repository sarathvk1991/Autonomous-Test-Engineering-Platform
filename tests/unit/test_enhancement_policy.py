"""Unit tests for the governed EnhancementPolicy and its builder (CAP-081A).

The policy is governed data only — immutable, versioned, deterministic. The builder
constructs; it enriches nothing, detects no relationship, generates no observation.
These tests assert construction and shape, never an enhancement computation, because
no engine exists yet.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.enhancement.models.enums import (
    ObservationCategory,
    RelationshipType,
)
from requirement_intelligence.enhancement.policy import (
    DEFAULT_ENHANCEMENT_POLICY_ID,
    EnhancementPolicy,
    EnhancementPolicyBuilder,
    default_enhancement_policy,
)
from requirement_intelligence.enhancement.version import ENHANCEMENT_POLICY_VERSION


@pytest.mark.unit
class TestDefaultPolicy:
    def test_default_is_versioned_and_identified(self) -> None:
        policy = default_enhancement_policy()
        assert policy.policy_id == DEFAULT_ENHANCEMENT_POLICY_ID
        assert policy.policy_version == ENHANCEMENT_POLICY_VERSION

    def test_builder_is_deterministic(self) -> None:
        assert EnhancementPolicyBuilder().build() == EnhancementPolicyBuilder().build()

    def test_policy_is_immutable(self) -> None:
        policy = default_enhancement_policy()
        with pytest.raises(ValidationError):
            policy.description = "changed"  # type: ignore[misc]

    def test_core_capabilities_enabled_reserved_capabilities_disabled(self) -> None:
        # Enrichment/relationships/observations are the CAP-081A foundation;
        # completeness/consistency analysis are reserved extension points
        # (Recommendation 7) — off by default until a future milestone implements them.
        switches = default_enhancement_policy().capability_switches
        assert switches.enable_enrichment
        assert switches.enable_relationship_detection
        assert switches.enable_observation_generation
        assert not switches.enable_completeness_analysis
        assert not switches.enable_consistency_analysis

    def test_relationship_rules_cover_the_full_governed_vocabulary(self) -> None:
        # Every RelationshipType is enabled by default (Recommendation 2).
        policy = default_enhancement_policy()
        assert set(policy.relationship_rules.enabled_relationship_types) == set(RelationshipType)

    def test_observation_rules_cover_the_full_governed_vocabulary(self) -> None:
        policy = default_enhancement_policy()
        assert set(policy.observation_rules.enabled_categories) == set(ObservationCategory)


@pytest.mark.unit
class TestPolicyValidation:
    def test_negative_bound_rejected(self) -> None:
        from requirement_intelligence.enhancement.policy.enhancement_policy import (
            RelationshipRules,
        )

        with pytest.raises(ValidationError):
            RelationshipRules(max_relationships_per_requirement=-1)

    def test_policy_round_trips(self) -> None:
        policy = default_enhancement_policy()
        dumped = policy.model_dump(mode="json", by_alias=True)
        assert EnhancementPolicy.model_validate(dumped) == policy
