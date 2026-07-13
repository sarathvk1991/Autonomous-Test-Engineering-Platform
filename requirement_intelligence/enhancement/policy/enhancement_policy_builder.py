"""Builder for the governed :class:`EnhancementPolicy`.

Construction only. It assembles the framework's default governed policy — a
deterministic, immutable value — and rejects nothing beyond the model's own field
constraints. It performs no enrichment, detects no relationship, generates no
observation, and has no runtime consumers.

CAP-081A ships the governed default at ``EnhancementPolicyVersion`` 1.0.0. The values
are **governed data**: tuning them is a versioned policy change, never an engine code
change, and no future engine hard-codes any of them (Recommendation 4).
"""

from __future__ import annotations

from requirement_intelligence.enhancement.identity.enhancement_identity import (
    EnhancementPolicyId,
)
from requirement_intelligence.enhancement.policy.enhancement_policy import (
    EnhancementCapabilitySwitches,
    EnhancementPolicy,
    EnrichmentRules,
    ObservationRules,
    RelationshipRules,
)
from requirement_intelligence.enhancement.version import ENHANCEMENT_POLICY_VERSION

#: The identity of the framework's default governed enhancement policy.
DEFAULT_ENHANCEMENT_POLICY_ID = EnhancementPolicyId("default-enhancement-policy")


class EnhancementPolicyBuilder:
    """Assemble the governed default :class:`EnhancementPolicy`."""

    def build(self) -> EnhancementPolicy:
        """Return the framework's default governed enhancement policy."""
        return EnhancementPolicy(
            policy_id=DEFAULT_ENHANCEMENT_POLICY_ID,
            policy_version=ENHANCEMENT_POLICY_VERSION,
            description=(
                "Default enhancement policy (CAP-081A): governed capability switches "
                "and deterministic configuration. Architecture freeze only — no "
                "capability is wired to a runtime engine yet."
            ),
            capability_switches=EnhancementCapabilitySwitches(
                enable_enrichment=True,
                enable_relationship_detection=True,
                enable_observation_generation=True,
                enable_completeness_analysis=False,
                enable_consistency_analysis=False,
            ),
            enrichment_rules=EnrichmentRules(
                max_attributes_per_requirement=10,
                attribute_key_vocabulary=(),
            ),
            relationship_rules=RelationshipRules(
                max_relationships_per_requirement=10,
            ),
            observation_rules=ObservationRules(
                max_observations_per_requirement=10,
            ),
        )


def default_enhancement_policy() -> EnhancementPolicy:
    """Return the framework's default governed enhancement policy."""
    return EnhancementPolicyBuilder().build()
