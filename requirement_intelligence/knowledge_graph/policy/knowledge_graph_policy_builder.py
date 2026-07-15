"""Builder for the governed :class:`KnowledgeGraphPolicy`.

Construction only. It assembles the framework's default governed policy — a
deterministic, immutable value — and rejects nothing beyond the model's own field
constraints. It ingests no node, ingests no edge, partitions no subgraph, observes
no fact, detects no finding, and has no runtime consumers.

CAP-084A ships the governed default at ``KnowledgePolicyVersion`` 1.0.0 with
``enable_deterministic_engine`` reserved off — no engine exists yet. The values
are **governed data**: tuning them is a versioned policy change, never an engine
code change, and no future engine hard-codes any of them (mirrors ADR-0022
Recommendation 5).
"""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.identity import KnowledgePolicyId
from requirement_intelligence.knowledge_graph.policy.knowledge_graph_policy import (
    KnowledgeGraphCapabilitySwitches,
    KnowledgeGraphPolicy,
    KnowledgeGraphThresholds,
)
from requirement_intelligence.knowledge_graph.version import KNOWLEDGE_POLICY_VERSION

#: The identity of the framework's default governed knowledge graph policy.
DEFAULT_KNOWLEDGE_GRAPH_POLICY_ID = KnowledgePolicyId("default-knowledge-graph-policy")


class KnowledgeGraphPolicyBuilder:
    """Assemble the governed default :class:`KnowledgeGraphPolicy`."""

    def build(self) -> KnowledgeGraphPolicy:
        """Return the framework's default governed knowledge graph policy."""
        return KnowledgeGraphPolicy(
            policy_id=DEFAULT_KNOWLEDGE_GRAPH_POLICY_ID,
            policy_version=KNOWLEDGE_POLICY_VERSION,
            description=(
                "Default knowledge graph policy (CAP-084A): governed capability "
                "switches and deterministic thresholds. No engine exists yet; the "
                "framework is architecture-only and unwired into any runtime pipeline."
            ),
            capability_switches=KnowledgeGraphCapabilitySwitches(
                enable_node_ingestion=True,
                enable_edge_ingestion=True,
                enable_subgraph_partitioning=True,
                enable_observation_generation=True,
                enable_finding_detection=True,
                enable_deterministic_engine=False,
                enable_ml_engine=False,
                enable_llm_engine=False,
            ),
            thresholds=KnowledgeGraphThresholds(
                max_nodes_per_graph=10_000,
                max_edges_per_graph=50_000,
                max_traversal_depth=25,
            ),
        )


def default_knowledge_graph_policy() -> KnowledgeGraphPolicy:
    """Return the framework's default governed knowledge graph policy."""
    return KnowledgeGraphPolicyBuilder().build()
