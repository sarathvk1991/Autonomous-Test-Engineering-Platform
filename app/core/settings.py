"""Centralised, type-safe application settings.

Settings are loaded once from environment variables (and an optional ``.env``
file) via pydantic-settings, then cached. Layers and infrastructure modules
read configuration exclusively through :func:`get_settings` — no module reads
``os.environ`` directly. This keeps configuration validated, documented, and
overridable in tests.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureOpenAISettings(BaseSettings):
    """Connection settings for the Azure OpenAI provider."""

    model_config = SettingsConfigDict(env_prefix="AZURE_OPENAI_", extra="ignore")

    endpoint: str = ""
    api_key: str = ""
    api_version: str = "2024-06-01"
    deployment: str = "gpt-4o"
    embedding_deployment: str = "text-embedding-3-large"
    timeout_seconds: int = 60
    max_retries: int = 3


class Settings(BaseSettings):
    """Root application settings — the single source of truth for config."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---------------------------------------------------------
    app_name: str = Field(default="Autonomous Test Engineering Platform")
    app_env: str = Field(default="local")
    app_debug: bool = Field(default=True)
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # --- Logging -------------------------------------------------------------
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)

    # --- Persistence (future phase) -----------------------------------------
    database_url: str = Field(default="")

    # --- Nested provider settings -------------------------------------------
    azure_openai: AzureOpenAISettings = Field(default_factory=AzureOpenAISettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings singleton.

    Cached so the ``.env`` file and environment are parsed only once. Call
    ``get_settings.cache_clear()`` in tests to force a reload.
    """
    return Settings()
