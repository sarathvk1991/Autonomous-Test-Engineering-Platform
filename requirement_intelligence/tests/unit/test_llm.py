"""Unit tests for the LLM provider framework.

Covers:
- Provider creation via factory (valid and invalid names)
- Azure OpenAI stub behaviour
- LLM model serialisation
- Gemini provider configuration validation
- Gemini generate() with mocked SDK calls
- ProviderRegistry configuration loading
- list_providers() completeness

No real API calls are made.  All Gemini SDK interactions are mocked.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from requirement_intelligence.llm.llm_exceptions import (
    LLMError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderGenerationError,
)
from requirement_intelligence.llm.llm_factory import create_provider, list_providers
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.provider_registry import ProviderRegistry
from requirement_intelligence.llm.providers.azure_openai_provider import AzureOpenAIProvider
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.llm.providers.gemini_provider import GeminiProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_gemini_response(
    text: str = "Test response",
    finish_reason_name: str = "STOP",
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
) -> MagicMock:
    """Build a minimal MagicMock that mimics the Gemini SDK response shape."""
    candidate = MagicMock()
    candidate.finish_reason.name = finish_reason_name

    usage = MagicMock()
    usage.prompt_token_count = prompt_tokens
    usage.candidates_token_count = completion_tokens
    usage.total_token_count = prompt_tokens + completion_tokens

    response = MagicMock()
    response.text = text
    response.candidates = [candidate]
    response.usage_metadata = usage
    return response


# ---------------------------------------------------------------------------
# 1. LLM model serialisation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_llm_request_defaults() -> None:
    req = LLMRequest(prompt="hello")
    assert req.prompt == "hello"
    assert req.temperature == 0.0
    assert req.metadata == {}


@pytest.mark.unit
def test_llm_request_custom_values() -> None:
    req = LLMRequest(prompt="test", temperature=0.7, metadata={"run_id": "abc"})
    assert req.temperature == 0.7
    assert req.metadata["run_id"] == "abc"


@pytest.mark.unit
def test_llm_request_frozen() -> None:
    req = LLMRequest(prompt="immutable")
    with pytest.raises((ValidationError, TypeError)):
        req.prompt = "mutated"  # type: ignore[misc]


@pytest.mark.unit
def test_llm_response_required_fields() -> None:
    resp = LLMResponse(
        provider="gemini",
        model="gemini-1.5-flash",
        generated_text="result",
    )
    assert resp.provider == "gemini"
    assert resp.model == "gemini-1.5-flash"
    assert resp.generated_text == "result"
    assert resp.raw_response == {}
    assert resp.finish_reason is None
    assert resp.latency_ms is None
    assert resp.usage is None


@pytest.mark.unit
def test_llm_response_with_usage() -> None:
    usage = LLMUsage(prompt_tokens=5, completion_tokens=15, total_tokens=20)
    resp = LLMResponse(
        provider="gemini",
        model="gemini-1.5-flash",
        generated_text="ok",
        usage=usage,
    )
    assert resp.usage is not None
    assert resp.usage.total_tokens == 20


@pytest.mark.unit
def test_llm_usage_partial_none() -> None:
    usage = LLMUsage(total_tokens=100)
    assert usage.prompt_tokens is None
    assert usage.completion_tokens is None
    assert usage.total_tokens == 100


@pytest.mark.unit
def test_llm_response_serializes_to_dict() -> None:
    resp = LLMResponse(
        provider="gemini",
        model="gemini-1.5-flash",
        generated_text="output",
        finish_reason="stop",
        latency_ms=123.45,
    )
    data = resp.model_dump()
    assert data["provider"] == "gemini"
    assert data["finish_reason"] == "stop"
    assert data["latency_ms"] == 123.45


# ---------------------------------------------------------------------------
# 2. Exception hierarchy
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_exception_hierarchy() -> None:
    assert issubclass(ProviderConfigurationError, LLMError)
    assert issubclass(ProviderConnectionError, LLMError)
    assert issubclass(ProviderGenerationError, LLMError)
    assert issubclass(LLMError, Exception)


@pytest.mark.unit
def test_exceptions_are_raiseable() -> None:
    with pytest.raises(ProviderConfigurationError, match="config"):
        raise ProviderConfigurationError("config error")

    with pytest.raises(ProviderConnectionError, match="conn"):
        raise ProviderConnectionError("conn error")

    with pytest.raises(ProviderGenerationError, match="gen"):
        raise ProviderGenerationError("gen error")


# ---------------------------------------------------------------------------
# 3. Factory — valid provider creation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_factory_creates_gemini_provider() -> None:
    provider = create_provider("gemini", api_key="fake-key")
    assert isinstance(provider, GeminiProvider)
    assert isinstance(provider, LLMProvider)
    assert provider.provider_name == "gemini"


@pytest.mark.unit
def test_factory_creates_azure_openai_provider() -> None:
    provider = create_provider("azure_openai")
    assert isinstance(provider, AzureOpenAIProvider)
    assert isinstance(provider, LLMProvider)
    assert provider.provider_name == "azure_openai"


@pytest.mark.unit
def test_factory_invalid_provider_raises() -> None:
    with pytest.raises(ProviderConfigurationError, match="Unknown LLM provider"):
        create_provider("bedrock")


@pytest.mark.unit
def test_factory_invalid_provider_message_includes_supported() -> None:
    with pytest.raises(ProviderConfigurationError, match="azure_openai"):
        create_provider("nonexistent_llm")


@pytest.mark.unit
def test_list_providers_returns_all_known() -> None:
    providers = list_providers()
    assert "gemini" in providers
    assert "azure_openai" in providers


# ---------------------------------------------------------------------------
# 4. Azure OpenAI stub behaviour
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_azure_stub_validate_connection_raises_not_implemented() -> None:
    provider = AzureOpenAIProvider()
    with pytest.raises(NotImplementedError, match="not yet enabled"):
        provider.validate_connection()


@pytest.mark.unit
def test_azure_stub_generate_raises_not_implemented() -> None:
    provider = AzureOpenAIProvider()
    with pytest.raises(NotImplementedError, match="not yet enabled"):
        provider.generate("test prompt")


@pytest.mark.unit
def test_azure_stub_satisfies_interface() -> None:
    """AzureOpenAIProvider must be a concrete subclass of LLMProvider."""
    provider = AzureOpenAIProvider()
    assert isinstance(provider, LLMProvider)
    assert provider.provider_name == "azure_openai"


# ---------------------------------------------------------------------------
# 5. Gemini provider — configuration validation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_gemini_missing_api_key_raises_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    provider = GeminiProvider(api_key="")
    with pytest.raises(ProviderConfigurationError, match="GEMINI_API_KEY"):
        provider.validate_connection()


@pytest.mark.unit
def test_gemini_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "env-key-123")
    provider = GeminiProvider()
    assert provider._api_key == "env-key-123"


@pytest.mark.unit
def test_gemini_reads_model_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL_NAME", "gemini-1.5-pro")
    provider = GeminiProvider(api_key="key")
    assert provider._model_name == "gemini-1.5-pro"


@pytest.mark.unit
def test_gemini_default_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_MODEL_NAME", raising=False)
    provider = GeminiProvider(api_key="key")
    assert provider._model_name == "gemini-1.5-flash"


# ---------------------------------------------------------------------------
# 6. Gemini provider — generate() with mocked SDK
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_gemini_generate_returns_llm_response() -> None:
    fake_response = _make_fake_gemini_response("Generated output")

    mock_model = MagicMock()
    mock_model.generate_content.return_value = fake_response

    provider = GeminiProvider(api_key="fake-key", model_name="gemini-1.5-flash")

    with patch(
        "requirement_intelligence.llm.providers.gemini_provider.GeminiProvider._get_client",
        return_value=mock_model,
    ):
        result = provider.generate("Hello Gemini")

    assert isinstance(result, LLMResponse)
    assert result.provider == "gemini"
    assert result.model == "gemini-1.5-flash"
    assert result.generated_text == "Generated output"
    assert result.finish_reason == "STOP"
    assert result.latency_ms is not None
    assert result.latency_ms >= 0.0


@pytest.mark.unit
def test_gemini_generate_populates_usage() -> None:
    fake_response = _make_fake_gemini_response(
        text="result",
        prompt_tokens=8,
        completion_tokens=12,
    )
    mock_model = MagicMock()
    mock_model.generate_content.return_value = fake_response

    provider = GeminiProvider(api_key="fake-key")
    with patch(
        "requirement_intelligence.llm.providers.gemini_provider.GeminiProvider._get_client",
        return_value=mock_model,
    ):
        result = provider.generate("prompt")

    assert result.usage is not None
    assert result.usage.prompt_tokens == 8
    assert result.usage.completion_tokens == 12
    assert result.usage.total_tokens == 20


@pytest.mark.unit
def test_gemini_generate_sdk_error_raises_generation_error() -> None:
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = RuntimeError("API quota exceeded")

    provider = GeminiProvider(api_key="fake-key")
    with patch(
        "requirement_intelligence.llm.providers.gemini_provider.GeminiProvider._get_client",
        return_value=mock_model,
    ):
        with pytest.raises(ProviderGenerationError, match="API quota exceeded"):
            provider.generate("prompt")


@pytest.mark.unit
def test_gemini_validate_connection_success() -> None:
    mock_model = MagicMock()

    provider = GeminiProvider(api_key="fake-key")
    with patch(
        "requirement_intelligence.llm.providers.gemini_provider.GeminiProvider._get_client",
        return_value=mock_model,
    ):
        assert provider.validate_connection() is True


@pytest.mark.unit
def test_gemini_validate_connection_client_error_raises_connection_error() -> None:
    provider = GeminiProvider(api_key="fake-key")
    with patch(
        "requirement_intelligence.llm.providers.gemini_provider.GeminiProvider._get_client",
        side_effect=RuntimeError("network unreachable"),
    ):
        with pytest.raises(ProviderConnectionError, match="network unreachable"):
            provider.validate_connection()


@pytest.mark.unit
def test_gemini_missing_api_key_generate_raises() -> None:
    provider = GeminiProvider(api_key="")
    with pytest.raises(ProviderConfigurationError):
        provider.generate("prompt")


@pytest.mark.unit
def test_gemini_sdk_import_error_raises_config_error() -> None:
    """When google-generativeai is not installed, a clear error should surface."""
    provider = GeminiProvider(api_key="fake-key")

    import builtins
    real_import = builtins.__import__

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "google.generativeai":
            raise ImportError("No module named 'google.generativeai'")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        with pytest.raises(ProviderConfigurationError, match="google-generativeai"):
            provider._get_client()


# ---------------------------------------------------------------------------
# 7. ProviderRegistry
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_registry_default_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    registry = ProviderRegistry()
    assert registry.active_provider() == "gemini"


@pytest.mark.unit
def test_registry_reads_provider_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "azure_openai")
    registry = ProviderRegistry()
    assert registry.active_provider() == "azure_openai"


@pytest.mark.unit
def test_registry_config_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "azure_openai")
    registry = ProviderRegistry(config={"active_provider": "gemini"})
    assert registry.active_provider() == "gemini"


@pytest.mark.unit
def test_registry_provider_config_returns_empty_when_absent() -> None:
    registry = ProviderRegistry()
    assert registry.provider_config("gemini") == {}


@pytest.mark.unit
def test_registry_provider_config_returns_configured_values() -> None:
    cfg = {
        "providers": {
            "gemini": {"api_key": "my-key", "model_name": "gemini-1.5-pro"},
        }
    }
    registry = ProviderRegistry(config=cfg)
    gemini_cfg = registry.provider_config("gemini")
    assert gemini_cfg["api_key"] == "my-key"
    assert gemini_cfg["model_name"] == "gemini-1.5-pro"


@pytest.mark.unit
def test_registry_list_configured_providers() -> None:
    cfg = {
        "providers": {
            "gemini": {},
            "anthropic": {},
        }
    }
    registry = ProviderRegistry(config=cfg)
    configured = registry.list_configured_providers()
    assert "gemini" in configured
    assert "anthropic" in configured


@pytest.mark.unit
def test_registry_list_configured_providers_empty_when_no_config() -> None:
    registry = ProviderRegistry()
    assert registry.list_configured_providers() == []


# ---------------------------------------------------------------------------
# 8. End-to-end: factory + registry + provider (all mocked)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_full_flow_gemini_via_registry_and_factory() -> None:
    """Simulate the typical call path: registry → factory → provider.generate()."""
    fake_response = _make_fake_gemini_response("Full flow response")
    mock_model = MagicMock()
    mock_model.generate_content.return_value = fake_response

    cfg = {
        "active_provider": "gemini",
        "providers": {"gemini": {"api_key": "test-key", "model_name": "gemini-1.5-flash"}},
    }
    registry = ProviderRegistry(config=cfg)
    name = registry.active_provider()
    provider_cfg = registry.provider_config(name)

    provider = create_provider(name, **provider_cfg)

    with patch(
        "requirement_intelligence.llm.providers.gemini_provider.GeminiProvider._get_client",
        return_value=mock_model,
    ):
        result = provider.generate("Analyse this requirement")

    assert result.generated_text == "Full flow response"
    assert result.provider == "gemini"
