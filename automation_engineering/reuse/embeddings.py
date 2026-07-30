"""The embedding boundary: text in, vectors out -- a thin adapter over
Google's `google-genai` SDK, exactly the same seam discipline the platform
already applies to LLM generation
(:class:`~requirement_intelligence.llm.providers.base_provider.LLMProvider`/
:class:`~requirement_intelligence.llm.providers.gemini_provider.GeminiProvider`),
scoped narrowly to embeddings.

**Why a separate abstraction from `LLMProvider`, not a reuse of it.**
`LLMProvider.generate` is shaped around one text-completion request/response
(`LLMRequest`/`LLMResponse`) -- prompt in, generated text out. Embeddings are
a structurally different call (many texts in, one vector per text out, no
sampling temperature, no "generated text") -- forcing that shape through
`LLMRequest`/`LLMResponse` would mean overloading fields that do not apply
(`temperature`) or inventing ones that do not exist on the real contract
(a vector list). A second, narrow `EmbeddingProvider` Protocol -- mirroring
`LLMProvider`'s own discipline (thin adapter, no SDK type crosses the
boundary, one call, config-error vs. call-error distinguished) without
inheriting from it -- is the honest shape.

:class:`GeminiEmbeddingProvider` is a **live** implementation: it makes a
real network call when actually invoked. No live call happens anywhere in
this module's import or construction -- only inside `.embed(...)` itself,
exactly like `GeminiProvider.generate`. This environment has no
`GOOGLE_API_KEY` configured (verified directly, not assumed), so this class
is built and unit-tested against a mocked SDK client only -- the same
stub-vs-live split ADR-0044 D5 already documents for the SonarQube adapter
("the adapter is stub-tested; the live gate is exercised only where
[the live dependency] exists"). :mod:`.live_matcher` is the seam consumer;
the reuse engine (:mod:`.engine`) never imports this module at all.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any, Protocol

_DEFAULT_MODEL = "text-embedding-004"
_ENV_API_KEY = "GOOGLE_API_KEY"
_ENV_MODEL = "EMBEDDING_MODEL"


class EmbeddingConfigurationError(Exception):
    """Required configuration (API key, model name) is missing, or the SDK
    is not installed. Mirrors
    :class:`requirement_intelligence.llm.llm_exceptions.ProviderConfigurationError`'s
    own role for the embedding boundary specifically."""


class EmbeddingCallError(Exception):
    """The embedding call itself failed, or returned an unusable payload.
    Mirrors
    :class:`requirement_intelligence.llm.llm_exceptions.ProviderGenerationError`'s
    own role for the embedding boundary specifically. No SDK exception
    ever crosses this boundary unwrapped -- it is preserved as `__cause__`."""


class EmbeddingProvider(Protocol):
    """Turns a batch of texts into one vector per text, same order in as
    out. Batching the whole call is deliberate -- ADR-0044 D3's own
    embeddings rationale ("cheaper, batchable across a run's full step
    set... cacheable across runs") is only realized if a caller can embed
    many texts in one call, not one call per text."""

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """Return one embedding vector per element of `texts`, same order.

        Raises
        ------
        EmbeddingConfigurationError
            Missing API key/model or the SDK is not installed.
        EmbeddingCallError
            The call failed, or the response could not be mapped to vectors.
        """
        ...


class GeminiEmbeddingProvider:
    """`google-genai`-backed :class:`EmbeddingProvider` -- the live
    implementation ADR-0044 D3's embeddings lean resolves to.

    Parameters
    ----------
    api_key:
        Gemini API key. If *None*, read from the ``GOOGLE_API_KEY``
        environment variable (mirrors
        :class:`~requirement_intelligence.llm.providers.gemini_provider.GeminiProvider`
        exactly).
    model_name:
        Embedding model identifier. If *None*, read from the
        ``EMBEDDING_MODEL`` environment variable, falling back to
        ``text-embedding-004``.
    """

    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        self._api_key: str = api_key or os.environ.get(_ENV_API_KEY, "")
        self._model_name: str = model_name or os.environ.get(_ENV_MODEL, _DEFAULT_MODEL)
        self._client: Any = None

    def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        self._validate_configuration()
        client = self._get_client()
        raw = self._execute(client, texts)
        return self._map_response(raw, expected_count=len(texts))

    def _validate_configuration(self) -> None:
        if not self._api_key:
            raise EmbeddingConfigurationError(
                f"Gemini API key is required. Set the {_ENV_API_KEY!r} environment variable."
            )
        if not self._model_name:
            raise EmbeddingConfigurationError("Embedding model name must not be empty.")

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise EmbeddingConfigurationError(
                    "google-genai package is not installed. Run: pip install google-genai"
                ) from exc
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _execute(self, client: Any, texts: Sequence[str]) -> Any:
        try:
            return client.models.embed_content(model=self._model_name, contents=list(texts))
        except Exception as exc:
            raise EmbeddingCallError(f"Gemini embedding call failed: {exc}") from exc

    def _map_response(self, raw: Any, *, expected_count: int) -> tuple[tuple[float, ...], ...]:
        try:
            embeddings = raw.embeddings
            vectors = tuple(tuple(e.values) for e in embeddings)
        except (AttributeError, TypeError, ValueError) as exc:
            raise EmbeddingCallError(
                f"Could not extract embedding vectors from Gemini response: {exc}"
            ) from exc
        if len(vectors) != expected_count:
            raise EmbeddingCallError(
                f"Gemini returned {len(vectors)} embedding(s) for {expected_count} "
                "input text(s) -- expected one-to-one, same order."
            )
        return vectors


__all__ = [
    "EmbeddingCallError",
    "EmbeddingConfigurationError",
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
]
