"""Unit tests for the governed KnowledgeGraphRule/RuleCatalog and its builder (CAP-084B).

Rules are governed metadata only — immutable, versioned, deterministic. The
catalogue owns ordering/lookup only. These tests assert construction, shape
invariants, and catalogue-level determinism; no rule computes anything.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeEdgeType,
    KnowledgeFindingCategory,
    KnowledgeNodeType,
    KnowledgeSeverity,
)
from requirement_intelligence.knowledge_graph.rules import (
    KNOWLEDGE_GRAPH_RULE_CATALOG_VERSION,
    KNOWLEDGE_GRAPH_RULE_VERSION,
    KnowledgeGraphPolicyToggle,
    KnowledgeGraphRule,
    KnowledgeGraphRuleBuilder,
    KnowledgeGraphRuleCatalog,
    KnowledgeGraphRuleFamily,
    default_knowledge_graph_rule_catalog,
)


def _node_rule(**overrides: object) -> KnowledgeGraphRule:
    defaults: dict[str, object] = dict(
        rule_id="KG-NODE-TEST",
        rule_name="Test node rule",
        family=KnowledgeGraphRuleFamily.NODE,
        node_type=KnowledgeNodeType.REQUIREMENT,
        guidance="A test node rule.",
        policy_reference=KnowledgeGraphPolicyToggle.ENABLE_NODE_INGESTION,
        evaluation_order=1,
    )
    defaults.update(overrides)
    return KnowledgeGraphRule(**defaults)  # type: ignore[arg-type]


def _edge_rule(**overrides: object) -> KnowledgeGraphRule:
    defaults: dict[str, object] = dict(
        rule_id="KG-EDGE-TEST",
        rule_name="Test edge rule",
        family=KnowledgeGraphRuleFamily.EDGE,
        edge_type=KnowledgeEdgeType.DEPENDS_ON,
        guidance="A test edge rule.",
        policy_reference=KnowledgeGraphPolicyToggle.ENABLE_EDGE_INGESTION,
        evaluation_order=2,
    )
    defaults.update(overrides)
    return KnowledgeGraphRule(**defaults)  # type: ignore[arg-type]


def _structural_rule(**overrides: object) -> KnowledgeGraphRule:
    defaults: dict[str, object] = dict(
        rule_id="KG-STR-TEST",
        rule_name="Test structural rule",
        family=KnowledgeGraphRuleFamily.STRUCTURAL,
        finding_category=KnowledgeFindingCategory.ISOLATED_NODE,
        severity_hint=KnowledgeSeverity.WARNING,
        guidance="A test structural rule.",
        policy_reference=KnowledgeGraphPolicyToggle.ENABLE_FINDING_DETECTION,
        evaluation_order=3,
    )
    defaults.update(overrides)
    return KnowledgeGraphRule(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestRuleShapeValidation:
    def test_valid_node_rule_constructs(self) -> None:
        rule = _node_rule()
        assert rule.node_type == KnowledgeNodeType.REQUIREMENT

    def test_valid_edge_rule_constructs(self) -> None:
        rule = _edge_rule()
        assert rule.edge_type == KnowledgeEdgeType.DEPENDS_ON

    def test_valid_structural_rule_constructs(self) -> None:
        rule = _structural_rule()
        assert rule.finding_category == KnowledgeFindingCategory.ISOLATED_NODE
        assert rule.severity_hint == KnowledgeSeverity.WARNING

    def test_is_immutable(self) -> None:
        rule = _node_rule()
        with pytest.raises(ValidationError):
            rule.rule_name = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        rule = _structural_rule()
        dumped = rule.model_dump(mode="json", by_alias=True)
        assert KnowledgeGraphRule.model_validate(dumped) == rule

    def test_node_rule_missing_node_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _node_rule(node_type=None)

    def test_node_rule_naming_edge_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _node_rule(edge_type=KnowledgeEdgeType.USES)

    def test_node_rule_naming_finding_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _node_rule(finding_category=KnowledgeFindingCategory.CYCLE)

    def test_edge_rule_missing_edge_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _edge_rule(edge_type=None)

    def test_edge_rule_naming_node_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _edge_rule(node_type=KnowledgeNodeType.CAPABILITY)

    def test_structural_rule_missing_finding_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _structural_rule(finding_category=None)

    def test_structural_rule_missing_severity_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _structural_rule(severity_hint=None)

    def test_structural_rule_naming_node_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _structural_rule(node_type=KnowledgeNodeType.DOCUMENT)

    def test_structural_rule_naming_edge_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _structural_rule(edge_type=KnowledgeEdgeType.RELATED_TO)

    def test_invalid_rule_id_shape_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _node_rule(rule_id="not-upper-case")

    def test_default_rule_version_is_the_cap_084b_foundation(self) -> None:
        assert _node_rule().rule_version == KNOWLEDGE_GRAPH_RULE_VERSION


@pytest.mark.unit
class TestRuleCatalog:
    def test_catalog_round_trips(self) -> None:
        catalog = KnowledgeGraphRuleCatalog(rules=(_node_rule(), _edge_rule()))
        dumped = catalog.model_dump(mode="json", by_alias=True)
        assert KnowledgeGraphRuleCatalog.model_validate(dumped) == catalog

    def test_duplicate_rule_ids_rejected(self) -> None:
        rule = _node_rule()
        with pytest.raises(ValidationError):
            KnowledgeGraphRuleCatalog(rules=(rule, rule))

    def test_out_of_order_rules_rejected(self) -> None:
        first = _node_rule(rule_id="KG-NODE-A", evaluation_order=20)
        second = _node_rule(rule_id="KG-NODE-B", evaluation_order=10)
        with pytest.raises(ValidationError):
            KnowledgeGraphRuleCatalog(rules=(first, second))

    def test_rule_lookup_by_id(self) -> None:
        rule = _node_rule()
        catalog = KnowledgeGraphRuleCatalog(rules=(rule,))
        assert catalog.rule(rule.rule_id) == rule

    def test_rule_lookup_missing_returns_none(self) -> None:
        catalog = KnowledgeGraphRuleCatalog(rules=(_node_rule(),))
        assert catalog.rule("KG-NODE-MISSING") is None

    def test_enabled_rules_excludes_disabled(self) -> None:
        enabled = _node_rule(rule_id="KG-NODE-A", evaluation_order=1)
        disabled = _node_rule(rule_id="KG-NODE-B", evaluation_order=2, enabled=False)
        catalog = KnowledgeGraphRuleCatalog(rules=(enabled, disabled))
        assert catalog.enabled_rules() == (enabled,)

    def test_by_family_filters_and_excludes_disabled(self) -> None:
        node_rule = _node_rule(rule_id="KG-NODE-A", evaluation_order=1)
        edge_rule = _edge_rule(rule_id="KG-EDGE-A", evaluation_order=2)
        catalog = KnowledgeGraphRuleCatalog(rules=(node_rule, edge_rule))
        assert catalog.by_family(KnowledgeGraphRuleFamily.NODE) == (node_rule,)
        assert catalog.by_family(KnowledgeGraphRuleFamily.EDGE) == (edge_rule,)

    def test_default_catalog_version(self) -> None:
        assert KnowledgeGraphRuleCatalog().catalog_version == KNOWLEDGE_GRAPH_RULE_CATALOG_VERSION


@pytest.mark.unit
class TestDefaultRuleCatalog:
    def test_builder_is_deterministic(self) -> None:
        assert KnowledgeGraphRuleBuilder().build() == KnowledgeGraphRuleBuilder().build()

    def test_default_catalog_has_twenty_two_rules(self) -> None:
        assert len(default_knowledge_graph_rule_catalog().rules) == 22

    def test_default_catalog_has_seven_node_rules(self) -> None:
        catalog = default_knowledge_graph_rule_catalog()
        assert len(catalog.by_family(KnowledgeGraphRuleFamily.NODE)) == 7

    def test_default_catalog_has_nine_edge_rules(self) -> None:
        catalog = default_knowledge_graph_rule_catalog()
        assert len(catalog.by_family(KnowledgeGraphRuleFamily.EDGE)) == 9

    def test_default_catalog_has_six_structural_rules(self) -> None:
        catalog = default_knowledge_graph_rule_catalog()
        assert len(catalog.by_family(KnowledgeGraphRuleFamily.STRUCTURAL)) == 6

    def test_default_catalog_covers_the_seven_recommended_node_types(self) -> None:
        # MODULE and COMPONENT are governed KnowledgeNodeType members without a
        # rule in the CAP-084B default catalogue — the recommended rule set
        # names only the seven types the deterministic engine actually projects.
        catalog = default_knowledge_graph_rule_catalog()
        node_types = {rule.node_type for rule in catalog.by_family(KnowledgeGraphRuleFamily.NODE)}
        assert node_types == set(KnowledgeNodeType) - {
            KnowledgeNodeType.MODULE,
            KnowledgeNodeType.COMPONENT,
        }

    def test_default_catalog_covers_every_governed_edge_type(self) -> None:
        catalog = default_knowledge_graph_rule_catalog()
        edge_types = {rule.edge_type for rule in catalog.by_family(KnowledgeGraphRuleFamily.EDGE)}
        assert edge_types == set(KnowledgeEdgeType)

    def test_default_catalog_covers_every_governed_finding_category(self) -> None:
        catalog = default_knowledge_graph_rule_catalog()
        categories = {
            rule.finding_category for rule in catalog.by_family(KnowledgeGraphRuleFamily.STRUCTURAL)
        }
        assert categories == set(KnowledgeFindingCategory)

    def test_all_rules_are_enabled_by_default(self) -> None:
        catalog = default_knowledge_graph_rule_catalog()
        assert len(catalog.enabled_rules()) == len(catalog.rules)

    def test_node_rules_reference_the_node_ingestion_switch(self) -> None:
        catalog = default_knowledge_graph_rule_catalog()
        for rule in catalog.by_family(KnowledgeGraphRuleFamily.NODE):
            assert str(rule.policy_reference) == "enable_node_ingestion"

    def test_edge_rules_reference_the_edge_ingestion_switch(self) -> None:
        catalog = default_knowledge_graph_rule_catalog()
        for rule in catalog.by_family(KnowledgeGraphRuleFamily.EDGE):
            assert str(rule.policy_reference) == "enable_edge_ingestion"

    def test_structural_rules_reference_the_finding_detection_switch(self) -> None:
        catalog = default_knowledge_graph_rule_catalog()
        for rule in catalog.by_family(KnowledgeGraphRuleFamily.STRUCTURAL):
            assert str(rule.policy_reference) == "enable_finding_detection"
