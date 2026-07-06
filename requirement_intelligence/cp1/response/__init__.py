"""CP1 response orchestration (CAP-064, CAP-066).

The CP1 analogue of the Validation ``response/`` package.  Hosts:

* the **Validation → CP1 handoff seam** (``ValidationToCP1Handoff``, CAP-064) — the
  pure orchestration boundary owned **above** both the Validation Platform and CP1
  (ADR-0011 §D4) that gates on the Validation verdict (§D5) and binds one ``CP1Input``;
* the **CP1 composition root** (``build_cp1_service`` → ``CP1Service``, CAP-066) — the
  explicit, deterministic assembly of the registry, pipeline, and engine into a single
  ready-to-run service.

Neither owns engineering-readiness knowledge: the seam owns only the transfer; the
composition root owns only assembly.  PlatformContext/CLI wiring are later milestones.
"""

from __future__ import annotations

from requirement_intelligence.cp1.response.cp1_composition import CP1Service, build_cp1_service
from requirement_intelligence.cp1.response.cp1_handoff import (
    CP1_ELIGIBLE_VALIDATION_VERDICTS,
    ValidationToCP1Handoff,
)

__all__ = [
    "CP1_ELIGIBLE_VALIDATION_VERDICTS",
    "CP1Service",
    "ValidationToCP1Handoff",
    "build_cp1_service",
]
