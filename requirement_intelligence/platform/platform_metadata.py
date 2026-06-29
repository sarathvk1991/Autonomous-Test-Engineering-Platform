"""Centralized platform metadata.

Single source of truth for platform/version identifiers, the architecture
capability catalogue, the provider catalogue, and the CLI command list. The CLI
(and the version subcommand in particular) reads from here so that capability
status is defined once and never scattered as literals across the code.

This module contains data only — no behaviour and no business logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from requirement_intelligence.prompts.prompt_constants import PROMPT_VERSION

# --- Versions ---------------------------------------------------------------
PLATFORM_VERSION = "1.0.0"
CLI_VERSION = "1.0.0"
REASONING_CONTRACT_VERSION = "1.0.0"  # docs/architecture/ai-reasoning-contract.md
EXECUTION_PACKAGE_VERSION = "1.0.0"
BASELINE_VERSION = "1.0.0"

# Re-exported for convenience so callers have one import for all versions.
__all__ = [
    "ARCHITECTURE_COMPONENTS",
    "BASELINE_VERSION",
    "CLI_COMMANDS",
    "CLI_VERSION",
    "EXECUTION_PACKAGE_VERSION",
    "PLATFORM_VERSION",
    "PROMPT_VERSION",
    "PROVIDERS",
    "REASONING_CONTRACT_VERSION",
    "Capability",
    "ProviderInfo",
    "supported_provider_ids",
]


@dataclass(frozen=True)
class Capability:
    """An architecture capability and whether it is currently available."""

    name: str
    available: bool
    note: str = ""


@dataclass(frozen=True)
class ProviderInfo:
    """An LLM provider, its CLI id, and whether it is implemented today."""

    id: str
    display: str
    available: bool
    note: str = ""


# --- Architecture capability catalogue --------------------------------------
# Add a new capability here (and flip ``available`` when implemented). The CLI
# never hardcodes component status; it renders this list.
ARCHITECTURE_COMPONENTS: tuple[Capability, ...] = (
    Capability("Connector Registry", True),
    Capability("Connectors", True),
    Capability("Mappers", True),
    Capability("Consolidation Engine", True),
    Capability("Prompt Framework", True),
    Capability("LLM Framework", True),
    Capability("Gemini Provider", True),
    Capability("Requirement Analysis Service", True),
    Capability("Execution Package", True),
    Capability("Response Validator", False, "Planned"),
    Capability("CP1 Validator", False, "Planned"),
    Capability("Feature Generator", False, "Planned"),
    Capability("Test Generator", False, "Planned"),
)

# --- Provider catalogue -----------------------------------------------------
PROVIDERS: tuple[ProviderInfo, ...] = (
    ProviderInfo("gemini", "Gemini", True),
    ProviderInfo("azure_openai", "Azure OpenAI", False, "Reserved"),
    ProviderInfo("anthropic", "Anthropic", False, "Reserved"),
    ProviderInfo("bedrock", "Bedrock", False, "Reserved"),
    ProviderInfo("ollama", "Ollama", False, "Reserved"),
)

# --- CLI command catalogue --------------------------------------------------
CLI_COMMANDS: tuple[str, ...] = (
    "analyze",
    "list-artifacts",
    "validate",
    "benchmark",
    "version",
    "help",
)


def supported_provider_ids() -> tuple[str, ...]:
    """Return the ids of providers that are implemented and runnable today."""
    return tuple(provider.id for provider in PROVIDERS if provider.available)
