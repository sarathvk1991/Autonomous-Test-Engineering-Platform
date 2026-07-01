# Response Normalizer

The **exclusive public entry point** into the Response Normalization subsystem —
the normalization sibling of the [`ResponseValidator`](../../validation/response/).
It orchestrates a single normalization run and returns the one canonical
`NormalizationResult`. It performs **no normalization itself**.

> **Scope.** This package is **orchestration only**. It parses nothing, inspects no
> JSON/XML, recovers no structure, records no observations, creates no
> `ParsedResponse`, mutates no `LLMResponse`, and implements no
> `NORMALIZATION-00NN` responsibility. Those are the work of the responsibilities
> it will orchestrate — future tasks.

---

## Architecture position

```text
   LLMResponse                         (provider-independent text + outcome)
        │
        ▼
   ResponseNormalizer                  ◄── this component (exclusive entry point)
        │  resolves context · configuration · profile; runs the pipeline ONCE
        ▼
   NormalizationResult                 (aggregate: ParsedResponse + observations + telemetry)
        │
        ▼
   Response Validator                  (first consumer; reads ParsedResponse + observations)
```

The Normalizer is the seat the architecture reserved for it: the framework
(`NormalizationLayer`, `NormalizationPipeline`, `NormalizationRegistry`) is the
*execution* machinery; the Normalizer is the *orchestration boundary* that drives
it on a caller's behalf, exactly as `ResponseValidator` drives the validation
pipeline.

## Components

| Module | Responsibility |
| ------ | -------------- |
| `response_normalizer.py` | `ResponseNormalizer` — the single public API (`normalize`). |
| `response_normalizer_exceptions.py` | The `NormalizationError` orchestration hierarchy. |
| `normalization_profile.py` | `NormalizationProfile` + `resolve_profile` — the four canonical profiles (metadata only). |
| `normalization_execution_context.py` | `NormalizationExecutionContext` + builder — the immutable execution identity (pre-existing; reused, not duplicated). |

## Public API

```python
from requirement_intelligence.normalization.response import ResponseNormalizer

normalizer = ResponseNormalizer(registry, pipeline, platform_defaults)
result = normalizer.normalize(llm_response)   # -> NormalizationResult
```

`normalize(llm_response)` is the **only** operational method. A read-only
`last_execution_context` is exposed for observability; reading it never performs
or alters normalization. There is no other mutable state.

## Dependency injection

The registry and pipeline are **injected**, never constructed internally
(mirroring `ResponseValidator`):

```python
registry = NormalizationRegistry()
# ... register NORMALIZATION-00NN responsibilities here (future) ...
pipeline = NormalizationPipeline(registry)          # seals the registry
normalizer = ResponseNormalizer(registry, pipeline, NormalizationConfiguration())
```

Construction validates dependency types and raises `PipelineConstructionError`
(registry/pipeline) or `ConfigurationResolutionError` (platform defaults) — it
never normalizes.

## Configuration hierarchy

Resolution follows the same precedence as the Response Validator, lowest to
highest:

```text
   Platform Defaults ─► Profile ─► Execution Configuration ─► Runtime Overrides
```

The highest-precedence layer supplied wins. **Only platform defaults flow through
the public `normalize` path today**; the higher layers exist in
`_resolve_configuration` so the hierarchy is complete and ready to extend without
changing the public contract.

## Execution flow

```text
   normalize(llm_response)
        │ 1. resolve configuration (hierarchy above)
        │ 2. resolve profile (default: Standard) — validated
        │ 3. build NormalizationExecutionContext (version provenance)
        │ 4. run the pipeline EXACTLY ONCE
        │ 5. return the NormalizationResult unchanged
        ▼
   NormalizationResult
```

No retries, loops, recursion, or parallelism. The result is returned **unchanged**
— the Normalizer never inspects or interprets it.

## Profiles

Four immutable, metadata-only canonical profiles: `MINIMAL`, `STANDARD` (default),
`STRICT`, `ENTERPRISE`. They carry **no responsibility lists yet** — a profile
*names* a breadth of normalization; responsibility selection arrives with the
first concrete `NORMALIZATION-00NN` responsibilities. This is exactly the
Validation Profile philosophy.

## Execution context

The Normalizer **reuses** the existing `build_normalization_execution_context`
builder — it does not duplicate execution-identity logic. Because an `LLMResponse`
carries no upstream execution or correlation identity (the subsystem is
source-decoupled), those context fields resolve to `None` today; every version
field is stamped from the centralized framework constants.

## Exception model

The orchestration hierarchy mirrors the Response Validator's one-for-one:

```text
NormalizationError
├── ConfigurationResolutionError
├── ProfileResolutionError
├── PipelineConstructionError
└── NormalizationExecutionError
```

Framework exceptions (`NormalizationFrameworkError` and subclasses) are
**translated** into `NormalizationExecutionError` at the boundary — framework
internals never leak to callers. A `MALFORMED` outcome or a recorded observation
is a **normal result**, never an exception.

## Design decisions

1. **Orchestration only.** The Normalizer coordinates; it never normalizes,
   parses, judges, or creates a `ParsedResponse`.
2. **Mirror architecture, not implementation.** It reuses the framework and the
   execution-context builder; no framework logic is copied.
3. **Dependency injection.** Registry and pipeline are injected so the
   responsibility set is fixed and testable.
4. **Single invocation.** The pipeline runs exactly once per `normalize`.
5. **Translate, never leak.** Framework errors become orchestration errors.
6. **One read-only observability surface.** `last_execution_context`, nothing else.

## Comparison with `ResponseValidator`

| Aspect | `ResponseValidator` | `ResponseNormalizer` |
| ------ | ------------------- | -------------------- |
| Public API | `validate(analysis_result)` | `normalize(llm_response)` |
| Input | `AnalysisResult` (carries execution/analysis ids) | `LLMResponse` (no ids — source-decoupled) |
| Output | `ValidationResult` (verdict, issues) | `NormalizationResult` (facts, no verdict) |
| Execution context | `ValidationExecutionContext` (has `profile`) | `NormalizationExecutionContext` (**no** `profile` field) |
| Profiles | 5 (incl. `COMPLIANCE`) | 4 (no `COMPLIANCE`) |
| Exceptions | `ResponseValidatorError` + 4 | `NormalizationError` + 4 |
| DI | registry + pipeline + defaults | registry + pipeline + defaults |
| Config hierarchy | Platform → Profile → Execution → Runtime | identical |
| Correlation | from `AnalysisResult` | `None` today (LLMResponse carries none) |

The Normalizer is a **sibling, not a clone**: the deviations (no context profile
field, no `COMPLIANCE` profile, facts-not-judgments, source-decoupled identity)
all track the frozen normalization architecture.

## Future responsibilities & wiring

- **`NORMALIZATION-0001…0005`** — the concrete responsibilities register into the
  injected `NormalizationRegistry`; the Normalizer needs **no change** to
  orchestrate them (it already runs whatever the registry contains).
- **Profile-driven selection** — when responsibilities exist, profiles gain their
  selection behaviour behind the same `NormalizationProfile` shape.
- **CLI / platform wiring** — the Normalizer is deliberately **not** wired into the
  CLI here; that is a later delivery step (see the Platform Capability Matrix).
