# Response Validation Framework

| Attribute | Value |
| --------- | ----- |
| Package | `requirement_intelligence/validation/` |
| Status | Foundation — framework **frozen**; canonical models implemented; no rules yet |
| Governing specifications | `docs/architecture/ai-response-validation.md` · `docs/architecture/validation-canonical-models.md` |
| Next task | Concrete validation rules + Response Validator orchestration |

---

## Purpose

The `validation` package is the **mandatory quality gate between AI generation
and every downstream engineering capability** in the Autonomous Test Engineering
Platform.  No requirement normalisation, CP1 validation, feature generation,
test generation, or output writing may consume AI output that has not first
passed through this layer.

This package provides the **framework** — the extensible, deterministic
infrastructure (rule contract, registry, pipeline) — and the **canonical
information model** the framework produces.  It contains no actual validation
logic yet; concrete rules arrive in a subsequent task.

---

## Framework position

The validation framework sits between the canonical models it produces and the
services that consume its verdict:

```text
   Validation Framework        ← this package: registry, pipeline, rule contract
          │
          ▼
   Validation Canonical Models ← ValidationIssue / Summary / Statistics /
          │                       Configuration / FrameworkMetadata / Result
          ▼
   Validation Rules            ← concrete, per-layer rule implementations (future)
          │
          ▼
   Response Validator          ← assembles a pipeline from configuration (future)
          │
          ▼
   Requirement Analysis Service ← upstream producer of the AnalysisResult that the
                                  Response Validator gates before downstream use
```

The framework defines *how* rules are catalogued and executed.  The canonical
models define *what information* a run produces.  The rules supply the actual
checks.  The Response Validator wires a configured pipeline together and exposes
it to the Requirement Analysis Service and other downstream consumers.

---

## Architecture

### Overview

```text
  ┌──────────────────────────────────────────────────────────────────┐
  │                  Response Validation Framework                    │
  │                                                                  │
  │  ValidationConfiguration ──────────────────────────────►         │
  │  (execution policy)                                              │
  │                              ┌────────────────────────┐          │
  │  AnalysisResult ───────────► │  ValidationPipeline    │          │
  │                              │  (orchestrator)        │          │
  │                              └──────────┬─────────────┘          │
  │                                         │ iterates               │
  │                                         ▼                        │
  │                         ┌──────────────────────────────┐         │
  │                         │   ValidationRegistry         │         │
  │                         │   (ordered rule catalogue)   │         │
  │                         └──────────────┬───────────────┘         │
  │                                        │ provides                │
  │                         ┌──────────────▼───────────────┐         │
  │                         │   ValidationRule (abstract)  │         │
  │                         │   × N (one per concern)      │         │
  │                         └──────────────┬───────────────┘         │
  │                                        │ produces                │
  │                                        ▼                         │
  │                         ┌──────────────────────────────┐         │
  │                         │   ValidationIssue × N        │         │
  │                         └──────────────┬───────────────┘         │
  │                                        │ derived + owned into     │
  │                                        ▼                         │
  │   ┌──────────────────────────────────────────────────────────┐  │
  │   │                  ValidationResult                        │  │
  │   │  owns: Summary · Statistics · ValidationIssue collection │  │
  │   │  references: Configuration · FrameworkMetadata           │  │
  │   │  contains: original AnalysisResult                       │  │
  │   │  verdict: PASSED / PASSED_WITH_WARNINGS / FAILED / BLOCKED│  │
  │   └──────────────────────────────────────────────────────────┘  │
  │            ▲ always returned — even when empty (PASSED)           │
  └──────────────────────────────────────────────────────────────────┘
```

### Layered validation pipeline

Rules are executed in fixed layer order, from most foundational to most
semantic.  A foundational failure halts progression before meaningless
secondary errors accumulate (Fail Fast — §3.1 of the AI Response Validation
Architecture).

```text
  AI Response
       │
       ▼
  ┌─────────────────────┐
  │  Transport          │  1 — was a usable response received?
  └──────────┬──────────┘
             ▼
  ┌─────────────────────┐
  │  Syntax / JSON      │  2 — is it well-formed structured data?
  └──────────┬──────────┘
             ▼
  ┌─────────────────────┐
  │  Schema             │  3 — does it match the expected versioned schema?
  └──────────┬──────────┘
             ▼
  ┌─────────────────────┐
  │  Structural         │  4 — are required containers / relationships present?
  └──────────┬──────────┘
             ▼
  ┌─────────────────────┐
  │  Content            │  5 — are field values typed, ranged, and present?
  └──────────┬──────────┘
             ▼
  ┌─────────────────────┐
  │  Evidence           │  6 — are conclusions backed by required evidence?
  └──────────┬──────────┘
             ▼
  ┌─────────────────────┐
  │  Traceability       │  7 — is every element auditable end to end?
  └──────────┬──────────┘
             ▼
  ┌─────────────────────┐
  │  Reasoning          │  8 — is the output internally coherent?
  └──────────┬──────────┘
             ▼
  ┌─────────────────────┐
  │  Business Rule      │  9 — are platform-level structural rules satisfied?
  └──────────┬──────────┘
             ▼
       (future) ValidationResult
```

---

## Modules

### `validation_rule_layer.py`

Defines the **dependency-free** location concept shared by the rule and its
metadata:

* **`ValidationLayer`** — the nine ordered validation concerns as an enum.
* **`LAYER_ORDER`** — the architecture-mandated layer execution sequence.

Both names remain importable from `validation_rule` and from the package root;
this module only changes where they are *defined*, avoiding an import cycle
between `validation_rule` and `validation_rule_metadata`.

### `validation_rule_metadata.py`

`ValidationRuleMetadata` is the **immutable identity model** for a rule.  It
consolidates every descriptive property the rule used to expose individually
into one frozen value object:

| Field | Status | Meaning |
| ----- | ------ | ------- |
| `rule_id` | Active | Stable unique identifier (`<LAYER>-<NNNN>`). |
| `rule_name` | Active | Human-readable label. |
| `rule_version` | Active | Version of *this rule's logic*; defaults to `1.0.0`. |
| `validation_layer` | Active | The single layer the rule belongs to. |
| `enabled` | Active | Whether the rule participates in a run. |
| `tags` | Reserved | Free-form classification labels. |
| `documentation_reference` | Reserved | Pointer to the rule's documentation. |
| `validation_contract_version` | Reserved | Validation *semantics* version targeted. |
| `future_schema_compatibility` | Reserved | Declared schema-evolution marker. |

The object is a frozen value — any attempt to reassign an attribute raises
`dataclasses.FrozenInstanceError`.  Immutable identity is what allows a rule's
metadata to appear safely in result records and observability signals.

**Three independent versions** (never conflate them):

| Version | Scope | Advances when… |
| ------- | ----- | -------------- |
| **Rule Version** (`rule_version`) | One rule's logic | That rule's behaviour changes. |
| **Validation Contract Version** | Validation *semantics* for the whole subsystem (categories, severity, pipeline, result/issue models) | The *meaning* of validation changes (architecture §13). |
| **Validator Version** | The validator *implementation* as a whole | The implementation changes with no change in meaning. |

### `validation_rule.py`

* **`ValidationRule`** — the abstract base class every rule must implement.
* Re-exports `ValidationLayer` and `LAYER_ORDER` for backward compatibility.

A rule now implements a single abstract property — **`metadata`** — returning a
`ValidationRuleMetadata`.  The legacy identity properties (`rule_id`,
`rule_name`, `validation_layer`, `rule_version`, `enabled`) remain as
**convenience wrappers** that read through `metadata`, so every existing caller
keeps working unchanged.

`ValidationRule` is the structural equivalent of `LLMProvider`,
`SourceConnector`, and `BaseMapper` in the platform's other framework
contracts.  Each rule encapsulates exactly one validation concern and is
**immutable**, **stateless**, and **order-independent** (Rule Independence —
§3.11 of the governing architecture).

#### Rule Documentation Contract

Every concrete `ValidationRule` must document these seven sections in its class
docstring.  This is a **documentation standard only — there is no runtime
enforcement** — but it is a conformance requirement for any rule accepted into
the framework:

| Section | Documents |
| ------- | --------- |
| **Purpose** | The single concern the rule validates. |
| **Validation Layer** | Which `ValidationLayer` the rule belongs to. |
| **Inputs** | What part of the response the rule reads. |
| **Outputs** | What findings the rule can produce. |
| **Failure Conditions** | When the rule raises a finding. |
| **Worked Example** | A concrete passing and failing case. |
| **Architecture Reference** | The governing section of the architecture document. |

### `validation_registry.py`

`ValidationRegistry` catalogues `ValidationRule` instances.

* Rules are registered explicitly — no reflection, no dynamic loading.
* Ordering is deterministic: layer order first, registration order within a
  layer.
* Supports retrieval by layer, by enabled status, or all rules.
* Duplicate `rule_id` raises `ValidationRegistryError` immediately.

Mirrors the role of `_PROVIDER_REGISTRY` in the LLM provider framework.

#### Registry lifecycle

A registry has an explicit two-state lifecycle (`RegistryState`):

```text
   OPEN ──register()──► OPEN ──seal() / pipeline construction──► SEALED
                                                                    │
                                         register() ──► ValidationRegistryError
```

* A new registry starts **`OPEN`** and accepts registrations.
* `seal()` transitions it to **`SEALED`** (idempotent); constructing a
  `ValidationPipeline` from a registry seals it automatically.
* Registering into a sealed registry raises `ValidationRegistryError`.
* Retrieval works in either state.

Sealing guarantees the rule set a pipeline executes is **fixed for that
pipeline's lifetime**, which is what makes a validation run reproducible.
Inspect the state via `registry.state` or `registry.is_sealed`.

### `validation_pipeline.py`

`ValidationPipeline` orchestrates rule execution.

* Accepts a populated `ValidationRegistry` and **seals it** on construction.
* `run(analysis_result, configuration=None)` calls `rule.validate(analysis_result)`
  for each enabled rule, in registry order.
* **Always returns a `ValidationResult`** — see *Pipeline output* below.
* Contains **no validation logic, no AI knowledge, no business rules**.  It only
  *derives* a summary and verdict by rolling up the issues the rules produced;
  it never decides trustworthiness itself.

#### Pipeline output — always a `ValidationResult`

`run()` is the **permanent framework contract**: it always returns a
fully-populated `ValidationResult`, and **there are no placeholder return types
(`list[Any]`, `None`, temporary objects) anywhere in the framework**.

* An **empty run** — no rules registered, or zero issues produced — is a *valid*
  execution, **not** a placeholder.  Its `ValidationSummary`,
  `ValidationStatistics`, and `ValidationFrameworkMetadata` are still populated,
  and the verdict is `PASSED`.
* The verdict follows **highest severity wins** (architecture §6, §8): any
  `CRITICAL` ⇒ `BLOCKED`; else any `ERROR` ⇒ `FAILED`; else any `WARNING` ⇒
  `PASSED_WITH_WARNINGS`; else `PASSED`.
* The original `AnalysisResult` is preserved on the result, unaltered.
* A rule that raises propagates the exception unchanged (an infrastructure
  failure, never a verdict) after the pipeline records `PipelineState.FAILED`.

Future implementations must **populate** this object, never replace it.

#### Pipeline lifecycle

The pipeline exposes an **observable** state (`PipelineState`) via
`pipeline.state`.  The state is **informational only — it never influences
validation behaviour**; the findings a run produces are identical regardless of
how the state is read.

```text
   (construct) ─► CREATED ─► READY ─► RUNNING ─► COMPLETED ─► RUNNING ...
                                         │
                                         └─► FAILED ─► RUNNING ...

   DISPOSED is reserved — no current transition enters it.
```

| State | Meaning |
| ----- | ------- |
| `CREATED` | Under construction; not yet ready. |
| `READY` | Construction succeeded; registry sealed; ready to run. |
| `RUNNING` | A `run()` call is in progress. |
| `COMPLETED` | The most recent `run()` finished successfully. |
| `FAILED` | The most recent `run()` raised before completing. |
| `DISPOSED` | Reserved for a future explicit teardown step. |

Designed for future evolution:
- **Fail Fast**: a future revision may halt after a foundational blocking issue.
  Today every enabled rule runs; the halt is a deferred behavioural change.
- **Parallel execution**: Rule Independence makes intra-layer parallelism safe.

### `models/` — the Validation Canonical Models

The implementation-independent information model, governed by
`docs/architecture/validation-canonical-models.md`.  All models inherit the
shared `Schema` base (immutable, strict, `camelCase` serialization) and carry
**information only** — no behaviour, no rules, no I/O.

| Model | Role |
| ----- | ---- |
| `ValidationIssue` | One atomic, immutable finding; severity fixed at creation; evidence optional. |
| `ValidationSummary` | Derived roll-up (counts + health) over the issues; holds **no** issue objects. |
| `ValidationStatistics` | Operational telemetry of a run; never influences the verdict. |
| `ValidationConfiguration` | Execution policy (enabled layers, thresholds, collection flags); never philosophy. |
| `ValidationFrameworkMetadata` | Immutable provenance: framework / contract / pipeline / registry versions. |
| `ValidationResult` | Aggregate root and **sole** framework output (see ownership below). |

Controlled vocabulary (dedicated `StrEnum`s in `models/validation_enums.py`):
`ValidationSeverity` (`INFO`/`WARNING`/`ERROR`/`CRITICAL`), `ValidationVerdict`
(`PASSED`/`PASSED_WITH_WARNINGS`/`FAILED`/`BLOCKED`), `ValidationHealth`
(`HEALTHY`/`WARNING`/`DEGRADED`/`CRITICAL`).

**`ValidationResult` relationships** (per architecture §8):

```text
   ValidationResult
     ├─ owns ──────► ValidationSummary        (derived counts + health)
     ├─ owns ──────► ValidationStatistics     (telemetry)
     ├─ owns ──────► ValidationIssue[]         (immutable tuple; may be empty)
     ├─ references ► ValidationConfiguration   (the governing policy)
     ├─ references ► ValidationFrameworkMetadata (producing-framework provenance)
     └─ contains ──► AnalysisResult            (the preserved original, unaltered)
```

### `validation_exceptions.py`

Framework-level exception hierarchy:

```text
ValidationFrameworkError           ← base; catch this to handle all framework errors
├── ValidationPipelineError        ← pipeline cannot be assembled or executed
├── ValidationRegistryError        ← registry cannot register or retrieve a rule
└── ValidationRuleError            ← a rule violates its contract
```

These are **not** validation findings.  A `ValidationFrameworkError` means the
infrastructure failed, not that an AI response was judged untrustworthy.

---

## Relationship to governing documents

### AI Response Validation Architecture

`docs/architecture/ai-response-validation.md` defines the validation
**philosophy** — why, whether, and how trustworthiness is judged.  This
framework realises that philosophy as executable infrastructure.  The key
architecture principles this framework upholds:

| Principle | How this framework upholds it |
| --------- | ----------------------------- |
| **Fail Fast** (§3.1) | Layer ordering; pipeline halt on a foundational blocking issue (deferred) |
| **Never Guess** (§3.2) | Rules produce findings for missing/ambiguous content; no inference |
| **Preserve Original Response** (§3.3) | Pipeline passes the `AnalysisResult` unchanged and preserves it on the result |
| **Deterministic Validation** (§3.4) | Rules are stateless; registry ordering is stable; summary/verdict are pure derivations |
| **Layered Validation** (§3.5) | Nine ordered layers; each rule owns exactly one concern |
| **Rule Independence** (§3.11) | Rules share no state; any permutation yields the same findings |
| **Provider Independence** (§3.8) | No provider reference anywhere in this framework |

### Validation Canonical Models

`docs/architecture/validation-canonical-models.md` defines the validation
**information model**.  It is **implemented** in `models/` (see above): the five
canonical models plus `ValidationFrameworkMetadata`.  `ValidationPipeline.run()`
returns the aggregate-root `ValidationResult`; **no placeholder return types
remain** anywhere in the framework.

---

## Future work (next tasks)

### Response Validator (future)

A `ResponseValidator` orchestrator will assemble a `ValidationPipeline` from a
`ValidationConfiguration` and expose the high-level API consumed by the
`RequirementAnalysisService` and other downstream services.

### Concrete validation rules (future, per layer)

Rules implementing the nine layers will be added under `validation/rules/`
(or per-layer sub-packages) as they are specified and approved.

---

## Design decisions

| Decision | Rationale |
| -------- | --------- |
| **Explicit registration only** | Avoids implicit magic; keeps the framework testable and auditable. Mirrors the LLM factory pattern. |
| **Registry owns ordering** | Single source of truth; the pipeline never re-sorts. Separation of ordering logic from execution logic. |
| **Instances, not classes, in registry** | Rules are stateless; sharing instances is safe and avoids repeated construction. |
| **`run()` always returns `ValidationResult`** | The permanent contract: an empty run is a valid `PASSED` result, never a placeholder. Future work populates this object, never replaces it. |
| **Summary/verdict derived in the pipeline, not the models** | Models hold information only; rolling issues up into a summary/verdict is pure derivation, kept in the framework-integration layer. |
| **Validation enums live beside the models** | The platform's `shared` `ValidationVerdict` (CP1: PASS/FAIL/WARN) has different semantics; the subsystem's four-state vocabulary is kept local to avoid name collision. |
| **Framework exceptions separate from findings** | A `ValidationFrameworkError` is an infrastructure failure; a `ValidationIssue` is a normal outcome. Conflating them would confuse error handling. |
| **`enabled` defaults to `True`** | Opt-in disable (override to `False`) is safer than opt-in enable. A rule that forgets to return `True` would silently skip validation. |
| **Identity in immutable `ValidationRuleMetadata`** | A single frozen identity value is versioned, observable, and safe to embed in result records. Legacy identity properties remain as read-through wrappers, so no caller breaks. |
| **Registry sealing** | Freezing the rule set at pipeline construction guarantees a reproducible run; late registration would let a pipeline's behaviour drift silently. |
| **Observable but inert pipeline state** | `PipelineState` aids observability and debugging, but the pipeline never branches on it — keeping behaviour deterministic and independent of lifecycle bookkeeping. |
| **Documentation contract, not runtime check** | The seven required docstring sections are enforced by review, not code; runtime enforcement would add overhead and could not assert prose quality anyway. |
