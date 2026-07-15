# ADR-0021 — Cross-Execution Data Architecture & Historical Intelligence Constitution

- **Status:** Proposed
- **Date:** 2026-07-15
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing design:** none — this ADR *is* the governing design, exactly as ADR-0020 introduces no proposal document because it is not subsystem architecture.
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution) and every architectural ADR it in turn reviewed (ADR-0011 through ADR-0019).
- **Runtime status:** Not applicable. This is a **documentation-only constitutional milestone**: no runtime behaviour, no implementation, no models, no runtime contracts, no `PlatformContext` changes, no serializers, no Execution Package changes, no manifest changes, no CLI changes, and no version bumps (Architecture, Platform, or otherwise). It permanently defines how the platform transitions from deterministic single-execution reasoning (Layer 1) into historical learning (Layer 2+) — it does not build any part of that transition.

## Scope note

ADR-0020 defines **platform evolution** — the seven architectural layers, their dependency direction, and the lifecycle every capability in every layer must follow. ADR-0021 defines **data evolution across time** — what kind of truth each layer is allowed to produce and consume, and the permanent rule that a fact about one execution and a conclusion inferred from many executions can never be confused with one another. Together they are the constitutional documents governing every future platform capability: ADR-0020 answers "where does this capability live?"; ADR-0021 answers "what kind of truth is this capability allowed to touch, and what kind must it never claim to be?"

---

## Stage 0 — Repository assessment

ADR-0015 through ADR-0020 were reviewed for existing ownership of historical data, execution lineage across runs, or organizational memory.

**Layer 1 is complete**, per ADR-0020's own Stage 0 review: Engineering Context, Requirement Analysis, Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, and the Execution Package are all accepted and live.

**Every Layer 1 runtime contract represents exactly one execution.** `EngineeringContext`, `AnalysisResult`, `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `CP1Result`, `QualityGovernanceResult`, and `RecommendationResult` are each scoped to a single `analysis_id` / `execution_id` pair. None of them carries a field, a reference, or a computation that spans two executions. The one place the word "lineage" already appears — `docs/architecture/execution-package.md` §3, "Execution Lineage" — describes the *within-one-execution* data flow (SourceArtifacts → ConsolidatedArtifacts → EngineeringContext → … → RecommendationResult), not lineage *across* executions over time. No existing document defines:

- historical ownership — no subsystem owns "the set of all past executions";
- historical datasets — no model, table, or file format aggregates more than one execution;
- execution lineage across runs — nothing links execution *N* to execution *N-1*;
- organizational memory — nothing persists a conclusion beyond the run that produced it.

**Conclusion:**

> No constitutional ownership exists. Proceed.

---

## Stage 1 — Introducing ADR-0021

This document, `docs/adr/0021-cross-execution-data-architecture.md`, is **Proposed**. It is a **constitutional ADR**, not a subsystem ADR: it defines no runtime contract, no policy, no model, and no service of its own. Its purpose is the Cross-Execution Data Architecture and Historical Intelligence Constitution — the permanent rules for what kind of truth may exist once a platform capability starts reasoning across more than one execution.

---

## Stage 2 — Problem statement

Today the platform reasons about exactly one execution. Every runtime contract — from `EngineeringContext` through `RecommendationResult` — belongs to one execution and answers a question about that execution alone (ADR-0020 Layer 1).

Nothing currently owns:

- **historical truth** — the durable record of what happened across many executions;
- **execution lineage** — how one execution relates to the ones before it;
- **historical datasets** — the organized, indexed corpus a learning capability would read from;
- **organizational learning** — conclusions that outlive the run that produced them;
- **temporal reasoning** — trend, drift, or change-over-time computation;
- **trend persistence** — where a computed trend is stored so it need not be recomputed;
- **execution relationships** — links between executions (same module, same policy, sequential runs).

Without constitutional guidance, the first capability to need any of these (CAP-083 onward, per ADR-0020's Layer 2) would have to invent an answer under deadline pressure — and every capability after it would inherit whatever ad hoc answer that first one chose. Left ungoverned, this risks:

- **duplicated history** — two capabilities each building their own partial record of "what happened," disagreeing at the edges;
- **inconsistent datasets** — no shared schema, so a trend computed one way in CAP-083 cannot be compared to one computed another way in CAP-086;
- **competing truths** — a learned pattern and the executions it was learned from drifting apart with no way to tell which one is authoritative;
- **hidden state** — a prediction or recommendation that depends on history no one can inspect, breaking the explainability principle ADR-0020 §Stage 7 already made constitutional;
- **irreproducible learning** — a conclusion that cannot be regenerated from source, because the source was never durably, immutably recorded in the first place.

---

## Stage 3 — Truth hierarchy

The platform recognizes exactly three kinds of truth, and only three. Every future capability must be built entirely in terms of them.

### Runtime Truth

**Owned by:** Layer 1 (ADR-0020).

**Examples:** `EngineeringContext`, `AnalysisResult`, `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `CP1Result`, `QualityGovernanceResult`, `RecommendationResult`.

**Characteristics:** immutable, deterministic, execution-scoped, explainable, canonical.

**Answers:** *What happened during one execution?*

Runtime Truth is never inferred. It is the direct, deterministic output of a governed engine reasoning over one execution's inputs — the ground truth every other kind of truth is ultimately built from.

### Historical Truth

**Owned by:** Layer 2 (Continuous Learning, ADR-0020).

**Constructed exclusively from:** Runtime Truth.

**Characteristics:** append-only, immutable, chronological, versioned, reproducible.

**Answers:** *What has happened over many executions?*

Historical Truth is not a new kind of fact — it is the durable, ordered accumulation of Runtime Truth that already existed, one execution at a time. It adds nothing runtime truth did not already contain; it organizes it across time.

### Derived Knowledge

**Produced by:** Layers 2 through 7 (ADR-0020).

**Examples:** trends, learned patterns, features, predictions, optimizations, autonomous plans, organizational intelligence.

**Characteristics:** derived, reproducible, explainable, **never canonical history**.

**Answers:** *What can we infer from history?*

Derived Knowledge is the platform's entire output above Layer 1 — every feature, prediction, optimization, autonomous action, and organizational insight. All of it is reproducible from Historical Truth; none of it is itself a historical fact. A trend computed from ten executions is a *conclusion about* those ten executions, never an eleventh execution's worth of new ground truth.

**Frozen dependency hierarchy:**

```
Runtime Truth
        ↓
Historical Truth
        ↓
Derived Knowledge
```

Never the reverse — Derived Knowledge may never be treated as Historical Truth, and Historical Truth may never be treated as (or edited to become) Runtime Truth. Never merged — the three layers of truth are never collapsed into one model, one store, or one contract.

### Why the three are kept separate (mandatory principle)

- **Runtime Truth is the canonical record of a single execution and is never inferred.** It is produced once, by the governed Layer 1 engine that owns it, and by nothing else.
- **Historical Truth is the canonical accumulation of immutable Runtime Truth across executions and is never altered by learning.** Layer 2 organizes it; Layers 3–7 read it; nothing above Layer 1 is ever permitted to write back into it.
- **Derived Knowledge is always reproducible from Historical Truth but is never itself considered historical fact.** A prediction, an optimization, or an autonomous plan can be regenerated, revised, or superseded without rewriting a single byte of history — because it was never history to begin with.

This distinction is foundational for every future Layer 2–7 capability. It exists precisely to prevent a learned artifact — a trend, a prediction, an autonomous recommendation — from ever being mistaken for, stored as, or trusted as canonical historical record. A platform that let its inferences quietly become its history would lose the ability to tell, a year later, whether something actually happened or was merely once predicted to.

---

## Stage 4 — Execution identity philosophy

**One execution is immutable.** Once `RecommendationResult` (or any Layer 1 terminal contract) completes for a given `execution_id`, nothing about that execution ever changes — not its inputs, not its intermediate results, not its final verdict.

**Corrections create new executions.** If a mistake is found, or evidence changes, or a policy is retuned, the platform runs again — a new `execution_id`, a new complete set of Runtime Truth. It never reaches back into the old execution's record to patch it.

**History references executions. History never edits executions.** Historical Truth (Layer 2) is built by appending references to completed, immutable executions — it names them, orders them, indexes them — and it never opens one back up to change what it recorded.

---

## Stage 5 — Historical Truth

**Historical truth is append-only.** A new entry is added when an execution completes; no existing entry is ever removed.

**Never rewritten. Never corrected. Never mutated.** If an execution's Runtime Truth was wrong, the correction is a *new* execution (Stage 4) with its *own* new Historical Truth entry — the old entry stays exactly as it was, because it accurately recorded what that execution actually produced at the time.

**History records:**

- what happened (the referenced Runtime Truth contracts),
- when (execution timestamp provenance, already present on every Layer 1 result),
- under which architecture (the Architecture Version in force),
- under which policies (each consumed subsystem's governed policy id/version),
- under which versions (every independently evolving contract/framework/engine version already frozen by Layer 1, per Stage 9).

**Historical truth is permanent.** Once appended, an entry is never deleted, archived-and-forgotten, or silently superseded — retention and indexing (Stage 6) may change how it is *found*, never whether it *exists*.

---

## Stage 6 — Historical Dataset

**Historical Dataset** is the canonical owner of historical executions — the single place Layer 2 organizes what Stage 5 requires to be recorded.

**It owns:**

- ordering — the chronological sequence of executions;
- lineage — how executions relate to one another across time (same module, same policy generation, sequential runs);
- retention — how long an entry remains directly queryable (never whether it remains true — see Stage 5);
- indexing — the structures that make a historical query fast;
- search — the query surface a learning capability actually reads from;
- organization — grouping, partitioning, and any other structural arrangement of the corpus.

**Continuous Learning consumes Historical Datasets. Never Execution Packages directly.** A Layer 2 (or higher) capability that reached past the Historical Dataset to read `manifest.json` or a `*_report.md` file directly would be depending on a projection (Stage 7) instead of the canonical record it projects — exactly the reverse-dependency and layer-skipping ADR-0020 §Stage 5 already forbids, now named explicitly for this seam.

---

## Stage 7 — Data evolution rules

**Historical datasets are constructed exclusively from runtime contracts** — `EngineeringContext`, `AnalysisResult`, `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `CP1Result`, `QualityGovernanceResult`, `RecommendationResult`, and their future Layer 1 peers.

**Never from:**

- reports (`*_report.md`),
- Markdown (`*.md` of any kind),
- manifests (`manifest.json`),
- logs,
- console output,
- execution artifacts generally.

**Execution artifacts remain projections only** — exactly the serialization invariant ADR-0016 §D16, ADR-0017 §D30, ADR-0018 §D8, and ADR-0019 §D9/§D10 each already froze for their own subsystem's Execution Package output. A projection may be regenerated, reformatted, or deleted at will because it carries no information the runtime contract does not already carry; a Historical Dataset built from a projection would inherit that same disposability for something that is supposed to be permanent (Stage 5). The Historical Dataset must therefore be built from the runtime contracts themselves — the same objects the Execution Package projects, read directly, never through the projection.

---

## Stage 8 — Historical explainability

Every future learning decision must be explainable through exactly this chain:

```
Historical Dataset
        ↓
Runtime Contracts
        ↓
Execution Inputs
```

A Layer 2–7 conclusion that cannot be traced down through the Historical Dataset, to the specific Runtime Truth contracts it aggregates, to the execution inputs those contracts were computed from, is not explainable and must not be constructible — the same "at least one reference" discipline ADR-0019 §D7 froze for a single `Recommendation`, now required end-to-end across the entire historical chain. **Learning must never depend upon hidden state.** If a trend, a feature, or a prediction cannot name which historical entries it was built from, it has failed this principle regardless of how accurate it appears to be.

---

## Stage 9 — Version evolution

The following version axes evolve **independently** — tuning, extending, or re-baselining one must never force a change to any other:

- **Execution versions** — the identity/provenance of one execution (already frozen per-subsystem across ADR-0015–ADR-0019).
- **Architecture versions** — the platform's Architecture Version (currently `1.2.0`, unchanged by this ADR).
- **Platform versions** — the platform's Platform Version (currently `1.0.0`, unchanged by this ADR).
- **Runtime contract versions** — each Layer 1 `*ResultVersion` (e.g. `RecommendationResultVersion`, `QualityGovernanceResultVersion`), each already its own independent axis.
- **Policy versions** — each Layer 1 `*PolicyVersion`, likewise already independent.
- **Dataset versions** — the Historical Dataset's own schema/organization version (Layer 2, reserved).
- **Learning versions** — a Continuous Learning capability's own implementation version (Layer 2, reserved).
- **Feature versions** — a `FeatureResult` schema version (Layer 3, reserved, per ADR-0020).
- **Prediction versions** — a `PredictionResult` schema version (Layer 4, reserved, per ADR-0020).

This is the same independent-version-axis discipline ADR-0015 §C, ADR-0016 §D6, ADR-0017's identity module, ADR-0018 §D5, and ADR-0019 §D5/§D9 each already applied within one subsystem — Recommendation 9 (Stage 13) lifts it into a permanent, platform-wide rule that also governs the new cross-execution axes this ADR introduces.

---

## Stage 10 — Historical dependency rules

```
Execution
        ↓
Execution Package
        ↓
Historical Dataset
        ↓
Continuous Learning
        ↓
Feature Engineering
        ↓
Prediction
        ↓
Optimization
        ↓
Autonomous Engineering
        ↓
Organizational Intelligence
```

**Never bypass** — no stage reaches past its immediate predecessor (Continuous Learning never reads an Execution Package directly, per Stage 6). **Never skip layers** — Feature Engineering consumes Continuous Learning's output, never raw executions. **Never duplicate datasets** — exactly one Historical Dataset is the canonical corpus; no capability builds a second, competing one. **Never create reverse dependencies** — nothing earlier in this chain ever imports, invokes, or depends on anything later in it.

This chain is the data-flow realization of ADR-0020 Stage 5's layer dependency rule, specialized to the Execution → History → Learning seam this ADR governs.

---

## Stage 11 — Ownership

Each stage of the chain has **exactly one owner**:

| Owner | Owns |
|---|---|
| Execution Package | execution persistence |
| Historical Dataset | historical organization |
| Continuous Learning | learning |
| Feature Engineering | features |
| Prediction | prediction |
| Optimization | optimization |
| Autonomous Engineering | execution (of governed engineering work) |
| Organizational Intelligence | organizational reasoning |

No owner may perform another's role — the Historical Dataset does not learn; Continuous Learning does not compute features; Feature Engineering does not predict. Each stage produces exactly the runtime contract Stage 6 of ADR-0020 already requires (or, for the Historical Dataset, the versioned historical record Stage 9 of this ADR requires) and nothing more.

---

## Stage 12 — Data lifecycle

Every unit of data in the platform progresses through exactly this permanent lifecycle:

```
Execution
        ↓
Runtime Truth
        ↓
Execution Package
        ↓
Historical Dataset
        ↓
Continuous Learning
        ↓
Feature Engineering
        ↓
Prediction
        ↓
Optimization
        ↓
Autonomous Engineering
        ↓
Organizational Intelligence
```

No stage is skipped, and no stage is reordered — the same discipline ADR-0020 §Stage 8 froze for a *capability's* lifecycle, now frozen for *data's* lifecycle as it moves through those same capabilities.

---

## Stage 13 — Constitutional recommendations

### Recommendation 1 — Historical truth is immutable

### Recommendation 2 — History is append-only

### Recommendation 3 — Runtime Truth is the only source of Historical Truth

### Recommendation 4 — Historical Truth is the only source of Derived Knowledge

### Recommendation 5 — Execution Packages remain serialization only

### Recommendation 6 — Learning never rewrites history

### Recommendation 7 — Feature Engineering consumes historical knowledge rather than raw execution artifacts whenever historical context is required

### Recommendation 8 — Every learned conclusion is reproducible from Historical Truth

### Recommendation 9 — Every historical object evolves independently through versioned contracts

### Recommendation 10 — Truth hierarchy is permanent

```
Runtime Truth
        ↓
Historical Truth
        ↓
Derived Knowledge
```

### Recommendation 11 — Every future Layer 2–7 capability must declare its Truth Hierarchy level

Every future Layer 2–7 ADR must explicitly identify which level of the Truth Hierarchy (Stage 3) it **consumes** and which level it **produces**. This is mandatory for all future ADRs — the same discipline ADR-0019 §D2 already required of every recommendation ("which upstream result, which id, which version"), now required of every future capability's relationship to history itself.

---

## Stage 14 — Verification

This milestone is documentation only. Verified:

- zero runtime changes — no file under `requirement_intelligence/` was touched;
- zero model changes — no Pydantic model, dataclass, or contract was added or modified;
- zero policy changes — no `*Policy` class or governed default was touched;
- zero `PlatformContext` changes — `platform_context.py` was not touched;
- zero serializers — no `serialization/` package was added or modified;
- zero Execution Package changes — `execution_data.py`, `execution_writer.py`, `manifest_builder.py` were not touched;
- zero manifest changes — no new manifest key exists;
- zero CLI changes — `scripts/run_requirement_analysis.py` was not touched;
- zero version bumps — Architecture Version (`1.2.0`), Platform Version (`1.0.0`), and every Layer 1 contract/policy/framework version are unchanged.

The repository remains byte-identical outside this one new documentation file.

---

## Stage 15 — Final constitutional review

1. **Is Runtime Truth permanently defined?** Yes — Stage 3: immutable, deterministic, execution-scoped, explainable, canonical; owned by Layer 1.
2. **Is Historical Truth permanently defined?** Yes — Stage 3/5: append-only, immutable, chronological, versioned, reproducible; owned by Layer 2.
3. **Is Derived Knowledge permanently defined?** Yes — Stage 3: derived, reproducible, explainable, never canonical history; produced by Layers 2–7.
4. **Is the Truth Hierarchy permanently frozen?** Yes — Runtime Truth → Historical Truth → Derived Knowledge, never reversed, never merged.
5. **Is execution immutability permanently frozen?** Yes — Stage 4: one execution never changes; corrections create new executions.
6. **Is append-only history permanently frozen?** Yes — Stage 5: never rewritten, never corrected, never mutated.
7. **Are Historical Datasets uniquely owned?** Yes — Stage 6/11: exactly one Historical Dataset, owning ordering/lineage/retention/indexing/search/organization.
8. **Are dependency directions permanently frozen?** Yes — Stage 10: Execution → Execution Package → Historical Dataset → Continuous Learning → Feature Engineering → Prediction → Optimization → Autonomous Engineering → Organizational Intelligence, upward only.
9. **Does this introduce zero runtime behavior?** Confirmed — Stage 14: documentation-only diff, full repository verification unaffected.
10. **Is the repository constitutionally ready to begin CAP-083A?** Yes.

---

## Ownership, scope, and governance

- **Owns:** the Truth Hierarchy (Runtime Truth / Historical Truth / Derived Knowledge), execution immutability, the append-only history rule, Historical Dataset ownership, the cross-execution data lifecycle, and the version-independence rules for every historical/derived axis.
- **Does not own:** any Layer 1 runtime contract, policy, engine, orchestration, or Execution Package (those remain exactly where ADR-0011 through ADR-0019 place them); any Layer 2–7 capability's internal design (those remain the province of their own future ADRs, each required by Recommendation 11 to declare its Truth Hierarchy level).
- **Governance:** registered alongside ADR-0020 as a platform constitutional document. **Proposed** — it becomes **Accepted** as CAP-083 and every subsequent Layer 2–7 capability is built under it without deviation.
