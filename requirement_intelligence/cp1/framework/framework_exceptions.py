"""Custom exceptions for the CP1 engine framework.

Hierarchy
---------
CP1FrameworkError
├── CP1PipelineError
├── CP1RegistryError
└── CP1CriterionError

Design notes
------------
These exceptions describe **framework-level failures** — problems with how the CP1
infrastructure is configured, assembled, or invoked.  They are deliberately
separate from CP1 *findings* (which are not exceptions but canonical
:class:`~requirement_intelligence.cp1.models.cp1_finding.CP1Finding` objects produced
when the framework operates normally).

A ``CP1FrameworkError`` means the framework itself could not perform its work; it
does **not** mean that any requirement was judged not engineering-ready.  This
mirrors the Response Validation Framework's exception design exactly.
"""

from __future__ import annotations


class CP1FrameworkError(Exception):
    """Base exception for all CP1 engine framework errors.

    Raise a subclass in preference to this class directly.  Catching
    ``CP1FrameworkError`` will catch all framework-level failures.
    """


class CP1PipelineError(CP1FrameworkError):
    """Raised when the CP1 pipeline cannot be assembled or executed.

    This exception does **not** represent a not-ready requirement set; it
    represents a failure of the pipeline infrastructure itself (for example,
    constructing a pipeline from something that is not a registry).
    """


class CP1RegistryError(CP1FrameworkError):
    """Raised when the CP1 criterion registry cannot fulfil a request.

    Examples
    --------
    - A criterion is registered with a ``criterion_id`` that is already present.
    - An attempt is made to register into a registry that has been sealed.

    This signals a programming error in how the framework is assembled, not a
    problem with any requirement being assessed.
    """


class CP1CriterionError(CP1FrameworkError):
    """Raised when a CP1 criterion is improperly defined or invoked.

    Criterion authors should not raise this exception themselves; the framework
    raises it when a criterion violates its contract.
    """
