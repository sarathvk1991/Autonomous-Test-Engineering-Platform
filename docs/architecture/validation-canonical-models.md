# Validation Canonical Models

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Canonical Information Model   |
| Status               | Approved — foundational                                           |
| Scope                | The implementation-independent information model of validation      |
| Governs              | The conceptual models every Response Validator implementation must realise |
| Depends on           | AI Response Validation Architecture · AI Reasoning Contract · Requirement Analysis Service |
| Audience             | Solution Architects · Technical Architects · Lead Engineers · Data Architects |
| Implementation-bound | No — valid regardless of language, framework, persistence, serialization, or model provider |

> **Architectural Decision**
> The **AI Response Validation Architecture** defines validation *philosophy* —
> why, whether, and how trustworthiness is judged. This document defines
> validation *information* — the canonical models that carry the judgement. They
> are two halves of one governing whole: a Response Validator implementation must
> conform to **both**. Neither supersedes the other.

---

## 1. Purpose

### 1.1 Why canonical models exist

The validation architecture establishes *what validation means*. But meaning
must be carried by a stable shape: every validation run produces findings, a
verdict, summaries, and metrics that the rest of the platform — and human
reviewers — must read, store, correlate, and audit. If each implementation
invented its own shape for that information:

- Downstream consumers would couple to implementation accidents instead of a
  stable model.
- The same finding would be described differently by different validators,
  defeating determinism and audit.
- Reimplementing the validator on another technology would silently change what
  a "validation result" *is*.

The canonical models exist to **fix the meaning, ownership, relationships,
lifecycle, and invariants of validation information** — once, independent of any
technology. They are the bridge between the architecture and any future
implementation.

> **Principle**
> These models define the **information model**, not the implementation. They
> describe *what the information means and how it relates*, never *how it is
> stored, serialised, or coded*. They are enterprise domain models for the
> validation subsystem: meaning over mechanism.

### 1.2 What this document is **not**

| This document is NOT | Because |
| -------------------- | ------- |
| A schema definition | It defines conceptual attributes and their meaning, not a serialisation contract. |
| An implementation specification | No data structures, storage, inheritance, or interfaces are described. |
| A redefinition of philosophy | Verdict semantics, severity, and boundary live in the AI Response Validation Architecture. |
| A provider or technology document | No model, vendor, language, framework, or format is referenced. |

> **Architectural Decision**
> The architecture defines validation **philosophy**. The canonical models define
> validation **information**. **Implementations must conform to both.** This split
> lets the information model stay stable while implementations evolve, and lets
> philosophy stay stable while the information model is extended (§13).

---

## 2. Canonical Models Overview

Validation is described by **six canonical models**. One — the `ParsedResponse`
— is the normalized **representation validation consumes**; the other five form
one cohesive **result aggregate** rooted at the `ValidationResult`.

| Model | Role | One-line meaning |
| ----- | ---- | ---------------- |
| **ParsedResponse** | Consumed representation (Shared Platform Artifact) | The single, immutable, provider- and format-independent normalized structure of the response; the substrate every validation layer — and every other platform consumer — reads (§8). |
| **ValidationIssue** | Atomic finding | One objective, immutable observation about the response. |
| **ValidationSummary** | Derived overview | A roll-up of all issues; never authored, only derived. |
| **ValidationStatistics** | Operational metrics | Observational facts about the run; never affect the verdict. |
| **ValidationResult** | Canonical output | The single, immutable output of validation; owns everything. |
| **ValidationConfiguration** | Behaviour input | Declares which layers, thresholds, and observability govern a run. |

> **Architectural Decision**
> **`ParsedResponse` is a Core Canonical Model and a Shared Platform Artifact, not
> a Syntax-specific or Validation-specific one.** It is a peer of `LLMResponse`,
> `AnalysisResult`, and the validation result models, and is **consumed across the
> platform** — within validation the Syntax layer reads its Normalization Outcome
> and every later layer reads its normalized structure, and beyond validation
> Requirement Normalization, Feature Generation, Test Generation, AI Evaluation,
> Analytics, and future components read the same instance. Validation is merely its
> **first** consumer, not its owner. It is created once, before any consumer runs,
> by the **Response Normalization Layer** (Response Normalization Contract); the
> models here govern *what it holds*, never *how it is created*.

### 2.1 Relationship diagram

```text
        ┌───────────────────────────┐    ┌───────────────────────────┐
        │  ValidationConfiguration  │    │      ParsedResponse        │  consumed
        │  influences how a run runs │    │  the normalized structure  │  representation
        └─────────────┬─────────────┘    │  every layer reads         │  (created once,
                      │ governs           └─────────────┬─────────────┘   before the run)
                      │ (input)                         │ read by every layer (input)
                      ▼                                 ▼
        ┌───────────────────────────────────────────────┐
        │              ValidationResult                  │  the canonical output
        │                                                │
        │   contains ► ValidationSummary  (derived)      │
        │   contains ► ValidationStatistics (observed)   │
        │   contains ► ValidationIssue collection        │
        │   contains ► Original Response (preserved)     │
        │   contains ► Final Verdict                     │
        └───────────────────────────────────────────────┘
                      ▲                       ▲
                      │ summarises            │ counts / rolls up
        ┌─────────────┴───────────┐           │
        │     ValidationIssue *    │───────────┘
        └──────────────────────────┘
```

| Relationship | Meaning |
| ------------ | ------- |
| **ParsedResponse → Run** | The normalized representation is an *input* every validation layer reads; it is created once before the run and is not a finding the run produces. |
| **Configuration → Result** | Configuration is an *input* that shapes the run; it is referenced by the result, not owned as a finding. |
| **Result contains Issues** | The result is the owner of every issue produced during the run. |
| **Result contains Summary** | The summary is a derived roll-up the result carries; it cannot exist on its own. |
| **Result contains Statistics** | The statistics are observational metrics the result carries about the run. |
| **Summary summarises Issues** | The summary's every number is computed *from* the issue collection. |

---

## 3. ValidationIssue

The **ValidationIssue** is the atomic unit of validation — one precise,
explainable finding. It is the conceptual realisation of the Validation Issue
Model in the AI Response Validation Architecture (§7 there).

**Purpose.** Record exactly one objective observation about the response, with
everything needed to understand, locate, act on, and audit it.

**Lifecycle.** A ValidationIssue is *created* by a validation layer at the moment
a rule observes a condition, and is *never altered* thereafter. It is born
complete or not at all.

**Invariants.**
- **Immutable after creation** — no attribute changes once the issue exists.
- **Severity is fixed at creation** — an issue never changes severity later.
- **One observation** — an issue describes a single condition, not a cluster.

**Relationships.** Every ValidationIssue is owned by exactly one
ValidationResult and is counted by exactly one ValidationSummary.

### 3.1 Conceptual attributes

| Attribute | Meaning |
| --------- | ------- |
| **Issue Identifier** | A stable handle that uniquely references this finding. |
| **Category** | The validation concern that raised it (transport, syntax, schema, structure, content, evidence, traceability, reasoning, business rule). |
| **Severity** | The degree of threat to trustworthiness: INFO, WARNING, ERROR, or CRITICAL. Fixed at creation. |
| **Location** | Where in the response the condition occurs. |
| **Message** | A human-readable statement of what was observed and why it matters. |
| **Evidence** | The observed value or condition that substantiates the finding. |
| **Recommendation** | What would resolve the finding. |
| **Blocking Indicator** | Whether this issue, alone, prevents downstream consumption. |
| **Correlation Identifier** | The trace key linking the issue to its originating analysis and run. |
| **Validation Layer** | The layer that produced the issue. |
| **Timestamp** | When the observation was made. |

> **Principle**
> A ValidationIssue represents **one objective observation** and is **immutable**.
> It never changes severity, never mutates, and never merges with another. Because
> findings are immutable observations, the same response always yields the same
> issues — the foundation of deterministic, auditable validation.

> **Example**
> Identifier `VAL-0048`; Category *Evidence*; Severity *ERROR* (fixed); Location
> `risks[2].evidence`; Message "Risk presented without supporting evidence";
> Evidence "evidence list is empty"; Recommendation "Attach at least one evidence
> reference"; Blocking Indicator *true*; Correlation `EX-7741`; Layer *Evidence*;
> Timestamp recorded at observation. Nothing about this issue may change later.

---

## 4. ValidationSummary

**Purpose.** Provide an at-a-glance roll-up of every finding so consumers and
reviewers can grasp a run's outcome without reading each issue. It is a lens over
the issues, **not** a replacement for them.

### 4.1 Conceptual attributes

| Attribute | Meaning |
| --------- | ------- |
| **Total Issues** | The count of all issues in the run. |
| **Severity Counts** | The number of issues per severity (INFO, WARNING, ERROR, CRITICAL). |
| **Category Counts** | The number of issues per validation category. |
| **Blocking Issues** | The count of issues whose Blocking Indicator is set. |
| **Overall Health** | A derived qualitative read of the run, consistent with the verdict. |

> **Architectural Decision**
> The ValidationSummary is **derived, never authored**. Every number is computed
> from the ValidationIssue collection; nothing in it is entered or edited by hand.
> If the summary and the issues ever disagreed, the issues are authoritative and
> the summary is wrong. This keeps the summary a faithful, recomputable projection
> of the findings.

---

## 5. ValidationStatistics

**Purpose.** Capture the operational facts of a validation run — how long it
took, how much work it did — so the gate itself can be measured and trended.
These are observability signals, aligned with the AI Response Validation
Architecture's observability model.

### 5.1 Conceptual attributes

| Attribute | Meaning |
| --------- | ------- |
| **Validation Duration** | How long the run took. |
| **Rules Executed** | How many rules ran. |
| **Rules Passed** | How many rules observed no issue. |
| **Rules Failed** | How many rules raised at least one issue. |
| **Execution Timestamp** | When the run occurred. |
| **Validator Version** | The implementation version that ran. |
| **Validation Contract Version** | The version of the validation *semantics* in force. |
| **Schema Version** | The schema version validated against. |
| **Execution Correlation** | The identifier stitching this run to its originating analysis and downstream. |

> **Principle**
> Statistics are **operational and observational only**. They describe the run;
> they **never affect the verdict**. A slow run, a high rule count, or any metric
> value can never make output more or less trustworthy. Severity and the verdict
> are decided exclusively by the issues (§3), never by statistics.

---

## 6. ValidationResult

The **ValidationResult** is the canonical output of the validation subsystem —
the one artifact every downstream consumer receives. It is the conceptual
realisation of the Validation Result Model in the AI Response Validation
Architecture (§8 there).

**Purpose.** Carry the complete, final outcome of a validation run: the verdict,
every finding, the derived summary, the operational statistics, the governing
configuration reference, and the unaltered original response.

**Relationships.** The ValidationResult is the **aggregate root**: it owns the
issue collection, contains the summary and statistics, references the
configuration that governed the run, and preserves the original response.

**Lifecycle.** A ValidationResult is *assembled once*, at the end of a run, from
the issues collected and the statistics observed, and is *immutable* thereafter.

### 6.1 Conceptual contents

| Content | Meaning |
| ------- | ------- |
| **Original Response** | The exact, unaltered AI output that was validated. |
| **Validation Issues** | The complete collection of findings the result owns. |
| **ValidationSummary** | The derived roll-up over those issues. |
| **ValidationStatistics** | The observational metrics of the run. |
| **ValidationConfiguration reference** | A reference to the configuration that governed the run. |
| **Final Verdict** | One of PASSED, PASSED_WITH_WARNINGS, FAILED, or BLOCKED. |

> **Architectural Decision**
> The ValidationResult is **immutable**, **preserves the original response
> unchanged**, and is the **sole output** of the validation layer. No downstream
> component receives validation information by any other path, and none may alter
> the result. This single, immutable output is what makes validation auditable and
> reproducible.

---

## 7. ValidationConfiguration

**Purpose.** Declare the *behaviour* of a validation run — which layers are
active, what observability is captured, and which contract version governs. It
shapes *how thoroughly* validation runs; it never decides *what is trustworthy*.

### 7.1 Conceptual properties

| Property | Meaning |
| -------- | ------- |
| **Validation Contract Version** | The version of validation semantics the run must honour. |
| **Enabled Validation Layers** | Which validation layers participate in the run. |
| **Severity Thresholds** | Operational thresholds for observability and reporting of severities. |
| **Observability Level** | How much operational detail the run captures. |
| **Future Extension Points** | Reserved hooks for forthcoming configuration without breaking the model. |

> **Principle**
> Configuration **affects execution, never philosophy**. It is not a place for
> business rules, correctness criteria, or verdict logic. It may turn a layer on
> or off or tune observability; it can never redefine what a severity means, what
> the boundary is, or how a verdict is reached. Those belong to the architecture
> and the Validation Contract Version, not to a run's configuration.

> **Architectural Decision**
> ValidationConfiguration is an **input that influences a run**, not a finding the
> run produces. The ValidationResult *references* the configuration for
> traceability but does not let it alter any verdict. Severity thresholds adjust
> what is *surfaced*, never whether output is *trustworthy*.

---

## 8. ParsedResponse

The **ParsedResponse** is the canonical **structural representation of an AI
response** — the single, normalized view of the response's structure. It is a
**Shared Platform Artifact**: validation is its **first** consumer, not its owner.
The Syntax layer reads its **Normalization Outcome**, every later validation layer
reads its **normalized structure**, and every other platform consumer (Requirement
Normalization, Feature Generation, Test Generation, AI Evaluation, Analytics, and
future components) reads the **same instance**.

**Purpose.** Carry the one normalized structure of the response — together with
the Normalization Outcome and the Normalization Observations a consumer needs — so
that **consumers read structure; they never recover it.**

**Creation.** A ParsedResponse is *created once*, before any consumer runs, by the
**Response Normalization Layer** (governed by the Response Normalization
Contract). These canonical models govern *what it holds*; the Response
Normalization Contract governs *how it is created, owned, shared, and versioned*.
No consumer creates, recovers, or re-derives it.

**Lifecycle.** Created exactly once from the response's normalized text,
**immutable** thereafter, **shared** across the platform, **never copied, never
mutated, never recreated** (Response Normalization Contract §6).

**Invariants.**
- **Immutable after creation** — no attribute changes once it exists.
- **Shared, single instance** — every consumer receives the identical instance;
  none reparses `generated_text`.
- **Provider-independent** — it holds no provider payloads or provider strings.
- **Format-independent** — it represents normalized structure, **not** a specific
  serialization format.
- **Observation-only** — it records the structure and facts that are present; it
  never repairs, completes, or judges them.

**Relationships.** A ParsedResponse is a normalized derivative of the response's
`generated_text`; it is reached by consumers via the analysis result under
validation; it is the structural counterpart of the execution-outcome
normalization already established for the Transport layer. Its representation is
versioned by the **ParsedResponse Version**; the meaning of normalization is
versioned by the **Normalization Contract Version** (Response Normalization
Contract §12).

### 8.1 Conceptual attributes

| Attribute | Meaning |
| --------- | ------- |
| **Normalization Outcome** | A normalized, provider-independent **fact**: whether the response was `NORMALIZED` (well-formed structure recovered) or `MALFORMED` (no well-formed structure). The fact the Syntax layer judges. |
| **Normalized Structure** | When `NORMALIZED`: the format-neutral structural view (objects, arrays, scalars, identifiers) that Schema, Structural, Content, Evidence, Traceability, Reasoning, and Business Rule layers — and every other platform consumer — read. |
| **Normalization Observations** | Recorded, **un-judged facts** a structural view alone would lose — e.g. duplicate field identifiers within an object, and character-encoding observations — captured for a consumer to interpret. They carry no severity and no verdict, and are **never** a `ValidationIssue` (Response Normalization Contract §8, §10). |
| **Source Reference** | A link back to the response's preserved original `generated_text`, so the normalized view never replaces the original. |

> **Architectural Decision**
> **`ParsedResponse` represents normalized structure, not a specific serialization
> format.** The structure a response expresses — its objects, arrays, scalars, and
> identifiers — is independent of the format used to express it. A future
> structured format normalizes into the *same* `ParsedResponse`, and no consumer
> changes. Binding the model to one format would make every consumer format-aware
> and defeat the purpose of a canonical representation.

> **Architectural Decision**
> **`ParsedResponse` is a Shared Platform Artifact, not a Validation artifact.**
> It is produced once by the Response Normalization Layer and read, unchanged, by
> the whole platform. Validation's primacy in time confers no ownership; no
> consumer may shape it to its own needs. It is governed by these models (its
> shape) and the Response Normalization Contract (its creation, ownership, sharing,
> and versioning).

> **Principle**
> The ParsedResponse is **created once and read many times**. The Response
> Normalization Layer owns its *creation*; the ParsedResponse owns its
> *information*; consumers *consume* that information. These three roles never
> merge — which is exactly what keeps every validation rule independent and free of
> any need to recover structure for itself. **Normalization records facts;
> validation interprets facts** (Response Normalization Contract §10).

> **Example**
> Normalization Outcome `NORMALIZED`; Normalized Structure a document with an
> executive-summary object, a requirements array, a risks array, and a
> recommendations array; Normalization Observations record that no duplicate field
> identifier occurred and the encoding is intact; Source Reference points to the
> preserved `generated_text`. The Syntax layer reads the outcome and observations;
> the Schema layer reads the structure. Nothing about this representation changes
> during validation.

---

## 9. Model Relationships

The result models form one aggregate with clear ownership, aggregation, and
derivation lines; the `ParsedResponse` is the consumed representation that feeds
the run.

```text
        ValidationConfiguration   ──influences──►  (a validation run)
                                                         │
                                                         ▼
        ┌──────────────────────── ValidationResult ───────────────────────┐
        │  (aggregate root · immutable · sole output)                      │
        │                                                                  │
        │   owns ──────────►  ValidationIssue  (collection, immutable)     │
        │                          │                                       │
        │   contains ──────►  ValidationSummary  ◄── derived FROM issues   │
        │                                                                  │
        │   contains ──────►  ValidationStatistics  ◄── observed during run│
        │                                                                  │
        │   references ────►  ValidationConfiguration  (for traceability)  │
        │                                                                  │
        │   preserves ─────►  Original Response  (unaltered)               │
        └──────────────────────────────────────────────────────────────────┘
```

| Line | Kind | Explanation |
| ---- | ---- | ----------- |
| **Result → Issues** | Ownership | The result owns the issue collection; issues have no existence outside their result. |
| **Result → Summary** | Aggregation | The result contains the summary as a part; the summary cannot exist independently. |
| **Result → Statistics** | Aggregation | The result contains the statistics as observational parts of the run. |
| **Summary → Issues** | Derivation | Every value in the summary is computed from the issues; it owns no facts of its own. |
| **Result → Configuration** | Reference | The result points to the governing configuration without owning or mutating it. |
| **Configuration → Run** | Influence | Configuration shapes execution; it is an input, not contained content. |
| **Result → Original Response** | Preservation | The result carries the response unchanged, guaranteeing the original survives. |

---

## 10. Model Lifecycle

The models come into being in a fixed conceptual order: configuration precedes
the run; the normalized representation is created once before the run; issues are
observed during it; the summary and statistics are produced from it; and the
result finalises everything.

```text
   1. ValidationConfiguration exists  ──  before any validation begins
                 │
                 ▼
   2. ParsedResponse is created       ──  normalized once, before the run, by the
                 │                         Response Normalization Layer (immutable)
                 ▼
   3. Validation run begins under that configuration, reading the ParsedResponse
                 │
                 ▼
   4. ValidationIssue objects are created  ──  one per observed condition (immutable)
                 │
                 ▼
   5. ValidationSummary is derived  ──  computed from the issue collection
                 │
                 ▼
   6. ValidationStatistics are collected  ──  observed facts of the run
                 │
                 ▼
   7. ValidationResult is finalised  ──  assembled once, then immutable
                 │
                 ▼
   8. ValidationResult returned  ──  the sole output, carrying the verdict
```

| Stage | What happens | State after |
| ----- | ------------ | ----------- |
| **Configuration** | The governing configuration is established | Exists before validation; unchanged by the run |
| **Normalization** | The Response Normalization Layer creates the `ParsedResponse` once | Immutable; read by every layer; never re-created |
| **Issue creation** | Layers observe conditions and emit immutable issues | Each issue is complete and frozen at creation |
| **Summary derivation** | The roll-up is computed from the issues | Faithful projection of the findings |
| **Statistics collection** | Operational metrics are recorded | Observational only; no verdict effect |
| **Result finalisation** | All parts are assembled and the verdict resolved | Immutable; original response preserved |

> **Architectural Decision**
> The lifecycle is **strictly ordered and one-directional**. A later stage never
> reaches back to alter an earlier one: the summary cannot change an issue,
> statistics cannot change the summary, and finalising the result freezes all of
> it. This ordering is what makes a result reproducible from its inputs.

---

## 11. Model Invariants

These invariants are binding on every conforming implementation. They are the
architectural guarantees the models exist to uphold.

| # | Invariant | Why it matters |
| - | --------- | -------------- |
| 0 | **ParsedResponse is immutable, provider- and format-independent, and observation-only.** | The substrate every layer reads must be stable, origin-neutral, format-neutral, and never repaired — or layers would disagree about the same response. |
| 1 | **ValidationIssue is immutable.** | Findings are objective observations; mutation would break determinism and audit. |
| 2 | **ValidationResult is immutable.** | The output must be a stable, reproducible record of one run. |
| 3 | **ValidationSummary is derived only.** | A summary that could be authored could disagree with the facts it summarises. |
| 4 | **ValidationStatistics are observational only.** | Metrics describe the run; they must never influence the verdict. |
| 5 | **Original response is preserved.** | The exact AI output must survive validation for audit and reprocessing. |
| 6 | **ValidationResult owns all issues.** | A single owner gives every finding one authoritative home. |
| 7 | **ValidationSummary cannot exist independently.** | It is a part of a result, meaningless without the issues it projects. |
| 8 | **ValidationStatistics cannot influence the verdict.** | The verdict is decided by issues and severity alone. |
| 9 | **ValidationConfiguration cannot modify philosophy.** | Behaviour may be tuned; meaning, boundary, and verdict logic may not. |

> **Principle**
> Severity is decided once, at issue creation, and the verdict is decided once, at
> result finalisation. Nothing — not the summary, not statistics, not
> configuration — may revise either after the fact. Immutability is not a
> convenience; it is the guarantee that makes the whole subsystem auditable.

---

## 12. Relationship to Other Architecture Documents

These models do not stand alone. They realise the information half of the
validation subsystem and connect to the platform's surrounding architecture.

| Document | Relationship to these models |
| -------- | ---------------------------- |
| **AI Reasoning Contract** | Defines what trustworthy output requires (evidence, traceability). The Evidence and Location attributes of a ValidationIssue make the *presence* of those requirements observable. |
| **Requirement Analysis Service** | Produces the raw response. The Original Response preserved in a ValidationResult is exactly what that service emitted. |
| **Response Normalization Contract** | Governs how the `ParsedResponse` defined here is *created* — once, before validation, by the Response Normalization Layer. These models define *what* the `ParsedResponse` holds; that contract defines *how* it comes into being. |
| **AI Response Validation** | Defines validation philosophy. These models are the canonical information that philosophy operates on; a validator conforms to both. |
| **Prompt Framework** | Shapes the request behind the response. The schema a run validates against — recorded in statistics — aligns with what the prompt asked for. |
| **Execution Package** | Carries the response and its provenance into validation; supplies the Correlation Identifier these models propagate. |
| **Response Validator (future)** | The implementation that *realises* these models; bound to them and to the AI Response Validation Architecture. |
| **CP1 Validation (future)** | A downstream consumer of the ValidationResult; it reads, never alters, the canonical output. |

### 12.1 Dependency diagram

```text
   [AI Reasoning Contract]        [Prompt Framework]
            │ defines trust            │ shapes request
            ▼                          ▼
   [Requirement Analysis Service] ──► raw response ──► (Execution Package: provenance)
            │ emits LLMResponse (generated_text)
            ▼
   [Response Normalization Contract] ── governs ──► Response Normalization Layer
            │ creates the ParsedResponse (ONCE)
            ▼
   [AI Response Validation Architecture] ── philosophy ──►  ┌─────────────────────────┐
                                                            │  VALIDATION CANONICAL    │
   [Validation Canonical Models] ──── information ───────►  │  MODELS (this document)  │
   (ParsedResponse · ValidationIssue · ValidationSummary ·  │  defines ParsedResponse  │
    ValidationStatistics · ValidationResult ·               │  + the result aggregate  │
    ValidationConfiguration)                                └────────────┬────────────┘
                                                  realised by            │ conforms to both
                                                            ▼            ▼
                                              [Response Validator (future)]
                                                            │ reads ParsedResponse; emits ValidationResult
                                                            ▼
                                              [CP1 Validation (future)] (consumer)
```

> **Architectural Decision**
> A Response Validator implementation conforms to **two** governing artifacts at
> once: the **AI Response Validation Architecture** (philosophy) and the
> **Validation Canonical Models** (information). The **Response Normalization
> Contract** governs how the `ParsedResponse` is *created*; these models govern
> what it *holds*. Downstream consumers depend only on the ValidationResult and
> never reach inside the validator.

---

## 13. Future Evolution

The information model is designed to be **extended, never replaced**. New models
may be added to describe concerns not yet modelled; the six canonical models
remain stable beneath them.

| Possible future model | Intent | Constraint |
| --------------------- | ------ | ---------- |
| **ValidationRule** | Model an individual rule as a first-class concept | Extends, does not replace; rules remain order-independent and deterministic. |
| **ValidationLayer** | Model a layer as a first-class concept | Must preserve the existing pipeline and one-concern-per-layer ordering. |
| **ValidationPolicy** | Model externalised verdict/observability policy | Configures behaviour only; never redefines philosophy or verdict logic. |
| **ValidationEvidence** | Model evidence strength, not merely presence | A future extension of the Evidence concern; bound by determinism and immutability. |
| **ValidationHistory** | Model the sequence of runs over a response | Observational; never alters any past, immutable ValidationResult. |

> **Architectural Decision**
> **Future models extend the information model; they never replace the canonical
> models.** Any new model is added alongside the six defined here, bound by the
> same invariants — immutability, derivation, observational statistics, preserved
> original response, and configuration-without-philosophy. A change that mutates a
> canonical model, lets a derived view author facts, or lets statistics or
> configuration influence the verdict is non-conforming. Changes to the canonical
> models advance the Validation Contract Version and require an Architecture
> Decision Record.

---

## Appendix — Conformance Checklist

A Response Validator implementation conforms to these canonical models only if
every box can be checked:

- [ ] Models remain implementation-independent (no language, framework, storage, or serialization assumptions).
- [ ] ParsedResponse is a Core Canonical Model and a Shared Platform Artifact, created once before any consumer runs, immutable, shared, provider- and format-independent, and observation-only.
- [ ] No consumer creates, recovers, re-derives, copies, mutates, or reparses the ParsedResponse; every consumer reads the same instance.
- [ ] Normalization Observations and the Normalization Outcome are un-judged facts — they carry no severity or verdict and are never a ValidationIssue.
- [ ] ValidationIssue is immutable, with severity fixed at creation.
- [ ] ValidationResult is immutable and is the sole output of validation.
- [ ] The original response is preserved unchanged within the result.
- [ ] ValidationSummary is derived from the issues only — never authored or edited.
- [ ] ValidationStatistics are observational only and never influence the verdict.
- [ ] ValidationConfiguration affects execution behaviour only — never validation philosophy.
- [ ] ValidationResult owns all issues; the summary cannot exist independently of it.
- [ ] Model relationships (ownership, aggregation, derivation, reference) are preserved.
- [ ] The model lifecycle is strictly ordered and one-directional.
- [ ] Future models extend, and never replace, the six canonical models.
- [ ] The implementation conforms to both these models and the AI Response Validation Architecture.
