# Response Validator

| Attribute | Value |
| --------- | ----- |
| Package | `requirement_intelligence/validation/response/` |
| Status | Implemented — orchestration layer; no validation rules yet |
| Governing specifications | `docs/architecture/response-validator.md` · `docs/architecture/validation-rule-catalog.md` · `docs/architecture/validation-canonical-models.md` · `docs/architecture/ai-response-validation.md` |
| Public entry point | `ResponseValidator.validate(analysis_result) -> ValidationResult` |

---

## Purpose

The `response` package is the **single, exclusive orchestration entry point**
into the Response Validation subsystem. The `ResponseValidator` coordinates the
execution context, configuration, profile, registry, pipeline, and result into
one repeatable act of validation.

It **performs no validation itself.** Whether a response is trustworthy is
decided by the rules and assembled by the framework; the Validator only decides
*how the run is conducted* and returns the single canonical `ValidationResult`
unchanged.

---

## Responsibilities

| The Validator does | The Validator does **not** |
| ------------------ | -------------------------- |
| Validate the configuration | Execute rule logic |
| Resolve the Validation Profile | Interpret the `ValidationResult` |
| Create the `ValidationExecutionContext` | Repair or retry |
| Coordinate the pipeline | Log, persist, or report |
| Execute the pipeline **once** | Perform CP1 or any downstream gating |
| Return the `ValidationResult` unchanged | Mutate the input or the output |

---

## Execution Flow

`validate(analysis_result)` performs a fixed, ordered sequence
(`response-validator.md` §5):

```text
   AnalysisResult
        │
        ▼
   ResponseValidator
        │  1. resolve & validate configuration  (hierarchy, §8)
        │  2. resolve profile                    (default: Standard)
        │  3. build ValidationExecutionContext   (full version provenance)
        │  4. run pipeline EXACTLY once
        ▼
   ValidationPipeline ──► (registry → rules) ──► ValidationResult
        │
        ▼
   ValidationResult  (returned unchanged)
```

The pipeline is invoked **exactly once** — no retries, loops, recursion, or
parallel execution. Any framework exception raised during the run is **translated**
into a `ValidationExecutionError`, so implementation exceptions never leak across
the orchestration boundary.

---

## Execution Context

`ValidationExecutionContext` is **immutable orchestration metadata** for one run
— never validation data. It carries identity, the selected profile, the resolved
configuration, timestamps, correlation, and full version provenance. Findings and
verdicts live only in the `ValidationResult`.

The context is built by `build_execution_context(...)`, which populates **every**
provenance field from centralized version constants and from the analysed
response — no value is hardcoded:

| Provenance field | Source |
| ---------------- | ------ |
| `platform_version` | `PLATFORM_VERSION` |
| `framework_version` | `FRAMEWORK_VERSION` (framework metadata) |
| `validator_version` | `VALIDATOR_VERSION` |
| `rule_catalog_version` | `RULE_CATALOG_VERSION` |
| `validation_contract_version` | the resolved configuration |
| `prompt_version` · `reasoning_contract_version` | the `AnalysisResult` |
| `execution_id` · `analysis_id` · `correlation_id` | the `AnalysisResult` |
| `validation_id` | freshly generated per run |

The most recent context is available read-only via
`ResponseValidator.last_execution_context` (observability only).

---

## Configuration Hierarchy

The effective configuration is resolved along a fixed precedence
(`response-validator.md` §8). **Highest precedence wins.**

```text
   Platform Defaults  →  Profile  →  Execution Configuration  →  Runtime Overrides
   (lowest)                                                       (highest)
```

Today only **Platform Defaults** are wired into the public path; the higher
layers are accepted by `_resolve_configuration(...)` so the hierarchy is complete
and ready to extend without changing the public contract. Resolution is pure — no
business logic, no verdict influence.

---

## Profile Resolution

A `ValidationProfile` is a named, immutable selection of rules
(`validation-rule-catalog.md` §13). Five canonical profiles exist as metadata only
(no rule lists yet):

| Profile | Intent |
| ------- | ------ |
| `Minimal` | Lightest viable gate; Core rules only. |
| `Standard` | **Default** balanced gate; Core + common Extended. |
| `Strict` | Maximum depth; Core + all Extended. |
| `Compliance` | Regulatory coverage; Core + Extended + Organization (compliance). |
| `Enterprise` | Organization-wide policy; Core + Extended + Organization. |

`resolve_profile(name=None)` returns the canonical profile; with no name it
returns **Standard**. An unknown name raises `ProfileResolutionError`. Profiles
select rules; **rules never know profiles**.

---

## Relationship with the Validation Framework

The Validator is the only component that drives the framework on a caller's
behalf. It depends on the framework **contracts**, never their internals.

```text
   ResponseValidator
        │ holds      │ executes once
        ▼            ▼
   ValidationRegistry   ValidationPipeline.run(analysis_result, configuration)
   (held for future            │
    rule discovery)            ▼
                          ValidationResult  (the single output)
```

- **Registry** — injected and held for rule discovery as the catalog grows; the
  Validator adds no rules itself today.
- **Pipeline** — injected, pre-constructed (it seals its registry on construction)
  and invoked exactly once.
- **No behavioural changes** are made to the registry or the pipeline.

### Exception translation

| Boundary failure | Raised by the Validator |
| ---------------- | ----------------------- |
| Bad registry / pipeline dependency | `PipelineConstructionError` |
| No valid configuration | `ConfigurationResolutionError` |
| Profile cannot be resolved | `ProfileResolutionError` |
| Pipeline run fails (framework or unexpected error) | `ValidationExecutionError` (original preserved as the cause) |

All inherit `ResponseValidatorError`. A `FAILED`/`BLOCKED` **verdict is not an
exception** — it is a normal result on the `ValidationResult`.

---

## Future Extensions

Reserved behind the single entry point (`response-validator.md` §15) — not
implemented today:

- **Rule discovery & registration** — profiles selecting catalogued rules into
  the registry once concrete rules exist.
- **Execution configuration & runtime overrides** — higher precedence layers in
  the configuration hierarchy.
- **Custom / organization profiles**, **adaptive profiles**, **profile versions**.
- **Repair**, **retry**, **AI-assisted validation**, **rule parallelization**.

Every future capability is additive **behind** `validate(...)`; the orchestration
contract and the `ValidationResult` output stay stable.

---

## Next step

The orchestration layer is complete and ready for the **first Transport
validation rule** (`TRANSPORT-0001 ResponseExistsRule`), implemented per
`docs/development/validation-rule-development-guide.md`. No validation logic,
rule implementations, or transport rules exist yet.
