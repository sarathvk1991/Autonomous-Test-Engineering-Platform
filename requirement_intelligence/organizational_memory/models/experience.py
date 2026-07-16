"""The :class:`Experience` — one captured observation drawn from a completed
Layer 2 peer's Derived Knowledge.

An ``Experience`` names one Continuous Improvement or Knowledge Graph object
(a finding, a trend, an opportunity, a node, an edge, an observation, a
structural finding) that Organizational Memory has captured as raw material
for future promotion (ADR-0026 §Stage 2/6). It is the bottom rung of this
framework's own concrete model hierarchy — never a copy of the object it
names, only a governed reference to it (Recommendation 2 of ADR-0027).

No experience is captured here — a future engine (CAP-085B, reserved)
populates this model by reference from an already-completed
``ContinuousImprovementResult`` or ``KnowledgeGraphResult``; this milestone
only shapes the contract.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.organizational_memory.identity import ExperienceId
from requirement_intelligence.organizational_memory.models.enums import (
    OrganizationalMemoryConfidence,
    OrganizationalMemorySourceLayer,
)
from shared.contracts.base import Schema


class Experience(Schema):
    """One captured observation from a completed Layer 2 peer — data only.

    ``source_reference_id`` names the Continuous Improvement or Knowledge
    Graph object this experience concerns, by id only — never by embedding
    that object's content (Recommendation 2 of ADR-0027, mirroring
    ``KnowledgeNode.referenced_id`` and ``ImprovementFinding.
    contributing_execution_ids``'s reference-only discipline).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    experience_id: ExperienceId = Field(
        ..., description="Deterministic identity of this experience."
    )
    source_layer: OrganizationalMemorySourceLayer = Field(
        ..., description="Which completed Layer 2 peer this experience was captured from."
    )
    source_reference_id: str = Field(
        ...,
        min_length=1,
        description="Id of the Continuous Improvement or Knowledge Graph object referenced.",
    )
    description: str = Field(..., min_length=1, description="Human-readable description.")
    confidence: OrganizationalMemoryConfidence = Field(
        ..., description="Governed confidence in this experience (metadata, never truth)."
    )
