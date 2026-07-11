"""Builder for :class:`GroundingAssessment`.

Construction only. The builder mints the deterministic ``GroundingAssessmentId``
as a pure function of the context id and the graded requirements, then defers to
the assessment's validators (findings reference known requirements; a finding
exists for exactly the hallucinated requirements). It computes no metric.
"""

from __future__ import annotations

from collections.abc import Sequence

from requirement_intelligence.grounding.identity.grounding_identity import (
    GroundingAssessmentId,
    GroundingConfigurationVersion,
    GroundingFrameworkVersion,
)
from requirement_intelligence.grounding.models.assessment import (
    GroundingAssessment,
    GroundingSummary,
)
from requirement_intelligence.grounding.models.findings import GroundingFinding
from requirement_intelligence.grounding.models.grounded_requirement import GroundedRequirement
from requirement_intelligence.grounding.models.metrics import GroundingMetrics
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)


def _assessment_content(requirements: Sequence[GroundedRequirement]) -> str:
    """A stable, order-preserving fingerprint of the graded requirements."""
    return "\n".join(f"{req.requirement_id}:{req.classification}" for req in requirements)


class GroundingAssessmentBuilder:
    """Assemble a :class:`GroundingAssessment`, minting its deterministic id."""

    def build(
        self,
        *,
        context_id: str,
        grounded_requirements: tuple[GroundedRequirement, ...],
        metrics: GroundingMetrics,
        summary: GroundingSummary,
        findings: tuple[GroundingFinding, ...] = (),
        framework_version: GroundingFrameworkVersion = GROUNDING_FRAMEWORK_VERSION,
        configuration_version: GroundingConfigurationVersion = GROUNDING_CONFIGURATION_VERSION,
    ) -> GroundingAssessment:
        """Return a validated grounding assessment for the supplied grading."""
        assessment_id = GroundingAssessmentId.for_run(
            context_id, _assessment_content(grounded_requirements)
        )
        return GroundingAssessment(
            assessment_id=assessment_id,
            context_id=context_id,
            grounded_requirements=grounded_requirements,
            findings=findings,
            metrics=metrics,
            summary=summary,
            framework_version=framework_version,
            configuration_version=configuration_version,
        )
