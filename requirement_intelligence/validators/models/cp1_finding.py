"""CP1Finding — the atomic engineering-readiness finding.

:class:`CP1Finding` is the CP1 analogue of the Validation subsystem's
:class:`~requirement_intelligence.validation.models.validation_issue.ValidationIssue`:
it records exactly **one** objective engineering-readiness observation about the
validated requirements, with everything needed to understand, locate, act on, and
audit it.

Governance
----------
* The concern a finding reports is a **criterion** governed by the
  **Engineering Readiness Criteria Catalog**
  (``docs/architecture/engineering-readiness-criteria-catalog.md``); the finding
  references that criterion by its stable ``CP1-NNNN`` identity (``criterion_id``).
* CP1 is a **flat** namespace — there is **no** validation-layer concept here
  (Criteria Catalog §4, ADR-0012), so — unlike ``ValidationIssue`` — a finding
  carries **no** ``validation_layer``.
* CP1 recognises **no** fail-fast layer halting (Criteria Catalog §5, ADR-0012),
  so — unlike ``ValidationIssue`` — a finding carries **no** ``blocking`` flag.

This model carries **information only**.  It contains **no** readiness policy, no
threshold, no scoring, and no judgement: it does not decide the criterion's
verdict, it only *records* the contribution a criterion produced.  Findings are
*produced by* future CP1 criteria and *owned by* a
:class:`~requirement_intelligence.validators.models.cp1_result.CP1Result`.

Versioning
----------
:data:`CP1_FINDING_VERSION` is the version of this representation's *shape*, owned
here as its single source of truth and advanced additively via an ADR — the same
discipline used by the Validation canonical models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema
from shared.enums.base import ValidationVerdict

#: The **CP1Finding Version** — the version of this representation's *shape*.
#: Owned here as the single source of truth; advances additively via an ADR.
CP1_FINDING_VERSION = "1.0"


class CP1Finding(Schema):
    """One atomic, immutable engineering-readiness finding.

    Field names serialise as ``camelCase`` (``findingId``, ``criterionId``,
    ``verdictContribution``, ``correlationId``, …); Python attributes stay
    ``snake_case``.  The model is immutable and strictly validated (inherited from
    :class:`~shared.contracts.base.Schema`): every attribute, including the verdict
    contribution, is fixed at creation and can never change.

    Fields
    ------
    cp1_finding_version:
        The **CP1Finding Version** — the shape version this instance conforms to.
        Defaults to :data:`CP1_FINDING_VERSION`.
    finding_id:
        Stable handle that uniquely references this finding.
    criterion_id:
        The stable ``CP1-NNNN`` identity of the readiness criterion that produced
        the finding (Criteria Catalog §4).
    criterion_version:
        Version of the criterion's definition at the time the finding was produced.
    verdict_contribution:
        The ``PASS``/``FAIL``/``WARN`` contribution this finding carries
        (``shared`` :class:`~shared.enums.base.ValidationVerdict` — CP1's governed
        verdict vocabulary, deliberately distinct from the Validation subsystem's
        four-state verdict).  The overall CP1 verdict is aggregated **by the future
        CP1 engine**, never by a finding.
    message:
        Human-readable statement of what was observed and why it matters.
    location:
        Where in the validated requirements the observation concerns (e.g. which
        requirement or section).
    evidence:
        The observed value or condition that substantiates the finding.  Optional —
        some findings (e.g. a missing element) have no evidence value.
    recommendation:
        What would resolve the finding.
    correlation_id:
        Trace key linking the finding to its originating analysis and run.
    created_at:
        When the observation was made.
    metadata:
        Free-form metadata associated with the finding.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    cp1_finding_version: str = CP1_FINDING_VERSION
    finding_id: str
    criterion_id: str
    criterion_version: str
    verdict_contribution: ValidationVerdict
    message: str
    location: str
    evidence: str | None = None
    recommendation: str
    correlation_id: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
