# Response Normalization Contract

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Normalization Subsystem |
| Status               | Approved — foundational — **FROZEN**                              |
| Scope                | The normalization of a provider-independent `LLMResponse` into the canonical `ParsedResponse`, and the governance of that subsystem |
| Governs              | The Response Normalization Layer · `ParsedResponse` ownership, lifecycle & sharing · Normalization Outcomes · Normalization Observations · the Normalization–Validation boundary · Normalization Contract Version · ParsedResponse Version · the Normalization Responsibility Catalog · normalization evolution |
| Depends on           | AI Response Validation Architecture · Validation Canonical Models · Requirement Analysis Service |
| Audience             | Solution Architects · Technical Architects · Lead Engineers · QA Architects |
| Implementation-bound | No — valid regardless of language, framework, serialization format, or AI provider |

> **Architectural Decision**
> The **Response Normalization Layer** is a **permanent, independent platform
> subsystem** — not merely a "normalization seam." It is the single subsystem at
> which a provider-independent `LLMResponse` becomes the canonical, shared
> `ParsedResponse`. It is not part of validation, not part of generation, and not
> part of any provider adapter. It exists for one reason: to produce, exactly once,
> the one immutable, format-neutral structural representation that the whole
> platform reads. This contract governs *that subsystem* — its responsibilities,
> ownership, lifecycle, outcomes, observations, boundary, versioning, and
> evolution — and nothing else.

---

## 1. Purpose

### 1.1 Why response normalization exists

The platform's AI generation layer produces an `LLMResponse` whose only content
field is `generated_text` — a single block of provider-independent text that
expresses a structured document. Every consumer downstream of generation — the
validation pipeline first among them — needs to reason about the **structure**
that text expresses, not the text itself.

If each consumer recovered that structure independently:

- The same response would be interpreted **many times**, once per consumer,
  wasting work and inviting divergent interpretations of the same input.
- "Is this response well-formed structured data?" — a single concern — would be
  re-derived everywhere, dissolving the one-concern-per-layer guarantee of the
  validation pipeline (AI Response Validation Architecture §4).
- A subtle difference in how two consumers recovered structure could make them
  **disagree about the same response**, destroying determinism.

The Response Normalization Layer exists to **recover the structure of the
response exactly once, deterministically, and provider-independently**, and to
carry that structure forward as a single canonical model — the `ParsedResponse`
— that every consumer reads without re-deriving.

> **Principle**
> The transition from **text** to **structure** happens **once**, in one
> subsystem, and is **shared** by every consumer. Recovering structure is a
> normalization concern, not a validation concern; consumers *read* the normalized
> structure, they never *produce* it.

### 1.2 The established precedent: normalize once

The platform already solved the identical shape of problem for execution
outcomes. A provider adapter normalizes every provider's termination signals into
one canonical `ExecutionStatus` (`COMPLETED` / `TIMEOUT` / `FAILED`), and every
validation rule reads that **normalized fact** instead of interpreting
provider-specific codes (LLM data models — *Provider Normalization Contract*).

Response normalization extends that proven precedent from **outcome** to
**structure**:

| Concern | Normalized once into | Read by |
| ------- | -------------------- | ------- |
| Execution **outcome** | `ExecutionStatus` (by the provider adapter) | Transport rules |
| Response **structure** | `ParsedResponse` (by the Response Normalization Layer) | Every platform consumer — validation first |

> **Architectural Decision**
> **`ParsedResponse` is to structure what `ExecutionStatus` is to outcome.** Each
> is a normalized, provider-independent fact, produced once at a single subsystem
> and read — never re-derived — by consumers. The Response Normalization Layer is
> the structural counterpart of the adapter's outcome normalization.

### 1.3 What this document is **not**

| This document is NOT | Because |
| -------------------- | ------- |
| A validation specification | It governs how structure is normalized, never how structure is judged. Validation philosophy lives in the AI Response Validation Architecture. |
| A canonical model definition | `ParsedResponse`'s information model is defined in the Validation Canonical Models; this document governs how it is *created, owned, shared, and versioned*. |
| A reasoning specification | How the AI *thinks* is governed by the AI Reasoning Contract; this document concerns only the *shape* of what it produced. |
| A provider or format document | No model, vendor, SDK, endpoint, serialization format, or normalization mechanism is referenced. |

---

## 2. Scope

### 2.1 What this contract owns

| Owned responsibility | Description |
| -------------------- | ----------- |
| **The Response Normalization Layer** | The permanent subsystem and its frozen responsibilities (§4). |
| **`ParsedResponse` creation** | The act of producing the one canonical structural representation from an `LLMResponse` (§5). |
| **`ParsedResponse` ownership & lifecycle** | Single creation, immutability, sharing, no copies, no recreation (§6). |
| **`ParsedResponse` as a Shared Platform Artifact** | Its status as a platform-wide artifact, not a validation artifact (§7). |
| **Normalization Observations** | The first-class concept of recorded, un-judged facts (§8). |
| **Normalization Outcomes** | The governed set of outcomes a normalization may report (§9). |
| **The Normalization–Validation boundary** | The permanent line between facts and judgments (§10). |
| **Provider independence of normalization** | The guarantee that normalization is a *format* concern, never a *provider* concern (§11). |
| **Normalization versioning** | The two independent versions — Normalization Contract Version and ParsedResponse Version (§12). |
| **The Normalization Responsibility Catalog** | The conceptual catalog of normalization responsibilities (§13). |
| **Normalization evolution** | How normalization may grow without breaking consumers (§15). |

### 2.2 What this contract does **not** own

| Not owned here | Owned elsewhere |
| -------------- | --------------- |
| **Validation** | AI Response Validation Architecture · Validation Rule Catalog |
| **Reasoning** | AI Reasoning Contract |
| **AI generation / providers** | Requirement Analysis Service · provider framework |
| **Normalization mechanism** | A replaceable implementation detail; never an architectural concern |
| **Schema conformance** | The Schema validation layer |
| **Business rules** | The Business Rule validation layer |
| **The `ParsedResponse` information model** | Validation Canonical Models (this document governs its *creation, ownership, sharing, and versioning*, not its attribute shape) |

> **Architectural Decision**
> The Response Normalization Layer **performs no validation, no repair, no
> interpretation, no enrichment, no filtering, no mutation, and no transformation
> of business meaning.** It recovers structure, records the outcome, records
> observations, preserves the original — nothing more. A normalization step that
> judged, repaired, enriched, filtered, mutated, or reinterpreted would collapse
> the boundary between *normalizing* and *validating* (§10).

---

## 3. Normalization Philosophy

These principles are binding on every conforming Response Normalization Layer
implementation.

### 3.1 Normalize Once

The transition from `generated_text` to `ParsedResponse` happens **exactly once**
per response, in one subsystem, before any consumer runs. No consumer re-derives
structure.

### 3.2 Observe, Never Repair

Normalization recovers the structure that is **actually present**. It never
fixes, completes, reformats, coerces, enriches, filters, or "cleans" a malformed
response. A response that does not express well-formed structure yields a
`MALFORMED` outcome (§9) — it is never silently repaired into a structure that was
not there. This mirrors **Preserve Original Response** (AI Response Validation
Architecture §3.3): the original `generated_text` survives unchanged alongside the
`ParsedResponse`.

### 3.3 Provider- and Format-Independent

Normalization references no provider, model, vendor, or endpoint, and is not
coupled to any single serialization format. It recovers *normalized structure*,
not "the structure of format X" (§11).

### 3.4 Deterministic

Given the same `generated_text`, normalization always produces the same
`ParsedResponse` and the same outcome. Normalization depends on no randomness,
time, or external mutable state. Determinism here is a precondition of the
validation pipeline's determinism (AI Response Validation Architecture §3.4).

### 3.5 Non-Interpreting

Normalization assigns no meaning. It does not decide whether a field is required,
whether a value is valid, or whether a section is missing. It records *what
structure exists* and *whether it is well-formed*; every judgement about that
structure belongs to a consumer.

### 3.6 Facts, Not Judgments

Normalization produces **facts**; validation (and every other consumer) produces
**judgments** (§10). A Normalization Outcome and a Normalization Observation are
facts about the response. They carry no severity, no verdict, and are never
themselves a `ValidationIssue`.

> **Principle**
> Normalization is **mechanical and meaning-free**. It answers "what structure is
> here, and is it well-formed?" — never "is this structure correct, complete, or
> acceptable?" The first is normalization; the rest is interpretation by a
> consumer.

---

## 4. The Response Normalization Layer (permanent subsystem)

The **Response Normalization Layer** is a **permanent, independent platform
subsystem**. It sits between the `LLMResponse` (the provider-independent output of
generation) and every platform consumer, the Response Validator first among them.

```text
   Provider Adapter
        │ normalizes outcome → ExecutionStatus, text → generated_text
        ▼
   LLMResponse                         (provider-independent text + outcome)
        │
        ▼
   Response Normalization Layer        ◄── this contract (permanent subsystem)
        │ recovers structure ONCE; no validation / repair / interpretation /
        │ enrichment / filtering / mutation / business transformation
        ▼
   ParsedResponse                      (the one canonical, shared structural representation)
        │
        ▼
   Platform consumers                  (Validation first; see §7)
```

### 4.1 The frozen responsibilities

The subsystem's responsibility is **permanently limited** to exactly four acts:

| # | Responsibility | Description |
| - | -------------- | ----------- |
| 1 | **Receive an `LLMResponse`** | Accept the provider-independent response as its only input. |
| 2 | **Produce one `ParsedResponse`** | Recover the single normalized structural representation and emit exactly one immutable `ParsedResponse`. |
| 3 | **Record the Normalization Outcome** | State whether the response was `NORMALIZED` or `MALFORMED` (§9). |
| 4 | **Record Normalization Observations** | Capture recorded, un-judged facts a consumer may need (§8). |

It does **nothing else**. (The acts of *preserving the original* and *producing an
immutable* artifact are intrinsic to acts 1–2; they are catalogued explicitly as
responsibilities in §13.)

### 4.2 What it must never do

> **Architectural Decision — the Response Normalization Layer is permanently
> bounded.** The subsystem **MUST NEVER**:
>
> - **Validate** — it never judges trustworthiness or conformance.
> - **Repair** — it never fixes, completes, or coerces a malformed response.
> - **Interpret** — it never assigns meaning to structure.
> - **Enrich** — it never adds inferred or derived content.
> - **Filter** — it never drops, hides, or selects parts of the response.
> - **Mutate** — it never alters the `LLMResponse` or the `ParsedResponse` after
>   creation.
> - **Transform business meaning** — it never reshapes content into domain
>   concepts.
>
> **Implementation may evolve. Responsibilities may not.** The mechanism by which
> structure is recovered may be optimised, replaced, or re-tuned freely beneath
> this contract. The four responsibilities above, and the seven prohibitions, are
> **frozen**: changing them is an architecture change that **requires an approved
> Architecture Decision Record (ADR)**.

---

## 5. ParsedResponse Creation

The Response Normalization Layer **owns creation**; the `ParsedResponse` **owns
information**; every consumer **consumes information**. These three roles are
strictly separated.

| Role | Owner | Responsibility |
| ---- | ----- | -------------- |
| **Creation** | Response Normalization Layer | *How* the `ParsedResponse` comes into being (once, deterministically). |
| **Information** | `ParsedResponse` (Validation Canonical Models §8) | *What* the representation holds — normalized structure, outcome, observations. |
| **Consumption** | Every platform consumer (Validation first; §7) | *Reading* the representation; never creating or normalizing it. |

> **Architectural Decision**
> **Creation, information, and consumption are three separate concerns with three
> separate owners.** The normalization layer never validates; the `ParsedResponse`
> never creates or judges itself; no consumer normalizes. This separation is what
> lets the normalization mechanism evolve, the representation stay stable, and
> consumers stay independent — each without disturbing the others.

---

## 6. ParsedResponse Ownership & Lifecycle

```text
   LLMResponse
        │
        ▼
   Response Normalization Layer        (creates exactly once)
        │
        ▼
   ParsedResponse                      (immutable · shared · never copied / mutated / recreated)
```

The `ParsedResponse` lifecycle is **frozen**:

| Property | Guarantee |
| -------- | --------- |
| **Created exactly once** | It is produced a single time, by the Response Normalization Layer, immediately after `generated_text` is available and before any consumer runs. |
| **Immutable** | No attribute changes after creation. |
| **Shared** | Every downstream subsystem receives the **identical** `ParsedResponse` instance. |
| **Never copied** | Consumers do not clone or fork it; there is one canonical artifact. |
| **Never mutated** | No consumer alters it; it is read-only for all. |
| **Never recreated** | It is not re-derived, re-normalized, or rebuilt by any consumer. |

> **Architectural Decision**
> **There is exactly one `ParsedResponse` per response, and every consumer reads
> the same one.** No downstream component re-recovers structure from
> `generated_text`; doing so would reintroduce the divergence and waste the
> subsystem exists to eliminate (§1.1). The single, shared, immutable instance is
> the guarantee that makes structure recovery deterministic platform-wide.

> **Principle**
> **No consumer reparses `generated_text`.** The raw text is preserved for audit
> (§13, `NORMALIZATION-0004`), but the *structure* is read only from the one
> shared `ParsedResponse`. A consumer that recovers structure for itself is
> non-conforming.

---

## 7. ParsedResponse as a Shared Platform Artifact

`ParsedResponse` is **not owned by validation**. Validation is merely its **first
consumer**. The same immutable instance is available to every current and future
platform subsystem.

```text
   LLMResponse
        │
        ▼
   Response Normalization
        │
        ▼
   ParsedResponse
        │
        ├────────► Validation                 (first consumer)
        │
        ├────────► Requirement Normalization
        │
        ├────────► Feature Generation
        │
        ├────────► Test Generation
        │
        ├────────► AI Evaluation
        │
        ├────────► Analytics
        │
        └────────► Future Platform Components
```

> **Architectural Decision**
> **`ParsedResponse` is a Shared Platform Artifact, not a Validation artifact.**
> It is produced once by the Response Normalization Layer and shared, read-only,
> across the platform. Because it is shared rather than owned by any one consumer,
> no consumer may shape, extend, or constrain it to its own needs; it is governed
> solely by this contract and the Validation Canonical Models. Validation's
> primacy in time (it is the first consumer) confers no ownership.

---

## 8. Normalization Observations

A **Normalization Observation** is a **first-class architectural concept**: a
recorded, un-judged fact about the response that a naïve structural view would
lose. The Response Normalization Layer captures observations on the
`ParsedResponse` so consumers can read them without re-deriving anything.

| Observation (examples) | What it records |
| ---------------------- | --------------- |
| **Duplicate structural identifiers** | That a field identifier occurred more than once within one object (a normalized structure silently collapses duplicates). |
| **Malformed representation** | That the response did not express recoverable well-formed structure (paired with the `MALFORMED` outcome, §9). |
| **Encoding observations** | That the response's character encoding is intact, or that a lossy/encoding anomaly was detected. |
| **Future structural observations** | Additive facts a future consumer requires (governed; §15). |

Normalization Observations are:

- **Recorded** — captured as facts on the `ParsedResponse`.
- **Never judged** — normalization forms no opinion about them.
- **Never assigned severity** — severity is a validation concept (§10).
- **Never assigned a verdict** — verdicts are a validation concept (§10).
- **Never converted into a `ValidationIssue`** — only a validation rule may, by
  reading an observation, *decide* to raise a `ValidationIssue`.

> **Principle**
> **Normalization records facts. Validation interprets facts.** A Normalization
> Observation states *that* something is so; whether that fact matters — and with
> what severity, verdict, or recommendation — is a judgement made later by a
> consumer, never by normalization.

---

## 9. Normalization Outcomes

A normalization reports exactly one **Normalization Outcome** — a normalized,
provider-independent fact analogous to `ExecutionStatus`.

| Outcome | Meaning | Read by |
| ------- | ------- | ------- |
| **NORMALIZED** | The response expresses well-formed structured data; a normalized structure was recovered. | Syntax confirms well-formedness; every later consumer reads the structure. |
| **MALFORMED** | The response does not express well-formed structured data; no structure could be recovered. | The Syntax layer reads this as its foundational, progression-stopping concern. |

> **Architectural Decision**
> The Normalization Outcome is a **fact**, not a verdict. Normalization reports
> `MALFORMED`; the Syntax layer *decides* what that means for the verdict (a
> foundational, blocking concern per the AI Response Validation Architecture). The
> outcome set is deliberately small and governed: a new outcome is an architecture
> change requiring an ADR, exactly like a new `ExecutionStatus`.

---

## 10. The Normalization–Validation Boundary

The line between normalization and validation is **permanent** and **absolute**.

> **Architectural Decision**
> **Normalization produces facts. Validation produces judgments.** Normalization
> says *what is*; validation says *what it means*. Nothing on the normalization
> side of the boundary carries severity, a verdict, or a recommendation; nothing
> on the validation side recovers structure.

| Side | Produces | Examples |
| ---- | -------- | -------- |
| **Normalization (facts)** | Outcomes and Observations | `NORMALIZED`; `MALFORMED`; Observation = duplicate identifier; Observation = encoding observation |
| **Validation (judgments)** | Verdicts, severities, issues | `PASSED`; `PASSED_WITH_WARNINGS`; `FAILED`; `BLOCKED`; Severity; `ValidationIssue`; Recommendation; Verdict |

```text
        NORMALIZATION  (facts)                 │   VALIDATION  (judgments)
   ─────────────────────────────────────────── │ ───────────────────────────────────────────
        Normalization Outcome                   │   Verdict (PASSED / … / BLOCKED)
        Normalization Observation               │   Severity (INFO / WARNING / ERROR / CRITICAL)
        ParsedResponse (structure)              │   ValidationIssue
        "what is"                               │   Recommendation
                                                │   "what it means"
   ─────────────────────────────────────────── │ ───────────────────────────────────────────
              records facts                     │        interprets facts
```

> **Principle**
> A Normalization Observation is **never** a `ValidationIssue`, and a Normalization
> Outcome is **never** a verdict. A validation rule may *read* an observation or an
> outcome and *decide* to raise an issue — but that decision, and any severity or
> recommendation attached to it, belongs entirely to validation. Crossing this
> boundary in either direction is non-conforming.

---

## 11. Provider Independence

Normalization strengthens, and never weakens, provider independence.

```text
   Provider-specific payload
        │ adapter normalizes: outcome → ExecutionStatus, text → generated_text
        ▼
   generated_text                       (provider-independent text)
        │ ONE shared, format-level normalization — the only structure recovery
        ▼
   ParsedResponse                       (provider-independent structure + outcome + observations)
```

A new provider conforms with **no change to normalization and no change to any
consumer**: its adapter normalizes its payload into `generated_text` exactly as
today; the one Response Normalization Layer recovers structure from that text.
Because structure recovery is a **format** concern — identical across every
provider that emits the requested format — **no provider-specific normalization
exists anywhere**.

> **Architectural Decision — why `ParsedResponse` is format-independent.**
> `ParsedResponse` represents **normalized structure, not a specific serialization
> format.** A structured document may be expressed today in one format and tomorrow
> in another; the structure it expresses — objects, arrays, scalars, identifiers —
> is the same. Binding `ParsedResponse` to one format would make every consumer
> format-aware and force a rewrite whenever the format changed. Keeping it
> format-neutral means new structured formats normalize into the *same*
> representation and no consumer changes.

---

## 12. Normalization Versioning

Normalization is governed by **two independent versions**. Conflating them — or
merging either with the validation versions — would make it impossible to tell a
change in *normalization semantics* from a change in *the representation's shape*
from a change in *validation*.

| Version | Governs | Changes when… |
| ------- | ------- | ------------- |
| **Normalization Contract Version** | Normalization **philosophy, architecture, semantics, and compatibility rules** — the meaning of the outcomes, the observations, the boundary, and the responsibilities. | The *meaning or governance* of normalization changes (a new outcome, a new observation class, a boundary clarification). |
| **ParsedResponse Version** | The **canonical representation** — the attributes the `ParsedResponse` carries and their **additive evolution and compatibility**. | The *shape* of the representation changes additively (a new attribute, a new observation field). |

### 12.1 Why the two versions are intentionally independent

- The **representation can grow without the meaning of normalization changing.**
  Adding a new additive attribute to `ParsedResponse` advances the **ParsedResponse
  Version** but need not change the Normalization Contract Version.
- The **meaning of normalization can change without the representation changing
  shape.** Clarifying the boundary or governing a new outcome advances the
  **Normalization Contract Version** even when no attribute is added.
- Consumers depend on the two for different reasons: a consumer reading a new
  attribute cares about the **ParsedResponse Version**; a consumer reasoning about
  *what normalization guarantees* cares about the **Normalization Contract
  Version**.

> **Architectural Decision**
> **The Normalization Contract Version (semantics) and the ParsedResponse Version
> (representation) are independent — and both are independent of the Validation
> Contract Version, the Validator Version, and the Framework Version.** Each
> isolates one source of change so any difference in behaviour can be attributed
> precisely. Both advance only through an ADR; the normalization *mechanism* may
> change with no version movement so long as it produces an identical
> `ParsedResponse`.

### 12.2 Relationship to the platform's other versions

| Version | Governs | Owned by |
| ------- | ------- | -------- |
| **Normalization Contract Version** | Normalization semantics & governance | This contract |
| **ParsedResponse Version** | The canonical representation's additive shape | This contract (representation defined in Validation Canonical Models §8) |
| **Validation Contract Version** | Validation semantics | AI Response Validation Architecture §13 |
| **Validator Version** | Validation implementation | AI Response Validation Architecture §13.4 |
| **Framework Version** | Framework structure | Validation framework |

---

## 13. Normalization Responsibility Catalog

This is a **conceptual catalog of normalization responsibilities**. These are
**NOT validation rules** — they carry the `NORMALIZATION-` prefix to make explicit
that they belong to a different subsystem entirely and follow a separate
governance from the `<LAYER>-NNNN` validation Rule Catalog.

| ID | Responsibility | Description |
| -- | -------------- | ----------- |
| **NORMALIZATION-0001** | Recover normalized structure | Recover the single, format-neutral structural representation of `generated_text`. |
| **NORMALIZATION-0002** | Determine normalization outcome | Decide and record the Normalization Outcome (`NORMALIZED` / `MALFORMED`, §9). |
| **NORMALIZATION-0003** | Capture normalization observations | Record the Normalization Observations the structure alone would lose (§8). |
| **NORMALIZATION-0004** | Preserve original response | Carry the original `generated_text` through unchanged, available for audit. |
| **NORMALIZATION-0005** | Produce immutable `ParsedResponse` | Emit exactly one immutable, shared `ParsedResponse` (§6). |

> **Architectural Decision**
> **Normalization responsibilities define normalization behaviour only.** Every
> responsibility in this catalog:
>
> - **never creates a `ValidationIssue`**,
> - **never assigns severity**,
> - **never assigns a verdict**, and
> - **never performs validation**.
>
> They describe *what normalization does*, never *what any judgement means*. The
> catalog is governed by the Normalization Contract Version and grows additively
> through an ADR, exactly like the validation Rule Catalog grows — but the two
> catalogs never merge and never cross the boundary of §10.

---

## 14. Relationship to Other Architecture Documents

```text
   [AI Reasoning Contract]            (how the AI must reason)
            │
            ▼
   [Requirement Analysis Service]     (produces LLMResponse / AnalysisResult)
            │ emits generated_text + execution_status
            ▼
   [Response Normalization Contract]  ◄── THIS DOCUMENT
            │ governs the Response Normalization Layer → ParsedResponse (Shared Platform Artifact)
            ▼
   [Validation Canonical Models]      (defines ParsedResponse as a Core Canonical Model)
            │
            ▼
   [AI Response Validation Arch.]     (philosophy that reads ParsedResponse)
            │
            ▼
   [Validation Rule Catalog]          (Syntax reads the outcome; Schema+ read the structure)
            │
            ▼
   [Response Validator]               (orchestrates validation over ParsedResponse — first consumer)
```

| Document | Relationship to this contract |
| -------- | ----------------------------- |
| **Requirement Analysis Service** | Produces the `LLMResponse` whose `generated_text` this contract normalizes. |
| **Validation Canonical Models** | Defines `ParsedResponse` as a Core Canonical Model; this contract governs how that model is *created, owned, shared, and versioned*. |
| **AI Response Validation Architecture** | Defines validation philosophy; validation reads the `ParsedResponse` this contract produces. No validation layer normalizes. |
| **Validation Rule Catalog** | The Syntax layer reads the Normalization Outcome and Observations; Schema onward read the structure. |
| **Response Validator** | Orchestrates validation over the `ParsedResponse`; it never normalizes. It is the *first* consumer, not the owner. |
| **AI Reasoning Contract** | Defines what trustworthy output requires; normalization makes its *structure* observable without judging it. |

> **Architectural Decision**
> This contract sits **between generation and every consumer**. It depends upward
> on the analysis service that produces the response and is consumed downward by
> the canonical models, the validation philosophy, the rule catalog, the
> validator, and every future platform component. It introduces no new dependency
> direction; it names the one subsystem that already had to exist.

---

## 15. Future Extensibility

The normalization contract is designed to be **extended, never replaced**.

| Reserved direction | Intent | Constraint under this contract |
| ------------------ | ------ | ------------------------------ |
| **Additional structured formats** | Normalize new structured formats into the same `ParsedResponse`. | Format-neutral by design (§11); no consumer changes. |
| **Additional Normalization Observations** | Capture new facts a future consumer requires. | Additive observation; advances the ParsedResponse Version (shape) and, if it changes meaning, the Normalization Contract Version. |
| **Additional Normalization Outcomes** | Express a new normalized outcome class. | Governed like a new `ExecutionStatus`; advances the Normalization Contract Version; requires an ADR. |
| **Additional Normalization responsibilities** | Catalog a new normalization behaviour. | A new `NORMALIZATION-00NN` entry (§13); never a validation rule; requires an ADR. |
| **New consumers** | New platform subsystems read the same `ParsedResponse`. | Read-only consumers of the Shared Platform Artifact (§7); no change to normalization. |

> **Architectural Decision**
> **Future normalization capabilities extend the contract; they never replace it.**
> Every addition remains provider-independent, format-neutral, deterministic, and
> observation-only, and is admitted only through an ADR. A capability that repairs,
> interprets, enriches, filters, mutates, validates, or binds to a single format is
> non-conforming.

---

## 16. Architecture Principles Summary

| # | Principle | One-line meaning |
| - | --------- | ---------------- |
| 1 | **Normalize once.** | Text becomes structure exactly once, in one subsystem. |
| 2 | **Observe, never repair.** | Normalization recovers structure; it never fixes it. |
| 3 | **Provider- and format-independent.** | Structure recovery is a format concern, never a provider one. |
| 4 | **Deterministic.** | Same text, same `ParsedResponse`, every time. |
| 5 | **Non-interpreting.** | Normalization records structure; it assigns no meaning. |
| 6 | **Facts, not judgments.** | Normalization produces facts; validation produces judgments. |
| 7 | **Creation ≠ information ≠ consumption.** | Three roles, three owners, never merged. |
| 8 | **One shared, immutable artifact.** | One `ParsedResponse`, read by all, copied/mutated/recreated by none. |
| 9 | **Shared Platform Artifact.** | `ParsedResponse` belongs to the platform, not to validation. |
| 10 | **Two independent versions.** | Normalization Contract Version (semantics) and ParsedResponse Version (shape). |
| 11 | **Responsibilities frozen; mechanism free.** | Implementation may evolve; responsibilities may not. |
| 12 | **Extend, never replace.** | New formats, observations, outcomes, and responsibilities are additive and governed. |

---

## 17. Architecture Freeze

> **Architectural Decision — Architecture Freeze**
> With this document, the following are **permanently frozen architectural
> contracts** for the Response Normalization subsystem:
>
> - **The Response Normalization Layer** (§4) — a permanent, independent platform
>   subsystem with four responsibilities and seven prohibitions.
> - **`ParsedResponse`** (§5, §6; Validation Canonical Models §8) — the canonical,
>   shared structural representation.
> - **Normalization Outcome** (§9) — the governed `NORMALIZED` / `MALFORMED` fact
>   set.
> - **Normalization Observations** (§8) — recorded, un-judged facts; never a
>   `ValidationIssue`, severity, or verdict.
> - **`ParsedResponse` ownership** (§6, §7) — created once; a Shared Platform
>   Artifact, not a validation artifact.
> - **`ParsedResponse` lifecycle** (§6) — created exactly once, immutable, shared,
>   never copied, never mutated, never recreated.
> - **Response Normalization boundaries** (§10) — normalization produces facts;
>   validation produces judgments.
> - **Response Normalization responsibilities** (§4.1, §13) — the four acts and the
>   `NORMALIZATION-00NN` catalog.
> - **Normalization Contract Version** and **ParsedResponse Version** (§12) — the
>   two independent normalization versions.
>
> **Future evolution must extend these concepts; it must never replace them.**
> **Architectural changes require an approved ADR. Implementation improvements do
> not.** A change that violates any frozen contract above is non-conforming by
> definition.

> **Definition of Done**
> This document is the governing specification for response normalization in the
> Autonomous Test Engineering Platform. It establishes the Response Normalization
> Layer as a permanent subsystem that turns a provider-independent `LLMResponse`
> into the canonical, shared `ParsedResponse`, and governs normalization
> philosophy, `ParsedResponse` creation, ownership, lifecycle and sharing,
> Normalization Outcomes, Normalization Observations, the Normalization–Validation
> boundary, the two normalization versions, the Normalization Responsibility
> Catalog, and future evolution. It governs **only** normalization — never
> validation, reasoning, providers, normalization mechanism, Schema, or business
> rules. It is implementation-independent and remains valid even if the platform is
> reimplemented on an entirely different technology stack, serialization format, or
> AI provider.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Response Normalization Layer** | The permanent, independent platform subsystem that turns an `LLMResponse` into the canonical `ParsedResponse` exactly once; it validates, repairs, interprets, enriches, filters, mutates, and transforms nothing (§4). |
| **ParsedResponse** | The canonical, provider- and format-independent normalized structure of the response; created once, immutable, shared, and read by every platform consumer (§5–§7; Validation Canonical Models §8). |
| **Normalization Outcome** | A normalized, provider-independent fact — `NORMALIZED` or `MALFORMED` — stating whether well-formed structure was recovered (§9). |
| **Normalization Observation** | A recorded, un-judged fact about the response (e.g. a duplicate identifier, an encoding observation) captured on the `ParsedResponse`; never a severity, verdict, or `ValidationIssue` (§8). |
| **Shared Platform Artifact** | An artifact produced once and shared read-only across the whole platform; `ParsedResponse` is one, owned by no single consumer (§7). |
| **Normalization Contract Version** | The version governing normalization *semantics, philosophy, architecture, and compatibility rules* (§12). |
| **ParsedResponse Version** | The version governing the *canonical representation's additive shape and compatibility* (§12). |
| **Normalization Responsibility** | A catalogued `NORMALIZATION-00NN` behaviour of the subsystem; never a validation rule (§13). |
| **Normalization–Validation Boundary** | The permanent line at which facts (normalization) become judgments (validation) (§10). |

## Appendix B — Conformance Checklist

A Response Normalization Layer implementation conforms to this contract only if
every box can be checked:

- [ ] Recovers structure **exactly once**, before any consumer runs.
- [ ] Produces **one** `ParsedResponse` that is immutable, shared, never copied, never mutated, never recreated.
- [ ] Records a single **Normalization Outcome** (`NORMALIZED` / `MALFORMED`).
- [ ] Records **Normalization Observations** as un-judged facts — no severity, no verdict, never a `ValidationIssue`.
- [ ] Preserves the original `generated_text` unchanged.
- [ ] **Never** validates, repairs, interprets, enriches, filters, mutates, or transforms business meaning.
- [ ] Is **provider- and format-independent** — no provider, vendor, endpoint, or serialization format influences it.
- [ ] Is **deterministic** — the same `generated_text` yields the same `ParsedResponse` and outcome.
- [ ] Exposes the `ParsedResponse` as a **Shared Platform Artifact** — no downstream component reparses `generated_text`.
- [ ] Respects the **Normalization–Validation boundary** — produces facts, never judgments.
- [ ] Carries the two normalization versions (**Normalization Contract Version**, **ParsedResponse Version**) independently of the validation versions.
- [ ] Remains implementation-independent (no language, framework, storage, mechanism, or provider assumptions).
