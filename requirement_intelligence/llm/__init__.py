"""LLM provider framework for the Requirement Intelligence layer.

Public surface
--------------
LLMProvider          — abstract base (import from providers.base_provider)
LLMRequest           — input model
LLMResponse          — output model
LLMUsage             — token accounting
ProviderType         — provider identity enum (shared.enums.base)
create_provider()    — factory entry point
ProviderRegistry     — configuration loader
LLMError             — base exception
ProviderConfigurationError
ProviderConnectionError
ProviderGenerationError
"""

from requirement_intelligence.llm.llm_exceptions import (
    LLMError,
    ProviderConfigurationError,
    ProviderConnectionError,
    ProviderGenerationError,
)
from requirement_intelligence.llm.llm_factory import create_provider, list_providers
from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse, LLMUsage
from requirement_intelligence.llm.provider_registry import ProviderRegistry
from requirement_intelligence.llm.providers.base_provider import LLMProvider
from shared.enums.base import ProviderType

__all__ = [
    "LLMError",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "LLMUsage",
    "ProviderConfigurationError",
    "ProviderConnectionError",
    "ProviderGenerationError",
    "ProviderRegistry",
    "ProviderType",
    "create_provider",
    "list_providers",
]
