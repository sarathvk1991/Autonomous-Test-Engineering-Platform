"""Connector Registry — orchestrator for connector and mapper execution."""

from __future__ import annotations

import importlib
from typing import Any

from requirement_intelligence.models.source_artifact import SourceArtifact
from requirement_intelligence.registry.registry_exceptions import RegistryValidationError
from requirement_intelligence.registry.registry_loader import RegistryLoader


class ConnectorRegistry:
    """Orchestrates loading, validating, and executing source connectors and mappers."""

    def __init__(self, loader: RegistryLoader | None = None) -> None:
        """Initializes the connector registry and validates enabled sources.

        Args:
            loader: Registry loader instance. Defaults to loading from the standard location.

        Raises:
            RegistryValidationError: If any enabled source configuration fails metadata validation.
        """
        self.loader = loader or RegistryLoader()
        self._validate_enabled_sources()

    def _dynamic_load(self, class_path: str) -> type:
        """Dynamically imports and returns a class from a dot-separated path.

        Args:
            class_path: The fully-qualified class path.

        Returns:
            type: The loaded class.

        Raises:
            RegistryValidationError: If module loading or attribute retrieval fails.
        """
        if not class_path or not isinstance(class_path, str):
            raise RegistryValidationError(f"Invalid class path structure: {class_path}")

        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            return cls
        except (ValueError, ImportError, AttributeError) as exc:
            raise RegistryValidationError(
                f"Failed to dynamically load class '{class_path}': {exc}"
            ) from exc

    def create_connector(self, source_config: dict[str, Any]) -> Any:
        """Loads and instantiates the connector declared by *source_config*.

        The registry is the single owner of connector construction; callers that
        need a configured connector without executing it (metadata validation,
        health checks) obtain it here rather than importing connectors directly.

        Args:
            source_config: Configuration dict for a source.

        Returns:
            Any: The instantiated ``SourceConnector``.

        Raises:
            RegistryValidationError: If the class cannot be loaded or instantiated.
        """
        connector_class_path = source_config.get("connectorClass", "")
        connector_cls = self._dynamic_load(connector_class_path)
        try:
            return connector_cls(source_config)
        except Exception as exc:
            raise RegistryValidationError(
                f"Failed to instantiate connector '{connector_class_path}': {exc}"
            ) from exc

    def _validate_enabled_sources(self) -> None:
        """Validates metadata for all enabled sources at startup.

        Verifies that each connector's get_source_id() matches the registry sourceId.

        Raises:
            RegistryValidationError: If there is a sourceId mismatch or if the
                connector class cannot be loaded.
        """
        for source_config in self.loader.get_enabled_sources():
            connector_class_path = source_config.get("connectorClass", "")
            connector = self.create_connector(source_config)

            # Check get_source_id matches sourceId from registry
            registry_source_id = source_config.get("sourceId")
            connector_source_id = connector.get_source_id()
            if connector_source_id != registry_source_id:
                raise RegistryValidationError(
                    f"Metadata validation failed: registry sourceId '{registry_source_id}' "
                    f"does not match connector get_source_id() '{connector_source_id}' "
                    f"for class '{connector_class_path}'."
                )

            # TODO(phase-1): Once mappers expose metadata, validate that the mapper's
            # source system matches the sourceSystem/sourceId declared in the registry.
            # Do not implement mapper metadata methods or change the BaseMapper contract here.

    def execute_source(self, source_config: dict[str, Any]) -> list[SourceArtifact]:
        """Executes a single source configuration.

        Args:
            source_config: Configuration dict for a source.

        Returns:
            list[SourceArtifact]: Canonical SourceArtifacts resulting from execution.
        """
        mapper_class_path = source_config.get("mapperClass", "")
        mapper_cls = self._dynamic_load(mapper_class_path)

        # Instantiate the connector and execute
        connector = self.create_connector(source_config)
        connector.validate_connection()
        raw_records = connector.fetch_raw_records()

        # Instantiate the mapper and map
        try:
            mapper = mapper_cls()
        except Exception as exc:
            raise RegistryValidationError(
                f"Failed to instantiate mapper '{mapper_class_path}': {exc}"
            ) from exc

        artifacts = mapper.map(raw_records)
        return artifacts

    def execute_all(self) -> list[SourceArtifact]:
        """Loads and executes all enabled sources, returning a combined list of artifacts.

        Returns:
            list[SourceArtifact]: Canonical SourceArtifacts from all executed sources.
        """
        all_artifacts: list[SourceArtifact] = []
        for source_config in self.loader.get_enabled_sources():
            artifacts = self.execute_source(source_config)
            all_artifacts.extend(artifacts)
        return all_artifacts
