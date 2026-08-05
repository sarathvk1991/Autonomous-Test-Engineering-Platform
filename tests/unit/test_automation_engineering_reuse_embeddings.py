"""Unit tests for `GeminiEmbeddingProvider` -- a thin adapter over the
`google-genai` SDK's `embed_content`. The SDK is always mocked; no live
Gemini API call is made (this environment has no `GOOGLE_API_KEY`
configured, verified directly in the build's own investigation -- the same
stub-vs-live split ADR-0044 D5 already documents for the SonarQube adapter).

Mirrors `requirement_intelligence/tests/unit/test_gemini_provider.py`'s own
mocking pattern exactly: patch the private `_get_client` method, build a
`MagicMock` shaped like the real SDK response.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from automation_engineering.reuse.embeddings import (
    EmbeddingCallError,
    EmbeddingConfigurationError,
    EmbeddingProvider,
    GeminiEmbeddingProvider,
)

pytestmark = pytest.mark.unit

_CLIENT_PATH = "automation_engineering.reuse.embeddings.GeminiEmbeddingProvider._get_client"


def _fake_embedding_response(vectors: list[list[float]]) -> MagicMock:
    response = MagicMock()
    embeddings = []
    for vector in vectors:
        embedding = MagicMock()
        embedding.values = vector
        embeddings.append(embedding)
    response.embeddings = embeddings
    return response


def _fake_client(
    response: MagicMock | None = None, side_effect: Exception | None = None
) -> MagicMock:
    client = MagicMock()
    if side_effect is not None:
        client.models.embed_content.side_effect = side_effect
    else:
        client.models.embed_content.return_value = response or _fake_embedding_response(
            [[0.1, 0.2]]
        )
    return client


def test_provider_conforms_to_seam() -> None:
    provider: EmbeddingProvider = GeminiEmbeddingProvider(api_key="fake-key")
    assert hasattr(provider, "embed")


def test_default_model_is_gemini_embedding_001(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    provider = GeminiEmbeddingProvider(api_key="fake-key")
    assert provider._model_name == "gemini-embedding-001"


def test_reads_api_key_and_model_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "env-key")
    monkeypatch.setenv("EMBEDDING_MODEL", "custom-embedding-model")
    provider = GeminiEmbeddingProvider()
    assert provider._api_key == "env-key"
    assert provider._model_name == "custom-embedding-model"


def test_embed_returns_one_vector_per_text_same_order() -> None:
    client = _fake_client(_fake_embedding_response([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]))
    provider = GeminiEmbeddingProvider(api_key="fake-key")

    with patch(_CLIENT_PATH, return_value=client):
        result = provider.embed(["one", "two", "three"])

    assert result == ((0.1, 0.2), (0.3, 0.4), (0.5, 0.6))


def test_embed_calls_sdk_exactly_once_with_all_texts_batched() -> None:
    client = _fake_client(_fake_embedding_response([[0.1], [0.2]]))
    provider = GeminiEmbeddingProvider(api_key="fake-key", model_name="text-embedding-004")

    with patch(_CLIENT_PATH, return_value=client):
        provider.embed(["a", "b"])

    client.models.embed_content.assert_called_once()
    kwargs = client.models.embed_content.call_args.kwargs
    assert kwargs["model"] == "text-embedding-004"
    assert kwargs["contents"] == ["a", "b"]


def test_missing_api_key_raises_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    provider = GeminiEmbeddingProvider(api_key="")
    with pytest.raises(EmbeddingConfigurationError, match="GOOGLE_API_KEY"):
        provider.embed(["text"])


def test_sdk_not_installed_raises_configuration_error() -> None:
    provider = GeminiEmbeddingProvider(api_key="fake-key")

    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "google":
            raise ImportError("No module named 'google'")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        with pytest.raises(EmbeddingConfigurationError, match="google-genai"):
            provider._get_client()


class _FakeSDKError(Exception):
    """Stand-in for a provider-specific SDK exception type."""


def test_call_failure_wrapped_no_sdk_exception_crosses_boundary() -> None:
    client = _fake_client(side_effect=_FakeSDKError("quota exceeded"))
    provider = GeminiEmbeddingProvider(api_key="fake-key")

    with patch(_CLIENT_PATH, return_value=client):
        with pytest.raises(EmbeddingCallError, match="quota exceeded") as exc_info:
            provider.embed(["text"])

    assert not isinstance(exc_info.value, _FakeSDKError)
    assert isinstance(exc_info.value.__cause__, _FakeSDKError)


def test_mismatched_response_count_raises_call_error() -> None:
    client = _fake_client(_fake_embedding_response([[0.1, 0.2]]))  # only 1, for 2 inputs
    provider = GeminiEmbeddingProvider(api_key="fake-key")

    with patch(_CLIENT_PATH, return_value=client):
        with pytest.raises(EmbeddingCallError, match="expected one-to-one"):
            provider.embed(["one", "two"])


def test_unextractable_embeddings_raises_call_error() -> None:
    bad_response = MagicMock()
    type(bad_response).embeddings = property(
        lambda _self: (_ for _ in ()).throw(ValueError("no embeddings"))
    )
    client = _fake_client(bad_response)
    provider = GeminiEmbeddingProvider(api_key="fake-key")

    with patch(_CLIENT_PATH, return_value=client):
        with pytest.raises(EmbeddingCallError, match="Could not extract"):
            provider.embed(["text"])


class _FakeRateLimitError(Exception):
    """Stand-in for `google.genai.errors.ClientError` on a 429 --
    `code`/`status`/`details` are the exact attributes
    `automation_engineering.reuse.embeddings._is_retryable`/
    `_parse_retry_delay_seconds` read; no real SDK class is imported."""

    def __init__(self, retry_delay: str | None = None) -> None:
        super().__init__("429 RESOURCE_EXHAUSTED. quota exceeded")
        self.code = 429
        self.status = "RESOURCE_EXHAUSTED"
        self.details = (
            {"error": {"details": [{"retryDelay": retry_delay}]}}
            if retry_delay is not None
            else {"error": {}}
        )


def test_retry_after_one_429_then_succeeds() -> None:
    """FIX 3 verification: a stub provider that 429s once then succeeds --
    the call backs off (via the injected fake `sleep`) and retries, bounded,
    succeeding on the second attempt."""
    client = MagicMock()
    client.models.embed_content.side_effect = [
        _FakeRateLimitError(),
        _fake_embedding_response([[0.1, 0.2]]),
    ]
    sleeps: list[float] = []
    provider = GeminiEmbeddingProvider(
        api_key="fake-key", sleep=sleeps.append, clock=lambda: 0.0
    )

    with patch(_CLIENT_PATH, return_value=client):
        result = provider.embed(["text"])

    assert result == ((0.1, 0.2),)
    assert client.models.embed_content.call_count == 2
    assert len(sleeps) == 1
    assert sleeps[0] > 0


def test_retry_honors_retry_delay_from_the_sdk_error() -> None:
    """The SDK error's own `retryDelay` (e.g. `"34s"`) is honored over the
    fixed exponential fallback, when parseable."""
    client = MagicMock()
    client.models.embed_content.side_effect = [
        _FakeRateLimitError(retry_delay="34s"),
        _fake_embedding_response([[0.1, 0.2]]),
    ]
    sleeps: list[float] = []
    provider = GeminiEmbeddingProvider(
        api_key="fake-key", sleep=sleeps.append, clock=lambda: 0.0
    )

    with patch(_CLIENT_PATH, return_value=client):
        provider.embed(["text"])

    assert sleeps == [34.0]


def test_persistent_429_exhausts_retry_and_raises_call_error() -> None:
    """FIX 3 verification: a persistent 429 exhausts the bounded retry and
    raises `EmbeddingCallError` -- the backstop for FIX 2's per-need
    escalation, never an infinite retry loop."""
    client = MagicMock()
    client.models.embed_content.side_effect = _FakeRateLimitError()
    sleeps: list[float] = []
    provider = GeminiEmbeddingProvider(
        api_key="fake-key", max_retries=3, sleep=sleeps.append, clock=lambda: 0.0
    )

    with patch(_CLIENT_PATH, return_value=client):
        with pytest.raises(EmbeddingCallError, match="quota exceeded"):
            provider.embed(["text"])

    assert client.models.embed_content.call_count == 4  # first attempt + 3 retries
    assert len(sleeps) == 3


def test_non_retryable_failure_never_retries() -> None:
    """A plain SDK exception (no `code`/`status`) is not judged retryable --
    the existing `test_call_failure_wrapped_no_sdk_exception_crosses_boundary`
    already proves the wrap; this proves it also never sleeps/retries."""
    client = _fake_client(side_effect=_FakeSDKError("bad request"))
    sleeps: list[float] = []
    provider = GeminiEmbeddingProvider(api_key="fake-key", sleep=sleeps.append)

    with patch(_CLIENT_PATH, return_value=client):
        with pytest.raises(EmbeddingCallError):
            provider.embed(["text"])

    assert client.models.embed_content.call_count == 1
    assert sleeps == []


def test_pacing_sleeps_when_the_per_minute_limit_would_be_exceeded() -> None:
    """FIX 3 verification (pacing half): once `max_calls_per_minute` calls
    have been made within the trailing 60-second window, the next call
    blocks (via the injected fake `sleep`) until the window admits it."""
    client = _fake_client(_fake_embedding_response([[0.1]]))
    sleeps: list[float] = []
    clock_values = iter([0.0, 0.0, 10.0, 10.0])
    provider = GeminiEmbeddingProvider(
        api_key="fake-key",
        max_calls_per_minute=1,
        sleep=sleeps.append,
        clock=lambda: next(clock_values, 70.0),
    )

    with patch(_CLIENT_PATH, return_value=client):
        provider.embed(["first"])
        provider.embed(["second"])

    assert client.models.embed_content.call_count == 2
    assert len(sleeps) == 1
    assert sleeps[0] == pytest.approx(50.0)  # 60s window - 10s already elapsed
