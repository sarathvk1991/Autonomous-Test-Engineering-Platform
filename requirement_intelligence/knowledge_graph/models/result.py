"""The :class:`KnowledgeGraphResult` — the frozen runtime contract of the Knowledge
Graph Framework (CAP-084A architecture freeze, ADR-0023 §D3/§D4; permanently
certified as the sole runtime contract by CAP-084B.1, ADR-0023 §D11).

CAP-084A freezes the architecture before any engine exists — exactly as CAP-083A
did for ``ContinuousImprovementResult`` before CAP-083B's deterministic engine, and
CAP-082A did for ``RecommendationResult`` before CAP-082B's. CAP-084B then
implements the first real engine behind this unchanged contract, and CAP-084B.1
permanently certifies ``KnowledgeGraphResult`` as the canonical runtime contract —
no field, computation, or signature changes for that certification, exactly as
CAP-083B.1 certified ``ContinuousImprovementResult`` (ADR-0022 §D10).

It **is**:

* the complete runtime output — the single object a future deterministic
  Knowledge Graph engine (reserved) will cross from into serialization, exactly
  as ``ContinuousImprovementResult`` crosses from the Continuous Improvement
  Framework's own deterministic engine;
* the canonical runtime contract — the only Knowledge Graph aggregate, the second
  Layer 2 runtime contract (ADR-0020), a peer to no Layer 1 result (it consumes
  none of them directly, ADR-0021 §Stage 8) and consumed by no other Layer 2
  capability yet;
* independently versioned — ``result_version`` (:class:`KnowledgeGraphResultVersion`)
  evolves on its own axis, never forcing (or forced by) the framework, policy, or
  node/edge/observation schema versions, and vice versa (ADR-0023 §D5/§D6,
  mirroring ADR-0022 §D10);
* deterministic — a pure function of the resolved Historical Dataset and the
  governed policy; no randomness, no wall-clock dependence beyond the injected
  clock;
* immutable — ``frozen=True`` (via ``Schema``), tuple-backed collections, no field
  can change after construction;
* self-contained — every node, edge, subgraph, observation, finding, summary
  metric, and consumed historical-dataset reference already lives here, so the
  result is reproducible with no need to re-run graph construction or inspect any
  runtime service (mirrors Recommendation 8 of ADR-0022);
* explainable — every node, edge, subgraph, observation, and finding is
  reconstructable from this object alone; no upstream subsystem, engine,
  provider, policy, or service need ever be inspected or re-run (Recommendation 8
  of ADR-0023);
* serializer-independent — a future serializer projects this object; this object
  never depends on a serializer existing;
* execution-package-independent — this object exists and is fully meaningful with
  no Execution Package, CLI phase, or manifest wired to it at all (CAP-084A —
  none of those exist yet);
* historical-storage-independent — this object never depends on a real Historical
  Dataset implementation existing; it references one by id only
  (``HistoricalDatasetReference``) and is equally valid whether that dataset is
  backed by a future deterministic provider or a real implementation
  (Recommendation 5 of ADR-0023);
* engine-independent — this object's shape does not depend on which engine
  produced it; a future deterministic, statistical, ML, or LLM engine emits the
  identical contract (Recommendation 5/7 of ADR-0023).

It is **not**:

* Runtime Truth; Historical Truth; a report; Markdown; JSON formatting; an
  execution artifact; a manifest; a CLI object; a renderer; a serializer; a
  transport object; a projection; an Execution Package object; a predictor; an
  optimizer; the Knowledge Graph engine itself; a graph database; a graph query
  surface; a service; a policy; a builder; a Historical Dataset.

Each of those is a separate, later owner that *consumes* this object (or, for
Historical Dataset, a separate, earlier owner this object *references* — never
embeds); none of them computes anything this object doesn't already carry.

The validators enforce cross-referential integrity only. No node, edge, subgraph,
observation, or finding is computed here (CAP-084A architecture freeze, ADR-0023).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from requirement_intelligence.knowledge_graph.identity import (
    KnowledgeGraphFrameworkVersion,
    KnowledgeGraphId,
    KnowledgeGraphResultId,
    KnowledgeGraphResultVersion,
    KnowledgePolicyId,
    KnowledgePolicyVersion,
)
from requirement_intelligence.knowledge_graph.models.edge import KnowledgeEdge
from requirement_intelligence.knowledge_graph.models.finding import KnowledgeFinding
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.knowledge_graph.models.node import KnowledgeNode
from requirement_intelligence.knowledge_graph.models.observation import KnowledgeObservation
from requirement_intelligence.knowledge_graph.models.subgraph import KnowledgeSubgraph
from requirement_intelligence.knowledge_graph.models.summary import (
    KnowledgeMetrics,
    KnowledgeSummary,
)
from shared.contracts.base import Schema

#: Version of the ``KnowledgeGraphResult`` **runtime contract** schema.
#: Independent of every other Knowledge Graph version axis —
#: ``KnowledgeGraphFrameworkVersion``, ``KnowledgePolicyVersion``,
#: ``KnowledgeNodeVersion``, ``KnowledgeEdgeVersion``,
#: ``KnowledgeObservationVersion`` — a change here never forces any of those to
#: change, and vice versa (frozen, CAP-084A, ADR-0023 §D5/§D6, mirroring
#: ``ContinuousImprovementResultVersion``, ADR-0022 §D4/§D10).
KNOWLEDGE_GRAPH_RESULT_VERSION = KnowledgeGraphResultVersion(1, 0, 0)


class KnowledgeGraphResult(Schema):
    """The complete, deterministic platform graph for one build.

    ``KnowledgeGraphResult`` is the **permanent runtime contract** — the only
    Knowledge Graph object that crosses into serialization. It is **not** a
    report, an execution artifact, serialization, a renderer, a graph database, or
    a calculator: it already contains everything (every node, edge, subgraph,
    observation, finding, the summary, the metrics, the governing policy
    identity/version, and the consumed historical-dataset reference) any
    downstream projection needs.

    **Serialization invariant (frozen, mirrors ADR-0022 §D8).** Every future
    execution artifact concerning Knowledge Graph will be a **pure projection** of
    a ``KnowledgeGraphResult`` — reproducible from it alone, computing nothing. A
    renderer must never call a Knowledge Graph engine, a graph database,
    ``PlatformContext``, add a node, add an edge, partition a subgraph, observe a
    fact, name a finding, compute a metric, or invoke a policy.

    **Ownership (frozen, CAP-084A, ADR-0023 §D3).** This is the **sole** owner of
    every node, edge, subgraph, observation, finding, summary metric, policy
    identity/version, and consumed historical-dataset reference produced by the
    Knowledge Graph Framework. Nothing upstream and nothing downstream owns
    these — no execution artifact, manifest, subsystem-local relationship model
    (e.g. Requirement Enhancement's ``RelationshipGraph``), or other subsystem may
    duplicate that ownership (Recommendation 10 of ADR-0023). The future engine
    that assembles this object and any future graph storage it privately consults
    are both engine-internal implementation detail — neither is part of this
    contract, and neither is named by any field here.

    **Explainability (frozen, CAP-084A, Recommendation 8 of ADR-0023).** Every
    node, edge, subgraph, observation, and finding is explainable entirely from
    this object's contents, traceable through the referenced
    ``HistoricalDatasetReference`` down to Runtime Truth and execution inputs
    (ADR-0021 §Stage 8) — no downstream consumer should ever need to re-run graph
    construction or inspect the engine, the storage, the service, or
    ``PlatformContext``.

    **Truth Hierarchy boundary (frozen, ADR-0021 §Stage 3).** This result is
    Derived Knowledge: reproducible from the ``HistoricalDatasetReference`` it
    consumed, but never itself Historical Truth or Runtime Truth. It must never be
    written back into the Historical Dataset it was computed from, and no future
    Knowledge Graph build may consume a prior ``KnowledgeGraphResult``,
    ``KnowledgeNode``, ``KnowledgeEdge``, ``KnowledgeSubgraph``,
    ``KnowledgeObservation``, or ``KnowledgeFinding`` as an input (mirrors
    Recommendation 11 of ADR-0022: Derived Knowledge must never recursively
    consume Derived Knowledge).

    **Runtime boundary (frozen, CAP-084A; permanently certified, CAP-084B.1,
    ADR-0023 §D11).** Runtime ends at this object: ``HistoricalDatasetReference``
    → (private ``HistoricalDatasetProvider`` → engine-internal ``HistoricalDataset``)
    → ``DeterministicKnowledgeGraphEngine`` → ``KnowledgeGraphResult``. Everything
    after that — serialization, reports, Markdown, JSON, graph storage, the
    Execution Package — is projection only and must compute nothing; none of it
    exists yet (CAP-084A/CAP-084B introduce none of it). This boundary is now
    permanently frozen: future serializers, reports, and Execution Package
    integrations must consume ``KnowledgeGraphResult`` only, never the engine,
    the provider, the service, or ``PlatformContext``.

    **Golden regression boundary (frozen).** A future golden dataset compares this
    object's content, never Markdown or JSON formatting. A presentation change
    must never invalidate a runtime regression baseline; only a change to this
    object's content (or its ``result_version``) is a runtime regression.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    result_id: KnowledgeGraphResultId = Field(..., description="Deterministic result id.")
    graph_id: KnowledgeGraphId = Field(
        ..., description="Deterministic identity of the canonical graph this result represents."
    )
    historical_dataset: HistoricalDatasetReference = Field(
        ..., description="Provenance of the historical dataset this graph was built from."
    )

    nodes: tuple[KnowledgeNode, ...] = Field(
        default=(), description="Every platform entity node recorded in this graph."
    )
    edges: tuple[KnowledgeEdge, ...] = Field(
        default=(), description="Every governed relationship edge recorded in this graph."
    )
    subgraphs: tuple[KnowledgeSubgraph, ...] = Field(
        default=(), description="Every coherent graph partition identified for this build."
    )
    observations: tuple[KnowledgeObservation, ...] = Field(
        default=(), description="Every deterministic structural fact recorded for this build."
    )
    findings: tuple[KnowledgeFinding, ...] = Field(
        default=(), description="Every deterministic structural issue recorded for this build."
    )
    summary: KnowledgeSummary = Field(..., description="The headline summary of this build.")
    metrics: KnowledgeMetrics = Field(..., description="The deterministic numeric roll-up.")

    policy_id: KnowledgePolicyId = Field(..., description="Identity of the governing policy.")
    policy_version: KnowledgePolicyVersion = Field(
        ..., description="Version of the governing policy."
    )
    framework_version: KnowledgeGraphFrameworkVersion = Field(...)
    result_version: KnowledgeGraphResultVersion = Field(
        default=KNOWLEDGE_GRAPH_RESULT_VERSION,
        description="Version of the KnowledgeGraphResult runtime-contract schema.",
    )
    started_at: datetime = Field(..., description="When this Knowledge Graph build started.")
    completed_at: datetime = Field(..., description="When this Knowledge Graph build completed.")

    @model_validator(mode="after")
    def _validate_result(self) -> KnowledgeGraphResult:
        """Cross-references and lifetime must be internally consistent."""
        if self.completed_at < self.started_at:
            raise ValueError("completed_at precedes started_at.")

        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("nodes must not contain duplicate ids.")
        known_node_ids = set(node_ids)

        edge_ids = [edge.edge_id for edge in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("edges must not contain duplicate ids.")
        known_edge_ids = set(edge_ids)

        for edge in self.edges:
            if edge.source_node_id not in known_node_ids:
                raise ValueError(
                    f"KnowledgeEdge {edge.edge_id!r} references source node "
                    f"{edge.source_node_id!r}, which is not present in this result's nodes."
                )
            if edge.target_node_id not in known_node_ids:
                raise ValueError(
                    f"KnowledgeEdge {edge.edge_id!r} references target node "
                    f"{edge.target_node_id!r}, which is not present in this result's nodes."
                )

        subgraph_ids = [subgraph.subgraph_id for subgraph in self.subgraphs]
        if len(subgraph_ids) != len(set(subgraph_ids)):
            raise ValueError("subgraphs must not contain duplicate ids.")
        for subgraph in self.subgraphs:
            for node_id in subgraph.node_ids:
                if node_id not in known_node_ids:
                    raise ValueError(
                        f"KnowledgeSubgraph {subgraph.subgraph_id!r} references node "
                        f"{node_id!r}, which is not present in this result's nodes."
                    )
            for edge_id in subgraph.edge_ids:
                if edge_id not in known_edge_ids:
                    raise ValueError(
                        f"KnowledgeSubgraph {subgraph.subgraph_id!r} references edge "
                        f"{edge_id!r}, which is not present in this result's edges."
                    )

        observation_ids = [observation.observation_id for observation in self.observations]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("observations must not contain duplicate ids.")
        for observation in self.observations:
            for node_id in observation.subject_node_ids:
                if node_id not in known_node_ids:
                    raise ValueError(
                        f"KnowledgeObservation {observation.observation_id!r} references "
                        f"node {node_id!r}, which is not present in this result's nodes."
                    )
            for edge_id in observation.subject_edge_ids:
                if edge_id not in known_edge_ids:
                    raise ValueError(
                        f"KnowledgeObservation {observation.observation_id!r} references "
                        f"edge {edge_id!r}, which is not present in this result's edges."
                    )

        finding_ids = [finding.finding_id for finding in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("findings must not contain duplicate ids.")
        for finding in self.findings:
            for node_id in finding.subject_node_ids:
                if node_id not in known_node_ids:
                    raise ValueError(
                        f"KnowledgeFinding {finding.finding_id!r} references node "
                        f"{node_id!r}, which is not present in this result's nodes."
                    )
            for edge_id in finding.subject_edge_ids:
                if edge_id not in known_edge_ids:
                    raise ValueError(
                        f"KnowledgeFinding {finding.finding_id!r} references edge "
                        f"{edge_id!r}, which is not present in this result's edges."
                    )

        return self
