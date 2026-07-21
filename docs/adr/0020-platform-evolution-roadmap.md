# ADR-0020 — Platform Evolution Roadmap & Architectural Constitution

- **Status:** Proposed
- **Date:** 2026-07-15
- **Supersedes:** nothing. **Amends:** nothing (see the Stage 0 note below for one corrected header in ADR-0016).
- **Governing design:** none — this ADR *is* the governing design. It introduces no proposal document because it is not subsystem architecture.
- **Depends on:** every accepted architectural ADR to date (ADR-0011 through ADR-0019) and the platform capabilities they govern.
- **Runtime status:** Not applicable. This is a **documentation-only** milestone: no runtime behaviour, no code, no model, no policy, no `PlatformContext`, no Execution Package, no CLI, no serializer, and no version number (Architecture or Platform) changes. It does not implement, wire, or freeze anything; it names the permanent structure everything already built fits into, and the structure everything not yet built must fit into.

## Scope note

Unlike every ADR before it, ADR-0020 is not owned by a subsystem and does not govern one. ADR-0011–ADR-0019 each froze the architecture of a single capability inside **Layer 1** (defined below). ADR-0020 sits above all of them: it is the platform's **architectural constitution** — the permanent statement of what layers exist, what each layer owns, how layers may depend on one another, what lifecycle every capability must pass through, and where a future capability belongs. No subsystem ADR is amended or superseded by it (with one narrow exception noted in Stage 0): it names a structure those ADRs already implicitly followed, and asks that every future one follow it explicitly.

---

## Stage 0 — Repository assessment

Before writing this ADR, every accepted architectural ADR governing the Requirement Intelligence pipeline was reviewed for lifecycle consistency and completed runtime integration.

| ADR | Capability | Runtime status reviewed |
|---|---|---|
| ADR-0011/0012/0013 | CP1 (engineering-readiness engine, criteria catalog, first criterion) | Accepted; live — CP1 runs after the Validation → CP1 handoff opens, immediately before Quality Governance. |
| ADR-0015 | Engineering Context Orchestration | Accepted; live — `EngineeringContextOrchestrator` composes every run's context under a governed, swappable policy (CAP-076C/D). |
| ADR-0016 | Grounding & Traceability | **Header inconsistency found and corrected as part of this Stage 0 review** (see note below). Body text and dependent ADRs already confirmed it: Accepted; live — Grounding runs immediately after Analysis, and `GroundingResult` is a completed peer every later capability (Quality Governance, Recommendation) consumes. |
| ADR-0017 | Quality Governance | Accepted; live — the terminal release authority, wired in after CP1 (CAP-080D), manifest purity hardened (CAP-080D.1). |
| ADR-0018 | Requirement Enhancement | Accepted; live — wired in immediately after Analysis (CAP-081C). |
| ADR-0019 | Recommendation | Accepted; live — wired in immediately after Quality Governance, at the frozen end of the pipeline (CAP-082C). |

**Validation** and **Requirement Analysis** are governed by pre-ADR-numbering architecture documents (`docs/architecture/ai-response-validation.md`, `docs/architecture/validation-*-contract.md`, and the Requirement Analysis service documentation) rather than a single numbered ADR; both are live, completed Layer 1 members referenced as consumed peers throughout ADR-0011–ADR-0019. This is not an inconsistency — it predates the ADR convention this platform later adopted — and this roadmap does not require retrofitting a number onto them to include them as Layer 1 members below.

**Inconsistency found and corrected:** ADR-0016's header still read "Status: Proposed (design only — CAP-077 introduces no runtime behaviour in this milestone)" and "Runtime status: Not yet implemented," even though its own body text states "CAP-077E activated the runtime" and every later ADR (0017, 0018, 0019) lists `GroundingResult` as an already-completed peer result it consumes. The header was simply never updated when Grounding's runtime was activated in a later milestone (CAP-077E/CAP-077F.2) — a documentation staleness bug, not an architectural weakness. It has been corrected as a narrow, additive header fix alongside this ADR (no runtime, code, or contract change); ADR-0016's architecture is otherwise untouched.

**No other inconsistency was found.** Every reviewed capability:

- reached runtime integration (a real, deterministic engine wired into the live pipeline, not just an architecture freeze);
- followed the same shape of lifecycle — architecture freeze, then a deterministic implementation, then a runtime-contract freeze (where a dedicated milestone existed for it), then runtime integration, then Execution Package integration, then a golden re-baseline;
- consumes only lower/prior-stage results, never reaching backward into a downstream consumer or forward into a not-yet-computed result.

> No architectural weakness found. Proceeding with documentation only.

---

## Stage 1 — Introducing ADR-0020

This document, `docs/adr/0020-platform-evolution-roadmap.md`, is **Proposed**. It is the platform constitution, not subsystem architecture: it defines no runtime contract, no policy, no model, and no service. Its only content is the permanent structure — layers, dependency rules, the capability lifecycle, and a placement guide — that every subsystem ADR before and after it is expected to fit.

---

## Stage 2 — Problem statement

The repository now contains multiple independently governed subsystems — Engineering Context, Requirement Analysis, Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, and Recommendation — each frozen and integrated one capability at a time, each governed by its own ADR, each following (informally, ADR by ADR) a similar shape of lifecycle.

That similarity was never written down as a rule. Without a platform-level architectural roadmap, every future capability risks:

- **Architectural drift** — a new capability inventing its own lifecycle, its own dependency direction, or its own composition-root pattern instead of the one every prior capability already proved out.
- **Duplicated responsibilities** — two subsystems each partially owning the same concern (a scoring calculation, a decision, a projection) because no document says which layer owns it.
- **Misplaced capabilities** — a capability that reasons over historical trends built as if it were a single-execution concern, or a single-execution concern built as if it needed a knowledge graph.
- **Circular dependencies** — a "lower" capability reaching forward into a "higher" one's not-yet-computed output, because no document freezes which direction dependencies may run.
- **Inconsistent lifecycle adoption** — a capability shipped straight to runtime integration without ever freezing its contract, or a contract frozen and then never activated, with no governing document to say that both are required, in order.

The platform therefore requires a permanent architectural constitution: not another subsystem ADR, but the document that tells every subsystem ADR where it belongs and what rules it must obey.

---

## Stage 3 — Platform vision

The platform evolves through multiple architectural layers, each one a distinct level of reasoning built on top of the ones below it.

- Each layer **consumes** the layer below it — its completed, frozen runtime contracts, never its internals.
- Each layer **never bypasses** the layer below it — a higher layer cannot reach past an intermediate layer to consume something two levels down as if the layer between did not exist.
- Each layer **never owns** the responsibilities of the layer below it — computing a lower layer's judgement inside a higher layer duplicates ownership and is forbidden, exactly as ADR-0001 forbids it between subsystems within a single layer.
- Each layer **never creates a reverse dependency** — nothing in a lower layer may import, invoke, or depend on anything in a higher layer, ever.

Every capability, present or future, must belong to **exactly one** architectural layer. A capability that seems to span two layers has not yet been decomposed correctly.

---

## Stage 4 — Platform layers

### Layer 1 — Requirement Intelligence

**Purpose:** Execution Intelligence — deterministic, governed reasoning over **one** Requirement Intelligence execution.

**Includes:**

- Engineering Context (Engineering Context Orchestration, ADR-0015)
- Requirement Analysis
- Requirement Enhancement (ADR-0018)
- Grounding (ADR-0016)
- Validation
- CP1 (ADR-0011/0012/0013)
- Quality Governance (ADR-0017)
- Recommendation (ADR-0019)
- Execution Package

**Ownership.** Layer 1 owns everything about judging a single execution: what evidence the reasoner saw, what it produced, whether that production is enriched, grounded, structurally valid, engineering-ready, releasable, and what to recommend doing about all of that. It owns the Execution Package that projects every one of those judgements into a durable, inspectable artifact set.

**Questions Layer 1 answers:**

- What evidence did the reasoner see, and how was it composed? (Engineering Context)
- What did the reasoner produce? (Requirement Analysis)
- What does the requirement set look like structurally — enriched, related, observed? (Requirement Enhancement)
- Is each generated requirement supported by the evidence? (Grounding)
- Is the response well-formed against the reasoning contract? (Validation)
- Is the run engineering-ready? (CP1)
- Is the run releasable on quality grounds? (Quality Governance)
- Given everything already judged, what should an engineer do next? (Recommendation)
- How is all of the above persisted, checksummed, and indexed for exactly this run? (Execution Package)

Layer 1 reasons over **one execution at a time** and never looks backward across runs. That is precisely the boundary Layer 2 exists to cross.

### Layer 2 — Continuous Learning

**Constitutional foundation:** ADR-0021 (Truth Hierarchy: Runtime Truth → Historical Truth → Derived Knowledge), ADR-0024 (Historical Dataset & Historical Truth Constitution — the permanent definition of Historical Truth, Historical Dataset ownership, the Historical Dataset Resolution Principle, storage independence, and the Layer 1 → Historical Dataset → Layer 2 dependency chain every Continuous Learning capability inherits by citation, elevated from the pattern CAP-083 and CAP-084 each independently discovered), ADR-0025 (Derived Knowledge Architecture & Layer 2 Constitution — the permanent definition of Derived Knowledge, Layer 2's exclusive right to produce it, immutability, explainability, and the peer-independence rule governing every Layer 2 capability's relationship to every other, elevated from the pattern ADR-0022 and ADR-0023 each independently discovered), ADR-0026 (Organizational Knowledge Architecture & Learning Constitution — the permanent definition of Organizational Knowledge, the knowledge hierarchy and maturity model, promotion, retirement, confidence, and the explainability chain the CAP-085 Organizational Memory and future CAP-086 Learning Framework capabilities are constitutionally required to satisfy), and ADR-0028 (Learning Constitution — the permanent definition of Learning, Learned Knowledge, the four-level Knowledge Promotion Chain, Learning Validation, Lineage, Maturity, Confidence, Evolution, and Learning's relationship to Feature Engineering, Prediction, Optimization, and Organizational Intelligence, elevating and detailing the Learning principles ADR-0026 §Stage 11 first froze, ahead of the future CAP-086 Learning Framework capability it constitutionally governs).

**Introduces (CAP-083/084's full lifecycles post-date this ADR, see ADR-0022/ADR-0023; CAP-085–086 remain reserved, not yet built):**

- **CAP-083 — Continuous Improvement** — Accepted, live (ADR-0022; CAP-083A architecture freeze → CAP-083B deterministic engine → CAP-083B.1 runtime contract freeze → CAP-083C runtime integration). The first Layer 2 capability to complete its lifecycle.
- **CAP-084 — Knowledge Graph** — Accepted, live (ADR-0023; CAP-084A architecture & governance freeze → CAP-084B deterministic engine → CAP-084B.1 runtime contract freeze → CAP-084C runtime integration). The second Layer 2 capability to complete its lifecycle, mirroring CAP-083's own.
- **CAP-085 — Organizational Memory** — Accepted, live (ADR-0027; CAP-085A architecture & governance freeze → CAP-085A.1 engine architecture refinement → CAP-085B deterministic engine → CAP-085B.1 runtime contract freeze → CAP-085C runtime integration). The third Layer 2 capability to complete its lifecycle, and the first to exercise ADR-0025's fan-in exception in the live pipeline — a consumer of both Continuous Improvement's and Knowledge Graph's completed results, active immediately after Knowledge Graph, at the permanently frozen end of the live pipeline.
- **CAP-086 — Learning Framework** — Accepted, live (ADR-0029; CAP-086A architecture & governance freeze → CAP-086A.1 engine architecture refinement & governance freeze → CAP-086A.2 decision governance & deterministic execution constitution → CAP-086B deterministic engine implemented behind the frozen contracts → CAP-086B.1 runtime contract freeze → CAP-086C runtime integration). The fourth and final Layer 2 capability to complete its lifecycle, mirroring CAP-083/084/085's own — and the first Layer 2 capability to consume exactly one already-completed Layer 2 tier rather than a Historical Dataset reference or a two-peer fan-in; active immediately after Organizational Memory, at the permanently frozen end of the live pipeline. **Layer 2 is now fully operational end to end** — Continuous Improvement, Knowledge Graph, Organizational Memory, and Learning all execute live, in their permanently frozen order.

**Purpose:** Historical Intelligence — reasoning over **many** completed Layer 1 executions, never a single one in isolation.

**Why this layer exists.** Every Layer 1 capability answers a question about one execution. None of them answers "has grounding gotten better or worse over the last twenty runs of this module?", "which requirement patterns keep getting flagged by Quality Governance?", or "what did the organization learn the last time this kind of gap was recommended?" Those are historical questions — they require a corpus of completed `RecommendationResult` / `QualityGovernanceResult` / `GroundingResult` objects, not a single one. Building that reasoning *inside* a Layer 1 capability would make a single-execution judge also an owner of cross-execution history — exactly the coupling ADR-0001 forbids within Layer 1, now forbidden across layers too (Stage 5).

**Why Feature Engineering must not bypass it.** Layer 3 (Feature Engineering) needs stable, reusable numerical representations — and a representation is only reusable if it is built from a durable historical record, not recomputed ad hoc from whatever Layer 1 executions happen to be lying around. If Feature Engineering read raw Layer 1 results directly, every feature engine would re-implement its own historical aggregation, the aggregation would drift between engines, and there would be no single place to audit "where did this feature's history come from?" Layer 2 is that single place: it owns the corpus, the trends, and the organizational memory *once*, so every higher layer inherits one consistent, explainable history instead of reconstructing its own.

### Layer 2.5 — Executable Specification Engineering

**Amendment note (additive only, ADR-0030).** This layer entry was added by ADR-0030 (CAP-087A — Executable Specification Engineering Architecture & Governance Freeze). It does not renumber, redefine, or reorder Layer 1, Layer 2, or Layer 3, or any layer above them; it names a position ADR-0020's original seven-question placement tree (Stage 9) never anticipated — see ADR-0030 Stage 0 and D1 for the full placement analysis. No other line in this document, and no existing runtime contract, was changed by this amendment.

**Constitutional foundation:** ADR-0028 (Learning Constitution — Recommendation 19's "Learning is the sole sanctioned bridge from Layer 2 to Layer 3," the rule this layer's own Layer 2 dependency is defined against), ADR-0018/ADR-0016/the Validation architecture/ADR-0019 (the four same-execution Layer 1 contracts this layer consumes), and ADR-0030 (Executable Specification Engineering Architecture & Governance Freeze — the full architectural definition of this layer).

**Introduces:** CAP-087 — Executable Specification Engineering — Proposed (ADR-0030; CAP-087A architecture & governance freeze only; no engine, no runtime contract certification, no runtime integration yet — those remain reserved future milestones, CAP-087B onward).

**Purpose:** Specification Production — transforming one execution's already-judged Layer 1 output, enriched by Layer 2's institutionalized organizational Learning, into a technology-independent, executable Specification Model. Neither Layer 1 nor Layer 2 produces anything a rendering tool or reviewer can act on directly; this layer is the platform's first to do so.

**Runtime contract:** `SpecificationEngineeringResult` (reserved, dormant — ADR-0030 §D3 names it the platform's first instance of a fifth, distinct kind of truth, **Specification Truth**: neither Runtime Truth, Historical Truth, Derived Knowledge, Organizational Knowledge, nor Learned Knowledge).

**Why this layer exists, and why it is not Layer 3.** Layer 3's `FeatureResult` is a numerical representation (§Layer 3, below); this layer's output is a qualitative, structured specification graph, and computes no number that estimates, scores, or predicts anything. Placing specification production inside Layer 3 would have required redefining Layer 3's own frozen purpose — forbidden. Placing it inside Layer 1 is impossible under Stage 5's own upward-only dependency rule, because it must consume `LearningResult` (Layer 2's own terminal output). Layer 2.5 is therefore the smallest position that satisfies both constraints: higher than Layer 2 (so it may consume Learning), not Layer 3 (so Layer 3's own definition stays untouched).

**Dependency boundary.** Layer 2.5 consumes exactly five already-frozen runtime contracts — `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `RecommendationResult` (same-execution Layer 1 peers) and `LearningResult` (the sole Layer 2 bridge, per ADR-0028 Recommendation 19) — and nothing else. It never reaches past `LearningResult` into `ContinuousImprovementResult`, `KnowledgeGraphResult`, or `OrganizationalMemoryResult` directly (the identical no-skip discipline Stage 5 already freezes for every other layer boundary). Nothing above Layer 2.5 exists yet; a future Layer 3+ capability that needs a specification-tier conclusion must reach it through `SpecificationEngineeringResult` alone, never past it.

**Boundary.** Executable Specification Engineering produces specifications; it never generates executable test code, step definitions, or test data, never executes a test, and never calls an external system (ADR-0030 D5). Full architecture: ADR-0030 and `docs/proposals/executable-specification-engineering.md`.

### Layer 3 — Feature Engineering

**Purpose:** Transform deterministic runtime contracts (Layer 1's completed results, and Layer 2's historical aggregates) into reusable, numerical feature vectors.

**Runtime contract:** `FeatureResult`.

**Examples:**

- Requirement Complexity
- Grounding Stability
- Recommendation Density
- Governance Stability
- Validation Stability
- Historical Trend Features

**Boundary.** Feature Engineering constructs features. It predicts nothing. A `FeatureResult` is explainable entirely from the Layer 1 / Layer 2 contracts it was built from — it never invents a value that cannot be traced to one of them.

### Layer 4 — Prediction & Insights

**Purpose:** Prediction — estimating future outcomes from Layer 3's feature vectors.

**Runtime contract:** `PredictionResult`.

**Examples:**

- Risk
- Schedule
- Architecture
- Security
- Regression
- Delivery

**Boundary.** Explainability is mandatory: every `PredictionResult` must name the `FeatureResult` inputs (and, transitively, the Layer 1/2 contracts) it was derived from. A prediction with no traceable feature basis is not constructible — the same explainability discipline ADR-0019 §D7 established for `Recommendation`, now a platform-wide rule (Stage 7).

### Layer 5 — Optimization

**Purpose:** Engineering optimization — choosing the best plan given Layer 4's predictions.

**Runtime contract:** `OptimizationResult`.

**Examples:**

- Sprint optimization
- Backlog optimization
- Release optimization
- Dependency optimization
- Developer allocation

**Boundary.** Optimization chooses; it does not execute. No `OptimizationResult` ever performs an action — that is Layer 6's exclusive responsibility.

### Layer 6 — Autonomous Engineering

**Purpose:** Governed execution — carrying out engineering work Layer 5 selected.

**Runtime contract:** `ExecutionActionResult`.

**Examples:**

- Story generation
- Requirement refinement
- Automation generation
- Documentation updates
- PR preparation
- Architecture proposals

**Boundary.** Every action produced here must be **auditable**, **governed**, and **reversible** — the same non-negotiable triad Quality Governance and Recommendation already apply to a single execution's judgement, now applied to an autonomous action taken on the strength of everything below it.

### Layer 7 — Organizational Intelligence

**Purpose:** Cross-project intelligence — reasoning across the organization's entire portfolio of platform-governed projects.

**Runtime contract:** `OrganizationResult`.

**Examples:**

- Portfolio health
- Engineering maturity
- Architecture evolution
- Capability benchmarking
- Technology trends
- Strategic recommendations

**Boundary.** Layer 7 is the **final consumer** of the platform (Recommendation 10). Nothing depends on it; it depends on every layer below it, aggregated across projects rather than within one.

---

## Stage 5 — Dependency rules (frozen)

```
Layer N
    ↓
Layer N+1
```

- Dependencies flow **upward only** — a higher-numbered layer may consume a lower-numbered layer's completed runtime contracts.
- **Never downward** — no lower layer may import, invoke, or depend on any higher layer, under any circumstance.
- **Never circular** — no layer may depend on a layer that (directly or transitively) depends on it.
- **Never skip layers** — Layer 4 consumes Layer 3's `FeatureResult`, never Layer 1's raw results directly; Layer 6 consumes Layer 5's `OptimizationResult`, never Layer 4's `PredictionResult` directly. Each layer's contract is the *only* sanctioned entry point into it (Stage 6).

This is the same one-way discipline every Layer 1 ADR already froze for its own subsystem (ADR-0016 §D8, ADR-0017 §D30/D31, ADR-0018 §D9, ADR-0019 §D9/§D10) — Recommendation 6 lifts it from "within one layer" to "across every layer."

---

## Stage 6 — Runtime contract principle (frozen)

Every capability, in every layer, owns exactly:

- its **runtime contract** (the single object that crosses out of it — a `*Result`),
- its **policy** (governed, immutable configuration),
- its **engine** (the deterministic-first implementation behind its runtime contract),
- its **orchestration** (the thin service that sequences its engine and nothing else),
- its **execution package** (or projection layer) that renders its runtime contract into durable artifacts.

Nothing else. A capability does not own another capability's contract, policy, engine, orchestration, or projection — and a higher layer never reaches past a capability's runtime contract to touch any of those four internals directly. The runtime contract is the *only* cross-layer (and cross-capability) integration mechanism (Recommendation 3).

---

## Stage 7 — Explainability principle (frozen)

Every higher-layer output must be explainable **solely** from the lower-layer runtime contracts it consumed.

- No hidden inference — a `PredictionResult`, `OptimizationResult`, or `ExecutionActionResult` may never depend on state that is not itself a named, versioned, lower-layer contract.
- No opaque reasoning — the chain from a Layer 7 `OrganizationResult` back down to the Layer 1 `RecommendationResult`s it ultimately aggregates must be traceable at every hop, exactly as `Recommendation` traces back to an `EnhancementFinding` / `GroundingFinding` / `ValidationIssue` / `CP1Finding` / `QualityFinding` today (ADR-0019 §D7).
- No unexplained predictions — Layer 4 in particular must never produce a prediction that cannot name the Layer 3 features (and, transitively, the Layer 1/2 contracts) it was derived from.

This is the platform-wide generalization of Recommendation 7 (ADR-0019): "explainability first" was a subsystem rule; it is now a constitutional one.

---

## Stage 8 — Capability lifecycle (frozen)

Every capability, in every layer, present or future, must progress through the same seven stages, in the same order, skipping none:

```
Architecture Freeze
    ↓
Deterministic Implementation
    ↓
Runtime Contract Freeze
    ↓
Runtime Integration
    ↓
Execution Package Integration
    ↓
Golden Rebaseline
    ↓
Architecture Certification
```

This is not a new invention — it is the lifecycle every Layer 1 capability already walked, named explicitly for the first time:

| Stage | Quality Governance | Requirement Enhancement | Recommendation |
|---|---|---|---|
| Architecture Freeze | ADR-0017 (CAP-080A) | ADR-0018 (CAP-081A) | ADR-0019 (CAP-082A) |
| Deterministic Implementation | CAP-080B | CAP-081B | CAP-082B |
| Runtime Contract Freeze | CAP-080B.1.1 | CAP-081B.1 | CAP-082B.1 |
| Runtime Integration | CAP-080D | CAP-081C | CAP-082C |
| Execution Package Integration | CAP-080D | CAP-081C | CAP-082C |
| Golden Rebaseline | (CAP-080D) | (CAP-081C) | (CAP-082C, `1.3.0`→`1.4.0`) |
| Architecture Certification | this ADR's Stage 0 review | this ADR's Stage 0 review | this ADR's Stage 0 review |

No capability skips a stage, and no capability may reorder them — a runtime cannot be integrated before its contract is frozen, and a contract cannot be frozen before a deterministic implementation exists to freeze it against.

---

## Stage 9 — Architectural decision tree

A placement guide for every future capability (CAP), answered in order — the first "yes" names the layer:

```
Does this capability reason over one execution?
    → Layer 1: Requirement Intelligence

Does it reason over many executions?
    → Layer 2: Continuous Learning

Does it transform judged execution output (Layer 1), enriched by Learning (Layer 2), into a technology-independent, executable specification?
    → Layer 2.5: Executable Specification Engineering

Does it produce reusable numerical representations?
    → Layer 3: Feature Engineering

Does it estimate future outcomes?
    → Layer 4: Prediction & Insights

Does it choose the best plan?
    → Layer 5: Optimization

Does it perform engineering work?
    → Layer 6: Autonomous Engineering

Does it reason across organizations?
    → Layer 7: Organizational Intelligence
```

A capability that answers "yes" to more than one question has not yet been decomposed correctly (Stage 3) — split it until each piece answers exactly one question, and place each piece in its own layer.

**Amendment note (additive only, ADR-0030).** The Layer 2.5 question above was added by ADR-0030. It occupies the tree's existing order (immediately after the Layer 2 question, immediately before the Layer 3 question) without reordering, rewording, or renumbering any other question.

---

## Stage 10 — Platform evolution diagram

```
Layer 7
Organizational Intelligence
                ▲
Layer 6
Autonomous Engineering
                ▲
Layer 5
Optimization
                ▲
Layer 4
Prediction & Insights
                ▲
Layer 3
Feature Engineering
                ▲
Layer 2.5
Executable Specification Engineering
    └── CAP-087 Executable Specification Engineering (Proposed, CAP-087A architecture only)
                ▲
Layer 2
Continuous Learning
    ├── CAP-083 Continuous Improvement
    ├── CAP-084 Knowledge Graph
    ├── CAP-085 Organizational Memory
    └── CAP-086 Learning Framework
                ▲
Layer 1
Requirement Intelligence
    ├── Engineering Context
    ├── Analysis
    ├── Enhancement
    ├── Grounding
    ├── Validation
    ├── CP1
    ├── Quality Governance
    ├── Recommendation
    └── Execution Package
```

---

## Stage 11 — Long-term vision

This roadmap intentionally places Machine Learning, LLMs, Prediction, Optimization, and Autonomous Engineering **after** deterministic, governed reasoning — never before it, and never as a substitute for it.

The platform philosophy, in order:

```
Governance
    ↓
Determinism
    ↓
Learning
    ↓
Prediction
    ↓
Optimization
    ↓
Autonomy
```

Never the reverse. A platform that predicted before it could deterministically judge, or acted autonomously before it could explain a single recommendation, would have built its most consequential capabilities on its least trustworthy foundation. Every layer above Layer 1 exists only because Layer 1 first proved that a judgement can be governed, deterministic, and fully explainable — and every layer from here forward is required to prove the same thing before the next one is allowed to depend on it.

---

## Stage 12 — Recommendations (permanent, platform-wide)

### Recommendation 1 — Single layer membership

Every capability belongs to exactly one architectural layer.

### Recommendation 2 — Upward consumption only

Higher layers consume lower layers only.

### Recommendation 3 — Runtime contracts are the sole integration mechanism

Runtime contracts are the only cross-layer integration mechanism.

### Recommendation 4 — One lifecycle

Every capability follows the identical lifecycle (Stage 8).

### Recommendation 5 — Governance precedes intelligence

Governance precedes intelligence.

### Recommendation 6 — Learning precedes features

Historical learning precedes feature engineering.

### Recommendation 7 — Features precede prediction

Feature engineering precedes prediction.

### Recommendation 8 — Prediction precedes optimization

Prediction precedes optimization.

### Recommendation 9 — Optimization precedes autonomy

Optimization precedes autonomous engineering.

### Recommendation 10 — Organizational intelligence is terminal

Organizational intelligence is the final consumer of the platform.

---

## Ownership, scope, and governance

- **Owns:** the platform's layer definitions, cross-layer dependency rules, the capability lifecycle, and the architectural placement guide.
- **Does not own:** any subsystem's runtime contract, policy, engine, orchestration, or execution package — those remain owned exactly where ADR-0011 through ADR-0019 (and every future subsystem ADR) already place them.
- **Governance:** registered as the platform's architectural constitution. **Proposed** — it names a structure every prior ADR already followed informally and asks that every future one follow it explicitly; it becomes **Accepted** as future capabilities (starting with CAP-083) are placed and built under it without deviation.
