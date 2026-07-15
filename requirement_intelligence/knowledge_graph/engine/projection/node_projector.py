"""Deterministic node projection (CAP-084B).

``NodeProjector`` is the **sole node authority**: it is the only component that
constructs :class:`KnowledgeNode` instances from a resolved
:class:`~requirement_intelligence.knowledge_graph.engine.historical_dataset.
HistoricalDataset`. It performs **no inference, no AI, no heuristics** — every
node it emits is a direct, governed projection of an entity id the historical
dataset already names (Recommendation 2 of ADR-0023: nodes reference runtime
contracts, they never duplicate them).

Only governed node types are ever emitted, and only when the corresponding
:class:`KnowledgeGraphRule` is enabled and its gating policy switch is on. The
same dataset always produces identical node identifiers (`KnowledgeNodeId` is a
pure function of node type + referenced id) — determinism is structural, not a
best effort.
"""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.engine.historical_dataset import HistoricalDataset
from requirement_intelligence.knowledge_graph.identity import KnowledgeNodeId
from requirement_intelligence.knowledge_graph.models.enums import KnowledgeNodeType
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.policy import KnowledgeGraphPolicy
from requirement_intelligence.knowledge_graph.rules import (
    KnowledgeGraphRuleCatalog,
    KnowledgeGraphRuleFamily,
)

_LABELS = {
    KnowledgeNodeType.EXECUTION: "Execution",
    KnowledgeNodeType.REQUIREMENT: "Requirement",
    KnowledgeNodeType.RECOMMENDATION: "Recommendation",
    KnowledgeNodeType.FINDING: "Finding",
    KnowledgeNodeType.CAPABILITY: "Capability",
    KnowledgeNodeType.DOCUMENT: "Document",
    KnowledgeNodeType.DATASET: "Dataset",
}


class NodeProjector:
    """Project a resolved :class:`HistoricalDataset` into governed :class:`KnowledgeNode` entries.

    The sole node authority (Recommendation 1 of ADR-0023: Knowledge Graph owns
    platform structure). Deduplicates by :class:`KnowledgeNodeId` — the same
    referenced entity, seen across multiple executions, yields exactly one node.
    """

    def __init__(
        self, policy: KnowledgeGraphPolicy, rule_catalog: KnowledgeGraphRuleCatalog
    ) -> None:
        """Store the governed collaborators this projector reads. Construction only."""
        self._policy = policy
        self._catalog = rule_catalog

    def project(self, dataset: HistoricalDataset) -> tuple[KnowledgeNode, ...]:
        """Deterministically project *dataset* into governed nodes, in stable order."""
        enabled_types = self._enabled_node_types()
        nodes: dict[KnowledgeNodeId, KnowledgeNode] = {}

        for execution in dataset.executions:
            if KnowledgeNodeType.EXECUTION in enabled_types:
                self._add(nodes, KnowledgeNodeType.EXECUTION, execution.execution_id)
            if KnowledgeNodeType.REQUIREMENT in enabled_types:
                self._add(nodes, KnowledgeNodeType.REQUIREMENT, execution.requirement_id)
            if execution.recommendation_id and KnowledgeNodeType.RECOMMENDATION in enabled_types:
                self._add(nodes, KnowledgeNodeType.RECOMMENDATION, execution.recommendation_id)
            if execution.finding_id and KnowledgeNodeType.FINDING in enabled_types:
                self._add(nodes, KnowledgeNodeType.FINDING, execution.finding_id)
            if execution.capability_id and KnowledgeNodeType.CAPABILITY in enabled_types:
                self._add(nodes, KnowledgeNodeType.CAPABILITY, execution.capability_id)
            if execution.document_id and KnowledgeNodeType.DOCUMENT in enabled_types:
                self._add(nodes, KnowledgeNodeType.DOCUMENT, execution.document_id)

        if KnowledgeNodeType.DATASET in enabled_types:
            self._add(nodes, KnowledgeNodeType.DATASET, dataset.dataset_id)

        return tuple(nodes.values())

    def _enabled_node_types(self) -> frozenset[KnowledgeNodeType]:
        """Return the governed node types whose rule is enabled and policy-gated on."""
        types: set[KnowledgeNodeType] = set()
        for rule in self._catalog.by_family(KnowledgeGraphRuleFamily.NODE):
            if rule.node_type is None:
                continue
            if getattr(self._policy.capability_switches, str(rule.policy_reference)):
                types.add(rule.node_type)
        return frozenset(types)

    @staticmethod
    def _add(
        nodes: dict[KnowledgeNodeId, KnowledgeNode],
        node_type: KnowledgeNodeType,
        referenced_id: str,
    ) -> None:
        """Insert the node for *referenced_id* if not already present. Deduplication only."""
        node_id = KnowledgeNodeId.for_entity(node_type.value, referenced_id)
        if node_id in nodes:
            return
        nodes[node_id] = KnowledgeNode(
            node_id=node_id,
            node_type=node_type,
            referenced_id=referenced_id,
            label=f"{_LABELS[node_type]} {referenced_id}",
        )
