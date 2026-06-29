"""Gemini LLM provider — thin adapter over Google's official Gen AI SDK.

This is the first live provider in the platform.  It is a **thin adapter** and
nothing more: it validates provider configuration, converts a provider-agnostic
:class:`LLMRequest` into a Gemini request, performs exactly one Gemini call, and
converts the Gemini response back into a provider-agnostic :class:`LLMResponse`.

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
"""

from __future__ import annotations

import os
import time
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


class GeminiProvider(LLMProvider):
    """Google Gemini implementation of :class:`LLMProvider`.

    All interaction with the ``google-genai`` SDK happens inside this class. The
    rest of the platform sees only :class:`LLMRequest` and :class:`LLMResponse`.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
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
        """
        self._api_key: str = api_key or os.environ.get(_ENV_API_KEY, "")
        self._model_name: str = (
            model_name or os.environ.get(_ENV_MODEL, _DEFAULT_MODEL)
        )
        self._client: Any = None  # lazily initialised in _get_client()

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

    def _execute(
        self,
        client: Any,
        contents: str,
        config: dict[str, Any],
    ) -> Any:
        """Invoke Gemini exactly once.

        Wraps any SDK failure in :class:`ProviderGenerationError` so no SDK
        exception type crosses the provider boundary.  Performs no retries.
        """
        try:
            return client.models.generate_content(
                model=self._model_name,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            raise ProviderGenerationError(
                f"Gemini generation failed: {exc}"
            ) from exc

    def _map_response(
        self,
        raw: Any,
        request: LLMRequest,
        latency_ms: float,
    ) -> LLMResponse:
        """Convert a Gemini SDK response into a provider-agnostic LLMResponse.

        No Gemini SDK types escape this method.  The request metadata is echoed
        into ``raw_response`` so it is never lost.
        """
        try:
            generated_text: str = raw.text
        except (AttributeError, ValueError) as exc:
            raise ProviderGenerationError(
                f"Could not extract text from Gemini response: {exc}"
            ) from exc

        finish_reason = self._extract_finish_reason(raw)
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
