# Validation Rule Implementation Contract

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Rule Implementation Pattern |
| Status               | Approved — Foundational — **FROZEN**                              |
| Scope                | The **engineering structure** every concrete validation rule — of every layer (Syntax, Schema, Structural, Content, Evidence, Traceability, Reasoning, Business Rule) — must conform to: its lifecycle, single concern, permitted inputs and outputs, facts-vs-exception discipline, independence, metadata discipline, dependency-injection philosophy, and evolution |
| Governs              | Rule lifecycle · single concern · input discipline · output discipline · facts-vs-exceptions · rule independence · metadata discipline · dependency-injection philosophy · the engineering + conformance checklists · the frozen engineering patterns |
| Complements          | Validation Rule Catalog (governs *which* rules exist and *what* each validates) · Validation Rule Development Guide (the Python operationalization of this contract) — it **replaces neither** |
| Depends on           | Validation Rule Catalog · AI Response Validation Architecture · Validation Canonical Models (`ValidationIssue`, `ValidationInput`) · Response Validator Architecture · ADR-0003 · Validation Framework (`ValidationRule` contract) |
| Audience             | Lead Engineers · Platform Engineers · Technical Architects · QA Architects · Reviewers |
| Implementation-bound | No — valid regardless of language, framework, serialization format, algorithm, or AI provider |

> **Architectural Decision**
> This contract captures the **engineering structure** that emerged from four
> completed, independent rule implementations — `TRANSPORT-0001` … `TRANSPORT-0004`
> — and freezes it as the template every present and future validation rule must
> follow. It is **not** an architecture redesign. The Validation Rule Catalog, the
> Validation Framework, the `ValidationRule` contract, the Validation Canonical
> Models, ADR-0003, and the `ValidationInput` are already frozen and are
> **unchanged** by this document. This contract adds one thing those documents
> deliberately left to engineering: the **repeatable shape of a conforming rule
> implementation**. It is the validation-layer analogue of the frozen
> **Normalization Stage Implementation Contract**.

---

## 1. Purpose

### 1.1 Why this contract exists

The frozen architecture answers, permanently, *which* validation rules exist,
*what single concern* each owns, *which layer* it belongs to, and *what severity
and blocking* it carries (Validation Rule Catalog); *how* the framework registers
and runs rules (Validation Framework); *what a finding is* (Validation Canonical
Models); and *what the canonical input is* (`ValidationInput`, ADR-0003). What
those documents intentionally do **not** answer is the recurring engineering
question a rule author faces:

> *"Given the frozen architecture, what is the concrete, repeatable structure a
> conforming rule implementation must take — so that every rule, in every layer,
> looks, behaves, and fails the same way?"*

Four Transport rules have now been built — and, under ADR-0003, migrated — to the
same structure. That structure is no longer a guess; it is a **proven pattern**.
This contract records it so that `SYNTAX-0001` and every future
`<LAYER>-NNNN` rule is implemented **identically in structure**, reviewed against
a single checklist, and never re-negotiated per rule or per layer.

### 1.2 What this contract governs — and what it does not

| This contract governs | This contract does **not** govern |
| --------------------- | --------------------------------- |
| The **engineering structure** of a rule: lifecycle, single concern, input/output discipline, facts-vs-exceptions, independence, metadata discipline, dependency philosophy. | **What** a rule validates — its concern, layer, severity, blocking, identity, and number allocation (Validation Rule Catalog). |
| The permanent patterns every rule instantiates. | **How** the rule is written in a specific language — subclassing, files, typing, tests, tooling, docstrings (Validation Rule Development Guide). |
| The rules a reviewer certifies a rule against, independent of technology. | Pipeline orchestration, profile selection, result assembly (Framework · Response Validator). |

> **Principle**
> The Catalog governs **what exists**. This contract governs **how a rule is
> structured**. The Development Guide governs **how that structure is written in
> code**. Three tiers, one direction, no overlap.

### 1.3 Where this contract sits

```text
   [Validation Rule Catalog]        WHICH rules exist · concern · layer · severity · blocking
            │
            ▼
   [Validation Rule Implementation Contract]  ◄── THIS DOCUMENT (the engineering structure)
            │  (implementation-independent; the same philosophy as the
            │   Normalization Stage Implementation Contract)
            ▼
   [Validation Rule Development Guide]  the Python operationalization of this contract
            │
            ▼
   conforming rule implementations (TRANSPORT-0001…0004 today; SYNTAX-0001 next)
```

| Artifact | Relationship to this contract |
| -------- | ----------------------------- |
| **Validation Rule Catalog** | The single authority for a rule's identity, concern, layer, severity, and blocking. This contract governs *how* a rule realises its catalog entry; it never redefines identity, concern, layer, severity, or blocking. |
| **AI Response Validation Architecture** | Supplies the binding philosophy every rule obeys — Deterministic Validation (§3.4), Preserve Original Response (§3.3), Rule Independence (§3.11), Explain Every Failure (§3.6). This contract turns that philosophy into an implementation structure; it never alters it. |
| **Validation Canonical Models** | Define what a `ValidationIssue` is and what the `ValidationInput` holds. This contract governs the discipline of *reading* the input and *producing* issues; it never redefines either model. |
| **`ValidationInput` (ADR-0003)** | The immutable, execution-scoped input every rule receives. This contract governs how a rule reads it; it never changes its shape or ownership. |
| **Validation Framework (`ValidationRule`)** | The abstract contract (`metadata`, `validate`) this structure is realised through. This contract is the implementation-facing elaboration of that contract; it adds no method and changes no signature. |
| **Validation Rule Development Guide** | The Python realization of this contract. Where the two appear to differ, this contract (architecture) is the source of truth and the guide is corrected. |

> **Architectural Decision — this contract adds a pattern, not a power.** It grants
> no rule any new concern, input, output, dependency, or authority. Every rule here
> is a consequence of a frozen upstream decision, expressed as an implementation
> obligation. A conflict between this contract and any frozen document is resolved
> in favour of the frozen document, through an ADR — never silently here (§14).

---

## 2. Rule Lifecycle

A rule passes through the same phases in every validation run. The phases are the
same for every rule, in every layer; only the one owned concern differs.

```text
   Construct once   a rule is constructed once, with its immutable identity and any
                    injected mechanism it needs; construction validates its wiring.
        │
        ▼
   Receive input    the pipeline invokes the rule, handing it the immutable,
                    read-only ValidationInput for one execution.
        │
        ▼
   Produce findings the rule evaluates its one concern and produces a list of
                    ValidationIssue findings (empty when the concern is satisfied).
        │
        ▼
   Return           the rule returns the list and nothing else; it signals success
                    by returning an empty list, not by any other channel.
        │
        ▼
   Reusable         the rule retains no per-execution state; the same instance
                    evaluates any number of executions identically.
```

### 2.1 Construct once

A rule is **constructed once** and is **reusable across executions**. Construction
establishes the rule's immutable identity (§8) and injects any collaborator the
rule genuinely needs (§9). Construction **validates its own wiring**: a
collaborator of the wrong kind fails construction as an **infrastructure/wiring
failure**, never a validation finding. A rule holds no per-execution state, so the
same instance runs any number of executions identically.

### 2.2 Receive input

The rule is invoked **once per execution** by the pipeline, which hands it the
immutable `ValidationInput` (ADR-0003). A rule never invokes itself, never loops,
never retries, and never re-executes within one execution.

### 2.3 Produce findings

Within execution the rule performs its **one concern** and produces a **list of
`ValidationIssue`** — zero when the concern is satisfied, one per observed
occurrence otherwise. It reads only what its concern requires (§4) and produces
only findings it owns (§5).

### 2.4 Return

A rule completes by **returning its list of findings**. Success is signalled by an
empty list. This return-only surface is what keeps rules independent and the
framework the single assembler of results (§7).

### 2.5 Reusable

A rule keeps **no reference** to the `ValidationInput` and **no per-execution
state** after it returns. Nothing a rule produced during one execution survives
into another. Reusability is a structural property, not an optimisation.

> **Architectural Decision — no execution state, ever.** A rule that cached the
> input, accumulated findings between calls, or memoised a verdict would break
> Determinism (§3.4) and Rule Independence (§3.11) and could not be parallelised.
> The lifecycle is frozen precisely so that "construct once, run many, remember
> nothing" holds for every rule.

---

## 3. Single Concern

> **Principle**
> **Exactly one rule owns exactly one validation concern — and only one.** A rule
> that checks two things is two rules (Validation Rule Catalog §3). A concern
> checked by two rules is a duplicated responsibility and a defect in the catalog.

Every rule **MUST**:

| # | Responsibility | Meaning |
| - | -------------- | ------- |
| 1 | **Own exactly one concern** | The single concern assigned to its catalog entry — never a second, never a share of another's. |
| 2 | **Read only what its concern requires** | Read only the parts of the `ValidationInput` its concern needs — never more. |
| 3 | **Produce only findings it owns** | Emit issues for its concern only; never annotate or extend another rule's finding. |
| 4 | **Defer, never duplicate** | When the datum a *sibling* rule owns is absent, the rule returns no findings for that absence rather than re-reporting a concern another rule owns. |

A rule **MUST NEVER**:

| The rule never… | Because that belongs to |
| ---------------- | ----------------------- |
| **Normalize** — parse, recover, or re-derive structure | the Response Normalization Layer (structure is recovered once, before validation) |
| **Repair** — fix, complete, coerce, or "clean" the response | nothing — repair is forbidden platform-wide (Preserve Original Response, §3.3) |
| **Mutate the `ValidationInput`** — edit the response, the normalization result, or the parsed structure | nobody — the input is immutable and read-only |
| **Aggregate** — roll findings into a summary, verdict, or count | the pipeline (result assembly) |
| **Coordinate** — order, select, enable, or invoke other rules | the framework/pipeline |
| **Validate another rule's concern** — check what a sibling owns | that sibling rule |

> **Architectural Decision — the prohibitions are the boundary made concrete.**
> Each forbidden act would collapse a frozen boundary: normalizing or repairing
> crosses the Normalization–Validation line; mutating the input destroys the shared
> artifact every rule reads; aggregating or coordinating turns a rule into the
> pipeline; validating a sibling's concern duplicates ownership. A rule that does
> any of these is non-conforming by definition. **When a rule's responsibility can
> be described only with the word "and", it is too large and must be split**
> (Catalog §18).

---

## 4. Inputs

A rule receives **exactly one input**: the **`ValidationInput`** (ADR-0003) — the
immutable, execution-scoped binding of the analysed response and its
normalization output.

| Rule input discipline | Statement |
| --------------------- | --------- |
| **Exactly `ValidationInput`** | The one and only argument a rule evaluates. A rule reads no globals, no environment, no clock, no configuration, and no other rule. |
| **Read-only** | The input is observed, never modified — no field of the `ValidationInput`, the `AnalysisResult`, the `NormalizationResult`, or the `ParsedResponse` is altered (Preserve Original Response, §3.3). |
| **Never mutate** | A rule never edits, repairs, reshapes, or copy-and-alters the input. |
| **Never cache** | A rule never stores the input (or any part of it) on itself for reuse across executions. |
| **Never retain** | A rule holds no reference to the input after it returns. |

What each layer reads *through* the input is fixed by the frozen architecture (the
*vehicle* is this input; the *what* is the Catalog):

| Layer | Reads (through the `ValidationInput`) |
| ----- | ------------------------------------ |
| **Transport** | `analysis_result` — delivery-level facts (the `LLMResponse`, execution identity). |
| **Syntax** | the **Normalization Outcome** via `normalization_result.parsed_response`, and the **Normalization Observations** via `normalization_result`. |
| **Schema · Structural · Content · Evidence · Traceability · Reasoning · Business Rule** | the **normalized structure** via `normalization_result.parsed_response`. |

> **Principle**
> A rule **reads normalized facts; it never recovers them**. The transition from
> text to structure happened once, before the pipeline ran. Every rule reads the
> same shared `ParsedResponse` through the same `ValidationInput`; no rule parses,
> normalizes, or re-derives structure for itself — which is exactly what keeps rules
> independent (§7) and one-concern-per-layer intact.

---

## 5. Outputs

A rule produces **exactly one kind of output**: a **list of `ValidationIssue`**.

| Rule output discipline | Statement |
| ---------------------- | --------- |
| **Exactly a list of `ValidationIssue`** | The sole product of a rule. |
| **Empty list = success** | Returning an empty list means the rule observed nothing worth recording — the normal, common case. |
| **One issue per occurrence** | A rule may emit several issues if its single concern occurs several times, but every issue describes the *same* concern. |
| **Each issue is complete** | Every issue carries what makes it explainable and actionable — its category, severity, layer, location, message, evidence, recommendation, blocking indicator, and correlation (Explain Every Failure, §3.6; Canonical Models §3). |
| **Severity and blocking per issue** | Each issue carries the severity and blocking capability the Catalog assigns to the rule (Catalog §14, §15); these live on the *finding*, not on the rule's identity metadata (§8). |

A rule **MUST NEVER** return:

| The rule never returns | Because |
| ---------------------- | ------- |
| `None` | Absence of findings is an **empty list**, never a null. |
| a boolean | A rule reports findings, not a pass/fail flag. |
| a `ParsedResponse` or `NormalizationResult` | Those are inputs it reads, never products it emits. |
| a `ValidationResult`, summary, verdict, or statistics | Result assembly is the pipeline's job (Response Validator; Canonical Models §6). |
| pipeline state, execution context, or another rule's output | A rule knows none of these. |

> **Architectural Decision — the rule produces findings; the pipeline produces the
> result.** A rule's responsibility ends at returning its list of issues. It does
> not decide the verdict, roll up a summary, or know any downstream consumer. This
> one-directional flow is what keeps rules independent and the subsystem governable
> (Catalog §19).

---

## 6. Facts vs Exceptions

Validation produces **findings, not exceptions** for anything about the response.
The distinction mirrors the normalization philosophy exactly and is permanent and
absolute.

| Situation | Result |
| --------- | ------ |
| **The concern is violated** (invalid, missing, malformed, duplicated, unsupported, …) | A **`ValidationIssue`** (a finding), returned in the list. Never an exception. |
| **The concern is satisfied** | An **empty list**. Never an exception. |
| **Expected-absent data** (e.g. an optional element a sibling rule owns) | A finding or a pass per the catalog concern — **never** an exception. |
| **The rule's own mechanism fails unexpectedly** (a genuine, uninterpretable internal state) | A **`ValidationRuleError`** — an infrastructure failure the rule could not perform its work. |
| **The rule is wired incorrectly at construction** | A **wiring failure** (infrastructure), raised before any execution. |

The three consequences an author must internalise:

1. **An invalid response is not an exception.** It is a successful, finding-producing
   outcome: validation's job is to *record what is wrong*, and "the content is
   invalid" is a thing to record — as a `ValidationIssue`. Only an inability to
   *run* is exceptional.
2. **Infrastructure failures are exceptions.** A mechanism that fails unexpectedly,
   or a rule that cannot perform its work, raises `ValidationRuleError` — so an
   infrastructure failure never masquerades as a finding, and a finding never
   masquerades as a crash.
3. **The two families never mix.** Findings flow through the returned list;
   infrastructure and wiring failures flow as exceptions. Keeping them disjoint is
   what preserves the boundary: a broken run never disguises itself as a judgement
   about the response, and a judgement about the response never aborts the run.

> **Architectural Decision — never raise because the content is invalid.** This is
> the validation-side counterpart of the normalization rule that "`MALFORMED` is a
> fact, not an exception". A rule that raised on invalid content would make the
> verdict depend on control flow, break Determinism (§3.4), and rob Human
> Governance of an explainable finding. Invalid content is always a
> `ValidationIssue`; only infrastructure and wiring failures raise.

---

## 7. Rule Independence

> **This section is critical.** It is the property on which determinism, audit, and
> future parallelism all rest (Catalog §16; AI Response Validation §3.11).

Every rule must exhibit all of these simultaneously. A rule **never**:

| The rule never… | Meaning |
| ---------------- | ------- |
| **invokes another rule** | It calls, imports, or references no other rule. |
| **depends on execution order** | Its findings are identical under any permutation of the layer's rules; the only ordering it may rely on is the pipeline's *layer* ordering, never sibling *rule* order. |
| **reads another rule's output** | It never consumes, assumes, or waits on a sibling's findings. |
| **coordinates** | It never orders, selects, enables, disables, or sequences another rule. |
| **aggregates** | It never rolls findings up into a summary, verdict, or count. |
| **shares execution state** | It holds no mutable state and writes to no shared structure; one rule's execution never changes what another observes. |

And every rule is, positively:

| Property | Meaning |
| -------- | ------- |
| **Deterministic** | Same `ValidationInput` ⇒ same findings, every time. |
| **Stateless** | No memory between evaluations; it depends only on the input before it. |
| **Idempotent** | Evaluating twice on the same input yields the same result, with no cumulative effect. |
| **Independent** | It depends on no other rule's output or existence. |
| **Parallelizable** | Sharing no state and observing no sibling, it may be evaluated concurrently. |
| **Non-mutating** | It reads the input; it never alters it. |

> **Architectural Decision — Rule Independence is non-negotiable.** A rule that
> depends on execution order, shares mutable state, coordinates a sibling, or
> mutates the input is non-conforming and must not be catalogued or shipped.
> Independence is what lets the framework reorder or parallelise rule evaluation in
> future without changing a single verdict.

---

## 8. Metadata

Every rule carries a single **immutable identity**. Identity is *declared* by the
rule and *governed* by the Catalog — the metadata never invents identity, it only
surfaces the catalog-assigned identity at runtime.

| Identity field | Meaning |
| -------------- | ------- |
| **Rule ID** | The permanent `<LAYER>-NNNN` identifier from the Catalog; never renumbered, reused, or reassigned. |
| **Rule Name** | The concern-describing name from the Catalog; may be refined without changing identity. |
| **Validation Layer** | The one layer the rule belongs to. |
| **Rule Version** | The version of *this rule's* own definition. |
| **Enabled state** | A **descriptive** flag stating whether the rule participates; it does not self-activate (§8.1). |
| **Reserved extension points** | Behaviourless fields (e.g. classification labels, targeted contract version) so identity can grow without a breaking change. |

Severity and blocking are **not** identity metadata — they are decided **per
finding**, on each `ValidationIssue` the rule emits (§5), exactly as the Catalog
assigns them. Identity is *who the rule is*; severity/blocking are *what a specific
finding means*.

### 8.1 Metadata is descriptive — it never drives execution

Metadata exists to make a rule **observable and auditable**: so a validation run
can be traced to the exact rules, versions, and layers that produced it. It is
*runtime identity*, not *governing architecture*, and it deliberately **does not
control execution**:

- **Layer does not sort.** The pipeline executes rules in the
  architecture-mandated layer order; it never reads a rule's declared layer to
  reorder. Declared layer *describes* position; it never *produces* it.
- **Enabled does not self-activate.** A rule does not switch itself on or off.
  *Participation* is an orchestration concern governed by profiles (Response
  Validator §6); the flag describes a decision made elsewhere, it does not make it.

> **Architectural Decision — identity is descriptive; execution is coordinated.**
> Separating *what a rule says it is* from *how the run is driven* is what lets the
> layer order be governed in one place while a rule's identity stays a passive,
> immutable fact safe to stamp into a result. If metadata drove execution, a
> mis-declared field could silently reorder or disable a rule.

---

## 9. Dependency Injection

A rule receives its collaborators by **injection**, never by internal
construction, discovery, global lookup, or reflection. Two rules govern *whether* a
rule has an injected collaborator:

- **Inject a mechanism that genuinely varies.** When a rule's concern has an
  implementation *mechanism* that can legitimately differ — for example, an
  expected-shape definition a Schema rule checks against, a policy threshold a
  Business Rule rule enforces, or a comparison strategy a Content rule applies —
  that mechanism is injected behind a stable seam, so the rule stays deterministic
  and provider/format-independent and new mechanisms are added without changing the
  rule.
- **Do not inject a mechanism that does not vary.** When a rule's logic is fixed
  and governed, the rule takes **no** collaborator. Injecting something that cannot
  differ would be a speculative abstraction, not a dependency.

Never inject — these are not dependencies:

| Never injected | Why |
| -------------- | --- |
| **Constants** | A fixed value is part of the rule's definition, not a varying mechanism. |
| **Policies as plain values / fixed algorithms** | If it cannot legitimately differ, it is not a dependency. |
| **Versions** | Version identity is metadata (§8), not an injected collaborator. |
| **Metadata** | Identity is declared, not injected. |
| **Other rules, the pipeline, the registry, or the result** | A rule depends on none of these (§7). |

Construction **validates the rule's wiring**: a mis-typed or missing collaborator
fails at construction as an infrastructure/wiring error (§6), before any execution.

> **Architectural Decision — inject variation, not ceremony.** Dependency injection
> exists to isolate the parts that can legitimately differ, not to wrap every rule
> in a collaborator for symmetry. The four Transport rules prove the fixed-logic
> side: each takes **no** collaborator because its rule cannot vary. A future rule
> chooses by the same test — *does a real mechanism vary?* — never by imitation.

---

## 10. Engineering Checklist

Every rule implementation must satisfy all of the following before it is
considered complete:

- [ ] The rule realises **exactly one** catalog concern and blends no other (§3).
- [ ] The rule is **constructed once** and is **reusable**, holding no per-execution
      state (§2).
- [ ] The rule reads **only** the `ValidationInput`, **read-only**, and reads only
      what its concern requires (§4).
- [ ] The rule **never** normalizes, repairs, mutates, aggregates, coordinates, or
      validates another rule's concern (§3).
- [ ] The rule returns **exactly** a list of `ValidationIssue`; an **empty list**
      means success (§5).
- [ ] The rule returns **no** `None`, boolean, `ParsedResponse`,
      `NormalizationResult`, `ValidationResult`, verdict, or pipeline state (§5).
- [ ] Each issue is **complete** (category, severity, layer, location, message,
      evidence, recommendation, blocking, correlation) and carries the **Catalog's**
      severity and blocking (§5).
- [ ] The rule **records invalid content as a finding** and **raises only** for an
      infrastructure or wiring failure (§6).
- [ ] The rule is **deterministic, stateless, idempotent, independent,
      parallelizable, and non-mutating** (§7).
- [ ] The rule **defers, never duplicates** a concern a sibling rule owns (§3).
- [ ] The rule carries a **single immutable identity** and reads all identity from
      it; identity is **descriptive** and never drives execution (§8).
- [ ] The rule **injects a collaborator only where a real mechanism varies**;
      otherwise it takes none, and construction validates its wiring (§9).
- [ ] The rule communicates **only** through its returned findings — no hidden
      coupling, no side effects, no shared state (§5, §7).

---

## 11. Conformance Checklist (for reviewers)

A reviewer can certify a rule against this contract only if every box can be
checked:

- [ ] **Catalogued first** — the Rule ID, layer, concern, severity, and blocking
      exist in the Catalog before implementation (Catalog §22).
- [ ] **Single concern** — one concern, no "and" (§3).
- [ ] **Lifecycle** — construct once, reusable, no execution state (§2).
- [ ] **Input discipline** — `ValidationInput` only, read-only, never mutated,
      cached, or retained (§4).
- [ ] **Reads normalized facts, never recovers them** — no parsing or normalization
      in a rule (§4).
- [ ] **Output discipline** — a list of `ValidationIssue` only; empty = success;
      never `None`/verdict/result/state (§5).
- [ ] **Explainable findings** — every issue states what/where/why and how to
      resolve, with the Catalog's severity and blocking (§5).
- [ ] **Facts, not exceptions** — invalid content is a finding; only
      infrastructure/wiring failures raise (§6).
- [ ] **Independent** — no rule-to-rule invocation, order dependence,
      coordination, aggregation, or shared state (§7).
- [ ] **Deterministic & non-mutating** — same input, same findings; input never
      altered (§7).
- [ ] **Immutable identity** — a single frozen identity, read-only, non-executing;
      metadata does not drive execution (§8).
- [ ] **Principled injection** — a collaborator only where a mechanism varies;
      wiring validated at construction (§9).
- [ ] **No hidden coupling** — the rule communicates only through its returned
      findings (§5, §7).
- [ ] Any architectural change to the above is made through an approved **ADR**
      (§14).

---

## 12. Future Extensibility

The rule set grows **additively**, exactly as the Catalog grows (Catalog §9.10,
§23). Every future layer instantiates this contract **without modification**:

| Future layer | Instantiates this contract by… |
| ------------ | ------------------------------ |
| **Schema** | reading the normalized structure from the `ParsedResponse`; one concern per rule (required sections, field types, enumerations, required collections); optionally injecting an expected-shape mechanism (§9). |
| **Structural** | reading container/relationship presence from the normalized structure; one concern per rule. |
| **Content** | reading field-level values from the normalized structure; one concern per rule; optionally injecting a comparison mechanism. |
| **Evidence** | reading evidence-reference presence from the normalized structure; one concern per rule. |
| **Traceability** | reading trace-link presence from the normalized structure; one concern per rule. |
| **Reasoning** | reading cross-element coherence from the normalized structure; one concern per rule. |
| **Business Rule** | reading declared platform-policy satisfaction from the normalized structure; one concern per rule; optionally injecting a policy/threshold mechanism (§9). |

> **Architectural Decision — the pattern is the extension mechanism.** Because every
> rule has the same structure, a new rule — in any layer — is added by
> *instantiating this contract*, not by inventing a new structure. A rule that
> normalized, repaired, mutated the input, aggregated, coordinated, raised on
> invalid content, or carried execution state is non-conforming regardless of its
> layer or number. No layer needs a bespoke engineering pattern; each needs only its
> catalogued concerns.

---

## 13. Engineering Patterns Discovered (frozen)

These are the reusable engineering patterns **proven by** `TRANSPORT-0001` …
`TRANSPORT-0004` (including their ADR-0003 migration) and frozen by this contract.
None is invented; each is captured from the four completed implementations.

| # | Frozen pattern | What it means |
| - | -------------- | ------------- |
| 1 | **Immutable identity, constructed once, shared** | A single frozen identity per rule, fixed at construction and reused for every execution, safe to stamp into a result. |
| 2 | **Identity metadata is descriptive** | Identity carries no severity/blocking and never drives execution; severity and blocking live on each finding. |
| 3 | **`ValidationInput`-only input** | The rule evaluates exactly one immutable, read-only input and nothing else (ADR-0003). |
| 4 | **Read normalized facts, never recover them** | The rule reads the shared `ParsedResponse`/observations through the input; it never parses or normalizes. |
| 5 | **`ValidationIssue`-only output** | The rule returns a list of findings and nothing else; an empty list is success. |
| 6 | **Deterministic findings** | The same input yields the same findings, with stable identity/location and only the timestamp varying. |
| 7 | **Facts, not exceptions** | Invalid content is a `ValidationIssue`; only infrastructure/wiring failures raise. |
| 8 | **Defer, never duplicate** | When a datum a sibling owns is absent, the rule defers rather than re-reporting another rule's concern. |
| 9 | **Reusable, stateless instances** | The rule keeps no per-execution state; one instance serves every run. |
| 10 | **Dependency injection only for varying mechanisms** | Inject a collaborator only where a real mechanism varies; take none where the logic is fixed; validate wiring at construction. |
| 11 | **Orchestration belongs to the framework** | The rule never orders, selects, invokes, or coordinates; the pipeline does. |
| 12 | **`ValidationResult` belongs to the pipeline** | The rule never assembles a result, verdict, or summary; the pipeline assembles the single canonical result. |

---

## 14. Architecture Freeze

> **Architectural Decision — Architecture Freeze**
> With this document, the following become **frozen** for every validation rule
> implementation, in every layer:
>
> - **The rule lifecycle** — construct once, receive the immutable `ValidationInput`,
>   produce findings, return, remain reusable with no execution state (§2).
> - **Single concern** — one rule, one concern; the prohibitions of §3.
> - **Input discipline** — `ValidationInput` only, read-only, never mutated, cached,
>   or retained (§4).
> - **Output discipline** — a list of `ValidationIssue` only; empty = success; the
>   forbidden returns of §5.
> - **Facts-vs-exceptions** — invalid content is a finding; only
>   infrastructure/wiring failures raise (§6).
> - **Rule independence** — deterministic, stateless, idempotent, independent,
>   parallelizable, non-mutating; no coordination or aggregation (§7).
> - **Metadata discipline** — immutable, descriptive identity that never drives
>   execution (§8).
> - **Dependency philosophy** — inject varying mechanisms only; validate wiring at
>   construction (§9).
> - **The frozen engineering patterns** (§13).
>
> **Only implementation may evolve** beneath these contracts. **The architecture may
> evolve only through an approved Architecture Decision Record (ADR).** A rule that
> violates any frozen item above is non-conforming by definition. This contract
> changes **no** frozen upstream contract, **no** ownership, **no** rule identity,
> and **no** canonical model; it records the implementation structure those
> contracts assumed.

> **Definition of Done**
> This document is the governing implementation structure for every validation rule
> in the platform. It governs the rule lifecycle, the single-concern discipline, the
> input and output discipline, the facts-vs-exception philosophy, rule independence,
> the metadata discipline, the dependency-injection philosophy, and the engineering
> and conformance checklists. It governs **only** the rule implementation structure —
> never *which* rules exist or *what* each validates (Validation Rule Catalog), *how*
> a rule is written in a specific language (Validation Rule Development Guide), *how*
> the run is orchestrated (Response Validator), or *how* the result is assembled
> (Validation Framework). It is implementation-independent and remains valid even if
> the platform is reimplemented on an entirely different technology stack or driven by
> an entirely different AI provider.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Validation rule** | A single, atomic check that validates exactly one concern about a response, structured per this contract (§2–§9). |
| **`ValidationInput`** | The immutable, execution-scoped input every rule receives: the binding of the `AnalysisResult` and its `NormalizationResult` (ADR-0003). |
| **`ValidationIssue`** | The atomic, immutable finding a rule produces; the only kind of output a rule returns (§5; Canonical Models §3). |
| **Finding** | A `ValidationIssue` — the record of a violated concern. Never an exception (§6). |
| **Infrastructure/wiring failure** | An inability to perform the work — a mechanism failure or mis-wired collaborator — surfaced as a `ValidationRuleError`, never a finding (§6). |
| **Defer, never duplicate** | Returning no findings for a datum a *sibling* rule owns, rather than re-reporting another rule's concern (§3). |
| **Immutable identity** | A rule's single, frozen, descriptive metadata, fixed at construction; it never drives execution (§8). |
| **Principled injection** | Injecting a collaborator only where a real mechanism varies, and none where the logic is fixed (§9). |
| **Reusable rule instance** | A rule constructed once and evaluated for any number of executions, retaining no per-execution state (§2). |

## Appendix B — Consistency Verification

Verified consistent with every frozen artifact it touches. **No inconsistency was
found.**

| Document | Consistency check | Result |
| -------- | ----------------- | ------ |
| **Validation Rule Catalog** | Single concern, one-concern-one-layer, severity/blocking-by-finding, independence — restated as implementation structure, never redefined. | ✅ Consistent — no identity, concern, layer, severity, or blocking changed. |
| **AI Response Validation Architecture** | Determinism, Preserve Original Response, Rule Independence, Explain Every Failure expressed as implementation obligations only. | ✅ Consistent — no philosophy changed. |
| **Validation Canonical Models** | `ValidationIssue` and `ValidationInput` read and produced per their frozen shapes. | ✅ Consistent — no canonical model changed. |
| **`ValidationRule` (Framework)** | `metadata` + `validate(response) -> list[ValidationIssue]` structure elaborated, not altered; `response: Any` unchanged. | ✅ Consistent — no signature changed. |
| **ADR-0003 / `ValidationInput`** | The `ValidationInput` is the sole input; ownership and the same-execution invariant untouched. | ✅ Consistent — no input contract changed. |
| **Transport rule implementations** | The four rules already conform to every clause here (post-ADR-0003 migration). | ✅ Consistent — this contract is the pattern they proved. |
| **Validation Rule Development Guide** | The guide is the Python operationalization *below* this contract; no clause here restates a Python specific. | ✅ Consistent — clean boundary, no duplication. |

> If any future change to a frozen document contradicts this contract, that is an
> architecture change: **stop and resolve it through an ADR**, never silently in this
> document.
