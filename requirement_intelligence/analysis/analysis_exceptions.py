"""Orchestration-level exceptions for the Requirement Analysis Service.

These exceptions describe failures in *coordinating* an AI analysis — never the
internals of a specific provider.  Provider-specific exceptions are caught inside
the service and re-raised as :class:`ProviderExecutionError`, so no provider
implementation detail leaks across the orchestration boundary.

Hierarchy
---------
AnalysisError
├── AnalysisConfigurationError
├── PromptGenerationError
├── ProviderExecutionError
└── AnalysisExecutionError
"""

from __future__ import annotations


class AnalysisError(Exception):
    """Base exception for all Requirement Analysis Service errors."""


class AnalysisConfigurationError(AnalysisError):
    """Raised when the service is misconfigured.

    Detected before any AI call is attempted.

    Examples
    --------
    - A required collaborator (prompt builder or provider) was not injected.
    - The reasoning contract version is missing or empty.
    """


class PromptGenerationError(AnalysisError):
    """Raised when a prompt cannot be produced for the supplied evidence.

    Covers both prompt construction and conversion into a provider-agnostic
    request.  Execution does not proceed when this is raised.
    """


class ProviderExecutionError(AnalysisError):
    """Raised when the AI provider fails to execute the request.

    Wraps any provider-specific failure (configuration, connection, generation)
    so that no provider exception type escapes the orchestration boundary.
    """


class AnalysisExecutionError(AnalysisError):
    """Raised for unexpected failures during orchestration.

    Used distinctly so an internal orchestration fault is never mistaken for a
    prompt-generation or provider fault.
    """
