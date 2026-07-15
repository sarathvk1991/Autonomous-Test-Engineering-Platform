"""The governed :class:`KnowledgeGraphRuleCatalog` — an ordered collection of
knowledge graph rules (CAP-084B).

A ``KnowledgeGraphRuleCatalog`` owns **ordering, lookup, grouping, and
enabled-rule selection** over a set of :class:`KnowledgeGraphRule` — and
nothing else. It performs **no projection, no analysis, no decision**: it
neither reads a Historical Dataset nor a policy value. The deterministic
engine's projectors and analyzers iterate the catalogue; the catalogue only
holds and organises the governed rules (mirroring the Continuous Improvement
Framework's own governed rule catalogue, ADR-0022).

Determinism
-----------
Rules are stored in a single canonical order — ascending ``evaluation_order``,
then ``rule_id`` as a stable tie-break — so iteration, serialization, and every
derived grouping are reproducible run after run, independent of insertion
order.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.knowledge_graph.identity import KnowledgeGraphRuleCatalogVersion
from requirement_intelligence.knowledge_graph.rules.knowledge_graph_rule import (
    KnowledgeGraphRule,
    KnowledgeGraphRuleFamily,
)
from shared.contracts.base import Schema

#: Version of the governed default rule catalogue (CAP-084B foundation).
KNOWLEDGE_GRAPH_RULE_CATALOG_VERSION = KnowledgeGraphRuleCatalogVersion(1, 0, 0)


def _canonical_order(rule: KnowledgeGraphRule) -> tuple[int, str]:
    """The deterministic sort key: ``evaluation_order`` then ``rule_id``."""
    return (rule.evaluation_order, rule.rule_id)


class KnowledgeGraphRuleCatalog(Schema):
    """A deterministic, ordered collection of governed :class:`KnowledgeGraphRule`.

    The catalogue is immutable and self-contained. It exposes ordering, lookup
    by id, filtering by family, and the enabled-only projection the engine
    consumes. It owns no behaviour beyond organising its rules.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    catalog_version: KnowledgeGraphRuleCatalogVersion = Field(
        default=KNOWLEDGE_GRAPH_RULE_CATALOG_VERSION,
        description="Version of this governed rule set.",
    )
    rules: tuple[KnowledgeGraphRule, ...] = Field(
        default=(), description="The governed rules, stored in canonical order."
    )

    @model_validator(mode="after")
    def _validate_catalog(self) -> KnowledgeGraphRuleCatalog:
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

    def enabled_rules(self) -> tuple[KnowledgeGraphRule, ...]:
        """Return the enabled rules only, in canonical order.

        The engine iterates exactly this projection: a catalogue-disabled rule
        is not evaluated at all, distinct from a policy-toggled-off rule (which
        the engine skips at generation time by reading the rule's
        ``policy_reference``).
        """
        return tuple(rule for rule in self.rules if rule.enabled)

    def rule(self, rule_id: str) -> KnowledgeGraphRule | None:
        """Return the rule with *rule_id*, or ``None`` when absent."""
        for candidate in self.rules:
            if candidate.rule_id == rule_id:
                return candidate
        return None

    def by_family(self, family: KnowledgeGraphRuleFamily) -> tuple[KnowledgeGraphRule, ...]:
        """Return the enabled rules in *family*, in canonical order."""
        return tuple(rule for rule in self.enabled_rules() if rule.family == family)
