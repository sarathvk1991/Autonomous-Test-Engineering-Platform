"""CP1 subsystem.

The first-class platform subsystem that decides whether the **validated**
requirements are fit to engineer software from — the engineering-readiness gate
between the Validation Platform and Feature Generation, governed by **ADR-0011**
(CP1 Validation Engine & the Validation → CP1 Handoff) and **ADR-0012**
(Engineering Readiness Criteria Catalog).

* :mod:`requirement_intelligence.cp1.models` — the CP1 canonical information models
  (``CP1Input``, ``CP1Result``, ``CP1Finding``), carrying information only.

The CP1 engine (criterion contract, registry, pipeline) and the concrete
engineering-readiness criteria are future milestones; this subsystem currently owns
its canonical models only (CAP-062).
"""

from __future__ import annotations
