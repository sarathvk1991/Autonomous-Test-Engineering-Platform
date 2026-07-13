"""Unit tests for the governed EnhancementRuleCatalog and its builder (CAP-081B).

The catalogue is governed data only — immutable, versioned, deterministic. The builder
constructs; it evaluates nothing. These tests assert construction, shape, ordering, and
lookup, never an enhancement computation (that belongs to ``test_enhancement_engine.py``).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.enhancement.models.enums import EnhancementSeverity
from requirement_intelligence.enhancement.rules import (
    EnhancementCapabilityToggle,
    EnhancementMechanism,
    EnhancementPolicyRef,
    EnhancementRule,
    EnhancementRuleBuilder,
    EnhancementRuleCatalog,
    EnhancementRuleCategory,
    default_enhancement_rule_catalog,
)
from requirement_intelligence.enhancement.rules.enhancement_rule_catalog import (
    ENHANCEMENT_RULE_CATALOG_VERSION,
)


@pytest.mark.unit
class TestDefaultCatalog:
    def test_default_is_versioned(self) -> None:
        catalog = default_enhancement_rule_catalog()
        assert catalog.catalog_version == ENHANCEMENT_RULE_CATALOG_VERSION

    def test_builder_is_deterministic(self) -> None:
        assert EnhancementRuleBuilder().build() == EnhancementRuleBuilder().build()

    def test_catalog_is_immutable(self) -> None:
        catalog = default_enhancement_rule_catalog()
        with pytest.raises(ValidationError):
            catalog.rules = ()  # type: ignore[misc]

    def test_spans_all_three_categories(self) -> None:
        catalog = default_enhancement_rule_catalog()
        categories = {rule.category for rule in catalog.rules}
        assert categories == set(EnhancementRuleCategory)

    def test_thirteen_governed_rules(self) -> None:
        # 3 enrichment + 4 relationship + 6 observation mechanisms (Stage 1-6).
        assert len(default_enhancement_rule_catalog().rules) == 13

    def test_every_mechanism_has_exactly_one_rule(self) -> None:
        catalog = default_enhancement_rule_catalog()
        mechanisms = [rule.mechanism for rule in catalog.rules]
        assert set(mechanisms) == set(EnhancementMechanism)
        assert len(mechanisms) == len(set(mechanisms))

    def test_rules_stored_in_canonical_order(self) -> None:
        catalog = default_enhancement_rule_catalog()
        orders = [rule.evaluation_order for rule in catalog.rules]
        assert orders == sorted(orders)


@pytest.mark.unit
class TestCatalogLookup:
    def test_enabled_rules_returns_only_enabled(self) -> None:
        catalog = default_enhancement_rule_catalog()
        assert catalog.enabled_rules() == catalog.rules  # all default-enabled

        disabled_first = catalog.rules[0].model_copy(update={"enabled": False})
        modified = EnhancementRuleCatalog(rules=(disabled_first, *catalog.rules[1:]))
        assert len(modified.enabled_rules()) == len(catalog.rules) - 1

    def test_rule_lookup_by_id(self) -> None:
        catalog = default_enhancement_rule_catalog()
        found = catalog.rule("ER-ENR-001")
        assert found is not None
        assert found.mechanism == EnhancementMechanism.STABLE_IDENTITY_ASSIGNMENT
        assert catalog.rule("does-not-exist") is None

    def test_rule_lookup_by_mechanism(self) -> None:
        catalog = default_enhancement_rule_catalog()
        found = catalog.rule_for_mechanism(EnhancementMechanism.DUPLICATE_REQUIREMENT_TEXT)
        assert found is not None
        assert found.rule_id == "ER-REL-001"

    def test_by_category_returns_only_that_category(self) -> None:
        catalog = default_enhancement_rule_catalog()
        relationship_rules = catalog.by_category(EnhancementRuleCategory.RELATIONSHIP)
        assert len(relationship_rules) == 4
        assert all(
            rule.category == EnhancementRuleCategory.RELATIONSHIP for rule in relationship_rules
        )


@pytest.mark.unit
class TestRuleValidation:
    def test_mechanism_category_mismatch_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EnhancementRule(
                rule_id="ER-BAD-001",
                rule_name="Mismatched rule",
                category=EnhancementRuleCategory.ENRICHMENT,
                mechanism=EnhancementMechanism.ISOLATED_REQUIREMENT,  # an OBSERVATION mechanism
                capability_switch=EnhancementCapabilityToggle.ENABLE_ENRICHMENT,
                policy_ref=EnhancementPolicyRef.ENRICHMENT_RULES,
                description="Deliberately wrong category.",
                evaluation_order=999,
            )

    def test_duplicate_rule_ids_rejected(self) -> None:
        catalog = default_enhancement_rule_catalog()
        duplicate = catalog.rules[0]
        with pytest.raises(ValidationError):
            EnhancementRuleCatalog(rules=(duplicate, duplicate))

    def test_duplicate_mechanisms_rejected(self) -> None:
        catalog = default_enhancement_rule_catalog()
        first, second = catalog.rules[0], catalog.rules[1]
        clashing = second.model_copy(update={"mechanism": first.mechanism, "rule_id": "ER-X-999"})
        with pytest.raises(ValidationError):
            EnhancementRuleCatalog(rules=(first, clashing))

    def test_out_of_order_rules_rejected(self) -> None:
        catalog = default_enhancement_rule_catalog()
        with pytest.raises(ValidationError):
            EnhancementRuleCatalog(rules=tuple(reversed(catalog.rules)))

    def test_rule_round_trips(self) -> None:
        catalog = default_enhancement_rule_catalog()
        dumped = catalog.model_dump(mode="json", by_alias=True)
        assert EnhancementRuleCatalog.model_validate(dumped) == catalog

    def test_default_severity_is_info(self) -> None:
        rule = EnhancementRule(
            rule_id="ER-X-001",
            rule_name="Default severity",
            category=EnhancementRuleCategory.ENRICHMENT,
            mechanism=EnhancementMechanism.STABLE_IDENTITY_ASSIGNMENT,
            capability_switch=EnhancementCapabilityToggle.ENABLE_ENRICHMENT,
            policy_ref=EnhancementPolicyRef.ENRICHMENT_RULES,
            description="Uses the default severity.",
            evaluation_order=1,
        )
        assert rule.severity == EnhancementSeverity.INFO

    def test_rule_version_defaults_to_governed_constant(self) -> None:
        from requirement_intelligence.enhancement.rules.enhancement_rule import (
            ENHANCEMENT_RULE_VERSION,
        )

        rule = default_enhancement_rule_catalog().rules[0]
        assert rule.rule_version == ENHANCEMENT_RULE_VERSION
