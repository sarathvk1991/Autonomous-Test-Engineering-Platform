"""NORMALIZATION-0003 — Capture Normalization Observations.

The **third** internal stage of the ``ResponseNormalizer``.  It owns exactly one
concern: capturing the recorded, un-judged ``NormalizationObservation`` facts that
a structural view alone would lose, and appending them to the Assembly State's
transient observation collection — the facts the ``NormalizationResult`` (never the
``ParsedResponse``) will carry.

Responsibility Documentation Contract
-------------------------------------
1. **Purpose** — Capture zero or more ``NormalizationObservation`` facts about the
   run, and append them to the Assembly State for the ``NormalizationResult`` to
   aggregate.
2. **Catalog ID** — ``NORMALIZATION-0003`` (Normalization Responsibility Catalog
   §5; Response Normalization Contract §13).
3. **Inputs** — the result of structure recovery (``0001``), read from
   :attr:`~requirement_intelligence.normalization.response.assembly.assembly_state.AssemblyState.normalized_structure`;
   the determined outcome (``0002``) is read, when present, only as corroborating
   **evidence** for a recorded observation — never as the decision that a fact
   exists (that is derived from ``0001``'s recovery result, this stage's frozen
   dependency — Catalog §5; Assembly Contract §6).
4. **Outputs** — zero or more **Normalization Observations** appended to the
   Assembly State's transient observation collection.  The observations are owned
   by the ``NormalizationResult``; they are **never** carried on the
   ``ParsedResponse`` and are **never** read by NORMALIZATION-0005 (Assembly
   Contract §5, §6; Validation Canonical Models §8.1).
5. **Worked example** — when ``0001`` recorded an **absent** structure, ``0003``
   records one ``malformed_representation`` observation stating *that* the response
   expressed no recoverable well-formed structure (Response Normalization Contract
   §8).  When ``0001`` recovered a structure, ``0003`` records **zero** observations
   — nothing a structural view would lose is derivable from the recovered structure
   alone at this stage — and that is a fully successful result.
6. **Architecture Reference** — ``docs/architecture/normalization-assembly-contract.md``
   §6 (NORMALIZATION-0003); ``docs/architecture/normalization-responsibility-catalog.md``
   §5; ``docs/architecture/normalization-stage-implementation-contract.md``; ADR-0002.

Facts, never judgments (Response Normalization Contract §8, §10)
---------------------------------------------------------------
An observation is a **fact**.  It carries **no severity, no verdict, no
recommendation, and no blocking indicator** — those are validation judgments across
the frozen §10 boundary.  A later validation rule may *read* an observation and
*decide* to raise a ``ValidationIssue``; that decision belongs entirely to
validation.  A ``NormalizationObservation`` is **never itself** a ``ValidationIssue``.

Single concern — what it never does
-----------------------------------
It **never** recovers structure (``0001``), determines the outcome (``0002``),
creates the source reference (``0004``), assembles the ``ParsedResponse``
(``0005``), validates, judges, repairs, coordinates, or mutates the ``LLMResponse``.
It writes **only** observations.

Why it has no injected collaborator
-----------------------------------
Like NORMALIZATION-0002 — and unlike NORMALIZATION-0001 — this stage takes **no**
injected collaborator: the facts it records are fixed by architecture (Response
Normalization Contract §8), so there is no varying *mechanism* to inject.  The
observation identifier is derived deterministically from the stage's identity, and
the timestamp is taken from the platform's shared clock helper, exactly as the
frozen validation subsystem stamps a ``ValidationIssue``'s ``created_at`` — no
speculative time/identity abstraction is introduced (Stage Implementation Contract
§9.2).

Determinism (Stage Implementation Contract §4)
----------------------------------------------
The **semantic content** of every observation — which observations are recorded,
their type, and their detail — is a deterministic function of the upstream facts.
The observation's identity and timestamp are run-scoped **execution metadata**
carried by the ``NormalizationResult`` (an execution fact about the run), not part
of the deterministic canonical ``ParsedResponse`` — so stamping ``created_at`` from
the shared clock is consistent with determinism, exactly as it is for a
``ValidationIssue``.

Facts, not exceptions (Assembly Contract §8)
--------------------------------------------
Recording a ``malformed_representation`` observation — or recording **no**
observation at all — is a **fact**; zero observations is a successful result.  The
stage raises
:class:`~requirement_intelligence.normalization.response.assembly.stage_exceptions.ObservationCaptureError`
**only** for an infrastructure/ordering failure: it was invoked before
NORMALIZATION-0001 recorded the structure it depends on (Assembly Contract §7).
"""

from __future__ import annotations

from requirement_intelligence.llm.llm_models import LLMResponse
from requirement_intelligence.normalization.models.normalization_observation import (
    OBSERVATION_DUPLICATE_IDENTIFIER,
    OBSERVATION_ENCODING,
    OBSERVATION_MALFORMED_REPRESENTATION,
    NormalizationObservation,
)
from requirement_intelligence.normalization.response.assembly.assembly_state import (
    DUPLICATE_IDENTIFIERS_METADATA_KEY,
    ENCODING_OBSERVATIONS_METADATA_KEY,
    AssemblyState,
)
from requirement_intelligence.normalization.response.assembly.normalization_stage import (
    NormalizationStage,
)
from requirement_intelligence.normalization.response.assembly.normalization_stage_metadata import (
    NormalizationStageMetadata,
)
from requirement_intelligence.normalization.response.assembly.stage_exceptions import (
    ObservationCaptureError,
)
from shared.utils.ids import utc_now

#: The immutable identity of NORMALIZATION-0003, constructed once and shared.
_METADATA = NormalizationStageMetadata(
    stage_id="NORMALIZATION-0003",
    stage_name="Capture Normalization Observations",
    order=3,
    documentation_reference=(
        "docs/architecture/normalization-assembly-contract.md#6-stage-contracts"
    ),
)


class CaptureNormalizationObservations(NormalizationStage):
    """NORMALIZATION-0003 — capture the run's un-judged normalization observations.

    The stage takes **no injected collaborator**: the facts it records are fixed by
    architecture (Response Normalization Contract §8).  It reads the structure
    recovered by ``0001`` from the Assembly State and appends zero or more
    :class:`~requirement_intelligence.normalization.models.normalization_observation.NormalizationObservation`
    facts to the transient observation collection destined for the
    ``NormalizationResult``.
    """

    @property
    def metadata(self) -> NormalizationStageMetadata:
        return _METADATA

    def execute(self, llm_response: LLMResponse, assembly_state: AssemblyState) -> None:
        """Capture the run's observations and append them to *assembly_state*.

        Reads the normalized structure recovered by ``0001`` (this stage's frozen
        dependency), the outcome determined by ``0002`` (read, when present, only as
        corroborating evidence), and the duplicate-identifier **facts** forwarded by
        ``0001`` as a transient execution fact; writes **only** observations,
        appended to the transient collection.  Recording a
        ``malformed_representation`` observation, a ``duplicate_identifier``
        observation per forwarded fact, or **none** at all is a **fact**; the outcome
        value, the forwarded facts, and the ``LLMResponse`` are never judged, and
        none is mutated.  The stage never parses JSON and never detects duplicates.

        Raises
        ------
        ObservationCaptureError
            If NORMALIZATION-0001 has not recorded the normalized structure yet
            (an ordering/coordination failure — Assembly Contract §7), which is an
            infrastructure error, never a normalization fact.
        """
        if not assembly_state.normalized_structure_recorded:
            raise ObservationCaptureError(
                f"{self.stage_id!r} requires the normalized structure from "
                f"NORMALIZATION-0001 to be recorded first; the assembly chain must "
                f"execute 0001 before 0003 (Assembly Contract §7)."
            )

        # A recorded **absence** of structure is the malformed-representation fact
        # (Response Normalization Contract §8).  The outcome, when already
        # determined by 0002, is attached as corroborating evidence — never as the
        # decision that the fact exists (that is derived from 0001's recovery
        # result, this stage's frozen dependency).
        if assembly_state.normalized_structure is None:
            outcome = assembly_state.normalization_outcome
            assembly_state.add_observation(
                NormalizationObservation(
                    observation_id=(f"{self.stage_id}:{OBSERVATION_MALFORMED_REPRESENTATION}"),
                    observation_type=OBSERVATION_MALFORMED_REPRESENTATION,
                    detail=(
                        "The response did not express recoverable well-formed "
                        "structure; no normalized structure was recovered."
                    ),
                    evidence=(outcome.value if outcome is not None else None),
                    created_at=utc_now(),
                )
            )

        # When a structure was recovered, no observation is derivable from the
        # recovered structure alone at this stage — zero observations is a fully
        # successful result (Assembly Contract §8; Response Normalization Contract §8).

        # Duplicate-identifier observations.  The duplicate-key **facts** were
        # detected by the recovery mechanism and forwarded by NORMALIZATION-0001 as a
        # transient execution fact (Assembly Contract §4).  This stage only **reads**
        # those facts and turns each into a ``duplicate_identifier`` observation — it
        # never parses, never detects, and never judges.  Absent facts → no
        # observation (the common case); this is additive to, and independent of, the
        # malformed-representation observation above.
        duplicate_identifiers = assembly_state.internal_metadata.get(
            DUPLICATE_IDENTIFIERS_METADATA_KEY, ()
        )
        for index, identifier in enumerate(duplicate_identifiers):
            assembly_state.add_observation(
                NormalizationObservation(
                    observation_id=(f"{self.stage_id}:{OBSERVATION_DUPLICATE_IDENTIFIER}:{index}"),
                    observation_type=OBSERVATION_DUPLICATE_IDENTIFIER,
                    detail=(
                        f"The field identifier {identifier!r} is duplicated within a "
                        f"structural object."
                    ),
                    location=identifier,
                    created_at=utc_now(),
                )
            )

        # Encoding-integrity observations.  The encoding **facts** were detected by
        # the recovery mechanism and forwarded by NORMALIZATION-0001 as a transient
        # execution fact (Assembly Contract §4).  This stage only **reads** those
        # facts and turns each into an ``encoding_observation`` — it never inspects the
        # text, never parses, never detects, and never judges.  Absent facts → no
        # observation (the common case); additive to, and independent of, the
        # malformed and duplicate observations above.
        encoding_observations = assembly_state.internal_metadata.get(
            ENCODING_OBSERVATIONS_METADATA_KEY, ()
        )
        for index, detail in enumerate(encoding_observations):
            assembly_state.add_observation(
                NormalizationObservation(
                    observation_id=f"{self.stage_id}:{OBSERVATION_ENCODING}:{index}",
                    observation_type=OBSERVATION_ENCODING,
                    detail=detail,
                    created_at=utc_now(),
                )
            )
