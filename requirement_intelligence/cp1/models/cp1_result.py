"""CP1Result — the aggregate root and single output of the CP1 Validation Engine.

:class:`CP1Result` is the CP1 analogue of the Validation subsystem's
:class:`~requirement_intelligence.validation.models.validation_result.ValidationResult`:
it is the **one artifact** every downstream consumer receives from a CP1 run, and it
gates the handoff to Feature Generation (ADR-0011).

Ownership, reference, and containment:

* **Owns** the :class:`~requirement_intelligence.cp1.models.cp1_finding.CP1Finding`
  collection.
* **Contains** (preserves unchanged) the
  :class:`~requirement_intelligence.cp1.models.cp1_input.CP1Input` that was
  judged — the validated input is referenced, never mutated (mirroring how
  ``ValidationResult`` preserves its ``AnalysisResult``; ADR-0011 §D4).

This model carries **information only**.  It holds **no** readiness policy, no
threshold, no scoring, and no judgement logic: the ``overall_verdict`` and the
findings are *recorded* here by the future CP1 engine, which derives them — this
model never derives them itself.  The result is immutable: assembled once, at the
end of a run, and never altered.

Versioning
----------
:data:`CP1_RESULT_VERSION` is the version of this representation's *shape*, owned
here as its single source of truth and advanced additively via an ADR.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.cp1.models.cp1_finding import CP1Finding
from requirement_intelligence.cp1.models.cp1_input import CP1Input
from shared.contracts.base import Schema
from shared.enums.base import ValidationVerdict

#: The **CP1Result Version** — the version of this representation's *shape*.
#: Owned here as the single source of truth; advances additively via an ADR.
CP1_RESULT_VERSION = "1.0"


class CP1Result(Schema):
    """Immutable aggregate root — the single output of the CP1 Validation Engine.

    Field names serialise as ``camelCase`` (``cp1Id``, ``cp1Input``,
    ``overallVerdict``, ``cp1ResultVersion``, …); Python attributes stay
    ``snake_case``.

    Fields
    ------
    cp1_result_version:
        The **CP1Result Version** — the shape version this instance conforms to.
        Defaults to :data:`CP1_RESULT_VERSION`.
    cp1_id:
        Unique identity of this CP1 run.
    validation_id:
        Identity of the validation run whose result this CP1 run consumed
        (carried for direct traceability; also present on ``cp1_input``).
    execution_id:
        Identity of the AI invocation that produced the analysed response.
    analysis_id:
        Identity of the analysis operation the response belongs to.
    cp1_input:
        The original, unaltered :class:`CP1Input` that was judged (preserved, not
        mutated).
    overall_verdict:
        The single overall CP1 outcome — ``PASS``/``FAIL``/``WARN`` (``shared``
        :class:`~shared.enums.base.ValidationVerdict`, CP1's governed vocabulary).
        Recorded here; derived by the future CP1 engine, never by this model.
    findings:
        The complete collection of engineering-readiness findings the result owns.
        An immutable tuple; an empty tuple is a valid result.
    started_at / completed_at:
        Wall-clock start and completion timestamps of the CP1 run.
    metadata:
        Free-form metadata associated with the result.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    cp1_result_version: str = CP1_RESULT_VERSION
    cp1_id: str
    validation_id: str
    execution_id: str
    analysis_id: str

    # Contained — the preserved original input.
    cp1_input: CP1Input

    # Owned.
    findings: tuple[CP1Finding, ...] = Field(default_factory=tuple)

    overall_verdict: ValidationVerdict
    started_at: datetime
    completed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
