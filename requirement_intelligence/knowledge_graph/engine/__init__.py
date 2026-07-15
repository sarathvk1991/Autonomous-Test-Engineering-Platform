"""The deterministic Knowledge Graph engine and its private collaborators (CAP-084B).

Only :class:`DeterministicKnowledgeGraphEngine`, :class:`HistoricalDatasetProvider`,
:class:`DeterministicHistoricalDatasetProvider`, :class:`HistoricalDataset`, and
:class:`HistoricalExecutionRecord` are exported at this level — for construction
by :class:`~requirement_intelligence.knowledge_graph.knowledge_graph_service.
DeterministicKnowledgeGraphService` only. The projection, analysis, and builder
subpackages are internal collaborators: none of them is a runtime contract, and
none is exported from the top-level ``knowledge_graph`` package.
"""

from __future__ import annotations

from requirement_intelligence.knowledge_graph.engine.deterministic_engine import (
    DeterministicKnowledgeGraphEngine,
)
from requirement_intelligence.knowledge_graph.engine.historical_dataset import (
    DeterministicHistoricalDatasetProvider,
    HistoricalDataset,
    HistoricalDatasetProvider,
    HistoricalExecutionRecord,
)

__all__ = [
    "DeterministicHistoricalDatasetProvider",
    "DeterministicKnowledgeGraphEngine",
    "HistoricalDataset",
    "HistoricalDatasetProvider",
    "HistoricalExecutionRecord",
]
