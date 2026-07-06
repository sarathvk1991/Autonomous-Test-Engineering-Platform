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
  owning the findings, preserving the input, and referencing the framework provenance.
* :class:`CP1Finding` — one atomic engineering-readiness finding.
* :class:`CP1FrameworkMetadata` — immutable provenance of the executing framework
  (lives here, mirroring ``ValidationFrameworkMetadata`` in ``validation/models/``).
"""

from __future__ import annotations

from requirement_intelligence.cp1.models.cp1_finding import (
    CP1_FINDING_VERSION,
    CP1Finding,
)
from requirement_intelligence.cp1.models.cp1_input import (
    CP1_INPUT_VERSION,
    CP1Input,
)
from requirement_intelligence.cp1.models.cp1_result import (
    CP1_RESULT_VERSION,
    CP1Result,
)
from requirement_intelligence.cp1.models.framework_metadata import (
    CP1_FRAMEWORK_VERSION,
    CP1_PIPELINE_VERSION,
    CP1_REGISTRY_VERSION,
    DEFAULT_CP1_CRITERIA_CONTRACT_VERSION,
    CP1FrameworkMetadata,
)

__all__ = [
    "CP1_FINDING_VERSION",
    "CP1_FRAMEWORK_VERSION",
    "CP1_INPUT_VERSION",
    "CP1_PIPELINE_VERSION",
    "CP1_REGISTRY_VERSION",
    "CP1_RESULT_VERSION",
    "DEFAULT_CP1_CRITERIA_CONTRACT_VERSION",
    "CP1Finding",
    "CP1FrameworkMetadata",
    "CP1Input",
    "CP1Result",
]
