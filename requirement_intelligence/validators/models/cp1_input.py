"""CP1Input — the canonical input to the CP1 Validation Engine.

:class:`CP1Input` is a **Core Canonical Model** introduced by **ADR-0011 (CP1
Validation Engine & the Validation → CP1 Handoff)**.  It is the single, immutable
object the CP1 engine — and therefore every future engineering-readiness criterion
— consumes *after* the Validation Platform has validated a response.  It is the
**downstream analogue of the**
:class:`~requirement_intelligence.validation.models.validation_input.ValidationInput`
(ADR-0003) one layer further along the pipeline.

Why this model exists
---------------------
CP1 judges the **engineering readiness** of the *validated, analysed* requirements.
Those requirements are carried in the normalized structure of the shared
``ParsedResponse`` — reached **through** the ``NormalizationResult`` (single-owner
rule, ADR-0003) — while the proof that the response *passed* validation, and its
provenance, live on the ``ValidationResult``.  ``CP1Input`` binds both sources into
one canonical input so the CP1 engine consumes a single object.

CP1 does **not** consume the ``ValidationResult`` directly, because the
``ValidationResult`` preserves only the raw ``AnalysisResult`` and does **not**
carry the normalized structure CP1 must read (ADR-0011 §D3, alternative A1); binding
the ``NormalizationResult`` here is what gives CP1 the validated requirements
without re-normalizing.

Owns only the binding — never facts
-----------------------------------
``CP1Input`` **references, and never copies**, exactly two existing artifacts, and
owns **no facts of its own**:

* ``validation_result`` — the Validation Platform's output for the response: the
  verdict/provenance proving it passed and the preserved ``AnalysisResult``.  Owned
  by the Validation subsystem; unchanged by this model.
* ``normalization_result`` — the aggregate that carries the shared ``ParsedResponse``
  (via ``normalization_result.parsed_response``) and its normalized structure.  Owned
  by the ``ResponseNormalizer``; unchanged by this model.

It does **not** own or duplicate the ``ParsedResponse``, any finding, verdict,
summary, or derived structure, and it never re-derives readiness.  This mirrors how
``ValidationInput`` references (never copies) its ``AnalysisResult`` and
``NormalizationResult``.

The verdict gate is **not** here
--------------------------------
Gating — that CP1 runs only when the validation verdict permits (ADR-0011 §D5) — is
enforced by the **Validation → CP1 seam above both boundaries**, never by this
model.  ``CP1Input`` references the ``ValidationResult`` for provenance; it does
**not** inspect, judge, or enforce the verdict.  That would be judgement, which this
information-only model never performs.

Lifecycle invariant
-------------------
A ``CP1Input`` is an **immutable, execution-scoped aggregate**, created **exactly
once after validation completes**, binding **exactly one ``ValidationResult`` and
one corresponding ``NormalizationResult`` for the same execution**.  It is never
rebound, never mutated, and never reused across executions.  Immutability is
guaranteed by the frozen :class:`~shared.contracts.base.Schema` base; the
same-execution binding is enforced at construction (see
:meth:`CP1Input._enforce_same_execution`) — a **structural integrity** check, not a
validation or readiness judgement (mirroring ``ValidationInput``, ADR-0003 §6).

Versioning
----------
:data:`CP1_INPUT_VERSION` is the version of this representation's *shape*, owned here
as its single source of truth and advanced additively via an ADR — the same
discipline used by
:data:`~requirement_intelligence.validation.models.validation_input.VALIDATION_INPUT_VERSION`.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.normalization.models.normalization_result import (
    NormalizationResult,
)
from requirement_intelligence.validation.models.validation_result import ValidationResult
from shared.contracts.base import Schema

#: The **CP1Input Version** — the version of this canonical input's *shape*
#: (ADR-0011).  Owned here as the single source of truth; independent of the
#: Validation versions, the Normalization versions, and the ParsedResponse Version.
#: Advances additively via an ADR.
CP1_INPUT_VERSION = "1.0"


class CP1Input(Schema):
    """The single, immutable canonical input to the CP1 Validation Engine.

    Field names serialise as ``camelCase`` (``cp1InputVersion``,
    ``validationResult``, ``normalizationResult``); Python attributes stay
    ``snake_case``.  The model is immutable and strictly validated (``frozen``,
    ``extra="forbid"`` — inherited from :class:`~shared.contracts.base.Schema`): it
    rejects unknown fields and cannot be mutated after construction.

    The two references are stored **as-is** — the same instances passed in, never
    copies — so ``cp1_input.validation_result is validation_result`` and
    ``cp1_input.normalization_result is normalization_result`` both hold.

    Fields
    ------
    cp1_input_version:
        The **CP1Input Version** — the shape version this instance conforms to.
        Defaults to :data:`CP1_INPUT_VERSION`.
    validation_result:
        The Validation Platform's output for the validated response (referenced,
        never copied): the verdict/provenance and the preserved ``AnalysisResult``.
        Owned by the Validation subsystem.
    normalization_result:
        The normalization aggregate for the **same execution** (referenced, never
        copied).  Carries the shared ``ParsedResponse`` (``.parsed_response``) whose
        normalized structure holds the validated, analysed requirements CP1 judges.
        Owned by the ``ResponseNormalizer``.
    metadata:
        Free-form metadata associated with the binding.  Preserved verbatim.  Never
        a finding, verdict, observation, statistic, or provider payload.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    cp1_input_version: str = CP1_INPUT_VERSION
    validation_result: ValidationResult
    normalization_result: NormalizationResult
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _enforce_same_execution(self) -> CP1Input:
        """Enforce the same-execution binding integrity invariant (ADR-0011 §D3).

        A ``CP1Input`` binds one ``ValidationResult`` and one *corresponding*
        ``NormalizationResult`` — both describing the **same execution**.  When the
        ``NormalizationResult`` carries a correlation identifier, it **must** equal
        the ``ValidationResult``'s ``execution_id``; a mismatch is a handoff defect
        and is rejected at construction.

        When the ``NormalizationResult`` carries **no** correlation identifier
        (``correlation_id is None``), the binding cannot be contradicted and is
        accepted — this model never *fabricates* a correlation.  This is a
        structural integrity check, not a validation or readiness judgement about the
        response.
        """
        correlation_id = self.normalization_result.correlation_id
        if correlation_id is not None and correlation_id != self.validation_result.execution_id:
            raise ValueError(
                "CP1Input must bind a ValidationResult and a NormalizationResult for "
                "the same execution: normalization_result.correlation_id "
                f"{correlation_id!r} != validation_result.execution_id "
                f"{self.validation_result.execution_id!r}."
            )
        return self
