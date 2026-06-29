"""Abstract base class for all LLM providers.

Every concrete provider must inherit from :class:`LLMProvider` and implement
all three abstract methods.  No implementation logic belongs here — this module
is the single stable contract that the Prompt Builder, Response Validator,
CP1 Engine, and Output Writer depend on.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.llm.llm_models import LLMResponse


class LLMProvider(ABC):
    """Contract that every LLM provider must satisfy.

    The factory and all downstream components depend on this abstraction, never
    on a concrete provider class.  Adding a new provider requires only:

    1. Implementing this interface.
    2. Registering the provider name in :mod:`requirement_intelligence.llm.llm_factory`.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short, stable identifier for this provider.

        Returns
        -------
        str
            Examples: ``"gemini"``, ``"azure_openai"``.
        """

    @abstractmethod
    def validate_connection(self) -> bool:
        """Verify that the provider is reachable and correctly configured.

        Returns
        -------
        bool
            ``True`` when the provider is ready to serve generation requests.

        Raises
        ------
        ProviderConfigurationError
            If required configuration (e.g. API key) is absent.
        ProviderConnectionError
            If the provider endpoint cannot be reached.
        """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Generate a text response for the given prompt.

        Parameters
        ----------
        prompt:
            The fully-rendered prompt string.
        temperature:
            Sampling temperature (0.0 = deterministic).

        Returns
        -------
        LLMResponse
            Provider-agnostic response object.

        Raises
        ------
        ProviderGenerationError
            If the provider rejects the request or returns an unexpected payload.
        """
