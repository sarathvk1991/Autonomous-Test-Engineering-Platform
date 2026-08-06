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

**Default model, corrected (2026-08-05, the free-tier survivability build).**
`text-embedding-004` 404s against a real Gemini API key -- verified directly
against the live end-to-end run this build's own task responds to; the model
this platform's real key actually serves is `gemini-embedding-001`, now the
default. `EMBEDDING_MODEL` still overrides either way.

**Pacing and bounded retry-with-backoff (2026-08-05, the free-tier
survivability build).** A live run's embedding calls previously had no
pacing and no retry: a single `429 RESOURCE_EXHAUSTED` failed immediately,
wrapped as `EmbeddingCallError` with zero attempt to wait it out, even
though the SDK's own error response frequently names exactly how long to
wait (`retryDelay`). Two mechanisms now live at this boundary, both scoped
to the embedding call only (never woven into `.live_matcher` or the reuse
engine, which know nothing about either):

1. **Proactive pacing** (`_pace`) -- before every call, blocks just long
   enough to keep this provider's own trailing-60-second call count under
   `max_calls_per_minute` (default 90, a defensive margin under the free
   tier's observed 100/minute embedding quota). A run whose batching
   (`LiveSemanticMatcher.prime`) already collapsed most calls to one or two
   rarely blocks here at all -- this guards the rarer case of a run large
   enough to still make several calls.
2. **Reactive retry-with-backoff** (`_execute`) -- a retryable failure (a
   429/`RESOURCE_EXHAUSTED`, or a 5xx/`UNAVAILABLE`) is retried up to
   `max_retries` times, honoring the SDK error's own `retryDelay` when
   present (parsed from `google.genai.errors.APIError.details`, the raw
   response body Google's own `RetryInfo` proto is nested inside), falling
   back to a fixed exponential schedule (`backoff_base_seconds * 2**attempt`,
   capped at `backoff_max_seconds`) when it is absent or unparseable. A
   non-retryable failure (anything else -- a config problem masquerading as
   a call failure, a malformed request) is still wrapped and raised
   immediately, unchanged. Retry exhaustion still raises `EmbeddingCallError`
   -- this is a BOUNDED retry, not a substitute for the per-need transport
   isolation `automation_engineering.stage.runner` provides (the backstop
   when retry alone isn't enough).

`sleep`/`clock` are constructor-injectable (default `time.sleep`/
`time.monotonic`) specifically so tests can prove the retry/backoff
SEQUENCE deterministically, with no real delay -- the same reason a fake
clock is standard practice for testing any backoff schedule.
"""

from __future__ import annotations

import math
import os
import time
from collections import deque
from collections.abc import Callable, Sequence
from typing import Any, Protocol

from automation_engineering.errors import TransportFailureError

_DEFAULT_MODEL = "gemini-embedding-001"
_ENV_API_KEY = "GOOGLE_API_KEY"
_ENV_MODEL = "EMBEDDING_MODEL"

#: Defensive margin under the free tier's observed 100-request/minute
#: embedding quota (the live run's own measured limit) -- not the quota
#: itself, a margin below it, so this provider's own pacing does not assume
#: it is the only caller against that quota in a given minute.
DEFAULT_MAX_CALLS_PER_MINUTE = 90

#: Retries attempted (in addition to the first try) before a retryable
#: failure is abandoned and raised as `EmbeddingCallError`.
DEFAULT_MAX_RETRIES = 4
DEFAULT_BACKOFF_BASE_SECONDS = 2.0
DEFAULT_BACKOFF_MAX_SECONDS = 60.0

_RATE_WINDOW_SECONDS = 60.0


class EmbeddingConfigurationError(Exception):
    """Required configuration (API key, model name) is missing, or the SDK
    is not installed. Mirrors
    :class:`requirement_intelligence.llm.llm_exceptions.ProviderConfigurationError`'s
    own role for the embedding boundary specifically. Deliberately NOT a
    :class:`~automation_engineering.errors.TransportFailureError`: a missing
    key/model fails identically on every retry, so per-need escalation would
    only produce N identical escalations instead of one clear, immediate
    failure -- the same config-vs-call distinction Layer 1/2's own provider
    boundary already draws."""


class EmbeddingCallError(TransportFailureError):
    """The embedding call itself failed (after any retry this boundary
    attempted), or returned an unusable payload. Mirrors
    :class:`requirement_intelligence.llm.llm_exceptions.ProviderGenerationError`'s
    own role for the embedding boundary specifically. No SDK exception ever
    crosses this boundary unwrapped -- it is preserved as `__cause__`."""


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


def cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Cosine similarity between two embedding vectors -- **public and
    shared** (promoted from :mod:`automation_engineering.reuse.live_matcher`'s
    own private helper, ADR-0046 D3/D7's "promote, don't duplicate"
    discipline). Every consumer that scores one embedded text against
    another (:class:`~automation_engineering.reuse.live_matcher.
    LiveSemanticMatcher`'s need-vs-catalog matching; CP5's orphaned-glue
    semantic hint, :mod:`automation_engineering.cp5.orphaned_glue`; a future
    CP5 cross-suite near-duplicate sweep, ADR-0046 D3) uses this one
    formula, never a second hand-maintained copy."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _is_retryable(exc: Exception) -> bool:
    """A 429/`RESOURCE_EXHAUSTED` or 5xx/`UNAVAILABLE` -- the shapes
    `google.genai.errors.APIError`'s own `code`/`status` attributes carry
    for a rate-limit or transient-server condition. Anything else (a bad
    request, an auth failure, a plain SDK exception with neither attribute)
    is not retried -- retrying it would only delay an outcome retry cannot
    change."""
    code = getattr(exc, "code", None)
    if isinstance(code, int) and (code == 429 or 500 <= code < 600):
        return True
    status = getattr(exc, "status", None)
    return status in ("RESOURCE_EXHAUSTED", "UNAVAILABLE")


def _parse_retry_delay_seconds(details: Any) -> float | None:
    """Recursively search an SDK error's own `.details` payload (the raw
    response body `google.genai.errors.APIError` stores) for a
    `RetryInfo`-shaped `retryDelay` (Google API errors nest it under
    `error.details[]`, e.g. `{"retryDelay": "34s"}`), returned as seconds.
    Returns `None` when nothing parseable is found -- callers fall back to a
    fixed exponential schedule; a parsing miss never raises."""
    if isinstance(details, dict):
        raw = details.get("retryDelay")
        if isinstance(raw, str) and raw.endswith("s"):
            try:
                return float(raw[:-1])
            except ValueError:
                pass
        for value in details.values():
            found = _parse_retry_delay_seconds(value)
            if found is not None:
                return found
    elif isinstance(details, list):
        for item in details:
            found = _parse_retry_delay_seconds(item)
            if found is not None:
                return found
    return None


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
        ``gemini-embedding-001``.
    max_calls_per_minute, max_retries, backoff_base_seconds,
    backoff_max_seconds:
        Pacing/retry configuration -- see module docstring.
    sleep, clock:
        Injectable for deterministic, delay-free tests of the pacing/retry
        schedule. Default to the real ``time.sleep``/``time.monotonic``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        *,
        max_calls_per_minute: int = DEFAULT_MAX_CALLS_PER_MINUTE,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base_seconds: float = DEFAULT_BACKOFF_BASE_SECONDS,
        backoff_max_seconds: float = DEFAULT_BACKOFF_MAX_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._api_key: str = api_key or os.environ.get(_ENV_API_KEY, "")
        self._model_name: str = model_name or os.environ.get(_ENV_MODEL, _DEFAULT_MODEL)
        self._client: Any = None
        self._max_calls_per_minute = max_calls_per_minute
        self._max_retries = max_retries
        self._backoff_base_seconds = backoff_base_seconds
        self._backoff_max_seconds = backoff_max_seconds
        self._sleep = sleep
        self._clock = clock
        self._call_timestamps: deque[float] = deque()

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

    def _pace(self) -> None:
        """Block until another call keeps this provider's own trailing
        60-second call count under `max_calls_per_minute`. See module
        docstring, "Proactive pacing"."""
        now = self._clock()
        window_start = now - _RATE_WINDOW_SECONDS
        while self._call_timestamps and self._call_timestamps[0] < window_start:
            self._call_timestamps.popleft()
        if len(self._call_timestamps) >= self._max_calls_per_minute:
            wait = self._call_timestamps[0] + _RATE_WINDOW_SECONDS - now
            if wait > 0:
                self._sleep(wait)
            now = self._clock()
            window_start = now - _RATE_WINDOW_SECONDS
            while self._call_timestamps and self._call_timestamps[0] < window_start:
                self._call_timestamps.popleft()
        self._call_timestamps.append(self._clock())

    def _execute(self, client: Any, texts: Sequence[str]) -> Any:
        attempt = 0
        while True:
            self._pace()
            try:
                return client.models.embed_content(model=self._model_name, contents=list(texts))
            except Exception as exc:
                if attempt >= self._max_retries or not _is_retryable(exc):
                    raise EmbeddingCallError(f"Gemini embedding call failed: {exc}") from exc
                delay = _parse_retry_delay_seconds(getattr(exc, "details", None))
                if delay is None:
                    delay = min(
                        self._backoff_base_seconds * (2**attempt), self._backoff_max_seconds
                    )
                else:
                    delay = min(delay, self._backoff_max_seconds)
                self._sleep(delay)
                attempt += 1

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
    "DEFAULT_BACKOFF_BASE_SECONDS",
    "DEFAULT_BACKOFF_MAX_SECONDS",
    "DEFAULT_MAX_CALLS_PER_MINUTE",
    "DEFAULT_MAX_RETRIES",
    "EmbeddingCallError",
    "EmbeddingConfigurationError",
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
    "cosine_similarity",
]
