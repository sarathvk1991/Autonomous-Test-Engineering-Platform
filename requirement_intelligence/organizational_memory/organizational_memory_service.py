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

Runtime status (CAP-085A)
    ``build`` is abstract and dormant: :class:`DormantOrganizationalMemoryService`
    raises ``NotImplementedError`` on every call. No experience is captured, no
    lesson is promoted, no best practice is institutionalized, and no lifecycle
    is recorded. Only ``PlatformContext`` may construct it outside this
    package. A later milestone (CAP-085B, reserved) implements the method
    behind this unchanged signature, exactly as CAP-083B implemented the
    Continuous Improvement Framework's own entry point behind the ADR-0022
    boundary and CAP-084B implemented the Knowledge Graph Framework's own
    entry point behind the ADR-0023 boundary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.continuous_improvement.models.result import (
    ContinuousImprovementResult,
)
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult
from requirement_intelligence.organizational_memory.models.result import OrganizationalMemoryResult


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
        Abstract in CAP-085A; a future CAP-085B milestone implements it behind
        this unchanged signature.
        """
        raise NotImplementedError


class DormantOrganizationalMemoryService(OrganizationalMemoryService):
    """The CAP-085A registered default — architecture only, no behaviour.

    Every call to ``build`` raises ``NotImplementedError``. This is the
    intentional, permanent shape of a dormant Layer 2 service (mirrors the
    dormant default services Continuous Improvement registered at CAP-083A
    and Knowledge Graph registered at CAP-084A, both since replaced by their
    own deterministic successors) — it exists so ``PlatformContext`` has a
    real, constructible object to return before any engine exists, and so the
    abstract contract above is provably instantiable.
    """

    def build(
        self,
        continuous_improvement_result: ContinuousImprovementResult,
        knowledge_graph_result: KnowledgeGraphResult,
    ) -> OrganizationalMemoryResult:
        """Always raises — no Organizational Memory engine exists yet (CAP-085A)."""
        raise NotImplementedError(
            "Organizational Memory is architecture-only (CAP-085A); no deterministic "
            "engine exists yet. See CAP-085B."
        )
