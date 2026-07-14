"""The canonical governed :class:`RecommendationPolicy`.

A ``RecommendationPolicy`` defines **what recommendation generation, prioritization,
grouping, and confidence scoring are allowed to do** — deterministic configuration and
enabled capability switches a future engine must obey. It is the Recommendation
Framework counterpart to the Requirement Enhancement ``EnhancementPolicy``, the
Quality Governance ``QualityPolicy``, and the Grounding ``MatchingPolicy``: an
immutable, declarative, governed rule set that contains **no executable logic**. A
future engine reads a policy and acts within it; the policy computes nothing.

Policy vs engine (frozen, ADR-0019)
------------------------------------
* ``RecommendationPolicy`` — the governed rules and switches (this file). Data only.
* A future deterministic / ML / LLM / hybrid recommendation engine (CAP-082B onward)
  — the behaviour that acts within them against the completed enhancement, grounding,
  validation, CP1, and quality governance results.

Tuning recommendation behaviour is therefore a *versioned policy change*, never an
engine code change, and it must never force a change to ``RecommendationResult`` or
the service contract (Recommendation 5: independent capability evolution).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.recommendation.identity.recommendation_identity import (
    RecommendationPolicyId,
    RecommendationPolicyVersion,
)
from requirement_intelligence.recommendation.models.enums import (
    RecommendationPriority,
    RecommendationType,
)
from shared.contracts.base import Schema


class RecommendationCapabilitySwitches(Schema):
    """Governed on/off switches for each recommendation capability. Data only.

    Each future capability (generation, prioritization, grouping, confidence
    scoring, and the future deterministic/ML/LLM engine families) is independently
    enabled/disabled here — a governed data change, never an engine change
    (Recommendation 5).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    enable_prioritization: bool = Field(
        default=True, description="Whether recommendation prioritization may run."
    )
    enable_grouping: bool = Field(
        default=True, description="Whether recommendation grouping may run."
    )
    enable_confidence_scoring: bool = Field(
        default=True, description="Whether recommendation confidence scoring may run."
    )
    enable_deterministic_engine: bool = Field(
        default=False,
        description="Whether the deterministic recommendation engine is enabled (CAP-082B).",
    )
    enable_ml_engine: bool = Field(
        default=False,
        description="Whether a future ML recommendation engine is enabled (reserved).",
    )
    enable_llm_engine: bool = Field(
        default=False,
        description="Whether a future LLM recommendation engine is enabled (reserved).",
    )


class PrioritizationRules(Schema):
    """Governed deterministic configuration for prioritization. Data only.

    Bounds a future prioritization engine must respect; it computes no priority
    itself.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    enabled_priorities: tuple[RecommendationPriority, ...] = Field(
        default=tuple(RecommendationPriority),
        description="Priority levels a future engine may assign.",
    )
    max_recommendations_per_priority: int = Field(
        ..., ge=0, description="Maximum recommendations a future engine may assign per priority."
    )


class GroupingRules(Schema):
    """Governed deterministic configuration for grouping. Data only."""

    model_config = ConfigDict(alias_generator=to_camel)

    enabled_categories: tuple[RecommendationType, ...] = Field(
        default=tuple(RecommendationType),
        description="Recommendation types a future engine may group recommendations under.",
    )
    max_recommendations_per_group: int = Field(
        ..., ge=0, description="Maximum recommendations a future engine may place in one group."
    )


class ConfidenceRules(Schema):
    """Governed deterministic thresholds for confidence scoring. Data only.

    Bounds a future confidence-scoring engine must respect; this model computes no
    confidence value itself (mirrors ``ConfidencePolicy``, ADR-0016 §D... no logic,
    thresholds only).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    minimum_confidence_to_surface: float = Field(
        ..., ge=0.0, le=1.0, description="Minimum confidence a recommendation must meet to surface."
    )
    high_confidence_threshold: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence at or above which a recommendation is high-confidence.",
    )

    @model_validator(mode="after")
    def _validate_thresholds(self) -> ConfidenceRules:
        """The surfacing floor must not exceed the high-confidence threshold."""
        if self.minimum_confidence_to_surface > self.high_confidence_threshold:
            raise ValueError(
                "minimum_confidence_to_surface must not exceed high_confidence_threshold."
            )
        return self


class ProjectionRules(Schema):
    """Governed deterministic configuration for future projection/reporting. Data only.

    A future serializer or Execution Package projection reads these bounds; this
    model performs no rendering and no projection itself (Recommendation 8: runtime
    before reporting).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    max_recommendations_in_summary: int = Field(
        ..., ge=0, description="Maximum recommendations a future summary projection may list."
    )
    include_low_priority_in_report: bool = Field(
        default=False, description="Whether a future report projection may include LOW priority."
    )


class RecommendationPolicy(Schema):
    """An immutable, declarative, governed rule set for recommendation generation."""

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: RecommendationPolicyId = Field(..., description="Governed policy identity.")
    policy_version: RecommendationPolicyVersion = Field(
        ..., description="Semantic policy version."
    )
    description: str = Field(..., min_length=1, description="Human-readable policy summary.")

    capability_switches: RecommendationCapabilitySwitches = Field(
        ..., description="Which recommendation capabilities are enabled."
    )
    prioritization_rules: PrioritizationRules = Field(
        ..., description="Governed deterministic configuration for prioritization."
    )
    grouping_rules: GroupingRules = Field(
        ..., description="Governed deterministic configuration for grouping."
    )
    confidence_rules: ConfidenceRules = Field(
        ..., description="Governed deterministic thresholds for confidence scoring."
    )
    projection_rules: ProjectionRules = Field(
        ..., description="Governed deterministic configuration for future projection."
    )
