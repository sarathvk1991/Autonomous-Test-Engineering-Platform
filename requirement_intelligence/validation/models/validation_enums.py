"""Enumerations for the Validation Canonical Models.

These three enums are the controlled vocabulary of the Response Validation
subsystem, as defined in ``docs/architecture/validation-canonical-models.md``
and ``docs/architecture/ai-response-validation.md``:

* :class:`ValidationSeverity` — how much an issue threatens trustworthiness.
* :class:`ValidationVerdict` — the single overall outcome of a validation run.
* :class:`ValidationHealth` — the derived qualitative read of a run.

Implementation decision
-----------------------
The platform already defines a ``ValidationVerdict`` in
``shared/enums/base.py`` with the values ``PASS`` / ``FAIL`` / ``WARN`` — that
enum belongs to the **CP1** quality gate and has different semantics.  The
Response Validation subsystem has a distinct four-state verdict
(``PASSED`` / ``PASSED_WITH_WARNINGS`` / ``FAILED`` / ``BLOCKED``).  To avoid
overloading one name with two meanings, the validation-subsystem enums live here
beside the canonical models they serve, keeping this vocabulary cohesive and
independently versionable.  This placement does not alter the governing
architecture.

Convention
----------
Like the platform's other enums (``shared/enums/base.py``) these are
``StrEnum``s with lowercase string values, so they serialise cleanly to
``camelCase`` JSON and to storage, and compare equal to their string value.
"""

from __future__ import annotations

from enum import StrEnum


class ValidationSeverity(StrEnum):
    """The degree to which a validation issue threatens trustworthiness.

    Ordered from least to most severe.  Severity is fixed at issue creation and
    drives the overall verdict (see :class:`ValidationVerdict`).
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationVerdict(StrEnum):
    """The single overall outcome of a validation run.

    Members
    -------
    PASSED
        No blocking concerns; output is trustworthy.
    PASSED_WITH_WARNINGS
        Output is trustworthy; non-blocking concerns were recorded.
    FAILED
        One or more ``ERROR`` issues; output is not trustworthy.
    BLOCKED
        One or more ``CRITICAL`` issues; output is unsafe to process.
    """

    PASSED = "passed"
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"
    BLOCKED = "blocked"


class ValidationHealth(StrEnum):
    """A derived qualitative read of a validation run, carried on the summary.

    Members
    -------
    HEALTHY
        No issues of concern.
    WARNING
        Only non-blocking warnings were observed.
    DEGRADED
        At least one error-level issue was observed.
    CRITICAL
        At least one critical issue was observed.
    """

    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
