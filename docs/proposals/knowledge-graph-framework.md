# Knowledge Graph Framework — Design Proposal

- **Status:** Accepted (CAP-084A froze the architecture; CAP-084B implemented the first deterministic engine behind it, unchanged; CAP-084B.1 permanently certified the runtime contract, no behaviour change; CAP-084C activated the runtime and Execution Package in the live pipeline)
- **Capability:** CAP-084 — Knowledge Graph Framework
- **Milestones covered:** CAP-084A (Architecture & Governance Freeze), CAP-084B (Deterministic Knowledge Graph Engine — see §8a), CAP-084B.1 (KnowledgeGraphResult Runtime Contract Freeze — see §8b), CAP-084C (Runtime Integration & Execution Package Activation — see §8c)
- **Governed by:** ADR-0023
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution), ADR-0022 (Continuous Improvement Framework — the first Layer 2 capability and this framework's direct architectural precedent, including its own CAP-083B.1 runtime contract freeze and CAP-083C runtime integration), ADR-0024 (Historical Dataset & Historical Truth Constitution).

---

## 1. Problem

Layer 1 answers questions about one execution. ADR-0022 built Layer 2's first capability, Continuous Improvement, which answers questions about recurrence *of values* across many executions — which finding keeps recurring, which metric is trending. Neither layer answers a different, structural question: *given every entity and relationship this platform has ever produced, how does everything connect?* Which requirement traces to which evidence, which module depends on which component, which execution generated which finding, which recommendation addresses which requirement — across the whole platform, never scoped to one execution and never re-implementing any one subsystem's own local reasoning about its own concerns.

**No subsystem answers this today** (confirmed by the Stage 0 assessment of CAP-084A, ADR-0023). Left unbuilt, every future consumer needing cross-subsystem structure would have to re-derive it ad hoc from whatever local relationship models happen to exist; built as an extension of Requirement Enhancement, Continuous Improvement, or any other existing subsystem, it would fuse a distinct responsibility into an owner that already has one — exactly the coupling ADR-0001 forbids.

## 2. Scope of CAP-084A

CAP-084A is a **pure architecture milestone**. It freezes:

- the subsystem and its ownership boundary
- the canonical runtime contract, `KnowledgeGraphResult`
- the canonical models (`KnowledgeNode`, `KnowledgeEdge`, `KnowledgeSubgraph`, `KnowledgeObservation`, `KnowledgeFinding`, `KnowledgeSummary`, `KnowledgeMetrics`, `HistoricalDatasetReference`)
- the typed identities (`KnowledgePolicyId`, `KnowledgeGraphId`, `KnowledgeNodeId`, `KnowledgeEdgeId`, `KnowledgeSubgraphId`, `KnowledgeObservationId`, `KnowledgeFindingId`, `KnowledgeGraphResultId`)
- the independent version axes (`KnowledgeGraphFrameworkVersion`, `KnowledgePolicyVersion`, `KnowledgeNodeVersion`, `KnowledgeEdgeVersion`, `KnowledgeObservationVersion`, `KnowledgeGraphResultVersion`)
- the governed `KnowledgeGraphPolicy` (capability switches, deterministic thresholds)
- the dormant `KnowledgeGraphService` contract, registered with `PlatformContext`

**CAP-084A does not implement graph generation.** No node is ingested, no edge is ingested, no subgraph is partitioned, no observation is recorded, no finding is detected. No serializer, no Execution Package integration, no CLI phase, no Platform Version bump, no Architecture Version bump, no golden dataset change.

## 3. Stage 0 — Repository assessment (no redesign)

Every existing graph-like structure was reviewed before writing this proposal:

| Structure | Owner | Scope | Why it is not a platform Knowledge Graph |
|---|---|---|---|
| `RelationshipGraph` | `RequirementEnhancementResult` (ADR-0018) | One enhancement execution | Real graph shape (nodes + typed edges + validator), but strictly single-execution; performs no graph algorithm. |
| Grounding's evidence links | `GroundedRequirement.evidence_links` | One grounding execution | Graph-*shaped* prose, but implemented as a flat per-requirement link list — no shared node set, no graph container. |
| Validation | none | N/A | Deliberately dependency-free (Rule Independence); the only ordering concept is a fixed enum layer sequence, not a relationship graph. |
| `RecommendationReference` | `Recommendation` (ADR-0019) | One recommendation execution | A flat citation (source, id, version) — no node/edge validator, no shared node set. |
| `contributing_execution_ids` | `ImprovementFinding` / `ImprovementTrend` (ADR-0022) | One historical dataset | A flat id list, validated only for count/uniqueness — not a graph. |
| `ContextCorrelation` / `ContextDependencies` | `EngineeringContext` (ADR-0015) | One orchestrated context, reserving a cross-context slot | The closest existing structure to a genuine graph, but its `related_context_ids` slot is empty today — reserved, not populated or queryable. |

A full-repository grep for `knowledge_graph`, `KnowledgeGraph`, and "platform graph" found no code module anywhere — every hit is documentation naming CAP-084 as a reserved, unbuilt capability. **This is a greenfield capability**; no redesign of any existing structure is needed or proposed. Every structure above remains exactly where it is, owned by exactly the subsystem that already owns it (ADR-0023 §D9, Recommendation 10).

> No architectural weakness found. Proceeding with a pure architecture and governance freeze.

## 4. Subsystem & ownership

`requirement_intelligence/knowledge_graph/` owns **only**:

- the canonical graph (`KnowledgeGraphResult`)
- nodes (`KnowledgeNode`)
- edges (`KnowledgeEdge`)
- graph partitions (`KnowledgeSubgraph`)
- graph metadata (identities, versions, policy)
- graph observations (`KnowledgeObservation`)
- graph findings (`KnowledgeFinding`)
- graph summaries and metrics (`KnowledgeSummary`, `KnowledgeMetrics`)

It never owns Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, Continuous Improvement, the Execution Package, the Historical Dataset itself, Feature Engineering, Prediction, Optimization, or Autonomous Execution (Recommendation 1, ADR-0023).

## 5. Canonical models

Every model is immutable (`Schema`, `frozen=True`), tuple-backed where it holds a collection, camelCase-serialising, and validator-guarded only for **structural integrity** — no behavior, no inference:

- **`KnowledgeNode`** — one platform entity (`node_id`, governed `node_type`, `referenced_id`, `label`). Never owns the entity itself — only its identifier (Recommendation 2).
- **`KnowledgeEdge`** — one governed relationship (`edge_id`, governed `edge_type`, `source_node_id`, `target_node_id`, `rationale`). No free-form edge type is ever accepted (Recommendation 3).
- **`KnowledgeSubgraph`** — one coherent graph partition (`subgraph_id`, `label`, `node_ids`, `edge_ids`) — member nodes/edges by reference only, never copied.
- **`KnowledgeObservation`** — one deterministic structural fact (`observation_id`, governed `category`, `subject_node_ids`, `subject_edge_ids`, `description`). No AI, no prediction (Recommendation 7).
- **`KnowledgeFinding`** — one deterministic structural issue (`finding_id`, governed `category`, `severity`, `subject_node_ids`, `subject_edge_ids`, `message`) — isolated node, broken lineage, duplicate edge, orphan graph, missing relationship, cycle. Must reference at least one node or edge (explainability, mirrors `ImprovementOpportunity`).
- **`KnowledgeSummary`** / **`KnowledgeMetrics`** — human-readable aggregate and graph statistics only (node/edge/subgraph/observation/finding counts, connected components, average degree, orphan nodes) — recorded values, never model-internal calculations.
- **`HistoricalDatasetReference`** — duplicated (not imported) from Continuous Improvement's own type of the same name and shape, per the self-containment discipline every subsystem's base types already follow.
- **`KnowledgeGraphResult`** — the canonical runtime contract: every node, edge, subgraph, observation, finding, the summary, the metrics, the governing policy identity/version, and the consumed `HistoricalDatasetReference`.

## 6. Explainability invariant

Every `KnowledgeEdge`'s endpoints must exist among the result's nodes. Every `KnowledgeSubgraph`'s member ids must exist among the result's own nodes/edges. Every `KnowledgeObservation`'s and `KnowledgeFinding`'s subject ids must exist among the result's nodes/edges. A `KnowledgeFinding` with zero subject references is not constructible — a structural issue with no traceable evidence is not explainable (ADR-0023 §D4/§D7, Recommendation 8).

## 7. Governed policy

`KnowledgeGraphPolicy` — immutable, declarative, no executable logic:

- **`KnowledgeGraphCapabilitySwitches`** — independent on/off switches: `enable_node_ingestion`, `enable_edge_ingestion`, `enable_subgraph_partitioning`, `enable_observation_generation`, `enable_finding_detection` (all `True` by default — governed intent, no engine reads them yet), plus `enable_deterministic_engine` / `enable_ml_engine` / `enable_llm_engine` (all reserved `False` until a future engine milestone).
- **`KnowledgeGraphThresholds`** — governed numeric bounds a future engine must respect: `max_nodes_per_graph`, `max_edges_per_graph`, `max_traversal_depth` (with a validator enforcing the traversal bound never exceeds the node bound).

A `KnowledgeGraphPolicyBuilder` and `default_knowledge_graph_policy()` assemble the CAP-084A default at `KnowledgePolicyVersion` 1.0.0.

## 8. Runtime boundary (frozen, dormant)

`KnowledgeGraphService` exposes exactly one method:

```python
def build(
    self,
    historical_dataset: HistoricalDatasetReference,
) -> KnowledgeGraphResult:
    ...
```

It depends only on the `HistoricalDatasetReference` it consumes — never an *implementation* class, never a Layer 1 subsystem, and never Continuous Improvement (a stricter boundary than any Layer 1 subsystem imposes on its peers — Recommendation 1). Abstract at CAP-084A; `DormantKnowledgeGraphService` raised `NotImplementedError`. CAP-084B implements the method behind this unchanged signature, exactly as CAP-083B implemented `ContinuousImprovementService.improve` behind the ADR-0022 boundary.

## 8a. CAP-084B — Deterministic Knowledge Graph Engine

CAP-084B is that later milestone: it implements `build` behind the unchanged signature above, exactly as ADR-0023 §D10 describes.

**Modular architecture (new discipline).** Unlike every prior engine in this platform, `DeterministicKnowledgeGraphEngine` is not one large class — it is a thin pipeline orchestrator over independent, single-responsibility collaborators, none exported, none a runtime contract: `NodeProjector` / `EdgeProjector` (`engine/projection/`), `SubgraphDetector` / `ObservationEngine` / `FindingEngine` (`engine/analysis/`), and `SummaryBuilder` / `MetricsBuilder` / `ResultBuilder` (`engine/builders/`).

**Rule catalogue.** `knowledge_graph/rules/` introduces `KnowledgeGraphRule` (metadata only — id, `KnowledgeGraphRuleFamily`, the governed node/edge type or finding category + severity it names, a policy reference, an enable switch), `KnowledgeGraphRuleCatalog` (ordering/lookup only), and `KnowledgeGraphRuleBuilder`/`default_knowledge_graph_rule_catalog()` shipping 22 governed rules: 7 NODE, 9 EDGE, 6 STRUCTURAL.

**Historical Dataset Resolution Principle (Recommendation 9).** `HistoricalDatasetReference` still carries provenance only — no Historical Dataset implementation exists. `DeterministicKnowledgeGraphEngine` resolves it through a private, constructor-injected `HistoricalDatasetProvider` into an engine-internal `HistoricalDataset`: not a runtime contract, not Historical Truth, not Derived Knowledge, never exported past the package boundary — the identical pattern CAP-083B established for Continuous Improvement, deliberately replicated (never imported across the two packages). The CAP-084B default, `DeterministicHistoricalDatasetProvider`, synthesizes reproducible per-execution facts as a pure function of the reference's own fields (SHA-256 digests — no UUID, no clock).

**Deterministic algorithms.** Node/edge projection: direct lookup-and-construct from named entity ids. Subgraph detection: connected-component BFS. Observation/finding detection: arithmetic, set operations, and graph traversal (longest-chain search, iterative cycle detection). No AI, no prediction, no statistics beyond these.

**Policy governance.** Every capability the engine exercises is read from `KnowledgeGraphPolicy` via each rule's `policy_reference` — never hard-coded. `KnowledgePolicyVersion` advances 1.0.0 → 1.1.0 for this value change (Recommendation 5); the policy's *shape* is unchanged.

**Explainability.** Every node/edge/observation/finding names the exact ids it concerns — reaffirming Recommendation 8, now exercised by a real engine.

**Derived Knowledge principle.** Every execution of `build` derives its graph directly from the resolved `HistoricalDataset` — never from a prior `KnowledgeGraphResult` or any of its constituents (mirrors ADR-0022 Recommendation 11).

**Still not activated.** `PlatformContext.create_knowledge_graph_service()` now returns `DeterministicKnowledgeGraphService`, replacing `DormantKnowledgeGraphService` (which CAP-084B removes). `create_knowledge_graph_rule_catalog()` is added alongside `create_knowledge_graph_policy()`. Still unwired: nothing calls `build()` at runtime, so the golden baseline, Architecture Version, and Platform Version are all unchanged.

**Tests.** New deterministic tests cover rule catalogue construction, projection determinism, subgraph detection, observation generation, every finding category (including cycle detection), builder single-computation guarantees, end-to-end engine determinism and explainability, policy gating, and containment (no Layer 1 imports, no Continuous Improvement import, no serializer, no Execution Package, no CLI, no graph database, provider stays private).

## 8b. Runtime Contract Freeze (CAP-084B.1)

CAP-084B.1 permanently certifies `KnowledgeGraphResult` as the runtime contract
of the Knowledge Graph Framework, before the subsystem is activated in the live
pipeline — mirroring CAP-080B.1.1 (`QualityAssessmentResult`), CAP-081B.1
(`RequirementEnhancementResult`), CAP-082B.1 (`RecommendationResult`), and
CAP-083B.1 (`ContinuousImprovementResult`). **No runtime behaviour changes.** No
field, no computation, no signature changed; only documentation and
architecture-only tests were added. Full detail lives in ADR-0023 §D11;
summarised here:

**Frozen definition.** `KnowledgeGraphResult` is *the complete deterministic
runtime record produced from exactly one execution of*
`KnowledgeGraphService.build()`.

- **IS:** the complete runtime output of one Knowledge Graph build; the
  canonical Layer 2 structural representation; Derived Knowledge;
  self-contained; independently versioned; deterministic; explainable;
  projection-independent.
- **IS NOT:** Historical Truth; graph storage; a graph database; execution
  history; an execution package; a report; a renderer; a serializer; a CLI
  object; a mutable graph.

**Ownership (no overlap).** `NodeProjector`/`EdgeProjector` own projection only.
`SubgraphDetector` owns partitioning only. `ObservationEngine`/`FindingEngine`
own structural analysis only. `SummaryBuilder`/`MetricsBuilder` own aggregation
only. The private `HistoricalDatasetProvider` owns resolving a reference into
an internal `HistoricalDataset` only — never a runtime contract.
`DeterministicKnowledgeGraphEngine` owns pipeline orchestration of those
collaborators only. `KnowledgeGraphService` owns orchestration only.
`KnowledgeGraphResult` owns nodes, edges, subgraphs, observations, findings,
summary, metrics, provenance, and governing policy identity/version only — it
never owns runtime engines, the Historical Dataset, graph storage, the
execution package, reports, serialization, a graph database, or future graph
embeddings/Graph RAG/ML reasoning. A future serializer owns projection only. A
future Execution Package owns packaging only. `PlatformContext` owns
composition only.

**Explainability.** Every node, edge, subgraph, observation, finding, and
summary/metrics value is reconstructable solely from `KnowledgeGraphResult` —
no provider inspection, no engine rerun, no graph storage inspection required.

**Runtime boundary.** Runtime ends at `KnowledgeGraphResult`. Everything after
it — serializers, reports, dashboards, Markdown, graph storage, the Execution
Package — is projection, and must consume `KnowledgeGraphResult` only, never
the engine, the provider, the service, or `PlatformContext`:

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

**Historical Dataset Resolution Principle (frozen permanently, mirrors
ADR-0022 Recommendation 10).** `HistoricalDatasetReference` intentionally
carries provenance only. Implementations may resolve the referenced dataset
through private collaborators. The resolved dataset is an implementation
detail; the public runtime boundary remains `HistoricalDatasetReference →
KnowledgeGraphResult`. `HistoricalDatasetProvider` remains private,
replaceable, and constructor-injected.

**Derived Knowledge principle (frozen permanently, Recommendation 11).**
`KnowledgeGraphResult` is Derived Knowledge. It never becomes Historical
Truth. Historical Truth never becomes Runtime Truth. Knowledge Graph must
never recursively consume its own prior Derived Knowledge.

**Version-axis independence.** Eight distinct version types exist —
`KnowledgeGraphFrameworkVersion`, `KnowledgePolicyVersion`,
`KnowledgeGraphRuleVersion`, `KnowledgeGraphRuleCatalogVersion`,
`KnowledgeNodeVersion` (reserved), `KnowledgeEdgeVersion` (reserved),
`KnowledgeObservationVersion` (reserved), `KnowledgeGraphResultVersion` (the
only axis stamped onto a model today) — each evolving independently.
`KnowledgeSubgraph`, `KnowledgeFinding`, and `KnowledgeSummary`/
`KnowledgeMetrics` carry no dedicated schema-version type of their own — a
deliberate architectural consolidation, not a gap. No new version type was
invented for this certification.

**Future engine compatibility.** Future deterministic, ML, LLM, Graph Neural
Network, graph database, and Graph RAG engines must all reuse
`KnowledgeGraphResult` without contract changes.

**Certification.** `KnowledgeGraphResult` is constitutionally certified as
the permanent Layer 2 runtime contract for Knowledge Graph — completing
Architecture Freeze (CAP-084A) → Deterministic Implementation (CAP-084B) →
Runtime Contract Freeze (CAP-084B.1). Runtime Integration (CAP-084C, done)
was the only remaining step before this framework went live — see §8c.

## 8c. Knowledge Graph Runtime, Serializer, Execution Package, Golden Integration (CAP-084C)

CAP-084C activates the already-complete Knowledge Graph Framework in the live
Requirement Intelligence runtime — Layer 2's second capability going live. No
redesign: no frozen contract, policy shape, or engine behaviour changed. Full
detail lives in ADR-0023 §D12; summarised here:

**Knowledge Graph Runtime.** Knowledge Graph executes exactly once,
immediately after Continuous Improvement, at the permanently frozen end of
the pipeline:

```
... Recommendation → Historical Dataset → Continuous Improvement
    → Knowledge Graph → Execution Package
```

It consumes exactly one `HistoricalDatasetReference` — never a Layer 1 peer
result, and never `ContinuousImprovementResult` (Recommendation 1/9). No real,
multi-execution Historical Dataset implementation exists yet (ADR-0021
§Stage 6, reserved), so the CLI reuses the exact deterministic single-execution
minting strategy CAP-083C introduced (`execution_count` = `history_window` =
1, `first_execution_id` = `last_execution_id` = this run's own
`execution_id`, `generated_at` = this run's own `completed_at`) — never a
second minting strategy, just against the deliberately duplicated
`knowledge_graph.models.HistoricalDatasetReference` type. The CLI's
`run_knowledge_graph_phase` obtains `KnowledgeGraphService` exclusively from
`PlatformContext` and calls `build(historical_dataset)` — identical failure
semantics to every peer subsystem (surfaced, never fatal), and runs whenever
this is a live run.

**Unlike Continuous Improvement's always-empty golden shape.** Continuous
Improvement's single-execution reference satisfies neither its recurrence nor
trend floor, so the golden dataset always observes an empty
`ContinuousImprovementResult`. Knowledge Graph's CAP-084B provider has no such
floor: it unconditionally synthesizes a requirement, an execution, and a
dataset node from every reference, plus up to four more node types
conditionally, gated by a digest of the reference's own `dataset_id` (which
embeds this run's random `execution_id`). The golden dataset therefore always
observes a small, genuine, non-empty `KnowledgeGraphResult` whose exact
node/edge count legitimately varies across independent runs while remaining
perfectly reproducible for any fixed reference — the golden baseline asserts
structural bounds and invariants (3–7 nodes, exactly one connected component,
at most one finding — a documented `CYCLE` finding is possible when both
`capability` and `document` nodes co-occur, ADR-0023 §D12), never an exact
literal count.

**Knowledge Graph Serializer (`knowledge_graph/serialization/`).**
`KnowledgeGraphSerializer` renders `knowledge_graph_result.json` (canonical
`model_dump`), `knowledge_graph_report.md`, and `knowledge_graph_metrics.md` —
a pure projection computing nothing; every rendered value already exists
inside `KnowledgeGraphResult`. It imports no engine, service, policy, rule
catalogue, or `HistoricalDatasetProvider` implementation.

**Execution Package.** `ExecutionData.knowledge_graph_result` is
additive-only (no existing field changed). `ExecutionWriter` appends the three
Knowledge Graph artifacts only when `knowledge_graph_result` is present — the
same conditional-append mechanism as every other peer subsystem, no special
case, written immediately after the Continuous Improvement artifacts.

**Manifest purity (mirrors ADR-0017 §D31, ADR-0022 §D11).** The manifest gains
exactly three additive keys — `knowledgeGraphExecuted`,
`knowledgeGraphReport`, `knowledgeGraphMetrics` — a flag and two artifact
filenames. No node, edge, subgraph, observation, finding, summary, or metric
value is ever copied into the manifest; that runtime state lives exclusively
in `KnowledgeGraphResult` / `knowledge_graph_result.json`.

**Golden integration.** `_run_golden_pipeline()` now builds immediately after
Continuous Improvement; `PipelineResult` carries `knowledge_graph_result`. The
golden dataset re-baselines `GOLDEN_DATASET_VERSION` `1.5.0` → `1.6.0` — the
nine source artifacts and the golden response are unchanged; only the
generated artifact set grows by the three Knowledge Graph files. The
Architecture Version remains `1.2.0`; the Platform Version is unchanged.

**One-way dependency chain (frozen).**

```
Knowledge Graph Runtime (engine + service)
    → KnowledgeGraphResult
    → Knowledge Graph Serializer
    → Execution Package
    → Manifest
    → Release
```

## 9. PlatformContext

`PlatformContext` exposes three composition-root methods, construction only:

- `create_knowledge_graph_policy() -> KnowledgeGraphPolicy`
- `create_knowledge_graph_rule_catalog() -> KnowledgeGraphRuleCatalog` (CAP-084B)
- `create_knowledge_graph_service() -> KnowledgeGraphService` (returns `DeterministicKnowledgeGraphService`, CAP-084B; live in the pipeline since CAP-084C)

Mirroring `create_improvement_policy()` / `create_improvement_rule_catalog()` / `create_continuous_improvement_service()` (ADR-0022), these are the **only** sanctioned points outside the `knowledge_graph` package that may construct its objects, enforced by a containment test.

## 10. Execution package

Activated by CAP-084C (§8c). Every Knowledge Graph execution artifact is a **pure projection** of `KnowledgeGraphResult`, reproducible from it alone, computing nothing — the same serialization invariant ADR-0022 §D8 established for Continuous Improvement (Recommendation 8: runtime before reporting).

## 11. Implementation roadmap (non-normative)

1. **Done (CAP-084A).** Architecture & governance freeze: canonical models, typed identities, independent version axes, governed policy, dormant service contract, `PlatformContext` registration.
2. **Done (CAP-084B).** Deterministic Knowledge Graph Engine: derive nodes/edges/subgraphs/observations/findings strictly from a resolved Historical Dataset (Recommendation 2), projecting subsystem-local structures (e.g. `RelationshipGraph`) by reference, never re-implementing their reasoning — via independent, modular collaborators. See §8a.
3. **Done (CAP-084B.1).** `KnowledgeGraphResult` Runtime Contract Freeze: permanent certification, no behaviour change. See §8b.
4. **Done (CAP-084C).** Runtime activation — `build` wired into the pipeline after Continuous Improvement, the Execution Package projection added, golden dataset re-baselined `1.5.0` → `1.6.0`. See §8c.
5. Historical Dataset implementation (reserved, ADR-0021 §Stage 6, ADR-0024) — the actual storage/ordering/lineage/retention/indexing/search `HistoricalDatasetReference` currently only names, and that a future `HistoricalDatasetProvider` may resolve against instead of the CAP-084B deterministic synthesis.
6. Graph storage (reserved) — a future Neo4j, RDF, property graph, SQL, or in-memory implementation behind the unchanged `build` signature (Recommendation 5).
7. Future AI graph reasoning, graph embeddings, graph traversal, and Graph RAG (reserved), behind the unchanged `KnowledgeGraphResult` contract — never a redesign of it.
8. CAP-085 (Organizational Memory), CAP-086 (Learning Framework) — the remaining reserved Layer 2 capabilities.

Each lands behind the unchanged `build` signature and the unchanged `KnowledgeGraphResult` contract — no architectural change required.

## 12. Terminology

- **Knowledge node** — one platform entity, referenced by id only (`KnowledgeNode`).
- **Knowledge edge** — one governed, directed relationship between two nodes (`KnowledgeEdge`).
- **Knowledge subgraph** — one coherent partition of the canonical graph, by reference only (`KnowledgeSubgraph`).
- **Knowledge observation** — one deterministic structural fact, never a judgement (`KnowledgeObservation`).
- **Knowledge finding** — one deterministic structural issue (`KnowledgeFinding`).
- **Knowledge Graph Framework** is a distinct capability from every Layer 1 subsystem and from Continuous Improvement — a peer consumer of Historical Truth, a projector of subsystem-local structures, extending none of them and owning none of their responsibilities.
