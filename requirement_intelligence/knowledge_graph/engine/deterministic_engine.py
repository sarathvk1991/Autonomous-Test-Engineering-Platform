"""``DeterministicKnowledgeGraphEngine`` — the first real implementation behind
``KnowledgeGraphService`` (CAP-084B, ADR-0023 §D9).

Unlike every previous engine in this platform, this is **not one large engine
class**. It is a thin pipeline orchestrator over independent, deterministic
components — projectors, analyzers, and builders — each owning exactly one
responsibility (Recommendation 1 of ADR-0023: Knowledge Graph owns platform
structure, not execution behaviour, decomposed the same way structurally). The
engine's only job is to call each component once, in the frozen order, and
thread its output into the next:

    HistoricalDatasetReference
        -> HistoricalDatasetProvider -> HistoricalDataset
        -> NodeProjector -> nodes
        -> EdgeProjector -> edges
        -> SubgraphDetector -> subgraphs
        -> ObservationEngine -> observations
        -> FindingEngine -> findings
        -> SummaryBuilder -> summary
        -> MetricsBuilder -> metrics
        -> ResultBuilder -> KnowledgeGraphResult

Pure deterministic function: the same ``HistoricalDatasetReference`` (resolved
through the same provider, under the same policy and rule catalogue) always
produces an identical ``KnowledgeGraphResult`` (up to its own minted identity,
which is itself a pure function of the dataset id).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from requirement_intelligence.knowledge_graph.engine.analysis import (
    FindingEngine,
    ObservationEngine,
    SubgraphDetector,
)
from requirement_intelligence.knowledge_graph.engine.builders import (
    MetricsBuilder,
    ResultBuilder,
    SummaryBuilder,
)
from requirement_intelligence.knowledge_graph.engine.historical_dataset import (
    DeterministicHistoricalDatasetProvider,
    HistoricalDatasetProvider,
)
from requirement_intelligence.knowledge_graph.engine.projection import EdgeProjector, NodeProjector
from requirement_intelligence.knowledge_graph.identity import KnowledgeGraphId
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.result import KnowledgeGraphResult
from requirement_intelligence.knowledge_graph.models.summary import (
    KnowledgeMetrics,
    KnowledgeSummary,
)
from requirement_intelligence.knowledge_graph.policy import KnowledgeGraphPolicy
from requirement_intelligence.knowledge_graph.rules import (
    KnowledgeGraphRuleCatalog,
    default_knowledge_graph_rule_catalog,
)
from requirement_intelligence.knowledge_graph.version import KNOWLEDGE_GRAPH_FRAMEWORK_VERSION


class DeterministicKnowledgeGraphEngine:
    """The first deterministic implementation behind ``KnowledgeGraphService``.

    Consumes only a :class:`HistoricalDatasetReference`, the governed
    :class:`KnowledgeGraphPolicy`, and the governed
    :class:`KnowledgeGraphRuleCatalog`. Every collaborator below owns exactly
    one responsibility so a future statistical, ML, or LLM-based engine can
    reuse the same decomposition without changing the public ``build`` contract.
    """

    def __init__(
        self,
        *,
        policy: KnowledgeGraphPolicy,
        rule_catalog: KnowledgeGraphRuleCatalog | None = None,
        provider: HistoricalDatasetProvider | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Store the governed collaborators this engine reads. Construction only."""
        self._policy = policy
        self._catalog = (
            rule_catalog if rule_catalog is not None else default_knowledge_graph_rule_catalog()
        )
        self._provider = (
            provider if provider is not None else DeterministicHistoricalDatasetProvider()
        )
        self._clock = clock or (lambda: datetime.now(UTC))

        self._node_projector = NodeProjector(policy, self._catalog)
        self._edge_projector = EdgeProjector(policy, self._catalog)
        self._subgraph_detector = SubgraphDetector(policy)
        self._observation_engine = ObservationEngine(policy)
        self._finding_engine = FindingEngine(policy)
        self._summary_builder = SummaryBuilder()
        self._metrics_builder = MetricsBuilder()
        self._result_builder = ResultBuilder()

    def build(self, historical_dataset: HistoricalDatasetReference) -> KnowledgeGraphResult:
        """Build the platform graph for *historical_dataset*. Deterministic."""
        started_at = self._clock()
        graph_id = KnowledgeGraphId.for_dataset(historical_dataset.dataset_id)

        if not self._policy.capability_switches.enable_deterministic_engine:
            return self._empty_result(
                graph_id=graph_id,
                historical_dataset=historical_dataset,
                started_at=started_at,
                completed_at=self._clock(),
                headline=(
                    "Knowledge Graph construction is disabled by policy "
                    "(enable_deterministic_engine=False)."
                ),
            )

        dataset = self._provider.resolve(historical_dataset)
        graph_id_str = str(graph_id)

        nodes = self._node_projector.project(dataset)
        edges = self._edge_projector.project(dataset, nodes)
        subgraphs = self._subgraph_detector.detect(graph_id_str, nodes, edges)
        observations = self._observation_engine.analyze(graph_id_str, nodes, edges, subgraphs)
        findings = self._finding_engine.detect(graph_id_str, nodes, edges, subgraphs)

        summary = self._summary_builder.build(
            self._policy, nodes, edges, subgraphs, observations, findings
        )
        metrics = self._metrics_builder.build(nodes, edges, subgraphs)

        completed_at = self._clock()
        return self._result_builder.build(
            graph_id=graph_id,
            historical_dataset=historical_dataset,
            nodes=nodes,
            edges=edges,
            subgraphs=subgraphs,
            observations=observations,
            findings=findings,
            summary=summary,
            metrics=metrics,
            policy=self._policy,
            framework_version=KNOWLEDGE_GRAPH_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _empty_result(
        self,
        *,
        graph_id: KnowledgeGraphId,
        historical_dataset: HistoricalDatasetReference,
        started_at: datetime,
        completed_at: datetime,
        headline: str,
    ) -> KnowledgeGraphResult:
        """Return the policy-disabled empty result. No projection, no analysis."""
        summary = KnowledgeSummary(
            policy_id=self._policy.policy_id,
            policy_version=self._policy.policy_version,
            total_nodes=0,
            total_edges=0,
            total_subgraphs=0,
            total_observations=0,
            total_findings=0,
            headline=headline,
        )
        metrics = KnowledgeMetrics(
            node_count=0,
            edge_count=0,
            subgraph_count=0,
            connected_component_count=0,
            average_degree=0.0,
            orphan_node_count=0,
        )
        return self._result_builder.build(
            graph_id=graph_id,
            historical_dataset=historical_dataset,
            nodes=(),
            edges=(),
            subgraphs=(),
            observations=(),
            findings=(),
            summary=summary,
            metrics=metrics,
            policy=self._policy,
            framework_version=KNOWLEDGE_GRAPH_FRAMEWORK_VERSION,
            started_at=started_at,
            completed_at=completed_at,
        )
