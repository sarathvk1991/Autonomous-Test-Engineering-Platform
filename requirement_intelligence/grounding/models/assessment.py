"""Aggregate grounding models: summary, assessment, and the result carrier.

:class:`GroundingAssessment` is the per-run root aggregate — every grounded
requirement, its findings, metrics, and headline summary. :class:`GroundingResult`
is the carrier that ties the assessment to the analysis it graded, a peer to
``AnalysisResult`` / ``ValidationResult`` / ``CP1Result``.

The validators enforce cross-referential integrity only (findings reference known
requirements; a finding exists for exactly the hallucinated requirements). No
metric is computed here.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.grounding.identity.grounding_identity import (
    GroundingAssessmentId,
    GroundingConfigurationVersion,
    GroundingFrameworkVersion,
    GroundingResultVersion,
)
from requirement_intelligence.grounding.models.enums import (
    HALLUCINATION_CLASSIFICATIONS,
    SupportClassification,
)
from requirement_intelligence.grounding.models.findings import GroundingFinding
from requirement_intelligence.grounding.models.grounded_requirement import GroundedRequirement
from requirement_intelligence.grounding.models.metrics import GroundingMetrics
from shared.contracts.base import Schema


class GroundingSummary(Schema):
    """The human-facing headline for one grounding assessment."""

    model_config = ConfigDict(alias_generator=to_camel)

    total_requirements: int = Field(..., ge=0)
    supported: int = Field(..., ge=0)
    partially_supported: int = Field(..., ge=0)
    unsupported: int = Field(..., ge=0)
    grounding_score: int = Field(..., ge=0, le=100)
    verdict: str = Field(..., min_length=1, description="One-line overall verdict.")


class GroundingAssessment(Schema):
    """The complete grounding assessment for one reasoning session."""

    model_config = ConfigDict(alias_generator=to_camel)

    assessment_id: GroundingAssessmentId = Field(..., description="Deterministic assessment id.")
    context_id: str = Field(..., min_length=1, description="Id of the EngineeringContext graded.")
    grounded_requirements: tuple[GroundedRequirement, ...] = Field(
        default=(), description="Every generated requirement, graded."
    )
    findings: tuple[GroundingFinding, ...] = Field(
        default=(), description="Hallucination findings (UNSUPPORTED / CONTRADICTED)."
    )
    metrics: GroundingMetrics = Field(..., description="The run's grounding metrics.")
    summary: GroundingSummary = Field(..., description="The headline summary.")
    framework_version: GroundingFrameworkVersion = Field(...)
    configuration_version: GroundingConfigurationVersion = Field(...)

    @model_validator(mode="after")
    def _validate_assessment(self) -> GroundingAssessment:
        """Findings must reference known requirements, one per hallucinated requirement."""
        requirement_ids = {str(req.requirement_id) for req in self.grounded_requirements}
        for finding in self.findings:
            if str(finding.requirement_id) not in requirement_ids:
                raise ValueError(
                    f"Finding '{finding.finding_id}' references requirement "
                    f"'{finding.requirement_id}', which is not in this assessment."
                )

        hallucinated = {
            str(req.requirement_id)
            for req in self.grounded_requirements
            if SupportClassification(req.classification) in HALLUCINATION_CLASSIFICATIONS
        }
        flagged = {str(finding.requirement_id) for finding in self.findings}
        if hallucinated != flagged:
            raise ValueError(
                "Findings must cover exactly the hallucinated requirements: "
                f"hallucinated={sorted(hallucinated)}, flagged={sorted(flagged)}."
            )
        return self


#: Version of the ``GroundingResult`` **runtime contract** schema. Independent of the
#: framework, strategy, match-result, classification, and confidence versions; a change
#: here never forces any of those to change, and vice versa.
GROUNDING_RESULT_VERSION = GroundingResultVersion(1, 0, 0)


class GroundingResult(Schema):
    """The complete, deterministic grounding assessment for one Requirement Intelligence run.

    ``GroundingResult`` is the **runtime contract** — the canonical repository-level
    aggregate the Grounding runtime produces and ``GroundingService.assess`` returns. It is
    the *only* runtime object that crosses into serialization. It is **not** a report, **not**
    an execution artifact, **not** serialization, **not** a renderer, and **not** a metrics
    calculator: it already contains everything (grounded requirements, findings, metrics,
    summary, explanations, versions) that any downstream projection needs.

    **Serialization invariant (frozen, CAP-077E.1).** Every execution artifact
    (``grounding_result.json``, ``grounding_report.md``, ``grounding_metrics.md``) is a
    **pure projection** of a ``GroundingResult`` — reproducible from it alone. A renderer
    must never invoke a strategy, normalizer, matching/classification/confidence policy,
    metrics builder, pipeline, or service, and must never recompute anything.

    **Version.** ``result_version`` carries the schema version of this runtime contract,
    so the contract can evolve without forcing renderer or framework changes.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    analysis_id: str = Field(..., min_length=1, description="The analysis this grounds.")
    execution_id: str = Field(..., min_length=1, description="The AI invocation this grounds.")
    assessment: GroundingAssessment = Field(..., description="The grounding assessment.")
    framework_version: GroundingFrameworkVersion = Field(...)
    configuration_version: GroundingConfigurationVersion = Field(...)
    result_version: GroundingResultVersion = Field(
        default=GROUNDING_RESULT_VERSION,
        description="Version of the GroundingResult runtime-contract schema.",
    )
    started_at: datetime = Field(..., description="When grounding started.")
    completed_at: datetime = Field(..., description="When grounding completed.")

    @model_validator(mode="after")
    def _validate_result(self) -> GroundingResult:
        """Completion cannot precede start."""
        if self.completed_at < self.started_at:
            raise ValueError("completed_at precedes started_at.")
        return self
