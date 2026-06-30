# Transport Validation Rules

| Attribute | Value |
| --------- | ----- |
| Package | `requirement_intelligence/validation/rules/transport/` |
| Layer | Transport — the most foundational validation concern |
| Status | Two production rules implemented (`TRANSPORT-0001`, `TRANSPORT-0002`) |
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

---

## Current Rules

| Rule ID | Name | Concern |
| ------- | ---- | ------- |
| `TRANSPORT-0001` | Response Exists | An LLM response object is present on the `AnalysisResult`. |
| `TRANSPORT-0002` | Empty Response | An existing LLM response carries usable generated content. |

### Why `TRANSPORT-0001` and `TRANSPORT-0002` are separate rules

They validate **two distinct concerns** and must remain separate (Validation Rule
Catalog §3 — one rule, one responsibility):

| Rule | Single concern | Reads | Fails when |
| ---- | -------------- | ----- | ---------- |
| `TRANSPORT-0001` | The **response object exists** | `llm_response` (presence) | `llm_response is None` |
| `TRANSPORT-0002` | The **generated content exists** | `llm_response.generated_text` (emptiness) | content is empty / whitespace-only |

A single combined "response is usable" rule would hide *which* aspect failed (a
missing response object vs. a present-but-empty one), couple two independent
reasons to change, and break the one-concern-per-rule contract. Keeping them
separate means each can fail, evolve, and be reasoned about independently — and
`TRANSPORT-0002` deliberately **defers** (returns no findings) when the response
object is absent, so the two rules never report the same condition twice.

---

## Future Rules

Reserved in the Validation Rule Catalog (§9.1); **not implemented yet**. Each
will be a separate single-concern rule added to this package and registered via
`register_transport_rules`, with no framework change:

| Rule ID | Name | Concern |
| ------- | ---- | ------- |
| `TRANSPORT-0003` | Timeout | The generation did not time out. |
| `TRANSPORT-0004` | Provider Failure | The generation did not fail at the delivery boundary. |

---

## Registration

`register_transport_rules(registry)` registers every implemented Transport rule
with a `ValidationRegistry` using the framework's existing `register` mechanism —
no behavioural change to the registry. It must be called **before** the pipeline
is constructed (the pipeline seals its registry on construction).

```text
   ValidationRegistry ──register_transport_rules──► [ TRANSPORT-0001, TRANSPORT-0002 ]
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
