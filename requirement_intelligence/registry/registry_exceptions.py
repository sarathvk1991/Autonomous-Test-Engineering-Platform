"""Exceptions for the Connector Registry."""

class RegistryError(Exception):
    """Base class for all connector registry errors."""


class RegistryValidationError(RegistryError):
    """Raised when the registry configuration or source metadata fails validation."""
