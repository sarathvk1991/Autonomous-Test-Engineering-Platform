"""CP1 Canonical Models (CAP-062).

The immutable, implementation-independent information models the CP1 Validation
Engine consumes and produces, governed by **ADR-0011** (CP1 Validation Engine & the
Validation → CP1 Handoff) and the **Engineering Readiness Criteria Catalog**
(ADR-0012).

All models inherit the shared :class:`~shared.contracts.base.Schema` base (immutable,
strict, ``camelCase`` serialization) and carry **information only** — no engine
behaviour, no pipeline behaviour, no criterion execution, no readiness policy, no
threshold, no scoring, and no judgement.

* :class:`CP1Input` — the single canonical input to CP1: the Validation → CP1
  handoff binding (references the ``ValidationResult`` + ``NormalizationResult``).
* :class:`CP1Result` — the single canonical output of a CP1 run: the aggregate root
  owning the findings and preserving the input.
* :class:`CP1Finding` — one atomic engineering-readiness finding.
"""

from __future__ import annotations

from requirement_intelligence.validators.models.cp1_finding import (
    CP1_FINDING_VERSION,
    CP1Finding,
)
from requirement_intelligence.validators.models.cp1_input import (
    CP1_INPUT_VERSION,
    CP1Input,
)
from requirement_intelligence.validators.models.cp1_result import (
    CP1_RESULT_VERSION,
    CP1Result,
)

__all__ = [
    "CP1_FINDING_VERSION",
    "CP1_INPUT_VERSION",
    "CP1_RESULT_VERSION",
    "CP1Finding",
    "CP1Input",
    "CP1Result",
]
