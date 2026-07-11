"""Builder for the governed :class:`MatchingPolicy`.

Construction only. It assembles the framework's default governed policy — a
deterministic, immutable value — and rejects nothing beyond the model's own field
constraints. It performs no matching and has no runtime consumers.

CAP-077A.5 shipped a weightless foundation; CAP-077B (this policy, version 2.0.0)
sets the meaningful weights and thresholds Strategy V1 matches against. These are
**governed data**: tuning them is a versioned policy change, never a matcher code
change, and the matcher hard-codes none of them.
"""

from __future__ import annotations

from requirement_intelligence.grounding.matching.enums import MatchRankingKey, MatchTieBreaker
from requirement_intelligence.grounding.matching.policy import (
    DEFAULT_MATCHING_POLICY_ID,
    MATCHING_POLICY_VERSION,
    MatchingPolicy,
)
from requirement_intelligence.grounding.matching.rules import (
    MatchingRanking,
    MatchingThresholds,
    MatchingTieBreaker,
    MatchingWeights,
)


class MatchingPolicyBuilder:
    """Assemble the governed default :class:`MatchingPolicy`."""

    def build(self) -> MatchingPolicy:
        """Return the framework's default governed matching policy."""
        return MatchingPolicy(
            policy_id=DEFAULT_MATCHING_POLICY_ID,
            policy_version=MATCHING_POLICY_VERSION,
            description="Default matching policy (CAP-077B): governed weights for Strategy V1.",
            thresholds=MatchingThresholds(
                minimum_match_score=1,
                minimum_token_overlap=1,
                minimum_exact_terms=0,
            ),
            weights=MatchingWeights(
                title_weight=5,
                description_weight=3,
                rule_key_weight=4,
                tag_weight=2,
                component_weight=2,
                endpoint_weight=2,
                exact_token_bonus=2,
                partial_token_bonus=1,
            ),
            ranking=MatchingRanking(
                keys=(
                    MatchRankingKey.MATCH_SCORE,
                    MatchRankingKey.EXACT_TERMS,
                    MatchRankingKey.TOKEN_OVERLAP,
                )
            ),
            tie_breaker=MatchingTieBreaker(key=MatchTieBreaker.SOURCE_RECORD_ID, ascending=True),
        )


def default_matching_policy() -> MatchingPolicy:
    """Return the framework's default governed matching policy."""
    return MatchingPolicyBuilder().build()
