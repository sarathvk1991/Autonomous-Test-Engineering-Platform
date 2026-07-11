"""Builder for :class:`GroundingResult`.

Construction only. The builder ties a completed :class:`GroundingAssessment` to
the analysis it graded and stamps the framework and configuration versions.
Timestamps are supplied by the caller (never read from the clock here), so the
builder itself introduces no non-determinism.
"""

from __future__ import annotations

from datetime import datetime

from requirement_intelligence.grounding.identity.grounding_identity import (
    GroundingConfigurationVersion,
    GroundingFrameworkVersion,
)
from requirement_intelligence.grounding.models.assessment import (
    GroundingAssessment,
    GroundingResult,
)
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)


class GroundingResultBuilder:
    """Assemble the :class:`GroundingResult` carrier for one run."""

    def build(
        self,
        *,
        analysis_id: str,
        execution_id: str,
        assessment: GroundingAssessment,
        started_at: datetime,
        completed_at: datetime,
        framework_version: GroundingFrameworkVersion = GROUNDING_FRAMEWORK_VERSION,
        configuration_version: GroundingConfigurationVersion = GROUNDING_CONFIGURATION_VERSION,
    ) -> GroundingResult:
        """Return a validated grounding result carrier."""
        return GroundingResult(
            analysis_id=analysis_id,
            execution_id=execution_id,
            assessment=assessment,
            framework_version=framework_version,
            configuration_version=configuration_version,
            started_at=started_at,
            completed_at=completed_at,
        )
