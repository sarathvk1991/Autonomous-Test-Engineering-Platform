# Requirement Analysis Service Architecture

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification                                |
| Status               | Approved — foundational                                            |
| Scope                | Orchestration of AI analysis within the platform                   |
| Governs              | All AI execution workflows in the Autonomous Test Engineering Platform |
| Depends on           | AI Reasoning Contract · Prompt Framework · LLM Provider Framework   |
| Audience             | Solution Architects · AI Architects · Senior Engineers · Platform Engineers · Technical Leads |
| Implementation-bound | No — valid regardless of language, framework, or model provider    |

> **Architectural Decision**
> The Requirement Analysis Service is defined as the **single orchestration
> boundary** for AI execution. It coordinates *how* an analysis is run; it does
> not decide *how the platform reasons* (governed by the **AI Reasoning
> Contract**) nor *how prompts are worded* (governed by the **Prompt Framework**).
> Orchestration, reasoning, and prompting are separate concerns by design.

---

## 1. Purpose

### 1.1 Why this service exists

The platform draws conclusions about engineering evidence by invoking AI models.
That invocation involves several moving parts: assembling a prompt, constructing
an execution request, calling a provider, capturing metadata, and returning a
result. If every component that wanted an AI answer performed those steps
itself, the platform would suffer:

- **Scattered provider calls** — many components would each need to know how to
  talk to an AI provider.
- **Inconsistent metadata** — traceability and observability would vary by
  caller.
- **Tight coupling** — a change in provider, prompt assembly, or execution
  semantics would ripple across the codebase.
- **No governance choke point** — there would be no single place to enforce
  policy, observability, or future capabilities such as failover.

The Requirement Analysis Service exists to **own and centralise AI execution
orchestration**. It is the one place through which all AI analysis flows.

### 1.2 Orchestration, not reasoning

> **Principle**
> Orchestration is *coordination of steps*. Reasoning is *the cognitive work the
> AI performs*. These are different responsibilities and are deliberately kept
> apart.

| Concern        | Owned by | Question it answers |
| -------------- | -------- | ------------------- |
| **Orchestration** | Requirement Analysis Service | *In what order, with what inputs, and with what metadata is an analysis executed?* |
| **Reasoning**     | AI Reasoning Contract        | *How must the AI think — evidence, gaps, risks, honesty?* |
| **Prompting**     | Prompt Framework             | *How is the reasoning expressed as an instruction to a model?* |
| **Execution**     | LLM Provider Framework       | *How is a request physically dispatched to a model?* |

The service **coordinates** these collaborators. It never embeds reasoning logic
of its own. The quality and behaviour of the AI's thinking is, and remains,
governed exclusively by the **AI Reasoning Contract**.

---

## 2. Responsibilities

### 2.1 Responsibilities the service owns

| Responsibility | Description |
| -------------- | ----------- |
| **Receive consolidated engineering evidence** | Accept a consolidated artifact representing one unit of work as the input to analysis. |
| **Initiate AI analysis** | Act as the entry point that begins an AI analysis workflow. |
| **Coordinate prompt generation** | Delegate prompt construction to the Prompt Framework and obtain a versioned prompt. |
| **Coordinate AI execution** | Hand the prepared request to the provider framework for dispatch. |
| **Collect execution metadata** | Capture identifiers, versions, timing, and provider/model context for every run. |
| **Return analysis results** | Assemble and return a conceptual Analysis Result to the caller. |

### 2.2 Responsibilities the service does **not** own

The service is deliberately narrow. The following are explicitly **out of scope**
and belong to other parts of the platform:

| Not owned by this service | Owned elsewhere |
| ------------------------- | --------------- |
| **Response validation**   | Response Validation Architecture (future) |
| **CP1 validation**        | CP1 Validation Architecture (future) |
| **Persistence / storage** | Output Generation / storage layer |
| **Reporting**             | Reporting / governance layer |
| **Output generation**     | Output Generation Architecture (future) |
| **Source ingestion**      | Connector Framework + Source Registry |

> **Architectural Decision**
> The service produces a **raw, un-validated** Analysis Result. It does not judge
> whether the AI's answer is correct, complete, or acceptable. Validation is a
> separate, downstream responsibility. Mixing orchestration with validation would
> couple two independently evolving concerns.

---

## 3. Architectural Position

The service sits between the engineering evidence layer and the validation layer.
It is the **only** component that crosses the boundary into AI execution.

```text
        ┌─────────────────────────────────────────────┐
        │              Engineering Layer               │
        │   (ingestion · canonical model · consolidation)
        └───────────────────────┬─────────────────────┘
                                │  consolidated evidence
                                ▼
        ┌─────────────────────────────────────────────┐
        │        Requirement Analysis Service          │  ◄── single AI
        │              (orchestration)                 │      orchestration
        └───────┬───────────────────────────┬─────────┘      boundary
                │ asks for prompt            │ asks for execution
                ▼                            ▼
        ┌───────────────┐            ┌───────────────────┐
        │ Prompt        │            │ LLM Provider      │
        │ Framework     │            │ Framework         │
        └───────────────┘            └─────────┬─────────┘
                                               │ produces
                                               ▼
        ┌─────────────────────────────────────────────┐
        │                Analysis Result               │
        └───────────────────────┬─────────────────────┘
                                │  raw, un-validated
                                ▼
        ┌─────────────────────────────────────────────┐
        │               Validation Layer               │
        │     (response validation · CP1 · …)          │
        └─────────────────────────────────────────────┘
```

### 3.1 Interaction explanations

| Interaction | Meaning |
| ----------- | ------- |
| **Engineering Layer → Service** | The engineering layer hands over consolidated evidence; this is the *only* input the service needs to begin. |
| **Service → Prompt Framework** | The service requests a complete, versioned prompt for the supplied evidence. It does not author prompt text. |
| **Service → LLM Provider Framework** | The service submits a prepared execution request. It does not know which concrete provider answers. |
| **Provider → Analysis Result** | The provider's raw response is captured and wrapped, together with execution metadata, into an Analysis Result. |
| **Service → Validation Layer** | The service returns the Analysis Result. Whether the result is *good* is decided downstream, not here. |

---

## 4. Guiding Principles

### 4.1 Single Entry Point

**Purpose.** Provide exactly one doorway into AI execution for the whole
platform.

**Rules.**
- All AI analysis requests pass through this service.
- No other component invokes a provider directly.
- New AI workflows are built *on top of* this service, not around it.

**Example.** A future "re-analyse on change" workflow calls the Requirement
Analysis Service; it does not call a provider itself.

### 4.2 Single Responsibility

**Purpose.** Keep the service focused on orchestration alone.

**Rules.**
- The service coordinates steps; it does not validate, persist, or report.
- Logic that is not "coordinate an AI analysis" does not belong here.

**Example.** Deciding whether an AI answer passes CP1 is rejected from this
service and delegated to the validation layer.

### 4.3 Provider Independence

**Purpose.** Make the underlying AI provider a replaceable detail.

**Rules.**
- The service depends on the provider *framework's abstraction*, never on a
  concrete provider.
- Swapping or adding a provider must not change the orchestration contract.

**Example.** Changing which provider executes a request is a configuration
concern; callers of the service observe no difference in its interface.

### 4.4 Prompt Independence

**Purpose.** Decouple orchestration from prompt wording and structure.

**Rules.**
- The service never embeds prompt text.
- Prompt content and versioning are owned by the Prompt Framework.
- A prompt change must not require a service change.

**Example.** Evolving the prompt to a new version requires no modification to the
orchestration sequence.

### 4.5 Reasoning Independence

**Purpose.** Keep cognitive behaviour governed by the reasoning contract, not by
orchestration code.

**Rules.**
- The service does not encode how the AI should think.
- Reasoning rules live in the **AI Reasoning Contract**.

**Example.** A change to the hallucination policy is made in the reasoning
contract and its prompts — not in this service.

### 4.6 Deterministic Orchestration

**Purpose.** Ensure the *orchestration sequence* is predictable and repeatable.

**Rules.**
- Given the same evidence and configuration, the service performs the same
  ordered steps and captures the same metadata fields.
- Non-determinism is confined to the AI response itself, never to the workflow.

> **Architectural Decision**
> Determinism applies to *orchestration*, not to AI output. The platform
> guarantees a stable, reproducible *process*; the AI's wording may still vary
> within the bounds of the reasoning contract.

### 4.7 Observability by Design

**Purpose.** Make every analysis traceable and measurable from the outset.

**Rules.**
- Every execution captures identifiers, versions, timing, and context.
- Observability is mandatory, not optional or best-effort.

**Example.** Each analysis emits a correlation identifier that links evidence,
prompt version, reasoning version, provider, model, and timing.

### 4.8 Extensibility

**Purpose.** Allow new capabilities without breaking existing callers.

**Rules.**
- New behaviours (retry, failover, caching, etc.) are added *behind* the existing
  orchestration contract.
- The public orchestration responsibilities defined here remain stable.

**Example.** Adding provider failover changes internal behaviour only; callers
continue to request an analysis exactly as before.

---

## 5. Execution Flow

The service performs a fixed, ordered orchestration sequence. The numbered
workflow below is the canonical sequence; the steps are stable even as internal
mechanics evolve.

```text
   1. Receive consolidated artifact
                │
                ▼
   2. Generate prompt        (delegate → Prompt Framework)
                │
                ▼
   3. Create execution request
                │
                ▼
   4. Invoke AI provider     (delegate → LLM Provider Framework)
                │
                ▼
   5. Receive response
                │
                ▼
   6. Capture execution metadata
                │
                ▼
   7. Return analysis result
```

| Step | Name | Description |
| ---- | ---- | ----------- |
| 1 | **Receive consolidated artifact** | The service accepts one consolidated unit of evidence as the analysis input. It validates that the input is structurally present, not whether the AI's eventual answer is correct. |
| 2 | **Generate prompt** | The service asks the Prompt Framework for a complete, versioned prompt built from the evidence. The prompt's wording and version are owned by that framework. |
| 3 | **Create execution request** | The service assembles a provider-agnostic execution request: the prompt, a unique execution identifier, and any orchestration parameters. No provider-specific shaping occurs. |
| 4 | **Invoke AI provider** | The service hands the request to the provider framework, which dispatches it to whichever provider is configured. The service does not know or care which one. |
| 5 | **Receive response** | The raw AI response is returned to the service. The service treats it as opaque content to be carried forward, not interpreted. |
| 6 | **Capture execution metadata** | The service records identifiers, versions, timing, and provider/model context (see §10). This happens for every run, success or failure. |
| 7 | **Return analysis result** | The service assembles the conceptual Analysis Result and returns it to the caller for downstream validation. |

> **Worked example**
> A technical lead triggers analysis of a consolidated *"payment refund"* unit.
> The service (1) receives the evidence, (2) obtains prompt version *v1.x*, (3)
> creates execution request *EX-7741*, (4) invokes the configured provider, (5)
> receives the raw answer, (6) records that *EX-7741* used prompt *v1.x*,
> reasoning contract *vN*, a given model, and took 2.4s, and (7) returns the
> Analysis Result. Whether the answer is *acceptable* is decided later, by the
> validation layer.

---

## 6. Architectural Boundaries

The service's power comes from how little it is permitted to touch. Boundaries
are enforced to keep orchestration isolated from ingestion, validation, and
storage.

### 6.1 What the service MAY access

| Allowed collaborator | Why |
| -------------------- | --- |
| **Prompt Framework** | To obtain a versioned prompt for the evidence. |
| **Provider Framework** | To dispatch an execution request to an abstract provider. |
| **Execution Metadata** | To record observability and traceability for each run. |

### 6.2 What the service MUST NOT access

| Forbidden collaborator | Why it is forbidden |
| ---------------------- | ------------------- |
| **Connectors**         | Ingestion is upstream; orchestration must not fetch raw source data. |
| **Source Registry**    | Source selection/configuration is an ingestion concern, not an AI concern. |
| **Mappers**            | Normalisation into the canonical model happens before consolidation. |
| **Validation Engine**  | Judging the AI answer is a separate, downstream responsibility. |
| **Reporting**          | Presentation/governance is downstream of validated results. |
| **Storage**            | Persistence is owned by output/storage layers, not orchestration. |
| **CP1**                | A specific validation gate; the service must remain validation-agnostic. |
| **Business Rules**     | Domain rule evaluation is reasoning/validation territory, not orchestration. |

### 6.3 Why these boundaries exist

```text
   Ingestion ──► Canonical Model ──► Consolidation ──► [ Analysis Service ] ──► Validation ──► Output
      ▲                                                       │                     ▲
      └──────────── must NOT reach back ─────────────────────┘                     │
                                                              └── must NOT reach forward ──┘
```

> **Architectural Decision**
> The service may look **sideways** (to the Prompt and Provider frameworks) but
> never **backward** into ingestion nor **forward** into validation, reporting,
> or storage. This one-directional discipline is what keeps each layer
> independently replaceable.

---

## 7. Analysis Lifecycle

The lifecycle of a single analysis, expressed as a sequence of transitions
between collaborators.

```text
   Caller                 Requirement              Prompt            Provider
     │                  Analysis Service          Framework         Framework
     │                        │                       │                 │
     │  request analysis      │                       │                 │
     │ ─────────────────────► │                       │                 │
     │                        │   build prompt        │                 │
     │                        │ ────────────────────► │                 │
     │                        │   versioned prompt    │                 │
     │                        │ ◄──────────────────── │                 │
     │                        │   execute request                       │
     │                        │ ──────────────────────────────────────► │
     │                        │   raw response                          │
     │                        │ ◄────────────────────────────────────── │
     │                        │  capture metadata                       │
     │                        │  assemble Analysis Result               │
     │   Analysis Result      │                                         │
     │ ◄───────────────────── │                                         │
     ▼                        ▼                                         ▼
```

| Transition | Meaning |
| ---------- | ------- |
| **Caller → Service** | A caller requests an analysis by supplying consolidated evidence. The caller may be a person-triggered workflow or an automated pipeline. |
| **Service → Prompt Framework** | The service requests a complete, versioned prompt; it receives prompt content plus its version identity. |
| **Service → Provider Framework** | The service submits the execution request and awaits the raw response. |
| **Provider Framework → Service** | The provider's raw output is returned, opaque and un-interpreted. |
| **Service (internal)** | The service captures execution metadata and assembles the Analysis Result. |
| **Service → Caller** | The assembled Analysis Result is returned for downstream validation. |

---

## 8. Analysis Result

The **Analysis Result** is the conceptual output of the service. It bundles the
AI's raw answer together with everything required to trace and govern that
answer. It is described here *conceptually* — no implementation model is defined.

| Information element | What it represents | Why it is included |
| ------------------- | ------------------ | ------------------ |
| **Analysis identifier** | A unique handle for this analysis | Lets the rest of the platform reference the analysis |
| **Execution metadata** | The runtime facts of the invocation (see §10) | Enables observability and audit |
| **Provider information** | Which abstract provider executed the request | Supports comparison and substitution analysis |
| **Prompt version** | The version of the prompt contract used | Enables regression analysis across prompt changes |
| **Reasoning version** | The version of the AI Reasoning Contract in force | Distinguishes reasoning changes from prompt changes |
| **Execution timestamps** | Start and completion times | Supports duration, SLA, and trend metrics |
| **AI response** | The raw, un-validated model output | The actual analytical content, carried forward as-is |

> **Principle**
> The Analysis Result is a **carrier**, not a **judge**. It transports the AI's
> answer and its full provenance to the validation layer without asserting that
> the answer is correct. Correctness is determined downstream.

> **Worked example**
> Analysis *AN-3320* contains: execution *EX-7741*, an abstract provider
> reference, prompt version *v1.2.0*, reasoning version *vN*, start/finish
> timestamps yielding a 2.4s duration, and the raw AI answer. A reviewer (or the
> validation layer) can reconstruct exactly how this answer was produced.

---

## 9. Error Handling Philosophy

The service distinguishes **categories** of failure so that responsibility for
each is clear and so that downstream components can react appropriately. The
service's job is to **classify and surface** failures with full metadata — not to
hide, retry silently (today), or repair them.

| Category | Origin | Architectural responsibility |
| -------- | ------ | ---------------------------- |
| **Configuration** | Missing or invalid orchestration/provider configuration | Detected before execution; surfaced as a configuration failure with no AI call attempted. |
| **Prompt generation** | The Prompt Framework cannot produce a prompt | Surfaced as a prompt-generation failure; execution does not proceed. |
| **Provider communication** | The provider cannot be reached or rejects the request | Surfaced as a communication failure with execution metadata captured. |
| **Execution failure** | The provider responds, but the response is unusable at the transport level | Surfaced as an execution failure; the partial metadata is still recorded. |
| **Unexpected platform failure** | An unforeseen internal error | Surfaced distinctly so it is never mistaken for an AI or provider fault. |

### 9.1 Separation of responsibilities

```text
   Configuration error ─► fail fast, before any AI call
   Prompt error        ─► fail before execution
   Provider error      ─► fail during execution, metadata captured
   Execution error     ─► fail after dispatch, metadata captured
   Unexpected error    ─► isolated and clearly labelled
```

> **Architectural Decision**
> A failure to *produce* an AI answer (configuration, prompt, provider,
> execution) is the service's concern. A failure of the AI answer to be *correct
> or acceptable* is **not** — that is the validation layer's concern. The two
> must never be conflated.

---

## 10. Observability

Every analysis emits a consistent set of execution metadata. Observability is a
first-class architectural requirement, not an afterthought.

| Metadata | Meaning | Why it matters |
| -------- | ------- | -------------- |
| **Analysis ID** | Unique identity of the analysis | Top-level reference for the whole operation |
| **Execution ID** | Unique identity of the specific invocation | Pinpoints one run for debugging and audit |
| **Prompt Version** | Version of the prompt used | Regression analysis across prompt evolution |
| **Reasoning Contract Version** | Version of the governing reasoning contract | Separates reasoning changes from prompt changes |
| **Provider** | Abstract provider that executed the request | Provider comparison and substitution analysis |
| **Model** | The model identity used | Pinpoints model-driven variation |
| **Execution Time** | When the invocation occurred | Temporal correlation across the platform |
| **Duration** | How long the invocation took | Performance, SLA, and cost insight |
| **Correlation Identifier** | Cross-component trace key | Stitches evidence → analysis → validation → output |
| **Artifact Identifier** | The consolidated evidence analysed | Links the answer back to its input |

### 10.1 Why this matters

```text
   Artifact ──► Analysis ──► Validation ──► Output ──► Governance
       └──────────── single correlation identifier ───────────┘
```

> **Principle**
> If an analysis cannot be traced — by analysis, execution, prompt version,
> reasoning version, provider, model, timing, and correlation — it cannot be
> governed. Observability is what makes provider substitution, regression
> analysis, and audit possible.

---

## 11. Future Evolution

The service is designed so that significant capabilities can be added **without
changing its public orchestration contract**. Each capability below slots in
behind the existing entry point.

| Future capability | Intent | Contract impact |
| ----------------- | ------ | --------------- |
| **Retry Policies** | Re-attempt transient failures | Internal only; callers unaffected |
| **Provider Failover** | Fall back to an alternate provider | Internal only; orchestration interface unchanged |
| **Multiple AI Providers** | Route to different providers by policy | Internal routing; entry point stable |
| **Consensus Analysis** | Combine multiple model answers into one result | New internal strategy; same Analysis Result shape |
| **Parallel Analysis** | Analyse several units concurrently | Throughput enhancement; per-analysis contract unchanged |
| **Agent Orchestration** | Coordinate multiple reasoning roles | Added behind the entry point; reasoning still governed by the contract |
| **Caching** | Reuse results for identical evidence | Transparent optimisation |
| **Streaming Responses** | Emit partial output as it arrives | Delivery enhancement; result semantics preserved |
| **Rate Limiting** | Protect providers and control cost | Internal control; callers see no interface change |

> **Architectural Decision**
> Every future enhancement must be additive **behind** the single orchestration
> entry point. If a proposed capability would force callers to change how they
> request an analysis, it must be redesigned. The orchestration contract is
> stable by mandate.

---

## 12. Architecture Principles

The philosophy of the service, distilled:

| # | Principle | One-line meaning |
| - | --------- | ---------------- |
| 1 | **One orchestration entry point.** | All AI execution flows through this service. |
| 2 | **Provider implementations remain replaceable.** | The concrete provider is a configuration detail. |
| 3 | **Reasoning remains independent.** | Cognitive behaviour is governed by the AI Reasoning Contract. |
| 4 | **Prompting remains independent.** | Prompt content and versioning are owned by the Prompt Framework. |
| 5 | **Validation remains independent.** | The service returns raw results; correctness is judged downstream. |
| 6 | **Execution metadata is always captured.** | Every run is traceable and observable by design. |
| 7 | **No downstream component invokes providers directly.** | The service is the exclusive AI execution boundary. |

> **Architectural Decision**
> **The Requirement Analysis Service is the exclusive orchestration boundary for
> all AI execution within the Autonomous Test Engineering Platform.** No other
> component may invoke an AI provider, assemble an execution request, or bypass
> the metadata capture defined here. This single boundary is what makes the AI
> layer governable, observable, and replaceable.

---

## 13. Relationship to Other Architecture Documents

This document does not stand alone. It assumes and builds upon the platform's
existing architecture. References below are by **document name only**.

| Document | Contribution to the platform | Relationship to this service |
| -------- | ---------------------------- | ---------------------------- |
| **Source Registry** | Defines which engineering sources exist and how they are selected | Upstream of analysis; the service never touches it. |
| **Connector Framework** | Defines how raw evidence is retrieved from sources | Upstream of analysis; ingestion is out of scope here. |
| **Canonical Requirement Model** | Defines the normalised, source-agnostic representation of evidence | Provides the shape of evidence that consolidation builds upon. |
| **Consolidation Engine** | Groups related evidence into one unit of work | Produces the consolidated input this service consumes. |
| **LLM Provider Framework** | Defines the provider-agnostic execution abstraction | A direct collaborator; the service dispatches through it. |
| **AI Reasoning Contract** | Defines how the AI must think | Governs reasoning; the service orchestrates but never overrides it. |
| **Prompt Framework** | Defines how reasoning is expressed as versioned prompts | A direct collaborator; the service requests prompts from it. |

```text
   [Source Registry] + [Connector Framework]
                │
                ▼
   [Canonical Requirement Model] ──► [Consolidation Engine]
                                            │ consolidated evidence
                                            ▼
                         [ Requirement Analysis Service ]
                            │ uses                 │ uses
                            ▼                       ▼
                   [Prompt Framework]      [LLM Provider Framework]
                            ▲
                            │ governed by
                   [AI Reasoning Contract]
```

---

## 14. Future Architecture Roadmap

The following architecture documents are **reserved**. They extend the platform
*after* analysis, and none of them alter the orchestration responsibilities
defined in this document.

| Reserved document | Purpose | Boundary guarantee |
| ----------------- | ------- | ------------------ |
| **Response Validation Architecture** | Judge whether an AI answer is structurally and semantically acceptable | Consumes the Analysis Result; does not change how it is produced. |
| **CP1 Validation Architecture** | Apply the CP1 quality gate to validated requirements | Downstream of response validation; orchestration unaffected. |
| **Output Generation Architecture** | Persist and shape accepted results into platform outputs | Downstream of validation; the service still only orchestrates. |
| **Agent Orchestration Architecture** | Coordinate multiple reasoning agents for complex analyses | Slots in behind the single entry point (see §11). |
| **Knowledge Graph Architecture** | Persist and query relationships between artifacts and conclusions | Supplies/consumes evidence; reasoning and orchestration boundaries hold. |

> **Architectural Decision**
> These future documents **extend** the platform; they do not **redefine** AI
> orchestration. The single-entry-point and metadata-capture responsibilities
> established here remain in force across every future AI workflow.

> **Definition of Done**
> This document establishes the Requirement Analysis Service as the single
> orchestration boundary for AI execution and serves as the governing
> architecture specification for all future AI workflows within the Autonomous
> Test Engineering Platform. It remains valid even if the platform is
> reimplemented on an entirely different technology stack.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Orchestration** | Coordination of the ordered steps required to execute an AI analysis. |
| **Reasoning** | The cognitive analytical work performed by the AI, governed by the AI Reasoning Contract. |
| **Consolidated artifact** | One unit of related engineering evidence, produced by the Consolidation Engine. |
| **Execution request** | A provider-agnostic instruction to run one AI invocation. |
| **Analysis Result** | The conceptual carrier bundling the raw AI answer with its full provenance and metadata. |
| **Provider framework** | The provider-agnostic abstraction through which AI requests are dispatched. |
| **Correlation identifier** | A trace key linking evidence, analysis, validation, and output. |

## Appendix B — Conformance Checklist

An AI workflow conforms to this architecture only if every box can be checked:

- [ ] All AI execution is initiated through the Requirement Analysis Service.
- [ ] No component outside the service invokes a provider directly.
- [ ] The service delegates prompt creation to the Prompt Framework.
- [ ] The service dispatches execution through the provider framework abstraction.
- [ ] Execution metadata is captured for every run, including failures.
- [ ] The service returns a raw, un-validated Analysis Result.
- [ ] The service performs no validation, persistence, reporting, or ingestion.
- [ ] Full traceability (analysis, execution, prompt version, reasoning version, provider, model, timing, correlation, artifact) is preserved.
- [ ] New capabilities are added behind the existing orchestration entry point.
