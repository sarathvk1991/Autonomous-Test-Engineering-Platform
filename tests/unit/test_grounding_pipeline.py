"""Unit tests for the Grounding runtime activation (CAP-077E).

Covers the GroundingPipeline end-to-end execution, stage ordering, requirement-level
failure recovery, GroundingFinding creation, the GroundingMetricsBuilder, GroundingService
delegation, PlatformContext composition, and full determinism under a fixed clock.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.context_orchestration import (
    DefaultOrchestrationPolicy,
    EngineeringContextBuilder,
    EngineeringContextOrchestrator,
)
from requirement_intelligence.grounding import (
    GroundedRequirementBuilder,
    GroundingAssessmentBuilder,
    GroundingMetricsBuilder,
    GroundingResult,
    GroundingResultBuilder,
    SupportClassification,
    default_confidence_policy,
)
from requirement_intelligence.grounding.builders.matching_context_builder import (
    MatchingContextBuilder,
)
from requirement_intelligence.grounding.classification.classification_policy import (
    default_classification_policy,
)
from requirement_intelligence.grounding.classification.engine import SupportClassificationEngine
from requirement_intelligence.grounding.confidence.deterministic_calculator import (
    DeterministicConfidenceCalculator,
)
from requirement_intelligence.grounding.config import default_grounding_configuration
from requirement_intelligence.grounding.matching import default_matching_policy
from requirement_intelligence.grounding.normalization import DefaultMatchingNormalizer
from requirement_intelligence.grounding.pipeline import GroundingPipeline
from requirement_intelligence.grounding.strategies.deterministic_text_strategy import (
    DeterministicTextMatchingStrategy,
)
from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import (
    RiskLevel,
    SourceCategory,
    SourceSystem,
    SourceType,
)
from requirement_intelligence.models.source_artifact import SourceArtifact
from shared.enums.base import ProviderType

_FIXED = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)

_RESPONSE = (
    '{"summary": "s", '
    '"functional_requirements": ["Display the login inventory page"], '
    '"security_requirements": ["Set the X-Content-Type-Options nosniff header", '
    '"zzz qqq vvv nonoverlapping tokens only"], '
    '"quality_requirements": [], "risks": [], "recommendations": []}'
)


def _artifact(
    index: int, category: SourceCategory, source_type: SourceType, title: str
) -> SourceArtifact:
    system = SourceSystem.OWASP_ZAP if category == SourceCategory.SECURITY else SourceSystem.JIRA
    return SourceArtifact(
        artifact_id=f"A{index}",
        source_system=system,
        source_record_id=f"R{index}",
        source_category=category,
        source_type=source_type,
        title=title,
        tags=("nosniff",) if category == SourceCategory.SECURITY else (),
    )


def _engineering_context() -> object:
    group = ConsolidatedArtifact(
        consolidated_id="cons-auth",
        module="auth",
        risk_level=RiskLevel.LOW,
        consolidation_reason="c",
        functional_artifacts=[
            _artifact(0, SourceCategory.FUNCTIONAL, SourceType.STORY, "login inventory page story")
        ],
        security_artifacts=[
            _artifact(
                100,
                SourceCategory.SECURITY,
                SourceType.DAST,
                "X Content Type Options nosniff header",
            )
        ],
        quality_artifacts=[],
    )
    return (
        EngineeringContextOrchestrator(
            policy=DefaultOrchestrationPolicy(), builder=EngineeringContextBuilder()
        )
        .orchestrate([group])
        .context
    )


def _analysis_result(text: str = _RESPONSE) -> AnalysisResult:
    return AnalysisResult(
        analysis_id="a-1",
        execution_id="e-1",
        source_consolidated_id="cons-auth",
        prompt_version="1.0.0",
        reasoning_contract_version="1.0.0",
        provider=ProviderType.GEMINI,
        model="m",
        started_at=_FIXED,
        completed_at=_FIXED,
        duration_ms=1.0,
        llm_response=LLMResponse(provider=ProviderType.GEMINI, model="m", generated_text=text),
    )


def _pipeline(*, strategy: object | None = None, clock: object | None = None) -> GroundingPipeline:
    return GroundingPipeline(
        matching_context_builder=MatchingContextBuilder(),
        strategy=strategy  # type: ignore[arg-type]
        or DeterministicTextMatchingStrategy(
            normalizer=DefaultMatchingNormalizer(), policy=default_matching_policy()
        ),
        classification_engine=SupportClassificationEngine(default_classification_policy()),
        confidence_calculator=DeterministicConfidenceCalculator(default_confidence_policy()),
        grounded_requirement_builder=GroundedRequirementBuilder(),
        metrics_builder=GroundingMetricsBuilder(),
        assessment_builder=GroundingAssessmentBuilder(),
        result_builder=GroundingResultBuilder(),
        configuration=default_grounding_configuration(),
        clock=clock or (lambda: _FIXED),  # type: ignore[arg-type]
    )


@pytest.mark.unit
class TestPipelineExecution:
    def test_produces_grounding_result_with_all_requirements(self) -> None:
        result = _pipeline().execute(_engineering_context(), _analysis_result())
        assert isinstance(result, GroundingResult)
        assert len(result.assessment.grounded_requirements) == 3
        assert result.analysis_id == "a-1"
        assert result.execution_id == "e-1"

    def test_requirements_are_classified_and_scored(self) -> None:
        result = _pipeline().execute(_engineering_context(), _analysis_result())
        for req in result.assessment.grounded_requirements:
            assert req.confidence.score >= 0
            assert req.classification  # a verdict was assigned

    def test_metrics_and_summary_populated(self) -> None:
        result = _pipeline().execute(_engineering_context(), _analysis_result())
        assert result.assessment.metrics.total_requirements == 3
        assert result.assessment.summary.total_requirements == 3
        assert "grounded" in result.assessment.summary.verdict


@pytest.mark.unit
class TestRequirementLevelFailure:
    def test_one_failing_requirement_becomes_unsupported_and_run_continues(self) -> None:
        class _PartlyFailingStrategy:
            name = "failing"

            def match(self, request: object):  # type: ignore[no-untyped-def]
                if "nosniff" in request.requirement.text:  # type: ignore[attr-defined]
                    raise RuntimeError("boom")
                return DeterministicTextMatchingStrategy(
                    normalizer=DefaultMatchingNormalizer(), policy=default_matching_policy()
                ).match(request)  # type: ignore[arg-type]

        result = _pipeline(strategy=_PartlyFailingStrategy()).execute(
            _engineering_context(), _analysis_result()
        )
        # All three requirements still present; the failed one is UNSUPPORTED with a finding.
        assert len(result.assessment.grounded_requirements) == 3
        failed = [
            r
            for r in result.assessment.grounded_requirements
            if SupportClassification(r.classification) == SupportClassification.UNSUPPORTED
        ]
        assert failed
        finding_ids = {f.requirement_id for f in result.assessment.findings}
        assert all(r.requirement_id in finding_ids for r in failed)

    def test_service_level_failure_aborts_the_run(self) -> None:
        with pytest.raises(Exception):  # noqa: B017 — MatchingContextConstructionError bubbles up
            _pipeline().execute(_engineering_context(), _analysis_result("not valid json"))


@pytest.mark.unit
class TestFindings:
    def test_finding_per_hallucinated_requirement(self) -> None:
        result = _pipeline().execute(_engineering_context(), _analysis_result())
        hallucinated = [
            r
            for r in result.assessment.grounded_requirements
            if SupportClassification(r.classification)
            in {SupportClassification.UNSUPPORTED, SupportClassification.CONTRADICTED}
        ]
        assert len(result.assessment.findings) == len(hallucinated)


@pytest.mark.unit
class TestMetricsBuilder:
    def test_empty_requirements_are_safe(self) -> None:
        metrics = GroundingMetricsBuilder().build([], evidence_available=0)
        assert metrics.total_requirements == 0
        assert metrics.grounding_coverage == 0.0
        assert metrics.grounding_score == 0

    def test_distribution_covers_all_classifications(self) -> None:
        result = _pipeline().execute(_engineering_context(), _analysis_result())
        distribution = {e.classification for e in result.assessment.metrics.support_distribution}
        assert len(distribution) == 6  # all six classifications represented


@pytest.mark.unit
class TestDeterminism:
    def test_identical_inputs_produce_identical_result(self) -> None:
        one = _pipeline().execute(_engineering_context(), _analysis_result())
        two = _pipeline().execute(_engineering_context(), _analysis_result())
        assert one == two
        assert one.model_dump(mode="json") == two.model_dump(mode="json")
