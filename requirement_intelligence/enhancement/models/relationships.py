"""The :class:`RequirementRelationship` and the canonical :class:`RelationshipGraph`.

Recommendation 2 (ADR-0018): one canonical relationship model covers every
relationship type in :class:`~requirement_intelligence.enhancement.models.enums.
RelationshipType`. Future capabilities add a *type*, never a new relationship model.

Recommendation 6 (ADR-0018): all future analyses that reason about requirement
relationships — duplicates, dependencies, contradictions, traceability, impact
analysis — derive from the one canonical :class:`RelationshipGraph`, never a separate
relationship store. This is Requirement Enhancement's single source of truth for
requirement relationships.

Both models carry information only; validators enforce cross-referential integrity —
never a computed confidence, weight, or derived semantic — exactly mirroring the
``QualityGovernanceResult`` / ``QualityAssessment`` validator convention (ADR-0017 §D3).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.enhancement.identity.enhancement_identity import (
    RelationshipGraphId,
)
from requirement_intelligence.enhancement.models.enums import RelationshipType
from shared.contracts.base import Schema


class RequirementRelationship(Schema):
    """One directed, typed edge between two requirements. Data only.

    ``source_requirement_id`` and ``target_requirement_id`` name the source
    requirements they relate (owned upstream, by Analysis / Consolidation) — this
    model never copies their content. No relationship is derived here; a future
    relationship-detection engine populates ``relationship_type`` and ``rationale``.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    relationship_id: str = Field(..., min_length=1, description="Identity of this relationship.")
    source_requirement_id: str = Field(
        ..., min_length=1, description="The relationship's source requirement id."
    )
    target_requirement_id: str = Field(
        ..., min_length=1, description="The relationship's target requirement id."
    )
    relationship_type: RelationshipType = Field(
        ..., description="The governed relationship type (Recommendation 2)."
    )
    rationale: str = Field(
        ..., min_length=1, description="Human-readable reason the relationship was recorded."
    )

    @model_validator(mode="after")
    def _validate_relationship(self) -> RequirementRelationship:
        """A requirement cannot relate to itself."""
        if self.source_requirement_id == self.target_requirement_id:
            raise ValueError("A requirement relationship cannot name the same requirement twice.")
        return self


class RelationshipGraph(Schema):
    """The single canonical requirement-relationship graph for one enhancement run.

    ``requirement_ids`` are the graph's nodes; ``relationships`` are its edges. Every
    edge must reference nodes already present in the graph — the validator enforces
    that structural integrity, never a graph algorithm (no cycle detection, no
    traversal, no derived metric). Future traversal/analysis capabilities read this
    graph; they never build a second one (Recommendation 6).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    graph_id: RelationshipGraphId = Field(..., description="Deterministic graph identity.")
    requirement_ids: tuple[str, ...] = Field(
        default=(), description="The graph's nodes — every requirement id it names."
    )
    relationships: tuple[RequirementRelationship, ...] = Field(
        default=(), description="The graph's edges."
    )

    @model_validator(mode="after")
    def _validate_graph(self) -> RelationshipGraph:
        """Every edge must reference nodes already present in the graph."""
        nodes = set(self.requirement_ids)
        for relationship in self.relationships:
            if relationship.source_requirement_id not in nodes:
                raise ValueError(
                    f"Relationship {relationship.relationship_id!r} names source "
                    f"requirement {relationship.source_requirement_id!r}, which is not "
                    f"a node of this graph."
                )
            if relationship.target_requirement_id not in nodes:
                raise ValueError(
                    f"Relationship {relationship.relationship_id!r} names target "
                    f"requirement {relationship.target_requirement_id!r}, which is not "
                    f"a node of this graph."
                )
        relationship_ids = [relationship.relationship_id for relationship in self.relationships]
        if len(relationship_ids) != len(set(relationship_ids)):
            raise ValueError("RelationshipGraph must not contain duplicate relationship ids.")
        return self
