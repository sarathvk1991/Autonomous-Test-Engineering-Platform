"""CP1 framework composition helpers.

Thin, behaviour-free helpers that compose the CP1 framework's pieces (registry →
pipeline).  They mirror the *role* of the Validation subsystem's ``validator_factory``
at the **framework** level, but they register **no criteria**: the Engineering
Readiness Criteria Catalog is intentionally empty (ADR-0012), and wiring concrete
criteria is a later milestone (the CP1 engine / criteria).

These helpers contain **no engineering-readiness knowledge, no policy, and no
judgement**.  They only assemble infrastructure.
"""

from __future__ import annotations

from requirement_intelligence.cp1.framework.criterion_pipeline import CP1CriterionPipeline
from requirement_intelligence.cp1.framework.criterion_registry import CP1CriterionRegistry


def build_cp1_criterion_registry() -> CP1CriterionRegistry:
    """Build a fresh, empty CP1 criterion registry.

    Registers **no criteria** — none exist yet (ADR-0012).  This is the seam where
    the future CP1 engine will register governed criteria in catalog order.

    Returns
    -------
    CP1CriterionRegistry
        A new, open, empty registry.
    """
    return CP1CriterionRegistry()


def build_cp1_criterion_pipeline(
    registry: CP1CriterionRegistry | None = None,
) -> CP1CriterionPipeline:
    """Compose a CP1 criterion pipeline from a registry.

    Parameters
    ----------
    registry:
        The registry supplying the criterion set.  When omitted, a fresh empty
        registry is created — a pipeline over an empty registry is a valid
        (empty-run) pipeline.  Constructing the pipeline **seals** the registry.

    Returns
    -------
    CP1CriterionPipeline
        A ready pipeline whose criterion set is fixed for its lifetime.
    """
    return CP1CriterionPipeline(registry if registry is not None else CP1CriterionRegistry())
