"""The governed :class:`PromotionRuleCatalog` — an ordered collection of
promotion rules (CAP-085B).

A ``PromotionRuleCatalog`` owns **ordering, lookup, grouping, and
enabled-rule selection** over a set of :class:`PromotionRule` — and nothing
else. It performs **no capture, no clustering, no generation, no decision**:
it consumes neither a ``ContinuousImprovementResult`` nor a
``KnowledgeGraphResult``. The deterministic engine's collaborators iterate
the catalogue; the catalogue only holds and organises the governed rules
(mirroring the Knowledge Graph Framework's own governed rule catalogue,
ADR-0023, and the Continuous Improvement Framework's own, ADR-0022).

Determinism
-----------
Rules are stored in a single canonical order — ascending ``evaluationOrder``,
then ``ruleId`` as a stable tie-break — so iteration, serialization, and every
derived grouping are reproducible run after run, independent of insertion
order.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.organizational_memory.identity import PromotionRuleCatalogVersion
from requirement_intelligence.organizational_memory.rules.promotion_rule import (
    PromotionHierarchyLevel,
    PromotionRule,
    PromotionRuleCategory,
)
from shared.contracts.base import Schema

#: Version of the governed default rule catalogue (CAP-085B foundation).
PROMOTION_RULE_CATALOG_VERSION = PromotionRuleCatalogVersion(1, 0, 0)


def _canonical_order(rule: PromotionRule) -> tuple[int, str]:
    """The deterministic sort key: ``evaluation_order`` then ``rule_id``."""
    return (rule.evaluation_order, rule.rule_id)


class PromotionRuleCatalog(Schema):
    """A deterministic, ordered collection of governed :class:`PromotionRule`.

    The catalogue is immutable and self-contained. It exposes ordering,
    lookup by id, filtering by category or hierarchy level, and the
    enabled-only projection the engine consumes. It owns no behaviour beyond
    organising its rules.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    catalog_version: PromotionRuleCatalogVersion = Field(
        default=PROMOTION_RULE_CATALOG_VERSION,
        description="Version of this governed rule set.",
    )
    rules: tuple[PromotionRule, ...] = Field(
        default=(), description="The governed rules, stored in canonical order."
    )

    @model_validator(mode="after")
    def _validate_catalog(self) -> PromotionRuleCatalog:
        """Rules have unique ids and are stored in canonical order."""
        ids = [rule.rule_id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("Catalog rule ids must be unique.")
        if list(self.rules) != sorted(self.rules, key=_canonical_order):
            raise ValueError(
                "Catalog rules must be stored in canonical order "
                "(ascending evaluationOrder, then ruleId)."
            )
        return self

    def enabled_rules(self) -> tuple[PromotionRule, ...]:
        """Return the enabled rules only, in canonical order.

        The engine iterates exactly this projection: a catalogue-disabled
        rule is not evaluated at all, distinct from a policy-toggled-off rule
        (which the engine skips at generation time by reading the rule's
        ``capability_switch``).
        """
        return tuple(rule for rule in self.rules if rule.enabled)

    def rule(self, rule_id: str) -> PromotionRule | None:
        """Return the rule with *rule_id*, or ``None`` when absent."""
        for candidate in self.rules:
            if candidate.rule_id == rule_id:
                return candidate
        return None

    def by_category(self, category: PromotionRuleCategory) -> tuple[PromotionRule, ...]:
        """Return the enabled rules in *category*, in canonical order."""
        return tuple(rule for rule in self.enabled_rules() if rule.category == category)

    def by_hierarchy_level(
        self, level: PromotionHierarchyLevel
    ) -> tuple[PromotionRule, ...]:
        """Return the enabled rules supporting *level*, in canonical order."""
        return tuple(
            rule for rule in self.enabled_rules() if rule.supported_hierarchy_level == level
        )
