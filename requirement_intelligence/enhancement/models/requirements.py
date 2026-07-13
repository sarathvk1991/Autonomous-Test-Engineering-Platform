"""The :class:`EnhancedRequirement` — the single canonical enriched requirement.

Recommendation 1 (ADR-0018): there must never be multiple "enhanced requirement"
representations. Every future enrichment stage — deterministic tagging, AI-assisted
enrichment, historical intelligence — extends this one model rather than inventing a
competing structure. It carries information only; a future enrichment engine populates
it, this model never derives anything.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.enhancement.identity.enhancement_identity import (
    EnhancedRequirementId,
)
from shared.contracts.base import Schema


class EnhancementAttribute(Schema):
    """One deterministic key/value attribute attached to an enriched requirement.

    A generic, governed extension point: a future enrichment engine attaches
    attributes (e.g. a derived tag, a classification label) without widening
    :class:`EnhancedRequirement` itself. The attribute carries no computation — it is
    populated by whichever engine derived it.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    key: str = Field(..., min_length=1, description="The attribute's governed name.")
    value: str = Field(..., description="The attribute's value.")


class EnhancedRequirement(Schema):
    """The canonical, immutable enrichment of one generated requirement.

    References the source requirement by id; it never copies or reinterprets the
    requirement's own content (that remains owned by Analysis / Consolidation). This
    model only carries what Requirement Enhancement adds: deterministic attributes and
    the ids of the relationships and observations that involve this requirement —
    never duplicated content, only references (mirrors ``AssessmentFindingReference``'s
    reference-not-copy convention, ADR-0017 §D26).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    enhanced_requirement_id: EnhancedRequirementId = Field(
        ..., description="Deterministic identity of this enrichment."
    )
    requirement_id: str = Field(
        ..., min_length=1, description="Identity of the source requirement (owned upstream)."
    )
    attributes: tuple[EnhancementAttribute, ...] = Field(
        default=(), description="Deterministic attributes a future enrichment engine attaches."
    )
    relationship_ids: tuple[str, ...] = Field(
        default=(),
        description="Ids of the RequirementRelationship edges this requirement participates in.",
    )
    observation_ids: tuple[str, ...] = Field(
        default=(),
        description="Ids of the RequirementObservation entries naming this requirement.",
    )
