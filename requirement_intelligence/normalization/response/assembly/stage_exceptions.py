"""Exceptions for the internal normalization stages of the ``ResponseNormalizer``.

Hierarchy
---------
::

    NormalizationStageError
    ├── StructureRecoveryError        (NORMALIZATION-0001 recovery-mechanism failure)
    ├── OutcomeDeterminationError     (NORMALIZATION-0002 ordering failure)
    ├── ObservationCaptureError       (NORMALIZATION-0003 ordering failure)
    ├── SourceReferenceCreationError  (NORMALIZATION-0004 reference-mechanism failure)
    ├── ParsedResponseAssemblyError   (NORMALIZATION-0005 ordering / misuse failure)
    ├── AssemblyStateError            (Assembly State write-contract violation)
    └── StageCoordinationError        (stage-coordinator wiring failure)

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


class OutcomeDeterminationError(NormalizationStageError):
    """Raised when the normalization outcome cannot be determined for an *infrastructure* reason.

    This is **not** raised when a response is malformed — a ``MALFORMED`` outcome is
    a **fact** recorded into the Assembly State (Assembly Contract §8).  It is raised
    only when NORMALIZATION-0002 runs without its required input — i.e. the
    normalized structure from NORMALIZATION-0001 has not been recorded — which is a
    coordination/ordering failure (Assembly Contract §7: ``0002`` never executes
    before ``0001``), never a normalization fact.
    """


class ObservationCaptureError(NormalizationStageError):
    """Raised when observations cannot be captured for an *infrastructure* reason.

    This is **not** raised for a malformed or empty response — recording a
    ``malformed_representation`` observation (or recording **no** observation at
    all) is a **fact**, and zero observations is a perfectly successful result
    (Assembly Contract §8; Response Normalization Contract §8).  It is raised only
    when NORMALIZATION-0003 runs without its required input — i.e. the normalized
    structure from NORMALIZATION-0001 has not been recorded — which is a
    coordination/ordering failure (Assembly Contract §7: ``0003`` never executes
    before ``0001``), never a normalization fact.
    """


class SourceReferenceCreationError(NormalizationStageError):
    """Raised when the source reference cannot be created for an *infrastructure* reason.

    This is **not** raised for a malformed or empty response — creating a source
    reference is a **fact** for every response (even an empty one has a stable
    content reference), never an exception (Assembly Contract §8; Response
    Normalization Contract §8).  NORMALIZATION-0004 depends on **no** prior stage
    (Catalog §5), so there is no ordering guard; this is raised only when the
    reference-creation mechanism itself fails unexpectedly — so that an
    infrastructure failure never masquerades as a normalization fact.
    """


class ParsedResponseAssemblyError(NormalizationStageError):
    """Raised when the ``ParsedResponse`` cannot be assembled for an *infrastructure* reason.

    This is **not** raised for a ``MALFORMED`` response — a ``MALFORMED`` outcome is
    a **fact**, and NORMALIZATION-0005 still assembles a ``ParsedResponse`` for it
    (with ``normalized_structure`` absent).  It is raised only when:

    * the stage is asked to assemble before its required inputs were recorded — the
      normalized structure (``0001``), the outcome (``0002``), or the source
      reference (``0004``) — a coordination/ordering failure (Assembly Contract §7
      invariant 2: ``0005`` never assembles without an outcome and a source
      reference); or
    * the write-loop ``execute`` is invoked on the assembling stage, whose product
      leaves the boundary through the coordinator's **consumer seam** (``assemble``),
      never through ``execute`` (Stage Implementation Contract §3.3, §7.2).

    Neither is a normalization fact.
    """


class AssemblyStateError(NormalizationStageError):
    """Raised when the Assembly State is used in violation of its write contract.

    Example
    -------
    A stage attempts to record a fact it has already recorded (a duplicate write).
    Each owned fact is written **exactly once** (Assembly Contract §7); a second
    write is a programming error in stage coordination, not a normalization fact.
    """


class StageCoordinationError(NormalizationStageError):
    """Raised when the internal stage coordinator is *assembled* incorrectly.

    Example
    -------
    The coordinator is constructed with an object that is not a
    :class:`~requirement_intelligence.normalization.response.assembly.normalization_stage.NormalizationStage`.

    This is a **wiring** error (a programming error in how the coordinator is
    assembled), never a normalization fact.  It is distinct from a stage's own
    infrastructure failure during execution, which propagates from the stage
    unchanged.
    """
