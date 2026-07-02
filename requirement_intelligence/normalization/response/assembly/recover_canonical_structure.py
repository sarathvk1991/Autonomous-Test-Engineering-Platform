"""NORMALIZATION-0001 — Recover Canonical Structure.

The **first** internal stage of the ``ResponseNormalizer``.  It owns exactly one
concern: recovering the single, canonical, format-neutral structural
representation the response expresses, and recording it (or its absence) into the
Assembly State.

Responsibility Documentation Contract
-------------------------------------
1. **Purpose** — Recover the format-neutral normalized structure the response
   expresses, and record it (or its absence) as a fact.
2. **Catalog ID** — ``NORMALIZATION-0001`` (Normalization Responsibility Catalog
   §5; Response Normalization Contract §13).
3. **Inputs** — the ``LLMResponse``'s provider-independent ``generated_text``
   only.  (It is the first stage; it reads no earlier stage's fact.)
4. **Outputs** — the **Normalized Structure** fact written to the Assembly State:
   a format-neutral mapping when structure is recoverable, or ``None`` (a recorded
   absence) otherwise.
5. **Worked example** — a response expressing a document with an executive-summary
   object and a requirements array is recovered as format-neutral objects and
   arrays.  A response expressing no well-formed structure records an **absent**
   structure (``None``) — a fact NORMALIZATION-0002 later reads to determine a
   ``MALFORMED`` outcome.
6. **Architecture Reference** — ``docs/architecture/normalization-assembly-contract.md``
   §6 (NORMALIZATION-0001); ``docs/architecture/normalization-responsibility-catalog.md``
   §5; ADR-0002.

Single concern — what it never does
-----------------------------------
It **never** determines the outcome (``0002``), captures observations (``0003``),
creates the source reference (``0004``), assembles the ``ParsedResponse``
(``0005``), validates, repairs, judges, infers business meaning, mutates the
``LLMResponse``, or performs any downstream work.  Its single **owned** fact is the
normalized structure.  When its recovery mechanism additionally reports
duplicate-identifier **facts** (the optional ``DuplicateIdentifierReporter``
capability) or character-encoding integrity **facts** (the optional
``EncodingIntegrityReporter`` capability), the stage forwards them as **transient
execution facts** (Assembly Contract §4) for ``0003`` to turn into
``duplicate_identifier`` / ``encoding_observation`` observations — it never creates
the observations itself, and the forwarded facts are never an owned fact.

Format independence (Catalog §2.2, §3.4)
----------------------------------------
The stage never parses a serialization format itself.  It delegates recovery to an
injected
:class:`~requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer.CanonicalStructureRecoverer`,
so JSON, Markdown, XML, or any future representation is handled by a *recoverer*,
never by the stage.  New formats are new recoverers, added without changing this
stage.

Facts, not exceptions (Assembly Contract §8)
--------------------------------------------
A missing, empty, malformed, or unexpected response is a **fact** — recorded as an
absent (``None``) or as-recovered structure.  The stage raises
:class:`~requirement_intelligence.normalization.response.assembly.stage_exceptions.StructureRecoveryError`
**only** when the recovery mechanism itself fails for an infrastructure reason.
"""

from __future__ import annotations

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.response.assembly.assembly_state import (
    DUPLICATE_IDENTIFIERS_METADATA_KEY,
    ENCODING_OBSERVATIONS_METADATA_KEY,
    AssemblyState,
)
from requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer import (
    CanonicalStructureRecoverer,
    DuplicateIdentifierReporter,
    EncodingIntegrityReporter,
)
from requirement_intelligence.normalization.response.assembly.normalization_stage import (
    NormalizationStage,
)
from requirement_intelligence.normalization.response.assembly.normalization_stage_metadata import (
    NormalizationStageMetadata,
)
from requirement_intelligence.normalization.response.assembly.stage_exceptions import (
    StructureRecoveryError,
)

#: The immutable identity of NORMALIZATION-0001, constructed once and shared.
_METADATA = NormalizationStageMetadata(
    stage_id="NORMALIZATION-0001",
    stage_name="Recover Canonical Structure",
    order=1,
    documentation_reference=(
        "docs/architecture/normalization-assembly-contract.md#6-stage-contracts"
    ),
)


class RecoverCanonicalStructure(NormalizationStage):
    """NORMALIZATION-0001 — recover the response's canonical, format-neutral structure.

    The stage is assembled by **dependency injection** from a
    :class:`~requirement_intelligence.normalization.response.assembly.canonical_structure_recoverer.CanonicalStructureRecoverer`.
    The recoverer owns the format *mechanism*; the stage owns the *concern* of
    recovering structure and recording the fact.  This keeps the stage
    provider-independent, format-independent, and extensible (Catalog §2.2, §3.4).

    Parameters
    ----------
    recoverer:
        The injected collaborator that turns the response text into a format-neutral
        structure (or ``None`` when none is recoverable).

    Raises
    ------
    StructureRecoveryError
        At construction, if *recoverer* does not satisfy the
        :class:`CanonicalStructureRecoverer` protocol (an infrastructure /
        wiring error, never a normalization fact).
    """

    def __init__(self, recoverer: CanonicalStructureRecoverer) -> None:
        if not isinstance(recoverer, CanonicalStructureRecoverer):
            raise StructureRecoveryError(
                "RecoverCanonicalStructure requires a CanonicalStructureRecoverer; "
                f"got {type(recoverer).__name__!r}."
            )
        self._recoverer = recoverer

    @property
    def metadata(self) -> NormalizationStageMetadata:
        return _METADATA

    def execute(self, llm_response: LLMResponse, assembly_state: AssemblyState) -> None:
        """Recover the normalized structure and write it to *assembly_state*.

        Reads **only** ``llm_response.generated_text``; writes **only** the
        normalized structure.  A recovered structure and an absent structure
        (``None``) are both **facts**.  Only an infrastructure failure of the
        recovery mechanism raises.
        """
        text = llm_response.generated_text
        try:
            structure = self._recoverer.recover(text)
        except Exception as exc:
            # An infrastructure failure of the recovery mechanism — never a
            # normalization fact.  Absence of structure is returned as None above,
            # not raised here.
            raise StructureRecoveryError(
                f"Canonical-structure recovery failed for stage {self.stage_id!r}: {exc}"
            ) from exc

        # The Normalized Structure fact — a recovered mapping, or None (a recorded
        # absence).  Recorded exactly once; it is this stage's single OWNED fact.
        assembly_state.record_normalized_structure(structure)

        # Additionally forward any duplicate-identifier facts the recovery mechanism
        # reported, as a TRANSIENT execution fact (Assembly Contract §4) — never an
        # owned fact, never an observation.  Only when a structure was recovered (an
        # identifier can only be "duplicated within an object" if an object exists)
        # and only when the mechanism supports the optional reporting capability; a
        # mechanism that does not report duplicates leaves behaviour unchanged.
        if structure is not None and isinstance(self._recoverer, DuplicateIdentifierReporter):
            duplicate_identifiers = self._recoverer.duplicate_identifiers(text)
            if duplicate_identifiers:
                assembly_state.set_internal_metadata(
                    DUPLICATE_IDENTIFIERS_METADATA_KEY, duplicate_identifiers
                )

        # Likewise forward any character-encoding integrity facts as a TRANSIENT
        # execution fact.  Encoding integrity is a property of the decoded text and is
        # **independent of well-formedness**, so it is forwarded regardless of whether
        # a structure was recovered (a malformed response can still be corrupt).
        if isinstance(self._recoverer, EncodingIntegrityReporter):
            encoding_observations = self._recoverer.encoding_observations(text)
            if encoding_observations:
                assembly_state.set_internal_metadata(
                    ENCODING_OBSERVATIONS_METADATA_KEY, encoding_observations
                )
