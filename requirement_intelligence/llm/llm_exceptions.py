"""Custom exceptions for the LLM provider framework.

Hierarchy
---------
LLMError
├── ProviderConfigurationError
├── ProviderConnectionError
└── ProviderGenerationError
"""


class LLMError(Exception):
    """Base exception for all LLM provider errors."""


class ProviderConfigurationError(LLMError):
    """Raised when a provider cannot be initialised due to missing or invalid
    configuration.

    Examples
    --------
    - Missing API key environment variable.
    - Unknown provider name requested from the factory.
    - Invalid model name.
    """


class ProviderConnectionError(LLMError):
    """Raised when a provider endpoint cannot be reached or authentication
    fails.

    Examples
    --------
    - Network timeout contacting the Gemini API.
    - Invalid or expired API key rejected by the provider.
    """


class ProviderGenerationError(LLMError):
    """Raised when the provider rejects the generation request or returns an
    unexpected payload.

    Examples
    --------
    - Provider returns a safety block or content-filter refusal.
    - Response payload is missing the expected text field.
    - Provider quota exhausted.
    """
