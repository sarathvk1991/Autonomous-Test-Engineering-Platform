"""The :class:`KnowledgeNode` — one platform entity, referenced by id only.

A ``KnowledgeNode`` represents one platform entity — a requirement, a module, a
component, an execution, a finding, a recommendation, a capability, a dataset, a
document (the governed ``KnowledgeNodeType`` vocabulary). It **never owns the
entity itself**: it carries only the entity's own identifier and a human-readable
label, never a copy of the entity's content (Recommendation 2 of ADR-0023, mirroring
every prior subsystem's reference-not-copy convention, e.g.
``RecommendationReference``, ``EnhancementFinding``'s observation reference).

No node is derived here — a future engine (CAP-084B) populates this model by
projecting subsystem-local structures (e.g. Requirement Enhancement's
``RelationshipGraph``) into the canonical platform graph; this milestone only
shapes the contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.knowledge_graph.identity import KnowledgeNodeId
from requirement_intelligence.knowledge_graph.models.enums import KnowledgeNodeType
from shared.contracts.base import Schema


class KnowledgeNode(Schema):
    """One platform entity — data only, referencing an external object by id alone."""

    model_config = ConfigDict(alias_generator=to_camel)

    node_id: KnowledgeNodeId = Field(..., description="Deterministic identity of this node.")
    node_type: KnowledgeNodeType = Field(
        ..., description="The governed platform entity type this node represents."
    )
    referenced_id: str = Field(
        ...,
        min_length=1,
        description="Identity of the referenced platform entity. Never the entity itself.",
    )
    label: str = Field(..., min_length=1, description="Human-readable display label.")
