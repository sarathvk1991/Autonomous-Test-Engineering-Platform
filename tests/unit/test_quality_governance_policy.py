"""Unit tests for the governed QualityPolicy and its builder (CAP-080A).

The policy is governed data only — immutable, versioned, deterministic. The builder
constructs; it evaluates nothing. These tests assert construction and shape, never a
governance calculation, because none exists yet.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.quality_governance.policy import (
    DEFAULT_QUALITY_POLICY_ID,
    QualityPolicy,
    QualityPolicyBuilder,
    QualityThresholds,
    default_quality_policy,
)
from requirement_intelligence.quality_governance.version import QUALITY_POLICY_VERSION


@pytest.mark.unit
class TestDefaultPolicy:
    def test_default_is_versioned_and_identified(self) -> None:
        policy = default_quality_policy()
        assert policy.policy_id == DEFAULT_QUALITY_POLICY_ID
        assert policy.policy_version == QUALITY_POLICY_VERSION

    def test_builder_is_deterministic(self) -> None:
        assert QualityPolicyBuilder().build() == QualityPolicyBuilder().build()

    def test_policy_is_immutable(self) -> None:
        policy = default_quality_policy()
        with pytest.raises(ValidationError):
            policy.description = "changed"  # type: ignore[misc]

    def test_two_bands_are_present_and_distinct(self) -> None:
        # The decision is not a single-score threshold: FAIL and WARNING are two
        # separate governed bands (ADR-0017 Recommendation 7).
        policy = default_quality_policy()
        assert policy.failure_thresholds != policy.warning_thresholds

    def test_mandatory_release_rules_present(self) -> None:
        rules = default_quality_policy().release_rules
        assert rules.block_on_hallucination
        assert rules.block_on_validation_failure
        assert rules.block_on_cp1_failure
        assert rules.require_engineering_readiness

    def test_per_source_severity_budgets_present(self) -> None:
        policy = default_quality_policy()
        assert policy.validation_severity_thresholds.max_critical == 0
        assert policy.cp1_severity_thresholds.max_critical == 0


@pytest.mark.unit
class TestPolicyValidation:
    def test_rate_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            QualityThresholds(
                minimum_grounding_score=50,
                maximum_hallucination_rate=1.5,
                minimum_confidence=50,
                minimum_evidence_coverage=0.5,
            )

    def test_score_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            QualityThresholds(
                minimum_grounding_score=200,
                maximum_hallucination_rate=0.1,
                minimum_confidence=50,
                minimum_evidence_coverage=0.5,
            )

    def test_policy_round_trips(self) -> None:
        policy = default_quality_policy()
        dumped = policy.model_dump(mode="json", by_alias=True)
        assert QualityPolicy.model_validate(dumped) == policy
