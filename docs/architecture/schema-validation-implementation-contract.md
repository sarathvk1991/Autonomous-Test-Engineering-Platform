# Schema Validation Implementation Contract

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Layer Specialization |
| Status               | Approved — Foundational — **FROZEN**                              |
| Scope                | The **Schema-layer specialization** every concrete Schema validation rule (`SCHEMA-0001` and beyond) must conform to, on top of the general Validation Rule Implementation Contract |
| Governs              | The Schema layer's permitted/forbidden inputs, permitted/prohibited behaviour, dependency boundaries, facts-vs-judgement discipline, layer relationships, determinism, and the Schema-specific engineering patterns and checklists |
| Complements          | Validation Rule Implementation Contract (general engineering structure) · Validation Rule Catalog (identity, concern, severity, blocking) — it **replaces neither** and **duplicates neither** |
| Depends on           | Validation Rule Catalog · Validation Rule Implementation Contract · AI Response Validation Architecture · Validation Canonical Models (`ParsedResponse`, `ValidationInput`, `ValidationIssue`) · Response Normalization Contract · ADR-0003 |
| Audience             | Lead Engineers · Platform Engineers · Technical Architects · QA Architects · Reviewers |
| Implementation-bound | No — valid regardless of language, framework, serialization format, algorithm, or AI provider |

> **Architectural Decision**
> This contract is a **layer specialization**, not a new engineering model. Every
> Schema rule is first and fully governed by the **Validation Rule Implementation
> Contract** (lifecycle, single concern, `ValidationInput`-only input,
> `ValidationIssue`-only output, facts-vs-exceptions, independence, immutable
> metadata, principled dependency injection). This document adds **only** what is
> *specific to the Schema layer* — chiefly *which* part of the `ValidationInput` a
> Schema rule may read, and where Schema's responsibility begins and ends relative
> to Syntax and Structural. It introduces no new rule, no new severity, no new
> ownership, and requires no ADR. Where this document and a frozen upstream document
> appear to differ, the upstream document governs and the difference is resolved
> through an ADR — never silently here.

---

## 1. Purpose

### 1.1 Why this contract exists

The **Validation Rule Implementation Contract** answers, permanently, the
*engineering structure* every validation rule of every layer must take. The
**Validation Rule Catalog** answers *which* Schema rules exist and *what* each one
validates (`SCHEMA-0001` RequiredSectionsRule, `SCHEMA-0002` FieldTypesRule,
`SCHEMA-0003` EnumerationsRule, `SCHEMA-0004` RequiredArraysRule — Catalog §9.3),
with their severity and blocking (Catalog §14, §15). What neither answers directly
is the one recurring, Schema-specific question:

> *"What makes a Schema validation rule a **Schema** rule — as opposed to a Syntax
> rule before it or a Structural rule after it?"*

Three Syntax rules are complete; the Schema layer is next. The Schema layer's
defining property is not its engineering structure (that is shared) but **what it
reads and what it may conclude**: a Schema rule judges whether the already
well-formed, normalized structure **conforms to the expected, versioned shape** —
nothing before that (well-formedness is Syntax's) and nothing after it (composition
is Structural's; meaning is Content's). This contract freezes that boundary so every
`SCHEMA-00NN` rule is implemented identically and never strays.

### 1.2 What this contract governs — and what it does not

| This contract governs | This contract does **not** govern |
| --------------------- | --------------------------------- |
| The Schema layer's **permitted and forbidden inputs** (§4, §5). | The general rule structure — lifecycle, output shape, exception philosophy, metadata, independence (Validation Rule Implementation Contract). |
| Schema's **prohibited behaviour** and **dependency boundaries** (§7, §8). | *Which* Schema rules exist, their identity, concern, **severity**, or **blocking** (Validation Rule Catalog §9.3, §14, §15). |
| The **relationship** of Schema to Normalization, Syntax, and Structural (§10). | Pipeline orchestration, profile selection, result assembly (Framework · Response Validator). |
| The Schema-specific **engineering patterns** and **checklists** (§13, §16–§18). | How structure is *created* (Response Normalization Contract) or what the `ParsedResponse` *holds* (Canonical Models). |

> **Principle**
> The Catalog governs **what a Schema rule validates**. The Validation Rule
> Implementation Contract governs **how any rule is structured**. This document
> governs **what makes that structure a *Schema* rule** — its inputs, its boundary,
> and nothing else.

---

## 2. What makes a rule a Schema rule

A rule is a Schema rule when **all** of the following hold. Each is elaborated in
the sections cited.

| # | Defining property | Section |
| - | ----------------- | ------- |
| 1 | Its single concern is **conformance of the well-formed structure to the expected, versioned shape** — presence of a schema-required section, a field's expected type, a permitted enumerated value, or the presence of a required collection. | §3 |
| 2 | Its **only functional input** is the **normalized structure** (`ValidationInput → normalization_result → parsed_response → normalized_structure`). | §4 |
| 3 | It **never** reads the Normalization Outcome, the observations, `generated_text`, provider metadata, or any other input for its decision. | §5 |
| 4 | It **assumes the structure is well-formed** (Syntax has run) and **defers** when no structure was recovered — it never re-checks well-formedness. | §10.2 |
| 5 | It validates **shape**, never **composition/nesting** (Structural) and never **content meaning/quality** (Content onward). | §7, §10.3 |
| 6 | It **reads** the structure (a normalization fact) and **produces** judgements (`ValidationIssue`); it never mutates, normalizes, or repairs. | §9 |

> **Architectural Decision — Schema is the *shape-conformance* layer.** Syntax asks
> *"is there an unambiguous structure at all?"* Schema asks *"does that structure
> match the shape we expect?"* Structural asks *"are the required containers
> composed and nested correctly?"* Content asks *"are the values meaningful?"* A
> rule that answers anything other than the shape-conformance question is not a
> Schema rule, regardless of where it is registered.

---

## 3. Ownership

Each Schema concern is owned by exactly one Schema rule, and the Schema layer as a
whole owns exactly one family of concerns: **shape conformance to the expected,
versioned schema**. The concern families are already partitioned by the Catalog
(§9.3) and must not blur:

| Concern family | Owning rule (Catalog §9.3) | The one question it answers |
| -------------- | -------------------------- | --------------------------- |
| Required sections present | `SCHEMA-0001` | Does every schema-required section exist? |
| Field types | `SCHEMA-0002` | Is each field of its expected type? |
| Enumerated values | `SCHEMA-0003` | Does each enumerated field hold a permitted value? |
| Required collections present | `SCHEMA-0004` | Does each required collection exist? |

> **Principle (aligned with ADR-0004)**
> **Existence of any schema-declared property, section, container, or collection is
> Schema; composition/hierarchy/organization is Structural; value meaning/quality is
> Content.** Per ADR-0004, **all** existence — including container and section
> presence — belongs to Schema; Structural owns no existence check. Schema owns
> presence *and* machine-readable conformance **as declared by the shape** (a
> required property/section/container/collection exists, a field's type is correct, an
> enum value is permitted). It owns nothing about how the present parts are composed,
> nested, or organized (Structural), nor about whether a present value is meaningful
> (Content).

Ownership of everything upstream and downstream is unchanged: Response
Normalization owns creation of the structure; Syntax owns well-formedness;
Structural owns composition; Content onward own meaning. A Schema rule adds no new
owned fact — it produces judgements only.

---

## 4. Permitted Inputs

A Schema rule receives the single canonical input every rule receives — the
**`ValidationInput`** (ADR-0003) — and its **only functional input** is the
**normalized structure**:

```text
   ValidationInput
      → normalization_result
          → parsed_response
              → normalized_structure     ← the Schema rule's functional input
```

| Input discipline | Statement |
| ---------------- | --------- |
| **Functional input = the normalized structure** | The rule's decision reads only `parsed_response.normalized_structure` — the format-neutral objects, arrays, scalars, and identifiers Response Normalization recovered once. |
| **Read-only** | The structure is observed, never modified (Preserve Original Response; Canonical Models invariants). |
| **The same shared instance** | Every layer from Schema onward reads the *same* `ParsedResponse`; the rule never copies, re-derives, or re-parses it. |
| **Correlation is provenance, not a functional input** | The issue's `correlation_id` is derived from execution identity exactly as for every other rule (Validation Rule Implementation Contract §8; Development Guide §8); it is not a Schema decision input. |

> **Architectural Decision — Schema reads the normalized structure, and only that.**
> This is the single line that most sharply separates Schema from Syntax. Syntax
> reads the **Normalization Outcome** and the **Normalization Observations**; Schema
> — and every later layer — reads the **normalized structure**. A Schema rule that
> reached for the outcome or the observations would be doing Syntax's job.

---

## 5. Forbidden Inputs

A Schema rule **MUST NEVER** read, for its decision:

| Forbidden input | Why — and who owns it |
| --------------- | --------------------- |
| **Normalization Outcome** (`NORMALIZED` / `MALFORMED`) | Well-formedness is **Syntax**'s concern (`SYNTAX-0001`). Schema assumes it (§10.2). |
| **Normalization Observations** | The duplicate-identifier / encoding facts are **Syntax**'s functional inputs (`SYNTAX-0002`, `SYNTAX-0003`); they are never a Schema input. |
| **`generated_text`** | Raw text is the normalizer's input, not validation's; reading it would re-derive structure and break Rule Independence. |
| **Provider / model metadata** | Validation is provider-independent; the verdict is a property of the structure, never its origin. |
| **`AnalysisResult` / `LLMResponse` (as a decision input)** | Schema judges the normalized structure, not the transport carrier. (`execution_id` may be read as issue *provenance* only — never as a decision input.) |
| **`ParsedResponse.source_reference` / `metadata` (as a decision input)** | These are provenance/free-form fields, not the shape under validation. |
| **Another rule's findings** | Rules are independent (Validation Rule Implementation Contract §7). |

> **Principle**
> Schema's forbidden inputs are the definition of its restraint. The moment a
> "Schema" rule needs the outcome, an observation, or the raw text, it has either
> strayed into Syntax or is trying to detect something normalization already
> settled. Its evidence is the structure, and only the structure.

---

## 6. Permitted Outputs

Unchanged from the general contract, stated here for completeness: a Schema rule
returns **exactly a list of `ValidationIssue`** — empty when the shape conforms, or
one issue per observed occurrence of its single concern (a rule may emit several
issues if its one concern occurs several times; e.g. two fields of the wrong type →
two issues). Each issue carries the **severity and blocking the Catalog assigns**
(Catalog §14, §15) — for example, a missing required section is `ERROR` (Catalog
§14). This contract assigns **no** severity or blocking; it defers entirely to the
Catalog.

> **Note — Schema is a foundational, progression-stopping *category* (AI Response
> Validation §5), yet its findings are typically `ERROR` → `FAILED` (Catalog §14),
> not `CRITICAL` → `BLOCKED`.** There is no contradiction: `FAILED` means the output
> is untrustworthy and must not be consumed (a downstream stop), while `BLOCKED` is
> reserved for the unsafe-to-process failures of Transport/Syntax. Severity remains
> the Catalog's to assign per rule (§14); a Schema rule never invents it.

---

## 7. Prohibited Behaviour

A Schema rule **MUST NEVER**:

| The rule never… | Because that belongs to |
| ---------------- | ----------------------- |
| **Parse, normalize, or recover structure** | Response Normalization (structure is recovered once, before validation). |
| **Repair, complete, or coerce** the structure or its values | nobody — repair is forbidden platform-wide. |
| **Mutate** the `ParsedResponse` or the normalized structure | nobody — it is an immutable Shared Platform Artifact. |
| **Re-check well-formedness** (parseability, duplicate identifiers, encoding) | **Syntax** (`SYNTAX-0001…0003`). |
| **Validate container composition or parent-child nesting** | **Structural** (`STRUCTURE-00NN`). |
| **Judge the meaning, quality, emptiness, or range of a conformant value** | **Content** (`CONTENT-00NN`) and later layers. |
| **Aggregate, coordinate, or invoke another rule** | the pipeline / framework. |

> **Architectural Decision — the prohibitions draw Schema's two edges.** The
> *upper* edge is Syntax: Schema never re-asks "is it well-formed?" The *lower*
> edge is Structural and Content: Schema never asks "is it composed correctly?" or
> "is the value good?" A Schema rule that crosses either edge duplicates another
> layer's concern and is non-conforming.

---

## 8. Dependency Boundaries

- **On Response Normalization:** a Schema rule depends only on the *information* in
  the `ParsedResponse` (the normalized structure). It never depends on how
  normalization produced it, on any normalization stage, or on the
  `NormalizationResult`'s observations.
- **On the expected shape:** the "expected, versioned shape" a Schema rule checks
  against is **governed knowledge** — defined by the Validation Rule Catalog (the
  rule's concern), the AI Reasoning Contract, and the Prompt Framework (what the
  response is required to contain). A rule may **inject** the expected-shape
  definition as a collaborator **only where it genuinely varies** (e.g. a
  versioned or profile-specific schema), per the general contract's
  dependency-injection philosophy (Validation Rule Implementation Contract §9); a
  fixed, governed shape needs no injected collaborator. A **formal, published
  schema definition** is a reserved future capability (AI Response Validation §14)
  that, when it arrives, is injected the same way and changes no rule's identity or
  verdict model.
- **On other rules:** none. Schema rules are independent (Validation Rule
  Implementation Contract §7); the only ordering they may rely on is the pipeline's
  layer order (Transport → Syntax → Schema → …).

> **Architectural Decision — inject the shape only if the shape varies.** Because
> the expected shape is the one thing that can legitimately differ across schema
> versions or profiles, it is the natural — and only — candidate for injection in a
> Schema rule. Everything else about a Schema rule is fixed. This is the direct
> Schema application of the general contract's "inject variation, not ceremony."

---

## 9. Facts vs Judgement

Schema sits entirely on the **judgement** side of the frozen
Normalization–Validation boundary (Response Normalization Contract §10).

- The **normalized structure** is a **fact** produced by Response Normalization.
- A Schema rule **reads** that fact and **decides** whether it conforms to the
  expected shape; a non-conformance is a **judgement** expressed as a
  `ValidationIssue`.
- A Schema rule **produces no facts**, records no observations, and mutates
  nothing. It never turns a fact into another fact; it turns a fact into a verdict
  input.

> **Principle**
> Normalization records what the structure *is*; Schema judges whether that
> structure is *what the platform expected*. The structure is never re-derived and
> never altered — Schema only reads it and reasons about its shape.

---

## 10. Relationship to Other Layers

```text
   Response Normalization      creates the ParsedResponse (normalized structure) ONCE
            │  (fact: structure + outcome + observations)
            ▼
   Syntax                      judges well-formedness: outcome NORMALIZED?  no duplicate
            │                  identifiers?  encoding intact?   (reads outcome + observations)
            ▼
   Schema                      judges conformance & EXISTENCE: required sections/containers/
            │                  collections present + types + enums   (reads the structure)  ◄── THIS LAYER
            ▼
   Structural                  judges composition/hierarchy/organization: the parts that
                               EXIST are nested/related/organized correctly (ADR-0004)
```

### 10.1 What Schema assumes

- That a **usable, non-empty response** was delivered (Transport guaranteed it).
- That the response is **well-formed, unambiguous structured data** — the
  Normalization Outcome is `NORMALIZED`, no field identifier is duplicated, and the
  character encoding is intact (Syntax guaranteed it).
- That a **normalized structure exists** to read when the response is well-formed.

### 10.2 What Schema never assumes — and how it defers

- Schema **never assumes** it must re-verify well-formedness. If the response was
  **not** well-formed, no normalized structure was recovered
  (`normalized_structure` is absent). Because well-formedness is **Syntax's**
  concern, a Schema rule confronted with an absent structure **defers** — it
  returns no findings — rather than reporting a shape defect or raising. It never
  re-reports what Syntax owns (defer-don't-duplicate, mirroring the Transport rules'
  deferral when the response object is absent).
- Schema **never assumes** the containers are correctly composed or nested (that is
  Structural), nor that conformant values are meaningful (that is Content).

> **Architectural Decision — Schema defers on an absent structure; it never
> re-judges well-formedness.** In the frozen pipeline a not-well-formed response is
> already a Syntax finding (and, being foundational, halts progression). A Schema
> rule therefore treats "no structure to inspect" as "not my concern" and returns
> an empty finding set — never a second, misattributed report of the same problem.

### 10.3 What Schema validates — and never validates

| Schema **validates** | Schema **never validates** |
| -------------------- | -------------------------- |
| Presence of a **schema-required section/field** (`SCHEMA-0001`). | Whether the response is **well-formed** (Syntax). |
| A field's **expected type** (`SCHEMA-0002`). | Whether the **containers are composed / nested** correctly (Structural). |
| A **permitted enumerated value** (`SCHEMA-0003`). | Whether a present value is **empty, duplicated, in range, or meaningful** (Content). |
| Presence of a **required collection** (`SCHEMA-0004`). | Whether conclusions are **grounded, traceable, coherent, or policy-compliant** (Evidence → Business Rule). |

### 10.4 Where Schema's responsibility begins and ends

- **Begins** exactly where Syntax ends: the structure is well-formed and
  unambiguous; the question is no longer *"is there a usable structure?"* but *"does
  the structure match the expected shape?"*
- **Ends** exactly where Structural begins: once every schema-required field exists
  with the right type and permitted value and every required collection is present,
  the question shifts to *"are the containers composed and nested correctly?"* —
  which Schema never answers.

---

## 11. Lifecycle

A Schema rule follows the **exact lifecycle** of the general contract (construct
once → receive the immutable `ValidationInput` → produce findings → return →
remain reusable with no execution state). No Schema-specific lifecycle deviation
exists. The only Schema-specific note is the §10.2 **deferral**: a well-formed
absence of the shape's concern yields findings; an *absent structure* yields an
empty list (deferral), not a raise.

---

## 12. Determinism

A Schema rule is deterministic in the general sense (same `ValidationInput` ⇒ same
findings). The Schema-specific determinism note: the finding set is a deterministic
function of the **normalized structure** (and, where injected, the fixed expected
shape). Because the structure is recovered once and shared read-only, two Schema
rules — or the same rule run twice — always reach the same conclusion. A Schema rule
must never let iteration order over a mapping, a clock, or any external state affect
its findings.

---

## 13. Engineering Patterns (frozen, Schema-specific)

These are the Schema-layer specializations of the frozen general patterns. They
introduce nothing new structurally; they fix the Schema application.

| # | Frozen Schema pattern | What it means |
| - | --------------------- | ------------- |
| 1 | **Structure-only functional input** | A Schema rule reads only `parsed_response.normalized_structure` for its decision — never the outcome, observations, or raw text. |
| 2 | **Assume well-formed; defer on absent structure** | It assumes Syntax passed; when no structure was recovered it returns `[]` (deferral), never a shape finding and never a raise. |
| 3 | **Shape, not composition, not content** | It judges presence/type/enum/collection conformance only — never nesting/relationships (Structural) or value meaning (Content). |
| 4 | **Governed expected shape; inject only if it varies** | The expected shape is governed knowledge; inject a shape definition only where it legitimately varies (versioned/profile/formal schema). |
| 5 | **Read the fact, produce a judgement** | It reads the immutable structure fact and emits `ValidationIssue` judgements; it mutates, normalizes, and repairs nothing. |
| 6 | **Catalog-governed severity/blocking** | Each issue carries the Catalog's severity and blocking (e.g. missing section → `ERROR`); the rule invents neither. |

---

## 14. Examples (illustrative; not new architecture)

> **Worked example — a Schema finding vs. its neighbours.**
> Consider a normalized structure whose `confidence` field holds `"very high"` while
> the schema permits only `{LOW, MEDIUM, HIGH}`.
> - **Schema (`SCHEMA-0003`)** raises a finding: the enumerated value is not
>   permitted — a *shape* defect.
> - **Syntax** says nothing: the response *was* well-formed; the outcome is
>   `NORMALIZED`.
> - **Structural** says nothing: whether the (existing) `requirements` container is
>   correctly nested/organized is a different concern (its *presence* is Schema's,
>   ADR-0004).
> - **Content** says nothing: whether a *valid* confidence is *consistent with the
>   evidence* is a Reasoning concern.
> Only Schema owns "is this value within its permitted set?".

> **Worked example — deferral on an absent structure.**
> A response that did not normalize (`MALFORMED`) has no `normalized_structure`.
> `SYNTAX-0001` already raised the (blocking) well-formedness finding. Every Schema
> rule, finding no structure to inspect, returns `[]` — it does not re-report the
> malformed response as a "missing required section". The single problem is reported
> once, by its one owner.

---

## 15. Future Proofing — implementing SCHEMA-0001 and beyond

Every future Schema rule is added **without changing architecture** by
instantiating this contract on top of the general one:

1. **Confirm the rule is catalogued** — `SCHEMA-00NN` exists in the Rule Catalog
   with an approved identity, concern, layer, severity, and blocking (Catalog §22).
2. **Realise the general structure** — construct-once, immutable metadata,
   `ValidationInput`-only input, `ValidationIssue`-only output, facts-not-exceptions,
   independence (Validation Rule Implementation Contract).
3. **Apply the Schema specialization** — read only the normalized structure (§4),
   read none of the forbidden inputs (§5), defer on an absent structure (§10.2),
   judge shape only (§7), inject the expected shape only if it varies (§8).
4. **Take severity and blocking from the Catalog** (§6).
5. **Add it to the Schema layer's registration** and its tests, exactly as the
   Syntax layer did — no framework, validator, canonical-model, or normalization
   change is required.

> **Architectural Decision — the Schema layer grows additively.** New shape concerns
> become new `SCHEMA-00NN` rules (or, in future, richer shape mechanisms injected
> into existing rules), never enlargements of an existing rule and never new inputs.
> Adopting a **formal published schema** is a reserved capability (AI Response
> Validation §14): it is injected as a varying shape mechanism (§8) under the same
> verdict model, changing no identity and requiring no ADR unless it changes a
> frozen contract.

---

## 16. Implementation Checklist

Every Schema rule must satisfy the general contract's checklist **and** all of:

- [ ] Its **single concern** is a shape-conformance concern catalogued under the
      Schema layer (§2, §3).
- [ ] Its **functional input** is `parsed_response.normalized_structure` and nothing
      else (§4).
- [ ] It reads **none** of the forbidden inputs — outcome, observations,
      `generated_text`, provider, or another rule's findings (§5).
- [ ] It **defers** (returns `[]`) when no normalized structure was recovered; it
      never re-reports well-formedness and never raises for an absent structure
      (§10.2).
- [ ] It judges **shape only** — never composition/nesting (Structural) or value
      meaning (Content) (§7, §10.3).
- [ ] It **mutates, normalizes, and repairs nothing** (§7, §9).
- [ ] It injects an expected-shape collaborator **only where the shape varies**
      (§8).
- [ ] Each issue carries the **Catalog's** severity and blocking (§6).
- [ ] It is **deterministic** over the normalized structure (§12).

## 17. Conformance Checklist (for reviewers)

A reviewer certifies a Schema rule only if the general conformance checklist passes
**and**:

- [ ] **Schema concern** — one catalogued shape concern, and only one (§3).
- [ ] **Structure-only input** — reads the normalized structure; reads no forbidden
      input (§4, §5).
- [ ] **Deferral** — an absent structure yields `[]`, never a shape finding, never a
      raise (§10.2).
- [ ] **Two-edged boundary** — never re-checks well-formedness (Syntax) and never
      checks composition/nesting (Structural) or value meaning (Content) (§7, §10).
- [ ] **Judgement, not fact** — reads the immutable structure; produces
      `ValidationIssue`s only; mutates nothing (§9).
- [ ] **Principled shape injection** — an expected-shape collaborator only where the
      shape varies (§8).
- [ ] **Catalog-governed severity/blocking** — never invented (§6).
- [ ] Any architectural change to the above is made through an approved **ADR**
      (§19).

---

## 18. Relationship to the Existing Contracts (no duplication)

| Question | Answered by |
| -------- | ----------- |
| *Which* Schema rules exist; their identity, concern, severity, blocking? | **Validation Rule Catalog** (§9.3, §14, §15). |
| *How* is any rule structured (lifecycle, output, exceptions, metadata, independence, DI)? | **Validation Rule Implementation Contract**. |
| *What makes a rule a Schema rule* (its inputs, boundary, layer relationships)? | **This document.** |
| *How is a rule written in Python* (files, typing, tests, tooling)? | **Validation Rule Development Guide.** |

> **Principle**
> This contract is intentionally thin. Everything a Schema rule shares with every
> other rule lives in the general contract; everything about *which* Schema rules
> exist lives in the Catalog. What remains here is only the Schema layer's
> input discipline and boundary — the irreducible answer to "what makes a Schema
> rule a Schema rule."

---

## 19. Architecture Freeze

> **Architectural Decision — Architecture Freeze**
> With this document, the following become **frozen** for every Schema-layer rule
> implementation:
>
> - **The Schema functional input** — the normalized structure only (§4).
> - **The Schema forbidden inputs** — outcome, observations, raw text, provider,
>   other rules' findings (§5).
> - **The Schema prohibitions** — no parse/normalize/recover, no repair, no mutation,
>   no re-checking well-formedness, no composition/nesting, no content meaning (§7).
> - **The assume-and-defer rule** — assume well-formed; defer on an absent structure
>   (§10.2).
> - **The layer boundaries** — Normalization → Syntax → Schema → Structural, with
>   Schema's responsibility beginning where Syntax ends and ending where Structural
>   begins (§10).
> - **The Schema engineering patterns** (§13).
>
> **Only implementation may evolve** beneath these contracts. **The architecture may
> evolve only through an approved Architecture Decision Record (ADR).** This document
> changes **no** frozen upstream contract, **no** rule identity, **no** severity or
> blocking, **no** canonical model, and requires **no** ADR; it specialises the
> frozen general contract for the Schema layer.

> **Definition of Done**
> This document is the governing Schema-layer specialization for the platform. It
> governs the Schema layer's permitted and forbidden inputs, prohibited behaviour,
> dependency boundaries, facts-vs-judgement discipline, layer relationships,
> determinism, and the Schema-specific engineering patterns and checklists. It
> governs **only** what makes a rule a *Schema* rule — never the general rule
> structure (Validation Rule Implementation Contract), *which* rules exist (Rule
> Catalog), or *how* a rule is written in code (Development Guide). It is
> implementation-independent and remains valid even if the platform is reimplemented
> on an entirely different technology stack, serialization format, or AI provider.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Schema validation rule** | A validation rule whose single concern is conformance of the well-formed normalized structure to the expected, versioned shape (§2, §3). |
| **Normalized structure** | The format-neutral structural view (`parsed_response.normalized_structure`) recovered once by Response Normalization; a Schema rule's only functional input (§4). |
| **Expected (versioned) shape** | The governed definition of the sections, types, enumerated value-domains, and required collections the response must exhibit — from the Catalog, the AI Reasoning Contract, and the Prompt Framework; optionally an injected/formal schema in future (§8). |
| **Shape conformance** | Whether the structure exhibits the expected sections/types/enums/collections — Schema's exclusive concern (§10.3). |
| **Deferral (Schema)** | Returning `[]` when no normalized structure was recovered, because well-formedness is Syntax's concern (§10.2). |
| **Composition / hierarchy / organization** | The nesting, parent-child relationships, and arrangement of the parts that already **exist** — **Structural**'s concern, never Schema's (§7, §10.3; ADR-0004). Existence of those parts is **Schema**'s. |

## Appendix B — Consistency Verification

Verified consistent with every frozen artifact it touches. The Schema ↔ Structural
ownership boundary is governed by **ADR-0004** (existence → Schema;
composition/hierarchy/organization → Structural); this contract is aligned to it.

| Document | Consistency check | Result |
| -------- | ----------------- | ------ |
| **Validation Rule Catalog** | Schema layer purpose (§8.3), rules (§9.3), severity (§14 — `SCHEMA-0001` = `ERROR`), blocking (§15). The Schema/Structural existence boundary is reassigned by **ADR-0004** (existence → Schema; the Structural existence rules `STRUCTURE-0001…0004` are Deprecated); this contract reflects that reassignment. | ✅ Consistent — aligned with ADR-0004; no severity/blocking changed. |
| **Validation Rule Implementation Contract** | General lifecycle/input/output/exception/metadata/independence/DI inherited unchanged; only the Schema specialization added. | ✅ Consistent — no general rule changed; no duplication. |
| **AI Response Validation Architecture** | Progressive layering (§4), Schema category progression-stopping (§5), severity model (§6), formal-schema as future capability (§14) honoured. | ✅ Consistent — `ERROR → FAILED` vs `CRITICAL → BLOCKED` reconciled (§6 note). |
| **Validation Canonical Models / `ParsedResponse`** | Schema reads `normalized_structure` read-only; never mutates; observations remain the `NormalizationResult`'s. | ✅ Consistent — no canonical model changed. |
| **Response Normalization Contract** | Facts (structure) produced by normalization; judgements by Schema; §10 boundary preserved. | ✅ Consistent — no ownership changed. |
| **ADR-0003 / `ValidationInput`** | Schema consumes the `ValidationInput`; reads the structure via `normalization_result.parsed_response`. | ✅ Consistent — no input contract changed. |

> If any future change to a frozen document contradicts this contract, that is an
> architecture change: **stop and resolve it through an ADR**, never silently in this
> document.
