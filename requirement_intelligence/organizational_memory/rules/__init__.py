"""The governed :class:`PromotionRuleCatalog` and its builder (CAP-085B)."""

from __future__ import annotations

from requirement_intelligence.organizational_memory.rules.promotion_rule import (
    OrganizationalMemoryPolicyToggle,
    PromotionHierarchyLevel,
    PromotionRule,
    PromotionRuleCategory,
)
from requirement_intelligence.organizational_memory.rules.promotion_rule_builder import (
    PromotionRuleBuilder,
    default_promotion_rule_catalog,
)
from requirement_intelligence.organizational_memory.rules.promotion_rule_catalog import (
    PROMOTION_RULE_CATALOG_VERSION,
    PromotionRuleCatalog,
)

__all__ = [
    "PROMOTION_RULE_CATALOG_VERSION",
    "OrganizationalMemoryPolicyToggle",
    "PromotionHierarchyLevel",
    "PromotionRule",
    "PromotionRuleBuilder",
    "PromotionRuleCatalog",
    "PromotionRuleCategory",
    "default_promotion_rule_catalog",
]
