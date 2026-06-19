"""Connector Framework — abstract base class for all source connectors.

This module defines the common SourceConnector contract that all external integration
connectors (such as JIRA, OWASP ZAP, SonarQube) must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class SourceConnector(ABC):
    """Abstract base class that defines the interface for all source connectors.

    Every source connector must extend this class and implement all its abstract
    methods to integrate with the Requirement Intelligence Layer.
    """

    @abstractmethod
    def get_source_id(self) -> str:
        """Returns a unique identifier for the source.

        Example:
            'jira', 'zap', 'sonarqube'

        Returns:
            str: The unique identifier.
        """

    @abstractmethod
    def get_source_name(self) -> str:
        """Returns a human-readable name for the source.

        Example:
            'JIRA', 'OWASP ZAP', 'SonarQube'

        Returns:
            str: The human-readable name.
        """

    @abstractmethod
    def connect(self) -> bool:
        """Establishes or validates connectivity with the source system.

        This method should verify that connectivity (authentication, network path,
        etc.) is operational and can be reused.

        Returns:
            bool: True if connection succeeds, False otherwise.
        """

    @abstractmethod
    def validate_connection(self) -> bool:
        """Performs health validation checks against the source.

        Checks if the source is reachable, authorized, and correctly configured.

        Returns:
            bool: True if source is reachable and configured correctly, False otherwise.
        """

    @abstractmethod
    def fetch_raw_records(self) -> list[dict[str, Any]]:
        """Fetches raw records from the source system.

        Example:
            JIRA issues, ZAP findings, SonarQube vulnerabilities.

        Returns:
            list[dict[str, Any]]: A list of raw records represented as dictionaries.
        """

    @abstractmethod
    def parse_records(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transforms raw source records into a common internal representation.

        Args:
            raw_records: A list of raw dictionaries retrieved from the source system.

        Returns:
            list[dict[str, Any]]: A list of parsed and standardized records.
        """

    @abstractmethod
    def get_metadata(self) -> dict[str, Any]:
        """Returns metadata about the connector.

        Example:
            {
                "source": "jira",
                "version": "1.0",
                "supported_entities": ["issues"]
            }

        Returns:
            dict[str, Any]: The connector metadata.
        """
