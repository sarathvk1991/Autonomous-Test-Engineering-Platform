"""NORMALIZATION-0005 — Assemble ParsedResponse.

The **fifth and final** internal stage of the ``ResponseNormalizer``.  It owns
exactly one concern: assembling the single, immutable, shared ``ParsedResponse``
from the finalized facts the earlier stages produced — and **nothing else**.

Responsibility Documentation Contract
-------------------------------------
1. **Purpose** — Compose the immutable ``ParsedResponse`` from the facts already in
   the Assembly State; add no meaning of its own.
2. **Catalog ID** — ``NORMALIZATION-0005`` (Normalization Responsibility Catalog
   §5; Response Normalization Contract §13).
3. **Inputs** — the **Normalized Structure** (``0001``), the **Normalization
   Outcome** (``0002``), and the **Source Reference** (``0004``), read from the
   Assembly State.  It **never** reads the observations (``0003``) — they are
   aggregated by the ``NormalizationResult``, never carried on the ``ParsedResponse``
   (Assembly Contract §6, §7 invariant 3; Canonical Models §8.1).
4. **Output** — exactly one immutable ``ParsedResponse``, handed **out of the
   boundary** through the coordinator's consumer seam; **nothing** is written back
   into the Assembly State (Assembly Contract §6; Stage Implementation Contract
   §7.2).
5. **Worked example** — with the structure recovered, the outcome determined, and
   the source reference created, ``0005`` composes them — with the representation's
   version — into one immutable ``ParsedResponse``.  It adds no meaning: it composes
   existing facts into the canonical shape and freezes it.
6. **Architecture Reference** — ``docs/architecture/normalization-assembly-contract.md``
   §6 (NORMALIZATION-0005); ``docs/architecture/normalization-responsibility-catalog.md``
   §5; ``docs/architecture/normalization-stage-implementation-contract.md``; ADR-0002.

Assembly is composition, never interpretation
---------------------------------------------
``0005`` **owns no fact** — it owns the *assembly*.  It composes the facts produced
by ``0001``, ``0002``, and ``0004``; it never re-derives, enriches, judges, repairs,
or interprets them (Catalog §5; Stage Implementation Contract §5).

The one designed asymmetry — output via the consumer seam
---------------------------------------------------------
Unlike the writing stages (``0001`` through ``0004``), the assembling stage does **not**
write its product back into the Assembly State — the Assembly State never contains a
``ParsedResponse`` (Assembly Contract §4, §7 invariant 12).  Its product is an
**output handed out of the boundary** through the coordinator's **consumer seam**:
the coordinator runs stages ``0001`` through ``0004`` and then calls :meth:`assemble` as its
consumer, which reads the finalized state and returns the immutable
``ParsedResponse`` (Stage Implementation Contract §3.3, §7.2, §13 pattern 11).  The
write-loop :meth:`execute` is therefore **not** this stage's path and is never
invoked on it.

Representation version and metadata
-----------------------------------
``parsed_response_version`` is owned by the ``ParsedResponse`` model as its single
source of truth; ``0005`` lets it take the model's canonical default rather than
re-specifying it.  ``metadata`` is the representation's own free-form metadata; the
current chain produces none, and the Assembly State's only metadata is
**boundary-local** internal bookkeeping that must never leave the boundary (Assembly
Contract §4), so it is **never** copied onto the ``ParsedResponse`` — ``metadata``
stays the model's canonical default (an empty mapping).

Single concern — what it never does
-----------------------------------
It **never** recovers structure (``0001``), determines the outcome (``0002``),
captures observations (``0003``), creates the source reference (``0004``),
validates, judges, repairs, coordinates stages, catches stage exceptions, mutates
the Assembly State, mutates the ``LLMResponse``, or mutates the ``ParsedResponse``
after construction.  It only composes and freezes.

Facts, not exceptions (Assembly Contract §8)
--------------------------------------------
A ``MALFORMED`` outcome is a **fact**: ``0005`` still assembles a ``ParsedResponse``
(with ``normalized_structure`` absent).  The stage raises
:class:`~requirement_intelligence.normalization.response.assembly.stage_exceptions.ParsedResponseAssemblyError`
**only** for an ordering/coordination failure (a required input was not recorded) or
the misuse of :meth:`execute` — never for a malformed response.
"""

from __future__ import annotations

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.models.parsed_response import ParsedResponse
from requirement_intelligence.normalization.response.assembly.assembly_state import (
    AssemblyState,
)
from requirement_intelligence.normalization.response.assembly.normalization_stage import (
    NormalizationStage,
)
from requirement_intelligence.normalization.response.assembly.normalization_stage_metadata import (
    NormalizationStageMetadata,
)
from requirement_intelligence.normalization.response.assembly.stage_exceptions import (
    ParsedResponseAssemblyError,
)

#: The immutable identity of NORMALIZATION-0005, constructed once and shared.
_METADATA = NormalizationStageMetadata(
    stage_id="NORMALIZATION-0005",
    stage_name="Assemble ParsedResponse",
    order=5,
    documentation_reference=(
        "docs/architecture/normalization-assembly-contract.md#6-stage-contracts"
    ),
)


class AssembleParsedResponse(NormalizationStage):
    """NORMALIZATION-0005 — assemble the immutable ``ParsedResponse`` from finalized facts.

    The stage takes **no injected collaborator**: assembly is pure composition of
    already-produced facts, with no varying mechanism (Stage Implementation Contract
    §9.2).  Its product leaves the boundary through :meth:`assemble` (the
    coordinator's consumer seam), never through the write-loop :meth:`execute`.
    """

    @property
    def metadata(self) -> NormalizationStageMetadata:
        return _METADATA

    def assemble(self, assembly_state: AssemblyState) -> ParsedResponse:
        """Compose the immutable ``ParsedResponse`` from *assembly_state* and return it.

        This is the coordinator's **consumer** for the normalization chain: it reads
        the finalized structure (``0001``), outcome (``0002``), and source reference
        (``0004``), and returns exactly one immutable ``ParsedResponse``.  It reads
        **no** observations (``0003``), writes **nothing** back into *assembly_state*,
        and mutates nothing.

        Raises
        ------
        ParsedResponseAssemblyError
            If a required input was not recorded first — the normalized structure
            (``0001``), the outcome (``0002``), or the source reference (``0004``) —
            an ordering/coordination failure (Assembly Contract §7 invariant 2),
            never a normalization fact.
        """
        if not assembly_state.normalized_structure_recorded:
            raise ParsedResponseAssemblyError(
                f"{_METADATA.stage_id!r} requires the normalized structure from "
                f"NORMALIZATION-0001 to be recorded before assembly (Assembly "
                f"Contract §7)."
            )
        if not assembly_state.normalization_outcome_recorded:
            raise ParsedResponseAssemblyError(
                f"{_METADATA.stage_id!r} requires the normalization outcome from "
                f"NORMALIZATION-0002 to be recorded before assembly (Assembly "
                f"Contract §7 invariant 2)."
            )
        if not assembly_state.source_reference_recorded:
            raise ParsedResponseAssemblyError(
                f"{_METADATA.stage_id!r} requires the source reference from "
                f"NORMALIZATION-0004 to be recorded before assembly (Assembly "
                f"Contract §7 invariant 2)."
            )

        # Pure composition of finalized facts into the canonical shape, then frozen.
        # parsed_response_version and metadata take the model's canonical defaults
        # (the model owns the version; the current chain produces no representation
        # metadata, and boundary-local internal metadata must never leak — Assembly
        # Contract §4).  Observations (0003) are deliberately never read.
        return ParsedResponse(
            normalization_outcome=assembly_state.normalization_outcome,
            normalized_structure=assembly_state.normalized_structure,
            source_reference=assembly_state.source_reference,
        )

    def execute(self, llm_response: LLMResponse, assembly_state: AssemblyState) -> None:
        """Not the assembling stage's path — raises to prevent misuse.

        The assembling stage produces an **output** that leaves the boundary through
        the coordinator's consumer seam (:meth:`assemble`), not a fact written into
        the Assembly State.  Placing ``0005`` in the coordinator's write-loop would
        discard its product, so ``execute`` is never a valid invocation on this stage
        (Stage Implementation Contract §3.3, §7.2, §13 pattern 11).
        """
        raise ParsedResponseAssemblyError(
            f"{_METADATA.stage_id!r} is the terminal assembling stage: assemble the "
            f"ParsedResponse through the coordinator's consumer seam by calling "
            f"'assemble', not through the write-loop 'execute' (Stage Implementation "
            f"Contract §3.3, §7.2)."
        )
