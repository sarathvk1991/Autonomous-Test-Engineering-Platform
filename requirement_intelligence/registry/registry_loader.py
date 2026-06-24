"""Loader for the source registry configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from requirement_intelligence.registry.registry_exceptions import RegistryValidationError


class RegistryLoader:
    """Loads and validates the source registry configuration."""

    def __init__(self, registry_path: Path | str | None = None) -> None:
        """Initializes the registry loader.

        Args:
            registry_path: Path to the source-registry.json file. Defaults to the
                standard location under requirement_intelligence/config/.
        """
        if registry_path is None:
            self.registry_path = Path(__file__).parent.parent / "config" / "source-registry.json"
        else:
            self.registry_path = Path(registry_path)

    def load_registry(self) -> dict[str, Any]:
        """Loads and parses the source registry JSON file.

        Returns:
            dict[str, Any]: The loaded registry configuration.

        Raises:
            RegistryValidationError: If the registry file cannot be found, read,
                or parsed as valid JSON.
        """
        if not self.registry_path.exists():
            raise RegistryValidationError(f"Registry file not found at: {self.registry_path}")
        
        try:
            with self.registry_path.open("r", encoding="utf-8") as handle:
                registry = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryValidationError(
                f"Failed to read or parse registry file at {self.registry_path}: {exc}"
            ) from exc

        self._validate_structure(registry)
        return registry

    def get_enabled_sources(self) -> list[dict[str, Any]]:
        """Loads the registry, filters for enabled sources, and sorts them by priority.

        Defaults from the registry are applied to each source configuration if they
        are missing.

        Returns:
            list[dict[str, Any]]: Enabled source configurations sorted by priority.
        """
        registry = self.load_registry()
        defaults = registry.get("defaults", {})
        enabled_sources = []

        for source in registry.get("sources", []):
            # Apply defaults to the source
            source_config = {**defaults, **source}
            
            # Ensure 'enabled' is boolean, evaluate truthiness
            if source_config.get("enabled", False):
                enabled_sources.append(source_config)

        # Sort by priority ascending (lower priority numbers run first)
        # Default priority to a high number (like 999) if missing
        enabled_sources.sort(key=lambda s: s.get("priority", 999))
        return enabled_sources

    def _validate_structure(self, registry: dict[str, Any]) -> None:
        """Validates the basic structure of the loaded registry.

        Args:
            registry: The parsed registry dictionary.

        Raises:
            RegistryValidationError: If the registry structure is invalid.
        """
        if not isinstance(registry, dict):
            raise RegistryValidationError("Registry must be a JSON object.")

        if "sources" not in registry:
            raise RegistryValidationError("Registry is missing the 'sources' list.")

        if not isinstance(registry["sources"], list):
            raise RegistryValidationError("'sources' key in registry must be a list.")

        defaults = registry.get("defaults", {})
        if not isinstance(defaults, dict):
            raise RegistryValidationError("'defaults' key in registry must be a JSON object.")

        for idx, source in enumerate(registry["sources"]):
            if not isinstance(source, dict):
                raise RegistryValidationError(f"Source at index {idx} must be a JSON object.")

            source_config = {**defaults, **source}

            # Required fields
            for field in ("sourceId", "connectorClass", "mapperClass"):
                val = source_config.get(field)
                if not val or not isinstance(val, str) or not val.strip():
                    raise RegistryValidationError(
                        f"Source at index {idx} is missing required string field: '{field}'"
                    )

            # Priority must be an integer if present
            priority = source_config.get("priority")
            if priority is not None and not isinstance(priority, int):
                raise RegistryValidationError(
                    f"Source '{source_config.get('sourceId')}' has non-integer priority: {priority}"
                )
