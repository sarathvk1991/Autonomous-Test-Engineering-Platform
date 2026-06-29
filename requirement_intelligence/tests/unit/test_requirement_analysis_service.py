"""Unit tests for the Requirement Analysis Service.

The service is the single orchestration boundary for AI execution. These tests
verify orchestration only — prompt building and provider execution are mocked,
so no live AI calls are made. Real ``PromptRequest`` and ``LLMResponse`` objects
are used so the genuine prompt→request bridge is exercised.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from requirement_intelligence.analysis.analysis_configuration import (
    AnalysisConfiguration,
)
from requirement_intelligence.analysis.analysis_exceptions import (
    AnalysisConfigurationError,
    AnalysisError,
    AnalysisExecutionError,
    PromptGenerationError,
    ProviderExecutionError,
)
from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.analysis.requirement_analysis_service import (
    RequirementAnalysisService,
)
from requirement_intelligence.llm.llm_exceptions import ProviderGenerationError
from requirement_intelligence.llm.llm_models import LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import RiskLevel
from requirement_intelligence.prompts.requirement_prompt_builder import (
    PromptRequest,
    RequirementPromptBuilder,
)

_REASONING_VERSION = "rc-1.0.0"
_PROMPT_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config(
    reasoning_contract_version: str = _REASONING_VERSION,
) -> AnalysisConfiguration:
    return AnalysisConfiguration(
        reasoning_contract_version=reasoning_contract_version
    )


def _consolidated(consolidated_id: str = "CONS-1") -> ConsolidatedArtifact:
    return ConsolidatedArtifact(
        consolidated_id=consolidated_id,
        module="payments",
        risk_level=RiskLevel.HIGH,
    )


def _prompt_request(consolidated_id: str = "CONS-1") -> PromptRequest:
    return PromptRequest(
        system_prompt="SYSTEM",
        user_prompt="USER",
        prompt_version=_PROMPT_VERSION,
        source_consolidated_id=consolidated_id,
    )


def _llm_response() -> LLMResponse:
    return LLMResponse(
        provider="gemini",
        model="gemini-1.5-flash",
        generated_text="raw ai answer",
        finish_reason="STOP",
        latency_ms=12.5,
        usage=LLMUsage(prompt_tokens=5, completion_tokens=7, total_tokens=12),
    )


def _make_service(
    *,
    prompt_request: PromptRequest | None = None,
    llm_response: LLMResponse | None = None,
    build_side_effect: Exception | None = None,
    generate_side_effect: Exception | None = None,
) -> tuple[RequirementAnalysisService, MagicMock, MagicMock]:
    """Build a service with mocked collaborators; return (service, builder, provider)."""
    builder = MagicMock(spec=RequirementPromptBuilder)
    provider = MagicMock(spec=LLMProvider)

    if build_side_effect is not None:
        builder.build.side_effect = build_side_effect
    else:
        builder.build.return_value = prompt_request or _prompt_request()

    if generate_side_effect is not None:
        provider.generate.side_effect = generate_side_effect
    else:
        provider.generate.return_value = llm_response or _llm_response()

    service = RequirementAnalysisService(
        prompt_builder=builder,
        provider=provider,
        configuration=_config(),
    )
    return service, builder, provider


# ---------------------------------------------------------------------------
# 1. Successful orchestration
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_analyze_returns_analysis_result() -> None:
    service, _, _ = _make_service()
    result = service.analyze(_consolidated())
    assert isinstance(result, AnalysisResult)


@pytest.mark.unit
def test_analyze_invokes_builder_and_provider_once() -> None:
    service, builder, provider = _make_service()
    artifact = _consolidated()

    service.analyze(artifact)

    builder.build.assert_called_once_with(artifact)
    provider.generate.assert_called_once()


@pytest.mark.unit
def test_analyze_passes_llm_request_with_execution_id_as_request_id() -> None:
    service, _, provider = _make_service()
    result = service.analyze(_consolidated())

    llm_request = provider.generate.call_args.args[0]
    assert llm_request.request_id == result.execution_id
    assert llm_request.prompt  # the bridged prompt is non-empty


# ---------------------------------------------------------------------------
# 2. AnalysisResult correctness
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_analysis_result_correctness() -> None:
    response = _llm_response()
    service, _, _ = _make_service(llm_response=response)

    result = service.analyze(_consolidated("CONS-XYZ"))

    assert result.source_consolidated_id == "CONS-XYZ"
    assert result.provider == "gemini"
    assert result.model == "gemini-1.5-flash"
    assert result.llm_response is response
    assert result.completed_at >= result.started_at


@pytest.mark.unit
def test_analysis_result_serializes_camelcase() -> None:
    service, _, _ = _make_service()
    result = service.analyze(_consolidated())

    data = result.model_dump(by_alias=True)
    for key in (
        "analysisId",
        "executionId",
        "sourceConsolidatedId",
        "promptVersion",
        "reasoningContractVersion",
        "startedAt",
        "completedAt",
        "durationMs",
        "llmResponse",
    ):
        assert key in data


@pytest.mark.unit
def test_analysis_result_is_immutable() -> None:
    service, _, _ = _make_service()
    result = service.analyze(_consolidated())
    with pytest.raises((TypeError, ValueError)):
        result.analysis_id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 3. UUID generation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_ids_are_uuid4_and_distinct() -> None:
    service, _, _ = _make_service()
    result = service.analyze(_consolidated())

    assert result.analysis_id != result.execution_id
    assert UUID(result.analysis_id).version == 4
    assert UUID(result.execution_id).version == 4


@pytest.mark.unit
def test_each_analysis_gets_fresh_ids() -> None:
    service, _, _ = _make_service()
    first = service.analyze(_consolidated())
    second = service.analyze(_consolidated())

    assert first.analysis_id != second.analysis_id
    assert first.execution_id != second.execution_id


# ---------------------------------------------------------------------------
# 4. Duration calculation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_duration_ms_is_non_negative_float() -> None:
    service, _, _ = _make_service()
    result = service.analyze(_consolidated())
    assert isinstance(result.duration_ms, float)
    assert result.duration_ms >= 0.0


@pytest.mark.unit
def test_duration_ms_computed_from_timestamps() -> None:
    service, _, _ = _make_service()
    start = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    end = start + timedelta(milliseconds=1500)

    with patch(
        "requirement_intelligence.analysis.requirement_analysis_service.datetime"
    ) as fake_datetime:
        fake_datetime.now.side_effect = [start, end]
        result = service.analyze(_consolidated())

    assert result.started_at == start
    assert result.completed_at == end
    assert result.duration_ms == 1500.0


# ---------------------------------------------------------------------------
# 5. Version + metadata propagation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_prompt_version_propagates() -> None:
    service, _, _ = _make_service(prompt_request=_prompt_request())
    result = service.analyze(_consolidated())
    assert result.prompt_version == _PROMPT_VERSION


@pytest.mark.unit
def test_reasoning_contract_version_propagates() -> None:
    service, _, _ = _make_service()
    result = service.analyze(_consolidated())
    assert result.reasoning_contract_version == _REASONING_VERSION


@pytest.mark.unit
def test_metadata_propagation() -> None:
    service, _, _ = _make_service(prompt_request=_prompt_request("CONS-META"))
    result = service.analyze(_consolidated("CONS-META"))
    # Framework metadata bridged through PromptRequest.to_llm_request.
    assert result.metadata["prompt_version"] == _PROMPT_VERSION
    assert result.metadata["source_consolidated_id"] == "CONS-META"


# ---------------------------------------------------------------------------
# 6. Error handling
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_prompt_builder_failure_raises_prompt_generation_error() -> None:
    service, _, provider = _make_service(build_side_effect=RuntimeError("boom"))
    with pytest.raises(PromptGenerationError, match="Prompt generation failed"):
        service.analyze(_consolidated())
    # Provider is never invoked when prompt generation fails.
    provider.generate.assert_not_called()


@pytest.mark.unit
def test_provider_failure_raises_provider_execution_error() -> None:
    service, _, _ = _make_service(
        generate_side_effect=ProviderGenerationError("quota exceeded")
    )
    with pytest.raises(ProviderExecutionError, match="Provider execution failed"):
        service.analyze(_consolidated())


@pytest.mark.unit
def test_provider_specific_exception_does_not_leak() -> None:
    service, _, _ = _make_service(
        generate_side_effect=ProviderGenerationError("internal provider detail")
    )
    with pytest.raises(ProviderExecutionError) as exc_info:
        service.analyze(_consolidated())
    # The raised error is an orchestration error, not the provider's exception.
    assert not isinstance(exc_info.value, ProviderGenerationError)
    # The original provider exception is preserved as the cause for debugging.
    assert isinstance(exc_info.value.__cause__, ProviderGenerationError)


@pytest.mark.unit
def test_all_orchestration_errors_share_base() -> None:
    assert issubclass(AnalysisConfigurationError, AnalysisError)
    assert issubclass(PromptGenerationError, AnalysisError)
    assert issubclass(ProviderExecutionError, AnalysisError)
    assert issubclass(AnalysisExecutionError, AnalysisError)


# ---------------------------------------------------------------------------
# 7. Configuration validation (constructor)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_missing_prompt_builder_raises_configuration_error() -> None:
    with pytest.raises(AnalysisConfigurationError, match="prompt builder"):
        RequirementAnalysisService(
            prompt_builder=None,  # type: ignore[arg-type]
            provider=MagicMock(spec=LLMProvider),
            configuration=_config(),
        )


@pytest.mark.unit
def test_missing_provider_raises_configuration_error() -> None:
    with pytest.raises(AnalysisConfigurationError, match="provider"):
        RequirementAnalysisService(
            prompt_builder=MagicMock(spec=RequirementPromptBuilder),
            provider=None,  # type: ignore[arg-type]
            configuration=_config(),
        )


@pytest.mark.unit
def test_missing_configuration_raises_configuration_error() -> None:
    with pytest.raises(AnalysisConfigurationError, match="configuration"):
        RequirementAnalysisService(
            prompt_builder=MagicMock(spec=RequirementPromptBuilder),
            provider=MagicMock(spec=LLMProvider),
            configuration=None,  # type: ignore[arg-type]
        )


@pytest.mark.unit
def test_configuration_reasoning_version_propagates() -> None:
    builder = MagicMock(spec=RequirementPromptBuilder)
    builder.build.return_value = _prompt_request()
    provider = MagicMock(spec=LLMProvider)
    provider.generate.return_value = _llm_response()

    service = RequirementAnalysisService(
        prompt_builder=builder,
        provider=provider,
        configuration=_config(reasoning_contract_version="rc-9.9.9"),
    )
    result = service.analyze(_consolidated())
    assert result.reasoning_contract_version == "rc-9.9.9"
