# Normalization Stage Implementation Contract

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Stage Implementation Pattern |
| Status               | Approved — Foundational — **FROZEN**                              |
| Scope                | The **engineering implementation pattern** every internal normalization stage (`NORMALIZATION-0001 … 0005` and beyond) must conform to — its lifecycle, responsibilities, prohibitions, metadata, Assembly-State interaction, exception philosophy, dependency rules, and evolution |
| Governs              | Stage lifecycle · stage implementation responsibilities · stage prohibitions · stage metadata contract · Assembly-State read/write discipline · fact-vs-exception discipline · forward-only dependency rules · additive stage evolution · the engineering + conformance checklists |
| Complements          | Normalization Assembly Contract (it does **not** replace it) |
| Depends on           | Response Normalization Contract · Normalization Responsibility Catalog · Normalization Assembly Contract · Response Normalizer Architecture · ADR-0002 · Validation Canonical Models (`ParsedResponse`) |
| Audience             | Lead Engineers · Platform Engineers · Technical Architects · QA Architects · Reviewers |
| Implementation-bound | No — valid regardless of language, framework, serialization format, algorithm, or AI provider |

> **Architectural Decision**
> This contract captures the **engineering implementation pattern** that emerged
> from two completed, independent stage implementations — `NORMALIZATION-0001`
> (Recover Canonical Structure) and `NORMALIZATION-0002` (Determine Normalization
> Outcome) — and freezes it as the template every present and future stage must
> follow. It is **not** an architecture redesign. The Response Normalization
> architecture, the Assembly Contract, ADR-0002, the Responsibility Catalog, the
> Framework, and the Response Normalizer are already frozen and are **unchanged** by
> this document. This contract adds one thing those documents deliberately left to
> engineering: the **repeatable shape of a conforming stage implementation**.

---

## 1. Purpose

### 1.1 Why this contract exists

The frozen normalization architecture answers, permanently, *which* stages exist,
*what* each owns, *what* it depends on, and *in what order* they participate
(Responsibility Catalog), and *how* their intermediate facts flow through a
transient Assembly State (Assembly Contract). What those documents intentionally do
**not** answer is the recurring engineering question a stage author faces:

> *"Given the frozen architecture, what is the concrete, repeatable shape a
> conforming stage implementation must take — so that every stage looks, behaves,
> and fails the same way?"*

Two stages have now been built to the same shape, independently. That shape is no
longer a guess; it is a **proven pattern**. This contract records it so that
`NORMALIZATION-0003`, `0004`, `0005`, and every future `NORMALIZATION-00NN` stage
are implemented **identically in structure**, reviewed against a single checklist,
and never re-negotiated per stage.

### 1.2 Why it complements the Assembly Contract instead of replacing it

The two documents answer **different questions** and never overlap:

| Question | Answered by |
| -------- | ----------- |
| *What may the Assembly State hold, and how do stages collaborate through it?* | **Normalization Assembly Contract** (the collaboration contract) |
| *What repeatable shape must a conforming stage implementation take?* | **This contract** (the implementation pattern) |

The Assembly Contract governs the **medium and the collaboration**; this contract
governs the **implementing unit**. The Assembly Contract says *a stage writes its
one owned fact to the Assembly State*; this contract says *how a stage is
structured so that it does exactly that — one concern, one owned fact, guarded
writes, injected mechanism where a mechanism varies, facts recorded and
infrastructure failures raised, immutable metadata, and a communicate-by-writing
execution surface.* Neither restates the other; removing either would leave a real
gap.

> **Principle**
> The Assembly Contract governs **collaboration**; this contract governs
> **implementation shape**. A stage conforms only when it satisfies **both**.

---

## 2. Relationship to Other Artifacts

This contract sits beneath the frozen normalization documents and above the stage
code. It introduces **no new dependency direction** and **no new ownership**.

```text
   [Response Normalization Contract]     philosophy · facts-not-judgments · Normalize Once · Observe-Never-Repair
            │
            ▼
   [Normalization Responsibility Catalog]  WHICH stages exist · single concern · ownership · order
            │
            ▼
   [Normalization Assembly Contract]     the Assembly State · stage collaboration · invariants
            │  ADR-0002 draws the framework-vs-component boundary
            ▼
   [Normalization Stage Implementation Contract]  ◄── THIS DOCUMENT (the implementation pattern)
            │
            ▼
   conforming stage implementations (0001 … 0005 …)  coordinated inside the ResponseNormalizer
```

| Artifact | Relationship to this contract |
| -------- | ----------------------------- |
| **Response Normalization Contract** | Supplies the binding philosophy every stage obeys — Normalize Once, Observe-Never-Repair, provider/format independence, determinism, non-interpretation, facts-not-judgments (§3). This contract turns that philosophy into an implementation shape; it never alters it. |
| **Normalization Responsibility Catalog** | The single authority for *which* stages exist, each one's single concern, its owned fact, its forward-only dependencies, and the frozen order. This contract governs *how* a stage realises its catalog entry; it never redefines identity, concern, ownership, dependency, or order. |
| **Normalization Assembly Contract** | Governs the Assembly State and the read/write collaboration through it. This contract's Assembly-State rules (§7) are the **implementation-facing restatement** of the Assembly Contract's stage contracts and invariants — consistent with them, never additive to them. |
| **Response Normalizer** | The single orchestration boundary that coordinates the stages internally. This contract governs the stages it coordinates; it never changes the Normalizer's orchestration contract, exception boundary, profiles, or execution context. |
| **Framework** | Generic execution infrastructure. Per ADR-0002 the stages are **not** framework execution units; this contract governs the internal stages only and depends on **no** framework implementation detail. |
| **ADR-0002** | Establishes that the five stages are internal to the `ResponseNormalizer` and that the framework is unaware of the Assembly State and `ParsedResponse` construction. This contract lives entirely inside that boundary. |
| **`ParsedResponse` (Validation Canonical Models)** | The immutable representation the assembling stage produces. This contract never redefines its shape; it only governs the implementation discipline of the stage that assembles it. |

> **Architectural Decision — this contract adds a pattern, not a power.** It grants
> no stage any new ownership, dependency, outcome, observation class, or authority.
> Every rule here is a consequence of a frozen upstream decision, expressed as an
> implementation obligation. A conflict between this contract and any frozen
> document is resolved in favour of the frozen document, through an ADR — never
> silently here (§12).

---

## 3. Stage Lifecycle

A stage passes through five phases in every normalization execution. The phases are
the same for every stage; only the one owned concern differs.

```text
   Creation      a stage is constructed once, with its immutable identity and any
                 injected mechanism it needs; construction validates its wiring.
        │
        ▼
   Execution     the coordinator invokes the stage exactly once, handing it the
                 read-only response and the shared Assembly State.
        │
        ▼
   Fact          the stage reads only the facts it is permitted to read and writes
   production    its one owned fact to the Assembly State (or, for the assembling
                 stage, produces the representation as an output).
        │
        ▼
   Completion    the stage returns having written exactly its one fact; it returns
                 nothing and signals success by the fact's presence, not a value.
        │
        ▼
   Disposal      the stage retains no per-execution state; the Assembly State is
                 execution-local and is discarded after the final stage.
```

### 3.1 Creation

A stage is **constructed once** and is **reusable across executions**. Construction
establishes the stage's immutable identity (§6) and injects any collaborator the
stage needs (§9). Construction **validates its own wiring**: if an injected
collaborator is of the wrong kind, construction fails as a **wiring error** — an
infrastructure failure, never a normalization fact. A stage holds no
per-execution state, so the same instance runs any number of executions
identically.

> **Proven pattern.** `NORMALIZATION-0001` is constructed with an injected
> structure-recovery mechanism and rejects a collaborator that does not satisfy the
> recovery seam at construction time. `NORMALIZATION-0002` is constructed with
> **no** collaborator, because its rule does not vary (§9). Both carry a single
> immutable identity fixed at construction.

### 3.2 Execution

The stage is invoked **exactly once per execution** by the coordinator, which hands
it (a) the read-only response under normalization and (b) the shared, execution-
local Assembly State. A stage never invokes itself, never loops, never retries, and
never re-executes within one execution (Assembly Contract §7.8).

### 3.3 Fact production

Within execution the stage performs its **one concern** and **writes its one owned
fact** to the Assembly State — its structure, its outcome, its observation set, or
its source reference. A recovered value and a recorded **absence** are both facts.
The stage reads only what it is permitted to read (§7) and writes nothing it does
not own.

The **assembling stage** is the one designed asymmetry: its product — the immutable
representation — is an **output handed out of the boundary**, never stored back into
the Assembly State (§7.4). It still executes exactly once, still reads only
finalized upstream facts, and still writes no fact it does not own.

### 3.4 Completion

A stage completes by **returning nothing**. Success is signalled by the presence of
the owned fact in the Assembly State, not by a return value. This
*communicate-by-writing* surface is what keeps stages composable and the Assembly
State the single collaboration medium (§7).

### 3.5 Disposal

A stage keeps **no reference** to the Assembly State or to any per-execution fact
after it returns. The Assembly State is **execution-local**: created when the
execution begins, written by the stages in order, and discarded after the final
stage. Nothing a stage produced during one execution survives into another except
through the products handed out of the boundary (the representation and the
aggregated observations).

---

## 4. Implementation Responsibilities

Every stage **MUST**:

| # | Responsibility | Meaning |
| - | -------------- | ------- |
| 1 | **Own exactly one concern** | The single concern assigned to its catalog entry — never a second one, never a share of another's. |
| 2 | **Own exactly one fact** | Produce and write exactly one owned fact (its structure, outcome, observation set, or source reference; or, for the assembling stage, the one representation output). |
| 3 | **Read only required facts** | Read only the response and the upstream facts its concern requires — never a fact it does not need, never a later stage's fact. |
| 4 | **Write only owned facts** | Write only the fact it owns; never write, extend, or annotate a fact owned by another stage. |
| 5 | **Preserve previous facts** | Leave every already-recorded fact exactly as it is; facts accumulate, they are never edited. |
| 6 | **Never mutate upstream input** | Treat the response as strictly read-only; never alter it, and never copy-and-alter it. |
| 7 | **Never perform another stage's work** | Recover structure only in the recovery stage, determine the outcome only in the outcome stage, and so on; no stage does a neighbour's job. |
| 8 | **Be deterministic** | Given the same response and the same upstream facts, produce the same fact every time — no randomness, clock, or external mutable state. |
| 9 | **Record facts; raise only for infrastructure failure** | A missing, empty, malformed, or unexpected response is recorded as a fact; only an inability to *perform the work* is raised (§8). |
| 10 | **Carry an immutable identity** | Expose a single immutable metadata identity and read all identity fields from it (§6). |

> **Proven pattern — single concern, one owned fact.** `0001` writes only the
> normalized structure; `0002` reads only that structure and writes only the
> outcome. Neither reads a later fact, neither edits the other's fact, and neither
> mutates the response. This is the shape every stage repeats.

---

## 5. Implementation Prohibitions

A stage **MUST NEVER**:

| The stage never… | Because that belongs to |
| ---------------- | ----------------------- |
| **Validate** — judge trustworthiness or conformance | the validation subsystem, across the frozen §10 boundary |
| **Repair** — fix, complete, coerce, or "clean" a response | nothing — repair is forbidden platform-wide (Observe, Never Repair) |
| **Judge facts** — assign severity, meaning, or acceptability | a downstream consumer |
| **Produce verdicts** — pass / fail / blocked or any recommendation | validation |
| **Create the representation** — assemble the `ParsedResponse` | the assembling stage alone (`NORMALIZATION-0005`) |
| **Mutate a fact owned by another stage** — edit, overwrite, or delete it | that fact's single owner |
| **Re-run another stage** — recover, re-determine, or re-derive an upstream fact | the stage that owns it (each fact is produced once) |
| **Coordinate execution** — order, select, retry, or invoke other stages | the coordinator (the execution engine) |
| **Depend on framework implementation** — read framework internals or registry state | nothing — the stages are internal to the component (ADR-0002) |
| **Read provider-specific information** — a provider, model, vendor, endpoint, or serialization format | nothing — normalization is provider- and format-independent |
| **Contain business logic** — reshape content into domain concepts | downstream domain layers |

> **Architectural Decision — the prohibitions are the boundary made concrete.** Each
> forbidden act would collapse a frozen boundary: validating or judging crosses the
> Normalization–Validation line; repairing breaks Observe-Never-Repair; assembling
> outside the assembling stage duplicates an owner; coordinating turns a stage into
> the engine; reading provider or business detail reintroduces coupling the whole
> subsystem exists to remove. A stage that does any of these is non-conforming by
> definition.

---

## 6. Metadata Contract

Every stage carries a single **immutable identity**. Identity is *declared* by the
stage and *governed* by the architecture — the metadata never invents identity, it
only surfaces the catalog-assigned identity at runtime.

| Identity field | Meaning |
| -------------- | ------- |
| **Identity (stable identifier)** | The permanent `NORMALIZATION-00NN` identifier from the Responsibility Catalog; never renumbered, reused, or reassigned. |
| **Name** | A short, human-readable label for the stage's concern. |
| **Order** | The stage's declared position in the frozen chain (`0001 → … → 0005`). It **describes** position; it does **not** drive execution (§6.1). |
| **Version** | The version of *this stage's* logic, advanced when the stage's own behaviour changes. |
| **Documentation reference** | A pointer to the governing architecture for this stage. |
| **Enabled state** | Whether the stage participates; a **descriptive** flag, not a self-activation switch (§6.1). |
| **Future-compatibility fields** | Reserved, behaviourless extension points (e.g. classification labels, the catalog version an identity targets) so identity can grow without a breaking change. |

### 6.1 Why metadata exists — and why it does **not** control execution

Metadata exists to make a stage **observable and auditable**: so a run can be traced
to the exact stages, versions, and catalog positions that produced it, without
re-running anything. It is *runtime identity*, not *governing architecture*.

Metadata deliberately **does not control execution**:

- **Order does not sort.** The coordinator executes stages in the **order it is
  given**, which is the frozen catalog order. It never reads a stage's declared
  `order` field to sort or reorder. Declared order is a description that must
  *match* the coordination order, never the mechanism that *produces* it.
- **Enabled does not self-activate.** A stage does not switch itself on or off by
  its `enabled` flag. *Participation* is an orchestration concern governed by
  profiles (Responsibility Catalog §8; Normalizer §11); the flag describes a
  decision made elsewhere, it does not make it.

> **Architectural Decision — identity is descriptive; execution is coordinated.**
> Separating *what a stage says it is* from *how the run is driven* is what lets the
> order be frozen in one place (the catalog, enforced by the coordinator) while a
> stage's identity remains a passive, immutable fact safe to stamp into provenance.
> If metadata controlled execution, a mis-declared field could silently reorder or
> disable a stage — precisely the divergence the frozen order forbids.

> **Proven pattern — immutable identity, constructed once, shared.** Each completed
> stage holds a single frozen identity object, fixed at construction and reused for
> every execution; identity fields are read from that one object, never recomputed.

---

## 7. Assembly-State Interaction

The Assembly State is the **only** medium through which a stage collaborates. All
interaction obeys the Assembly Contract; the rules below are its implementation-
facing restatement.

### 7.1 Allowed reads

A stage may read:

- the **response** under normalization (read-only); and
- the **upstream facts** its concern requires — and **only** those.

A stage never reads a fact produced by a later stage, and never reads a fact its
concern does not need.

### 7.2 Allowed writes

A stage may write **only the one fact it owns**:

| Stage concern | Owned write |
| ------------- | ----------- |
| Recover structure | the normalized structure (or its recorded absence) |
| Determine outcome | the one normalization outcome |
| Capture observations | zero or more observations, appended to the transient observation collection |
| Create source reference | the one source reference |
| Assemble representation | **no Assembly-State write** — the representation is an output handed out of the boundary (§7.4) |

### 7.3 Single-write rule and ownership rule

Each **owned fact** is written **exactly once**. A second write of an already-
recorded owned fact is a **coordination defect**, surfaced as an infrastructure
failure — never a normalization fact. Every fact has **exactly one** owning stage;
no stage writes a fact another stage owns. (Observations are the one append-only
collection: many observations, still one owning stage.)

### 7.4 Never overwrite · never delete · never leak

- **Never overwrite** — a recorded fact is immutable for the rest of the execution.
- **Never delete** — no stage removes a fact from the Assembly State.
- **Never leak** — the Assembly State never leaves the component boundary; a stage
  never returns it, stores it, shares it, or lets it escape. Products leave the
  boundary only as the representation and the aggregated observations.

### 7.5 Read-before-write ordering

When a stage's concern depends on an upstream fact, the stage **verifies the fact is
present before it acts**. If the required upstream fact has not been recorded, the
stage raises an **infrastructure/ordering failure** — the chain was mis-ordered — it
does **not** fabricate a fact or a fallback.

> **Proven pattern — the ordering guard.** `NORMALIZATION-0002` checks that the
> structure it depends on has been recorded before determining the outcome; absent
> that upstream fact, it raises an ordering failure rather than inventing a
> `MALFORMED` result. This is the read-before-write guard every dependent stage
> repeats.

> **Proven pattern — guarded single writes.** The Assembly State refuses a second
> write of any owned fact and treats a duplicate as a coordination defect, so the
> single-write rule is enforced at the point of writing, not left to convention.

---

## 8. Exception Philosophy

Normalization produces **facts, not exceptions**. The distinction is permanent and
absolute.

| Situation | Result |
| --------- | ------ |
| **No well-formed structure recovered** | Recorded as an **absent structure** (a fact); the outcome stage records **`MALFORMED`** (a fact). Never an exception. |
| **A malformed, empty, or unexpected response** | Recorded as facts (an absent structure, an outcome, possibly an observation). The chain **completes**. Never an exception. |
| **A stage's own mechanism fails unexpectedly** | An **infrastructure exception** — the stage could not perform its work. |
| **A required upstream fact is missing when a stage runs** | An **ordering/coordination exception** — the chain was mis-ordered. |
| **A stage is wired incorrectly at construction** | A **wiring exception** — an infrastructure failure, raised before any execution. |

The three consequences an author must internalise:

1. **`MALFORMED` is not an exception.** It is a successful, fact-producing outcome:
   the subsystem's job is to *record what is present*, and "the response was
   malformed" is a thing that is present. Only an inability to *run* is exceptional.
2. **Infrastructure failures are exceptions.** A mechanism that fails unexpectedly,
   or a stage that cannot perform its work, raises — so an infrastructure failure
   never masquerades as a `MALFORMED` fact.
3. **Ordering violations are exceptions.** Running a dependent stage before its
   upstream fact exists is a coordination defect, raised — never absorbed into a
   fabricated fact.

> **Architectural Decision — two families that never mix.** Facts flow through the
> Assembly State; infrastructure and ordering failures flow as exceptions. Keeping
> them disjoint is what preserves the Normalization–Validation boundary: a stage
> never judges a malformed response (that is validation's job later), and a broken
> run never disguises itself as a judgement about the response.

> **Proven pattern — facts recorded, infrastructure raised.** `0001` records an
> absent structure when none is recoverable and raises only when its recovery
> mechanism itself fails; `0002` records `MALFORMED` as a fact and raises only when
> invoked out of order. Every stage draws the line in the same place.

---

## 9. Dependency Rules

### 9.1 Forward-only, acyclic, no implicit coordination

- **Forward-only** — a stage reads only the facts of stages before it in the frozen
  order; it never reads a later stage's fact.
- **No cycles** — because dependencies are forward-only, the dependency graph is
  acyclic; no stage transitively depends on itself.
- **No backward dependencies** — a stage never reaches "downstream" for a fact that
  does not yet exist, and never assumes a later stage's behaviour.
- **No implicit coordination** — a stage never orders, selects, invokes, or waits on
  another stage. All ordering is owned by the coordinator; stages are ignorant of
  one another's existence and communicate **only** through recorded facts.

### 9.2 Dependency injection philosophy

A stage receives its collaborators by **injection**, never by internal construction,
discovery, global lookup, or reflection. Two rules govern *whether* a stage has an
injected collaborator:

- **Inject a mechanism that genuinely varies.** When a stage's concern has a
  format- or environment-specific *mechanism* (for example, how structure is
  recovered from text), that mechanism is injected behind a stable seam, so the
  stage stays provider- and format-independent and new mechanisms are added without
  changing the stage.
- **Do not inject a mechanism that does not vary.** When a stage's rule is fixed and
  governed (for example, "structure recovered ⇒ `NORMALIZED`; absent ⇒
  `MALFORMED`"), the stage takes **no** collaborator. Injecting a policy that cannot
  differ would be a speculative abstraction, not a dependency.

> **Architectural Decision — inject variation, not ceremony.** Dependency injection
> exists to isolate the parts that can legitimately differ, not to wrap every stage
> in a collaborator for symmetry's sake. The two completed stages prove both sides:
> one injects a varying recovery mechanism; the other, whose rule cannot vary, takes
> nothing. A future stage chooses by the same test — *does a real mechanism vary?* —
> never by imitation.

---

## 10. Stage Evolution

The stage set grows **additively**, exactly as the Responsibility Catalog and the
Assembly Contract grow.

| Rule | Statement |
| ---- | --------- |
| **Additive only** | A new stage `NORMALIZATION-0006+` is appended; it never replaces or splits an existing stage. |
| **Never reorder** | Existing stages keep their frozen positions; a new stage joins at a reserved higher position, preserving the forward-only chain. |
| **New owned fact** | A new stage introduces its **own** owned fact; it never re-owns structure, outcome, observations, source reference, or the representation. |
| **Same shape** | A new stage follows this contract unchanged — single concern, one owned fact, guarded write, injected mechanism only if one varies, facts-not-exceptions, immutable identity. |
| **ADR-gated architecture** | Adding a stage, changing a concern, a dependency, an owned fact, or the order is an **architecture** change requiring an ADR (Catalog §11; Assembly Contract §11). |
| **Free implementation** | Improving *how* an existing stage fulfils its concern requires no ADR. |

> **Architectural Decision — the pattern is the extension mechanism.** Because every
> stage has the same shape, a new stage is added by *instantiating the pattern*, not
> by inventing a new one. A stage that repaired, judged, re-owned a fact, reordered
> the chain, coordinated its neighbours, or read provider/business detail is
> non-conforming regardless of its number.

---

## 11. Engineering Checklist

Every new stage implementation must satisfy all of the following before it is
considered complete:

- [ ] The stage realises **exactly one** catalog concern and blends no other.
- [ ] The stage produces and writes **exactly one** owned fact (or, for the
      assembling stage, the one representation output).
- [ ] The stage reads **only** the response and the **upstream** facts its concern
      requires — never a later stage's fact, never a fact it does not need.
- [ ] The stage **preserves** every already-recorded fact and mutates none.
- [ ] The stage treats the response as **strictly read-only**.
- [ ] The stage is **deterministic** — same response and upstream facts ⇒ same fact.
- [ ] The stage **records** a missing/empty/malformed/unexpected response as a fact
      and **raises only** for an infrastructure, ordering, or wiring failure.
- [ ] A dependent stage **verifies its upstream fact is present** before acting and
      raises an ordering failure if it is not.
- [ ] Each owned fact is written **exactly once**; a duplicate write is treated as a
      coordination defect, never a fact.
- [ ] The stage carries a **single immutable identity** and reads all identity
      fields from it.
- [ ] The stage's declared **order matches** its frozen catalog position and is used
      only descriptively — the stage never sorts, selects, or coordinates.
- [ ] The stage **injects a collaborator only where a real mechanism varies**;
      otherwise it takes none.
- [ ] Construction **validates the stage's wiring** and fails as an infrastructure
      error, never a normalization fact.
- [ ] The stage carries a **documentation reference** to its governing architecture.
- [ ] The stage performs **none** of the prohibited acts (§5).
- [ ] The stage retains **no** per-execution state and never lets the Assembly State
      escape the boundary.

---

## 12. Conformance Checklist (for reviewers)

A reviewer can certify a stage against this contract only if every box can be
checked:

- [ ] **Single concern** — the stage owns one concern and only one (§4).
- [ ] **Single owned fact** — it writes one owned fact and nothing it does not own
      (§4, §7.2).
- [ ] **Read discipline** — it reads only permitted upstream facts and the
      read-only response (§7.1).
- [ ] **No mutation** — it never mutates the response or another stage's fact (§4,
      §7.4).
- [ ] **Forward-only** — it reads no later stage's fact; the dependency graph stays
      acyclic (§9.1).
- [ ] **No coordination** — it never orders, selects, invokes, or waits on another
      stage (§9.1).
- [ ] **Facts, not judgments** — it produces no verdict, severity, recommendation,
      or validation issue (§5, §8).
- [ ] **Observe, never repair** — it never fixes, completes, or coerces a response
      (§5).
- [ ] **Fact vs. exception** — `MALFORMED`/absence is a fact; only
      infrastructure/ordering/wiring failures raise (§8).
- [ ] **Single write** — each owned fact is written once; duplicates are rejected
      (§7.3).
- [ ] **Read-before-write** — a dependent stage guards on its upstream fact (§7.5).
- [ ] **Immutable identity** — a single frozen identity, read-only, non-executing
      (§6).
- [ ] **Metadata does not drive execution** — order and enabled are descriptive
      (§6.1).
- [ ] **Injection is principled** — a collaborator only where a mechanism varies
      (§9.2).
- [ ] **Wiring validated** — construction rejects a mis-wired collaborator (§3.1).
- [ ] **Provider/format-independent** — no provider, vendor, endpoint, or format
      influences the stage (§5).
- [ ] **No escape / no state** — the Assembly State never leaks; the stage keeps no
      per-execution state (§3.5, §7.4).
- [ ] **Additive evolution** — a new stage follows the pattern and re-owns nothing
      (§10).
- [ ] Any architectural change to the above is made through an approved **ADR**.

---

## 13. Frozen Engineering Decisions

These are the reusable engineering patterns **proven by** `NORMALIZATION-0001` and
`NORMALIZATION-0002` and frozen by this contract. None is invented; each is captured
from the two completed implementations.

| # | Frozen pattern | What it means |
| - | -------------- | ------------- |
| 1 | **Single-concern implementation** | One stage owns one concern and writes one fact — never a second. |
| 2 | **One owned fact per stage** | Every fact has exactly one producing stage; ownership never overlaps. |
| 3 | **Guarded single writes** | Each owned fact is written exactly once; a duplicate write is a coordination defect, rejected at the point of writing. |
| 4 | **Read-before-write ordering guard** | A dependent stage verifies its upstream fact is present and raises an ordering failure otherwise, never fabricating a fallback. |
| 5 | **Communicate by writing, not returning** | A stage signals success by the presence of its fact, returning nothing; the Assembly State is the single collaboration medium. |
| 6 | **Facts, not exceptions** | Missing/malformed/unexpected responses are recorded as facts; only infrastructure, ordering, and wiring failures raise. |
| 7 | **Principled dependency injection** | Inject a collaborator only where a real mechanism varies; take none where the rule is fixed and governed. |
| 8 | **Constructor-time wiring validation** | A mis-wired collaborator fails at construction as an infrastructure error, before any execution. |
| 9 | **Immutable identity, constructed once, shared** | A single frozen identity object per stage, reused for every execution, safe to stamp into provenance. |
| 10 | **Descriptive metadata, coordinated execution** | Identity fields (order, enabled) describe; they never sort, select, or activate — the coordinator drives the frozen order. |
| 11 | **The assembling stage is the one designed asymmetry** | The final stage produces the representation as an output handed out of the boundary and writes no fact back into the Assembly State. |
| 12 | **Per-stage documentation contract** | Each stage documents its Purpose, catalog identity, inputs, outputs, a worked example, and its architecture reference. |

---

## 14. Architecture Freeze

> **Architectural Decision — Architecture Freeze**
> With this document, the following become **frozen** for every internal
> normalization stage implementation:
>
> - **The stage lifecycle** — creation, execution, fact production, completion,
>   disposal (§3).
> - **The implementation responsibilities** — the ten MUSTs of §4.
> - **The implementation prohibitions** — the acts of §5 a stage must never perform.
> - **The metadata contract** — immutable identity; metadata describes, it does not
>   control execution (§6).
> - **The Assembly-State interaction rules** — allowed reads/writes, single-write,
>   ownership, read-before-write, never overwrite/delete/leak (§7).
> - **The exception philosophy** — facts vs. infrastructure/ordering/wiring failures;
>   `MALFORMED` is a fact (§8).
> - **The dependency rules** — forward-only, acyclic, no implicit coordination,
>   principled injection (§9).
> - **The additive stage-evolution rules** (§10).
> - **The frozen engineering decisions** (§13).
>
> **Only implementation may evolve** beneath these contracts. **The architecture may
> evolve only through an approved Architecture Decision Record (ADR).** A stage that
> violates any frozen item above is non-conforming by definition. This contract
> changes **no** frozen upstream contract, **no** ownership, **no** ordering, and
> **no** canonical model; it records the implementation pattern those contracts
> assumed.

> **Definition of Done**
> This document is the governing implementation pattern for the internal
> normalization stages of the platform. It governs the stage lifecycle, the
> implementation responsibilities and prohibitions, the metadata contract, the
> Assembly-State interaction discipline, the fact-vs-exception philosophy, the
> forward-only dependency rules, additive stage evolution, and the engineering and
> conformance checklists. It governs **only** the stage implementation pattern —
> never *which* stages exist (Responsibility Catalog), *how* they collaborate through
> the Assembly State (Assembly Contract), *what* the `ParsedResponse` holds (Canonical
> Models), or *how* the run is orchestrated (Response Normalizer). It is
> implementation-independent and remains valid even if the platform is reimplemented
> on an entirely different technology stack, serialization format, or AI provider.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Stage** | An internal unit of the `ResponseNormalizer` that owns exactly one normalization concern from the Responsibility Catalog and writes one owned fact to the Assembly State (§3, §4). |
| **Owned fact** | The single fact a stage produces and writes; every fact has exactly one owning stage (§7.3). |
| **Communicate by writing** | A stage's execution surface: it signals success by writing its fact, returning nothing (§3.4, §13). |
| **Ordering guard** | A dependent stage's check that its required upstream fact is present before it acts; its absence is an ordering failure (§7.5). |
| **Guarded single write** | The discipline that each owned fact is written exactly once; a duplicate is a coordination defect (§7.3). |
| **Principled injection** | Injecting a collaborator only where a real mechanism varies, and none where the rule is fixed (§9.2). |
| **Immutable identity** | A stage's single, frozen, descriptive metadata, fixed at construction (§6). |
| **Assembling stage** | The final stage, which produces the representation as an output handed out of the boundary and writes no fact back into the Assembly State (§7.2, §13). |
| **Infrastructure failure** | An inability to perform the work — a mechanism failure, an ordering violation, or a wiring error — surfaced as an exception, never a normalization fact (§8). |

## Appendix B — Consistency Verification

Verified consistent with every frozen artifact it touches. **No inconsistency was
found.**

| Document | Consistency check | Result |
| -------- | ----------------- | ------ |
| **Response Normalization Contract** | Facts-not-judgments, Observe-Never-Repair, determinism, provider/format independence expressed as implementation obligations only. | ✅ Consistent — no philosophy changed. |
| **Normalization Responsibility Catalog** | Single concern, one owner per fact, forward-only dependencies, frozen order — restated as implementation rules, never redefined. | ✅ Consistent — no identity, ownership, dependency, or order changed. |
| **Normalization Assembly Contract** | Assembly-State reads/writes, single-write, read-before-write, no-leak, facts-not-exceptions, the assembling stage's no-write output. | ✅ Consistent — this contract is the implementation-facing restatement of §6–§8. |
| **Response Normalizer** | Orchestration, exception boundary, profiles, execution context untouched; coordination remains the engine's concern, not a stage's. | ✅ Consistent — no orchestration contract changed. |
| **ADR-0002** | Stages internal to the component; framework unaware of the Assembly State and `ParsedResponse` construction; stages depend on no framework internal. | ✅ Consistent — this contract lives entirely inside the boundary. |
| **`ParsedResponse` (Validation Canonical Models)** | The representation's shape is untouched; only the assembling stage's implementation discipline is governed. | ✅ Consistent — no canonical model changed. |

> If any future change to a frozen document contradicts this contract, that is an
> architecture change: **stop and resolve it through an ADR**, never silently in this
> document.
