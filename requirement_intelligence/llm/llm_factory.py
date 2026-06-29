"""LLM Provider Factory.

Single place that maps a provider name to a concrete :class:`LLMProvider`
instance.  All other modules that need an LLM provider call
:func:`create_provider`; no module instantiates a provider directly.

Supported provider names
------------------------
``"gemini"``
    Google Gemini — active implementation.
``"azure_openai"``
    Azure OpenAI — stub; raises :class:`NotImplementedError` until the licence
    is activated.

Adding a new provider
---------------------
1. Implement :class:`~requirement_intelligence.llm.providers.base_provider.LLMProvider`.
2. Add an entry to ``_PROVIDER_REGISTRY`` below.
3. No other change is required anywhere in the platform.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.llm.llm_exceptions import ProviderConfigurationError
from requirement_intelligence.llm.providers.azure_openai_provider import AzureOpenAIProvider
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from requirement_intelligence.llm.providers.gemini_provider import GeminiProvider

# Maps the public provider name (as used in configuration / environment) to the
# concrete class.  Values are *classes*, not instances.
_PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "azure_openai": AzureOpenAIProvider,
}


def create_provider(
    provider_name: str,
    **kwargs: Any,
) -> LLMProvider:
    """Instantiate and return a provider by name.

    Parameters
    ----------
    provider_name:
        Case-sensitive provider identifier (e.g. ``"gemini"``).
    **kwargs:
        Optional keyword arguments forwarded to the provider constructor.
        Useful for injecting API keys or model names in tests without touching
        environment variables.

    Returns
    -------
    LLMProvider
        A concrete provider instance ready for use.

    Raises
    ------
    ProviderConfigurationError
        When *provider_name* is not recognised.
    """
    provider_class = _PROVIDER_REGISTRY.get(provider_name)
    if provider_class is None:
        supported = ", ".join(sorted(_PROVIDER_REGISTRY))
        raise ProviderConfigurationError(
            f"Unknown LLM provider {provider_name!r}. "
            f"Supported providers: {supported}."
        )
    return provider_class(**kwargs)


def list_providers() -> list[str]:
    """Return the names of all registered providers.

    Returns
    -------
    list[str]
        Sorted list of provider name strings.
    """
    return sorted(_PROVIDER_REGISTRY)
