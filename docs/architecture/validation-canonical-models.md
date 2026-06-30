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
> philosophy stay stable while the information model is extended (§12).

---

## 2. Canonical Models Overview

Validation is described by **five canonical models**. Together they form one
cohesive aggregate rooted at the `ValidationResult`.

| Model | Role | One-line meaning |
| ----- | ---- | ---------------- |
| **ValidationIssue** | Atomic finding | One objective, immutable observation about the response. |
| **ValidationSummary** | Derived overview | A roll-up of all issues; never authored, only derived. |
| **ValidationStatistics** | Operational metrics | Observational facts about the run; never affect the verdict. |
| **ValidationResult** | Canonical output | The single, immutable output of validation; owns everything. |
| **ValidationConfiguration** | Behaviour input | Declares which layers, thresholds, and observability govern a run. |

### 2.1 Relationship diagram

```text
        ┌───────────────────────────┐
        │  ValidationConfiguration  │  influences how a run executes
        └─────────────┬─────────────┘
                      │ governs (input, not contained)
                      ▼
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

## 8. Model Relationships

The five models form one aggregate with clear ownership, aggregation, and
derivation lines.

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

## 9. Model Lifecycle

The models come into being in a fixed conceptual order: configuration precedes
the run; issues are observed during it; the summary and statistics are produced
from it; and the result finalises everything.

```text
   1. ValidationConfiguration exists  ──  before any validation begins
                 │
                 ▼
   2. Validation run begins under that configuration
                 │
                 ▼
   3. ValidationIssue objects are created  ──  one per observed condition (immutable)
                 │
                 ▼
   4. ValidationSummary is derived  ──  computed from the issue collection
                 │
                 ▼
   5. ValidationStatistics are collected  ──  observed facts of the run
                 │
                 ▼
   6. ValidationResult is finalised  ──  assembled once, then immutable
                 │
                 ▼
   7. ValidationResult returned  ──  the sole output, carrying the verdict
```

| Stage | What happens | State after |
| ----- | ------------ | ----------- |
| **Configuration** | The governing configuration is established | Exists before validation; unchanged by the run |
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

## 10. Model Invariants

These invariants are binding on every conforming implementation. They are the
architectural guarantees the models exist to uphold.

| # | Invariant | Why it matters |
| - | --------- | -------------- |
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

## 11. Relationship to Other Architecture Documents

These models do not stand alone. They realise the information half of the
validation subsystem and connect to the platform's surrounding architecture.

| Document | Relationship to these models |
| -------- | ---------------------------- |
| **AI Reasoning Contract** | Defines what trustworthy output requires (evidence, traceability). The Evidence and Location attributes of a ValidationIssue make the *presence* of those requirements observable. |
| **Requirement Analysis Service** | Produces the raw response. The Original Response preserved in a ValidationResult is exactly what that service emitted. |
| **AI Response Validation** | Defines validation philosophy. These models are the canonical information that philosophy operates on; a validator conforms to both. |
| **Prompt Framework** | Shapes the request behind the response. The schema a run validates against — recorded in statistics — aligns with what the prompt asked for. |
| **Execution Package** | Carries the response and its provenance into validation; supplies the Correlation Identifier these models propagate. |
| **Response Validator (future)** | The implementation that *realises* these models; bound to them and to the AI Response Validation Architecture. |
| **CP1 Validation (future)** | A downstream consumer of the ValidationResult; it reads, never alters, the canonical output. |

### 11.1 Dependency diagram

```text
   [AI Reasoning Contract]        [Prompt Framework]
            │ defines trust            │ shapes request
            ▼                          ▼
   [Requirement Analysis Service] ──► raw response ──► (Execution Package: provenance)
                                                              │
                                                              ▼
   [AI Response Validation Architecture] ── philosophy ──►  ┌─────────────────────────┐
                                                            │  VALIDATION CANONICAL    │
   [Validation Canonical Models] ──── information ───────►  │  MODELS (this document)  │
                                                            └────────────┬────────────┘
                                                  realised by            │ conforms to both
                                                            ▼            ▼
                                              [Response Validator (future)]
                                                            │ emits ValidationResult
                                                            ▼
                                              [CP1 Validation (future)] (consumer)
```

> **Architectural Decision**
> A Response Validator implementation conforms to **two** governing artifacts at
> once: the **AI Response Validation Architecture** (philosophy) and the
> **Validation Canonical Models** (information). Downstream consumers depend only
> on the ValidationResult and never reach inside the validator.

---

## 12. Future Evolution

The information model is designed to be **extended, never replaced**. New models
may be added to describe concerns not yet modelled; the five canonical models
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
> models.** Any new model is added alongside the five defined here, bound by the
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
- [ ] ValidationIssue is immutable, with severity fixed at creation.
- [ ] ValidationResult is immutable and is the sole output of validation.
- [ ] The original response is preserved unchanged within the result.
- [ ] ValidationSummary is derived from the issues only — never authored or edited.
- [ ] ValidationStatistics are observational only and never influence the verdict.
- [ ] ValidationConfiguration affects execution behaviour only — never validation philosophy.
- [ ] ValidationResult owns all issues; the summary cannot exist independently of it.
- [ ] Model relationships (ownership, aggregation, derivation, reference) are preserved.
- [ ] The model lifecycle is strictly ordered and one-directional.
- [ ] Future models extend, and never replace, the five canonical models.
- [ ] The implementation conforms to both these models and the AI Response Validation Architecture.
