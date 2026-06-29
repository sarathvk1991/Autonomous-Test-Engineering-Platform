"""Platform Capabilities — the platform introspection model.

:class:`PlatformCapabilities` is the single place that answers "what is this
platform, what can it do, and what is it running on?". The ``version`` command
(and any future introspection consumer) reads from here instead of reaching into
many metadata constants directly.

It contains **no business logic** — every method only reports centrally-defined
metadata or read-only host facts.
"""

from __future__ import annotations

import platform as host_platform
from pathlib import Path

from requirement_intelligence.platform import platform_metadata as meta


class PlatformCapabilities:
    """Read-only introspection over platform metadata and host identity."""

    def platform_identity(self) -> dict[str, str]:
        """Return the platform name, architecture, and execution mode."""
        return {
            "name": meta.PLATFORM_NAME,
            "architecture": meta.PLATFORM_ARCHITECTURE,
            "executionMode": meta.PLATFORM_EXECUTION_MODE,
        }

    def platform_versions(self) -> dict[str, str]:
        """Return the platform-level version identifiers."""
        return {
            "platformVersion": meta.PLATFORM_VERSION,
            "cliVersion": meta.CLI_VERSION,
            "promptVersion": meta.PROMPT_VERSION,
            "reasoningContractVersion": meta.REASONING_CONTRACT_VERSION,
            "executionPackageVersion": meta.EXECUTION_PACKAGE_VERSION,
            "manifestSchemaVersion": meta.MANIFEST_SCHEMA_VERSION,
        }

    def architecture_components(self) -> tuple[meta.Capability, ...]:
        """Return every architecture capability."""
        return meta.ARCHITECTURE_COMPONENTS

    def implemented_components(self) -> tuple[meta.Capability, ...]:
        """Return capabilities that are available today."""
        return tuple(c for c in meta.ARCHITECTURE_COMPONENTS if c.available)

    def planned_components(self) -> tuple[meta.Capability, ...]:
        """Return capabilities reserved for a future phase."""
        return tuple(c for c in meta.ARCHITECTURE_COMPONENTS if not c.available)

    def component_groups(self) -> tuple[tuple[str, tuple[meta.Capability, ...]], ...]:
        """Return ordered ``(group title, components)`` pairs for display."""
        groups: list[tuple[str, tuple[meta.Capability, ...]]] = []
        for group_id, title in meta.COMPONENT_GROUPS:
            members = tuple(
                c for c in meta.ARCHITECTURE_COMPONENTS if c.group == group_id
            )
            groups.append((title, members))
        return tuple(groups)

    def providers(self) -> tuple[meta.ProviderInfo, ...]:
        """Return the provider catalogue."""
        return meta.PROVIDERS

    def supported_commands(self) -> tuple[str, ...]:
        """Return the registered CLI command names."""
        return meta.CLI_COMMANDS

    def system_identity(self) -> dict[str, str]:
        """Return read-only host facts (no sensitive information)."""
        return {
            "pythonVersion": host_platform.python_version(),
            "operatingSystem": f"{host_platform.system()} {host_platform.release()}",
            "platformArchitecture": host_platform.machine(),
            "currentWorkingDirectory": str(Path.cwd()),
        }
