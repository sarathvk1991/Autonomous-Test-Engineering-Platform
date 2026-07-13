"""The canonical governed :class:`EnhancementPolicy`.

An ``EnhancementPolicy`` defines **what enrichment, relationship detection, and
observation generation are allowed to do** — deterministic configuration and enabled
capability switches a future engine must obey. It is the Requirement Enhancement
counterpart to the Quality Governance ``QualityPolicy`` and the Grounding
``MatchingPolicy``: an immutable, declarative, governed rule set that contains **no
executable logic**. A future engine reads a policy and acts within it; the policy
computes nothing.

Policy vs engine (frozen, ADR-0018)
------------------------------------
* ``EnhancementPolicy`` — the governed rules and switches (this file). Data only.
* A future enrichment / relationship-detection / observation engine — the behaviour
  that acts within them against a completed ``EngineeringContext`` /
  ``AnalysisResult``.

Tuning enhancement behaviour is therefore a *versioned policy change*, never an engine
code change, and it must never force a change to ``RequirementEnhancementResult`` or
the service contract (Recommendation 4: independent capability evolution).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.enhancement.identity.enhancement_identity import (
    EnhancementPolicyId,
    EnhancementPolicyVersion,
)
from requirement_intelligence.enhancement.models.enums import (
    ObservationCategory,
    RelationshipType,
)
from shared.contracts.base import Schema


class EnhancementCapabilitySwitches(Schema):
    """Governed on/off switches for each enhancement capability. Data only.

    Each future capability (enrichment, relationship detection, observation
    generation, completeness analysis, consistency analysis) is independently
    enabled/disabled here — a governed data change, never an engine change
    (Recommendation 4).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    enable_enrichment: bool = Field(default=True, description="Whether enrichment may run.")
    enable_relationship_detection: bool = Field(
        default=True, description="Whether relationship detection may run."
    )
    enable_observation_generation: bool = Field(
        default=True, description="Whether observation generation may run."
    )
    enable_completeness_analysis: bool = Field(
        default=False,
        description="Whether completeness analysis may run (reserved, Recommendation 7).",
    )
    enable_consistency_analysis: bool = Field(
        default=False,
        description="Whether consistency analysis may run (reserved, Recommendation 7).",
    )


class EnrichmentRules(Schema):
    """Governed deterministic configuration for enrichment. Data only.

    Bounds a future enrichment engine must respect; it computes no attribute itself.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    max_attributes_per_requirement: int = Field(
        ..., ge=0, description="Maximum EnhancementAttribute entries per requirement."
    )
    attribute_key_vocabulary: tuple[str, ...] = Field(
        default=(), description="Governed vocabulary of attribute keys a future engine may attach."
    )


class RelationshipRules(Schema):
    """Governed deterministic configuration for relationship detection. Data only."""

    model_config = ConfigDict(alias_generator=to_camel)

    enabled_relationship_types: tuple[RelationshipType, ...] = Field(
        default=tuple(RelationshipType),
        description="Relationship types a future detection engine may record.",
    )
    max_relationships_per_requirement: int = Field(
        ..., ge=0, description="Maximum relationship edges per requirement."
    )


class ObservationRules(Schema):
    """Governed deterministic configuration for observation generation. Data only."""

    model_config = ConfigDict(alias_generator=to_camel)

    enabled_categories: tuple[ObservationCategory, ...] = Field(
        default=tuple(ObservationCategory),
        description="Observation categories a future engine may record.",
    )
    max_observations_per_requirement: int = Field(
        ..., ge=0, description="Maximum observations naming a single requirement."
    )


class EnhancementPolicy(Schema):
    """An immutable, declarative, governed rule set for requirement enhancement."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: EnhancementPolicyId = Field(..., description="Governed policy identity.")
    policy_version: EnhancementPolicyVersion = Field(..., description="Semantic policy version.")
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    capability_switches: EnhancementCapabilitySwitches = Field(
        ..., description="Which enhancement capabilities are enabled."
    )
    enrichment_rules: EnrichmentRules = Field(
        ..., description="Governed deterministic configuration for enrichment."
    )
    relationship_rules: RelationshipRules = Field(
        ..., description="Governed deterministic configuration for relationship detection."
    )
    observation_rules: ObservationRules = Field(
        ..., description="Governed deterministic configuration for observation generation."
    )
