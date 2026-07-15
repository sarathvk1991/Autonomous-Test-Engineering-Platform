"""Deterministic :class:`KnowledgeGraphResult` assembly (CAP-084B).

``ResultBuilder`` is the **only constructor** of ``KnowledgeGraphResult``
anywhere in this engine — no other module assembles the final result. It mints
the result's own identity from the already-computed graph id and assembles the
frozen contract from already-finished collaborators. It computes nothing itself
beyond minting that one deterministic id.
"""

from __future__ import annotations

from datetime import datetime

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeGraphFrameworkVersion,
    KnowledgeGraphId,
    KnowledgeGraphResultId,
)
from requirement_intelligence.knowledge_graph.models.edge import KnowledgeEdge
from requirement_intelligence.knowledge_graph.models.finding import KnowledgeFinding
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.observation import KnowledgeObservation
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult
from requirement_intelligence.knowledge_graph.models.subgraph import KnowledgeSubgraph
from requirement_intelligence.knowledge_graph.models.summary import (
    KnowledgeMetrics,
    KnowledgeSummary,
)
from requirement_intelligence.knowledge_graph.policy import KnowledgeGraphPolicy


class ResultBuilder:
    """Assemble the one :class:`KnowledgeGraphResult` for a build. Computed once."""

    def build(
        self,
        *,
        graph_id: KnowledgeGraphId,
        historical_dataset: HistoricalDatasetReference,
        nodes: tuple[KnowledgeNode, ...],
        edges: tuple[KnowledgeEdge, ...],
        subgraphs: tuple[KnowledgeSubgraph, ...],
        observations: tuple[KnowledgeObservation, ...],
        findings: tuple[KnowledgeFinding, ...],
        summary: KnowledgeSummary,
        metrics: KnowledgeMetrics,
        policy: KnowledgeGraphPolicy,
        framework_version: KnowledgeGraphFrameworkVersion,
        started_at: datetime,
        completed_at: datetime,
    ) -> KnowledgeGraphResult:
        """Assemble the frozen ``KnowledgeGraphResult`` from already-finished collaborators."""
        return KnowledgeGraphResult(
            result_id=KnowledgeGraphResultId.for_graph(str(graph_id)),
            graph_id=graph_id,
            historical_dataset=historical_dataset,
            nodes=nodes,
            edges=edges,
            subgraphs=subgraphs,
            observations=observations,
            findings=findings,
            summary=summary,
            metrics=metrics,
            policy_id=policy.policy_id,
            policy_version=policy.policy_version,
            framework_version=framework_version,
            started_at=started_at,
            completed_at=completed_at,
        )
