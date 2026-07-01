# Normalization Responsibility Catalog

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Responsibility Catalog |
| Status               | Approved — Foundational — **FROZEN**                              |
| Scope                | The governed catalog of every `NORMALIZATION-00NN` responsibility — its identity, single concern, ownership, dependencies, and ordering |
| Governs              | Responsibility identity · single concern · ownership · dependencies · registration/execution ordering · catalog numbering · reserved ranges · responsibility evolution |
| Depends on           | Response Normalization Contract · Validation Canonical Models (`ParsedResponse`) · Response Normalizer Architecture · Response Normalization Framework |
| Audience             | Solution Architects · Technical Architects · Platform Engineers · Lead Engineers · QA Architects |
| Implementation-bound | No — valid regardless of language, framework, serialization format, algorithm, or AI provider |

> **Architectural Decision**
> This catalog is the **permanent governing specification for the set of
> normalization responsibilities**. It governs *what each responsibility is, what it
> owns, what it depends on, and in what order it participates* — never *how it is
> built*. It is the normalization counterpart of the Validation Rule Catalog: the
> two catalogs are siblings in discipline and disjoint in subject, and they never
> merge (Response Normalization Contract §13).

---

## 1. Purpose

### 1.1 Why normalization responsibilities exist

The Response Normalization subsystem turns a provider-independent `LLMResponse`
into the canonical `ParsedResponse`, exactly once, before any consumer runs. That
transformation is not a single indivisible act: structure must be recovered, an
outcome determined, observations captured, the original preserved by reference,
and the immutable representation assembled. Each of these is a **distinct concern**.
A **Normalization Responsibility** is the architectural unit that owns exactly one
such concern.

If these concerns were fused into one undifferentiated step:

- **Ownership would blur** — no one could say which concern produced which fact,
  defeating audit and determinism.
- **Concerns would leak** — outcome determination could quietly depend on how
  observations were captured, or structure recovery could drift into judgment.
- **Evolution would stall** — a change to one concern would risk every other,
  because none would have an independent, governed identity.

The catalog exists so that each concern has **one immutable identity, one owner,
and one place in the order** — permanently.

### 1.2 Why responsibilities differ from validation rules

A validation rule produces a **judgment** — a finding about whether a response is
trustworthy. A normalization responsibility produces a **fact** — a statement of
what structure is present and what was observed. The two live on opposite sides of
the permanent Normalization–Validation boundary (Response Normalization Contract
§10).

| Aspect | Validation Rule | Normalization Responsibility |
| ------ | --------------- | ---------------------------- |
| Produces | judgments (issues, severity, verdict) | facts (structure, outcome, observations) |
| Boundary | interprets facts | records facts |
| Catalog | `<LAYER>-NNNN` (Validation Rule Catalog) | `NORMALIZATION-00NN` (this catalog) |
| Ordering | by validation layer | by registration order (no layers) |
| Output | contributes to a verdict | contributes to the `ParsedResponse` and the run's facts |

### 1.3 Why normalization needs a governed catalog

Because responsibilities are shared, ordered, and permanent, their identities and
boundaries must be **governed once**, not re-decided per implementation. A governed
catalog guarantees that every conforming implementation recovers structure,
determines the outcome, captures observations, references the original, and
assembles the representation as the **same** five governed concerns — so the
`ParsedResponse` means the same thing everywhere.

> **Principle**
> **This document governs identity, ordering, responsibility, and ownership —
> never implementation.** *What* a responsibility is and *where* it sits are frozen
> here; *how* it recovers structure or captures a fact is an implementation detail
> that may evolve freely beneath this catalog.

---

## 2. Scope

### 2.1 What this catalog governs

| Governed | Description |
| -------- | ----------- |
| **Identity** | The permanent `NORMALIZATION-00NN` identifier of each responsibility. |
| **Single concern** | The one concern each responsibility owns, and only that concern. |
| **Ownership** | Which fact or artifact each responsibility produces and owns. |
| **Dependencies** | Which prior responsibilities' facts each one reads (forward-only). |
| **Ordering** | The registration order that is the execution order (§8). |
| **Catalog numbering** | The numbering scheme and reserved ranges (§9). |
| **Responsibility evolution** | How the catalog grows additively (§9). |

### 2.2 What this catalog does **not** govern

| Not governed here | Owned elsewhere |
| ----------------- | --------------- |
| **Implementation** | A conforming implementation; never an architectural concern. |
| **Algorithms** | The mechanism by which structure is recovered or a fact captured. |
| **Parsers / formats** | Any parsing mechanism or serialization format. |
| **Providers** | Any model, vendor, or endpoint. |
| **Repair** | Forbidden platform-wide; nothing repairs (Response Normalization Contract §3.2). |
| **Validation** | The Response Validator and the Validation Rule Catalog. |
| **Business logic** | Downstream domain layers. |
| **The `ParsedResponse` shape** | Validation Canonical Models §8. |
| **Orchestration** | Response Normalizer Architecture. |

> **Architectural Decision**
> The catalog is deliberately **narrow**. It names and orders concerns; it does not
> describe how they are fulfilled. A change to a mechanism is not a change to this
> catalog; a change to an identity, an owner, a dependency, or the order **is**, and
> requires an ADR (§11).

---

## 3. Architectural Principles

These eleven principles are binding on every `NORMALIZATION-00NN` responsibility
and on the catalog as a whole.

### 3.1 Single Responsibility

> **Principle** — Each responsibility owns **exactly one** concern. It never blends
> two, and no two responsibilities share one. The concern is complete and
> indivisible.

### 3.2 Deterministic Responsibility

> **Principle** — Given the same input and the same prior facts, a responsibility
> produces the **same** fact every time. It depends on no randomness, time, or
> external mutable state. Determinism here is the precondition of the whole
> subsystem's determinism.

### 3.3 Facts, Not Judgments

> **Principle** — A responsibility produces **facts** — never judgments. It records
> *what is*; it never assigns severity, verdict, recommendation, or trustworthiness.
> Interpretation belongs to a consumer (Response Normalization Contract §10).

### 3.4 Provider Independence

> **Principle** — A responsibility references no provider, model, vendor, endpoint,
> or serialization format. It operates on the already-provider-independent input and
> recovers *normalized* structure, not "the structure of format X."

### 3.5 No Repair

> **Principle** — A responsibility **observes, never repairs**. It records the
> structure and facts that are actually present; it never fixes, completes, coerces,
> enriches, or "cleans" a response. A response without well-formed structure yields
> a `MALFORMED` outcome, never a silently repaired one.

### 3.6 Ordered Execution

> **Principle** — Responsibilities participate in a **fixed order**. The order is
> architectural (§4, §8): it reflects the dependency of later facts on earlier ones,
> and no implementation may reorder it.

### 3.7 Shared Artifact

> **Principle** — The responsibilities collectively produce **one** canonical
> `ParsedResponse` — a Shared Platform Artifact created once and read by every
> consumer. No responsibility produces a private or duplicate representation.

### 3.8 No Responsibility Overlap

> **Principle** — No responsibility duplicates, overrides, or re-derives another's
> concern. Every fact has exactly **one** producing responsibility; ownership never
> overlaps.

### 3.9 Immutable Identity

> **Principle** — A responsibility's `NORMALIZATION-00NN` identity is **permanent**.
> Identifiers are never renumbered, reused, or retired-and-reassigned; a renamed
> concern keeps its identifier.

### 3.10 Extensible Catalog

> **Principle** — The catalog grows **additively**. New concerns are new
> `NORMALIZATION-00NN` entries appended to reserved ranges; existing entries are
> never replaced or reordered to accommodate them.

### 3.11 Architecture Before Implementation

> **Principle** — A responsibility's identity, concern, ownership, dependencies, and
> order are settled **here, in architecture**, before any implementation exists.
> Implementation conforms to the catalog; the catalog never conforms to an
> implementation.

---

## 4. Responsibility Overview

The subsystem's work is governed as **five permanent responsibilities**, executed
in a fixed order:

```text
   NORMALIZATION-0001   Recover Canonical Structure
        │
        ▼
   NORMALIZATION-0002   Determine Normalization Outcome
        │
        ▼
   NORMALIZATION-0003   Capture Normalization Observations
        │
        ▼
   NORMALIZATION-0004   Create Source Reference (preserve original by reference)
        │
        ▼
   NORMALIZATION-0005   Assemble ParsedResponse
```

### 4.1 Why the ordering exists

The order is **not arbitrary** — it is the order in which facts become available:

- Structure must be recovered (**0001**) before an outcome about that structure can
  be determined (**0002**) and before the observations a naïve structural view would
  lose can be captured (**0003**).
- The reference to the preserved original (**0004**) is independent of the recovered
  structure but is created before assembly so the representation can carry it.
- The immutable `ParsedResponse` can only be assembled (**0005**) once the facts it
  carries — outcome, structure, and source reference — already exist.

> **Architectural Decision — ordering is architectural, not incidental.** The order
> `0001 → 0002 → 0003 → 0004 → 0005` encodes a **forward-only dependency**: every
> responsibility may read the facts of those before it and none of those after it.
> Implementation **cannot change this order**; doing so would let a responsibility
> read a fact that does not yet exist. The order is frozen (§11).

---

## 5. Responsibility Definitions

Each responsibility below owns exactly one concern. Inputs and outputs are stated
architecturally — as the abstract facts consumed and produced — never as data
structures, formats, or mechanisms.

---

### NORMALIZATION-0001 — Recover Canonical Structure

| Field | Statement |
| ----- | --------- |
| **Purpose** | Recover the single, canonical, format-neutral structural representation the response expresses. |
| **Single concern** | Structure recovery — and only structure recovery. |
| **Inputs** | The provider-independent response under normalization. |
| **Outputs** | The **Normalized Structure** fact (a `ParsedResponse` attribute) when structure is recoverable; the absence of recoverable structure otherwise. |
| **Dependencies** | None — it is the first responsibility. |
| **Non-responsibilities** | Never judges, validates, determines the outcome, records observations, references the original, repairs, or assembles the `ParsedResponse`. |

> **Worked architectural example.** A response expresses a document composed of an
> executive-summary section, a requirements collection, and a risks collection.
> `0001` recovers that structure as normalized, format-neutral objects, arrays, and
> identifiers. Whether the document is *complete* or *correct* is never its concern —
> it recovers what is present.

> **Architecture Decision.** `0001` produces the **Normalized Structure** fact only.
> Deciding what the recovery *means* (well-formed or not) is the concern of `0002`;
> `0001` never crosses into that judgment.

---

### NORMALIZATION-0002 — Determine Normalization Outcome

| Field | Statement |
| ----- | --------- |
| **Purpose** | Determine the single, provider-independent **Normalization Outcome** for the response. |
| **Single concern** | Outcome determination — and only outcome determination. |
| **Inputs** | The result of structure recovery (`0001`). |
| **Outputs** | Exactly one **Normalization Outcome** fact — `NORMALIZED` or `MALFORMED` — and nothing else (a `ParsedResponse` attribute). |
| **Dependencies** | `0001`. |
| **Non-responsibilities** | Never produces a verdict, severity, or recommendation; never recovers structure; never captures observations; never assembles the `ParsedResponse`. |

> **Worked architectural example.** When `0001` recovered a well-formed structural
> representation, `0002` records the outcome `NORMALIZED`. When no well-formed
> structure could be recovered, `0002` records `MALFORMED`. The outcome is a **fact**
> that a later consumer (the Syntax validation layer) may *judge* — `0002` never
> judges it.

> **Architecture Decision.** The outcome set is **exactly two** members and is
> governed like a normalized execution outcome. A new outcome is an architecture
> change requiring an ADR (Response Normalization Contract §9); `0002` never invents
> one.

---

### NORMALIZATION-0003 — Capture Normalization Observations

| Field | Statement |
| ----- | --------- |
| **Purpose** | Capture the recorded, un-judged **Normalization Observations** that a structural view alone would lose. |
| **Single concern** | Observation capture — and only observation capture. |
| **Inputs** | The result of structure recovery (`0001`). |
| **Outputs** | Zero or more **Normalization Observations** — un-judged facts. |
| **Owner of the output** | The **`NormalizationResult`** aggregate — **not** the `ParsedResponse`. Observations are execution facts about the run; they are never carried on the canonical representation (Validation Canonical Models §8; Response Normalization Contract §8). |
| **Dependencies** | `0001`. |
| **Non-responsibilities** | Never assigns severity, verdict, recommendation, or a blocking indicator; never becomes a validation issue; never recovers structure; never assembles the `ParsedResponse`. |

> **Worked architectural example.** During recovery, two identifiers within one
> object were found to collide, and the response's character integrity was intact.
> `0003` records these as observations — *that* a duplicate identifier occurred and
> *that* the integrity is intact. Whether either **matters** is a judgment reserved
> for a consumer; `0003` only records the facts.

> **Architecture Decision — observations belong to the `NormalizationResult`, not the
> `ParsedResponse`.** This is the single-owner rule made concrete: the representation
> is owned by the `ParsedResponse`; the observations about the run that produced it
> are owned by the `NormalizationResult`. `0003` therefore never contributes to the
> `ParsedResponse` assembled by `0005`.

---

### NORMALIZATION-0004 — Create Source Reference

*(Fulfils the Contract's "Preserve Original Response" responsibility, §13, by
reference.)*

| Field | Statement |
| ----- | --------- |
| **Purpose** | Create the immutable **Source Reference** that links the representation back to the preserved original response. |
| **Single concern** | Source referencing — and only source referencing. |
| **Inputs** | The identity of the original response under normalization. |
| **Outputs** | The **Source Reference** fact (a `ParsedResponse` attribute). |
| **Dependencies** | The original response (independent of `0001`–`0003`). |
| **Non-responsibilities** | Never **copies** the original; never **mutates** it; never recovers structure; never determines the outcome; never captures observations; never assembles the `ParsedResponse`. |

> **Worked architectural example.** The normalized representation must never replace
> the original response. `0004` creates a reference *to* the preserved original, so a
> consumer can always reach the unaltered source without the representation ever
> holding a copy of it.

> **Architecture Decision — preserve by reference, never by copy.** The original is
> preserved *unchanged* precisely because `0004` references it rather than
> duplicating or altering it. Preservation and referencing are the same concern
> viewed from two sides: the Contract calls it "preserve the original," the canonical
> models call the resulting attribute the "Source Reference." `0004` owns both.

---

### NORMALIZATION-0005 — Assemble ParsedResponse

| Field | Statement |
| ----- | --------- |
| **Purpose** | Assemble the single, immutable, shared `ParsedResponse` from the facts produced by the preceding responsibilities. |
| **Single concern** | Representation assembly — and only assembly. |
| **Inputs** | The **Normalized Structure** (`0001`), the **Normalization Outcome** (`0002`), and the **Source Reference** (`0004`), together with the representation's version and metadata. |
| **Outputs** | Exactly one immutable **`ParsedResponse`** — a Shared Platform Artifact. |
| **Dependencies** | `0001`, `0002`, `0004`. **Not** `0003` — observations are aggregated by the `NormalizationResult`, not carried on the `ParsedResponse`. |
| **Non-responsibilities** | Never validates, judges, enriches, interprets, repairs, or mutates the representation; never recovers structure; never captures observations. |

> **Worked architectural example.** With the structure recovered, the outcome
> determined, and the source reference created, `0005` assembles them — with the
> representation's version and any metadata — into one immutable `ParsedResponse`.
> It adds no meaning of its own: it composes existing facts into the canonical shape
> and freezes it.

> **Architecture Decision — assembly is composition, never interpretation.** `0005`
> **creates** the `ParsedResponse` (confirming the Response Normalizer never does —
> Response Normalizer Architecture §4). It composes already-produced facts; it never
> enriches or judges them. The result is immutable, shared, never copied, never
> recreated (Response Normalization Contract §6).

---

## 6. Responsibility Relationships

The responsibilities form a **forward-only chain**. The chain below shows the
**execution sequence**; the ownership annotations show where each fact is carried.

```text
   LLMResponse
        │
        ▼
   NORMALIZATION-0001  ── produces ─► Normalized Structure ─────────────┐
        │                                                               │
        ▼                                                               │
   NORMALIZATION-0002  ── produces ─► Normalization Outcome ────────────┤ (into ParsedResponse)
        │                                                               │
        ▼                                                               │
   NORMALIZATION-0003  ── produces ─► Normalization Observations ──┐    │
        │                                                          │    │
        ▼                                                          │    │
   NORMALIZATION-0004  ── produces ─► Source Reference ────────────┼────┤
        │                                                          │    │
        ▼                                                          │    │
   NORMALIZATION-0005  ── assembles ─► ParsedResponse ◄────────────┼────┘
        │                                                          │
        ▼                                                          │
   NormalizationResult ◄── aggregates ParsedResponse + ───────────┘
                            Normalization Observations + telemetry
```

| Relationship | Meaning |
| ------------ | ------- |
| **LLMResponse → 0001** | The provider-independent response is the only input the chain needs to begin. |
| **0001 → 0002** | The outcome is determined from the result of structure recovery. |
| **0001 → 0003** | Observations are captured from facts the recovery surfaces. |
| **original → 0004** | The source reference links to the preserved original, independent of recovery. |
| **0001 · 0002 · 0004 → 0005** | The representation is assembled from the structure, the outcome, and the source reference. |
| **0005 → ParsedResponse** | Assembly produces the single Shared Platform Artifact. |
| **0003 → NormalizationResult** | Observations are aggregated by the result, **not** carried on the `ParsedResponse`. |
| **0005 + 0003 → NormalizationResult** | The result aggregates the `ParsedResponse` **and** the observations (and telemetry). |

> **Architectural Decision — the execution chain is linear; the ownership is not.**
> Responsibilities execute in one line (`0001 → … → 0005`), but the facts they
> produce have **two** destinations: the `ParsedResponse` (structure, outcome, source
> reference) and the `NormalizationResult` (observations). The linear arrow is
> *execution sequence*, never an implication that observations flow into the
> `ParsedResponse`.

---

## 7. Responsibility Independence

The catalog guarantees strict independence among responsibilities.

| Guarantee | How it holds |
| --------- | ------------ |
| **Each owns one concern** | §5 assigns exactly one concern per responsibility; §3.1 forbids blending. |
| **No responsibility duplicates another** | §3.8 — every fact has exactly one producer; the five concerns are disjoint. |
| **No responsibility reads future outputs** | §4.1, §6 — dependencies are forward-only; a responsibility reads only the facts of those before it. |
| **No shared mutable state** | Facts are contributed to an **immutable, append-only** record of the run; a responsibility appends its own fact and never edits another's. Nothing is mutated. |
| **No overlapping ownership** | Structure (`0001`), outcome (`0002`), observations (`0003`), source reference (`0004`), and assembly (`0005`) are owned by exactly one responsibility each; `0005` composes but never re-derives. |
| **Parallel evolution is possible** | Because concerns are disjoint and identities immutable, a change to how one concern is fulfilled cannot disturb another. |

> **Architectural Decision — independence is what makes the chain reproducible.**
> Because no responsibility mutates a shared object and none reads a fact that does
> not yet exist, the same input always yields the same `ParsedResponse` and the same
> observations. Independence is not a convenience; it is the guarantee behind
> subsystem determinism.

---

## 8. Registration Order

| Concept | Statement |
| ------- | --------- |
| **Registration** | Responsibilities are registered explicitly, in catalog order. |
| **Execution** | They execute in the order they were registered. |
| **Ordering** | **Registration order is execution order.** There is no separate ordering dimension. |

Normalization has **no layers** (the deliberate deviation from validation, which
orders rules by layer). Ordering therefore comes from registration alone.

> **Clarification (ADR-0002).** This ordering is owned and enforced **inside the
> `ResponseNormalizer`**: the five responsibilities are the Normalizer's **internal
> stages**, and "registration" here means their fixed internal stage sequence — not
> an execution order imposed by the generic Response Normalization Framework
> registry. The framework provides only generic execution infrastructure and is
> unaware of the five-stage sequence. The catalog still **governs** the order (§4,
> §11); ADR-0002 only clarifies *where* it is enforced (the component), which is why
> the forward-only dependency chain is legitimate without contradicting the
> framework's order-independent responsibility contract.

| Rule | Statement |
| ---- | --------- |
| **Never reordered dynamically** | The order is fixed at registration; nothing re-sorts it at run time. |
| **Never profile-dependent** | A profile never changes the order. |
| **Profiles determine participation, never ordering** | A profile may govern *which* responsibilities participate; those that do always run in catalog order. |

> **Architectural Decision — order is registration; participation is profile.** These
> are two independent axes. The **order** is frozen by this catalog (§4, §11); the
> **participation** may be governed by a Normalization Profile (Response Normalizer
> Architecture §11). A profile that reordered responsibilities would break the
> forward-only dependency chain and is non-conforming.

---

## 9. Future Evolution

The catalog is designed to be **extended, never replaced**.

| Reserved | Intent | Constraint |
| -------- | ------ | ---------- |
| **`NORMALIZATION-0006`+** | New normalization concerns a future consumer requires. | Appended additively; a new entry, never a rewrite of an existing one. |

Binding evolution rules:

- **Extend, never replace** — a new concern is a new `NORMALIZATION-00NN` entry;
  existing responsibilities are never redefined out of existence.
- **Never renumber** — existing identifiers keep their numbers forever.
- **Never reuse identifiers** — a retired concern's number is never reassigned.
- **Additive ordering** — new responsibilities join at reserved higher numbers,
  preserving the forward-only chain; they never insert between frozen entries.
- **Architectural changes require an ADR** — a new responsibility, a changed
  concern, a changed dependency, or a changed order is an architecture change.
- **Implementation changes do not** — improving *how* a responsibility fulfils its
  concern requires no ADR (Response Normalization Contract §4.2).

> **Architectural Decision — growth is additive and governed.** The catalog may gain
> `NORMALIZATION-0006` and beyond, each provider-independent, deterministic,
> fact-producing, and non-repairing. A capability that repairs, interprets, judges,
> or binds to a format is non-conforming regardless of its number.

---

## 10. Relationships

This catalog sits among the frozen normalization and validation artifacts.

```text
   [Response Normalization Contract]        governs the subsystem & this catalog (§13)
            │
            ▼
   [Normalization Responsibility Catalog]   ◄── THIS DOCUMENT (the governed stages)
            │ realised as internal stages, coordinated by ▼
   [Response Normalizer]                     the single orchestration boundary (ADR-0002)
            │ builds on ▼
   [Response Normalization Framework]        generic execution infrastructure (registry · pipeline)
            │ the Normalizer produces ▼
   [ParsedResponse]  +  [NormalizationResult]   the artifact + its aggregate
            │
            ▼
   [Response Validator]                      first consumer (reads ParsedResponse + observations)
```

| Artifact | Relationship |
| -------- | ------------ |
| **Response Normalization Contract** | Defines the catalog's governance and the `NORMALIZATION-00NN` numbering (§13); this document elaborates each entry. |
| **Response Normalizer** | Coordinates the five responsibilities as its **internal stages** and owns the Assembly State; the `ParsedResponse` is assembled by its internal stage `0005`, within the Normalizer boundary (ADR-0002). |
| **Normalization Framework** | Provides the **generic execution infrastructure** the Normalizer builds on; it does **not** register or execute the five stages individually and is unaware of the Assembly State and `ParsedResponse` construction (ADR-0002). |
| **`ParsedResponse`** | The Shared Platform Artifact assembled by `0005` from the facts of `0001`, `0002`, `0004`. |
| **`NormalizationResult`** | The aggregate that owns the `ParsedResponse` **and** the observations from `0003` (plus telemetry). |
| **Validation Canonical Models** | Define the `ParsedResponse` shape the responsibilities produce; the catalog never redefines that shape. |
| **Response Validator** | The first consumer of the `NormalizationResult`; it reads the `ParsedResponse` and observations and never normalizes. |
| **Validation Rule Catalog** | The sibling catalog for judgments; it and this catalog never merge and never cross the §10 boundary. |
| **Platform Capability Matrix** | Tracks the maturity of each responsibility as it is implemented. |
| **Architecture Freeze Index** | Records this catalog and its frozen items. |

> **Architectural Decision — one boundary, two catalogs.** Facts are governed here;
> judgments are governed by the Validation Rule Catalog. The `NORMALIZATION-` and
> `<LAYER>-NNNN` numbering spaces are permanently separate.

---

## 11. Architecture Freeze

> **Architectural Decision — Architecture Freeze**
> With this document, the following become **frozen architectural contracts** for
> the Normalization Responsibility Catalog:
>
> - **Responsibility identities** — `NORMALIZATION-0001 … 0005`, each with its named
>   concern (§5).
> - **Ordering** — the fixed, forward-only sequence `0001 → 0002 → 0003 → 0004 →
>   0005` (§4, §8).
> - **Ownership** — structure (`0001`), outcome (`0002`), observations (`0003`, owned
>   by the `NormalizationResult`), source reference (`0004`), and the assembled
>   `ParsedResponse` (`0005`) (§5, §6).
> - **Single concern** — one concern per responsibility; no blending (§3.1).
> - **Responsibility boundaries** — the non-responsibilities of each entry (§5, §6).
> - **Dependencies** — the forward-only dependency set of each responsibility (§6).
> - **Catalog numbering** — the `NORMALIZATION-00NN` scheme (§9).
> - **Reserved ranges** — `NORMALIZATION-0006`+ reserved for additive growth (§9).
>
> **Only implementation may evolve** beneath these contracts. **The architecture may
> evolve only through an approved Architecture Decision Record (ADR).** A change that
> renumbers, reuses, reorders, merges, splits, or reassigns any responsibility is
> non-conforming by definition.

> **Definition of Done**
> This document is the definitive specification of the normalization responsibilities
> for the platform. It governs their identity, single concern, ownership,
> dependencies, ordering, numbering, reserved ranges, and evolution. It governs
> **only** the responsibilities — never implementation, algorithms, parsers,
> providers, formats, repair, validation, or the `ParsedResponse` shape. It is
> implementation-independent and remains valid even if the platform is reimplemented
> on an entirely different technology stack, serialization format, or AI provider.
> With its approval, the Response Normalization architecture is **complete and
> frozen**.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Normalization Responsibility** | The architectural unit that owns exactly one normalization concern, identified as `NORMALIZATION-00NN` (§1, §5). |
| **Responsibility Catalog** | The governed set of all normalization responsibilities — this document (§2). |
| **Canonical Structure** | The single, normalized, format-neutral structural representation a response expresses; recovered by `0001` and carried as the `ParsedResponse`'s Normalized Structure (§5). |
| **Normalization Outcome** | The provider-independent fact `NORMALIZED` or `MALFORMED`, determined by `0002` (§5). |
| **Normalization Observation** | A recorded, un-judged fact captured by `0003` and aggregated by the `NormalizationResult` — never carried on the `ParsedResponse` (§5). |
| **Source Reference** | The immutable reference to the preserved original response, created by `0004` (§5). |
| **ParsedResponse** | The single, immutable, shared canonical structural representation, assembled by `0005`; a Shared Platform Artifact (§5). |
| **NormalizationResult** | The aggregate that owns the `ParsedResponse` together with the observations and telemetry of the run (§6). |
| **Shared Platform Artifact** | An artifact produced once and read read-only across the whole platform; the `ParsedResponse` is one (§3.7). |
| **Registration Order** | The order in which responsibilities are registered, which is their execution order; never reordered, never profile-dependent (§8). |

## Appendix B — Conformance Checklist

A normalization implementation conforms to this catalog only if every box can be
checked:

- [ ] Realises exactly the responsibilities `NORMALIZATION-0001 … 0005`, each with its governed concern.
- [ ] Each responsibility owns **one** concern and blends no other.
- [ ] No responsibility duplicates, overrides, or re-derives another's concern.
- [ ] `0001` recovers the canonical structure and never judges or determines the outcome.
- [ ] `0002` produces exactly one outcome — `NORMALIZED` or `MALFORMED` — and nothing else.
- [ ] `0003` produces observations only, with no severity, verdict, recommendation, or blocking indicator.
- [ ] `0003`'s observations are owned by the **`NormalizationResult`**, never carried on the `ParsedResponse`.
- [ ] `0004` creates a source reference and never copies or mutates the original.
- [ ] `0005` assembles the `ParsedResponse` and never validates, enriches, interprets, or repairs it.
- [ ] `0005` assembles from structure, outcome, and source reference — **not** from observations.
- [ ] Every responsibility produces **facts**, never judgments (§3.3).
- [ ] Every responsibility is **deterministic** — same input and prior facts ⇒ same fact.
- [ ] No responsibility **repairs**, completes, or coerces a response.
- [ ] No responsibility references a provider, model, endpoint, or serialization format.
- [ ] Execution follows the fixed order `0001 → 0002 → 0003 → 0004 → 0005`.
- [ ] Registration order **is** execution order; nothing reorders it dynamically.
- [ ] Profiles govern **participation**, never ordering.
- [ ] No responsibility reads a fact produced by a later responsibility.
- [ ] No responsibility mutates shared state; facts accumulate append-only.
- [ ] Identifiers are never renumbered, reused, or reordered; growth is additive at `NORMALIZATION-0006`+.
- [ ] The implementation conforms to this catalog **and** the Response Normalization Contract.
