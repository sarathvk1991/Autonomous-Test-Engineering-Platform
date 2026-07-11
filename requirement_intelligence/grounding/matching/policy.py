"""The canonical governed :class:`MatchingPolicy`.

A ``MatchingPolicy`` defines **what constitutes a match** — the thresholds, weights,
permitted relations, ranking, and tie-breaking a matcher must obey. It is the
counterpart to the Engineering Context Orchestration ``OrchestrationPolicy``: an
immutable, declarative, governed rule set. It contains **no executable logic**; the
grounding strategy reads a policy and implements the comparison.

Policy vs configuration vs algorithm
------------------------------------
* ``NormalizationConfiguration`` — mechanical preprocessing switches.
* ``MatchingPolicy`` — the governed decision rules for what counts as a match.
* ``GroundingStrategy`` — the algorithm that applies the policy to normalized text.

Tuning matching behaviour is therefore a *versioned policy change*, never an
algorithm change — the property that lets one policy serve a deterministic, a
semantic, and a hybrid matcher unchanged.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity import MatchingPolicyId, MatchingPolicyVersion
from requirement_intelligence.grounding.matching.rules import (
    MatchingRanking,
    MatchingThresholds,
    MatchingTieBreaker,
    MatchingWeights,
)
from shared.contracts.base import Schema

#: Version of the governed matching policy shape / default. Advances additively;
#: any change that could alter which links a prior policy admits is MAJOR and
#: re-baselines the golden dataset. 2.0.0 (CAP-077B) replaces the CAP-077A.5
#: weightless foundation with the meaningful weights and thresholds Strategy V1
#: matches against — a governed data change (no matcher code depends on the values).
#: The policy is unwired, so no execution artifact or golden baseline carries the
#: 1.0.0 values; the bump invalidates no stored data.
MATCHING_POLICY_VERSION = MatchingPolicyVersion(2, 0, 0)

#: The identity of the framework's default governed matching policy.
DEFAULT_MATCHING_POLICY_ID = MatchingPolicyId("default-matching-policy")


class MatchingPolicy(Schema):
    """An immutable, declarative, governed rule set for what constitutes a match."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: MatchingPolicyId = Field(..., description="Governed policy identity.")
    policy_version: MatchingPolicyVersion = Field(..., description="Semantic policy version.")
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    thresholds: MatchingThresholds = Field(..., description="Minimum bars a match must clear.")
    weights: MatchingWeights = Field(..., description="Per-field/per-kind scoring weights.")
    ranking: MatchingRanking = Field(..., description="Ordered ranking keys.")
    tie_breaker: MatchingTieBreaker = Field(..., description="Final total-order tie-breaker.")

    allow_cross_domain_matching: bool = Field(
        default=True, description="Permit a requirement to match evidence in another domain."
    )
    allow_partial_matching: bool = Field(default=True, description="Permit PARTIAL relation links.")
    allow_derived_matching: bool = Field(default=True, description="Permit DERIVED relation links.")
    allow_negative_matching: bool = Field(
        default=True, description="Permit NEGATIVE relation links."
    )
    allow_contradicting_matching: bool = Field(
        default=True, description="Permit CONTRADICTING relation links."
    )
