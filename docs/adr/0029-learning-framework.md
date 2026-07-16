# ADR-0029 — Learning Framework

- **Status:** Proposed (CAP-086A — Architecture & Governance Freeze)
- **Date:** 2026-07-16 (CAP-086A — Architecture & Governance Freeze)
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** a future runtime-integration milestone (CAP-086B, reserved) will implement a deterministic engine behind the frozen contracts, mirroring how CAP-083B implemented the first deterministic Continuous Improvement engine behind ADR-0022, CAP-084B implemented the first deterministic Knowledge Graph engine behind ADR-0023, and CAP-085B implemented the first deterministic Organizational Memory engine behind ADR-0027.
- **Governing design:** `docs/proposals/learning-framework.md`
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — this is the fourth and final Layer 2 capability it names), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — the Truth Hierarchy this framework's every boundary applies), ADR-0025 (Derived Knowledge Architecture & Layer 2 Constitution — the peer-independence and fan-in rules this framework's own single-input boundary is defined against), ADR-0026 (Organizational Knowledge Architecture & Learning Constitution — Learning's earliest principles, §Stage 11), and ADR-0028 (Learning Constitution — the full constitutional definition of what this framework produces: Learning, Learned Knowledge, the four-level Knowledge Promotion Chain, Learning Validation, Lineage, Maturity, Confidence, and Evolution). Also informed by ADR-0022 (Continuous Improvement Framework), ADR-0023 (Knowledge Graph Framework), and ADR-0027 (Organizational Memory Framework) — the three completed Layer 2 peer capabilities that precede this one, and the direct architectural precedent this ADR mirrors.
- **Runtime status:** **Architecture only (CAP-086A).** `LearningService.build` is an **abstract, dormant contract**; `DormantLearningService` raises `NotImplementedError` on every call. No candidate is proposed, no learning is validated, no confidence is recorded, no lifecycle is recorded, and nothing is wired into a runtime path. Runtime behaviour is byte-identical; the golden baseline is unchanged; the Architecture Version remains **1.2.0**.

## Problem

ADR-0020 named Continuous Learning as Layer 2 and reserved four capabilities inside it: CAP-083 (Continuous Improvement), CAP-084 (Knowledge Graph), CAP-085 (Organizational Memory), CAP-086 (Learning Framework). ADR-0022 built the first — Continuous Improvement observes recurrence across a Historical Dataset. ADR-0023 built the second — Knowledge Graph projects structure across the same Historical Dataset. ADR-0027 built the third — Organizational Memory curates both peers' conclusions into trusted Organizational Knowledge. None of the three answers a fourth, final question ADR-0026 §Stage 10 and ADR-0028 §Stage 1 already name: *given everything the organization now trusts, what should change?* No existing capability validates a proposed change into reusable, institutional understanding that permanently improves future reasoning.

Left unbuilt, and built without a frozen architecture first, the first capability to validate organizational learning would have to invent, under deadline pressure, exactly the kind of ad hoc answer ADR-0021 §Stage 2 warned against: duplicated validation logic, inconsistent maturity criteria, competing "what we learned" records, and no single place to audit why a piece of Learning is trusted.

### Stage 0 — Repository assessment

Before writing this ADR, every prior architectural ADR governing Layer 2 was reviewed:

- **ADR-0020, ADR-0021, ADR-0024, ADR-0025, ADR-0026, ADR-0028** — the platform's constitutional documents. Reviewed in full; none conflicts with this ADR, and Stage 0 of this milestone found no inconsistency requiring correction to any of them.
- **ADR-0022 (Continuous Improvement)**, **ADR-0023 (Knowledge Graph)**, and **ADR-0027 (Organizational Memory)** — all three confirmed **completed, live Layer 2 capabilities**. Organizational Memory is the highest completed Layer 2 capability (CAP-085A → CAP-085A.1 → CAP-085B → CAP-085B.1 → CAP-085C, all live). None of the three owns Learned Knowledge, a Learning object, or Learning Framework itself — confirmed by direct review of all three ADRs' Ownership sections and by repository-wide search.
- **Search performed** for `LearningResult`, `LearningService`, `LearningPolicy`, `learning_framework`, `LearningEngine` across `requirement_intelligence/`, `docs/adr/`, and `docs/proposals/`: the only hit prior to this milestone is ADR-0025 §Stage 4's own single-sentence forward-reference to a future `LearningResult`, inside an illustrative list, not a definition. **Learning Framework does not exist anywhere in the repository prior to this milestone.**

**No duplicated ownership, overlapping concept, hidden coupling, or architectural conflict was found.** Continuous Improvement, Knowledge Graph, and Organizational Memory remain exactly where ADR-0022, ADR-0023, and ADR-0027 already placed them, unchanged by this milestone.

> No architectural weakness found. Proceeding with a pure architecture and governance freeze.

## Decision

Introduce a new governed subsystem, **`requirement_intelligence/learning/`**, that will own the validation, promotion, maturity, and governance of Learned Knowledge — built from **one completed Organizational Memory result**, never from a Layer 1 runtime contract, never from the Historical Dataset directly, never from either of Organizational Memory's own consumed Layer 2 peers directly, and never by re-implementing Organizational Memory's own curation. It:

1. Introduces canonical, immutable models — `LearningCandidate`, `LearningValidation`, `LearningConfidence`, `Learning`, `LearningLifecycle`, `LearningSummary`, `LearningMetrics`, and `LearningResult` — following the `Schema` conventions and the typed-identity pattern of ADR-0015–ADR-0019, ADR-0022, ADR-0023, and ADR-0027.
2. Introduces strongly typed identities — `LearningPolicyId`, `LearningCandidateId`, `LearningValidationId`, `LearningConfidenceId`, `LearningId`, `LearningLifecycleId`, `LearningResultId` — deterministic value objects, no UUIDs, no timestamps, no randomness.
3. Introduces independent version axes — `LearningFrameworkVersion`, `LearningPolicyVersion`, `LearningVersion` (reserved), `LearningLifecycleVersion` (reserved), `LearningValidationVersion` (reserved), `LearningResultVersion` — each evolving without forcing the others to change (Recommendation 13 of ADR-0028, ADR-0022/ADR-0023/ADR-0027 precedent).
4. Introduces a governed `LearningPolicy` (immutable data: capability switches, deterministic thresholds) with a `LearningPolicyBuilder` and `default_learning_policy()`.
5. Fixes the single runtime boundary — `LearningService.build(organizational_memory_result: OrganizationalMemoryResult) -> LearningResult` — as an **abstract, dormant contract**. `PlatformContext` gains `create_learning_policy()` and `create_learning_service()`.

The Learning Framework consumes **Organizational Knowledge only** — never Derived Knowledge directly, never Historical Truth, never Runtime Truth, never an Execution Package artifact, never a report or a manifest (ADR-0028 §Stage 12, ADR-0021 §Stage 7/8). It is the **fourth and final Layer 2 peer**, and — unlike Organizational Memory's own deliberate two-peer fan-in (ADR-0025 §Stage 7/8) — consumes exactly **one** already-completed Layer 2 tier: the single tier immediately beneath it (ADR-0028 §Stage 12/16).

**CAP-086A establishes the architecture only.** No candidate is proposed, no learning is validated, no confidence is recorded, no lifecycle is recorded, no historical dataset is touched, and nothing is wired into a runtime path. Runtime behaviour is byte-identical; the golden baseline is unchanged; the Architecture Version remains 1.2.0.

The full model and roadmap is in `docs/proposals/learning-framework.md`.

---

## D1 — Layer placement: why Learning is Layer 2, the terminal capability, never Layer 3

Learning answers a question none of its three Layer 2 predecessors asks: *what should change?* (ADR-0026 §Stage 10, ADR-0028 §Stage 1). This is still a question about **many executions**, reasoned over through one already-completed Layer 2 aggregate — never a question about *one* execution (Layer 1) and never yet a question about numerical feature representation, prediction, optimization, or autonomy (Layers 3–6). It therefore remains Layer 2 (ADR-0020 §Stage 4), exactly where ADR-0020 already reserved CAP-086. It is not Layer 3: Feature Engineering transforms Layer 1 and Layer 2 results into numerical vectors (ADR-0020 §Stage 4, Layer 3) — Learning validates and matures knowledge, it computes no feature vector, estimates nothing, and chooses nothing (ADR-0028 §Stage 12).

## D2 — Runtime boundary: why Learning consumes exactly one Organizational Memory result, never a fan-in pair

Unlike Organizational Memory — which consumes **two** already-completed Layer 2 peer results, ADR-0025 §Stage 7/8's deliberate fan-in exception — Learning consumes **exactly one** already-completed Layer 2 tier: `OrganizationalMemoryResult`. This is not a narrowing of the fan-in principle; it is ADR-0028 §Stage 12/16's own frozen shape: Learning is the sole sanctioned bridge from Layer 2 to Layer 3, and that bridge reaches no further back than the one tier immediately beneath it (the no-skip discipline ADR-0020 §Stage 5 already freezes between numbered layers, and ADR-0025 §Stage 7/8 already freezes within Layer 2's own capability sequence). `LearningService.build`'s single-parameter signature is the direct realization of that boundary — Learning never touches `ContinuousImprovementResult` or `KnowledgeGraphResult` directly, and never resolves a `HistoricalDatasetReference` of its own (Recommendation 7/8 of ADR-0027, Recommendation 6/7 of this ADR).

## D3 — Why `LearningResult` is Learned Knowledge, never Organizational Knowledge, Derived Knowledge, Historical Truth, or Runtime Truth

The runtime contract is `LearningResult` — the fourth and final Layer 2 runtime contract, and the platform's first concrete instance of **Learned Knowledge** (ADR-0028 §Stage 2), sitting one level above Organizational Knowledge in the four-level Knowledge Promotion Chain ADR-0028 §Stage 2/5 freezes. It is derived exclusively from the one consumed `OrganizationalMemoryResult`, never itself becoming Organizational Knowledge, Historical Truth, Runtime Truth, or a copy of the consumed result. It must never be written back into `OrganizationalMemoryResult`, and it must never recursively consume a prior `LearningResult` (mirrors ADR-0022 Recommendation 11, ADR-0023 Recommendation 11/17, ADR-0025 Recommendation 2, ADR-0027 §D3/Recommendation 19, and Recommendation 20 of ADR-0028).

## D4 — Validation ownership: why Learning is the sole validator, and validation records history rather than performing it

`LearningValidation` **records** that a validation event happened — which of the six governed Stage 6 gates it covered, a rationale, a timestamp reference, a confidence level, and the governing policy version in force — but never performs the validation itself (ADR-0028 §Stage 6, Recommendation 1/2 below). Learning is the sole owner of the entire validation mechanism, from `LearningCandidate` through `Learning`; no other subsystem may validate, and no future engine may validate silently — every validation this framework's future engine ever performs must leave a `LearningValidation` record behind.

## D5 — Maturity ownership: why maturity is a record, never a transition performed here

`LearningLifecycle` **records** which governed maturity level — `CANDIDATE` through `RETIRED` — a subject currently occupies (ADR-0028 §Stage 8), but never transitions it. Learning is the sole owner of maturity state for every `LearningCandidate` and `Learning` it produces; no other subsystem may advance, institutionalize, or retire a Learning object, and maturity evolves upward only — nothing is ever deleted (Recommendation 4 below, mirrors Recommendation 4 of ADR-0027 lifted to the maturity axis).

## D6 — Policy ownership: capability switches and thresholds, never algorithms

`LearningPolicy` governs candidate proposal, validation, confidence recording, and lifecycle recording through capability switches, and bounds a future engine's validation behaviour through deterministic thresholds (`minimum_best_practices_for_candidate`, `minimum_validation_gates_for_learning`, `minimum_confidence_for_learning`) — data only, no executable logic, mirroring `OrganizationalMemoryPolicy` (ADR-0027). Tuning validation behaviour is a versioned policy change, never an engine code change (Recommendation 5, ADR-0022/ADR-0027 precedent).

## D7 — PlatformContext: the sole composition root

`PlatformContext` gains exactly two composition-root methods — `create_learning_policy()` and `create_learning_service()` — the **only** sanctioned points outside the `learning` package that may construct its governed objects, enforced by a containment test (mirrors ADR-0022 §D6, ADR-0023 §D6, ADR-0027 §D7).

## D8 — Future replaceability

A future deterministic, ML, LLM, GraphRAG, reinforcement learning, or neuro-symbolic Learning engine (CAP-086B onward, reserved) must implement the identical `build(OrganizationalMemoryResult) -> LearningResult` contract without `LearningResult` or `LearningPolicy` changing shape (ADR-0028 §Stage 17, Recommendation 14 below). `LearningCapabilitySwitches.enable_deterministic_engine` / `enable_ml_engine` / `enable_llm_engine` / `enable_reinforcement_learning_engine` / `enable_neuro_symbolic_engine` all remain reserved off until their respective future engine exists.

---

### Recommendation 1 — Learning is the sole validator of Learned Knowledge

No other subsystem may propose a candidate, validate a learning, record a confidence, or record a lifecycle transition on Learning's behalf. It never owns Organizational Memory's, Continuous Improvement's, or Knowledge Graph's own responsibilities, and none of them may validate on its behalf (ADR-0028 Recommendation 4).

### Recommendation 2 — Learning is promoted, never rewritten

Promoting a `LearningCandidate` into `Learning` produces a **new** object referencing the one it was promoted from; the lower-rung object is never edited in place (ADR-0028 §Stage 5/11, Recommendation 17 of ADR-0028).

### Recommendation 3 — Learning emerges only from governed validation

A `Learning` must reference exactly one source `LearningCandidate` and exactly one certifying `LearningValidation` (enforced today by the model's own reference validators); *when* a candidate is eligible for that promotion is a governed policy decision (`minimum_confidence_for_learning`, `minimum_validation_gates_for_learning`) a future engine reads, never a literal hard-coded in the model or the engine (ADR-0028 Recommendation 15).

### Recommendation 4 — Learning maturity is append-only

Advancement (`CANDIDATE` → `OBSERVED` → `VALIDATED` → `TRUSTED` → `INSTITUTIONAL` → `STANDARD` → `RETIRED`) moves upward only; nothing is ever deleted, and every lifecycle record remains permanently present and explainable (ADR-0028 §Stage 8, Recommendation 6 of ADR-0028).

### Recommendation 5 — Validation preserves complete provenance

Every `LearningValidation` names every gate it cleared, plus the rationale, the confidence, and the policy version in force — an unbroken reference chain, never a summary that discards it (ADR-0028 §Stage 6, Recommendation 16 of ADR-0028).

### Recommendation 6 — Learning consumes Organizational Knowledge only

`build`'s only parameter is `OrganizationalMemoryResult` — Organizational Knowledge (ADR-0026 §Stage 1), never `ContinuousImprovementResult` or `KnowledgeGraphResult` embedded directly (ADR-0028 §Stage 12, Recommendation 7 of ADR-0026, Recommendation 8 of ADR-0027).

### Recommendation 7 — Learning never consumes Derived Knowledge, Historical Truth, or Runtime Truth directly

Unlike Continuous Improvement and Knowledge Graph, this framework never resolves a `HistoricalDatasetReference` and never constructs a `HistoricalDatasetProvider` of its own; unlike Organizational Memory, it never consumes two Layer 2 peers — it reaches every earlier tier only indirectly, through the one Organizational Knowledge result it consumes (ADR-0028 §Stage 12, D2 above).

### Recommendation 8 — Feature Engineering consumes Learning rather than any earlier Layer 2 tier directly

A future Layer 3 Feature Engineering capability must consume `LearningResult` wherever a fully-matured Layer 2 conclusion is required, never skip past Learning to `OrganizationalMemoryResult`, `ContinuousImprovementResult`, or `KnowledgeGraphResult` directly — the same no-skip discipline ADR-0025 §Stage 7/8 and ADR-0028 §Stage 12/16 already freeze for the internal sequence of Layer 2 capabilities (Recommendation 19 of ADR-0028).

### Recommendation 9 — Learning remains fully explainable

Every `LearningCandidate`, `LearningValidation`, `LearningConfidence`, `Learning`, and `LearningLifecycle` record is reconstructable solely from `LearningResult`, traceable through the referenced `OrganizationalMemoryResult` id down to Best Practice, Lesson, Experience, Historical Dataset, Execution Ids, and Runtime Truth (ADR-0028 §Stage 10, Recommendation 8 of ADR-0028).

### Recommendation 10 — Runtime contracts always precede visualization and reporting

`LearningResult` is frozen before any serializer, execution package integration, dashboard, or reporting capability exists (mirrors ADR-0022 §D8, ADR-0023 §D8, ADR-0027 §D19; Recommendation 8 of ADR-0022).

### Recommendation 11 — Validation and maturity advancement are implementation-independent

How a future engine decides *when* to validate or advance maturity is an implementation detail entirely internal to that engine; it must never change `LearningResult`'s shape, `LearningValidation`'s shape, or `LearningLifecycle`'s shape to express a new validation or maturity strategy (mirrors Recommendation 11 of ADR-0027, Recommendation 13 of ADR-0028).

### Recommendation 12 — Future AI implementations must preserve LearningResult unchanged

A future statistical, ML, LLM, GraphRAG, reinforcement learning, or neuro-symbolic Learning engine must implement the identical `build` contract and emit the identical `LearningResult` shape its deterministic successor will establish (ADR-0028 §Stage 17/Recommendation 14, D8 above).

### Recommendation 13 — Learning never mutates Organizational Knowledge

No Learning build writes back into `OrganizationalMemoryResult`, and no Learning object is ever mistaken for a `BestPractice`, `Lesson`, or `Experience` (ADR-0026 §Stage 11, Recommendation 2 of ADR-0028).

### Recommendation 14 — Learning completes Layer 2

Continuous Improvement, Knowledge Graph, Organizational Memory, and Learning together exhaust Layer 2's responsibilities (ADR-0028 §Stage 16, Recommendation 18 of ADR-0028); no fifth Layer 2 capability is required or anticipated by this ADR.

---

## Trade-offs

- **Learning consumes exactly one Layer 2 tier, unlike Organizational Memory's own two-peer fan-in.** Accepted: ADR-0028 §Stage 12/16 exists precisely to authorize this narrower shape; this ADR follows it exactly (Stage 0, D2).
- **`LearningResult` references the consumed `OrganizationalMemoryResult` id as a plain string rather than embedding the result.** Accepted: this is the same "reference, never copy" discipline every prior subsystem's consumed-input models already apply (ADR-0018 `EnhancementInputReference`, ADR-0019 `RecommendationInputReference`, ADR-0027's own two-id reference), applied here to one Layer 2 tier instead of two.
- **Governed defaults (`minimum_best_practices_for_candidate`, `minimum_validation_gates_for_learning`, `minimum_confidence_for_learning`) are calibrated conservatively, not empirically.** The CAP-086A default policy bounds reflect a deliberately conservative first pass — all six governed gates required, a minimum of two corroborating best practices, and the highest confidence ordinal — not yet tuned against real validated learning. Accepted: tuning is a versioned policy change under a future golden re-baseline, never an engine code change (Recommendation 5 of this ADR).

## Future evolution

- **CAP-086B — Deterministic Learning Engine (reserved).** The first real engine behind the frozen `build` signature: deterministic candidate proposal, validation, and confidence/lifecycle recording strictly from the one resolved `OrganizationalMemoryResult` (Recommendation 6), never independent analysis or re-implementation of Organizational Memory's own curation.
- **Runtime activation (CAP-086C, reserved)** — wiring `build` into a live pipeline, plus a future Execution Package projection and golden re-baseline, mirroring CAP-085C's activation of Organizational Memory.
- **Feature Engineering (Layer 3, reserved)** — the first capability outside Layer 2, to consume `LearningResult` per Recommendation 8 above, completing the Layer 2 → Layer 3 bridge ADR-0028 §Stage 16 names.
- **Future AI validation, promotion reasoning, and institutional-adoption modeling over Learned Knowledge** (reserved) — higher-layer or engine-variant capabilities that consume `LearningResult` without ever becoming part of this contract.
- Promotion of the shared version/identity value-objects to `shared/` (the debt ADR-0015 §C, ADR-0016, ADR-0017, ADR-0018 §D5, ADR-0019 §D5, ADR-0022, ADR-0023, and ADR-0027 already name).

## Ownership, runtime position, governance

- **Owns:** validated Learned Knowledge — learning candidates, learnings, validation history, confidence records, maturity/lifecycle state, Learning Framework metadata.
- **Does not own:** Engineering Context Orchestration, Analysis, Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, Continuous Improvement, Knowledge Graph, Organizational Memory, the Execution Package, or the Historical Dataset itself (ADR-0021 §Stage 6 names that owner, not this ADR). Does not own any Feature Engineering responsibility (ADR-0020 §Stage 4, reserved for Layer 3).
- **Runtime position (architecture only — CAP-086A):** `OrganizationalMemoryResult` → (future engine, reserved) → `LearningResult`. Architecture frozen; no engine exists; nothing is wired into any execution pipeline.
- **Governance:** registered as CAP-086 for the Requirement Intelligence Platform's Layer 2 — the fourth and final capability built under ADR-0020/ADR-0021/ADR-0025/ADR-0026/ADR-0028, following Continuous Improvement (ADR-0022), Knowledge Graph (ADR-0023), and Organizational Memory (ADR-0027). This ADR is **Proposed**; a future CAP-086B extends it with the first deterministic engine under an unchanged contract, exactly mirroring ADR-0022's, ADR-0023's, and ADR-0027's own status ahead of their own B-milestones. The repository is certified ready for **CAP-086B — Deterministic Learning Engine**.
