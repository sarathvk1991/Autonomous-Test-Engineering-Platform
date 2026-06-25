"""Exceptions for the Consolidation Engine."""

from __future__ import annotations


class ConsolidationError(Exception):
    """Base class for all consolidation errors."""


class ConsolidationInputError(ConsolidationError):
    """Raised when the input to the engine is not a valid list of SourceArtifacts."""
