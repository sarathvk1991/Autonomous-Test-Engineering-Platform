"""Canonical, immutable models for the Knowledge Graph Framework."""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.models.edge import KnowledgeEdge
from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeEdgeType,
    KnowledgeFindingCategory,
    KnowledgeNodeType,
    KnowledgeObservationCategory,
    KnowledgeSeverity,
)
from requirement_intelligence.knowledge_graph.models.finding import KnowledgeFinding
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.observation import KnowledgeObservation
from requirement_intelligence.knowledge_graph.models.result import (
    KNOWLEDGE_GRAPH_RESULT_VERSION,
    KnowledgeGraphResult,
)
from requirement_intelligence.knowledge_graph.models.subgraph import KnowledgeSubgraph
from requirement_intelligence.knowledge_graph.models.summary import (
    KnowledgeMetrics,
    KnowledgeSummary,
)

__all__ = [
    "KNOWLEDGE_GRAPH_RESULT_VERSION",
    "HistoricalDatasetReference",
    "KnowledgeEdge",
    "KnowledgeEdgeType",
    "KnowledgeFinding",
    "KnowledgeFindingCategory",
    "KnowledgeGraphResult",
    "KnowledgeMetrics",
    "KnowledgeNode",
    "KnowledgeNodeType",
    "KnowledgeObservation",
    "KnowledgeObservationCategory",
    "KnowledgeSeverity",
    "KnowledgeSubgraph",
    "KnowledgeSummary",
]
