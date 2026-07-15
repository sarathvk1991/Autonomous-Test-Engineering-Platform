"""Unit tests for the governed :class:`RecommendationRule` catalogue (CAP-082B).

Rules are immutable metadata only — no executable behaviour. These tests assert
construction, shape invariants, catalogue ordering/lookup, and governed coverage
(every source, every recommendation type, every priority) — never a recommendation
computation, which is the engine's job (covered in ``test_recommendation_engine.py``).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.recommendation.models.enums import (
    RecommendationEffort,
    RecommendationPriority,
    RecommendationSource,
    RecommendationType,
)
from requirement_intelligence.recommendation.rules import (
    RECOMMENDATION_RULE_CATALOG_VERSION,
    RECOMMENDATION_RULE_VERSION,
    RecommendationPolicyToggle,
    RecommendationRule,
    RecommendationRuleBuilder,
    RecommendationRuleCatalog,
    RecommendationRuleCategory,
    default_recommendation_rule_catalog,
)


def _rule(**overrides: object) -> RecommendationRule:
    defaults: dict[str, object] = dict(
        rule_id="RC-TEST-001",
        rule_name="Test rule",
        category=RecommendationRuleCategory.ENHANCEMENT_DEPENDENCY_GAP,
        source_subsystem=RecommendationSource.ENHANCEMENT,
        recommendation_type=RecommendationType.RESOLVE_DEPENDENCY,
        guidance="Do the thing.",
        priority_hint=RecommendationPriority.MEDIUM,
        effort_hint=RecommendationEffort.MEDIUM,
        confidence_hint=0.7,
        policy_reference=RecommendationPolicyToggle.ENABLE_DETERMINISTIC_ENGINE,
        evaluation_order=1,
    )
    defaults.update(overrides)
    return RecommendationRule(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestRecommendationRule:
    def test_valid_rule_constructs(self) -> None:
        rule = _rule()
        assert rule.rule_id == "RC-TEST-001"

    def test_is_immutable(self) -> None:
        rule = _rule()
        with pytest.raises(ValidationError):
            rule.rule_name = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        rule = _rule()
        dumped = rule.model_dump(mode="json", by_alias=True)
        assert RecommendationRule.model_validate(dumped) == rule

    def test_default_rule_version(self) -> None:
        assert _rule().rule_version == RECOMMENDATION_RULE_VERSION

    def test_default_enabled_true(self) -> None:
        assert _rule().enabled is True

    def test_can_be_disabled(self) -> None:
        assert _rule(enabled=False).enabled is False

    def test_confidence_hint_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            _rule(confidence_hint=1.5)
        with pytest.raises(ValidationError):
            _rule(confidence_hint=-0.1)

    def test_negative_evaluation_order_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _rule(evaluation_order=-1)

    def test_empty_rule_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _rule(rule_id="")

    def test_lowercase_rule_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _rule(rule_id="rc-test-001")

    def test_category_source_mismatch_rejected(self) -> None:
        """A rule naming a category that belongs to a different source is invalid."""
        with pytest.raises(ValidationError):
            _rule(
                category=RecommendationRuleCategory.GROUNDING_UNSUPPORTED,
                source_subsystem=RecommendationSource.ENHANCEMENT,
            )

    def test_every_category_maps_to_exactly_one_source(self) -> None:
        """Every governed category constructs successfully against its true source."""
        expectations = {
            RecommendationRuleCategory.ENHANCEMENT_DEPENDENCY_GAP: RecommendationSource.ENHANCEMENT,
            RecommendationRuleCategory.ENHANCEMENT_DUPLICATE_REQUIREMENT: (
                RecommendationSource.ENHANCEMENT
            ),
            RecommendationRuleCategory.ENHANCEMENT_CONSISTENCY_WARNING: (
                RecommendationSource.ENHANCEMENT
            ),
            RecommendationRuleCategory.ENHANCEMENT_CONSISTENCY_CRITICAL: (
                RecommendationSource.ENHANCEMENT
            ),
            RecommendationRuleCategory.ENHANCEMENT_TRACEABILITY_GAP: (
                RecommendationSource.ENHANCEMENT
            ),
            RecommendationRuleCategory.GROUNDING_UNSUPPORTED: RecommendationSource.GROUNDING,
            RecommendationRuleCategory.GROUNDING_CONTRADICTED: RecommendationSource.GROUNDING,
            RecommendationRuleCategory.VALIDATION_ISSUE_INFO: RecommendationSource.VALIDATION,
            RecommendationRuleCategory.VALIDATION_ISSUE_WARNING: RecommendationSource.VALIDATION,
            RecommendationRuleCategory.VALIDATION_ISSUE_ERROR: RecommendationSource.VALIDATION,
            RecommendationRuleCategory.VALIDATION_ISSUE_CRITICAL: RecommendationSource.VALIDATION,
            RecommendationRuleCategory.CP1_FINDING_FAIL: RecommendationSource.CP1,
            RecommendationRuleCategory.CP1_FINDING_WARN: RecommendationSource.CP1,
            RecommendationRuleCategory.QUALITY_FINDING_INFO: (
                RecommendationSource.QUALITY_GOVERNANCE
            ),
            RecommendationRuleCategory.QUALITY_FINDING_WARNING: (
                RecommendationSource.QUALITY_GOVERNANCE
            ),
            RecommendationRuleCategory.QUALITY_FINDING_FAILURE: (
                RecommendationSource.QUALITY_GOVERNANCE
            ),
            RecommendationRuleCategory.QUALITY_DECISION_FAIL: (
                RecommendationSource.QUALITY_GOVERNANCE
            ),
            RecommendationRuleCategory.QUALITY_DECISION_PASS_WITH_WARNINGS: (
                RecommendationSource.QUALITY_GOVERNANCE
            ),
        }
        assert set(expectations) == set(RecommendationRuleCategory)
        for category, source in expectations.items():
            rule = _rule(
                category=category,
                source_subsystem=source,
                rule_id=f"RC-{category.value.upper()}",
            )
            assert rule.category == category


@pytest.mark.unit
class TestRecommendationRuleCatalog:
    def test_empty_catalog_is_valid(self) -> None:
        catalog = RecommendationRuleCatalog()
        assert catalog.rules == ()

    def test_default_catalog_version(self) -> None:
        assert default_recommendation_rule_catalog().catalog_version == (
            RECOMMENDATION_RULE_CATALOG_VERSION
        )

    def test_duplicate_rule_ids_rejected(self) -> None:
        rule = _rule()
        with pytest.raises(ValidationError):
            RecommendationRuleCatalog(rules=(rule, rule))

    def test_duplicate_categories_rejected(self) -> None:
        rule_a = _rule(rule_id="RC-A")
        rule_b = _rule(rule_id="RC-B")
        with pytest.raises(ValidationError):
            RecommendationRuleCatalog(rules=(rule_a, rule_b))

    def test_out_of_order_rules_rejected(self) -> None:
        first = _rule(
            rule_id="RC-A",
            category=RecommendationRuleCategory.ENHANCEMENT_DEPENDENCY_GAP,
            source_subsystem=RecommendationSource.ENHANCEMENT,
            evaluation_order=20,
        )
        second = _rule(
            rule_id="RC-B",
            category=RecommendationRuleCategory.GROUNDING_UNSUPPORTED,
            source_subsystem=RecommendationSource.GROUNDING,
            evaluation_order=10,
        )
        with pytest.raises(ValidationError):
            RecommendationRuleCatalog(rules=(first, second))

    def test_round_trips(self) -> None:
        catalog = default_recommendation_rule_catalog()
        dumped = catalog.model_dump(mode="json", by_alias=True)
        assert RecommendationRuleCatalog.model_validate(dumped) == catalog

    def test_builder_is_deterministic(self) -> None:
        assert RecommendationRuleBuilder().build() == RecommendationRuleBuilder().build()

    def test_enabled_rules_excludes_disabled(self) -> None:
        enabled = _rule(rule_id="RC-A", evaluation_order=1)
        disabled = _rule(
            rule_id="RC-B",
            category=RecommendationRuleCategory.GROUNDING_UNSUPPORTED,
            source_subsystem=RecommendationSource.GROUNDING,
            evaluation_order=2,
            enabled=False,
        )
        catalog = RecommendationRuleCatalog(rules=(enabled, disabled))
        assert catalog.enabled_rules() == (enabled,)

    def test_rule_lookup_by_id(self) -> None:
        catalog = default_recommendation_rule_catalog()
        rule = catalog.rule("RC-ENH-001")
        assert rule is not None
        assert rule.category == RecommendationRuleCategory.ENHANCEMENT_DEPENDENCY_GAP

    def test_rule_lookup_missing_id_returns_none(self) -> None:
        assert default_recommendation_rule_catalog().rule("NOPE") is None

    def test_rule_for_category_returns_enabled_rule(self) -> None:
        catalog = default_recommendation_rule_catalog()
        rule = catalog.rule_for_category(RecommendationRuleCategory.GROUNDING_CONTRADICTED)
        assert rule is not None
        assert rule.source_subsystem == RecommendationSource.GROUNDING

    def test_rule_for_category_disabled_rule_returns_none(self) -> None:
        rule = _rule(enabled=False)
        catalog = RecommendationRuleCatalog(rules=(rule,))
        assert (
            catalog.rule_for_category(RecommendationRuleCategory.ENHANCEMENT_DEPENDENCY_GAP) is None
        )

    def test_by_source_filters_correctly(self) -> None:
        catalog = default_recommendation_rule_catalog()
        cp1_rules = catalog.by_source(RecommendationSource.CP1)
        assert len(cp1_rules) == 2
        assert all(r.source_subsystem == RecommendationSource.CP1 for r in cp1_rules)

    def test_canonical_order_is_evaluation_order_then_rule_id(self) -> None:
        catalog = default_recommendation_rule_catalog()
        keys = [(r.evaluation_order, r.rule_id) for r in catalog.rules]
        assert keys == sorted(keys)


@pytest.mark.unit
class TestDefaultCatalogCoverage:
    def test_covers_every_recommendation_source(self) -> None:
        catalog = default_recommendation_rule_catalog()
        sources = {rule.source_subsystem for rule in catalog.rules}
        assert sources == set(RecommendationSource)

    def test_covers_every_recommendation_type(self) -> None:
        catalog = default_recommendation_rule_catalog()
        types = {rule.recommendation_type for rule in catalog.rules}
        assert types == set(RecommendationType)

    def test_covers_every_recommendation_priority(self) -> None:
        catalog = default_recommendation_rule_catalog()
        priorities = {rule.priority_hint for rule in catalog.rules}
        assert priorities == set(RecommendationPriority)

    def test_covers_every_governed_category(self) -> None:
        catalog = default_recommendation_rule_catalog()
        categories = {rule.category for rule in catalog.rules}
        assert categories == set(RecommendationRuleCategory)

    def test_eighteen_governed_rules(self) -> None:
        assert len(default_recommendation_rule_catalog().rules) == 18

    def test_all_rules_reference_the_deterministic_engine_toggle(self) -> None:
        catalog = default_recommendation_rule_catalog()
        assert all(
            rule.policy_reference == RecommendationPolicyToggle.ENABLE_DETERMINISTIC_ENGINE
            for rule in catalog.rules
        )

    def test_all_rules_enabled_by_default(self) -> None:
        catalog = default_recommendation_rule_catalog()
        assert catalog.enabled_rules() == catalog.rules
