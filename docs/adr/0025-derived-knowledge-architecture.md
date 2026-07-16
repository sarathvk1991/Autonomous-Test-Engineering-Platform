# ADR-0025 — Derived Knowledge Architecture & Layer 2 Constitution

- **Status:** Proposed
- **Date:** 2026-07-16
- **Supersedes:** nothing. **Amends:** nothing. **Elevates:** the Derived Knowledge definition ADR-0021 §Stage 3 introduced in one short paragraph, into a full constitutional document — mirroring how ADR-0024 elevated Historical Truth from the same section of the same ADR. Every principle ADR-0022 and ADR-0023 each independently restated about `ContinuousImprovementResult` and `KnowledgeGraphResult` being Derived Knowledge is generalized here, once, as the platform-wide constitution every third and later Layer 2 capability inherits by citation.
- **Governing design:** none — this ADR *is* the governing design, exactly as ADR-0020, ADR-0021, and ADR-0024 introduce no proposal document because none of them is subsystem architecture.
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — defines the seven layers and Layer 2's membership), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — defines the three-level Truth Hierarchy this ADR extends), ADR-0024 (Historical Dataset & Historical Truth Constitution — the sibling constitutional document this ADR completes the trio alongside). Informed by ADR-0022 (Continuous Improvement Framework) and ADR-0023 (Knowledge Graph Framework) — the two existing Derived Knowledge producers whose independently-reached, converging design choices this ADR generalizes into constitution, exactly as ADR-0024 generalized their converging Historical Dataset Resolution Principle.
- **Runtime status:** Not applicable. This is a **documentation-only constitutional milestone**: no runtime behaviour, no implementation, no models, no runtime contracts, no `PlatformContext` changes, no policies, no services, no serializers, no Execution Package changes, no manifest changes, no CLI changes, and no version bumps (Architecture, Platform, or otherwise). It permanently defines what Derived Knowledge is, who may produce it, how it evolves, how Layer 2 capabilities relate to one another, and how every future Layer 2+ capability must be built — it does not build any part of that definition.

## Scope note

ADR-0020 defines **platform evolution** — the seven layers and their dependency direction. ADR-0021 defines **data evolution across time** — the three-level Truth Hierarchy (Runtime Truth → Historical Truth → Derived Knowledge) and the permanent rule that these three never collapse into one. ADR-0024 completed the middle tier: a full constitution for Historical Truth and the Historical Dataset that owns it. This ADR completes the top tier of that same hierarchy: a full constitution for **Derived Knowledge** — the entire output of Layer 2 and every layer above it — and, because Layer 2 is the first layer to produce it, a constitution for how Layer 2's own capabilities relate to one another as peers. Together, ADR-0020, ADR-0021, ADR-0024, and ADR-0025 are the four constitutional documents governing every future platform capability from Layer 2 onward: ADR-0020 answers "where does this capability live?"; ADR-0021 answers "what kind of truth is this capability allowed to touch?"; ADR-0024 answers "how is Historical Truth organized and resolved?"; ADR-0025 answers "what is this capability allowed to *produce*, and how must it relate to its peers?"

This is **not** a subsystem ADR. It defines no `requirement_intelligence/` package, no `PlatformContext` method, no policy, no model, no service. It is a constitutional document, exactly like ADR-0020, ADR-0021, and ADR-0024.

---

## Stage 0 — Repository assessment

Before writing this ADR, the following were reviewed:

- **ADR-0020** (§Stage 4, Layer 2): names Continuous Learning as Layer 2, lists all four reserved capabilities (CAP-083 Continuous Improvement, CAP-084 Knowledge Graph, CAP-085 Organizational Memory, CAP-086 Learning Framework), and already cites ADR-0021/ADR-0024 as Layer 2's constitutional foundation. It does not yet name a constitutional foundation for what Layer 2 (and every layer above it) actually *produces*.
- **ADR-0021** (§Stage 3): defines the three-level Truth Hierarchy and gives Derived Knowledge a short, one-paragraph definition — "derived, reproducible, explainable, never canonical history," produced by Layers 2 through 7. This is correct and unchanged by this ADR; it has simply never been given the full ownership/immutability/evolution/lifecycle/replaceability treatment ADR-0024 gave Historical Truth from the same source paragraph.
- **ADR-0022** (§D3, §D10, §D11, Recommendation 11): `ContinuousImprovementResult` is independently confirmed as Derived Knowledge — reproducible from `HistoricalDatasetReference`, never itself canonical history, never recursively consuming a prior `ContinuousImprovementResult`.
- **ADR-0023** (§D3, §D11, §D12, Recommendation 11/17): `KnowledgeGraphResult` is independently confirmed as Derived Knowledge — the identical set of properties, independently re-derived rather than imported, exactly as ADR-0024 Stage 0 already found for the Historical Dataset Resolution Principle.
- **ADR-0024**: confirms Historical Truth is already fully, constitutionally frozen (Stage 2–9) — immutable, append-only, execution-derived, replayable, versioned, explainable, storage-independent — with the Historical Dataset as its sole owner. Derived Knowledge's own constitution has no equivalent document.

**Confirmed:**

- **Continuous Improvement and Knowledge Graph both produce Derived Knowledge.** Neither is Historical Truth, neither is Runtime Truth, and neither has ever been mistaken for, stored as, or promoted to either (ADR-0022 §D3, ADR-0023 §D3).
- **Historical Truth is already constitutionally frozen** — ADR-0021 §Stage 5 and the entirety of ADR-0024. This ADR depends on, and never restates, that freeze.
- **Derived Knowledge has no constitutional definition of its own yet** — only ADR-0021 §Stage 3's originating paragraph, restated independently (never contradicted, but never generalized) by ADR-0022 and ADR-0023 each on their own terms.

**Duplication found (expected, not a defect):** ADR-0022's and ADR-0023's own "Derived Knowledge principle" passages (ADR-0022 §D10, ADR-0023 §D11) are near-identical prose, independently written, exactly the same pattern ADR-0024 Stage 0 found and resolved for the Historical Dataset Resolution Principle. This is the direct motivation for this ADR: elevate the converged answer once, so a third Layer 2 capability inherits it by citation instead of writing a third near-identical paragraph.

**Contradiction found and resolved (not a blocking inconsistency):** A literal, single-line dependency chain running `Continuous Improvement → Knowledge Graph → Organizational Memory → Learning Framework` — the shape a first draft of this ADR's own Stage 8 might suggest — would contradict ADR-0022 Recommendation 1/9 and ADR-0023 Recommendation 1/9, both of which freeze Continuous Improvement and Knowledge Graph as **peers that never consume one another**, and would contradict this same ADR's own Stage 7 (below). The two are reconcilable, and Stage 8 below freezes the reconciled shape: Continuous Improvement and Knowledge Graph both consume Historical Truth **directly and independently** (a fan-out, not a chain), and a future Organizational Memory is the **fan-in point** that may consume both — never the reverse, and never a pairwise dependency between the two peers themselves. This is stated explicitly here, rather than silently resolved, so the reconciliation is itself part of the permanent record.

**No other inconsistency or overlapping ownership was found.** CAP-085 (Organizational Memory) and CAP-086 (Learning Framework) have no ADR yet — this document is free to freeze their relationship to CAP-083/084 and to Layer 3 without amending or contradicting anything already built.

> No blocking inconsistency found; one apparent tension was identified and resolved within this document itself (Stage 8). Proceeding with a pure constitutional freeze.

---

## Stage 1 — Define Derived Knowledge

Permanently defined, restating and detailing ADR-0021 §Stage 3:

**Derived Knowledge is:**

- **deterministic** — the same Historical Truth, reasoned over by the same governed engine and policy, always produces the same Derived Knowledge;
- **reproducible** — regenerable at any time from the Historical Truth it was computed from, with no dependence on when it was first computed;
- **immutable** — once produced, never modified (Stage 4);
- **explainable** — every conclusion traces back to the specific Historical Truth entries it was computed from (Stage 5);
- **computed exclusively from Historical Truth** — the sole permitted input to the act of *producing* Derived Knowledge (Stage 3).

**Derived Knowledge is never:**

- computed from **Runtime Truth directly** — a Layer 2 engine consumes a `HistoricalDatasetReference`, never a Layer 1 runtime contract embedded directly (ADR-0021 §Stage 6, ADR-0022 §D2, ADR-0023 §D2);
- computed from **another Derived Knowledge object** — no engine may consume a prior `ContinuousImprovementResult`, a prior `KnowledgeGraphResult`, or any future Layer 2+ Derived Knowledge contract as an input to producing new Derived Knowledge (Recommendation 2 below; this is the platform-wide generalization of ADR-0021 Recommendation 11, ADR-0022 Recommendation 11, and ADR-0023 Recommendation 11/17);
- **Historical Truth itself** — Derived Knowledge is never written back into the Historical Dataset (Stage 2);
- **Runtime Truth itself** — Derived Knowledge never substitutes for, edits, or is mistaken for a Layer 1 runtime contract.

This is not a new rule — `ContinuousImprovementResult` and `KnowledgeGraphResult` already satisfy every clause of this definition today. This stage names, once, the definition both independently satisfy.

---

## Stage 2 — Truth Hierarchy extension

Extends ADR-0021 §Stage 3 by re-freezing, permanently:

```
Runtime Truth
        ↓
Historical Truth
        ↓
Derived Knowledge
```

**Derived Knowledge never becomes Historical Truth.** A trend, a finding, a structural observation, or any future Layer 2+ conclusion is never appended to the Historical Dataset as if it were a completed execution.

**Historical Truth never becomes Derived Knowledge.** Historical Truth is never relabelled, reclassified, or "promoted" into a Derived Knowledge contract without an actual, governed act of derivation — the direction of the arrow is a computation, not a status change.

**The direction is permanent.** Neither arrow ever reverses, and the three levels are never merged into one model, one store, or one contract (ADR-0021 §Stage 3). This is the platform's single most load-bearing invariant: every Layer 2–7 capability's trustworthiness depends on the guarantee that its own output can never quietly become the history the next capability treats as ground truth.

---

## Stage 3 — Ownership

Freeze ownership.

**Only Layer 2 may create Derived Knowledge.** Every Layer 2 capability (Continuous Improvement, Knowledge Graph, and every future Layer 2 capability) is a producer; nothing below Layer 2 produces Derived Knowledge, and nothing above Layer 2 produces it *from scratch* — Layers 3–7 consume it and produce their own, later-tier knowledge (Stage 9), but the specific tier this ADR names "Derived Knowledge" is Layer 2's alone to originate.

**Layer 3 and above consume Derived Knowledge.** They never recreate it, never mutate it, and never compete with it. Consuming Derived Knowledge means reading a completed, frozen Layer 2 runtime contract (`ContinuousImprovementResult`, `KnowledgeGraphResult`, and their future peers) — never re-deriving the same conclusion by reaching back into Historical Truth a second time in parallel to Layer 2's own governed computation. A Layer 3 capability that recomputed "what repeats" from raw Historical Truth, duplicating Continuous Improvement's own responsibility, would violate this ownership rule exactly as ADR-0001 forbids duplicated ownership within a single layer (ADR-0020 §Stage 3).

**Layer 3's own, explicitly wider consumption right is unaffected.** ADR-0020 §Stage 4 (Layer 3) already permits Feature Engineering to transform "Layer 1's completed results, **and** Layer 2's historical aggregates" — Layer 3 may consume Runtime Truth (Layer 1) directly for its own feature-construction purposes, because Layer 3 is the layer whose job is exactly that transformation. This does not contradict Derived Knowledge's own production rule (Stage 1: Derived Knowledge is computed exclusively from Historical Truth) — that rule constrains how *Layer 2* produces Derived Knowledge, not how *Layer 3* consumes multiple lower layers. Layer 4 and above, by contrast, must never skip Layer 3 to reach Layer 1 or Layer 2 directly (ADR-0020 §Stage 5) — the "never skip layers" rule applies from Layer 4 upward, exactly as ADR-0020 §Stage 5 already states.

---

## Stage 4 — Immutability

Freeze permanently.

**Every Derived Knowledge contract is immutable.** `ContinuousImprovementResult`, `KnowledgeGraphResult`, a future `OrganizationalMemoryResult`, a future `LearningResult`, and every Derived Knowledge contract not yet named: once produced, **never modified**.

**Only superseded, never patched.** A correction, an update, or a re-observation over more recent Historical Truth is a **new** Derived Knowledge object with its own identity — never an in-place edit of the old one. The old object remains exactly as it was, an accurate record of what was concluded from the Historical Truth available at the time it was produced (mirrors ADR-0021 §Stage 4's execution-immutability principle, and ADR-0021 §Stage 5's append-only Historical Truth principle, lifted one tier up).

---

## Stage 5 — Explainability

Freeze permanently.

**Every Derived Knowledge artifact must be explainable entirely from Historical Truth.** No hidden inference, no opaque state, no external memory. A conclusion that cannot name which Historical Truth entries produced it is not explainable and must not be constructible — the same "at least one reference" discipline ADR-0019 §D7 froze for a single `Recommendation`, ADR-0021 §Stage 8 required end-to-end across the historical chain, and ADR-0022 §D7 / ADR-0023 §D7 each already enforce as a model invariant.

**The chain is always two hops, never more, never fewer:**

```
Derived Knowledge
        ↓
Historical Truth
        ↓
Runtime Truth
```

Every conclusion traces back to Historical Truth; Historical Truth itself traces back to Runtime Truth (ADR-0024 Stage 9). A Derived Knowledge artifact is never explainable by re-running its own engine, inspecting a provider, or consulting `PlatformContext` — the artifact alone must suffice (ADR-0022 §D10/§D11, ADR-0023 §D11/§D12).

---

## Stage 6 — Knowledge evolution

Freeze permanently.

**Knowledge evolves by producing new Derived Knowledge.** Never by editing existing Derived Knowledge.

- **No patching** — an existing `ContinuousImprovementResult` or `KnowledgeGraphResult` is never partially updated in place.
- **No merging** — two Derived Knowledge objects are never combined into a third that silently absorbs and discards their individual identities; an aggregation (Organizational Memory, Stage 8) is itself a **new** Derived Knowledge object that *references* the objects it aggregated, never one that erases them.
- **No mutation** — no field of a previously-produced Derived Knowledge contract is ever changed after construction (restates Stage 4 at the level of platform behaviour rather than object shape).

This is the same discipline Stage 4 freezes for one object's own immutability, restated here as the platform's evolution mechanism: the *system* gets smarter by accumulating more, newer, better Derived Knowledge — never by making any single piece of Derived Knowledge retroactively different from what it was.

---

## Stage 7 — Layer independence

Freeze permanently.

**Layer 2 capabilities are peers.** Continuous Improvement never consumes Knowledge Graph. Knowledge Graph never consumes Continuous Improvement (ADR-0022 Recommendation 1/9, ADR-0023 Recommendation 1/9, ADR-0023 §D3: "two Layer 2 capabilities sitting at the same Truth Hierarchy level do not consume one another's output without a deliberate, explicitly-declared future ADR — none exists today"). This ADR does not introduce that deliberate future ADR; the peer boundary remains exactly as strict as ADR-0022 and ADR-0023 already froze it.

**Future Organizational Memory (CAP-085) may consume both.** It is not a peer of Continuous Improvement or Knowledge Graph — it is a distinct, later capability whose entire purpose is answering a question neither peer answers alone ("what should be remembered?", Recommendation 15 below), and doing so requires reading both of their completed runtime contracts. Consuming both is not "peer coupling" — Organizational Memory is downstream of both, not beside either.

**Future Learning Framework (CAP-086) may consume Organizational Memory.** It must not skip past Organizational Memory to consume Continuous Improvement or Knowledge Graph directly — the same no-skip discipline ADR-0020 §Stage 5 freezes between numbered layers, applied here to the internal sequence of capabilities *within* Layer 2 (Stage 8).

**No peer coupling.** Two Layer 2 capabilities that both answer a question over the same Historical Truth remain structurally independent of one another (Recommendation 15: Layer 2 Completeness) — neither may import, invoke, or depend on the other's engine, service, policy, or runtime contract.

---

## Stage 8 — Dependency graph

Freeze permanently. Resolving the Stage 0 tension explicitly: this is a **fan-in graph**, not a linear chain. Continuous Improvement and Knowledge Graph both branch directly off Historical Truth, independently; Organizational Memory is the point where those two branches converge.

```
Runtime Truth
        ↓
Historical Truth
        ↓
    ┌───┴────────────┐
Continuous       Knowledge
Improvement        Graph
    └───┬────────────┘
        ↓
Organizational Memory
        ↓
Learning Framework
        ↓
Feature Engineering
        ↓
Prediction
        ↓
Optimization
        ↓
Autonomous Decisions
```

**Reading this graph:**

- Historical Truth has exactly two direct Layer 2 consumers today (Continuous Improvement, Knowledge Graph) — a fan-out, not a single path. A future third Layer 2 capability that also consumes Historical Truth directly, and is also a peer of these two (never consuming or being consumed by them), joins this same fan-out level.
- Organizational Memory is the fan-in: the first capability permitted to consume more than one Layer 2 peer's output. It is not itself a peer of Continuous Improvement or Knowledge Graph — it is their shared, later consumer (Stage 7).
- Learning Framework consumes Organizational Memory only — never skipping to Continuous Improvement or Knowledge Graph directly.
- From Feature Engineering downward, this graph is exactly ADR-0020 §Stage 5's already-frozen inter-layer dependency chain: each layer consumes the frozen runtime contract of the layer immediately below it, never skipping, never reversing.

**Every dependency moves downward only.** No reverse dependency — nothing earlier in this graph ever imports, invokes, or depends on anything later in it. **No (unauthorized) peer dependency** — the only cross-branch edges are the two explicit fan-in arrows into Organizational Memory; Continuous Improvement and Knowledge Graph never directly reference one another. **No skip-layer, and no skip-capability, dependency** — Learning Framework cannot reach past Organizational Memory, exactly as Layer 4 cannot reach past Layer 3 (ADR-0020 §Stage 5).

---

## Stage 9 — Knowledge lifecycle

Freeze permanently. Every unit of knowledge in the platform progresses through exactly this permanent lifecycle — the data-lifecycle analogue of ADR-0020 §Stage 8's capability lifecycle:

```
Runtime Truth
        ↓
Historical Truth
        ↓
Derived Knowledge
        ↓
Aggregated Knowledge
        ↓
Learned Knowledge
        ↓
Engineered Features
        ↓
Predictions
        ↓
Optimizations
        ↓
Autonomous Decisions
```

**Mapped to layers and capabilities:**

| Stage | Owner | Layer |
|---|---|---|
| Runtime Truth | Layer 1 capabilities | Layer 1 |
| Historical Truth | Historical Dataset (ADR-0024) | Layer 2 (organizing) |
| Derived Knowledge | Continuous Improvement, Knowledge Graph | Layer 2 |
| Aggregated Knowledge | Organizational Memory (CAP-085, reserved) | Layer 2 |
| Learned Knowledge | Learning Framework (CAP-086, reserved) | Layer 2 |
| Engineered Features | Feature Engineering | Layer 3 |
| Predictions | Prediction & Insights | Layer 4 |
| Optimizations | Optimization | Layer 5 |
| Autonomous Decisions | Autonomous Engineering | Layer 6 |

No stage is skipped, and no stage is reordered — the same discipline ADR-0021 §Stage 12 already froze for data moving through Execution → Historical Dataset → Continuous Learning → Feature Engineering → …, extended here with the two intermediate Layer 2 stages (Aggregated Knowledge, Learned Knowledge) this ADR names for the first time. Layer 7 (Organizational Intelligence) is not a stage of *this* per-project lifecycle — it is the cross-project aggregation of many completed instances of this lifecycle, one per platform-governed project (ADR-0020 §Stage 4, Layer 7).

---

## Stage 10 — Replaceability

Freeze permanently.

**Every Layer 2 implementation must be replaceable.** Deterministic, statistical, ML, LLM, Graph Neural Network, and Graph RAG engines — present and future — must all reuse **identical runtime contracts**. A future statistical Continuous Improvement engine, a future LLM-based Knowledge Graph reasoning engine, or a future ML-based Organizational Memory engine must each implement the same frozen `*Service` signature and emit the same frozen `*Result` contract shape their deterministic predecessor already established (ADR-0022 Recommendation 5, ADR-0023 Recommendation 5/7, generalized here platform-wide for every current and future Layer 2 capability).

**Consequence.** No consumer of a Layer 2 runtime contract — not Organizational Memory, not Learning Framework, not Layer 3 Feature Engineering, not any future layer — may ever depend on *which kind* of engine produced the Derived Knowledge it consumes. Engine replaceability is invisible above the runtime contract boundary, by construction.

---

## Stage 11 — Derived Knowledge principles

Freeze permanently.

### Recommendation 1 — Derived Knowledge never mutates Historical Truth

No Layer 2+ capability writes back into the Historical Dataset. The Historical Dataset is append-only from completed executions alone (ADR-0024 Stage 3/8).

### Recommendation 2 — Derived Knowledge never becomes Runtime Truth

A trend, a finding, a structural observation, or any future conclusion is never mistaken for, stored as, or substituted for a Layer 1 runtime contract.

### Recommendation 3 — Derived Knowledge must always be reproducible

The same Historical Truth, reasoned over by the same governed engine and policy, always produces the same Derived Knowledge (Stage 1).

### Recommendation 4 — Historical Truth remains the sole evidence authority

Derived Knowledge is computed exclusively from Historical Truth (Stage 1, Stage 3) — never from Runtime Truth directly, and never from another Derived Knowledge object.

### Recommendation 5 — No capability owns another capability's knowledge

Continuous Improvement does not own Knowledge Graph's structural conclusions; Knowledge Graph does not own Continuous Improvement's recurrence conclusions; Organizational Memory does not own either's underlying computation, only its own aggregation (Stage 7).

### Recommendation 6 — Layer 3 consumes Layer 2

Feature Engineering consumes Layer 2's frozen runtime contracts (and, where ADR-0020 §Stage 4 explicitly permits, Layer 1's) — it never reaches past Layer 2 to reconstruct what Layer 2 already computed (Stage 3).

### Recommendation 7 — Feature Engineering never recomputes Layer 2

A feature that duplicates Continuous Improvement's recurrence detection, or Knowledge Graph's structural analysis, inside a Layer 3 engine violates Recommendation 5 and Recommendation 6 simultaneously — Layer 3 transforms Layer 2's output into features; it does not re-derive Layer 2's own conclusions independently.

### Recommendation 8 — Predictions never become evidence

A `PredictionResult` (Layer 4) is Derived Knowledge's descendant, not Historical Truth's peer. It is never appended to the Historical Dataset, never treated as a Runtime Truth input to a future execution, and never consumed by Layer 2 as if it were Historical Truth (Stage 2's one-way direction, extended to every later tier).

### Recommendation 9 — Knowledge storage is independent from computation

How a Derived Knowledge contract is eventually persisted, indexed, or queried (a future storage layer) is an implementation detail, never part of this contract — mirrors ADR-0024 Recommendation 5/12 (storage independence) and ADR-0023 Recommendation 5/12 (graph storage independence), generalized here for every Layer 2+ contract.

### Recommendation 10 — Explainability always precedes intelligence

No Layer 2+ capability may add probabilistic, statistical, ML, or LLM reasoning before its deterministic, explainable form exists and is frozen — the same discipline ADR-0020 §Stage 11 already freezes platform-wide (Governance → Determinism → Learning → Prediction → Optimization → Autonomy), restated here as it applies specifically to Derived Knowledge production.

### Recommendation 11 — Every decision must trace back to Runtime Truth

Any autonomous decision, optimization, or prediction — however many tiers of Derived Knowledge it passed through — must be traceable, hop by hop, all the way back to the Runtime Truth (Layer 1 execution) it ultimately originates from (Stage 5's two-hop chain, applied transitively across every tier in Stage 9's lifecycle).

### Recommendation 12 — Future AI implementations must preserve contracts

A future ML, LLM, GNN, or Graph RAG implementation of any Layer 2+ capability must implement the identical frozen runtime contract its deterministic predecessor established, changing no field, no signature, and no consumer-visible shape (Stage 10).

---

## Stage 12 — Cross references

`docs/adr/0020-platform-evolution-roadmap.md` §Layer 2 — Continuous Learning is updated to add ADR-0025 alongside its existing ADR-0021/ADR-0024 constitutional-foundation citation, naming it as the constitutional authority for Derived Knowledge and Layer 2 peer independence. No roadmap restructuring: the CAP-083/084/085/086 lifecycle lines and layer ordering are unchanged — this is a citation addition only.

`docs/adr/0022-continuous-improvement-framework.md` and `docs/adr/0023-knowledge-graph-framework.md` are each updated to add ADR-0025 to their **Depends on** line, and their respective "Derived Knowledge principle" passages (ADR-0022 §D10, ADR-0023 §D11) gain a one-sentence pointer to this ADR as the now-canonical, platform-wide source for the principle both already independently state. Neither ADR's own prose is deleted or restructured — both remain fully self-contained per-subsystem records; this ADR is additive precedent for the *next* Layer 2 capability, not a retroactive rewrite of the first two.

No behavioral changes. No roadmap restructuring.

---

## Stage 13 — Verification

This milestone is documentation only. Verified:

- zero runtime changes — no file under `requirement_intelligence/` was touched;
- zero model changes — no Pydantic model, dataclass, or contract was added or modified;
- zero policy changes — no `*Policy` class or governed default was touched;
- zero `PlatformContext` changes — `platform_context.py` was not touched;
- zero service changes — no `*Service` class was added or modified;
- zero serializer changes — no `serialization/` package was added or modified;
- zero Execution Package changes — `execution_data.py`, `execution_writer.py`, `manifest_builder.py` were not touched;
- zero golden changes — the golden dataset and its version are unchanged;
- zero version bumps — Architecture Version (`1.2.0`), Platform Version (`1.0.0`), and every existing runtime contract/policy/framework version are unchanged.

Ruff, the full repository test suite, productization, and golden verification were run after this change; all pass, and the repository remains byte-identical outside three documentation files: this new ADR, and the citation additions to ADR-0020, ADR-0022, and ADR-0023.

---

## Stage 14 — Final constitutional review

1. **Is Derived Knowledge permanently defined?** Yes — Stage 1: deterministic, reproducible, immutable, explainable, computed exclusively from Historical Truth; never from Runtime Truth directly, never from another Derived Knowledge object, never Historical Truth, never Runtime Truth.
2. **Is Derived Knowledge permanently distinguished from Historical Truth?** Yes — Stage 2: the Truth Hierarchy direction is permanent and one-way; neither level ever becomes, absorbs, or merges with the other.
3. **Is Layer 2 permanently defined as the sole producer of Derived Knowledge?** Yes — Stage 3: only Layer 2 creates it; Layer 3 and above consume, never recreate, mutate, or compete with it.
4. **Is Derived Knowledge permanently immutable?** Yes — Stage 4: every contract is immutable once produced; only superseded by new Derived Knowledge, never patched.
5. **Is the explainability chain permanently frozen?** Yes — Stage 5: Derived Knowledge → Historical Truth → Runtime Truth, always exactly two hops, always traceable, no hidden state.
6. **Are peer Layer 2 capabilities permanently independent?** Yes — Stage 7: Continuous Improvement and Knowledge Graph never consume one another; only a later, distinct capability (Organizational Memory) may consume both.
7. **Is the downward dependency rule permanently frozen?** Yes — Stage 8: the fan-out/fan-in dependency graph moves downward only, with no reverse, unauthorized peer, or skip-capability dependency.
8. **Can future ML/LLM/GNN implementations replace deterministic engines without changing contracts?** Yes — Stage 10/Recommendation 12: every future engine variant must implement the identical frozen runtime contract.
9. **Does this introduce zero runtime behavior?** Confirmed — Stage 13: documentation-only diff across four files; Ruff, the full test suite, productization, and golden verification are all unaffected.
10. **Is the repository constitutionally ready for CAP-085A — Organizational Memory Framework?** Yes. A future Organizational Memory architecture milestone may now cite this ADR directly for the Derived Knowledge definition, the fan-in consumption right over Continuous Improvement and Knowledge Graph, immutability, explainability, and engine replaceability — without re-deriving any of them, exactly as CAP-083 and CAP-084 no longer need to re-derive the Historical Dataset Resolution Principle now that ADR-0024 exists.

---

## Additional constitutional recommendations

Included per this milestone's brief, frozen alongside Recommendations 1–12 above.

### Recommendation 13 — Canonical knowledge ownership

Every fact must have exactly one canonical owner. Historical facts belong only to the Historical Dataset (ADR-0024 §Stage 6/11). Derived conclusions belong only to their producing Layer 2 runtime contract (Stage 3/4). No duplication — no second place in the platform is ever permitted to also claim ownership of a fact or a conclusion.

### Recommendation 14 — Knowledge before intelligence

Freeze the platform philosophy, one further tier of detail below ADR-0020 §Stage 11's Governance → Determinism → Learning → Prediction → Optimization → Autonomy:

```
Evidence
        ↓
History
        ↓
Knowledge
        ↓
Memory
        ↓
Learning
        ↓
Features
        ↓
Prediction
        ↓
Optimization
        ↓
Autonomy
```

Every future capability must fit somewhere within this chain — a capability that cannot be placed on it has not yet been decomposed correctly (mirrors ADR-0020 §Stage 3's identical requirement for the seven numbered layers).

### Recommendation 15 — Layer 2 completeness

Freeze that every Layer 2 capability must answer a fundamentally different question over the same Historical Truth:

- Continuous Improvement → *"What repeats?"*
- Knowledge Graph → *"What connects?"*
- Organizational Memory → *"What should be remembered?"*
- Learning Framework → *"What should change?"*

No two Layer 2 capabilities may compete for the same architectural responsibility — the direct application, at the Layer 2 level, of ADR-0001's single-owner-per-responsibility principle and ADR-0020 §Stage 3's "every capability belongs to exactly one layer" rule, now sharpened to "and answers exactly one question no peer already answers."

---

## Ownership, scope, and governance

- **Owns:** the definition of Derived Knowledge (Stage 1), the Truth Hierarchy's upper boundary (Stage 2), Layer 2 production ownership (Stage 3), Derived Knowledge immutability (Stage 4), the Derived Knowledge explainability chain (Stage 5), knowledge evolution rules (Stage 6), Layer 2 peer independence (Stage 7), the Layer 2 → Layer 7 dependency graph (Stage 8), the platform-wide knowledge lifecycle (Stage 9), and engine replaceability for every Layer 2+ capability (Stage 10).
- **Does not own:** the Truth Hierarchy's lower two levels (Runtime Truth and Historical Truth remain ADR-0021's and ADR-0024's); any Layer 1 runtime contract, policy, engine, orchestration, or Execution Package (ADR-0011 through ADR-0019); any specific Layer 2+ capability's own internal design, models, policy, or engine (those remain the province of their own subsystem ADRs — ADR-0022, ADR-0023, and every future Layer 2+ ADR); any concrete Organizational Memory or Learning Framework implementation (CAP-085/086, reserved future work, not introduced here).
- **Governance:** registered alongside ADR-0020, ADR-0021, and ADR-0024 as a platform constitutional document. **Proposed** — it becomes **Accepted** once a future capability (starting with CAP-085 — Organizational Memory Framework) is built directly against it without deviation, exactly as ADR-0020's own constitution became the standard CAP-083 and CAP-084 were built under.
