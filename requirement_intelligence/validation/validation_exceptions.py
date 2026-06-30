"""Custom exceptions for the Response Validation Framework.

Hierarchy
---------
ValidationFrameworkError
├── ValidationPipelineError
├── ValidationRegistryError
└── ValidationRuleError

Design notes
------------
These exceptions describe **framework-level failures** — problems with how the
validation infrastructure is configured, assembled, or invoked.  They are
deliberately separate from validation *findings* (which are not exceptions but
canonical model objects produced when the framework operates normally).

A ValidationFrameworkError means the framework itself could not perform its
work; it does not mean that an AI response was judged untrustworthy.
"""

from __future__ import annotations


class ValidationFrameworkError(Exception):
    """Base exception for all Response Validation Framework errors.

    Raise a subclass in preference to this class directly.  Catching
    ``ValidationFrameworkError`` will catch all framework-level failures.
    """


class ValidationPipelineError(ValidationFrameworkError):
    """Raised when the validation pipeline cannot be assembled or executed.

    Examples
    --------
    - A pipeline is constructed with no rules registered.
    - A rule raises an unexpected exception during pipeline execution.
    - Pipeline configuration is contradictory or incomplete.

    This exception does **not** represent a failed AI response; it represents
    a failure of the pipeline infrastructure itself.
    """


class ValidationRegistryError(ValidationFrameworkError):
    """Raised when the validation registry cannot fulfil a request.

    Examples
    --------
    - A rule is registered with a ``rule_id`` that is already present.
    - A registry lookup fails because the requested layer is unknown.
    - An attempt is made to mutate a registry that has been sealed.

    This exception signals a programming error in how the validation framework
    is assembled, not a problem with any AI response being validated.
    """


class ValidationRuleError(ValidationFrameworkError):
    """Raised when a validation rule is improperly defined or invoked.

    Examples
    --------
    - A rule implementation returns a type that the pipeline cannot collect.
    - A rule raises an unhandled internal error during ``validate()``.
    - A rule's ``rule_id`` or ``validation_layer`` is malformed.

    Rule authors should not raise this exception themselves; the pipeline
    raises it when a rule violates its contract.
    """
