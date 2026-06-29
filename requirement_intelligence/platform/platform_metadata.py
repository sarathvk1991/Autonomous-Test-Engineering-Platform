"""Centralized platform metadata.

Single source of truth for platform/version identifiers, the architecture
capability catalogue, the provider catalogue, and the CLI command list. The CLI
(via :class:`~requirement_intelligence.platform.platform_capabilities.PlatformCapabilities`)
and the manifest builder read from here so that capability status and version
numbers are defined once and never scattered as literals across the code.

This module contains data only — no behaviour and no business logic.

Version semantics
-----------------
* ``PLATFORM_VERSION`` — the platform release as a whole.
* ``EXECUTION_PACKAGE_VERSION`` — the execution-artifact generation contract.
* ``MANIFEST_SCHEMA_VERSION`` — the JSON contract of ``manifest.json``. Future
  manifest field changes should only require incrementing this constant.

Each platform component is also versioned independently so a single component can
evolve without bumping the whole platform.
"""

from __future__ import annotations

from dataclasses import dataclass

from requirement_intelligence.prompts.prompt_constants import PROMPT_VERSION

# --- Top-level versions -----------------------------------------------------
PLATFORM_VERSION = "1.0.0"
CLI_VERSION = "1.0.0"
REASONING_CONTRACT_VERSION = "1.0.0"  # docs/architecture/ai-reasoning-contract.md
EXECUTION_PACKAGE_VERSION = "1.0.0"
BASELINE_VERSION = "1.0.0"
MANIFEST_SCHEMA_VERSION = "1.0.0"  # JSON contract of manifest.json

# --- Independently-versioned platform components ----------------------------
CONNECTOR_REGISTRY_VERSION = "1.0.0"
MAPPER_VERSION = "1.0.0"
CONSOLIDATION_ENGINE_VERSION = "1.0.0"
PROMPT_FRAMEWORK_VERSION = "1.0.0"
LLM_FRAMEWORK_VERSION = "1.0.0"
ANALYSIS_SERVICE_VERSION = "1.0.0"
EXECUTION_WRITER_VERSION = "1.0.0"
PLATFORM_CAPABILITIES_VERSION = "1.0.0"

# --- Platform identity ------------------------------------------------------
PLATFORM_NAME = "Autonomous Test Engineering Platform"
PLATFORM_ARCHITECTURE = "Modular Monolith"
PLATFORM_EXECUTION_MODE = "Single Deployable Unit"


@dataclass(frozen=True)
class Capability:
    """An architecture capability, its display group, and availability."""

    name: str
    available: bool
    group: str = ""
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
# never hardcodes component status; it renders this list, grouped.
ARCHITECTURE_COMPONENTS: tuple[Capability, ...] = (
    Capability("Connector Registry", True, group="core"),
    Capability("Connectors", True, group="core"),
    Capability("Mappers", True, group="core"),
    Capability("Consolidation Engine", True, group="core"),
    Capability("Prompt Framework", True, group="ai"),
    Capability("LLM Framework", True, group="ai"),
    Capability("Gemini Provider", True, group="ai"),
    Capability("Requirement Analysis Service", True, group="ai"),
    Capability("Execution Package", True, group="execution"),
    Capability("Requirement Analysis CLI", True, group="execution"),
    Capability("Response Validator", False, group="future", note="Planned"),
    Capability("CP1 Validator", False, group="future", note="Planned"),
    Capability("Feature Generator", False, group="future", note="Planned"),
    Capability("Test Generator", False, group="future", note="Planned"),
)

# Ordered (group id, display title) pairs used to render grouped output.
COMPONENT_GROUPS: tuple[tuple[str, str], ...] = (
    ("core", "Core Platform"),
    ("ai", "AI Platform"),
    ("execution", "Execution Platform"),
    ("future", "Future Platform"),
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


__all__ = [
    "ANALYSIS_SERVICE_VERSION",
    "ARCHITECTURE_COMPONENTS",
    "BASELINE_VERSION",
    "CLI_COMMANDS",
    "CLI_VERSION",
    "COMPONENT_GROUPS",
    "CONNECTOR_REGISTRY_VERSION",
    "CONSOLIDATION_ENGINE_VERSION",
    "EXECUTION_PACKAGE_VERSION",
    "EXECUTION_WRITER_VERSION",
    "LLM_FRAMEWORK_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "MAPPER_VERSION",
    "PLATFORM_ARCHITECTURE",
    "PLATFORM_CAPABILITIES_VERSION",
    "PLATFORM_EXECUTION_MODE",
    "PLATFORM_NAME",
    "PLATFORM_VERSION",
    "PROMPT_FRAMEWORK_VERSION",
    "PROMPT_VERSION",
    "PROVIDERS",
    "REASONING_CONTRACT_VERSION",
    "Capability",
    "ProviderInfo",
    "supported_provider_ids",
]
