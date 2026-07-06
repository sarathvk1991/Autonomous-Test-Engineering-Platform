"""CP1 response orchestration (CAP-064).

Hosts the **Validation → CP1 handoff seam** (``ValidationToCP1Handoff``) — the pure
orchestration boundary, owned **above** both the Validation Platform and CP1
(**ADR-0011 §D4**), that gates on the Validation verdict (**§D5**) and binds a single
``CP1Input``.  The CP1 analogue of the Validation ``response/`` package.

The seam owns **only the transfer**: it does not execute CP1, aggregate findings,
build a ``CP1Result``, evaluate criteria, or judge readiness.  The concrete CP1
engine and any PlatformContext/CLI wiring are later milestones.
"""

from __future__ import annotations

from requirement_intelligence.cp1.response.cp1_handoff import (
    CP1_ELIGIBLE_VALIDATION_VERDICTS,
    ValidationToCP1Handoff,
)

__all__ = [
    "CP1_ELIGIBLE_VALIDATION_VERDICTS",
    "ValidationToCP1Handoff",
]
