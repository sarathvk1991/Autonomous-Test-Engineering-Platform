# Response Validator Architecture

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Orchestration Boundary |
| Status               | Approved — foundational                                           |
| Scope                | Orchestration of response validation within the platform           |
| Governs              | The single entry point, execution flow, context, lifecycle, configuration, profile selection, and result production of validation |
| Depends on           | AI Response Validation Architecture · Validation Canonical Models · Validation Rule Catalog |
| Audience             | Solution Architects · Technical Architects · Lead Engineers · QA Architects · Platform Engineers |
| Implementation-bound | No — valid regardless of language, framework, persistence, or AI provider |

> **Architectural Decision**
> The Response Validator is the **exclusive entry point into the Response
> Validation subsystem**. Every request to validate AI output flows through it and
> only through it. The Validator does **not** validate — it **orchestrates**
> validation, coordinating the framework, the pipeline, the rules, the profile,
> and the configuration to produce one canonical result.

> **Amendment — ADR-0003 (canonical input).** The Validator's single input is the
> **`ValidationInput`** canonical model — the binding of the analysed response
> (`AnalysisResult`) and its same-execution `NormalizationResult` (which carries the
> shared `ParsedResponse` and the observations). This supersedes the earlier
> single-input `AnalysisResult` so that Syntax-onward rules can read normalized facts
> without re-deriving structure. The Single Entry Point is unchanged — still one
> public method, one input object; the object is simply richer. The Validator never
> normalizes and never calls the Response Normalizer; the `ValidationInput` is
> assembled by the handoff seam above both orchestration boundaries (ADR-0003 §4).

---

## 1. Purpose

### 1.1 Why the Response Validator exists

The Response Validation subsystem is composed of several governed parts: the
Validation Rule Catalog (which rules exist), the Validation Framework (the
registry and rule contract), the Validation Pipeline (ordered execution), the
validation rules (single-concern checks), and the Validation Canonical Models
(the information model). Something must **coordinate** these parts into a single,
repeatable act of validation. If every caller wired those parts together itself:

- **Orchestration would scatter** — each caller would select profiles, build a
  registry, construct a pipeline, and assemble a result in its own way.
- **Inconsistency would creep in** — two callers could validate the same response
  under subtly different rule sets, defeating determinism and audit.
- **No governance choke point** — there would be no single place to enforce
  configuration, observability, version provenance, or future capabilities.

The Response Validator exists to be that **single orchestration boundary**. It is
the one component through which all validation flows, and the one place where
profile, configuration, framework coordination, and result production are
governed.

### 1.2 The Validator orchestrates; it does not validate

> **Principle**
> **The Response Validator coordinates validation; it never performs it.** Whether
> a response is trustworthy is decided by the rules (Validation Rule Catalog) and
> assembled by the framework into a `ValidationResult` (Validation Canonical
> Models). The Validator decides *how the act of validation is run* — which
> profile, which configuration, in what order — never *what the verdict is*.

| Concern | Owned by | Question it answers |
| ------- | -------- | ------------------- |
| **Orchestration** | Response Validator | *With what profile and configuration is validation executed, and how is its result produced?* |
| **Validation** | Validation Rules | *Is this one concern satisfied?* |
| **Assembly** | Validation Framework + Canonical Models | *What is the single result of all findings?* |
| **Rule definition** | Validation Rule Catalog | *Which rules exist and what does each mean?* |

### 1.3 What this document is **not**

| This document is NOT | Because |
| -------------------- | ------- |
| An implementation guide | It defines *what* the Validator coordinates, never *how* it is built. |
| A validation specification | Validation philosophy lives in the AI Response Validation Architecture. |
| A rule specification | Rule identity and meaning live in the Validation Rule Catalog. |
| A provider or technology document | No model, vendor, language, framework, or format is referenced. |

---

## 2. Scope

### 2.1 What the Validator owns

| Owned responsibility | Description |
| -------------------- | ----------- |
| **Validation orchestration** | Coordinating the whole act of validation from input to result. |
| **Profile selection** | Choosing the Validation Profile that governs which rules apply (§6). |
| **Configuration application** | Applying the runtime `ValidationConfiguration` policy (§7). |
| **Framework coordination** | Driving the Validation Framework to register rules and build the pipeline. |
| **Pipeline execution** | Invoking the pipeline once, in the framework's defined manner. |
| **Result production** | Returning the single canonical `ValidationResult` (§17). |
| **Observability** | Emitting execution and correlation metadata for every run (§19). |
| **Error translation** | Classifying and surfacing orchestration failures distinctly from verdicts (§16). |

### 2.2 What the Validator does **not** own

| Not owned by the Validator | Owned elsewhere |
| -------------------------- | --------------- |
| **Validation logic** | Validation rules (Validation Rule Catalog). |
| **Rule implementations** | The conforming rule implementations. |
| **Canonical models** | Validation Canonical Models. |
| **Reasoning** | AI Reasoning Contract. |
| **Prompting** | Prompt Framework. |
| **AI execution** | Requirement Analysis Service + provider framework. |
| **Persistence** | Output / storage layer (future). |
| **Reporting** | Reporting / governance layer (future). |
| **CP1** | CP1 Validation Architecture (future). |

> **Architectural Decision**
> The Validator is deliberately **narrow**. It coordinates a result; it does not
> judge it, store it, report it, or act on it. Mixing orchestration with
> validation, persistence, or downstream gating would couple independently
> evolving concerns and dissolve the single-boundary guarantee.

---

## 3. Architectural Position

The Response Validator sits between the analysis layer (which produces the
response) and the validation machinery (which judges it). It is the **only**
component that crosses the boundary into the Validation Framework.

```text
        ┌─────────────────────────────────────────────┐
        │              AnalysisResult                  │  the analysed AI output
        └───────────────────────┬─────────────────────┘
                                │  input to validation
                                ▼
        ┌─────────────────────────────────────────────┐
        │             Response Validator               │  ◄── single orchestration
        │               (orchestration)                │      boundary
        └───────┬───────────────────────────┬─────────┘
                │ coordinates                │ executes
                ▼                            ▼
        ┌───────────────┐            ┌───────────────────┐
        │  Validation   │            │   Validation      │
        │  Framework    │ ─ builds ─►│   Pipeline        │
        └───────────────┘            └─────────┬─────────┘
                                               │ runs (in layer order)
                                               ▼
                                     ┌───────────────────┐
                                     │  Validation Rules │  one concern each
                                     └─────────┬─────────┘
                                               │ produce findings
                                               ▼
        ┌─────────────────────────────────────────────┐
        │              ValidationResult                │  the single output
        └─────────────────────────────────────────────┘
```

### 3.1 Relationship explanations

| Relationship | Meaning |
| ------------ | ------- |
| **ValidationInput → Validator** | The handoff seam hands over the `ValidationInput` (analysed response + its `NormalizationResult`; ADR-0003); this is the *only* input the Validator needs to begin. |
| **Validator → Validation Framework** | The Validator drives the framework to register the selected rules and build a pipeline. It never registers rules ad hoc. |
| **Framework → Validation Pipeline** | The framework constructs the ordered pipeline; the Validator does not order rules itself. |
| **Pipeline → Validation Rules** | The pipeline invokes each rule in layer order; the Validator never calls a rule directly. |
| **Rules → ValidationResult** | Findings are assembled into the single canonical result, which the Validator returns unchanged. |

---

## 4. Guiding Principles

These eleven principles are binding. Every conforming Response Validator
implementation must satisfy all of them simultaneously.

### 4.1 Single Entry Point

**Purpose.** Provide exactly one doorway into validation for the whole platform.

**Rules.**
- All validation requests pass through the Validator.
- No other component builds a registry, constructs a pipeline, or invokes rules.
- New validation workflows are built *on top of* the Validator, not around it.

**Expected behaviour.** Every validated response in the platform was validated by
the Validator.

**Worked example.** A future "re-validate on change" workflow calls the Response
Validator; it does not assemble a pipeline itself.

### 4.2 Single Responsibility

**Purpose.** Keep the Validator focused on orchestration alone.

**Rules.**
- The Validator coordinates steps; it does not validate, persist, or report.
- Logic that is not "coordinate one validation run" does not belong here.

**Expected behaviour.** Deciding whether a finding is blocking is rejected from
the Validator and left to the rules and the result model.

**Worked example.** Computing the overall verdict is the canonical model's
concern; the Validator returns the verdict, it does not derive it.

### 4.3 Deterministic Orchestration

**Purpose.** Ensure the *orchestration sequence* is predictable and repeatable.

**Rules.**
- Given the same input, profile, and configuration, the Validator performs the
  same ordered steps and produces a result of the same shape.
- Non-determinism is confined to the response being validated, never to the
  workflow.

**Expected behaviour.** Re-running validation of the same response under the same
profile and configuration yields an equivalent result.

> **Architectural Decision**
> Determinism applies to **orchestration**, not to the response. The Validator
> guarantees a stable, reproducible *process*; the content under validation is
> whatever the analysis layer produced.

### 4.4 Configuration Driven

**Purpose.** Make runtime behaviour a function of declared configuration, not
hidden defaults.

**Rules.**
- Every run is governed by an explicit `ValidationConfiguration` (§7).
- When none is supplied, a defined default configuration applies.

**Expected behaviour.** Changing observability depth or enabled layers is a
configuration change, never a code change to the Validator.

**Worked example.** A run that collects extra observability detail differs from a
standard run only in its configuration.

### 4.5 Profile Driven

**Purpose.** Make the *breadth* of validation a function of the selected profile.

**Rules.**
- The Validator selects exactly one Validation Profile per run (§6).
- The profile names the rule set; the Validator never hand-picks individual
  rules.

**Expected behaviour.** Switching from Standard to Strict broadens the rule set
without any change to the Validator's logic.

**Worked example.** A compliance run differs from a standard run only in its
selected profile.

### 4.6 Framework Independence

**Purpose.** Make the validation framework a replaceable collaborator.

**Rules.**
- The Validator depends on the framework's *contract*, never on its internals.
- Replacing or evolving the framework must not change the orchestration contract.

**Expected behaviour.** A framework internal change is invisible to callers of
the Validator.

### 4.7 Rule Independence

**Purpose.** Preserve the catalog's rule-independence guarantee at the
orchestration layer.

**Rules.**
- The Validator never assumes a rule's order, output, or existence beyond the
  profile selection.
- The Validator never couples two rules.

**Expected behaviour.** Rules remain deterministic, stateless, and parallelizable
(Validation Rule Catalog §16); the Validator does nothing to undermine this.

**Worked example.** The Validator does not feed one rule's finding into another;
it only collects the assembled result.

### 4.8 Immutable Inputs

**Purpose.** Guarantee the response under validation is never altered.

**Rules.**
- The Validator treats the `AnalysisResult` as read-only.
- It never mutates, repairs, or reshapes the input.

**Expected behaviour.** The exact response handed in is the exact response
validated and preserved on the result.

### 4.9 Immutable Outputs

**Purpose.** Guarantee the result is a stable, final record.

**Rules.**
- The Validator returns the `ValidationResult` unaltered.
- It never edits the verdict, the findings, or the assembled result.

**Expected behaviour.** The result a caller receives is identical to the one the
framework assembled.

> **Principle**
> The Validator is a **conductor, not an author**. It transports an immutable
> input to an immutable output; it composes neither the response nor the verdict.

### 4.10 Observability First

**Purpose.** Make every run traceable and measurable from the outset.

**Rules.**
- Every run emits execution identity, correlation, profile, configuration,
  timing, and versions (§19).
- Observability is mandatory, not best-effort.

**Expected behaviour.** Each run can be traced end to end by a single correlation
identifier.

### 4.11 Future Extensibility

**Purpose.** Allow new capabilities without breaking existing callers.

**Rules.**
- New behaviours (repair, retry, incremental validation, adaptive profiles) are
  added *behind* the existing entry point (§15).
- The public orchestration responsibilities defined here remain stable.

**Expected behaviour.** Adding a retry capability changes internal behaviour only;
callers request validation exactly as before.

---

## 5. Responsibilities

The Validator performs a fixed, ordered orchestration sequence. The steps are
stable even as internal mechanics evolve.

```text
   1. Receive AnalysisResult
                │
                ▼
   2. Validate configuration
                │
                ▼
   3. Select Validation Profile
                │
                ▼
   4. Build Rule Registry        (delegate → Validation Framework)
                │
                ▼
   5. Construct Validation Pipeline (delegate → Validation Framework)
                │
                ▼
   6. Execute Pipeline
                │
                ▼
   7. Collect ValidationResult
                │
                ▼
   8. Return ValidationResult
```

| Step | Name | Description |
| ---- | ---- | ----------- |
| 1 | **Receive ValidationInput** | Accept one `ValidationInput` (the `AnalysisResult` bound to its `NormalizationResult`; ADR-0003) as the input. The Validator confirms the input is structurally present, not whether its verdict is good. |
| 2 | **Validate configuration** | Confirm the supplied (or default) `ValidationConfiguration` is present and coherent before any work begins (§7). |
| 3 | **Select Validation Profile** | Choose exactly one profile, which names the rule set to apply (§6). |
| 4 | **Build Rule Registry** | Ask the framework to register the profile's rules (rule discovery, §10). The Validator never enumerates rules itself. |
| 5 | **Construct Validation Pipeline** | Ask the framework to build the ordered pipeline from the registry (§8). |
| 6 | **Execute Pipeline** | Invoke the pipeline once against the response, in the framework's defined manner. |
| 7 | **Collect ValidationResult** | Receive the single canonical result the framework assembles. |
| 8 | **Return ValidationResult** | Return the result unchanged to the caller (§17). |

> **Worked example**
> A technical lead triggers validation of an analysed *"payment refund"* response.
> The Validator (1) receives the `AnalysisResult`, (2) validates the configuration,
> (3) selects the *Standard* profile, (4) has the framework register the Standard
> rule set, (5) constructs the pipeline, (6) executes it once, (7) collects the
> `ValidationResult` (verdict `PASSED_WITH_WARNINGS`), and (8) returns it. Whether
> the verdict is *acted upon* is decided downstream.

---

## 6. Validation Profiles

A **Validation Profile** is a named selection of rules (Validation Rule Catalog
§13). The Validator selects exactly one profile per run; the rules never know
which profile invoked them.

| Profile | Intent | Rule breadth |
| ------- | ------ | ------------ |
| **Minimal** | The lightest viable gate. | Core rules only. |
| **Standard** | The default balanced gate. | Core + common Extended rules. |
| **Strict** | Maximum depth for high-stakes analysis. | Core + all Extended rules. |
| **Compliance** | Coverage tuned to regulatory obligations. | Core + Extended + Organization (compliance) rules. |
| **Enterprise** | Organization-wide policy enforcement. | Core + Extended + Organization rules. |

### 6.1 Selection rules

- Exactly **one** profile governs a run.
- A profile may only *select* rules; it can never disable a Core rule (Validation
  Rule Catalog §10).
- The selected profile is recorded in the run's observability and provenance
  (§18, §19).

### 6.2 Default profile

> **Architectural Decision**
> When no profile is explicitly requested, the Validator applies the **Standard**
> profile. The default is a defined architectural choice, not an accident of
> implementation, so that an unqualified validation request has a stable, known
> breadth.

### 6.3 Future custom profiles

Custom and organization-defined profiles are a reserved capability (§15). They
extend the set of selectable profiles; they never change how a profile is
selected or how rules behave.

---

## 7. Configuration

The **ValidationConfiguration** is the runtime policy of a validation run
(Validation Canonical Models). It governs *how thoroughly* validation runs — never
*what is trustworthy*.

| Conceptual field | Meaning |
| ---------------- | ------- |
| **Validation Contract Version** | The validation semantics the run must honour. |
| **Enabled layers** | Which validation layers participate in the run. |
| **Minimum severity** | The observability threshold for surfacing findings by severity. Affects reporting, never the verdict. |
| **Collect statistics** | Whether operational telemetry is captured for the run. |
| **Collect metadata** | Whether free-form metadata is captured for the run. |
| **Future extensions** | Reserved hooks for forthcoming policy without a breaking change. |

> **Principle**
> **Configuration is runtime policy, never business logic.** It may turn a layer
> on or off or tune observability; it can never redefine a severity, a verdict, or
> a rule's concern. Those belong to the catalog and the canonical models, not to a
> run's configuration.

---

## 8. Configuration Hierarchy

Configuration is resolved from multiple sources in a fixed precedence order. The
Validator merges them so that the most specific source wins.

```text
   Platform Defaults        (lowest precedence — the baseline)
          │ overridden by
          ▼
   Profile                  (the selected profile's policy)
          │ overridden by
          ▼
   Execution Configuration  (the configuration supplied for this run)
          │ overridden by
          ▼
   Runtime Overrides        (highest precedence — explicit per-run overrides)
```

| Source | Role |
| ------ | ---- |
| **Platform Defaults** | The baseline policy applied when nothing more specific is given. |
| **Profile** | Policy implied by the selected profile (e.g. breadth of layers). |
| **Execution Configuration** | The explicit `ValidationConfiguration` supplied for this run. |
| **Runtime Overrides** | Narrow, explicit overrides applied to this single run. |

> **Architectural Decision**
> **Highest precedence wins, and precedence is fixed.** Resolution always proceeds
> Platform Defaults → Profile → Execution Configuration → Runtime Overrides, so the
> effective configuration of any run is deterministic and reconstructable. No
> source may reorder the hierarchy, and no override may relax a Core guarantee.

---

## 9. Pipeline Construction

The Validator does not build the pipeline itself; it **coordinates** the framework
to do so from the selected profile and resolved configuration. The construction
is described conceptually — no mechanism is defined.

```text
   Caller            Response             Validation            Validation
     │               Validator             Framework             Pipeline
     │                   │                     │                     │
     │  validate(input)  │                     │                     │
     │ ────────────────► │                     │                     │
     │                   │ resolve config +    │                     │
     │                   │ select profile      │                     │
     │                   │ ─────────────┐      │                     │
     │                   │ ◄────────────┘      │                     │
     │                   │ register rule set   │                     │
     │                   │ ──────────────────► │                     │
     │                   │ registry ready      │                     │
     │                   │ ◄────────────────── │                     │
     │                   │ construct pipeline  │                     │
     │                   │ ──────────────────► │                     │
     │                   │                     │ build (layer order) │
     │                   │                     │ ──────────────────► │
     │                   │ pipeline ready      │                     │
     │                   │ ◄────────────────────────────────────────│
     │                   │                                           │
```

| Construction input | Role |
| ------------------ | ---- |
| **Profile** | Names which rules are registered (§6). |
| **Configuration** | Governs which layers participate and how the run is observed (§7). |
| **Registry** | The framework's catalogue of the selected rules. |
| **Pipeline** | The ordered execution structure the framework builds from the registry. |

> **Principle**
> The Validator **asks** the framework to construct the registry and pipeline; it
> never orders rules, never re-sorts layers, and never embeds construction logic.
> Construction is a framework concern coordinated by the Validator.

---

## 10. Rule Discovery

Rule discovery is the conceptual act of determining which rules participate in a
run. It is fully governed and deterministic.

| Stage | Meaning |
| ----- | ------- |
| **Conform to the Rule Catalog** | Only rules defined and governed by the Validation Rule Catalog are eligible. No ungoverned rule may appear. |
| **Filter by profile** | The selected profile (§6) narrows the eligible rules to the set it names. |
| **Sort by layer** | Eligible rules are ordered by the architecture-mandated layer order (foundational → semantic). |
| **Load into registry** | The ordered rule set is registered with the framework, ready for pipeline construction. |

> **Architectural Decision**
> **Discovery is by governed selection, not by search.** The Validator never
> "finds" rules opportunistically; it selects exactly the catalogued rules the
> profile names, in layer order. This keeps the participating rule set
> deterministic, auditable, and reproducible for any run.

---

## 11. Validator Independence

> **Architectural Decision**
> **The Response Validator must never know individual rule implementations.** It
> coordinates **contracts only** — the framework contract, the profile, the
> configuration, and the canonical result. It does not know what any rule checks,
> how a rule decides, or how a rule is built.

| The Validator knows | The Validator never knows |
| ------------------- | ------------------------- |
| That a profile names a set of rules. | What any individual rule validates. |
| That the framework registers and orders rules. | How a rule reaches its finding. |
| That the pipeline produces a `ValidationResult`. | The internal mechanics of any rule. |

> **Principle**
> The Validator's independence from rule implementations is what lets the catalog
> grow without limit and rules evolve freely — none of it changes the
> orchestration. A Validator that knew a rule's internals would couple
> orchestration to validation and break the single-boundary guarantee.

---

## 12. Execution Context

The **ValidationExecutionContext** is a conceptual runtime context that
accompanies a single validation run. It carries the *orchestration metadata* of
the run — never the validation data.

| Element | Meaning |
| ------- | ------- |
| **Execution identity** | A unique handle for this validation run. |
| **Profile** | The Validation Profile selected for the run (§6). |
| **Configuration** | The resolved `ValidationConfiguration` governing the run (§7, §8). |
| **Timestamps** | When the run started and completed. |
| **Versions** | The version provenance recorded for the run (§18). |
| **Correlation identifiers** | The trace keys linking this run to its originating analysis and downstream consumers. |

> **Architectural Decision**
> **The Execution Context is orchestration metadata only — never validation data.**
> It records *how the run was conducted* (identity, profile, configuration, timing,
> versions, correlation); it never holds findings, verdicts, or any judgement about
> the response. Findings and verdicts live only in the `ValidationResult`. Keeping
> these separate prevents orchestration bookkeeping from ever being mistaken for a
> validation outcome.

---

## 13. Execution Lifecycle

A validation run advances through a fixed, observable lifecycle. The state is
informational; it never changes the verdict.

```text
   ┌─────────┐ configure ┌────────────┐ build  ┌────────────────┐ run  ┌────────────┐
   │ Created │ ─────────►│ Configured │ ──────►│ Pipeline Ready │ ────►│ Executing  │
   └─────────┘           └────────────┘        └────────────────┘      └─────┬──────┘
                                                                             │
                                                       ┌─────────────────────┴───────────┐
                                                       ▼                                 ▼
                                                ┌────────────┐                    ┌────────────┐
                                                │ Completed  │                    │   Failed   │
                                                └────────────┘                    └────────────┘
```

| State | Meaning |
| ----- | ------- |
| **Created** | The run is initiated; the Execution Context exists but no work has begun. |
| **Configured** | Configuration is resolved and validated; the profile is selected. |
| **Pipeline Ready** | The framework has registered the rules and built the pipeline. |
| **Executing** | The pipeline is running the rules against the response. |
| **Completed** | The run finished and produced a `ValidationResult`. |
| **Failed** | The run could not produce a result due to an orchestration error (§16). |

> **Principle**
> A `Failed` run is an **orchestration failure**, not a validation verdict. A run
> that completes and produces a `FAILED` verdict is `Completed`, not `Failed`. The
> lifecycle describes whether the *run* succeeded; the verdict describes whether
> the *response* is trustworthy. The two are never conflated.

---

## 14. Execution Modes

The Validator supports conceptual **execution modes**. Each mode is a way of
invoking the same orchestration; none changes how a rule behaves.

| Mode | Meaning | Status |
| ---- | ------- | ------ |
| **Full Validation** | Validate the entire response against the complete selected rule set. | Active |
| **Profile Validation** | Validate against the rule set named by a specific profile. | Active |
| **Incremental Validation** | Validate only the parts of a response affected by a change. | Reserved (future) |
| **Revalidation** | Re-run validation of a previously validated response. | Reserved (future) |

> **Architectural Decision**
> Execution modes are **orchestration strategies behind the single entry point**.
> Full and Profile validation are active today; Incremental and Revalidation are
> reserved for the future (§15). A new mode may be added without changing the
> entry point, the result shape, or any rule.

---

## 15. Execution Flow

The end-to-end flow of a single validation run, expressed as a sequence between
collaborators.

```text
   AnalysisResult        Response          Registry         Pipeline          Rules
        │                Validator            │                │                │
        │  validate      │                    │                │                │
        │ ─────────────► │                    │                │                │
        │                │ resolve config     │                │                │
        │                │ select profile     │                │                │
        │                │ register rules     │                │                │
        │                │ ─────────────────► │                │                │
        │                │ construct pipeline │                │                │
        │                │ ──────────────────────────────────► │                │
        │                │ execute            │                │                │
        │                │ ──────────────────────────────────► │   run in       │
        │                │                    │                │ ─ layer order ─►│
        │                │                    │                │   findings      │
        │                │                    │                │ ◄───────────────│
        │                │ ValidationResult   │                │                │
        │                │ ◄──────────────────────────────────│                │
        │ ValidationResult                    │                │                │
        │ ◄───────────── │                    │                │                │
        ▼                ▼                    ▼                ▼                ▼
```

| Transition | Meaning |
| ---------- | ------- |
| **AnalysisResult → Validator** | A caller requests validation by supplying the analysed response. |
| **Validator → Registry** | The Validator has the framework register the profile's rules. |
| **Validator → Pipeline** | The Validator has the framework construct and then execute the pipeline. |
| **Pipeline → Rules** | The pipeline invokes each rule in layer order; rules return findings. |
| **Pipeline → Validator** | The assembled `ValidationResult` returns to the Validator. |
| **Validator → Caller** | The Validator returns the result unchanged. |

---

## 16. Error Handling

The Validator distinguishes **categories** of orchestration failure so that
responsibility for each is clear. Its job is to **classify and surface** failures
— not to hide, retry, or repair them today.

| Category | Origin | Architectural responsibility |
| -------- | ------ | ---------------------------- |
| **Configuration errors** | Missing or incoherent configuration | Detected before execution; surfaced as a configuration failure with no pipeline built. |
| **Construction errors** | The registry or pipeline cannot be assembled | Surfaced as a construction failure; execution does not proceed. |
| **Execution errors** | A rule or the pipeline fails at the infrastructure level | Surfaced as an execution failure with execution context captured. |
| **Unexpected errors** | An unforeseen internal failure | Surfaced distinctly so it is never mistaken for a validation verdict. |

### 16.1 Reserved (not current responsibilities)

| Reserved capability | Intent |
| ------------------- | ------ |
| **Future repair** | Propose a corrected response after a failure. |
| **Future retry** | Re-attempt a transient failure. |
| **Future AI-assisted repair** | Use model assistance to remediate certain failures. |

> **Architectural Decision**
> **Retry and repair are NOT current responsibilities of the Response Validator.**
> Today the Validator classifies and surfaces failures; it does not recover from
> them. Repair, retry, and AI-assisted repair are reserved capabilities (§15) that,
> when introduced, must sit *behind* the single entry point without changing the
> result contract. A failure to *produce* a result is an orchestration error; a
> response judged *untrustworthy* is a verdict — the two are never conflated.

---

## 17. Validation Result

The **ValidationResult** is the single, canonical output of the Validator
(Validation Canonical Models §6; AI Response Validation Architecture §8). The
Validator returns it unchanged.

| Guarantee | Meaning |
| --------- | ------- |
| **Only output** | The Validator returns exactly one `ValidationResult` per run and nothing else. |
| **Never exposes pipeline state** | The internal state of the pipeline is never surfaced to callers. |
| **Never exposes rule mechanics** | How individual rules executed is never surfaced; only the assembled findings appear. |
| **Immutable** | The result is returned exactly as the framework assembled it. |

> **Architectural Decision**
> **The `ValidationResult` is the sole output of the Response Validator.** No
> caller receives pipeline internals, rule execution traces, or partial state. The
> Validator exposes a single, immutable result — the one governed artifact every
> downstream consumer depends on. This keeps the subsystem's surface minimal and
> its internals replaceable.

---

## 18. Version Provenance

Every `ValidationResult` records the full provenance of the versions that
governed its run, so any result can be reproduced and any change precisely
attributed.

| Version | Records | Source |
| ------- | ------- | ------ |
| **Platform Version** | The platform release in force. | Platform context |
| **Framework Version** | The Validation Framework component version. | Framework |
| **Validator Version** | The Response Validator implementation version. | Validator |
| **Validation Contract Version** | The validation *semantics* in force. | Configuration / framework |
| **Rule Catalog Version** | The governed rule set in force (Validation Rule Catalog §21). | Rule Catalog |
| **Profile Version** *(future)* | The version of the selected profile. | Profile (reserved) |
| **Prompt Version** | The prompt contract that produced the response. | AnalysisResult |
| **Reasoning Contract Version** | The reasoning contract in force for the response. | AnalysisResult |

> **Principle**
> **Provenance is what makes a verdict reproducible.** Because every result records
> the platform, framework, validator, contract, catalog, profile, prompt, and
> reasoning versions, a change in outcome can be attributed precisely — to the
> orchestration, the rule set, the validation semantics, or the upstream analysis.
> A result without full provenance cannot be governed.

---

## 19. Observability

Every run emits a consistent set of orchestration metadata. Observability is a
first-class architectural requirement, not an afterthought.

| Signal | Meaning |
| ------ | ------- |
| **Execution identifier** | Unique identity of this validation run. |
| **Correlation identifier** | The trace key linking analysis → validation → downstream. |
| **Profile** | The Validation Profile selected for the run. |
| **Configuration** | The resolved configuration that governed the run. |
| **Duration** | How long the run took. |
| **Rules executed** | How many rules participated. |
| **Rules skipped** | How many eligible rules were not run (e.g. disabled by configuration). |
| **Blocking rule** | The rule, if any, whose finding halted progression. |
| **Versions** | The full version provenance of the run (§18). |

### 19.1 Relationship to the execution package

The run's orchestration metadata is carried as the **execution package** of the
validation run — the provenance and correlation context that travels with the
result. It stitches the analysed response, the validation run, and every
downstream consumer into a single, traceable chain.

```text
   Analysis ──► Response Validator ──► Validation ──► Downstream (CP1 · Feature Generation)
       └────────────── single correlation identifier ──────────────┘
```

> **Principle**
> If a run cannot be traced — by execution identity, correlation, profile,
> configuration, timing, rule counts, blocking rule, and full version provenance —
> it cannot be governed. Observability is what makes regression analysis,
> profile comparison, and audit possible.

---

## 20. Relationships

The Response Validator does not stand alone. It sits within the platform's
governing chain — constrained by the documents upstream and consumed by the
capabilities downstream.

```text
   AI Reasoning Contract             (how the AI must reason)
            │ governs the meaning of trustworthy output
            ▼
   Requirement Analysis Service      (produces the AnalysisResult)
            │ emits the analysed response to be validated
            ▼
   Response Validation Architecture  (why & whether output is trustworthy)
            │ defines the validation philosophy & verdict model
            ▼
   Validation Canonical Models       (the validation information model)
            │ defines issues, results, severity, verdicts
            ▼
   Validation Rule Catalog           (the governed set of rules)
            │ defines every rule's identity, layer, severity, blocking
            ▼
   Response Validator                ◄── THIS DOCUMENT (the orchestration boundary)
            │ selects a profile; coordinates the framework
            ▼
   Validation Framework              (registry · pipeline · rule contract)
            │ registers rules; builds and runs the pipeline
            ▼
   Validation Pipeline               (ordered rule execution)
            │ assembles findings
            ▼
   ValidationResult                  (the single validated output)
            │ consumed only when the verdict permits
            ▼
   CP1                               (downstream quality gate)
            │ operates on validated output
            ▼
   Feature Generation                (downstream engineering capability)
```

| Relationship | Meaning |
| ------------ | ------- |
| **AI Reasoning Contract → Requirement Analysis Service** | The contract defines how the AI must reason; the service produces output embodying it. |
| **Requirement Analysis Service → Response Validation Architecture** | The service emits the analysed response that the validation gate must judge. |
| **Response Validation Architecture → Canonical Models** | The philosophy defines verdicts and severity; the models give them a stable shape. |
| **Canonical Models → Rule Catalog** | The models define what a finding *is*; the catalog defines which findings *exist*. |
| **Rule Catalog → Response Validator** | The catalog defines the rules; the Validator selects and coordinates them by profile. |
| **Response Validator → Validation Framework** | The Validator drives the framework to register rules and build the pipeline. |
| **Validation Framework → Validation Pipeline** | The framework constructs the ordered pipeline the Validator executes. |
| **Pipeline → ValidationResult** | Findings are assembled into the single validated output. |
| **ValidationResult → CP1 → Feature Generation** | Only validated output flows to the downstream gate and engineering capabilities. |

> **Architectural Decision**
> The Validator **depends upward** on the reasoning contract, validation
> architecture, canonical models, and rule catalog, and is **consumed downward** by
> the framework it drives and the capabilities it gates. It introduces no new
> dependency direction; it is the single coordinating boundary at one fixed point
> in the chain.

---

## 21. Future Evolution

The Validator is designed so that significant capabilities can be added **without
changing its public orchestration contract**. Each capability slots in behind the
single entry point.

| Reserved capability | Intent | Contract impact |
| ------------------- | ------ | --------------- |
| **AI-assisted validation** | Use model assistance within a run. | Internal strategy; result contract unchanged. |
| **Rule parallelization** | Evaluate independent rules concurrently. | Throughput enhancement; Rule Independence makes it safe (§4.7). |
| **Repair engine** | Propose corrected output after failure. | Added behind the entry point; never mutates the input (§4.8). |
| **Retry engine** | Re-attempt transient failures. | Internal control; callers unaffected. |
| **Adaptive profiles** | Choose a profile from run context. | New selection strategy; profile mechanics unchanged. |
| **Dynamic rule loading** | Admit governed rules at runtime. | Discovery enhancement; only catalogued rules remain eligible (§10). |
| **Organization policies** | Apply organization-defined rule selections. | New profiles/configuration; entry point stable. |

> **Architectural Decision**
> Every future enhancement must be additive **behind** the single orchestration
> entry point. If a proposed capability would force callers to change how they
> request validation, or would alter the `ValidationResult` contract, it must be
> redesigned. The orchestration contract is stable by mandate.

---

## 22. Architecture Principles Summary

The philosophy of the Response Validator, distilled:

| # | Principle | One-line meaning |
| - | --------- | ---------------- |
| 1 | **One orchestration entry point.** | All validation flows through the Validator. |
| 2 | **Orchestrate, never validate.** | The Validator coordinates; rules judge. |
| 3 | **Single responsibility.** | It coordinates one run; it never persists, reports, or gates. |
| 4 | **Deterministic orchestration.** | Same input, profile, and configuration ⇒ same process. |
| 5 | **Configuration driven.** | Runtime behaviour is declared policy, not hidden defaults. |
| 6 | **Profile driven.** | Breadth of validation is the selected profile; rules stay context-free. |
| 7 | **Framework independent.** | The framework is a replaceable collaborator. |
| 8 | **Rule independent.** | The Validator never knows a rule's internals. |
| 9 | **Immutable inputs and outputs.** | It alters neither the response nor the result. |
| 10 | **Observable by design.** | Every run is traceable with full provenance. |
| 11 | **Extend behind the entry point.** | New capabilities never change the orchestration contract. |

---

> **Architectural Decision — Architecture Freeze**
> With this document, the following become **frozen architectural contracts** for
> the Response Validation orchestration boundary:
>
> - **Entry Point** (§1, §4.1) — the Validator is the single, exclusive doorway.
> - **Execution Flow** (§5, §15) — the fixed, ordered orchestration sequence.
> - **Execution Context** (§12) — orchestration metadata only, never validation data.
> - **Execution Lifecycle** (§13) — Created → Configured → Pipeline Ready →
>   Executing → Completed / Failed.
> - **Configuration Hierarchy** (§8) — Platform Defaults → Profile → Execution
>   Configuration → Runtime Overrides; highest precedence wins.
> - **Profile Selection** (§6) — exactly one profile per run; Standard by default.
> - **Pipeline Construction** (§9) — coordinated through the framework, never
>   embedded in the Validator.
> - **Result Production** (§17) — a single, immutable `ValidationResult` is the
>   sole output.
> - **Version Provenance** (§18) — every result records its full version provenance.
> - **Future Extension Points** (§14, §15, §16.1) — reserved capabilities sit behind
>   the single entry point.
>
> **Implementation may evolve freely** beneath these contracts. **The architecture
> may evolve only through an approved Architecture Decision Record (ADR).** A change
> that violates any frozen contract above is non-conforming by definition.

> **Definition of Done**
> This document is the definitive orchestration specification for the entire
> Response Validation subsystem. It establishes the Response Validator as the
> single orchestration boundary and governs the entry point, execution flow,
> execution context, execution lifecycle, configuration and its hierarchy, profile
> selection, pipeline construction, rule discovery, result production, version
> provenance, observability, and future evolution. It is implementation-independent
> and remains valid even if the platform is reimplemented on an entirely different
> technology stack or driven by an entirely different AI provider.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Response Validator** | The single orchestration boundary that coordinates a validation run; it orchestrates, it does not validate (§1). |
| **Orchestration** | Coordination of the ordered steps required to run one validation (§5). |
| **AnalysisResult** | The analysed AI response handed to the Validator as input (§3). |
| **Validation Profile** | A named selection of rules chosen by the Validator (§6). |
| **ValidationConfiguration** | The runtime policy governing a validation run (§7). |
| **Configuration Hierarchy** | The fixed precedence resolving configuration sources (§8). |
| **ValidationExecutionContext** | The conceptual runtime context carrying a run's orchestration metadata (§12). |
| **Execution Lifecycle** | The states a run passes through: Created → Configured → Pipeline Ready → Executing → Completed / Failed (§13). |
| **Execution Mode** | A strategy for invoking validation behind the single entry point (§14). |
| **ValidationResult** | The single, immutable canonical output of a validation run (§17). |
| **Version Provenance** | The complete set of versions recorded on a result (§18). |
| **Validation Framework** | The registry, rule contract, and pipeline the Validator coordinates (§3). |

## Appendix B — Conformance Checklist

A Response Validator implementation conforms to this architecture only if every
box can be checked:

- [ ] Is the **single entry point** — all validation flows through it.
- [ ] **Selects exactly one profile** per run, defaulting to Standard.
- [ ] **Applies an explicit configuration**, resolved through the fixed hierarchy.
- [ ] Contains **no validation logic** — it orchestrates, it does not judge.
- [ ] Contains **no rule logic** and never knows a rule's internals.
- [ ] **Coordinates pipeline construction** through the framework; it never orders rules itself.
- [ ] **Returns a `ValidationResult` only** — never pipeline state or rule mechanics.
- [ ] Is **deterministic** — same input, profile, and configuration yield the same process.
- [ ] Performs **immutable orchestration** — it alters neither the input nor the output.
- [ ] Is **framework independent** — it depends on the framework contract, not its internals.
- [ ] Is **rule independent** — it coordinates contracts, never implementations.
- [ ] Carries a **ValidationExecutionContext** of orchestration metadata only.
- [ ] Records **full version provenance** on every result.
- [ ] Emits **complete observability** for every run.
- [ ] Classifies and surfaces **orchestration errors** distinctly from verdicts; does not retry or repair.
- [ ] Is **future extensible** — new capabilities sit behind the single entry point.
