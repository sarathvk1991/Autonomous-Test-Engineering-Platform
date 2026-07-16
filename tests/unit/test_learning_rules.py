"""Tests for the governed :class:`LearningRuleCatalog` (CAP-086B).

Covers the builder, the default catalogue, category/hierarchy-level
filtering, canonical ordering, and rejection of malformed catalogues. No
algorithm reads this catalogue's threshold values — it is metadata only
(ADR-0029 D6, Stage 3 of the CAP-086B brief).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.learning.identity import LearningRuleCatalogVersion
from requirement_intelligence.learning.rules import (
    LEARNING_RULE_CATALOG_VERSION,
    LearningHierarchyLevel,
    LearningPolicyToggle,
    LearningRule,
    LearningRuleBuilder,
    LearningRuleCatalog,
    LearningRuleCategory,
    default_learning_rule_catalog,
)

_ALL_CATEGORIES = tuple(LearningRuleCategory)


def _rule(**overrides: object) -> LearningRule:
    defaults: dict[str, object] = dict(
        rule_id="LN-TEST-001",
        title="Test rule",
        description="A test rule.",
        category=LearningRuleCategory.DETERMINISM,
        priority=10,
        capability_switch=LearningPolicyToggle.ENABLE_CANDIDATE_PROPOSAL,
        supported_hierarchy_level=LearningHierarchyLevel.CANDIDATE,
        documentation_reference="ADR-0029 D18",
        evaluation_order=10,
    )
    defaults.update(overrides)
    return LearningRule(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestLearningRule:
    def test_constructs_with_valid_fields(self) -> None:
        rule = _rule()
        assert rule.rule_id == "LN-TEST-001"

    def test_is_immutable(self) -> None:
        rule = _rule()
        with pytest.raises(ValidationError):
            rule.title = "mutated"  # type: ignore[misc]

    def test_rejects_lowercase_rule_id(self) -> None:
        with pytest.raises(ValidationError):
            _rule(rule_id="ln-test-001")

    def test_rejects_empty_title(self) -> None:
        with pytest.raises(ValidationError):
            _rule(title="")

    def test_rejects_empty_documentation_reference(self) -> None:
        with pytest.raises(ValidationError):
            _rule(documentation_reference="")

    def test_rejects_negative_priority(self) -> None:
        with pytest.raises(ValidationError):
            _rule(priority=-1)

    def test_default_rule_version_is_1_0_0(self) -> None:
        assert str(_rule().rule_version) == "1.0.0"

    def test_enabled_defaults_true(self) -> None:
        assert _rule().enabled is True

    def test_round_trips(self) -> None:
        rule = _rule()
        dumped = rule.model_dump(mode="json", by_alias=True)
        assert LearningRule.model_validate(dumped) == rule

    def test_serializes_camel_case(self) -> None:
        dumped = _rule().model_dump(mode="json", by_alias=True)
        assert "ruleId" in dumped
        assert "capabilitySwitch" in dumped
        assert "supportedHierarchyLevel" in dumped
        assert "evaluationOrder" in dumped


@pytest.mark.unit
class TestGovernedVocabularies:
    def test_category_has_exactly_twelve_members(self) -> None:
        assert len(_ALL_CATEGORIES) == 12

    def test_hierarchy_level_has_exactly_six_members(self) -> None:
        assert {member.value for member in LearningHierarchyLevel} == {
            "candidate",
            "learning",
            "validation",
            "confidence",
            "promotion",
            "lifecycle",
        }

    def test_policy_toggle_matches_the_four_governed_capability_switches(self) -> None:
        assert {member.value for member in LearningPolicyToggle} == {
            "enable_candidate_proposal",
            "enable_validation",
            "enable_confidence_recording",
            "enable_lifecycle_recording",
        }


@pytest.mark.unit
class TestLearningRuleCatalog:
    def test_constructs_empty_catalog(self) -> None:
        catalog = LearningRuleCatalog()
        assert catalog.rules == ()

    def test_rejects_duplicate_rule_ids(self) -> None:
        with pytest.raises(ValidationError):
            LearningRuleCatalog(rules=(_rule(evaluation_order=10), _rule(evaluation_order=20)))

    def test_rejects_out_of_order_rules(self) -> None:
        first = _rule(rule_id="LN-A-001", evaluation_order=20)
        second = _rule(rule_id="LN-B-001", evaluation_order=10)
        with pytest.raises(ValidationError):
            LearningRuleCatalog(rules=(first, second))

    def test_accepts_rules_already_in_canonical_order(self) -> None:
        first = _rule(rule_id="LN-A-001", evaluation_order=10)
        second = _rule(rule_id="LN-B-001", evaluation_order=20)
        catalog = LearningRuleCatalog(rules=(first, second))
        assert catalog.rules == (first, second)

    def test_is_immutable(self) -> None:
        catalog = LearningRuleCatalog()
        with pytest.raises(ValidationError):
            catalog.rules = (_rule(),)  # type: ignore[misc]

    def test_enabled_rules_excludes_disabled(self) -> None:
        enabled = _rule(rule_id="LN-A-001", evaluation_order=10, enabled=True)
        disabled = _rule(rule_id="LN-B-001", evaluation_order=20, enabled=False)
        catalog = LearningRuleCatalog(rules=(enabled, disabled))
        assert catalog.enabled_rules() == (enabled,)

    def test_rule_lookup_by_id(self) -> None:
        rule = _rule()
        catalog = LearningRuleCatalog(rules=(rule,))
        assert catalog.rule("LN-TEST-001") == rule

    def test_rule_lookup_returns_none_for_missing_id(self) -> None:
        catalog = LearningRuleCatalog()
        assert catalog.rule("LN-MISSING-001") is None

    def test_by_category_filters_correctly(self) -> None:
        determinism = _rule(rule_id="LN-A-001", evaluation_order=10)
        validation = _rule(
            rule_id="LN-B-001", evaluation_order=20, category=LearningRuleCategory.VALIDATION
        )
        catalog = LearningRuleCatalog(rules=(determinism, validation))
        assert catalog.by_category(LearningRuleCategory.VALIDATION) == (validation,)

    def test_by_hierarchy_level_filters_correctly(self) -> None:
        candidate = _rule(rule_id="LN-A-001", evaluation_order=10)
        learning = _rule(
            rule_id="LN-B-001",
            evaluation_order=20,
            supported_hierarchy_level=LearningHierarchyLevel.LEARNING,
        )
        catalog = LearningRuleCatalog(rules=(candidate, learning))
        assert catalog.by_hierarchy_level(LearningHierarchyLevel.LEARNING) == (learning,)


@pytest.mark.unit
class TestLearningRuleBuilder:
    def test_builds_twenty_four_rules(self) -> None:
        catalog = LearningRuleBuilder().build()
        assert len(catalog.rules) == 24

    def test_default_catalog_version_is_1_0_0(self) -> None:
        catalog = LearningRuleBuilder().build()
        assert str(catalog.catalog_version) == "1.0.0"

    def test_default_catalog_spans_every_governed_category(self) -> None:
        catalog = LearningRuleBuilder().build()
        represented = {rule.category for rule in catalog.rules}
        assert represented == set(_ALL_CATEGORIES)

    @pytest.mark.parametrize("category", _ALL_CATEGORIES)
    def test_every_category_has_at_least_two_rules(self, category: LearningRuleCategory) -> None:
        catalog = LearningRuleBuilder().build()
        assert len(catalog.by_category(category)) >= 2

    def test_all_default_rules_are_enabled(self) -> None:
        catalog = LearningRuleBuilder().build()
        assert catalog.enabled_rules() == catalog.rules

    def test_module_level_helper_matches_builder(self) -> None:
        assert default_learning_rule_catalog() == LearningRuleBuilder().build()

    def test_repeated_calls_return_equal_but_independent_catalogs(self) -> None:
        a = default_learning_rule_catalog()
        b = default_learning_rule_catalog()
        assert a == b
        assert a is not b

    def test_default_catalog_is_already_in_canonical_order(self) -> None:
        catalog = LearningRuleBuilder().build()
        assert list(catalog.rules) == sorted(
            catalog.rules, key=lambda rule: (rule.evaluation_order, rule.rule_id)
        )

    def test_no_rule_carries_a_threshold_value(self) -> None:
        """Rules are metadata only — every governed number lives in LearningPolicy
        (Recommendation 24/28 of ADR-0029)."""
        assert "threshold" not in LearningRule.model_fields

    def test_no_two_rules_share_an_evaluation_order(self) -> None:
        catalog = LearningRuleBuilder().build()
        orders = [rule.evaluation_order for rule in catalog.rules]
        assert len(orders) == len(set(orders))


@pytest.mark.unit
class TestVersionAxisIndependence:
    def test_catalog_version_type_is_distinct(self) -> None:
        assert isinstance(LEARNING_RULE_CATALOG_VERSION, LearningRuleCatalogVersion)

    def test_catalog_version_is_1_0_0(self) -> None:
        assert str(LEARNING_RULE_CATALOG_VERSION) == "1.0.0"
