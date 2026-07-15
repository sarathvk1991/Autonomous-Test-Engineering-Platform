"""The :class:`KnowledgeObservation` — one deterministic structural fact.

A ``KnowledgeObservation`` records a deterministic fact about the graph's
structure — coverage, lineage depth, structural consistency (the governed
``KnowledgeObservationCategory`` vocabulary) — never a problem with the graph
(that is the disjoint ``KnowledgeFinding`` vocabulary) and never a prediction or
probabilistic judgement (Recommendation 7 of ADR-0023: no AI, no LLM reasoning).

No observation is derived here — a future engine (CAP-084B) populates this model
by reference from already-computed nodes/edges; this milestone only shapes the
contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeId,
    KnowledgeNodeId,
    KnowledgeObservationId,
)
from requirement_intelligence.knowledge_graph.models.enums import KnowledgeObservationCategory
from shared.contracts.base import Schema


class KnowledgeObservation(Schema):
    """One deterministic structural fact — data only, never a judgement."""

    model_config = ConfigDict(alias_generator=to_camel)

    observation_id: KnowledgeObservationId = Field(
        ..., description="Deterministic identity of this observation."
    )
    category: KnowledgeObservationCategory = Field(
        ..., description="The governed structural fact this observation records."
    )
    subject_node_ids: tuple[KnowledgeNodeId, ...] = Field(
        default=(), description="Nodes this observation concerns (reference only)."
    )
    subject_edge_ids: tuple[KnowledgeEdgeId, ...] = Field(
        default=(), description="Edges this observation concerns (reference only)."
    )
    description: str = Field(..., min_length=1, description="Human-readable description.")
