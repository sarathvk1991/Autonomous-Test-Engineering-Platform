"""The canonical :class:`ClassificationResult` — Matching's output, classified.

``ClassificationResult`` is the **internal** canonical contract between Support
Classification and Confidence (CAP-077D). It records the support verdict for one
requirement plus the evidence links partitioned by role, and a short deterministic
reason. It is *not* an execution artifact and is *not* exposed outside the Grounding
subsystem.

Pipeline position::

    MatchResult → ClassificationResult → Confidence → GroundedRequirement

Keeping this as a distinct model isolates CAP-077D: confidence is computed *from* a
``ClassificationResult`` without re-running matching or re-classifying.

Immutability & determinism
--------------------------
A frozen :class:`~shared.contracts.base.Schema` with tuple-backed collections and
camelCase serialisation. No timestamps, UUIDs, or runtime objects. Classifying the
same ``MatchResult`` under the same policy yields an equal result.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity import (
    ClassificationVersion,
    GroundedRequirementId,
)
from requirement_intelligence.grounding.models.enums import SupportClassification
from requirement_intelligence.grounding.models.evidence import RequirementEvidenceLink
from shared.contracts.base import Schema

#: Version of the ``ClassificationResult`` schema (not the policy). Advances
#: additively; a shape change a prior consumer could misread is MAJOR.
CLASSIFICATION_VERSION = ClassificationVersion(1, 0, 0)


class ClassificationResult(Schema):
    """The complete support-classification output for one requirement.

    Internal to Grounding. Built by :class:`SupportClassificationEngine` from a
    ``MatchResult``; consumed by the confidence calculator (CAP-077D) and the
    ``GroundedRequirementBuilder``.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    requirement_id: GroundedRequirementId = Field(..., description="The classified requirement.")
    support_classification: SupportClassification = Field(..., description="The support verdict.")

    supporting_links: tuple[RequirementEvidenceLink, ...] = Field(
        default=(), description="Direct/corroborating support links."
    )
    contradicting_links: tuple[RequirementEvidenceLink, ...] = Field(
        default=(), description="Contradicting/negative links."
    )
    partial_links: tuple[RequirementEvidenceLink, ...] = Field(
        default=(), description="Partial support links."
    )
    derived_links: tuple[RequirementEvidenceLink, ...] = Field(
        default=(), description="Derived support links."
    )
    unknown_links: tuple[RequirementEvidenceLink, ...] = Field(
        default=(), description="Links whose relation the policy does not categorise."
    )

    classification_reason: str = Field(
        ..., min_length=1, description="Deterministic reason for the verdict (governed, not prose)."
    )
    classification_version: ClassificationVersion = Field(
        default=CLASSIFICATION_VERSION, description="Version of the ClassificationResult schema."
    )

    @property
    def evidence_links(self) -> tuple[RequirementEvidenceLink, ...]:
        """All links, in canonical role order — the grounding of the requirement."""
        return (
            self.supporting_links
            + self.partial_links
            + self.derived_links
            + self.contradicting_links
            + self.unknown_links
        )
