# Response Normalizer Architecture

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Orchestration Boundary |
| Status               | Approved — foundational — **FROZEN**                              |
| Scope                | Orchestration of response normalization within the platform        |
| Governs              | The single entry point, execution flow, context, configuration, profile selection, exception translation, observability, and result production of normalization |
| Depends on           | Response Normalization Contract · Validation Canonical Models (`ParsedResponse`) · Response Normalization Framework · Response Validator Architecture (mirrored pattern) |
| Audience             | Solution Architects · Technical Architects · Lead Engineers · QA Architects · Platform Engineers |
| Implementation-bound | No — valid regardless of language, framework, persistence, serialization, or AI provider |

> **Architectural Decision**
> The Response Normalizer is the **exclusive entry point into the Response
> Normalization subsystem**. Every request to normalize an AI response flows
> through it and only through it. The Normalizer does **not** normalize — it
> **orchestrates** normalization, coordinating the framework, the pipeline, the
> responsibilities, the profile, and the configuration to produce one canonical
> `NormalizationResult`.

---

## 1. Purpose

### 1.1 Why the Response Normalizer exists

The Response Normalization subsystem is composed of several governed parts: the
Normalization Responsibility Catalog (which responsibilities exist — Response
Normalization Contract §13), the Normalization Framework (the registry,
responsibility contract, and pipeline), the `NormalizationResult` aggregate and
the `ParsedResponse` canonical model (the information model), and the
`NormalizationExecutionContext` (execution identity). Something must **coordinate**
these parts into a single, repeatable act of normalization. If every caller wired
those parts together itself:

- **Orchestration would scatter** — each caller would select a profile, populate a
  registry, construct a pipeline, and assemble a run in its own way.
- **Inconsistency would creep in** — two callers could normalize the same response
  under subtly different responsibility sets, defeating determinism and audit.
- **No governance choke point** — there would be no single place to enforce
  configuration, observability, version provenance, or future capabilities.

The Response Normalizer exists to be that **single orchestration boundary**. It is
the one component through which all normalization flows, and the one place where
profile, configuration, framework coordination, and result production are
governed.

### 1.2 The Normalizer orchestrates; it does not normalize

> **Principle**
> **The Response Normalizer coordinates normalization; it never performs it.** What
> structure a response expresses is recovered by the normalization
> **responsibilities** (Response Normalization Contract §13) and assembled by the
> framework into a `NormalizationResult` (which carries the `ParsedResponse`). The
> Normalizer decides *how the act of normalization is run* — which profile, which
> configuration — never *what structure is recovered* and never *whether it is
> well-formed*.

| Concern | Owned by | Question it answers |
| ------- | -------- | ------------------- |
| **Orchestration** | Response Normalizer | *With what profile and configuration is normalization executed, and how is its result produced?* |
| **Normalization** | Normalization Responsibilities | *What structure does this response express, and what facts does it record?* |
| **Assembly** | Normalization Framework + Canonical Models | *What is the single result — the `ParsedResponse` plus observations — of the run?* |
| **Responsibility definition** | Normalization Responsibility Catalog | *Which responsibilities exist and what does each mean?* |

### 1.3 What this document is **not**

| This document is NOT | Because |
| -------------------- | ------- |
| An implementation guide | It defines *what* the Normalizer coordinates, never *how* it is built. |
| A normalization specification | Normalization philosophy lives in the Response Normalization Contract. |
| A canonical-model definition | `ParsedResponse` and the result aggregate are defined in the Validation Canonical Models. |
| A responsibility specification | Responsibility identity and meaning live in the Normalization Responsibility Catalog. |
| A provider or technology document | No model, vendor, language, framework, or serialization format is referenced. |

---

## 2. Scope

### 2.1 What the Normalizer owns

| Owned responsibility | Description |
| -------------------- | ----------- |
| **Normalization orchestration** | Coordinating the whole act of normalization from input to result. |
| **Profile selection** | Choosing the Normalization Profile that governs which responsibilities apply (§11). |
| **Configuration application** | Applying the resolved `NormalizationConfiguration` policy (§8). |
| **Framework coordination** | Driving the Normalization Framework (registry + pipeline) to execute the responsibilities. |
| **Pipeline execution** | Invoking the pipeline **exactly once**, in the framework's defined manner (§7). |
| **Execution context creation** | Producing the immutable `NormalizationExecutionContext` for the run (§10). |
| **Result production** | Returning the single canonical `NormalizationResult` unchanged. |
| **Observability** | Exposing the run's execution context for tracing (§13). |
| **Exception translation** | Classifying and surfacing orchestration failures distinctly from normalization facts (§12). |

### 2.2 What the Normalizer does **not** own

| Not owned by the Normalizer | Owned elsewhere |
| --------------------------- | --------------- |
| **Normalization logic** | Normalization responsibilities (Responsibility Catalog). |
| **Responsibility implementations** | The conforming responsibility implementations. |
| **`ParsedResponse` creation** | The responsibilities that recover structure (Response Normalization Contract §5). |
| **The canonical models** | Validation Canonical Models (`ParsedResponse`, `NormalizationResult`). |
| **The execution context's shape** | The `NormalizationExecutionContext` model and its builder. |
| **Reasoning** | AI Reasoning Contract. |
| **AI execution** | Requirement Analysis Service + provider framework. |
| **Validation** | Response Validator (the first consumer of the result). |
| **Persistence / reporting** | Output / governance layers (future). |

> **Architectural Decision**
> The Normalizer is deliberately **narrow**. It coordinates a result; it does not
> recover structure, record facts, judge, store, or report it. Mixing
> orchestration with normalization, validation, or persistence would couple
> independently evolving concerns and dissolve the single-boundary guarantee.

---

## 3. Architectural Principles

These eleven principles are binding. Every conforming Response Normalizer
implementation must satisfy all of them simultaneously.

### 3.1 Single Orchestration Boundary

> **Principle** — Normalization enters the subsystem through the Normalizer and
> nowhere else. There is exactly one doorway, so profile, configuration,
> observability, and provenance are governed in one place.

### 3.2 No Normalization Logic

> **Principle** — The Normalizer never parses, inspects, recovers structure,
> determines an outcome, or records an observation. It coordinates the parts that
> do. **Orchestrate, never normalize.**

### 3.3 Exactly-Once Execution

> **Principle** — Each call runs the pipeline **once** — no retries, loops,
> recursion, or parallel invocation. One input yields one coordinated run and one
> result.

### 3.4 Dependency Injection

> **Principle** — The registry, pipeline, and platform-default configuration are
> **injected**, never constructed inside the Normalizer. The responsibility set is
> therefore fixed, explicit, and testable.

### 3.5 Framework Reuse

> **Principle** — The Normalizer **reuses** the Normalization Framework and the
> existing execution-context builder; it duplicates no framework logic. The
> framework is a replaceable collaborator behind a stable contract.

### 3.6 Deterministic Orchestration

> **Principle** — Same input, profile, and configuration ⇒ the same orchestration
> process. The Normalizer introduces no randomness, hidden state, or ordering of
> its own; it trusts the framework's deterministic execution.

### 3.7 Provider Independence

> **Principle** — The Normalizer references no provider, model, vendor, or
> serialization format. It accepts the already-provider-independent `LLMResponse`
> and strengthens, never weakens, provider independence.

### 3.8 Configuration Resolution

> **Principle** — Runtime behaviour is resolved through a fixed precedence
> hierarchy (§8), never through scattered or hidden defaults.

### 3.9 Exception Translation

> **Principle** — Framework exceptions are **translated** at the boundary into
> orchestration exceptions; framework internals never leak to callers (§12).

### 3.10 Observability First

> **Principle** — Every run exposes its immutable execution context for tracing.
> Observability is a read-only surface; it never performs or alters normalization.

### 3.11 Future Extensibility

> **Principle** — New capabilities (responsibility selection by profile, additional
> configuration layers, new profiles) are added **behind** the single entry point,
> never by changing the orchestration contract.

---

## 4. Architecture Overview

The Response Normalizer sits between the AI generation layer (which produces the
`LLMResponse`) and the normalization machinery (which recovers its structure). It
is the **only** component that crosses the boundary into the Normalization
Framework.

```text
        ┌─────────────────────────────────────────────┐
        │                 LLMResponse                  │  provider-independent output
        └───────────────────────┬─────────────────────┘
                                │  input to normalization
                                ▼
        ┌─────────────────────────────────────────────┐
        │             Response Normalizer              │  ◄── single orchestration
        │               (orchestration)                │      boundary
        └───────┬───────────────────────────┬─────────┘
                │ coordinates                │ executes ONCE
                ▼                            ▼
        ┌───────────────┐            ┌───────────────────┐
        │ Normalization │            │  Normalization    │
        │  Framework    │ ─ builds ─►│  Pipeline         │
        │ (registry)    │            └─────────┬─────────┘
        └───────────────┘                      │ runs (registration order)
                                               ▼
                                     ┌───────────────────┐
                                     │  Normalization    │  one responsibility each;
                                     │  Responsibilities │  they recover structure
                                     └─────────┬─────────┘
                                               │ produce facts + ParsedResponse
                                               ▼
        ┌─────────────────────────────────────────────┐
        │             NormalizationResult              │  the single output (aggregate):
        │   ParsedResponse · observations · telemetry  │  ParsedResponse + facts
        └───────────────────────┬─────────────────────┘
                                │  consumed by
                                ▼
        ┌─────────────────────────────────────────────┐
        │              Response Validator              │  first consumer (never normalizes)
        └─────────────────────────────────────────────┘
```

### 4.1 Relationship explanations

| Relationship | Meaning |
| ------------ | ------- |
| **LLMResponse → Normalizer** | The generation layer hands over the provider-independent response; this is the *only* input the Normalizer needs to begin. |
| **Normalizer → Normalization Framework** | The Normalizer drives the framework (an injected registry and pipeline). It never registers responsibilities ad hoc. |
| **Framework → Pipeline** | The framework executes responsibilities in registration order; the Normalizer never orders them itself. |
| **Pipeline → Responsibilities** | The pipeline invokes each responsibility; the Normalizer never calls one directly. |
| **Responsibilities → NormalizationResult** | Facts and the `ParsedResponse` are assembled into the single aggregate result, which the Normalizer returns unchanged. |
| **NormalizationResult → Response Validator** | Validation is the first consumer; it reads the `ParsedResponse` and observations, and never normalizes. |

> **Architectural Decision — the Normalizer orchestrates; responsibilities
> normalize; the framework executes.** The `ParsedResponse` is **created by
> responsibilities**, not by the Normalizer; the `NormalizationResult` **aggregates**
> that `ParsedResponse` together with the recorded observations and telemetry. The
> Normalizer owns the *coordination*, never the *content*.

---

## 5. Responsibilities

The Normalizer's responsibility is **permanently limited** to coordination. Each
act below is orchestration; none is normalization.

| # | Responsibility | Description |
| - | -------------- | ----------- |
| 1 | **Resolve configuration** | Resolve the effective `NormalizationConfiguration` through the fixed hierarchy (§8). |
| 2 | **Resolve the profile** | Select and validate exactly one Normalization Profile for the run; default Standard (§11). |
| 3 | **Create the execution context** | Build the immutable `NormalizationExecutionContext` with full version provenance (§10). |
| 4 | **Coordinate the pipeline** | Invoke the framework pipeline **exactly once** with the resolved configuration. |
| 5 | **Return the result** | Return the single `NormalizationResult` unchanged. |

> **Architectural Decision**
> These five acts are the **whole** of the Normalizer. It does nothing else — no
> inspection, interpretation, repair, retry, logging, persistence, or reporting.
> Adding any such behaviour is an architecture change requiring an ADR.

---

## 6. Non-responsibilities

The Normalizer **MUST NEVER**:

| It never… | Because that belongs to |
| --------- | ----------------------- |
| **Parses** text, JSON, XML, or any format | a normalization responsibility |
| **Normalizes** / recovers structure | a normalization responsibility |
| **Repairs** a malformed response | nothing — repair is forbidden platform-wide (Contract §3.2) |
| **Creates a `ParsedResponse`** | the responsibilities (Contract §5) |
| **Creates observations** | the responsibilities (Contract §8) |
| **Judges** or assigns severity / verdict | validation (Contract §10) |
| **Validates** | the Response Validator |
| **Mutates the `LLMResponse`** | nothing — the input is immutable |
| **Implements a responsibility** | the Responsibility Catalog |
| **Contains business logic** | downstream domain layers |

> **Architectural Decision**
> The prohibitions above are **frozen**. A Normalizer that parsed, normalized,
> repaired, judged, created a `ParsedResponse`, recorded an observation, or mutated
> its input would collapse the boundary between *orchestrating* and *normalizing*
> and is non-conforming by definition.

---

## 7. Execution Flow

One call to the single public operation produces one coordinated run.

```text
   LLMResponse
        │
        ▼
   Response Normalizer
        │  1. resolve configuration (hierarchy §8)
        │  2. resolve + validate profile (default Standard §11)
        │  3. build NormalizationExecutionContext (version provenance §10)
        │  4. invoke the pipeline EXACTLY ONCE
        ▼
   Normalization Framework  ──►  Normalization Pipeline
        │                              │ runs responsibilities in registration order
        │                              ▼
        │                        Normalization Responsibilities
        │                              │ recover structure → ParsedResponse + observations
        ▼                              ▼
   NormalizationResult  ◄───── assembled by the framework (aggregate)
        │
        ▼
   returned UNCHANGED to the caller
```

### 7.1 Sequence

| Step | Actor | Action |
| ---- | ----- | ------ |
| 1 | Caller | Invokes the single public operation with an `LLMResponse`. |
| 2 | Normalizer | Resolves configuration; resolves and validates the profile. |
| 3 | Normalizer | Builds the immutable execution context; records it for observability. |
| 4 | Normalizer | Invokes the pipeline **once**, passing the resolved configuration. |
| 5 | Framework | Runs the registered responsibilities; assembles the `NormalizationResult`. |
| 6 | Normalizer | Returns the `NormalizationResult` unchanged. |

> **Worked example.** A caller submits an `LLMResponse`. The Normalizer resolves
> the platform-default configuration, resolves the Standard profile, builds an
> execution context stamped with the framework/pipeline/registry/responsibility-
> catalog/contract versions, and runs the pipeline once. The framework returns a
> `NormalizationResult` whose `ParsedResponse` holds the recovered structure and
> whose observation collection records any un-judged facts. The Normalizer returns
> that result unchanged — it never inspects the structure or the observations.

---

## 8. Configuration Resolution

Configuration is resolved through a **fixed precedence hierarchy**, lowest to
highest:

```text
   Platform Defaults ─► Profile ─► Execution Configuration ─► Runtime Overrides
```

| Layer | Meaning |
| ----- | ------- |
| **Platform Defaults** | The baseline configuration the Normalizer is constructed with; always present. |
| **Profile** | Configuration implied by the selected Normalization Profile (reserved). |
| **Execution Configuration** | Per-run configuration supplied by a caller (reserved). |
| **Runtime Overrides** | The highest-precedence, last-word overrides (reserved). |

The **highest-precedence layer that is supplied wins**. Today only **Platform
Defaults** flow through the public path; the higher layers exist in the resolution
contract so the hierarchy is complete and ready to extend without changing the
public API.

> **Architectural Decision**
> The hierarchy exists **now**, even though only one layer is wired, so that future
> per-profile, per-execution, and per-runtime configuration can be introduced
> **without changing the orchestration contract**. Resolution is pure precedence —
> no business logic and no influence on the recovered structure or facts.

---

## 9. Dependency Injection

The Normalizer is assembled from three injected collaborators:

| Injected dependency | Role |
| ------------------- | ---- |
| **Registry** | The normalization registry that holds the responsibility set. |
| **Pipeline** | The pipeline that executes the registered responsibilities. |
| **Configuration** | The platform-default `NormalizationConfiguration`. |

> **Architectural Decision**
> Registry and pipeline are **injected, never constructed internally**. This fixes
> the responsibility set for the Normalizer's lifetime (the pipeline seals the
> registry), makes the subsystem assembly explicit and testable, and lets the
> responsibility set evolve **without changing the Normalizer**. Construction
> validates the collaborators' types and fails as an orchestration error; it never
> normalizes.

---

## 10. Execution Context

| Aspect | Statement |
| ------ | --------- |
| **Purpose** | Record the **execution identity** of one normalization run — which run, under which framework/contract versions, and when it began. |
| **Ownership** | The Normalizer **creates** the context per run and holds the most recent one for observability; it does not own the context's *shape* (that is the `NormalizationExecutionContext` model). |
| **Lifecycle** | Built once at the start of a run, immutable thereafter, replaced (not mutated) on the next run. |
| **Relationship** | The Normalizer **reuses** the existing `NormalizationExecutionContext` and its builder; it duplicates no execution-identity logic. |

> **Architectural Decision — the execution context carries execution identity
> only.** It records *which execution produced this normalization*, never any
> normalization fact, observation, `ParsedResponse`, or judgment. Because the input
> `LLMResponse` carries no upstream execution or correlation identity (the subsystem
> is source-decoupled), those context fields are legitimately absent today; every
> version field is stamped from the centralized framework constants.

> **Architectural Decision — the execution context carries no profile.** Unlike the
> validation execution context, the `NormalizationExecutionContext` deliberately has
> **no profile field** (normalization has no profile analogue on the context, per
> its frozen design). The Normalizer therefore **resolves and validates** the
> profile as a run step — a bad profile still fails as a `ProfileResolutionError` —
> but does not stamp it onto the context. This is an intentional, governed deviation
> from the Response Validator, not an omission.

---

## 11. Profiles

A **Normalization Profile** names a breadth of normalization. The Normalizer
selects exactly one profile per run.

| Property | Statement |
| -------- | --------- |
| **Purpose** | Name the breadth of normalization a run applies. |
| **Metadata only** | A profile carries a name and a description — nothing more. |
| **No responsibility lists** | A profile does **not** yet enumerate responsibilities; selection behaviour arrives with the first concrete responsibilities. |
| **Canonical set** | Minimal · Standard (default) · Strict · Enterprise. |
| **Future extensibility** | New canonical or custom profiles extend the set behind the same profile shape. |

> **Architectural Decision — profiles are metadata only.** This mirrors the
> Validation Profile philosophy exactly. A profile *names* breadth; it never carries
> responsibility logic. The canonical set deliberately omits a `COMPLIANCE` profile
> (a validation-specific concern): normalization has no rules, layers, or severity,
> so its profiles are breadth-oriented only.

---

## 12. Exception Boundary

Framework exceptions and orchestration exceptions are two distinct families. The
Normalizer **translates** the former into the latter at its boundary.

```text
   Framework exceptions (framework error family)
        │  raised by the registry / pipeline / a responsibility
        ▼
   Response Normalizer  ── translates ──►  Orchestration exceptions
                                            (orchestration error family)
```

| Orchestration exception | Raised when |
| ----------------------- | ----------- |
| **base orchestration error** | (abstract) the root all orchestration failures share. |
| **Configuration resolution error** | a valid configuration cannot be resolved. |
| **Profile resolution error** | the profile cannot be resolved. |
| **Pipeline construction error** | the injected registry or pipeline is not of the expected framework type. |
| **Normalization execution error** | the pipeline run fails; the framework exception is translated and preserved as the cause. |

> **Architectural Decision — framework exceptions never leak.** Callers depend on
> the orchestration exception family, never on framework internals, so the framework
> may evolve freely beneath the boundary. Crucially, a `MALFORMED` outcome or a
> recorded observation is a **normal fact** carried by the `NormalizationResult` — it
> is **never** an exception. An orchestration error means the run *could not be
> conducted*, never that the response was judged (normalization never judges —
> Contract §10).

---

## 13. Observability

| Surface | Statement |
| ------- | --------- |
| **`last_execution_context`** | Exposes the immutable execution context of the most recent run. |
| **Read-only** | Reading it never performs, alters, or re-runs normalization. |
| **No other mutable state** | The Normalizer holds only its injected collaborators and the most-recent execution context; nothing else changes at runtime. |

> **Architectural Decision**
> Observability is a **single, read-only surface**. It exists so a run can be traced
> to its execution identity and version provenance without re-running it. The
> Normalizer exposes no pipeline state, no responsibility internals, and no mutable
> run counters.

---

## 14. Relationship to the Response Validator

The Response Normalizer is the **sibling** of the Response Validator: the same
orchestration architecture, with deliberate differences that track the frozen
normalization architecture.

| Aspect | Response Validator | Response Normalizer |
| ------ | ------------------ | ------------------- |
| Single entry point | ✓ | ✓ |
| Orchestrate, never do the work | ✓ (never validates) | ✓ (never normalizes) |
| Input | the analysed AI result (carries execution/analysis identity) | the raw provider-independent response (carries no identity) |
| Output | the validation result (verdict + findings) | the normalization result (facts; **no** verdict) |
| Execution context | carries a **profile** | carries **no** profile field |
| Profiles | five (includes a compliance profile) | four (no compliance profile) |
| Dependency injection | registry + pipeline + defaults | registry + pipeline + defaults |
| Configuration hierarchy | Platform → Profile → Execution → Runtime | identical |
| Exception translation | framework → orchestration | identical shape |
| Correlation identity | carried from the input | absent today (input carries none) |

> **Architectural Decision — shared architecture, intentional differences.** The
> two orchestration boundaries share their skeleton by design, so the platform has
> one predictable orchestration shape. Every difference is a consequence of a frozen
> upstream decision: normalization produces *facts, not judgments* (Contract §10);
> its input is *source-decoupled*; and its execution context deliberately omits a
> profile field. The Normalizer mirrors the Validator's **architecture**, never its
> implementation.

---

## 15. Future Evolution

The Response Normalizer is designed to remain **thin and stable** while everything
around it grows.

| Reserved direction | Intent | Constraint |
| ------------------ | ------ | ---------- |
| **Normalization responsibilities** | `NORMALIZATION-0001…0005` (and beyond) register into the injected registry. | The Normalizer needs **no change** to orchestrate them. |
| **Profile-driven selection** | Profiles gain responsibility-selection behaviour. | Behind the same profile shape; the entry point is unchanged. |
| **Additional configuration layers** | Profile / execution / runtime configuration become wired. | The hierarchy already exists; the public API is unchanged. |
| **`ParsedResponse` evolution** | The canonical representation grows additively. | Owned by the canonical models; the Normalizer never touches its shape. |
| **New consumers** | New platform subsystems read the `NormalizationResult`. | Read-only consumers; no orchestration change. |

> **Architectural Decision — the Normalizer stays thin permanently.** As
> responsibilities, profiles, configuration, and `ParsedResponse` evolve, the
> Normalizer's contract does not. New capabilities sit **behind** the single entry
> point. A change that thickens the Normalizer with normalization, judgment, or
> business logic is non-conforming.

---

## 16. Relationships

The Response Normalizer realises the *orchestration* half of the subsystem the
Response Normalization Contract governs, and depends on the surrounding
architecture.

```text
   [Requirement Analysis Service]      (produces the LLMResponse)
            │ emits generated_text + execution_status
            ▼
   [Response Normalization Contract]   (governs the subsystem, ParsedResponse lifecycle)
            │
            ▼
   [Response Normalizer]  ◄── THIS DOCUMENT (the orchestration boundary)
            │ coordinates ▼
   [Response Normalization Framework]  (registry · pipeline · responsibilities)
            │ assembles ▼
   [Validation Canonical Models]       (ParsedResponse · NormalizationResult)
            │
            ▼
   [Response Validator]                (first consumer; reads ParsedResponse + observations)
```

| Document | Relationship to this specification |
| -------- | ---------------------------------- |
| **Response Normalization Contract** | Governs the subsystem the Normalizer is the entry point to; defines the responsibilities it orchestrates and the `ParsedResponse` lifecycle. |
| **Validation Canonical Models** | Define `ParsedResponse` and the `NormalizationResult` the Normalizer returns. |
| **Response Normalization Framework** | Provides the registry, pipeline, and responsibility contract the Normalizer coordinates. |
| **Response Validator Architecture** | The mirrored orchestration pattern; the first consumer of the Normalizer's output. |
| **AI Response Validation Architecture** | Describes the consumer that reads the `NormalizationResult`; the Normalizer never validates. |
| **Requirement Analysis Service** | Produces the `LLMResponse` the Normalizer accepts. |

> **Architectural Decision**
> This specification introduces **no new dependency direction**. It names the one
> component that already had to exist between generation and validation. It depends
> upward on the analysis service and the normalization contract, and is consumed
> downward by validation and every future consumer of the `NormalizationResult`.

---

## 17. Architecture Freeze

> **Architectural Decision — Architecture Freeze**
> With this document, the following become **frozen architectural contracts** for
> the Response Normalization orchestration boundary:
>
> - **Single public API** (§5, §7) — one operational entry point returning a
>   `NormalizationResult`.
> - **Single orchestration boundary** (§1, §3.1) — normalization enters through the
>   Normalizer and nowhere else.
> - **Dependency injection** (§9) — registry, pipeline, and configuration are
>   injected, never constructed internally.
> - **Configuration hierarchy** (§8) — Platform Defaults → Profile → Execution →
>   Runtime; highest precedence wins.
> - **Execution context** (§10) — execution identity only; no profile field; no
>   normalization data.
> - **Exception translation** (§12) — framework exceptions are translated into
>   orchestration exceptions and never leak.
> - **Observability** (§13) — a single read-only `last_execution_context`; no other
>   mutable runtime state.
> - **Exactly-once execution** (§3.3, §7) — the pipeline runs once per call.
> - **No normalization logic** (§2, §6) — the Normalizer never parses, normalizes,
>   repairs, judges, creates a `ParsedResponse`, records observations, or mutates
>   its input.
>
> **Implementation may evolve freely** beneath these contracts. **The architecture
> may evolve only through an approved Architecture Decision Record (ADR).** A change
> that violates any frozen contract above is non-conforming by definition.

> **Definition of Done**
> This document is the definitive orchestration specification for the Response
> Normalization subsystem. It establishes the Response Normalizer as the single
> orchestration boundary and governs the entry point, execution flow, execution
> context, configuration and its hierarchy, profile selection, dependency
> injection, pipeline coordination, exception translation, observability, result
> production, and future evolution. It governs **only** orchestration — never
> normalization, validation, reasoning, providers, canonical-model shape, or the
> responsibilities it coordinates. It is implementation-independent and remains
> valid even if the platform is reimplemented on an entirely different technology
> stack, serialization format, or AI provider.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Response Normalizer** | The single orchestration boundary that coordinates a normalization run; it orchestrates, it does not normalize (§1). |
| **Orchestration** | Coordination of the ordered steps required to run one normalization (§5, §7). |
| **LLMResponse** | The provider-independent AI response handed to the Normalizer as input (§4). |
| **Normalization Profile** | A named, metadata-only selection of normalization breadth chosen by the Normalizer (§11). |
| **NormalizationConfiguration** | The runtime policy governing a normalization run (§8). |
| **Configuration Hierarchy** | The fixed precedence resolving configuration sources (§8). |
| **NormalizationExecutionContext** | The immutable execution identity carrying a run's version provenance and identifiers (§10). |
| **Normalization Framework** | The registry, responsibility contract, and pipeline the Normalizer coordinates (§4, §9). |
| **Normalization Responsibility** | A catalogued `NORMALIZATION-00NN` behaviour that recovers structure or records facts (§4). |
| **ParsedResponse** | The canonical, shared normalized structure created by the responsibilities, carried on the `NormalizationResult` (§4). |
| **NormalizationResult** | The single, immutable aggregate output of a run — `ParsedResponse` plus observations and telemetry (§4). |
| **Exception Boundary** | The line at which framework exceptions are translated into orchestration exceptions (§12). |

## Appendix B — Conformance Checklist

A Response Normalizer implementation conforms to this architecture only if every
box can be checked:

- [ ] Is the **single entry point** — all normalization flows through it.
- [ ] **Selects exactly one profile** per run, defaulting to Standard.
- [ ] **Applies an explicit configuration**, resolved through the fixed hierarchy.
- [ ] Contains **no normalization logic** — it orchestrates, it never recovers structure.
- [ ] **Creates no `ParsedResponse`** and **records no observation** — responsibilities do.
- [ ] **Never parses, repairs, judges, validates, or mutates the `LLMResponse`.**
- [ ] **Injects** its registry, pipeline, and configuration; it constructs none internally.
- [ ] **Reuses** the execution-context builder; it duplicates no execution-identity logic.
- [ ] Creates a **`NormalizationExecutionContext`** of execution identity only — no profile, no normalization data.
- [ ] Invokes the pipeline **exactly once** per call — no retries, loops, or parallelism.
- [ ] **Returns a `NormalizationResult` only** — never pipeline state or responsibility mechanics.
- [ ] **Translates** framework exceptions into orchestration exceptions; framework internals never leak.
- [ ] Treats a `MALFORMED` outcome or an observation as a **normal fact**, never an exception.
- [ ] Exposes a **single read-only** `last_execution_context`; holds no other mutable runtime state.
- [ ] Is **provider- and format-independent** — no provider, vendor, endpoint, or format influences it.
- [ ] Is **future extensible** — new capabilities sit behind the single entry point.
- [ ] Remains **implementation-independent** (no language, framework, storage, or provider assumptions).
