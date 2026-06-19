"""SonarQube source connector.

Fetches code-quality issues / quality-gate findings from SonarQube and returns
raw payloads for the SonarQube parser to canonicalise. Logic deferred.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.connectors.base import SourceConnector


class SonarQubeConnector(SourceConnector):
    """Connector for SonarQube."""

    def get_source_id(self) -> str:
        """Returns a unique identifier for the source."""
        return "sonarqube"

    def get_source_name(self) -> str:
        """Returns a human-readable name for the source."""
        return "SonarQube"

    def connect(self) -> bool:
        """Establishes or validates connectivity with SonarQube."""
        raise NotImplementedError

    def validate_connection(self) -> bool:
        """Performs health validation checks against SonarQube."""
        raise NotImplementedError

    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw records from SonarQube."""
        raise NotImplementedError

    def parse_records(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transforms SonarQube records into common representation."""
        raise NotImplementedError

    def get_metadata(self) -> dict[str, Any]:
        """Returns metadata about the SonarQube connector."""
        raise NotImplementedError
