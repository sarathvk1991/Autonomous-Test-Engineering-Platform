"""ParsedResponse — the canonical structural representation of one AI response.

:class:`ParsedResponse` is a **Core Canonical Model** and a **Shared Platform
Artifact**.  It is the single, immutable, provider- and format-independent
normalized structure of one AI response — the substrate every platform consumer
reads without re-deriving.  It is the conceptual realisation of the
``ParsedResponse`` defined in ``docs/architecture/validation-canonical-models.md``
(§8), whose *creation, ownership, sharing, and versioning* are governed by
``docs/architecture/response-normalization-contract.md``.

Peer, not property
------------------
``ParsedResponse`` is a **peer** of
:class:`~requirement_intelligence.llm.llm_models.LLMResponse`,
:class:`~requirement_intelligence.analysis.analysis_models.AnalysisResult`, and the
validation/normalization result models — not a part of any of them.  Validation is
merely its **first** consumer (Response Normalization Contract §7); Requirement
Normalization, Feature Generation, Test Generation, AI Evaluation, Analytics, and
future components read the **same** instance.  No subsystem owns it.

Creation and lifecycle
----------------------
A ``ParsedResponse`` is **created once**, before any consumer runs, by the future
``ResponseNormalizer`` (governed by the Response Normalization Contract).  This
model governs *what it holds*; it contains **no** creation, parsing, validation,
provider, repair, or business logic — **information only**.  It is immutable,
shared, and never copied, mutated, or recreated (Response Normalization Contract
§6).

What it owns — and deliberately does not
----------------------------------------
It owns **only the canonical representation**: the Normalization Outcome, the
normalized structure, and a reference to the preserved original response.  It owns
**no** execution identity (``NormalizationExecutionContext``), framework metadata
(``NormalizationFrameworkMetadata``), statistics (``NormalizationStatistics``),
verdict/issues/recommendations (``ValidationResult`` and its aggregate), provider
metadata (``LLMResponse``), transport state, reasoning, or business meaning.  Each
remains owned by its existing model.

Deliberate deviation from Canonical Models §8.1 — Normalization Observations
----------------------------------------------------------------------------
``validation-canonical-models.md`` §8.1 lists **Normalization Observations** as a
fourth ParsedResponse attribute.  This implementation **deliberately excludes**
them: the Normalization Observations remain owned solely by
:class:`~requirement_intelligence.normalization.models.normalization_result.NormalizationResult`
(which already owns an ``observations`` tuple), so the same facts are never stored
in two canonical homes.  This is a **governed, recorded deviation** — not a silent
one — and reconciling it with §8.1 (either by moving observations onto
``ParsedResponse`` or by amending §8.1) requires an ADR.  It changes neither the
Normalization Outcome fact set nor the ParsedResponse Version's additive
compatibility.

Versioning
----------
:data:`PARSED_RESPONSE_VERSION` is the **ParsedResponse Version** (Response
Normalization Contract §12) — the version of the *representation's shape*, owned
here as its single source of truth.  It is **independent** of the Normalization
Contract Version (semantics), the validation versions, and the framework versions.
The shape evolves **additively**; a shape change advances this version through an
ADR.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema
from shared.enums.base import NormalizationOutcome

#: The **ParsedResponse Version** — the version of the canonical representation's
#: *shape* (Response Normalization Contract §12).  Owned here as the single source
#: of truth; independent of the Normalization Contract Version, the validation
#: versions, and the framework versions.  Advances additively via an ADR.
PARSED_RESPONSE_VERSION = "1.0"


class ParsedResponse(Schema):
    """The immutable, canonical structural representation of one AI response.

    Field names serialise as ``camelCase`` (``parsedResponseVersion``,
    ``normalizationOutcome``, ``normalizedStructure``, ``sourceReference``);
    Python attributes stay ``snake_case``.  The model is immutable and strictly
    validated (inherited from :class:`~shared.contracts.base.Schema`): every
    field with a forbidden home is simply absent, and construction rejects
    unknown fields.

    Fields
    ------
    parsed_response_version:
        The **ParsedResponse Version** — the shape version this instance conforms
        to.  Defaults to :data:`PARSED_RESPONSE_VERSION`.
    normalization_outcome:
        The normalized, provider-independent structural **fact**
        (:class:`~shared.enums.base.NormalizationOutcome`): ``NORMALIZED`` or
        ``MALFORMED``.  A fact the Syntax layer reads and judges — never a verdict
        (Response Normalization Contract §9, §10).
    normalized_structure:
        When ``NORMALIZED``: the **format-neutral** structural view of the
        response — a document of objects, arrays, scalars, and identifiers, held
        as nested values.  ``None`` when ``MALFORMED`` (no structure was
        recovered).  It represents *structure*, never a specific serialization
        format (Canonical Models §8; Response Normalization Contract §11).
    source_reference:
        A link back to the response's **preserved original** ``generated_text``,
        so the normalized view never replaces the original (Response
        Normalization Contract §3.2, §13 ``NORMALIZATION-0004``).  Optional — it
        is a *reference*, never a copy of the provider text, keeping the model
        provider-independent.
    metadata:
        Free-form metadata associated with the representation.  Preserved
        verbatim.  Never a verdict, observation, statistic, or provider payload.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    parsed_response_version: str = PARSED_RESPONSE_VERSION
    normalization_outcome: NormalizationOutcome
    normalized_structure: dict[str, Any] | None = None
    source_reference: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
