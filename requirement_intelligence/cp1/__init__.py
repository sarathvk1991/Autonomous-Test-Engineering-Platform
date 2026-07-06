"""CP1 subsystem.

The first-class platform subsystem that decides whether the **validated**
requirements are fit to engineer software from — the engineering-readiness gate
between the Validation Platform and Feature Generation, governed by **ADR-0011**
(CP1 Validation Engine & the Validation → CP1 Handoff) and **ADR-0012**
(Engineering Readiness Criteria Catalog).

* :mod:`requirement_intelligence.cp1.models` — the CP1 canonical information models
  (``CP1Input``, ``CP1Result``, ``CP1Finding``), carrying information only (CAP-062).
* :mod:`requirement_intelligence.cp1.framework` — the reusable, behaviour-free engine
  infrastructure: criterion contract, registry, pipeline, and framework provenance
  (ADR-0011 §D7).  **Implemented** (CAP-063); knows nothing about engineering
  readiness.
* :mod:`requirement_intelligence.cp1.criteria` — the concrete engineering-readiness
  criteria (ADR-0012).  **Implemented:** `CP1-0001` (`EngineeringInputAvailabilityCriterion`,
  ADR-0013) — the catalog's first and only criterion (CAP-067A).
* :mod:`requirement_intelligence.cp1.response` — the **Validation → CP1 handoff seam**
  (``ValidationToCP1Handoff``); gates on the Validation verdict and binds one
  ``CP1Input`` (ADR-0011 §D4/§D5).  **Implemented** (CAP-064).
* :mod:`requirement_intelligence.cp1.engine` — the **CP1 Engine** (``CP1Engine``): it
  **executes the registered governed criteria and aggregates their findings into the
  overall CP1 verdict**, assembling the ``CP1Result`` (ADR-0011 §D7; ADR-0012 §8).
  **Implemented** (CAP-065).  Criteria own engineering policy; the engine owns
  orchestration only — it builds no registry/pipeline (that is the composition root).

The CP1 subsystem is complete end-to-end: canonical models (CAP-062), framework
(CAP-063), seam (CAP-064), engine (CAP-065), composition root (CAP-066,
``cp1/response/cp1_composition.py``), and its **first governed criterion** ``CP1-0001``
(CAP-067A).  A composed ``CP1Service`` runs `Validation → CP1 → CP1Result`
deterministically.
"""

from __future__ import annotations
