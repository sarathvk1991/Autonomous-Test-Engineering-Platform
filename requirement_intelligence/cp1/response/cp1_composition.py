"""CP1 composition root (CAP-066).

Assembles the already-governed CP1 components — the criterion registry, the criterion
pipeline, and the engine — into a single ready-to-run :class:`CP1Service`, preserving
every ownership boundary of ADR-0011 and ADR-0012.

Owns only wiring
----------------
The composition root owns **object assembly and dependency wiring only**.  It
introduces **no** engineering-readiness knowledge: no criterion, no threshold, no
heuristic, no scoring, no weighting, no policy.  Ownership is unchanged:

* **Criteria** own engineering policy (future; none exist).
* **Engine** owns execution, aggregation, and ``CP1Result`` assembly (CAP-065).
* **Framework** owns criterion execution and finding collection (CAP-063).
* **Seam** owns the Validation → CP1 binding (CAP-064).
* **This module** owns none of those — only assembly.

Explicit, deterministic registration
------------------------------------
Registration is **explicit** — no reflection, no auto-discovery, no plugin scan, no
service locator.  The Engineering Readiness Criteria Catalog is intentionally **empty**
(ADR-0012), so the registry is assembled with **zero criteria** — the
architecture-correct state.  When governed criteria exist, they are registered here,
explicitly, in catalog order.

Statelessness & thread-safety
-----------------------------
:class:`CP1Service` holds only immutable wiring: a **sealed** ``CP1CriterionRegistry``
(registration closed; retrieval only) and the stateless ``CP1Engine``.  It holds **no**
long-lived pipeline — the ``CP1CriterionPipeline`` carries observable per-run state, so
a **fresh pipeline is constructed per** :meth:`CP1Service.run` **call** from the sealed
registry.  The service therefore has no shared mutable state, is safe to share across
threads, and every build produces an equivalent service (same criteria set, same
engine behaviour).
"""

from __future__ import annotations

from requirement_intelligence.cp1.engine import CP1Engine
from requirement_intelligence.cp1.framework import (
    CP1CriterionPipeline,
    CP1CriterionRegistry,
    build_cp1_criterion_registry,
)
from requirement_intelligence.cp1.models import CP1Input, CP1Result


class CP1Service:
    """The assembled, ready-to-run CP1 service — a single execution entry point.

    Owns only immutable wiring: a sealed ``CP1CriterionRegistry`` and the stateless
    ``CP1Engine``.  Registry and pipeline construction are hidden from callers; the
    sole public operation is :meth:`run`.
    """

    def __init__(self, registry: CP1CriterionRegistry, engine: CP1Engine) -> None:
        self._registry = registry
        self._engine = engine

    def run(self, cp1_input: CP1Input) -> CP1Result:
        """Execute the assembled CP1 run over *cp1_input* and return the ``CP1Result``.

        Builds a fresh ``CP1CriterionPipeline`` from the sealed registry (keeping the
        service free of shared mutable state) and delegates execution + aggregation to
        the engine.  With zero governed criteria the pipeline produces no findings and
        the engine derives a ``PASS`` verdict.
        """
        pipeline = CP1CriterionPipeline(self._registry)
        return self._engine.run(cp1_input, pipeline)


def build_cp1_service() -> CP1Service:
    """Compose a ready-to-run :class:`CP1Service` — the CP1 composition root.

    Explicit, deterministic assembly:

    1. construct an empty ``CP1CriterionRegistry``;
    2. register all governed criteria — **none exist yet** (catalog empty, ADR-0012);
    3. **seal** the registry (registration closed → immutable);
    4. construct the stateless ``CP1Engine``;
    5. return the assembled :class:`CP1Service`.

    Holds no state; every call returns an equivalent service.
    """
    registry = build_cp1_criterion_registry()
    # Register all governed criteria here, explicitly, in catalog order.  The
    # Engineering Readiness Criteria Catalog is intentionally empty (ADR-0012), so
    # there are zero criteria to register — the architecture-correct state.
    registry.seal()
    return CP1Service(registry=registry, engine=CP1Engine())
