# Response Validation Framework

| Attribute | Value |
| --------- | ----- |
| Package | `requirement_intelligence/validation/` |
| Status | Foundation — framework skeleton, no rules yet |
| Governing specifications | `docs/architecture/ai-response-validation.md` · `docs/architecture/validation-canonical-models.md` |
| Next task | Canonical validation models (`ValidationIssue`, `ValidationResult`, …) |

---

## Purpose

The `validation` package is the **mandatory quality gate between AI generation
and every downstream engineering capability** in the Autonomous Test Engineering
Platform.  No requirement normalisation, CP1 validation, feature generation,
test generation, or output writing may consume AI output that has not first
passed through this layer.

This package provides the **framework skeleton** — the extensible, deterministic
infrastructure that future validation rules plug into.  It contains no actual
validation logic; that arrives in subsequent tasks.

---

## Architecture

### Overview

```text
  ┌──────────────────────────────────────────────────────────────────┐
  │                  Response Validation Framework                    │
  │                                                                  │
  │  ValidationConfiguration ──────────────────────────────►         │
  │  (future canonical model)                                        │
  │                              ┌────────────────────────┐          │
  │  AI Response ──────────────► │  ValidationPipeline    │          │
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
  │                         └──────────────────────────────┘         │
  │                                        │ produces (future)       │
  │                                        ▼                        │
  │                         ┌──────────────────────────────┐         │
  │                         │   ValidationIssue            │         │
  │                         │   (next task)                │         │
  │                         └──────────────────────────────┘         │
  │                                        │ aggregated into         │
  │                                        ▼                         │
  │                         ┌──────────────────────────────┐         │
  │                         │   ValidationResult           │         │
  │                         │   (next task)                │         │
  │                         └──────────────────────────────┘         │
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

### `validation_rule.py`

Defines:

* **`ValidationLayer`** — the nine ordered validation concerns as an enum.
* **`LAYER_ORDER`** — the architecture-mandated layer execution sequence.
* **`ValidationRule`** — the abstract base class every rule must implement.

`ValidationRule` is the structural equivalent of `LLMProvider`,
`SourceConnector`, and `BaseMapper` in the platform's other framework
contracts.  Each rule encapsulates exactly one validation concern and is
**immutable**, **stateless**, and **order-independent** (Rule Independence —
§3.11 of the governing architecture).

### `validation_registry.py`

`ValidationRegistry` catalogues `ValidationRule` instances.

* Rules are registered explicitly — no reflection, no dynamic loading.
* Ordering is deterministic: layer order first, registration order within a
  layer.
* Supports retrieval by layer, by enabled status, or all rules.
* Duplicate `rule_id` raises `ValidationRegistryError` immediately.

Mirrors the role of `_PROVIDER_REGISTRY` in the LLM provider framework.

### `validation_pipeline.py`

`ValidationPipeline` orchestrates rule execution.

* Accepts a populated `ValidationRegistry`.
* Calls `rule.validate(response)` for each enabled rule, in registry order.
* Collects and returns findings without interpreting them.
* Contains **no validation logic, no AI knowledge, no business rules**.

Designed for future evolution:
- **Fail Fast**: will halt after foundational blocking findings once canonical
  models are available.
- **Parallel execution**: Rule Independence makes intra-layer parallelism safe.
- **`ValidationResult`**: the return type will change once canonical models are
  defined.

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
| **Fail Fast** (§3.1) | Layer ordering; pipeline halts on blocking findings (future) |
| **Never Guess** (§3.2) | Rules produce findings for missing/ambiguous content; no inference |
| **Preserve Original Response** (§3.3) | Pipeline passes response unchanged; rules must not mutate it |
| **Deterministic Validation** (§3.4) | Rules are stateless; registry ordering is stable |
| **Layered Validation** (§3.5) | Nine ordered layers; each rule owns exactly one concern |
| **Rule Independence** (§3.11) | Rules share no state; any permutation yields the same findings |
| **Provider Independence** (§3.8) | No provider reference anywhere in this framework |

### Validation Canonical Models

`docs/architecture/validation-canonical-models.md` defines the validation
**information model** — the meaning, ownership, relationships, and lifecycle of
`ValidationIssue`, `ValidationSummary`, `ValidationStatistics`,
`ValidationResult`, and `ValidationConfiguration`.

This framework does **not** yet contain those models.  The current
`validate()` return type (`list[Any]`) and `run()` return type (`list[Any]`)
are open placeholders.  The next task fills them in with the canonical types.

---

## Future work (next tasks)

### Canonical Validation Models (next task)

The following will be added in the next task under this package or a sibling:

| Model | Purpose |
| ----- | ------- |
| `ValidationIssue` | Atomic, immutable finding — one rule, one condition |
| `ValidationSummary` | Derived roll-up of the issue collection |
| `ValidationStatistics` | Operational metrics of a validation run |
| `ValidationResult` | Immutable aggregate root — the sole pipeline output |
| `ValidationConfiguration` | Input that shapes a run; never alters verdict logic |

Once these are defined:
1. `ValidationRule.validate()` will be typed as `list[ValidationIssue]`.
2. `ValidationPipeline.run()` will return `ValidationResult`.
3. The pipeline will gain Fail Fast halt logic.

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
| **`list[Any]` return placeholder** | Stable signature before canonical models exist; typed `list[ValidationIssue]` in the next task without a breaking change. |
| **Framework exceptions separate from findings** | A `ValidationFrameworkError` is an infrastructure failure; a `ValidationIssue` is a normal outcome. Conflating them would confuse error handling. |
| **`enabled` defaults to `True`** | Opt-in disable (override to `False`) is safer than opt-in enable. A rule that forgets to return `True` would silently skip validation. |
