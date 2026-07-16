# ADR-0028 — Learning Constitution

- **Status:** Proposed
- **Date:** 2026-07-16
- **Supersedes:** nothing. **Amends:** nothing. **Elevates:** ADR-0026 §Stage 11's "Learning principles" (three short paragraphs: Learning consumes Organizational Knowledge, Learning does not consume Runtime Truth directly, Learning does not mutate Organizational Knowledge) into a full constitutional document — exactly as ADR-0024 elevated Historical Truth from ADR-0021 §Stage 3's one paragraph, ADR-0025 elevated Derived Knowledge from that same section, and ADR-0026 itself elevated Organizational Knowledge from ADR-0025 §Stage 9's one table row ("Aggregated Knowledge"). This ADR is that identical act of elevation performed once more, for the tier directly above Organizational Knowledge.
- **Governing design:** none — this ADR *is* the governing design, exactly as ADR-0020, ADR-0021, ADR-0024, ADR-0025, and ADR-0026 introduce no proposal document because none of them is subsystem architecture.
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — reserves CAP-086 inside Layer 2), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — the Truth Hierarchy this ADR sits above), ADR-0024 (Historical Dataset & Historical Truth Constitution — the tier three levels below this one), ADR-0025 (Derived Knowledge Architecture & Layer 2 Constitution — the tier two levels below this one, and the origin of the `LearningResult` forward-reference this ADR gives its first real definition), and ADR-0026 (Organizational Knowledge Architecture & Learning Constitution — the tier immediately below this one, and the source of the brief Learning principles this ADR details in full). Informed by ADR-0027 (Organizational Memory Framework) — the completed, live Layer 2 capability whose `OrganizationalMemoryResult` is the concrete runtime contract this ADR's Learning tier consumes, and whose own closing line certifies the repository "ready for CAP-086A — Learning Framework Architecture & Governance Freeze," the exact point at which a constitutional ADR belongs, ahead of that milestone.
- **Runtime status:** Not applicable. This is a **documentation-only constitutional milestone**: no runtime behaviour, no implementation, no models, no runtime contracts, no `PlatformContext` changes, no policies, no services, no serializers, no Execution Package changes, no manifest changes, no CLI changes, no tests, and no version bumps (Architecture, Platform, or otherwise). It permanently defines what Learning is, what Learned Knowledge is, how Learning is validated, matures, evolves, and relates to every layer around it — it does not build any part of that definition, and it is **not** CAP-086, **not** a `LearningResult`, **not** a `LearningService`, **not** a `LearningPolicy`, and **not** a `PlatformContext` registration. Those remain a future subsystem ADR (CAP-086A) this document exists to govern in advance.

## Scope note

ADR-0020 defines **platform evolution** — the seven layers. ADR-0021 defines **data evolution across time** — the three-level Truth Hierarchy. ADR-0024 completed the constitution for Historical Truth. ADR-0025 completed the constitution for Derived Knowledge and Layer 2 peer independence. ADR-0026 completed the constitution for Organizational Knowledge — the curated, matured tier Organizational Memory (CAP-085, now live per ADR-0027) produces. This ADR completes the constitution for the **next** tier ADR-0025 §Stage 9 first named ("Learned Knowledge") and ADR-0026 §Stage 4/§Stage 11 already positioned and lightly principled but never fully detailed: **Learning** — the reusable organizational understanding a future Learning Framework (CAP-086) will produce from Organizational Knowledge, and the constitutional bridge between Layer 2 (Continuous Learning) and Layer 3 (Feature Engineering). Together, ADR-0020, ADR-0021, ADR-0024, ADR-0025, ADR-0026, and ADR-0028 are the six constitutional documents governing every future platform capability: ADR-0020 answers "where does this capability live?"; ADR-0021 answers "what kind of truth is this capability allowed to touch?"; ADR-0024 answers "how is Historical Truth organized and resolved?"; ADR-0025 answers "what is Layer 2 allowed to produce, and how do its peers relate?"; ADR-0026 answers "how does that production mature into something an organization can trust and act on?"; ADR-0028 answers "what does the organization do with that trust, and how does Layer 2 hand off to Layer 3?"

This is **not** a subsystem ADR. It is **not** CAP-086. It defines no `requirement_intelligence/` package, no `PlatformContext` method, no policy, no model, no service — it defines the platform-wide principles the future CAP-086A architecture freeze inherits, exactly as ADR-0026 did for CAP-085A before it.

---

## Stage 0 — Repository assessment

Before writing this ADR, the following were reviewed in full:

- **ADR-0020** (§Stage 4, Layer 2): reserves CAP-086 (Learning Framework) as the fourth and final named Layer 2 capability, alongside CAP-083 (Continuous Improvement, live), CAP-084 (Knowledge Graph, live), and CAP-085 (Organizational Memory, live per ADR-0027). CAP-086 carries no lifecycle entry — no architecture freeze, no engine, no runtime contract.
- **ADR-0021** (§Stage 3): the Truth Hierarchy — Runtime Truth → Historical Truth → Derived Knowledge — confirmed constitutionally frozen and unaffected by anything since.
- **ADR-0024**: Historical Truth's full constitution — confirmed frozen, unaffected.
- **ADR-0025**: Derived Knowledge's full constitution and Layer 2 peer independence — confirmed frozen. §Stage 4 lists a **future** `LearningResult` in one sentence, alongside `OrganizationalMemoryResult`, purely as an example of "every Derived Knowledge contract not yet named" that must be immutable once produced — a forward-reference inside an illustrative list, not a definition, not a model, not a schema.
- **ADR-0026**: Organizational Knowledge's full constitution — confirmed frozen. §Stage 4 positions "Learning" as the lifecycle rung immediately above "Organizational Knowledge." §Stage 10 names the question Learning Framework alone answers ("What should change?"). §Stage 11 freezes exactly three Learning principles: Learning consumes Organizational Knowledge; Learning does not consume Runtime Truth directly; Learning does not mutate Organizational Knowledge. Nothing else about Learning is defined — no lifecycle of its own, no maturity axis of its own, no validation criteria, no lineage chain, no evolution rule, no relationship to Feature Engineering, Prediction, Optimization, or Organizational Intelligence.
- **ADR-0027**: Organizational Memory Framework — confirmed **Accepted, live**. `OrganizationalMemoryResult` is a real, certified, runtime-active contract (CAP-085A → CAP-085A.1 → CAP-085B → CAP-085B.1 → CAP-085C, all complete). Its closing governance line reads: *"The repository is certified ready for CAP-086A — Learning Framework Architecture & Governance Freeze."* Recommendation 8 of ADR-0027 already freezes that a future Learning Framework "must consume `OrganizationalMemoryResult`, never `ContinuousImprovementResult` or `KnowledgeGraphResult` directly." ADR-0027's own Ownership section states it "does not own any Learning Framework responsibility (ADR-0026 §Stage 11, reserved for CAP-086)."
- **Repository-wide search** for `LearningResult`, `LearningService`, `LearningPolicy`, `learning_framework`, `LearningEngine` across `requirement_intelligence/`, `docs/adr/`, and `docs/proposals/`: the only hit is ADR-0025 §Stage 4's single-sentence forward-reference described above. No package, no module, no class, no test, no proposal document, no `PlatformContext` method exists.
- **`git status`**: working tree clean prior to this milestone. `ruff check .` (via the project's own `.venv`): all checks passed.

**Confirmed:**

- **Organizational Memory is the highest completed Layer 2 capability.** ADR-0027 is Accepted and live; its runtime contract, `OrganizationalMemoryResult`, is real and integrated at the permanently frozen end of the live pipeline.
- **Learning has never been defined** beyond its lifecycle position (ADR-0026 §Stage 4) and three short principles (ADR-0026 §Stage 11). No maturity model, no validation criteria, no lineage chain, no evolution rule, no relationship to Layer 3/4/5/7 has ever been frozen for it.
- **No Learning subsystem exists.** No `requirement_intelligence/learning/` package, no proposal document.
- **No `LearningResult` exists.** The one textual occurrence of the name is a forward-reference example inside ADR-0025 §Stage 4, not a model, not a schema, not code.
- **No `LearningService` exists.** No entry point, abstract or otherwise.
- **No `LearningPolicy` exists.** No governed configuration object.
- **No Learning engine exists.** No deterministic, statistical, ML, or LLM implementation of any kind.
- **No contradiction exists.** Every prior ADR that touches Learning (ADR-0020, ADR-0025, ADR-0026, ADR-0027) does so consistently: Learning is Layer 2, positioned above Organizational Knowledge, consumes Organizational Knowledge only, and remains entirely unbuilt and unconstitutionalized beyond that. Nothing here needs correction.

> No inconsistency found. The repository is exactly where ADR-0027 says it is: ready for a Learning Framework architecture freeze, and — one milestone earlier than that, following the identical precedent ADR-0026 set ahead of CAP-085A — ready for the constitutional document that governs it. Proceeding to freeze that constitution. No redesign performed.

---

## Purpose

This ADR permanently defines:

- **Learning**
- **Learned Knowledge**
- **Learning Validation**
- **Learning Lineage**
- **Learning Evolution**
- **Learning Maturity**
- **Learning Confidence**
- **Learning Promotion**
- **Learning Explainability**
- **Learning Ownership**
- Learning's relationship to **Feature Engineering**
- Learning's relationship to **Prediction**
- Learning's relationship to **Optimization**
- Learning's relationship to **Organizational Intelligence**

This ADR becomes the constitutional document governing CAP-086.

---

## Stage 1 — Define Learning

Permanently defined:

> **Learning is the creation of reusable organizational understanding that permanently improves future reasoning.**

**Learning is organizational understanding** — content, never code, never a rule, never an engine, exactly as ADR-0026 §Stage 1 already froze for Organizational Knowledge one tier below (an engine may produce Learning, and a later engine may read it, but the engine is never part of it).

**Learning is NOT:**

- **Historical storage** — that is the Historical Dataset's exclusive ownership (ADR-0024 §Stage 3); Learning never records what happened, only what should be understood as a result of it.
- **Graph construction** — that is Knowledge Graph's exclusive ownership (ADR-0023 §D1); Learning never projects structure, it consumes conclusions already projected.
- **Recommendation** — that is Layer 1's `Recommendation` (ADR-0019), scoped to one execution; Learning is never execution-scoped.
- **Prediction** — that is a future Layer 4 product (ADR-0020 §Stage 4); Learning precedes Prediction and never performs it (Stage 13).
- **Optimization** — that is a future Layer 5 product; Learning precedes Optimization and never performs it (Stage 14).
- **Decision making** — Learning informs; it never chooses. Choosing is Layer 5's and Layer 6's role (ADR-0020 §Stage 4).
- **Feature Engineering** — Learning prepares understanding; it never computes a numerical representation (Stage 12).

This is not a new invention layered on top of prior ADRs — it is the single, precise name for the lifecycle rung ADR-0025 §Stage 9 called "Learned Knowledge" and ADR-0026 §Stage 4 called "Learning," now given the full definitional treatment those two documents deferred.

---

## Stage 2 — Define Learned Knowledge

Freeze four distinct constitutional levels, permanently:

```
Historical Truth
        ↓
Derived Knowledge
        ↓
Organizational Knowledge
        ↓
Learned Knowledge
```

Each level owns a different responsibility, and **none may substitute for another**:

| Level | Owned by | Answers | Constitution |
|---|---|---|---|
| **Historical Truth** | Historical Dataset (Layer 2, organizing) | *What has happened, across many executions?* | ADR-0024 |
| **Derived Knowledge** | Continuous Improvement, Knowledge Graph (Layer 2) | *What can we infer from history?* | ADR-0025 |
| **Organizational Knowledge** | Organizational Memory (Layer 2, live per ADR-0027) | *What has this organization learned is true?* | ADR-0026 |
| **Learned Knowledge** | Learning Framework (Layer 2, reserved) | *What should this organization now do differently?* | this ADR |

**Learned Knowledge is never Organizational Knowledge, never Derived Knowledge, never Historical Truth, and never Runtime Truth.** It is a distinct, later tier, computed exclusively from Organizational Knowledge (Stage 3), exactly as Organizational Knowledge is computed exclusively from Derived Knowledge (ADR-0026 §Stage 1) and Derived Knowledge exclusively from Historical Truth (ADR-0025 §Stage 1). The chain of exclusive-computation rules is now four levels deep, and every level's rule is identical in shape: consume only the level immediately below, never skip, never reverse.

This definition is frozen permanently.

---

## Stage 3 — Define Learning Ownership

Freeze permanently.

**Learning owns:**

- validated organizational understanding
- generalized organizational behavior
- organizational heuristics
- institutional learning
- organizational adaptation

**Learning owns nothing below Organizational Knowledge.** It never owns a Best Practice's own curation (Organizational Memory's role, ADR-0026 Recommendation 10), never owns recurrence detection (Continuous Improvement's role, ADR-0022), never owns structural projection (Knowledge Graph's role, ADR-0023), never owns Historical Truth's organization (ADR-0024 §Stage 3), and never owns a single execution's Runtime Truth (ADR-0021 §Stage 3). Learning consumes each of those, transitively, through exactly one direct input — Organizational Knowledge (Stage 2) — and owns only what it itself produces from that input.

**Learning owns nothing above itself either.** It never owns a Feature (Layer 3), a Prediction (Layer 4), an Optimization (Layer 5), an Autonomous Decision (Layer 6), or an Organizational Intelligence conclusion (Layer 7) — those remain each their own future layer's exclusive ownership (ADR-0020 §Stage 4; Stages 12–15 below).

---

## Stage 4 — Learning Principles

Freeze permanently:

- **Learning never rewrites history.** No Learning object ever alters a Historical Truth entry, directly or indirectly (extends ADR-0024 §Stage 8, ADR-0025 Recommendation 1, ADR-0026 Recommendation 9 one further tier up).
- **Learning never mutates Organizational Knowledge.** A Learning conclusion is never written back into a `BestPractice`, a `Lesson`, or an `Experience` (restates ADR-0026 §Stage 11's third principle, generalized to every Organizational Knowledge object, not only Best Practices).
- **Learning creates new knowledge.** Every Learning object is newly produced, never an edit of something that already existed (Stage 11).
- **Learning references previous knowledge.** Every Learning object names the Organizational Knowledge it was built from — never floats free of it (Stage 10).
- **Learning remains explainable.** No Learning conclusion may exist that cannot be traced, hop by hop, back to Runtime Truth (Stage 10).
- **Learning is deterministic.** The same Organizational Knowledge, reasoned over by the same governed engine and policy, always produces the same Learning (mirrors ADR-0025 §Stage 1, ADR-0026 §Stage 5, lifted one tier).
- **Learning is reproducible.** Learning is regenerable at any time from the Organizational Knowledge it was computed from, with no dependence on when it was first computed (mirrors ADR-0025 §Stage 1).
- **Learning is append-only.** New Learning is added; no prior Learning is ever removed, rewritten, or silently superseded in place (Stage 11).

These eight principles are the complete, permanent constitution governing every future Learning object, of any maturity, any confidence, any engine implementation.

---

## Stage 5 — Knowledge Promotion Chain

Freeze the constitutional promotion chain permanently:

```
Historical Truth
        ↓
Derived Knowledge
        ↓
Organizational Knowledge
        ↓
Learned Knowledge
```

**Each transition is a promotion.** Historical Truth is promoted into Derived Knowledge by a Layer 2 producer reasoning over it (ADR-0025 §Stage 1). Derived Knowledge is promoted into Organizational Knowledge by Organizational Memory curating it (ADR-0026 §Stage 6, ADR-0027 §D11). Organizational Knowledge is promoted into Learned Knowledge by a future Learning Framework validating it (Stage 6 below).

**Every promotion creates a new immutable object.** Nothing is rewritten. Nothing is replaced. This is not a new rule invented here — it is the same promotion discipline ADR-0021 §Stage 4 froze for executions, ADR-0024 §Stage 8 froze for Historical Truth, ADR-0025 §Stage 4/6 froze for Derived Knowledge, and ADR-0026 §Stage 6 froze for Organizational Knowledge — now confirmed, once more, for the fourth and final tier of this chain. A promotion chain with a weak link at any tier would compromise every tier above it; this stage exists to confirm the chain holds all the way to Learning, with no exception carved out for it.

Freeze this permanently.

---

## Stage 6 — Learning Validation

Freeze permanently what becomes Learning.

**Learning requires:**

- **sufficient Organizational Knowledge** — a single Best Practice, in isolation, is not enough; Learning requires enough curated Organizational Knowledge for a governed engine to reason across more than one Best Practice (the same non-triviality floor ADR-0026 §Stage 3's `Verified` threshold and ADR-0027's governed minimums already apply one tier below);
- **validated evidence** — every input Best Practice must itself already carry the `Verified` maturity level or higher (ADR-0026 §Stage 3) before Learning may consume it; Learning never reasons over merely `Observed` or `Repeated` Organizational Knowledge;
- **repeatability** — the same Organizational Knowledge, reasoned over under the same governed policy, must yield the same Learning every time (Stage 4);
- **organizational confidence** — a Learning candidate must clear a governed confidence threshold before it may be promoted to validated Learning (Stage 9);
- **organizational usefulness** — a Learning candidate must be actionable at the organizational level, not merely descriptive (mirrors the Lesson/Best Practice distinction ADR-0026 §Stage 2 already draws between "descriptive" and "prescriptive" rungs, lifted one tier: Learning is never merely an observation about Organizational Knowledge, it is a conclusion about what should change);
- **complete explainability** — a Learning candidate that cannot reconstruct its full lineage (Stage 10) is not validated and must not be constructible.

**Learning is validated. Learning is never speculative.** A Learning object that has not cleared every one of these gates does not exist as Learning — it remains, at most, an unvalidated Learning Candidate (Stage 7), never promoted, never consumed by anything above it.

Freeze this permanently.

---

## Stage 7 — Learning Lifecycle

Freeze permanently:

```
Observation
        ↓
Experience
        ↓
Lesson
        ↓
Best Practice
        ↓
Organizational Knowledge
        ↓
Learning Candidate
        ↓
Validated Learning
        ↓
Institutional Learning
        ↓
Reusable Organizational Learning
```

**Reading this lifecycle.** The first five rungs — Observation through Organizational Knowledge — are exactly ADR-0026 §Stage 2's Knowledge Hierarchy, unmodified and uninterrupted (this ADR neither renames nor restructures a single rung of it). The four new rungs above Organizational Knowledge are this ADR's own:

| Rung | Definition | Who creates it | Who consumes it |
|---|---|---|---|
| **Learning Candidate** | A proposed conclusion about what should change, drawn from one or more Best Practices, not yet validated (Stage 6 not yet cleared). | A future Learning Framework (CAP-086) | The same capability's own validation step |
| **Validated Learning** | A Learning Candidate that has cleared every Stage 6 gate — sufficient, validated, repeatable, confident, useful, explainable. | A future Learning Framework, after validation | Institutional adoption, or superseding Learning |
| **Institutional Learning** | Validated Learning actively consulted by downstream capabilities as governing understanding — the Learning-tier analogue of ADR-0026 §Stage 3's `Institutionalized` maturity level. | A future Learning Framework, after institutional adoption | Every future consumer of Learning |
| **Reusable Organizational Learning** | The complete, curated body of Institutional Learning an organization can explain, trust, and reuse across future reasoning — the tier this entire ADR constitutionally governs. | A future Learning Framework (CAP-086) | Feature Engineering (Stage 12), and every layer above it |

No stage is skipped, and no stage is reordered — the same discipline ADR-0020 §Stage 8 froze for a capability's lifecycle, ADR-0021 §Stage 12 froze for data's lifecycle, and ADR-0025 §Stage 9/ADR-0026 §Stage 4 froze for knowledge's lifecycle, now extended one further, final tier.

---

## Stage 8 — Learning Maturity

Freeze permanently:

```
Candidate
        ↓
Observed
        ↓
Validated
        ↓
Trusted
        ↓
Institutional
        ↓
Standard
        ↓
Retired
```

**Maturity measures adoption. Not evidence.** This is a distinct axis from ADR-0026 §Stage 3's Organizational Knowledge maturity ladder (`Observed → Repeated → Verified → Institutionalized → Retired`) — that ladder measures how far a piece of *Organizational Knowledge* has progressed toward institutional trust; this ladder measures how far a piece of *Learning* has progressed toward organization-wide adoption, one tier above it. A `Candidate` Learning object has been proposed but not yet examined. `Observed` Learning has been examined at least once. `Validated` Learning has cleared Stage 6 in full. `Trusted` Learning has been validated and has additionally been relied upon without contradiction across more than one subsequent reasoning cycle. `Institutional` Learning is actively consulted as governing understanding. `Standard` Learning has become the default assumption new reasoning is built on top of, absent a specific reason to deviate. `Retired` Learning is no longer actively consulted, but — exactly as ADR-0026 §Stage 7 already freezes for Organizational Knowledge — never deleted.

**Learning evolves upward. Never downward.** Learning that reaches `Trusted` never reverts to `Observed`; if new evidence contradicts it, the old maturity record stays exactly as it was, and a new, superseding Learning object is produced instead (Stage 11), carrying its own maturity level from the start — the identical discipline ADR-0026 §Stage 3 already freezes one tier below.

Freeze this permanently.

---

## Stage 9 — Learning Confidence

Freeze permanently:

**Confidence measures evidence. Maturity measures organizational adoption.** These are orthogonal axes, exactly as ADR-0026 §Stage 8 already freezes for Organizational Knowledge one tier below: a newly-proposed Learning Candidate can carry high confidence if its underlying Best Practices are already deeply `Verified`; a long-`Institutional` piece of Learning can, in principle, still carry only medium confidence if the Organizational Knowledge base beneath it has not grown since institutionalization.

**Confidence may increase. Maturity may remain unchanged.** Accumulating more corroborating Organizational Knowledge can raise a Learning object's confidence without moving it a single rung up the maturity ladder (Stage 8) — adoption is a separate, deliberate, organizational act, never an automatic consequence of rising confidence. Confidence itself follows the same append-only discipline as everything else in this constitution: a confidence change is never a mutation of an existing Learning object's recorded content, it is the production of a **new** Learning object carrying the updated confidence and referencing the one it supersedes (mirrors ADR-0026 §Stage 8's identical rule for Organizational Knowledge confidence).

**Freeze independence.** Confidence and maturity are tracked independently and neither substitutes for the other, permanently.

---

## Stage 10 — Learning Lineage

Freeze permanently. Every Learning object must reconstruct:

```
Learning
        ↓
Organizational Knowledge
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

**Learning without lineage is forbidden.** This chain is not a new invention — the first eight hops (Learning down through Runtime Truth) are exactly ADR-0027 §D13's already-frozen explainability chain (`Best Practice → Lesson → Experience → Continuous Improvement OR Knowledge Graph → Historical Dataset → Execution Ids → Runtime Truth`), with exactly one new hop added at the top (`Learning → Organizational Knowledge`). A Learning object that cannot name the specific Organizational Knowledge (Best Practice, and transitively Lesson and Experience) it was built from, and through it the specific Historical Dataset entries and Runtime Truth executions those objects ultimately reference, is not explainable and must not be constructible — the same "at least one reference" discipline ADR-0019 §D7 first froze for a single `Recommendation`, and every intervening ADR (ADR-0021 §Stage 8, ADR-0025 Stage 5, ADR-0026 §Stage 9, ADR-0027 §D13) has required, unbroken, at every tier since.

Freeze this permanently.

---

## Stage 11 — Learning Evolution

Freeze permanently:

**Learning never mutates.** Once produced, a Learning object — at any maturity level, any confidence level — is never modified.

**Learning creates successor Learning.** A correction, an update, or a re-validation over more recent Organizational Knowledge is a **new** Learning object with its own identity, its own maturity, its own confidence, referencing the Learning object it supersedes — never an in-place edit of the old one (mirrors ADR-0021 §Stage 4's execution immutability, ADR-0024 §Stage 8's append-only Historical Truth, ADR-0025 §Stage 4/6's Derived Knowledge immutability, and ADR-0026 §Stage 6's Organizational Knowledge promotion discipline — the same non-negotiable pattern, now frozen for its fifth tier running).

**Previous Learning remains immutable.** The old object remains exactly as it was: an accurate record of what was validated from the Organizational Knowledge available at the time it was produced.

Freeze append-only evolution permanently.

---

## Stage 12 — Relationship to Feature Engineering

Freeze permanently:

**Learning prepares reusable understanding. Feature Engineering consumes Learning.** Layer 3 (ADR-0020 §Stage 4) transforms "Layer 1's completed results, and Layer 2's historical aggregates" into numerical feature vectors — and Learning, as the terminal Layer 2 tier (Stage 16), is the most refined of those aggregates a Feature Engineering capability may draw on.

**Learning never computes features.** No Learning object ever produces a `FeatureResult` or any numerical representation — that is Layer 3's exclusive ownership (ADR-0020 §Stage 4).

**Feature Engineering never creates Learning.** No Layer 3 capability ever produces a Learning object, a Learning Candidate, or any object at or below the Learning tier — Layer 3 consumes Learning, it never originates it, exactly as Layer 3 already never originates Derived Knowledge or Organizational Knowledge (ADR-0025 §Stage 3, ADR-0026 Recommendation 11).

---

## Stage 13 — Relationship to Prediction

Freeze permanently:

**Prediction consumes Learning.** A future Layer 4 `PredictionResult` (ADR-0020 §Stage 4) is explainable, transitively, through the Layer 3 `FeatureResult` inputs it names and, through them, the Learning those features were built from (Stage 10's chain, extended one further tier by Layer 3's own explainability rule, ADR-0020 §Stage 7).

**Learning never consumes Prediction.** No Learning object, of any maturity or confidence, ever reads a `PredictionResult` as an input — the reverse-dependency prohibition ADR-0020 §Stage 5 freezes between numbered layers, restated here explicitly for the Layer 2 tier this ADR governs.

Freeze dependency direction permanently.

---

## Stage 14 — Relationship to Optimization

Freeze permanently:

**Optimization consumes Prediction.** A future Layer 5 `OptimizationResult` chooses among Layer 4's estimated outcomes (ADR-0020 §Stage 4).

**Learning never consumes Optimization.** No Learning object ever reads an `OptimizationResult` — Optimization is three layers downstream of Learning (Layer 2 → Layer 3 → Layer 4 → Layer 5), and the reverse-dependency prohibition (ADR-0020 §Stage 5) applies across every one of those hops, not merely the adjacent one.

Freeze dependency direction permanently.

---

## Stage 15 — Relationship to Organizational Intelligence

Freeze permanently:

**Learning prepares intelligence. Learning is not intelligence.** Layer 7 (Organizational Intelligence, ADR-0020 §Stage 4) reasons across an organization's entire portfolio of platform-governed projects — Learning is one project's own Layer 2 conclusion about what should change, a necessary input several layers below Layer 7, never itself a cross-project conclusion.

Freeze this distinction permanently.

---

## Stage 16 — Layer 2 Completion Principle

Freeze permanently:

**Continuous Improvement, Knowledge Graph, Organizational Memory, and Learning collectively complete Layer 2.** Every capability ADR-0020 §Stage 4 reserved inside Continuous Learning now has a constitutional definition: Continuous Improvement and Knowledge Graph produce Derived Knowledge (ADR-0025, both live); Organizational Memory produces Organizational Knowledge (ADR-0026, live per ADR-0027); Learning produces Learned Knowledge (this ADR, reserved as CAP-086). No fifth Layer 2 capability is anticipated or required by this constitution — Layer 2's own question set (ADR-0026 §Stage 10: "What repeats?", "What connects?", "What deserves to be remembered?", "What should change?") is exhaustive by construction.

**Feature Engineering is the first Layer 3 capability.** Nothing in Layer 2 answers "how do we represent this numerically?" (ADR-0026 §Stage 10) — that question belongs entirely to Layer 3, and only Layer 3.

**No future Layer 2 capability may bypass Learning.** Any future capability that reasons over more than one execution and answers a question already answered by Continuous Improvement, Knowledge Graph, Organizational Memory, or Learning duplicates an existing owner and violates ADR-0025 Recommendation 15/ADR-0026 §Stage 10's single-owner-per-responsibility principle. A future capability that reasons over Organizational Knowledge to produce something Feature Engineering could consume, without going through Learning, would silently reintroduce the exact ad hoc risk ADR-0021 §Stage 2 and ADR-0027's own Problem section warn against — a second, competing "what should change" record.

**Learning is the constitutional bridge from Continuous Learning to Feature Engineering.** It is the last tier of Layer 2 (Stage 2, Stage 7) and the sole sanctioned entry point Layer 3 may use to consume Layer 2's most refined conclusion (Stage 12). This is the platform's single most load-bearing statement about where Layer 2 ends and Layer 3 begins.

---

## Stage 17 — Future Engine Replaceability

Freeze permanently:

Future **deterministic**, **ML**, **LLM**, **GraphRAG**, **neuro-symbolic**, **RL**, and **hybrid** engines must all produce identical Learning contracts. Whatever technique a future Learning Framework engine uses to validate a Learning Candidate, promote it to Validated Learning, or institutionalize it as Reusable Organizational Learning, the object it produces must still satisfy Stage 1's definition, Stage 6's validation gates, Stage 8's maturity levels, Stage 9's confidence/maturity separation, Stage 10's lineage chain, and Stage 11's append-only evolution — exactly as ADR-0025 Stage 10/Recommendation 12 and ADR-0026 §Stage 13/Recommendation 14 already froze this identical guarantee for every tier below this one.

**Implementations change. Contracts remain permanent.**

---

## Stage 18 — Constitutional Recommendations

Freeze permanently.

### Recommendation 1 — Learning never owns Runtime Truth

Learning never touches a Layer 1 execution record directly (Stage 3; extends ADR-0021 §Stage 3, ADR-0025 Stage 1, ADR-0026 §Stage 11).

### Recommendation 2 — Learning never owns Historical Truth

Learning never touches the Historical Dataset directly, and never writes back into it (Stage 3, Stage 4; extends ADR-0024 §Stage 3, ADR-0025 Recommendation 1, ADR-0026 Recommendation 9).

### Recommendation 3 — Learning never owns Derived Knowledge

Learning never re-derives, mutates, or competes with `ContinuousImprovementResult` or `KnowledgeGraphResult` (Stage 3; extends ADR-0025 §Stage 3).

### Recommendation 4 — Learning never owns Organizational Knowledge

Learning never re-curates, promotes, or retires a `BestPractice`, `Lesson`, or `Experience` on Organizational Memory's behalf (Stage 3, Stage 4; extends ADR-0026 Recommendation 10, ADR-0027 Recommendation 1).

### Recommendation 5 — Learning creates Learned Knowledge

Learning is the sole, exclusive producer of the tier this ADR names Learned Knowledge (Stage 2, Stage 3).

### Recommendation 6 — Learning is append-only

New Learning supersedes; it never overwrites (Stage 8, Stage 11).

### Recommendation 7 — Learning is reproducible

The same Organizational Knowledge, under the same governed policy, always yields the same Learning (Stage 4, Stage 6).

### Recommendation 8 — Learning is explainable

Every Learning object reconstructs its complete lineage back to Runtime Truth, with no hidden inference (Stage 10).

### Recommendation 9 — Learning precedes Feature Engineering

No Layer 3 capability may consume anything Layer 2 has not already validated as Learning where a Learning-tier conclusion is the input required (Stage 12, Stage 16).

### Recommendation 10 — Learning precedes Prediction

No Layer 4 capability may skip past Feature Engineering and Learning to reach Organizational Knowledge, Derived Knowledge, or Historical Truth directly (Stage 13; extends ADR-0020 §Stage 5's no-skip rule).

### Recommendation 11 — Learning precedes Optimization

No Layer 5 capability may consume Learning, Organizational Knowledge, Derived Knowledge, or Historical Truth directly, bypassing Prediction (Stage 14; extends ADR-0020 §Stage 5).

### Recommendation 12 — Learning precedes Organizational Intelligence

No Layer 7 capability may treat a single project's Learning as if it were already cross-project intelligence (Stage 15).

### Recommendation 13 — Learning contracts evolve independently

A future `LearningResult` schema version, a future `LearningPolicy` version, and a future Learning engine's own internal version all evolve on independent axes, exactly as every prior runtime contract's version axes already do (mirrors ADR-0021 §Stage 9, ADR-0027 §D18's version-axis independence).

### Recommendation 14 — Learning engines are replaceable

Every future Learning engine variant — deterministic, ML, LLM, GraphRAG, neuro-symbolic, RL, hybrid — must implement an identical frozen contract without changing its shape (Stage 17).

### Recommendation 15 — Learning requires validation

No Learning Candidate may be treated as Learning until it clears every Stage 6 gate (Stage 6, Stage 7).

### Recommendation 16 — Learning requires lineage

No Learning object may exist without a complete, reconstructable chain back to Runtime Truth (Stage 10).

### Recommendation 17 — Learning promotion is immutable

Every promotion in the Knowledge Promotion Chain (Stage 5) and every maturity/confidence transition (Stage 8, Stage 9) produces a new object; none rewrites a prior one.

### Recommendation 18 — Learning completes Layer 2

Continuous Improvement, Knowledge Graph, Organizational Memory, and Learning together exhaust Layer 2's responsibilities; no fifth Layer 2 capability is required or anticipated by this constitution (Stage 16).

### Recommendation 19 — Learning is the sole bridge to Feature Engineering

Layer 3 must reach Layer 2 exclusively through Learning's frozen runtime contract wherever a Layer 2 conclusion more refined than a single Derived Knowledge or Organizational Knowledge object is required — never by reaching past Learning to an earlier Layer 2 tier for that purpose (Stage 12, Stage 16).

### Recommendation 20 — Learning never becomes evidence for itself

A future Learning object is never fed back into Organizational Knowledge, Derived Knowledge, or Historical Truth as if it were newly-observed evidence, and no Learning engine may recursively consume a prior Learning object's own successor chain as if it were independent corroborating Organizational Knowledge (extends ADR-0025 Recommendation 8, ADR-0026 Recommendation 8, one further tier up).

---

## Stage 19 — Cross References

`docs/adr/0020-platform-evolution-roadmap.md` §Layer 2 — Continuous Learning is updated to add ADR-0028 alongside its existing ADR-0021/ADR-0024/ADR-0025/ADR-0026 constitutional-foundation citation. No roadmap restructuring: the CAP-083/084/085/086 lifecycle lines, capability list, and layer ordering are unchanged — this is a citation addition only.

`docs/adr/0026-organizational-knowledge-architecture.md` is updated to add a one-way pointer to ADR-0028, noting explicitly that ADR-0026 defines **Organizational Knowledge** and freezes Learning's earliest principles (§Stage 11) while ADR-0028 gives **Learning** its own full constitutional treatment. **No constitutional rule inside ADR-0026 is modified** — every Stage, every Recommendation, and §Stage 11's own three principles remain exactly as ADR-0026 froze them; this is a citation addition only.

`docs/adr/0027-organizational-memory-framework.md` is updated to add a one-way pointer to ADR-0028, noting that the Learning Framework responsibility ADR-0027's own Ownership section already disclaims ("reserved for CAP-086") is now constitutionally governed by ADR-0028 ahead of CAP-086A. **No rule inside ADR-0027 is modified** — its Accepted status, its live runtime position, and every Recommendation remain exactly as frozen; this is a citation addition only.

No restructuring. Only additive references.

---

## Stage 20 — Verification

This milestone is documentation only. Verified:

- zero runtime changes — no file under `requirement_intelligence/` was touched;
- zero model changes — no Pydantic model, dataclass, or contract was added or modified;
- zero policy changes — no `*Policy` class or governed default was touched;
- zero `PlatformContext` changes — `platform_context.py` was not touched;
- zero service changes — no `*Service` class was added or modified;
- zero serializer changes — no `serialization/` package was added or modified;
- zero Execution Package changes — `execution_data.py`, `execution_writer.py`, `manifest_builder.py` were not touched;
- zero CLI changes — `scripts/run_requirement_analysis.py` was not touched;
- zero test changes — no test file was added or modified;
- zero golden changes — the golden dataset and its version are unchanged;
- zero version bumps — Architecture Version (`1.2.0`), Platform Version (`1.0.0`), and every existing runtime contract/policy/framework version are unchanged.

`ruff check .` (via the repository's own `.venv`): all checks passed, both before and after this change — no Python file is touched by this milestone, so this result is unaffected by construction. The repository remains byte-identical outside four documentation files: this new ADR, and the citation additions to ADR-0020, ADR-0026, and ADR-0027.

---

## Final Constitutional Review

1. **Is Learning permanently defined?** Yes — Stage 1: the creation of reusable organizational understanding that permanently improves future reasoning; explicitly not historical storage, graph construction, recommendation, prediction, optimization, decision making, or feature engineering.
2. **Is Learned Knowledge permanently defined?** Yes — Stage 2: the fourth constitutional level, Historical Truth → Derived Knowledge → Organizational Knowledge → Learned Knowledge, each owned by a distinct capability, none substitutable for another.
3. **Is the Knowledge Promotion Chain permanently frozen?** Yes — Stage 5: four one-way promotions, each producing a new immutable object, nothing rewritten, nothing replaced.
4. **Is Learning Validation permanently frozen?** Yes — Stage 6: sufficiency, validated evidence, repeatability, confidence, usefulness, and complete explainability are all required before a Learning Candidate becomes Learning; Learning is never speculative.
5. **Is Learning Lineage permanently frozen?** Yes — Stage 10: Learning → Organizational Knowledge → Best Practice → Lesson → Experience → (Continuous Improvement or Knowledge Graph) → Historical Dataset → Execution Ids → Runtime Truth, extending ADR-0027 §D13's chain by exactly one hop; Learning without lineage is forbidden.
6. **Is Learning distinct from Organizational Memory?** Yes — Stage 2/Stage 3: Organizational Memory produces Organizational Knowledge; Learning produces Learned Knowledge, a distinct, later tier, computed exclusively from Organizational Knowledge, never confused with a `BestPractice`, `Lesson`, or `Experience` itself.
7. **Is Learning distinct from Feature Engineering?** Yes — Stage 12: Learning prepares reusable understanding; Feature Engineering consumes it and computes numerical representations; neither performs the other's role.
8. **Is Learning maturity permanently frozen?** Yes — Stage 8: Candidate → Observed → Validated → Trusted → Institutional → Standard → Retired, upward only, never downward; a distinct axis from ADR-0026 §Stage 3's Organizational Knowledge maturity, one tier above it.
9. **Is Learning confidence permanently frozen?** Yes — Stage 9: confidence measures evidence, maturity measures adoption, the two axes are independent and neither substitutes for the other.
10. **Is Learning evolution permanently frozen?** Yes — Stage 11: Learning never mutates; corrections and updates create successor Learning; previous Learning remains immutable.
11. **Is Layer 2 constitutionally complete?** Yes — Stage 16: Continuous Improvement, Knowledge Graph, Organizational Memory, and Learning collectively exhaust Layer 2's question set; no fifth Layer 2 capability is anticipated by this constitution.
12. **Is Learning permanently defined as the bridge to Layer 3?** Yes — Stage 12, Stage 16: Learning is the sole sanctioned Layer 2 → Layer 3 entry point wherever a fully-matured Layer 2 conclusion is required.
13. **Are dependency directions permanently frozen?** Yes — Stage 12/13/14/15: Feature Engineering consumes Learning (never the reverse); Prediction consumes Learning transitively through Features (never the reverse); Optimization consumes Prediction (never Learning directly); Organizational Intelligence sits three layers above Learning and never treats it as already cross-project.
14. **Are implementations permanently replaceable?** Yes — Stage 17/Recommendation 14: deterministic, ML, LLM, GraphRAG, neuro-symbolic, RL, and hybrid engines must all produce identical Learning contracts.
15. **Does this introduce zero runtime behavior?** Confirmed — Stage 20: documentation-only diff across four files; `ruff check .` passes, unaffected by construction, since no Python file is touched.
16. **Is the repository constitutionally ready for CAP-086A?** Yes. A future Learning Framework architecture milestone may now cite this ADR directly for Learning's definition, the four-level Knowledge Promotion Chain, validation gates, lineage chain, maturity/confidence model, evolution discipline, and every cross-layer relationship — without re-deriving any of them, exactly as CAP-085A was able to cite ADR-0026 directly instead of re-deriving Organizational Knowledge's own constitution.

---

## Ownership, scope, and governance

- **Owns:** the definition of Learning (Stage 1), the four-level Knowledge Promotion Chain and Learned Knowledge's position within it (Stage 2, Stage 5), Learning ownership (Stage 3), Learning's eight core principles (Stage 4), Learning Validation (Stage 6), the Learning Lifecycle's four new rungs above Organizational Knowledge (Stage 7), Learning Maturity (Stage 8), Learning Confidence (Stage 9), Learning Lineage (Stage 10), Learning Evolution (Stage 11), Learning's relationship to Feature Engineering, Prediction, Optimization, and Organizational Intelligence (Stages 12–15), the Layer 2 Completion Principle (Stage 16), and future Learning engine replaceability (Stage 17).
- **Does not own:** the Truth Hierarchy or its lower three levels (Runtime Truth, Historical Truth, and Derived Knowledge remain ADR-0021's, ADR-0024's, and ADR-0025's, unmodified); Organizational Knowledge, its hierarchy, maturity, promotion, retirement, or confidence model (remain ADR-0026's, unmodified); any Layer 1 runtime contract, policy, engine, orchestration, or Execution Package (ADR-0011 through ADR-0019); the actual layer definitions or dependency rules (remain ADR-0020's, unmodified); Organizational Memory's own architecture, engine, or runtime contract (remain ADR-0027's, live, unmodified); any concrete Learning Framework, Feature Engineering, Prediction, Optimization, Autonomous Engineering, or Organizational Intelligence implementation (reserved future work, not introduced here).
- **Governance:** registered alongside ADR-0020, ADR-0021, ADR-0024, ADR-0025, and ADR-0026 as a platform constitutional document. **Proposed** — it becomes **Accepted** once a future capability (starting with CAP-086A — Learning Framework Architecture & Governance Freeze) is built directly against it without deviation, exactly as ADR-0026 became the standard CAP-085A was built under.
