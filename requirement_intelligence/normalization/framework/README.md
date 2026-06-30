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
| `normalization_metadata.py` | `NormalizationResponsibilityMetadata` — immutable identity (`NORMALIZATION-NNNN`). |
| `normalization_registry.py` | `NormalizationRegistry` + `RegistryState` — registration, ordering, sealing, duplicate prevention. |
| `normalization_pipeline.py` | `NormalizationPipeline` + `PipelineState` — orchestration, lifecycle, statistics, result assembly. |
| `normalization_layer.py` | `NormalizationLayer` — the framework seat of the subsystem (composes registry + pipeline). **Not** the `ResponseNormalizer`. |
| `normalization_exceptions.py` | The `NormalizationFrameworkError` hierarchy. |
| `../models/` | `NormalizationObservation`, `NormalizationConfiguration`, `NormalizationStatistics`, `NormalizationFrameworkMetadata`, `NormalizationResult`. |

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
| ParsedResponse Version (§12) | owned by the future `ParsedResponse` model |

## Relationship to ParsedResponse

`ParsedResponse` is a **Core Canonical Model**, implemented by a **separate**
task. The framework does **not** build it. `NormalizationResult.parsed_response`
is the **architecture-approved placeholder** (`Any | None`, always `None` today):
when `ParsedResponse` lands, only the type annotation changes — no field is added,
renamed, or moved, so no consumer breaks.

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
   execute in registration order. (Hence no layer attribute on metadata, and
   registry ordering is insertion order.)
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
