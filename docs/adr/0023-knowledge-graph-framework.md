# ADR-0023 — Knowledge Graph Framework

- **Status:** Proposed (CAP-084A — Architecture & Governance Freeze)
- **Date:** 2026-07-15 (CAP-084A — Architecture & Governance Freeze)
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** a future deterministic-engine milestone (CAP-084B, reserved, mirroring how CAP-083B implemented the first deterministic Continuous Improvement engine behind ADR-0022).
- **Governing design:** `docs/proposals/knowledge-graph-framework.md`
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — this is the second Layer 2 capability it names) and ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — this framework's every boundary is a direct application of ADR-0021's Truth Hierarchy). Also informed by ADR-0022 (Continuous Improvement Framework — the first Layer 2 capability, and the direct architectural precedent this ADR mirrors).
- **Runtime status:** **Not implemented (CAP-084A).** `KnowledgeGraphService.build` is an abstract, dormant contract; `DormantKnowledgeGraphService` raises `NotImplementedError` on every call. `PlatformContext.create_knowledge_graph_service()` constructs the dormant service by default. Nothing calls `build` at runtime — no CLI phase, no Execution Package field, no historical dataset storage exists — so runtime behaviour remains byte-identical and the golden baseline is unchanged. The Architecture Version remains **1.2.0** and no frozen contract of any Layer 1 or Layer 2 subsystem changed.

## Problem

ADR-0020 named Continuous Learning as Layer 2 and reserved four capabilities inside it: CAP-083 (Continuous Improvement), CAP-084 (Knowledge Graph), CAP-085 (Organizational Memory), CAP-086 (Learning Framework). ADR-0022 built the first of those — Continuous Improvement observes recurrence across a Historical Dataset. Neither it nor any Layer 1 subsystem answers a different, structural question: *how does everything in this platform relate to everything else?* Which requirement traces to which evidence, which module depends on which component, which execution generated which finding, which recommendation addresses which requirement — across the whole platform, not within one execution and not within one subsystem's own local model of its own concerns.

Left unbuilt, and built without a frozen architecture first, the first cross-subsystem structural capability would have to invent, under deadline pressure, exactly the kind of ad hoc answer ADR-0021 §Stage 2 warned against: duplicated relationships, inconsistent node identities, competing local "graphs" each claiming to be authoritative, hidden coupling between subsystems that should stay independent.

### Stage 0 — Repository assessment

Before writing this ADR, every existing graph-like structure in the repository was reviewed:

- **Requirement Enhancement's `RelationshipGraph`** (`requirement_intelligence/enhancement/models/relationships.py`) already has real graph shape — a node set (`requirement_ids`) and typed, directed edges (`RequirementRelationship`: source → target with a governed `RelationshipType` and rationale) — with a validator enforcing every edge references nodes present in the graph. But it is strictly **single-execution**: it is the sole owner of `RequirementEnhancementResult`, docstring'd as "the single canonical requirement-relationship graph for **one enhancement run**," and carries `analysis_id`/`execution_id`, never a dataset/corpus reference. It performs no graph algorithm — no cycle detection, no traversal, no derived metric.
- **Grounding's traceability** (`requirement_intelligence/grounding/models/evidence.py`) is graph-*shaped* in its own docstring ("one edge of the traceability graph") but is implemented as a flat `evidence_links` fan-out hung off each `GroundedRequirement` — no separate graph container, no shared node set, no cross-requirement structure.
- **Validation** has no graph at all — it deliberately enforces Rule Independence (`validation_rule.py`): rules depend only on the response being validated, never on sibling rule output or execution order. The only "dependency" concept is a fixed enum layer ordering, architecture-mandated sequencing, not a relationship graph.
- **Recommendation's `RecommendationReference`** (`requirement_intelligence/recommendation/models/recommendation.py`) is a flat citation — `source`, `referenced_id`, `referenced_version` — never a graph edge; there is no node/edge validator, no shared node set, no graph container.
- **Continuous Improvement's `contributing_execution_ids`** (on `ImprovementFinding` / `ImprovementTrend`) is a flat id list, not a graph — validated only for count-matches-cardinality and no duplicates.
- **Engineering Context's `ContextCorrelation`** (`requirement_intelligence/context_orchestration/models/engineering_context.py`) is the closest existing structure to a genuine cross-artifact graph: an asserted `from_artifact_id` → `to_artifact_id` relationship with a `basis`, wrapped by `ContextDependencies`, which *already reserves* a `related_context_ids` slot for cross-context (cross-execution) linkage. Today it is empty — "correlation inference is a later milestone" — a reserved container, not a populated or queryable graph.
- A full-repository grep for `knowledge_graph`, `KnowledgeGraph`, and "platform graph" found **no code module anywhere** — every hit is documentation only (ADR-0020's roadmap reservation, ADR-0022's reiteration of that reservation, and a one-row intent table entry in `docs/architecture/ai-reasoning-contract.md` / `requirement-analysis-service.md` noting that "persisted, queryable relationships between artifacts... must strengthen, not replace, evidence grounding"). **This is a greenfield capability.**

**Why none of the above is a platform Knowledge Graph.** Every existing graph-like structure is either (a) strictly execution-scoped and owned by exactly one Layer 1 subsystem's own runtime contract (Enhancement's `RelationshipGraph`), (b) a flat reference/citation with no shared node identity or cross-object validator (Grounding's evidence links, Recommendation's references, Continuous Improvement's execution-id lists), or (c) an intentionally empty, reserved slot for future cross-execution linkage that no subsystem populates or queries today (Engineering Context's `ContextDependencies`). None of them names entities with a platform-wide, cross-subsystem identity; none of them is queryable across executions; none of them is anyone's job to keep consistent as a single structural source of truth. That job is exactly what ADR-0020 reserved as CAP-084.

**Why this becomes a new Layer 2 capability, not an extension of an existing one.** Folding a cross-subsystem structural graph into any Layer 1 subsystem would make a single-execution judge (or a single subsystem's own local relationship model) also an owner of platform-wide structure — exactly the coupling ADR-0001 forbids within a layer, and exactly the layer-boundary violation ADR-0020 §Stage 3 forbids across layers, and exactly the same reasoning ADR-0022 §D1 already applied to justify Continuous Improvement's own placement in Layer 2. Knowledge Graph is a distinct responsibility with a distinct owner: it is a **consumer only** of Historical Truth (Recommendation 9 below) and a **projector only** of already-computed, subsystem-local structures (Recommendation 10 below) — never a re-implementer of Requirement Enhancement's, Grounding's, or any other subsystem's own reasoning.

> No architectural weakness was found that would block this milestone. Every existing graph-like structure remains exactly where it is, owned by exactly the subsystem that already owns it. Proceeding with a pure architecture and governance freeze.

## Decision

Introduce a new governed subsystem, **`requirement_intelligence/knowledge_graph/`**, that will own the platform's single structural authority — nodes, governed relationship edges, subgraphs, deterministic observations, and structural findings — built from a **Historical Dataset**, never from a single execution's Runtime Truth directly and never by re-implementing any Layer 1 subsystem's own reasoning. It:

1. Introduces canonical, immutable models — `KnowledgeNode`, `KnowledgeEdge`, `KnowledgeSubgraph`, `KnowledgeObservation`, `KnowledgeFinding`, `KnowledgeSummary`, `KnowledgeMetrics`, `HistoricalDatasetReference` (duplicated locally, mirroring ADR-0022's own duplication of the same-shaped type), and `KnowledgeGraphResult` — following the `Schema` conventions and the typed-identity pattern of ADR-0015–ADR-0019 and ADR-0022.
2. Introduces strongly typed identities — `KnowledgePolicyId`, `KnowledgeGraphId`, `KnowledgeNodeId`, `KnowledgeEdgeId`, `KnowledgeSubgraphId`, `KnowledgeObservationId`, `KnowledgeFindingId`, `KnowledgeGraphResultId` — deterministic value objects, no UUIDs, no timestamps, no randomness.
3. Introduces independent version axes — `KnowledgeGraphFrameworkVersion`, `KnowledgePolicyVersion`, `KnowledgeNodeVersion` (reserved), `KnowledgeEdgeVersion` (reserved), `KnowledgeObservationVersion` (reserved), `KnowledgeGraphResultVersion` — each evolving without forcing the others to change (Recommendation 5, ADR-0022 precedent).
4. Introduces a governed `KnowledgeGraphPolicy` (immutable data: capability switches, deterministic thresholds) with a `KnowledgeGraphPolicyBuilder` and `default_knowledge_graph_policy()`.
5. Fixes the single runtime boundary — `KnowledgeGraphService.build(historical_dataset: HistoricalDatasetReference) -> KnowledgeGraphResult` — as an **abstract, dormant contract**. `PlatformContext` gains `create_knowledge_graph_policy()` and `create_knowledge_graph_service()`.

The Knowledge Graph Framework consumes **Historical Truth only** — never a Layer 1 runtime contract directly, never Continuous Improvement's own `ContinuousImprovementResult`, never an Execution Package artifact, never a report or a manifest (ADR-0021 §Stage 7/§Stage 8). It is the **second Layer 2 peer**, alongside Continuous Improvement; each owns a disjoint responsibility and neither imports the other.

**CAP-084A establishes the architecture only.** No node is ingested, no edge is ingested, no subgraph is partitioned, no observation is recorded, no finding is detected, no historical dataset is built, and nothing is wired into a runtime path. Runtime behaviour is byte-identical; the golden baseline is unchanged; the Architecture Version remains 1.2.0.

The full model and roadmap is in `docs/proposals/knowledge-graph-framework.md`.

---

## D1 — Why Knowledge Graph is a new, Layer 2 subsystem, never an extension of a Layer 1 capability or of Continuous Improvement

A cross-subsystem structural question — *given every entity and relationship this platform has ever produced, how does everything connect?* — is not a question any Layer 1 subsystem asks (each reasons over one execution) and not a question Continuous Improvement asks either (it observes recurrence in *values* across executions — findings, trends, opportunities — never the *shape* of relationships between entities). Knowledge Graph owns **platform structure**, not execution behavior (Recommendation 1). Folding it into any existing subsystem would make a single-execution judge, or a value-observing capability, also an owner of cross-subsystem structural relationships — exactly the coupling ADR-0001 forbids within a layer and ADR-0020 §Stage 3 forbids across layers. Knowledge Graph is a distinct responsibility with a distinct owner, and — like Continuous Improvement — a **consumer only** of Historical Truth.

## D2 — Why Knowledge Graph consumes a `HistoricalDatasetReference`, never a Layer 1 result or a `ContinuousImprovementResult` directly

Exactly mirroring ADR-0022 §D2's reasoning (lifted from a dataset of executions to a dataset of executions the graph is built from): `HistoricalDatasetReference` names which dataset, which version, what execution range, what governed history window, and when the reference was minted — never the dataset's content, never a Layer 1 result embedded inside it, and never a prior `ContinuousImprovementResult` (Continuous Improvement's own Derived Knowledge is a peer output, not an upstream input Knowledge Graph may consume — see D3). This is why `KnowledgeGraphService.build` takes exactly one parameter: Knowledge Graph, like Continuous Improvement, is a Layer 2 capability with exactly one upstream concept to consume — the Historical Dataset — however many Layer 1 executions and however many local relationship models (e.g. `RelationshipGraph` instances) that dataset ultimately aggregates.

## D3 — Why `KnowledgeGraphResult` is Derived Knowledge, never Historical Truth or another Layer 2 capability's Derived Knowledge

The runtime contract is `KnowledgeGraphResult` — the second Layer 2 runtime contract, sitting one level above Runtime Truth in ADR-0021's Truth Hierarchy, exactly where `ContinuousImprovementResult` sits. It is **Derived Knowledge**: reproducible from the `HistoricalDatasetReference` it consumed, but never itself canonical history. It must never be written back into the Historical Dataset it was computed from, and it must never recursively consume a prior `KnowledgeGraphResult` or any of its constituents (mirrors ADR-0022 Recommendation 11's Derived-Knowledge-never-consumes-Derived-Knowledge principle, applied here). It is also a **peer**, not a consumer, of `ContinuousImprovementResult`: two Layer 2 capabilities sitting at the same Truth Hierarchy level do not consume one another's output without a deliberate, explicitly-declared future ADR — none exists today, so Knowledge Graph imports nothing from `continuous_improvement`.

## D4 — Why the models compute nothing (assembly targets only)

Every canonical model is `frozen`, tuple-backed, camelCase, and free of UUIDs/randomness, exactly like every prior subsystem's models. None computes a value: a future engine populates them. The only logic present is validator *invariants* that enforce cross-referential integrity: every `KnowledgeEdge`'s endpoints must exist among the result's `KnowledgeNode` entries; every `KnowledgeSubgraph`'s member node/edge ids must exist among the result's own nodes/edges; every `KnowledgeObservation`'s and `KnowledgeFinding`'s subject ids must exist among the result's nodes/edges; a `KnowledgeFinding` must reference at least one node or edge (mirrors `ImprovementOpportunity`'s "at least one reference" invariant, ADR-0022 §D4) — a structural issue with no traceable evidence is not explainable and must never be constructible.

## D5 — Why identities are deterministic and independently versioned

`KnowledgeGraphId.for_dataset(dataset_id)`, `KnowledgeNodeId.for_entity(node_type, referenced_id)`, `KnowledgeEdgeId.for_relationship(edge_type, source_node_id, target_node_id)`, `KnowledgeSubgraphId.for_ordinal`, `KnowledgeObservationId.for_ordinal`, `KnowledgeFindingId.for_ordinal`, and `KnowledgeGraphResultId.for_graph(graph_id)` are **pure functions** of their inputs — no clock, no UUID — so the same historical dataset always mints the same graph, the same entity always mints the same node, and a result is reproducible and comparable across builds over that dataset. This is the same discipline ADR-0022 §D5 froze for Continuous Improvement's own identities, lifted here from dataset-scoped-result to dataset-scoped-graph-and-result (two levels: `KnowledgeGraphId` names *which graph*, `KnowledgeGraphResultId` names *which build's result* of that graph). Six distinct version axes evolve **independently** (Recommendation 5 below); like every prior subsystem, no existing identifier is retyped, and the base identifier/version classes are duplicated (not imported) from `continuous_improvement` — the eventual home remains `shared/` (ADR-0015 §C, ADR-0016 §D6, ADR-0017 identity module docstring, ADR-0018 §D5, ADR-0019 §D5, ADR-0022 identity module docstring).

## D6 — Why the service boundary is fixed before any behaviour (dormant)

The subsystem exposes exactly one runtime entry point: `KnowledgeGraphService`, an abstract contract with a single method — `build(historical_dataset) -> KnowledgeGraphResult`. Everything else in the package (models, identities, policy) is internal. The service depends only on `HistoricalDatasetReference` — never on any Layer 1 *implementation* class, never on Continuous Improvement's own implementation, and never on the Historical Dataset's own implementation, which does not exist yet. Fixing the boundary *before* implementing any behaviour is what lets a later milestone (deterministic graph construction, CAP-084B) land behind the unchanged `build` signature, exactly as ADR-0022 §D6 did for `ContinuousImprovementService.improve`.

## D7 — Explainability first: every node, edge, subgraph, observation, and finding must be traceable to execution inputs

`KnowledgeNode` carries only a `referenced_id` naming the platform entity it represents — never a copy of that entity's content (Recommendation 2). `KnowledgeEdge` connects two node ids by governed `KnowledgeEdgeType` only — never a free-form relationship string (Recommendation 3). `KnowledgeSubgraph` references member nodes/edges by id only, never by embedding them. `KnowledgeObservation` and `KnowledgeFinding` each carry `subject_node_ids` / `subject_edge_ids` naming exactly what they concern, by id only. The model validators reject a subgraph, observation, or finding that references a node or edge outside the result's own sets, and reject a finding with zero subject references — a structural issue with no traceable evidence is not explainable and must never be constructible. This realizes ADR-0021 §Stage 8's historical explainability chain (`Historical Dataset → Runtime Contracts → Execution Inputs`) as a hard model invariant from the outset, exactly as ADR-0022 §D7 did for Continuous Improvement one capability over (Recommendation 8).

## D8 — Runtime vs. Execution Package boundary, frozen in advance

Exactly as ADR-0022 §D8 froze `ContinuousImprovementResult`'s serialization invariant before any serializer, Execution Package integration, or reporting capability existed, this milestone freezes `KnowledgeGraphResult`'s boundary before any Knowledge Graph serializer, Execution Package integration, dashboard, or graph query surface exists (Recommendation 8):

```
HistoricalDatasetReference → KnowledgeGraphService.build → KnowledgeGraphResult
    → Execution Package (future) → JSON / Markdown / reports
    → Graph storage (future, e.g. Neo4j, RDF, property graph, SQL, in-memory)
    → Graph traversal / embeddings / Graph RAG (future)
```

A future renderer must never call a Knowledge Graph engine, `PlatformContext`, add a node, add an edge, partition a subgraph, observe a fact, name a finding, compute a metric, or invoke a policy — rendering will be projection only. A future graph storage implementation (Neo4j, RDF, a property graph, SQL, or in-memory) must be swappable without changing `KnowledgeGraphResult`, the service signature, or any consumer of either (Recommendation 5).

## D9 — Local relationship models remain subsystem-local; Knowledge Graph is the single structural authority they may project into, never a competitor they must be rewritten to feed

Requirement Enhancement's `RelationshipGraph` (and any future subsystem-local relationship model) remains exactly where it is: the sole owner of one execution's own requirement-relationship structure, unchanged by this ADR. It does not evolve into a competing platform graph, and it is not deprecated, migrated, or restructured by CAP-084A. Instead, a future Knowledge Graph engine may **project** it — read it as one of many inputs and translate its nodes/edges into `KnowledgeNode` / `KnowledgeEdge` entries — without `RelationshipGraph` itself changing shape, and without Requirement Enhancement importing anything from `knowledge_graph` (Recommendation 10). This preserves single ownership of platform-wide structural relationships in exactly one place while letting every subsystem keep its own internal reasoning model exactly as it is today.

---

### Recommendation 1 — Knowledge Graph owns platform structure, not execution behavior

It never owns Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, Continuous Improvement, or the Execution Package. It never imports a Layer 1 subsystem, and it never imports Continuous Improvement — a stricter boundary than any Layer 1 subsystem imposes on its own peers, because Knowledge Graph's only upstream concept, like Continuous Improvement's, is the Historical Dataset (ADR-0021 §Stage 6), referenced by `HistoricalDatasetReference`, never a Layer 1 result or another Layer 2 capability's result embedded directly.

### Recommendation 2 — Nodes reference runtime contracts; they never duplicate them

`KnowledgeNode` carries `referenced_id` — the id of the platform entity it represents — never a copy of that entity's content. Enforced structurally: `KnowledgeNode` has no field capable of holding copied Runtime Truth, Historical Truth, or Derived Knowledge content, exactly mirroring `RecommendationReference`'s reference-not-copy convention (ADR-0019) and `ImprovementFinding`'s `contributing_execution_ids` (ADR-0022).

### Recommendation 3 — Edges are governed vocabulary, never free-form

`KnowledgeEdge.edge_type` is drawn exclusively from the governed `KnowledgeEdgeType` enum (`DEPENDS_ON`, `IMPLEMENTS`, `GENERATED_BY`, `REFERENCES`, `TRACEABLE_TO`, `DERIVED_FROM`, `RELATED_TO`, `BELONGS_TO`, `USES`). No free-form relationship string is ever accepted; a future engine or a future edge type is added by an additive `StrEnum` member, never by relaxing the field to a plain string.

### Recommendation 4 — `KnowledgeGraphResult` is the single runtime authority

The Execution Package, the CLI, reports, and future dashboards must consume only `KnowledgeGraphResult`. No other object in this subsystem is a runtime contract — not `KnowledgeGraphService`, not a future engine, not a future graph storage implementation.

### Recommendation 5 — Graph storage is an implementation detail

Graph storage — a future Neo4j, RDF, property graph, SQL, or in-memory implementation — is never part of this contract. Future storage implementations must be swappable behind `KnowledgeGraphService.build`'s unchanged signature without changing `KnowledgeGraphResult`, `HistoricalDatasetReference`, or `KnowledgeGraphPolicy` (mirrors ADR-0022 Recommendation 10's Historical Dataset Resolution Principle, applied here to graph storage instead of historical storage).

### Recommendation 6 — The graph is structural; prediction, optimization, and autonomy belong to higher layers

Knowledge Graph observes and records structure only. Predictions belong to Layer 4 (Prediction & Insights). Optimization belongs to Layer 5 (Optimization). Autonomy belongs to Layer 6 (Autonomous Engineering). No field, model, or future engine in this subsystem estimates a future value, proposes a plan, or acts on the platform — those are separate, later owners (ADR-0020).

### Recommendation 7 — Graph observations are deterministic; no probabilistic or LLM reasoning

`KnowledgeObservation` and `KnowledgeFinding` are both structural facts, computed deterministically from the graph's own already-recorded nodes and edges — no AI, no prediction, no statistical forecasting, no clustering, no embeddings, no semantic similarity, no LLM reasoning. A future statistical, ML, or LLM-based graph *reasoning* capability is a distinct, higher-layer concern (Recommendation 6) and, if ever built as a peer variant of graph construction itself, must implement the identical `KnowledgeGraphService.build` contract without changing `KnowledgeGraphResult`'s shape (mirrors ADR-0022 Recommendation 5).

### Recommendation 8 — Explainability first

Every node, edge, subgraph, observation, and finding must be explainable entirely from `KnowledgeGraphResult` alone, traceable through `HistoricalDatasetReference` down to Runtime Truth and execution inputs. No hidden structural state. Enforced today by the model validators' cross-referential-integrity and "at least one reference" invariants (§D4/§D7) — the invariant exists before any engine could violate it.

### Recommendation 9 — Preserve the Truth Hierarchy (mandatory, ADR-0021 §Stage 3/Recommendation 11)

This capability explicitly declares its Truth Hierarchy level, as ADR-0021 Recommendation 11 requires of every future Layer 2–7 capability:

- **Consumes:** Historical Truth (via `HistoricalDatasetReference`).
- **Produces:** Derived Knowledge (`KnowledgeGraphResult`).

It must never blur those constitutional layers — `KnowledgeGraphResult` is never written back as Historical Truth, `HistoricalDatasetReference` never embeds Runtime Truth directly, and `KnowledgeGraphResult` never recursively consumes a prior `KnowledgeGraphResult` or any other Layer 2 capability's Derived Knowledge (including `ContinuousImprovementResult`) without a deliberate, future, explicitly-declared ADR.

### Recommendation 10 — The graph is the single structural authority; local relationship models remain subsystem-local

Local relationship models — most directly Requirement Enhancement's `RelationshipGraph` — remain subsystem-local and must **not** evolve into competing platform graphs. Instead, they become inputs that a future Knowledge Graph engine may project into the canonical platform graph. This preserves single ownership of global structural relationships in exactly one place while allowing each subsystem to maintain its own internal reasoning model, exactly as it stands today (§D9).

---

## Trade-offs

- **A new subsystem introduces the platform's second Layer 2 capability with only one prior Layer 2 precedent (Continuous Improvement) to follow.** Accepted: ADR-0020/ADR-0021/ADR-0022 exist precisely to provide that precedent, and this ADR follows the identical architecture-freeze-before-behaviour discipline (Stage 0).
- **`HistoricalDatasetReference` is duplicated, not shared, between Continuous Improvement and Knowledge Graph.** Accepted: this mirrors every prior subsystem's identity/version base-class duplication (ADR-0015 §C and successors); the eventual promotion of both the reference type and the identity/version base classes to `shared/` remains acknowledged platform debt, not a defect introduced here.
- **Two Layer 2 capabilities (Continuous Improvement, Knowledge Graph) now exist side by side, each a peer consumer of Historical Truth, neither consuming the other.** Accepted: ADR-0021 §Stage 3 forbids Derived Knowledge from recursively consuming Derived Knowledge without a deliberate future ADR; keeping the two capabilities structurally independent today is the conservative default, not an oversight.
- **Governed defaults (`max_nodes_per_graph`, `max_edges_per_graph`, `max_traversal_depth`) are calibrated conservatively, not empirically.** The CAP-084A default policy bounds reflect a deliberately conservative first pass, not yet tuned against a real historical corpus or a real graph. Accepted: tuning is a versioned policy change under a future golden re-baseline, never an engine code change (Recommendation 5).

## Future evolution

- **Historical Dataset implementation** (reserved, ADR-0021 §Stage 6) — a future milestone (inside or alongside CAP-084, or shared with Continuous Improvement's own need for one) that actually builds the ordering/lineage/retention/indexing/search `HistoricalDatasetReference` currently only names.
- **CAP-084B (reserved)** — the first deterministic Knowledge Graph engine behind the frozen `build` signature: deterministic node/edge ingestion, subgraph partitioning, observation generation, and finding detection from a resolved Historical Dataset, strictly by reference (Recommendation 2), never independent analysis or re-implementation of any subsystem's own reasoning. Mirrors CAP-083B's implementation of the first deterministic Continuous Improvement engine.
- **Graph storage** (reserved) — a future Neo4j, RDF, property graph, SQL, or in-memory implementation behind `KnowledgeGraphService.build`'s unchanged signature (Recommendation 5).
- **Future AI graph reasoning, graph embeddings, graph traversal, and Graph RAG** (all reserved) — higher-layer or engine-variant capabilities that consume `KnowledgeGraphResult` (or a future graph storage backing it) without ever becoming part of this contract; any peer engine variant must satisfy Recommendation 7's determinism-first discipline for graph *construction* specifically, while reasoning/traversal/RAG capabilities built atop the constructed graph are separate, later, higher-layer owners (Recommendation 6).
- **Runtime activation (CAP-084C, reserved)** — wiring `build` into a live cross-execution pipeline, plus a future Execution Package projection and golden re-baseline, mirroring CAP-083C's activation of Continuous Improvement (ADR-0022 §D11).
- **CAP-085 (Organizational Memory), CAP-086 (Learning Framework)** — the remaining reserved Layer 2 capabilities (ADR-0020), each to declare its own Truth Hierarchy level per ADR-0021 Recommendation 11.
- Promotion of the shared version/identity value-objects (and the now twice-duplicated `HistoricalDatasetReference` shape) to `shared/` (the debt ADR-0015 §C, ADR-0016, ADR-0017, ADR-0018 §D5, ADR-0019 §D5, and ADR-0022 already name).

## Ownership, runtime position, governance

- **Owns:** the canonical platform graph — nodes, governed relationship edges, subgraphs, deterministic structural observations, deterministic structural findings, Knowledge Graph metadata.
- **Does not own:** Engineering Context Orchestration, Analysis, Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, Continuous Improvement, the Execution Package, or the Historical Dataset itself (ADR-0021 §Stage 6 names that owner, not this ADR). Does not own any subsystem-local relationship model (e.g. `RelationshipGraph`) — those remain owned exactly where they already are (§D9, Recommendation 10).
- **Runtime position (architecture frozen, dormant — CAP-084A):** `HistoricalDatasetReference` → (future engine, future graph storage) → `KnowledgeGraphResult` → (future) Execution Package. Architecture frozen; no engine exists yet; `KnowledgeGraphService` is abstract and its registered default (`DormantKnowledgeGraphService`) raises `NotImplementedError` on every call; nothing is wired into any execution pipeline.
- **Governance:** registered as CAP-084 for the Requirement Intelligence Platform's Layer 2 — the second capability built under ADR-0020/ADR-0021, following Continuous Improvement (ADR-0022). This ADR is **Proposed** for its architecture scope, exactly mirroring ADR-0022's own status ahead of its own CAP-083B/B.1/C lifecycle.
