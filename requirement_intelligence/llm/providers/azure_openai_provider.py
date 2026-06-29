"""Azure OpenAI provider stub.

This provider will be enabled once the organisation's Azure OpenAI licence
becomes available.  The class satisfies the :class:`LLMProvider` interface so
the factory and tests can reference it today without any real SDK dependency.

To activate this provider in the future:
1. Uncomment / add the ``openai`` SDK calls.
2. Add ``AZURE_OPENAI_ENDPOINT``, ``AZURE_OPENAI_API_KEY``, and
   ``AZURE_OPENAI_DEPLOYMENT`` to the environment configuration.
3. Remove the :class:`NotImplementedError` guards.
"""

from __future__ import annotations

from requirement_intelligence.llm.llm_models import LLMRequest, LLMResponse
from requirement_intelligence.llm.providers.base_provider import LLMProvider


class AzureOpenAIProvider(LLMProvider):
    """Stub implementation of the Azure OpenAI provider.

    All methods raise :class:`NotImplementedError`.  This class exists so the
    rest of the platform can reference ``"azure_openai"`` as a valid provider
    name without requiring the ``openai`` SDK or live credentials.

    Licensing status: NOT YET AVAILABLE — stub only.
    """

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    def validate_connection(self) -> bool:
        """Not implemented — Azure OpenAI licence not yet available.

        Raises
        ------
        NotImplementedError
            Always.  Remove this guard when licensing is activated.
        """
        raise NotImplementedError(
            "Azure OpenAI provider is not yet enabled. "
            "This stub will be replaced once the licence is available."
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Not implemented — Azure OpenAI licence not yet available.

        Parameters
        ----------
        request:
            Ignored at this time.

        Raises
        ------
        NotImplementedError
            Always.  Remove this guard when licensing is activated.
        """
        raise NotImplementedError(
            "Azure OpenAI provider is not yet enabled. "
            "This stub will be replaced once the licence is available."
        )
