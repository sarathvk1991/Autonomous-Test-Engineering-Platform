"""SonarQube source connector.

Fetches raw SonarQube issues from the configured source and returns them without
canonical transformation. Parsing is handled by the SonarQube parser layer.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.connectors.base import SourceConnector


class SonarQubeConnector(SourceConnector):
    """Connector for SonarQube."""

    def get_source_id(self) -> str:
        """Returns the source identifier."""
        return "sonarqube"

    def get_source_name(self) -> str:
        """Returns the source display name."""
        return "SonarQube"

    def validate_connection(self) -> bool:
        """Validates SonarQube source availability.

        For Phase 1 FILE mode, this should validate the configured issues file.
        For future API mode, this should validate SonarQube API connectivity.
        """
        raise NotImplementedError

    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw SonarQube issue records."""
        raise NotImplementedError

    def get_metadata(self) -> dict[str, Any]:
        """Returns SonarQube connector metadata."""
        return {
            "sourceId": self.get_source_id(),
            "sourceName": self.get_source_name(),
            "version": "1.0",
            "supportedInputModes": ["FILE", "API"],
            "supportedEntities": ["issues", "quality_gate", "measures"]
        }