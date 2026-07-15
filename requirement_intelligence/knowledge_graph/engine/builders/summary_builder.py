"""Deterministic :class:`KnowledgeSummary` assembly (CAP-084B).

``SummaryBuilder`` computes the summary **exactly once** per build, from
already-finished nodes, edges, subgraphs, observations, and findings. It
recomputes nothing those collections already recorded — it only counts and
narrates.
"""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.models.edge import KnowledgeEdge
from requirement_intelligence.knowledge_graph.models.finding import KnowledgeFinding
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.observation import KnowledgeObservation
from requirement_intelligence.knowledge_graph.models.subgraph import KnowledgeSubgraph
from requirement_intelligence.knowledge_graph.models.summary import KnowledgeSummary
from requirement_intelligence.knowledge_graph.policy import KnowledgeGraphPolicy


class SummaryBuilder:
    """Assemble the one :class:`KnowledgeSummary` for a build. Computed once."""

    def build(
        self,
        policy: KnowledgeGraphPolicy,
        nodes: tuple[KnowledgeNode, ...],
        edges: tuple[KnowledgeEdge, ...],
        subgraphs: tuple[KnowledgeSubgraph, ...],
        observations: tuple[KnowledgeObservation, ...],
        findings: tuple[KnowledgeFinding, ...],
    ) -> KnowledgeSummary:
        """Return the headline summary for this build. Pure aggregation, no policy read
        beyond identity/version."""
        headline = (
            f"{len(nodes)} node(s), {len(edges)} edge(s), {len(subgraphs)} subgraph(s), "
            f"{len(observations)} observation(s), {len(findings)} finding(s)."
        )
        return KnowledgeSummary(
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            total_nodes=len(nodes),
            total_edges=len(edges),
            total_subgraphs=len(subgraphs),
            total_observations=len(observations),
            total_findings=len(findings),
            headline=headline,
        )
