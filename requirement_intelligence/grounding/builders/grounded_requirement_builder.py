"""Builder for :class:`GroundedRequirement`.

Construction only. Since CAP-077C the builder assembles a grounded requirement from a
:class:`ClassificationResult` (the support verdict + partitioned evidence links) rather
than taking a bare classification, so classification is never re-performed here. It
still takes the confidence and explanation as inputs — the builder computes neither.
Confidence remains a caller-supplied placeholder until CAP-077D.
"""

from __future__ import annotations

from requirement_intelligence.grounding.classification.models import ClassificationResult
from requirement_intelligence.grounding.identity.grounding_identity import GroundedRequirementId
from requirement_intelligence.grounding.models.confidence import GroundingConfidence
from requirement_intelligence.grounding.models.explanation import GroundingExplanation
from requirement_intelligence.grounding.models.grounded_requirement import GroundedRequirement
from requirement_intelligence.models.enums import SourceCategory


class GroundedRequirementBuilder:
    """Assemble a :class:`GroundedRequirement` from a classified requirement."""

    def build(
        self,
        *,
        classification_result: ClassificationResult,
        confidence: GroundingConfidence,
        explanation: GroundingExplanation,
        domain: SourceCategory,
        text: str,
        position: int,
    ) -> GroundedRequirement:
        """Return a validated grounded requirement for the supplied classification.

        The requirement id, support verdict, and evidence links come from
        *classification_result*; the id is re-derived from ``(domain, text)`` and must
        match — a guard that the classification answers this requirement.
        """
        requirement_id = GroundedRequirementId.for_requirement(domain, text)
        if requirement_id != classification_result.requirement_id:
            raise ValueError(
                f"ClassificationResult is for '{classification_result.requirement_id}', "
                f"not the requirement '{requirement_id}' being built."
            )
        return GroundedRequirement(
            requirement_id=requirement_id,
            domain=domain,
            text=text,
            position=position,
            classification=classification_result.support_classification,
            confidence=confidence,
            evidence_links=classification_result.evidence_links,
            explanation=explanation,
        )
