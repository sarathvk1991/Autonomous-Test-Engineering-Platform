# ADR-0027 — Organizational Memory Framework

- **Status:** Accepted, live (CAP-085A — Architecture & Governance Freeze; CAP-085A.1 — Engine Architecture Refinement & Governance Freeze; CAP-085B — Deterministic Engine implemented behind the frozen contracts; CAP-085B.1 — `OrganizationalMemoryResult` Runtime Contract permanently certified, no behaviour change; CAP-085C — Runtime Integration, active in the live pipeline)
- **Date:** 2026-07-16 (CAP-085A — Architecture & Governance Freeze); 2026-07-16 (CAP-085A.1 — Engine Architecture Refinement & Governance Freeze); 2026-07-16 (CAP-085B — Deterministic Organizational Memory Engine); 2026-07-16 (CAP-085B.1 — Runtime Contract Freeze); 2026-07-16 (CAP-085C — Runtime Integration)
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** CAP-085A.1 (Engine Architecture Refinement — froze the future deterministic engine's internal decomposition, the adjacent-only promotion discipline, and engine governance *before* any engine existed, mirroring how ADR-0023 §D10 pre-specified Knowledge Graph's own modular decomposition ahead of CAP-084B; see the Internal Engine Architecture section and D9–D16); CAP-085B (Deterministic Organizational Memory Engine — implements the first real engine behind the doubly-frozen contracts, filling exactly the shape D9–D16 pre-specified; see §D17); CAP-085B.1 (permanent `OrganizationalMemoryResult` runtime-contract certification, mirroring CAP-084B.1, CAP-083B.1, CAP-082B.1, CAP-081B.1, and CAP-080B.1.1 — no behaviour change; see §D18); CAP-085C (Runtime Integration — wires `build` into the live pipeline immediately after Knowledge Graph, mirroring CAP-084C's activation of Knowledge Graph; see §D19).
- **Governing design:** `docs/proposals/organizational-memory-framework.md`
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — this is the third Layer 2 capability it names), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — the Truth Hierarchy this framework's every boundary applies), ADR-0025 (Derived Knowledge Architecture & Layer 2 Constitution — the fan-in exception this framework is the first concrete implementation of, ADR-0025 §Stage 7/8), and ADR-0026 (Organizational Knowledge Architecture & Learning Constitution — the full constitutional definition of what this framework produces, including the knowledge hierarchy CAP-085A.1's D10 enforces at the model level). Also informed by ADR-0022 (Continuous Improvement Framework) and ADR-0023 (Knowledge Graph Framework) — the two completed Layer 2 peer capabilities this framework consumes, and the direct architectural precedent this ADR mirrors, including ADR-0023 §D10's modular engine decomposition CAP-085A.1's own D9 mirrored one milestone ahead of implementation, and now CAP-085B has filled, and their own CAP-083B.1 and CAP-084B.1 runtime contract freezes CAP-085B.1 mirrored, and CAP-084C's own runtime integration CAP-085C now mirrors.
- **Runtime status:** **Live (CAP-085C).** `OrganizationalMemoryService.build` has a real implementation, `DeterministicOrganizationalMemoryService`, delegating to a private `DeterministicOrganizationalMemoryEngine` — a thin pipeline orchestrator over independent, modular collaborators (experience collection, clustering, lesson generation/consolidation, best-practice generation, promotion recording, lifecycle recording, summary/metrics/result builders), governed by the `PromotionRuleCatalog` and `OrganizationalMemoryPolicy`, policy-gated, fully explainable — see §D17. `OrganizationalMemoryResult` is constitutionally certified as the permanent runtime contract (§D18). `PlatformContext.create_organizational_memory_service()` constructs the deterministic service by default. `run_organizational_memory_phase` now calls `build` immediately after Knowledge Graph, at the permanently frozen end of the live pipeline, whenever both `ContinuousImprovementResult` and `KnowledgeGraphResult` are present — no `HistoricalDatasetReference` is minted, the fan-in exception exercised live for the first time (§D19). The Architecture Version remains **1.2.0**, `OrganizationalMemoryResultVersion` remains **1.0.0**, the Platform Version is unchanged, and the golden baseline is re-baselined only for the additive Execution Package artifacts (`GOLDEN_DATASET_VERSION` `1.6.0` → `1.7.0`). See §D19.

## Problem

ADR-0020 named Continuous Learning as Layer 2 and reserved four capabilities inside it: CAP-083 (Continuous Improvement), CAP-084 (Knowledge Graph), CAP-085 (Organizational Memory), CAP-086 (Learning Framework). ADR-0022 built the first — Continuous Improvement observes recurrence across a Historical Dataset. ADR-0023 built the second — Knowledge Graph projects structure across the same Historical Dataset. Neither answers a third, different question: *given everything Continuous Improvement and Knowledge Graph have each independently concluded, what deserves to be remembered?* ADR-0026 §Stage 10 already names this the question Organizational Memory alone answers — no existing capability curates, promotes, or institutionalizes a conclusion into something an organization can trust and act on months or years later.

Left unbuilt, and built without a frozen architecture first, the first capability to curate cross-capability knowledge would have to invent, under deadline pressure, exactly the kind of ad hoc answer ADR-0021 §Stage 2 warned against: duplicated curation logic, inconsistent promotion criteria, competing "what we learned" records, and no single place to audit why a Best Practice is trusted.

### Stage 0 — Repository assessment

Before writing this ADR, every prior architectural ADR governing Layer 2 was reviewed:

- **ADR-0020, ADR-0021, ADR-0024, ADR-0025, ADR-0026** — the platform's constitutional documents. Reviewed in full; none conflicts with this ADR, and Stage 0 of this milestone found no inconsistency requiring correction to any of them.
- **ADR-0022 (Continuous Improvement)** and **ADR-0023 (Knowledge Graph)** — both confirmed **completed, live Layer 2 peer capabilities**. Both produce Derived Knowledge (`ContinuousImprovementResult`, `KnowledgeGraphResult` — ADR-0022 §D3, ADR-0023 §D3). Neither owns Organizational Knowledge, a Lesson, a Best Practice, or Organizational Memory itself — confirmed by direct review of both ADRs' Ownership sections and by repository-wide search.
- **Search performed** for `lesson`, `experience`, `best practice`, `organizational memory`, `knowledge promotion` across `requirement_intelligence/`, `docs/adr/`, and `docs/proposals/`: every hit is either this milestone's own reservation (ADR-0020/0022/0023 naming CAP-085 as reserved), or unrelated prose (e.g. "the RC-1 lesson" in ADR-0016, a narrative idiom, not a competing model). **Organizational Memory does not exist anywhere in the repository prior to this milestone.**

**No duplicated ownership, overlapping concept, hidden coupling, or architectural conflict was found.** Continuous Improvement and Knowledge Graph remain exactly where ADR-0022 and ADR-0023 already placed them, unchanged by this milestone.

> No architectural weakness found. Proceeding with a pure architecture and governance freeze.

## Decision

Introduce a new governed subsystem, **`requirement_intelligence/organizational_memory/`**, that will own the curation, promotion, lifecycle, and governance of Organizational Knowledge — built from **two completed Layer 2 peer results**, never from a single execution's Runtime Truth, never from the Historical Dataset directly, and never by re-implementing either peer's own reasoning. It:

1. Introduces canonical, immutable models — `Experience`, `Lesson`, `BestPractice`, `KnowledgePromotion`, `KnowledgeLifecycle`, `OrganizationalMemorySummary`, `OrganizationalMemoryMetrics`, and `OrganizationalMemoryResult` — following the `Schema` conventions and the typed-identity pattern of ADR-0015–ADR-0019, ADR-0022, and ADR-0023.
2. Introduces strongly typed identities — `OrganizationalMemoryPolicyId`, `OrganizationalMemoryId`, `ExperienceId`, `LessonId`, `BestPracticeId`, `KnowledgePromotionId`, `KnowledgeLifecycleId`, `OrganizationalMemoryResultId` — deterministic value objects, no UUIDs, no timestamps, no randomness.
3. Introduces independent version axes — `OrganizationalMemoryFrameworkVersion`, `OrganizationalMemoryPolicyVersion`, `LessonVersion` (reserved), `BestPracticeVersion` (reserved), `KnowledgeLifecycleVersion` (reserved), `OrganizationalMemoryResultVersion` — each evolving without forcing the others to change (Recommendation 5, ADR-0022/ADR-0023 precedent).
4. Introduces a governed `OrganizationalMemoryPolicy` (immutable data: capability switches, deterministic thresholds) with an `OrganizationalMemoryPolicyBuilder` and `default_organizational_memory_policy()`.
5. Fixes the single runtime boundary — `OrganizationalMemoryService.build(continuous_improvement_result: ContinuousImprovementResult, knowledge_graph_result: KnowledgeGraphResult) -> OrganizationalMemoryResult` — as an **abstract, dormant contract**. `PlatformContext` gains `create_organizational_memory_policy()` and `create_organizational_memory_service()`.

The Organizational Memory Framework consumes **Derived Knowledge only** — never Historical Truth directly, never Runtime Truth, never an Execution Package artifact, never a report or a manifest (ADR-0025 §Stage 1/3, ADR-0021 §Stage 7/8). It is the **third Layer 2 peer**, and the first to exercise ADR-0025's fan-in exception: it may consume *both* Continuous Improvement's and Knowledge Graph's completed results, because it is not itself a peer of either — it is their shared, later, downstream consumer (ADR-0025 §Stage 7/8).

**CAP-085A establishes the architecture only.** No experience is captured, no lesson is promoted, no best practice is institutionalized, no lifecycle is recorded, no historical dataset is touched, and nothing is wired into a runtime path. Runtime behaviour is byte-identical; the golden baseline is unchanged; the Architecture Version remains 1.2.0.

The full model and roadmap is in `docs/proposals/organizational-memory-framework.md`.

---

## D1 — Layer placement: why Organizational Memory is Layer 2, a peer-of-peers, never Layer 3

Organizational Memory answers a question neither Continuous Improvement nor Knowledge Graph asks alone: *what deserves to be remembered?* (ADR-0026 §Stage 10). This is still a question about **many executions**, reasoned over through two already-completed Layer 2 aggregates — never a question about *one* execution (Layer 1) and never yet a question about numerical feature representation, prediction, optimization, or autonomy (Layers 3–6). It therefore remains Layer 2 (ADR-0020 §Stage 4), exactly where ADR-0020 already reserved CAP-085. It is not Layer 3: Feature Engineering transforms Layer 1 and Layer 2 results into numerical vectors (ADR-0020 §Stage 4, Layer 3) — Organizational Memory curates and promotes knowledge, it computes no feature vector, estimates nothing, and chooses nothing.

## D2 — Runtime boundary: why Organizational Memory consumes exactly two Layer 2 results, never a HistoricalDatasetReference

Unlike Continuous Improvement and Knowledge Graph — each of which consumes exactly one `HistoricalDatasetReference` and never a Layer 1 result or the other peer's result directly (ADR-0022 §D2, ADR-0023 §D2) — Organizational Memory consumes **exactly two already-completed Layer 2 results**, and never touches the Historical Dataset itself. This is not an inconsistency; it is ADR-0025 §Stage 7/8's deliberate fan-in exception, exercised here for the first time: Continuous Improvement and Knowledge Graph remain strict peers that never consume one another, but Organizational Memory — a distinct, later, downstream capability — may consume both, because curating "what deserves to be remembered" requires reading what both peers already concluded, not re-deriving either conclusion from raw Historical Truth a third time. `OrganizationalMemoryService.build`'s two-parameter signature is the direct realization of that fan-in.

## D3 — Why `OrganizationalMemoryResult` is Organizational Knowledge, never Derived Knowledge, Historical Truth, or Runtime Truth

The runtime contract is `OrganizationalMemoryResult` — the third Layer 2 runtime contract, and the platform's first concrete instance of **Organizational Knowledge** (ADR-0026 §Stage 1), sitting one level above Derived Knowledge in the extended Truth Hierarchy ADR-0026 §Stage 4 freezes. It is derived exclusively from the two consumed Layer 2 results, never itself becoming Historical Truth, Runtime Truth, or a third copy of either consumed Derived Knowledge object. It must never be written back into either `ContinuousImprovementResult` or `KnowledgeGraphResult`, and it must never recursively consume a prior `OrganizationalMemoryResult` (mirrors ADR-0022 Recommendation 11, ADR-0023 Recommendation 11/17, ADR-0025 Recommendation 2, and ADR-0026 Recommendation 9).

## D4 — Promotion ownership: why Organizational Memory is the sole curator, and promotion records history rather than performing it

`KnowledgePromotion` **records** that a promotion happened — source ids, target ids, rationale, a timestamp reference, a confidence level, and the governing policy version in force — but never performs the promotion itself (ADR-0026 §Stage 6, Recommendation 5 of this ADR). Organizational Memory is the sole owner of the entire promotion mechanism, from `Experience` through `Lesson` to `BestPractice`; no other subsystem may promote, and no future engine may promote silently — every promotion this framework's future engine ever performs must leave a `KnowledgePromotion` record behind (Recommendation 1/2 below).

## D5 — Lifecycle ownership: why retirement is a record, never a transition performed here

`KnowledgeLifecycle` **records** which governed state — `ACTIVE`, `DEPRECATED`, `HISTORICAL`, or `ARCHIVED` — a subject currently occupies (ADR-0026 §Stage 7), but never transitions it. Organizational Memory is the sole owner of lifecycle state for every `Experience`, `Lesson`, and `BestPractice` it curates; no other subsystem may retire, deprecate, or archive an Organizational Memory object, and retirement changes visibility only — nothing is ever deleted (Recommendation 4 below).

## D6 — Policy ownership: capability switches and thresholds, never algorithms

`OrganizationalMemoryPolicy` governs experience capture, lesson promotion, best-practice promotion, and retirement through capability switches, and bounds a future engine's promotion behaviour through deterministic thresholds (`minimum_experiences_for_lesson`, `minimum_lessons_for_best_practice`, `minimum_confidence_for_best_practice`) — data only, no executable logic, mirroring `ImprovementPolicy` (ADR-0022) and `KnowledgeGraphPolicy` (ADR-0023). Tuning promotion behaviour is a versioned policy change, never an engine code change (Recommendation 5, ADR-0022 precedent).

**Clarified permanently (CAP-085A.1).** `OrganizationalMemoryPolicy` **governs** promotion; it never **performs** promotion. A future engine **executes** policy — it reads capability switches and thresholds and acts within the bounds they set — but the policy object itself contains no method that captures an experience, generates a lesson, or institutionalizes a best practice. This is the same policy/engine separation ADR-0022 and ADR-0023 already froze for their own subsystems, restated here explicitly because CAP-085B's future engine will be the first Organizational Memory collaborator pipeline to actually read this policy at runtime (D9 below).

## D7 — PlatformContext: the sole composition root

`PlatformContext` gains exactly two composition-root methods — `create_organizational_memory_policy()` and `create_organizational_memory_service()` — the **only** sanctioned points outside the `organizational_memory` package that may construct its governed objects, enforced by a containment test (mirrors ADR-0022 §D6, ADR-0023 §D6).

## D8 — Future replaceability

A future deterministic, statistical, ML, LLM, GraphRAG, or neuro-symbolic Organizational Memory engine (CAP-085B onward, reserved) must implement the identical `build(ContinuousImprovementResult, KnowledgeGraphResult) -> OrganizationalMemoryResult` contract without `OrganizationalMemoryResult` or `OrganizationalMemoryPolicy` changing shape (ADR-0026 §Stage 13, Recommendation 12 below). `OrganizationalMemoryCapabilitySwitches.enable_deterministic_engine` / `enable_ml_engine` / `enable_llm_engine` / `enable_graph_rag_engine` / `enable_neuro_symbolic_engine` all remain reserved off until their respective future engine exists.

## Internal Engine Architecture (frozen, CAP-085A.1)

CAP-085A.1 strengthens the architecture *before* CAP-085B implements a deterministic engine — freezing the internal decomposition, promotion discipline, and governance a future engine must satisfy, exactly as ADR-0023 §D10 pre-specified Knowledge Graph's own modular decomposition (`NodeProjector`, `EdgeProjector`, `SubgraphDetector`, `ObservationEngine`, `FindingEngine`, `SummaryBuilder`, `MetricsBuilder`, `ResultBuilder`) one milestone ahead of CAP-084B's implementation. This section introduces **no code**: no collaborator class exists yet, and none is created by this milestone. It permanently freezes the *shape* CAP-085B must fill.

### D9 — Deterministic engine decomposition (frozen, CAP-085A.1)

The canonical Organizational Memory engine — whenever CAP-085B implements it — shall consist of independently replaceable collaborators, mirroring the modular discipline ADR-0023 §D10 established for Knowledge Graph rather than the single-engine-class discipline ADR-0022 §D9 used for Continuous Improvement:

```
ExperienceCollector
        ↓
ExperienceClusterer
        ↓
LessonGenerator
        ↓
LessonConsolidator
        ↓
BestPracticeGenerator
        ↓
PromotionRecorder
        ↓
LifecycleRecorder
        ↓
SummaryBuilder
        ↓
MetricsBuilder
        ↓
ResultBuilder
```

Each collaborator owns exactly one responsibility (Recommendation 14 below). No collaborator computes another collaborator's responsibility — `ExperienceCollector` never generates a lesson; `LessonGenerator` never institutionalizes a best practice; `SummaryBuilder` never captures an experience. A future ML, LLM, GraphRAG, or neuro-symbolic engine may replace any single collaborator (e.g. swap `LessonGenerator` for one backed by an LLM) without changing the public `build` contract or any sibling collaborator — the same reuse guarantee ADR-0023 §D10 froze for Knowledge Graph's own decomposition. The runtime contract, `OrganizationalMemoryResult`, remains unchanged regardless of which collaborators a future milestone implements first or replaces later.

### D10 — Knowledge hierarchy: adjacent promotion only (frozen, CAP-085A.1)

```
Experience
        ↓
Lesson
        ↓
Best Practice
```

**Only adjacent promotion is permitted.** Experience may be promoted to Lesson; Lesson may be promoted to Best Practice. **Forbidden permanently:** Experience promoted directly to Best Practice, skipping Lesson. Best Practice never becomes Experience, and no promotion ever moves downward. This is not a new constraint introduced by this milestone — it is already structurally guaranteed by the CAP-085A model shapes: `Lesson.source_experience_ids` is typed `tuple[ExperienceId, ...]` and carries no field capable of holding a `BestPracticeId`; `BestPractice.source_lesson_ids` is typed `tuple[LessonId, ...]` and carries no field capable of holding an `ExperienceId`. CAP-085A.1 freezes this as permanent constitutional intent (Recommendation 13 below) so no future engine, rule, or model revision may widen either field's type to skip a level.

### D11 — Organizational Knowledge Promotion Principle (frozen, CAP-085A.1)

Promotion **creates** new Organizational Knowledge. Promotion **never edits** existing knowledge (restates Stage 6/Recommendation 2 of ADR-0026, D4 above, at full CAP-085A.1 precision). Every promotion must record:

* **source ids** — the lower-rung object(s) promoted from;
* **target ids** — the higher-rung object(s) promoted to;
* **promotion rationale** — why the promotion occurred;
* **policy version** — the governing `OrganizationalMemoryPolicyVersion` in force at the moment of promotion;
* **confidence** — the governed confidence level recorded at that moment;
* **provenance** — the full reference chain back through the promoted-from object(s) to Historical Truth and Runtime Truth (D13 below).

Every promotion must be reproducible: the same source knowledge, read under the same policy version, yields the same target knowledge. `KnowledgePromotion` already carries every one of these fields except an explicit provenance label (`source_ids`, `target_ids`, `rationale`, `policy_version`, `confidence`, `promoted_at`) — provenance itself is not a field of `KnowledgePromotion` because it is not additional data to store; it is the reference chain D13 already freezes, reconstructable by following `source_ids` transitively through the result's own `experiences`/`lessons`/`best_practices` collections.

### D12 — Engine layering: collaborator visibility (frozen, CAP-085A.1)

Each collaborator's inputs and outputs are fixed in advance, so a future engine cannot quietly widen a collaborator's responsibility by handing it data it has no architectural business seeing:

| Collaborator | May produce | May consume |
|---|---|---|
| `ExperienceCollector` | `Experience` only | `ContinuousImprovementResult`, `KnowledgeGraphResult` |
| `ExperienceClusterer` | grouped `Experience` references only | `Experience` only |
| `LessonGenerator` | `Lesson` only | `Experience` only |
| `LessonConsolidator` | consolidated `Lesson` references only | `Lesson` only |
| `BestPracticeGenerator` | `BestPractice` only | `Lesson` only |
| `PromotionRecorder` | `KnowledgePromotion` only | `Lesson` and `BestPractice` only |
| `LifecycleRecorder` | `KnowledgeLifecycle` only | Organizational Knowledge (`Experience`/`Lesson`/`BestPractice`) only |
| `SummaryBuilder` | `OrganizationalMemorySummary` only | already-finished collaborator output; computes no knowledge |
| `MetricsBuilder` | `OrganizationalMemoryMetrics` only | already-finished collaborator output; computes no knowledge |
| `ResultBuilder` | `OrganizationalMemoryResult` only | already-finished collaborator output; assembles only (D16) |

`SummaryBuilder` and `MetricsBuilder` never compute knowledge — they tally already-recorded rows by a field those rows already carry (counts, distributions), exactly the "presentation only" discipline ADR-0022's and ADR-0023's own serializers already apply one layer downstream (`ContinuousImprovementSerializer`, `KnowledgeGraphSerializer`), lifted here one stage earlier into the engine itself because Organizational Memory's summary/metrics are runtime-contract fields, not projection artifacts.

### D13 — Complete explainability chain (frozen, CAP-085A.1)

Every Organizational Memory object must reconstruct this complete chain:

```
Best Practice
        ↓
Lesson
        ↓
Experience
        ↓
Continuous Improvement
        OR
Knowledge Graph
        ↓
Historical Dataset
        ↓
Execution Ids
        ↓
Runtime Truth
```

The first three hops (`BestPractice` → `Lesson` → `Experience`) are enforced today by each model's own "at least one reference" validator (D3/D4 of the original ADR, §6/§7 of the proposal). The fourth hop (`Experience` → its named `source_layer` / `source_reference_id`) is enforced today by `Experience`'s own required fields. The remaining hops (`ContinuousImprovementResult`/`KnowledgeGraphResult` → Historical Dataset → execution ids → Runtime Truth) are already frozen by ADR-0022 §D7/§D10 and ADR-0023 §D7/§D11 for each peer's own explainability chain — Organizational Memory's own chain composes with theirs rather than duplicating them. No Organizational Knowledge object may be promoted unless this complete chain can be reconstructed (Recommendation 17 below).

### D14 — Promotion rules: a reserved, conceptual rule catalogue (frozen, CAP-085A.1)

A future `PromotionRule` concept is reserved, mirroring `ImprovementRule` (ADR-0022) and `KnowledgeGraphRule` (ADR-0023) — metadata only, never an embedded algorithm, containing conceptual fields such as:

* **promotion type** — which adjacent-hierarchy promotion this rule governs (Experience → Lesson, or Lesson → Best Practice);
* **minimum experiences** — the floor a future engine must clear before promoting to Lesson;
* **minimum lessons** — the floor a future engine must clear before promoting to Best Practice;
* **confidence threshold** — the minimum confidence level required;
* **priority** — deterministic ordering among competing candidate promotions;
* **capability switch** — the `OrganizationalMemoryCapabilitySwitches` field this rule is gated by.

**No implementation exists.** This is governance only — a reserved shape a future `organizational_memory/rules/` package (CAP-085B, reserved) will fill, mirroring `continuous_improvement/rules/` and `knowledge_graph/rules/`. Any future deterministic engine must consume only the governed rule catalogue and the governed policy — never a hard-coded literal threshold (Recommendation 16 below).

### D15 — Lifecycle ownership: `LifecycleRecorder` as sole owner (frozen, CAP-085A.1)

`LifecycleRecorder` (D9/D12) is the **only** owner of lifecycle recording. No generator (`ExperienceCollector`, `LessonGenerator`, `BestPracticeGenerator`) may create a `KnowledgeLifecycle` entry as a side effect of its own work. No builder (`SummaryBuilder`, `MetricsBuilder`, `ResultBuilder`) may infer a lifecycle state from counts or shape. No future serializer may compute a lifecycle state — a serializer projects the `KnowledgeLifecycle` records `OrganizationalMemoryResult` already carries, exactly as every other subsystem's serializer projects rather than computes (ADR-0022 §D8, ADR-0023 §D8).

### D16 — Result ownership: `ResultBuilder` as sole constructor (frozen, CAP-085A.1)

`ResultBuilder` (D9/D12) is the **only** constructor of `OrganizationalMemoryResult` anywhere in the future engine. No other collaborator — not `ExperienceCollector`, not `LessonGenerator`, not `BestPracticeGenerator`, not `PromotionRecorder`, not `LifecycleRecorder`, not `SummaryBuilder`, not `MetricsBuilder` — may construct it. Every other collaborator produces intermediate immutable artifacts only (tuples of `Experience`, `Lesson`, `BestPractice`, `KnowledgePromotion`, `KnowledgeLifecycle`, or the `OrganizationalMemorySummary`/`OrganizationalMemoryMetrics` themselves), never the final result. This exactly mirrors Knowledge Graph's own frozen invariant (ADR-0023 §D10: "`ResultBuilder` is the **only** constructor of `KnowledgeGraphResult` anywhere in this engine"), enforced there today by a dedicated containment test (`test_result_builder_is_the_only_result_constructor_in_the_engine`) that CAP-085B's own test suite must replicate once the `engine/` package exists.

## D17 — Deterministic Organizational Memory Engine (CAP-085B)

CAP-085B implements the first real engine behind the CAP-085A/CAP-085A.1 boundary — exactly the modular collaborator pipeline D9/D12 pre-specified, filled in without redesigning any frozen contract. No architectural weakness was found in Stage 0 review of CAP-085A.1: `OrganizationalMemoryResult` remains the permanent runtime contract, `OrganizationalMemoryService` the permanent entry point, `OrganizationalMemoryPolicy` and every canonical model frozen, `PlatformContext` the sole composition root, and Organizational Memory still fully unwired into any execution pipeline. CAP-085B proceeded as a **pure implementation milestone** — no redesign, no frozen-contract change.

**Collaborator architecture.** `DeterministicOrganizationalMemoryEngine` is a thin pipeline orchestrator, exactly as D9 specified: `ExperienceCollector` → `ExperienceClusterer` → `LessonGenerator` → `LessonConsolidator` → `BestPracticeGenerator` → `PromotionRecorder` → `LifecycleRecorder` → `SummaryBuilder`/`MetricsBuilder` → `ResultBuilder`, each in its own module under `organizational_memory/engine/`, each owning exactly the responsibility D12's table already froze. `ResultBuilder` remains the sole constructor of `OrganizationalMemoryResult` (D16); every other collaborator returns an intermediate immutable artifact only.

**Rule catalogue (new package, `organizational_memory/rules/`).** Fulfils D14: `PromotionRule` is metadata only (rule id, `PromotionRuleCategory`, title, description, priority, `capability_switch`, `supported_hierarchy_level`, `documentation_reference`) — no lambda, no callback, no embedded algorithm, and deliberately **no numeric threshold field** (every governed number the engine actually reads remains exclusively owned by `OrganizationalMemoryThresholds`, per D14/Recommendation 16). `PromotionRuleCatalog` owns ordering/lookup/category-and-level projections only. `PromotionRuleBuilder`/`default_promotion_rule_catalog()` ship 24 governed rules spanning the ten categories D14/Stage 1 of the CAP-085B brief named: 6 Experience Capture, 2 each of Experience Consolidation, Lesson Generation, Lesson Consolidation, Best Practice Generation, Promotion, Lifecycle, Explainability, Determinism, and Structural Integrity.

**Deterministic algorithms only.** Experience capture is direct reference construction from each named source object (`ImprovementFinding`, `ImprovementTrend`, `ImprovementOpportunity`, `KnowledgeFinding`, `KnowledgeObservation`, `KnowledgeSubgraph`) — one Experience per object, deduplicated by deterministic id. Clustering is byte-equality grouping on `(source_layer, description)` — never semantic similarity, never an embedding. Lesson generation and Best Practice generation are floor-gated aggregation: a cluster or lesson-group is promoted only once it clears the governed `minimum_experiences_for_lesson` / `minimum_lessons_for_best_practice` threshold, exactly the same conservative-floor discipline ADR-0022 §D9 and ADR-0023 §D10 already established for their own engines. Confidence is a deterministic function of evidence-count-over-threshold (§D11, `engine/_confidence.py`) — never a statistical estimate, never an ML score. No ML, no LLM, no embeddings, no vector search, no semantic similarity, no probabilistic inference, no fuzzy matching, no randomness, no prediction, no statistical learning anywhere in this engine.

**Promotion recorder.** `PromotionRecorder` records one `KnowledgePromotion` per Lesson generated and one per Best Practice generated — source ids, target id, rationale, the injected clock's `completed_at`, the promoted object's own confidence, and the governing `OrganizationalMemoryPolicyVersion`. It performs no inference and constructs no Lesson or Best Practice itself (D11, Recommendation 5).

**Lifecycle recorder.** `LifecycleRecorder` records exactly one `ACTIVE` `KnowledgeLifecycle` entry for every Experience, Lesson, and Best Practice this build produced. It never predicts retirement, never ages knowledge, and never removes or overwrites a prior entry (D15, ADR-0026 §Stage 7).

**Ownership (reaffirms D9/D12/D15/D16, now exercised by real code).** `ExperienceCollector` is the sole Experience authority. `ExperienceClusterer` is the sole clustering authority. `LessonGenerator` is the sole Lesson authority. `LessonConsolidator` is the sole consolidation authority. `BestPracticeGenerator` is the sole Best Practice authority — and generates only from Lessons, never directly from Experiences (no skip-level promotion, Recommendation 13). `PromotionRecorder` is the sole promotion authority. `LifecycleRecorder` is the sole lifecycle authority. `SummaryBuilder` and `MetricsBuilder` each compute their target exactly once, from already-finished collaborators, and compute no knowledge themselves. `ResultBuilder` is the sole `OrganizationalMemoryResult` constructor.

**Explainability (reaffirms D13, now exercised by real code).** Every Experience names the one source object it references. Every Lesson names every contributing Experience. Every Best Practice names every contributing Lesson. Every `KnowledgePromotion` names its source and target ids. Every `KnowledgeLifecycle` names its subject. The complete chain — Best Practice → Lesson → Experience → (Continuous Improvement or Knowledge Graph) → Historical Dataset → Execution Ids → Runtime Truth — is reconstructable from `OrganizationalMemoryResult` alone; the first four hops are enforced today by the frozen models' own validators, and the remaining hops compose with ADR-0022 §D7/§D10's and ADR-0023 §D7/§D11's own already-frozen explainability chains.

**Curation, never analysis (Recommendation 18, new — see below).** The engine generates no new technical finding, diagnosis, structural observation, or analytical conclusion. Every Experience references an object Continuous Improvement or Knowledge Graph already produced; every Lesson and Best Practice is a curation, consolidation, or promotion of that already-produced evidence — never a new judgement about the underlying system.

**PlatformContext.** `create_organizational_memory_service()` now returns `DeterministicOrganizationalMemoryService` (replacing `DormantOrganizationalMemoryService`, which CAP-085B removes — mirroring how CAP-083B's and CAP-084B's own deterministic services replaced their dormant predecessors). Still unwired: nothing calls `build()` at runtime, so the golden baseline, Architecture Version, and Platform Version are all unchanged.

**Future ML/LLM/GraphRAG/neuro-symbolic engines.** `OrganizationalMemoryCapabilitySwitches.enable_ml_engine` / `enable_llm_engine` / `enable_graph_rag_engine` / `enable_neuro_symbolic_engine` remain reserved off. A future such engine implements the identical `OrganizationalMemoryService.build` contract and may replace any single modular collaborator (or all of them) without `OrganizationalMemoryResult` or `OrganizationalMemoryPolicy` changing shape (D8, Recommendation 12).

**Tests.** New deterministic tests cover the rule catalogue (governed vocabulary, metadata-only shape, no threshold field), each collaborator's sole-authority ownership, clustering determinism, floor-gated lesson/best-practice generation, confidence scaling, promotion provenance completeness, lifecycle append-only recording, builder single-computation guarantees, end-to-end engine determinism and explainability, policy gating, and containment (no Layer 1 imports, no Historical Dataset touched directly, no peer implementation class imported, `HistoricalDatasetProvider`/`HistoricalDatasetReference` never crossing in, only `PlatformContext` constructs the service externally).

## D18 — OrganizationalMemoryResult Runtime Contract (CAP-085B.1 permanent certification)

CAP-085B.1 makes **no runtime behaviour change whatsoever**. It permanently certifies `OrganizationalMemoryResult` as the canonical runtime contract of the Organizational Memory Framework, exactly as CAP-080B.1.1 certified `QualityAssessmentResult`, CAP-081B.1 certified `RequirementEnhancementResult`, CAP-082B.1 certified `RecommendationResult`, CAP-083B.1 certified `ContinuousImprovementResult`, and CAP-084B.1 certified `KnowledgeGraphResult` — each *before* its subsystem's own runtime activation. This section is the permanent reference for that certification; nothing here changes a field, a computation, or a signature.

**Frozen definition.** `OrganizationalMemoryResult` is *the complete deterministic runtime record produced from exactly one execution of* `OrganizationalMemoryService.build()`.

**OrganizationalMemoryResult IS.** The complete runtime output of one Organizational Memory build; the canonical Layer 2 curation contract; Organizational Knowledge (ADR-0026 §Stage 1); self-contained; independently versioned; deterministic; explainable; projection-independent.

**OrganizationalMemoryResult IS NOT.** Derived Knowledge; Historical Truth; Runtime Truth; either consumed Layer 2 result's own content; an execution package; a report; a renderer; a serializer; a CLI object; a mutable ledger.

**Ownership (frozen, no overlap).**

| Component | Owns | Owns *not* |
|---|---|---|
| `ExperienceCollector` | experience capture from named Continuous Improvement / Knowledge Graph objects | clustering, generation, promotion, lifecycle, orchestration |
| `ExperienceClusterer` | byte-equality experience clustering | experience capture, generation, promotion, lifecycle |
| `LessonGenerator` / `LessonConsolidator` | floor-gated lesson generation, lesson consolidation | experience capture, best-practice generation, promotion, lifecycle |
| `BestPracticeGenerator` | floor-gated best-practice generation from Lessons only | experience/lesson generation, promotion, lifecycle |
| `PromotionRecorder` | promotion-record construction | generation of the promoted knowledge itself, lifecycle |
| `LifecycleRecorder` | lifecycle-state record construction | generation, promotion |
| `SummaryBuilder` / `MetricsBuilder` | summary, metrics | orchestration, generation, promotion, lifecycle, packaging |
| `DeterministicOrganizationalMemoryEngine` | pipeline orchestration of the collaborators above | any runtime contract, projection, packaging |
| `OrganizationalMemoryService` | orchestration only | any computation the engine performs |
| `OrganizationalMemoryResult` | experiences, lessons, best practices, promotions, lifecycles, summary, metrics, provenance, governing policy identity/version, and the two consumed Layer 2 result id references | runtime engines, either consumed Layer 2 result's own content, execution package, reports, serialization, future graph embeddings, future Graph RAG, future ML/neuro-symbolic reasoning |
| Serializer (future) | projection only | generation, orchestration, packaging |
| Execution Package (future) | packaging only | generation, orchestration, projection logic |
| CLI (future) | orchestration (of the pipeline call) only | generation, projection, packaging |
| `PlatformContext` | composition only | generation, orchestration, projection, packaging |

**Explainability (frozen).** Every experience, lesson, best practice, promotion, and lifecycle record must be reconstructable solely from `OrganizationalMemoryResult`. No upstream subsystem, engine, service, or `PlatformContext` needs ever be inspected or re-run. `OrganizationalMemoryResult` is the complete explanation.

**Runtime boundary (frozen).** Runtime ends at

```
ContinuousImprovementResult + KnowledgeGraphResult
        ↓
OrganizationalMemoryService
        ↓
OrganizationalMemoryResult
```

Everything after that is projection only. Future serializers, reports, dashboards, Markdown, HTML, and the Execution Package must consume `OrganizationalMemoryResult` only — never the engine, never the service, never `PlatformContext`, and must compute nothing.

```
ContinuousImprovementResult + KnowledgeGraphResult
    → DeterministicOrganizationalMemoryEngine
    → OrganizationalMemoryResult
    → Serializer (future)
    → Execution Package (future)
    → Manifest (future)
    → Release
```

No reverse dependency: nothing later in this chain is ever imported by anything earlier in it.

**Layer 2 Fan-In Reference Principle (frozen permanently, mirrors ADR-0025 §Stage 7/8, D2 above).** `OrganizationalMemoryResult` intentionally references the two consumed Layer 2 results by id only (`continuous_improvement_result_id`, `knowledge_graph_result_id`) — never embedding either result's content. The public runtime boundary remains `ContinuousImprovementResult + KnowledgeGraphResult → OrganizationalMemoryResult`; the referenced results themselves remain each their own subsystem's already-frozen runtime contract (ADR-0022 §D3, ADR-0023 §D3), never duplicated here.

**Organizational Knowledge principle (frozen permanently, mirrors D3 above; now the platform-wide constitution of ADR-0026).** `OrganizationalMemoryResult` is Organizational Knowledge — never Derived Knowledge, Historical Truth, or Runtime Truth. It must never be written back into either `ContinuousImprovementResult` or `KnowledgeGraphResult` it was computed from. Every execution of `build` derives its curated knowledge directly from the two resolved Layer 2 results — never from a prior `OrganizationalMemoryResult`. Organizational Knowledge must never recursively consume Organizational Knowledge. ADR-0026 generalizes this principle platform-wide — future Organizational Knowledge capabilities cite ADR-0026 directly rather than restating this paragraph.

**Organizational Knowledge Truth Hierarchy remains permanent (frozen permanently, Recommendation 19 below).** `OrganizationalMemoryResult` never becomes Derived Knowledge, Historical Truth, or Runtime Truth, and it must never be written back into either consumed Layer 2 result.

**Curation remains deterministic (frozen permanently, Recommendation 20 below).** Experience capture, clustering, lesson/best-practice generation, promotion, and lifecycle recording must remain reproducible from the same two consumed Layer 2 results and the same governed policy.

**Organizational Memory remains explainable (frozen permanently, Recommendation 9 above).** Every experience, lesson, best practice, promotion, and lifecycle record must be traceable to the two consumed Layer 2 results within the same `OrganizationalMemoryResult`.

**Runtime precedes projection (frozen permanently, Recommendation 10 above).** Serialization, dashboards, reporting, and the Execution Package are execution-time projections. They must never redefine or mutate this runtime contract.

**Version-axis independence (frozen; full detail in `organizational_memory/identity/organizational_memory_identity.py`'s module docstring).** Eight distinct runtime-contract-facing version types exist — `OrganizationalMemoryFrameworkVersion`, `OrganizationalMemoryPolicyVersion`, `LessonVersion` (reserved), `BestPracticeVersion` (reserved), `KnowledgeLifecycleVersion` (reserved), `PromotionRuleVersion` (CAP-085B), `PromotionRuleCatalogVersion` (CAP-085B), `OrganizationalMemoryResultVersion` (the only axis stamped onto a model today) — each evolving independently. A ninth type, `OrganizationalMemoryEngineVersion` (CAP-085B), versions the deterministic engine's own internal implementation rather than any runtime-contract-facing schema, and is therefore excluded from this contract's axis count — mirroring the engine/contract separation every prior subsystem's own freeze already established. `Experience`, `KnowledgePromotion`, and `OrganizationalMemoryMetrics` carry no dedicated schema-version type of their own; `OrganizationalMemorySummary` carries only the governing policy version — a deliberate architectural consolidation, mirroring the precedent CAP-082B.1 established and CAP-083B.1/CAP-084B.1 reaffirmed for their own atomic finding/issue models; no new version type is invented by this certification.

**Future engine compatibility (frozen permanently).** Future statistical, ML, LLM, GraphRAG, and neuro-symbolic engines must all reuse `OrganizationalMemoryResult` without contract changes.

**Additional constitutional principles (frozen, CAP-085B.1), cross-referenced to the Recommendations already governing this ADR:**

1. `OrganizationalMemoryResult` is the sole runtime authority for Organizational Knowledge produced by Organizational Memory (Recommendation 1; frozen definition, above).
2. `OrganizationalMemoryResult` references, never embeds, the two consumed Layer 2 results (Layer 2 Fan-In Reference Principle, above; Recommendation 6).
3. `OrganizationalMemoryResult` never becomes Derived Knowledge, Historical Truth, or Runtime Truth, and is never recursively consumed by a future Organizational Memory build (Organizational Knowledge principle, above; Recommendation 19 below).
4. Runtime contracts evolve independently of engines, services, rule catalogues, serializers, and execution packaging (Version-axis independence, above; Recommendation 5).
5. Organizational Memory remains a pure Layer 2 fan-in consumer of Continuous Improvement's and Knowledge Graph's Derived Knowledge and must never consume Layer 1 runtime contracts directly, nor recursively consume its own previous Organizational Knowledge (D2, D3, Recommendation 6/7).
6. Future statistical, ML, LLM, GraphRAG, and neuro-symbolic engines must implement the unchanged `build(ContinuousImprovementResult, KnowledgeGraphResult) -> OrganizationalMemoryResult` contract, ensuring long-term engine replaceability (D8, Recommendation 12).

**Certification.** `OrganizationalMemoryResult` is hereby constitutionally certified as the permanent Layer 2 runtime contract for Organizational Memory, completing the same architectural lifecycle (Architecture Freeze → Engine Architecture Refinement → Deterministic Implementation → Runtime Contract Freeze) previously established for Quality Governance (CAP-080B.1.1), Requirement Enhancement (CAP-081B.1), Recommendation (CAP-082B.1), Continuous Improvement (CAP-083B.1), and Knowledge Graph (CAP-084B.1). No field, validator, or signature changed to produce this certification. The repository is certified ready for **CAP-085C — Organizational Memory Runtime Integration**, with no further architectural work required.

## D19 — Organizational Memory Runtime Integration (CAP-085C)

CAP-085C activates the already-complete Organizational Memory Framework in the live Requirement Intelligence runtime — Layer 2's third capability going live, and the first to exercise ADR-0025's fan-in exception in the live pipeline. It does not redesign Organizational Memory, change any frozen contract, alter the policy shape, modify the deterministic engine, or introduce new curation logic — it wires the existing implementation into the live pipeline and activates the Execution Package projections, exactly as CAP-084C did for Knowledge Graph (ADR-0023 §D12).

**Activation and execution order (frozen).** Organizational Memory executes exactly once, immediately after Knowledge Graph, at the permanently frozen end of the pipeline:

```
Engineering Context → Analysis → Requirement Enhancement → Grounding
    → Validation → CP1 → Quality Governance → Recommendation → Historical Dataset
    → Continuous Improvement → Knowledge Graph → Organizational Memory
    → Execution Package
```

Never before Knowledge Graph, never in parallel, never conditionally reordered.

**No `HistoricalDatasetReference` minting (frozen, the fan-in exception exercised in the live pipeline for the first time).** Unlike Continuous Improvement and Knowledge Graph, Organizational Memory consumes exactly the two already-completed Layer 2 peer results this same pipeline run just produced — `ContinuousImprovementResult` and `KnowledgeGraphResult` — never a `HistoricalDatasetReference`, and never any Layer 1 runtime contract directly (D2, Recommendation 6/7). There is nothing to mint: the CLI's `run_organizational_memory_phase` passes the two already-computed peer results straight through. It runs only when **both** peer results are present — a strictly stronger gate than either peer's own single-result gate, and the direct live-pipeline realization of ADR-0025 §Stage 7/8's fan-in exception.

**The golden dataset's known shape (frozen, new nuance).** Continuous Improvement's single-execution reference always yields an empty `ContinuousImprovementResult` (D12 above), so `ExperienceCollector` captures nothing from that side. Knowledge Graph's own golden shape (ADR-0023 §D12) always yields exactly 3 observations and exactly 1 subgraph, plus 0 or 1 digest-gated finding — so `ExperienceCollector` captures 4 or 5 experiences from the Knowledge Graph side alone. `ExperienceClusterer` groups by exact `(source_layer, description)` equality, and these descriptions are all structurally distinct, so no cluster ever reaches the governed `minimum_experiences_for_lesson` floor of 3 — the golden dataset therefore never promotes a lesson, a best practice, or a promotion record, though it does record one `ACTIVE` `KnowledgeLifecycle` entry per captured experience. This is a genuine, reproducible structural property of the golden dataset (proven by `test_golden_baseline.py`'s own bounded-shape test), never an unexplained one.

**CLI (frozen).** The CLI's `run_organizational_memory_phase` obtains `OrganizationalMemoryService` exclusively from `PlatformContext` and calls `build(continuous_improvement_result, knowledge_graph_result)` — identical failure semantics to every prior phase: an Organizational Memory failure is surfaced but never fatal to the analysis run, and it runs only when both consumed peer results are present. The CLI orchestrates only — no experience capture, clustering, lesson generation, promotion, or lifecycle recording logic exists in the CLI.

**Execution Package (frozen, mirrors ADR-0023 §D12).** `ExecutionData.organizational_memory_result` is an additive-only field (no existing field changed). `OrganizationalMemorySerializer` (`organizational_memory/serialization/`) renders `organizational_memory_result.json` (canonical `model_dump`), `organizational_memory_report.md`, and `organizational_memory_metrics.md` — a pure projection computing nothing; every rendered value already exists inside `OrganizationalMemoryResult`. `ExecutionWriter` appends these three artifacts only when `organizational_memory_result` is present — no special case, the same conditional-append mechanism as every peer subsystem, written immediately after the Knowledge Graph artifacts.

**Manifest purity (frozen, mirrors ADR-0017 §D31, ADR-0023 §D12).** The manifest gains exactly three additive keys — `organizationalMemoryExecuted`, `organizationalMemoryReport`, `organizationalMemoryMetrics` — a flag and two artifact filenames. No experience, lesson, best practice, promotion, lifecycle record, summary, or metric value is ever copied into the manifest; that runtime state lives exclusively in `OrganizationalMemoryResult` / `organizational_memory_result.json`. When Organizational Memory did not run, the manifest is byte-identical to before — no key is added, no schema change (`manifestSchemaVersion` stays `1.0.0`).

**Golden integration (frozen).** `_run_golden_pipeline()` now builds immediately after Knowledge Graph; `PipelineResult` carries `organizational_memory_result`. The golden dataset re-baselines from `GOLDEN_DATASET_VERSION` `1.6.0` to `1.7.0` — the nine source artifacts and the golden response are unchanged; only the generated artifact set grows by the three Organizational Memory files, exactly as `1.5.0` and `1.6.0` did for Continuous Improvement and Knowledge Graph respectively. The Architecture Version remains `1.2.0`; the Platform Version is unchanged.

**One-way dependency chain (frozen, mirrors §D18/ADR-0023 §D12).**

```
Organizational Memory Runtime (engine + service)
    → OrganizationalMemoryResult
    → Organizational Memory Serializer
    → Execution Package
    → Manifest
    → Release
```

Nothing later in this chain imports or invokes anything earlier except through the frozen `OrganizationalMemoryResult` contract. The serializer imports no engine, service, policy, or rule catalogue. The writer and manifest builder import only the serializer, never the engine or the service. The CLI imports only `PlatformContext.create_organizational_memory_service()`, never `DeterministicOrganizationalMemoryEngine` or `PromotionRuleCatalog` directly.

**Ownership (frozen, no overlap; reaffirms §D18's table with the CLI and Execution Package now live).** The engine's collaborators capture/cluster/generate/consolidate/promote/record as already frozen. Service orchestrates only. `OrganizationalMemoryResult` owns runtime state only. The serializer projects only. The Execution Package packages only. The CLI orchestrates (the pipeline call) only. `PlatformContext` composes only.

**Execution Package remains projection-only (Recommendation 21, new).** Every Organizational Memory execution artifact is reproducible solely from `OrganizationalMemoryResult`. No artifact generation invokes the engine, the service, or `PlatformContext` — enforced by dedicated containment tests over `OrganizationalMemorySerializer`, `ExecutionWriter`, and `ManifestBuilder` (§D19).

**Layer separation preserved (Recommendation 22, new).** Organizational Memory remains a Layer 2 capability. Runtime integration introduces no direct dependency on any Layer 1 implementation class, and no dependency on Continuous Improvement's or Knowledge Graph's own implementation classes — the CLI, the serializer, and the Execution Package all reach Organizational Memory exclusively through `PlatformContext.create_organizational_memory_service()` and `OrganizationalMemoryResult`.

---

### Recommendation 1 — Organizational Memory is the sole curator of Organizational Knowledge

No other subsystem may capture an experience, promote a lesson, institutionalize a best practice, or record a lifecycle transition on Organizational Memory's behalf. It never owns Continuous Improvement's or Knowledge Graph's own responsibilities, and neither of them may curate on its behalf (ADR-0026 Recommendation 10).

### Recommendation 2 — Lessons are promoted, never rewritten

Promoting an Experience into a Lesson, or a Lesson into a BestPractice, produces a **new** object referencing the one(s) it was promoted from; the lower-rung object is never edited in place (ADR-0026 §Stage 6, Recommendation 2).

### Recommendation 3 — Best Practices emerge only from governed promotion

A `BestPractice` must reference at least one source `Lesson` (enforced today by the model's own "at least one reference" validator); *when* a Lesson is eligible for that promotion is a governed policy decision (`minimum_confidence_for_best_practice`, `minimum_lessons_for_best_practice`) a future engine reads, never a literal hard-coded in the model or the engine (ADR-0026 Recommendation 4).

### Recommendation 4 — Knowledge lifecycle is append-only

Retirement (`ACTIVE` → `DEPRECATED` → `HISTORICAL` → `ARCHIVED`) changes visibility only; nothing is ever deleted, and every lifecycle record remains permanently present and explainable (ADR-0026 §Stage 7, Recommendation 12).

### Recommendation 5 — Promotion preserves complete provenance

Every `KnowledgePromotion` names every source id and every target id it connected, plus the rationale, the confidence, and the policy version in force — an unbroken reference chain, never a summary that discards it (ADR-0026 §Stage 6, Recommendation 3).

### Recommendation 6 — Organizational Memory consumes Derived Knowledge only

`build`'s only parameters are `ContinuousImprovementResult` and `KnowledgeGraphResult` — both Derived Knowledge (ADR-0025 §Stage 1), never a Layer 1 runtime contract embedded directly (ADR-0025 Recommendation 4, ADR-0026 Recommendation 7).

### Recommendation 7 — Organizational Memory never consumes Historical Truth directly

Unlike Continuous Improvement and Knowledge Graph, this framework never resolves a `HistoricalDatasetReference` and never constructs a `HistoricalDatasetProvider` of its own — it reaches Historical Truth only indirectly, through the two Derived Knowledge results it consumes (ADR-0025 §Stage 3, D2 above).

### Recommendation 8 — Learning Framework consumes Organizational Memory rather than Continuous Improvement or Knowledge Graph directly

A future Learning Framework (CAP-086) must consume `OrganizationalMemoryResult`, never `ContinuousImprovementResult` or `KnowledgeGraphResult` directly — the same no-skip discipline ADR-0025 §Stage 7/8 and ADR-0026 §Stage 11 already freeze for the internal sequence of Layer 2 capabilities.

### Recommendation 9 — Organizational Memory remains fully explainable

Every `Experience`, `Lesson`, `BestPractice`, `KnowledgePromotion`, and `KnowledgeLifecycle` record is reconstructable solely from `OrganizationalMemoryResult`, traceable through the two referenced Layer 2 result ids down to Historical Truth and Runtime Truth (ADR-0026 §Stage 9, ADR-0027 §D3).

### Recommendation 10 — Runtime contracts always precede visualization and reporting

`OrganizationalMemoryResult` is frozen before any serializer, execution package integration, dashboard, or reporting capability exists (mirrors ADR-0022 §D8, ADR-0023 §D8; Recommendation 8 of ADR-0022).

### Recommendation 11 — Promotion and retirement are implementation-independent

How a future engine decides *when* to promote or retire is an implementation detail entirely internal to that engine; it must never change `OrganizationalMemoryResult`'s shape, `KnowledgePromotion`'s shape, or `KnowledgeLifecycle`'s shape to express a new promotion or retirement strategy (ADR-0026 Recommendation 13).

### Recommendation 12 — Future AI implementations must preserve OrganizationalMemoryResult unchanged

A future statistical, ML, LLM, GraphRAG, or neuro-symbolic Organizational Memory engine must implement the identical `build` contract and emit the identical `OrganizationalMemoryResult` shape its deterministic successor will establish (ADR-0026 Recommendation 14, D8 above).

### Recommendation 13 — Organizational Knowledge Promotion Principle (mandatory, CAP-085A.1, frozen permanently)

Knowledge promotion may occur only between adjacent levels of the Organizational Knowledge hierarchy (D10). Experience may be promoted to Lesson; Lesson may be promoted to Best Practice. Promotion may never skip hierarchy levels — Experience is never promoted directly to Best Practice.

### Recommendation 14 — Single Responsibility Collaborators (mandatory, CAP-085A.1, frozen permanently)

Every deterministic engine collaborator (D9/D12) owns exactly one transformation. No collaborator performs multiple architectural responsibilities — a future `LessonGenerator` that also records lifecycle state, or a future `SummaryBuilder` that also generates a best practice, violates this Recommendation regardless of how the resulting `OrganizationalMemoryResult` looks.

### Recommendation 15 — Result Assembly Principle (mandatory, CAP-085A.1, frozen permanently)

Only `ResultBuilder` may construct `OrganizationalMemoryResult` (D16). All other collaborators produce intermediate immutable artifacts only.

### Recommendation 16 — Promotion is Policy Governed (mandatory, CAP-085A.1, frozen permanently)

Promotion decisions must always be governed by `OrganizationalMemoryPolicy` and the future `PromotionRule` catalogue (D6, D14) — never a literal threshold hard-coded in a collaborator. Algorithms execute policy; they never define policy.

### Recommendation 17 — Explainability Before Promotion (mandatory, CAP-085A.1, frozen permanently)

No Organizational Knowledge object may be promoted unless it can reconstruct a complete provenance chain back to Runtime Truth (D13). A promotion that cannot name its full chain — through the object(s) it was promoted from, through the named Continuous Improvement or Knowledge Graph source, through the Historical Dataset, down to Runtime Truth — is not explainable and must not be constructible.

### Recommendation 18 — Organizational Memory Curates, It Does Not Analyze (mandatory, CAP-085B, frozen permanently)

Organizational Memory shall never generate new technical findings, diagnoses, structural observations, or analytical conclusions. It may only:

* capture
* consolidate
* curate
* promote
* institutionalize
* lifecycle-manage

Organizational Knowledge derived from completed Layer 2 capabilities. Technical inference remains the responsibility of:

* Continuous Improvement
* Knowledge Graph
* Future Learning capabilities

This recommendation is permanently frozen.

### Recommendation 19 — Organizational Knowledge Truth Hierarchy Boundary is Permanent (mandatory, CAP-085B.1, frozen permanently)

`OrganizationalMemoryResult` never becomes Derived Knowledge, Historical Truth, or Runtime Truth (D3, D18). It must never be written back into either `ContinuousImprovementResult` or `KnowledgeGraphResult` it was computed from, and no Organizational Memory build may recursively consume a prior `OrganizationalMemoryResult` as an input.

### Recommendation 20 — Curation Remains Deterministic (mandatory, CAP-085B.1, frozen permanently)

Experience capture, clustering, lesson/best-practice generation, promotion recording, and lifecycle recording must remain reproducible from the same two consumed Layer 2 results and the same governed policy (D18). A future statistical, ML, LLM, GraphRAG, or neuro-symbolic engine may change *how* curation decides, but never breaks reproducibility of `OrganizationalMemoryResult` for the same inputs and policy version.

### Recommendation 21 — Execution Package remains projection-only (mandatory, CAP-085C, frozen permanently)

Every Organizational Memory execution artifact is reproducible solely from `OrganizationalMemoryResult`. No artifact generation may invoke the engine, the service, or `PlatformContext` — enforced by dedicated containment tests over `OrganizationalMemorySerializer`, `ExecutionWriter`, and `ManifestBuilder` (§D19).

### Recommendation 22 — Runtime integration must not weaken Layer separation (mandatory, CAP-085C, frozen permanently)

Organizational Memory remains a Layer 2 capability. Runtime integration must not introduce direct dependencies on any Layer 1 implementation class, nor on Continuous Improvement's or Knowledge Graph's own implementation classes. The CLI, the serializer, and the Execution Package all reach Organizational Memory exclusively through `PlatformContext.create_organizational_memory_service()` and `OrganizationalMemoryResult` — never `DeterministicOrganizationalMemoryEngine`, `PromotionRuleCatalog`, or any Layer 1, Continuous Improvement, or Knowledge Graph subsystem directly.

---

## Trade-offs

- **A new subsystem introduces the platform's third Layer 2 capability, and its first fan-in consumer of two peers.** Accepted: ADR-0025 §Stage 7/8 exists precisely to authorize this shape in advance; this ADR follows it exactly (Stage 0, D2).
- **`OrganizationalMemoryResult` references two Layer 2 result ids as plain strings rather than embedding either result.** Accepted: this is the same "reference, never copy" discipline every prior subsystem's consumed-input models already apply (ADR-0018 `EnhancementInputReference`, ADR-0019 `RecommendationInputReference`), applied here to two Layer 2 peers instead of Layer 1 results.
- **Governed defaults (`minimum_experiences_for_lesson`, `minimum_lessons_for_best_practice`, `minimum_confidence_for_best_practice`) are calibrated conservatively, not empirically.** The CAP-085A default policy bounds reflect a deliberately conservative first pass, not yet tuned against real curated knowledge. Accepted: tuning is a versioned policy change under a future golden re-baseline, never an engine code change (Recommendation 5 of this ADR).

## Future evolution

- **CAP-085B — Deterministic Organizational Memory Engine (done).** The first real engine behind the frozen `build` signature: deterministic experience capture, lesson promotion, and best-practice promotion strictly from the two resolved Layer 2 results (Recommendation 6), never independent analysis or re-implementation of either peer's own reasoning — implemented as the modular collaborator pipeline CAP-085A.1's D9/D12 pre-specified (`ExperienceCollector` through `ResultBuilder`), governed by the `PromotionRuleCatalog` D14 named, never a single monolithic engine class. See §D17.
- **CAP-085B.1 — OrganizationalMemoryResult Runtime Contract Freeze (done).** Permanently certifies `OrganizationalMemoryResult` as the canonical Layer 2 runtime contract (§D18) — no field, validator, or signature change; documentation and architecture tests only, mirroring CAP-084B.1.
- **CAP-085C — Runtime Integration (done).** Wires `build` into the live pipeline immediately after Knowledge Graph, adds the `OrganizationalMemorySerializer` Execution Package projection, and re-baselines the golden dataset `1.6.0` → `1.7.0`, mirroring CAP-084C's activation of Knowledge Graph (ADR-0023 §D12). See §D19.
- **CAP-086 (Learning Framework)** — the remaining reserved Layer 2 capability (ADR-0020), to consume `OrganizationalMemoryResult` per Recommendation 8 above.
- **Future AI graph reasoning, embeddings, and Graph RAG over curated knowledge** (reserved) — higher-layer or engine-variant capabilities that consume `OrganizationalMemoryResult` without ever becoming part of this contract.
- Promotion of the shared version/identity value-objects to `shared/` (the debt ADR-0015 §C, ADR-0016, ADR-0017, ADR-0018 §D5, ADR-0019 §D5, ADR-0022, and ADR-0023 already name).

## Ownership, runtime position, governance

- **Owns:** curated Organizational Knowledge — experiences, lessons, best practices, promotion history, lifecycle state, Organizational Memory metadata. Owns the deterministic engine and its modular collaborators (D9–D17), the governed `PromotionRuleCatalog`, the engine-internal confidence computation, and the projection-only `OrganizationalMemorySerializer` (D19).
- **Does not own:** Engineering Context Orchestration, Analysis, Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, Continuous Improvement, Knowledge Graph, the Execution Package, or the Historical Dataset itself (ADR-0021 §Stage 6 names that owner, not this ADR). Does not own any Learning Framework responsibility (ADR-0026 §Stage 11, reserved for CAP-086). Never generates a new technical finding or analytical conclusion (Recommendation 18) — that remains Continuous Improvement's and Knowledge Graph's own responsibility.
- **Runtime position (live — CAP-085C):** `ContinuousImprovementResult` + `KnowledgeGraphResult` → `ExperienceCollector` → `ExperienceClusterer` → `LessonGenerator` → `LessonConsolidator` → `BestPracticeGenerator` → `PromotionRecorder` → `LifecycleRecorder` → `SummaryBuilder`/`MetricsBuilder` → `ResultBuilder` → `OrganizationalMemoryResult` → `OrganizationalMemorySerializer` → Execution Package. Architecture frozen; the deterministic engine exists and is fully tested; `OrganizationalMemoryResult` is constitutionally certified as the permanent runtime contract (§D18); `run_organizational_memory_phase` now wires `build` into the live pipeline, immediately after Knowledge Graph (§D19).
- **Governance:** registered as CAP-085 for the Requirement Intelligence Platform's Layer 2 — the third capability built under ADR-0020/ADR-0021/ADR-0025/ADR-0026, following Continuous Improvement (ADR-0022) and Knowledge Graph (ADR-0023). This ADR is **Proposed**; CAP-085A.1 strengthened it with the frozen internal engine architecture and promotion/lifecycle/result ownership rules under an unchanged public contract; CAP-085B extends it with the first deterministic engine implementing that frozen shape; CAP-085B.1 permanently certifies that contract; CAP-085C activates it in the live pipeline, exactly mirroring ADR-0022's and ADR-0023's own runtime-integration milestones. The repository is certified ready for **CAP-086A — Learning Framework Architecture & Governance Freeze**.
