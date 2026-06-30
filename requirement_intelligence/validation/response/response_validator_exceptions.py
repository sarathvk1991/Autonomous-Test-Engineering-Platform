"""Exception hierarchy for the Response Validator orchestration layer.

Hierarchy
---------
ResponseValidatorError
├── ConfigurationResolutionError
├── ProfileResolutionError
├── PipelineConstructionError
└── ValidationExecutionError

Design notes
------------
These exceptions describe **orchestration-level failures** — problems the
Response Validator encounters while coordinating a validation run.  They are
deliberately distinct from two other things:

* **Framework exceptions** (``ValidationFrameworkError`` and its subclasses) —
  raised by the registry, pipeline, or a rule.  The Response Validator
  *translates* those into the exceptions here so that callers never depend on
  framework internals (see ``docs/architecture/response-validator.md`` §16).
* **Validation verdicts** — a ``FAILED`` or ``BLOCKED`` verdict is a normal,
  successful outcome carried by the ``ValidationResult``; it is **never** an
  exception.  A ``ResponseValidatorError`` means the run could not be conducted,
  not that the response was judged untrustworthy.
"""

from __future__ import annotations


class ResponseValidatorError(Exception):
    """Base exception for all Response Validator orchestration failures.

    Raise a subclass in preference to this class directly.  Catching
    ``ResponseValidatorError`` catches every orchestration-level failure and
    nothing from the validation framework, because framework exceptions are
    translated before they cross the orchestration boundary.
    """


class ConfigurationResolutionError(ResponseValidatorError):
    """Raised when a valid ``ValidationConfiguration`` cannot be resolved.

    Examples
    --------
    - The platform-default configuration is missing or of the wrong type.
    - The configuration hierarchy resolves to no usable configuration.

    This is a *configuration* failure detected before any pipeline executes; no
    validation is attempted.
    """


class ProfileResolutionError(ResponseValidatorError):
    """Raised when a Validation Profile cannot be resolved.

    Examples
    --------
    - A requested profile name does not correspond to a canonical profile.

    This is an orchestration failure: the run cannot proceed because the rule
    set to apply could not be selected.
    """


class PipelineConstructionError(ResponseValidatorError):
    """Raised when the registry or pipeline cannot be assembled.

    Examples
    --------
    - The Response Validator is constructed with a registry or pipeline that is
      not of the expected framework type.

    This signals a wiring error in how the validation subsystem is assembled,
    not a problem with any response being validated.
    """


class ValidationExecutionError(ResponseValidatorError):
    """Raised when the pipeline run fails at the orchestration boundary.

    The Response Validator translates any framework exception raised during
    ``ValidationPipeline.run`` — or any unexpected internal error during
    execution — into this exception, preserving the original as the cause.

    A ``ValidationExecutionError`` means the validation **could not be produced**.
    It is never used to report a ``FAILED`` or ``BLOCKED`` verdict, which are
    normal results carried by the ``ValidationResult``.
    """
