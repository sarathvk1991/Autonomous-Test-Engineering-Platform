"""Builder for the governed default :class:`EnhancementRuleCatalog` (CAP-081B).

Construction only. It assembles the framework's default governed rule catalogue — a
deterministic, immutable value — and rejects nothing beyond the models' own field and
invariant constraints. It performs no enhancement, reads no upstream input, and has no
runtime consumers beyond the engine that iterates it.

The catalogue is **governed data**. Future rule additions, removals, or retunings
require only a builder change, never an engine code change (Recommendation 4). Every
deterministic bound lives in the :class:`EnhancementPolicy`; a rule here only names
*which* policy section scopes it (:class:`EnhancementPolicyRef`).

The default catalogue spans all three governed :class:`EnhancementRuleCategory` values
— enrichment, relationship, observation — so the deterministic engine exercises every
category from day one.
"""

from __future__ import annotations

from requirement_intelligence.enhancement.models.enums import EnhancementSeverity
from requirement_intelligence.enhancement.rules.enhancement_rule import (
    EnhancementCapabilityToggle,
    EnhancementMechanism,
    EnhancementPolicyRef,
    EnhancementRule,
    EnhancementRuleCategory,
)
from requirement_intelligence.enhancement.rules.enhancement_rule_catalog import (
    ENHANCEMENT_RULE_CATALOG_VERSION,
    EnhancementRuleCatalog,
)


class EnhancementRuleBuilder:
    """Assemble the governed default :class:`EnhancementRuleCatalog`."""

    def build(self) -> EnhancementRuleCatalog:
        """Return the framework's default governed rule catalogue, in canonical order."""
        rules = (
            # ---- Enrichment --------------------------------------------------
            EnhancementRule(
                rule_id="ER-ENR-001",
                rule_name="Assign a stable enhanced-requirement identity",
                category=EnhancementRuleCategory.ENRICHMENT,
                mechanism=EnhancementMechanism.STABLE_IDENTITY_ASSIGNMENT,
                capability_switch=EnhancementCapabilityToggle.ENABLE_ENRICHMENT,
                policy_ref=EnhancementPolicyRef.ENRICHMENT_RULES,
                description=(
                    "Every generated requirement receives a deterministic "
                    "EnhancedRequirementId, a pure function of the enhancement run and "
                    "the requirement id."
                ),
                evaluation_order=10,
            ),
            EnhancementRule(
                rule_id="ER-ENR-002",
                rule_name="Attach a deterministic provenance attribute",
                category=EnhancementRuleCategory.ENRICHMENT,
                mechanism=EnhancementMechanism.PROVENANCE_ATTRIBUTE,
                capability_switch=EnhancementCapabilityToggle.ENABLE_ENRICHMENT,
                policy_ref=EnhancementPolicyRef.ENRICHMENT_RULES,
                description=(
                    "Attach the source domain and response position as a deterministic "
                    "'provenance' attribute — where the requirement came from."
                ),
                evaluation_order=20,
            ),
            EnhancementRule(
                rule_id="ER-ENR-003",
                rule_name="Attach a deterministic traceability attribute",
                category=EnhancementRuleCategory.ENRICHMENT,
                mechanism=EnhancementMechanism.TRACEABILITY_ATTRIBUTE,
                capability_switch=EnhancementCapabilityToggle.ENABLE_ENRICHMENT,
                policy_ref=EnhancementPolicyRef.ENRICHMENT_RULES,
                description=(
                    "Attach a deterministic 'traceability' attribute recording the "
                    "analysis and execution ids the requirement was generated under."
                ),
                evaluation_order=30,
            ),
            # ---- Relationship --------------------------------------------------
            EnhancementRule(
                rule_id="ER-REL-001",
                rule_name="Detect duplicate requirement text",
                category=EnhancementRuleCategory.RELATIONSHIP,
                mechanism=EnhancementMechanism.DUPLICATE_REQUIREMENT_TEXT,
                capability_switch=EnhancementCapabilityToggle.ENABLE_RELATIONSHIP_DETECTION,
                policy_ref=EnhancementPolicyRef.RELATIONSHIP_RULES,
                description=(
                    "Two requirements whose normalized text is identical are recorded as "
                    "DUPLICATES — an exact string match, never semantic similarity."
                ),
                evaluation_order=40,
            ),
            EnhancementRule(
                rule_id="ER-REL-002",
                rule_name="Detect an explicit dependency reference",
                category=EnhancementRuleCategory.RELATIONSHIP,
                mechanism=EnhancementMechanism.EXPLICIT_DEPENDENCY_REFERENCE,
                capability_switch=EnhancementCapabilityToggle.ENABLE_RELATIONSHIP_DETECTION,
                policy_ref=EnhancementPolicyRef.RELATIONSHIP_RULES,
                description=(
                    "A requirement containing a governed dependency keyword that also "
                    "contains another requirement's text verbatim is recorded as "
                    "DEPENDS_ON — keyword-triggered substring matching only."
                ),
                evaluation_order=50,
            ),
            EnhancementRule(
                rule_id="ER-REL-003",
                rule_name="Detect an explicit refinement reference",
                category=EnhancementRuleCategory.RELATIONSHIP,
                mechanism=EnhancementMechanism.REFINEMENT_REFERENCE,
                capability_switch=EnhancementCapabilityToggle.ENABLE_RELATIONSHIP_DETECTION,
                policy_ref=EnhancementPolicyRef.RELATIONSHIP_RULES,
                description=(
                    "A requirement containing a governed refinement keyword that also "
                    "contains another requirement's text verbatim is recorded as "
                    "REFINES — keyword-triggered substring matching only."
                ),
                evaluation_order=60,
            ),
            EnhancementRule(
                rule_id="ER-REL-004",
                rule_name="Detect an explicit parent-child reference",
                category=EnhancementRuleCategory.RELATIONSHIP,
                mechanism=EnhancementMechanism.PARENT_CHILD_REFERENCE,
                capability_switch=EnhancementCapabilityToggle.ENABLE_RELATIONSHIP_DETECTION,
                policy_ref=EnhancementPolicyRef.RELATIONSHIP_RULES,
                description=(
                    "A requirement containing a governed parent-child keyword that also "
                    "contains another requirement's text verbatim is recorded as "
                    "DERIVED_FROM — keyword-triggered substring matching only."
                ),
                evaluation_order=70,
            ),
            # ---- Observation -----------------------------------------------------
            EnhancementRule(
                rule_id="ER-OBS-001",
                rule_name="Observe an isolated requirement",
                category=EnhancementRuleCategory.OBSERVATION,
                mechanism=EnhancementMechanism.ISOLATED_REQUIREMENT,
                capability_switch=EnhancementCapabilityToggle.ENABLE_OBSERVATION_GENERATION,
                policy_ref=EnhancementPolicyRef.OBSERVATION_RULES,
                severity=EnhancementSeverity.INFO,
                description="A requirement with no edges at all in the relationship graph.",
                evaluation_order=80,
            ),
            EnhancementRule(
                rule_id="ER-OBS-002",
                rule_name="Observe an orphan requirement",
                category=EnhancementRuleCategory.OBSERVATION,
                mechanism=EnhancementMechanism.ORPHAN_REQUIREMENT,
                capability_switch=EnhancementCapabilityToggle.ENABLE_OBSERVATION_GENERATION,
                policy_ref=EnhancementPolicyRef.OBSERVATION_RULES,
                severity=EnhancementSeverity.INFO,
                description=(
                    "A requirement that is only ever the target of a relationship — "
                    "other requirements reference it, but it references nothing itself."
                ),
                evaluation_order=90,
            ),
            EnhancementRule(
                rule_id="ER-OBS-003",
                rule_name="Observe a duplicate requirement",
                category=EnhancementRuleCategory.OBSERVATION,
                mechanism=EnhancementMechanism.DUPLICATE_REQUIREMENT_OBSERVATION,
                capability_switch=EnhancementCapabilityToggle.ENABLE_OBSERVATION_GENERATION,
                policy_ref=EnhancementPolicyRef.OBSERVATION_RULES,
                severity=EnhancementSeverity.WARNING,
                description="One observation per DUPLICATES edge already in the graph.",
                evaluation_order=100,
            ),
            EnhancementRule(
                rule_id="ER-OBS-004",
                rule_name="Observe a disconnected graph",
                category=EnhancementRuleCategory.OBSERVATION,
                mechanism=EnhancementMechanism.DISCONNECTED_GRAPH,
                capability_switch=EnhancementCapabilityToggle.ENABLE_OBSERVATION_GENERATION,
                policy_ref=EnhancementPolicyRef.OBSERVATION_RULES,
                severity=EnhancementSeverity.WARNING,
                description=(
                    "The relationship graph has more than one connected component — a "
                    "set-level observation naming every requirement in the run."
                ),
                evaluation_order=110,
            ),
            EnhancementRule(
                rule_id="ER-OBS-005",
                rule_name="Observe a missing dependency",
                category=EnhancementRuleCategory.OBSERVATION,
                mechanism=EnhancementMechanism.MISSING_DEPENDENCY,
                capability_switch=EnhancementCapabilityToggle.ENABLE_OBSERVATION_GENERATION,
                policy_ref=EnhancementPolicyRef.OBSERVATION_RULES,
                severity=EnhancementSeverity.WARNING,
                description=(
                    "A requirement contains a dependency keyword but no other "
                    "requirement's text could be deterministically resolved from it."
                ),
                evaluation_order=120,
            ),
            EnhancementRule(
                rule_id="ER-OBS-006",
                rule_name="Observe a relationship inconsistency",
                category=EnhancementRuleCategory.OBSERVATION,
                mechanism=EnhancementMechanism.RELATIONSHIP_INCONSISTENCY,
                capability_switch=EnhancementCapabilityToggle.ENABLE_OBSERVATION_GENERATION,
                policy_ref=EnhancementPolicyRef.OBSERVATION_RULES,
                severity=EnhancementSeverity.CRITICAL,
                description=(
                    "A cycle exists in the DEPENDS_ON subgraph — a circular dependency, "
                    "detected by deterministic graph traversal."
                ),
                evaluation_order=130,
            ),
        )
        return EnhancementRuleCatalog(catalog_version=ENHANCEMENT_RULE_CATALOG_VERSION, rules=rules)


def default_enhancement_rule_catalog() -> EnhancementRuleCatalog:
    """Return the framework's default governed rule catalogue."""
    return EnhancementRuleBuilder().build()
