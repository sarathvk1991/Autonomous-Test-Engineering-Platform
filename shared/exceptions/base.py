"""Platform-wide exception hierarchy.

A single rooted hierarchy lets the API layer translate any domain failure into a
consistent HTTP response and lets every layer raise semantically meaningful
errors instead of bare ``Exception``. Subclass these in a layer when a more
specific error adds value.
"""

from __future__ import annotations


class PlatformError(Exception):
    """Base class for every error raised by the platform."""


class ConfigurationError(PlatformError):
    """Invalid, missing, or inconsistent configuration."""


# --- Connector / source-integration failures --------------------------------
class ConnectorError(PlatformError):
    """Base error for any source connector."""


class ConnectorAuthError(ConnectorError):
    """Authentication/authorisation against a source system failed."""


class ConnectorTimeoutError(ConnectorError):
    """A source system did not respond within the allotted time."""


class ConnectorResponseError(ConnectorError):
    """A source system returned an unexpected or malformed response."""


# --- Parsing / modelling ----------------------------------------------------
class ParserError(PlatformError):
    """Raw source payload could not be parsed into the canonical model."""


# --- AI provider ------------------------------------------------------------
class AIProviderError(PlatformError):
    """The Azure OpenAI provider returned an error or unusable result."""


# --- Validation (e.g. CP1 control point) ------------------------------------
class ValidationError(PlatformError):
    """A validation/quality-gate check failed."""
