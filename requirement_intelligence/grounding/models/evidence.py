"""Evidence reference and requirement-to-evidence link models.

An :class:`EvidenceReference` is an immutable pointer back to one
``SourceArtifact`` in the ``EngineeringContext`` — by its stable
``(source_system, source_record_id)`` identity, never by the per-run ``uuid4``
``artifact_id``. A :class:`RequirementEvidenceLink` is one edge of the
traceability graph: a requirement, the evidence that bears on it, and how.

These models carry **no matching logic**. Construction and validation only; the
links are supplied by a future ``GroundingStrategy`` (CAP-077B).
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.models.enums import EvidenceRelation
from requirement_intelligence.models.enums import SourceCategory, SourceSystem, SourceType
from shared.contracts.base import Schema


class EvidenceReference(Schema):
    """An immutable pointer to one source artifact in the engineering context.

    Identity is ``(source_system, source_record_id)`` — the same traceable key a
    ``SourceArtifact`` carries back to its origin system. The per-run ``artifact_id``
    is deliberately not referenced: it is a ``uuid4`` and would make the reference
    non-reproducible.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    source_system: SourceSystem = Field(..., description="Origin system of the evidence.")
    source_record_id: str = Field(..., min_length=1, description="Stable id within the origin.")
    source_category: SourceCategory = Field(..., description="Evidence domain.")
    source_type: SourceType = Field(..., description="Record type of the evidence.")


class RequirementEvidenceLink(Schema):
    """One requirement-to-evidence edge: the evidence, the relation, and the match.

    ``match_score`` is a deterministic 0-100 measure a strategy assigns; ``matched_terms``
    records *what* earned the score, so the link is self-explaining. ``rationale`` is a
    short human-readable justification.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    evidence: EvidenceReference = Field(..., description="The referenced evidence artifact.")
    relation: EvidenceRelation = Field(
        ..., description="How the evidence relates to the requirement."
    )
    match_score: int = Field(..., ge=0, le=100, description="Deterministic 0-100 match strength.")
    matched_terms: tuple[str, ...] = Field(
        default=(), description="Terms that earned the match (explainability)."
    )
    rationale: str = Field(..., min_length=1, description="Why this link was drawn.")
