"""Loader for the source registry configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from requirement_intelligence.registry.execution_mode import resolve_execution_mode
from requirement_intelligence.registry.registry_exceptions import RegistryValidationError


class RegistryLoader:
    """Loads and validates the source registry configuration."""

    def __init__(
        self,
        registry_path: Path | str | None = None,
        execution_mode: str | None = None,
    ) -> None:
        """Initializes the registry loader.

        Args:
            registry_path: Path to the source-registry.json file. Defaults to the
                standard location under requirement_intelligence/config/.
            execution_mode: Ingestion mode ("FILE" or "API") to apply to every
                enabled source. Defaults to the canonical mode resolved from the
                ``EXECUTION_MODE`` environment variable.

        Raises:
            RegistryValidationError: If ``EXECUTION_MODE`` names an unsupported mode.
        """
        if registry_path is None:
            self.registry_path = Path(__file__).parent.parent / "config" / "source-registry.json"
        else:
            self.registry_path = Path(registry_path)

        self.execution_mode = execution_mode or resolve_execution_mode()

        # Caches the validated registry so the JSON file is read and parsed only once.
        self._registry_cache: dict[str, Any] | None = None

    def load_registry(self, force_reload: bool = False) -> dict[str, Any]:
        """Loads and parses the source registry JSON file.

        The registry is read, parsed, and validated on the first call and then
        cached. Subsequent calls return the cached registry without touching the
        filesystem, unless ``force_reload`` is set.

        Args:
            force_reload: If True, ignore the cache and re-read the file from disk.

        Returns:
            dict[str, Any]: The loaded registry configuration.

        Raises:
            RegistryValidationError: If the registry file cannot be found, read,
                or parsed as valid JSON.
        """
        if self._registry_cache is not None and not force_reload:
            return self._registry_cache

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
        self._registry_cache = registry
        return registry

    def get_enabled_sources(self) -> list[dict[str, Any]]:
        """Loads the registry, filters for enabled sources, and sorts them by priority.

        Defaults from the registry are applied to each source configuration if they
        are missing, and the canonical ``execution_mode`` is stamped onto every
        source as its ``inputMode``. This is the single point at which the global
        FILE/API selection reaches the connectors: each connector reads ``inputMode``
        from the configuration it is handed and never learns how the mode was chosen.

        Returns:
            list[dict[str, Any]]: Enabled source configurations sorted by priority.
        """
        registry = self.load_registry()
        defaults = registry.get("defaults", {})
        enabled_sources = []

        for source in registry.get("sources", []):
            # Apply defaults to the source, then impose the canonical execution mode.
            source_config = {**defaults, **source, "inputMode": self.execution_mode}

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
