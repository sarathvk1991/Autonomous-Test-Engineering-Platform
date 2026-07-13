"""The canonical governed :class:`EnhancementRule` and its controlled vocabularies (CAP-081B).

An ``EnhancementRule`` is **metadata only** — the governed declaration of *what*
deterministic mechanism an enhancement rule names, *which* governed policy substructure
scopes it, and *which* capability switch gates it. It carries **no executable
behaviour**: no lambda, no callable, no embedded threshold, no calculation. The
:class:`~requirement_intelligence.enhancement.engine.DeterministicRequirementEnhancementEngine`
owns the behaviour; a rule only *names* it — exactly mirroring how ``QualityRule``
relates to its deterministic Quality Governance rule evaluator (ADR-0017 §D25).

The declaration is fully governed and deterministic:

* :class:`EnhancementRuleCategory` — which of the three CAP-081A capability lanes
  (enrichment / relationship / observation) the rule belongs to.
* :class:`EnhancementMechanism` — the governed vocabulary of deterministic mechanisms
  the engine dispatches on (Stage 3/4/5, ADR-0018 §D31 precedent for named,
  non-computed vocabularies).
* :class:`EnhancementCapabilityToggle` — which governed
  ``EnhancementCapabilitySwitches`` field gates this rule at evaluation time; a
  disabled toggle makes the engine skip the rule entirely (no output, not an error).
* :class:`EnhancementPolicyRef` — which governed ``EnhancementPolicy`` substructure
  scopes the rule's deterministic bounds (max counts, enabled vocabularies) — a rule
  never carries a literal bound; it names the policy section that owns one
  (Recommendation 4: independent capability evolution via governed data, never an
  engine change).

Because a rule is data, adding, removing, or retuning a rule is a versioned catalogue
change (an ``EnhancementRuleBuilder`` edit), never an engine code change.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.enhancement.identity.enhancement_identity import (
    EnhancementRuleVersion,
)
from requirement_intelligence.enhancement.models.enums import EnhancementSeverity
from shared.contracts.base import Schema

#: Version of the governed ``EnhancementRule`` **schema** (CAP-081B foundation).
ENHANCEMENT_RULE_VERSION = EnhancementRuleVersion(1, 0, 0)


class EnhancementRuleCategory(StrEnum):
    """Which of the three CAP-081A capability lanes a rule belongs to."""

    ENRICHMENT = "enrichment"
    RELATIONSHIP = "relationship"
    OBSERVATION = "observation"


class EnhancementMechanism(StrEnum):
    """The governed vocabulary of deterministic mechanisms the engine dispatches on.

    Each member names one deterministic procedure the engine performs — string
    comparison, keyword-triggered substring matching, or graph traversal. No member
    implies semantic similarity, embeddings, statistics, or AI (Stage 3/4 of CAP-081B).
    """

    # Enrichment (Stage 3).
    STABLE_IDENTITY_ASSIGNMENT = "stable_identity_assignment"
    PROVENANCE_ATTRIBUTE = "provenance_attribute"
    TRACEABILITY_ATTRIBUTE = "traceability_attribute"

    # Relationship (Stage 4) — all keyword-triggered, deterministic substring matches.
    DUPLICATE_REQUIREMENT_TEXT = "duplicate_requirement_text"
    EXPLICIT_DEPENDENCY_REFERENCE = "explicit_dependency_reference"
    REFINEMENT_REFERENCE = "refinement_reference"
    PARENT_CHILD_REFERENCE = "parent_child_reference"

    # Observation (Stage 5) — derived only from enhanced requirements + the graph.
    ISOLATED_REQUIREMENT = "isolated_requirement"
    ORPHAN_REQUIREMENT = "orphan_requirement"
    DUPLICATE_REQUIREMENT_OBSERVATION = "duplicate_requirement_observation"
    DISCONNECTED_GRAPH = "disconnected_graph"
    MISSING_DEPENDENCY = "missing_dependency"
    RELATIONSHIP_INCONSISTENCY = "relationship_inconsistency"


#: The category each mechanism belongs to — a fixed, governed lookup, never a
#: computation. Enforced as a shape invariant by :meth:`EnhancementRule._validate_rule`.
_MECHANISM_CATEGORY: dict[EnhancementMechanism, EnhancementRuleCategory] = {
    EnhancementMechanism.STABLE_IDENTITY_ASSIGNMENT: EnhancementRuleCategory.ENRICHMENT,
    EnhancementMechanism.PROVENANCE_ATTRIBUTE: EnhancementRuleCategory.ENRICHMENT,
    EnhancementMechanism.TRACEABILITY_ATTRIBUTE: EnhancementRuleCategory.ENRICHMENT,
    EnhancementMechanism.DUPLICATE_REQUIREMENT_TEXT: EnhancementRuleCategory.RELATIONSHIP,
    EnhancementMechanism.EXPLICIT_DEPENDENCY_REFERENCE: EnhancementRuleCategory.RELATIONSHIP,
    EnhancementMechanism.REFINEMENT_REFERENCE: EnhancementRuleCategory.RELATIONSHIP,
    EnhancementMechanism.PARENT_CHILD_REFERENCE: EnhancementRuleCategory.RELATIONSHIP,
    EnhancementMechanism.ISOLATED_REQUIREMENT: EnhancementRuleCategory.OBSERVATION,
    EnhancementMechanism.ORPHAN_REQUIREMENT: EnhancementRuleCategory.OBSERVATION,
    EnhancementMechanism.DUPLICATE_REQUIREMENT_OBSERVATION: EnhancementRuleCategory.OBSERVATION,
    EnhancementMechanism.DISCONNECTED_GRAPH: EnhancementRuleCategory.OBSERVATION,
    EnhancementMechanism.MISSING_DEPENDENCY: EnhancementRuleCategory.OBSERVATION,
    EnhancementMechanism.RELATIONSHIP_INCONSISTENCY: EnhancementRuleCategory.OBSERVATION,
}


class EnhancementCapabilityToggle(StrEnum):
    """A governed ``EnhancementCapabilitySwitches`` field that gates a rule.

    Names the switch rather than the rule reading it directly, so retuning which
    capability gates a rule is a catalogue change, and flipping the switch itself is a
    policy change — neither is an engine change.
    """

    ENABLE_ENRICHMENT = "enable_enrichment"
    ENABLE_RELATIONSHIP_DETECTION = "enable_relationship_detection"
    ENABLE_OBSERVATION_GENERATION = "enable_observation_generation"
    ENABLE_COMPLETENESS_ANALYSIS = "enable_completeness_analysis"
    ENABLE_CONSISTENCY_ANALYSIS = "enable_consistency_analysis"


class EnhancementPolicyRef(StrEnum):
    """*Which* governed :class:`EnhancementPolicy` substructure scopes a rule.

    A rule names a policy section rather than carrying a literal bound, so every
    deterministic limit (max attributes, max relationships, max observations, enabled
    vocabularies) is governed data tuned by a versioned policy change.
    """

    NONE = "none"
    ENRICHMENT_RULES = "enrichment_rules"
    RELATIONSHIP_RULES = "relationship_rules"
    OBSERVATION_RULES = "observation_rules"


class EnhancementRule(Schema):
    """One governed enhancement rule — immutable metadata, no behaviour.

    A rule declares the governed mechanism it names (:attr:`mechanism`), the capability
    switch that gates it (:attr:`capability_switch`), and the policy section that
    scopes it (:attr:`policy_ref`). It carries no executable logic; the engine resolves
    both the switch and the policy section and applies the named mechanism.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    rule_id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[A-Z0-9][A-Z0-9._:-]*$",
        description="Stable, governed rule identity (e.g. 'ER-ENR-001').",
    )
    rule_version: EnhancementRuleVersion = Field(
        default=ENHANCEMENT_RULE_VERSION, description="Version of this rule's definition."
    )
    rule_name: str = Field(..., min_length=1, description="Human-readable rule name.")
    category: EnhancementRuleCategory = Field(
        ..., description="The capability lane this rule governs."
    )
    mechanism: EnhancementMechanism = Field(
        ..., description="The governed deterministic mechanism the engine applies."
    )
    capability_switch: EnhancementCapabilityToggle = Field(
        ..., description="The governed policy switch that gates this rule."
    )
    policy_ref: EnhancementPolicyRef = Field(
        ..., description="Which governed EnhancementPolicy substructure scopes this rule."
    )
    severity: EnhancementSeverity = Field(
        default=EnhancementSeverity.INFO,
        description="For an OBSERVATION-category rule, the severity its output carries.",
    )
    description: str = Field(..., min_length=1, description="What the rule governs and why.")
    enabled: bool = Field(default=True, description="Whether the catalogue evaluates this rule.")
    evaluation_order: int = Field(
        ..., ge=0, description="Deterministic ordering key within the catalogue."
    )

    @model_validator(mode="after")
    def _validate_rule(self) -> EnhancementRule:
        """The mechanism must belong to the declared category — a shape invariant only."""
        expected = _MECHANISM_CATEGORY[self.mechanism]
        if expected != self.category:
            raise ValueError(
                f"Rule '{self.rule_id}' names mechanism {self.mechanism!r} which belongs to "
                f"category {expected!r}, not the declared {self.category!r}."
            )
        return self
