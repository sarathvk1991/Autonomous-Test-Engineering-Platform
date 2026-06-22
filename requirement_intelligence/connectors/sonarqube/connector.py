"""SonarQube source connector.

Fetches raw SonarQube issues from the configured source and returns them without
canonical transformation. Parsing is handled by the SonarQube parser layer.

The connector supports two input modes selected via ``inputMode`` in
source-registry.json:

- FILE: the current Phase 1 implementation path (reads ``inputPath``).
- API: the planned Phase 1 end-state (currently stubbed).

Downstream layers must not depend on which mode produced the records.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.connectors import connector_io
from requirement_intelligence.connectors.base import SourceConnector
from requirement_intelligence.connectors.connector_exceptions import (
    ConnectorConfigurationError,
)


class SonarQubeConnector(SourceConnector):
    """Connector for SonarQube."""

    def get_source_id(self) -> str:
        """Returns the source identifier."""
        return "sonarqube"

    def get_source_name(self) -> str:
        """Returns the source display name."""
        return "SonarQube"

    def validate_connection(self) -> bool:
        """Validates SonarQube source availability for the configured input mode.

        FILE mode validates that the configured ``inputPath`` exists and is
        readable. API mode validates that required connection fields are
        present (the actual API ping is stubbed for later in Phase 1).

        Raises:
            ConnectorConfigurationError: If ``inputMode`` is invalid/missing.
            ConnectorConnectionError: If the source is unavailable.
        """
        mode = connector_io.get_input_mode(self.source_config)
        if mode == connector_io.FILE_MODE:
            return connector_io.validate_input_file(self.source_config)
        if mode == connector_io.API_MODE:
            return connector_io.validate_api_config(self.source_config)
        raise ConnectorConfigurationError(
            f"Unsupported inputMode '{mode}' for SonarQube connector. "
            f"Expected one of {connector_io.SUPPORTED_INPUT_MODES}."
        )

    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw SonarQube issue records for the configured input mode.

        Raises:
            ConnectorConfigurationError: If ``inputMode`` is invalid/missing.
            ConnectorConnectionError: If the source is unavailable.
            ConnectorFetchError: If raw records cannot be fetched.
        """
        mode = connector_io.get_input_mode(self.source_config)
        if mode == connector_io.FILE_MODE:
            return self._fetch_from_file()
        if mode == connector_io.API_MODE:
            return self._fetch_from_api()
        raise ConnectorConfigurationError(
            f"Unsupported inputMode '{mode}' for SonarQube connector. "
            f"Expected one of {connector_io.SUPPORTED_INPUT_MODES}."
        )

    def _fetch_from_file(self) -> list[dict[str, Any]]:
        """Reads raw SonarQube records from the configured ``inputPath``."""
        return connector_io.read_json_records(self.source_config)

    def _fetch_from_api(self) -> list[dict[str, Any]]:
        """Fetches raw SonarQube records from the SonarQube API.

        Raises:
            NotImplementedError: Always, until API-mode ingestion is delivered
                later in Phase 1.
        """
        raise NotImplementedError(
            "SonarQube API-mode ingestion is not yet implemented. It is planned "
            "for the Phase 1 end-state; use FILE mode for now."
        )

    def get_metadata(self) -> dict[str, Any]:
        """Returns SonarQube connector metadata."""
        return {
            "sourceId": self.get_source_id(),
            "sourceName": self.get_source_name(),
            "schemaVersion": "1.0",
            "supportedInputModes": ["FILE", "API"],
            "supportedEntities": ["issues", "quality_gate", "measures"],
        }
