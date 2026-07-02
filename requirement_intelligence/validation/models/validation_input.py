"""ValidationInput — the canonical input to the Response Validation subsystem.

:class:`ValidationInput` is a **Core Canonical Model** introduced by
**ADR-0003 (Validation Input and the Normalization → Validation Handoff)**.  It is
the single, immutable object the Response Validator — and therefore every
validation rule — consumes *after* Response Normalization has completed.

Why this model exists
---------------------
Every validation layer from **Syntax** onward reasons about the *normalized* view
of a response, not the raw text: Syntax reads the **Normalization Outcome** from
the ``ParsedResponse`` and the **Normalization Observations** from the
``NormalizationResult``; Schema through Business Rule read the **normalized
structure** from the ``ParsedResponse``.  Transport, by contrast, reads
delivery-level facts from the ``AnalysisResult``.  ``ValidationInput`` binds both
sources into one canonical input so that a single object serves **all nine**
validation layers without any rule re-deriving structure
(``docs/architecture/validation-canonical-models.md`` §8; Validation Rule Catalog
§8; Syntax Layer Design Review; ADR-0003).

Owns only the binding — never facts
-----------------------------------
``ValidationInput`` **references, and never copies**, exactly two existing
artifacts, and owns **no facts of its own**:

* ``analysis_result`` — the original, un-validated response (the ``LLMResponse``,
  ``generated_text``, execution identity, and provenance).  Owned by the
  Requirement Analysis Service; unchanged by this model.
* ``normalization_result`` — the aggregate that carries the shared
  ``ParsedResponse`` (via ``normalization_result.parsed_response``) and **owns**
  the Normalization Observations (via ``normalization_result.observations``).
  Owned by the ``ResponseNormalizer``; unchanged by this model.

It does **not** own or duplicate the ``ParsedResponse``, the observations, any
finding, verdict, summary, or derived structure.  It reaches the ``ParsedResponse``
only through the ``NormalizationResult`` — preserving the single-owner rules frozen
for both (ADR-0003; Architecture Freeze Index §5).  This mirrors how
:class:`~requirement_intelligence.analysis.analysis_models.AnalysisResult`
references (never copies) its ``LLMResponse``.

Lifecycle invariant (ADR-0003 §6)
---------------------------------
A ``ValidationInput`` is an **immutable, execution-scoped aggregate**, created
**exactly once after normalization completes**, binding **exactly one
``AnalysisResult`` and one corresponding ``NormalizationResult`` for the same
execution**.  It is never rebound, never mutated, and never reused across
executions.  Immutability is guaranteed by the frozen
:class:`~shared.contracts.base.Schema` base; the same-execution binding is enforced
at construction (see :meth:`ValidationInput._enforce_same_execution`).

No behaviour
------------
This model carries **information only**: no copies, no derived fields, no helper
methods, and **no validation logic** (it never judges the response — that is the
rules' job).  The one constructor check it performs is a structural *integrity*
invariant (same-execution binding), not a validation judgment.

Versioning
----------
:data:`VALIDATION_INPUT_VERSION` is the version of this representation's *shape*,
owned here as its single source of truth and advanced additively via an ADR — the
same discipline used by
:data:`~requirement_intelligence.models.parsed_response.PARSED_RESPONSE_VERSION`.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.normalization.models.normalization_result import (
    NormalizationResult,
)
from shared.contracts.base import Schema

#: The **ValidationInput Version** — the version of this canonical input's *shape*
#: (ADR-0003).  Owned here as the single source of truth; independent of the
#: Validation Contract Version, the Validator Version, the framework versions, and
#: the ParsedResponse Version.  Advances additively via an ADR.
VALIDATION_INPUT_VERSION = "1.0"


class ValidationInput(Schema):
    """The single, immutable canonical input to the Response Validation subsystem.

    Field names serialise as ``camelCase`` (``validationInputVersion``,
    ``analysisResult``, ``normalizationResult``); Python attributes stay
    ``snake_case``.  The model is immutable and strictly validated (``frozen``,
    ``extra="forbid"`` — inherited from :class:`~shared.contracts.base.Schema`):
    it rejects unknown fields and cannot be mutated after construction.

    The two references are stored **as-is** — the same instances passed in, never
    copies — so ``validation_input.analysis_result is analysis_result`` and
    ``validation_input.normalization_result is normalization_result`` both hold.

    Fields
    ------
    validation_input_version:
        The **ValidationInput Version** — the shape version this instance conforms
        to.  Defaults to :data:`VALIDATION_INPUT_VERSION`.
    analysis_result:
        The analysed response under validation (referenced, never copied).  Its
        ``LLMResponse`` carries the preserved original ``generated_text``; Transport
        rules read delivery facts from here.  Owned by the Requirement Analysis
        Service.
    normalization_result:
        The normalization aggregate for the **same execution** (referenced, never
        copied).  Carries the shared ``ParsedResponse`` (``.parsed_response``) that
        Syntax reads its outcome from and Schema onward read structure from, and
        **owns** the Normalization Observations (``.observations``) that
        ``SYNTAX-0002`` and ``SYNTAX-0003`` read.  Owned by the
        ``ResponseNormalizer``.
    metadata:
        Free-form metadata associated with the binding.  Preserved verbatim.  Never
        a finding, verdict, observation, statistic, or provider payload.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    validation_input_version: str = VALIDATION_INPUT_VERSION
    analysis_result: AnalysisResult
    normalization_result: NormalizationResult
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _enforce_same_execution(self) -> ValidationInput:
        """Enforce the ADR-0003 §6 same-execution binding integrity invariant.

        A ``ValidationInput`` binds one ``AnalysisResult`` and one *corresponding*
        ``NormalizationResult`` — both describing the **same execution**.  When the
        ``NormalizationResult`` carries a correlation identifier, it **must** equal
        the ``AnalysisResult``'s ``execution_id``; a mismatch is a handoff defect
        and is rejected at construction.

        When the ``NormalizationResult`` carries **no** correlation identifier
        (``correlation_id is None``), the binding cannot be contradicted and is
        accepted — this model never *fabricates* a correlation.  This is a
        structural integrity check, not a validation judgment about the response.
        """
        correlation_id = self.normalization_result.correlation_id
        if correlation_id is not None and correlation_id != self.analysis_result.execution_id:
            raise ValueError(
                "ValidationInput must bind an AnalysisResult and a NormalizationResult "
                "for the same execution: normalization_result.correlation_id "
                f"{correlation_id!r} != analysis_result.execution_id "
                f"{self.analysis_result.execution_id!r}."
            )
        return self
