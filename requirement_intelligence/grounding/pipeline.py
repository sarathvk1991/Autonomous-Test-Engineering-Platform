"""The private :class:`GroundingPipeline` — the frozen stage sequencer (CAP-077E).

An internal implementation detail behind :meth:`GroundingService.assess`. It owns
**sequencing only** — iteration, ordering, and delegation — and computes nothing itself:
every stage is a governed component it invokes. It is not public and not registered in
``PlatformContext`` as a factory; the composition root constructs it inside
``create_grounding_service`` and injects it into the service.

Frozen execution order (ADR-0016 §D15)::

    EngineeringContext + AnalysisResult
      → MatchingContextBuilder → MatchingContext → MatchingRequest(s)
      → GroundingStrategy (normalizes internally) → MatchResult
      → SupportClassificationEngine → ClassificationResult
      → ConfidenceCalculator → ConfidenceAssessment
      → GroundedRequirementBuilder → GroundedRequirement
      → GroundingMetricsBuilder → GroundingMetrics + GroundingSummary
      → GroundingResultBuilder → GroundingResult

Processing is **sequential** and deterministic (no parallelism, no randomness; timestamps
come from an injected clock so a fixed clock yields a byte-identical result).

Failure semantics (ADR-0016 §D15): a requirement that cannot be grounded becomes an
UNSUPPORTED fallback (and therefore a ``GroundingFinding``) and processing continues — a
``GroundingResult`` is always produced. A *service-level* failure before requirement
processing (e.g. ``MatchingContextBuilder`` rejecting a malformed ``AnalysisResult``)
propagates and fails the whole ``assess`` call.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration.models.engineering_context import (
    EngineeringContext,
)
from requirement_intelligence.grounding.builders.grounded_requirement_builder import (
    GroundedRequirementBuilder,
)
from requirement_intelligence.grounding.builders.grounding_assessment_builder import (
    GroundingAssessmentBuilder,
)
from requirement_intelligence.grounding.builders.grounding_result_builder import (
    GroundingResultBuilder,
)
from requirement_intelligence.grounding.builders.matching_context_builder import (
    MatchingContextBuilder,
)
from requirement_intelligence.grounding.classification.engine import SupportClassificationEngine
from requirement_intelligence.grounding.classification.models import ClassificationResult
from requirement_intelligence.grounding.confidence.calculator import ConfidenceCalculator
from requirement_intelligence.grounding.confidence.models import (
    ConfidenceAssessment,
    ConfidenceExplanation,
)
from requirement_intelligence.grounding.config import GroundingConfiguration
from requirement_intelligence.grounding.contracts.grounding_strategy import GroundingStrategy
from requirement_intelligence.grounding.metrics_builder import GroundingMetricsBuilder
from requirement_intelligence.grounding.models.assessment import GroundingResult
from requirement_intelligence.grounding.models.enums import (
    HALLUCINATION_CLASSIFICATIONS,
    ConfidenceBand,
    GroundingSeverity,
    SupportClassification,
)
from requirement_intelligence.grounding.models.explanation import GroundingExplanation
from requirement_intelligence.grounding.models.findings import GroundingFinding
from requirement_intelligence.grounding.models.grounded_requirement import GroundedRequirement
from requirement_intelligence.grounding.models.match_result import MatchResult
from requirement_intelligence.grounding.models.matching import MatchingRequest, MatchingRequirement


class GroundingPipeline:
    """Sequences the grounding stages for one run. Delegation only — computes nothing."""

    def __init__(
        self,
        *,
        matching_context_builder: MatchingContextBuilder,
        strategy: GroundingStrategy,
        classification_engine: SupportClassificationEngine,
        confidence_calculator: ConfidenceCalculator,
        grounded_requirement_builder: GroundedRequirementBuilder,
        metrics_builder: GroundingMetricsBuilder,
        assessment_builder: GroundingAssessmentBuilder,
        result_builder: GroundingResultBuilder,
        configuration: GroundingConfiguration,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Wire the governed collaborators this pipeline delegates to."""
        self._matching_context_builder = matching_context_builder
        self._strategy = strategy
        self._classification_engine = classification_engine
        self._confidence_calculator = confidence_calculator
        self._grounded_requirement_builder = grounded_requirement_builder
        self._metrics_builder = metrics_builder
        self._assessment_builder = assessment_builder
        self._result_builder = result_builder
        self._configuration = configuration
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self, engineering_context: EngineeringContext, analysis_result: AnalysisResult
    ) -> GroundingResult:
        """Run the frozen pipeline end to end and return the aggregate ``GroundingResult``."""
        started_at = self._clock()

        # Service-level stage: a failure here fails the whole run (no per-requirement work yet).
        matching_context = self._matching_context_builder.build(
            engineering_context, analysis_result, self._configuration
        )

        grounded: list[GroundedRequirement] = []
        for request in matching_context.to_requests():
            grounded.append(self._ground_one(request))

        findings = self._findings(grounded)
        metrics = self._metrics_builder.build(
            grounded, evidence_available=len(matching_context.evidence)
        )
        summary = self._metrics_builder.build_summary(grounded, metrics)
        assessment = self._assessment_builder.build(
            context_id=str(engineering_context.context_id),
            grounded_requirements=tuple(grounded),
            metrics=metrics,
            summary=summary,
            findings=findings,
        )
        completed_at = self._clock()
        return self._result_builder.build(
            analysis_id=analysis_result.analysis_id,
            execution_id=analysis_result.execution_id,
            assessment=assessment,
            started_at=started_at,
            completed_at=completed_at,
        )

    # -- per-requirement sequencing ---------------------------------------

    def _ground_one(self, request: MatchingRequest) -> GroundedRequirement:
        """Ground one requirement, or fall back to UNSUPPORTED on a requirement-level failure."""
        requirement = request.requirement
        try:
            match_result: MatchResult = self._strategy.match(request)
            classification = self._classification_engine.classify(match_result)
            confidence = self._confidence_calculator.calculate(classification)
        except Exception as exc:
            classification, confidence = self._fallback(requirement, exc)
        return self._grounded_requirement_builder.build(
            classification_result=classification,
            confidence_assessment=confidence,
            explanation=_explanation(classification, confidence),
            domain=requirement.domain,
            text=requirement.text,
            position=requirement.position,
        )

    def _fallback(
        self, requirement: MatchingRequirement, error: Exception
    ) -> tuple[ClassificationResult, ConfidenceAssessment]:
        """Represent a failed requirement as an UNSUPPORTED verdict with zero confidence."""
        reason = f"grounding failed: {type(error).__name__}: {error}"
        classification = ClassificationResult(
            requirement_id=requirement.requirement_id,
            support_classification=SupportClassification.UNSUPPORTED,
            classification_reason=reason,
        )
        confidence = ConfidenceAssessment(
            requirement_id=requirement.requirement_id,
            confidence_score=0,
            confidence_band=ConfidenceBand.LOW,
            confidence_explanation=ConfidenceExplanation(summary=reason),
        )
        return classification, confidence

    @staticmethod
    def _findings(
        grounded: list[GroundedRequirement],
    ) -> tuple[GroundingFinding, ...]:
        """One finding per hallucinated requirement — exactly what the assessment requires."""
        findings: list[GroundingFinding] = []
        for requirement in grounded:
            classification = SupportClassification(requirement.classification)
            if classification not in HALLUCINATION_CLASSIFICATIONS:
                continue
            severity = (
                GroundingSeverity.CRITICAL
                if classification == SupportClassification.CONTRADICTED
                else GroundingSeverity.WARNING
            )
            findings.append(
                GroundingFinding(
                    finding_id=f"gf-{requirement.requirement_id}",
                    requirement_id=requirement.requirement_id,
                    classification=classification,
                    severity=severity,
                    message=requirement.explanation.summary or str(classification),
                )
            )
        return tuple(findings)


def _explanation(
    classification: ClassificationResult, confidence: ConfidenceAssessment
) -> GroundingExplanation:
    """Assemble the requirement-scoped explanation from the classification and confidence."""
    supporting = tuple(link.evidence for link in classification.supporting_links)
    conflicting = tuple(link.evidence for link in classification.contradicting_links)
    return GroundingExplanation(
        summary=confidence.confidence_explanation.summary or classification.classification_reason,
        supporting_evidence=supporting,
        missing_evidence=() if supporting else ("no supporting evidence",),
        conflicting_evidence=conflicting,
        confidence_breakdown=confidence.confidence_components,
        recommendations=confidence.confidence_explanation.recommendations,
    )
