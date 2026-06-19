"""OWASP ZAP source connector.

Fetches raw OWASP ZAP alerts from the configured source and returns them without
canonical transformation. Parsing is handled by the ZAP parser layer.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.connectors.base import SourceConnector


class ZapConnector(SourceConnector):
    """Connector for OWASP ZAP."""

    def get_source_id(self) -> str:
        """Returns the source identifier."""
        return "owasp_zap"

    def get_source_name(self) -> str:
        """Returns the source display name."""
        return "OWASP ZAP"

    def validate_connection(self) -> bool:
        """Validates OWASP ZAP source availability.

        For Phase 1 FILE mode, this should validate the configured alert file.
        For future API mode, this should validate ZAP API connectivity.
        """
        raise NotImplementedError

    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw OWASP ZAP alert records."""
        raise NotImplementedError

    def get_metadata(self) -> dict[str, Any]:
        """Returns OWASP ZAP connector metadata."""
        return {
            "sourceId": self.get_source_id(),
            "sourceName": self.get_source_name(),
            "schemaVersion": "1.0",
            "supportedInputModes": ["FILE", "API"],
            "supportedEntities": ["alerts", "findings"]
        }