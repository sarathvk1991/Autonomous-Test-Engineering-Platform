"""Reusable Azure OpenAI client factory.

This is the *only* place the platform constructs an Azure OpenAI client. Layers
(e.g. the Requirement Analyzer) depend on this factory so model configuration,
retries, and timeouts are governed centrally rather than re-implemented per
call site.

NOTE: Infrastructure boundary only — no prompt or business logic lives here.
"""

from __future__ import annotations

from functools import lru_cache

from openai import AzureOpenAI

from app.core.settings import get_settings


@lru_cache(maxsize=1)
def get_azure_openai_client() -> AzureOpenAI:
    """Return a cached, configured Azure OpenAI client.

    Configuration is sourced from :func:`app.core.settings.get_settings`. The
    client is cached so connection setup happens once per process.
    """
    cfg = get_settings().azure_openai
    return AzureOpenAI(
        azure_endpoint=cfg.endpoint,
        api_key=cfg.api_key,
        api_version=cfg.api_version,
        timeout=cfg.timeout_seconds,
        max_retries=cfg.max_retries,
    )
