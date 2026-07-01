"""Exception hierarchy for the Response Normalizer orchestration layer.

Hierarchy
---------
NormalizationError
├── ConfigurationResolutionError
├── ProfileResolutionError
├── PipelineConstructionError
└── NormalizationExecutionError

Design notes
------------
These exceptions describe **orchestration-level failures** — problems the
Response Normalizer encounters while coordinating a normalization run.  They
mirror the Response Validator's orchestration exceptions one-for-one, so the two
sibling entry points fail in the same, predictable shape.  They are deliberately
distinct from two other things:

* **Framework exceptions** (``NormalizationFrameworkError`` and its subclasses) —
  raised by the registry, pipeline, or a responsibility.  The Response Normalizer
  *translates* those into the exceptions here so that callers never depend on
  framework internals (mirroring ``docs/architecture/response-validator.md`` §16).
* **Normalization facts** — a ``MALFORMED`` outcome or a recorded Normalization
  Observation is a normal, successful result carried by the
  ``NormalizationResult``; it is **never** an exception.  A ``NormalizationError``
  means the run could not be *conducted*, never that the response was judged
  (normalization never judges — Response Normalization Contract §10).
"""

from __future__ import annotations


class NormalizationError(Exception):
    """Base exception for all Response Normalizer orchestration failures.

    Raise a subclass in preference to this class directly.  Catching
    ``NormalizationError`` catches every orchestration-level failure and nothing
    from the normalization framework, because framework exceptions are translated
    before they cross the orchestration boundary.
    """


class ConfigurationResolutionError(NormalizationError):
    """Raised when a valid ``NormalizationConfiguration`` cannot be resolved.

    Examples
    --------
    - The platform-default configuration is missing or of the wrong type.
    - The configuration hierarchy resolves to no usable configuration.

    This is a *configuration* failure detected before any pipeline executes; no
    normalization is attempted.
    """


class ProfileResolutionError(NormalizationError):
    """Raised when a Normalization Profile cannot be resolved.

    Examples
    --------
    - A requested profile name does not correspond to a canonical profile.

    This is an orchestration failure: the run cannot proceed because the profile
    to apply could not be selected.
    """


class PipelineConstructionError(NormalizationError):
    """Raised when the registry or pipeline cannot be assembled.

    Examples
    --------
    - The Response Normalizer is constructed with a registry or pipeline that is
      not of the expected framework type.

    This signals a wiring error in how the normalization subsystem is assembled,
    not a problem with any response being normalized.
    """


class NormalizationExecutionError(NormalizationError):
    """Raised when the pipeline run fails at the orchestration boundary.

    The Response Normalizer translates any framework exception raised during
    ``NormalizationPipeline.run`` — or any unexpected internal error during
    execution — into this exception, preserving the original as the cause.

    A ``NormalizationExecutionError`` means the ``NormalizationResult`` **could
    not be produced**.  It is never used to report a ``MALFORMED`` outcome or an
    observation, which are normal facts carried by the ``NormalizationResult``.
    """
