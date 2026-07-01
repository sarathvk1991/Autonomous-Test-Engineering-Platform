# Syntax Layer Design Review

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Architecture Design Review (decision record input)                 |
| Status               | Complete — recommendation issued                                  |
| Phase                | Phase 2 — Syntax layer (pre-implementation review)                 |
| Scope                | Whether the canonical execution model is sufficient for Syntax validation |
| References           | validation-rule-catalog.md · validation-canonical-models.md · response-normalization-contract.md · response-validator.md · ai-response-validation.md · ai-reasoning-contract.md · validation-rule-development-guide.md |
| Outcome              | **OPTION B** — a provider- and format-independent normalized representation is required before Syntax rules |
| Implementation-bound | No — this review specifies an abstraction; it implements nothing   |

> **This is an architectural review only.** No rule is implemented, no framework,
> validator, pipeline, registry, or canonical model is modified. The review
> determines the next implementation step and specifies (without building) any
> abstraction it proves necessary.

> **Refinement note (architecture refinement following this review).** The
> abstraction this review proves necessary has since been generalized and made
> first-class: the creating component is the **Response Normalization Layer**
> (governed by the **Response Normalization Contract**); the representation is the
> **`ParsedResponse`**, a **Core Canonical Model** (Validation Canonical Models §8)
> that represents **normalized structure, not a specific serialization format**.
> The wording throughout this review reflects that refinement: "normalization"
> replaces any format- or mechanism-specific framing, and creation
> (Response Normalization Layer), information (`ParsedResponse`), and consumption
> (Validation Framework) are treated as three separate concerns.
>
> The Response Normalization architecture has since been **frozen** (Response
> Normalization Contract §17). Three further refinements that post-date this review
> and govern its conclusions: (1) `ParsedResponse` is a **Shared Platform Artifact**
> — validation is its *first* consumer, not its owner, and Requirement
> Normalization, Feature Generation, Test Generation, AI Evaluation, and Analytics
> read the same instance; (2) **normalization produces facts, validation produces
> judgments** — a Normalization Outcome or Normalization Observation is never a
> severity, verdict, or `ValidationIssue`; (3) normalization carries **two
> independent versions** — the **Normalization Contract Version** (semantics) and
> the **ParsedResponse Version** (representation shape).

---

## 1. Purpose

The Transport layer is complete and frozen. Before any Syntax rule is written,
this review answers one decisive question:

> **Can Syntax rules operate directly on `generated_text`, or does the platform
> require a normalized, provider-independent structured representation first?**

The answer determines whether the next milestone is "implement Syntax rules"
(Option A) or "implement a canonical normalized representation, *then* Syntax
rules" (Option B).

---

## 2. Current Architecture

### 2.1 What exists today

| Element | Today |
| ------- | ----- |
| AI output | The model is prompted to return **structured data** (a single structured document). |
| `LLMResponse.generated_text` | The **raw text** of that document — a `str`. The only content field on the canonical model. |
| `LLMResponse` (normalized) | `execution_status` (`COMPLETED`/`TIMEOUT`/`FAILED`), `usage`, `latency_ms` — provider-independent, normalized by the adapter. |
| `LLMResponse` (opaque) | `finish_reason`, `raw_response` — provider-specific, never interpreted downstream. |
| `AnalysisResult` | Carries one `LLMResponse` plus execution identity/provenance. |
| **Normalized structure** | **Not on the canonical model.** The execution/reporting package alone recovers structure from `generated_text` ad hoc (`execution_metrics.observe_response_counts`) to report a well-formedness flag and array counts. That recovery is observation-only and is *not* available to validation. |

### 2.2 The decisive observation

The platform **already recovers the response's structure** — but in the
*reporting* layer, ad hoc, and the result is **thrown away** (not carried on the
canonical model). The canonical model exposes only the **raw `generated_text`
string**. Validation has no normalized structural view.

> **Finding.** Structure recovery already happens; it is simply not canonical. The
> question is not *whether* the response must be normalized, but *where the one
> canonical normalization lives* and *who owns it*. (The refined architecture
> answers this: the **Response Normalization Layer** owns it.)

---

## 3. Transport Assumptions (the foundation Syntax builds on)

Because the Transport layer is frozen and every Transport rule is `CRITICAL`/
blocking, any response that **reaches the Syntax layer** has already satisfied
four guarantees. Syntax may assume them and must never re-check them:

| Guarantee (assumed) | Owned by |
| ------------------- | -------- |
| A response object exists (`llm_response is not None`) | `TRANSPORT-0001` |
| The response carries non-empty generated content | `TRANSPORT-0002` |
| The execution did not time out (`execution_status != TIMEOUT`) | `TRANSPORT-0003` |
| The execution did not fail at the delivery boundary (`execution_status != FAILED`) | `TRANSPORT-0004` |

Syntax therefore starts from: *"non-empty text from a completed, delivered
execution exists."* Its job begins exactly where Transport's ends.

---

## 4. Syntax Responsibilities

Per the Rule Catalog (§8.2) and AI Response Validation Architecture (§4), the
Syntax layer owns **one family of concerns: is the response well-formed
structured data that can be interpreted without ambiguity?**

Syntax owns (it **judges** these by reading the normalized representation; it
never recovers the structure itself):

- **Well-formedness** — the response normalized into a single, unambiguous
  structural representation (outcome `NORMALIZED`).
- **Invalid serialization / malformed document** — the response did *not*
  normalize (outcome `MALFORMED`).
- **Ambiguity within the structure** — e.g. duplicate field identifiers in the
  same object that make interpretation non-deterministic.
- **Character-encoding integrity** — the text is intact, not corrupted by a lossy
  decode.

Syntax does **not** own: recovering the structure (that is the Response
Normalization Layer), whether the (well-formed) structure matches an *expected*
shape (Schema), whether required containers exist (Structural), or any field
meaning (Content onward).

### 4.1 Classifying the example concerns

The brief listed several concerns; each belongs to exactly one layer:

| Concern | Layer | Why |
| ------- | ----- | --- |
| Well-formed response | **Syntax** | Well-formedness of the structured document. |
| Parseability | **Syntax** | The defining Syntax question — judged from the normalization outcome. |
| Invalid serialization | **Syntax** | The document is not well-formed structured data. |
| Malformed document | **Syntax** | Same family — the normalization outcome is `MALFORMED`. |
| Structural completeness | **Schema** (required sections) + **Structural** (container composition) | "Expected sections present" is Schema; "containers present and correctly nested" is Structural. **Not Syntax.** |
| Unexpected truncation | **Transport** (delivery completeness) | "Was the delivery cut short?" is a delivery-level fact. Its *symptom* (the response won't normalize) surfaces at Syntax, but the *concern* is Transport. |

> **Boundary note — truncation vs. malformedness.** A response truncated at the
> delivery boundary is a **Transport** concern ("the delivery did not complete").
> Whether the bytes we *do* have form a well-formed document is a **Syntax**
> concern. A complete-but-malformed document fails Syntax, not Transport; a
> truncated delivery is caught at Transport. They are distinct and must not be
> conflated.

---

## 5. Layer Boundaries (no overlap; one family of concerns each)

| Layer | Owns (one family) | Reads | Does **not** touch |
| ----- | ----------------- | ----- | ------------------ |
| **Response Normalization** *(not a validation layer)* | Creating the normalized representation once | `LLMResponse.generated_text` | Any judgement — it validates nothing |
| **Transport** | Delivery-level guarantees about the execution | `llm_response` presence, `generated_text` emptiness, `execution_status` | Anything about the *content* of the text |
| **Syntax** | Well-formedness of the response as structured data | the **normalized representation** → its **Normalization Outcome** + **Normalization Observations** | Whether the structure matches an expected shape |
| **Schema** | Conformance of the normalized structure to the expected, versioned shape | the **normalized structure** (fields, types, enums, required collections) | Field *meaning* or *quality* |
| **Structural** | Presence/composition of required containers & relationships | the **normalized structure** (top-level sections, nesting) | The *content* inside containers |
| **Content** | Field-level value validity (presence, range, duplication) | the **normalized structure** (individual values) | Groundedness, traceability, coherence |
| **Evidence** | Conclusions carry required evidence references | the **normalized structure** (evidence links present) | Whether links resolve / are coherent |
| **Traceability** | Elements are traceable to source/context | the **normalized structure** (trace links) | Whether evidence exists / is coherent |
| **Reasoning** | Internal coherence & consistency | the **normalized structure** (cross-element) | Declared platform policy |
| **Business Rule** | Declared platform-level structural policy | the **normalized structure** (coverage/completeness) | Real-world correctness, approval |

> **Critical structural fact.** The transition from *text* to *structure* happens
> **once, in the Response Normalization Layer — before any validation layer runs**,
> not inside Syntax. Syntax is the **first layer to read** the normalized
> representation (its outcome and observations); every layer from **Schema onward
> reads the normalized structure**. No validation layer recovers structure for
> itself — which is precisely what makes Response Normalization a first-class
> component rather than a Syntax responsibility.

---

## 6. Canonical Model Assessment

### 6.1 Inspection

| Model | Carries a normalized/structured view? | Sufficient for Syntax+? |
| ----- | --------------------------------- | ----------------------- |
| `LLMResponse` | **No** — only raw `generated_text: str` | Sufficient for *normalizing from*, not for *reading structure* |
| `AnalysisResult` | **No** — wraps `LLMResponse` | Same |
| `ValidationResult` | N/A — it is the *output* of validation, not an input | Not applicable |

### 6.2 The core problem: re-derived structure and rule independence

If Syntax rules recover structure from `generated_text` directly and nothing is
normalized (Option A), then **every layer from Schema onward must recover the
structure again** to read fields — there is no normalized structure to read. This
collides with two frozen principles:

- **Rule Independence (Catalog §16).** Rules are stateless and share no mutable
  state, so they cannot hand a recovered structure to one another. Under Option A
  each rule that needs structure must **re-derive it** — structure would be
  recovered once at Syntax and then again in *every* Schema/Structural/Content/
  Evidence/Traceability/Reasoning/Business rule. That is wasteful and a
  determinism hazard (two rules could recover structure with different leniency
  and disagree).
- **One concern, one layer (Catalog §8).** "Is it well-formed?" is a **Syntax**
  concern. If Schema must re-derive well-formedness to read a field, the Syntax
  concern leaks into every later layer.

### 6.3 The established precedent: normalize once

The platform already solved the identical shape of problem for execution
outcomes: the provider adapter **normalizes once** into `ExecutionStatus`, and
every rule **reads the normalized fact** rather than interpreting provider codes.
The same principle applies to structure: **normalize once** into a canonical
representation; Syntax validates the **normalization outcome**; Schema onward read
the **normalized structure**. No rule re-derives structure; no rule depends on
another rule.

> **Architectural Decision (proposed → since adopted).** The transition from raw
> text to normalized structure must happen **exactly once**, in a dedicated
> first-class component — the **Response Normalization Layer** (Response
> Normalization Contract) — and the result must be a **canonical, provider- and
> format-independent representation** (`ParsedResponse`) that every validation
> layer reads. This mirrors `ExecutionStatus` precisely — outcome normalized once,
> read by rules; here, **structure** is normalized once, read by rules. Creation is
> owned by the Response Normalization Layer; the `ParsedResponse` owns the
> information; the Validation Framework consumes it. The three never merge.

---

## 7. Required Abstraction (specified — NOT implemented)

The review concludes a missing abstraction exists. It is specified here for a
future task; **this review implements nothing.**

### 7.1 Proposed concept

A provider- and format-independent **`ParsedResponse`** (alternative names:
`StructuredResponse`, `DocumentRepresentation`) — the **canonical structural
representation of an AI response**. It carries the **one canonical normalized
structure** of `generated_text`. It **represents normalized structure, not a
specific serialization format**; normalization is merely today's mechanism for
producing it, and a future structured format normalizes into the same
representation.

The refinement separates three concerns with three owners:

| Concern | Owner | Responsibility |
| ------- | ----- | -------------- |
| **Creation** | **Response Normalization Layer** (Response Normalization Contract) | *How* the `ParsedResponse` comes into being — once, deterministically, before validation. |
| **Information** | **`ParsedResponse`** (Validation Canonical Models §8) | *What* the representation holds — normalized structure, outcome, source reference. The Normalization Observations are aggregated by the **`NormalizationResult`**, not the `ParsedResponse`. |
| **Consumption** | **Validation Framework** (Syntax → Business Rule) | *Reading* the representation to reach verdicts; never creating or normalizing it. |

| Aspect | Specification |
| ------ | ------------- |
| **Responsibility** | Hold the single, normalized structural view of `generated_text`, the **Normalization Outcome**, and a reference to the preserved original — so that consumers *read*, never *recover structure*. The **Normalization Observations** consumers need are aggregated by the **`NormalizationResult`**, not held on the `ParsedResponse`. |
| **Normalization Outcome** | A normalized enum, e.g. `NORMALIZED` / `MALFORMED` — analogous to `ExecutionStatus`. This is the **fact** `SYNTAX-0001` reads (never itself a verdict). |
| **Structure** | When `NORMALIZED`: a normalized structural tree (objects/arrays/scalars/identifiers) — the input Schema/Structural/Content/… and every other platform consumer read. **Format-neutral by definition.** |
| **Normalization Observations** | Recorded, un-judged **facts** a naïve structural view would lose — aggregated by the **`NormalizationResult`** (the aggregate that owns the `ParsedResponse`), never carried on the `ParsedResponse`. E.g. **duplicate field identifiers** (a normalized structure silently de-duplicates), needed by `SYNTAX-0002`; and **encoding integrity**, needed by `SYNTAX-0003`. They carry no severity or verdict and are never a `ValidationIssue` (Response Normalization Contract §8, §10). |
| **Ownership / producer** | The **Response Normalization Layer** — a permanent, first-class component between `LLMResponse` and the Response Validator. Structure recovery is a **format** concern, identical across providers, so it is **not** per-adapter and **not** per-rule logic. |
| **Carrier** | Recommended: a field on `LLMResponse` (a normalized derivative of `generated_text`, sitting beside `execution_status`). Alternative: on `AnalysisResult`. Either keeps it on the canonical model the rules already receive. |
| **Lifecycle** | Created **once**, immediately after `generated_text` is available and before validation; **immutable**; **read-only** for every rule; never mutated, never re-derived. |
| **Relationship to existing models** | A normalized derivative of `LLMResponse.generated_text`; reached by rules via the `AnalysisResult` under validation; a **Core Canonical Model** and the structural sibling of `ExecutionStatus` (which normalizes *outcome*; this normalizes *structure*). |
| **Why it belongs in the canonical model** | Every layer from Syntax onward depends on it; it must be produced once, deterministically, and shared as a stable contract — the defining purpose of a canonical model. It is a peer of the other canonical models, not a Syntax-specific one. |
| **Why it must be provider-independent** | Structure is a **format** concern, not a provider concern. Every provider's adapter already yields `generated_text` in the same requested format; one format-level normalization recovers it. No provider-specific structure logic exists anywhere — exactly like `ExecutionStatus`. |

### 7.2 What it is **not**

- Not a Schema. It records *that the response is well-formed* and *what structure
  resulted* — never whether that structure matches an expected shape (that is
  Schema).
- Not provider-specific. It never holds SDK payloads (`raw_response`) or
  provider strings (`finish_reason`).
- Not format-specific. It represents normalized structure, never a particular
  serialization format.
- Not a repair. It normalizes; it never fixes, completes, or coerces malformed
  input (consistent with "observe, never repair").

---

## 8. Provider Independence

The proposed `ParsedResponse` strengthens, and never weakens, provider
independence:

```text
   Provider-specific payload
        │ (adapter normalizes outcome → ExecutionStatus, text → generated_text)
        ▼
   generated_text (provider-independent text)
        │ Response Normalization Layer — format-level normalization, the ONLY recovery
        ▼
   Normalization Result (aggregate)
        ├─ ParsedResponse { Normalization Outcome · structure · source reference }
        └─ Normalization Observations (execution facts)
        │ read read-only
        ▼
   Syntax rules (outcome + observations)  →  Schema+ rules (structure)
```

A new provider (Azure OpenAI, Anthropic, Bedrock, Ollama, …) conforms with **no
change to any rule and no change to normalization**: it normalizes its payload
into `generated_text` exactly as today; the one Response Normalization Layer
recovers structure from that text into `ParsedResponse`. No provider-specific
structure recovery exists, mirroring the `ExecutionStatus` model that is already
proven across the frozen Transport layer.

---

## 9. Execution Flow (proposed, end-to-end)

```text
   Requirement Analysis Service
        │ provider adapter normalizes → LLMResponse(generated_text, execution_status, …)
        ▼
   Response Normalization Layer: normalize generated_text  →  Normalization Result   (ONCE)
        │ aggregates the ParsedResponse + Normalization Observations
        ▼
   Response Validator → Validation Pipeline (layer order)
        ├─ Transport  reads execution_status / presence / emptiness     (frozen)
        ├─ Syntax     reads ParsedResponse.normalization_outcome + NormalizationResult observations  ← new layer
        └─ Schema +   read ParsedResponse.structure
        ▼
   ValidationResult
```

Under this flow the Syntax rules read normalized facts and are therefore
**order-independent** among themselves (Rule Independence holds); Schema onward
read the structure without re-deriving it.

---

## 10. Syntax Rule Preview (catalogued §9.2 — analysis only)

| Rule | Single concern | Reads (under Option B) | Notes |
| ---- | -------------- | ---------------------- | ----- |
| `SYNTAX-0001` ValidStructureRule | The response is well-formed structured data | `ParsedResponse.normalization_outcome == MALFORMED` | Foundational; `CRITICAL`/blocking — a malformed response cannot be validated further. |
| `SYNTAX-0002` DuplicateKeysRule | No duplicate field identifier within an object | `NormalizationResult` duplicate-identifier observation | Requires normalization to **surface duplicates**; a normalized structure silently drops them. This is a concrete requirement on the Normalization Observation design (aggregated by the `NormalizationResult`). |
| `SYNTAX-0003` EncodingRule | The response's character encoding is intact | `NormalizationResult` encoding observation (or `generated_text` integrity) | See finding below — its true home needs confirmation. |

**Execution order & dependencies.** Under Option B every Syntax rule reads a
normalized fact, so the rules are **independent and order-free** (only the
*layer* ordering — Transport → Syntax → Schema — matters). Each is a single
responsibility; none should be split.

**Findings on individual rules (for the implementation task, not decided here):**

- **`SYNTAX-0002` constrains the abstraction.** Because a normalized structure
  silently de-duplicates identifiers, `ParsedResponse` must **record
  duplicate-identifier occurrences** for `SYNTAX-0002` to read. This is a design
  input to the abstraction, not a blocker.
- **`SYNTAX-0003` (Encoding) — home to confirm.** `generated_text` is already a
  **decoded `str`** by the time it reaches the canonical model (decoding happens
  at the adapter). So "encoding intact" is largely established *before* Syntax.
  Two coherent options for the implementation task: (a) treat encoding integrity
  as a **normalized observation** captured by the Response Normalization Layer and
  have `SYNTAX-0003` read it; or (b) re-examine whether the concern is a
  delivery/normalization fact closer to Transport. Either way it does **not**
  change this review's recommendation. No rule needs to *move layers* today; this
  is a scoping question for the rule's implementation.

No catalogued Syntax rule should move to another layer, and none should be split.

---

## 11. Engineering Review — raw text vs. normalized representation

| Dimension | Option A — rules recover structure from `generated_text` | Option B — normalized `ParsedResponse` |
| --------- | --------------------------------------- | -------------------------------------- |
| Structure recoveries per run | 1 (Syntax) **+ N** (every later rule that reads a field) | **Exactly 1** (Response Normalization Layer) |
| Rule Independence (§16) | Strained — rules re-derive structure; risk of divergent recoveries | Upheld — rules read one normalized fact |
| One concern, one layer (§8) | Violated — well-formedness re-derived in Schema+ | Upheld — normalization outcome read by Syntax |
| Determinism | At risk — multiple recoveries can disagree | Strong — one normalization, one result |
| Consistency with platform | Diverges from the `ExecutionStatus` precedent | Matches the proven "normalize once" precedent |
| Provider compatibility | Equal | Equal (format-level normalization; no provider logic) |
| Upfront work before Syntax | Lower (no new model) | Higher (specify + build the model first) |
| Long-term rework | High — Schema layer forces the model anyway, after Syntax shipped on raw text | Low — built once, every layer benefits |

**Conclusion of the engineering review.** Option A's only advantage is lower
*immediate* effort; it incurs guaranteed rework at the Schema layer and conflicts
with two frozen principles. Option B normalizes once, upholds Rule Independence
and layer ownership, and matches the established normalization precedent.

---

## 12. Future Extensibility

- **More structured formats.** `ParsedResponse` represents normalized structure,
  not a serialization format; the abstraction names "structured data," not any one
  format. A future structured format normalizes into the same representation;
  rules are unaffected.
- **More providers.** Covered by §8 — no provider-specific structure recovery
  exists.
- **Richer syntactic checks.** New Syntax concerns (e.g. additional ambiguity
  classes) become new `SYNTAX-00NN` rules reading additional normalized
  observations aggregated by the `NormalizationResult` — additive, governed by ADR,
  no framework change.
- **Schema onward.** Every later layer consumes `ParsedResponse.structure`
  unchanged; the abstraction is the shared substrate for the rest of the
  pipeline.

---

## 13. Recommendations

1. **Adopt Option B.** Introduce a provider- and format-independent, normalized
   representation (`ParsedResponse`/`StructuredResponse`) as a **Core Canonical
   Model** **before** implementing any Syntax rule.
2. **Normalize once, in the Response Normalization Layer** (post-adapter,
   pre-pipeline), governed by the **Response Normalization Contract**. Structure
   recovery is a format concern, not per-provider and not per-rule logic.
3. **Design the representation to record Normalization Observations** a normalized
   structure loses — at minimum duplicate-identifier occurrences (`SYNTAX-0002`)
   and an encoding-integrity signal (`SYNTAX-0003`).
4. **Keep it observation-only** — normalize, never repair (no completion, no
   coercion), consistent with the platform's "observe, never repair" stance.
5. **Confirm `SYNTAX-0003`'s home** during the model task (normalized observation
   vs. a delivery/normalization fact); do not block on it.
6. **Do not modify the frozen Transport layer, framework, validator, pipeline, or
   registry** — the change is purely an additive Core Canonical Model + the
   Response Normalization Layer that creates it.

---

## 14. Architecture Decision

> **Architectural Decision**
> Syntax rules **must not** recover structure from `generated_text` independently.
> The platform shall introduce a single, provider- and format-independent
> **normalized representation** of the response (`ParsedResponse`), produced
> **once** by the **Response Normalization Layer** (Response Normalization
> Contract) and carried on the canonical model as a **Core Canonical Model**, which
> the Syntax layer validates (its normalization outcome) and every subsequent layer
> reads (its structure). Creation, information, and consumption are three separate
> concerns: the Response Normalization Layer creates it, the `ParsedResponse` holds
> it, the Validation Framework consumes it. This upholds Rule Independence and
> one-concern-per-layer and extends the proven "normalize once" precedent
> established by `ExecutionStatus`. The representation is **specified** by this
> review and **implemented by a dedicated future task** — not here.

---

## 15. Final Conclusion

The existing canonical model exposes only **raw `generated_text`**. Syntax could
*technically* recover structure from it directly, but doing so would force **every
later layer to re-derive the structure**, breaking Rule Independence and leaking
the Syntax concern across the pipeline. The platform already proves it recovers
the response's structure — only in the reporting layer, ad hoc, and discards the
result. The correct architecture is to **normalize once** into a canonical,
provider- and format-independent representation, exactly as execution outcomes are
normalized once into `ExecutionStatus`.

> ### Recommendation: **OPTION B**
>
> **A new provider- and format-independent canonical representation is required.**
> Implement that model (the `ParsedResponse`/`StructuredResponse` Core Canonical
> Model and the Response Normalization Layer that creates it) **before** writing
> any Syntax rule.
>
> Option A (operate directly on `generated_text`) is **rejected**: it conflicts
> with Rule Independence (§16) and one-concern-per-layer (§8), diverges from the
> `ExecutionStatus` precedent, and guarantees rework at the Schema layer.

**Next milestone:** *Response Normalization task* — specify and implement the
provider- and format-independent `ParsedResponse` Core Canonical Model and the
**Response Normalization Layer** that creates it (governed by the **Response
Normalization Contract**; additive only; no
Transport/framework/validator/pipeline/registry change). Syntax rule
implementation (`SYNTAX-0001`–`SYNTAX-0003`) begins **after** that model and layer
land.
