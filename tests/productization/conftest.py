"""Shared fixtures for CAP-070 productization tests.

Provides:
* ``golden_stub_provider``  — a deterministic, in-process LLM provider stub
  that returns the golden response without any network I/O.
* ``golden_pipeline_result``  — executes the complete pipeline once and returns
  a :class:`PipelineResult` bundle that every test in this package can inspect.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from requirement_intelligence.analysis.analysis_configuration import AnalysisConfiguration
from requirement_intelligence.cp1.response import CP1Service, build_cp1_service
from requirement_intelligence.cp1.response.cp1_handoff import ValidationToCP1Handoff
from requirement_intelligence.execution.execution_data import ExecutionData
from requirement_intelligence.execution.execution_writer import ExecutionWriter, ExecutionWriteResult
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
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
from requirement_intelligence.prompts.requirement_prompt_builder import RequirementPromptBuilder
from requirement_intelligence.consolidation.consolidation_engine import ConsolidationEngine
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.analysis.requirement_analysis_service import (
    RequirementAnalysisService,
)
from requirement_intelligence.validation import ValidationInput
from requirement_intelligence.validation.models.validation_result import ValidationResult
from requirement_intelligence.cp1.models.cp1_result import CP1Result
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

    def validate_connection(self) -> bool:  # noqa: D102
        return True

    def generate(self, request: LLMRequest) -> LLMResponse:  # noqa: D102
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
    selected: ConsolidatedArtifact

    # Analysis
    analysis_result: Any  # AnalysisResult

    # Normalization
    normalization_result: NormalizationResult

    # Validation
    validation_result: ValidationResult

    # CP1
    cp1_result: CP1Result | None

    # Execution package
    execution_data: ExecutionData
    write_result: ExecutionWriteResult
    output_dir: Path


# ---------------------------------------------------------------------------
# Pipeline executor helper
# ---------------------------------------------------------------------------


def _run_golden_pipeline(tmp_dir: Path) -> PipelineResult:
    """Execute the complete pipeline with the golden dataset and stub provider.

    This function orchestrates every subsystem in the governed pipeline order:

        SourceArtifacts
            → ConsolidationEngine
            → RequirementAnalysisService (stub provider)
            → ResponseNormalizer
            → ValidationInput binding (handoff seam)
            → ResponseValidator
            → ValidationToCP1Handoff (gate)
            → CP1Service
            → ExecutionWriter

    No external I/O is performed.  The output directory is ``tmp_dir``.
    """
    context = PlatformContext()

    # -----------------------------------------------------------------------
    # Step 1 — Consolidation
    # -----------------------------------------------------------------------
    engine = ConsolidationEngine()
    consolidated = engine.consolidate(GOLDEN_SOURCE_ARTIFACTS)

    # Select deterministically (most artifacts first, then by id).
    def _key(c: ConsolidatedArtifact) -> tuple[int, str]:
        total = (
            len(c.functional_artifacts)
            + len(c.security_artifacts)
            + len(c.quality_artifacts)
        )
        return (-total, c.consolidated_id)

    selected = sorted(consolidated, key=_key)[0]

    # -----------------------------------------------------------------------
    # Step 2 — Prompt building + Analysis (stub provider)
    # -----------------------------------------------------------------------
    prompt_builder = RequirementPromptBuilder()
    stub_provider = GoldenStubProvider()

    service = RequirementAnalysisService(
        prompt_builder=prompt_builder,
        provider=stub_provider,
        configuration=AnalysisConfiguration(
            reasoning_contract_version=meta.REASONING_CONTRACT_VERSION,
        ),
    )
    analysis_result = service.analyze(selected)
    prompt_request = prompt_builder.build(selected)
    llm_request = prompt_request.to_llm_request(request_id=analysis_result.execution_id)

    # -----------------------------------------------------------------------
    # Step 3 — Normalization
    # -----------------------------------------------------------------------
    norm_registry = NormalizationRegistry()
    normalizer = ResponseNormalizer(
        norm_registry,
        NormalizationPipeline(norm_registry),
        NormalizationConfiguration(),
    )
    normalization_result = normalizer.normalize(analysis_result.llm_response)

    # -----------------------------------------------------------------------
    # Step 4 — Validation
    # -----------------------------------------------------------------------
    validation_profile = context.get_validation_profile()  # default = STANDARD
    validation_input = ValidationInput(
        analysis_result=analysis_result,
        normalization_result=normalization_result,
    )
    validator = context.create_response_validator_for_profile(validation_profile)
    validation_result = validator.validate(validation_input)

    # -----------------------------------------------------------------------
    # Step 5 — Validation → CP1 handoff
    # -----------------------------------------------------------------------
    handoff = context.create_validation_to_cp1_handoff()
    cp1_input = handoff.hand_off(validation_result, normalization_result)
    cp1_result: CP1Result | None = None
    if cp1_input is not None:
        cp1_result = context.cp1_service.run(cp1_input)

    # -----------------------------------------------------------------------
    # Step 6 — Execution package
    # -----------------------------------------------------------------------
    execution_data = ExecutionData(
        selected=selected,
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
    )

    tmp_dir.mkdir(parents=True, exist_ok=True)
    write_result = ExecutionWriter().write(tmp_dir, execution_data)

    return PipelineResult(
        source_artifact_count=len(GOLDEN_SOURCE_ARTIFACTS),
        consolidated_artifacts=consolidated,
        selected=selected,
        analysis_result=analysis_result,
        normalization_result=normalization_result,
        validation_result=validation_result,
        cp1_result=cp1_result,
        execution_data=execution_data,
        write_result=write_result,
        output_dir=tmp_dir,
    )


# ---------------------------------------------------------------------------
# pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def golden_pipeline_result(tmp_path_factory: pytest.TempPathFactory) -> PipelineResult:
    """Execute the golden pipeline once per module and cache the result.

    Scope is ``module`` so the pipeline runs once for the entire test module
    (determinism tests run it a second time themselves using ``tmp_path``).
    """
    tmp_dir = tmp_path_factory.mktemp("golden_baseline_run1")
    return _run_golden_pipeline(tmp_dir)


@pytest.fixture()
def golden_stub_provider() -> GoldenStubProvider:
    """Return a fresh golden stub provider."""
    return GoldenStubProvider()
