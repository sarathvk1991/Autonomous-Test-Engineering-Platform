"""Abstract base class for the internal normalization stages of the ``ResponseNormalizer``.

This module defines :class:`NormalizationStage` — the stable contract every
internal normalization stage (``NORMALIZATION-0001 … 0005``) implements.  It is the
**reference pattern** that every current and future stage follows, exactly as
``ValidationRule`` is the pattern for validation rules.

Where stages live (ADR-0002)
----------------------------
Per **ADR-0002**, these stages are **internal to the ``ResponseNormalizer``**, not
framework
:class:`~requirement_intelligence.normalization.framework.normalization_responsibility.NormalizationResponsibility`
instances.  They are coordinated within the ``ResponseNormalizer`` boundary through
a shared
:class:`~requirement_intelligence.normalization.response.assembly.assembly_state.AssemblyState`
(the Normalization Assembly Contract), and the generic framework never sees them.

What a stage is
---------------
A stage owns **exactly one** concern from the Normalization Responsibility Catalog
(§5).  It **reads** the ``LLMResponse`` and the facts already present in the
Assembly State, and **writes** its one owned fact back to the Assembly State.  It
records **facts**, never judgments; it never repairs, never validates, and never
mutates the ``LLMResponse``.

Stage Independence (Assembly Contract §6, §7)
---------------------------------------------
Every conforming stage must be:

1. **Single-concern** — it owns one fact and writes only that fact.
2. **Deterministic** — the same inputs always produce the same recorded fact.
3. **Non-mutating** — it never mutates the ``LLMResponse`` or another stage's fact.
4. **Forward-only** — it reads only facts produced by earlier stages, never later
   ones; the dependency graph stays acyclic.

These are structural requirements of the contract, not runtime-enforced.

Facts, not exceptions (Assembly Contract §8)
--------------------------------------------
A missing, malformed, or unexpected response is a **fact** the stage records into
the Assembly State — never an exception.  A stage raises
:class:`~requirement_intelligence.normalization.response.assembly.stage_exceptions.NormalizationStageError`
**only** for an infrastructure failure (the stage could not perform its work).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.response.assembly.assembly_state import (
    AssemblyState,
)
from requirement_intelligence.normalization.response.assembly.normalization_stage_metadata import (
    NormalizationStageMetadata,
)

__all__ = [
    "NormalizationStage",
    "NormalizationStageMetadata",
]


class NormalizationStage(ABC):
    """Abstract contract every internal normalization stage must satisfy.

    Adding a new stage
    ------------------
    1. Subclass :class:`NormalizationStage`.
    2. Implement :attr:`metadata` (an immutable
       :class:`~requirement_intelligence.normalization.response.assembly.normalization_stage_metadata.NormalizationStageMetadata`)
       and :meth:`execute`.
    3. Read only the ``LLMResponse`` and the Assembly State facts of *earlier*
       stages; write only this stage's one owned fact.

    No other change is required: the ``ResponseNormalizer`` coordinates the stages
    in catalog order (Assembly Contract §5), and the generic framework is unaware
    of them (ADR-0002).

    Identity comes from metadata
    ----------------------------
    A stage's descriptive identity lives in a single immutable
    :class:`NormalizationStageMetadata`, exposed through :attr:`metadata`.
    Convenience wrappers (:attr:`stage_id`, :attr:`stage_name`,
    :attr:`stage_version`, :attr:`order`, :attr:`enabled`) read from it.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def metadata(self) -> NormalizationStageMetadata:
        """Immutable descriptive identity of this stage.

        The single source of truth for ``stage_id``, ``stage_name``,
        ``stage_version``, ``order``, ``enabled``, and the reserved extension
        points.  Must be an immutable :class:`NormalizationStageMetadata`.
        """

    @property
    def stage_id(self) -> str:
        """Stable ``NORMALIZATION-NNNN`` identifier (reads :attr:`metadata`)."""
        return self.metadata.stage_id

    @property
    def stage_name(self) -> str:
        """Human-readable stage name (reads :attr:`metadata`)."""
        return self.metadata.stage_name

    @property
    def stage_version(self) -> str:
        """The version of this stage's logic (reads :attr:`metadata`)."""
        return self.metadata.stage_version

    @property
    def order(self) -> int:
        """The stage's declared position in the assembly chain (reads :attr:`metadata`)."""
        return self.metadata.order

    @property
    def enabled(self) -> bool:
        """Whether the stage participates in the assembly chain (reads :attr:`metadata`)."""
        return self.metadata.enabled

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    @abstractmethod
    def execute(self, llm_response: LLMResponse, assembly_state: AssemblyState) -> None:
        """Perform this stage's one concern, writing its owned fact to *assembly_state*.

        Parameters
        ----------
        llm_response:
            The provider-independent ``LLMResponse`` under normalization, treated as
            **read-only**.
        assembly_state:
            The transient
            :class:`~requirement_intelligence.normalization.response.assembly.assembly_state.AssemblyState`
            for this execution.  The stage reads the facts of *earlier* stages and
            writes its **one** owned fact.

        Returns
        -------
        None
            A stage communicates by writing to *assembly_state*, never by returning
            a value.

        Notes
        -----
        * **Records facts, never judgments** — no severity, verdict, or
          ``ValidationIssue`` (Contract §10).
        * **Never repairs** and **never mutates** *llm_response* or another stage's
          fact (Contract §3.2; Assembly Contract §7).
        * **Raises**
          :class:`~requirement_intelligence.normalization.response.assembly.stage_exceptions.NormalizationStageError`
          **only** for an infrastructure failure — a missing/malformed/unexpected
          response is recorded as a fact, never raised (Assembly Contract §8).
        """
