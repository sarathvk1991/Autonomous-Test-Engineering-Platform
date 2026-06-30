# Transport Validation Rules

| Attribute | Value |
| --------- | ----- |
| Package | `requirement_intelligence/validation/rules/transport/` |
| Layer | Transport — the most foundational validation concern |
| Status | **Complete** — all four production rules implemented (`TRANSPORT-0001`–`TRANSPORT-0004`); layer frozen |
| Governing specifications | `docs/architecture/validation-rule-catalog.md` · `docs/development/validation-rule-development-guide.md` |

---

## Purpose

The **Transport** layer answers the single most foundational question of the
validation pipeline: *was a usable response received at all?* Transport rules
never inspect content, structure, schema, evidence, or meaning — only whether
there is something to validate.

Each rule validates **exactly one concern** and is **pure, deterministic,
stateless, idempotent, non-mutating, and side-effect free** (Validation Rule
Catalog §16).

---

## Transport Layer Architecture

Normalization happens once, at the provider adapter. Every Transport rule then
validates a single, already-normalized execution guarantee off the
provider-independent `LLMResponse` — none of them ever touches a provider.

```text
   ┌──────────────┐
   │   Provider    │  Gemini · Azure OpenAI · Anthropic · Bedrock · Ollama · …
   └──────┬───────┘     (provider-specific SDK response)
          │
          ▼
   ┌──────────────────┐
   │  Provider Adapter │  NORMALIZES: outcome → ExecutionStatus, usage → LLMUsage,
   │  (only normalizer)│             latency → latency_ms, text → generated_text
   └──────┬───────────┘
          │ constructs
          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                      LLMResponse                              │
   │  provider-independent: generated_text · execution_status ·   │
   │                        usage · latency_ms                    │
   │  provider-specific (opaque): finish_reason · raw_response    │
   └──────┬───────────────────────────────────────────────────────┘
          │ carried on the AnalysisResult, validated in layer order
          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  TRANSPORT-0001  ResponseExists   guarantee: a response object │
   │                  reads llm_response (presence)                │
   ├──────────────────────────────────────────────────────────────┤
   │  TRANSPORT-0002  EmptyResponse    guarantee: usable content    │
   │                  reads generated_text (emptiness)             │
   ├──────────────────────────────────────────────────────────────┤
   │  TRANSPORT-0003  Timeout          guarantee: not timed out     │
   │                  reads execution_status == TIMEOUT            │
   ├──────────────────────────────────────────────────────────────┤
   │  TRANSPORT-0004  ProviderFailure  guarantee: no delivery       │
   │                  reads execution_status == FAILED   failure    │
   └──────┬───────────────────────────────────────────────────────┘
          │ findings assembled (highest severity wins)
          ▼
   ┌──────────────┐
   │ ValidationResult │
   └──────────────┘
```

### One rule, one execution guarantee

Each Transport rule validates **exactly one execution guarantee**, reading
exactly one provider-independent signal. The guarantees are disjoint, so the
rules never overlap and a finding always names the precise broken guarantee:

| Rule | Execution guarantee | Reads (provider-independent) | Fails when |
| ---- | ------------------- | ---------------------------- | ---------- |
| `TRANSPORT-0001` | A response object exists | `llm_response` (presence) | `llm_response is None` |
| `TRANSPORT-0002` | Usable content exists | `generated_text` (emptiness) | empty / whitespace-only |
| `TRANSPORT-0003` | The execution did not time out | `execution_status` | `== TIMEOUT` |
| `TRANSPORT-0004` | The execution did not fail at the delivery boundary | `execution_status` | `== FAILED` |

`TIMEOUT` and `FAILED` are **sibling, non-overlapping** execution outcomes (the
adapter normalizes a timeout to `TIMEOUT` and any other delivery-boundary failure
to `FAILED`). This is why `TRANSPORT-0003` and `TRANSPORT-0004` each own exactly
one outcome and never collide. Rules `0002`–`0004` deliberately **defer** (no
findings) when the response object is absent, leaving that to `TRANSPORT-0001` —
so no condition is ever reported twice.

---

## Rule Catalog

### `TRANSPORT-0001` — Response Exists

| Field | Value |
| ----- | ----- |
| Rule ID | `TRANSPORT-0001` |
| Class | `ResponseExistsRule` |
| Name | Response Exists |
| Layer | `TRANSPORT` |
| Rule Version | `1.0.0` |
| Classification | Core |
| Severity | `CRITICAL` |
| Blocking | `True` |
| Purpose | Verify that an `AnalysisResult` contains an LLM response object. |

**Behaviour**

| Condition | Outcome |
| --------- | ------- |
| `llm_response` is present | **Pass** — returns an empty collection (no findings). |
| `llm_response` is `None` | **Fail** — returns exactly one `CRITICAL`, blocking `ValidationIssue`. |

The rule examines **only** response existence. It performs no content
inspection, no JSON parsing, no schema validation, no reasoning, no
provider-specific logic, no retries, no repair, and no mutation.

**Failure issue (every canonical field populated)**

| Field | Value |
| ----- | ----- |
| `severity` | `CRITICAL` |
| `blocking` | `True` |
| `category` / `validation_layer` | `transport` |
| `location` | `llm_response` |
| `message` | "The analysis result does not contain an LLM response." |
| `recommendation` | "Regenerate the AI response before continuing." |
| `evidence` | `None` |
| `correlation_id` | derived from the response's execution identity |

### `TRANSPORT-0002` — Empty Response

| Field | Value |
| ----- | ----- |
| Rule ID | `TRANSPORT-0002` |
| Class | `EmptyResponseRule` |
| Name | Empty Response |
| Layer | `TRANSPORT` |
| Rule Version | `1.0.0` |
| Classification | Core |
| Severity | `CRITICAL` |
| Blocking | `True` |
| Purpose | Verify that an existing LLM response contains usable generated content. |

**Behaviour**

| Condition | Outcome |
| --------- | ------- |
| `generated_text` exists and `generated_text.strip()` is non-empty | **Pass** — returns an empty collection. |
| `generated_text == ""` or contains only whitespace | **Fail** — returns exactly one `CRITICAL`, blocking `ValidationIssue`. |
| `llm_response` is `None` | **Defers** — existence is `TRANSPORT-0001`'s concern; returns no findings. |

The rule examines **only** the emptiness of generated content. It never inspects
requirements, recommendations, risks, JSON, schema, structure, reasoning, or
provider metadata.

**Failure issue (every canonical field populated)**

| Field | Value |
| ----- | ----- |
| `severity` | `CRITICAL` |
| `blocking` | `True` |
| `category` / `validation_layer` | `transport` |
| `location` | `generated_text` |
| `message` | "The LLM response contains no generated content." |
| `recommendation` | "Regenerate the AI response before continuing." |
| `evidence` | `None` |
| `issue_id` | `TRANSPORT-0002:generated_text` (deterministic) |
| `correlation_id` | derived from the response's execution identity |

> **Verdict note.** Because the issue is `CRITICAL`, the frozen verdict model
> resolves the overall verdict to `BLOCKED` (a `CRITICAL` finding makes the output
> unsafe to process). The response is correctly *rejected* — never `PASSED`.

### `TRANSPORT-0003` — Timeout

| Field | Value |
| ----- | ----- |
| Rule ID | `TRANSPORT-0003` |
| Class | `TimeoutRule` |
| Name | Timeout |
| Layer | `TRANSPORT` |
| Rule Version | `1.0.0` |
| Classification | Core |
| Severity | `CRITICAL` |
| Blocking | `True` |
| Purpose | Verify that the completed AI execution did not terminate because of a timeout. |

**Behaviour**

| Condition | Outcome |
| --------- | ------- |
| `execution_status` is `COMPLETED` (or any non-timeout outcome) | **Pass** — returns an empty collection. |
| `execution_status` is `TIMEOUT` | **Fail** — returns exactly one `CRITICAL`, blocking `ValidationIssue`. |
| `llm_response` is `None` | **Defers** — existence is `TRANSPORT-0001`'s concern; returns no findings. |

The rule validates **execution outcome only**. It never inspects generated
content, requirements, recommendations, risks, JSON, schema, reasoning, provider
metadata, or business logic.

**Failure issue (every canonical field populated)**

| Field | Value |
| ----- | ----- |
| `severity` | `CRITICAL` |
| `blocking` | `True` |
| `category` / `validation_layer` | `transport` |
| `location` | `execution` |
| `message` | "The AI execution terminated because of a timeout." |
| `recommendation` | "Retry the AI analysis or investigate execution timeout settings." |
| `evidence` | `None` |
| `issue_id` | `TRANSPORT-0003:timeout` (deterministic) |
| `correlation_id` | derived from the response's execution identity |

> **Verdict note.** Like `TRANSPORT-0002`, a `CRITICAL` timeout finding resolves to
> `BLOCKED` under the frozen verdict model — the response is *rejected*.

#### Why timeout validation is independent of provider implementations

The rule reads **only** the normalized, provider-independent
`ExecutionStatus` on the `LLMResponse` — never a provider-specific timeout code.
Each provider adapter (Gemini, Azure OpenAI, Anthropic, Bedrock, Ollama, …)
**normalizes** its own termination signal into `ExecutionStatus` *before*
constructing the `LLMResponse`. The validator never normalizes and never
understands provider codes; normalization is exclusively a provider-adapter
responsibility (`shared/enums/base.py :: ExecutionStatus`).

```text
   Provider-specific termination signal
            │ (provider adapter normalizes — the ONLY place this happens)
            ▼
   ExecutionStatus.{COMPLETED | TIMEOUT}   ← normalized, provider-independent
            │ read read-only
            ▼
   TimeoutRule (provider-agnostic)
```

This is why a new provider needs **no** change to the rule: as long as it
normalizes its timeout into `ExecutionStatus.TIMEOUT`, `TRANSPORT-0003` validates
it correctly and unchanged.

### `TRANSPORT-0004` — Provider Failure

| Field | Value |
| ----- | ----- |
| Rule ID | `TRANSPORT-0004` |
| Class | `ProviderFailureRule` |
| Name | Provider Failure |
| Layer | `TRANSPORT` |
| Rule Version | `1.0.0` |
| Classification | Core |
| Severity | `CRITICAL` |
| Blocking | `True` |
| Purpose | Verify that the AI execution did not fail at the provider/delivery boundary. |

**Behaviour**

| Condition | Outcome |
| --------- | ------- |
| `execution_status` is `COMPLETED` (or any non-failure outcome, incl. `TIMEOUT`) | **Pass** — returns an empty collection. |
| `execution_status` is `FAILED` | **Fail** — returns exactly one `CRITICAL`, blocking `ValidationIssue`. |
| `llm_response` is `None` | **Defers** — existence is `TRANSPORT-0001`'s concern; returns no findings. |

The rule validates **execution outcome only**. It reads **only**
`execution_status` — never `finish_reason`, `raw_response`, the provider SDK
payload, `generated_text`, requirements, recommendations, or risks.

**Failure issue (every canonical field populated)**

| Field | Value |
| ----- | ----- |
| `severity` | `CRITICAL` |
| `blocking` | `True` |
| `category` / `validation_layer` | `transport` |
| `location` | `execution` |
| `message` | "The AI execution failed at the provider delivery boundary." |
| `recommendation` | "Retry the AI request or investigate the provider failure before continuing." |
| `evidence` | `None` |
| `issue_id` | `TRANSPORT-0004:provider_failure` (deterministic) |
| `correlation_id` | derived from the response's execution identity |

> **Verdict note.** Like `TRANSPORT-0002`/`TRANSPORT-0003`, a `CRITICAL` finding
> resolves to `BLOCKED` under the frozen verdict model — the response is *rejected*.

#### Relationship to `TRANSPORT-0003`: `TIMEOUT` vs `FAILED`

`TRANSPORT-0003` and `TRANSPORT-0004` are **sibling** rules over the same
normalized field (`execution_status`), but they validate **disjoint** outcomes:

| Outcome | Meaning | Owned by |
| ------- | ------- | -------- |
| `ExecutionStatus.TIMEOUT` | The execution was cut short by a deadline/time-limit. | `TRANSPORT-0003` |
| `ExecutionStatus.FAILED` | The execution failed at the delivery boundary (a provider/transport error or refusal that is **not** a timeout). | `TRANSPORT-0004` |

A timeout is normalized to `TIMEOUT` (never `FAILED`); any other delivery-boundary
failure is normalized to `FAILED` (never `TIMEOUT`). Because the outcomes are
mutually exclusive, each rule fails on exactly one value and they **never collide**
— a `TIMEOUT` execution passes `TRANSPORT-0004`, and a `FAILED` execution passes
`TRANSPORT-0003`. This is why they are two rules, not one: each owns one outcome,
fails on one value, and can evolve independently.

---

## Current Rules

| Rule ID | Name | Concern |
| ------- | ---- | ------- |
| `TRANSPORT-0001` | Response Exists | An LLM response object is present on the `AnalysisResult`. |
| `TRANSPORT-0002` | Empty Response | An existing LLM response carries usable generated content. |
| `TRANSPORT-0003` | Timeout | The completed AI execution did not terminate because of a timeout. |
| `TRANSPORT-0004` | Provider Failure | The AI execution did not fail at the provider/delivery boundary. |

### Why the Transport rules are separate

Each validates **one distinct concern** and must remain separate (Validation Rule
Catalog §3 — one rule, one responsibility):

| Rule | Single concern | Reads | Fails when |
| ---- | -------------- | ----- | ---------- |
| `TRANSPORT-0001` | The **response object exists** | `llm_response` (presence) | `llm_response is None` |
| `TRANSPORT-0002` | The **generated content exists** | `llm_response.generated_text` (emptiness) | content is empty / whitespace-only |
| `TRANSPORT-0003` | The **execution did not time out** | `llm_response.execution_status` (normalized outcome) | `execution_status == TIMEOUT` |
| `TRANSPORT-0004` | The **execution did not fail at the provider boundary** | `llm_response.execution_status` (normalized outcome) | `execution_status == FAILED` |

A single combined "response is usable" rule would hide *which* aspect failed (a
missing object vs. an empty one vs. a timed-out vs. a failed execution), couple
independent reasons to change, and break the one-concern-per-rule contract.
Keeping them separate means each can fail, evolve, and be reasoned about
independently — and `TRANSPORT-0002`–`TRANSPORT-0004` deliberately **defer**
(return no findings) when the response object is absent, so the rules never report
the same condition twice.

---

## Transport Layer Complete

The Transport layer is **complete and frozen**: exactly four production rules,
each guaranteeing one foundational property of the execution before any higher
layer runs.

| # | Guarantee | Rule |
| - | --------- | ---- |
| 1 | **The response exists.** | `TRANSPORT-0001` Response Exists |
| 2 | **The response contains usable content.** | `TRANSPORT-0002` Empty Response |
| 3 | **The execution did not time out.** | `TRANSPORT-0003` Timeout |
| 4 | **The execution did not fail at the provider boundary.** | `TRANSPORT-0004` Provider Failure |

Because every Transport rule is `CRITICAL` and blocking, a violation of any of the
four guarantees rejects the response (`BLOCKED`) before content is interpreted.
Therefore **every higher validation layer — Syntax, Schema, Structural, Content,
Evidence, Traceability, Reasoning, Business Rule — may safely assume** that a
response which reaches it:

- exists (is a real `LLMResponse`),
- carries non-empty generated content,
- came from an execution that completed (no timeout), and
- came from an execution that did not fail at the provider boundary.

Higher layers never re-check these foundational facts; they build on them. No
further Transport rules are planned — the layer's reserved range is fully
allocated for its four execution guarantees.

---

## Registration

`register_transport_rules(registry)` registers every implemented Transport rule
with a `ValidationRegistry` using the framework's existing `register` mechanism —
no behavioural change to the registry. It must be called **before** the pipeline
is constructed (the pipeline seals its registry on construction).

```text
   ValidationRegistry ──register_transport_rules──► [ TRANSPORT-0001, TRANSPORT-0002, TRANSPORT-0003, TRANSPORT-0004 ]
            │ (construct & seal)
            ▼
   ValidationPipeline ──executes rules in layer order──► ValidationResult
```

---

## Relationship to the Response Validator

The `ResponseValidator` is the exclusive orchestration entry point. It is
assembled from a registry (populated by `register_transport_rules`), a pipeline,
and the platform-default configuration. Calling `validator.validate(analysis_result)`
runs the registered Transport rules naturally and returns the single
`ValidationResult`:

```text
   AnalysisResult ──► ResponseValidator ──► ValidationPipeline ──► TRANSPORT-0001
                                                                       │
                                                                       ▼
                                                                 ValidationResult
```

The Validator never executes rule logic itself — it coordinates; the rule judges
its single concern.

---

## Relationship to the Validation Framework

These rules are plain `ValidationRule` implementations discovered by
**registration**, never by import side effects. The framework contracts are
unchanged:

- `ValidationRule` — the abstract contract each rule implements (`metadata` +
  `validate`).
- `ValidationRegistry` — catalogues the rule instances.
- `ValidationPipeline` — runs them in layer order and assembles the
  `ValidationResult`.
- `ValidationIssue` / `ValidationResult` — the canonical models the rule produces
  and the pipeline returns.

Adding a Transport rule requires only a new single-concern file here plus a line
in `register_transport_rules` — no framework code changes.
