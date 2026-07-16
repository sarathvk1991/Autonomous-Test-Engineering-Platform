"""OrganizationalMemoryService — the single runtime entry point into the
Organizational Memory Framework.

Architecture (ADR-0027)
------------------------
``OrganizationalMemoryService`` is the permanent **orchestration boundary** of
the Organizational Memory Framework — the third Layer 2 capability (ADR-0020),
following Continuous Improvement (ADR-0022) and Knowledge Graph (ADR-0023).
Everything outside the subsystem will talk to curation through this one
contract; nothing else is a public runtime surface. It mirrors the role the
Continuous Improvement Framework's and Knowledge Graph Framework's own runtime
services play for their subsystems (ADR-0022 §D6, ADR-0023 §D6): a single seam
that will coordinate collaborators and own none of their work.

Derived Knowledge only — the fan-in exception (frozen, ADR-0025 §Stage 7/8,
Recommendation 6/7 of ADR-0027)
---------------------------------------------------------------------------
``build`` consumes **only** two completed Layer 2 peer results —
:class:`~requirement_intelligence.continuous_improvement.models.result.
ContinuousImprovementResult` and :class:`~requirement_intelligence.
knowledge_graph.models.result.KnowledgeGraphResult` — never a Layer 1 runtime
contract, never a ``HistoricalDatasetReference``, and never an Execution
Package artifact. Organizational Memory is the deliberate fan-in point ADR-0025
§Stage 7/8 carved out: Continuous Improvement and Knowledge Graph remain
peers that never consume one another (ADR-0022 Recommendation 1/9, ADR-0023
Recommendation 1/9), but Organizational Memory — a distinct, later, downstream
capability, not a third peer — may consume both. This is why this service's
signature legitimately imports both subsystems' frozen runtime contract types
directly, unlike every prior Layer 2 service's own strict "no Layer 1, no
Layer 2 peer" containment (ADR-0022 §D6, ADR-0023 §D6): Organizational Memory's
containment rule is narrower in one respect (no Historical Truth, no Layer 1)
and wider in exactly one respect (both Layer 2 peers, and only those two). The
dependency direction is still one-way:

    ContinuousImprovementResult ─┐
                                  ├─▶ OrganizationalMemoryService.build
    KnowledgeGraphResult ────────┘
        ─▶ OrganizationalMemoryResult

What the service OWNS
    orchestration, lifecycle, dependency coordination, and execution ordering.

What the service does NOT own
    Continuous Improvement, Knowledge Graph, the Historical Dataset, any Layer 1
    subsystem, and the Execution Package. Each is a separate owner. The future
    deterministic (and any future statistical, ML, LLM, GraphRAG, or
    neuro-symbolic) Organizational Memory engine is an **internal
    implementation detail** of the service and can be replaced without
    changing this contract.

Runtime status (CAP-085B)
    ``build`` is now implemented: :class:`DeterministicOrganizationalMemoryService`
    delegates to a private :class:`~requirement_intelligence.organizational_memory.
    engine.DeterministicOrganizationalMemoryEngine` that performs deterministic
    experience capture, clustering, lesson generation/consolidation,
    best-practice generation, promotion recording, and lifecycle recording end
    to end — via independent, modular collaborators, never one large engine.
    The service is still **not wired into any execution pipeline** (nothing
    calls ``build`` at runtime) and only ``PlatformContext`` may construct it
    outside this package — so runtime behaviour is byte-identical and the
    golden baseline is unchanged. Runtime integration is future work, exactly
    as CAP-083B implemented the Continuous Improvement Framework's own entry
    point before a later milestone activated it, and CAP-084B did the same for
    the Knowledge Graph Framework.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.continuous_improvement.models.result import (
    ContinuousImprovementResult,
)
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult
from requirement_intelligence.organizational_memory.engine import (
    DeterministicOrganizationalMemoryEngine,
)
from requirement_intelligence.organizational_memory.models.result import OrganizationalMemoryResult
from requirement_intelligence.organizational_memory.policy import OrganizationalMemoryPolicy


class OrganizationalMemoryService(ABC):
    """The permanent runtime contract for building one curated organizational memory.

    A single public method, ``build``, curates experiences, lessons, and best
    practices from two completed Layer 2 peer results under a governed
    :class:`OrganizationalMemoryPolicy` and returns an
    :class:`OrganizationalMemoryResult`. Implementations orchestrate; they
    delegate construction to internal collaborators and own no continuous
    improvement logic, no knowledge graph logic, themselves.
    """

    @abstractmethod
    def build(
        self,
        continuous_improvement_result: ContinuousImprovementResult,
        knowledge_graph_result: KnowledgeGraphResult,
    ) -> OrganizationalMemoryResult:
        """Build curated organizational memory from two completed Layer 2 peer results.

        Parameters
        ----------
        continuous_improvement_result:
            The completed ``ContinuousImprovementResult`` to draw experiences
            from — never modified, never re-derived.
        knowledge_graph_result:
            The completed ``KnowledgeGraphResult`` to draw experiences from —
            never modified, never re-derived.

        Returns
        -------
        OrganizationalMemoryResult
            The complete, self-contained record of every experience, lesson,
            best practice, promotion, and lifecycle record built for this pair
            of consumed results.

        Notes
        -----
        Abstract at CAP-085A; :class:`DeterministicOrganizationalMemoryService`
        (CAP-085B) implements it behind this unchanged signature.
        """
        raise NotImplementedError


class DeterministicOrganizationalMemoryService(OrganizationalMemoryService):
    """The registered default service (CAP-085B) — thin orchestration over the engine.

    Holds a private :class:`~requirement_intelligence.organizational_memory.
    engine.DeterministicOrganizationalMemoryEngine` and delegates ``build`` to
    it, owning only the public boundary and construction. It **computes
    nothing itself**: the engine's modular collaborators perform experience
    capture, clustering, lesson generation/consolidation, best-practice
    generation, promotion recording, and lifecycle recording. Mirrors how the
    Continuous Improvement and Knowledge Graph subsystems' own deterministic
    runtime services delegate to their private engines (ADR-0022, ADR-0023) —
    a thin service, real behaviour one layer down. Replaces
    ``DormantOrganizationalMemoryService`` (CAP-085A), which CAP-085B removes,
    mirroring how CAP-083B's and CAP-084B's own deterministic services
    replaced their dormant predecessors.
    """

    def __init__(self, *, policy: OrganizationalMemoryPolicy) -> None:
        """Construct the private deterministic engine this service delegates to."""
        self._engine = DeterministicOrganizationalMemoryEngine(policy=policy)

    def build(
        self,
        continuous_improvement_result: ContinuousImprovementResult,
        knowledge_graph_result: KnowledgeGraphResult,
    ) -> OrganizationalMemoryResult:
        """Build curated Organizational Memory via the deterministic engine — delegation only."""
        return self._engine.build(continuous_improvement_result, knowledge_graph_result)
