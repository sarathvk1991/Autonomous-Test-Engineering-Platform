# Platform Capability Matrix

| Attribute | Value |
| --------- | ----- |
| Document type | Engineering Governance / Executive Maturity View |
| Status | Living document — governance artifact |
| Governance baseline | **Validation Platform v1.0.0** (Git tag `v1.0.0-validation-platform`; see [release notes](../releases/v1.0.0-validation-platform.md)) |
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
| `CAP-040…059` | Validation | `CAP-040…052` | `CAP-053…059` |
| `CAP-060…` | Downstream / Future | `CAP-060…066` | `CAP-067…` |

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
| CAP-030 | Response Normalization (subsystem) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CAP-031 | ParsedResponse | ✓ | n/a | ✓ | ✓ | ✓ | ◑ |
| CAP-032 | ResponseNormalizer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Governance**

| ID | Capability | Purpose | Current Version | Introduced In | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| -- | ---------- | ------- | --------------- | ------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| CAP-030 | Response Normalization (subsystem) | Turn `LLMResponse` into the canonical structure exactly once | `FRAMEWORK_VERSION` 1.0.0 · `NORMALIZATION_CONTRACT_VERSION` 1.0 | 1.0.0 | Implementation | Canonical Models, Provider Framework | None recorded | Production Ready | Complete · Frozen | **Subsystem complete and operational**: generic framework (registry/pipeline/result/execution-context) + the five internal `NORMALIZATION-0001…0005` stages + `ResponseNormalizer` wired end-to-end (`normalization/`, tested). Governing contracts frozen. The five stages are internal to the `ResponseNormalizer`, not framework units (ADR-0002). |
| CAP-031 | ParsedResponse | The immutable, shared canonical structural representation | `PARSED_RESPONSE_VERSION` 1.0 | 1.0.0 | Shared | `NormalizationOutcome` enum, Canonical Models §8 | None recorded | Production Ready | Complete | `models/parsed_response.py`; ownership aligned (observations owned by `NormalizationResult`); now assembled by stage `NORMALIZATION-0005` and carried on the `NormalizationResult`. |
| CAP-032 | ResponseNormalizer | Concrete producer of a real `ParsedResponse`; owns the `NORMALIZATION-0001…0005` **internal stages** + Assembly State (ADR-0002) | `n/a` (via `FRAMEWORK_VERSION` 1.0.0) | 1.0.0 | Implementation | Normalization Framework (CAP-030), ParsedResponse (CAP-031), `LLMResponse`, Normalization Assembly Contract | None recorded | Production Ready | Complete | **Implemented and wired end-to-end**: the five internal stages (`NORMALIZATION-0001…0005`), the Assembly State, the Stage Coordinator, the JSON structure recoverer, and the orchestration populate a real `ParsedResponse` (`normalization/response/`, tested incl. end-to-end). Stages are internal to the normalizer, not framework units (ADR-0002); governed by the frozen **Assembly Contract** and **Stage Implementation Contract**. |

### 5.5 Validation

**Lifecycle**

| ID | Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| -- | ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| CAP-040 | Validation Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CAP-041 | Response Validator | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| CAP-042 | Transport Layer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CAP-043 | Syntax Layer | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| CAP-044 | Schema Layer | ✓ | ✓ | ✓ | ◑ | ✓ | ✗ |
| CAP-045 | Structural Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-046 | Content Layer | ✓ | ✓ | ✓ | ◑ | ✓ | ✗ |
| CAP-047 | Evidence Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-048 | Traceability Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-049 | Reasoning Layer | ✓ | ✓ | ✓ | ◑ | ✓ | ✗ |
| CAP-050 | Business Rule Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| CAP-051 | ValidationInput (canonical input) | ✓ | n/a | ✓ | ✓ | ✓ | ✗ |
| CAP-052 | Validation Profiles | ✓ | ✓ | n/a | ✓ | ✓ | ✗ |

**Governance**

| ID | Capability | Purpose | Current Version | Introduced In | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| -- | ---------- | ------- | --------------- | ------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| CAP-040 | Validation Framework | Reusable rule/registry/pipeline infrastructure | `FRAMEWORK_VERSION` 1.0.0 · `DEFAULT_VALIDATION_CONTRACT_VERSION` 1.0 | 1.0.0 | Framework | Canonical Models | None recorded | Frozen | Frozen | `validation/`; treated as frozen (Syntax Design Review §"do not modify the frozen framework"). |
| CAP-041 | Response Validator | Orchestrate validation over a `ValidationInput` (ADR-0003) | `VALIDATOR_VERSION` 1.0.0 · `RULE_CATALOG_VERSION` 1.0.0 | 1.0.0 | Implementation | Validation Framework, Canonical Models, ValidationInput (CAP-051) | None recorded | Production Ready | Complete | Orchestrator + tests (`validation/response/response_validator.py`); **wired end-to-end**: the composition root (`validator_factory`) assembles the fully-wired validator, `PlatformContext` is the single construction hub, and the CLI `--validate` phase builds the `ValidationInput` via the `ResponseNormalizer`. The complete `ValidationResult` is persisted (`validation_result.json`) and rendered (`validation_report.md`); governed Validation Profiles (CAP-052) select the rule subset. |
| CAP-042 | Transport Layer | Validate delivery-boundary facts (exists, non-empty, no timeout, no failure) | Rules at `DEFAULT_RULE_VERSION` 1.0.0 | 1.0.0 | Implementation | Validation Framework, ValidationInput (CAP-051), `LLMResponse`/`ExecutionStatus` | None recorded | Frozen | Frozen | 4 rules (`TRANSPORT-0001…0004`) implemented + tested; **migrated to read `response.analysis_result`** under ADR-0003 (identity/severity/blocking unchanged). Rule Catalog §"Transport Layer Status — FROZEN". |
| CAP-043 | Syntax Layer | Judge well-formedness from the Normalization Outcome + observations | Rules at `DEFAULT_RULE_VERSION` 1.0.0 | 1.0.0 | Implementation | Validation Framework, ValidationInput (CAP-051), ParsedResponse, `NormalizationResult` | None recorded | Production Ready | Complete | 3 rules (`SYNTAX-0001…0003`) implemented + tested. Rule Catalog §8.2 + Syntax Design Review define it; input path resolved by ADR-0003 (`ValidationInput`). |
| CAP-044 | Schema Layer | Judge structure against the expected shape | Rules at `DEFAULT_RULE_VERSION` 1.0.0 | 1.0.0 | Implementation | Validation Framework, ParsedResponse | None (`SCHEMA-0003` governed-deferred) | Implementation In Progress | In Progress | `SCHEMA-0001` (RequiredSectionsRule), `SCHEMA-0002` (FieldTypesRule), and `SCHEMA-0004` (RequiredArraysRule) implemented + tested. **`SCHEMA-0003` (EnumerationsRule) is Reserved · Deferred · Awaiting governed enumeration (ADR-0005)** — the governed response schema has no enumerated field, so the rule has nothing to validate; its ID is frozen and never reused. |
| CAP-045 | Structural Layer | Judge composition/hierarchy/organization | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse | Await Structural cataloguing ADR | Architecture Complete | Deferred | Boundary frozen (ADR-0004); **no active catalogued rules** (`STRUCTURE-0001…0004` Deprecated). Concrete composition rules await a governed **composable/nested response** *and* a cataloguing ADR (ADR-0006 §D). |
| CAP-046 | Content Layer | Judge content-level concerns | Rules at `DEFAULT_RULE_VERSION` 1.0.0 | 1.0.0 | Implementation | Validation Framework, ParsedResponse | None (`CONTENT-0003/0004` deferred) | Implementation In Progress | In Progress | Per ADR-0006: `CONTENT-0001` (EmptyRequirement) **implemented + tested**, `CONTENT-0002` (DuplicateRequirement — scope frozen **within-collection** by ADR-0007) **implemented + tested**. **Reserved · Deferred** `CONTENT-0003` (no per-item description), `CONTENT-0004` (no per-item confidence). |
| CAP-047 | Evidence Layer | Judge presence/adequacy of evidence | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse | Await schema enrichment | Architecture Complete | Deferred | Per ADR-0006: **all Reserved · Deferred** (`EVIDENCE-0001…0003`) — the governed response carries no per-item evidence reference. |
| CAP-048 | Traceability Layer | Judge traceability of claims | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse | Await schema enrichment | Architecture Complete | Deferred | Per ADR-0006: **all Reserved · Deferred** (`TRACEABILITY-0001…0003`) — no per-item source/trace linkage in the governed response. |
| CAP-049 | Reasoning Layer | Judge reasoning integrity | Rules at `DEFAULT_RULE_VERSION` 1.0.0 | 1.0.0 | Implementation | Validation Framework, ParsedResponse, Reasoning Contract | None (`REASONING-0001/0003` deferred) | Implementation In Progress | In Progress | Per ADR-0006 (as revised): **`REASONING-0002`** comparison mechanism frozen byte-exact by ADR-0008 — **implemented + tested**. **`REASONING-0001`** (ContradictoryRequirement) is **Reserved · Deferred** by ADR-0009 (Proposed) — no governed deterministic contradiction mechanism. **`REASONING-0003`** (CircularLogic) is **Reserved · Deferred** by ADR-0010 (Proposed) — no governed deterministic mechanism (needs an inferential dependency structure the response lacks). Both supersede their ADR-0006 Implementable classifications. **Reasoning layer fully dispositioned: 0002 implemented; 0001 & 0003 deferred.** Semantic contradiction/coherence detection is a future capability behind a future ADR. |
| CAP-050 | Business Rule Layer | Judge domain/business-rule conformance | `n/a` (not built) | Not Recorded | Implementation | Validation Framework, ParsedResponse | Await governed policy | Architecture Complete | Deferred | Per ADR-0006: **all Reserved · Deferred** (`BUSINESS-0001…0004`) — no governed minimum/coverage/completeness policy exists to measure against. |
| CAP-051 | ValidationInput (canonical input) | The immutable, execution-scoped binding of `AnalysisResult` + `NormalizationResult` consumed by validation (ADR-0003) | `VALIDATION_INPUT_VERSION` 1.0 | 1.0.0 | Shared | AnalysisResult, NormalizationResult (incl. ParsedResponse) | None recorded | Production Ready | Complete | `validation/models/validation_input.py`; implemented + tested (`tests/unit/test_validation_input.py`). Owns only the binding; references never copies. Governed by ADR-0003 + Canonical Models §8A. |
| CAP-052 | Validation Profiles | Governed, immutable rule-selection identities (which layers' rules run) | `n/a` (orchestration) | 1.0.0 | Implementation | Validation Framework, Response Validator (CAP-041) | Add profiles additively as new layers land | Production Ready | Complete | `validation/profiles/` — `ValidationProfileRegistry` owns six governed profiles (`default`, `strict`, `transport-only`, `syntax-only`, `schema-only`, `content-review`); the Validation Factory builds a registry per profile; ordering stays governed by `LAYER_ORDER`. Orchestration only — rules are unaware of profiles. Selected via CLI `--validation-profile`; recorded in `validation_result.json` and `validation_report.md`. Distinct from the Response Validator's internal run-policy `ValidationProfile`. |

### 5.6 Downstream (known future)

**Lifecycle**

| ID | Capability | Architecture | Framework | Canonical Models | Implementation | Testing | Frozen |
| -- | ---------- | :----------: | :-------: | :--------------: | :------------: | :-----: | :----: |
| CAP-060 | CP1 Validator | ✓ | n/a | ✓ | ◑ | ✗ | ✗ |
| CAP-061 | Engineering Readiness Criteria Catalog | ✓ | n/a | n/a | ✓ | n/a | ✗ |
| CAP-062 | CP1 Canonical Models | ✓ | n/a | ✓ | ✓ | ✓ | ✗ |
| CAP-063 | CP1 Framework | ✓ | ✓ | n/a | ✓ | ✓ | ✗ |
| CAP-064 | Validation → CP1 Seam | ✓ | n/a | n/a | ✓ | ✓ | ✗ |
| CAP-065 | CP1 Engine | ✓ | ✓ | n/a | ✓ | ✓ | ✗ |
| CAP-066 | CP1 Composition Root | ✓ | n/a | n/a | ✓ | ✓ | ✗ |
| CAP-067B | CP1 PlatformContext & CLI Wiring | ✓ | n/a | n/a | ✓ | ✓ | ✗ |

**Governance**

| ID | Capability | Purpose | Current Version | Introduced In | Owner | Dependencies | Next Planned Milestone | Maturity | Status | Notes |
| -- | ---------- | ------- | --------------- | ------------- | ----- | ------------ | ---------------------- | -------- | ------ | ----- |
| CAP-060 | CP1 Validator | Downstream quality gate consuming validated output | `n/a` (umbrella) | 1.0.0 | Implementation | Response Validator; CP1 Models (CAP-062); CP1 Framework (CAP-063) | CP1 engine + Validation → CP1 seam | Implementation In Progress | In Progress | Umbrella CP1 capability, now **architecturally governed by ADR-0011 (Accepted)**. Decomposed into CAP-061 (Criteria Catalog), CAP-062 (models), CAP-063 (framework), CAP-064 (seam), CAP-065 (engine), CAP-066 (composition root), the first criterion `CP1-0001` (CAP-067A, implemented), and **PlatformContext/CLI wiring (CAP-067B, implemented)** — CP1 now runs end-to-end in the application pipeline. Remaining: further governed criteria. Legacy `validators/cp1.py` stub **reconciled (CAP-063A)** — duplicate models removed; retained only as the `CP1Validator` placeholder per ADR-0011 §D9 (owns no models/logic). |
| CAP-061 | Engineering Readiness Criteria Catalog | The governed catalog defining which engineering-readiness criteria exist (`CP1-NNNN` identity, lifecycle, ordering, severity/verdict contribution) | `Catalog Version` 1.1.0 (**one criterion**) | 1.0.0 | Architecture | ADR-0012 · ADR-0013 | Next governed criterion (via §11) | Production Ready | Complete · **1 criterion implemented** | `docs/architecture/engineering-readiness-criteria-catalog.md`; governed by **ADR-0012 (Accepted)**. First criterion **`CP1-0001` (EngineeringInputAvailabilityCriterion)** governed by **ADR-0013 (Accepted)** and **Implemented** (CAP-067A; `cp1/criteria/engineering_input_availability.py`, registered in the composition root) — deterministic pooled-requirement-count ≥ 1, `CP1Input`-only, 100% unit-tested (`tests/unit/test_cp1_engineering_input_availability.py`). The CP1 analogue of the Validation Rule Catalog. |
| CAP-062 | CP1 Canonical Models | The immutable CP1 information models (`CP1Input`, `CP1Result`, `CP1Finding`, `CP1FrameworkMetadata`) | `CP1_INPUT_VERSION` 1.0 · `CP1_RESULT_VERSION` **1.1** · `CP1_FINDING_VERSION` 1.0 | 1.0.0 | Shared | ValidationResult · NormalizationResult (CP1Input); `shared` ValidationVerdict | CP1 engine (later milestone) | Production Ready | Complete | `requirement_intelligence/cp1/models/` (first-class **CP1 subsystem**, mirroring `validation/` and `normalization/`); governed by **ADR-0011 (Accepted)**; `CP1Input` mirrors `ValidationInput` (same-execution integrity); `CP1Result` now **references `CP1FrameworkMetadata`** (provenance), mirroring `ValidationResult` — additive, `CP1_RESULT_VERSION` 1.0→1.1. Flat `CP1-NNNN` finding identity (ADR-0012). 100% unit-tested (`tests/unit/test_cp1_models.py`). |
| CAP-063 | CP1 Framework | Reusable, behaviour-free CP1 engine infrastructure (criterion contract, registry, pipeline, provenance) | `CP1_FRAMEWORK_VERSION` 1.0.0 · `CP1_PIPELINE_VERSION` 1.0.0 · `CP1_REGISTRY_VERSION` 1.0.0 | 1.0.0 | Framework | CP1 Canonical Models (CAP-062) | CP1 engine (verdict aggregation + `CP1Result` assembly) | Production Ready | Complete | `requirement_intelligence/cp1/framework/`; mirrors the frozen Validation Framework; **flat** `CP1-NNNN` registry (no layers, ADR-0012 §4); pipeline **collects findings, derives no verdict** (aggregation reserved to the engine, ADR-0012 §8). Behaviour-free — knows nothing about engineering readiness. 100% unit-tested (`tests/unit/test_cp1_framework.py`). No criterion exists (catalog empty). |
| CAP-064 | Validation → CP1 Seam | Pure-orchestration handoff: gate on the Validation verdict, then bind one `CP1Input` | `n/a` (orchestration) | 1.0.0 | Shared (above both boundaries) | ValidationResult (CAP-041) · NormalizationResult · CP1Input (CAP-062) | PlatformContext/CLI wiring; CP1 engine | Production Ready | Complete | `requirement_intelligence/cp1/response/cp1_handoff.py` (`ValidationToCP1Handoff`); owned **above both boundaries** (ADR-0011 §D4); gates on `PASSED`/`PASSED_WITH_WARNINGS` (§D5), else returns `None`. References (never copies) `ValidationResult` + `NormalizationResult`; same-execution invariant delegated to `CP1Input`. Stateless; owns **only** the transfer — no CP1 execution/aggregation/`CP1Result`. 100% unit-tested (`tests/unit/test_cp1_handoff.py`). |
| CAP-065 | CP1 Engine | Execute the registered governed criteria and aggregate their findings into the overall CP1 verdict | `n/a` (orchestration) | 1.0.0 | Implementation | CP1 Framework (CAP-063); CP1 Canonical Models (CAP-062) | Composition root; first criterion `CP1-0001`; PlatformContext/CLI wiring | Production Ready | Complete | `requirement_intelligence/cp1/engine/cp1_engine.py` (`CP1Engine`). The **"Aggregate Result"** stage (ADR-0011 §D7): accepts a `CP1Input` + a `CP1CriterionPipeline`, executes it **once**, aggregates findings → `PASS`/`FAIL`/`WARN` (ADR-0012 §8: any FAIL→FAIL; else any WARN→WARN; else PASS), and assembles the immutable `CP1Result` (preserving `CP1Input` + `CP1FrameworkMetadata`). **Criteria own engineering policy; the engine owns orchestration only** — no criteria/thresholds/heuristics/policy, no registry/pipeline construction. Stateless, deterministic, thread-safe. 100% unit-tested (`tests/unit/test_cp1_engine.py`). |
| CAP-066 | CP1 Composition Root | Explicit, deterministic assembly of the CP1 components into a ready-to-run service | `n/a` (composition) | 1.0.0 | Implementation | CP1 Framework (CAP-063); CP1 Engine (CAP-065) | First criterion `CP1-0001`; PlatformContext/CLI wiring | Production Ready | Complete | `requirement_intelligence/cp1/response/cp1_composition.py` (`build_cp1_service` → `CP1Service`). Builds an **empty** registry (zero governed criteria — catalog empty, ADR-0012), registers criteria **explicitly** (none), seals it, constructs the `CP1Engine`, and exposes a single `run(cp1_input) → CP1Result` entry point (hiding registry/pipeline). **Owns only assembly/wiring** — no criteria/policy/thresholds; no reflection/auto-registration/DI/service-locator. Holds only immutable wiring (sealed registry + stateless engine); builds a fresh pipeline per run → stateless, thread-safe, deterministic. 100% unit-tested (`tests/unit/test_cp1_composition.py`). |
| CAP-067B | CP1 PlatformContext & CLI Wiring | Integrate the assembled CP1 subsystem into the application pipeline: `Analysis → Normalization → Validation → ValidationToCP1Handoff → CP1Service.run() → Execution Package` | `n/a` (integration) | 1.0.0 | Implementation | CP1 Composition Root (CAP-066); Validation → CP1 Seam (CAP-064); PlatformContext; CLI | Downstream consumption of `CP1Result` (reporting/persistence — future) | Production Ready | Complete | `PlatformContext.cp1_service` owns the **single** `CP1Service`, built exclusively via `build_cp1_service()` (CAP-066); `PlatformContext.create_validation_to_cp1_handoff()` constructs the seam (CAP-064). The CLI (`scripts/run_requirement_analysis.py::run_cp1_phase`) executes validation, invokes `ValidationToCP1Handoff`, calls `CP1Service.run()` **only** when a `CP1Input` is returned (gate open, ADR-0011 §D5), and places the `CP1Result` into the execution flow. The CLI constructs **no** registry/pipeline/criteria/engine/`CP1Input` and invents no gating/aggregation. `ExecutionData` **transports** the `CP1Result` only — no persistence/reporting/rendering added this milestone. Covered by `tests/unit/test_run_requirement_analysis.py` (PlatformContext single-service ownership, CLI orchestration, PASS→runs / FAIL·BLOCKED→skipped, end-to-end, determinism, thread safety). |

## 6. Overall Platform Health

Objective counts, derived directly from the repository (no estimation):

| View | Derivation | Result |
| ---- | ---------- | ------ |
| **Architecture capability catalogue** | `platform_metadata.ARCHITECTURE_COMPONENTS` with `available=True` | **11 of 14** components available (78.6%). Not available: CP1 Validator, Feature Generator, Test Generator. |
| **Validation layers implemented** | Rule modules under `validation/rules/` | **5 of 9** layers have implemented rules (Transport, Syntax, Schema, Content, Reasoning) — **13 rules total**. Structural, Evidence, Traceability, and Business Rule are deferred (ADR-0005/0006/0009/0010). |
| **Validation layers frozen** | Freeze statements in the Rule Catalog | **1 of 9** frozen (Transport); Syntax/Schema/Content/Reasoning implemented but not yet freeze-declared. |
| **LLM providers active** | `platform_metadata.PROVIDERS` with `available=True` | **1 of 5** (Gemini; four reserved). |
| **Response Normalization** | Subsystem completeness | **Complete**: framework + `ParsedResponse` + all five internal `NORMALIZATION-0001…0005` stages + `ResponseNormalizer` wired end-to-end. |

| Bucket | Capabilities |
| ------ | ------------ |
| **Frozen** | Response Normalization subsystem (CAP-030), ResponseNormalizer (CAP-032), Transport Layer (CAP-042), Validation Framework (CAP-040). |
| **Completed (Production Ready)** | Ingestion & Core (CAP-001…003), AI Generation implementation (CAP-011…014), Execution & Platform (CAP-020…024), Response Normalization subsystem (CAP-030), ParsedResponse (CAP-031), ResponseNormalizer (CAP-032), **Response Validator (CAP-041, wired end-to-end incl. persistence + reporting)**, Syntax Layer (CAP-043), ValidationInput (CAP-051), **Validation Profiles (CAP-052)**, **CP1 Canonical Models (CAP-062)**, **CP1 Framework (CAP-063)**, **Validation → CP1 Seam (CAP-064)**, **CP1 Engine (CAP-065)**, **CP1 Composition Root (CAP-066)**, **CP1 PlatformContext & CLI Wiring (CAP-067B)**. |
| **Governed (complete)** | Engineering Readiness Criteria Catalog (CAP-061) — one criterion **implemented** (`CP1-0001`, ADR-0013 Accepted). |
| **Partially implemented** | Schema Layer (CAP-044: `SCHEMA-0001/0002/0004`; `0003` deferred), Content Layer (CAP-046: `CONTENT-0001/0002`), Reasoning Layer (CAP-049: `REASONING-0002`). |
| **In Progress** | CP1 Validator umbrella (CAP-060) — models, framework, seam, engine, composition root, the first criterion `CP1-0001`, **and PlatformContext/CLI wiring (CAP-067B)** done; CP1 now runs end-to-end. Remaining: further governed criteria. |
| **Planned / Deferred** | Structural, Evidence, Traceability, Business Rule layers (CAP-045/047/048/050); Feature/Test Generators. |

## 7. Implementation Roadmap

The deterministic validation initiative is **feature-complete for the currently
governed response schema**. The following milestones are **complete**:

> **Completed:** **ResponseNormalizer (CAP-032)** — the concrete normalizer and the
> five internal `NORMALIZATION-0001…0005` stages produce a real `ParsedResponse`,
> wired end-to-end and tested. This closes the Response Normalization milestone.

> **Completed:** **ADR-0003 plumbing — `ValidationInput` (CAP-051)** — the canonical
> Normalization → Validation input is implemented; the Response Validator and
> Validation Pipeline consume it; the Transport rules are migrated.

> **Completed:** **Syntax Layer (CAP-043)** — `SYNTAX-0001…0003` implemented + tested.

> **Completed:** **Response Validator wiring (CAP-041)** — the composition root
> (`validator_factory`), `PlatformContext`, and the CLI `--validate` phase wire the
> validator end-to-end; `ValidationResult` is persisted (`validation_result.json`)
> and rendered (`validation_report.md`).

> **Completed:** **Validation Profiles (CAP-052)** — six governed profiles select the
> rule subset via CLI `--validation-profile`; ordering stays governed by `LAYER_ORDER`.

Remaining validation work — **all governed-deferred pending a future
schema-enrichment / semantic-reasoning ADR** (no dates; grounded in ADR-0005/0006/
0009/0010 and the Rule Catalog layer order):

1. **Schema `SCHEMA-0003`** — Reserved · Deferred (ADR-0005): no governed enumerated field.
2. **Content `CONTENT-0003/0004`** — Reserved · Deferred (ADR-0006): no per-item
   description/confidence in the governed response.
3. **Reasoning `REASONING-0001/0003`** — Reserved · Deferred (ADR-0009/0010): no
   governed deterministic contradiction/circular-logic mechanism.
4. **Structural, Evidence, Traceability, Business Rule layers (CAP-045/047/048/050)** —
   Deferred: await a governed composable/enriched response and a cataloguing ADR.

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
