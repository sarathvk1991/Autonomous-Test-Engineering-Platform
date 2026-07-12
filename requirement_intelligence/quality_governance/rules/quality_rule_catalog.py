"""The governed :class:`QualityRuleCatalog` — an ordered collection of quality rules (CAP-080B).

A ``QualityRuleCatalog`` owns **ordering, lookup, grouping, and enabled-rule
selection** over a set of :class:`QualityRule` — and nothing else. It performs **no
evaluation**: it neither reads an upstream result nor a threshold, and it makes no
decision. The :class:`DeterministicQualityRuleEvaluator` iterates the catalogue; the
catalogue only holds and organises the governed rules (ADR-0017 §D25).

Determinism
-----------
Rules are stored in a single canonical order — ascending ``evaluation_order``, then
``rule_id`` as a stable tie-break — so iteration, serialization, and every derived
grouping are reproducible run after run, independent of insertion order.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.quality_governance.evaluation.models import RuleCategory
from requirement_intelligence.quality_governance.identity.quality_identity import (
    QualityRuleCatalogVersion,
)
from requirement_intelligence.quality_governance.rules.quality_rule import QualityRule
from shared.contracts.base import Schema

#: Version of the governed default rule catalogue (CAP-080B foundation).
QUALITY_RULE_CATALOG_VERSION = QualityRuleCatalogVersion(1, 0, 0)


def _canonical_order(rule: QualityRule) -> tuple[int, str]:
    """The deterministic sort key: ``evaluation_order`` then ``rule_id``."""
    return (rule.evaluation_order, rule.rule_id)


class QualityRuleCatalog(Schema):
    """A deterministic, ordered collection of governed :class:`QualityRule`.

    The catalogue is immutable and self-contained. It exposes ordering, lookup by id,
    grouping by category, and the enabled-only projection the evaluator consumes. It
    owns no behaviour beyond organising its rules.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    catalog_version: QualityRuleCatalogVersion = Field(
        default=QUALITY_RULE_CATALOG_VERSION, description="Version of this governed rule set."
    )
    rules: tuple[QualityRule, ...] = Field(
        default=(), description="The governed rules, stored in canonical order."
    )

    @model_validator(mode="after")
    def _validate_catalog(self) -> QualityRuleCatalog:
        """Rules have unique ids and are stored in canonical order.

        Uniqueness keeps lookup unambiguous; the canonical-order invariant guarantees
        that two catalogues with the same rules serialise identically regardless of how
        they were assembled. No value is computed.
        """
        ids = [rule.rule_id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("Catalog rule ids must be unique.")
        if list(self.rules) != sorted(self.rules, key=_canonical_order):
            raise ValueError(
                "Catalog rules must be stored in canonical order "
                "(ascending evaluationOrder, then ruleId)."
            )
        return self

    def enabled_rules(self) -> tuple[QualityRule, ...]:
        """Return the enabled rules only, in canonical order.

        The evaluator iterates exactly this projection: a disabled rule is not
        evaluated at all (it produces no evaluation), distinct from a ``SKIPPED`` one.
        """
        return tuple(rule for rule in self.rules if rule.enabled)

    def rule(self, rule_id: str) -> QualityRule | None:
        """Return the rule with *rule_id*, or ``None`` when absent."""
        for candidate in self.rules:
            if candidate.rule_id == rule_id:
                return candidate
        return None

    def by_category(self, category: RuleCategory) -> tuple[QualityRule, ...]:
        """Return the rules in *category*, in canonical order."""
        return tuple(rule for rule in self.rules if rule.category == category)
