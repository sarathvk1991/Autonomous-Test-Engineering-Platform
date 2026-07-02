# ADR 0003 — The Validation Input and the Normalization → Validation Handoff

- **Status:** Proposed (awaiting ratification)
- **Date:** 2026-07-02

## Context

The Response Normalization subsystem is complete and frozen: the
`ResponseNormalizer` turns an `LLMResponse` into a `NormalizationResult` that
carries the canonical `ParsedResponse` and owns the Normalization Observations.
The Response Validation subsystem is complete and frozen down to its rule-execution
contract: the `ResponseValidator` orchestrates a `ValidationPipeline` that runs
`ValidationRule` instances and assembles a single `ValidationResult`. The Transport
layer (four rules) is implemented and frozen.

Every frozen validation artifact states that the **Syntax** layer must read the
**Normalization Outcome** from the `ParsedResponse` (`SYNTAX-0001`) and the
**Normalization Observations** from the `NormalizationResult` (`SYNTAX-0002`
duplicate identifiers, `SYNTAX-0003` encoding), and that every layer from **Schema**
onward must read the **normalized structure** from the same `ParsedResponse`
(Validation Rule Catalog §8.2, §8.3–§8.9; AI Response Validation §4.4; Syntax Layer
Design Review §5, §9; Validation Canonical Models §8).

**The two subsystems are not connected.** The design review that preceded this ADR
established, from the repository state:

- `ResponseValidator.validate(analysis_result: AnalysisResult)` and
  `ValidationPipeline.run(analysis_result: AnalysisResult)` accept **only** the
  `AnalysisResult`.
- `AnalysisResult` carries `analysis_id`, `execution_id`, provenance, and the raw
  `LLMResponse`. It has **no** `ParsedResponse`, **no** `NormalizationResult`, and
  no field for either.
- The validation package imports **neither** `ParsedResponse` **nor**
  `NormalizationResult` anywhere; the `ResponseNormalizer` is **not wired** into the
  analysis layer, the CLI, or validation.
- `ParsedResponse` (`requirement_intelligence/models/parsed_response.py`)
  deliberately does **not** carry observations; the Normalization Observations are
  owned **solely** by `NormalizationResult` (a governed deviation from Validation
  Canonical Models §8.1 that itself requires an ADR to change).

Consequently **`SYNTAX-0001` cannot be implemented today**: there is no path by
which a rule can reach the `ParsedResponse` or the observations. This is not a
coding gap that can be closed silently in a rule; it is a missing architectural
decision about the **canonical input to validation** and about **who joins
normalization output to the analysed response**. Because that input shape must
serve **all nine** validation layers — not only Syntax — the decision must be made
once, deliberately, before the first Syntax rule is written.

### Forces

1. **Two frozen single-boundary guarantees must survive.** The `ResponseNormalizer`
   is the single orchestration boundary of normalization and **never validates**;
   the `ResponseValidator` is the single orchestration boundary of validation and
   **never normalizes** (Response Validator §2.2). Neither may absorb the other's
   job.
2. **Frozen ownership must survive.** `ParsedResponse` is a Shared Platform Artifact
   created once, referenced never copied; `NormalizationResult` is the aggregate
   root that owns the observations; `AnalysisResult` is owned and produced by the
   Requirement Analysis Service; each has exactly one governing document
   (Architecture Freeze Index §5).
3. **A model cycle is forbidden.** Normalization *consumes* the analysis output
   (`LLMResponse`). Any design that makes `AnalysisResult` embed the
   `NormalizationResult` creates a circular dependency between the analysis and
   normalization model layers.
4. **Observations have exactly one home.** They live on `NormalizationResult`. A
   design that copies them elsewhere re-creates the two-homes defect this platform
   explicitly forbids.
5. **The solution must serve every future layer.** Schema, Structural, Content,
   Evidence, Traceability, Reasoning, and Business Rule all read the *same*
   `ParsedResponse`; the input shape chosen for Syntax is the input shape they all
   inherit.
6. **The rule contract is already generic.** `ValidationRule.validate(self,
   response: Any)` is typed `Any`. The abstract rule contract therefore does **not**
   need to change; only the concrete object passed as `response`, and the two typed
   orchestration signatures, are at issue.

## Decision

Introduce a new **Core Canonical Model — the `ValidationInput`** — as the single,
canonical input to the Response Validation subsystem, and define an explicit
**Normalization → Validation handoff** owned **above** both frozen orchestration
boundaries.

### 1. The `ValidationInput` canonical model

`ValidationInput` is a thin, immutable aggregate that **references, and never
copies**, exactly two existing artifacts:

| Reference | Provides | Owner (unchanged) |
| --------- | -------- | ----------------- |
| `analysis_result: AnalysisResult` | The original, un-validated response (`LLMResponse`, `generated_text`), execution identity, and provenance. | Requirement Analysis Service |
| `normalization_result: NormalizationResult` | The shared `ParsedResponse` (Normalization Outcome + normalized structure) via `.parsed_response`, and the Normalization Observations via `.observations`. | `ResponseNormalizer` |

`ValidationInput` **owns nothing but the binding**. It holds no findings, no
verdict, no structure of its own, and no copy of the `ParsedResponse` or the
observations — exactly as `AnalysisResult` references (not copies) its
`LLMResponse`, and as `ValidationResult` references (not copies) its configuration.
It is immutable and carries the execution correlation that ties its two references
to one and the same run.

It is added as a new Core Canonical Model under the extension clause the frozen
Validation Canonical Models already grants (§13, "New models may be added to
describe concerns not yet modelled"). It **does not** alter any of the six existing
canonical models.

### 2. The canonical validation input becomes `ValidationInput`

The object flowing into validation — and therefore the `response` every rule
receives — is the `ValidationInput`, not the bare `AnalysisResult`.

- `ResponseValidator.validate(...)` takes a `ValidationInput`. The **Single Entry
  Point** guarantee is preserved: still one doorway, still one input object; the
  object is simply richer.
- `ValidationPipeline.run(...)` takes the same `ValidationInput` and passes it
  unchanged to each rule.
- `ValidationRule.validate(self, response: Any)` is **unchanged** — `response` is
  now a `ValidationInput` at runtime, which the `Any` contract already admits.

### 3. How every rule reads what it needs

| Layer | Reads (via `ValidationInput`) | Source of truth |
| ----- | ----------------------------- | --------------- |
| **Transport** | `analysis_result.llm_response` / `execution_status` / emptiness | `AnalysisResult` (delivery facts) |
| **Syntax `SYNTAX-0001`** | `normalization_result.parsed_response.normalization_outcome` | `ParsedResponse` (a fact) |
| **Syntax `SYNTAX-0002`** | duplicate-identifier observations in `normalization_result.observations` | `NormalizationResult` (facts) |
| **Syntax `SYNTAX-0003`** | encoding observation in `normalization_result.observations` | `NormalizationResult` (facts) |
| **Schema … Business Rule** | `normalization_result.parsed_response.normalized_structure` | `ParsedResponse` (the one shared structure) |

Every rule reads the **same single `ParsedResponse` instance**; no rule parses,
normalizes, copies, or re-derives structure (upholding Rule Independence and
one-concern-per-layer). The observations remain **un-judged facts**; a rule turns a
fact into a judgment (`ValidationIssue`) — normalization records facts, validation
interprets them (Response Normalization Contract §10).

### 4. Ownership of the transition

The **Normalization → Validation handoff is owned by the platform's end-to-end
response-processing orchestration — a seam that sits *above* both frozen
orchestration boundaries** — never by the `ResponseNormalizer` and never by the
`ResponseValidator`.

```text
        Requirement Analysis Service
                 │  produces
                 ▼
            AnalysisResult ─────────────────────────┐
                 │  (its LLMResponse)                │ (referenced, unchanged)
                 ▼                                   │
        ResponseNormalizer   (single normalization boundary — never validates)
                 │  produces                         │
                 ▼                                   │
          NormalizationResult ──────────────┐        │
          (ParsedResponse + observations)   │        │
                                            ▼        ▼
                    ┌───────────────── HANDOFF SEAM ─────────────────┐
                    │  binds by reference → ValidationInput          │  ◄── owns the transition
                    │  (no normalization, no validation, no judgment)│
                    └───────────────────────┬────────────────────────┘
                                            │ ValidationInput
                                            ▼
        ResponseValidator   (single validation boundary — never normalizes)
                 │  orchestrates the pipeline over the ValidationInput
                 ▼
            ValidationResult
```

The seam performs **no** normalization and **no** validation. Its only
responsibilities are: (a) obtain the `NormalizationResult` for this execution from
the `ResponseNormalizer`, and (b) construct the `ValidationInput` that binds it to
the matching `AnalysisResult`, enforcing the integrity invariant that both
references describe the **same execution/correlation**. This is exactly the
end-to-end wiring the roadmap already anticipates ("wire the Response Validator
end-to-end", Platform Capability Matrix CAP-041 / §7); this ADR gives that wiring a
governed shape. Whether the seam is realised today as the CLI/pipeline composition
or later as a dedicated orchestrator is an **implementation** choice; the
**ownership principle** — the binding lives above both boundaries — is fixed here.

The `ResponseValidator` **must not** call the `ResponseNormalizer` (that would make
validation own normalization, violating Response Validator §2.2 and the
single-boundary guarantee). The seam calls both.

### 5. `AnalysisResult` does not evolve

`AnalysisResult` keeps its exact current shape. It gains **no** normalization
field. This preserves its single owner (the Requirement Analysis Service), avoids a
nullable "sometimes-populated" field, and — decisively — avoids the analysis →
normalization model cycle (force 3). The `ValidationInput` lives in the validation
layer, which legitimately depends on both upstream models; the dependency fans **in**
to validation, it does not cycle.

### 6. Lifecycle invariant (permanent)

> **Architectural Invariant — `ValidationInput` is an immutable, execution-scoped
> aggregate.**
> A `ValidationInput` is **created exactly once, after normalization completes**, and
> binds **exactly one `AnalysisResult` to exactly one corresponding
> `NormalizationResult` produced for the same execution**. Once created it is
> **immutable**: it is **never rebound** (its two references never change), **never
> mutated**, and **never reused across executions** — each execution constructs its
> own `ValidationInput`, and it does not outlive the run it was created for.

This is a **lifecycle invariant only**. It changes **no** ownership, **no**
dependency, and **no** responsibility established elsewhere in this ADR: the
`AnalysisResult` and `NormalizationResult` keep their owners and shapes, the
`ParsedResponse` remains the single shared instance referenced through the
`NormalizationResult`, the observations keep their single home, and the handoff seam
remains the sole creator of the `ValidationInput` (§4). The invariant simply fixes,
permanently, *when* the aggregate comes into being (once, post-normalization), *what*
it binds (one `AnalysisResult` + one same-execution `NormalizationResult`), and that
it is stable and disposable per run. It reinforces the same-execution integrity
invariant of §4 and the platform-wide immutability discipline already applied to
`ParsedResponse`, `NormalizationResult`, `AnalysisResult`, and `ValidationResult`.

## Questions this ADR resolves

| # | Question | Resolution |
| - | -------- | ---------- |
| 1 | Canonical input to the Response Validator after normalization? | The new **`ValidationInput`** aggregate (references `AnalysisResult` + `NormalizationResult`). |
| 2 | How does `ParsedResponse` reach every rule? | Via `ValidationInput.normalization_result.parsed_response` — the one shared instance, read-only, identical for every rule; no rule re-derives it. |
| 3 | How do the Normalization Observations reach `SYNTAX-0002`/`SYNTAX-0003`? | Via `ValidationInput.normalization_result.observations` — the single owning home, unchanged; the rules read the duplicate-identifier and encoding facts and raise issues. |
| 4 | Which component owns the transition? | A **handoff seam above both boundaries** (the end-to-end response-processing orchestration). Neither the `ResponseNormalizer` nor the `ResponseValidator` owns it. |
| 5 | Should `AnalysisResult` evolve, or a new object be introduced? | **A new object** (`ValidationInput`). `AnalysisResult` does **not** evolve. |
| 6 | Effect on future Schema…Business layers? | Uniform and one-time: every later layer reads `normalized_structure` from the **same** `ParsedResponse` via the **same** `ValidationInput`. One input shape serves all nine layers; nothing further is renegotiated per layer. |
| 7 | Preserve frozen ownership? | Yes — see the table below. |

### Ownership preservation

| Frozen artifact | Frozen ownership rule | Effect of this ADR |
| --------------- | --------------------- | ------------------ |
| **`ParsedResponse`** | Created once by the `ResponseNormalizer`; Shared Platform Artifact; referenced, never copied/mutated/recreated. | **Unchanged.** `ValidationInput` reaches it through the `NormalizationResult`; every rule reads the same instance. Its shape is untouched (still no observations); `PARSED_RESPONSE_VERSION` does not move. |
| **`NormalizationResult`** | Aggregate root and single output of normalization; sole owner of the observations. | **Unchanged.** `ValidationInput` references it; observations keep their single home. |
| **`AnalysisResult`** | Produced and owned by the Requirement Analysis Service; carries the response forward. | **Unchanged shape and owner.** `ValidationInput` references it. |
| **`ResponseNormalizer`** | Single orchestration boundary of normalization; never validates. | **Unchanged.** It neither binds nor validates; it still produces the `NormalizationResult`. |
| **`ResponseValidator`** | Single orchestration boundary of validation; orchestrates, never validates; returns one `ValidationResult`. | **Entry-point input type amended** from `AnalysisResult` to `ValidationInput` (the one governed change). Its responsibilities, lifecycle, profile selection, configuration hierarchy, result production, and "never normalize" guarantee are all unchanged. |

## Consequences

- ✅ `SYNTAX-0001`, `SYNTAX-0002`, and `SYNTAX-0003` become implementable: each has a
  defined, read-only path to the exact fact it needs.
- ✅ All nine layers are served by a single input shape decided once; Schema…Business
  need no further plumbing decision.
- ✅ Both single-boundary guarantees survive: the seam, not either boundary, owns the
  join.
- ✅ No frozen canonical model is mutated; the observations keep exactly one home; the
  `ParsedResponse` stays shared and referenced.
- ✅ The abstract `ValidationRule` contract (`response: Any`) is unchanged; the four
  frozen Transport rules keep their identity, concern, severity, and blocking.
- ⚠️ **Governed amendments follow from this ADR** (to be applied as a separate,
  ratified step — not by this ADR document):
  - `docs/architecture/response-validator.md` §3/§5 — input becomes `ValidationInput`.
  - `docs/architecture/validation-canonical-models.md` §2/§13 — add `ValidationInput`
    as a Core Canonical Model (additive).
  - `docs/architecture/validation-rule-catalog.md` §8.2 — the Syntax "reads" wording
    is realised through `ValidationInput` (no rule identity changes).
  - `docs/development/validation-rule-development-guide.md` — the `response` a rule
    receives is a `ValidationInput`; examples updated accordingly.
  - `docs/governance/architecture-freeze-index.md` and
    `docs/governance/platform-capability-matrix.md` — reference this ADR; add the
    `ValidationInput` capability row per the Matrix §8 process.
- ⚠️ **Version impact:** introducing the `ValidationInput` and changing the validator
  input shape changes what validation *consumes* and is therefore a **Validation
  Contract Version** advance (major, per AI Response Validation §13.2) and a
  **Validator Version** advance; re-pointing the four Transport rules' field access
  to `analysis_result.…` is an **implementation** (mechanism) change advancing the
  Validator Version only — no Rule Version and no architectural change to any
  Transport rule. `PARSED_RESPONSE_VERSION`, the Normalization Contract Version, and
  the `NormalizationResult` shape do **not** move.
- ⚠️ Implementation must enforce the seam's integrity invariant: a `ValidationInput`
  binds a `NormalizationResult` and an `AnalysisResult` from the **same execution**;
  a mismatched or absent `NormalizationResult` is a construction/handoff failure
  (an infrastructure error), never a validation verdict.

## Alternatives considered

- **A1 — Carry `ParsedResponse` on `LLMResponse` (or `AnalysisResult`)** (the Syntax
  Layer Design Review §7.1 primary suggestion). **Rejected:** it is *insufficient*
  (observations are deliberately not on the `ParsedResponse`, so `SYNTAX-0002`/`0003`
  remain unserved); it couples provider/analysis models to normalization; and
  carrying `ParsedResponse` on `LLMResponse` would create the analysis/normalization
  model cycle (force 3).
- **A2 — Evolve `AnalysisResult` to reference the `NormalizationResult`.**
  **Rejected:** it creates the analysis → normalization **model cycle** (force 3),
  since normalization already consumes the analysis output; it introduces a second
  producer of `AnalysisResult` (the seam rebuilding an immutable model the Analysis
  Service owns), blurring single-ownership; and it makes the normalization reference
  a nullable field that is populated only sometimes.
- **A3 — Extend the validation input contract to take a second parameter
  (`NormalizationResult`) on the validator/pipeline/rule.** **Rejected:** it
  multiplies the validator entry point and the rule surface, works against Single
  Entry Point (Response Validator §4.1) and the additive-behind-the-entry-point rule
  (§21), and spreads the join across every rule instead of localising it in one
  input object.
- **A4 — Let the `ResponseValidator` call the `ResponseNormalizer`.** **Rejected:**
  it makes validation own normalization, violating Response Validator §2.2 and the
  single-boundary guarantee; it also re-derives normalization inside the validation
  boundary, defeating "normalize once".
- **A5 — Leave the gap and reconcile it inside the first Syntax rule.**
  **Rejected:** it would bake a silent, per-rule reconciliation into code, break Rule
  Independence (each rule reaching for normalization its own way), and violate the
  platform's freeze philosophy (architecture decided before implementation) — the
  same reasoning that produced ADR-0002.

## Scope note

This ADR decides **the input shape and the ownership of the handoff**. It does
**not** define the `ValidationInput`'s field names or serialization, the seam's
concrete home (CLI wiring vs. a dedicated orchestrator), or the Syntax rules'
internal logic. Those belong to the implementation task and to the forthcoming
Syntax Validation Implementation Contract, which this ADR unblocks. `ValidationInput`
is the working name; the final name is an implementation choice (alternatives:
`ValidationSubject`, `AnalyzedResponse`, `NormalizedAnalysis`).
