"""Builder for the governed :class:`MatchingPolicy`.

Construction only. It assembles the framework's default governed policy — a
deterministic, immutable value — and rejects nothing beyond the model's own field
constraints. It performs no matching and has no runtime consumers.

The default is intentionally *permissive and weightless*: every relation is allowed
and every weight is zero at CAP-077A.5. The first strategy (CAP-077B) sets meaningful
weights and thresholds by advancing the policy version under the golden re-baseline
procedure — a governed data change, not a code change.
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
            description="Default matching policy (CAP-077A.5): permissive, weightless foundation.",
            thresholds=MatchingThresholds(),
            weights=MatchingWeights(),
            ranking=MatchingRanking(
                keys=(MatchRankingKey.MATCH_SCORE, MatchRankingKey.EXACT_TERMS)
            ),
            tie_breaker=MatchingTieBreaker(key=MatchTieBreaker.SOURCE_RECORD_ID, ascending=True),
        )


def default_matching_policy() -> MatchingPolicy:
    """Return the framework's default governed matching policy."""
    return MatchingPolicyBuilder().build()
