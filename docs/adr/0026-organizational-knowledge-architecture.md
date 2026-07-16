# ADR-0026 — Organizational Knowledge Architecture & Learning Constitution

- **Status:** Proposed
- **Date:** 2026-07-16
- **Supersedes:** nothing. **Amends:** nothing. **Elevates:** the lifecycle tier ADR-0025 §Stage 9 named "Aggregated Knowledge" (owned, once built, by Organizational Memory / CAP-085) and "Learned Knowledge" (owned, once built, by Learning Framework / CAP-086) — both named there in one table row each — into a full constitutional document, exactly as ADR-0024 elevated Historical Truth from ADR-0021 §Stage 3's one paragraph, and ADR-0025 elevated Derived Knowledge from the same section.
- **Governing design:** none — this ADR *is* the governing design, exactly as ADR-0020, ADR-0021, ADR-0024, and ADR-0025 introduce no proposal document because none of them is subsystem architecture.
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — defines the seven layers and reserves CAP-085/CAP-086 inside Layer 2), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — defines the Truth Hierarchy this ADR sits above), ADR-0024 (Historical Dataset & Historical Truth Constitution — the sibling constitutional document for the tier two levels below this one), and ADR-0025 (Derived Knowledge Architecture & Layer 2 Constitution — the sibling constitutional document for the tier immediately below this one; ADR-0025 defines **Derived Knowledge**, this ADR defines **Organizational Knowledge**, the next tier up the same lifecycle ADR-0025 §Stage 9 already named).
- **Runtime status:** Not applicable. This is a **documentation-only constitutional milestone**: no runtime behaviour, no implementation, no models, no runtime contracts, no `PlatformContext` changes, no policies, no services, no serializers, no Execution Package changes, no manifest changes, no CLI changes, and no version bumps (Architecture, Platform, or otherwise). It permanently defines what Organizational Knowledge is, how it matures, how it evolves, how future capabilities consume it, and how intelligence grows from it — it does not build any part of that definition, and it is **not** Organizational Memory, **not** Learning Framework, and **not** Feature Engineering. Those remain future subsystem ADRs this document exists to govern in advance.

## Scope note

ADR-0020 defines **platform evolution** — the seven layers. ADR-0021 defines **data evolution across time** — the three-level Truth Hierarchy. ADR-0024 completed the constitution for the middle tier (Historical Truth). ADR-0025 completed the constitution for the tier immediately above it (Derived Knowledge) and, because Layer 2 is where Derived Knowledge is first produced, also froze how Layer 2's peer capabilities relate to one another. This ADR completes the constitution for the **next** tier ADR-0025 §Stage 9 already named but did not detail: **Organizational Knowledge** — the curated, matured, cross-execution knowledge a future Organizational Memory (CAP-085) will produce from Continuous Improvement's and Knowledge Graph's Derived Knowledge, and the **Learning** a future Learning Framework (CAP-086) will produce from Organizational Knowledge. Together, ADR-0020, ADR-0021, ADR-0024, ADR-0025, and ADR-0026 are the five constitutional documents governing every future platform capability: ADR-0020 answers "where does this capability live?"; ADR-0021 answers "what kind of truth is this capability allowed to touch?"; ADR-0024 answers "how is Historical Truth organized and resolved?"; ADR-0025 answers "what is Layer 2 allowed to produce, and how do its peers relate?"; ADR-0026 answers "how does that production mature into something an organization can trust and act on, and how does learning begin?"

This is **not** a subsystem ADR. It is **not** Organizational Memory. It is **not** Learning Framework. It is **not** Feature Engineering. It defines no `requirement_intelligence/` package, no `PlatformContext` method, no policy, no model, no service — it defines the platform-wide principles every future capability from CAP-085 onward inherits, exactly as ADR-0020 §Stage 3 requires of every capability not yet built.

---

## Stage 0 — Repository assessment

Before writing this ADR, the following were reviewed:

- **ADR-0020** (§Stage 4, Layer 2): reserves CAP-085 (Organizational Memory) and CAP-086 (Learning Framework) inside Layer 2, alongside CAP-083 (Continuous Improvement, built) and CAP-084 (Knowledge Graph, built). Neither CAP-085 nor CAP-086 has its own ADR yet.
- **ADR-0021** (§Stage 3): the Truth Hierarchy — Runtime Truth → Historical Truth → Derived Knowledge — is confirmed constitutionally frozen and unchanged by anything since.
- **ADR-0024**: Historical Truth's own full constitution — confirmed constitutionally frozen, unaffected by and unaffecting this ADR.
- **ADR-0025**: Derived Knowledge's own full constitution, and Layer 2 peer independence — confirmed constitutionally frozen. Its §Stage 9 Knowledge Lifecycle table names two tiers this ADR now details in full: "Aggregated Knowledge" (Organizational Memory's future output) and "Learned Knowledge" (Learning Framework's future output).

**Confirmed:**

- **The Truth Hierarchy is constitutionally frozen** (ADR-0021 §Stage 3, unamended).
- **Historical Truth is constitutionally frozen** (ADR-0024, unamended).
- **Derived Knowledge is constitutionally frozen** (ADR-0025, unamended).
- **Organizational Knowledge has no constitutional definition** — ADR-0025 §Stage 9 names its lifecycle position ("Aggregated Knowledge") in one table row and moves on; nothing gives it the ownership/maturity/promotion/retirement/confidence/explainability treatment ADR-0024 gave Historical Truth and ADR-0025 gave Derived Knowledge.
- **Organizational Memory (CAP-085) has not yet been introduced** — reserved by name in ADR-0020 only; no ADR, no proposal, no code.
- **Learning Framework (CAP-086) has not yet been introduced** — the same: reserved by name only.
- **No subsystem currently owns "Lesson," "Best Practice," "Experience," or "Knowledge Confidence"** — confirmed by repository-wide search; these terms appear nowhere in `requirement_intelligence/`, `docs/adr/`, or `docs/proposals/` prior to this document.

**Terminology reconciliation (found, resolved, not a blocking inconsistency).** ADR-0025 §Stage 9 already names the lifecycle tier this ADR governs "Aggregated Knowledge" (Organizational Memory) and "Learned Knowledge" (Learning Framework). This ADR uses the more precise, fully-specified names **Organizational Knowledge** and **Learning** for the identical two lifecycle positions — the same relationship ADR-0024's full "Historical Truth" constitution has to ADR-0021 §Stage 3's brief mention of the same term, and ADR-0025's full "Derived Knowledge" constitution has to that same section. This is a **detailing**, never a redefinition: nothing in ADR-0025's own text is changed (per this ADR's own Stage 15 instruction, honored below), and the two names refer to the same position in the same frozen lifecycle. Stage 4 below states this mapping explicitly so no future reader mistakes it for two competing lifecycles.

**Terminology reconciliation (found, resolved, not a blocking inconsistency).** Stage 2's Knowledge Hierarchy below uses the generic terms "Observation" and "Finding" as the *bottom* rungs of a knowledge-maturity ladder. These are **conceptual** terms, never a rename of the frozen `ImprovementFinding` (ADR-0022), `KnowledgeObservation`, or `KnowledgeFinding` (ADR-0023) model classes — those remain exactly what they are: Layer 2 Derived Knowledge, already shipped, already frozen, untouched by this document. A future Organizational Memory may read those exact objects as *raw material* for its own "Observation"/"Finding" rungs, but this ADR neither renames nor reaches into either subsystem's models. Stage 2 states this explicitly.

**No other duplicated concept, conflicting terminology, overlapping ownership, or hidden assumption was found.** CAP-085 and CAP-086 have no ADR yet, so this document is free to freeze their conceptual responsibilities without amending or contradicting anything already built.

> No blocking inconsistency found; two terminology relationships were identified and resolved explicitly within this document (above, and Stage 2/4 below). Proceeding with a pure constitutional freeze.

---

## Stage 1 — Define Organizational Knowledge

Permanently defined.

**Organizational Knowledge is:**

- **explainable** — every claim traces back through Derived Knowledge to Historical Truth to Runtime Truth (Stage 9);
- **curated** — never a raw aggregation; a deliberate, governed act of selection and maturation separates it from the Derived Knowledge it was built from (Stage 6);
- **reproducible** — regenerable from the same Derived Knowledge inputs at any time;
- **immutable** — once produced, never modified, only promoted or retired (Stage 3, Stage 6, Stage 7);
- **derived exclusively from Derived Knowledge** — never computed from Historical Truth or Runtime Truth directly (Stage 4; mirrors the discipline ADR-0025 Stage 1 already froze for how Derived Knowledge itself is computed, lifted one tier up);
- **organizational rather than execution-specific** — it answers "what has this organization learned?", never "what happened in this one execution?" or "what happened across this one dataset?" (those are Layer 1's and Layer 2's own questions, ADR-0020 §Stage 4, ADR-0025 Stage 1).

**Organizational Knowledge is never:**

- **Runtime Truth** — it is never mistaken for, stored as, or substituted for a Layer 1 execution record;
- **Historical Truth** — it is never appended to the Historical Dataset (ADR-0024 §Stage 3, unchanged);
- **Derived Knowledge** — it is a distinct, later tier; `ContinuousImprovementResult` and `KnowledgeGraphResult` remain exactly what ADR-0025 already froze them as, never relabelled as Organizational Knowledge;
- **Prediction** — a future Layer 4 product, downstream of Learning (Stage 4), never confused with the knowledge Learning consumes;
- **Optimization** — a future Layer 5 product, further downstream still;
- **Autonomous Decision** — a future Layer 6 product, the furthest downstream of all;
- **implementation logic** — Organizational Knowledge is content, never code, never a rule, never an engine; an engine may read it, but the engine is never part of it.

---

## Stage 2 — Knowledge hierarchy

Freeze the permanent conceptual hierarchy:

```
Observation
        ↓
Finding
        ↓
Pattern
        ↓
Experience
        ↓
Lesson
        ↓
Best Practice
        ↓
Organizational Knowledge
```

**Conceptual definitions only — no subsystem ownership is assigned at this stage** (Stage 10 assigns capability responsibilities without redesigning ADR-0020's layers).

| Level | Definition | Who creates it | Who consumes it |
|---|---|---|---|
| **Observation** | One raw structural or recurrence fact, already present in Derived Knowledge (e.g. a Continuous Improvement finding, a Knowledge Graph structural observation). Not new content — the same fact, read as raw material. | Continuous Improvement, Knowledge Graph (already, as Derived Knowledge) | A future knowledge-maturation capability |
| **Finding** | One Observation judged noteworthy — still singular, still tied to a specific historical window, not yet compared across windows. | A future knowledge-maturation capability | The same capability's next maturation step |
| **Pattern** | Two or more Findings recognized as the same shape, across more than one historical window or subject. The first tier that is genuinely cross-Derived-Knowledge, not just cross-execution (that comparison already happened inside Layer 2). | A future knowledge-maturation capability | The same capability's next maturation step |
| **Experience** | A Pattern with enough repetition and enough time elapsed to be trusted as more than coincidence — still descriptive, not yet prescriptive. | A future knowledge-maturation capability | The same capability's next maturation step |
| **Lesson** | An Experience given an explicit, explainable conclusion — "when X recurs, Y follows." The first tier that says something actionable, still scoped to the evidence that produced it. | A future knowledge-maturation capability | Human review, or the next maturation step |
| **Best Practice** | A Lesson verified across enough independent Experiences that it is recommended generally, not just where it was first observed. | A future knowledge-maturation capability, after verification (Stage 3) | Every future consumer of Organizational Knowledge |
| **Organizational Knowledge** | The curated collection of Best Practices (and, where explicitly retained, the Lessons/Experiences/Patterns/Findings/Observations they were built from) an organization can explain, trust, and act on. | A future Organizational Memory (CAP-085) | Learning Framework (CAP-086), and every layer above it (Stage 4, Stage 10) |

The bottom two rungs (Observation, Finding) are deliberately generic terms, not a rename of `ImprovementFinding`, `KnowledgeObservation`, or `KnowledgeFinding` (Stage 0). The top rung (Organizational Knowledge) is the tier this entire ADR constitutionally governs.

---

## Stage 3 — Knowledge maturity

Freeze permanently.

```
Observed
        ↓
Repeated
        ↓
Verified
        ↓
Institutionalized
        ↓
Retired
```

**Knowledge evolves upward. Never downward.** A piece of knowledge that reaches `Verified` never reverts to `Observed` — if new evidence contradicts it, the *old* maturity record stays exactly as it was (Stage 6: promotion, never rewriting), and a **new** piece of knowledge is produced to supersede it, carrying its own maturity level from the start. This is the maturity-axis restatement of Stage 6's promotion principle and ADR-0025 Stage 4's immutability principle: an object's maturity level is itself part of its immutable record at the moment it was last produced, never edited after the fact.

- **Observed** — a Finding or Pattern has been recorded; no claim of reliability yet.
- **Repeated** — the same Pattern has recurred; still no claim that it generalizes.
- **Verified** — the Pattern has been checked against independent Experiences and holds; this is the threshold a Lesson must cross before it may become a Best Practice (Stage 14, Recommendation 4).
- **Institutionalized** — the knowledge is adopted as a governing Best Practice, actively consulted by downstream capabilities.
- **Retired** — the knowledge is no longer actively consulted, but never deleted (Stage 7).

---

## Stage 4 — Knowledge lifecycle

Freeze permanently. Extends ADR-0025 §Stage 9:

```
Runtime Truth
        ↓
Historical Truth
        ↓
Derived Knowledge
        ↓
Organizational Knowledge
        ↓
Learning
        ↓
Feature
        ↓
Prediction
        ↓
Decision
        ↓
Optimization
        ↓
Autonomy
```

**Mapping to ADR-0025 §Stage 9 (terminology reconciliation, Stage 0).** "Organizational Knowledge" here occupies the exact position ADR-0025 named "Aggregated Knowledge"; "Learning" here occupies the exact position ADR-0025 named "Learned Knowledge." No lifecycle position is added, removed, or reordered relative to ADR-0025 — this ADR only refines the two names ADR-0025 introduced without detailing, and interposes one additional, explicit "Decision" rung between Prediction and Optimization that ADR-0025 §Stage 9 left implicit (a future `PredictionResult` must still resolve into a chosen course of action before Layer 5 optimizes across a *set* of such decisions — the same distinction ADR-0020 §Stage 4 already draws between Layer 4's estimation and Layer 5's choice).

No stage is skipped, and no stage is reordered — the same discipline ADR-0020 §Stage 8 froze for a capability's lifecycle and ADR-0021 §Stage 12 froze for data's lifecycle, now extended one further tier.

---

## Stage 5 — Organizational Knowledge principles

Freeze permanently.

**Knowledge is:**

- **curated** — never a raw aggregation; a deliberate, governed act of selection separates signal from noise (Stage 6);
- **cumulative** — new Organizational Knowledge adds to what already exists; it never starts over from nothing each time (Stage 6, Stage 9);
- **immutable** — once produced, never modified (Stage 3, restated);
- **reproducible** — regenerable from the Derived Knowledge it was built from;
- **explainable** — every claim traces back through the full chain to Runtime Truth (Stage 9).

**Knowledge is never:**

- **speculative** — no Best Practice may be asserted without the Verified maturity level (Stage 3) and the explainable evidence chain (Stage 9) behind it;
- **hidden** — no knowledge object may exist that a downstream consumer cannot inspect;
- **rewritten** — an existing knowledge object's content never changes after production (Stage 3, Stage 6);
- **opaque** — no knowledge object may assert a conclusion without naming the Lessons, Experiences, Patterns, Findings, and Observations it was built from (Stage 9).

---

## Stage 6 — Knowledge promotion

Freeze permanently.

```
Observation
        ↓
Pattern
        ↓
Lesson
        ↓
Best Practice
```

**Knowledge is promoted, never rewritten.** Moving a Pattern to a Lesson, or a Lesson to a Best Practice, produces a **new** object at the higher rung that references the object(s) it was promoted from — it never edits the lower-rung object in place. The lower-rung object remains exactly as it was: an accurate record of what was known at that maturity level, at that time (mirrors ADR-0021 §Stage 4's execution immutability, ADR-0024 Stage 8's append-only Historical Truth, and ADR-0025 Stage 4/6's Derived Knowledge immutability — the same non-negotiable pattern, now frozen for its fourth tier running).

**Every promotion must remain explainable.** A Best Practice must be able to name the specific Lesson(s) it was promoted from; a Lesson must name the specific Experience(s); an Experience must name the specific Pattern(s); a Pattern must name the specific Finding(s)/Observation(s) — an unbroken reference chain, never a summary that discards the chain (Stage 9).

---

## Stage 7 — Knowledge retirement

Freeze permanently.

**Knowledge is never deleted.**

```
Active
        ↓
Deprecated
        ↓
Historical
        ↓
Archived
```

- **Active** — currently consulted by downstream capabilities as authoritative.
- **Deprecated** — superseded by newer Organizational Knowledge, no longer recommended for new decisions, but still explainable and still present.
- **Historical** — retained solely for explainability and audit; no longer surfaced as current guidance.
- **Archived** — retained at the lowest-visibility tier; still never deleted, never inaccessible to a query that explicitly asks for it.

**Retirement preserves explainability.** A decision made three years ago, using a Best Practice since deprecated, must still be explainable today by tracing back to that (now-deprecated, still-present) Best Practice — retirement changes *visibility*, never *existence*, exactly mirroring ADR-0024 Stage 5/8's principle that retention and indexing may change how an entry is *found*, never whether it *exists*.

---

## Stage 8 — Knowledge confidence

Freeze permanently.

**Confidence is metadata. Confidence never changes truth.**

```
Low
        ↓
Medium
        ↓
High
        ↓
Verified
```

**Confidence may evolve. Truth does not.** A Lesson's confidence level may rise from `Low` to `Verified` as more corroborating Experience accumulates — this is not a mutation of the Lesson's own recorded content (Stage 5/6), it is the *production of a new* Lesson object carrying the updated confidence, referencing the prior one it supersedes, exactly as every other promotion in Stage 6 works. Confidence is never a field on an existing object that changes in place; it is itself subject to the same append-only, promotion-not-rewrite discipline as the knowledge it describes.

Confidence is orthogonal to maturity (Stage 3): maturity describes *how far a piece of knowledge has progressed through the hierarchy*; confidence describes *how strongly the evidence supports it at its current maturity level*. A newly-Observed Pattern can carry Low confidence; a long-Institutionalized Best Practice can, in principle, still carry Medium confidence if its supporting Experience base is narrow — the two axes are tracked independently and neither substitutes for the other.

---

## Stage 9 — Explainability chain

Freeze permanently.

Every future Organizational Knowledge object must trace:

```
Lesson
        ↓
Patterns
        ↓
Findings
        ↓
Historical Truth
        ↓
Runtime Truth
```

**No hidden inference.** A Best Practice or Lesson that cannot name the specific Patterns it was promoted from, which cannot name the specific Findings/Observations they were promoted from, which cannot ultimately trace to specific Historical Truth entries and the Runtime Truth executions those entries reference, is not explainable and must not be constructible — the same "at least one reference" discipline ADR-0019 §D7 first froze for a single `Recommendation`, ADR-0021 §Stage 8 required end-to-end across the historical chain, ADR-0025 Stage 5 required for Derived Knowledge's own two-hop chain, and this stage now requires across every rung of the full knowledge hierarchy (Stage 2), however many hops that takes for any given object.

---

## Stage 10 — Capability responsibilities

Freeze conceptual responsibilities only. **This does not redesign ADR-0020** — every capability named below remains exactly where ADR-0020 §Stage 4 already places it; this stage only states, in one place, the distinct question each answers, extending ADR-0025 Recommendation 15 (Layer 2 Completeness) up through the layers this ADR's lifecycle (Stage 4) touches:

| Capability | Question it answers |
|---|---|
| Continuous Improvement | *"What repeats?"* |
| Knowledge Graph | *"What connects?"* |
| Organizational Memory | *"What deserves to be remembered?"* |
| Learning Framework | *"What should change?"* |
| Feature Engineering | *"What best represents knowledge numerically?"* |
| Prediction | *"What will likely happen?"* |
| Optimization | *"What should be done?"* |
| Autonomy | *"What should happen automatically?"* |

No two capabilities may compete for the same question (ADR-0025 Recommendation 15, restated once more at full lifecycle scope).

---

## Stage 11 — Learning principles

Freeze permanently.

**Learning consumes Organizational Knowledge.** A future Learning Framework (CAP-086) reads Best Practices (and, where it needs the evidence chain, the Lessons/Experiences/Patterns beneath them) — never raw Derived Knowledge, never Historical Truth, never Runtime Truth directly.

**Learning does not consume Runtime Truth directly.** The same no-skip discipline ADR-0020 §Stage 5 freezes between numbered layers, and ADR-0025 Stage 7/8 freezes within Layer 2's own capability sequence, applies here: Learning Framework must not reach past Organizational Memory to Continuous Improvement, Knowledge Graph, the Historical Dataset, or any Layer 1 execution.

**Learning does not mutate Organizational Knowledge.** Learning Framework is a consumer, never a co-owner, of the Organizational Knowledge it reads (Stage 5/6: immutable, promoted only by Organizational Memory's own governed process) — a "what should change" conclusion is Learning's own new output, never an edit to the knowledge that informed it.

---

## Stage 12 — Intelligence evolution

Freeze permanently.

```
Truth
        ↓
Knowledge
        ↓
Learning
        ↓
Features
        ↓
Prediction
        ↓
Decision
        ↓
Optimization
        ↓
Autonomy
```

**Each layer answers a different class of questions** (Stage 10): Truth answers "what happened?" (Layer 1) and "what has happened, accumulated?" (Historical Truth, ADR-0024); Knowledge answers "what have we learned is true?" (Derived Knowledge, ADR-0025, and Organizational Knowledge, this ADR); Learning answers "what should change?"; Features answer "how do we represent this numerically?"; Prediction answers "what will likely happen?"; Decision answers "what should be done, in this one instance?"; Optimization answers "what should be done, across many instances or constraints?"; Autonomy answers "what should happen without a human in the loop?"

**No layer replaces an earlier one.** Prediction never substitutes for Truth; Optimization never substitutes for Knowledge; Autonomy never substitutes for Learning. Each later class of question can only be asked because every earlier one was already answered, governed, deterministic, and explainable first (ADR-0020 §Stage 11's Governance → Determinism → Learning → Prediction → Optimization → Autonomy, restated once more at this ADR's own granularity).

---

## Stage 13 — Future replaceability

Freeze permanently.

**Future implementations may use** deterministic reasoning, statistical models, machine learning, LLMs, graph neural networks, reinforcement learning, neuro-symbolic AI, or any future paradigm not yet named — **without changing constitutional definitions.** Whatever technique a future Organizational Memory or Learning Framework engine uses to promote a Pattern into a Lesson, or a Lesson into a Best Practice, the object it produces must still satisfy Stage 1's definition, Stage 3's maturity levels, Stage 6's promotion discipline, Stage 7's retirement discipline, Stage 8's confidence/truth separation, and Stage 9's explainability chain — exactly as ADR-0025 Stage 10/Recommendation 12 already froze one tier below for Continuous Improvement's and Knowledge Graph's own future engine variants.

---

## Stage 14 — Constitutional recommendations

Freeze permanently, at least fifteen.

### Recommendation 1 — Organizational Knowledge is immutable

Once produced, a knowledge object at any rung of Stage 2's hierarchy is never modified (Stage 3, Stage 5, Stage 6).

### Recommendation 2 — Knowledge is promoted, never rewritten

Moving up the hierarchy (Stage 6) or the maturity axis (Stage 3) always produces a new object referencing the one it supersedes; it never edits the prior object in place.

### Recommendation 3 — Lessons require explainable evidence

A Lesson that cannot name the Experience(s), Pattern(s), and Finding(s) it was promoted from is not constructible (Stage 9).

### Recommendation 4 — Best Practices emerge from verified lessons

A Lesson must reach the `Verified` maturity level (Stage 3) before it may be promoted to a Best Practice (Stage 6) — an `Observed` or merely `Repeated` Lesson is never institutionalized.

### Recommendation 5 — Confidence is metadata, never truth

Confidence (Stage 8) describes how strongly evidence supports a claim; it never substitutes for, edits, or is confused with the claim's own immutable content.

### Recommendation 6 — Organizational Knowledge is reproducible

Given the same Derived Knowledge inputs and the same governed promotion policy, the same Organizational Knowledge results (Stage 1, Stage 5).

### Recommendation 7 — Learning consumes knowledge, not history

Learning Framework reads Organizational Knowledge; it never reaches past it to Derived Knowledge, Historical Truth, or Runtime Truth directly (Stage 11).

### Recommendation 8 — Predictions never become evidence

A Layer 4 `PredictionResult`, a Layer 5 decision or optimization, or a Layer 6 autonomous action is never fed back into Organizational Knowledge, Derived Knowledge, or Historical Truth as if it were newly-observed evidence (extends ADR-0025 Recommendation 8 one further tier up the lifecycle, Stage 4/12).

### Recommendation 9 — Organizational Knowledge never mutates Historical Truth

No future Organizational Memory or Learning Framework capability writes back into the Historical Dataset (extends ADR-0024 §Stage 3/8 and ADR-0025 Recommendation 1 to this tier).

### Recommendation 10 — Every capability owns exactly one class of knowledge

Continuous Improvement owns recurrence; Knowledge Graph owns structure; Organizational Memory owns curated organizational knowledge; Learning Framework owns learned change — no capability produces, stores, or governs another's (Stage 10, extends ADR-0025 Recommendation 5).

### Recommendation 11 — Intelligence consumes knowledge rather than engines

Every layer above Organizational Knowledge (Learning, Feature Engineering, Prediction, Optimization, Autonomy) consumes the frozen runtime contract a lower layer produced — never the engine, provider, service, or policy that produced it (extends ADR-0020 §Stage 6 and ADR-0025 Stage 5/10 to this tier).

### Recommendation 12 — Knowledge retirement is append-only

Deprecating, historicizing, or archiving a knowledge object (Stage 7) changes its visibility only; the object, and every reference chain through it, remains permanently present and explainable.

### Recommendation 13 — Organizational Knowledge remains implementation-independent

How a future Organizational Memory or Learning Framework stores, indexes, or queries its knowledge objects is an implementation detail, never part of this constitution (mirrors ADR-0024 Recommendation 5/12 and ADR-0025 Recommendation 9, generalized to this tier).

### Recommendation 14 — Future AI implementations preserve constitutional contracts

A future statistical, ML, LLM, GNN, reinforcement-learning, or neuro-symbolic implementation of Organizational Memory or Learning Framework must satisfy every stage of this ADR unchanged (Stage 13).

### Recommendation 15 — Platform evolution always follows Truth → Knowledge → Learning → Intelligence

No future capability may produce a prediction, an optimization, or an autonomous action without first passing through governed Truth, curated Knowledge, and deliberate Learning, in that order (Stage 4, Stage 12; the platform-wide restatement, at this ADR's own scope, of ADR-0020 §Stage 11's philosophy and ADR-0025 Recommendation 14/Recommendation 10 below it).

---

## Stage 15 — Cross references

`docs/adr/0020-platform-evolution-roadmap.md` §Layer 2 — Continuous Learning is updated to add ADR-0026 alongside its existing ADR-0021/ADR-0024/ADR-0025 constitutional-foundation citation. No roadmap restructuring: the CAP-083/084/085/086 lifecycle lines and layer ordering are unchanged — this is a citation addition only.

`docs/adr/0025-derived-knowledge-architecture.md` is updated to add ADR-0026 to its own constitutional cross-references, noting explicitly that ADR-0025 defines **Derived Knowledge** while ADR-0026 defines **Organizational Knowledge** — the next tier up the same lifecycle ADR-0025 §Stage 9 already named. **No constitutional rule inside ADR-0025 is modified** — Stage 9's table, its "Aggregated Knowledge"/"Learned Knowledge" naming, and every Recommendation remain exactly as ADR-0025 froze them; this is a citation addition only.

**ADR-0021 and ADR-0024 are not modified.** Stage 0's review found no inconsistency in either that this ADR needed to correct.

---

## Stage 16 — Verification

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

Ruff, the full repository test suite, productization, and golden verification were run after this change; all pass, and the repository remains byte-identical outside two documentation files: this new ADR, and the citation addition to ADR-0020. ADR-0025 receives one additive cross-reference paragraph, per Stage 15, with no rule changed.

---

## Stage 17 — Final constitutional review

1. **Is Organizational Knowledge permanently defined?** Yes — Stage 1: explainable, curated, reproducible, immutable, derived exclusively from Derived Knowledge, organizational rather than execution-specific; and explicitly not Runtime Truth, Historical Truth, Derived Knowledge, Prediction, Optimization, Autonomous Decision, or implementation logic.
2. **Is Organizational Knowledge permanently distinguished from Derived Knowledge?** Yes — Stage 1/Stage 4: a distinct, later lifecycle tier, computed exclusively from Derived Knowledge, never confused with `ContinuousImprovementResult` or `KnowledgeGraphResult` themselves.
3. **Is the Knowledge Hierarchy permanently frozen?** Yes — Stage 2: Observation → Finding → Pattern → Experience → Lesson → Best Practice → Organizational Knowledge, each rung conceptually defined with its creator and consumer.
4. **Is Knowledge Maturity permanently frozen?** Yes — Stage 3: Observed → Repeated → Verified → Institutionalized → Retired, upward only, never downward.
5. **Is Knowledge Promotion permanently frozen?** Yes — Stage 6: promotion produces a new, referencing object; the object promoted from is never rewritten.
6. **Is Knowledge Retirement permanently frozen?** Yes — Stage 7: Active → Deprecated → Historical → Archived; retirement changes visibility, never existence; nothing is ever deleted.
7. **Is the explainability chain permanently frozen?** Yes — Stage 9: Lesson → Patterns → Findings → Historical Truth → Runtime Truth, no hidden inference, no rung skipped.
8. **Can future deterministic, ML, LLM, GNN, RL, and neuro-symbolic implementations evolve without changing constitutional definitions?** Yes — Stage 13/Recommendation 14: every future engine variant must satisfy this ADR's definitions unchanged.
9. **Does this milestone introduce zero runtime behavior?** Confirmed — Stage 16: documentation-only diff across two files; Ruff, the full test suite, productization, and golden verification are all unaffected.
10. **Is the repository constitutionally ready for CAP-085A — Organizational Memory Framework?** Yes. A future Organizational Memory architecture milestone may now cite this ADR directly for the Organizational Knowledge definition, the full knowledge hierarchy and maturity model, promotion and retirement discipline, confidence/truth separation, and the explainability chain — without re-deriving any of them, exactly as CAP-083 and CAP-084 no longer need to re-derive ADR-0024's Historical Dataset Resolution Principle or ADR-0025's Derived Knowledge principle.

---

## Ownership, scope, and governance

- **Owns:** the definition of Organizational Knowledge (Stage 1), the conceptual knowledge hierarchy (Stage 2), knowledge maturity (Stage 3), the knowledge lifecycle's extension above Derived Knowledge (Stage 4), Organizational Knowledge's own principles (Stage 5), promotion (Stage 6), retirement (Stage 7), confidence (Stage 8), the explainability chain above Derived Knowledge (Stage 9), conceptual capability responsibilities from Organizational Memory through Autonomy (Stage 10), Learning's own principles (Stage 11), the intelligence-evolution ordering (Stage 12), and future engine replaceability for Organizational Memory and Learning Framework (Stage 13).
- **Does not own:** the Truth Hierarchy or its lower two levels (Runtime Truth and Historical Truth remain ADR-0021's and ADR-0024's); Derived Knowledge or Layer 2 peer independence (remain ADR-0025's, unmodified); any Layer 1 runtime contract, policy, engine, orchestration, or Execution Package (ADR-0011 through ADR-0019); the actual layer definitions or dependency rules (remain ADR-0020's, unmodified); any concrete Organizational Memory, Learning Framework, Feature Engineering, Prediction, Optimization, or Autonomous Engineering implementation (reserved future work, not introduced here).
- **Governance:** registered alongside ADR-0020, ADR-0021, ADR-0024, and ADR-0025 as a platform constitutional document. **Proposed** — it becomes **Accepted** once a future capability (starting with CAP-085A — Organizational Memory Framework) is built directly against it without deviation, exactly as ADR-0025 became the standard the next Layer 2 capability is expected to be built under.
