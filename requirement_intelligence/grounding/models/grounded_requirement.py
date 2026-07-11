"""The :class:`GroundedRequirement` — one generated requirement, graded.

A grounded requirement is the raw LLM requirement string *plus* its stable
identity, its support classification, its confidence, its evidence links, and its
structured explanation. It is the canonical downstream business object every later
phase consumes instead of the opaque raw string.

The validators enforce **contract invariants only** — they encode no matching,
scoring, or classification algorithm. They exist so an invalid grounded
requirement cannot be constructed (e.g. "supported" with no evidence).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity.grounding_identity import GroundedRequirementId
from requirement_intelligence.grounding.models.confidence import GroundingConfidence
from requirement_intelligence.grounding.models.enums import (
    CONFLICTING_RELATIONS,
    SUPPORTING_RELATIONS,
    EvidenceRelation,
    SupportClassification,
)
from requirement_intelligence.grounding.models.evidence import RequirementEvidenceLink
from requirement_intelligence.grounding.models.explanation import GroundingExplanation
from requirement_intelligence.models.enums import SourceCategory
from shared.contracts.base import Schema

_SUPPORTED_WITH_EVIDENCE = frozenset(
    {
        SupportClassification.SUPPORTED,
        SupportClassification.PARTIALLY_SUPPORTED,
        SupportClassification.WEAKLY_SUPPORTED,
    }
)


class GroundedRequirement(Schema):
    """One generated requirement together with its grounding verdict."""

    model_config = ConfigDict(alias_generator=to_camel)

    requirement_id: GroundedRequirementId = Field(..., description="Deterministic requirement id.")
    domain: SourceCategory = Field(..., description="The requirement's evidence domain.")
    text: str = Field(..., min_length=1, description="The generated requirement text.")
    position: int = Field(..., ge=0, description="Index within its category array in the response.")
    classification: SupportClassification = Field(..., description="Support verdict.")
    confidence: GroundingConfidence = Field(..., description="Deterministic confidence.")
    evidence_links: tuple[RequirementEvidenceLink, ...] = Field(
        default=(), description="The requirement-to-evidence links."
    )
    explanation: GroundingExplanation = Field(..., description="Structured explanation.")

    @property
    def source_systems(self) -> frozenset[str]:
        """Distinct origin systems across this requirement's evidence links."""
        return frozenset(str(link.evidence.source_system) for link in self.evidence_links)

    @model_validator(mode="after")
    def _validate_requirement(self) -> GroundedRequirement:
        """Enforce contract invariants between classification and evidence links."""
        relations = {EvidenceRelation(link.relation) for link in self.evidence_links}
        classification = SupportClassification(self.classification)

        if classification in _SUPPORTED_WITH_EVIDENCE and not (relations & SUPPORTING_RELATIONS):
            raise ValueError(
                f"Requirement '{self.requirement_id}' is classified '{classification}' but "
                f"carries no supporting evidence link."
            )
        if classification == SupportClassification.UNSUPPORTED and (
            relations & SUPPORTING_RELATIONS
        ):
            raise ValueError(
                f"Requirement '{self.requirement_id}' is UNSUPPORTED but carries a supporting "
                f"evidence link; an unsupported requirement has no support."
            )
        if classification == SupportClassification.CONTRADICTED and not (
            relations & CONFLICTING_RELATIONS
        ):
            raise ValueError(
                f"Requirement '{self.requirement_id}' is CONTRADICTED but carries no "
                f"contradicting or negative evidence link."
            )
        return self
