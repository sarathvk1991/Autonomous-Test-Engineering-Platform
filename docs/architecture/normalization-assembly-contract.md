# Normalization Assembly Contract

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Internal Collaboration Contract |
| Status               | Approved — Foundational — **FROZEN**                              |
| Scope                | The **internal** collaboration of the five normalization stages inside the `ResponseNormalizer` boundary — how their intermediate facts flow through a transient **Assembly State** before the immutable `ParsedResponse` is assembled |
| Governs              | Assembly State identity · stage collaboration · intermediate-fact ownership · assembly lifecycle · assembly invariants · Assembly State creation and destruction · single assembly · non-leakage |
| Depends on           | Response Normalization Contract · Response Normalizer Architecture · Normalization Responsibility Catalog · Validation Canonical Models (`ParsedResponse`) · ADR-0002 |
| Audience             | Solution Architects · Technical Architects · Platform Engineers · Lead Engineers · QA Architects |
| Implementation-bound | No — valid regardless of language, framework, serialization format, algorithm, or AI provider |

> **Architectural Decision**
> This document defines **only** the internal collaboration contract inside the
> `ResponseNormalizer` boundary established by **ADR-0002**. It is **not** a
> framework document, **not** a `ParsedResponse` document, **not** the Response
> Normalizer Architecture, **not** the Responsibility Catalog, and **not** an
> implementation guide. It governs *how the five internal normalization stages
> exchange intermediate facts*, and nothing else. What each stage *is* remains
> governed by the Normalization Responsibility Catalog; *what the `ParsedResponse`
> holds* remains governed by the Validation Canonical Models; *how the framework
> executes generically* remains governed by the Response Normalization Framework.

---

## 1. Design Review Outcome (performed before this contract was written)

This contract was written only after a full review of every frozen artifact it
depends on. The review's findings:

1. **Every stage's input/output is fully defined.** The Normalization
   Responsibility Catalog §5 defines each stage's abstract inputs and outputs, and
   Validation Canonical Models §8.1 defines the five `ParsedResponse` attributes.
   What was *missing* — and what this contract adds — is the **medium** through
   which one stage's intermediate fact reaches the next: the Assembly State (§3).

2. **Every fact has exactly one owner; no ownership is duplicated.** Normalized
   Structure → `0001`; Normalization Outcome → `0002`; Normalization Observations →
   `0003` (owned by the `NormalizationResult`, **not** the `ParsedResponse`); Source
   Reference → `0004`; the assembled `ParsedResponse` → `0005`. `0005` composes the
   structure, outcome, and source reference — it never re-derives any of them.

3. **Every stage can be implemented independently after this contract exists.**
   Each stage is written against the Assembly State's read/write contract (§6); no
   stage needs to know how another is implemented, only which fact it may read and
   which it must write.

4. **No remaining ambiguity about collaboration.** The only previously-undefined
   element — the intermediate medium — is now defined and bounded (§3, §4). The
   composition of this internal collaboration with the generic framework pipeline
   remains governed by the Response Normalizer Architecture and ADR-0002 and is
   deliberately **out of scope** here.

5. **No hidden cycles.** The dependency graph is a DAG: `0001 → 0002`, `0001 →
   0003`, `0004` independent, and `0005 ← {0001, 0002, 0004}`. `0005` does **not**
   depend on `0003`. There is no back-edge; the graph is acyclic (§7).

6. **`ParsedResponse` remains immutable.** The Assembly State is the *mutable
   working medium*; `0005` reads finalized facts from it and assembles the
   *immutable* `ParsedResponse` as an output that is handed out of the boundary. The
   `ParsedResponse` never references the Assembly State, and the Assembly State is
   destroyed after `0005` (§3, §6, §7). Mutable working state and an immutable
   product coexist without conflict.

7. **Nothing here becomes a canonical model.** The Assembly State is explicitly a
   transient, boundary-local working medium — never a canonical model, never
   returned, never stored, never shared (§3). This is a frozen prohibition (§12).

**No contradiction with any frozen document was found.** This contract is
consistent with the Response Normalization Contract, the Response Normalizer
Architecture, the Normalization Responsibility Catalog, the `ParsedResponse`
canonical model, the Validation Canonical Models, and ADR-0002 (§13).

---

## 2. Purpose

### 2.1 Why the Assembly Contract exists

Per **ADR-0002**, the `ResponseNormalizer` internally coordinates **five
architectural stages** (`NORMALIZATION-0001…0005`, governed by the Normalization
Responsibility Catalog). Those stages are **not** framework execution units; the
generic Response Normalization Framework never sees them.

During one normalization, the stages **exchange intermediate facts**: `0002` reads
the structure `0001` recovered; `0005` reads the structure, outcome, and source
reference produced by `0001`, `0002`, and `0004`. That exchange needs a medium —
and, because the framework must **never** know those intermediate facts (ADR-0002,
principle 7), the medium must live **entirely inside the `ResponseNormalizer`
boundary** and be governed by its own contract. This document is that contract.

### 2.2 What it is not

| It is not | Because |
| --------- | ------- |
| A framework document | The framework is generic and unaware of these facts (ADR-0002). |
| A `ParsedResponse` document | The representation's *shape* is governed by Validation Canonical Models §8. |
| The Response Normalizer Architecture | Orchestration, profile, configuration, and exception translation live there. |
| The Responsibility Catalog | *What each stage is* and *the frozen order* live there (§4, §5). |
| An implementation guide | It defines the collaboration contract, never a mechanism, algorithm, or data structure. |

> **Architectural Decision — the Assembly Contract governs collaboration, never
> implementation.** It states *which* fact each stage may read and must write, and
> *when*. *How* a stage recovers structure, determines an outcome, or assembles the
> representation is implementation, free to evolve beneath this contract.

---

## 3. The Assembly State

The **Assembly State** is the transient, boundary-local medium through which the
five stages exchange intermediate facts during a single normalization execution.

| Property | Statement |
| -------- | --------- |
| **Not a canonical model** | It is **never** a canonical model and must never become one. It has no version, no shared identity, and no cross-platform contract. |
| **Mutable** | Unlike the `ParsedResponse`, it is a working medium: stages append their facts to it as execution proceeds. |
| **Not shared** | It exists only inside the `ResponseNormalizer` boundary; no consumer, no framework component, and no downstream subsystem ever receives it. |
| **Not stored** | It is never persisted, cached, logged as an artifact, or reused across runs. |
| **Not returned** | It is never returned from the `ResponseNormalizer`; the run returns a `NormalizationResult`, never the Assembly State. |
| **Execution-local** | Exactly one Assembly State exists per normalization execution; it is created when the execution begins. |
| **Ceases to exist after `0005`** | Once `0005` has assembled the `ParsedResponse`, the Assembly State is discarded. It does not outlive the execution that created it. |

> **Architectural Decision — the Assembly State is transient working memory, never a
> canonical model.** The platform has exactly two normalization outputs that persist
> beyond a run: the immutable, shared `ParsedResponse` and the `NormalizationResult`
> that aggregates it. The Assembly State is neither. Making it a canonical model
> would give the same facts two homes (violating single-ownership), expose internal
> collaboration outside the boundary (violating ADR-0002), and couple consumers to
> the `ResponseNormalizer`'s internals. It is created, used, and destroyed within
> one execution — deliberately.

---

## 4. Assembly State Ownership

The Assembly State may contain **only** the intermediate facts the stages need to
collaborate, plus transient bookkeeping.

**Allowed**

| Allowed content | Why it is permitted |
| --------------- | ------------------- |
| **Normalized structure** | The intermediate fact `0001` produces and `0002`, `0003`, and `0005` read. |
| **Normalization outcome** | The intermediate fact `0002` produces and `0005` reads. |
| **Source reference** | The intermediate fact `0004` produces and `0005` reads. |
| **Captured observations (transient)** | The facts `0003` produces; held transiently until handed to the `NormalizationResult`. They are **never** read by `0005` and **never** enter the `ParsedResponse`. |
| **Internal assembly metadata** | Boundary-local bookkeeping (e.g. which stages have completed) that never leaves the boundary. |
| **Transient execution facts** | Any other short-lived fact a stage needs to pass forward, discarded with the Assembly State. |

**Forbidden**

| Forbidden content | Its one true owner (elsewhere) |
| ----------------- | ------------------------------ |
| **`ParsedResponse`** | It is the *output* of `0005`, an immutable Shared Platform Artifact carried by the `NormalizationResult` — never stored back into the working medium (Canonical Models §8; Contract §6). |
| **`ValidationIssue`** | A **judgment**, owned by the validation subsystem across the frozen §10 boundary. Normalization produces facts, never issues. |
| **Severity** | A validation judgment (Contract §10). |
| **Verdict** | A validation judgment (Contract §10). |
| **Recommendation** | A validation judgment (Contract §10). |
| **Statistics** | Operational telemetry owned by `NormalizationStatistics` on the `NormalizationResult`. |
| **Execution Context** | Execution identity owned by `NormalizationExecutionContext` (Response Normalizer §10). |
| **Framework Metadata** | Framework provenance owned by `NormalizationFrameworkMetadata`. |
| **Provider information** | Provider payloads/strings are excluded platform-wide; normalization is provider-independent (Contract §3.3, §11). |
| **Business information** | Domain meaning belongs to downstream layers; normalization never transforms business meaning (Contract §4.2). |

> **Architectural Decision — the Assembly State carries intermediate facts, never
> judgments, telemetry, provenance, or products.** Every forbidden item already has
> exactly one canonical owner. Admitting any of them into the Assembly State would
> either duplicate an owner (statistics, execution context, framework metadata),
> cross the frozen Normalization–Validation boundary (issue, severity, verdict,
> recommendation), reintroduce provider/business coupling, or fold the immutable
> product back into mutable working memory (`ParsedResponse`). The Assembly State
> holds only what the *next stage* must read — nothing durable, nothing judged.

---

## 5. Stage Collaboration Lifecycle

```text
   LLMResponse
        │
        ▼
   Assembly State created                 (transient · boundary-local)
        │
        ▼
   0001  recover canonical structure       ── writes ─► normalized structure
        │
        ▼
   0002  determine outcome                 ── reads structure · writes outcome
        │
        ▼
   0003  capture observations              ── reads structure · writes observations
        │                                     (transient → NormalizationResult)
        ▼
   0004  create source reference           ── reads original · writes source reference
        │
        ▼
   0005  assemble ParsedResponse           ── reads structure + outcome + source ref
        │                                     (NOT observations) → immutable ParsedResponse
        ▼
   NormalizationResult                     aggregates ParsedResponse + observations + telemetry
        │
        ▼
   Assembly State destroyed                (ceases to exist after 0005)
```

Each transition is a **write of exactly one owned fact** to the Assembly State (or,
for `0003`, the transient observation set destined for the `NormalizationResult`),
followed by the next stage's **read** of the facts already present. The order is
the frozen catalog chain (Catalog §4, §8); it is enforced **inside** the
`ResponseNormalizer` (ADR-0002), never by the framework.

> **Note.** `0003`'s observations flow to the `NormalizationResult`, **not** into
> the `ParsedResponse` `0005` assembles — the single-owner rule made concrete
> (Canonical Models §8.1; Catalog §6). This is why `0005` depends on `0001`, `0002`,
> and `0004`, but **not** on `0003`.

---

## 6. Stage Contracts

Each contract below governs a stage's collaboration through the Assembly State
only. A stage's *concern, identity, dependencies, and non-responsibilities* remain
governed by the Normalization Responsibility Catalog §5.

### NORMALIZATION-0001 — Recover Canonical Structure

| Aspect | Statement |
| ------ | --------- |
| **Purpose** | Recover the single, format-neutral normalized structure the response expresses. |
| **Consumes** | The `LLMResponse` under normalization (read-only). |
| **Produces** | The **Normalized Structure** intermediate fact — or its recorded absence. |
| **Reads** | Nothing from the Assembly State (it is the first stage). |
| **Writes** | The normalized structure (or its absence) to the Assembly State. |
| **Must never modify** | The `LLMResponse`; any other fact (there are none yet). |
| **Must never create** | Outcome, observations, source reference, `ParsedResponse`, or any judgment. |
| **Must never depend on** | Any later stage (`0002…0005`). |
| **Must complete before** | `0002`, `0003`, and `0005`. |

### NORMALIZATION-0002 — Determine Normalization Outcome

| Aspect | Statement |
| ------ | --------- |
| **Purpose** | Determine the one provider-independent Normalization Outcome (`NORMALIZED` / `MALFORMED`). |
| **Consumes** | The result of structure recovery (`0001`). |
| **Produces** | Exactly one **Normalization Outcome** fact. |
| **Reads** | The normalized structure (or its absence) from the Assembly State. |
| **Writes** | The outcome to the Assembly State. |
| **Must never modify** | The normalized structure; the `LLMResponse`. |
| **Must never create** | Structure, observations, source reference, `ParsedResponse`; a verdict, severity, or recommendation. |
| **Must never depend on** | `0003`, `0004`, `0005`. |
| **Must complete before** | `0005`. |

### NORMALIZATION-0003 — Capture Normalization Observations

| Aspect | Statement |
| ------ | --------- |
| **Purpose** | Capture recorded, un-judged Normalization Observations a structural view alone would lose. |
| **Consumes** | The result of structure recovery (`0001`). |
| **Produces** | Zero or more **Normalization Observations** (transient; destined for the `NormalizationResult`). |
| **Reads** | The normalized structure / recovery facts from the Assembly State. |
| **Writes** | The observation set to the Assembly State's transient observation collection. |
| **Must never modify** | The structure, outcome, source reference, or the `LLMResponse`. |
| **Must never create** | A `ParsedResponse` attribute; severity, verdict, recommendation, blocking indicator, or `ValidationIssue`. |
| **Must never depend on** | `0004`, `0005`; and its output is **never consumed by** `0005`. |
| **Must complete before** | `NormalizationResult` aggregation. |

### NORMALIZATION-0004 — Create Source Reference

| Aspect | Statement |
| ------ | --------- |
| **Purpose** | Create the immutable reference linking the representation back to the preserved original response. |
| **Consumes** | The identity of the original `generated_text` (independent of `0001`–`0003`). |
| **Produces** | The **Source Reference** fact. |
| **Reads** | The original's identity (not other stages' facts). |
| **Writes** | The source reference to the Assembly State. |
| **Must never modify** | The original response; it never copies or mutates it. |
| **Must never create** | Structure, outcome, observations, `ParsedResponse`. |
| **Must never depend on** | `0001`, `0002`, `0003`, `0005`. |
| **Must complete before** | `0005`. |

### NORMALIZATION-0005 — Assemble ParsedResponse

| Aspect | Statement |
| ------ | --------- |
| **Purpose** | Assemble the single, immutable, shared `ParsedResponse` from the finalized facts. |
| **Consumes** | The Normalized Structure (`0001`), the Normalization Outcome (`0002`), and the Source Reference (`0004`), plus the representation's version and metadata. |
| **Produces** | Exactly one immutable **`ParsedResponse`**, handed out of the boundary to the `NormalizationResult`. |
| **Reads** | The structure, outcome, and source reference from the Assembly State. |
| **Writes** | Nothing back into the Assembly State — the `ParsedResponse` is an output, never stored in the working medium (§4). |
| **Must never modify** | Any prior fact; it never enriches, interprets, judges, or repairs. |
| **Must never create** | Observations, severity, verdict, recommendation. |
| **Must never depend on** | `0003` (observations are aggregated by the `NormalizationResult`, not carried on the `ParsedResponse`). |
| **Must complete before** | Assembly State destruction and `NormalizationResult` finalization. |

---

## 7. Assembly Invariants

These invariants are **permanent**. A violation is non-conforming by definition.

1. **`0002` never executes before `0001`.**
2. **`0005` never executes without an outcome (`0002`) and a source reference (`0004`).**
3. **`0005` never depends on `0003`** — observations never enter the `ParsedResponse`.
4. **The dependency graph is acyclic** — `0001 → 0002`, `0001 → 0003`, `0004`
   independent, `0005 ← {0001, 0002, 0004}`; no back-edge exists.
5. **The Assembly State never leaves the `ResponseNormalizer` boundary** — not
   returned, not stored, not shared, not observable by the framework.
6. **The `ParsedResponse` is assembled exactly once**, by `0005`, per execution.
7. **No stage mutates a previous stage's fact** — facts are appended, never edited.
8. **No stage re-executes** within one normalization execution.
9. **No stage repairs malformed content** — Observe, Never Repair (Contract §3.2).
10. **The Assembly State is destroyed after assembly** — it does not outlive `0005`.
11. **The `ParsedResponse` is immutable after creation** — no attribute changes;
    it never references the Assembly State (Canonical Models §8; Contract §6).
12. **The Assembly State never contains a `ParsedResponse`, a judgment, telemetry,
    provenance, or provider/business information** (§4).

---

## 8. Failure Semantics

Normalization produces **facts, not exceptions** (Contract §3.6, §10). The
distinction is permanent:

| Situation | Result |
| --------- | ------ |
| **No well-formed structure recovered** | `0001` records the absence; `0002` records the **`MALFORMED`** outcome — a **fact**, never an exception. |
| **Response is malformed** | `0003` may record a `malformed_representation` observation; `0004` still creates the source reference; `0005` still assembles a `ParsedResponse` (outcome `MALFORMED`, normalized structure absent). Validation decides *what it means* later. |
| **A stage encounters an unexpected internal failure** | An **infrastructure exception**, distinct from any normalization fact. |
| **A framework failure** | A framework exception, translated at the `ResponseNormalizer` boundary (Response Normalizer §12) — never a normalization fact. |

Consequences:

- **`MALFORMED` is a fact, not an exception.** The chain completes; a `ParsedResponse`
  is still assembled (with a `MALFORMED` outcome and absent structure).
- **Stage failures produce facts; framework failures produce exceptions.** The two
  families never mix.
- **The Assembly State may terminate early.** If an infrastructure exception aborts
  the execution before `0005`, the Assembly State is discarded with the aborted run
  and the **`ParsedResponse` may remain absent**.
- **The `NormalizationResult` remains the aggregate** in every case — including an
  aborted one, where it carries no `ParsedResponse` (the placeholder stays absent)
  but still records the run's identity and telemetry.

> **Architectural Decision — a malformed response is a completed normalization, not
> a failure.** The subsystem's job is to *record what is present*, so "the response
> was malformed" is a successful, fact-producing outcome. Only an inability to *run*
> the normalization is an exception. This keeps the Normalization–Validation
> boundary intact: normalization never judges a `MALFORMED` response; the Syntax
> layer does (Contract §9, §10).

---

## 9. Relationship Matrix

```text
   Assembly State        (transient · boundary-local · never escapes)
        │ produces (0005)
        ▼
   ParsedResponse        (immutable · shared · carried by the result)
        │ aggregated by
        ▼
   NormalizationResult   (aggregate: ParsedResponse + observations + telemetry)
        │ consumed by
        ▼
   Response Validator    (first consumer; reads ParsedResponse + observations)
```

| Element | Escapes the `ResponseNormalizer` boundary? | Owner |
| ------- | :----------------------------------------: | ----- |
| **Assembly State** | **Never** | `ResponseNormalizer` (internal, transient) |
| **`ParsedResponse`** | Yes — as a Shared Platform Artifact | Its own canonical model; created by `0005` |
| **Normalization Observations** | Yes — via the aggregate | `NormalizationResult` |
| **`NormalizationResult`** | Yes — the single returned output | The framework's aggregate root |

> **Architectural Decision — the Assembly State never escapes; its products do.** The
> boundary is exact: the Assembly State is internal working memory that ceases to
> exist after `0005`, while the `ParsedResponse` (via `0005`) and the observations
> (via `0003`) escape only as content of the `NormalizationResult`. Nothing outside
> the boundary ever holds, reads, or depends on the Assembly State.

---

## 10. Relationship with ADR-0002

This document **complements** ADR-0002; the two do not overlap.

| Document | Governs |
| -------- | ------- |
| **ADR-0002** | The **boundary**: the generic Response Normalization Framework vs. the `ResponseNormalizer` component; that the five stages are internal to the component; that the framework is unaware of the Assembly State and `ParsedResponse` construction. |
| **This contract** | The **internal collaboration**: how the five internal stages exchange intermediate facts through the Assembly State inside that boundary. |

ADR-0002 established *that* the Assembly State exists and lives inside the
`ResponseNormalizer`; this contract defines *what it may hold, how the stages
collaborate through it, and its lifecycle*. ADR-0002 draws the boundary; this
contract governs the space inside it. Neither restates the other.

---

## 11. Future Extensibility

The five-stage chain grows **additively**, exactly as the Normalization
Responsibility Catalog grows (Catalog §9).

| Rule | Statement |
| ---- | --------- |
| **Additive only** | A new stage `NORMALIZATION-0006+` is appended; it never replaces an existing stage. |
| **Never reorder** | Existing stages `0001…0005` keep their positions; a new stage joins at a reserved higher position, preserving the forward-only chain. |
| **Never change ownership** | A new stage introduces its own owned fact; it never re-owns structure, outcome, observations, source reference, or the `ParsedResponse`. |
| **Never change Assembly State semantics** | A new stage may write a **new** allowed intermediate fact, but never turns the Assembly State into a canonical model, a durable store, or an escaping object; the §4 allowed/forbidden partition and the §3 transience are unchanged. |
| **ADR-gated** | Adding a stage, changing a dependency, or changing the order is an architecture change requiring an ADR (Catalog §11). |

> **Architectural Decision — growth is additive and boundary-preserving.** A future
> stage extends the chain without disturbing any existing owner, the acyclic graph,
> or the Assembly State's transient, non-canonical, non-escaping nature. A stage
> that repaired, judged, reordered, re-owned a fact, or persisted the Assembly State
> is non-conforming regardless of its number.

---

## 12. Architecture Freeze

> **Architectural Decision — Architecture Freeze**
> With this document, the following become **frozen architectural contracts** for
> the internal collaboration of the normalization stages:
>
> - **Assembly State identity** — a transient, boundary-local, non-canonical working
>   medium (§3).
> - **Stage collaboration** — the read/write contract of §6, through the Assembly
>   State only.
> - **Intermediate-fact ownership** — the §4 allowed/forbidden partition; one owner
>   per fact.
> - **Assembly lifecycle** — created at execution start, destroyed after `0005` (§3,
>   §5).
> - **Stage ordering** — the forward-only chain `0001 → 0002 → 0003 → 0004 → 0005`,
>   enforced inside the `ResponseNormalizer` (§5; ADR-0002).
> - **Assembly invariants** — all twelve invariants of §7.
> - **Creation and destruction** — exactly one Assembly State per execution; it does
>   not outlive the run (§3).
> - **Single assembly** — the `ParsedResponse` is assembled exactly once (§7.6).
> - **No leakage** — the Assembly State never escapes the boundary (§9).
>
> **Only implementation may evolve** beneath these contracts. **The architecture may
> evolve only through an approved Architecture Decision Record (ADR).** A change that
> makes the Assembly State canonical, durable, shared, or escaping; that reorders,
> re-owns, or re-executes a stage; that lets a stage repair, judge, or mutate a prior
> fact; or that carries a forbidden item in the Assembly State is non-conforming by
> definition.

> **Definition of Done**
> This document is the definitive specification of the internal collaboration
> between the five normalization stages inside the `ResponseNormalizer` boundary. It
> governs the Assembly State, stage collaboration, intermediate-fact ownership, the
> assembly lifecycle, the assembly invariants, and the boundary's non-leakage. It
> governs **only** that internal collaboration — never the framework, the
> `ParsedResponse` shape, the orchestration boundary, the responsibility definitions,
> validation, providers, or implementation. It is implementation-independent and
> remains valid even if the platform is reimplemented on an entirely different
> technology stack, serialization format, or AI provider.

---

## 13. Cross-Document Consistency

Verified consistent with every frozen artifact it touches. **No inconsistency was
found.**

| Document | Consistency check | Result |
| -------- | ----------------- | ------ |
| **Response Normalization Contract** | Facts-not-judgments (§10), Observe-Never-Repair (§3.2), Normalize-Once (§3.1), outcomes `NORMALIZED`/`MALFORMED` (§9), observations owned by the result (§8). | ✅ Consistent |
| **Response Normalizer Architecture** | The `ResponseNormalizer` owns the Assembly State and coordinates the internal stages; orchestration, exception translation, and boundary remain there. | ✅ Consistent |
| **ADR-0002** | Framework is generic and unaware of the Assembly State and `ParsedResponse`; the five are internal stages; `ParsedResponse` assembly is within the boundary. | ✅ Consistent — this document elaborates the internal collaboration ADR-0002 scoped. |
| **`ParsedResponse` (Validation Canonical Models §8)** | Five attributes only; observations excluded; immutable, shared, created once by the normalization layer; assembled from structure, outcome, and source reference. | ✅ Consistent — `0005` assembles exactly those attributes; the Assembly State never contains the `ParsedResponse`. |
| **Normalization Responsibility Catalog** | Five stages, single concern each, forward-only dependencies (`0005 ← 0001,0002,0004`; not `0003`), frozen order, additive growth. | ✅ Consistent — the stage contracts (§6) and invariants (§7) mirror the catalog exactly. |
| **Validation Canonical Models** | Single-owner rule; `NormalizationResult` aggregates the `ParsedResponse`, observations, statistics, framework metadata, execution context. | ✅ Consistent — the Assembly State forbids every item those models own (§4). |

> If any future change to a frozen document contradicts this contract, that is an
> architecture change: **stop and resolve it through an ADR**, never silently in this
> document.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Assembly State** | The transient, boundary-local, mutable, non-canonical medium through which the five normalization stages exchange intermediate facts during one execution; created at execution start, destroyed after `0005`, never shared, stored, or returned (§3). |
| **Intermediate fact** | A fact one stage produces for a later stage to read (normalized structure, outcome, source reference, transient observations) — held in the Assembly State, never durable in its own right (§4). |
| **Normalized Structure** | The format-neutral structural view recovered by `0001`; a `ParsedResponse` attribute when `NORMALIZED` (Canonical Models §8.1). |
| **Normalization Outcome** | The provider-independent fact `NORMALIZED` / `MALFORMED` determined by `0002` (Contract §9). |
| **Normalization Observation** | A recorded, un-judged fact captured by `0003`, owned by the `NormalizationResult`, never carried on the `ParsedResponse` (Contract §8). |
| **Source Reference** | The immutable reference to the preserved original created by `0004` (Catalog §5). |
| **ParsedResponse** | The single, immutable, shared canonical representation assembled by `0005`; the *output* of assembly, never a member of the Assembly State (Canonical Models §8). |
| **NormalizationResult** | The aggregate that owns the `ParsedResponse`, the observations, and the telemetry of the run. |
| **ResponseNormalizer boundary** | The component boundary (ADR-0002) inside which the stages and the Assembly State live and outside which the Assembly State never passes. |

## Appendix B — Conformance Checklist

An implementation conforms to this contract only if every box can be checked:

- [ ] Exactly one Assembly State exists per normalization execution.
- [ ] The Assembly State is never a canonical model, never versioned, never shared.
- [ ] The Assembly State is never persisted, cached, reused, or returned.
- [ ] The Assembly State is destroyed after `0005` and never outlives the execution.
- [ ] The Assembly State never leaves the `ResponseNormalizer` boundary.
- [ ] The Assembly State contains **only** allowed intermediate facts (§4).
- [ ] The Assembly State contains **no** `ParsedResponse`, judgment, severity, verdict, recommendation, statistics, execution context, framework metadata, provider, or business information.
- [ ] `0001` writes the normalized structure and reads nothing from the Assembly State.
- [ ] `0002` reads the structure and writes exactly one outcome; it never runs before `0001`.
- [ ] `0003` writes observations that flow to the `NormalizationResult` and are **never** read by `0005`.
- [ ] `0004` writes the source reference without copying or mutating the original.
- [ ] `0005` reads structure + outcome + source reference (never observations) and assembles exactly one immutable `ParsedResponse`.
- [ ] `0005` never runs without an outcome and a source reference.
- [ ] The dependency graph is acyclic; no stage reads a later stage's fact.
- [ ] No stage mutates a previous fact, re-executes, or repairs malformed content.
- [ ] `MALFORMED` is produced as a **fact**; only an inability to run produces an exception.
- [ ] The `ParsedResponse` is immutable after creation and never references the Assembly State.
- [ ] The `NormalizationResult` remains the aggregate in every case, including an aborted run.
- [ ] A new stage (`0006+`) is additive, never reorders, re-owns, or changes Assembly State semantics.
- [ ] Any architectural change to the above is made through an approved ADR.
