"""Unit tests for the governed Matching Policy framework (CAP-077A.5).

Cover the policy and rule models (immutability, serialization, equality, versioning),
the builder (deterministic, immutable output), the PlatformContext registration, and
the architectural boundary (policy is data; the strategy holds no policy, the policy
holds no algorithm).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.grounding import (
    MATCHING_POLICY_VERSION,
    MatchingPolicy,
    MatchingPolicyBuilder,
    MatchingPolicyId,
    MatchingPolicyVersion,
    MatchingRanking,
    MatchingThresholds,
    MatchingTieBreaker,
    MatchingWeights,
    default_matching_policy,
)
from requirement_intelligence.grounding.matching import MatchRankingKey, MatchTieBreaker
from requirement_intelligence.platform.platform_context import PlatformContext


@pytest.mark.unit
class TestMatchingRuleModels:
    def test_thresholds_bound_match_score(self) -> None:
        with pytest.raises(ValidationError):
            MatchingThresholds(minimum_match_score=101)

    def test_weights_default_to_zero(self) -> None:
        weights = MatchingWeights()
        assert weights.title_weight == 0
        assert weights.cross_source_bonus == 0

    def test_ranking_requires_at_least_one_key(self) -> None:
        with pytest.raises(ValidationError):
            MatchingRanking(keys=())

    def test_tie_breaker_constructs(self) -> None:
        tb = MatchingTieBreaker(key=MatchTieBreaker.SOURCE_RECORD_ID)
        assert tb.ascending is True


@pytest.mark.unit
class TestMatchingPolicy:
    def test_default_is_versioned_and_identified(self) -> None:
        policy = default_matching_policy()
        assert isinstance(policy.policy_id, MatchingPolicyId)
        assert policy.policy_version == MATCHING_POLICY_VERSION
        assert isinstance(policy.policy_version, MatchingPolicyVersion)

    def test_is_immutable(self) -> None:
        policy = default_matching_policy()
        with pytest.raises(ValidationError):
            policy.allow_partial_matching = False  # type: ignore[misc]

    def test_serialises_camel_case_and_round_trips(self) -> None:
        policy = default_matching_policy()
        dumped = policy.model_dump(mode="json", by_alias=True)
        assert dumped["policyVersion"] == "1.0.0"
        assert "allowCrossDomainMatching" in dumped
        assert "tieBreaker" in dumped
        assert MatchingPolicy.model_validate(dumped) == policy

    def test_default_ranking_and_tie_breaker(self) -> None:
        policy = default_matching_policy()
        assert policy.ranking.keys[0] == MatchRankingKey.MATCH_SCORE
        assert policy.tie_breaker.key == MatchTieBreaker.SOURCE_RECORD_ID


@pytest.mark.unit
class TestMatchingPolicyBuilder:
    def test_build_is_deterministic(self) -> None:
        assert MatchingPolicyBuilder().build() == MatchingPolicyBuilder().build()

    def test_produces_an_immutable_policy(self) -> None:
        policy = MatchingPolicyBuilder().build()
        with pytest.raises(ValidationError):
            policy.thresholds = MatchingThresholds()  # type: ignore[misc]


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_factory_returns_default_policy(self) -> None:
        policy = PlatformContext().create_matching_policy()
        assert isinstance(policy, MatchingPolicy)
        assert policy.policy_version == MATCHING_POLICY_VERSION


@pytest.mark.unit
class TestArchitecturalBoundary:
    def test_policy_carries_only_data_no_callables(self) -> None:
        """A MatchingPolicy is governed data: none of its fields is executable."""
        policy = default_matching_policy()
        for value in policy.model_dump().values():
            assert not callable(value)

    def test_policy_package_imports_no_algorithm(self) -> None:
        """MatchingPolicy is governed data: it must not depend on the matcher or its output.

        Checks *imports* (not docstrings): the policy package imports neither the
        strategy contract nor ``MatchResult``, proving the dependency runs
        algorithm→policy, never the reverse.
        """
        from pathlib import Path

        import requirement_intelligence.grounding.matching as matching_pkg

        package_dir = Path(matching_pkg.__file__).parent
        for module in package_dir.glob("*.py"):
            for line in module.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")):
                    assert "grounding_strategy" not in stripped
                    assert "match_result" not in stripped
                    assert "MatchResult" not in stripped
