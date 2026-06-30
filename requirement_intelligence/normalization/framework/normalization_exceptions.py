"""Custom exceptions for the Response Normalization Framework.

Hierarchy
---------
NormalizationFrameworkError
├── NormalizationPipelineError
├── NormalizationRegistryError
└── NormalizationResponsibilityError

Design notes
------------
These exceptions describe **framework-level failures** — problems with how the
normalization infrastructure is configured, assembled, or invoked.  They are
deliberately separate from Normalization Observations (which are not exceptions
but canonical facts produced when the framework operates normally).

A NormalizationFrameworkError means the framework itself could not perform its
work; it does **not** mean a response was judged in any way — normalization never
judges (Response Normalization Contract §10).

This hierarchy mirrors the Validation Framework's exception hierarchy
(``ValidationFrameworkError`` and its three subclasses) one-for-one, so the two
sibling subsystems fail in the same, predictable shape.
"""

from __future__ import annotations


class NormalizationFrameworkError(Exception):
    """Base exception for all Response Normalization Framework errors.

    Raise a subclass in preference to this class directly.  Catching
    ``NormalizationFrameworkError`` will catch all framework-level failures.
    """


class NormalizationPipelineError(NormalizationFrameworkError):
    """Raised when the normalization pipeline cannot be assembled or executed.

    Examples
    --------
    - A pipeline is constructed from something that is not a registry.
    - A responsibility raises an unexpected exception during execution.
    - The normalization input is missing.

    This exception does **not** represent a judged response; it represents a
    failure of the pipeline infrastructure itself.
    """


class NormalizationRegistryError(NormalizationFrameworkError):
    """Raised when the normalization registry cannot fulfil a request.

    Examples
    --------
    - A responsibility is registered with an ``id`` that is already present.
    - An attempt is made to register against a registry that has been sealed.

    This exception signals a programming error in how the framework is
    assembled, not a problem with any response being normalized.
    """


class NormalizationResponsibilityError(NormalizationFrameworkError):
    """Raised when a normalization responsibility is improperly defined or invoked.

    Examples
    --------
    - A responsibility implementation returns a type the pipeline cannot collect.
    - A responsibility raises an unhandled internal error during ``normalize()``.

    Responsibility authors should not raise this exception themselves; the
    pipeline raises it when a responsibility violates its contract.
    """
