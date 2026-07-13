"""The governed :class:`EnhancementRuleCatalog` — an ordered collection of enhancement
rules (CAP-081B).

An ``EnhancementRuleCatalog`` owns **ordering, lookup, grouping, and enabled-rule
selection** over a set of :class:`EnhancementRule` — and nothing else. It performs
**no enhancement**: it neither reads an ``EngineeringContext``/``AnalysisResult`` nor a
policy value, and it makes no decision. The
:class:`~requirement_intelligence.enhancement.engine.DeterministicRequirementEnhancementEngine`
iterates the catalogue; the catalogue only holds and organises the governed rules
(mirroring ``QualityRuleCatalog``, ADR-0017 §D25).

Determinism
-----------
Rules are stored in a single canonical order — ascending ``evaluation_order``, then
``rule_id`` as a stable tie-break — so iteration, serialization, and every derived
grouping are reproducible run after run, independent of insertion order.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.enhancement.identity.enhancement_identity import (
    EnhancementRuleCatalogVersion,
)
from requirement_intelligence.enhancement.rules.enhancement_rule import (
    EnhancementMechanism,
    EnhancementRule,
    EnhancementRuleCategory,
)
from shared.contracts.base import Schema

#: Version of the governed default rule catalogue (CAP-081B foundation).
ENHANCEMENT_RULE_CATALOG_VERSION = EnhancementRuleCatalogVersion(1, 0, 0)


def _canonical_order(rule: EnhancementRule) -> tuple[int, str]:
    """The deterministic sort key: ``evaluation_order`` then ``rule_id``."""
    return (rule.evaluation_order, rule.rule_id)


class EnhancementRuleCatalog(Schema):
    """A deterministic, ordered collection of governed :class:`EnhancementRule`.

    The catalogue is immutable and self-contained. It exposes ordering, lookup by id
    or mechanism, grouping by category, and the enabled-only projection the engine
    consumes. It owns no behaviour beyond organising its rules.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    catalog_version: EnhancementRuleCatalogVersion = Field(
        default=ENHANCEMENT_RULE_CATALOG_VERSION, description="Version of this governed rule set."
    )
    rules: tuple[EnhancementRule, ...] = Field(
        default=(), description="The governed rules, stored in canonical order."
    )

    @model_validator(mode="after")
    def _validate_catalog(self) -> EnhancementRuleCatalog:
        """Rules have unique ids and mechanisms, and are stored in canonical order."""
        ids = [rule.rule_id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("Catalog rule ids must be unique.")
        mechanisms = [rule.mechanism for rule in self.rules]
        if len(mechanisms) != len(set(mechanisms)):
            raise ValueError("Catalog rule mechanisms must be unique (one rule per mechanism).")
        if list(self.rules) != sorted(self.rules, key=_canonical_order):
            raise ValueError(
                "Catalog rules must be stored in canonical order "
                "(ascending evaluationOrder, then ruleId)."
            )
        return self

    def enabled_rules(self) -> tuple[EnhancementRule, ...]:
        """Return the enabled rules only, in canonical order.

        The engine iterates exactly this projection: a catalogue-disabled rule is not
        evaluated at all, distinct from a policy-toggled-off rule (which the engine
        skips at evaluation time by reading the rule's ``capability_switch``).
        """
        return tuple(rule for rule in self.rules if rule.enabled)

    def rule(self, rule_id: str) -> EnhancementRule | None:
        """Return the rule with *rule_id*, or ``None`` when absent."""
        for candidate in self.rules:
            if candidate.rule_id == rule_id:
                return candidate
        return None

    def rule_for_mechanism(self, mechanism: EnhancementMechanism) -> EnhancementRule | None:
        """Return the rule naming *mechanism*, or ``None`` when absent."""
        for candidate in self.rules:
            if candidate.mechanism == mechanism:
                return candidate
        return None

    def by_category(self, category: EnhancementRuleCategory) -> tuple[EnhancementRule, ...]:
        """Return the rules in *category*, in canonical order."""
        return tuple(rule for rule in self.rules if rule.category == category)
