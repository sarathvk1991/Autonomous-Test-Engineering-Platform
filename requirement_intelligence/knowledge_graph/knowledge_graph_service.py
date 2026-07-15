"""KnowledgeGraphService — the single runtime entry point into the Knowledge Graph
Framework.

Architecture (ADR-0023)
------------------------
``KnowledgeGraphService`` is the permanent **orchestration boundary** of the
Knowledge Graph Framework — the second Layer 2 capability (ADR-0020), following
Continuous Improvement (ADR-0022). Everything outside the subsystem will talk to
graph construction through this one contract; nothing else is a public runtime
surface. It mirrors the role the Continuous Improvement Framework's own runtime
service plays for that subsystem (ADR-0022 §D6): a single seam that will
coordinate collaborators and own none of their work.

Historical Truth only (frozen, ADR-0021 §Stage 8, Recommendation 9 of ADR-0023)
---------------------------------------------------------------------------------
``build`` consumes **only** a :class:`~requirement_intelligence.knowledge_graph.
models.historical_dataset_reference.HistoricalDatasetReference` — provenance
naming a Historical Dataset, never a Layer 1 runtime contract directly and never
an Execution Package artifact. This is the same boundary Continuous Improvement
draws (a stricter boundary than any Layer 1 subsystem's): Knowledge Graph never
imports ``requirement_intelligence.enhancement``, ``.grounding``, ``.validation``,
``.cp1``, ``.quality_governance``, ``.recommendation``, ``.continuous_improvement``,
or ``.execution`` at all. The dependency direction is one-way:

    HistoricalDatasetReference ─▶ KnowledgeGraphService.build
        ─▶ KnowledgeGraphResult

What the service will OWN
    orchestration, lifecycle, dependency coordination, execution ordering, and (in
    a later milestone) assembly of the final :class:`KnowledgeGraphResult`.

What the service does NOT own
    the Historical Dataset itself (ADR-0021 §Stage 6 names its owner), any Layer 1
    subsystem, Continuous Improvement, and the Execution Package. Each is a
    separate owner. A future deterministic, statistical, ML, or LLM Knowledge
    Graph engine is an **internal implementation detail** of the service and can
    be added without changing this contract.

Runtime status (CAP-084A)
    ``build`` is **abstract and dormant** — :class:`DormantKnowledgeGraphService`
    raises :class:`NotImplementedError` on every call. No node is ingested, no
    edge is ingested, no subgraph is partitioned, no observation is recorded, no
    finding is detected, and no historical dataset access exists. A later
    milestone (CAP-084B, mirroring CAP-083B) implements the method behind this
    unchanged signature.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult


class KnowledgeGraphService(ABC):
    """The permanent runtime contract for building one platform graph.

    A single public method, ``build``, derives nodes, edges, subgraphs,
    observations, and findings from a referenced Historical Dataset under a
    governed :class:`KnowledgeGraphPolicy` and returns a
    :class:`KnowledgeGraphResult`. Implementations orchestrate; they delegate
    construction to internal collaborators and own no historical storage, no
    graph storage, themselves.
    """

    @abstractmethod
    def build(
        self,
        historical_dataset: HistoricalDatasetReference,
    ) -> KnowledgeGraphResult:
        """Build the platform graph for the dataset named by *historical_dataset*.

        Parameters
        ----------
        historical_dataset:
            Provenance naming the Historical Dataset to build from — never the
            dataset's content, and never a Layer 1 runtime contract directly.

        Returns
        -------
        KnowledgeGraphResult
            The complete, self-contained record of every node, edge, subgraph,
            observation, and finding built for the dataset.

        Notes
        -----
        Abstract in CAP-084A; a future engine (CAP-084B) implements it behind
        this unchanged signature, exactly as the Continuous Improvement
        Framework's own deterministic engine was implemented in CAP-083B behind
        an unchanged ``improve`` signature.
        """
        raise NotImplementedError


class DormantKnowledgeGraphService(KnowledgeGraphService):
    """The CAP-084A registered default — architecture only, no behaviour.

    Every call to ``build`` raises :class:`NotImplementedError`. This is the
    Knowledge Graph Framework's counterpart to CAP-083A's own dormant service
    (later replaced by CAP-083B's deterministic one) — a placeholder that proves
    the contract is constructible and registered with :class:`PlatformContext`
    before any behaviour exists.
    """

    def build(
        self,
        historical_dataset: HistoricalDatasetReference,
    ) -> KnowledgeGraphResult:
        """Always raise — no Knowledge Graph engine exists yet (CAP-084A)."""
        raise NotImplementedError(
            "KnowledgeGraphService is architecture-only (CAP-084A): no engine "
            "exists yet. A future milestone (CAP-084B) implements 'build' behind "
            "this unchanged signature."
        )
