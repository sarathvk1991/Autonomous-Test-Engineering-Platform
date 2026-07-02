# AI Response Validation Layer Architecture

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Quality Gate       |
| Status               | Approved — foundational                                           |
| Scope                | Validation of AI output before downstream engineering consumption  |
| Governs              | All Response Validator implementations in the Autonomous Test Engineering Platform |
| Depends on           | AI Reasoning Contract · Requirement Analysis Service · Prompt Framework |
| Audience             | Solution Architects · Technical Architects · Lead Engineers · AI Architects · QA Architects |
| Implementation-bound | No — valid regardless of language, framework, or model provider    |

> **Architectural Decision**
> The Response Validation Layer is the **mandatory quality gate between AI
> generation and every downstream engineering capability**. No requirement
> normalisation, CP1 validation, feature generation, test generation, or output
> writing may consume AI output that has not first passed through this layer.
> Validation is not an optional refinement step; it is the load-bearing boundary
> that separates *generated content* from *trusted content*.

---

## 1. Purpose

### 1.1 Why AI response validation exists

The platform delegates analytical work to large language models. That work
produces output which other engineering capabilities will act upon —
normalising requirements, applying quality gates, generating features and
tests, and writing platform outputs. Each of those downstream capabilities
*assumes* the input it receives is well-formed, complete, evidence-backed, and
structurally sound.

That assumption is dangerous unless something guarantees it. AI output is
non-deterministic at the surface level (§ AI Reasoning Contract), can be
malformed, can omit required structure, can present conclusions without
evidence, and can — despite every reasoning safeguard — drift from what the
platform requires. If downstream components consumed raw AI output directly:

- A single malformed response would propagate corruption deep into the
  pipeline before failing, far from its cause.
- Each downstream component would re-implement its own ad-hoc checking, with
  inconsistent rigour and no shared definition of "acceptable."
- Trust in the platform's outputs would rest on hope rather than on a governed,
  auditable gate.
- Failures would be discovered late, expensively, and without explanation.

The Response Validation Layer exists to **decide whether AI output is
trustworthy enough to be consumed by downstream engineering activities** — and
to make that decision once, consistently, explainably, and at a single
governed boundary.

> **Principle**
> Validation is not merely JSON validation. Confirming that text parses as
> structured data is the *first* of many concerns, not the whole of them. The
> layer's true purpose is to determine **trustworthiness**, of which syntactic
> well-formedness is only a precondition.

### 1.2 What validation determines

Validation answers a single governing question: *is this AI output trustworthy
enough to be consumed downstream?* That question decomposes into five
dimensions the layer is responsible for assessing.

| Dimension       | The question it answers | Why downstream activities depend on it |
| --------------- | ----------------------- | -------------------------------------- |
| **Trust**       | Can a downstream component act on this output without independently re-checking it? | Trust is the entire reason the gate exists; once validated, output is consumed as-is. |
| **Quality**     | Does the output meet the structural and content standards the platform requires? | Poor-quality input produces poor-quality engineering artifacts downstream. |
| **Determinism** | Will the same output, validated again, reach the same verdict? | A non-deterministic gate cannot be governed, audited, or regression-tested. |
| **Safety**      | Will consuming this output corrupt, mislead, or destabilise downstream activities? | The gate protects the pipeline from malformed, incomplete, or unsupported content. |
| **Governance**  | Can a human reviewer understand, audit, and override the verdict? | Automated verdicts must remain accountable to human authority. |

### 1.3 What this document is **not**

| This document is NOT | Because |
| -------------------- | ------- |
| An implementation guide | No code, data structures, APIs, or libraries are described here. |
| A schema definition | It governs *that* schemas are validated, not the content of any specific schema. |
| Provider documentation | No model, vendor, SDK, or endpoint is referenced. |
| A reasoning specification | How the AI *thinks* is governed by the AI Reasoning Contract; this layer judges its *output*. |
| A retry or failover policy | It defines failure-handling *philosophy*; concrete policies live elsewhere (§10). |

---

## 2. Scope

### 2.1 What this layer owns

The Response Validation Layer owns the assessment of AI output and nothing
else. Its responsibilities are deliberately confined to *judging* an answer
already produced.

| Owned responsibility | Description |
| -------------------- | ----------- |
| **AI response validation** | The end-to-end act of judging whether an AI response is trustworthy enough to consume. |
| **Syntax validation** | Confirming the response is well-formed structured data — by reading the normalized representation (`ParsedResponse`) produced by the Response Normalization Layer (§4.4), never by parsing the response itself. |
| **Schema validation** | Confirming the normalized structure conforms to the expected, versioned schema — including the **presence (existence)** of every required section, container, and collection, plus types and enumerations (ADR-0004). |
| **Structural validation** | Confirming the **composition, hierarchy, and organization** of the parts that exist — nesting and relationships between sections; their *existence* is Schema's, not Structural's (ADR-0004). |
| **Content validation** | Confirming field-level content meets type, range, and presence expectations. |
| **Evidence validation** | Confirming conclusions are accompanied by the evidence references the platform requires. |
| **Traceability validation** | Confirming each output element carries the links that make it auditable. |
| **Quality assessment** | Forming an overall judgement of the response's fitness, expressed as a validation result. |
| **Validation reporting** | Producing an explainable record of every issue found and the resulting verdict. |

### 2.2 What this layer does **not** own

The layer is a judge, not an author, an interpreter, or an authority. The
following are explicitly **out of scope**.

| Not owned by this layer | Owned elsewhere |
| ----------------------- | --------------- |
| **AI generation** | Requirement Analysis Service + provider framework |
| **Prompt construction** | Prompt Framework |
| **Requirement extraction** | Reasoning + downstream normalisation |
| **Requirement normalisation** | Requirement Normalization Architecture (future) |
| **CP1 validation** | CP1 Validation Architecture (future) |
| **Feature generation** | Feature Generation Architecture (future) |
| **Test generation** | Test Generation Architecture (future) |
| **Output writing / persistence** | Output Generation / storage layer (future) |
| **Business approval** | Human governance (review queues) |
| **Project decisions** | Human stakeholders and product owners |

> **Architectural Decision**
> The layer judges **whether output is well-formed, complete, evidence-backed,
> and structurally trustworthy** — never **whether the output is correct in the
> real world**. Correctness about the system under analysis is a matter of
> evidence and human judgement (§9). Confusing structural trustworthiness with
> factual correctness would expand the layer beyond what it can deterministically
> decide, violating the boundary that makes it governable.

---

## 3. Guiding Principles

These eleven principles are binding. Every conforming Response Validator
implementation must satisfy all of them simultaneously. Where principles appear
to conflict, **Preserve Original Response** and **Human Governance** take
precedence.

### 3.1 Fail Fast

**Purpose.** Stop progression at the earliest point a defect makes downstream
work meaningless, so failures surface close to their cause.

**Rules.**
- A failure at a foundational layer (transport, syntax) halts progression to
  dependent layers.
- The layer must not attempt content checks on a response that did not normalize
  into well-formed structure (Normalization Outcome `MALFORMED`).
- The first blocking failure is reported immediately, with full context.

**Expected behaviour.** Validation behaves like a build pipeline: a foundational
break stops the run rather than producing a cascade of meaningless secondary
errors.

**Example.** A response that is not well-formed structured data is rejected at
the syntax layer; the validator does not then report fifty "missing field"
errors that are merely symptoms of the unparseable input.

### 3.2 Never Guess

**Purpose.** Ensure the verdict reflects what the response *actually contains*,
never what the validator assumes it *probably meant*.

**Rules.**
- Ambiguous, missing, or malformed content is reported as such — never inferred.
- The validator does not "helpfully" interpret a near-miss as a pass.
- Absence of a required element is a finding, not something to be filled in.

**Expected behaviour.** When a required element is missing or unclear, the layer
records a precise issue rather than substituting a plausible value.

**Example.** A required evidence reference is empty. The validator records a
missing-evidence issue; it does not assume which artifact was intended.

### 3.3 Preserve Original Response

**Purpose.** Guarantee that validation observes the AI output without altering
it, so the original is always available for audit, reprocessing, and human
review.

**Rules.**
- The validator never mutates, repairs, reformats, or "cleans" the AI response.
- The original response is carried through unchanged regardless of verdict.
- Any normalisation needed for inspection is internal and never replaces the
  original.

**Expected behaviour.** The exact bytes the AI produced remain available after
validation, identical to what was generated.

> **Architectural Decision**
> **Validation observes; it does not edit.** A layer that repaired output would
> blur the line between *judging* and *generating*, destroy the auditable
> original, and make verdicts irreproducible. Repair, where it ever exists, is a
> separate future capability (§14) that operates *outside* this layer.

### 3.4 Deterministic Validation

**Purpose.** Ensure the same response always produces the same verdict, so the
gate can be audited, regression-tested, and trusted.

**Rules.**
- Given the same response and the same schema/version, the verdict, the issues,
  and their severities are identical on every run.
- Validation logic must not depend on randomness, time, or external mutable
  state for its conclusions.
- Two validators of the same version must agree.

**Expected behaviour.** Re-validating an archived response years later yields the
same result it did originally.

**Example.** A response validated as `FAILED` with three `ERROR` issues produces
exactly that verdict and those issues every time it is re-validated under the
same schema version.

### 3.5 Layered Validation

**Purpose.** Keep each concern isolated so that failures are precise,
explainable, and independently evolvable.

**Rules.**
- Each validation layer assesses exactly one concern (§4).
- A layer assumes its predecessors have already passed.
- Layers are ordered from most foundational to most semantic.

**Expected behaviour.** A failure is always attributable to a specific concern —
"schema," "evidence," "traceability" — never to a vague "validation error."

**Example.** A structural failure is reported by the structural layer alone; it
does not masquerade as a content or evidence failure.

### 3.6 Explain Every Failure

**Purpose.** Make every negative verdict actionable and auditable.

**Rules.**
- Every issue states what failed, where, why, and what would resolve it.
- No issue may be a bare code or an opaque "invalid" with no context.
- The set of issues fully justifies the overall verdict.

**Expected behaviour.** A reviewer can read any issue and know precisely what to
fix without inspecting the validator's internals.

**Example.** Instead of "validation failed," the layer reports: *"ERROR — Schema:
required field `severity` missing at `risks[2]`. Expected one of {INFO, WARNING,
ERROR, CRITICAL}. Add a severity to this risk."*

### 3.7 Evidence Before Confidence

**Purpose.** Refuse to treat a fluent, confident-looking response as trustworthy
unless it carries the evidence the platform requires.

**Rules.**
- A conclusion presented without its required evidence reference is an issue,
  regardless of how well-formed it is.
- Persuasiveness of wording never substitutes for the presence of evidence.
- Evidence validation is a first-class concern, not an optional extra.

**Expected behaviour.** The layer is unmoved by eloquence; it checks for the
references that make a claim auditable (consistent with the AI Reasoning
Contract's evidence-driven reasoning).

**Example.** A high-severity risk with no linked evidence is flagged, even though
the prose reads convincingly.

### 3.8 Provider Independence

**Purpose.** Make the verdict a property of the *response and the schema*, never
of which provider or model produced it.

**Rules.**
- Validation logic references no provider, model, vendor, or endpoint.
- The same response yields the same verdict regardless of its origin.
- No provider receives lenient or privileged treatment.

**Expected behaviour.** Substituting the underlying model changes nothing about
how its output is judged.

**Example.** Two responses, identical in content but produced by different
models, receive identical verdicts.

### 3.9 Architecture Independence

**Purpose.** Keep the validation framework independent of any technology,
framework, or implementation strategy.

**Rules.**
- The layer is defined by responsibilities and contracts, not by code.
- Any conforming implementation, in any technology, satisfies this document.
- Implementation choices may change without changing this specification.

**Expected behaviour.** A complete reimplementation on a different stack is still
governed, unchanged, by this document.

### 3.10 Human Governance

**Purpose.** Keep a human accountable for every consequential decision, above any
automated verdict.

**Rules.**
- An automated verdict is a recommendation to the governance process, not a
  final authority over what humans may decide.
- A human may review, accept, override, or escalate any validation outcome.
- The layer never presents its verdict as beyond human override.

**Expected behaviour.** The gate accelerates and standardises human judgement; it
does not replace it.

> **Architectural Decision**
> **Human Governance overrides every automated validation decision.** A human
> reviewer may accept output the layer rejected, or reject output the layer
> passed. The layer's role is to inform that decision with a deterministic,
> explainable verdict — never to remove the human from the loop.

### 3.11 Rule Independence

**Purpose.** Ensure that the validation rules *within* a single validation layer
produce the same result regardless of the order in which they execute, so the
layer remains deterministic and amenable to future parallel evaluation.

**Rules.**
- Rules within a layer must be deterministic — each depends only on the response
  and the schema, never on which rules ran before it.
- Rules must not mutate shared state; one rule's execution must never change the
  input another rule observes.
- Rules should be parallelisable in future implementations; correctness must not
  rely on sequential evaluation.

**Expected behaviour.** Given a fixed response, any permutation of a layer's
rules yields an identical set of issues with identical severities. Execution
order is an implementation freedom, not a semantic dependency.

> **Worked example**
> Within the Evidence layer, three rules evaluate the same response:
> *Rule A* — every risk carries at least one evidence reference;
> *Rule B* — no evidence reference is empty;
> *Rule C* — every evidence reference points to a known source category.
> Whether they run A → B → C, C → B → A, or all three at once, the resulting
> issue set is identical. If `risks[2]` has an empty evidence list, *Rule A* and
> *Rule B* both raise their issues independently; neither suppresses, reorders,
> nor alters the other's finding, and neither modifies the response so as to mask
> a sibling rule's check.

> **Architectural Decision**
> **Rule Independence is what makes Deterministic Validation (§3.4) survive
> implementation evolution.** Because no rule depends on execution order or shared
> mutable state, a future implementation may reorder or parallelise rule
> evaluation for performance without changing a single verdict. Order-dependent
> rules are non-conforming.

---

## 4. Validation Philosophy

### 4.1 Validation is progressive

Validation is **progressive**: it advances through ordered layers, from the most
foundational concern to the most semantic. Each layer assumes the prior layers
have succeeded and adds exactly one new guarantee.

> **Principle**
> Each layer validates **one concern only**. A single failed layer stops
> progression when continuing would be meaningless or unsafe. This is what makes
> failures precise and the pipeline explainable.

Not every failure halts the pipeline. Foundational failures (transport, syntax,
schema) make all subsequent layers meaningless and therefore stop progression
immediately (Fail Fast, §3.1). Later-layer findings may, depending on severity
(§6), be *recorded* while progression continues — because a missing
recommendation does not invalidate a well-formed, schema-conformant response the
way unparseable input does.

### 4.2 Layered validation pipeline

```text
                         AI Response
                              │
                              ▼
                  ┌───────────────────────┐
                  │  Transport Validation  │  was a usable response received at all?
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │   Syntax Validation    │  is it well-formed structured data?
                  └───────────┬───────────┘      (reads the normalized representation)
                              ▼
                  ┌───────────────────────┐
                  │   Schema Validation    │  does the normalized structure match the schema?
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │ Structural Validation  │  are the existing parts composed / organized correctly?
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │  Content Validation    │  are field values typed, ranged, and present?
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │  Evidence Validation   │  are conclusions backed by required evidence?
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │ Traceability Validation│  is every element auditable end to end?
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │  Reasoning Validation  │  is the output internally coherent and consistent?
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │ Business Rule Validation│ does it satisfy declared platform-level rules?
                  └───────────┬───────────┘
                              ▼
                       Validation Result
```

### 4.3 Responsibility of each layer

| Layer | Concern | Responsibility |
| ----- | ------- | -------------- |
| **Transport** | Delivery | Confirm a usable response payload was actually received and is non-empty at the transport level. |
| **Syntax** | Well-formedness | Confirm the response is well-formed structured data, by reading the normalized representation (`ParsedResponse`); the layer itself never parses or normalizes (§4.4). |
| **Schema** | Shape conformance & existence | Confirm the normalized structure matches the expected, versioned schema — the required sections/containers/collections **exist** and the fields conform (types, enums) (ADR-0004). |
| **Structural** | Composition / hierarchy | Confirm the sections that **exist** are composed, nested, related, and organized correctly; existence itself is Schema's concern (ADR-0004). |
| **Content** | Field validity | Confirm individual values meet type, range, format, and presence expectations. |
| **Evidence** | Groundedness | Confirm conclusions carry the evidence references the platform requires (cf. AI Reasoning Contract). |
| **Traceability** | Auditability | Confirm each element carries the links needed to trace it back to its source and context. |
| **Reasoning** | Coherence | Confirm the output is internally consistent — no contradictions, no orphaned references, severities align with content. |
| **Business Rule** | Policy | Confirm declared, platform-level structural rules are satisfied (not domain correctness). |

### 4.4 Response Normalization precedes validation

Every layer from Syntax onward reasons about the **structure** the response
expresses, not the raw text. That structure is recovered **exactly once**, before
the pipeline runs, by the **Response Normalization Layer** — a permanent,
first-class architecture component governed by the **Response Normalization
Contract**. It turns the provider-independent `LLMResponse` into the canonical,
format-neutral `ParsedResponse` (Validation Canonical Models §8) that the pipeline
then reads.

```text
   Provider Adapter
        │ normalizes outcome → ExecutionStatus, text → generated_text
        ▼
   LLMResponse                       (provider-independent text + outcome)
        │
        ▼
   Response Normalization Layer      (recovers structure ONCE; no validation/repair/interpretation)
        │
        ▼
   Normalization Result              (aggregate produced by the subsystem)
        ├─ ParsedResponse            (canonical, provider- and format-independent structure — Shared Platform Artifact)
        └─ Normalization Observations (execution facts about the run)
        │
        ▼
   Response Validator                (consumes the Normalization Result)
        │ orchestrates the pipeline
        ▼
   Validation Pipeline               (Syntax reads the outcome + observations; Schema onward read the structure)
        │
        ▼
   Validation Result
```

The Response Validator consumes the **Normalization Result** and reads the
`ParsedResponse` together with the Normalization Observations the aggregate carries:

| Layer | What it reads |
| ----- | ------------- |
| **Transport** | Nothing — it reads delivery facts (`execution_status`, presence, emptiness) and runs *before* normalization is consulted. |
| **Syntax** | The **Normalization Outcome** (`NORMALIZED` / `MALFORMED`) from the `ParsedResponse`, and the **Normalization Observations** (e.g. duplicate identifiers, encoding integrity) from the **Normalization Result**. |
| **Schema · Structural · Content · Evidence · Traceability · Reasoning · Business Rule** | The **normalized structure** from the `ParsedResponse` — the same representation, read by all. |

> **Architectural Decision — why Response Normalization exists.**
> Recovering structure is a **normalization** concern, not a validation one. If
> each validation layer recovered structure for itself, the same response would be
> interpreted many times, the "is it well-formed?" concern would leak into every
> layer, and two layers could disagree about the same input. A single normalization
> step produces one shared, deterministic representation — exactly as the provider
> adapter is the single owner of outcome normalization (`ExecutionStatus`).

> **Architectural Decision — why no validation layer parses or normalizes.**
> The Response Normalization Layer **owns creation**; the `ParsedResponse` **owns
> information**; the validation framework **consumes information**. Therefore the
> Syntax layer **validates** the normalized representation — it does not produce
> it — and Schema, Structural, Content, Evidence, Traceability, Reasoning, and
> Business Rule all consume the **exact same** representation. No validation layer
> performs parsing, and no validation layer performs normalization. This upholds
> Rule Independence (§3.11): no layer depends on another having recovered structure
> first.

> **Architectural Decision — why `ParsedResponse` is format-independent.**
> The `ParsedResponse` represents **normalized structure, not a specific
> serialization format.** A structured document may be expressed in different
> formats over time; the structure it expresses is the same. Keeping the
> representation format-neutral means a new structured format normalizes into the
> *same* `ParsedResponse` and no validation layer changes (Response Normalization
> Contract §7).

> **Architectural Decision — normalization produces facts; validation produces
> judgments.** Normalization produces **facts** with distinct owners: the
> `ParsedResponse` carries the Normalization Outcome (`NORMALIZED` / `MALFORMED`),
> while the Normalization Observations (e.g. a duplicate identifier, an encoding
> observation) are aggregated by the **Normalization Result**, not the
> `ParsedResponse`. These facts carry **no severity, no
> verdict, and are never a `ValidationIssue`.** A validation rule may *read* a fact
> and *decide* to raise an issue — that judgement, and any severity or
> recommendation it carries, belongs entirely to validation. This boundary is
> permanent (Response Normalization Contract §10): nothing on the normalization
> side carries a verdict, and no validation layer recovers structure.

---

## 5. Validation Categories

Each category corresponds to a layer in the pipeline. The table below is the
authoritative reference for what each category checks, how it typically fails,
and whether a failure permits the pipeline to continue.

| Category | Purpose | Typical failures | Example | May execution continue? |
| -------- | ------- | ---------------- | ------- | ----------------------- |
| **Transport** | Confirm a usable response was received | Empty payload; truncated response; no content | A response payload of zero length | **No** — nothing to validate |
| **Syntax** | Confirm well-formed structured data | Malformed structure; unbalanced delimiters; unparseable text | Output is prose where structured data was required | **No** — cannot proceed unparsed |
| **Schema** | Confirm conformance & existence against the expected versioned schema | Missing required section/container/field/collection; wrong type; invalid enum; version mismatch | A required `severity` field absent on a risk; the `risks` container absent entirely (ADR-0004) | **No** — downstream relies on shape |
| **Structure** | Confirm composition, hierarchy, and organization | Broken parent-child nesting; mis-ordered or mis-organized sections that already exist | A present `risks` container mis-nested in the document hierarchy (its *absence* is a Schema finding, ADR-0004) | **No** — composition is foundational |
| **Content** | Confirm field-level validity | Wrong type; out-of-range value; invalid enumerated value; empty required string | `confidence` set to a value outside the allowed set | **Conditional** — by severity (§6) |
| **Evidence** | Confirm conclusions are grounded | Conclusion without evidence reference; dangling evidence link | A risk with an empty evidence list | **Conditional** — by severity (§6) |
| **Traceability** | Confirm auditable linkage | Missing source link; missing correlation identifier; broken trace chain | A requirement with no source artifact reference | **Conditional** — by severity (§6) |
| **Reasoning** | Confirm internal coherence | Contradictory items; severity inconsistent with content; orphaned cross-references | Two requirements asserting different limits for the same field | **Conditional** — by severity (§6) |
| **Business Rules** | Confirm declared platform rules | Violated declared platform policy; prohibited combination present | A response with fewer than the mandated minimum number of recommendations (a *policy* breach; a missing required *section* is Schema existence, ADR-0004) | **Conditional** — by severity (§6) |

> **Architectural Decision**
> Foundational categories (Transport, Syntax, Schema, Structure) are
> **progression-stopping by nature**: their failure makes every later category
> meaningless. Semantic categories (Content, Evidence, Traceability, Reasoning,
> Business Rules) are **severity-governed**: whether they stop progression is
> decided by the Severity Model (§6), not by the category itself.

---

## 6. Validation Severity Model

Every issue carries a severity. Severity expresses *how much the issue threatens
trustworthiness* and drives the execution decision.

| Severity | Purpose | Typical examples | Execution impact |
| -------- | ------- | ---------------- | ---------------- |
| **INFO** | Record an observation that does not threaten trust | A non-blocking stylistic note; an optional field absent | None — continue |
| **WARNING** | Flag a concern that should be reviewed but does not invalidate the output | A low-priority section sparse; a non-critical recommendation missing | Continue, with the warning recorded |
| **ERROR** | Mark a defect that makes the output untrustworthy for downstream use | A required field missing; an unsupported conclusion | Reject — output must not be consumed as-is |
| **CRITICAL** | Mark a defect that makes the output unsafe to process at all | Unparseable response; schema/version mismatch; structural collapse | Block — halt the pipeline immediately |

### 6.1 Severity decision matrix

| Highest severity present | Verdict | Downstream action |
| ------------------------ | ------- | ----------------- |
| None | **PASSED** | Continue — consume the output |
| INFO only | **PASSED** | Continue — observations recorded |
| WARNING (no ERROR/CRITICAL) | **PASSED_WITH_WARNINGS** | Continue with warnings — surface for review, consumption permitted |
| ERROR (no CRITICAL) | **FAILED** | Reject — do not consume; route for remediation/escalation |
| CRITICAL | **BLOCKED** | Block downstream execution — halt immediately; output is unsafe to process |

> **Principle**
> Severity is assigned by the *nature of the defect*, not by where it was found.
> A missing evidence reference is an `ERROR` whether it surfaces in the evidence
> layer or the reasoning layer. Consistent severity assignment is what makes the
> decision matrix deterministic.

---

## 7. Validation Issue Model

A **validation issue** is the atomic unit of a validation result: one precise,
explainable finding. The model is described *conceptually*; no implementation
structure is defined.

| Field | Represents | Why it is required |
| ----- | ---------- | ------------------ |
| **Issue Identifier** | A stable handle for this specific finding | Lets reviewers and systems reference the issue unambiguously |
| **Category** | Which validation concern raised it (§5) | Attributes the issue to a single, precise concern |
| **Severity** | How much it threatens trustworthiness (§6) | Drives the execution decision |
| **Message** | A human-readable statement of what failed and why | Makes the issue understandable without internals |
| **Affected Location** | Where in the response the issue occurs | Lets a reviewer navigate directly to the defect |
| **Evidence** | The observed value or condition that triggered the issue | Substantiates the finding; proves it is not a false positive |
| **Recommendation** | What would resolve the issue | Makes the issue actionable, not merely descriptive |
| **Blocking Indicator** | Whether this issue, alone, stops downstream consumption | Lets consumers reason about the verdict at the issue level |

> **Principle**
> Every validation issue must be **explainable**. An issue that cannot state
> *what* failed, *where*, *why*, and *how to resolve it* is not a valid issue —
> it is an opaque assertion that defeats Human Governance and Explain Every
> Failure (§3.6, §3.10). Explainability is a structural requirement of the model,
> not a courtesy.

> **Worked example**
> A single issue: *Identifier* `VAL-0048`; *Category* Evidence; *Severity* ERROR;
> *Message* "Risk presented without supporting evidence"; *Affected Location*
> `risks[2].evidence`; *Evidence* "evidence list is empty"; *Recommendation*
> "Attach at least one evidence reference linking this risk to a source
> artifact"; *Blocking Indicator* true. A reviewer needs nothing else to act.

---

## 8. Validation Result Model

The **validation result** is the conceptual output of the layer. It aggregates
every issue and resolves them into a single verdict, while preserving the
original response unchanged (§3.3).

| Information element | Represents |
| ------------------- | ---------- |
| **Overall state** | One of the four verdict states below |
| **Issues** | The complete, ordered set of validation issues found |
| **Severity summary** | Counts of issues by severity |
| **Original response** | The unaltered AI output that was validated |
| **Validation metadata** | Schema version, validation contract version, validator version, duration, correlation identifier (§11, §13.4) |

### 8.1 Result states

| State | Meaning | What downstream components must do |
| ----- | ------- | ---------------------------------- |
| **PASSED** | No blocking concerns; output is trustworthy | Consume the output normally |
| **PASSED_WITH_WARNINGS** | Output is trustworthy; non-blocking concerns were recorded | Consume the output; surface warnings for human review |
| **FAILED** | One or more `ERROR` issues; output is not trustworthy | Do **not** consume; route for remediation, escalation, or human decision |
| **BLOCKED** | One or more `CRITICAL` issues; output is unsafe to process | Halt the pipeline immediately; do not attempt further processing |

### 8.2 Result state transitions

```text
                         ┌──────────────────────────────┐
                         │      Validation begins        │
                         └───────────────┬──────────────┘
                                         ▼
                              accumulate issues per layer
                                         │
              ┌──────────────┬───────────┼───────────┬──────────────┐
              ▼              ▼           ▼           ▼              ▼
         no issues      INFO only    WARNING      ERROR        CRITICAL
              │              │       (no E/C)    (no CRIT)         │
              ▼              ▼           ▼           ▼              ▼
          ┌────────┐    ┌────────┐  ┌──────────────┐ ┌────────┐ ┌─────────┐
          │ PASSED │    │ PASSED │  │ PASSED_WITH_ │ │ FAILED │ │ BLOCKED │
          │        │    │        │  │  WARNINGS    │ │        │ │         │
          └───┬────┘    └───┬────┘  └──────┬───────┘ └───┬────┘ └────┬────┘
              │             │              │             │           │
              └─────────────┴──────────────┘             │           │
                            │ consume                    │ reject    │ halt
                            ▼                            ▼           ▼
                   downstream engineering         remediation   pipeline stop
                                                  / escalation
```

> **Architectural Decision**
> The verdict is the **highest severity wins**: a single `CRITICAL` forces
> `BLOCKED` regardless of how many lower-severity issues are present, and a single
> `ERROR` forces `FAILED`. There is no averaging, scoring, or tolerance budget.
> This keeps the verdict deterministic and the safety guarantee absolute.

---

## 9. Validation Boundary

> **This section is mandatory.** It defines precisely where validation stops, and
> why crossing that line would violate the platform's architecture principles.

The layer validates **the trustworthiness of the response as an artifact** — its
form, completeness, groundedness, and internal coherence. It does **not**
validate **truths about the world** that no deterministic check can establish.

| Concern | Within validation boundary? |
| ------- | --------------------------- |
| Transport / delivery of a usable response | ✓ |
| Syntax — well-formedness of the normalized structure | ✓ |
| Schema conformance | ✓ |
| Structural completeness | ✓ |
| Content / field validity | ✓ |
| Evidence completeness (references present) | ✓ |
| Traceability linkage present | ✓ |
| Internal coherence / consistency | ✓ |
| Declared platform structural rules | ✓ |
| **Requirement correctness** (is the requirement *right* for the system?) | ✗ |
| **Business approval** (should this be accepted?) | ✗ |
| **Requirement prioritisation** (what matters most?) | ✗ |
| **Test feasibility** (can this realistically be tested?) | ✗ |
| **Release readiness** (is the product ready to ship?) | ✗ |

### 9.1 Why the boundary must hold

```text
   ┌──────────────────────────────────────────────────────────┐
   │  INSIDE the boundary — deterministically decidable        │
   │  form · schema · structure · evidence present · coherence │
   └──────────────────────────────────────────────────────────┘
                              │
                  ════════════╪════════════  ← the validation boundary
                              │
   ┌──────────────────────────────────────────────────────────┐
   │  OUTSIDE the boundary — requires judgement / authority     │
   │  correctness · approval · priority · feasibility · release │
   └──────────────────────────────────────────────────────────┘
```

Every concern *inside* the boundary can be decided **deterministically** from
the response and its schema alone — satisfying Deterministic Validation (§3.4).
Every concern *outside* the boundary requires either world knowledge the layer
does not have, or human authority the layer must not usurp.

> **Architectural Decision**
> Expanding validation beyond these boundaries would violate three principles at
> once: **Deterministic Validation** (correctness and feasibility are not
> deterministically decidable), **Never Guess** (the layer would have to infer
> truths it cannot observe), and **Human Governance** (approval, priority, and
> release are human decisions). The boundary is not a limitation to be overcome;
> it is the line that keeps the layer governable.

---

## 10. Failure Handling Strategy

The layer defines five **failure-handling intents**. This document specifies the
*philosophy* of each — when each is appropriate. It does **not** define concrete
policies; specific retry counts, escalation routes, and back-off behaviour belong
to downstream orchestration and operational documents.

| Strategy | Intent | When it is appropriate |
| -------- | ------ | ---------------------- |
| **Reject** | Refuse to let the output be consumed | An `ERROR`-level result (`FAILED`): the output is untrustworthy |
| **Continue** | Permit consumption despite recorded concerns | A `WARNING`-level result (`PASSED_WITH_WARNINGS`): concerns are non-blocking |
| **Escalate** | Route the result to human governance | Any result a human must adjudicate — failures, ambiguous cases, repeated failures |
| **Retry** | Request a fresh generation of the output | A transport- or transient-level failure where regeneration may succeed |
| **Record Only** | Log the finding without affecting the verdict | `INFO`-level observations kept for analytics and trend insight |

> **Architectural Decision**
> This document defines failure-handling **philosophy only**. The decision *to*
> retry belongs here; *how many times*, *with what back-off*, and *to whom to
> escalate* are operational policies owned elsewhere. Embedding concrete policies
> in this governing document would couple a stable specification to volatile
> operational tuning.

### 10.1 Failure-handling flow

```text
              Validation Result produced
                        │
                        ▼
            ┌───────────────────────────┐
            │  What is the verdict?      │
            └───────────┬───────────────┘
        ┌───────────────┼───────────────┬────────────────┐
        ▼               ▼               ▼                ▼
     PASSED      PASSED_WITH_       FAILED           BLOCKED
        │          WARNINGS           │                 │
        │             │               │                 │
        ▼             ▼               ▼                 ▼
   ┌────────┐   ┌──────────┐   ┌────────────┐   ┌────────────────┐
   │Continue│   │ Continue │   │   Reject    │   │     Reject     │
   │        │   │ + Record │   │ + Escalate  │   │ + Escalate     │
   └────────┘   └──────────┘   └─────┬──────┘   └───────┬────────┘
                                     │                   │
                          transient / transport?         │
                                     │ yes               │ never auto-retry
                                     ▼                   ▼
                                  Retry          Halt; human governance
                                (policy elsewhere)
```

---

## 11. Observability

Validation must be **observable**: every validation run emits a consistent set of
signals so the gate itself can be measured, trended, and audited.

| Signal | Meaning | Why it matters |
| ------ | ------- | -------------- |
| **Validation Duration** | How long validation took | Performance and SLA insight; detects pathological inputs |
| **Issue Counts** | Total number of issues found | Volume signal for quality trends |
| **Severity Distribution** | Issue counts per severity | Distinguishes noise (INFO) from danger (CRITICAL) at a glance |
| **Validation Categories** | Which categories raised issues | Pinpoints *where* responses most often fail |
| **Response Size** | The size of the validated response | Correlates failures with abnormally large or truncated output |
| **Schema Version** | The schema version validated against | Separates schema-evolution effects from genuine regressions |
| **Validation Contract Version** | The version of the validation *semantics* in force (§13.4) | Distinguishes a change in what validation *means* from a change in its mechanism |
| **Validator Version** | The version of the validator that ran (implementation only) | Distinguishes validator changes from response changes |
| **Execution Correlation** | The identifier linking validation to its originating analysis | Stitches generation → validation → downstream into one trace |

### 11.1 Why validation must be observable

```text
   Analysis ──► Validation ──► Downstream engineering ──► Governance
        └──────────── single execution correlation ───────────┘
```

> **Principle**
> If a validation run cannot be traced — by duration, issue counts, severity
> distribution, categories, schema version, validation contract version,
> validator version, and execution correlation — then the gate itself cannot be
> governed. An unobservable quality
> gate is an unaccountable one. Observability is what makes validator regression
> analysis, schema-version impact analysis, and audit possible.

---

## 12. Relationship to Other Architecture Documents

The Response Validation Layer sits at the centre of the platform's trust
boundary. It consumes what generation produces and gates what every downstream
capability consumes.

| Document | Relationship to this layer |
| -------- | -------------------------- |
| **AI Reasoning Contract** | Defines what *trustworthy* output looks like — evidence, traceability, honesty. This layer enforces the *presence* of what that contract requires. |
| **Requirement Analysis Service** | Produces the raw, un-validated Analysis Result. This layer is its immediate, mandatory consumer. |
| **Response Normalization Contract** | Governs the Response Normalization Layer that turns the `LLMResponse` into the canonical `ParsedResponse` (§4.4) *before* validation. This layer **reads** that representation; it never normalizes. |
| **Validation Canonical Models — `ParsedResponse`** | The canonical, format-neutral normalized structure this layer consumes: the Syntax layer reads its outcome, every later layer reads its structure. |
| **Prompt Framework** | Shapes the request that produced the response. The schema this layer validates against is aligned with what the prompt asks for. |
| **Execution Package** | Carries the response and its provenance into validation; supplies the metadata this layer correlates against. |
| **Platform Capabilities** | The broader set of engineering capabilities that depend on validated output as a precondition. |
| **Response Validator (future)** | A conforming *implementation* of this specification; governed entirely by this document. |
| **Requirement Normalization (future)** | A downstream consumer; must never receive output that has not passed this gate. |
| **CP1 Validation (future)** | A downstream quality gate; operates only on already-validated output. |
| **Feature Generation (future)** | A downstream consumer; depends on validated requirements as input. |
| **Test Generation (future)** | A downstream consumer; depends on validated, feature-level input. |
| **Validation Canonical Models (future)** | Define the implementation-independent validation information model — the conceptual shape of issues, results, and severities. This document governs validation *philosophy*; the canonical models define the validation *information model*. A Response Validator implementation must conform to **both**. |

> **Architectural Decision**
> Responsibilities are split between two governing artifacts. The **Response
> Validation Architecture** (this document) governs *why* and *whether* output is
> trustworthy — the philosophy, principles, boundary, and verdict semantics. The
> **Validation Canonical Models** govern *what shape* the validation information
> takes — the implementation-independent model of issues and results. Neither
> supersedes the other; a conforming validator satisfies both simultaneously.

### 12.1 Dependency diagram

```text
        [AI Reasoning Contract]        [Prompt Framework]
                  │ defines trust            │ shapes request
                  ▼                          ▼
        [Requirement Analysis Service] ──► raw Analysis Result (LLMResponse)
                  │  (via Execution Package)
                  ▼
        [Response Normalization Contract] ──► Response Normalization Layer
                  │ creates the Normalization Result ONCE
                  │ (ParsedResponse + observations; no validation/repair)
                  ▼
        ┌─────────────────────────────────────────────┐
        │        RESPONSE VALIDATION LAYER             │  ◄── mandatory
        │   transport · syntax · schema · structure    │      quality gate
        │   content · evidence · traceability ·        │   reads the Normalization Result
        │   reasoning · business rules                 │ ◄─ never normalizes ──┐
        └───────────────────┬─────────────────────────┘                       │
                            │ PASSED / PASSED_WITH_WARNINGS only  [Validation Canonical
                            │                                      Models — ParsedResponse
                            │                                      + issue/result models]
                            │                                     defines the validation
                            │                                     information model
                            ▼
        ┌─────────────────────────────────────────────┐
        │       Downstream engineering (future)        │
        │  normalisation ─► CP1 ─► feature gen ─►       │
        │  test gen ─► output writing                  │
        └─────────────────────────────────────────────┘
                            │
                            ▼
                     [Human Governance]
```

---

## 13. Validation Contract Evolution

The behaviour this document governs is exposed to the rest of the platform as a
**Validation Contract**: the verdict states, the severity model, the categories,
the pipeline, and the issue and result models that downstream consumers rely on.
That contract is a **governed interface**, not an implementation detail. It must
evolve, but it must evolve *slowly and predictably*, because everything
downstream is built on the guarantees it makes today.

### 13.1 The Validation Contract is a governed interface

> **Principle**
> The Validation Contract is a governed interface. Every downstream consumer —
> normalisation, CP1, feature generation, test generation, output writing — codes
> against its verdict states, severities, and result shape. A change that alters
> those guarantees changes the behaviour of everything downstream, even if no
> downstream document is touched.

Two properties must be preserved across evolution:

- **Determinism must survive change.** Whenever possible, a contract change must
  not alter the verdict an existing, unchanged response would receive. A change
  that silently flips a previously `PASSED` response to `FAILED` is a breaking
  change and must be versioned and communicated as one.
- **Stability is a feature.** Consumers depend on the contract *not* changing
  under them. The default posture is conservatism: a change is admitted only when
  its value clearly outweighs the cost of disturbing every consumer.

### 13.2 Compatibility matrix

The following matrix classifies each kind of contract change by the version
increment it requires. *Backward compatible* changes are additive and safe for
existing consumers. *Minor version* changes extend behaviour without breaking
existing verdicts. *Major version* changes alter guarantees and require explicit
consumer migration.

| Change | Compatibility |
| ------ | ------------- |
| **Add optional field** | Backward Compatible |
| **Add required field** | Major Version |
| **Remove field** | Major Version |
| **Rename field** | Major Version |
| **Add validation rule** | Minor Version — *unless it changes blocking behaviour*, in which case Major Version |
| **Remove validation rule** | Major Version |
| **Change severity** (of an existing issue) | Major Version |
| **Add validation category** | Minor Version — *unless execution order changes*, in which case Major Version |
| **Add validation layer** | Minor Version — *unless downstream behaviour changes*, in which case Major Version |
| **Change validation philosophy** | Major Version |

> **Architectural Decision**
> The deciding question for every change is: *could this alter the verdict an
> existing, unchanged response receives, or the shape a consumer already depends
> on?* If yes, it is a **Major Version**. Adding a rule that only ever raises
> `INFO`/`WARNING` is minor; adding one that can raise `ERROR`/`CRITICAL` changes
> blocking behaviour and is therefore major. Severity changes are *always* major
> because severity drives the verdict (§6).

### 13.3 Why validation contracts evolve slowly

- **Downstream consumers depend on stability.** Every capability after the gate
  treats `PASSED`/`PASSED_WITH_WARNINGS` as a precondition. If that boundary
  shifts unpredictably, downstream behaviour becomes unpredictable too.
- **Determinism is a long-lived guarantee.** Re-validating an archived response
  must still reproduce its original verdict (§3.4). Frequent, breaking contract
  changes would erode the reproducibility that makes audit and regression
  analysis possible.
- **The gate is load-bearing.** Because it is the single boundary between
  generated and trusted content (§9, §14), instability here is felt everywhere.
  Slow evolution is not timidity; it is the discipline that keeps the whole
  pipeline governable.

### 13.4 Validation Contract Version vs Validator Version

The platform tracks **two distinct versions** for validation, governing two
distinct concerns. Conflating them would make it impossible to tell a change in
*meaning* from a change in *mechanism*.

| Version | Governs | Changes when… |
| ------- | ------- | ------------- |
| **Validation Contract Version** | The **semantics** of validation: validation categories, the severity model, the validation pipeline, the validation result model, and the validation issue model | The *meaning* of validation changes — a new category, a severity reassignment, a new verdict guarantee (per the matrix in §13.2) |
| **Validator Version** | The **implementation** only: how the validation is carried out | The implementation changes — a performance improvement, a refactor, a defect fix — with no change to validation meaning |

> **Architectural Decision**
> The **Validation Contract Version governs semantics; the Validator Version
> governs implementation.** Two validators with the same Validation Contract
> Version must produce the same verdict for the same response, even if their
> Validator Versions differ. Conversely, the Validator Version may advance freely
> — for performance or defect repair — without ever changing a verdict, and such
> advances require no Architecture Decision Record. This separation is what lets
> the implementation improve continuously while the contract stays stable.

#### 13.4.1 The four-version provenance

Every validated output is governed by four independent versions. Together they
make any verdict fully reproducible and any change precisely attributable.

| Version | Governs | Example |
| ------- | ------- | ------- |
| **Prompt Version** | How the request was worded | `v1.4.0` |
| **Reasoning Contract Version** | How the AI was required to think | `v2.0` |
| **Validation Contract Version** | What validation *means* — categories, severity, pipeline, result/issue models | `v1.1` |
| **Validator Version** | How validation was *implemented* | `v3.7.2` |

> **Principle**
> All four versions are required because each isolates a different source of
> change. A shift in output behaviour can then be attributed precisely: to the
> prompt, to the reasoning rules, to the *meaning* of validation, or to the
> *mechanism* of validation. Without the Validation Contract / Validator split, a
> verdict change could not be told apart from a mere implementation change — and
> the gate would lose its auditability. Both versions accompany every validation
> result alongside its observability signals (§11).

---

## 14. Future Evolution

The layer is designed to be **extended, never bypassed**. Each capability below
slots into the existing framework as an additional concern or strategy.

| Future capability | Intent | Constraint under this document |
| ----------------- | ------ | ------------------------------ |
| **Formal schema validation** | Validate against a published, versioned schema definition | A stronger Schema layer; same verdict model |
| **Semantic validation** | Assess meaning-level coherence beyond structure | A richer Reasoning layer; must remain deterministic |
| **Hallucination detection** | Detect unsupported assertions more deeply | Extends Evidence validation; never relaxes it |
| **Cross-provider validation** | Compare responses across providers | Must remain provider-independent (§3.8) |
| **Multiple validator pipeline** | Chain specialised validators | New layers added to the framework, not around it |
| **Repair strategies** | Propose corrected output | Operates *outside* the layer; never mutates the original (§3.3) |
| **Self-healing** | Automatically remediate certain failures | A downstream capability; the gate's verdict still stands |
| **Rule plug-ins** | Add declarative validation rules | Extend Business Rule validation; same severity model |
| **Policy engine** | Externalise verdict policies | Configures the framework; does not replace it |

> **Architectural Decision**
> **Future capabilities must extend the validation framework. They must not
> replace it.** Every new capability is an additional layer, strategy, or rule
> within the structure defined here — bound by the same principles, the same
> severity model, the same boundary, and the same verdict states. A capability
> that bypasses the gate, mutates the original response, introduces
> non-determinism, or crosses the validation boundary is non-conforming and must
> not ship.

### 14.1 Evidence Quality Assessment

Today, the Evidence Validation layer (§4, §5) asks a binary question: *does the
required evidence reference exist?* A conclusion with a present reference passes;
one with an empty or dangling reference fails. This is **Evidence Exists**
validation, and it is the whole of the current scope.

A future Validation Contract Version may evolve this layer from *Evidence Exists*
toward **Evidence Quality** — assessing not merely the presence of evidence but
its strength. The concepts such an extension might introduce include:

| Future evidence concept | Meaning |
| ----------------------- | ------- |
| **Strong Evidence** | A conclusion grounded in direct, authoritative, corroborated references |
| **Weak Evidence** | A conclusion grounded only in sparse, indirect, or single-source references |
| **Missing Evidence** | A conclusion presented with no supporting reference at all |
| **Conflicting Evidence** | A conclusion supported by references that contradict one another |
| **Derived Evidence** | A conclusion grounded in correlation across references rather than any single source |

> **Architectural Decision**
> **Evidence Quality Assessment is outside the current validation scope.** It is
> recorded here as a future extension of the Evidence Validation layer, not as a
> present capability. Any such extension is bound by every rule in this document:
> it must remain deterministic (§3.4), must not modify the response (§3.3), must
> express its findings through the existing severity and result models (§6, §8),
> and — because it would change what evidence validation *means* — must advance
> the Validation Contract Version as a Major Version change (§13.2). It mirrors
> the AI Reasoning Contract's Evidence Hierarchy, but as *validation* of evidence
> strength rather than *reasoning* over it.

---

## 15. Architecture Principles Summary

The philosophy of the Response Validation Layer, distilled:

| # | Principle | One-line meaning |
| - | --------- | ---------------- |
| 1 | **Validation is a quality gate, not a formatter.** | It judges trustworthiness; it never edits output. |
| 2 | **One concern per layer.** | Each layer validates exactly one thing, in order. |
| 3 | **Fail fast on foundations.** | Unparseable or non-conformant input stops progression. |
| 4 | **Explain every failure.** | Every issue is precise, located, and actionable. |
| 5 | **Evidence before confidence.** | Fluency is never a substitute for groundedness. |
| 6 | **Deterministic by mandate.** | The same response always yields the same verdict. |
| 7 | **Respect the boundary.** | Form and completeness are validated; correctness and approval are not. |
| 8 | **Provider- and architecture-independent.** | The verdict depends on the response, not its origin or stack. |
| 9 | **Observable by design.** | Every run is measurable, traceable, and auditable. |
| 10 | **Human governance is supreme.** | The verdict informs human decision; it never overrides it. |
| 11 | **Rules are order-independent.** | Within a layer, rules are deterministic, share no state, and may run in any order or in parallel. |

### 15.1 Layered architecture position

```text
   ┌──────────────────────────────────────────────────────────────┐
   │                     AI Generation Layer                       │
   │        (Requirement Analysis Service · providers)             │
   └───────────────────────────┬──────────────────────────────────┘
                               │ LLMResponse (raw, un-validated)
                               ▼
   ┌──────────────────────────────────────────────────────────────┐
   │              Response Normalization Layer                     │
   │   creates the Normalization Result ONCE · no validation/repair │
   └───────────────────────────┬──────────────────────────────────┘
                               │ Normalization Result
                               │ (ParsedResponse — canonical, format-neutral
                               │  structure — + Normalization Observations)
                               ▼
   ╔══════════════════════════════════════════════════════════════╗
   ║              RESPONSE VALIDATION LAYER                        ║
   ║                                                              ║
   ║   transport → syntax → schema → structure → content →        ║
   ║   evidence → traceability → reasoning → business rules        ║
   ║                                                              ║
   ║        PASSED · PASSED_WITH_WARNINGS · FAILED · BLOCKED       ║
   ╚═══════════════════════════════╤══════════════════════════════╝
                                   │ trusted output only
                                   ▼
   ┌──────────────────────────────────────────────────────────────┐
   │            Downstream Engineering Capabilities                │
   │  normalisation · CP1 · feature gen · test gen · output        │
   └───────────────────────────┬──────────────────────────────────┘
                               ▼
                        Human Governance
```

> **Architectural Decision**
> **The Response Validation Layer is the exclusive quality gate between AI
> generation and downstream engineering.** It is the single boundary at which
> generated content becomes trusted content.

> **Definition of Done**
> **No downstream component shall consume AI output without successful
> validation.** This document is the governing specification for every Response
> Validator implementation within the Autonomous Test Engineering Platform. It
> defines the philosophy, principles, responsibilities, boundaries, severity
> model, validation pipeline, issue and result models, observability, and future
> evolution of the layer. It is implementation-independent and remains valid even
> if the platform is reimplemented on an entirely different technology stack or
> driven by an entirely different AI provider.

---

> **Architectural Decision — Architecture Freeze**
> With this refinement, this document becomes the **governing architecture
> specification for all Response Validator implementations**. Future
> implementations may *extend* the validation framework, but they must not
> violate:
>
> - the **Validation Boundary** (§9),
> - the **Validation Philosophy** (§4),
> - the **Guiding Principles** (§3),
> - the **Severity Model** (§6),
> - the **Validation Result Model** (§8),
> - **Human Governance** (§3.10),
> - **Provider Independence** (§3.8), and
> - **Deterministic Validation** (§3.4).
>
> **Architecture changes require an Architecture Decision Record (ADR).**
> Implementation changes do not. A change to validation *semantics* — categories,
> severity, pipeline, result or issue models, or any boundary or principle above —
> advances the Validation Contract Version (§13) and is admissible only through an
> ADR. A change to validation *mechanism* advances only the Validator Version
> (§13.4) and proceeds without one. The frozen architecture is the contract; the
> implementation beneath it remains free to improve.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Validation** | The act of judging whether an AI response is trustworthy enough to be consumed downstream. |
| **Validation Issue** | A single, precise, explainable finding raised by a validation layer (§7). |
| **Validation Result** | The aggregate verdict over all issues, in one of four states, preserving the original response (§8). |
| **Evidence** | The references that ground a conclusion in source artifacts, required for trustworthiness (cf. AI Reasoning Contract). |
| **Schema** | The expected, versioned shape a response must conform to. |
| **Response Normalization Layer** | The permanent, independent platform subsystem that turns the `LLMResponse` into the canonical `ParsedResponse` exactly once, before validation; it performs no validation, repair, interpretation, enrichment, filtering, mutation, or business transformation (§4.4; Response Normalization Contract). |
| **ParsedResponse** | The canonical, provider- and format-independent normalized structure of the response; a Shared Platform Artifact consumed by every validation layer (Syntax reads its outcome, every later layer reads its structure) and by every other platform consumer (§4.4; Validation Canonical Models §8). |
| **Normalization Outcome** | A normalized, provider-independent fact — `NORMALIZED` or `MALFORMED` — that the Syntax layer judges; it is a fact, never a verdict (§4.4; Response Normalization Contract §9). |
| **Normalization Result** | The aggregate produced by the Response Normalization Layer: it owns the `ParsedResponse` together with the Normalization Observations, statistics, framework metadata, and execution context. Validation consumes it and reads the `ParsedResponse` together with the observations (§4.4; Response Normalization Contract §8). |
| **Normalization Observation** | A recorded, un-judged fact aggregated by the `NormalizationResult` (e.g. a duplicate identifier, an encoding observation) — never carried on the `ParsedResponse`; it carries no severity or verdict and is never a `ValidationIssue` until a rule decides to raise one (§4.4; Response Normalization Contract §8, §10). |
| **Shared Platform Artifact** | An artifact produced once and shared read-only across the whole platform; `ParsedResponse` is one — validation is its first consumer, not its owner (Response Normalization Contract §7). |
| **Normalization Contract Version** | The version governing normalization *semantics and governance*, independent of the Validation Contract Version (Response Normalization Contract §12). |
| **ParsedResponse Version** | The version governing the *additive shape* of the `ParsedResponse` representation, independent of normalization semantics (Response Normalization Contract §12). |
| **Traceability** | The linkage that lets each output element be traced back to its source and execution context. |
| **Severity** | The degree to which an issue threatens trustworthiness: INFO, WARNING, ERROR, or CRITICAL (§6). |
| **Business Rule** | A declared, platform-level structural rule the response must satisfy — not a domain-correctness judgement. |
| **Quality Gate** | A mandatory boundary that output must pass before it may be consumed; this layer is that gate. |
| **Determinism** | The property that the same response and schema always yield the same verdict (§3.4). |
| **Validation Contract** | The governed interface this document exposes: verdict states, severity model, categories, pipeline, and issue/result models (§13). |
| **Validation Contract Version** | The version governing validation *semantics* — categories, severity, pipeline, result and issue models (§13.4). |
| **Validator Version** | The version governing validation *implementation* only, independent of semantics (§13.4). |
| **Rule Independence** | The property that rules within a layer are deterministic, share no state, and produce the same result in any execution order (§3.11). |
| **Validation Canonical Models** | The future, implementation-independent information model of validation issues and results, which a validator must also conform to (§12). |

## Appendix B — Architecture Conformance Checklist

A Response Validator implementation conforms to this architecture only if every
box can be checked:

- [ ] Validation remains provider-independent (no provider, model, or vendor influences the verdict).
- [ ] Validation never modifies the AI output.
- [ ] Validation preserves the original response unchanged through to the result.
- [ ] Validation explains every failure with category, location, reason, and recommendation.
- [ ] Validation is deterministic — the same response and schema yield the same verdict every time.
- [ ] Validation layers each assess exactly one concern, in the defined order.
- [ ] Foundational failures (transport, syntax, schema, structure) stop progression (Fail Fast).
- [ ] Severity is assigned by the nature of the defect and drives the verdict via the decision matrix.
- [ ] Validation boundaries are respected — no correctness, approval, prioritisation, feasibility, or release judgement.
- [ ] Validation remains independent of downstream components and judges nothing on their behalf.
- [ ] Validation results are observable (duration, issue counts, severity distribution, categories, schema version, validation contract version, validator version, correlation).
- [ ] Human governance is preserved — every automated verdict can be reviewed and overridden.
- [ ] No downstream component consumes AI output that has not passed this gate.
- [ ] Rules within a layer are order-independent, mutate no shared state, and are parallelisable.
- [ ] Validation semantics and validation implementation are versioned separately (Validation Contract Version and Validator Version).
- [ ] Contract changes follow the compatibility matrix and are admitted only through an ADR.
- [ ] The implementation conforms to both this architecture and the Validation Canonical Models.
