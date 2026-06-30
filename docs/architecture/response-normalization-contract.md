# Response Normalization Contract

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Normalization Boundary |
| Status               | Approved — foundational                                           |
| Scope                | The normalization of a provider-independent `LLMResponse` into the canonical `ParsedResponse` |
| Governs              | Normalization philosophy · `ParsedResponse` creation · provider independence · normalization outcomes · normalization versioning · normalization evolution |
| Depends on           | AI Response Validation Architecture · Validation Canonical Models · Requirement Analysis Service |
| Audience             | Solution Architects · Technical Architects · Lead Engineers · QA Architects |
| Implementation-bound | No — valid regardless of language, framework, serialization format, or AI provider |

> **Architectural Decision**
> The **Response Normalization Layer** is the **single architectural seam at which
> a provider-independent `LLMResponse` becomes the canonical `ParsedResponse`**.
> It is not part of validation, not part of generation, and not part of any
> provider adapter. It exists for one reason: to produce, exactly once, the one
> immutable, format-neutral structural representation that every validation layer
> then reads. This contract governs *that normalization* — its philosophy, its
> outcomes, its versioning, and its independence — and nothing else.

---

## 1. Purpose

### 1.1 Why response normalization exists

The platform's AI generation layer produces an `LLMResponse` whose only content
field is `generated_text` — a single block of provider-independent text that
expresses a structured document. Every validation layer from Syntax onward needs
to reason about the **structure** that text expresses, not the text itself.

If each validation layer recovered that structure independently:

- The same response would be interpreted **many times**, once per layer, wasting
  work and inviting divergent interpretations of the same input.
- "Is this response well-formed structured data?" — a single concern — would be
  re-derived in every layer, dissolving the one-concern-per-layer guarantee of
  the validation pipeline (AI Response Validation Architecture §4).
- A subtle difference in how two layers recovered structure could make them
  **disagree about the same response**, destroying determinism.

The Response Normalization Layer exists to **recover the structure of the
response exactly once, deterministically, and provider-independently**, and to
carry that structure forward as a single canonical model — the `ParsedResponse`
— that every later layer reads without re-deriving.

> **Principle**
> The transition from **text** to **structure** happens **once**, at one seam,
> and is **shared** by every consumer. Recovering structure is a normalization
> concern, not a validation concern; validation *reads* the normalized structure,
> it never *produces* it.

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
| Response **structure** | `ParsedResponse` (by the Response Normalization Layer) | Syntax rules and every later layer |

> **Architectural Decision**
> **`ParsedResponse` is to structure what `ExecutionStatus` is to outcome.** Each
> is a normalized, provider-independent fact, produced once at a single seam and
> read — never re-derived — by the rules. The Response Normalization Layer is the
> structural counterpart of the adapter's outcome normalization.

### 1.3 What this document is **not**

| This document is NOT | Because |
| -------------------- | ------- |
| A validation specification | It governs how structure is normalized, never how structure is judged. Validation philosophy lives in the AI Response Validation Architecture. |
| A canonical model definition | `ParsedResponse`'s information model is defined in the Validation Canonical Models; this document governs how it is *created*. |
| A reasoning specification | How the AI *thinks* is governed by the AI Reasoning Contract; this document concerns only the *shape* of what it produced. |
| A provider or format document | No model, vendor, SDK, endpoint, serialization format, or normalization mechanism is referenced. |

---

## 2. Scope

### 2.1 What this contract owns

| Owned responsibility | Description |
| -------------------- | ----------- |
| **Normalization philosophy** | The principles every normalization step must satisfy (§3). |
| **`ParsedResponse` creation** | The act of producing the one canonical structural representation from an `LLMResponse` (§5, §6). |
| **Provider independence of normalization** | The guarantee that normalization is a *format* concern, never a *provider* concern (§7). |
| **Normalization outcomes** | The governed set of outcomes a normalization may report (§8). |
| **Normalization versioning** | The independent version that governs normalization *semantics* (§9). |
| **Normalization evolution** | How normalization may grow without breaking consumers (§11). |

### 2.2 What this contract does **not** own

| Not owned here | Owned elsewhere |
| -------------- | --------------- |
| **Validation** | AI Response Validation Architecture · Validation Rule Catalog |
| **Reasoning** | AI Reasoning Contract |
| **AI generation / providers** | Requirement Analysis Service · provider framework |
| **Normalization mechanism** | A replaceable implementation detail; never an architectural concern |
| **Schema conformance** | The Schema validation layer |
| **Business rules** | The Business Rule validation layer |
| **The `ParsedResponse` information model** | Validation Canonical Models (this document governs its *creation*, not its *shape*) |

> **Architectural Decision**
> The Response Normalization Layer **performs no validation, no repair, no
> interpretation, and no business logic.** It does not judge whether the structure
> is *expected* (Schema), whether containers are *present* (Structural), or what
> any value *means* (Content onward). It recovers structure and reports the
> outcome — nothing more. A normalization step that judged, repaired, or
> interpreted would collapse the boundary between *normalizing* and *validating*.

---

## 3. Normalization Philosophy

These principles are binding on every conforming Response Normalization Layer
implementation.

### 3.1 Normalize Once

The transition from `generated_text` to `ParsedResponse` happens **exactly once**
per response, at one seam, before validation begins. No consumer re-derives
structure.

### 3.2 Observe, Never Repair

Normalization recovers the structure that is **actually present**. It never
fixes, completes, reformats, coerces, or "cleans" a malformed response. A
response that does not express well-formed structure yields a `MALFORMED`
outcome (§8) — it is never silently repaired into a structure that was not there.
This mirrors **Preserve Original Response** (AI Response Validation Architecture
§3.3): the original `generated_text` survives unchanged alongside the
`ParsedResponse`.

### 3.3 Provider- and Format-Independent

Normalization references no provider, model, vendor, or endpoint, and is not
coupled to any single serialization format. It recovers *normalized structure*,
not "the structure of format X" (§7).

### 3.4 Deterministic

Given the same `generated_text`, normalization always produces the same
`ParsedResponse` and the same outcome. Normalization depends on no randomness,
time, or external mutable state. Determinism here is a precondition of the
validation pipeline's determinism (AI Response Validation Architecture §3.4).

### 3.5 Non-Interpreting

Normalization assigns no meaning. It does not decide whether a field is required,
whether a value is valid, or whether a section is missing. It records *what
structure exists* and *whether it is well-formed*; every judgement about that
structure belongs to a validation layer.

> **Principle**
> Normalization is **mechanical and meaning-free**. It answers "what structure is
> here, and is it well-formed?" — never "is this structure correct, complete, or
> acceptable?" The first is normalization; the rest is validation.

---

## 4. The Response Normalization Layer

The **Response Normalization Layer** is a permanent, first-class architecture
component. It sits between the `LLMResponse` (the provider-independent output of
generation) and the Response Validator (the orchestration boundary of
validation).

```text
   Provider Adapter
        │ normalizes outcome → ExecutionStatus, text → generated_text
        ▼
   LLMResponse                         (provider-independent text + outcome)
        │
        ▼
   Response Normalization Layer        ◄── this contract
        │ recovers structure ONCE; performs no validation / repair / interpretation
        ▼
   ParsedResponse                      (the one canonical structural representation)
        │
        ▼
   Response Validator
        │ orchestrates the pipeline
        ▼
   Validation Pipeline                 (Syntax reads outcome; Schema+ read structure)
        │
        ▼
   ValidationResult
```

| Responsibility of the layer | Description |
| --------------------------- | ----------- |
| **Receive `LLMResponse`** | Accept the provider-independent response as its only input. |
| **Recover structure once** | Produce the single normalized structural representation of `generated_text`. |
| **Report the outcome** | Record whether the response was `NORMALIZED` or `MALFORMED` (§8). |
| **Surface syntactic observations** | Capture normalized facts a later layer needs but a naïve recovery would lose (e.g. duplicate field identifiers, encoding integrity) (§6). |
| **Produce one immutable `ParsedResponse`** | Emit exactly one canonical representation, then never alter it. |

> **Architectural Decision — why the Response Normalization Layer exists.**
> Without a dedicated layer, structure recovery would either be duplicated across
> every validation layer (wasteful, non-deterministic) or smuggled into the
> Syntax layer (making every later layer depend on Syntax having run). A single,
> named component makes structure recovery a **shared, once-only, governed step**
> with one owner — exactly as the provider adapter is the single owner of outcome
> normalization. The layer is the *home* of the one canonical transition from text
> to structure.

---

## 5. ParsedResponse Creation

The Response Normalization Layer **owns creation**; the `ParsedResponse` **owns
information**; the Validation Framework **consumes information**. These three
roles are strictly separated.

| Role | Owner | Responsibility |
| ---- | ----- | -------------- |
| **Creation** | Response Normalization Layer | *How* the `ParsedResponse` comes into being (once, deterministically). |
| **Information** | `ParsedResponse` (Validation Canonical Models) | *What* the representation holds — the normalized structure and outcomes. |
| **Consumption** | Validation Framework (Syntax → Business Rule) | *Reading* the representation to reach verdicts. |

> **Architectural Decision**
> **Creation, information, and consumption are three separate concerns with three
> separate owners.** The normalization layer never validates; the `ParsedResponse`
> never creates or judges itself; the validation framework never normalizes. This
> separation is what lets the normalization mechanism evolve, the representation
> stay stable, and the rules stay independent — each without disturbing the
> others.

### 5.1 Lifecycle

```text
   1. LLMResponse exists                       (generated_text + execution_status)
                 │
                 ▼
   2. Response Normalization Layer runs        (ONCE, before validation)
                 │
                 ▼
   3. ParsedResponse is created                (immutable; outcome + structure + observations)
                 │
                 ▼
   4. Validation Pipeline reads ParsedResponse (Syntax reads outcome; Schema+ read structure)
                 │
                 ▼
   5. ValidationResult is produced             (the original generated_text is still preserved)
```

The `ParsedResponse` is created **once**, immediately after `generated_text` is
available and **before** the Validation Pipeline runs. It is **immutable** and
**read-only** for every rule; it is never re-created, never mutated, and never
re-derived by a consumer.

---

## 6. Normalization Observations

A naïve structure recovery loses facts that the Syntax layer must still be able
to judge. The Response Normalization Layer therefore captures, as **normalized
observations** on the `ParsedResponse`, any syntactic fact a later layer requires
that the structure alone would not preserve.

| Observation | Why it must be captured at normalization |
| ----------- | ----------------------------------------- |
| **Duplicate field identifiers** | A normalized structure silently collapses duplicate identifiers within one object; the *fact that a duplicate occurred* must be recorded for the Syntax layer to judge ambiguity. |
| **Encoding integrity** | Whether the response's character encoding is intact is a normalized fact established as the structure is recovered; the Syntax layer reads it rather than re-deriving it. |

> **Principle**
> An observation is a **normalized fact**, never a judgement. The normalization
> layer records *that* a duplicate identifier occurred; the Syntax layer decides
> *whether* that makes the response untrustworthy. Recording is normalization;
> deciding is validation.

---

## 7. Provider Independence

Normalization strengthens, and never weakens, provider independence.

```text
   Provider-specific payload
        │ adapter normalizes: outcome → ExecutionStatus, text → generated_text
        ▼
   generated_text                       (provider-independent text)
        │ ONE shared, format-level normalization — the only structure recovery
        ▼
   ParsedResponse                       (provider-independent structure + outcomes)
```

A new provider conforms with **no change to normalization and no change to any
rule**: its adapter normalizes its payload into `generated_text` exactly as today;
the one Response Normalization Layer recovers structure from that text. Because
structure recovery is a **format** concern — identical across every provider that
emits the requested format — **no provider-specific normalization exists
anywhere**.

> **Architectural Decision — why `ParsedResponse` is format-independent.**
> `ParsedResponse` represents **normalized structure, not a specific
> serialization format.** A structured document may be expressed today in one
> format and tomorrow in another; the structure it expresses — objects, arrays,
> scalars, identifiers — is the same. Binding `ParsedResponse` to one format would
> make every validation layer format-aware and force a rewrite whenever the format
> changed. Keeping it format-neutral means new structured formats normalize into
> the *same* representation and no rule changes.

---

## 8. Normalization Outcomes

A normalization reports exactly one **Normalization Outcome** — a normalized,
provider-independent fact analogous to `ExecutionStatus`.

| Outcome | Meaning | Consumed by |
| ------- | ------- | ----------- |
| **NORMALIZED** | The response expresses well-formed structured data; a normalized structure was recovered. | Syntax confirms well-formedness; Schema onward read the structure. |
| **MALFORMED** | The response does not express well-formed structured data; no structure could be recovered. | The Syntax layer reads this as its foundational, progression-stopping concern. |

> **Architectural Decision**
> The Normalization Outcome is the fact the **Syntax** layer validates; it is
> **not** itself a verdict. Normalization reports `MALFORMED`; the Syntax layer
> decides what that means for the verdict (a foundational, blocking concern per
> the AI Response Validation Architecture). The outcome set is deliberately small
> and governed: a new outcome is an architecture change requiring an ADR, exactly
> like a new `ExecutionStatus`.

---

## 9. Normalization Versioning

Normalization semantics are governed by an independent **Normalization Contract
Version**, distinct from every other version in the platform. Conflating them
would make it impossible to tell a change in *how structure is normalized* from a
change in *how it is validated* or *how validation is implemented*.

| Version | Governs | Changes when… |
| ------- | ------- | ------------- |
| **Normalization Contract Version** | The *semantics* of normalization: outcomes, observations, the meaning of `ParsedResponse`. | The meaning of normalization changes (a new outcome, a new observation). |
| **Validation Contract Version** | The *semantics* of validation. | The meaning of validation changes (AI Response Validation Architecture §13). |
| **Validator Version** | The validation *implementation*. | The implementation changes with no change in meaning. |
| **Framework Version** | The framework's structural components. | The framework structure changes. |

> **Architectural Decision**
> **Normalization is versioned independently of validation.** Because the
> `ParsedResponse` is consumed by every validation layer, a change to what
> normalization *means* could change what those layers observe — so it must be
> versioned and governed in its own right, advancing the Normalization Contract
> Version through an ADR. A change to the normalization *mechanism* that produces
> an identical `ParsedResponse` changes no version that consumers depend on.

---

## 10. Relationship to Other Architecture Documents

```text
   [AI Reasoning Contract]            (how the AI must reason)
            │
            ▼
   [Requirement Analysis Service]     (produces LLMResponse / AnalysisResult)
            │ emits generated_text + execution_status
            ▼
   [Response Normalization Contract]  ◄── THIS DOCUMENT
            │ governs the Response Normalization Layer → ParsedResponse
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
   [Response Validator]               (orchestrates validation over ParsedResponse)
```

| Document | Relationship to this contract |
| -------- | ----------------------------- |
| **Requirement Analysis Service** | Produces the `LLMResponse` whose `generated_text` this contract normalizes. |
| **Validation Canonical Models** | Defines `ParsedResponse` as a Core Canonical Model; this contract governs how that model is *created*. |
| **AI Response Validation Architecture** | Defines validation philosophy; the Syntax layer onward read the `ParsedResponse` this contract produces. No validation layer normalizes. |
| **Validation Rule Catalog** | The Syntax layer reads the Normalization Outcome; Schema onward read the structure. |
| **Response Validator** | Orchestrates validation over the `ParsedResponse`; it never normalizes. |
| **AI Reasoning Contract** | Defines what trustworthy output requires; normalization makes its *structure* observable without judging it. |

> **Architectural Decision**
> This contract sits **between generation and validation**. It depends upward on
> the analysis service that produces the response and is consumed downward by the
> canonical models, the validation philosophy, the rule catalog, and the
> validator. It introduces no new dependency direction; it names the one seam that
> already had to exist.

---

## 11. Future Extensibility

The normalization contract is designed to be **extended, never replaced**.

| Reserved direction | Intent | Constraint under this contract |
| ------------------ | ------ | ------------------------------ |
| **Additional structured formats** | Normalize new structured formats into the same `ParsedResponse`. | Format-neutral by design (§7); no rule changes. |
| **Additional normalization observations** | Capture new syntactic facts a future Syntax concern requires. | Additive observations on `ParsedResponse`; advances the Normalization Contract Version. |
| **Additional normalization outcomes** | Express a new normalized outcome class. | Governed like a new `ExecutionStatus`; requires an ADR. |
| **Richer structural representations** | Carry a more expressive normalized structure. | Must remain provider- and format-independent and observation-only. |

> **Architectural Decision**
> **Future normalization capabilities extend the contract; they never replace it.**
> Every addition remains provider-independent, format-neutral, deterministic, and
> observation-only, and is admitted only through an ADR that advances the
> Normalization Contract Version. A capability that repairs, interprets, validates,
> or binds to a single format is non-conforming.

---

## 12. Architecture Principles Summary

| # | Principle | One-line meaning |
| - | --------- | ---------------- |
| 1 | **Normalize once.** | Text becomes structure exactly once, at one seam. |
| 2 | **Observe, never repair.** | Normalization recovers structure; it never fixes it. |
| 3 | **Provider- and format-independent.** | Structure recovery is a format concern, never a provider one. |
| 4 | **Deterministic.** | Same text, same `ParsedResponse`, every time. |
| 5 | **Non-interpreting.** | Normalization records structure; it assigns no meaning. |
| 6 | **Creation ≠ information ≠ consumption.** | Three roles, three owners, never merged. |
| 7 | **Versioned independently.** | Normalization semantics carry their own version. |
| 8 | **Extend, never replace.** | New formats and observations are additive and governed. |

---

> **Architectural Decision — Architecture Freeze**
> With this document, the following become **frozen architectural contracts**:
>
> - **The Response Normalization Layer** (§4) — a permanent, first-class component
>   between `LLMResponse` and the Response Validator.
> - **Normalize Once** (§3.1) — structure is recovered exactly once, before
>   validation.
> - **Observe, Never Repair** (§3.2) — normalization never mutates or completes the
>   response.
> - **Provider- and Format-Independence** (§3.3, §7) — `ParsedResponse` represents
>   normalized structure, not a serialization format.
> - **Normalization Outcomes** (§8) — the governed outcome set.
> - **Normalization Contract Version** (§9) — normalization semantics versioned
>   independently.
>
> **Implementation may evolve freely** beneath these contracts. **The architecture
> may evolve only through an approved Architecture Decision Record (ADR).**

> **Definition of Done**
> This document is the governing specification for response normalization in the
> Autonomous Test Engineering Platform. It establishes the Response Normalization
> Layer as the single seam that turns a provider-independent `LLMResponse` into the
> canonical `ParsedResponse`, and governs normalization philosophy, `ParsedResponse`
> creation, provider independence, normalization outcomes, normalization
> versioning, and future evolution. It governs **only** normalization — never
> validation, reasoning, providers, normalization mechanism, Schema, or business
> rules. It is implementation-independent and remains valid even if the platform is
> reimplemented on an entirely different technology stack, serialization format, or
> AI provider.
</content>
</invoke>
