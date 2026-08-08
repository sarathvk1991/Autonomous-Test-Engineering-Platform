"""Gemini LLM provider — thin adapter over Google's official Gen AI SDK.

This is the first live provider in the platform.  It is a **thin adapter** and
nothing more: it validates provider configuration, converts a provider-agnostic
:class:`LLMRequest` into a Gemini request, performs exactly one Gemini call
(bounded retry aside — see below), and converts the Gemini response back into a
provider-agnostic :class:`LLMResponse`.

All Google SDK objects are confined to this module — no ``google.genai`` type
ever crosses the provider boundary, and no SDK exception escapes it.

The provider owns provider communication only.  It contains no prompt logic, no
orchestration, no validation, no parsing, and no knowledge of Requirement
Analysis or any downstream component.

SDK
---
Uses Google's current official Python SDK, ``google-genai`` (imported as
``from google import genai``).  The deprecated ``google-generativeai`` SDK is
**not** used.

Configuration
-------------
GOOGLE_API_KEY (env var, required)
    API key issued by Google AI Studio.
GEMINI_MODEL (env var, optional)
    Model to use (default: ``gemini-2.5-pro``).

Pacing and bounded retry-with-backoff (2026-08-05, Finding 2's own fix).
-------------------------------------------------------------------------
This provider is the ONE concrete `generate_content` call site shared by
every generation caller in the platform -- Layer 1/2's own requirement/
feature generation (`feature_engineering.generation.live_content_generator`,
`feature_engineering.remediation.live_remediator`) and Layer 3's four live
generators (`automation_engineering.generation.live_*_generator`) alike, all
via constructor-injected `LLMProvider` -- so fixing it here fixes the
boundary everywhere it is used, with no change to any of those six call
sites (each already catches this provider's own exception broadly and wraps
it in its own boundary's transport-failure type).

A live end-to-end run (`output/executions/run-20260805T105026014856Z-987575c0/`)
showed generation-call `429 RESOURCE_EXHAUSTED`s (the `generate_content`
free-tier quota, 15 requests/minute, distinct from the embedding boundary's
own separately-measured ~100/minute) transport-escalating correctly but
never being retried -- this provider "performs no retries," documented
plainly until now. Two mechanisms now live at this boundary, MIRRORING (not
sharing code with) `automation_engineering.reuse.embeddings.
GeminiEmbeddingProvider`'s own pacing/retry -- see that module's docstring
for the twin. Deliberately mirrored, not shared, because the two boundaries
differ in every dimension a shared helper would need to abstract over: a
different SDK call (`generate_content` vs. `embed_content`), a different
exception taxonomy to preserve (`ProviderGenerationError`, this provider's
own pre-existing contract, vs. `EmbeddingCallError`), a different real quota
(15/minute vs. ~100/minute), and different subsystems
(`requirement_intelligence.llm.providers` vs. `automation_engineering.reuse`)
with no existing precedent of either importing from the other for a concern
this narrow (exactly two call sites) -- introducing a new shared module
here would be the premature abstraction, not the fix.

1. **Proactive pacing** (`_pace`) -- before every call, blocks just long
   enough to keep this provider's own trailing-60-second call count under
   `max_calls_per_minute` (default 12 -- a defensive margin under the
   free tier's observed 15/minute `generate_content` quota, proportionally
   more conservative than the embedding boundary's 90-under-100 margin,
   since 15/minute leaves far less room for a shared quota with other
   callers).
2. **Reactive retry-with-backoff** (`_execute`) -- a retryable failure (a
   429/`RESOURCE_EXHAUSTED`, or a 5xx/`UNAVAILABLE`) is retried up to
   `max_retries` times, honoring the SDK error's own `retryDelay` when
   present, falling back to a fixed exponential schedule
   (`backoff_base_seconds * 2**attempt`, capped at `backoff_max_seconds`)
   when it is absent or unparseable -- the live run's own observed
   `retryDelay`s (0.9-1.5s) mean this recovers most transient 429s cheaply.
   A non-retryable failure is wrapped and raised immediately, unchanged.
   Retry exhaustion still raises `ProviderGenerationError` -- this
   provider's own pre-existing exception, unchanged in type -- which every
   existing caller already catches broadly and re-wraps as ITS OWN
   transport-failure type (Layer 3's `TransportFailureError` subclasses;
   Layer 2's own equivalent), so Fix 2's per-need/per-specification
   escalation is the unchanged backstop when this bounded retry is not
   enough.

`sleep`/`clock` are constructor-injectable (default `time.sleep`/
`time.monotonic`) for the same reason `GeminiEmbeddingProvider`'s are: tests
prove the retry/backoff SEQUENCE deterministically, with no real delay.
"""

from __future__ import annotations

import os
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from requirement_intelligence.llm.llm_exceptions import (
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderGenerationError,
)
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from shared.enums.base import ProviderType

_DEFAULT_MODEL = "gemini-2.5-pro"
_ENV_API_KEY = "GOOGLE_API_KEY"
_ENV_MODEL = "GEMINI_MODEL"

#: Defensive margin under the free tier's observed 15-request/minute
#: `generate_content` quota (the live run's own measured limit) -- not the
#: quota itself, a margin below it.
DEFAULT_MAX_CALLS_PER_MINUTE = 12

#: Retries attempted (in addition to the first try) before a retryable
#: failure is abandoned and raised as `ProviderGenerationError`.
DEFAULT_MAX_RETRIES = 4
DEFAULT_BACKOFF_BASE_SECONDS = 2.0
DEFAULT_BACKOFF_MAX_SECONDS = 60.0

_RATE_WINDOW_SECONDS = 60.0


def _is_retryable(exc: Exception) -> bool:
    """A 429/`RESOURCE_EXHAUSTED` or 5xx/`UNAVAILABLE` -- the shapes
    `google.genai.errors.APIError`'s own `code`/`status` attributes carry
    for a rate-limit or transient-server condition. Mirrors
    `automation_engineering.reuse.embeddings._is_retryable` exactly (same
    SDK, same error shape); not imported from there -- see this module's own
    docstring for why the two boundaries mirror rather than share."""
    code = getattr(exc, "code", None)
    if isinstance(code, int) and (code == 429 or 500 <= code < 600):
        return True
    status = getattr(exc, "status", None)
    return status in ("RESOURCE_EXHAUSTED", "UNAVAILABLE")


def _parse_retry_delay_seconds(details: Any) -> float | None:
    """Recursively search an SDK error's own `.details` payload for a
    `RetryInfo`-shaped `retryDelay` (e.g. `{"retryDelay": "1.2s"}`), returned
    as seconds. Returns `None` when nothing parseable is found. Mirrors
    `automation_engineering.reuse.embeddings._parse_retry_delay_seconds`
    exactly; see this module's own docstring for why it is a mirror, not a
    shared import."""
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


class GeminiProvider(LLMProvider):
    """Google Gemini implementation of :class:`LLMProvider`.

    All interaction with the ``google-genai`` SDK happens inside this class. The
    rest of the platform sees only :class:`LLMRequest` and :class:`LLMResponse`.
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
        """Initialise the Gemini provider.

        Parameters
        ----------
        api_key:
            Gemini API key.  If *None*, the value is read from the
            ``GOOGLE_API_KEY`` environment variable.
        model_name:
            Model identifier.  If *None*, the value is read from the
            ``GEMINI_MODEL`` environment variable, falling back to
            ``gemini-2.5-pro``.
        max_calls_per_minute, max_retries, backoff_base_seconds,
        backoff_max_seconds:
            Pacing/retry configuration -- see module docstring. Defaulted;
            no existing caller (`llm_factory.create_provider`, direct
            construction) passes these, so existing behavior is unchanged
            except for the retry/pacing itself.
        sleep, clock:
            Injectable for deterministic, delay-free tests of the pacing/
            retry schedule. Default to the real ``time.sleep``/
            ``time.monotonic``.
        """
        self._api_key: str = api_key or os.environ.get(_ENV_API_KEY, "")
        self._model_name: str = (
            model_name or os.environ.get(_ENV_MODEL, _DEFAULT_MODEL)
        )
        self._client: Any = None  # lazily initialised in _get_client()
        self._max_calls_per_minute = max_calls_per_minute
        self._max_retries = max_retries
        self._backoff_base_seconds = backoff_base_seconds
        self._backoff_max_seconds = backoff_max_seconds
        self._sleep = sleep
        self._clock = clock
        self._call_timestamps: deque[float] = deque()

    # ------------------------------------------------------------------
    # LLMProvider interface
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        """Short, stable identifier for this provider (``"gemini"``)."""
        return ProviderType.GEMINI.value

    def validate_connection(self) -> bool:
        """Verify configuration and that an SDK client can be constructed.

        Returns
        -------
        bool
            ``True`` when the client can be created without error.

        Raises
        ------
        ProviderConfigurationError
            When the API key or model name is absent, or the SDK is not
            installed.
        ProviderConnectionError
            When the SDK raises while constructing the client.
        """
        self._validate_configuration()
        try:
            self._get_client()
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            raise ProviderConnectionError(
                f"Gemini client initialisation failed: {exc}"
            ) from exc
        return True

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a single text response for the given request.

        The orchestration is a fixed, four-step adapter pipeline: validate
        configuration, build the Gemini request, execute exactly one call, and
        map the response.  Each step is delegated to a private helper.

        Parameters
        ----------
        request:
            The provider-agnostic request.  Only ``prompt``, ``temperature`` and
            ``metadata`` are consumed by this provider.

        Returns
        -------
        LLMResponse
            Provider-agnostic response with all Gemini-specific types removed.

        Raises
        ------
        ProviderConfigurationError
            When configuration is invalid or the SDK is not installed.
        ProviderGenerationError
            When the Gemini call fails or returns an unexpected payload.
        """
        self._validate_configuration()
        client = self._get_client()
        contents, config = self._build_request(request)

        start = time.monotonic()
        raw = self._execute(client, contents, config)
        latency_ms = (time.monotonic() - start) * 1000.0

        return self._map_response(raw, request, latency_ms)

    # ------------------------------------------------------------------
    # Private helpers — each with a single responsibility
    # ------------------------------------------------------------------

    def _validate_configuration(self) -> None:
        """Raise :class:`ProviderConfigurationError` for missing configuration."""
        if not self._api_key:
            raise ProviderConfigurationError(
                f"Gemini API key is required. Set the {_ENV_API_KEY!r} "
                "environment variable."
            )
        if not self._model_name:
            raise ProviderConfigurationError("Gemini model name must not be empty.")

    def _get_client(self) -> Any:
        """Return a cached ``google-genai`` client, creating it on first use."""
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise ProviderConfigurationError(
                    "google-genai package is not installed. "
                    "Run: pip install google-genai"
                ) from exc

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _build_request(self, request: LLMRequest) -> tuple[str, dict[str, Any]]:
        """Convert an :class:`LLMRequest` into Gemini call arguments.

        Returns the ``contents`` (the prompt) and a ``config`` mapping carrying
        the sampling temperature.  A plain mapping is used so the adapter does
        not depend on SDK config types at this layer.
        """
        contents: str = request.prompt
        config: dict[str, Any] = {"temperature": request.temperature}
        return contents, config

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

    def _execute(
        self,
        client: Any,
        contents: str,
        config: dict[str, Any],
    ) -> Any:
        """Invoke Gemini, with bounded retry-with-backoff on a retryable
        failure (module docstring, "Pacing and bounded retry-with-backoff").

        Wraps any non-retryable, or retry-exhausted, SDK failure in
        :class:`ProviderGenerationError` so no SDK exception type crosses
        the provider boundary -- unchanged in TYPE from before this fix,
        so every existing caller's own catch-all-and-rewrap boundary
        (`LiveFeatureContentGenerator`/`LiveFeatureRemediator`/Layer 3's
        four live generators) needs no change.
        """
        attempt = 0
        while True:
            self._pace()
            try:
                return client.models.generate_content(
                    model=self._model_name,
                    contents=contents,
                    config=config,
                )
            except Exception as exc:
                if attempt >= self._max_retries or not _is_retryable(exc):
                    raise ProviderGenerationError(
                        f"Gemini generation failed: {exc}"
                    ) from exc
                delay = _parse_retry_delay_seconds(getattr(exc, "details", None))
                if delay is None:
                    delay = min(
                        self._backoff_base_seconds * (2**attempt), self._backoff_max_seconds
                    )
                else:
                    delay = min(delay, self._backoff_max_seconds)
                self._sleep(delay)
                attempt += 1

    def _map_response(
        self,
        raw: Any,
        request: LLMRequest,
        latency_ms: float,
    ) -> LLMResponse:
        """Convert a Gemini SDK response into a provider-agnostic LLMResponse.

        No Gemini SDK types escape this method.  The request metadata is echoed
        into ``raw_response`` so it is never lost.

        **``None`` text is a generation failure, not a successful empty
        response (additive, the MALFORMED_RESPONSE crash fix).** The SDK's
        own ``.text`` accessor does not always raise on an unusable
        response -- for a non-``STOP`` completion (a live-measured example:
        Gemini's own ``MALFORMED_RESPONSE`` finish reason, an API-level
        value the currently-installed SDK's own enum does not recognize)
        with zero content parts, ``.text`` returns ``None`` cleanly, no
        exception. Previously that ``None`` flowed straight into
        ``LLMResponse(generated_text=None, ...)`` -- a pydantic model
        whose ``generated_text`` field requires ``str`` -- so construction
        itself raised an untyped, leaky ``pydantic.ValidationError``
        instead of this provider's own documented, typed
        :class:`~requirement_intelligence.llm.llm_exceptions.ProviderGenerationError`
        (whose own docstring already names exactly this case: "Response
        payload is missing the expected text field"). That ValidationError
        happened OUTSIDE this provider's own retry-with-backoff (which
        wraps only ``_execute``, the SDK call itself -- by the time
        ``_map_response`` runs, the call already succeeded; there is
        nothing left to retry), so every caller either had to catch a
        wrong-typed, undocumented exception via a blanket ``except
        Exception``, or would have seen an unhandled crash. Checking for
        ``None`` here, before construction, and raising the SAME typed
        exception the ``.text``-access failure path just above already
        raises, makes the failure ESCALATABLE the documented way -- exactly
        like a safety block or a quota-exhaustion failure, both of which
        this exception's own docstring already lists as its examples.
        """
        try:
            generated_text: str | None = raw.text
        except (AttributeError, ValueError) as exc:
            raise ProviderGenerationError(
                f"Could not extract text from Gemini response: {exc}"
            ) from exc

        finish_reason = self._extract_finish_reason(raw)

        if generated_text is None:
            raise ProviderGenerationError(
                "Gemini returned no text "
                f"(finish_reason={finish_reason!r}) -- the model completed "
                "the call but produced zero usable content, a provider-side "
                "generation failure distinct from a call/transport failure."
            )

        usage = self._extract_usage(raw)

        raw_response: dict[str, Any] = {
            "text": generated_text,
            "finish_reason": finish_reason,
            "request_metadata": dict(request.metadata),
        }

        return LLMResponse(
            provider=ProviderType.GEMINI,
            model=self._model_name,
            generated_text=generated_text,
            raw_response=raw_response,
            finish_reason=finish_reason,
            latency_ms=round(latency_ms, 2),
            usage=usage,
        )

    @staticmethod
    def _extract_finish_reason(raw: Any) -> str | None:
        """Best-effort extraction of the finish reason; never raises."""
        try:
            candidate = raw.candidates[0]
            reason = candidate.finish_reason
            name = getattr(reason, "name", None)
            return str(name) if name is not None else str(reason)
        except (AttributeError, IndexError, TypeError):
            return None

    @staticmethod
    def _extract_usage(raw: Any) -> LLMUsage | None:
        """Best-effort extraction of token usage; never raises."""
        try:
            um = raw.usage_metadata
            return LLMUsage(
                prompt_tokens=um.prompt_token_count,
                completion_tokens=um.candidates_token_count,
                total_tokens=um.total_token_count,
            )
        except (AttributeError, TypeError):
            return None
