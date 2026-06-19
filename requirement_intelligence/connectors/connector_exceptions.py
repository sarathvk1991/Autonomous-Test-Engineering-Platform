"""Custom exceptions for the Connector Framework.

This module defines typed exceptions raised by source connectors during
configuration validation, source availability checks, and raw data fetching.
"""


class ConnectorError(Exception):
    """Base exception for all connector-layer errors."""


class ConnectorConfigurationError(ConnectorError):
    """Raised when a connector is misconfigured.

    Examples:
        - Missing inputPath in FILE mode.
        - Missing baseUrl in API mode.
        - Unsupported inputMode.
        - Missing authentication configuration.
    """


class ConnectorConnectionError(ConnectorError):
    """Raised when a source cannot be reached or validated.

    Examples:
        - File does not exist.
        - File is not readable.
        - API endpoint is unavailable.
        - Authentication fails.
    """


class ConnectorFetchError(ConnectorError):
    """Raised when raw records cannot be fetched.

    Examples:
        - Invalid file read.
        - API request failure.
        - Permission denied.
        - Rate limit exceeded.
    """


class ConnectorParseError(ConnectorError):
    """Deprecated for connector layer.

    Parsing should be handled by parser classes. This exception is kept only for
    backward compatibility until parser-specific exceptions are introduced.
    """