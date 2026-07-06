"""CP1 engine (CAP-065).

Hosts the :class:`~requirement_intelligence.cp1.engine.cp1_engine.CP1Engine` — the
**"Aggregate Result"** stage of the CP1 pattern (ADR-0011 §D7).  **The CP1 Engine
executes the registered governed criteria and aggregates their findings into the
overall CP1 verdict**, assembling the single ``CP1Result``.

**Criteria own engineering policy; the engine owns orchestration only.**  The engine
is handed a ``CP1CriterionPipeline`` and runs it once — it does **not** build a
registry or pipeline, register criteria, or wire the composition root (a later
milestone), and it contains no readiness logic, threshold, heuristic, or policy.
"""

from __future__ import annotations

from requirement_intelligence.cp1.engine.cp1_engine import CP1Engine

__all__ = ["CP1Engine"]
