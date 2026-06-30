# Syntax Layer Design Review

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Architecture Design Review (decision record input)                 |
| Status               | Complete — recommendation issued                                  |
| Phase                | Phase 2 — Syntax layer (pre-implementation review)                 |
| Scope                | Whether the canonical execution model is sufficient for Syntax validation |
| References           | validation-rule-catalog.md · validation-canonical-models.md · response-validator.md · ai-response-validation.md · ai-reasoning-contract.md · validation-rule-development-guide.md |
| Outcome              | **OPTION B** — a provider-independent parsed representation is required before Syntax rules |
| Implementation-bound | No — this review specifies an abstraction; it implements nothing   |

> **This is an architectural review only.** No rule is implemented, no framework,
> validator, pipeline, registry, or canonical model is modified. The review
> determines the next implementation step and specifies (without building) any
> abstraction it proves necessary.

---

## 1. Purpose

The Transport layer is complete and frozen. Before any Syntax rule is written,
this review answers one decisive question:

> **Can Syntax rules operate directly on `generated_text`, or does the platform
> require a normalized, provider-independent structured representation first?**

The answer determines whether the next milestone is "implement Syntax rules"
(Option A) or "implement a canonical parsed representation, *then* Syntax rules"
(Option B).

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
| **Parsed structure** | **Not on the canonical model.** The execution/reporting package alone parses `generated_text` ad hoc (`execution_metrics.observe_response_counts`) to report `json_valid` and array counts. That parse is observation-only and is *not* available to validation. |

### 2.2 The decisive observation

The platform **already parses the response** — but in the *reporting* layer, ad
hoc, and the result is **thrown away** (not carried on the canonical model). The
canonical model exposes only the **raw `generated_text` string**. Validation has
no normalized structural view.

> **Finding.** A parse already happens; it is simply not canonical. The question
> is not *whether* the response must be parsed, but *where the one canonical
> parse lives* and *who owns it*.

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

Syntax owns:

- **Well-formedness / parseability** — the text parses into a single, unambiguous
  structural representation.
- **Invalid serialization / malformed document** — the text does *not* parse.
- **Ambiguity within the structure** — e.g. duplicate field identifiers in the
  same object that make interpretation non-deterministic.
- **Character-encoding integrity** — the text is intact, not corrupted by a lossy
  decode.

Syntax does **not** own: whether the (well-formed) structure matches an
*expected* shape (Schema), whether required containers exist (Structural), or any
field meaning (Content onward).

### 4.1 Classifying the example concerns

The brief listed several concerns; each belongs to exactly one layer:

| Concern | Layer | Why |
| ------- | ----- | --- |
| Well-formed response | **Syntax** | Parseability of the structured document. |
| Parseability | **Syntax** | The defining Syntax question. |
| Invalid serialization | **Syntax** | The document is not well-formed structured data. |
| Malformed document | **Syntax** | Same family — the parse fails. |
| Structural completeness | **Schema** (required sections) + **Structural** (container composition) | "Expected sections present" is Schema; "containers present and correctly nested" is Structural. **Not Syntax.** |
| Unexpected truncation | **Transport** (delivery completeness) | "Was the delivery cut short?" is a delivery-level fact. Its *symptom* (the resulting text won't parse) surfaces at Syntax, but the *concern* is Transport. |

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
| **Transport** | Delivery-level guarantees about the execution | `llm_response` presence, `generated_text` emptiness, `execution_status` | Anything about the *content* of the text |
| **Syntax** | Well-formedness of the text as structured data | the **text** → its **parse outcome** + syntactic observations | Whether the structure matches an expected shape |
| **Schema** | Conformance of the parsed structure to the expected, versioned shape | the **parsed structure** (fields, types, enums, required collections) | Field *meaning* or *quality* |
| **Structural** | Presence/composition of required containers & relationships | the **parsed structure** (top-level sections, nesting) | The *content* inside containers |
| **Content** | Field-level value validity (presence, range, duplication) | the **parsed structure** (individual values) | Groundedness, traceability, coherence |
| **Evidence** | Conclusions carry required evidence references | the **parsed structure** (evidence links present) | Whether links resolve / are coherent |
| **Traceability** | Elements are traceable to source/context | the **parsed structure** (trace links) | Whether evidence exists / is coherent |
| **Reasoning** | Internal coherence & consistency | the **parsed structure** (cross-element) | Declared platform policy |
| **Business Rule** | Declared platform-level structural policy | the **parsed structure** (coverage/completeness) | Real-world correctness, approval |

> **Critical structural fact.** Syntax is the **last layer that operates on the
> text**. Every layer from **Schema onward operates on the parsed structure.**
> The transition from *text* to *structure* happens **at Syntax** — which makes
> Syntax the natural home for the one canonical parse.

---

## 6. Canonical Model Assessment

### 6.1 Inspection

| Model | Carries a parsed/structured view? | Sufficient for Syntax+? |
| ----- | --------------------------------- | ----------------------- |
| `LLMResponse` | **No** — only raw `generated_text: str` | Sufficient for *parsing from*, not for *reading structure* |
| `AnalysisResult` | **No** — wraps `LLMResponse` | Same |
| `ValidationResult` | N/A — it is the *output* of validation, not an input | Not applicable |

### 6.2 The core problem: re-parsing and rule independence

If Syntax rules parse `generated_text` directly and nothing is normalized
(Option A), then **every layer from Schema onward must parse `generated_text`
again** to read fields — there is no parsed structure to read. This collides with
two frozen principles:

- **Rule Independence (Catalog §16).** Rules are stateless and share no mutable
  state, so they cannot hand a parsed object to one another. Under Option A each
  rule that needs structure must **re-parse** — the response would be parsed once
  at Syntax and then again in *every* Schema/Structural/Content/Evidence/
  Traceability/Reasoning/Business rule. That is wasteful and a determinism hazard
  (two rules could parse with different leniency and disagree).
- **One concern, one layer (Catalog §8).** "Is it parseable?" is a **Syntax**
  concern. If Schema must re-derive parseability to read a field, the Syntax
  concern leaks into every later layer.

### 6.3 The established precedent: normalize once

The platform already solved the identical shape of problem for execution
outcomes: the provider adapter **normalizes once** into `ExecutionStatus`, and
every rule **reads the normalized fact** rather than interpreting provider codes.
The same principle applies to structure: **parse once** into a normalized
representation; Syntax validates the **parse outcome**; Schema+ read the
**parsed structure**. No rule re-parses; no rule depends on another rule.

> **Architectural Decision (proposed).** The transition from raw text to parsed
> structure must happen **exactly once**, at a single normalization seam, and the
> result must be a **canonical, provider-independent representation** that every
> validation layer reads. This mirrors `ExecutionStatus` precisely — outcome
> normalized once, read by rules; here, **structure** is normalized once, read by
> rules.

---

## 7. Required Abstraction (specified — NOT implemented)

The review concludes a missing abstraction exists. It is specified here for a
future task; **this review implements nothing.**

### 7.1 Proposed concept

A provider- and format-independent **`ParsedResponse`** (alternative names:
`StructuredResponse`, `DocumentRepresentation`). It carries the **one canonical
parse** of `generated_text`.

| Aspect | Specification |
| ------ | ------------- |
| **Responsibility** | Hold the single, normalized structural view of `generated_text`, the **parse outcome**, and the **syntactic observations** needed by Syntax — so that validators *read*, never *parse*. |
| **Parse outcome** | A normalized enum, e.g. `ParseStatus { PARSED, MALFORMED }` — analogous to `ExecutionStatus`. This is the fact `SYNTAX-0001` reads. |
| **Structure** | When `PARSED`: a normalized structural tree (objects/arrays/scalars) — the input Schema/Structural/Content/… read. Format-neutral in concept. |
| **Syntactic observations** | Normalized facts a standard parse would lose — e.g. **duplicate field identifiers** (a standard parse silently de-duplicates), needed by `SYNTAX-0002`; and **encoding integrity**, needed by `SYNTAX-0003`. |
| **Ownership / producer** | A **single shared normalization step** at the same seam as adapter normalization (after `generated_text` exists, **before** the Validation Pipeline runs). Parsing is a **format** concern, identical across providers, so it is **not** per-adapter logic. |
| **Carrier** | Recommended: a field on `LLMResponse` (a normalized derivative of `generated_text`, sitting beside `execution_status`). Alternative: on `AnalysisResult`. Either keeps it on the canonical model the rules already receive. |
| **Lifecycle** | Created **once**, immediately after `generated_text` is available and before validation; **immutable**; **read-only** for every rule; never mutated, never re-parsed. |
| **Relationship to existing models** | A normalized derivative of `LLMResponse.generated_text`; reached by rules via the `AnalysisResult` under validation; conceptually the structural sibling of `ExecutionStatus` (which normalizes *outcome*; this normalizes *structure*). |
| **Why it belongs in the canonical model** | Every layer from Syntax onward depends on it; it must be produced once, deterministically, and shared as a stable contract — the defining purpose of a canonical model. |
| **Why it must be provider-independent** | Parsing/structure is a **format** concern, not a provider concern. Every provider's adapter already yields `generated_text` in the same requested format; one format-level normalization parses it. No provider-specific parse logic exists anywhere — exactly like `ExecutionStatus`. |

### 7.2 What it is **not**

- Not a Schema. It records *that the text parsed* and *what structure resulted* —
  never whether that structure matches an expected shape (that is Schema).
- Not provider-specific. It never holds SDK payloads (`raw_response`) or
  provider strings (`finish_reason`).
- Not a repair. It parses; it never fixes, fence-strips, or coerces malformed
  input (consistent with "observe, never repair").

---

## 8. Provider Independence

The proposed `ParsedResponse` strengthens, and never weakens, provider
independence:

```text
   Provider-specific payload
        │ (adapter normalizes outcome → ExecutionStatus, text → generated_text)
        ▼
   generated_text (raw, normalized text)
        │ (single shared, format-level normalization — the ONLY parse)
        ▼
   ParsedResponse { parse outcome · structure · syntactic observations }
        │ read read-only
        ▼
   Syntax rules (parse outcome)  →  Schema+ rules (structure)
```

A new provider (Azure OpenAI, Anthropic, Bedrock, Ollama, …) conforms with **no
change to any rule and no change to the parse**: it normalizes its payload into
`generated_text` exactly as today; the one shared normalization parses that text
into `ParsedResponse`. No provider-specific parsing exists, mirroring the
`ExecutionStatus` model that is already proven across the frozen Transport layer.

---

## 9. Execution Flow (proposed, end-to-end)

```text
   Requirement Analysis Service
        │ provider adapter normalizes → LLMResponse(generated_text, execution_status, …)
        ▼
   Normalization seam: parse generated_text  →  ParsedResponse   (ONCE)
        │ attached to the canonical model (LLMResponse / AnalysisResult)
        ▼
   Response Validator → Validation Pipeline (layer order)
        ├─ Transport  reads execution_status / presence / emptiness   (frozen)
        ├─ Syntax     reads ParsedResponse.parse_status + observations  ← new layer
        └─ Schema +   read ParsedResponse.structure
        ▼
   ValidationResult
```

Under this flow the Syntax rules read normalized facts and are therefore
**order-independent** among themselves (Rule Independence holds); Schema onward
read the structure without re-parsing.

---

## 10. Syntax Rule Preview (catalogued §9.2 — analysis only)

| Rule | Single concern | Reads (under Option B) | Notes |
| ---- | -------------- | ---------------------- | ----- |
| `SYNTAX-0001` ValidStructureRule | The response is well-formed structured data | `ParsedResponse.parse_status == MALFORMED` | Foundational; `CRITICAL`/blocking — a malformed document cannot be validated further. |
| `SYNTAX-0002` DuplicateKeysRule | No duplicate field identifier within an object | `ParsedResponse` duplicate-key observation | Requires the parse to **surface duplicates**; a standard parse drops them. This is a concrete requirement on the `ParsedResponse` design. |
| `SYNTAX-0003` EncodingRule | The response's character encoding is intact | `ParsedResponse` encoding observation (or `generated_text` integrity) | See finding below — its true home needs confirmation. |

**Execution order & dependencies.** Under Option B every Syntax rule reads a
normalized fact, so the rules are **independent and order-free** (only the
*layer* ordering — Transport → Syntax → Schema — matters). Each is a single
responsibility; none should be split.

**Findings on individual rules (for the implementation task, not decided here):**

- **`SYNTAX-0002` constrains the abstraction.** Because a standard parse silently
  de-duplicates keys, `ParsedResponse` must **record duplicate-key occurrences**
  for `SYNTAX-0002` to read. This is a design input to the abstraction, not a
  blocker.
- **`SYNTAX-0003` (Encoding) — home to confirm.** `generated_text` is already a
  **decoded `str`** by the time it reaches the canonical model (decoding happens
  at the adapter). So "encoding intact" is largely established *before* Syntax.
  Two coherent options for the implementation task: (a) treat encoding integrity
  as a **normalized observation** captured at the normalization seam and have
  `SYNTAX-0003` read it; or (b) re-examine whether the concern is a
  delivery/normalization fact closer to Transport. Either way it does **not**
  change this review's recommendation. No rule needs to *move layers* today; this
  is a scoping question for the rule's implementation.

No catalogued Syntax rule should move to another layer, and none should be split.

---

## 11. Engineering Review — raw text vs. normalized representation

| Dimension | Option A — rules parse `generated_text` | Option B — normalized `ParsedResponse` |
| --------- | --------------------------------------- | -------------------------------------- |
| Parses per validation run | 1 (Syntax) **+ N** (every later rule that reads a field) | **Exactly 1** (shared normalization) |
| Rule Independence (§16) | Strained — rules re-derive structure; risk of divergent parses | Upheld — rules read one normalized fact |
| One concern, one layer (§8) | Violated — parseability re-derived in Schema+ | Upheld — parse outcome owned by Syntax |
| Determinism | At risk — multiple parsers can disagree | Strong — one parse, one result |
| Consistency with platform | Diverges from the `ExecutionStatus` precedent | Matches the proven "normalize once" precedent |
| Provider compatibility | Equal | Equal (format-level normalization; no provider logic) |
| Upfront work before Syntax | Lower (no new model) | Higher (specify + build the model first) |
| Long-term rework | High — Schema layer forces the model anyway, after Syntax shipped on raw text | Low — built once, every layer benefits |

**Conclusion of the engineering review.** Option A's only advantage is lower
*immediate* effort; it incurs guaranteed rework at the Schema layer and conflicts
with two frozen principles. Option B parses once, upholds Rule Independence and
layer ownership, and matches the established normalization precedent.

---

## 12. Future Extensibility

- **More structured formats.** `ParsedResponse` is format-neutral in concept
  (today the document is JSON; the abstraction names "structured data"). A future
  format normalizes into the same representation; rules are unaffected.
- **More providers.** Covered by §8 — no provider-specific parsing exists.
- **Richer syntactic checks.** New Syntax concerns (e.g. additional ambiguity
  classes) become new `SYNTAX-00NN` rules reading additional normalized
  observations on `ParsedResponse` — additive, governed by ADR, no framework
  change.
- **Schema onward.** Every later layer consumes `ParsedResponse.structure`
  unchanged; the abstraction is the shared substrate for the rest of the
  pipeline.

---

## 13. Recommendations

1. **Adopt Option B.** Introduce a provider-independent, normalized parsed
   representation (`ParsedResponse`/`StructuredResponse`) on the canonical model
   **before** implementing any Syntax rule.
2. **Parse once, at a single shared normalization seam** (post-adapter,
   pre-pipeline). Parsing is a format concern, not per-provider logic.
3. **Design the representation to record syntactic observations** a standard
   parse loses — at minimum duplicate-key occurrences (`SYNTAX-0002`) and an
   encoding-integrity signal (`SYNTAX-0003`).
4. **Keep it observation-only** — parse, never repair (no fence-stripping, no
   coercion), consistent with the platform's "observe, never repair" stance.
5. **Confirm `SYNTAX-0003`'s home** during the model task (normalized observation
   vs. a delivery/normalization fact); do not block on it.
6. **Do not modify the frozen Transport layer, framework, validator, pipeline, or
   registry** — the change is purely an additive canonical model + a normalization
   step.

---

## 14. Architecture Decision

> **Architectural Decision**
> Syntax rules **must not** parse `generated_text` independently. The platform
> shall introduce a single, provider- and format-independent **parsed
> representation** of the response, produced **once** at a shared normalization
> seam and carried on the canonical model, which the Syntax layer validates (its
> parse outcome) and every subsequent layer reads (its structure). This upholds
> Rule Independence and one-concern-per-layer, and extends the proven
> "normalize once" precedent established by `ExecutionStatus`. The representation
> is **specified** by this review and **implemented by a dedicated future task** —
> not here.

---

## 15. Final Conclusion

The existing canonical model exposes only **raw `generated_text`**. Syntax could
*technically* parse it directly, but doing so would force **every later layer to
re-parse**, breaking Rule Independence and leaking the Syntax concern across the
pipeline. The platform already proves it parses the response — only in the
reporting layer, ad hoc, and discards the result. The correct architecture is to
**parse once** into a canonical, provider-independent representation, exactly as
execution outcomes are normalized once into `ExecutionStatus`.

> ### Recommendation: **OPTION B**
>
> **A new provider-independent canonical representation is required.** Implement
> that model (the `ParsedResponse`/`StructuredResponse` abstraction and its
> single normalization seam) **before** writing any Syntax rule.
>
> Option A (operate directly on `generated_text`) is **rejected**: it conflicts
> with Rule Independence (§16) and one-concern-per-layer (§8), diverges from the
> `ExecutionStatus` precedent, and guarantees rework at the Schema layer.

**Next milestone:** *Canonical Parsed-Representation task* — specify and implement
the provider-independent `ParsedResponse` model and its single normalization seam
(additive only; no Transport/framework/validator/pipeline/registry change). Syntax
rule implementation (`SYNTAX-0001`–`SYNTAX-0003`) begins **after** that model
lands.
