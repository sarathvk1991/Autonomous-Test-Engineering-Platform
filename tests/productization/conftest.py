"""Shared fixtures for CAP-070 productization tests.

Provides:
* ``golden_stub_provider``  — a deterministic, in-process LLM provider stub
  that returns the golden response without any network I/O.
* ``golden_pipeline_result``  — executes the complete pipeline once under the
  **active** orchestration policy and returns a :class:`PipelineResult` bundle
  that every test in this package can inspect.
* ``legacy_pipeline_result``  — the same pipeline under ``LegacySelectionPolicy``.
  The control arm: comparing the two isolates a behaviour change to the policy
  that caused it rather than to the code that executes it (CAP-076D Stage 11).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from requirement_intelligence.analysis.analysis_configuration import AnalysisConfiguration
from requirement_intelligence.analysis.requirement_analysis_service import (
    RequirementAnalysisService,
)
from requirement_intelligence.consolidation.consolidation_engine import ConsolidationEngine
from requirement_intelligence.context_orchestration import (
    EngineeringContext,
    LegacySelectionPolicy,
    OrchestrationPolicy,
)
from requirement_intelligence.continuous_improvement.models import (
    HistoricalDatasetReference,
)
from requirement_intelligence.cp1.models.cp1_result import CP1Result
from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.execution.execution_writer import (
    ExecutionWriter,
    ExecutionWriteResult,
)
from requirement_intelligence.knowledge_graph.models import (
    HistoricalDatasetReference as KnowledgeGraphHistoricalDatasetReference,
)
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.normalization.framework.normalization_pipeline import (
    NormalizationPipeline,
)
from requirement_intelligence.normalization.framework.normalization_registry import (
    NormalizationRegistry,
)
from requirement_intelligence.normalization.models.normalization_configuration import (
    NormalizationConfiguration,
)
from requirement_intelligence.normalization.models.normalization_result import NormalizationResult
from requirement_intelligence.normalization.response import ResponseNormalizer
from requirement_intelligence.platform import platform_metadata as meta
from requirement_intelligence.platform.platform_context import PlatformContext
from requirement_intelligence.validation import ValidationInput
from requirement_intelligence.validation.models.validation_result import ValidationResult
from shared.enums.base import ExecutionStatus, ProviderType
from tests.productization.fixtures.golden_dataset import (
    GOLDEN_LLM_RESPONSE_TEXT,
    GOLDEN_SOURCE_ARTIFACTS,
)

# ---------------------------------------------------------------------------
# Deterministic stub LLM provider
# ---------------------------------------------------------------------------

_GOLDEN_PROVIDER_NAME = "golden-stub"
_GOLDEN_MODEL = "golden-stub-model-1.0"


class GoldenStubProvider(LLMProvider):
    """Deterministic in-process LLM provider for CAP-070 golden baseline.

    Returns the fixed golden response for every ``generate`` call. Makes no
    network calls, reads no environment variables, and has no dependencies on
    external services.
    """

    @property
    def provider_name(self) -> str:
        return _GOLDEN_PROVIDER_NAME

    def validate_connection(self) -> bool:
        return True

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            provider=ProviderType.GEMINI,  # use existing enum; stub, not live
            model=_GOLDEN_MODEL,
            generated_text=GOLDEN_LLM_RESPONSE_TEXT,
            finish_reason="STOP",
            execution_status=ExecutionStatus.COMPLETED,
            latency_ms=1.0,
            usage=LLMUsage(
                prompt_tokens=512,
                completion_tokens=256,
                total_tokens=768,
            ),
        )


# ---------------------------------------------------------------------------
# Pipeline result bundle
# ---------------------------------------------------------------------------


@dataclass
class PipelineResult:
    """All artifacts produced by one complete pipeline run.

    Collects every subsystem output so tests can inspect any layer without
    re-running the pipeline.  Provenance fields (IDs, timestamps) are per-run
    and deliberately excluded from determinism comparisons.
    """

    # Engineering pipeline
    source_artifact_count: int
    consolidated_artifacts: list[ConsolidatedArtifact]
    #: The primary (highest-ranked) contributing group, persisted verbatim.
    selected: ConsolidatedArtifact

    # Engineering Context Orchestration
    engineering_context: EngineeringContext

    # Analysis
    analysis_result: Any  # AnalysisResult

    # Requirement Enhancement (strictly downstream of Analysis, upstream of Grounding)
    requirement_enhancement_result: Any  # RequirementEnhancementResult

    # Normalization
    normalization_result: NormalizationResult

    # Validation
    validation_result: ValidationResult

    # CP1
    cp1_result: CP1Result | None

    # Grounding
    grounding_result: Any  # GroundingResult

    # Quality Governance (terminal release authority)
    quality_governance_result: Any  # QualityGovernanceResult

    # Recommendation (peer capability, immediately after Quality Governance)
    recommendation_result: Any  # RecommendationResult

    # Continuous Improvement (Layer 2's first capability, immediately after
    # Recommendation)
    continuous_improvement_result: Any  # ContinuousImprovementResult

    # Knowledge Graph (Layer 2's second capability, immediately after
    # Continuous Improvement)
    knowledge_graph_result: Any  # KnowledgeGraphResult

    # Execution package
    execution_data: ExecutionData
    write_result: ExecutionWriteResult
    output_dir: Path


# ---------------------------------------------------------------------------
# Pipeline executor helper
# ---------------------------------------------------------------------------


def _run_golden_pipeline(
    tmp_dir: Path, policy: OrchestrationPolicy | None = None
) -> PipelineResult:
    """Execute the complete pipeline with the golden dataset and stub provider.

    This function orchestrates every subsystem in the governed pipeline order:

        SourceArtifacts
            → ConsolidationEngine
            → EngineeringContextOrchestrator (the active policy, unless overridden)
            → RequirementAnalysisService (stub provider)
            → ResponseNormalizer
            → ValidationInput binding (handoff seam)
            → ResponseValidator
            → ValidationToCP1Handoff (gate)
            → CP1Service
            → ExecutionWriter

    *policy* is passed through to ``PlatformContext`` so the baseline can be run
    under a governed policy other than the active one. It defaults to ``None``,
    which binds whatever the runtime binds — the baseline must never pin a policy
    the runtime does not execute.

    No external I/O is performed.  The output directory is ``tmp_dir``.
    """
    context = PlatformContext()

    # -----------------------------------------------------------------------
    # Step 1 — Consolidation
    # -----------------------------------------------------------------------
    engine = ConsolidationEngine()
    consolidated = engine.consolidate(GOLDEN_SOURCE_ARTIFACTS)

    # -----------------------------------------------------------------------
    # Step 2 — Engineering Context Orchestration (CAP-076C; multi-source CAP-076D)
    # -----------------------------------------------------------------------
    # Selection is the governed policy's decision, not this harness's. The golden
    # dataset consolidates to a single group carrying all three domains, so the
    # policies agree on *which* evidence reaches the prompt and differ only in the
    # order they present it. That is deliberate: the dataset isolates the ordering
    # rule, and the multi-group behaviour is proven where it belongs, over
    # candidate sets that actually have several groups.
    orchestration = context.create_engineering_context_orchestrator(policy).orchestrate(
        consolidated
    )
    engineering_context = orchestration.context
    selected = orchestration.primary_group

    # -----------------------------------------------------------------------
    # Step 3 — Prompt building + Analysis (stub provider)
    # -----------------------------------------------------------------------
    prompt_builder = context.create_prompt_builder()
    stub_provider = GoldenStubProvider()

    service = RequirementAnalysisService(
        prompt_builder=prompt_builder,
        provider=stub_provider,
        configuration=AnalysisConfiguration(
            reasoning_contract_version=meta.REASONING_CONTRACT_VERSION,
        ),
    )
    analysis_result = service.analyze(engineering_context)
    prompt_request = prompt_builder.build(engineering_context)
    llm_request = prompt_request.to_llm_request(request_id=analysis_result.execution_id)

    # -----------------------------------------------------------------------
    # Step 3b — Requirement Enhancement (CAP-081C): strictly downstream of Analysis,
    # upstream of Grounding. Consumes only EngineeringContext + AnalysisResult.
    # -----------------------------------------------------------------------
    requirement_enhancement_result = context.create_requirement_enhancement_service().enhance(
        engineering_context, analysis_result
    )

    # -----------------------------------------------------------------------
    # Step 4 — Normalization
    # -----------------------------------------------------------------------
    norm_registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        norm_registry,
        NormalizationPipeline(norm_registry),
        NormalizationConfiguration(),
    )
    normalization_result = normalizer.normalize(analysis_result.llm_response)

    # -----------------------------------------------------------------------
    # Step 5 — Validation
    # -----------------------------------------------------------------------
    validation_profile = context.get_validation_profile()  # default = STANDARD
    validation_input = ValidationInput(
        analysis_result=analysis_result,
        normalization_result=normalization_result,
    )
    validator = context.create_response_validator_for_profile(validation_profile)
    validation_result = validator.validate(validation_input)

    # -----------------------------------------------------------------------
    # Step 6 — Validation → CP1 handoff
    # -----------------------------------------------------------------------
    handoff = context.create_validation_to_cp1_handoff()
    cp1_input = handoff.hand_off(validation_result, normalization_result)
    cp1_result: CP1Result | None = None
    if cp1_input is not None:
        cp1_result = context.cp1_service.run(cp1_input)

    # -----------------------------------------------------------------------
    # Step 6b — Grounding (CAP-077F.2): strictly downstream of Analysis.
    # -----------------------------------------------------------------------
    grounding_result = context.create_grounding_service().assess(
        engineering_context, analysis_result
    )

    # -----------------------------------------------------------------------
    # Step 6c — Quality Governance (CAP-080D): the terminal release authority, run
    # immediately after CP1 on the three completed peer results. It consumes only
    # GroundingResult + ValidationResult + CP1Result and modifies nothing upstream. Its
    # QualityDecision is the canonical release verdict the execution package records.
    # -----------------------------------------------------------------------
    quality_governance_result = None
    if cp1_result is not None:
        quality_governance_result = context.create_quality_governance_service().evaluate(
            grounding_result, validation_result, cp1_result
        )

    # -----------------------------------------------------------------------
    # Step 6d — Recommendation (CAP-082C): immediately after Quality Governance, at
    # the permanently frozen end of the pipeline. It consumes only the five
    # completed peer results and runs exactly when all five exist. It modifies
    # nothing upstream.
    # -----------------------------------------------------------------------
    recommendation_result = None
    if quality_governance_result is not None:
        recommendation_result = context.create_recommendation_service().recommend(
            requirement_enhancement_result,
            grounding_result,
            validation_result,
            cp1_result,
            quality_governance_result,
        )

    # -----------------------------------------------------------------------
    # Step 6e — Continuous Improvement (CAP-083C): Layer 2's first capability,
    # immediately after Recommendation, at the permanently frozen end of the
    # pipeline. It consumes only a HistoricalDatasetReference — never any Layer 1
    # peer result (Recommendation 1, ADR-0022). No real, multi-execution Historical
    # Dataset implementation exists yet (ADR-0021 §Stage 6), so this mints the
    # minimal, deterministic reference a Historical Dataset of exactly this one
    # execution would produce — never the wall clock, so the reference stays
    # reproducible across runs.
    # -----------------------------------------------------------------------
    historical_dataset = HistoricalDatasetReference(
        dataset_id=f"single-execution:{analysis_result.execution_id}",
        dataset_version="1.0.0",
        first_execution_id=analysis_result.execution_id,
        last_execution_id=analysis_result.execution_id,
        execution_count=1,
        history_window=1,
        generated_at=analysis_result.completed_at,
    )
    continuous_improvement_result = context.create_continuous_improvement_service().improve(
        historical_dataset
    )

    # -----------------------------------------------------------------------
    # Step 6f — Knowledge Graph (CAP-084C): Layer 2's second capability,
    # immediately after Continuous Improvement, at the permanently frozen end of
    # the pipeline. It consumes only a HistoricalDatasetReference — never any
    # Layer 1 peer result, and never ContinuousImprovementResult (Recommendation
    # 1/9, ADR-0023). Reuses the exact CAP-083C single-execution minting
    # strategy, just against the deliberately duplicated
    # knowledge_graph.models.HistoricalDatasetReference type.
    # -----------------------------------------------------------------------
    kg_historical_dataset = KnowledgeGraphHistoricalDatasetReference(
        dataset_id=f"single-execution:{analysis_result.execution_id}",
        dataset_version="1.0.0",
        first_execution_id=analysis_result.execution_id,
        last_execution_id=analysis_result.execution_id,
        execution_count=1,
        history_window=1,
        generated_at=analysis_result.completed_at,
    )
    knowledge_graph_result = context.create_knowledge_graph_service().build(
        kg_historical_dataset
    )

    # -----------------------------------------------------------------------
    # Step 7 — Execution package
    # -----------------------------------------------------------------------
    execution_data = ExecutionData(
        selected=selected,
        engineering_context=engineering_context,
        prompt_request=prompt_request,
        llm_request=llm_request,
        result=analysis_result,
        dry_run=False,
        provider_name=_GOLDEN_PROVIDER_NAME,
        requested_model=_GOLDEN_MODEL,
        reasoning_contract_version=meta.REASONING_CONTRACT_VERSION,
        execution_name="golden-baseline",
        command_line_arguments={"subcommand": "analyze", "dry_run": False},
        subcommand="analyze",
        source_artifact_count=len(GOLDEN_SOURCE_ARTIFACTS),
        consolidated_artifacts=consolidated,
        validation_result=validation_result,
        validation_profile=validation_profile,
        cp1_result=cp1_result,
        grounding_result=grounding_result,
        quality_governance_result=quality_governance_result,
        requirement_enhancement_result=requirement_enhancement_result,
        recommendation_result=recommendation_result,
        continuous_improvement_result=continuous_improvement_result,
        knowledge_graph_result=knowledge_graph_result,
    )

    tmp_dir.mkdir(parents=True, exist_ok=True)
    write_result = ExecutionWriter().write(tmp_dir, execution_data)

    return PipelineResult(
        source_artifact_count=len(GOLDEN_SOURCE_ARTIFACTS),
        consolidated_artifacts=consolidated,
        selected=selected,
        engineering_context=engineering_context,
        analysis_result=analysis_result,
        requirement_enhancement_result=requirement_enhancement_result,
        normalization_result=normalization_result,
        validation_result=validation_result,
        cp1_result=cp1_result,
        grounding_result=grounding_result,
        quality_governance_result=quality_governance_result,
        recommendation_result=recommendation_result,
        continuous_improvement_result=continuous_improvement_result,
        knowledge_graph_result=knowledge_graph_result,
        execution_data=execution_data,
        write_result=write_result,
        output_dir=tmp_dir,
    )


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def golden_pipeline_result(tmp_path_factory: pytest.TempPathFactory) -> PipelineResult:
    """Execute the golden pipeline once per module under the **active** policy.

    Scope is ``module`` so the pipeline runs once for the entire test module
    (determinism tests run it a second time themselves using ``tmp_path``).
    """
    tmp_dir = tmp_path_factory.mktemp("golden_baseline_run1")
    return _run_golden_pipeline(tmp_dir)


@pytest.fixture(scope="module")
def legacy_pipeline_result(tmp_path_factory: pytest.TempPathFactory) -> PipelineResult:
    """The same pipeline under ``LegacySelectionPolicy`` — the control arm."""
    tmp_dir = tmp_path_factory.mktemp("golden_baseline_legacy")
    return _run_golden_pipeline(tmp_dir, policy=LegacySelectionPolicy())


@pytest.fixture()
def golden_stub_provider() -> GoldenStubProvider:
    """Return a fresh golden stub provider."""
    return GoldenStubProvider()
