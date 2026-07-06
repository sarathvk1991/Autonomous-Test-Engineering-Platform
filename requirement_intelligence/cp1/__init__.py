"""CP1 subsystem.

The first-class platform subsystem that decides whether the **validated**
requirements are fit to engineer software from — the engineering-readiness gate
between the Validation Platform and Feature Generation, governed by **ADR-0011**
(CP1 Validation Engine & the Validation → CP1 Handoff) and **ADR-0012**
(Engineering Readiness Criteria Catalog).

* :mod:`requirement_intelligence.cp1.models` — the CP1 canonical information models
  (``CP1Input``, ``CP1Result``, ``CP1Finding``), carrying information only.  **The
  only implemented package** (CAP-062).
* :mod:`requirement_intelligence.cp1.framework` — *reserved* home for the reusable
  engine infrastructure (criterion contract, registry, pipeline — ADR-0011 §D7).
* :mod:`requirement_intelligence.cp1.criteria` — *reserved* home for the concrete
  engineering-readiness criteria (ADR-0012; the catalog is currently empty).
* :mod:`requirement_intelligence.cp1.response` — *reserved* home for the CP1
  orchestrator and the Validation → CP1 handoff-seam consumer (ADR-0011 §D4).
* :mod:`requirement_intelligence.cp1.engine` — *reserved* home for the assembled,
  runnable CP1 engine composition (ADR-0011 §D7).

The four reserved packages are **intentionally empty** subsystem scaffolding: the
CP1 engine and the concrete engineering-readiness criteria are future milestones.
This subsystem currently owns its canonical models only (CAP-062).
"""

from __future__ import annotations
