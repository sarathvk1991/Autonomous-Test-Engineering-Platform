"""Builder for :class:`GroundedRequirement`.

Construction only. Since CAP-077C the builder assembles a grounded requirement from a
:class:`ClassificationResult` (the support verdict + partitioned evidence links); since
CAP-077C.1 it consumes a :class:`ConfidenceAssessment` (the Confidence subsystem's
output) rather than a raw ``GroundingConfidence``. It performs **no** classification and
**no** confidence calculation — it only assembles. The requirement's carried
``GroundingConfidence`` is transcribed from the assessment.
"""

from __future__ import annotations

from requirement_intelligence.grounding.classification.models import ClassificationResult
from requirement_intelligence.grounding.confidence.models import ConfidenceAssessment
from requirement_intelligence.grounding.identity.grounding_identity import GroundedRequirementId
from requirement_intelligence.grounding.models.confidence import GroundingConfidence
from requirement_intelligence.grounding.models.explanation import GroundingExplanation
from requirement_intelligence.grounding.models.grounded_requirement import GroundedRequirement
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)
from requirement_intelligence.models.enums import SourceCategory


class GroundedRequirementBuilder:
    """Assemble a :class:`GroundedRequirement` from a classified, confidence-assessed input."""

    def build(
        self,
        *,
        classification_result: ClassificationResult,
        confidence_assessment: ConfidenceAssessment,
        explanation: GroundingExplanation,
        domain: SourceCategory,
        text: str,
        position: int,
    ) -> GroundedRequirement:
        """Return a validated grounded requirement.

        The verdict and evidence links come from *classification_result*; the carried
        confidence is transcribed from *confidence_assessment*. Both must answer the
        same requirement (id re-derived from ``(domain, text)`` and checked) — a guard
        that the inputs were assembled for this requirement. The builder computes
        nothing.
        """
        requirement_id = GroundedRequirementId.for_requirement(domain, text)
        if requirement_id != classification_result.requirement_id:
            raise ValueError(
                f"ClassificationResult is for '{classification_result.requirement_id}', "
                f"not the requirement '{requirement_id}' being built."
            )
        if requirement_id != confidence_assessment.requirement_id:
            raise ValueError(
                f"ConfidenceAssessment is for '{confidence_assessment.requirement_id}', "
                f"not the requirement '{requirement_id}' being built."
            )
        confidence = GroundingConfidence(
            score=confidence_assessment.confidence_score,
            band=confidence_assessment.confidence_band,
            components=confidence_assessment.confidence_components,
            configuration_version=GROUNDING_CONFIGURATION_VERSION,
            framework_version=GROUNDING_FRAMEWORK_VERSION,
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
