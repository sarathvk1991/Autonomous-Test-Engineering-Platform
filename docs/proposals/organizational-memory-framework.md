# Organizational Memory Framework — Design Proposal

- **Status:** Proposed (CAP-085A froze the architecture; CAP-085A.1 froze the future engine's internal decomposition and governance; CAP-085B implemented the first deterministic engine behind it, unchanged; CAP-085B.1 permanently certified the runtime contract, no behaviour change)
- **Capability:** CAP-085 — Organizational Memory Framework
- **Milestones covered:** CAP-085A (Architecture & Governance Freeze), CAP-085A.1 (Engine Architecture Refinement & Governance Freeze — see §8a), CAP-085B (Deterministic Organizational Memory Engine — see §8b), CAP-085B.1 (OrganizationalMemoryResult Runtime Contract Freeze — see §8c)
- **Governed by:** ADR-0027
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution), ADR-0025 (Derived Knowledge Architecture & Layer 2 Constitution — the fan-in exception this framework is the first concrete implementation of), ADR-0026 (Organizational Knowledge Architecture & Learning Constitution — the full constitutional definition of what this framework produces).

---

## 1. Problem

Layer 1 answers questions about one execution. Continuous Improvement (ADR-0022) answers questions about recurrence *of values* across many executions. Knowledge Graph (ADR-0023) answers questions about the *structure* connecting entities across the platform. Neither answers a third, different question ADR-0026 §Stage 10 already names: *given everything Continuous Improvement and Knowledge Graph have each concluded, what deserves to be remembered?*

**No subsystem answers this today** (confirmed by the Stage 0 assessment of CAP-085A, ADR-0027). Left unbuilt, every future consumer needing curated, trustworthy, cross-capability knowledge would have to re-derive it ad hoc from raw Continuous Improvement and Knowledge Graph output; built as an extension of either existing subsystem, it would fuse a distinct responsibility into an owner that already has one — exactly the coupling ADR-0001 forbids.

## 2. Scope of CAP-085A

CAP-085A is a **pure architecture milestone**. It freezes:

- the subsystem and its ownership boundary
- the canonical runtime contract, `OrganizationalMemoryResult`
- the canonical models (`Experience`, `Lesson`, `BestPractice`, `KnowledgePromotion`, `KnowledgeLifecycle`, `OrganizationalMemorySummary`, `OrganizationalMemoryMetrics`)
- the typed identities (`OrganizationalMemoryPolicyId`, `OrganizationalMemoryId`, `ExperienceId`, `LessonId`, `BestPracticeId`, `KnowledgePromotionId`, `KnowledgeLifecycleId`, `OrganizationalMemoryResultId`)
- the independent version axes (`OrganizationalMemoryFrameworkVersion`, `OrganizationalMemoryPolicyVersion`, `LessonVersion`, `BestPracticeVersion`, `KnowledgeLifecycleVersion`, `OrganizationalMemoryResultVersion`)
- the governed `OrganizationalMemoryPolicy` (capability switches, deterministic thresholds)
- the dormant `OrganizationalMemoryService` contract, registered with `PlatformContext`

**CAP-085A does not implement curation.** No experience is captured, no lesson is promoted, no best practice is institutionalized, no lifecycle is recorded. No serializer, no Execution Package integration, no CLI phase, no Platform Version bump, no Architecture Version bump, no golden dataset change.

## 3. Stage 0 — Repository assessment (no redesign)

| Structure | Owner | Scope | Why it is not Organizational Memory |
|---|---|---|---|
| `ContinuousImprovementResult` | Continuous Improvement (ADR-0022) | One Historical Dataset's recurrence | Observes recurrence *of values* — findings, trends, opportunities — never curates a cross-capability conclusion into a Lesson or Best Practice. |
| `KnowledgeGraphResult` | Knowledge Graph (ADR-0023) | One Historical Dataset's structure | Projects structural connections — nodes, edges, subgraphs — never curates a Lesson or promotes a Best Practice. |
| ADR-0020 Layer 2 reservation (CAP-085/086) | Names, not implementations | No code exists for either remaining reserved Layer 2 capability. |

A full-repository grep for `lesson`, `experience`, `best practice`, `organizational memory`, and `knowledge promotion` found no code module anywhere — every hit is either this milestone's own reservation or unrelated prose (e.g. "the RC-1 lesson" in ADR-0016, a narrative idiom). **This is a greenfield capability**; no redesign of Continuous Improvement or Knowledge Graph is needed or proposed. Both remain exactly where they already are, owned by exactly the subsystem that already owns them (ADR-0027 §D1, Recommendation 1).

> No architectural weakness found. Proceeding with a pure architecture and governance freeze.

## 4. Subsystem & ownership

`requirement_intelligence/organizational_memory/` owns **only**:

- the canonical curated memory (`OrganizationalMemoryResult`)
- experiences (`Experience`)
- lessons (`Lesson`)
- best practices (`BestPractice`)
- promotion history (`KnowledgePromotion`)
- lifecycle state (`KnowledgeLifecycle`)
- Organizational Memory metadata (identities, versions, policy)
- memory summaries and metrics (`OrganizationalMemorySummary`, `OrganizationalMemoryMetrics`)

It never owns Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, Continuous Improvement, Knowledge Graph, the Execution Package, the Historical Dataset itself, Learning Framework, Feature Engineering, Prediction, Optimization, or Autonomous Execution (Recommendation 1, ADR-0027).

## 5. Canonical models

Every model is immutable (`Schema`, `frozen=True`), tuple-backed where it holds a collection, camelCase-serialising, and validator-guarded only for **structural integrity** — no behavior, no inference:

- **`Experience`** — one captured observation drawn from a completed Continuous Improvement or Knowledge Graph object (`experience_id`, governed `source_layer`, `source_reference_id`, `description`, `confidence`). References the source object by id only — never its content (Recommendation 6 of ADR-0027).
- **`Lesson`** — one explainable conclusion promoted from one or more Experiences (`lesson_id`, `source_experience_ids`, `message`, `confidence`). Must reference at least one Experience (explainability, mirrors `KnowledgeFinding`).
- **`BestPractice`** — one generally-recommended conclusion promoted from one or more Lessons (`best_practice_id`, `source_lesson_ids`, `title`, `description`, `confidence`). Must reference at least one Lesson.
- **`KnowledgePromotion`** — one governed record that a promotion happened (`promotion_id`, `source_ids`, `target_ids`, `rationale`, `promoted_at`, `confidence`, `policy_version`). Records history; never performs promotion.
- **`KnowledgeLifecycle`** — one governed record of a subject's current retirement state (`lifecycle_id`, `subject_id`, governed `state`, `state_reason`). Records state; never transitions it.
- **`OrganizationalMemorySummary`** / **`OrganizationalMemoryMetrics`** — human-readable aggregate and build statistics only (experience/lesson/best-practice/promotion counts, lifecycle-state distribution) — recorded values, never model-internal calculations.
- **`OrganizationalMemoryResult`** — the canonical runtime contract: every experience, lesson, best practice, promotion record, lifecycle record, the summary, the metrics, the governing policy identity/version, and the two consumed Layer 2 result id references.

## 6. Explainability invariant

Every `Lesson`'s `source_experience_ids` must resolve among the result's own `experiences`. Every `BestPractice`'s `source_lesson_ids` must resolve among the result's own `lessons`. Every `KnowledgePromotion`'s `source_ids`/`target_ids`, and every `KnowledgeLifecycle`'s `subject_id`, must resolve among the result's own experience/lesson/best-practice ids. A `Lesson` with zero source experiences, or a `BestPractice` with zero source lessons, is not constructible — a conclusion with no traceable evidence is not explainable (ADR-0027 §D3/§D9, Recommendation 9).

## 7. Governed policy

`OrganizationalMemoryPolicy` — immutable, declarative, no executable logic:

- **`OrganizationalMemoryCapabilitySwitches`** — independent on/off switches: `enable_experience_capture`, `enable_lesson_promotion`, `enable_best_practice_promotion`, `enable_retirement` (all `True` by default — governed intent, no engine reads them yet), plus `enable_deterministic_engine` / `enable_ml_engine` / `enable_llm_engine` / `enable_graph_rag_engine` / `enable_neuro_symbolic_engine` (all reserved `False` until a future engine milestone).
- **`OrganizationalMemoryThresholds`** — governed numeric bounds a future engine must respect: `minimum_experiences_for_lesson`, `minimum_lessons_for_best_practice`, `minimum_confidence_for_best_practice`.

An `OrganizationalMemoryPolicyBuilder` and `default_organizational_memory_policy()` assemble the CAP-085A default at `OrganizationalMemoryPolicyVersion` 1.0.0.

## 8. Runtime boundary (frozen, dormant)

`OrganizationalMemoryService` exposes exactly one method:

```python
def build(
    self,
    continuous_improvement_result: ContinuousImprovementResult,
    knowledge_graph_result: KnowledgeGraphResult,
) -> OrganizationalMemoryResult:
    ...
```

It depends only on the two completed Layer 2 results it consumes — never an *implementation* class, never a Layer 1 subsystem, and never the Historical Dataset directly (ADR-0025 §Stage 7/8's fan-in exception; ADR-0027 §D2/Recommendation 7). Abstract at CAP-085A; `DormantOrganizationalMemoryService` raises `NotImplementedError`. A later CAP-085 milestone implements the method behind this unchanged signature, exactly as CAP-083B implemented Continuous Improvement's own entry point behind the ADR-0022 boundary and CAP-084B implemented Knowledge Graph's own entry point behind the ADR-0023 boundary.

## 8a. CAP-085A.1 — Internal Engine Architecture

CAP-085A.1 freezes the future deterministic engine's internal decomposition and governance *before* CAP-085B implements it — no code, no collaborator class, no rule catalogue exists yet. Full detail lives in ADR-0027's "Internal Engine Architecture" section and D9–D16; summarised here:

**Deterministic engine decomposition (D9).** A modular collaborator pipeline, mirroring Knowledge Graph's own decomposition (ADR-0023 §D10) rather than Continuous Improvement's single-engine-class shape (ADR-0022 §D9):

```
ExperienceCollector → ExperienceClusterer → LessonGenerator → LessonConsolidator
    → BestPracticeGenerator → PromotionRecorder → LifecycleRecorder
    → SummaryBuilder/MetricsBuilder → ResultBuilder
```

Each collaborator owns exactly one responsibility; none computes another's (Recommendation 14).

**Knowledge hierarchy: adjacent promotion only (D10).** Experience → Lesson → Best Practice. Promotion never skips a level (Experience directly to Best Practice is forbidden) and never moves downward — already structurally guaranteed by the CAP-085A model shapes (`Lesson.source_experience_ids` cannot hold a `BestPracticeId`; `BestPractice.source_lesson_ids` cannot hold an `ExperienceId`), now frozen as permanent constitutional intent (Recommendation 13).

**Organizational Knowledge Promotion Principle (D11).** Promotion creates new knowledge; it never edits existing knowledge. Every promotion records source ids, target ids, rationale, policy version, confidence, and provenance (the reconstructable reference chain, D13) — fields `KnowledgePromotion` already carries.

**Engine layering: collaborator visibility (D12).** Each collaborator's permitted inputs and outputs are fixed in advance (see ADR-0027's table) — `SummaryBuilder` and `MetricsBuilder` never compute knowledge, only tally already-recorded rows; `ResultBuilder` alone assembles the final result.

**Complete explainability chain (D13).** `Best Practice → Lesson → Experience → (Continuous Improvement or Knowledge Graph) → Historical Dataset → Execution Ids → Runtime Truth`. No promotion may occur unless this full chain is reconstructable (Recommendation 17).

**Promotion rules: a reserved, conceptual rule catalogue (D14).** A future `PromotionRule` (mirroring `ImprovementRule`/`KnowledgeGraphRule`) is reserved — promotion type, minimum experiences, minimum lessons, confidence threshold, priority, capability switch — governance only, no implementation (Recommendation 16).

**Lifecycle ownership (D15).** `LifecycleRecorder` is the sole owner of lifecycle recording; no generator, builder, or future serializer may create or infer a lifecycle entry.

**Result ownership (D16).** `ResultBuilder` is the sole constructor of `OrganizationalMemoryResult`, exactly mirroring Knowledge Graph's own frozen invariant (ADR-0023 §D10; Recommendation 15).

## 8b. CAP-085B — Deterministic Organizational Memory Engine

CAP-085B is the later milestone §8a's D9–D16 pre-specified: it implements `build` behind the unchanged signature above, exactly as ADR-0027 §D17 describes.

**Modular architecture, exactly as pre-specified.** `DeterministicOrganizationalMemoryEngine` is a thin pipeline orchestrator, never a monolithic class: `ExperienceCollector` → `ExperienceClusterer` → `LessonGenerator` → `LessonConsolidator` → `BestPracticeGenerator` → `PromotionRecorder` → `LifecycleRecorder` → `SummaryBuilder`/`MetricsBuilder` → `ResultBuilder`, each in `organizational_memory/engine/`, each owning exactly one responsibility.

**Rule catalogue.** `organizational_memory/rules/` introduces `PromotionRule` (metadata only — id, `PromotionRuleCategory`, title, description, priority, `capability_switch`, `supported_hierarchy_level`, `documentation_reference` — deliberately no numeric threshold field), `PromotionRuleCatalog` (ordering/lookup/category/level projections only), and `PromotionRuleBuilder`/`default_promotion_rule_catalog()` shipping 24 governed rules across the ten categories §8a's D14 named.

**Deterministic algorithms.** Experience capture: direct reference construction from each named source object, deduplicated by deterministic id. Clustering: byte-equality grouping on `(source_layer, description)` — never semantic similarity. Lesson/Best-Practice generation: floor-gated aggregation against `OrganizationalMemoryThresholds`. Confidence: a deterministic function of evidence-count-over-threshold. No ML, no LLM, no embeddings, no vector search, no semantic similarity, no probabilistic inference, no fuzzy matching, no randomness, no prediction, no statistical learning.

**Ownership.** `ExperienceCollector` is the sole Experience authority; `ExperienceClusterer` the sole clustering authority; `LessonGenerator` the sole Lesson authority; `LessonConsolidator` the sole consolidation authority; `BestPracticeGenerator` the sole Best Practice authority (from Lessons only — never Experiences directly); `PromotionRecorder` the sole promotion authority; `LifecycleRecorder` the sole lifecycle authority; `SummaryBuilder`/`MetricsBuilder` each compute exactly once and compute no knowledge; `ResultBuilder` the sole `OrganizationalMemoryResult` constructor.

**Curation, never analysis.** The engine generates no new technical finding, diagnosis, structural observation, or analytical conclusion — every Experience references an object Continuous Improvement or Knowledge Graph already produced (Recommendation 18).

**Still not activated.** `PlatformContext.create_organizational_memory_service()` now returns `DeterministicOrganizationalMemoryService`, replacing `DormantOrganizationalMemoryService` (which CAP-085B removes). Still unwired: nothing calls `build()` at runtime, so the golden baseline, Architecture Version, and Platform Version are all unchanged.

**Tests.** New deterministic tests cover rule catalogue construction, each collaborator's sole-authority ownership, clustering/generation determinism, floor-gated promotion, confidence scaling, promotion provenance completeness, lifecycle append-only recording, builder single-computation guarantees, end-to-end engine determinism and explainability, policy gating, and containment (no Layer 1 imports, no Historical Dataset touched directly, no peer implementation class imported, provider stays absent, only `PlatformContext` constructs the service externally).

## 8c. Runtime Contract Freeze (CAP-085B.1)

CAP-085B.1 permanently certifies `OrganizationalMemoryResult` as the runtime
contract of the Organizational Memory Framework, before the subsystem is
activated in the live pipeline — mirroring CAP-080B.1.1
(`QualityAssessmentResult`), CAP-081B.1 (`RequirementEnhancementResult`),
CAP-082B.1 (`RecommendationResult`), CAP-083B.1
(`ContinuousImprovementResult`), and CAP-084B.1 (`KnowledgeGraphResult`).
**No runtime behaviour changes.** No field, no computation, no signature
changed; only documentation and architecture-only tests were added. Full
detail lives in ADR-0027 §D18; summarised here:

**Frozen definition.** `OrganizationalMemoryResult` is *the complete
deterministic runtime record produced from exactly one execution of*
`OrganizationalMemoryService.build()`.

- **IS:** the complete runtime output of one Organizational Memory build;
  the canonical Layer 2 curation contract; Organizational Knowledge;
  self-contained; independently versioned; deterministic; explainable;
  projection-independent.
- **IS NOT:** Derived Knowledge; Historical Truth; Runtime Truth; either
  consumed Layer 2 result's own content; an execution package; a report; a
  renderer; a serializer; a CLI object; a mutable ledger.

**Ownership (no overlap).** `ExperienceCollector` owns experience capture
only. `ExperienceClusterer` owns clustering only. `LessonGenerator`/
`LessonConsolidator` own lesson generation/consolidation only.
`BestPracticeGenerator` owns best-practice generation from Lessons only.
`PromotionRecorder` owns promotion-record construction only.
`LifecycleRecorder` owns lifecycle-state record construction only.
`SummaryBuilder`/`MetricsBuilder` own aggregation only.
`DeterministicOrganizationalMemoryEngine` owns pipeline orchestration of
those collaborators only. `OrganizationalMemoryService` owns orchestration
only. `OrganizationalMemoryResult` owns experiences, lessons, best
practices, promotions, lifecycles, summary, metrics, provenance, governing
policy identity/version, and the two consumed Layer 2 result id references
only — it never owns runtime engines, either consumed result's own content,
the execution package, reports, serialization, or future
GraphRAG/ML/neuro-symbolic reasoning. A future serializer owns projection
only. A future Execution Package owns packaging only. `PlatformContext` owns
composition only.

**Explainability.** Every experience, lesson, best practice, promotion, and
lifecycle record is reconstructable solely from `OrganizationalMemoryResult`
— no engine rerun, no service inspection required.

**Runtime boundary.** Runtime ends at `OrganizationalMemoryResult`.
Everything after it — serializers, reports, dashboards, Markdown, the
Execution Package — is projection, and must consume
`OrganizationalMemoryResult` only, never the engine, the service, or
`PlatformContext`:

```
ContinuousImprovementResult + KnowledgeGraphResult
    → DeterministicOrganizationalMemoryEngine
    → OrganizationalMemoryResult
    → Serializer (future)
    → Execution Package (future)
    → Manifest (future)
    → Release
```

**Layer 2 Fan-In Reference Principle (frozen permanently, mirrors ADR-0025
§Stage 7/8).** `OrganizationalMemoryResult` intentionally references the two
consumed Layer 2 results by id only — never embedding either result's
content. The public runtime boundary remains
`ContinuousImprovementResult + KnowledgeGraphResult →
OrganizationalMemoryResult`.

**Organizational Knowledge principle (frozen permanently, Recommendation
19).** `OrganizationalMemoryResult` is Organizational Knowledge. It never
becomes Derived Knowledge, Historical Truth, or Runtime Truth. Organizational
Memory must never recursively consume its own prior Organizational
Knowledge.

**Version-axis independence.** Eight distinct runtime-contract-facing
version types exist — `OrganizationalMemoryFrameworkVersion`,
`OrganizationalMemoryPolicyVersion`, `LessonVersion` (reserved),
`BestPracticeVersion` (reserved), `KnowledgeLifecycleVersion` (reserved),
`PromotionRuleVersion`, `PromotionRuleCatalogVersion`,
`OrganizationalMemoryResultVersion` (the only axis stamped onto a model
today) — each evolving independently. A ninth type,
`OrganizationalMemoryEngineVersion`, versions the engine's own internal
implementation, not any runtime-contract-facing schema, and is excluded from
this count. `Experience`, `KnowledgePromotion`, and
`OrganizationalMemoryMetrics` carry no dedicated schema-version type of
their own; `OrganizationalMemorySummary` carries only the governing policy
version — a deliberate architectural consolidation, not a gap. No new
version type was invented for this certification.

**Future engine compatibility.** Future statistical, ML, LLM, GraphRAG, and
neuro-symbolic engines must all reuse `OrganizationalMemoryResult` without
contract changes.

**Certification.** `OrganizationalMemoryResult` is constitutionally
certified as the permanent Layer 2 runtime contract for Organizational
Memory — completing Architecture Freeze (CAP-085A) → Engine Architecture
Refinement (CAP-085A.1) → Deterministic Implementation (CAP-085B) → Runtime
Contract Freeze (CAP-085B.1). Runtime Integration (CAP-085C, reserved) is
the only remaining step before this framework is live.

## 9. PlatformContext

`PlatformContext` exposes two composition-root methods, construction only:

- `create_organizational_memory_policy() -> OrganizationalMemoryPolicy`
- `create_organizational_memory_service() -> OrganizationalMemoryService`

Mirroring `create_improvement_policy()` / `create_continuous_improvement_service()` (ADR-0022) and `create_knowledge_graph_policy()` / `create_knowledge_graph_service()` (ADR-0023), these are the **only** sanctioned points outside the `organizational_memory` package that may construct its objects, enforced by a containment test.

## 10. Execution package

Not introduced by CAP-085A. When a future milestone activates the runtime, every Organizational Memory execution artifact will be a **pure projection** of `OrganizationalMemoryResult`, reproducible from it alone, computing nothing — the same serialization invariant ADR-0022 §D8 and ADR-0023 §D8 established for their own subsystems (Recommendation 10 of ADR-0027).

## 11. Implementation roadmap (non-normative)

1. **Done (CAP-085A).** Architecture & governance freeze: canonical models, typed identities, independent version axes, governed policy, dormant service contract, `PlatformContext` registration.
2. **Done (CAP-085A.1).** Engine architecture refinement & governance freeze: the future engine's modular collaborator decomposition, adjacent-only promotion discipline, engine layering, the complete explainability chain, and reserved promotion-rule governance — no code, still architecture only. See §8a.
3. **Done (CAP-085B).** Deterministic Organizational Memory Engine: implement the CAP-085A.1 collaborator pipeline strictly from the two resolved Layer 2 results (Recommendation 6 of ADR-0027), never independent analysis. See §8b.
4. **Done (CAP-085B.1).** OrganizationalMemoryResult Runtime Contract Freeze: permanent certification, no behaviour change. See §8c.
5. Runtime activation (CAP-085C, reserved) — wire `build` into a live cross-execution pipeline, add a future Execution Package projection, golden re-baseline, mirroring CAP-083C's activation of Continuous Improvement and CAP-084C's activation of Knowledge Graph.
6. Future AI curation — statistical, ML, LLM, GraphRAG, and neuro-symbolic engines (reserved), behind the unchanged `OrganizationalMemoryResult` contract — never a redesign of it.
7. CAP-086 (Learning Framework) — the remaining reserved Layer 2 capability, to consume `OrganizationalMemoryResult` (Recommendation 8 of ADR-0027).

Each lands behind the unchanged `build` signature and the unchanged `OrganizationalMemoryResult` contract — no architectural change required.

## 12. Terminology

- **Experience** — one captured observation from a completed Layer 2 peer, referenced by id only (`Experience`).
- **Lesson** — one explainable conclusion promoted from one or more Experiences (`Lesson`), still scoped to the evidence that produced it.
- **Best Practice** — one generally-recommended conclusion promoted from one or more verified Lessons (`BestPractice`).
- **Knowledge Promotion** — one governed record that a promotion event occurred (`KnowledgePromotion`) — history, never the act itself.
- **Knowledge Lifecycle** — one governed record of a subject's current retirement state (`KnowledgeLifecycle`) — a record, never a transition.
- **Organizational Memory Framework** is a distinct, Layer 2 capability from every Layer 1 subsystem, and the first Layer 2 capability to legitimately consume two Layer 2 peers (ADR-0025 §Stage 7/8) — a curator of Organizational Knowledge (ADR-0026), extending none of its consumed peers and owning none of their responsibilities.
