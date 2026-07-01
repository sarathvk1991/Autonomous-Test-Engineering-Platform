# Platform Capability Matrix

| Attribute | Value |
| --------- | ----- |
| Document type | Engineering Governance / Executive Maturity View |
| Status | Living document — governance artifact |
| Scope | Every major platform capability and its implementation maturity |
| Source of truth | The repository — centralized version constants and actual code/tests |
| Sibling documents | [Architecture Freeze Index](./architecture-freeze-index.md) · [Architecture Coverage Dashboard](./architecture-coverage-dashboard.md) |

> This document **describes** the platform; it does **not define** it. Architecture
> is defined by the documents under [`docs/architecture/`](../architecture/);
> capability status is derived from the actual repository state. When
> implementation status or a version constant changes, **this document is updated**
> — it never drives a code or architecture change.

---

## 1. Purpose

The Platform Capability Matrix is the single **executive view of platform
maturity**. It answers, at a glance, *what exists*, *how mature each capability
is*, *which version it carries*, *what it depends on*, and *what comes next* — for
the whole Autonomous Test Engineering Platform. It is the canonical
implementation-progress document: every other progress claim defers to it.

It exists so that no one has to reconstruct platform status by reading the code.
Each row is populated from the actual repository — the centralized version
constants, the presence of implementation modules, and the presence of tests —
never from estimation or aspiration.

## 2. Intended Audience

| Audience | How this document serves them |
| -------- | ----------------------------- |
| **Architects** | Confirms which contracts are frozen and where architecture is complete but implementation has not begun — the boundary they govern. |
| **Engineering Leads** | A planning surface: what is Production Ready, what is In Progress, and the execution order of remaining milestones. |
| **Developers** | Shows exactly which capability to build next, what it depends on, and which framework/canonical models are already available to build upon. |
| **Reviewers** | A checklist against which a change can be judged: does it match the declared maturity, and does it respect frozen boundaries? |
| **Future Contributors** | An onboarding map of the whole platform — capability, purpose, maturity, and ownership — without needing tribal knowledge. |

## 3. How to read this matrix

- Every capability carries an immutable **Capability ID** (`CAP-NNN`). The ID is
  the stable handle: it **never changes**, even if the display name evolves. IDs
  are used to refer to capabilities throughout the governance layer. See §3.1.
- The capabilities are presented as **two linked tables per group**, sharing the
  **Capability ID**, so that all governance columns are captured without an
  unreadably wide single table:
  - a **Lifecycle table** — the six lifecycle stages as `✓` (done), `◑` (partial),
    `✗` (not started), or `n/a` (not applicable to this capability); and
  - a **Governance table** — Purpose, Current Version, Introduced In, Owner,
    Dependencies, Next Planned Milestone, Maturity, Status, and Notes.
- **Current Version** is copied verbatim from the centralized version constant
  when one exists; `n/a` means no such capability-specific constant exists yet.
- **Introduced In** is the **first platform version** in which the capability
  appeared, from repository evidence (its version constant plus `PLATFORM_VERSION`).
  It is *historical*, not the current version. Where a capability is not yet
  built (no code, no constant), it reads **Not Recorded** — no release history is
  invented.
- A capability is only marked complete in a lifecycle stage when that stage is
  **actually present in the repository** (a module for Implementation, a test
  module for Testing, a header/§ freeze statement for Frozen).

### 3.1 Capability IDs

Capability IDs are **immutable and sequential**, allocated in **per-domain blocks**
with reserved gaps so future capabilities slot into the right domain without
renumbering existing ones:

| Block | Domain | Assigned | Reserved for growth |
| ----- | ------ | -------- | ------------------- |
| `CAP-001…009` | Ingestion & Core | `CAP-001…003` | `CAP-004…009` |
| `CAP-010…019` | AI Generation | `CAP-010…014` | `CAP-015…019` |
| `CAP-020…029` | Execution & Platform | `CAP-020…024` | `CAP-025…029` |
| `CAP-030…039` | Response Normalization | `CAP-030…032` | `CAP-033…039` |
| `CAP-040…059` | Validation | `CAP-040…050` | `CAP-051…059` |
| `CAP-060…` | Downstream / Future | `CAP-060` | `CAP-061…` |

> An ID, once assigned, is **permanent**. A renamed capability keeps its ID; a
> removed capability's ID is **retired, never reused**. Allocating the next ID for
> a new capability is described in §8.

## 4. Capability lifecycle

Every capability advances through the same one-directional lifecycle. A later
stage never begins before the earlier stages it depends on are in place.

```text
   Architecture ─► Framework ─► Canonical Models ─► Implementation ─► Testing ─► Frozen
```

| Stage | Meaning |
| ----- | ------- |
| **Architecture** | A governing specification defines the capability's philosophy, responsibilities, and boundaries (a document under `docs/architecture/`). |
| **Framework** | The reusable, behaviour-free infrastructure the capability plugs into exists (registry, pipeline, base contracts) — but no concrete capability logic yet. |
| **Canonical Models** | The immutable information models the capability produces or consumes are defined (e.g. `ParsedResponse`, `ValidationResult`). |
| **Implementation** | Concrete, runnable code that performs the capability's real work exists in the repository. |
| **Testing** | Automated tests cover the implementation (a dedicated test module exists and passes). |
| **Frozen** | The architectural contract is declared immutable; it evolves only through an ADR. Implementation beneath it may still improve. |

> **Frozen is not the end of the lifecycle for code.** A frozen capability may
> continue to gain implementation, tests, and performance work; what is frozen is
> the *architecture*, not the *mechanism*. See the
> [Architecture Freeze Index](./architecture-freeze-index.md) §7.

## 5. Capability Matrix

Legend for lifecycle cells: `✓` complete · `◑` partial · `✗` not started · `n/a`
not applicable.

### 5.1 Ingestion & Core

**Lifecycle**

| ID | Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| -- | ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| CAP-001 | Connector Framework & Registry | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| CAP-002 | Mappers | ✓ | n/a | ✓ | ✓ | ✓ | ✗ |
| CAP-003 | Consolidation Engine | ✓ | n/a | ✓ | ✓ | ✓ | ✗ |

**Governance**

| ID | Capability | Purpose | Current Version | Introduced In | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| -- | ---------- | ------- | --------------- | ------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| CAP-001 | Connector Framework & Registry | Integrate external systems (JIRA, ZAP, SonarQube) behind one contract | `CONNECTOR_REGISTRY_VERSION` 1.0.0 | 1.0.0 | Implementation | shared contracts | None recorded | Production Ready | Complete | `connectors/`, `registry/`; catalogue `available=True`. |
| CAP-002 | Mappers | Normalise each source record into `SourceArtifact` | `MAPPER_VERSION` 1.0.0 | 1.0.0 | Implementation | Connectors, Canonical Data Model | None recorded | Production Ready | Complete | `mappers/`; per-source mapper tests present. |
| CAP-003 | Consolidation Engine | Group source artifacts into `ConsolidatedArtifact` | `CONSOLIDATION_ENGINE_VERSION` 1.0.0 | 1.0.0 | Implementation | Mappers | None recorded | Production Ready | Complete | `consolidation/`. |

### 5.2 AI Generation

**Lifecycle**

| ID | Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| -- | ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| CAP-010 | Reasoning Contract | ✓ | n/a | n/a | n/a | n/a | ✗ |
| CAP-011 | Prompt Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| CAP-012 | Provider (LLM) Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| CAP-013 | Gemini Provider | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| CAP-014 | Requirement Analysis Service | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |

**Governance**

| ID | Capability | Purpose | Current Version | Introduced In | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| -- | ---------- | ------- | --------------- | ------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| CAP-010 | Reasoning Contract | Define what trustworthy AI reasoning requires | `REASONING_CONTRACT_VERSION` 1.0.0 | 1.0.0 | Architecture | — | None recorded | Architecture Complete | Approved | `docs/architecture/ai-reasoning-contract.md`; a specification, not code. |
| CAP-011 | Prompt Framework | Render governed prompts for analysis | `PROMPT_FRAMEWORK_VERSION` 1.0.0 (`PROMPT_VERSION` 1.0.0) | 1.0.0 | Implementation | Reasoning Contract | None recorded | Production Ready | Complete | `prompts/`. |
| CAP-012 | Provider (LLM) Framework | Provider-agnostic request/response contract | `LLM_FRAMEWORK_VERSION` 1.0.0 | 1.0.0 | Implementation | shared enums (`ProviderType`, `ExecutionStatus`) | None recorded | Production Ready | Complete | `llm/`; named "LLM Framework" in code. |
| CAP-013 | Gemini Provider | Concrete provider adapter emitting `LLMResponse` | `n/a` (via `LLM_FRAMEWORK_VERSION`) | 1.0.0 | Implementation | Provider Framework | None recorded | Production Ready | Complete | `llm/providers/`; only active provider (others reserved). |
| CAP-014 | Requirement Analysis Service | Produce `AnalysisResult` (`LLMResponse`) from consolidated input | `ANALYSIS_SERVICE_VERSION` 1.0.0 | 1.0.0 | Implementation | Prompt Framework, Provider Framework, Consolidation | None recorded | Production Ready | Complete | `analysis/`; `docs/architecture/requirement-analysis-service.md`. |

### 5.3 Execution & Platform

**Lifecycle**

| ID | Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| -- | ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| CAP-020 | Execution Package | ✓ | n/a | ✓ | ✓ | ✓ | ✗ |
| CAP-021 | Execution History | ✓ | n/a | ✓ | ✓ | ◑ | ✗ |
| CAP-022 | Manifest | ✓ | n/a | ✓ | ✓ | ◑ | ✗ |
| CAP-023 | Baseline Metrics | ✓ | n/a | ✓ | ✓ | ◑ | ✗ |
| CAP-024 | Platform CLI | ✓ | n/a | ✓ | ✓ | ✓ | ✗ |

**Governance**

| ID | Capability | Purpose | Current Version | Introduced In | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| -- | ---------- | ------- | --------------- | ------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| CAP-020 | Execution Package | Generate execution artifacts for one analysis run | `EXECUTION_PACKAGE_VERSION` 1.0.0 | 1.0.0 | Implementation | Requirement Analysis Service | None recorded | Production Ready | Complete | `execution/`. |
| CAP-021 | Execution History | Persist/summarise past executions | `n/a` (via `EXECUTION_PACKAGE_VERSION`) | 1.0.0 | Implementation | Execution Package | None recorded | Production Ready | Complete | `execution/execution_history.py`. |
| CAP-022 | Manifest | Stable JSON contract of `manifest.json` | `MANIFEST_SCHEMA_VERSION` 1.0.0 | 1.0.0 | Implementation | Execution Package | None recorded | Production Ready | Complete | `execution/manifest_builder.py`. |
| CAP-023 | Baseline Metrics | Capture baseline execution metrics | `BASELINE_VERSION` 1.0.0 | 1.0.0 | Implementation | Execution Package | None recorded | Production Ready | Complete | `execution/baseline_metrics_builder.py`; CLI `benchmark`. |
| CAP-024 | Platform CLI | Operator entry point (`analyze`, `validate`, `benchmark`, …) | `CLI_VERSION` 1.0.0 | 1.0.0 | Implementation | Platform Metadata, Analysis Service | None recorded | Production Ready | Complete | `scripts/run_requirement_analysis.py`; commands in `platform_metadata.CLI_COMMANDS`. |

### 5.4 Response Normalization

**Lifecycle**

| ID | Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| -- | ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| CAP-030 | Response Normalization (subsystem) | ✓ | ✓ | ✓ | ◑ | ✓ | ✓ |
| CAP-031 | ParsedResponse | ✓ | n/a | ✓ | ✓ | ✓ | ◑ |
| CAP-032 | ResponseNormalizer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |

**Governance**

| ID | Capability | Purpose | Current Version | Introduced In | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| -- | ---------- | ------- | --------------- | ------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| CAP-030 | Response Normalization (subsystem) | Turn `LLMResponse` into the canonical structure exactly once | `FRAMEWORK_VERSION` 1.0.0 · `NORMALIZATION_CONTRACT_VERSION` 1.0 | 1.0.0 | Framework | Canonical Models, Provider Framework | Implement `ResponseNormalizer` (CAP-032) | Framework Complete | Contract Frozen | Generic framework (registry/pipeline/result/execution-context) built; **no responsibilities implemented** yet. The five normalization stages are internal to the `ResponseNormalizer`, not framework units (ADR-0002). |
| CAP-031 | ParsedResponse | The immutable, shared canonical structural representation | `PARSED_RESPONSE_VERSION` 1.0 | 1.0.0 | Shared | `NormalizationOutcome` enum, Canonical Models §8 | None recorded | Production Ready | Complete | `models/parsed_response.py`; ownership aligned (observations owned by `NormalizationResult`). |
| CAP-032 | ResponseNormalizer | Concrete producer of a real `ParsedResponse`; owns the `NORMALIZATION-0001…0005` **internal stages** + Assembly State (ADR-0002) | `n/a` (stages not built) | Not Recorded | Implementation | Normalization Framework (CAP-030), ParsedResponse (CAP-031), `LLMResponse` | **Next milestone** — build the five internal stages + Assembly Contract | Concept | Planned | Orchestration boundary exists; the five stages are internal to the normalizer, not framework units (ADR-0002). |

### 5.5 Validation

**Lifecycle**

| ID | Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| -- | ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| CAP-040 | Validation Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CAP-041 | Response Validator | ✓ | ✓ | ✓ | ◑ | ✓ | ✗ |
| CAP-042 | Transport Layer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CAP-043 | Syntax Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-044 | Schema Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-045 | Structural Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-046 | Content Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-047 | Evidence Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-048 | Traceability Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-049 | Reasoning Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-050 | Business Rule Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |

**Governance**

| ID | Capability | Purpose | Current Version | Introduced In | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| -- | ---------- | ------- | --------------- | ------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| CAP-040 | Validation Framework | Reusable rule/registry/pipeline infrastructure | `FRAMEWORK_VERSION` 1.0.0 · `DEFAULT_VALIDATION_CONTRACT_VERSION` 1.0 | 1.0.0 | Framework | Canonical Models | None recorded | Frozen | Frozen | `validation/`; treated as frozen (Syntax Design Review §"do not modify the frozen framework"). |
| CAP-041 | Response Validator | Orchestrate validation over an `AnalysisResult` | `VALIDATOR_VERSION` 1.0.0 · `RULE_CATALOG_VERSION` 1.0.0 | 1.0.0 | Implementation | Validation Framework, Canonical Models, ParsedResponse (future) | Wire end-to-end into the platform/CLI | Implementation In Progress | In Progress | Orchestrator class + tests exist (`validation/response/response_validator.py`); **not wired into CLI**; platform catalogue lists it `Planned`. |
| CAP-042 | Transport Layer | Validate delivery-boundary facts (exists, non-empty, no timeout, no failure) | Rules at `DEFAULT_RULE_VERSION` 1.0.0 | 1.0.0 | Implementation | Validation Framework, `LLMResponse`/`ExecutionStatus` | None recorded | Frozen | Frozen | 4 rules (`TRANSPORT-0001…0004`) implemented + tested; Rule Catalog §"Transport Layer Status — FROZEN". |
| CAP-043 | Syntax Layer | Judge well-formedness from the Normalization Outcome + observations | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse, `NormalizationResult` | Implement `SYNTAX-0001…0003` after the `ResponseNormalizer` (CAP-032) | Architecture Complete | Planned | Rule Catalog §8.2 + Syntax Design Review define it; **no rules implemented**. |
| CAP-044 | Schema Layer | Judge structure against the expected shape | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse | Follows Syntax | Architecture Complete | Planned | Rule Catalog only. |
| CAP-045 | Structural Layer | Judge structural completeness/consistency | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse | Follows Schema | Architecture Complete | Planned | Rule Catalog only. |
| CAP-046 | Content Layer | Judge content-level concerns | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse | Follows Structural | Architecture Complete | Planned | Rule Catalog only. |
| CAP-047 | Evidence Layer | Judge presence/adequacy of evidence | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse | Follows Content | Architecture Complete | Planned | Rule Catalog only. |
| CAP-048 | Traceability Layer | Judge traceability of claims | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse | Follows Evidence | Architecture Complete | Planned | Rule Catalog only. |
| CAP-049 | Reasoning Layer | Judge reasoning integrity | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse, Reasoning Contract | Follows Traceability | Architecture Complete | Planned | Rule Catalog only. |
| CAP-050 | Business Rule Layer | Judge domain/business-rule conformance | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse | Follows Reasoning | Architecture Complete | Planned | Rule Catalog only. |

### 5.6 Downstream (known future)

**Lifecycle**

| ID | Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| -- | ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| CAP-060 | CP1 Validator | ◑ | n/a | ✓ | ◑ | ✗ | ✗ |

**Governance**

| ID | Capability | Purpose | Current Version | Introduced In | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| -- | ---------- | ------- | --------------- | ------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| CAP-060 | CP1 Validator | Downstream quality gate consuming validated output | `n/a` (not built) | 1.0.0 | Implementation | Response Validator | None recorded | Implementation In Progress | Planned | `validators/cp1.py` present; platform catalogue lists CP1 Validator `Planned` — see consistency note. |

## 6. Overall Platform Health

Objective counts, derived directly from the repository (no estimation):

| View | Derivation | Result |
| ---- | ---------- | ------ |
| **Architecture capability catalogue** | `platform_metadata.ARCHITECTURE_COMPONENTS` with `available=True` | **10 of 14** components available (71.4%). Not available: Response Validator, CP1 Validator, Feature Generator, Test Generator. |
| **Validation layers implemented** | Rule modules under `validation/rules/` | **1 of 9** layers implemented (Transport). |
| **Validation layers frozen** | Freeze statements in the Rule Catalog | **1 of 9** frozen (Transport). |
| **LLM providers active** | `platform_metadata.PROVIDERS` with `available=True` | **1 of 5** (Gemini; four reserved). |
| **Response Normalization** | Framework vs. producer | Framework + `ParsedResponse` complete; **0 of 5** `NORMALIZATION-00NN` responsibilities implemented; `ResponseNormalizer` not built. |

| Bucket | Capabilities |
| ------ | ------------ |
| **Frozen** | Response Normalization subsystem (CAP-030, contract), Transport Layer (CAP-042), Validation Framework (CAP-040). |
| **Completed (Production Ready)** | Ingestion & Core (CAP-001…003), AI Generation implementation (CAP-011…014), Execution & Platform (CAP-020…024), ParsedResponse (CAP-031). |
| **In Progress** | Response Validator (CAP-041, orchestrator built, not wired), CP1 Validator (CAP-060). |
| **Planned** | ResponseNormalizer (CAP-032) + `NORMALIZATION-0001…0005`; Syntax → Business Rule layers (CAP-043…050); Feature/Test Generators. |

## 7. Implementation Roadmap

Remaining milestones in **execution order** (no dates; grounded in the
Response Normalization Contract §13, the Syntax Design Review, and the Rule
Catalog layer order):

1. **ResponseNormalizer (CAP-032)** — implement the concrete normalizer and the
   `NORMALIZATION-0001…0005` responsibilities; produce a real `ParsedResponse`.
2. **Response Validator wiring (CAP-041)** — register the existing orchestrator as
   a delivered platform capability and wire it end-to-end (CLI/platform catalogue).
3. **Syntax Layer (CAP-043)** — implement `SYNTAX-0001…0003` (reads the
   Normalization Outcome from `ParsedResponse` and observations from
   `NormalizationResult`).
4. **Schema Layer (CAP-044)** — implement the Schema rules.
5. **Structural → Content → Evidence → Traceability → Reasoning → Business Rule
   (CAP-045…050)** — implement the remaining validation layers in Rule Catalog
   order.

> The roadmap lists only work with an existing architectural mandate. Downstream
> layers named in the Architecture Overview (Feature/Test Generation, Execution,
> Failure Intelligence, Governance Dashboard) are known future direction and are
> not scheduled here.

## 8. Adding a future capability (governance process)

This is the **permanent process** for admitting a new capability into the platform
governance layer. It changes no architecture; it records a capability the
repository already gained (or is about to gain). Follow every step:

1. **Assign the next Capability ID.** Take the lowest **unused** ID from the
   reserved range of the capability's domain block (§3.1) — e.g. the next
   Response-Normalization capability is `CAP-033`. If the block is exhausted, open
   the next free block. **Never reuse a retired ID and never renumber an existing
   one.**
2. **Select the correct maturity.** Use the repository as the only evidence:
   `Concept` → `Architecture Complete` → `Framework Complete` →
   `Implementation In Progress` → `Production Ready` → `Frozen`. A stage is only
   ticked when it is actually present (a module, a test module, a freeze statement).
3. **Record the first introduction version.** Set **Introduced In** to the platform
   version in which the capability's code/constant first appears (from
   `PLATFORM_VERSION` and the capability's own version constant). If it is not yet
   built, use **Not Recorded** — never invent a version, and never let Introduced In
   exceed the Current Version.
4. **Record dependencies.** List **immediate** architectural dependencies only (by
   name and, where useful, Capability ID) — no deep trees.
5. **Update the roadmap.** If the capability implies remaining work, insert it into
   §7 in the correct execution order (no dates).
6. **Update the Architecture Coverage Dashboard.** Add the capability's row (same
   Capability ID) with its `✓`/`◑`/`✗` coverage and Implementation Readiness, and
   refresh the coverage counts. See
   [Architecture Coverage Dashboard](./architecture-coverage-dashboard.md).
7. **Update the Architecture Freeze Index (only if applicable).** If — and only if
   — a governing document declares the capability's contract **frozen**, add it to
   the [Architecture Freeze Index](./architecture-freeze-index.md) with its
   governing document and (if none is recorded) a **Not Recorded** freeze date.

> These seven steps keep the three governance documents in lock-step. They are a
> **documentation** process only: none of them changes architecture, and each is
> driven by evidence already present in the repository.
