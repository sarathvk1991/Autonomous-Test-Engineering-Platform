"""OWASP ZAP source connector.

Fetches security alerts/findings from an OWASP ZAP instance and returns raw
payloads for the ZAP parser to canonicalise. Logic deferred.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.connectors.base import SourceConnector


class ZapConnector(SourceConnector):
    """Connector for OWASP ZAP."""

    def get_source_id(self) -> str:
        """Returns a unique identifier for the source."""
        return "zap"

    def get_source_name(self) -> str:
        """Returns a human-readable name for the source."""
        return "OWASP ZAP"

    def connect(self) -> bool:
        """Establishes or validates connectivity with OWASP ZAP."""
        raise NotImplementedError

    def validate_connection(self) -> bool:
        """Performs health validation checks against OWASP ZAP."""
        raise NotImplementedError

    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw records from OWASP ZAP."""
        raise NotImplementedError

    def parse_records(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transforms OWASP ZAP records into common representation."""
        raise NotImplementedError

    def get_metadata(self) -> dict[str, Any]:
        """Returns metadata about the OWASP ZAP connector."""
        raise NotImplementedError
