"""The :class:`KnowledgeSummary` and :class:`KnowledgeMetrics` — the headline
projections for one Knowledge Graph build.

Both are pure aggregation models: **assembly targets only**. Every field is
supplied by a future assembler; nothing here is computed (mirroring
``ImprovementSummary`` / ``ImprovementMetrics``, ADR-0022).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgePolicyId,
    KnowledgePolicyVersion,
)
from shared.contracts.base import Schema


class KnowledgeSummary(Schema):
    """The governed headline for one Knowledge Graph build. A pure data container.

    ``headline`` is a one-line, deterministic description of the graph's shape
    (e.g. counts), analogous to ``ImprovementSummary.headline`` — Knowledge Graph
    renders **no prediction, optimization, or plan**: it is structural observation
    only (Recommendation 6 of ADR-0023; prediction is Layer 4's job, optimization
    Layer 5's, both reserved by ADR-0020).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: KnowledgePolicyId = Field(..., description="Governing policy identity.")
    policy_version: KnowledgePolicyVersion = Field(..., description="Governing policy version.")

    total_nodes: int = Field(..., ge=0, description="Total nodes recorded.")
    total_edges: int = Field(..., ge=0, description="Total edges recorded.")
    total_subgraphs: int = Field(..., ge=0, description="Total subgraphs recorded.")
    total_observations: int = Field(..., ge=0, description="Total observations recorded.")
    total_findings: int = Field(..., ge=0, description="Total findings recorded.")

    headline: str = Field(..., min_length=1, description="One-line deterministic build summary.")


class KnowledgeMetrics(Schema):
    """Deterministic numeric roll-ups for one Knowledge Graph build. Data only.

    Every statistic is recorded, never computed by this model — a future metrics
    assembler derives them from the nodes/edges/subgraphs, exactly as
    ``ImprovementMetrics`` are recorded values, not model-internal calculations.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    node_count: int = Field(..., ge=0, description="Total number of nodes.")
    edge_count: int = Field(..., ge=0, description="Total number of edges.")
    subgraph_count: int = Field(..., ge=0, description="Total number of subgraphs.")
    connected_component_count: int = Field(
        ..., ge=0, description="Number of connected components in the graph."
    )
    average_degree: float = Field(..., ge=0.0, description="Average node degree across the graph.")
    orphan_node_count: int = Field(
        ..., ge=0, description="Number of nodes with no incident edges."
    )
