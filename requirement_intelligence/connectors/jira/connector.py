"""Jira source connector.

Fetches issues/requirements from Jira via the infrastructure Jira client and
returns raw payloads for the Jira parser to canonicalise. Logic deferred.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.connectors.base import SourceConnector


class JiraConnector(SourceConnector):
    """Connector for Atlassian Jira."""

    def get_source_id(self) -> str:
        """Returns a unique identifier for the source."""
        return "jira"

    def get_source_name(self) -> str:
        """Returns a human-readable name for the source."""
        return "JIRA"

    def connect(self) -> bool:
        """Establishes or validates connectivity with JIRA."""
        raise NotImplementedError

    def validate_connection(self) -> bool:
        """Performs health validation checks against JIRA."""
        raise NotImplementedError

    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw records from JIRA."""
        raise NotImplementedError

    def parse_records(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transforms JIRA records into common representation."""
        raise NotImplementedError

    def get_metadata(self) -> dict[str, Any]:
        """Returns metadata about the JIRA connector."""
        raise NotImplementedError
