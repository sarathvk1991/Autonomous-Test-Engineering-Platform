# ADR-0023 — Knowledge Graph Framework

- **Status:** Accepted (CAP-084A — Architecture & Governance Freeze; CAP-084B — Deterministic Engine implemented behind the frozen contracts; CAP-084B.1 — `KnowledgeGraphResult` Runtime Contract permanently certified, no behaviour change; CAP-084C — Runtime Integration & Execution Package Activation, live in the pipeline)
- **Date:** 2026-07-15 (CAP-084A — Architecture & Governance Freeze); 2026-07-15 (CAP-084B — Deterministic Knowledge Graph Engine); 2026-07-16 (CAP-084B.1 — Runtime Contract Freeze); 2026-07-16 (CAP-084C — Runtime Integration)
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** CAP-084B (Deterministic Knowledge Graph Engine — implements the first real engine behind the frozen contracts, mirroring how CAP-083B implemented the first deterministic Continuous Improvement engine behind ADR-0022); CAP-084B.1 (permanent `KnowledgeGraphResult` runtime-contract certification, mirroring CAP-083B.1, CAP-082B.1, CAP-081B.1, and CAP-080B.1.1 — no behaviour change; see §D11); CAP-084C (Runtime Integration & Execution Package Activation, mirroring CAP-083C's activation of Continuous Improvement — see §D12).
- **Governing design:** `docs/proposals/knowledge-graph-framework.md`
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — this is the second Layer 2 capability it names), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — this framework's every boundary is a direct application of ADR-0021's Truth Hierarchy), and ADR-0025 (Derived Knowledge Architecture & Layer 2 Constitution — the platform-wide generalization of this framework's own Derived Knowledge principle and peer-independence rule, §D11/§D12 below). Also informed by ADR-0022 (Continuous Improvement Framework — the first Layer 2 capability, and the direct architectural precedent this ADR mirrors, including its own CAP-083B.1 runtime contract freeze and CAP-083C runtime integration) and ADR-0024 (Historical Dataset & Historical Truth Constitution — the constitutional freeze of the Historical Dataset Resolution Principle this framework's provider follows).
- **Runtime status:** **Live (CAP-084C).** `DeterministicKnowledgeGraphEngine` projects nodes, projects edges, partitions subgraphs, records observations, and detects findings entirely from the governed `KnowledgeGraphRuleCatalog` and `KnowledgeGraphPolicy`. The CLI's `run_knowledge_graph_phase` obtains `DeterministicKnowledgeGraphService` from `PlatformContext` and calls `build` immediately after Continuous Improvement, at the permanently frozen end of the pipeline, over a single-execution `HistoricalDatasetReference` this run reuses the exact CAP-083C minting strategy to produce (no real, multi-execution Historical Dataset implementation exists yet, ADR-0021 §Stage 6). `KnowledgeGraphSerializer` projects the result into three Execution Package artifacts (`knowledge_graph_result.json` / `knowledge_graph_report.md` / `knowledge_graph_metrics.md`), and the manifest gains three additive, package-metadata-only keys. The golden dataset re-baselined `1.5.0` → `1.6.0` to include them. The Architecture Version remains **1.2.0**, `KnowledgeGraphResult`'s shape is unchanged, and no frozen contract of any upstream subsystem changed. See §D12.

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

## D10 — Deterministic Knowledge Graph Engine (CAP-084B)

CAP-084B implements the first real engine behind the CAP-084A boundary. No architectural weakness was found in Stage 0 review of CAP-084A: `KnowledgeGraphResult` is the permanent runtime contract, `KnowledgeGraphService` the permanent entry point, `KnowledgeGraphPolicy` and every canonical model frozen, `PlatformContext` the sole composition root, and Knowledge Graph fully dormant. CAP-084B otherwise proceeded as a **pure implementation milestone** — no redesign, no frozen-contract change.

**Modular architecture, not one large engine (new discipline for this milestone).** Unlike every prior deterministic engine in this platform, `DeterministicKnowledgeGraphEngine` is a thin pipeline orchestrator, not a monolithic class. It decomposes into independent, single-responsibility, engine-internal collaborators — none exported, none a runtime contract, none visible outside `knowledge_graph/engine/`:

* **Projection** (`engine/projection/`) — `NodeProjector` (the sole node authority) and `EdgeProjector` (the sole edge authority) deterministically project a resolved Historical Dataset into governed `KnowledgeNode` / `KnowledgeEdge` entries. `EdgeProjector` never manufactures a dangling reference: an edge is emitted only when both endpoint nodes were actually projected, regardless of which node/edge rules are policy-enabled.
* **Analysis** (`engine/analysis/`) — `SubgraphDetector` (the sole subgraph authority) performs pure connected-component partitioning (undirected adjacency, deterministic BFS). `ObservationEngine` (the sole observation authority) records deterministic structural facts (node coverage, edge coverage, longest `DEPENDS_ON` chain, structural consistency) from the already-projected nodes/edges/subgraphs — never a judgement. `FindingEngine` (the sole finding authority) detects deterministic structural issues (isolated node, duplicate edge, orphan graph, missing relationship, broken lineage, cycle) — every finding explainable entirely from already-projected nodes/edges/subgraphs, including a dedicated iterative (non-recursive) directed-cycle detector.
* **Builders** (`engine/builders/`) — `SummaryBuilder` and `MetricsBuilder` each compute their target exactly once, from already-finished collaborators, no recomputation. `ResultBuilder` is the **only** constructor of `KnowledgeGraphResult` anywhere in this engine.

Each collaborator owns exactly one responsibility so a future statistical, ML, or LLM-based engine can reuse the same decomposition — or replace any single stage (e.g. swap `NodeProjector` for one backed by a real graph database's ingestion layer) — without changing the public `build` contract or any sibling collaborator.

**Governed rule catalogue (new package, `knowledge_graph/rules/`).** Mirrors `continuous_improvement/rules/`: `KnowledgeGraphRule` is metadata only (rule id, `KnowledgeGraphRuleFamily`, the governed node type / edge type / finding category + severity it names, a policy reference, an enable switch) — no lambda, no callback, no embedded algorithm. `KnowledgeGraphRuleCatalog` owns ordering/lookup only. `KnowledgeGraphRuleBuilder`/`default_knowledge_graph_rule_catalog()` ship 22 governed rules: 7 NODE rules (Requirement, Recommendation, Finding, Execution, Capability, Dataset, Document), 9 EDGE rules (Depends On, Generated By, Traceable To, Implements, References, Belongs To, Derived From, Related To, Uses), and 6 STRUCTURAL rules (one per `KnowledgeFindingCategory`).

**Historical Dataset Resolution Principle (frozen, reused from ADR-0022 §D9).** `HistoricalDatasetReference` intentionally carries provenance only — no Historical Dataset storage implementation exists yet, and CAP-084B does not build one. `DeterministicKnowledgeGraphEngine` resolves it through a private, constructor-injected `HistoricalDatasetProvider` into an engine-internal `HistoricalDataset` — a plain, unexported structure that is not a runtime contract, not Historical Truth, not Derived Knowledge, and never crosses the `knowledge_graph` package boundary. This is the identical pattern CAP-083B established for Continuous Improvement, deliberately replicated rather than shared: `knowledge_graph`'s `HistoricalDatasetProvider` / `HistoricalDataset` / `HistoricalExecutionRecord` are distinct classes from `continuous_improvement`'s own, never imported across the two packages (ADR-0021 §Stage 8; Recommendation 9 of this ADR). The CAP-084B default, `DeterministicHistoricalDatasetProvider`, synthesizes reproducible per-execution facts (a requirement id always; recommendation/finding/capability/document ids conditionally) as a pure function of the reference's own provenance fields via SHA-256 digests — no UUID, no clock, no real historical storage — solely to exercise the deterministic engine end to end. A future milestone may replace it with a provider backed by a real Historical Dataset implementation without changing the engine's public contract or any other collaborator.

**Deterministic algorithms only.** Node/edge projection is direct lookup-and-construct from already-named entity ids (Recommendation 2). Subgraph detection is textbook connected-component BFS. Observation generation and finding detection are arithmetic, set operations, and graph traversal (longest-chain search, cycle detection) — no AI, no prediction, no statistical forecasting, no clustering, no embeddings, no semantic similarity. Every outcome is explainable from operations already visible in this ADR.

**Policy governance.** Every capability the engine exercises — node ingestion, edge ingestion, subgraph partitioning, observation generation, finding detection, and the master `enable_deterministic_engine` gate — is read from `KnowledgeGraphPolicy.capability_switches`, resolved per rule via its `policy_reference`. No node type, edge type, or finding category is hard-coded as "always on" in the engine; the rule catalogue and policy jointly govern what runs.

**Explainability.** Every node carries its own `referenced_id`; every edge names its governed type and two endpoint node ids; every observation and finding names the exact node/edge ids it concerns. Nothing is inferred without a named, traceable structural fact already present in the graph.

**Derived Knowledge principle preserved (mandatory, mirrors ADR-0022 Recommendation 11).** Every execution of `build` derives its graph directly from the resolved `HistoricalDataset` — never from a prior `KnowledgeGraphResult`, `KnowledgeNode`, `KnowledgeEdge`, `KnowledgeSubgraph`, `KnowledgeObservation`, or `KnowledgeFinding`. Neither `build` nor `HistoricalDatasetProvider.resolve` accepts any Derived Knowledge type as a parameter.

**PlatformContext.** `create_knowledge_graph_service()` now returns `DeterministicKnowledgeGraphService` (replacing `DormantKnowledgeGraphService`, which CAP-084B removes — mirroring how CAP-083B's `DeterministicContinuousImprovementService` replaced its own dormant predecessor). `create_knowledge_graph_rule_catalog()` is added alongside `create_knowledge_graph_policy()`. Still unwired: nothing calls `build()` at runtime, so the golden baseline, Architecture Version, and Platform Version are all unchanged.

**Policy value tuning (not a shape change).** `KnowledgeGraphCapabilitySwitches.enable_deterministic_engine` flips `False → True` in the shipped default policy (`KnowledgePolicyVersion` 1.0.0 → 1.1.0) now that the engine exists — a versioned policy *value* change, exactly the kind Recommendation 5 anticipated, never a policy *shape* or engine code change.

**Future ML/LLM engines.** `KnowledgeGraphCapabilitySwitches.enable_ml_engine` / `enable_llm_engine` remain reserved off. A future statistical, ML, or LLM-based Knowledge Graph engine implements the identical `KnowledgeGraphService.build` contract and may replace any single modular collaborator (or all of them) without this ADR, `KnowledgeGraphResult`, or `KnowledgeGraphPolicy` changing shape.

**Tests.** New deterministic tests cover the rule catalogue (governed vocabulary, metadata-only shape), projection (node/edge determinism, identifier stability, no dangling edges), subgraph detection (connected components, disconnected graphs, isolated nodes), observation generation, finding detection (every structural category, including cycle detection), builders (summary/metrics/result each computed exactly once), end-to-end engine determinism and explainability, policy gating, provider isolation, and containment (no Layer 1 imports, no Continuous Improvement import, no serializer, no Execution Package, no CLI, no graph database implementation, `HistoricalDatasetProvider` remains private, only `PlatformContext` constructs the service externally).

## D11 — KnowledgeGraphResult Runtime Contract (CAP-084B.1 permanent certification)

CAP-084B.1 makes **no runtime behaviour change whatsoever**. It permanently certifies `KnowledgeGraphResult` as the canonical runtime contract of the Knowledge Graph Framework, exactly as CAP-080B.1.1 certified `QualityAssessmentResult`, CAP-081B.1 certified `RequirementEnhancementResult`, CAP-082B.1 certified `RecommendationResult`, and CAP-083B.1 certified `ContinuousImprovementResult` — each *before* its subsystem's own runtime activation. This section is the permanent reference for that certification; nothing here changes a field, a computation, or a signature.

**Frozen definition.** `KnowledgeGraphResult` is *the complete deterministic runtime record produced from exactly one execution of* `KnowledgeGraphService.build()`.

**KnowledgeGraphResult IS.** The complete runtime output of one Knowledge Graph build; the canonical Layer 2 structural representation; Derived Knowledge; self-contained; independently versioned; deterministic; explainable; projection-independent.

**KnowledgeGraphResult IS NOT.** Historical Truth; graph storage; a graph database; execution history; an execution package; a report; a renderer; a serializer; a CLI object; a mutable graph.

**Ownership (frozen, no overlap).**

| Component | Owns | Owns *not* |
|---|---|---|
| `NodeProjector` / `EdgeProjector` | node projection, edge projection | subgraph detection, observation, finding, orchestration |
| `SubgraphDetector` | connected-component partitioning | node/edge projection, observation, finding |
| `ObservationEngine` / `FindingEngine` | structural observations, structural findings | projection, orchestration, packaging |
| `SummaryBuilder` / `MetricsBuilder` | summary, metrics | orchestration, projection, packaging |
| `HistoricalDatasetProvider` (private) | resolving a reference into an internal `HistoricalDataset` | anything downstream of that resolution; never a runtime contract |
| `DeterministicKnowledgeGraphEngine` | pipeline orchestration of the collaborators above | any runtime contract, projection, packaging |
| `KnowledgeGraphService` | orchestration only | any computation the engine performs |
| `KnowledgeGraphResult` | nodes, edges, subgraphs, observations, findings, summary, metrics, provenance, governing policy identity/version | runtime engines, the Historical Dataset, graph storage, execution package, reports, serialization, a graph database, future graph embeddings, future Graph RAG, future ML reasoning |
| Serializer (future) | projection only | generation, orchestration, packaging |
| Execution Package (future) | packaging only | generation, orchestration, projection logic |
| CLI (future) | orchestration (of the pipeline call) only | generation, projection, packaging |
| `PlatformContext` | composition only | generation, orchestration, projection, packaging |

**Explainability (frozen).** Every node, edge, observation, finding, and summary/metrics value must be reconstructable solely from `KnowledgeGraphResult`. No provider needs to be inspected. No engine rerun is required. No graph storage needs to be inspected. `KnowledgeGraphResult` is the complete explanation.

**Runtime boundary (frozen).** Runtime ends at

```
HistoricalDatasetReference
        ↓
KnowledgeGraphService
        ↓
KnowledgeGraphResult
```

Everything after that is projection only. Future serializers, reports, dashboards, Markdown, HTML, graph storage, and the Execution Package must consume `KnowledgeGraphResult` only — never the engine, never the provider, never the service, never `PlatformContext`, and must compute nothing.

```
HistoricalDatasetReference
    → (private HistoricalDatasetProvider → engine-internal HistoricalDataset)
    → DeterministicKnowledgeGraphEngine
    → KnowledgeGraphResult
    → Serializer (future)
    → Execution Package (future)
    → Manifest (future)
    → Graph storage (future)
    → Release
```

No reverse dependency: nothing later in this chain is ever imported by anything earlier in it.

**Historical Dataset Resolution Principle (frozen permanently, mirrors ADR-0022 Recommendation 10).** `HistoricalDatasetReference` intentionally carries provenance only. Implementations may resolve the referenced dataset through private collaborators. The resolved dataset is an implementation detail — never a runtime contract, never Historical Truth, never Derived Knowledge, never exported past the `knowledge_graph` package boundary. The public runtime boundary remains `HistoricalDatasetReference → KnowledgeGraphResult`. `HistoricalDatasetProvider` remains private, replaceable, and constructor-injected — engine internal. Future storage implementations, including one backed by a real Historical Dataset implementation, may replace `DeterministicHistoricalDatasetProvider` freely; the `build` signature never changes as a result, and `KnowledgeGraphResult` must never expose it.

**Derived Knowledge principle (frozen permanently, Recommendation 11; now the platform-wide constitution of ADR-0025).** `KnowledgeGraphResult` is Derived Knowledge — never Historical Truth. It must never be written back into the Historical Dataset it was computed from. Every execution of `build` derives its graph directly from the resolved `HistoricalDataset` — never from a prior `KnowledgeGraphResult` or any prior `KnowledgeNode` / `KnowledgeEdge` / `KnowledgeSubgraph` / `KnowledgeObservation` / `KnowledgeFinding`. Derived Knowledge must never recursively consume Derived Knowledge. ADR-0025 generalizes this principle, and this framework's peer relationship to Continuous Improvement, platform-wide — future Layer 2 capabilities cite ADR-0025 directly rather than restating this paragraph.

**Graph storage remains an implementation detail (frozen permanently, Recommendation 12 below).** Neo4j, RDF, SQL, property graphs, or in-memory implementations must never affect this runtime contract.

**Projection remains deterministic (frozen permanently, Recommendation 13 below).** Node and edge projection must remain reproducible from the same Historical Dataset.

**Graph analysis remains explainable (frozen permanently, Recommendation 14 below).** Every structural observation and finding must be traceable to specific nodes and edges contained within the same `KnowledgeGraphResult`.

**Runtime precedes visualization (frozen permanently, Recommendation 15 below).** Visualization, graph rendering, graph exploration UIs, Graph RAG, embeddings, and graph queries are execution-time projections or future capabilities. They must never redefine or mutate this runtime contract.

**Version-axis independence (frozen; full detail in `knowledge_graph/identity/knowledge_graph_identity.py`'s module docstring).** Eight distinct version types exist — `KnowledgeGraphFrameworkVersion`, `KnowledgePolicyVersion`, `KnowledgeGraphRuleVersion`, `KnowledgeGraphRuleCatalogVersion`, `KnowledgeNodeVersion` (reserved), `KnowledgeEdgeVersion` (reserved), `KnowledgeObservationVersion` (reserved), `KnowledgeGraphResultVersion` (the only axis stamped onto a model today) — each evolving independently. `KnowledgeSubgraph`, `KnowledgeFinding`, and `KnowledgeSummary`/`KnowledgeMetrics` carry no dedicated schema-version type of their own — a deliberate architectural consolidation, mirroring the precedent CAP-082B.1 established and CAP-083B.1 reaffirmed for their own atomic finding/issue models; no new version type is invented by this certification.

**Future engine compatibility (frozen permanently).** Future deterministic, ML, LLM, Graph Neural Network, graph database, and Graph RAG engines must all reuse `KnowledgeGraphResult` without contract changes.

**Additional constitutional principles (frozen, CAP-084B.1), cross-referenced to the Recommendations already governing this ADR:**

1. `KnowledgeGraphResult` is the sole runtime authority for Derived Knowledge produced by Knowledge Graph (Recommendation 4; frozen definition, above).
2. `HistoricalDatasetProvider` is an implementation detail, not part of the platform architecture (mirrors ADR-0022 Recommendation 10).
3. `HistoricalDatasetReference` remains the only public input contract, regardless of future storage technologies (Recommendation 5; mirrors ADR-0022 Recommendation 10).
4. Historical dataset resolution is replaceable, but the runtime boundary is not (mirrors ADR-0022 Recommendation 10; Runtime boundary, above).
5. Runtime contracts evolve independently of engines, providers, serializers, execution packaging, graph storage, and historical storage (Version-axis independence, above; Recommendation 5).
6. Knowledge Graph remains a pure Layer 2 consumer of Historical Truth and must never consume Layer 1 runtime contracts directly, another Layer 2 capability's Derived Knowledge, or recursively consume its own previous Derived Knowledge (Recommendation 1, Recommendation 9).
7. Future deterministic, ML, LLM, Graph Neural Network, graph database, and Graph RAG engines must implement the unchanged `build(HistoricalDatasetReference) -> KnowledgeGraphResult` contract, ensuring long-term engine replaceability (Recommendation 5, Recommendation 7).

**Certification.** `KnowledgeGraphResult` is hereby constitutionally certified as the permanent Layer 2 runtime contract for Knowledge Graph, completing the same architectural lifecycle (Architecture Freeze → Deterministic Implementation → Runtime Contract Freeze) previously established for Quality Governance (CAP-080B.1.1), Requirement Enhancement (CAP-081B.1), Recommendation (CAP-082B.1), and Continuous Improvement (CAP-083B.1). No field, validator, or signature changed to produce this certification. The repository is certified ready for **CAP-084C — Knowledge Graph Runtime Integration**, with no further architectural work required.

## D12 — Knowledge Graph Runtime Integration (CAP-084C)

CAP-084C activates the already-complete Knowledge Graph Framework in the live Requirement Intelligence runtime — Layer 2's second capability going live. It does not redesign Knowledge Graph, change any frozen contract, alter the policy shape, modify the deterministic engine, or introduce new projection/analysis logic — it wires the existing implementation into the live pipeline and activates the Execution Package projections, exactly as CAP-083C did for Continuous Improvement (ADR-0022 §D11).

**Activation and execution order (frozen).** Knowledge Graph executes exactly once, immediately after Continuous Improvement, at the permanently frozen end of the pipeline:

```
Engineering Context → Analysis → Requirement Enhancement → Grounding
    → Validation → CP1 → Quality Governance → Recommendation → Historical Dataset
    → Continuous Improvement → Knowledge Graph → Execution Package
```

Never before Continuous Improvement, never in parallel, never conditionally reordered.

**`HistoricalDatasetReference` minting (frozen, reuses the CAP-083C strategy exactly).** Knowledge Graph consumes exactly one `HistoricalDatasetReference` — never a Layer 1 runtime contract directly, and never `ContinuousImprovementResult` or any other peer result this same pipeline run just produced (Recommendation 1, Recommendation 9). No real, multi-execution Historical Dataset implementation exists yet (ADR-0021 §Stage 6, reserved). Rather than invent a second minting strategy, the CLI reuses the exact deterministic single-execution reference CAP-083C introduced: `first_execution_id` and `last_execution_id` both name this run's own `AnalysisResult.execution_id`, `execution_count` and `history_window` are both `1`, and `generated_at` is this run's own `completed_at` — never the wall clock. The only difference from the Continuous Improvement helper is the target type: `knowledge_graph.models.HistoricalDatasetReference` rather than `continuous_improvement.models.HistoricalDatasetReference` — the deliberately duplicated, structurally identical type ADR-0023 Stage 0 and ADR-0024 Stage 0 both confirm. This performs no business logic and computes nothing beyond restating identity fields already carried — orchestration glue, not observation.

**Unlike Continuous Improvement's always-empty golden shape (new nuance, frozen).** Continuous Improvement's single-execution reference can satisfy neither its recurrence floor nor its trend floor, so the golden dataset always observes an empty `ContinuousImprovementResult`. Knowledge Graph's CAP-084B deterministic provider has no such floor: it unconditionally synthesizes a requirement, an execution, and a dataset node from every reference (three base nodes, two base edges — `BELONGS_TO` and `DERIVED_FROM`), and *conditionally* synthesizes up to four more node types (recommendation, finding, capability, document), each gated by a SHA-256 digest of the reference's own `dataset_id` — which embeds this run's randomly minted `execution_id`. The golden dataset therefore deterministically observes a small, genuine, **non-empty** `KnowledgeGraphResult` whose exact node/edge count varies, by design, across independent pipeline runs, while remaining perfectly reproducible for any *fixed* reference (proven by `test_knowledge_graph_execution_integration.py` and `test_golden_baseline.py`'s own same-reference determinism tests). This is not a regression risk: the golden baseline asserts structural bounds and invariants (always 3–7 nodes, always exactly one connected component, at most one finding). Every conditional node type is linked back to the requirement node the instant it is present, so isolation and broken lineage are structurally impossible at `execution_count=1` — but a cycle is **not** always impossible: when both `capability` and `document` nodes are present for the same execution, `IMPLEMENTS` (requirement → capability), `USES` (capability → document), and `REFERENCES` (document → requirement) form a genuine 3-node directed cycle the deterministic cycle detector correctly reports as one `CYCLE` finding. This was discovered during CAP-085A's own verification pass and corrected here and in `test_golden_baseline.py`; it is a real, reproducible structural property of the engine, never an unexplained one, and the golden baseline now asserts exactly that bound (at most one finding, and only of that category) instead of the narrower, incorrect "always zero findings" claim this section previously made.

**CLI (frozen).** The CLI's `run_knowledge_graph_phase` obtains `KnowledgeGraphService` exclusively from `PlatformContext` and calls `build(historical_dataset)` — identical failure semantics to Grounding/Quality Governance/Recommendation/Continuous Improvement: a Knowledge Graph failure is surfaced but never fatal to the analysis run, and it runs whenever this is a live run (a completed `AnalysisResult` exists, so a single-execution reference can be minted). The CLI orchestrates only — no projection, partitioning, observation, or finding-detection logic exists in the CLI.

**Execution Package (frozen, mirrors ADR-0022 §D11).** `ExecutionData.knowledge_graph_result` is an additive-only field (no existing field changed). `KnowledgeGraphSerializer` (`knowledge_graph/serialization/`) renders `knowledge_graph_result.json` (canonical `model_dump`), `knowledge_graph_report.md`, and `knowledge_graph_metrics.md` — a pure projection computing nothing; every rendered value already exists inside `KnowledgeGraphResult`. `ExecutionWriter` appends these three artifacts only when `knowledge_graph_result` is present — no special case, the same conditional-append mechanism as every peer subsystem, written immediately after the Continuous Improvement artifacts.

**Manifest purity (frozen, mirrors ADR-0017 §D31, ADR-0022 §D11).** The manifest gains exactly three additive keys — `knowledgeGraphExecuted`, `knowledgeGraphReport`, `knowledgeGraphMetrics` — a flag and two artifact filenames. No node, edge, subgraph, observation, finding, summary, or metric value is ever copied into the manifest; that runtime state lives exclusively in `KnowledgeGraphResult` / `knowledge_graph_result.json`. When Knowledge Graph did not run, the manifest is byte-identical to before — no key is added, no schema change (`manifestSchemaVersion` stays `1.0.0`).

**Golden integration (frozen).** `_run_golden_pipeline()` now builds immediately after Continuous Improvement; `PipelineResult` carries `knowledge_graph_result`. The golden dataset re-baselines from `GOLDEN_DATASET_VERSION` `1.5.0` to `1.6.0` — the nine source artifacts and the golden response are unchanged; only the generated artifact set grows by the three Knowledge Graph files, exactly as `1.4.0` and `1.5.0` did for Recommendation and Continuous Improvement respectively. The Architecture Version remains `1.2.0`; the Platform Version is unchanged.

**One-way dependency chain (frozen, mirrors §D8/ADR-0022 §D11).**

```
Knowledge Graph Runtime (engine + service)
    → KnowledgeGraphResult
    → Knowledge Graph Serializer
    → Execution Package
    → Manifest
    → Release
```

Nothing later in this chain imports or invokes anything earlier except through the frozen `KnowledgeGraphResult` contract. The serializer imports no engine, service, policy, rule catalogue, or `HistoricalDatasetProvider` implementation. The writer and manifest builder import only the serializer, never the engine, service, or provider. The CLI imports only `PlatformContext.create_knowledge_graph_service()`, never `DeterministicKnowledgeGraphEngine`, `KnowledgeGraphRuleCatalog`, or any `HistoricalDatasetProvider` directly.

**Ownership (frozen, no overlap; reaffirms §D11's table with the CLI and Execution Package now live).** The engine's collaborators project/partition/observe/detect/compute as already frozen. Service orchestrates only. `KnowledgeGraphResult` owns runtime state only. The serializer projects only. The Execution Package packages only. The CLI orchestrates (the pipeline call) only. `PlatformContext` composes only.

**Historical Dataset boundary preserved (Recommendation 16, new).** Knowledge Graph never caches, duplicates, or persists historical records outside the Historical Dataset it references. The single-execution reference this milestone reuses is provenance only — it names an execution, it never embeds or stores one — and CAP-084C introduces no historical storage of its own.

**Derived Knowledge never rewritten (Recommendation 17, new).** `KnowledgeGraphResult` is never written back into the Historical Dataset, and no future Knowledge Graph build may consume a prior `KnowledgeGraphResult` as an input. `build`'s only parameter remains `HistoricalDatasetReference` — unchanged by this milestone.

**Execution Package remains projection-only (Recommendation 18, new).** Every Knowledge Graph execution artifact is reproducible solely from `KnowledgeGraphResult`. No artifact generation invokes the engine, the provider, the service, or `PlatformContext` — enforced by the same containment tests that guard every peer subsystem's serializer and Execution Package boundary.

**Layer separation preserved (Recommendation 19, new).** Knowledge Graph remains a Layer 2 capability. Runtime integration introduces no direct dependency on any Layer 1 implementation class, and no dependency on Continuous Improvement's own implementation classes — the CLI, the serializer, and the Execution Package all reach Knowledge Graph exclusively through `PlatformContext.create_knowledge_graph_service()` and `KnowledgeGraphResult`.

**Historical Dataset implementation remains replaceable (Recommendation 20, new).** The runtime pipeline consumes only `HistoricalDatasetReference`. A future Historical Dataset implementation — and a future `HistoricalDatasetProvider` backed by it — may replace the single-execution reference this milestone reuses without requiring any change to the CLI, the serializer, the Execution Package, or `KnowledgeGraphResult`.

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

### Recommendation 11 — Structural Knowledge is never Historical Truth (mandatory, CAP-084B.1, frozen permanently)

`KnowledgeGraphResult` is **Derived Knowledge**. It must never become Historical Truth or be written back into the Historical Dataset. This reaffirms D3/D11 at the runtime boundary: `build`'s only parameter remains `HistoricalDatasetReference`, unchanged by this milestone, and no future Knowledge Graph build may consume a prior `KnowledgeGraphResult` or any of its constituents.

### Recommendation 12 — Graph storage remains an implementation detail (mandatory, CAP-084B.1, frozen permanently)

Neo4j, RDF, SQL, property graphs, or in-memory implementations must never affect runtime contracts. `KnowledgeGraphService.build`'s unchanged signature and `KnowledgeGraphResult`'s unchanged shape are the only surfaces any future graph storage implementation must satisfy.

### Recommendation 13 — Projection remains deterministic (mandatory, CAP-084B.1, frozen permanently)

Node and edge projection must remain reproducible from the same Historical Dataset. A future engine variant (deterministic, ML, LLM, Graph Neural Network) may change *how* projection is computed, but the same input must always be explainable from the resulting `KnowledgeGraphResult`.

### Recommendation 14 — Graph analysis remains explainable (mandatory, CAP-084B.1, frozen permanently)

Every structural observation and finding must be traceable to specific nodes and edges contained within the same `KnowledgeGraphResult`. No observation or finding may reference a node, edge, or fact outside the result that produced it.

### Recommendation 15 — Runtime precedes visualization (mandatory, CAP-084B.1, frozen permanently)

Visualization, graph rendering, graph exploration UIs, Graph RAG, embeddings, and graph queries are execution-time projections or future capabilities. They must never redefine or mutate the runtime contract `KnowledgeGraphResult` establishes.

### Recommendation 16 — Historical Dataset remains the sole Historical Truth (mandatory, CAP-084C, frozen permanently)

Knowledge Graph must never cache, duplicate, or persist historical records outside the Historical Dataset. It consumes Historical Truth but never owns it. The single-execution `HistoricalDatasetReference` the CAP-084C runtime reuses is provenance only — it names an execution, it never embeds or stores one — and runtime integration introduces no historical storage of its own.

### Recommendation 17 — Derived Knowledge is never rewritten into Historical Truth (mandatory, CAP-084C, frozen permanently)

`KnowledgeGraphResult` must never be written back into the Historical Dataset or become an input to future Knowledge Graph builds. This reaffirms Recommendation 11 at the runtime boundary: `build`'s only parameter remains `HistoricalDatasetReference`, unchanged by runtime activation.

### Recommendation 18 — Execution Package remains projection-only (mandatory, CAP-084C, frozen permanently)

Execution artifacts are reproducible solely from `KnowledgeGraphResult`. No artifact generation may invoke the engine, the provider, the service, or `PlatformContext` — enforced by dedicated containment tests over `KnowledgeGraphSerializer`, `ExecutionWriter`, and `ManifestBuilder` (§D12).

### Recommendation 19 — Runtime integration must not weaken Layer separation (mandatory, CAP-084C, frozen permanently)

Knowledge Graph remains a Layer 2 capability. Runtime integration must not introduce direct dependencies on any Layer 1 implementation class, nor on Continuous Improvement's own implementation classes. The CLI, the serializer, and the Execution Package all reach Knowledge Graph exclusively through `PlatformContext.create_knowledge_graph_service()` and `KnowledgeGraphResult` — never `DeterministicKnowledgeGraphEngine`, `KnowledgeGraphRuleCatalog`, or any Layer 1 or Continuous Improvement subsystem directly.

### Recommendation 20 — Historical Dataset implementation remains replaceable (mandatory, CAP-084C, frozen permanently)

The runtime pipeline consumes only `HistoricalDatasetReference`. Future storage implementations may evolve independently without requiring changes to the CLI, the serializer, the Execution Package, or `KnowledgeGraphResult` — including replacing the single-execution reference CAP-084C reuses with one backed by a real, multi-execution Historical Dataset.

---

## Trade-offs

- **A new subsystem introduces the platform's second Layer 2 capability with only one prior Layer 2 precedent (Continuous Improvement) to follow.** Accepted: ADR-0020/ADR-0021/ADR-0022 exist precisely to provide that precedent, and this ADR follows the identical architecture-freeze-before-behaviour discipline (Stage 0).
- **`HistoricalDatasetReference` is duplicated, not shared, between Continuous Improvement and Knowledge Graph.** Accepted: this mirrors every prior subsystem's identity/version base-class duplication (ADR-0015 §C and successors); the eventual promotion of both the reference type and the identity/version base classes to `shared/` remains acknowledged platform debt, not a defect introduced here.
- **Two Layer 2 capabilities (Continuous Improvement, Knowledge Graph) now exist side by side, each a peer consumer of Historical Truth, neither consuming the other.** Accepted: ADR-0021 §Stage 3 forbids Derived Knowledge from recursively consuming Derived Knowledge without a deliberate future ADR; keeping the two capabilities structurally independent today is the conservative default, not an oversight.
- **Governed defaults (`max_nodes_per_graph`, `max_edges_per_graph`, `max_traversal_depth`) are calibrated conservatively, not empirically.** The CAP-084A default policy bounds reflect a deliberately conservative first pass, not yet tuned against a real historical corpus or a real graph. Accepted: tuning is a versioned policy change under a future golden re-baseline, never an engine code change (Recommendation 5).

## Future evolution

- **Historical Dataset implementation** (reserved, ADR-0021 §Stage 6) — a future milestone (inside or alongside CAP-084, or shared with Continuous Improvement's own need for one) that actually builds the ordering/lineage/retention/indexing/search `HistoricalDatasetReference` currently only names.
- **CAP-084B — Deterministic Knowledge Graph Engine (done).** The first real engine behind the frozen `build` signature: deterministic node/edge projection, subgraph detection, observation generation, and finding detection from a resolved Historical Dataset, strictly by reference (Recommendation 2), never independent analysis or re-implementation of any subsystem's own reasoning — decomposed into independent, modular collaborators rather than one large engine. A private `HistoricalDatasetProvider` (Recommendation 9, mirroring ADR-0022 §D9) resolves `HistoricalDatasetReference` into an engine-internal dataset since no real Historical Dataset implementation exists yet. See §D10.
- **CAP-084B.1 — KnowledgeGraphResult Runtime Contract Freeze (done).** Permanently certifies `KnowledgeGraphResult` as the canonical Layer 2 runtime contract (§D11) — no field, validator, or signature change; documentation and architecture tests only, mirroring CAP-083B.1.
- **CAP-084C — Runtime Integration (done).** Wires `build` into the live pipeline immediately after Continuous Improvement, adds the `KnowledgeGraphSerializer` Execution Package projection, and re-baselines the golden dataset `1.5.0` → `1.6.0`, mirroring CAP-083C's activation of Continuous Improvement (ADR-0022 §D11). See §D12.
- **Graph storage** (reserved) — a future Neo4j, RDF, property graph, SQL, or in-memory implementation behind `KnowledgeGraphService.build`'s unchanged signature (Recommendation 5).
- **Future AI graph reasoning, graph embeddings, graph traversal, and Graph RAG** (all reserved) — higher-layer or engine-variant capabilities that consume `KnowledgeGraphResult` (or a future graph storage backing it) without ever becoming part of this contract; any peer engine variant must satisfy Recommendation 7's determinism-first discipline for graph *construction* specifically, while reasoning/traversal/RAG capabilities built atop the constructed graph are separate, later, higher-layer owners (Recommendation 6).
- **Runtime activation (CAP-084C, done)** — `build` wired into the live pipeline immediately after Continuous Improvement, the Execution Package projection added, golden dataset re-baselined `1.5.0` → `1.6.0`, mirroring CAP-083C's activation of Continuous Improvement (ADR-0022 §D11). See §D12.
- **CAP-085 (Organizational Memory), CAP-086 (Learning Framework)** — the remaining reserved Layer 2 capabilities (ADR-0020), each to declare its own Truth Hierarchy level per ADR-0021 Recommendation 11.
- Promotion of the shared version/identity value-objects (and the now twice-duplicated `HistoricalDatasetReference` shape) to `shared/` (the debt ADR-0015 §C, ADR-0016, ADR-0017, ADR-0018 §D5, ADR-0019 §D5, and ADR-0022 already name).

## Ownership, runtime position, governance

- **Owns:** the canonical platform graph — nodes, governed relationship edges, subgraphs, deterministic structural observations, deterministic structural findings, Knowledge Graph metadata.
- **Does not own:** Engineering Context Orchestration, Analysis, Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, Continuous Improvement, the Execution Package, or the Historical Dataset itself (ADR-0021 §Stage 6 names that owner, not this ADR). Does not own any subsystem-local relationship model (e.g. `RelationshipGraph`) — those remain owned exactly where they already are (§D9, Recommendation 10).
- **Runtime position (live — CAP-084C):** `HistoricalDatasetReference` → (private `HistoricalDatasetProvider` → engine-internal `HistoricalDataset`) → `NodeProjector` → `EdgeProjector` → `SubgraphDetector` → `ObservationEngine` → `FindingEngine` → `SummaryBuilder`/`MetricsBuilder` → `ResultBuilder` → `KnowledgeGraphResult` → `KnowledgeGraphSerializer` → Execution Package → Manifest → Release. Architecture frozen; the deterministic engine exists and is fully tested; `KnowledgeGraphResult` is constitutionally certified as the permanent runtime contract (§D11); the CLI wires `build` into the live pipeline immediately after Continuous Improvement (§D12).
- **Governance:** registered as CAP-084 for the Requirement Intelligence Platform's Layer 2 — the second capability built under ADR-0020/ADR-0021, following Continuous Improvement (ADR-0022) — and the second to go live. This ADR is **Accepted**; CAP-084B extends it with the first deterministic engine under an unchanged contract; CAP-084B.1 permanently certifies that contract; CAP-084C activates it in the live runtime, exactly mirroring ADR-0022's own CAP-083C activation.
