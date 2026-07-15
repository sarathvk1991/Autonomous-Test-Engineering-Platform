"""Builder for the governed :class:`RecommendationPolicy`.

Construction only. It assembles the framework's default governed policy — a
deterministic, immutable value — and rejects nothing beyond the model's own field
constraints. It generates no recommendation, prioritizes nothing, groups nothing,
and has no runtime consumers.

CAP-082A shipped the governed default at ``RecommendationPolicyVersion`` 1.0.0 with
``enable_deterministic_engine`` reserved off. CAP-082B advances it to 1.1.0 and flips
that switch to ``True`` now that ``DeterministicRecommendationEngine`` exists. The
values are **governed data**: tuning them is a versioned policy change, never an
engine code change, and no future engine hard-codes any of them (Recommendation 5).
"""

from __future__ import annotations

from requirement_intelligence.recommendation.identity.recommendation_identity import (
    RecommendationPolicyId,
)
from requirement_intelligence.recommendation.policy.recommendation_policy import (
    ConfidenceRules,
    GroupingRules,
    PrioritizationRules,
    ProjectionRules,
    RecommendationCapabilitySwitches,
    RecommendationPolicy,
)
from requirement_intelligence.recommendation.version import RECOMMENDATION_POLICY_VERSION

#: The identity of the framework's default governed recommendation policy.
DEFAULT_RECOMMENDATION_POLICY_ID = RecommendationPolicyId("default-recommendation-policy")


class RecommendationPolicyBuilder:
    """Assemble the governed default :class:`RecommendationPolicy`."""

    def build(self) -> RecommendationPolicy:
        """Return the framework's default governed recommendation policy."""
        return RecommendationPolicy(
            policy_id=DEFAULT_RECOMMENDATION_POLICY_ID,
            policy_version=RECOMMENDATION_POLICY_VERSION,
            description=(
                "Default recommendation policy (CAP-082B): governed capability "
                "switches and deterministic configuration. The deterministic engine "
                "is enabled; the framework remains unwired into the runtime pipeline."
            ),
            capability_switches=RecommendationCapabilitySwitches(
                enable_prioritization=True,
                enable_grouping=True,
                enable_confidence_scoring=True,
                enable_deterministic_engine=True,
                enable_ml_engine=False,
                enable_llm_engine=False,
            ),
            prioritization_rules=PrioritizationRules(
                max_recommendations_per_priority=25,
            ),
            grouping_rules=GroupingRules(
                max_recommendations_per_group=25,
            ),
            confidence_rules=ConfidenceRules(
                minimum_confidence_to_surface=0.5,
                high_confidence_threshold=0.8,
            ),
            projection_rules=ProjectionRules(
                max_recommendations_in_summary=10,
                include_low_priority_in_report=False,
            ),
        )


def default_recommendation_policy() -> RecommendationPolicy:
    """Return the framework's default governed recommendation policy."""
    return RecommendationPolicyBuilder().build()
