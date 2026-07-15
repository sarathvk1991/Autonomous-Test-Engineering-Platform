"""Builder for the governed default :class:`KnowledgeGraphRuleCatalog` (CAP-084B).

Construction only. It assembles the framework's default governed rule
catalogue — a deterministic, immutable value — and rejects nothing beyond the
models' own field and invariant constraints. It projects nothing, detects
nothing, and has no runtime consumers.

The catalogue is **governed data**. Future rule additions, removals, or
retunings require only a builder change, never an engine code change (mirrors
ADR-0022 Recommendation 6).

The default catalogue spans all nine governed :class:`KnowledgeNodeType`... no —
seven of the nine governed node types the projector actually populates, all nine
governed :class:`KnowledgeEdgeType` values, and all six governed
:class:`KnowledgeFindingCategory` values: seven NODE rules, nine EDGE rules, and
six STRUCTURAL rules.
"""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeEdgeType,
    KnowledgeFindingCategory,
    KnowledgeNodeType,
    KnowledgeSeverity,
)
from requirement_intelligence.knowledge_graph.rules.knowledge_graph_rule import (
    KnowledgeGraphPolicyToggle,
    KnowledgeGraphRule,
    KnowledgeGraphRuleFamily,
)
from requirement_intelligence.knowledge_graph.rules.knowledge_graph_rule_catalog import (
    KNOWLEDGE_GRAPH_RULE_CATALOG_VERSION,
    KnowledgeGraphRuleCatalog,
)

_NODE = KnowledgeGraphPolicyToggle.ENABLE_NODE_INGESTION
_EDGE = KnowledgeGraphPolicyToggle.ENABLE_EDGE_INGESTION
_STRUCTURAL = KnowledgeGraphPolicyToggle.ENABLE_FINDING_DETECTION


class KnowledgeGraphRuleBuilder:
    """Assemble the governed default :class:`KnowledgeGraphRuleCatalog`."""

    def build(self) -> KnowledgeGraphRuleCatalog:
        """Return the framework's default governed rule catalogue, in canonical order."""
        rules = (
            # ---- Node -----------------------------------------------------------------
            KnowledgeGraphRule(
                rule_id="KG-NODE-001",
                rule_name="Requirement node",
                family=KnowledgeGraphRuleFamily.NODE,
                node_type=KnowledgeNodeType.REQUIREMENT,
                guidance="A requirement entity is projected into a REQUIREMENT node.",
                policy_reference=_NODE,
                evaluation_order=10,
                tags=("node", "requirement"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-NODE-002",
                rule_name="Recommendation node",
                family=KnowledgeGraphRuleFamily.NODE,
                node_type=KnowledgeNodeType.RECOMMENDATION,
                guidance="A recommendation entity is projected into a RECOMMENDATION node.",
                policy_reference=_NODE,
                evaluation_order=20,
                tags=("node", "recommendation"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-NODE-003",
                rule_name="Finding node",
                family=KnowledgeGraphRuleFamily.NODE,
                node_type=KnowledgeNodeType.FINDING,
                guidance="A finding entity is projected into a FINDING node.",
                policy_reference=_NODE,
                evaluation_order=30,
                tags=("node", "finding"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-NODE-004",
                rule_name="Execution node",
                family=KnowledgeGraphRuleFamily.NODE,
                node_type=KnowledgeNodeType.EXECUTION,
                guidance="One historical execution is projected into an EXECUTION node.",
                policy_reference=_NODE,
                evaluation_order=40,
                tags=("node", "execution"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-NODE-005",
                rule_name="Capability node",
                family=KnowledgeGraphRuleFamily.NODE,
                node_type=KnowledgeNodeType.CAPABILITY,
                guidance="A capability entity is projected into a CAPABILITY node.",
                policy_reference=_NODE,
                evaluation_order=50,
                tags=("node", "capability"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-NODE-006",
                rule_name="Dataset node",
                family=KnowledgeGraphRuleFamily.NODE,
                node_type=KnowledgeNodeType.DATASET,
                guidance="The consumed Historical Dataset itself is projected into a DATASET node.",
                policy_reference=_NODE,
                evaluation_order=60,
                tags=("node", "dataset"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-NODE-007",
                rule_name="Document node",
                family=KnowledgeGraphRuleFamily.NODE,
                node_type=KnowledgeNodeType.DOCUMENT,
                guidance="A document entity is projected into a DOCUMENT node.",
                policy_reference=_NODE,
                evaluation_order=70,
                tags=("node", "document"),
            ),
            # ---- Edge -----------------------------------------------------------------
            KnowledgeGraphRule(
                rule_id="KG-EDGE-001",
                rule_name="Depends on",
                family=KnowledgeGraphRuleFamily.EDGE,
                edge_type=KnowledgeEdgeType.DEPENDS_ON,
                guidance="A requirement depends on the requirement of the prior execution.",
                policy_reference=_EDGE,
                evaluation_order=80,
                tags=("edge", "requirement"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-EDGE-002",
                rule_name="Generated by",
                family=KnowledgeGraphRuleFamily.EDGE,
                edge_type=KnowledgeEdgeType.GENERATED_BY,
                guidance="A recommendation is generated by the requirement it addresses.",
                policy_reference=_EDGE,
                evaluation_order=90,
                tags=("edge", "recommendation"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-EDGE-003",
                rule_name="Traceable to",
                family=KnowledgeGraphRuleFamily.EDGE,
                edge_type=KnowledgeEdgeType.TRACEABLE_TO,
                guidance="A finding is traceable to the requirement it concerns.",
                policy_reference=_EDGE,
                evaluation_order=100,
                tags=("edge", "finding"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-EDGE-004",
                rule_name="Implements",
                family=KnowledgeGraphRuleFamily.EDGE,
                edge_type=KnowledgeEdgeType.IMPLEMENTS,
                guidance="A requirement implements the capability it satisfies.",
                policy_reference=_EDGE,
                evaluation_order=110,
                tags=("edge", "capability"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-EDGE-005",
                rule_name="References",
                family=KnowledgeGraphRuleFamily.EDGE,
                edge_type=KnowledgeEdgeType.REFERENCES,
                guidance="A document references the requirement it documents.",
                policy_reference=_EDGE,
                evaluation_order=120,
                tags=("edge", "document"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-EDGE-006",
                rule_name="Belongs to",
                family=KnowledgeGraphRuleFamily.EDGE,
                edge_type=KnowledgeEdgeType.BELONGS_TO,
                guidance="A requirement belongs to the execution that produced it.",
                policy_reference=_EDGE,
                evaluation_order=130,
                tags=("edge", "execution"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-EDGE-007",
                rule_name="Derived from",
                family=KnowledgeGraphRuleFamily.EDGE,
                edge_type=KnowledgeEdgeType.DERIVED_FROM,
                guidance="An execution is derived from the historical dataset it belongs to.",
                policy_reference=_EDGE,
                evaluation_order=140,
                tags=("edge", "dataset"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-EDGE-008",
                rule_name="Related to",
                family=KnowledgeGraphRuleFamily.EDGE,
                edge_type=KnowledgeEdgeType.RELATED_TO,
                guidance="A recommendation is related to the finding recorded alongside it.",
                policy_reference=_EDGE,
                evaluation_order=150,
                tags=("edge", "recommendation", "finding"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-EDGE-009",
                rule_name="Uses",
                family=KnowledgeGraphRuleFamily.EDGE,
                edge_type=KnowledgeEdgeType.USES,
                guidance="A capability uses the document recorded alongside it.",
                policy_reference=_EDGE,
                evaluation_order=160,
                tags=("edge", "capability", "document"),
            ),
            # ---- Structural -------------------------------------------------------------
            KnowledgeGraphRule(
                rule_id="KG-STR-001",
                rule_name="Isolated node",
                family=KnowledgeGraphRuleFamily.STRUCTURAL,
                finding_category=KnowledgeFindingCategory.ISOLATED_NODE,
                severity_hint=KnowledgeSeverity.WARNING,
                guidance="A node has no incident edges at all.",
                policy_reference=_STRUCTURAL,
                evaluation_order=170,
                tags=("structural", "isolated_node"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-STR-002",
                rule_name="Duplicate edge",
                family=KnowledgeGraphRuleFamily.STRUCTURAL,
                finding_category=KnowledgeFindingCategory.DUPLICATE_EDGE,
                severity_hint=KnowledgeSeverity.WARNING,
                guidance="More than one edge connects the same pair of nodes.",
                policy_reference=_STRUCTURAL,
                evaluation_order=180,
                tags=("structural", "duplicate_edge"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-STR-003",
                rule_name="Orphan graph",
                family=KnowledgeGraphRuleFamily.STRUCTURAL,
                finding_category=KnowledgeFindingCategory.ORPHAN_GRAPH,
                severity_hint=KnowledgeSeverity.CRITICAL,
                guidance="The graph has nodes but records no relationships at all.",
                policy_reference=_STRUCTURAL,
                evaluation_order=190,
                tags=("structural", "orphan_graph"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-STR-004",
                rule_name="Missing relationship",
                family=KnowledgeGraphRuleFamily.STRUCTURAL,
                finding_category=KnowledgeFindingCategory.MISSING_RELATIONSHIP,
                severity_hint=KnowledgeSeverity.WARNING,
                guidance=(
                    "A recommendation or finding node lacks its expected governed edge "
                    "(GENERATED_BY / TRACEABLE_TO) to the requirement it concerns."
                ),
                policy_reference=_STRUCTURAL,
                evaluation_order=200,
                tags=("structural", "missing_relationship"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-STR-005",
                rule_name="Broken lineage",
                family=KnowledgeGraphRuleFamily.STRUCTURAL,
                finding_category=KnowledgeFindingCategory.BROKEN_LINEAGE,
                severity_hint=KnowledgeSeverity.CRITICAL,
                guidance="A subgraph with more than one node contains no REQUIREMENT node.",
                policy_reference=_STRUCTURAL,
                evaluation_order=210,
                tags=("structural", "broken_lineage"),
            ),
            KnowledgeGraphRule(
                rule_id="KG-STR-006",
                rule_name="Cycle",
                family=KnowledgeGraphRuleFamily.STRUCTURAL,
                finding_category=KnowledgeFindingCategory.CYCLE,
                severity_hint=KnowledgeSeverity.CRITICAL,
                guidance="A directed cycle exists among the graph's governed edges.",
                policy_reference=_STRUCTURAL,
                evaluation_order=220,
                tags=("structural", "cycle"),
            ),
        )
        return KnowledgeGraphRuleCatalog(
            catalog_version=KNOWLEDGE_GRAPH_RULE_CATALOG_VERSION, rules=rules
        )


def default_knowledge_graph_rule_catalog() -> KnowledgeGraphRuleCatalog:
    """Return the framework's default governed rule catalogue."""
    return KnowledgeGraphRuleBuilder().build()
