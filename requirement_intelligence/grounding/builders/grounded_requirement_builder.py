"""Builder for :class:`GroundedRequirement`.

Construction only. The builder mints the deterministic ``GroundedRequirementId``
from the requirement's domain and text so callers never invent one, then defers
to the model's validators to reject an invalid combination. It performs **no
matching, scoring, or classification** — every graded input is supplied.
"""

from __future__ import annotations

from requirement_intelligence.grounding.identity.grounding_identity import GroundedRequirementId
from requirement_intelligence.grounding.models.confidence import GroundingConfidence
from requirement_intelligence.grounding.models.enums import SupportClassification
from requirement_intelligence.grounding.models.evidence import RequirementEvidenceLink
from requirement_intelligence.grounding.models.explanation import GroundingExplanation
from requirement_intelligence.grounding.models.grounded_requirement import GroundedRequirement
from requirement_intelligence.models.enums import SourceCategory


class GroundedRequirementBuilder:
    """Assemble a :class:`GroundedRequirement`, minting its deterministic id."""

    def build(
        self,
        *,
        domain: SourceCategory,
        text: str,
        position: int,
        classification: SupportClassification,
        confidence: GroundingConfidence,
        explanation: GroundingExplanation,
        evidence_links: tuple[RequirementEvidenceLink, ...] = (),
    ) -> GroundedRequirement:
        """Return a validated grounded requirement for the supplied grading."""
        requirement_id = GroundedRequirementId.for_requirement(domain, text)
        return GroundedRequirement(
            requirement_id=requirement_id,
            domain=domain,
            text=text,
            position=position,
            classification=classification,
            confidence=confidence,
            evidence_links=evidence_links,
            explanation=explanation,
        )
