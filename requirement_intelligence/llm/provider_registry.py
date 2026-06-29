"""Provider registry — configuration loader for LLM providers.

Loads provider configuration from environment variables or an optional config
dict.  This is the single source of truth for which provider is active and how
it is configured.

Design notes
------------
* Future-ready for Gemini, Azure OpenAI, Anthropic, Bedrock, and any other
  provider, without code changes here.
* Does not instantiate providers — that is the factory's responsibility.
* Does not hard-code any provider name.  Provider identity comes from
  configuration.
"""

from __future__ import annotations

import os
from typing import Any

_DEFAULT_PROVIDER_ENV = "LLM_PROVIDER"
_DEFAULT_PROVIDER = "gemini"


class ProviderRegistry:
    """Thin configuration loader for LLM provider selection.

    Usage
    -----
    .. code-block:: python

        registry = ProviderRegistry()
        name = registry.active_provider()   # e.g. "gemini"
        cfg  = registry.provider_config(name)

        provider = create_provider(name, **cfg)
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialise the registry.

        Parameters
        ----------
        config:
            Optional mapping of provider-name → config dict.  When *None*, all
            configuration is read from environment variables at call time.
        """
        self._config: dict[str, Any] = config or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def active_provider(self) -> str:
        """Return the name of the currently configured active provider.

        Resolution order
        ----------------
        1. ``config["active_provider"]`` (if supplied at construction time).
        2. ``LLM_PROVIDER`` environment variable.
        3. Fall back to ``"gemini"``.

        Returns
        -------
        str
            Provider name, e.g. ``"gemini"`` or ``"azure_openai"``.
        """
        return (
            self._config.get("active_provider")
            or os.environ.get(_DEFAULT_PROVIDER_ENV, _DEFAULT_PROVIDER)
        )

    def provider_config(self, provider_name: str) -> dict[str, Any]:
        """Return the configuration dict for a specific provider.

        The returned dict is suitable for passing as ``**kwargs`` to
        :func:`~requirement_intelligence.llm.llm_factory.create_provider`.

        Parameters
        ----------
        provider_name:
            Provider identifier (e.g. ``"gemini"``).

        Returns
        -------
        dict[str, Any]
            Provider-specific configuration kwargs.  Empty dict when no
            explicit config is present (the provider will fall back to
            environment variables).
        """
        providers_cfg: dict[str, Any] = self._config.get("providers", {})
        return dict(providers_cfg.get(provider_name, {}))

    def list_configured_providers(self) -> list[str]:
        """Return provider names that have explicit configuration entries.

        Returns
        -------
        list[str]
            Sorted list of provider names found in the config dict.
        """
        return sorted(self._config.get("providers", {}).keys())
