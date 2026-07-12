"""Unit tests for the governed Quality Rule Catalogue (CAP-080B).

The catalogue owns metadata only — ordering, lookup, grouping, enabled-rule selection —
and no behaviour. These tests cover the rule model's immutability and invariants, the
catalogue's deterministic ordering and projections, builder determinism, and version
independence (ADR-0017 §D25).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.quality_governance.evaluation.models import RuleCategory
from requirement_intelligence.quality_governance.identity import (
    QualityRuleCatalogVersion,
    QualityRuleVersion,
)
from requirement_intelligence.quality_governance.models import QualitySeverity
from requirement_intelligence.quality_governance.rules import (
    QualityMetric,
    QualityMetricSubsystem,
    QualityReleaseToggle,
    QualityRule,
    QualityRuleBuilder,
    QualityRuleCatalog,
    QualityThresholdRef,
    RuleComparator,
    RuleType,
    default_quality_rule_catalog,
)


def _rule(**overrides: object) -> QualityRule:
    base: dict[str, object] = {
        "rule_id": "QG-TST-001",
        "rule_name": "Test rule",
        "category": RuleCategory.GROUNDING,
        "severity": QualitySeverity.FAILURE,
        "rule_type": RuleType.THRESHOLD,
        "description": "a governed test rule",
        "metric": QualityMetric.GROUNDING_SCORE,
        "comparator": RuleComparator.AT_LEAST,
        "threshold_ref": QualityThresholdRef.FAILURE_MIN_GROUNDING_SCORE,
        "evaluation_order": 10,
        "recommendation": "do the thing",
        "applicable_subsystem": QualityMetricSubsystem.GROUNDING,
    }
    base.update(overrides)
    return QualityRule(**base)  # type: ignore[arg-type]


@pytest.mark.unit
class TestQualityRule:
    def test_is_frozen(self) -> None:
        rule = _rule()
        with pytest.raises(ValidationError):
            rule.rule_id = "QG-OTHER"  # type: ignore[misc]

    def test_serialises_camelcase_and_round_trips(self) -> None:
        rule = _rule()
        dumped = rule.model_dump(mode="json", by_alias=True)
        assert dumped["ruleId"] == "QG-TST-001"
        assert dumped["thresholdRef"] == "failure_min_grounding_score"
        assert dumped["ruleVersion"] == str(QualityRuleVersion(1, 0, 0))
        assert QualityRule.model_validate(dumped) == rule

    def test_lowercase_rule_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _rule(rule_id="qg-tst-001")

    def test_must_not_hold_forbids_numeric_threshold(self) -> None:
        with pytest.raises(ValidationError):
            _rule(
                comparator=RuleComparator.MUST_NOT_HOLD,
                threshold_ref=QualityThresholdRef.FAILURE_MIN_GROUNDING_SCORE,
            )

    def test_numeric_comparator_requires_threshold(self) -> None:
        with pytest.raises(ValidationError):
            _rule(
                comparator=RuleComparator.AT_LEAST,
                threshold_ref=QualityThresholdRef.NONE,
            )

    def test_mandatory_rule_requires_governing_toggle(self) -> None:
        with pytest.raises(ValidationError):
            _rule(mandatory=True)

    def test_governing_toggle_requires_mandatory(self) -> None:
        with pytest.raises(ValidationError):
            _rule(governing_toggle=QualityReleaseToggle.BLOCK_ON_HALLUCINATION)

    def test_no_executable_behaviour_fields(self) -> None:
        """The rule owns only metadata — no callable/threshold-value fields."""
        fields = set(QualityRule.model_fields)
        assert "callable" not in fields
        assert "evaluate" not in fields
        assert "threshold_value" not in fields
        assert not any("lambda" in f for f in fields)


@pytest.mark.unit
class TestQualityRuleCatalog:
    def test_default_catalog_has_all_six_categories(self) -> None:
        catalog = default_quality_rule_catalog()
        present = {rule.category for rule in catalog.rules}
        assert present == {c.value for c in RuleCategory}

    def test_default_catalog_is_eighteen_rules(self) -> None:
        assert len(default_quality_rule_catalog().rules) == 18

    def test_rules_stored_in_canonical_order(self) -> None:
        rules = default_quality_rule_catalog().rules
        orders = [r.evaluation_order for r in rules]
        assert orders == sorted(orders)

    def test_out_of_order_rules_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QualityRuleCatalog(
                rules=(
                    _rule(rule_id="QG-B", evaluation_order=20),
                    _rule(rule_id="QG-A", evaluation_order=10),
                )
            )

    def test_duplicate_rule_ids_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QualityRuleCatalog(rules=(_rule(), _rule()))

    def test_enabled_rules_excludes_disabled(self) -> None:
        catalog = QualityRuleCatalog(
            rules=(
                _rule(rule_id="QG-A", evaluation_order=10, enabled=True),
                _rule(rule_id="QG-B", evaluation_order=20, enabled=False),
            )
        )
        enabled_ids = [r.rule_id for r in catalog.enabled_rules()]
        assert enabled_ids == ["QG-A"]

    def test_lookup_by_id(self) -> None:
        catalog = default_quality_rule_catalog()
        assert catalog.rule("QG-GRD-001") is not None
        assert catalog.rule("QG-NOPE") is None

    def test_grouping_by_category(self) -> None:
        catalog = default_quality_rule_catalog()
        grounding = catalog.by_category(RuleCategory.GROUNDING)
        assert len(grounding) == 6
        assert all(r.category == RuleCategory.GROUNDING for r in grounding)

    def test_round_trips_deterministically(self) -> None:
        catalog = default_quality_rule_catalog()
        dumped = catalog.model_dump(mode="json", by_alias=True)
        assert QualityRuleCatalog.model_validate(dumped) == catalog
        assert dumped["catalogVersion"] == str(QualityRuleCatalogVersion(1, 0, 0))


@pytest.mark.unit
class TestQualityRuleBuilder:
    def test_builder_is_deterministic(self) -> None:
        assert QualityRuleBuilder().build() == QualityRuleBuilder().build()

    def test_builder_output_serialises_identically(self) -> None:
        a = QualityRuleBuilder().build().model_dump(mode="json", by_alias=True)
        b = QualityRuleBuilder().build().model_dump(mode="json", by_alias=True)
        assert a == b

    def test_mandatory_rules_name_their_toggle(self) -> None:
        for rule in default_quality_rule_catalog().rules:
            if rule.category == RuleCategory.MANDATORY_RELEASE:
                assert rule.mandatory is True
                assert rule.governing_toggle is not None

    def test_catalog_version_independent_of_rule_version(self) -> None:
        """The catalogue and a rule version advance on independent axes."""
        catalog = default_quality_rule_catalog()
        assert isinstance(catalog.catalog_version, QualityRuleCatalogVersion)
        assert all(isinstance(r.rule_version, QualityRuleVersion) for r in catalog.rules)
