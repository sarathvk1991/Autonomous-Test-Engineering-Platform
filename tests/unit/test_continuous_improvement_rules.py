"""Unit tests for the governed :class:`ImprovementRule` catalogue (CAP-083B).

Rules are immutable metadata only — no executable behaviour. These tests assert
construction, per-family shape invariants, catalogue ordering/lookup, and
governed coverage (every source, every family) — never a computation, which is
the engine's job (covered in ``test_continuous_improvement_engine.py``).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.continuous_improvement.models.enums import (
    ImprovementFindingCategory,
    ImprovementOpportunityCategory,
    ImprovementSeverity,
    ImprovementSourceLayer,
)
from requirement_intelligence.continuous_improvement.rules import (
    IMPROVEMENT_RULE_CATALOG_VERSION,
    IMPROVEMENT_RULE_VERSION,
    ImprovementPolicyToggle,
    ImprovementRule,
    ImprovementRuleBuilder,
    ImprovementRuleCatalog,
    ImprovementRuleFamily,
    default_improvement_rule_catalog,
)


def _recurrence_rule(**overrides: object) -> ImprovementRule:
    defaults: dict[str, object] = dict(
        rule_id="IR-TEST-001",
        rule_name="Test recurrence rule",
        family=ImprovementRuleFamily.RECURRENCE,
        source_subsystem=ImprovementSourceLayer.VALIDATION,
        finding_category=ImprovementFindingCategory.RECURRING_VALIDATION_FAILURE,
        severity_hint=ImprovementSeverity.WARNING,
        guidance="Do the thing.",
        policy_reference=ImprovementPolicyToggle.ENABLE_RECURRING_FINDING_DETECTION,
        evaluation_order=1,
    )
    defaults.update(overrides)
    return ImprovementRule(**defaults)  # type: ignore[arg-type]


def _trend_rule(**overrides: object) -> ImprovementRule:
    defaults: dict[str, object] = dict(
        rule_id="IR-TEST-002",
        rule_name="Test trend rule",
        family=ImprovementRuleFamily.TREND,
        source_subsystem=ImprovementSourceLayer.GROUNDING,
        metric_name="groundingScore",
        guidance="Watch the metric.",
        policy_reference=ImprovementPolicyToggle.ENABLE_TREND_DETECTION,
        evaluation_order=2,
    )
    defaults.update(overrides)
    return ImprovementRule(**defaults)  # type: ignore[arg-type]


def _opportunity_rule(**overrides: object) -> ImprovementRule:
    defaults: dict[str, object] = dict(
        rule_id="IR-TEST-003",
        rule_name="Test opportunity rule",
        family=ImprovementRuleFamily.OPPORTUNITY,
        source_subsystem=ImprovementSourceLayer.QUALITY_GOVERNANCE,
        opportunity_category=ImprovementOpportunityCategory.RECURRING_QUALITY_ISSUE,
        finding_category=ImprovementFindingCategory.RECURRING_GOVERNANCE_FAILURE,
        guidance="Address the recurring issue.",
        policy_reference=ImprovementPolicyToggle.ENABLE_OPPORTUNITY_GENERATION,
        evaluation_order=3,
    )
    defaults.update(overrides)
    return ImprovementRule(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestImprovementRule:
    def test_valid_recurrence_rule_constructs(self) -> None:
        rule = _recurrence_rule()
        assert rule.family == ImprovementRuleFamily.RECURRENCE

    def test_valid_trend_rule_constructs(self) -> None:
        rule = _trend_rule()
        assert rule.metric_name == "groundingScore"

    def test_valid_opportunity_rule_with_finding_constructs(self) -> None:
        rule = _opportunity_rule()
        assert rule.opportunity_category == ImprovementOpportunityCategory.RECURRING_QUALITY_ISSUE

    def test_valid_opportunity_rule_with_metric_constructs(self) -> None:
        rule = _opportunity_rule(
            finding_category=None,
            metric_name="engineeringReadinessScore",
            source_subsystem=ImprovementSourceLayer.CP1,
        )
        assert rule.metric_name == "engineeringReadinessScore"

    def test_is_immutable(self) -> None:
        rule = _recurrence_rule()
        with pytest.raises(ValidationError):
            rule.rule_name = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        rule = _recurrence_rule()
        dumped = rule.model_dump(mode="json", by_alias=True)
        assert ImprovementRule.model_validate(dumped) == rule

    def test_default_rule_version(self) -> None:
        assert _recurrence_rule().rule_version == IMPROVEMENT_RULE_VERSION

    def test_default_enabled_true(self) -> None:
        assert _recurrence_rule().enabled is True

    def test_can_be_disabled(self) -> None:
        assert _recurrence_rule(enabled=False).enabled is False

    def test_negative_evaluation_order_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _recurrence_rule(evaluation_order=-1)

    def test_empty_rule_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _recurrence_rule(rule_id="")

    def test_lowercase_rule_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _recurrence_rule(rule_id="ir-test-001")

    # -- per-family shape invariants ------------------------------------------------

    def test_recurrence_rule_missing_finding_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementRule(
                rule_id="IR-BAD-001",
                rule_name="bad",
                family=ImprovementRuleFamily.RECURRENCE,
                source_subsystem=ImprovementSourceLayer.VALIDATION,
                severity_hint=ImprovementSeverity.WARNING,
                guidance="x",
                policy_reference=ImprovementPolicyToggle.ENABLE_RECURRING_FINDING_DETECTION,
                evaluation_order=1,
            )

    def test_recurrence_rule_missing_severity_hint_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementRule(
                rule_id="IR-BAD-002",
                rule_name="bad",
                family=ImprovementRuleFamily.RECURRENCE,
                source_subsystem=ImprovementSourceLayer.VALIDATION,
                finding_category=ImprovementFindingCategory.RECURRING_VALIDATION_FAILURE,
                guidance="x",
                policy_reference=ImprovementPolicyToggle.ENABLE_RECURRING_FINDING_DETECTION,
                evaluation_order=1,
            )

    def test_recurrence_rule_naming_opportunity_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _recurrence_rule(
                opportunity_category=ImprovementOpportunityCategory.RECURRING_QUALITY_ISSUE
            )

    def test_recurrence_rule_naming_metric_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _recurrence_rule(metric_name="groundingScore")

    def test_trend_rule_missing_metric_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementRule(
                rule_id="IR-BAD-003",
                rule_name="bad",
                family=ImprovementRuleFamily.TREND,
                source_subsystem=ImprovementSourceLayer.GROUNDING,
                guidance="x",
                policy_reference=ImprovementPolicyToggle.ENABLE_TREND_DETECTION,
                evaluation_order=1,
            )

    def test_trend_rule_naming_finding_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _trend_rule(finding_category=ImprovementFindingCategory.RECURRING_VALIDATION_FAILURE)

    def test_trend_rule_naming_severity_hint_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _trend_rule(severity_hint=ImprovementSeverity.WARNING)

    def test_opportunity_rule_missing_opportunity_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementRule(
                rule_id="IR-BAD-004",
                rule_name="bad",
                family=ImprovementRuleFamily.OPPORTUNITY,
                source_subsystem=ImprovementSourceLayer.QUALITY_GOVERNANCE,
                finding_category=ImprovementFindingCategory.RECURRING_GOVERNANCE_FAILURE,
                guidance="x",
                policy_reference=ImprovementPolicyToggle.ENABLE_OPPORTUNITY_GENERATION,
                evaluation_order=1,
            )

    def test_opportunity_rule_naming_neither_finding_nor_metric_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _opportunity_rule(finding_category=None)

    def test_opportunity_rule_naming_both_finding_and_metric_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _opportunity_rule(metric_name="groundingScore")

    def test_opportunity_rule_naming_severity_hint_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _opportunity_rule(severity_hint=ImprovementSeverity.INFO)


@pytest.mark.unit
class TestImprovementRuleCatalog:
    def test_empty_catalog_is_valid(self) -> None:
        catalog = ImprovementRuleCatalog()
        assert catalog.rules == ()

    def test_default_catalog_version(self) -> None:
        assert default_improvement_rule_catalog().catalog_version == (
            IMPROVEMENT_RULE_CATALOG_VERSION
        )

    def test_duplicate_rule_ids_rejected(self) -> None:
        rule = _recurrence_rule()
        with pytest.raises(ValidationError):
            ImprovementRuleCatalog(rules=(rule, rule))

    def test_out_of_order_rules_rejected(self) -> None:
        first = _recurrence_rule(rule_id="IR-A", evaluation_order=20)
        second = _trend_rule(rule_id="IR-B", evaluation_order=10)
        with pytest.raises(ValidationError):
            ImprovementRuleCatalog(rules=(first, second))

    def test_round_trips(self) -> None:
        catalog = default_improvement_rule_catalog()
        dumped = catalog.model_dump(mode="json", by_alias=True)
        assert ImprovementRuleCatalog.model_validate(dumped) == catalog

    def test_builder_is_deterministic(self) -> None:
        assert ImprovementRuleBuilder().build() == ImprovementRuleBuilder().build()

    def test_enabled_rules_excludes_disabled(self) -> None:
        enabled = _recurrence_rule(rule_id="IR-A", evaluation_order=1)
        disabled = _trend_rule(rule_id="IR-B", evaluation_order=2, enabled=False)
        catalog = ImprovementRuleCatalog(rules=(enabled, disabled))
        assert catalog.enabled_rules() == (enabled,)

    def test_rule_lookup_by_id(self) -> None:
        catalog = default_improvement_rule_catalog()
        rule = catalog.rule("IR-REC-001")
        assert rule is not None
        assert rule.family == ImprovementRuleFamily.RECURRENCE

    def test_rule_lookup_missing_id_returns_none(self) -> None:
        assert default_improvement_rule_catalog().rule("NOPE") is None

    def test_by_family_filters_correctly(self) -> None:
        catalog = default_improvement_rule_catalog()
        recurrence_rules = catalog.by_family(ImprovementRuleFamily.RECURRENCE)
        assert len(recurrence_rules) == 5
        assert all(r.family == ImprovementRuleFamily.RECURRENCE for r in recurrence_rules)

    def test_by_source_filters_correctly(self) -> None:
        catalog = default_improvement_rule_catalog()
        cp1_rules = catalog.by_source(ImprovementSourceLayer.CP1)
        assert len(cp1_rules) == 2
        assert all(r.source_subsystem == ImprovementSourceLayer.CP1 for r in cp1_rules)

    def test_canonical_order_is_evaluation_order_then_rule_id(self) -> None:
        catalog = default_improvement_rule_catalog()
        keys = [(r.evaluation_order, r.rule_id) for r in catalog.rules]
        assert keys == sorted(keys)


@pytest.mark.unit
class TestDefaultCatalogCoverage:
    def test_covers_every_improvement_source_layer(self) -> None:
        catalog = default_improvement_rule_catalog()
        sources = {rule.source_subsystem for rule in catalog.rules}
        assert sources == set(ImprovementSourceLayer)

    def test_covers_every_finding_category(self) -> None:
        catalog = default_improvement_rule_catalog()
        categories = {
            rule.finding_category for rule in catalog.by_family(ImprovementRuleFamily.RECURRENCE)
        }
        assert categories == set(ImprovementFindingCategory)

    def test_covers_every_opportunity_category(self) -> None:
        catalog = default_improvement_rule_catalog()
        categories = {
            rule.opportunity_category
            for rule in catalog.by_family(ImprovementRuleFamily.OPPORTUNITY)
        }
        assert categories == set(ImprovementOpportunityCategory)

    def test_sixteen_governed_rules(self) -> None:
        assert len(default_improvement_rule_catalog().rules) == 16

    def test_five_recurrence_six_trend_five_opportunity(self) -> None:
        catalog = default_improvement_rule_catalog()
        assert len(catalog.by_family(ImprovementRuleFamily.RECURRENCE)) == 5
        assert len(catalog.by_family(ImprovementRuleFamily.TREND)) == 6
        assert len(catalog.by_family(ImprovementRuleFamily.OPPORTUNITY)) == 5

    def test_all_rules_reference_the_correct_family_toggle(self) -> None:
        catalog = default_improvement_rule_catalog()
        expected = {
            ImprovementRuleFamily.RECURRENCE: (
                ImprovementPolicyToggle.ENABLE_RECURRING_FINDING_DETECTION
            ),
            ImprovementRuleFamily.TREND: ImprovementPolicyToggle.ENABLE_TREND_DETECTION,
            ImprovementRuleFamily.OPPORTUNITY: (
                ImprovementPolicyToggle.ENABLE_OPPORTUNITY_GENERATION
            ),
        }
        for rule in catalog.rules:
            assert rule.policy_reference == expected[ImprovementRuleFamily(rule.family)]

    def test_all_rules_enabled_by_default(self) -> None:
        catalog = default_improvement_rule_catalog()
        assert catalog.enabled_rules() == catalog.rules
