"""Unit tests for the Gemini provider — thin adapter over the google-genai SDK.

The Google SDK is always mocked; no live Gemini API calls are made. The mock
mirrors the current SDK shape: ``client.models.generate_content(...)`` returning
an object exposing ``.text``, ``.candidates`` and ``.usage_metadata``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from requirement_intelligence.llm.llm_exceptions import (
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderGenerationError,
)
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.llm.providers.gemini_provider import GeminiProvider
from shared.enums.base import ProviderType

_CLIENT_PATH = (
    "requirement_intelligence.llm.providers.gemini_provider.GeminiProvider._get_client"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    prompt: str = "Analyse this requirement",
    temperature: float = 0.0,
    request_id: str = "req-001",
    metadata: dict[str, Any] | None = None,
) -> LLMRequest:
    return LLMRequest(
        request_id=request_id,
        prompt=prompt,
        temperature=temperature,
        metadata=metadata or {},
    )


def _fake_response(
    text: str = "Generated output",
    finish_reason_name: str = "STOP",
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
) -> MagicMock:
    """Build a mock that mimics a google-genai GenerateContentResponse."""
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


def _fake_client(
    response: MagicMock | None = None,
    generate_side_effect: Exception | None = None,
) -> MagicMock:
    """Build a mock google-genai client: ``client.models.generate_content``."""
    client = MagicMock()
    if generate_side_effect is not None:
        client.models.generate_content.side_effect = generate_side_effect
    else:
        client.models.generate_content.return_value = response or _fake_response()
    return client


# ---------------------------------------------------------------------------
# 1. Interface conformance & configuration loading
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_provider_conforms_to_abstraction() -> None:
    provider = GeminiProvider(api_key="fake-key")
    assert isinstance(provider, LLMProvider)
    assert provider.provider_name == "gemini"


@pytest.mark.unit
def test_default_model_is_gemini_2_5_pro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    provider = GeminiProvider(api_key="fake-key")
    assert provider._model_name == "gemini-2.5-pro"


@pytest.mark.unit
def test_custom_model_is_respected() -> None:
    provider = GeminiProvider(api_key="fake-key", model_name="gemini-2.5-flash")
    assert provider._model_name == "gemini-2.5-flash"


@pytest.mark.unit
def test_reads_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "env-key-123")
    provider = GeminiProvider()
    assert provider._api_key == "env-key-123"


@pytest.mark.unit
def test_reads_model_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    provider = GeminiProvider(api_key="fake-key")
    assert provider._model_name == "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# 2. Successful generation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_generate_returns_llm_response() -> None:
    client = _fake_client(_fake_response("Generated output"))
    provider = GeminiProvider(api_key="fake-key", model_name="gemini-2.5-pro")

    with patch(_CLIENT_PATH, return_value=client):
        result = provider.generate(_make_request("Hello Gemini"))

    assert isinstance(result, LLMResponse)
    assert result.provider == ProviderType.GEMINI
    assert result.provider == "gemini"
    assert result.generated_text == "Generated output"
    assert result.finish_reason == "STOP"
    assert result.latency_ms is not None
    assert result.latency_ms >= 0.0


@pytest.mark.unit
def test_generate_executes_exactly_one_call() -> None:
    client = _fake_client()
    provider = GeminiProvider(api_key="fake-key")
    with patch(_CLIENT_PATH, return_value=client):
        provider.generate(_make_request())
    client.models.generate_content.assert_called_once()


# ---------------------------------------------------------------------------
# 3. Request mapping
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_request_mapping_passes_model_contents_and_config() -> None:
    client = _fake_client()
    provider = GeminiProvider(api_key="fake-key", model_name="gemini-2.5-pro")

    with patch(_CLIENT_PATH, return_value=client):
        provider.generate(_make_request(prompt="full prompt text", temperature=0.0))

    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-2.5-pro"
    assert kwargs["contents"] == "full prompt text"
    assert kwargs["config"]["temperature"] == 0.0


@pytest.mark.unit
def test_temperature_propagates_into_request() -> None:
    client = _fake_client()
    provider = GeminiProvider(api_key="fake-key")

    with patch(_CLIENT_PATH, return_value=client):
        provider.generate(_make_request(temperature=0.7))

    kwargs = client.models.generate_content.call_args.kwargs
    assert kwargs["config"]["temperature"] == 0.7


# ---------------------------------------------------------------------------
# 4. Response mapping
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_response_mapping_populates_usage_and_raw_response() -> None:
    response = _fake_response(text="result", prompt_tokens=8, completion_tokens=12)
    client = _fake_client(response)
    provider = GeminiProvider(api_key="fake-key")

    with patch(_CLIENT_PATH, return_value=client):
        result = provider.generate(_make_request("prompt"))

    assert result.generated_text == "result"
    assert result.usage is not None
    assert result.usage.prompt_tokens == 8
    assert result.usage.completion_tokens == 12
    assert result.usage.total_tokens == 20
    assert result.raw_response["text"] == "result"
    assert result.raw_response["finish_reason"] == "STOP"


@pytest.mark.unit
def test_model_propagates_to_response() -> None:
    client = _fake_client()
    provider = GeminiProvider(api_key="fake-key", model_name="gemini-2.5-flash")

    with patch(_CLIENT_PATH, return_value=client):
        result = provider.generate(_make_request())

    assert result.model == "gemini-2.5-flash"


@pytest.mark.unit
def test_metadata_is_not_lost() -> None:
    client = _fake_client()
    provider = GeminiProvider(api_key="fake-key")
    metadata = {"prompt_version": "1.0.0", "source_consolidated_id": "CONS-1"}

    with patch(_CLIENT_PATH, return_value=client):
        result = provider.generate(_make_request(metadata=metadata))

    assert result.raw_response["request_metadata"] == metadata


# ---------------------------------------------------------------------------
# 5. Configuration failures
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_missing_api_key_generate_raises_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    provider = GeminiProvider(api_key="")
    with pytest.raises(ProviderConfigurationError, match="GOOGLE_API_KEY"):
        provider.generate(_make_request())


@pytest.mark.unit
def test_missing_api_key_validate_connection_raises_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    provider = GeminiProvider(api_key="")
    with pytest.raises(ProviderConfigurationError, match="GOOGLE_API_KEY"):
        provider.validate_connection()


@pytest.mark.unit
def test_sdk_not_installed_raises_configuration_error() -> None:
    """A missing google-genai package surfaces as a configuration error."""
    provider = GeminiProvider(api_key="fake-key")

    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "google":
            raise ImportError("No module named 'google'")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        with pytest.raises(ProviderConfigurationError, match="google-genai"):
            provider._get_client()


# ---------------------------------------------------------------------------
# 6. Connection validation
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_validate_connection_success() -> None:
    provider = GeminiProvider(api_key="fake-key")
    with patch(_CLIENT_PATH, return_value=MagicMock()):
        assert provider.validate_connection() is True


@pytest.mark.unit
def test_validate_connection_client_error_raises_connection_error() -> None:
    provider = GeminiProvider(api_key="fake-key")
    with patch(_CLIENT_PATH, side_effect=RuntimeError("network unreachable")):
        with pytest.raises(ProviderConnectionError, match="network unreachable"):
            provider.validate_connection()


# ---------------------------------------------------------------------------
# 7. Exception wrapping (no SDK exception crosses the boundary)
# ---------------------------------------------------------------------------

class _FakeSDKError(Exception):
    """Stand-in for a provider-specific SDK exception type."""


@pytest.mark.unit
def test_generation_failure_wrapped_as_generation_error() -> None:
    client = _fake_client(generate_side_effect=_FakeSDKError("quota exceeded"))
    provider = GeminiProvider(api_key="fake-key")

    with patch(_CLIENT_PATH, return_value=client):
        with pytest.raises(ProviderGenerationError, match="quota exceeded") as exc_info:
            provider.generate(_make_request())

    # The SDK exception type does not cross the boundary, but is preserved as cause.
    assert not isinstance(exc_info.value, _FakeSDKError)
    assert isinstance(exc_info.value.__cause__, _FakeSDKError)


@pytest.mark.unit
def test_unextractable_text_raises_generation_error() -> None:
    bad_response = MagicMock()
    type(bad_response).text = property(
        lambda _self: (_ for _ in ()).throw(ValueError("no text"))
    )
    client = _fake_client(bad_response)
    provider = GeminiProvider(api_key="fake-key")

    with patch(_CLIENT_PATH, return_value=client):
        with pytest.raises(ProviderGenerationError, match="Could not extract text"):
            provider.generate(_make_request())
