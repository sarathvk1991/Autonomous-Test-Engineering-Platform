"""The :class:`KnowledgeFinding` — one deterministic structural issue.

A ``KnowledgeFinding`` names one deterministically distinguishable structural
issue — an isolated node, broken lineage, a duplicate edge, an orphan graph, a
missing relationship, a cycle (the governed ``KnowledgeFindingCategory``
vocabulary). It is **structural only**, never a quality, governance, or
recommendation judgement (those remain Layer 1's own finding vocabularies).

No finding is derived here — a future engine (CAP-084B) populates this model by
reference from already-computed nodes/edges; this milestone only shapes the
contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeEdgeId,
    KnowledgeFindingId,
    KnowledgeNodeId,
)
from requirement_intelligence.knowledge_graph.models.enums import (
    KnowledgeFindingCategory,
    KnowledgeSeverity,
)
from shared.contracts.base import Schema


class KnowledgeFinding(Schema):
    """One deterministic structural issue — data only, never a probabilistic judgement.

    ``subject_node_ids`` / ``subject_edge_ids`` name every node/edge this finding
    concerns, by id only — never by embedding that node's or edge's content
    (Recommendation 2 of ADR-0023, mirroring ``ImprovementOpportunity``'s
    reference-only evidence, ADR-0022).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    finding_id: KnowledgeFindingId = Field(
        ..., description="Deterministic identity of this finding."
    )
    category: KnowledgeFindingCategory = Field(
        ..., description="The governed structural issue this finding names."
    )
    severity: KnowledgeSeverity = Field(..., description="The finding's recorded severity.")
    subject_node_ids: tuple[KnowledgeNodeId, ...] = Field(
        default=(), description="Nodes this finding concerns (reference only)."
    )
    subject_edge_ids: tuple[KnowledgeEdgeId, ...] = Field(
        default=(), description="Edges this finding concerns (reference only)."
    )
    message: str = Field(..., min_length=1, description="Human-readable description.")

    @model_validator(mode="after")
    def _validate_finding(self) -> KnowledgeFinding:
        """A finding must be explainable from at least one node or edge."""
        if not self.subject_node_ids and not self.subject_edge_ids:
            raise ValueError(
                f"KnowledgeFinding {self.finding_id!r} must reference at least one node or "
                f"edge — a finding with no traceable evidence is not explainable."
            )
        return self
