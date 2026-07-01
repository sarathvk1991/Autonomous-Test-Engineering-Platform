# Response Normalization Framework

The permanent infrastructure through which every future **normalization
responsibility** executes. It is the framework half of the **Response
Normalization Layer** — the permanent platform subsystem that sits between the
provider-independent `LLMResponse` and the Response Validator, governed by
[`docs/architecture/response-normalization-contract.md`](../../../docs/architecture/response-normalization-contract.md).

> **Phase 1 scope.** This package is **framework infrastructure only**. It
> implements **no** normalization responsibility, **no** parsing, **no**
> JSON/format-specific behaviour, **no** provider behaviour, **no**
> `ParsedResponse`, **no** `ResponseNormalizer`, and **no** Syntax rule. Those are
> future tasks. This framework exists so they have a stable, governed foundation.

---

## Architecture

```text
   LLMResponse                         (provider-independent text + outcome)
        │
        ▼
   Response Normalization Layer        ◄── this subsystem (permanent)
        │  registry → pipeline → result        no validation / repair / interpretation
        ▼
   ParsedResponse                      (future Core Canonical Model — NOT built here)
        │
        ▼
   Response Validator                  (first consumer; never normalizes)
```

The framework owns **only** orchestration:

| Owned | Not owned (ever) |
| ----- | ---------------- |
| responsibility registration | parsing |
| execution ordering | validation |
| execution lifecycle | provider interaction |
| configuration | repair |
| framework metadata | business interpretation |
| execution statistics | schema validation |
| result assembly | syntax validation |

It is **implementation-, provider-, and format-independent**: the responsibility
contract is typed `Any` for its input, no module imports a provider or a
serialization format, and nothing parses anything.

---

## Components

| Module | Responsibility |
| ------ | -------------- |
| `normalization_responsibility.py` | `NormalizationResponsibility` — the abstract contract (one public method, `normalize`). The sibling of `ValidationRule`. |
| `normalization_metadata.py` | `NormalizationResponsibilityMetadata` — immutable runtime identity (`NORMALIZATION-NNNN`, version, descriptive `order`, reserved extension points). The sibling of `ValidationRuleMetadata`. |
| `normalization_registry.py` | `NormalizationRegistry` + `RegistryState` — registration, ordering, sealing, duplicate prevention. |
| `normalization_pipeline.py` | `NormalizationPipeline` + `PipelineState` — orchestration, lifecycle, statistics, result assembly. |
| `normalization_layer.py` | `NormalizationLayer` — the framework seat of the subsystem (composes registry + pipeline). **Not** the `ResponseNormalizer`. |
| `normalization_exceptions.py` | The `NormalizationFrameworkError` hierarchy. |
| `../models/` | `NormalizationObservation`, `NormalizationConfiguration`, `NormalizationStatistics`, `NormalizationFrameworkMetadata`, `NormalizationResult`. |
| `../response/` | `NormalizationExecutionContext` + `build_normalization_execution_context` — the immutable **execution identity** of a run (see below). |

---

## Lifecycle

**Registry** (`OPEN → SEALED`, one-directional):

```text
   OPEN ──register()──► OPEN ──seal() / pipeline construction──► SEALED
                                                                    │
                                  register() ──► NormalizationRegistryError
```

**Pipeline** (observable, informational only):

```text
   (construct) ─► CREATED ─► READY ─► RUNNING ─► COMPLETED ─► RUNNING ...
                                         │
                                         └─► FAILED ─► RUNNING ...
```

`NormalizationPipeline.run(source)` **always** returns a fully-populated
`NormalizationResult` — even with zero responsibilities or zero observations. An
empty result is a valid execution, not a placeholder.

---

## Registry

Mirrors `ValidationRegistry`: explicit registration (no reflection/scanning),
duplicate prevention by `responsibility_id`, sealing (automatic on pipeline
construction), and deterministic ordering.

**Deviation:** ordering is **registration order**, because normalization has **no
layers** (validation sorts by a nine-layer `LAYER_ORDER`).

## Pipeline

Mirrors `ValidationPipeline`: orchestration only, deterministic ordering (trusts
the registry, never re-sorts), state transitions, exception translation (a
responsibility error marks `FAILED` and re-raises unchanged — an infrastructure
error is never a normalization fact).

**Deviation:** result assembly is **pure aggregation of facts** — there is no
verdict, summary, severity, or health to derive (Contract §10).

## Responsibilities

A `NormalizationResponsibility` owns exactly one responsibility from the
**Normalization Responsibility Catalog** (Contract §13):
`NORMALIZATION-0001 … 0005`. It is **pure, deterministic, stateless, idempotent,
non-mutating**, and returns **facts** (`NormalizationObservation`) — never
judgments. None are implemented in Phase 1.

---

## Normalization Responsibility Metadata

Every `NormalizationResponsibility` owns **exactly one** immutable
`NormalizationResponsibilityMetadata` value, exposed through its `metadata`
property. This is the normalization sibling of `ValidationRuleMetadata`, held to
the same maturity bar. It is the **single source of truth for a responsibility's
identity**; the legacy read-through properties (`responsibility_id`,
`responsibility_name`, `responsibility_version`, `order`, `enabled`) are thin
wrappers that simply delegate to it, so every existing caller keeps working
unchanged.

```python
from requirement_intelligence.normalization.framework import (
    NormalizationResponsibility,
    NormalizationResponsibilityMetadata,
)


class RecoverCanonicalStructure(NormalizationResponsibility):
    _METADATA = NormalizationResponsibilityMetadata(
        responsibility_id="NORMALIZATION-0001",
        responsibility_name="Recover canonical structure",
        order=1,  # descriptive catalog position — never used to sequence execution
    )

    @property
    def metadata(self) -> NormalizationResponsibilityMetadata:
        return self._METADATA

    def normalize(self, source):
        ...  # returns facts; Phase 1 implements none

r = RecoverCanonicalStructure()
r.responsibility_id  # "NORMALIZATION-0001"  (reads r.metadata.responsibility_id)
r.order              # 1                     (reads r.metadata.order)
```

### Why immutable metadata exists

Before this refinement a responsibility scattered its identity across independent
properties, so identity could not be treated as one versioned, immutable value.
Consolidating it into one **frozen** object means a responsibility's identity can
appear safely in `NormalizationResult` records, telemetry, and audit trails with
**no risk of post-hoc mutation**. Reassigning any attribute raises
`FrozenInstanceError`; the free-form `metadata` map is a read-only
`MappingProxyType`, so the value object is immutable in content, not just in its
attribute bindings.

### What belongs inside metadata — and what does not

| Belongs inside (runtime identity) | Does **not** belong |
| --------------------------------- | ------------------- |
| `responsibility_id` — the `NORMALIZATION-NNNN` identifier | normalization behaviour (that is `normalize`) |
| `responsibility_name` — human-readable label | observations / facts (owned by `NormalizationResult`) |
| `responsibility_version` — this responsibility's logic version | outcome / verdict / severity (never — Contract §10) |
| `order` — declared catalog position (**descriptive only**) | execution ordering decisions (registration order owns those) |
| `enabled` — participation flag | parsing, provider, or format knowledge |
| `tags`, `documentation_reference` *(reserved)* | the `ParsedResponse` or its shape |
| `responsibility_catalog_version`, `normalization_contract_version` *(reserved)* | which responsibilities *exist* (the **Catalog** governs that) |
| `future_schema_compatibility`, `metadata` map *(reserved)* | any mutable state |

### Fields

| Field | Status | Meaning |
| ----- | ------ | ------- |
| `responsibility_id` | active | Stable `NORMALIZATION-NNNN` id (Catalog §3.9 — immutable, never a validation rule id). |
| `responsibility_name` | active | Short human-readable label. |
| `responsibility_version` | active | Version of *this responsibility's* logic (default `1.0.0`). |
| `order` | active | Declared catalog position (`1…5`). **Descriptive identity only** — never read to sequence execution. |
| `enabled` | active | Whether it participates in execution (default `True`). |
| `tags` | reserved | Free-form classification labels (default `()`). |
| `documentation_reference` | reserved | Pointer to the responsibility's documentation. |
| `responsibility_catalog_version` | reserved | The governing catalog version this identity targets. |
| `future_schema_compatibility` | reserved | Declared ParsedResponse / result schema compatibility marker. |
| `normalization_contract_version` | reserved | The normalization *semantics* version targeted (the `validation_contract_version` analogue). |
| `metadata` | reserved | Read-only map of auxiliary descriptive labels. |

Reserved fields carry no behaviour today; they exist so the contract can grow
without a breaking change — exactly as in `ValidationRuleMetadata`.

### The `order` field and "no separate ordering dimension"

`order` is the normalization analogue of validation's `validation_layer`, but
with a deliberate difference: **the framework never consumes it to sequence
execution.** Validation's registry *sorts rules by layer*; normalization's
registry orders responsibilities by **registration order alone** (Catalog §8:
"registration order **is** execution order; there is no separate ordering
dimension"). `order` therefore records the responsibility's *frozen catalog
position* (`0001 → … → 0005`, Catalog §4) as runtime provenance only. A conforming
caller registers in catalog order, so `order` and registration order agree by
construction — without the registry or pipeline ever reading `order`.

### Relationship: Responsibility · Metadata · Registry · Pipeline · Catalog

| Component | Role toward metadata |
| --------- | -------------------- |
| **Responsibility** | *Owns* one immutable metadata value and exposes it via `metadata`; its read-through properties delegate to it. |
| **Metadata** | *Is* the responsibility's runtime identity — the single source of truth. |
| **Registry** | *Consumes* metadata during registration (duplicate detection keys on `metadata.responsibility_id`); orders by registration, never by `order`. |
| **Pipeline** | *Executes* enabled responsibilities in registration order; reads no identity directly and never sorts by `order`. |
| **Responsibility Catalog** | *Governs* the architecture — which responsibilities exist, what each owns, and their frozen order. |

### Runtime identity vs governing architecture

Metadata is **runtime identity**: the value a responsibility carries into results
and telemetry when it executes. The **Normalization Responsibility Catalog**
(`docs/architecture/normalization-responsibility-catalog.md`) remains the
**governing architecture**: it decides *which* `NORMALIZATION-NNNN` responsibilities
exist, *what* each owns, *what* it depends on, and *in what order* they participate
— permanently and only through an ADR (Catalog §11). Metadata **declares** a
responsibility's catalog-assigned identity at runtime; it never defines or
overrides it. **The catalog governs; the metadata reports.** This mirrors — but
does not duplicate — how `ValidationRuleMetadata` is runtime identity while the
Validation Rule Catalog governs the rules.

---

## Execution Context

`NormalizationExecutionContext` (in [`../response/`](../response/)) is the
immutable **execution identity** of a single normalization run. It is the
normalization sibling of `ValidationExecutionContext` — adapted, never copied, to
the Response Normalization Contract. `build_normalization_execution_context()` is
its deterministic builder: it creates the run identity, captures the start
timestamp, and stamps every version from the centralized framework constants —
containing **no** normalization logic (no parsing, repair, interpretation, or
judgment), exactly like `build_execution_context` in validation.

### Why it exists

Four questions about one run must never be conflated, because conflating them
makes it impossible to attribute a difference in behaviour to its true cause:

| Concern | Question answered | Owned by |
| ------- | ----------------- | -------- |
| **Execution Context** | *Which execution produced this normalization?* | `NormalizationExecutionContext` |
| **Framework Metadata** | *Which framework produced this normalization?* | `NormalizationFrameworkMetadata` |
| **Statistics** | *How did this normalization execute?* | `NormalizationStatistics` |
| **Result** | *What facts were produced?* | `NormalizationResult` |

### What it owns

Execution identity and version provenance **only**:

- `normalization_id` — identity of *this* run;
- `execution_id` — identity of the originating AI invocation (optional; the
  framework is decoupled from any concrete source shape);
- `correlation_id` — the cross-component trace key (optional);
- `started_at` — when orchestration began;
- the five framework versions in force — `framework_version`, `pipeline_version`,
  `registry_version`, `responsibility_catalog_version`, and
  `normalization_contract_version` (all **reused** from the framework metadata
  module — no new constant is introduced);
- `metadata` — free-form execution metadata, preserved verbatim.

### What it deliberately does NOT own

It carries **no verdict, no severity, no observation, no outcome, no
ParsedResponse, and no telemetry counts**. It never crosses the
Normalization–Validation boundary (Contract §10): it holds neither a normalization
*fact* nor a *judgment*.

- **vs. Framework Metadata** — the context identifies the *execution* (its id,
  correlation, timestamp) and stamps versions as that execution's provenance;
  framework metadata identifies the *framework* as a producer. Version scalars
  appear in both — deliberately — because "which versions this execution ran
  under" is part of the execution's identity, exactly as
  `ValidationExecutionContext` stamps `frameworkVersion` alongside
  `ValidationFrameworkMetadata`.
- **vs. Statistics** — statistics measure *how the run performed*
  (`responsibilities_executed`, `observations_recorded`, duration). The context
  measures nothing; it identifies. The shared id/correlation/timestamps are the
  same intentional overlap that exists between `ValidationExecutionContext` and
  `ValidationStatistics`.
- **vs. Result** — the result carries the *facts* (observations, the future
  `ParsedResponse`) and *references* the other models. The context is referenced
  *by* an execution, not a container *of* facts; it never holds a `ParsedResponse`
  or an observation.

### Deviations from `ValidationExecutionContext`

The context is a **sibling**, not a clone; each deviation tracks a deviation the
subsystem already made:

1. **No profile.** Normalization has no `ValidationProfile` analogue, so there is
   no `profile` field.
2. **No embedded configuration.** `ValidationExecutionContext` embeds the
   resolved `ValidationConfiguration`; the normalization context does **not**
   embed `NormalizationConfiguration` (the `NormalizationResult` already
   references it). It stamps only the resolved `normalization_contract_version`
   scalar — the one provenance value it needs — avoiding the strongest form of
   duplication.
3. **No validator / platform / rule-catalog versions.** Those are validation
   concepts. The context stamps the *normalization* framework versions instead
   (pipeline, registry, responsibility catalog, normalization contract).
4. **Optional `execution_id` / `correlation_id`.** Validation carries these as
   required (sourced from a typed `AnalysisResult`); normalization's source is
   `Any` and the framework is source-decoupled, so both are `str | None`,
   consistent with `NormalizationStatistics` and `NormalizationResult`.

---

## Relationship to the Response Normalization Contract

This framework realises the *infrastructure* the Contract governs:

| Contract concept | Realised by |
| ---------------- | ----------- |
| Response Normalization Layer (§4) | `NormalizationLayer` (framework seat) |
| Normalize once, before consumers (§3.1) | one pipeline run per source |
| Observe, never repair (§3.2) | `normalize` returns facts; source is read-only |
| Normalization Observations (§8) | `NormalizationObservation` |
| Facts, not judgments (§10) | no verdict/severity/summary anywhere |
| Normalization Responsibility Catalog (§13) | `responsibility_id = NORMALIZATION-NNNN` |
| Normalization Contract Version (§12) | `NORMALIZATION_CONTRACT_VERSION` |
| ParsedResponse Version (§12) | `PARSED_RESPONSE_VERSION` on the `ParsedResponse` model |

## Relationship to ParsedResponse

`ParsedResponse` is a **Core Canonical Model** and **Shared Platform Artifact**,
implemented in [`requirement_intelligence/models/parsed_response.py`](../../models/parsed_response.py)
by a **separate** task — **not** by this framework. The framework still builds
none: `NormalizationResult.parsed_response` remains the **architecture-approved
placeholder** (`Any | None`, always `None` in Phase 1). Producing a real
`ParsedResponse` is the future `ResponseNormalizer`'s job; when it does, only that
field's type annotation tightens (`Any | None` → `ParsedResponse | None`) — no
field is added, renamed, or moved, so no consumer breaks.

> **Observations ownership.** The **`NormalizationResult`** is the aggregate that
> owns the Normalization Observations together with the `ParsedResponse`, the
> statistics, the framework metadata, and the execution context. The
> `ParsedResponse` owns only the canonical representation and never carries
> observations, so the same facts live in exactly one canonical home. The
> architecture documents (`validation-canonical-models.md` §8,
> `response-normalization-contract.md` §8) state this ownership consistently.

## Relationship to the Response Validator

The `ParsedResponse` this subsystem will eventually produce is a **Shared Platform
Artifact**; the Response Validator is its **first consumer**, not its owner, and
never normalizes (Contract §7, §10). This framework and the validation framework
are **siblings** with identical engineering discipline and disjoint
responsibilities.

## Future: ResponseNormalizer

The `ResponseNormalizer` is a **future** concrete component (not built here). It
will *use* this framework — registering the real `NORMALIZATION-0001…0005`
responsibilities, owning the input/format-facing concerns, and producing a real
`ParsedResponse`. `NormalizationLayer` is the stable seat it will build upon,
exactly as `ResponseValidator` builds upon the validation pipeline.

---

## Deliberate deviations from the Validation Framework

Normalization is a **sibling** subsystem, not a clone. Every deviation is
intentional:

1. **No layers.** No `ValidationLayer`/`LAYER_ORDER` analogue; responsibilities
   execute in registration order. Metadata therefore has **no layer attribute**;
   in its place it carries a **descriptive `order`** (the frozen catalog position)
   that the framework never reads to sequence execution — registry ordering is
   insertion order (Catalog §8). See
   [Normalization Responsibility Metadata](#normalization-responsibility-metadata).
2. **No verdict / severity / summary / health.** Normalization produces *facts*,
   not *judgments* (Contract §10). `NormalizationResult` has no verdict and no
   summary; `NormalizationObservation` has no severity, recommendation, or
   blocking flag.
3. **`normalize` returns observations, not issues.** Structurally like
   `validate → list[ValidationIssue]`, but the return is *un-judged facts*.
4. **Statistics measure facts, not pass/fail.** `responsibilities_executed` and
   `observations_recorded` replace `rules_passed`/`rules_failed`.
5. **Configuration carries no layer/severity policy.** Only fact-collection
   toggles remain.
6. **`ParsedResponse` placeholder.** The result carries a typed placeholder
   instead of a real model, preserving API stability until the model lands.
7. **`NormalizationLayer` facade.** A subsystem seat distinct from the future
   `ResponseNormalizer` (the validation analogue, `ResponseValidator`, already
   exists; its normalization counterpart is deferred).
8. **Two normalization versions.** `NORMALIZATION_CONTRACT_VERSION` (semantics)
   and the `ParsedResponse Version` (shape) are independent and independent of the
   validation versions (Contract §12).
9. **Execution Context without a profile or embedded configuration.**
   `NormalizationExecutionContext` mirrors `ValidationExecutionContext` but drops
   the profile and the embedded configuration, and makes upstream/correlation
   identity optional (see [Execution Context](#execution-context)).
