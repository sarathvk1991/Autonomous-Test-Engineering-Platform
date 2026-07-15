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

What the service OWNS
    orchestration, lifecycle, dependency coordination, and execution ordering.

What the service does NOT own
    the Historical Dataset itself (ADR-0021 §Stage 6 names its owner), any Layer 1
    subsystem, Continuous Improvement, and the Execution Package. Each is a
    separate owner. The deterministic engine (and any future statistical, ML, or
    LLM Knowledge Graph engine) is an **internal implementation detail** of the
    service and can be replaced without changing this contract.

Runtime status (CAP-084B)
    ``build`` is now implemented: :class:`DeterministicKnowledgeGraphService`
    delegates to a private :class:`~requirement_intelligence.knowledge_graph.
    engine.DeterministicKnowledgeGraphEngine` that performs deterministic node
    projection, edge projection, subgraph detection, observation generation, and
    finding detection end to end — via independent, modular collaborators, never
    one large engine. The service is still **not wired into any execution
    pipeline** (nothing calls ``build`` at runtime) and only ``PlatformContext``
    may construct it outside this package — so runtime behaviour is byte-identical
    and the golden baseline is unchanged. Runtime integration is future work,
    exactly as CAP-083B implemented the first deterministic Continuous
    Improvement engine before a later milestone activated it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.knowledge_graph.engine import (
    DeterministicKnowledgeGraphEngine,
    HistoricalDatasetProvider,
)
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult
from requirement_intelligence.knowledge_graph.policy import KnowledgeGraphPolicy
from requirement_intelligence.knowledge_graph.rules import KnowledgeGraphRuleCatalog


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
        Abstract in CAP-084A; :class:`DeterministicKnowledgeGraphService`
        (CAP-084B) implements it behind this unchanged signature.
        """
        raise NotImplementedError


class DeterministicKnowledgeGraphService(KnowledgeGraphService):
    """The registered default service (CAP-084B) — thin orchestration over the engine.

    Holds a private :class:`~requirement_intelligence.knowledge_graph.engine.
    DeterministicKnowledgeGraphEngine` and delegates ``build`` to it, owning
    only the public boundary and construction. It **computes nothing itself**:
    the engine's modular projectors, analyzers, and builders perform node
    projection, edge projection, subgraph detection, observation generation,
    finding detection, and result assembly. Mirrors how the Continuous
    Improvement subsystem's own deterministic runtime service delegates to its
    private engine (ADR-0022) — a thin service, real behaviour one layer down.
    """

    def __init__(
        self,
        *,
        policy: KnowledgeGraphPolicy,
        rule_catalog: KnowledgeGraphRuleCatalog | None = None,
        provider: HistoricalDatasetProvider | None = None,
    ) -> None:
        """Construct the private deterministic engine this service delegates to."""
        self._engine = DeterministicKnowledgeGraphEngine(
            policy=policy, rule_catalog=rule_catalog, provider=provider
        )

    def build(
        self,
        historical_dataset: HistoricalDatasetReference,
    ) -> KnowledgeGraphResult:
        """Build the platform graph via the deterministic engine — delegation only."""
        return self._engine.build(historical_dataset)
