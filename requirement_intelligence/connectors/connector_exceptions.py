"""Custom exceptions for the Connector Framework.

This module defines the hierarchy of exceptions raised by source connectors
during connectivity validation, record fetching, and data parsing.
"""


class ConnectorError(Exception):
    """Base exception for all errors that occur within the connector layer.

    All other custom connector exceptions inherit from this class. It can also
    be used directly for generic connector failures that do not fit into
    specific subclasses.
    """


class ConnectorConfigurationError(ConnectorError):
    """Exception raised when a connector is misconfigured.

    Examples:
        - Missing or invalid authentication credentials (API key, token, user/pass).
        - Missing, malformed, or unreachable source URL.
        - Invalid query parameters or settings in configuration.
    """


class ConnectorConnectionError(ConnectorError):
    """Exception raised when connection to the source system cannot be established or validated.

    Examples:
        - Network connection timeouts.
        - Host name resolution failures (DNS).
        - HTTP status codes representing service unavailability (e.g. 503).
    """


class ConnectorFetchError(ConnectorError):
    """Exception raised when a connector fails to retrieve raw data from the source system.

    Examples:
        - API rate limits exceeded (e.g. HTTP 429).
        - Permission denied/Unauthorized when fetching specific data (e.g. HTTP 403).
        - Server errors on specific requests (e.g. HTTP 500).
    """


class ConnectorParseError(ConnectorError):
    """Exception raised when a connector fails to transform raw data into the canonical format.

    Examples:
        - Malformed or unexpected response payloads (e.g. invalid JSON, XML,
          or missing required fields).
        - Data type mismatch during casting.
        - Schema validation errors on parsed records.
    """
