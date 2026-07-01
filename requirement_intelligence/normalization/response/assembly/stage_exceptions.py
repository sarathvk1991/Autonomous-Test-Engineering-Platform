"""Exceptions for the internal normalization stages of the ``ResponseNormalizer``.

Hierarchy
---------
::

    NormalizationStageError
    ├── StructureRecoveryError
    └── AssemblyStateError

Facts, not exceptions
---------------------
Per the Response Normalization Contract (§3.6, §10) and the Normalization Assembly
Contract (§8), a **malformed, empty, or unexpected** response is a **fact**, never
an exception.  A stage records that fact into the Assembly State (e.g. an absent
normalized structure); it does **not** raise.

These exceptions therefore describe **infrastructure failures only** — a stage (or
an injected collaborator) could not *perform its work*.  Raising one means the run
could not be conducted, never that a response was judged.  This mirrors the
framework's ``NormalizationFrameworkError`` discipline for the internal-stage
layer.
"""

from __future__ import annotations


class NormalizationStageError(Exception):
    """Base exception for all internal normalization-stage failures.

    Raise a subclass in preference to this class directly.  Catching
    ``NormalizationStageError`` catches every infrastructure failure raised by a
    stage or the Assembly State.  It is **never** raised for a normalization fact
    (a malformed/empty/unexpected response is recorded, not raised).
    """


class StructureRecoveryError(NormalizationStageError):
    """Raised when canonical-structure recovery fails for an *infrastructure* reason.

    This is **not** raised when no structure is present — that absence is a
    **fact** recorded into the Assembly State (Assembly Contract §8).  It is raised
    only when the recovery mechanism itself fails unexpectedly (for example, an
    injected ``CanonicalStructureRecoverer`` raises), so that an infrastructure
    failure never masquerades as a ``MALFORMED`` fact.
    """


class AssemblyStateError(NormalizationStageError):
    """Raised when the Assembly State is used in violation of its write contract.

    Example
    -------
    A stage attempts to record a fact it has already recorded (a duplicate write).
    Each owned fact is written **exactly once** (Assembly Contract §7); a second
    write is a programming error in stage coordination, not a normalization fact.
    """
