"""The Assembly State — transient collaboration medium for the normalization stages.

:class:`AssemblyState` realises the **Assembly State** governed by the
Normalization Assembly Contract (``docs/architecture/normalization-assembly-contract.md``).
It is the boundary-local medium through which the five internal
``ResponseNormalizer`` stages (``NORMALIZATION-0001 … 0005``) exchange their
intermediate facts during **one** normalization execution.

What it is — and is not (Assembly Contract §3)
----------------------------------------------
* **Not a canonical model.** It has no version, no shared identity, and no
  cross-platform contract.  It must never become one.
* **Mutable.** Unlike the ``ParsedResponse``, it is working memory: each stage
  appends its owned fact as execution proceeds.
* **Not shared / not stored / not returned.** It lives only inside the
  ``ResponseNormalizer`` boundary and is discarded after the final stage; no
  consumer, framework component, or downstream subsystem ever receives it.
* **Execution-local.** Exactly one Assembly State exists per execution.

Allowed contents (Assembly Contract §4)
---------------------------------------
Only the intermediate facts the stages need to collaborate, plus transient
bookkeeping: the **normalized structure** (``0001``), the **normalization
outcome** (``0002``), the **source reference** (``0004``), the transient
**observations** (``0003``, destined for the ``NormalizationResult``), and
free-form **internal metadata**.  It **never** holds a ``ParsedResponse``, a
``ValidationIssue``, severity, verdict, recommendation, statistics, execution
context, framework metadata, provider, or business information — each has exactly
one owner elsewhere.

Single-write discipline (Assembly Contract §7)
----------------------------------------------
Each *owned* fact (structure, outcome, source reference) is written **exactly
once**.  A second write raises
:class:`~requirement_intelligence.normalization.response.assembly.stage_exceptions.AssemblyStateError`
— a duplicate write is a coordination bug, not a normalization fact.  Observations
are an append-only collection.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.normalization.models.normalization_observation import (
    NormalizationObservation,
)
from requirement_intelligence.normalization.response.assembly.stage_exceptions import (
    AssemblyStateError,
)
from shared.enums.base import NormalizationOutcome

#: Internal-metadata key under which NORMALIZATION-0001 forwards the duplicate-key
#: **facts** its recovery mechanism reported, for NORMALIZATION-0003 to read and
#: turn into ``duplicate_identifier`` observations.  It names a **transient
#: execution fact** (Normalization Assembly Contract §4) — boundary-local
#: bookkeeping that never leaves the ``ResponseNormalizer`` boundary and is never a
#: canonical model, an owned fact, or an observation.
DUPLICATE_IDENTIFIERS_METADATA_KEY = "duplicate_identifiers"


class AssemblyState:
    """Transient, mutable, boundary-local medium for one normalization execution.

    Created when a normalization execution begins, written to by the stages in
    catalog order, and discarded after the final stage.  It is deliberately a
    plain mutable object — **not** an immutable :class:`~shared.contracts.base.Schema`
    — because it is working memory, never a canonical artifact (Assembly Contract
    §3).
    """

    def __init__(self) -> None:
        # --- Owned facts (each written exactly once) ----------------------
        self._normalized_structure: dict[str, Any] | None = None
        self._normalized_structure_recorded: bool = False

        self._normalization_outcome: NormalizationOutcome | None = None
        self._normalization_outcome_recorded: bool = False

        self._source_reference: str | None = None
        self._source_reference_recorded: bool = False

        # --- Transient facts / bookkeeping --------------------------------
        self._observations: list[NormalizationObservation] = []
        self._internal_metadata: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Normalized structure (owned by NORMALIZATION-0001)
    # ------------------------------------------------------------------

    def record_normalized_structure(self, structure: dict[str, Any] | None) -> None:
        """Record the normalized structure (or its absence) exactly once.

        Parameters
        ----------
        structure:
            The recovered format-neutral structure, or ``None`` when no structure
            was recoverable.  ``None`` is a **fact** (an absent structure), not an
            error.

        Raises
        ------
        AssemblyStateError
            If the normalized structure has already been recorded (Assembly
            Contract §7 — each owned fact is written exactly once).
        """
        if self._normalized_structure_recorded:
            raise AssemblyStateError(
                "The normalized structure has already been recorded; each owned "
                "fact is written exactly once (Assembly Contract §7)."
            )
        self._normalized_structure = structure
        self._normalized_structure_recorded = True

    @property
    def normalized_structure(self) -> dict[str, Any] | None:
        """The recorded normalized structure, or ``None`` (absent or not yet run)."""
        return self._normalized_structure

    @property
    def normalized_structure_recorded(self) -> bool:
        """``True`` once NORMALIZATION-0001 has recorded a structure (present or absent)."""
        return self._normalized_structure_recorded

    # ------------------------------------------------------------------
    # Normalization outcome (owned by NORMALIZATION-0002)
    # ------------------------------------------------------------------

    def record_normalization_outcome(self, outcome: NormalizationOutcome) -> None:
        """Record the normalization outcome exactly once.

        Raises
        ------
        AssemblyStateError
            If the outcome has already been recorded.
        """
        if self._normalization_outcome_recorded:
            raise AssemblyStateError(
                "The normalization outcome has already been recorded; each owned "
                "fact is written exactly once (Assembly Contract §7)."
            )
        self._normalization_outcome = outcome
        self._normalization_outcome_recorded = True

    @property
    def normalization_outcome(self) -> NormalizationOutcome | None:
        """The recorded normalization outcome, or ``None`` if not yet determined."""
        return self._normalization_outcome

    @property
    def normalization_outcome_recorded(self) -> bool:
        """``True`` once NORMALIZATION-0002 has recorded an outcome."""
        return self._normalization_outcome_recorded

    # ------------------------------------------------------------------
    # Source reference (owned by NORMALIZATION-0004)
    # ------------------------------------------------------------------

    def record_source_reference(self, source_reference: str) -> None:
        """Record the source reference exactly once.

        Raises
        ------
        AssemblyStateError
            If the source reference has already been recorded.
        """
        if self._source_reference_recorded:
            raise AssemblyStateError(
                "The source reference has already been recorded; each owned fact "
                "is written exactly once (Assembly Contract §7)."
            )
        self._source_reference = source_reference
        self._source_reference_recorded = True

    @property
    def source_reference(self) -> str | None:
        """The recorded source reference, or ``None`` if not yet created."""
        return self._source_reference

    @property
    def source_reference_recorded(self) -> bool:
        """``True`` once NORMALIZATION-0004 has recorded a source reference."""
        return self._source_reference_recorded

    # ------------------------------------------------------------------
    # Observations (owned by NORMALIZATION-0003; transient, append-only)
    # ------------------------------------------------------------------

    def add_observation(self, observation: NormalizationObservation) -> None:
        """Append one transient observation destined for the ``NormalizationResult``.

        Observations are an append-only collection — they are **never** carried on
        the ``ParsedResponse`` and are **never** read by NORMALIZATION-0005
        (Assembly Contract §5; Canonical Models §8.1).
        """
        self._observations.append(observation)

    @property
    def observations(self) -> tuple[NormalizationObservation, ...]:
        """The transient observations recorded so far, as an immutable snapshot."""
        return tuple(self._observations)

    # ------------------------------------------------------------------
    # Internal metadata (boundary-local bookkeeping)
    # ------------------------------------------------------------------

    def set_internal_metadata(self, key: str, value: Any) -> None:
        """Record a boundary-local bookkeeping value that never leaves the boundary."""
        self._internal_metadata[key] = value

    @property
    def internal_metadata(self) -> dict[str, Any]:
        """A snapshot of the boundary-local bookkeeping metadata."""
        return dict(self._internal_metadata)
