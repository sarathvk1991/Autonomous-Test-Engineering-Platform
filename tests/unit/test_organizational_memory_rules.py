"""Architecture-only tests for the governed :class:`PromotionRuleCatalog`
(CAP-085B, ADR-0027 §D14/§D17).

Covers the rule/catalogue shape, determinism, the builder's default 24-rule
catalogue across ten governed categories, and the "metadata only, no
threshold field" invariant. No behaviour is exercised — the catalogue is
data, iterated by the engine, never executed itself.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.organizational_memory.rules import (
    OrganizationalMemoryPolicyToggle,
    PromotionHierarchyLevel,
    PromotionRule,
    PromotionRuleBuilder,
    PromotionRuleCatalog,
    PromotionRuleCategory,
    default_promotion_rule_catalog,
)
from requirement_intelligence.organizational_memory.rules.promotion_rule import (
    PROMOTION_RULE_VERSION,
)
from requirement_intelligence.organizational_memory.rules.promotion_rule_catalog import (
    PROMOTION_RULE_CATALOG_VERSION,
)


def _rule(**overrides: object) -> PromotionRule:
    defaults: dict[str, object] = dict(
        rule_id="OM-TEST-001",
        title="Test rule",
        description="A test rule.",
        category=PromotionRuleCategory.EXPERIENCE_CAPTURE,
        priority=10,
        capability_switch=OrganizationalMemoryPolicyToggle.ENABLE_EXPERIENCE_CAPTURE,
        supported_hierarchy_level=PromotionHierarchyLevel.EXPERIENCE,
        documentation_reference="ADR-0027 §D9",
        evaluation_order=10,
    )
    defaults.update(overrides)
    return PromotionRule(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPromotionRule:
    def test_constructs_with_valid_fields(self) -> None:
        rule = _rule()
        assert rule.rule_id == "OM-TEST-001"
        assert rule.rule_version == PROMOTION_RULE_VERSION

    def test_is_immutable(self) -> None:
        rule = _rule()
        with pytest.raises(ValidationError):
            rule.title = "mutated"  # type: ignore[misc]

    def test_rejects_lowercase_rule_id(self) -> None:
        with pytest.raises(ValidationError):
            _rule(rule_id="om-test-001")

    def test_rejects_empty_title(self) -> None:
        with pytest.raises(ValidationError):
            _rule(title="")

    def test_rejects_empty_description(self) -> None:
        with pytest.raises(ValidationError):
            _rule(description="")

    def test_rejects_negative_priority(self) -> None:
        with pytest.raises(ValidationError):
            _rule(priority=-1)

    def test_rejects_negative_evaluation_order(self) -> None:
        with pytest.raises(ValidationError):
            _rule(evaluation_order=-1)

    def test_enabled_defaults_true(self) -> None:
        assert _rule().enabled is True

    def test_carries_no_numeric_threshold_field(self) -> None:
        """Recommendation 16 of ADR-0027: rules never carry an executable threshold."""
        forbidden = {
            "minimum_experiences",
            "minimum_lessons",
            "confidence_threshold",
            "threshold",
        }
        assert not (forbidden & set(PromotionRule.model_fields))

    def test_round_trips(self) -> None:
        rule = _rule()
        dumped = rule.model_dump(mode="json", by_alias=True)
        assert PromotionRule.model_validate(dumped) == rule


@pytest.mark.unit
class TestPromotionRuleCatalog:
    def test_constructs_empty(self) -> None:
        catalog = PromotionRuleCatalog()
        assert catalog.rules == ()
        assert catalog.catalog_version == PROMOTION_RULE_CATALOG_VERSION

    def test_rejects_duplicate_rule_ids(self) -> None:
        rule_a = _rule(evaluation_order=10)
        rule_b = _rule(evaluation_order=20)
        with pytest.raises(ValidationError):
            PromotionRuleCatalog(rules=(rule_a, rule_b))

    def test_rejects_out_of_order_rules(self) -> None:
        rule_a = _rule(rule_id="OM-TEST-002", evaluation_order=20)
        rule_b = _rule(rule_id="OM-TEST-001", evaluation_order=10)
        with pytest.raises(ValidationError):
            PromotionRuleCatalog(rules=(rule_a, rule_b))

    def test_accepts_canonically_ordered_rules(self) -> None:
        rule_a = _rule(rule_id="OM-TEST-001", evaluation_order=10)
        rule_b = _rule(rule_id="OM-TEST-002", evaluation_order=20)
        catalog = PromotionRuleCatalog(rules=(rule_a, rule_b))
        assert catalog.rules == (rule_a, rule_b)

    def test_enabled_rules_excludes_disabled(self) -> None:
        rule_a = _rule(rule_id="OM-TEST-001", evaluation_order=10, enabled=True)
        rule_b = _rule(rule_id="OM-TEST-002", evaluation_order=20, enabled=False)
        catalog = PromotionRuleCatalog(rules=(rule_a, rule_b))
        assert catalog.enabled_rules() == (rule_a,)

    def test_rule_lookup_by_id(self) -> None:
        rule = _rule()
        catalog = PromotionRuleCatalog(rules=(rule,))
        assert catalog.rule("OM-TEST-001") == rule
        assert catalog.rule("OM-MISSING") is None

    def test_by_category_filters_correctly(self) -> None:
        rule_a = _rule(rule_id="OM-TEST-001", evaluation_order=10)
        rule_b = _rule(
            rule_id="OM-TEST-002",
            evaluation_order=20,
            category=PromotionRuleCategory.LIFECYCLE,
            supported_hierarchy_level=PromotionHierarchyLevel.LIFECYCLE,
            capability_switch=OrganizationalMemoryPolicyToggle.ENABLE_RETIREMENT,
        )
        catalog = PromotionRuleCatalog(rules=(rule_a, rule_b))
        assert catalog.by_category(PromotionRuleCategory.EXPERIENCE_CAPTURE) == (rule_a,)
        assert catalog.by_category(PromotionRuleCategory.LIFECYCLE) == (rule_b,)

    def test_by_hierarchy_level_filters_correctly(self) -> None:
        rule_a = _rule(rule_id="OM-TEST-001", evaluation_order=10)
        rule_b = _rule(
            rule_id="OM-TEST-002",
            evaluation_order=20,
            supported_hierarchy_level=PromotionHierarchyLevel.LESSON,
            capability_switch=OrganizationalMemoryPolicyToggle.ENABLE_LESSON_PROMOTION,
        )
        catalog = PromotionRuleCatalog(rules=(rule_a, rule_b))
        assert catalog.by_hierarchy_level(PromotionHierarchyLevel.EXPERIENCE) == (rule_a,)
        assert catalog.by_hierarchy_level(PromotionHierarchyLevel.LESSON) == (rule_b,)

    def test_is_immutable(self) -> None:
        catalog = PromotionRuleCatalog(rules=(_rule(),))
        with pytest.raises(ValidationError):
            catalog.rules = ()  # type: ignore[misc]


@pytest.mark.unit
class TestPromotionRuleBuilder:
    def test_builds_twenty_four_governed_rules(self) -> None:
        catalog = PromotionRuleBuilder().build()
        assert len(catalog.rules) == 24

    def test_all_rules_enabled_by_default(self) -> None:
        catalog = PromotionRuleBuilder().build()
        assert len(catalog.enabled_rules()) == 24

    def test_covers_all_ten_governed_categories(self) -> None:
        catalog = PromotionRuleBuilder().build()
        categories = {rule.category for rule in catalog.rules}
        assert categories == set(PromotionRuleCategory)

    def test_experience_capture_has_six_rules(self) -> None:
        catalog = PromotionRuleBuilder().build()
        assert len(catalog.by_category(PromotionRuleCategory.EXPERIENCE_CAPTURE)) == 6

    @pytest.mark.parametrize(
        "category",
        [
            PromotionRuleCategory.EXPERIENCE_CONSOLIDATION,
            PromotionRuleCategory.LESSON_GENERATION,
            PromotionRuleCategory.LESSON_CONSOLIDATION,
            PromotionRuleCategory.BEST_PRACTICE_GENERATION,
            PromotionRuleCategory.PROMOTION,
            PromotionRuleCategory.LIFECYCLE,
            PromotionRuleCategory.EXPLAINABILITY,
            PromotionRuleCategory.DETERMINISM,
            PromotionRuleCategory.STRUCTURAL_INTEGRITY,
        ],
    )
    def test_every_other_category_has_two_rules(self, category: PromotionRuleCategory) -> None:
        catalog = PromotionRuleBuilder().build()
        assert len(catalog.by_category(category)) == 2

    def test_module_level_helper_matches_builder(self) -> None:
        assert default_promotion_rule_catalog() == PromotionRuleBuilder().build()

    def test_repeated_calls_return_equal_but_independent_catalogs(self) -> None:
        a = default_promotion_rule_catalog()
        b = default_promotion_rule_catalog()
        assert a == b
        assert a is not b

    def test_every_rule_names_a_documentation_reference(self) -> None:
        catalog = PromotionRuleBuilder().build()
        for rule in catalog.rules:
            assert rule.documentation_reference

    def test_no_rule_has_executable_behaviour(self) -> None:
        """No lambda, no callback — every field is data (str/int/bool/enum)."""
        catalog = PromotionRuleBuilder().build()
        for rule in catalog.rules:
            for value in rule.model_dump().values():
                assert not callable(value)
