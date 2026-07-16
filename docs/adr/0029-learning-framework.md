# ADR-0029 — Learning Framework

- **Status:** Proposed (CAP-086A — Architecture & Governance Freeze; CAP-086A.1 — Learning Architecture Refinement & Engine Governance Freeze; CAP-086A.2 — Learning Decision Governance & Deterministic Execution Constitution)
- **Date:** 2026-07-16 (CAP-086A — Architecture & Governance Freeze); 2026-07-16 (CAP-086A.1 — Learning Architecture Refinement & Engine Governance Freeze); 2026-07-16 (CAP-086A.2 — Learning Decision Governance & Deterministic Execution Constitution)
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** CAP-086A.1 (Learning Architecture Refinement — freezes the future deterministic engine's internal decomposition, the adjacent-only promotion discipline, the Validation/Institutionalization/Stability distinctions, and engine governance *before* any engine exists, mirroring how ADR-0023 §D10 pre-specified Knowledge Graph's own modular decomposition ahead of CAP-084B, and ADR-0027's own CAP-085A.1 pre-specified Organizational Memory's; see the Internal Engine Architecture section and D9–D17). CAP-086A.2 (Decision Governance & Deterministic Execution Constitution — freezes *how* every Learning decision must be made: deterministic, explainable, reproducible, policy-governed, immutable, append-only, and free of hidden state, plus the whole-engine purity guarantee those per-decision properties compose into; see the Decision Governance & Deterministic Execution section and D18–D26). A future runtime-integration milestone (CAP-086B, reserved) will implement a deterministic engine behind these now-triply-frozen contracts, mirroring how CAP-083B implemented the first deterministic Continuous Improvement engine behind ADR-0022, CAP-084B implemented the first deterministic Knowledge Graph engine behind ADR-0023, and CAP-085B implemented the first deterministic Organizational Memory engine behind ADR-0027.
- **Governing design:** `docs/proposals/learning-framework.md`
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — this is the fourth and final Layer 2 capability it names), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — the Truth Hierarchy this framework's every boundary applies), ADR-0025 (Derived Knowledge Architecture & Layer 2 Constitution — the peer-independence and fan-in rules this framework's own single-input boundary is defined against), ADR-0026 (Organizational Knowledge Architecture & Learning Constitution — Learning's earliest principles, §Stage 11), and ADR-0028 (Learning Constitution — the full constitutional definition of what this framework produces: Learning, Learned Knowledge, the four-level Knowledge Promotion Chain, Learning Validation, Lineage, Maturity, Confidence, and Evolution, including the adjacent-promotion discipline CAP-086A.1's D11 enforces at the model level, and the deterministic/explainable/reproducible decision discipline CAP-086A.2's D18 generalizes to every Learning decision). Also informed by ADR-0022 (Continuous Improvement Framework), ADR-0023 (Knowledge Graph Framework), and ADR-0027 (Organizational Memory Framework) — the three completed Layer 2 peer capabilities that precede this one, and the direct architectural precedent this ADR mirrors, including ADR-0023 §D10's and ADR-0027 §D9's modular engine decomposition CAP-086A.1's own D9 mirrors one milestone ahead of implementation.
- **Runtime status:** **Architecture only (CAP-086A; strengthened, still architecture only, CAP-086A.1; decision philosophy frozen, still architecture only, CAP-086A.2).** `LearningService.build` is an **abstract, dormant contract**; `DormantLearningService` raises `NotImplementedError` on every call. No candidate is proposed, no learning is validated, no confidence is recorded, no lifecycle is recorded, and nothing is wired into a runtime path. CAP-086A.1 introduced no code — no collaborator class, no rule catalogue, no `engine/` package — only the *shape* CAP-086B must fill. CAP-086A.2 introduces no code either — it freezes *how* CAP-086B's collaborators must decide, not what they decide (Decision Governance & Deterministic Execution, below). Runtime behaviour is byte-identical; the golden baseline is unchanged; the Architecture Version remains **1.2.0**.

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

**Clarified permanently (CAP-086A.1).** `LearningPolicy` **governs** validation and institutionalization; it never **performs** either. A future engine **executes** policy — it reads capability switches and thresholds and acts within the bounds they set — but the policy object itself contains no method that proposes a candidate, generates a learning, validates evidence, or institutionalizes anything. This is the same policy/engine separation ADR-0022, ADR-0023, and ADR-0027 §D6 already froze for their own subsystems, restated here explicitly because CAP-086B's future engine will be the first Learning collaborator pipeline to actually read this policy at runtime (D9 below).

## D7 — PlatformContext: the sole composition root

`PlatformContext` gains exactly two composition-root methods — `create_learning_policy()` and `create_learning_service()` — the **only** sanctioned points outside the `learning` package that may construct its governed objects, enforced by a containment test (mirrors ADR-0022 §D6, ADR-0023 §D6, ADR-0027 §D7).

## D8 — Future replaceability

A future deterministic, ML, LLM, GraphRAG, reinforcement learning, or neuro-symbolic Learning engine (CAP-086B onward, reserved) must implement the identical `build(OrganizationalMemoryResult) -> LearningResult` contract without `LearningResult` or `LearningPolicy` changing shape (ADR-0028 §Stage 17, Recommendation 14 below). `LearningCapabilitySwitches.enable_deterministic_engine` / `enable_ml_engine` / `enable_llm_engine` / `enable_reinforcement_learning_engine` / `enable_neuro_symbolic_engine` all remain reserved off until their respective future engine exists.

## Internal Engine Architecture (frozen, CAP-086A.1)

CAP-086A.1 strengthens the architecture *before* CAP-086B implements a deterministic engine — freezing the internal decomposition, promotion discipline, and governance a future engine must satisfy, exactly as ADR-0023 §D10 pre-specified Knowledge Graph's own modular decomposition and ADR-0027 §D9 pre-specified Organizational Memory's, each one milestone ahead of its own engine's implementation. This section introduces **no code**: no collaborator class exists yet, and none is created by this milestone. It permanently freezes the *shape* CAP-086B must fill.

### D9 — Deterministic engine decomposition (frozen, CAP-086A.1)

The canonical Learning engine — whenever CAP-086B implements it — shall consist of independently replaceable collaborators, mirroring the modular discipline ADR-0023 §D10 and ADR-0027 §D9 established for their own subsystems:

```
LearningCandidateCollector
        ↓
LearningCandidateClusterer
        ↓
LearningGenerator
        ↓
InstitutionalizationEvaluator
        ↓
LearningValidator
        ↓
StabilityEvaluator
        ↓
ConfidenceRecorder
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

Each collaborator owns exactly one responsibility (Recommendation 19 below). No collaborator computes another collaborator's responsibility — `LearningCandidateCollector` never validates; `LearningGenerator` never institutionalizes; `SummaryBuilder` never proposes a candidate. A future ML, LLM, GraphRAG, reinforcement learning, or neuro-symbolic engine may replace any single collaborator (e.g. swap `LearningValidator` for one backed by an LLM) without changing the public `build` contract or any sibling collaborator — the same reuse guarantee ADR-0023 §D10 and ADR-0027 §D9 froze for their own decompositions. The runtime contract, `LearningResult`, remains unchanged regardless of which collaborators a future milestone implements first or replaces later.

### D10 — Collaborator ownership and layering (frozen, CAP-086A.1)

Each collaborator's responsibility is fixed in advance, so a future engine cannot quietly widen a collaborator's scope by handing it work it has no architectural business performing:

| Collaborator | Owns only | Produces | Never |
|---|---|---|---|
| `LearningCandidateCollector` | candidate evidence collection | `LearningCandidate` | validates, clusters, generates Learning, computes confidence, institutionalizes, records lifecycle |
| `LearningCandidateClusterer` | duplicate elimination, canonical grouping | clustered candidate references only | validates, institutionalizes, creates Learning |
| `LearningGenerator` | Learning construction | `Learning` | validates, institutionalizes, computes confidence, records lifecycle |
| `InstitutionalizationEvaluator` | organizational-readiness determination | an institutionalization decision (consumed by `LifecycleRecorder`, never persisted directly by this collaborator) | creates Learning, validates evidence, records lifecycle, computes confidence |
| `LearningValidator` | `LearningValidation` construction | `LearningValidation` | institutionalizes, computes confidence as a standalone act, records lifecycle |
| `StabilityEvaluator` | stability evaluation across organizational evidence | a stability decision (D13; no dedicated runtime field yet) | computes confidence, institutionalizes, validates |
| `ConfidenceRecorder` | `LearningConfidence` construction | `LearningConfidence` | validates, institutionalizes, records lifecycle |
| `PromotionRecorder` | recording promotion decisions | promotion metadata (reserved; see note below) | creates Learning, validates Learning |
| `LifecycleRecorder` | `LearningLifecycle` construction | `LearningLifecycle` | generation, validation, institutionalization determination |
| `SummaryBuilder` | `LearningSummary` | `LearningSummary` | computes knowledge; tallies already-recorded rows only |
| `MetricsBuilder` | `LearningMetrics` | `LearningMetrics` | computes knowledge; tallies already-recorded rows only |
| `ResultBuilder` | `LearningResult` assembly | `LearningResult` | any upstream computation (D17) |

`SummaryBuilder` and `MetricsBuilder` never compute knowledge — they tally already-recorded rows by a field those rows already carry, exactly the "presentation only" discipline ADR-0022's, ADR-0023's, and ADR-0027's own summary/metrics builders already apply (ADR-0027 §D12).

**`PromotionRecorder`'s output is reserved, not a new model (frozen, CAP-086A.1).** Unlike Organizational Memory, which already ships a dedicated `KnowledgePromotion` record type at CAP-085A, Learning's CAP-086A brief was explicit — "Introduce immutable models: ... Nothing else" — and introduced no equivalent `LearningPromotion` record. This milestone changes no model (Stage 15 verification, below), so `PromotionRecorder`'s "promotion metadata" remains a reserved future concept, mirroring how ADR-0027 §D14 reserved `PromotionRule` as governance-only, no-implementation ahead of CAP-085B. No information is lost by this deferral: promotion provenance is already fully reconstructable today from `Learning.candidate_id` and `LearningValidation.candidate_id` alone (D11) — a future `LearningPromotion` record, if ever introduced, would add convenience, never a missing fact.

### D11 — Adjacent-only promotion (frozen, CAP-086A.1)

```
Best Practice
        ↓
Learning Candidate
        ↓
Learning
```

**Only adjacent promotion is permitted.** Best Practice may be promoted to Learning Candidate; Learning Candidate may be promoted to Learning. **Forbidden permanently:** Best Practice promoted directly to Learning, skipping Learning Candidate. This is not a new constraint introduced by this milestone — it is already structurally guaranteed by the CAP-086A model shapes: `LearningCandidate.source_best_practice_ids` is typed `tuple[str, ...]` and exists precisely to name Best Practice ids, while `Learning.candidate_id` is typed `LearningCandidateId` and carries no field capable of holding a raw Best Practice id directly. CAP-086A.1 freezes this as permanent constitutional intent (Recommendation 18 below) so no future engine, rule, or model revision may widen `Learning`'s shape to skip a level.

### D12 — Validation vs. Institutionalization (frozen, CAP-086A.1)

Two permanently distinct questions govern promotion from Learning Candidate to Learning:

- **Validation** answers: *is the Learning technically valid?* Owned exclusively by `LearningValidator`, expressed through `LearningValidation.gates_cleared` — the six governed ADR-0028 §Stage 6 gates (sufficiency, validated evidence, repeatability, organizational confidence, organizational usefulness, complete explainability).
- **Institutionalization** answers: *is the Learning organizationally ready for institutional adoption?* Owned exclusively by `InstitutionalizationEvaluator`, expressed through the already-frozen `LearningMaturity` vocabulary (specifically its `INSTITUTIONAL` and `STANDARD` rungs) and recorded, once decided, by `LifecycleRecorder` into a `LearningLifecycle` entry — never by `InstitutionalizationEvaluator` itself (D10).

**Institutionalization evaluates organizational readiness. It never evaluates technical correctness** — that remains `LearningValidator`'s exclusive responsibility. Neither collaborator performs the other's responsibility, permanently (Recommendation 16 below). This is not a new axis requiring a new model field — `LearningMaturity`'s seven-rung ladder (ADR-0028 §Stage 8) already distinguishes `VALIDATED` from `INSTITUTIONAL` from `STANDARD`; this D-section freezes which collaborator is responsible for which transition along that already-frozen ladder.

### D13 — Learning Stability (frozen, CAP-086A.1)

**Stability answers:** *has this Learning remained consistently valid across organizational evidence?*

Freeze the permanent three-axis independence:

- **Confidence** = strength of evidence (ADR-0028 §Stage 9, `LearningConfidenceLevel`).
- **Maturity** = organizational adoption (ADR-0028 §Stage 8, `LearningMaturity`).
- **Stability** = consistency over time.

The three concepts are permanently independent; none may substitute for another. A `Learning` object can carry `VERIFIED` confidence on its first observation and yet have no stability history at all; a long-`INSTITUTIONAL` `Learning` object can, in principle, still be unstable if recent organizational evidence has begun to contradict it. Owned exclusively by `StabilityEvaluator` (D9/D10).

**No dedicated runtime field exists yet (frozen scope boundary, CAP-086A.1).** This milestone introduces no model change (Stage 15 verification, below), so `LearningResult`'s frozen shape carries no dedicated Stability field today. This D-section freezes the *concept and its independence* from Confidence and Maturity, permanently — it does not yet decide how a stability decision is persisted. That is deferred to CAP-086B or a later, dedicated model-extension milestone, without needing to revisit this independence rule.

### D14 — Complete explainability chain (frozen, CAP-086A.1)

Every `Learning` object must reconstruct this complete chain:

```
Learning
        ↓
Learning Candidate
        ↓
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

The first hop (`Learning` → `Learning Candidate`) is enforced today by `Learning.candidate_id`'s own required field. The second hop (`Learning Candidate` → `Best Practice`) is enforced today by `LearningCandidate.source_best_practice_ids`'s own "at least one reference" validator. The remaining hops (`Best Practice` → `Lesson` → `Experience` → `Continuous Improvement`/`Knowledge Graph` → `Historical Dataset` → `Execution Ids` → `Runtime Truth`) are already frozen by ADR-0027 §D13 for Organizational Memory's own explainability chain — Learning's own chain composes with it, through the referenced `organizational_memory_result_id`, rather than duplicating it. No Learning Candidate may be promoted to Learning, and no Learning may be institutionalized, unless this complete chain can be reconstructed (Recommendation 21 below).

### D15 — Engine philosophy: institutionalizes, never invents (frozen, CAP-086A.1)

The Learning Engine never discovers new technical findings, diagnoses, structural observations, or analytical conclusions. It may only:

* validate
* institutionalize
* promote
* mature
* record confidence
* record stability
* record lifecycle

over Organizational Knowledge already produced by Continuous Improvement, Knowledge Graph, and Organizational Memory. It never:

* performs Continuous Improvement's own recurrence analysis
* discovers Knowledge Graph's own structural relationships
* creates Best Practices, Lessons, or Experiences (Organizational Memory's exclusive ownership, ADR-0026 Recommendation 10)
* creates Findings or Observations (Continuous Improvement's and Knowledge Graph's exclusive ownership)

This mirrors Recommendation 18 of ADR-0027 ("Organizational Memory Curates, It Does Not Analyze"), lifted one tier: Learning validates and matures, it does not analyze (Recommendation 15 below).

### D16 — Deterministic execution pipeline (frozen, CAP-086A.1)

Freeze the permanent execution order:

```
Collect candidates
        ↓
Cluster candidates
        ↓
Generate Learning
        ↓
Evaluate institutionalization
        ↓
Validate Learning
        ↓
Evaluate stability
        ↓
Record confidence
        ↓
Record promotion
        ↓
Record lifecycle
        ↓
Build summary
        ↓
Build metrics
        ↓
Build LearningResult
```

Future engines may change algorithms within any single stage. They must preserve this execution pipeline — no stage is skipped, and no stage is reordered, the same discipline ADR-0020 §Stage 8 froze for a capability's lifecycle and ADR-0027 §D17 froze for Organizational Memory's own collaborator pipeline, now frozen for Learning's.

### D17 — Result ownership and future replaceability (frozen, CAP-086A.1)

`ResultBuilder` is permanently the only owner of `LearningResult(...)` construction anywhere in the future engine. No other collaborator — not `LearningCandidateCollector`, not `LearningCandidateClusterer`, not `LearningGenerator`, not `InstitutionalizationEvaluator`, not `LearningValidator`, not `StabilityEvaluator`, not `ConfidenceRecorder`, not `PromotionRecorder`, not `LifecycleRecorder`, not `SummaryBuilder`, not `MetricsBuilder` — may construct it. Every other collaborator produces intermediate immutable artifacts or internal decisions only, never the final result. This exactly mirrors Organizational Memory's own frozen invariant (ADR-0027 §D16: "`ResultBuilder` is the **only** constructor of `OrganizationalMemoryResult` anywhere in this engine") and Knowledge Graph's before it (ADR-0023 §D10).

Every collaborator named in D9 may later have deterministic, ML, LLM, GraphRAG, reinforcement learning, neuro-symbolic, or hybrid implementations. `LearningService`, `LearningResult`, and `PlatformContext` remain unchanged regardless of which collaborators a future milestone implements first or replaces later (Recommendation 22 below).

## Decision Governance & Deterministic Execution (frozen, CAP-086A.2)

CAP-086A.2 freezes *how* every Learning decision must be made — before CAP-086B implements a single one. This section introduces **no code**: no collaborator class exists yet, no rule catalogue exists yet, and none is created by this milestone. It permanently freezes the decision philosophy CAP-086B's engine, and every future engine variant after it, must satisfy.

### D18 — Deterministic Decision Principle (frozen, CAP-086A.2)

Freeze permanently. Every Learning decision — whatever collaborator makes it, whatever engine implements that collaborator — is:

* **deterministic** — the same inputs always produce the same decision;
* **explainable** — every decision names the specific inputs it was derived from (D23);
* **reproducible** — regenerable at any time from the same inputs, with no dependence on when it was first made (D24);
* **policy-governed** — bounded by `LearningPolicy`'s capability switches and thresholds, never a literal hard-coded in a collaborator (D6);
* **immutable** — once made, never modified (D25);
* **append-only** — a changed decision is a *new* decision referencing the one it supersedes, never an edit (D25).

**No hidden reasoning. No hidden heuristics. No hidden cache. No hidden mutable state.** A collaborator that consults anything not named in D20 below — a module-level cache, a random seed, wall-clock time beyond an injected clock, a network call, an environment variable — violates this principle regardless of how plausible its output looks. This is the platform-wide "explainability first" discipline (ADR-0020 §Stage 7, ADR-0028 §Stage 4) restated at the granularity of a single Learning decision, the finest grain this constitution reaches.

### D19 — Decision Governance: every category obeys the same principle (frozen, CAP-086A.2)

Freeze permanently. D18's six properties apply, without exception, to every category of Learning decision this engine makes:

* **Promotion decisions** (Learning Candidate → Learning) are deterministic, explainable, reproducible, governed, append-only, and never mutate history (mirrors D11's adjacent-only discipline, now extended to the decision that triggers it).
* **Validation decisions** (`LearningValidator`) satisfy the same six properties. Validation is never heuristic and never depends on hidden context — only the candidate's own referenced Best Practices and the governed policy (D20).
* **Institutionalization decisions** (`InstitutionalizationEvaluator`) satisfy the same six properties. Institutionalization is permanently independent from Validation (D12): institutionalization never changes a validation outcome, and validation never changes an institutionalization outcome.
* **Stability decisions** (`StabilityEvaluator`) satisfy the same six properties. Stability never changes Confidence; Confidence never changes Stability; neither changes Maturity (D13, extended: all three axes remain independent inputs to, and independent outputs of, their own dedicated collaborator alone).
* **Confidence decisions** (`ConfidenceRecorder`) satisfy the same six properties. Confidence is always **derived** from the referenced evidence count and governed thresholds — never guessed, and never estimated from state a future reader cannot also inspect (D20).
* **Lifecycle decisions** (`LifecycleRecorder`) satisfy the same six properties. Every maturity transition is append-only: it is recorded as a new `LearningLifecycle` entry, never a mutation of a prior one, and never a rewrite of history (mirrors ADR-0028 §Stage 8, ADR-0026 §Stage 7).

No category is exempt, and no future engine variant may relax any one of D18's six properties for any single category while claiming to satisfy this ADR for the others.

### D20 — Decision Inputs and Collaborator Communication (frozen, CAP-086A.2)

Freeze permanently. Every Learning decision may consult only:

* the consumed `OrganizationalMemoryResult`;
* the governed `LearningPolicy`;
* immutable intermediate objects already produced by an earlier collaborator in the frozen D16 execution order.

**Nothing else.** Forbidden, permanently, for every collaborator: the Historical Dataset, `ContinuousImprovementResult`, `KnowledgeGraphResult`, any Layer 1 runtime contract, the Execution Package, any other runtime artifact, external storage of any kind, global interpreter state, and a prior `LearningResult` (mirrors Recommendation 6/7 of this ADR and Recommendation 20 of ADR-0028, restated at collaborator granularity).

**Collaborators communicate only through immutable objects.** Never through shared mutable state, a singleton cache, a module-level or global variable, a mutable field on the engine itself, or any other hidden side channel. Each collaborator receives immutable input and produces immutable output — nothing else crosses a collaborator boundary. This is the same self-containment discipline D12 of ADR-0027 already froze for Organizational Memory's own collaborator layering, restated here as the platform-wide default for every Learning collaborator without exception.

### D21 — Engine Purity (frozen, CAP-086A.2)

Freeze permanently. The deterministic Learning engine, taken as a whole, is a pure function:

```
OrganizationalMemoryResult
        +
LearningPolicy
        ↓
LearningResult
```

**Same input, same output, always.** No collaborator inside the pipeline may introduce non-determinism the whole-engine boundary does not already permit — the composition of twelve deterministic, side-effect-free collaborators (D9) is itself deterministic and side-effect-free, by construction. This is the direct generalization of D18's per-decision purity to the entire engine, and the property every future replacement of any single collaborator (D9/Recommendation 22) must preserve without exception.

### D22 — Result Assembly Remains Non-Computational (frozen, CAP-086A.2)

Freeze permanently, restating and sharpening D10/D17. `ResultBuilder` never computes a decision — it assembles the `LearningResult` from already-finished collaborator output only. `SummaryBuilder` never computes Learning — it tallies already-recorded rows into `LearningSummary`. `MetricsBuilder` never computes Learning — it tallies already-recorded rows into `LearningMetrics`. None of the three may re-derive, re-validate, re-institutionalize, or otherwise recompute anything a prior collaborator in the D16 pipeline already decided.

### D23 — Decision Explainability (frozen, CAP-086A.2)

Freeze permanently. Every Learning decision must name the specific inputs (D20) it was derived from — a decision that cannot name what produced it is not explainable and must not be constructible. This is D18's explainability property, detailed: explainability is not a property a decision acquires after the fact through documentation or a report; it is a structural requirement on the decision itself, satisfied only by referencing (never re-deriving) the exact inputs consulted, exactly as D14's explainability chain already requires end-to-end for `Learning` as an object, now required for every intermediate decision that leads to one.

### D24 — Decision Reproducibility (frozen, CAP-086A.2)

Freeze permanently. Given the same `OrganizationalMemoryResult`, the same `LearningPolicy`, and the same upstream collaborator outputs, every Learning decision must reproduce identically, regardless of when or how many times it is remade. This is D18's reproducibility property, detailed: reproducibility is what makes D21's engine purity possible in practice, and what makes a future golden regression test (CAP-086C, reserved) meaningful the moment one exists.

### D25 — Decision Immutability (frozen, CAP-086A.2)

Freeze permanently. Once a Learning decision is made, it is never modified. A later reconsideration — a re-validation, a re-institutionalization, a confidence update, a stability re-check — produces a **new** decision, recorded as a new object referencing the one it supersedes (mirrors ADR-0028 §Stage 11, Recommendation 2/4 of this ADR). The superseded decision remains exactly as it was: an accurate record of what was decided from the inputs available at the time. This is D18's immutable/append-only pair, detailed at the level of a single decision rather than a single object.

### D26 — Decision Traceability (frozen, CAP-086A.2)

Freeze permanently. Every Learning decision must be traceable, hop by hop, through the D20 inputs it consulted, composing with D14's already-frozen explainability chain (`Learning → Learning Candidate → Best Practice → Lesson → Experience → Continuous Improvement or Knowledge Graph → Historical Dataset → Execution Ids → Runtime Truth`). No decision may exist whose trace terminates at anything other than a named, versioned input — an untraceable decision is indistinguishable from a guess, and this constitution forbids guessing (D18, D23).

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

### Recommendation 15 — Learning Engine institutionalizes but never invents knowledge (mandatory, CAP-086A.1, frozen permanently)

The Learning Engine shall never generate new technical findings, diagnoses, structural observations, or analytical conclusions. It may only validate, institutionalize, promote, mature, record confidence, record stability, and record lifecycle over Organizational Knowledge already produced by Continuous Improvement, Knowledge Graph, and Organizational Memory (D15). Technical inference remains those three predecessors' own responsibility, permanently.

### Recommendation 16 — Validation is distinct from Institutionalization (mandatory, CAP-086A.1, frozen permanently)

Validation answers "is the Learning technically valid?" (`LearningValidator`, `LearningValidation.gates_cleared`). Institutionalization answers "is the Learning organizationally ready?" (`InstitutionalizationEvaluator`, expressed through `LearningMaturity`/`LearningLifecycle`). Neither collaborator performs the other's responsibility (D12).

### Recommendation 17 — Stability is distinct from Confidence and Maturity (mandatory, CAP-086A.1, frozen permanently)

Confidence measures the strength of evidence (ADR-0028 §Stage 9). Maturity measures organizational adoption (ADR-0028 §Stage 8). Stability measures consistency across organizational evidence over time. The three axes are permanently independent; none may substitute for another (D13).

### Recommendation 18 — Promotion remains adjacent, never skip-level (mandatory, CAP-086A.1, frozen permanently)

Best Practice may be promoted to Learning Candidate; Learning Candidate may be promoted to Learning. Best Practice promoted directly to Learning, skipping Learning Candidate, is forbidden permanently — already structurally guaranteed by `LearningCandidate.source_best_practice_ids`'s and `Learning.candidate_id`'s typed shapes (D11).

### Recommendation 19 — Single Responsibility Collaborators (mandatory, CAP-086A.1, frozen permanently)

Every deterministic engine collaborator (D9/D10) owns exactly one transformation. No collaborator performs multiple architectural responsibilities — a future `LearningGenerator` that also records lifecycle state, or a future `SummaryBuilder` that also validates a candidate, violates this Recommendation regardless of how the resulting `LearningResult` looks.

### Recommendation 20 — Result Assembly Principle (mandatory, CAP-086A.1, frozen permanently)

Only `ResultBuilder` may construct `LearningResult` (D17). All other collaborators produce intermediate immutable artifacts or internal decisions only.

### Recommendation 21 — Explainability precedes promotion and institutionalization (mandatory, CAP-086A.1, frozen permanently)

No Learning Candidate may be promoted to Learning, and no Learning may be institutionalized, unless it can reconstruct the complete provenance chain back to Runtime Truth (D14). A promotion or institutionalization decision that cannot name its full chain is not explainable and must not be constructible.

### Recommendation 22 — Future collaborators remain replaceable without contract change (mandatory, CAP-086A.1, frozen permanently)

Every collaborator named in D9 may later have deterministic, ML, LLM, GraphRAG, reinforcement learning, neuro-symbolic, or hybrid implementations. `LearningService`, `LearningResult`, and `PlatformContext` remain unchanged regardless of which collaborators a future milestone implements first or replaces later (D17).

### Recommendation 23 — Every Learning decision is deterministic, explainable, reproducible, governed, immutable, and append-only (mandatory, CAP-086A.2, frozen permanently)

No Learning decision, of any category, may satisfy fewer than all six of D18's properties. A decision satisfying only some of them is not a Learning decision and must not be constructible.

### Recommendation 24 — Learning decisions never depend on hidden state (mandatory, CAP-086A.2, frozen permanently)

No collaborator may consult a hidden cache, a hidden heuristic, hidden mutable state, or any input not named in D20. A decision that cannot be reproduced from its named inputs alone violates this Recommendation regardless of how accurate it appears (D18, D24).

### Recommendation 25 — Collaborators communicate only through immutable objects (mandatory, CAP-086A.2, frozen permanently)

No collaborator boundary may cross shared mutable state, a singleton cache, a global variable, or a mutable engine field. Every collaborator receives immutable input and produces immutable output, and nothing else (D20).

### Recommendation 26 — The deterministic engine is a pure function (mandatory, CAP-086A.2, frozen permanently)

`OrganizationalMemoryResult + LearningPolicy → LearningResult` is a pure function: the same pair of inputs always yields the same output, and no collaborator inside the pipeline may introduce non-determinism the whole-engine boundary does not already permit (D21).

### Recommendation 27 — Institutionalization, Stability, and Confidence decisions remain mutually independent (mandatory, CAP-086A.2, frozen permanently)

Institutionalization never changes a Validation outcome, and Validation never changes an Institutionalization outcome (D12/D19). Stability never changes Confidence; Confidence never changes Stability; neither changes Maturity (D13/D19). No future engine may collapse any two of these axes into a shared computation.

### Recommendation 28 — Confidence is always derived, never guessed (mandatory, CAP-086A.2, frozen permanently)

`ConfidenceRecorder`'s output must be a deterministic function of the referenced evidence count and the governed policy thresholds — never an estimate, a heuristic, or a value read from hidden state (D19/D20).

### Recommendation 29 — Lifecycle transitions are append-only and never rewrite history (mandatory, CAP-086A.2, frozen permanently)

Every maturity transition `LifecycleRecorder` records is a new `LearningLifecycle` entry, never a mutation of a prior one and never a rewrite of a prior maturity record (D19/D25, mirrors Recommendation 4).

### Recommendation 30 — ResultBuilder, SummaryBuilder, and MetricsBuilder assemble; they never compute Learning (mandatory, CAP-086A.2, frozen permanently)

None of the three may re-derive, re-validate, re-institutionalize, or otherwise recompute anything a prior collaborator in the D16 pipeline already decided — they tally and assemble already-finished output only (D22).

---

## Trade-offs

- **Learning consumes exactly one Layer 2 tier, unlike Organizational Memory's own two-peer fan-in.** Accepted: ADR-0028 §Stage 12/16 exists precisely to authorize this narrower shape; this ADR follows it exactly (Stage 0, D2).
- **`LearningResult` references the consumed `OrganizationalMemoryResult` id as a plain string rather than embedding the result.** Accepted: this is the same "reference, never copy" discipline every prior subsystem's consumed-input models already apply (ADR-0018 `EnhancementInputReference`, ADR-0019 `RecommendationInputReference`, ADR-0027's own two-id reference), applied here to one Layer 2 tier instead of two.
- **Governed defaults (`minimum_best_practices_for_candidate`, `minimum_validation_gates_for_learning`, `minimum_confidence_for_learning`) are calibrated conservatively, not empirically.** The CAP-086A default policy bounds reflect a deliberately conservative first pass — all six governed gates required, a minimum of two corroborating best practices, and the highest confidence ordinal — not yet tuned against real validated learning. Accepted: tuning is a versioned policy change under a future golden re-baseline, never an engine code change (Recommendation 5 of this ADR).

## Future evolution

- **Done (CAP-086A.1).** Engine architecture refinement & governance freeze: the future engine's modular 12-collaborator decomposition, adjacent-only promotion discipline, the Validation/Institutionalization/Stability distinctions, the complete explainability chain, and the reserved promotion-metadata concept — no code, still architecture only. See the Internal Engine Architecture section, D9–D17.
- **Done (CAP-086A.2).** Decision Governance & Deterministic Execution Constitution: the six permanent properties every Learning decision must satisfy (deterministic, explainable, reproducible, governed, immutable, append-only), the freedom from hidden state, collaborator-to-collaborator immutable-object-only communication, whole-engine purity, and per-category decision governance for promotion/validation/institutionalization/stability/confidence/lifecycle — no code, still architecture only. See the Decision Governance & Deterministic Execution section, D18–D26.
- **CAP-086B — Deterministic Learning Engine (reserved).** The first real engine behind the frozen `build` signature: implement the CAP-086A.1 collaborator pipeline strictly from the one resolved `OrganizationalMemoryResult` (Recommendation 6), obeying the CAP-086A.2 decision-governance constitution in every collaborator, never independent analysis or re-implementation of Organizational Memory's own curation.
- **Runtime activation (CAP-086C, reserved)** — wiring `build` into a live pipeline, plus a future Execution Package projection and golden re-baseline, mirroring CAP-085C's activation of Organizational Memory.
- **Feature Engineering (Layer 3, reserved)** — the first capability outside Layer 2, to consume `LearningResult` per Recommendation 8 above, completing the Layer 2 → Layer 3 bridge ADR-0028 §Stage 16 names.
- **Future AI validation, promotion reasoning, and institutional-adoption modeling over Learned Knowledge** (reserved) — higher-layer or engine-variant capabilities that consume `LearningResult` without ever becoming part of this contract.
- Promotion of the shared version/identity value-objects to `shared/` (the debt ADR-0015 §C, ADR-0016, ADR-0017, ADR-0018 §D5, ADR-0019 §D5, ADR-0022, ADR-0023, and ADR-0027 already name).

## Ownership, runtime position, governance

- **Owns:** validated Learned Knowledge — learning candidates, learnings, validation history, confidence records, maturity/lifecycle state, Learning Framework metadata. Owns the frozen internal engine decomposition and collaborator ownership (D9–D17), and the frozen decision-governance constitution every collaborator's own decisions must satisfy (D18–D26), both reserved ahead of the deterministic engine that will implement them.
- **Does not own:** Engineering Context Orchestration, Analysis, Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, Continuous Improvement, Knowledge Graph, Organizational Memory, the Execution Package, or the Historical Dataset itself (ADR-0021 §Stage 6 names that owner, not this ADR). Does not own any Feature Engineering responsibility (ADR-0020 §Stage 4, reserved for Layer 3).
- **Runtime position (architecture only — CAP-086A; strengthened, still architecture only — CAP-086A.1; decision philosophy frozen, still architecture only — CAP-086A.2):** `OrganizationalMemoryResult` → (future engine, reserved) → `LearningResult`. Architecture frozen; the internal collaborator pipeline is pre-specified; the decision-governance constitution every collaborator must satisfy is pre-specified; no engine exists; nothing is wired into any execution pipeline.
- **Governance:** registered as CAP-086 for the Requirement Intelligence Platform's Layer 2 — the fourth and final capability built under ADR-0020/ADR-0021/ADR-0025/ADR-0026/ADR-0028, following Continuous Improvement (ADR-0022), Knowledge Graph (ADR-0023), and Organizational Memory (ADR-0027). This ADR is **Proposed**; CAP-086A.1 strengthened it with the frozen internal engine architecture and validation/institutionalization/stability/promotion/result ownership rules under an unchanged public contract; CAP-086A.2 strengthened it further with the frozen decision-governance constitution — determinism, explainability, reproducibility, policy-governance, immutability, append-only evolution, freedom from hidden state, immutable-only collaborator communication, and whole-engine purity — every future collaborator's every decision must satisfy, still under the same unchanged public contract; a future CAP-086B extends it with the first deterministic engine implementing that doubly-frozen shape, exactly mirroring ADR-0022's, ADR-0023's, and ADR-0027's own status ahead of their own B-milestones. The repository is certified ready for **CAP-086B — Deterministic Learning Engine**.
