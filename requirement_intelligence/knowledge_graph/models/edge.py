"""The :class:`KnowledgeEdge` — one governed relationship between two nodes.

A ``KnowledgeEdge`` is a directed, typed relationship between exactly two
``KnowledgeNode`` entries, named from the governed ``KnowledgeEdgeType``
vocabulary — never a free-form relationship string (Recommendation 3 of ADR-0023).
It carries a rationale (why the relationship was recorded), mirroring
``RequirementRelationship`` (Requirement Enhancement's own execution-scoped
relationship edge, ADR-0018).

No edge is derived here — a future engine (CAP-084B) populates this model; this
milestone only shapes the contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.knowledge_graph.identity import KnowledgeEdgeId, KnowledgeNodeId
from requirement_intelligence.knowledge_graph.models.enums import KnowledgeEdgeType
from shared.contracts.base import Schema


class KnowledgeEdge(Schema):
    """One directed, governed relationship between two nodes — data only."""

    model_config = ConfigDict(alias_generator=to_camel)

    edge_id: KnowledgeEdgeId = Field(..., description="Deterministic identity of this edge.")
    edge_type: KnowledgeEdgeType = Field(
        ..., description="The governed relationship type this edge names."
    )
    source_node_id: KnowledgeNodeId = Field(..., description="The edge's originating node.")
    target_node_id: KnowledgeNodeId = Field(..., description="The edge's destination node.")
    rationale: str = Field(
        ..., min_length=1, description="Human-readable reason this relationship was recorded."
    )
