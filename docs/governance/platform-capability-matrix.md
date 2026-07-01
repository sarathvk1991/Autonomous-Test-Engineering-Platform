# Platform Capability Matrix

| Attribute | Value |
| --------- | ----- |
| Document type | Engineering Governance / Executive Maturity View |
| Status | Living document — governance artifact |
| Scope | Every major platform capability and its implementation maturity |
| Source of truth | The repository — centralized version constants and actual code/tests |
| Sibling document | [Architecture Freeze Index](./architecture-freeze-index.md) |

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

- The capabilities are presented as **two linked tables per group**, sharing the
  **Capability** key, so that all governance columns are captured without an
  unreadably wide single table:
  - a **Lifecycle table** — the six lifecycle stages as `✓` (done), `◑` (partial),
    `✗` (not started), or `n/a` (not applicable to this capability); and
  - a **Governance table** — Current Version, Owner, Dependencies, Next Planned
    Milestone, Maturity, Status, and Notes.
- **Purpose** is stated once, in the Governance table's first column context, and
  kept to one line.
- **Current Version** is copied verbatim from the centralized version constant
  when one exists; `n/a` means no such capability-specific constant exists yet.
- A capability is only marked complete in a lifecycle stage when that stage is
  **actually present in the repository** (a module for Implementation, a test
  module for Testing, a header/§ freeze statement for Frozen).

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

| Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| Connector Framework & Registry | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Mappers | ✓ | n/a | ✓ | ✓ | ✓ | ✗ |
| Consolidation Engine | ✓ | n/a | ✓ | ✓ | ✓ | ✗ |

**Governance**

| Capability | Purpose | Current Version | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| ---------- | ------- | --------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| Connector Framework & Registry | Integrate external systems (JIRA, ZAP, SonarQube) behind one contract | `CONNECTOR_REGISTRY_VERSION` 1.0.0 | Implementation | shared contracts | None recorded | Production Ready | Complete | `connectors/`, `registry/`; catalogue `available=True`. |
| Mappers | Normalise each source record into `SourceArtifact` | `MAPPER_VERSION` 1.0.0 | Implementation | Connectors, Canonical Data Model | None recorded | Production Ready | Complete | `mappers/`; per-source mapper tests present. |
| Consolidation Engine | Group source artifacts into `ConsolidatedArtifact` | `CONSOLIDATION_ENGINE_VERSION` 1.0.0 | Implementation | Mappers | None recorded | Production Ready | Complete | `consolidation/`. |

### 5.2 AI Generation

**Lifecycle**

| Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| Reasoning Contract | ✓ | n/a | n/a | n/a | n/a | ✗ |
| Prompt Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Provider (LLM) Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Gemini Provider | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| Requirement Analysis Service | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |

**Governance**

| Capability | Purpose | Current Version | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| ---------- | ------- | --------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| Reasoning Contract | Define what trustworthy AI reasoning requires | `REASONING_CONTRACT_VERSION` 1.0.0 | Architecture | — | None recorded | Architecture Complete | Approved | `docs/architecture/ai-reasoning-contract.md`; a specification, not code. |
| Prompt Framework | Render governed prompts for analysis | `PROMPT_FRAMEWORK_VERSION` 1.0.0 (`PROMPT_VERSION` 1.0.0) | Implementation | Reasoning Contract | None recorded | Production Ready | Complete | `prompts/`. |
| Provider (LLM) Framework | Provider-agnostic request/response contract | `LLM_FRAMEWORK_VERSION` 1.0.0 | Implementation | shared enums (`ProviderType`, `ExecutionStatus`) | None recorded | Production Ready | Complete | `llm/`; named "LLM Framework" in code. |
| Gemini Provider | Concrete provider adapter emitting `LLMResponse` | `n/a` (via `LLM_FRAMEWORK_VERSION`) | Implementation | Provider Framework | None recorded | Production Ready | Complete | `llm/providers/`; only active provider (others reserved). |
| Requirement Analysis Service | Produce `AnalysisResult` (`LLMResponse`) from consolidated input | `ANALYSIS_SERVICE_VERSION` 1.0.0 | Implementation | Prompt Framework, Provider Framework, Consolidation | None recorded | Production Ready | Complete | `analysis/`; `docs/architecture/requirement-analysis-service.md`. |

### 5.3 Execution & Platform

**Lifecycle**

| Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| Execution Package | ✓ | n/a | ✓ | ✓ | ✓ | ✗ |
| Execution History | ✓ | n/a | ✓ | ✓ | ◑ | ✗ |
| Manifest | ✓ | n/a | ✓ | ✓ | ◑ | ✗ |
| Baseline Metrics | ✓ | n/a | ✓ | ✓ | ◑ | ✗ |
| Platform CLI | ✓ | n/a | ✓ | ✓ | ✓ | ✗ |

**Governance**

| Capability | Purpose | Current Version | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| ---------- | ------- | --------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| Execution Package | Generate execution artifacts for one analysis run | `EXECUTION_PACKAGE_VERSION` 1.0.0 | Implementation | Requirement Analysis Service | None recorded | Production Ready | Complete | `execution/`. |
| Execution History | Persist/summarise past executions | `n/a` (via `EXECUTION_PACKAGE_VERSION`) | Implementation | Execution Package | None recorded | Production Ready | Complete | `execution/execution_history.py`. |
| Manifest | Stable JSON contract of `manifest.json` | `MANIFEST_SCHEMA_VERSION` 1.0.0 | Implementation | Execution Package | None recorded | Production Ready | Complete | `execution/manifest_builder.py`. |
| Baseline Metrics | Capture baseline execution metrics | `BASELINE_VERSION` 1.0.0 | Implementation | Execution Package | None recorded | Production Ready | Complete | `execution/baseline_metrics_builder.py`; CLI `benchmark`. |
| Platform CLI | Operator entry point (`analyze`, `validate`, `benchmark`, …) | `CLI_VERSION` 1.0.0 | Implementation | Platform Metadata, Analysis Service | None recorded | Production Ready | Complete | `scripts/run_requirement_analysis.py`; commands in `platform_metadata.CLI_COMMANDS`. |

### 5.4 Response Normalization

**Lifecycle**

| Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| Response Normalization (subsystem) | ✓ | ✓ | ✓ | ◑ | ✓ | ✓ |
| ParsedResponse | ✓ | n/a | ✓ | ✓ | ✓ | ◑ |
| ResponseNormalizer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |

**Governance**

| Capability | Purpose | Current Version | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| ---------- | ------- | --------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| Response Normalization (subsystem) | Turn `LLMResponse` into the canonical structure exactly once | `FRAMEWORK_VERSION` 1.0.0 · `NORMALIZATION_CONTRACT_VERSION` 1.0 | Framework | Canonical Models, Provider Framework | Implement `ResponseNormalizer` | Framework Complete | Contract Frozen | Framework (registry/pipeline/result/execution-context) built; **no responsibilities implemented** yet. |
| ParsedResponse | The immutable, shared canonical structural representation | `PARSED_RESPONSE_VERSION` 1.0 | Shared | `NormalizationOutcome` enum, Canonical Models §8 | None recorded | Production Ready | Complete | `models/parsed_response.py`; ownership aligned (observations owned by `NormalizationResult`). |
| ResponseNormalizer | Concrete producer of a real `ParsedResponse` (+ `NORMALIZATION-0001…0005`) | `n/a` (not built) | Implementation | Normalization Framework, ParsedResponse, `LLMResponse` | **Next milestone** — build the normalizer + responsibilities | Concept | Planned | No class exists; framework and canonical model are ready for it. |

### 5.5 Validation

**Lifecycle**

| Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| Validation Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Response Validator | ✓ | ✓ | ✓ | ◑ | ✓ | ✗ |
| Transport Layer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Syntax Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Schema Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Structural Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Content Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Evidence Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Traceability Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Reasoning Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| Business Rule Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |

**Governance**

| Capability | Purpose | Current Version | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| ---------- | ------- | --------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| Validation Framework | Reusable rule/registry/pipeline infrastructure | `FRAMEWORK_VERSION` 1.0.0 · `DEFAULT_VALIDATION_CONTRACT_VERSION` 1.0 | Framework | Canonical Models | None recorded | Frozen | Frozen | `validation/`; treated as frozen (Syntax Design Review §"do not modify the frozen framework"). |
| Response Validator | Orchestrate validation over an `AnalysisResult` | `VALIDATOR_VERSION` 1.0.0 · `RULE_CATALOG_VERSION` 1.0.0 | Implementation | Validation Framework, Canonical Models, ParsedResponse (future) | Wire end-to-end into the platform/CLI | Implementation In Progress | In Progress | Orchestrator class + tests exist (`validation/response/response_validator.py`); **not wired into CLI**; platform catalogue lists it `Planned`. |
| Transport Layer | Validate delivery-boundary facts (exists, non-empty, no timeout, no failure) | Rules at `DEFAULT_RULE_VERSION` 1.0.0 | Implementation | Validation Framework, `LLMResponse`/`ExecutionStatus` | None recorded | Frozen | Frozen | 4 rules (`TRANSPORT-0001…0004`) implemented + tested; Rule Catalog §"Transport Layer Status — FROZEN". |
| Syntax Layer | Judge well-formedness from the Normalization Outcome + observations | `n/a` (not built) | Implementation | Validation Framework, ParsedResponse, `NormalizationResult` | Implement `SYNTAX-0001…0003` after the `ResponseNormalizer` | Architecture Complete | Planned | Rule Catalog §8.2 + Syntax Design Review define it; **no rules implemented**. |
| Schema Layer | Judge structure against the expected shape | `n/a` (not built) | Implementation | Validation Framework, ParsedResponse | Follows Syntax | Architecture Complete | Planned | Rule Catalog only. |
| Structural Layer | Judge structural completeness/consistency | `n/a` (not built) | Implementation | Validation Framework, ParsedResponse | Follows Schema | Architecture Complete | Planned | Rule Catalog only. |
| Content Layer | Judge content-level concerns | `n/a` (not built) | Implementation | Validation Framework, ParsedResponse | Follows Structural | Architecture Complete | Planned | Rule Catalog only. |
| Evidence Layer | Judge presence/adequacy of evidence | `n/a` (not built) | Implementation | Validation Framework, ParsedResponse | Follows Content | Architecture Complete | Planned | Rule Catalog only. |
| Traceability Layer | Judge traceability of claims | `n/a` (not built) | Implementation | Validation Framework, ParsedResponse | Follows Evidence | Architecture Complete | Planned | Rule Catalog only. |
| Reasoning Layer | Judge reasoning integrity | `n/a` (not built) | Implementation | Validation Framework, ParsedResponse, Reasoning Contract | Follows Traceability | Architecture Complete | Planned | Rule Catalog only. |
| Business Rule Layer | Judge domain/business-rule conformance | `n/a` (not built) | Implementation | Validation Framework, ParsedResponse | Follows Reasoning | Architecture Complete | Planned | Rule Catalog only. |

### 5.6 Downstream (known future)

**Lifecycle**

| Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| CP1 Validator | ◑ | n/a | ✓ | ◑ | ✗ | ✗ |

**Governance**

| Capability | Purpose | Current Version | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| ---------- | ------- | --------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| CP1 Validator | Downstream quality gate consuming validated output | `n/a` (not built) | Implementation | Response Validator | None recorded | Implementation In Progress | Planned | `validators/cp1.py` present; platform catalogue lists CP1 Validator `Planned` — see consistency note. |

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
| **Frozen** | Response Normalization subsystem (contract), Transport Layer, Validation Framework. |
| **Completed (Production Ready)** | Ingestion & Core (3), AI Generation implementation (Prompt, Provider, Gemini, Analysis Service), Execution & Platform (5), ParsedResponse. |
| **In Progress** | Response Validator (orchestrator built, not wired), CP1 Validator. |
| **Planned** | ResponseNormalizer + `NORMALIZATION-0001…0005`; Syntax → Business Rule layers (8); Feature/Test Generators. |

## 7. Implementation Roadmap

Remaining milestones in **execution order** (no dates; grounded in the
Response Normalization Contract §13, the Syntax Design Review, and the Rule
Catalog layer order):

1. **ResponseNormalizer** — implement the concrete normalizer and the
   `NORMALIZATION-0001…0005` responsibilities; produce a real `ParsedResponse`.
2. **Response Validator wiring** — register the existing orchestrator as a
   delivered platform capability and wire it end-to-end (CLI/platform catalogue).
3. **Syntax Layer** — implement `SYNTAX-0001…0003` (reads the Normalization
   Outcome from `ParsedResponse` and observations from `NormalizationResult`).
4. **Schema Layer** — implement the Schema rules.
5. **Structural → Content → Evidence → Traceability → Reasoning → Business Rule**
   — implement the remaining validation layers in Rule Catalog order.

> The roadmap lists only work with an existing architectural mandate. Downstream
> layers named in the Architecture Overview (Feature/Test Generation, Execution,
> Failure Intelligence, Governance Dashboard) are known future direction and are
> not scheduled here.
