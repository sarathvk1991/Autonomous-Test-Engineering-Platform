"""NORMALIZATION-0004 — Create Source Reference.

The **fourth** internal stage of the ``ResponseNormalizer``.  It owns exactly one
concern: creating the immutable **Source Reference** that links the canonical
representation back to the *preserved original* response, and recording it into the
Assembly State.

Responsibility Documentation Contract
-------------------------------------
1. **Purpose** — Create the immutable Source Reference — a stable link back to the
   preserved original ``generated_text`` — and record it as a fact.  (Fulfils the
   Contract's "Preserve Original Response" responsibility §13 **by reference**.)
2. **Catalog ID** — ``NORMALIZATION-0004`` (Normalization Responsibility Catalog
   §5; Response Normalization Contract §13).
3. **Inputs** — the identity of the original response under normalization, read
   from ``LLMResponse.generated_text``.  It reads **no** earlier stage's fact — it
   is **independent** of ``0001`` through ``0003`` (Catalog §5; Assembly Contract §6).
4. **Outputs** — the **Source Reference** fact written to the Assembly State: a
   stable, provider-independent reference string.
5. **Worked example** — the normalized representation must never *replace* the
   original response.  ``0004`` creates a reference *to* the preserved original —
   a content-addressed handle — so a consumer can always reach the unaltered source
   without the representation ever holding a copy of it.
6. **Architecture Reference** — ``docs/architecture/normalization-assembly-contract.md``
   §6 (NORMALIZATION-0004); ``docs/architecture/normalization-responsibility-catalog.md``
   §5; ``docs/architecture/normalization-stage-implementation-contract.md``; ADR-0002.

What the Source Reference is — and is not
-----------------------------------------
The Source Reference is a **reference**, never a copy (Catalog §5 "preserve by
reference, never by copy"; ``ParsedResponse.source_reference``).  It is therefore:

* **not** the ``generated_text`` and **not** a duplicate of it — a one-way content
  digest cannot reconstruct the original;
* **not** provider metadata — it is derived from the already-provider-independent
  ``generated_text`` alone;
* **not** a copy of any other ``ParsedResponse`` field.

Implementation choice (documented, as the architecture leaves the *format* free)
--------------------------------------------------------------------------------
The architecture fixes the Source Reference's *role* (a stable link back to the
preserved original) and its *type* (a string), but deliberately leaves its *format*
to implementation.  The **simplest provider-independent, deterministic** reference
to content that carries **no** external identifier — the ``LLMResponse`` is
source-decoupled and holds no id (Response Normalizer §10) — is a **content
digest** of ``generated_text``, published as ``"sha256:<hex>"``.  This:

* is a stable reference (deterministic: the same ``generated_text`` always yields
  the same reference — Stage Implementation Contract §4);
* is provider- and format-independent (computed from the normalized text only);
* is not a copy (a one-way digest; the original text cannot be recovered from it);
* is self-describing (the ``sha256:`` scheme marks it unmistakably as a reference,
  not text).

The digest is computed inline with the standard library rather than importing the
execution package's ``sha256_text`` helper: the Response Normalization subsystem
must not depend on the higher execution/packaging layer (subsystem independence;
ADR-0002).  A one-line standard-library call is not architecturally significant
duplication, and adding a shared abstraction for a single normalization caller
would be speculative (Stage Implementation Contract §9.2).

Single concern — what it never does
-----------------------------------
It **never** recovers structure (``0001``), determines the outcome (``0002``),
captures observations (``0003``), assembles the ``ParsedResponse`` (``0005``),
validates, judges, repairs, coordinates, copies or mutates the ``LLMResponse``, or
writes any other Assembly State field.  It writes **only** the source reference.

Facts, not exceptions (Assembly Contract §8)
--------------------------------------------
Creating the source reference is a **fact** for *every* response — even an empty
one has a well-defined, stable content reference.  The stage raises
:class:`~requirement_intelligence.normalization.response.assembly.stage_exceptions.SourceReferenceCreationError`
**only** if the reference-creation mechanism itself fails for an infrastructure
reason — never to signal a malformed or empty response.
"""

from __future__ import annotations

import hashlib

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
    SourceReferenceCreationError,
)

#: The scheme that marks the reference as a content-addressed handle, not text.
_SOURCE_REFERENCE_SCHEME = "sha256"

#: The immutable identity of NORMALIZATION-0004, constructed once and shared.
_METADATA = NormalizationStageMetadata(
    stage_id="NORMALIZATION-0004",
    stage_name="Create Source Reference",
    order=4,
    documentation_reference=(
        "docs/architecture/normalization-assembly-contract.md#6-stage-contracts"
    ),
)


class CreateSourceReference(NormalizationStage):
    """NORMALIZATION-0004 — create the reference to the preserved original response.

    The stage takes **no injected collaborator**: the reference is a fixed,
    governed, content-addressed handle (see the module docstring), so there is no
    varying *mechanism* to inject.  It reads only ``LLMResponse.generated_text`` and
    records exactly one source-reference string.  It depends on **no** earlier stage
    (Catalog §5), so it carries no ordering guard.
    """

    @property
    def metadata(self) -> NormalizationStageMetadata:
        return _METADATA

    def execute(self, llm_response: LLMResponse, assembly_state: AssemblyState) -> None:
        """Create the source reference for *llm_response* and record it.

        Reads **only** ``llm_response.generated_text``; writes **only** the source
        reference.  The reference is a one-way content digest — a stable link to the
        preserved original, never a copy of it.  The ``LLMResponse`` is never
        mutated and no other Assembly State fact is touched.

        Raises
        ------
        SourceReferenceCreationError
            Only if the reference-creation mechanism itself fails for an
            infrastructure reason (Assembly Contract §8) — never for an empty or
            malformed response, which still yields a valid reference.
        """
        text = llm_response.generated_text
        try:
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        except Exception as exc:  # pragma: no cover - defensive, mirrors 0001
            # An infrastructure failure of the reference mechanism — never a
            # normalization fact.
            raise SourceReferenceCreationError(
                f"Source-reference creation failed for stage {self.stage_id!r}: {exc}"
            ) from exc

        # The Source Reference fact: a self-describing, content-addressed handle to
        # the preserved original — recorded exactly once; the stage writes no other
        # fact.
        assembly_state.record_source_reference(f"{_SOURCE_REFERENCE_SCHEME}:{digest}")
