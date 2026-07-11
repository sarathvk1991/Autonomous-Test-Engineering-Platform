"""Governed Matching Policy framework (CAP-077A.5).

Owns matching **policy** only — the governed decision rules for *what constitutes a
match*. It performs no matching, no normalization, no classification, and no
confidence calculation; a ``GroundingStrategy`` reads a :class:`MatchingPolicy` and
implements the comparison.
"""

from __future__ import annotations

from requirement_intelligence.grounding.matching.enums import MatchRankingKey, MatchTieBreaker
from requirement_intelligence.grounding.matching.policy import (
    DEFAULT_MATCHING_POLICY_ID,
    MATCHING_POLICY_VERSION,
    MatchingPolicy,
)
from requirement_intelligence.grounding.matching.policy_builder import (
    MatchingPolicyBuilder,
    default_matching_policy,
)
from requirement_intelligence.grounding.matching.rules import (
    MatchingRanking,
    MatchingThresholds,
    MatchingTieBreaker,
    MatchingWeights,
)

__all__ = [
    "DEFAULT_MATCHING_POLICY_ID",
    "MATCHING_POLICY_VERSION",
    "MatchRankingKey",
    "MatchTieBreaker",
    "MatchingPolicy",
    "MatchingPolicyBuilder",
    "MatchingRanking",
    "MatchingThresholds",
    "MatchingTieBreaker",
    "MatchingWeights",
    "default_matching_policy",
]
