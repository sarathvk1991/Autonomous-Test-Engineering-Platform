# ADR-0027 — Organizational Memory Framework

- **Status:** Proposed (CAP-085A — Architecture & Governance Freeze)
- **Date:** 2026-07-16 (CAP-085A — Architecture & Governance Freeze)
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** a future runtime-integration milestone (CAP-085B, reserved) will implement a deterministic engine behind the frozen contracts, mirroring how CAP-083B implemented the first deterministic Continuous Improvement engine behind ADR-0022 and CAP-084B implemented the first deterministic Knowledge Graph engine behind ADR-0023.
- **Governing design:** `docs/proposals/organizational-memory-framework.md`
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — this is the third Layer 2 capability it names), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — the Truth Hierarchy this framework's every boundary applies), ADR-0025 (Derived Knowledge Architecture & Layer 2 Constitution — the fan-in exception this framework is the first concrete implementation of, ADR-0025 §Stage 7/8), and ADR-0026 (Organizational Knowledge Architecture & Learning Constitution — the full constitutional definition of what this framework produces). Also informed by ADR-0022 (Continuous Improvement Framework) and ADR-0023 (Knowledge Graph Framework) — the two completed Layer 2 peer capabilities this framework consumes, and the direct architectural precedent this ADR mirrors.
- **Runtime status:** **Architecture only (CAP-085A).** `OrganizationalMemoryService.build` is an **abstract, dormant contract**; `DormantOrganizationalMemoryService` raises `NotImplementedError` on every call. No experience is captured, no lesson is promoted, no best practice is institutionalized, no lifecycle is recorded, and nothing is wired into a runtime path. Runtime behaviour is byte-identical; the golden baseline is unchanged; the Architecture Version remains **1.2.0**.

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

## D7 — PlatformContext: the sole composition root

`PlatformContext` gains exactly two composition-root methods — `create_organizational_memory_policy()` and `create_organizational_memory_service()` — the **only** sanctioned points outside the `organizational_memory` package that may construct its governed objects, enforced by a containment test (mirrors ADR-0022 §D6, ADR-0023 §D6).

## D8 — Future replaceability

A future deterministic, statistical, ML, LLM, GraphRAG, or neuro-symbolic Organizational Memory engine (CAP-085B onward, reserved) must implement the identical `build(ContinuousImprovementResult, KnowledgeGraphResult) -> OrganizationalMemoryResult` contract without `OrganizationalMemoryResult` or `OrganizationalMemoryPolicy` changing shape (ADR-0026 §Stage 13, Recommendation 12 below). `OrganizationalMemoryCapabilitySwitches.enable_deterministic_engine` / `enable_ml_engine` / `enable_llm_engine` / `enable_graph_rag_engine` / `enable_neuro_symbolic_engine` all remain reserved off until their respective future engine exists.

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

---

## Trade-offs

- **A new subsystem introduces the platform's third Layer 2 capability, and its first fan-in consumer of two peers.** Accepted: ADR-0025 §Stage 7/8 exists precisely to authorize this shape in advance; this ADR follows it exactly (Stage 0, D2).
- **`OrganizationalMemoryResult` references two Layer 2 result ids as plain strings rather than embedding either result.** Accepted: this is the same "reference, never copy" discipline every prior subsystem's consumed-input models already apply (ADR-0018 `EnhancementInputReference`, ADR-0019 `RecommendationInputReference`), applied here to two Layer 2 peers instead of Layer 1 results.
- **Governed defaults (`minimum_experiences_for_lesson`, `minimum_lessons_for_best_practice`, `minimum_confidence_for_best_practice`) are calibrated conservatively, not empirically.** The CAP-085A default policy bounds reflect a deliberately conservative first pass, not yet tuned against real curated knowledge. Accepted: tuning is a versioned policy change under a future golden re-baseline, never an engine code change (Recommendation 5 of this ADR).

## Future evolution

- **CAP-085B — Deterministic Organizational Memory Engine (reserved).** The first real engine behind the frozen `build` signature: deterministic experience capture, lesson promotion, and best-practice promotion strictly from the two resolved Layer 2 results (Recommendation 6), never independent analysis or re-implementation of either peer's own reasoning.
- **Runtime activation (CAP-085C, reserved)** — wiring `build` into a live pipeline, plus a future Execution Package projection and golden re-baseline, mirroring CAP-083C's activation of Continuous Improvement and CAP-084C's activation of Knowledge Graph.
- **CAP-086 (Learning Framework)** — the remaining reserved Layer 2 capability (ADR-0020), to consume `OrganizationalMemoryResult` per Recommendation 8 above.
- **Future AI graph reasoning, embeddings, and Graph RAG over curated knowledge** (reserved) — higher-layer or engine-variant capabilities that consume `OrganizationalMemoryResult` without ever becoming part of this contract.
- Promotion of the shared version/identity value-objects to `shared/` (the debt ADR-0015 §C, ADR-0016, ADR-0017, ADR-0018 §D5, ADR-0019 §D5, ADR-0022, and ADR-0023 already name).

## Ownership, runtime position, governance

- **Owns:** curated Organizational Knowledge — experiences, lessons, best practices, promotion history, lifecycle state, Organizational Memory metadata.
- **Does not own:** Engineering Context Orchestration, Analysis, Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, Continuous Improvement, Knowledge Graph, the Execution Package, or the Historical Dataset itself (ADR-0021 §Stage 6 names that owner, not this ADR). Does not own any Learning Framework responsibility (ADR-0026 §Stage 11, reserved for CAP-086).
- **Runtime position (architecture only — CAP-085A):** `ContinuousImprovementResult` + `KnowledgeGraphResult` → (future engine, reserved) → `OrganizationalMemoryResult`. Architecture frozen; no engine exists; nothing is wired into any execution pipeline.
- **Governance:** registered as CAP-085 for the Requirement Intelligence Platform's Layer 2 — the third capability built under ADR-0020/ADR-0021/ADR-0025/ADR-0026, following Continuous Improvement (ADR-0022) and Knowledge Graph (ADR-0023). This ADR is **Proposed**; a future CAP-085B extends it with the first deterministic engine under an unchanged contract, exactly mirroring ADR-0022's and ADR-0023's own status ahead of their own B-milestones.
