"""Gemini LLM provider implementation.

This is the first concrete provider in the platform.  All Gemini SDK objects
are confined to this module — no google.generativeai types leak into the
LLMResponse or any downstream component.

Configuration
-------------
GEMINI_API_KEY (env var, required)
    API key issued by Google AI Studio or Vertex AI.
GEMINI_MODEL_NAME (env var, optional)
    Model to use (default: ``gemini-1.5-flash``).
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

_DEFAULT_MODEL = "gemini-1.5-flash"
_ENV_API_KEY = "GEMINI_API_KEY"
_ENV_MODEL = "GEMINI_MODEL_NAME"


class GeminiProvider(LLMProvider):
    """Google Gemini implementation of :class:`LLMProvider`.

    All interaction with the ``google-generativeai`` SDK happens inside this
    class.  The rest of the platform sees only :class:`LLMResponse`.
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
            ``GEMINI_API_KEY`` environment variable.
        model_name:
            Model identifier.  If *None*, the value is read from the
            ``GEMINI_MODEL_NAME`` environment variable, falling back to
            ``gemini-1.5-flash``.
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
        return "gemini"

    def validate_connection(self) -> bool:
        """Verify API key presence and attempt a lightweight SDK initialisation.

        Returns
        -------
        bool
            ``True`` when the client can be created without error.

        Raises
        ------
        ProviderConfigurationError
            When the API key is absent or the model name is empty.
        ProviderConnectionError
            When the SDK raises an error during initialisation.
        """
        self._validate_config()
        try:
            self._get_client()
        except Exception as exc:
            raise ProviderConnectionError(
                f"Gemini client initialisation failed: {exc}"
            ) from exc
        return True

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate text using the Gemini API.

        Parameters
        ----------
        request:
            Provider-agnostic :class:`LLMRequest`.  Only ``request.prompt`` and
            ``request.temperature`` are consumed by this provider today.

        Returns
        -------
        LLMResponse
            Provider-agnostic response with all Gemini-specific types removed.

        Raises
        ------
        ProviderConfigurationError
            When configuration is invalid.
        ProviderGenerationError
            When the Gemini API call fails or returns an unexpected payload.
        """
        self._validate_config()

        start = time.monotonic()
        try:
            model = self._get_client()
            raw = model.generate_content(
                request.prompt,
                generation_config={"temperature": request.temperature},
            )
        except Exception as exc:
            raise ProviderGenerationError(
                f"Gemini generation failed: {exc}"
            ) from exc

        latency_ms = (time.monotonic() - start) * 1000.0

        return self._to_llm_response(raw, latency_ms)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_config(self) -> None:
        """Raise :class:`ProviderConfigurationError` for missing config."""
        if not self._api_key:
            raise ProviderConfigurationError(
                f"Gemini API key is required. Set the {_ENV_API_KEY!r} "
                "environment variable."
            )
        if not self._model_name:
            raise ProviderConfigurationError("Gemini model name must not be empty.")

    def _get_client(self) -> Any:
        """Return a cached Gemini GenerativeModel instance."""
        if self._client is None:
            try:
                import google.generativeai as genai
            except ImportError as exc:
                raise ProviderConfigurationError(
                    "google-generativeai package is not installed. "
                    "Run: pip install google-generativeai"
                ) from exc

            genai.configure(api_key=self._api_key)
            self._client = genai.GenerativeModel(self._model_name)
        return self._client

    def _to_llm_response(self, raw: Any, latency_ms: float) -> LLMResponse:
        """Convert a Gemini SDK response into a provider-agnostic LLMResponse.

        No Gemini SDK types escape this method.
        """
        try:
            generated_text: str = raw.text
        except (AttributeError, ValueError) as exc:
            raise ProviderGenerationError(
                f"Could not extract text from Gemini response: {exc}"
            ) from exc

        finish_reason: str | None = None
        usage: LLMUsage | None = None

        try:
            candidate = raw.candidates[0]
            finish_reason = str(candidate.finish_reason.name)
        except (AttributeError, IndexError):
            pass

        try:
            um = raw.usage_metadata
            usage = LLMUsage(
                prompt_tokens=um.prompt_token_count,
                completion_tokens=um.candidates_token_count,
                total_tokens=um.total_token_count,
            )
        except AttributeError:
            pass

        # Serialise the raw response as a plain dict for auditing.
        raw_response: dict[str, Any] = {"text": generated_text, "finish_reason": finish_reason}

        return LLMResponse(
            provider=ProviderType.GEMINI,
            model=self._model_name,
            generated_text=generated_text,
            raw_response=raw_response,
            finish_reason=finish_reason,
            latency_ms=round(latency_ms, 2),
            usage=usage,
        )
