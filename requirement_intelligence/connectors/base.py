"""Connector Framework — abstract base class for all source connectors.

Connectors are responsible only for validating source availability and fetching
raw records from an external/source system.

Parsing and canonical transformation must be handled by parser classes, not by
connectors.
"""

from abc import ABC, abstractmethod
from typing import Any


class SourceConnector(ABC):
    """Abstract base class for all source connectors.

    Concrete connectors such as JIRA, OWASP ZAP, and SonarQube must implement
    this contract.

    Responsibilities of a connector:
    - Identify the source.
    - Validate that the source is available/configured.
    - Fetch raw records from the source.

    Non-responsibilities:
    - Do not transform records into canonical format.
    - Do not apply business rules.
    - Do not perform requirement consolidation.
    """

    def __init__(self, source_config: dict[str, Any]) -> None:
        """Initializes the connector with source registry configuration.

        Args:
            source_config: Configuration entry from source-registry.json.
        """
        self.source_config = source_config

    @abstractmethod
    def get_source_id(self) -> str:
        """Returns the unique source identifier.

        Example:
            "jira", "owasp_zap", "sonarqube"

        Returns:
            str: Unique source identifier.
        """

    @abstractmethod
    def get_source_name(self) -> str:
        """Returns the human-readable source name.

        Example:
            "JIRA", "OWASP ZAP", "SonarQube"

        Returns:
            str: Human-readable source name.
        """

    @abstractmethod
    def validate_connection(self) -> bool:
        """Validates that the source is available and correctly configured.

        For FILE mode:
            - Validate file path exists.
            - Validate file is readable.
            - Validate expected file format.

        For API mode:
            - Validate endpoint availability.
            - Validate authentication.
            - Validate required permissions.

        Returns:
            bool: True if the source is valid and available.

        Raises:
            ConnectorConfigurationError: If configuration is invalid.
            ConnectorConnectionError: If the source is unavailable.
        """

    @abstractmethod
    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw records from the source.

        The returned data must remain source-specific and unmodified.
        Canonical transformation must be done by parser classes.

        Returns:
            list[dict[str, Any]]: Raw source records.

        Raises:
            ConnectorFetchError: If raw records cannot be fetched.
        """

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """Returns connector metadata.

        Example:
            {
                "sourceId": "jira",
                "sourceName": "JIRA",
                "inputMode": "FILE",
                "schemaVersion": "1.0"
            }

        Returns:
            dict[str, Any]: Connector metadata.
        """