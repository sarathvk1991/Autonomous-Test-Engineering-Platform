"""The :class:`KnowledgeSubgraph` — one coherent graph partition, by reference only.

A ``KnowledgeSubgraph`` names a coherent partition of the canonical platform
graph — a connected component, a module-scoped slice, or any other governed
grouping a future engine identifies. It references its member nodes and edges by
id only; it never embeds a copy of a ``KnowledgeNode`` or ``KnowledgeEdge``
(Recommendation 2 of ADR-0023) — the canonical objects live exclusively in
``KnowledgeGraphResult.nodes`` / ``.edges``.

No subgraph is derived here — a future engine (CAP-084B) populates this model;
this milestone only shapes the contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeId,
    KnowledgeNodeId,
    KnowledgeSubgraphId,
)
from shared.contracts.base import Schema


class KnowledgeSubgraph(Schema):
    """One coherent graph partition — reference only, never a copy of its members."""

    model_config = ConfigDict(alias_generator=to_camel)

    subgraph_id: KnowledgeSubgraphId = Field(
        ..., description="Deterministic identity of this subgraph."
    )
    label: str = Field(
        ..., min_length=1, description="Human-readable description of this partition."
    )
    node_ids: tuple[KnowledgeNodeId, ...] = Field(
        default=(), description="Member nodes of this partition (reference only)."
    )
    edge_ids: tuple[KnowledgeEdgeId, ...] = Field(
        default=(), description="Member edges of this partition (reference only)."
    )

    @model_validator(mode="after")
    def _validate_subgraph(self) -> KnowledgeSubgraph:
        """Member node/edge ids must not repeat within this partition."""
        if len(set(self.node_ids)) != len(self.node_ids):
            raise ValueError(
                f"KnowledgeSubgraph {self.subgraph_id!r} must not name the same node id twice."
            )
        if len(set(self.edge_ids)) != len(self.edge_ids):
            raise ValueError(
                f"KnowledgeSubgraph {self.subgraph_id!r} must not name the same edge id twice."
            )
        return self
