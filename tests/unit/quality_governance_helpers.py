"""Shared construction helpers for Quality Governance evaluator tests (CAP-080B).

Not a test module (no ``test_`` prefix, so pytest does not collect it). It builds valid,
tunable ``GroundingResult`` / ``ValidationResult`` / ``CP1Result`` carriers so each
evaluator test states only the metric it cares about. The evaluator reads a small,
well-defined slice of each result; these builders expose exactly that slice as keyword
arguments and default everything else to a clean, releasable run.
"""

from __future__ import annotations

from datetime import UTC, datetime

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.cp1.models import (
    CP1Finding,
    CP1FrameworkMetadata,
    CP1Input,
    CP1Result,
)
from requirement_intelligence.grounding.identity import GroundingAssessmentId
from requirement_intelligence.grounding.models import (
    GroundingAssessment,
    GroundingMetrics,
    GroundingResult,
    GroundingSummary,
)
from requirement_intelligence.grounding.version import (
    GROUNDING_CONFIGURATION_VERSION,
    GROUNDING_FRAMEWORK_VERSION,
)
from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.framework.normalization_pipeline import (
    NormalizationPipeline,
)
from requirement_intelligence.normalization.framework.normalization_registry import (
    NormalizationRegistry,
)
from requirement_intelligence.normalization.models.normalization_configuration import (
    NormalizationConfiguration,
)
from requirement_intelligence.normalization.response import ResponseNormalizer
from requirement_intelligence.validation.models import (
    DEFAULT_VALIDATION_CONTRACT_VERSION,
    FRAMEWORK_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    ValidationConfiguration,
    ValidationFrameworkMetadata,
    ValidationHealth,
    ValidationResult,
    ValidationStatistics,
    ValidationSummary,
)
from requirement_intelligence.validation.models import (
    ValidationVerdict as ValidationSubsystemVerdict,
)
from shared.enums.base import ValidationVerdict as CP1Verdict

_TS = datetime(2026, 7, 12, 12, 0, 0, tzinfo=UTC)
_TS_END = datetime(2026, 7, 12, 12, 0, 1, tzinfo=UTC)

ANALYSIS_ID = "AN-1"
EXECUTION_ID = "EX-1"


def make_grounding_result(
    *,
    grounding_score: int = 90,
    hallucination_rate: float = 0.0,
    average_confidence: float = 85.0,
    evidence_coverage: float = 0.9,
    analysis_id: str = ANALYSIS_ID,
    execution_id: str = EXECUTION_ID,
) -> GroundingResult:
    """A grounding result exposing exactly the metrics the evaluator reads."""
    metrics = GroundingMetrics(
        total_requirements=0,
        grounded_requirements=0,
        unsupported_requirements=0,
        grounding_coverage=1.0,
        evidence_coverage=evidence_coverage,
        requirement_coverage=1.0,
        evidence_utilization=1.0,
        traceability_completeness=1.0,
        average_confidence=average_confidence,
        cross_source_support=0.0,
        single_source_support=0.0,
        unsupported_rate=0.0,
        hallucination_rate=hallucination_rate,
        average_evidence_per_requirement=0.0,
        average_sources_per_requirement=0.0,
        evidence_reuse_ratio=0.0,
        grounding_score=grounding_score,
    )
    summary = GroundingSummary(
        total_requirements=0,
        supported=0,
        partially_supported=0,
        unsupported=0,
        grounding_score=grounding_score,
        verdict="synthetic run",
    )
    assessment = GroundingAssessment(
        assessment_id=GroundingAssessmentId.for_run("ctx-1", "c"),
        context_id="ctx-1",
        grounded_requirements=(),
        findings=(),
        metrics=metrics,
        summary=summary,
        framework_version=GROUNDING_FRAMEWORK_VERSION,
        configuration_version=GROUNDING_CONFIGURATION_VERSION,
    )
    return GroundingResult(
        analysis_id=analysis_id,
        execution_id=execution_id,
        assessment=assessment,
        framework_version=GROUNDING_FRAMEWORK_VERSION,
        configuration_version=GROUNDING_CONFIGURATION_VERSION,
        started_at=_TS,
        completed_at=_TS_END,
    )


def _analysis_result(
    execution_id: str = EXECUTION_ID, analysis_id: str = ANALYSIS_ID
) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=analysis_id,
        execution_id=execution_id,
        source_consolidated_id="C-1",
        prompt_version="1.0",
        reasoning_contract_version="1.0",
        provider="gemini",
        model="model",
        started_at=_TS,
        completed_at=_TS,
        duration_ms=1.0,
        llm_response=LLMResponse(provider="gemini", model="model", generated_text="x"),
    )


def _normalization_result(analysis: AnalysisResult):  # type: ignore[no-untyped-def]
    registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        registry, NormalizationPipeline(registry), NormalizationConfiguration()
    )
    return normalizer.normalize(analysis.llm_response)


def make_validation_result(
    *,
    verdict: ValidationSubsystemVerdict = ValidationSubsystemVerdict.PASSED,
    critical: int = 0,
    error: int = 0,
    warning: int = 0,
    info: int = 0,
    analysis_id: str = ANALYSIS_ID,
    execution_id: str = EXECUTION_ID,
) -> ValidationResult:
    """A validation result exposing exactly the verdict and severity counts the evaluator reads."""
    total = critical + error + warning + info
    health = ValidationHealth.HEALTHY
    if critical:
        health = ValidationHealth.CRITICAL
    elif error:
        health = ValidationHealth.DEGRADED
    elif warning:
        health = ValidationHealth.WARNING
    summary = ValidationSummary(
        total_issues=total,
        info_count=info,
        warning_count=warning,
        error_count=error,
        critical_count=critical,
        blocking_issue_count=critical + error,
        overall_health=health,
    )
    statistics = ValidationStatistics(
        validation_duration_ms=1.0,
        rules_executed=1,
        rules_passed=1,
        rules_failed=0,
        started_at=_TS,
        completed_at=_TS,
        validator_version=FRAMEWORK_VERSION,
        validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
        execution_id=execution_id,
    )
    framework_metadata = ValidationFrameworkMetadata(
        framework_version=FRAMEWORK_VERSION,
        validation_contract_version=DEFAULT_VALIDATION_CONTRACT_VERSION,
        pipeline_version=PIPELINE_VERSION,
        registry_version=REGISTRY_VERSION,
    )
    return ValidationResult(
        validation_id="VAL-1",
        execution_id=execution_id,
        analysis_id=analysis_id,
        analysis_result=_analysis_result(execution_id, analysis_id),
        validation_summary=summary,
        validation_statistics=statistics,
        validation_configuration=ValidationConfiguration(),
        validation_framework_metadata=framework_metadata,
        overall_verdict=verdict,
        started_at=_TS,
        completed_at=_TS,
    )


def _cp1_finding(finding_id: str, verdict: CP1Verdict) -> CP1Finding:
    return CP1Finding(
        finding_id=finding_id,
        criterion_id="CP1-0001",
        criterion_version="1.0",
        verdict_contribution=verdict,
        message="finding",
        location="functionalRequirements[0]",
        recommendation="fix",
        correlation_id=EXECUTION_ID,
        created_at=_TS,
    )


def make_cp1_result(
    *,
    verdict: CP1Verdict = CP1Verdict.PASS,
    blocking_findings: int = 0,
    warn_findings: int = 0,
    analysis_id: str = ANALYSIS_ID,
    execution_id: str = EXECUTION_ID,
) -> CP1Result:
    """A CP1 result exposing exactly the verdict and finding counts the evaluator reads."""
    analysis = _analysis_result(execution_id, analysis_id)
    cp1_input = CP1Input(
        validation_result=make_validation_result(
            analysis_id=analysis_id, execution_id=execution_id
        ),
        normalization_result=_normalization_result(analysis),
    )
    findings = tuple(
        _cp1_finding(f"CP1F-B{i}", CP1Verdict.FAIL) for i in range(blocking_findings)
    ) + tuple(_cp1_finding(f"CP1F-W{i}", CP1Verdict.WARN) for i in range(warn_findings))
    return CP1Result(
        cp1_id="CP1-RUN-1",
        validation_id="VAL-1",
        execution_id=execution_id,
        analysis_id=analysis_id,
        cp1_input=cp1_input,
        findings=findings,
        framework_metadata=CP1FrameworkMetadata(
            framework_version="1.0.0",
            criteria_contract_version="1.0",
            pipeline_version="1.0.0",
            registry_version="1.0.0",
        ),
        overall_verdict=verdict,
        started_at=_TS,
        completed_at=_TS_END,
    )
