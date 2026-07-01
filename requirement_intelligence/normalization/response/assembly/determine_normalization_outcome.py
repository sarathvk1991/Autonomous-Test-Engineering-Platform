"""NORMALIZATION-0002 — Determine Normalization Outcome.

The **second** internal stage of the ``ResponseNormalizer``.  It owns exactly one
concern: determining the single, provider-independent ``NormalizationOutcome`` from
the canonical structure NORMALIZATION-0001 already recovered, and recording it into
the Assembly State.

Responsibility Documentation Contract
-------------------------------------
1. **Purpose** — Determine the one provider-independent Normalization Outcome
   (``NORMALIZED`` / ``MALFORMED``) and record it as a fact.
2. **Catalog ID** — ``NORMALIZATION-0002`` (Normalization Responsibility Catalog
   §5; Response Normalization Contract §13).
3. **Inputs** — the result of structure recovery (``0001``), read from
   :attr:`~requirement_intelligence.normalization.response.assembly.assembly_state.AssemblyState.normalized_structure`.
4. **Outputs** — exactly one **Normalization Outcome** fact written to the Assembly
   State: ``NORMALIZED`` when a structure was recovered, ``MALFORMED`` when the
   structure is absent.
5. **Worked example** — when ``0001`` recovered a well-formed structure, ``0002``
   records ``NORMALIZED``; when ``0001`` recorded an absent structure, ``0002``
   records ``MALFORMED``.  The outcome is a **fact** a later consumer (the Syntax
   validation layer) may judge — ``0002`` never judges it.
6. **Architecture Reference** — ``docs/architecture/normalization-assembly-contract.md``
   §6 (NORMALIZATION-0002); ``docs/architecture/normalization-responsibility-catalog.md``
   §5; ADR-0002.

Single concern — what it never does
-----------------------------------
It answers **only** "was canonical structure successfully recovered?".  It **never**
determines quality, correctness, schema validity, business/semantic meaning,
reasoning quality, transport success, or validation success.  It never recovers
structure (``0001``), captures observations (``0003``), creates the source
reference (``0004``), assembles the ``ParsedResponse`` (``0005``), or produces a
verdict, severity, or recommendation.  It writes **only** the normalization outcome.

Why it has no injected collaborator
-----------------------------------
Unlike NORMALIZATION-0001 — which injects a ``CanonicalStructureRecoverer`` because
structure recovery is a format-specific *mechanism* — outcome determination has no
mechanism to vary: the rule is fixed and governed ("structure recovered ⇒
``NORMALIZED``; absent ⇒ ``MALFORMED``"), and the outcome set is **exactly two**
members whose growth is an ADR-gated architecture change (Catalog §5; Response
Normalization Contract §9).  Injecting a policy would be a speculative abstraction,
so this stage takes no dependency — the same ``NormalizationStage`` pattern as
``0001``, minus a mechanism it does not have.

Facts, not exceptions (Assembly Contract §8)
--------------------------------------------
``NORMALIZED`` and ``MALFORMED`` are **facts** — never exceptions.  The stage raises
:class:`~requirement_intelligence.normalization.response.assembly.stage_exceptions.OutcomeDeterminationError`
**only** for an infrastructure/ordering failure: it was invoked before
NORMALIZATION-0001 recorded the structure it depends on (Assembly Contract §7).
"""

from __future__ import annotations

from requirement_intelligence.llm.llm_models import LLMResponse
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
    OutcomeDeterminationError,
)
from shared.enums.base import NormalizationOutcome

#: The immutable identity of NORMALIZATION-0002, constructed once and shared.
_METADATA = NormalizationStageMetadata(
    stage_id="NORMALIZATION-0002",
    stage_name="Determine Normalization Outcome",
    order=2,
    documentation_reference=(
        "docs/architecture/normalization-assembly-contract.md#6-stage-contracts"
    ),
)


class DetermineNormalizationOutcome(NormalizationStage):
    """NORMALIZATION-0002 — determine the provider-independent normalization outcome.

    The stage takes **no injected collaborator**: the outcome rule is fixed and
    governed (Catalog §5).  It reads the structure recovered by ``0001`` from the
    Assembly State and records exactly one
    :class:`~shared.enums.base.NormalizationOutcome`.
    """

    @property
    def metadata(self) -> NormalizationStageMetadata:
        return _METADATA

    def execute(self, llm_response: LLMResponse, assembly_state: AssemblyState) -> None:
        """Determine the outcome from the recovered structure and record it.

        Reads **only** the normalized structure from *assembly_state*; writes
        **only** the normalization outcome.  ``NORMALIZED`` (structure present) and
        ``MALFORMED`` (structure absent) are both **facts**.  Determination does not
        read ``llm_response`` — the outcome is a function of ``0001``'s result alone
        (Catalog §5).

        Raises
        ------
        OutcomeDeterminationError
            If NORMALIZATION-0001 has not recorded the normalized structure yet
            (an ordering/coordination failure — Assembly Contract §7), which is an
            infrastructure error, never a ``MALFORMED`` fact.
        """
        if not assembly_state.normalized_structure_recorded:
            raise OutcomeDeterminationError(
                f"{self.stage_id!r} requires the normalized structure from "
                f"NORMALIZATION-0001 to be recorded first; the assembly chain must "
                f"execute 0001 before 0002 (Assembly Contract §7)."
            )

        # The Normalization Outcome fact: structure present ⇒ NORMALIZED; the
        # recorded absence of structure ⇒ MALFORMED. The stage judges nothing
        # beyond "was structure recovered?" and never invents a third outcome.
        outcome = (
            NormalizationOutcome.NORMALIZED
            if assembly_state.normalized_structure is not None
            else NormalizationOutcome.MALFORMED
        )
        assembly_state.record_normalization_outcome(outcome)
