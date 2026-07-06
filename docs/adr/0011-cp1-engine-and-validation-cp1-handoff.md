# ADR 0011 — The CP1 Validation Engine and the Validation → CP1 Handoff

- **Status:** Proposed
- **Date:** 2026-07-06

## Problem

The **CP1 Validation Engine** initiative must begin, but CP1 has **no governing
architecture** and its only existing artifact encodes a **contradictory input**.
`requirement_intelligence/validators/cp1.py` defines
`CP1Validator.validate(requirements: list[CanonicalRequirement])` — a signature
that **predates the Validation Platform** and consumes the *pre-AI, ingested*
requirement set. CP1's actual mandate is to evaluate **engineering readiness of
the requirements the Validation Platform has already validated** — a different
artifact, at a different pipeline stage, produced by a different responsibility.

The Validation Platform validates that an AI **response** is structurally and
deterministically correct. CP1 must decide whether those **validated
requirements** are fit to engineer software from. Those are distinct
responsibilities, and the seam between them is undefined. Until the input shape,
the handoff ownership, the flow position, the gating semantics, the engine
pattern, and the stub's disposition are decided **once, deliberately**, CP1
cannot be implemented without baking in an inconsistency and a non-deterministic
gate. This ADR makes those decisions and unblocks the initiative's foundation.

## Context

**Validation Platform v1.0.0 is complete and frozen** (`v1.0.0-validation-platform`).
The current end-to-end flow is:

```text
Consolidation → Requirement Analysis → Response Normalization → Validation Platform → ValidationResult
```

Reviewed governing artifacts: the Validation Platform (`validation/`), the
Response Validator (`docs/architecture/response-validator.md`), the AI Response
Validation Architecture, ADR-0003 through ADR-0010, the Platform Capability
Matrix, the Architecture Overview, the platform execution flow
(`workflows/requirement_pipeline.py`), the CP1 stub, the Execution Package, and
`PlatformContext`. The relevant facts established from the repository:

1. **`ValidationResult` does not carry the normalized structure.** It *contains*
   the preserved, unaltered `AnalysisResult` (which carries only the raw
   `LLMResponse`/`generated_text`), *owns* the summary/statistics/issues, and
   *references* configuration/framework metadata. It carries **no
   `ParsedResponse` and no `normalized_structure`**. The validated, AI-analysed
   requirements (`functionalRequirements` / `securityRequirements` /
   `qualityRequirements` / `recommendations`) live in
   `NormalizationResult.parsed_response.normalized_structure`, reached during a
   validation run through the `ValidationInput` — **not** on the `ValidationResult`.
2. **`ParsedResponse` already names CP1's siblings.** It is a Shared Platform
   Artifact whose declared consumers include *"Requirement Normalization, Feature
   Generation, Test Generation, AI Evaluation, Analytics."* The validated
   requirements CP1 must judge, and that Feature Generation later consumes, are
   the ones this shared instance carries.
3. **Two verdict vocabularies exist by deliberate design.** The Validation
   Platform owns `PASSED / PASSED_WITH_WARNINGS / FAILED / BLOCKED`
   (`validation/models/validation_enums.py`). CP1 owns `PASS / FAIL / WARN`
   (`shared/enums/base.ValidationVerdict`). The validation README records this
   separation as intentional ("different semantics; kept local to avoid name
   collision").
4. **The legacy stub is inconsistent.** `validators/cp1.py` consumes
   `list[CanonicalRequirement]` (the pre-AI ingested set) and raises
   `NotImplementedError`. It also owns the working `CP1Result` / `CP1Finding`
   models and the correct `PASS/FAIL/WARN` verdict.
5. **CP1 is already catalogued as `CAP-060`** (Downstream/Future), dependent on
   the Response Validator, and already carries a **flagged consistency note**.
6. **The Normalization → Validation handoff precedent is ADR-0003**: it
   introduced the `ValidationInput` canonical model and located the binding at a
   seam **above** both frozen orchestration boundaries. The Validation → CP1
   handoff is the identical situation one layer downstream.

### Forces

1. **The Validation Platform is frozen.** CP1 is downstream and additive; it must
   **neither modify nor extend** the Validation Platform, Response Normalization,
   or the Validation Framework.
2. **Normalize once; single boundaries survive.** The `ResponseNormalizer` never
   validates and the `ResponseValidator` never normalizes (Response Validator
   §2.2). CP1 must not re-normalize or re-parse; it must read the *already
   normalized* structure.
3. **`ValidationResult` alone is insufficient input.** It preserves the raw
   `AnalysisResult` but **not** the normalized structure CP1 must evaluate
   (context §1). Feeding CP1 the `ValidationResult` would force it to re-normalize
   the raw text — violating force 2.
4. **Determinism is platform-wide.** CP1's judgement must be **deterministic and
   governed**, exactly as validation is (AI Response Validation §3.4). "Suitable
   for engineering" cannot be an invented, per-implementation heuristic.
5. **The two verdict vocabularies must stay separate.** CP1 owns `PASS/FAIL/WARN`;
   it must not conflate with, or re-derive, the four-state validation verdict.
6. **One canonical owner; handoffs live above both boundaries.** Each concept has
   exactly one owner (governance §5); a cross-subsystem handoff is owned by the
   seam above both, never by either subsystem (ADR-0003 §4).
7. **Additive-via-ADR discipline.** New catalogued concerns grow additively
   behind ADRs, never invented in code (ADR-0004…0010). CP1's criteria inherit
   this discipline.

## Decision

Establish the **CP1 Validation Engine** as a downstream, additive, deterministic
**engineering-readiness gate**, and define an explicit **Validation → CP1
handoff** owned **above** both the Validation Platform and CP1 — mirroring the
Normalization → Validation handoff of ADR-0003.

### D1. What CP1 is, and why it exists

CP1 ("Control Point 1") is the **first engineering-fitness gate** of the
platform. Where the Validation Platform proves a response is *correct as an
artifact*, CP1 decides whether the **validated requirements are fit to engineer
software from**. It exists because a response can be perfectly valid (`PASSED`)
yet **unsuitable for engineering** — too sparse to build features from,
non-actionable, untestable, or lacking coverage. The Validation Platform
**deliberately does not judge fitness for downstream use**; without CP1,
valid-but-unsuitable requirements would flow uncaught into Feature Engineering
and corrupt everything built on them. CP1 is the fitness firewall between
Requirement Intelligence and downstream engineering.

### D2. Where CP1 begins and ends

- **Begins** at the Validation → CP1 seam (D4), immediately after the Validation
  Platform emits a `ValidationResult` whose verdict permits progression (D5).
  CP1 begins when it receives its `CP1Input`.
- **Ends** when CP1 emits its `CP1Result` (a `PASS/FAIL/WARN` verdict + findings).
  CP1 ends **before** Feature Generation; it never enters Feature Generation.

### D3. Introduce a dedicated, immutable `CP1Input` (identified, not designed)

CP1 consumes a **new Core Canonical Model — the `CP1Input`** — the single,
immutable canonical input to the CP1 engine, and **not** the `ValidationResult`
directly. `CP1Input` **references, and never copies**, the artifacts CP1 needs:
(a) the **validated normalized structure** (the analysed requirements, reached
through the shared `ParsedResponse`), and (b) the **validation provenance /
verdict** proving the response passed. It owns **only the binding** — no
findings, no verdict of its own, no derived structure — exactly as
`ValidationInput` owns only the binding of `AnalysisResult` + `NormalizationResult`.

It is added under the same additive extension clause the platform already used
for `ValidationInput` (Validation Canonical Models §13). **This ADR identifies
`CP1Input`; it does not design its fields, names, or serialization** — those
belong to the implementation task, exactly as ADR-0003 deferred the shape of
`ValidationInput`.

> **Justification (why a dedicated `CP1Input`, not the `ValidationResult`).**
> The decisive reason is force 3: the `ValidationResult` carries the preserved
> raw `AnalysisResult` but **not** the normalized structure CP1 must evaluate, so
> consuming it directly would compel CP1 to re-normalize — breaking normalize-once
> and the single-boundary guarantees. A dedicated `CP1Input` additionally
> **decouples** CP1 from validation's internal aggregate (summary, statistics,
> framework metadata) that CP1 must not reason about, keeps the **gating decision
> at the seam** rather than inside CP1, and makes the handoff the exact, symmetric
> analogue of ADR-0003 — one governed pattern reused, not a new one invented.

### D4. Execution flow and the Validation → CP1 seam

The governed end-to-end flow becomes:

```text
Consolidation → Requirement Analysis → Response Normalization → Validation Platform
        │
        ▼  ValidationResult
   ┌─────────────── VALIDATION → CP1 HANDOFF SEAM ───────────────┐
   │  gate on verdict (D5); bind by reference → CP1Input          │  ◄── owns the transition
   │  (no validation, no normalization, no engineering judgment)  │
   └───────────────────────────┬─────────────────────────────────┘
                               │ CP1Input
                               ▼
                          CP1 Engine
                               │ CP1Result
                    ┌──────────┴───────────┐
             PASS / WARN                 FAIL
                    │                       │
                    ▼                       ▼
           Feature Generation        halt + report
```

The seam performs **no** validation, **no** normalization, and **no**
engineering judgement. Its only responsibilities are: (a) read the upstream
verdict and gate (D5), and (b) construct the `CP1Input` binding the validated
normalized structure to its validation provenance. Ownership of the transition
lives **above both boundaries** — never inside the Response Validator and never
inside the CP1 engine — exactly as the Normalization → Validation seam is owned
above both the normalizer and the validator (ADR-0003 §4). Whether the seam is
realised as the CLI/pipeline composition (`PlatformContext`) or a dedicated
orchestrator is an **implementation** choice; the **ownership principle** is
fixed here.

### D5. Gating semantics

CP1 executes **only when the validation verdict ∈ { `PASSED`,
`PASSED_WITH_WARNINGS` }**. A `FAILED` or `BLOCKED` response **never reaches CP1**.

> **Justification.** It is incoherent to assess the engineering readiness of
> requirements carried by a response that failed *structural* validation — the
> content is not trustworthy as an artifact, so any readiness judgement over it
> would be meaningless. Fail-fast (AI Response Validation §3.1) is preserved.
> `PASSED_WITH_WARNINGS` **is** a passing (non-blocking) verdict under the
> platform's highest-severity-wins model, so it proceeds; the warnings are
> recorded upstream and may inform, but never pre-empt, CP1's independent
> judgement. The gate is enforced **by the seam** (D4), not by CP1 — CP1 trusts
> it is only ever invoked on a passable input, keeping CP1 free of upstream-verdict
> logic and preserving the vocabulary separation (force 5).

### D6. CP1 ownership

**Inside CP1 (illustrative — the concrete criteria are governed later, D8):** the
**engineering-readiness / suitability** of validated requirements — e.g.
actionability, testability, sufficiency/coverage adequacy, engineering-ambiguity,
buildability — evaluated **deterministically** over the validated normalized
structure.

**Never inside CP1:** artifact correctness (validation — frozen, upstream),
normalization, AI generation or re-generation, ingestion / consolidation /
classification, requirement rewriting / repair / remediation, feature or scenario
synthesis (Feature Generation), test generation, cross-run analytics, and **any
non-deterministic mechanism** (LLM / embedding / NLP heuristic judgement). CP1
must remain deterministic and governed like the rest of the platform.

### D7. CP1 architectural pattern

The CP1 engine **mirrors the platform's governed evaluation pattern**:

```text
Criterion (one concern) → Registry (sealed, deterministic order) → Pipeline → Aggregate Result (CP1Result)
```

This is the proven shape of the Validation Framework
(`ValidationRule → ValidationRegistry → ValidationPipeline → ValidationResult`),
reused **as a pattern** — CP1 does **not** import, subclass, or modify the frozen
Validation Framework. The pattern guarantees exactly what CP1 needs: deterministic
ordering (sealed registry), an always-populated result, one concern per criterion,
and criterion independence. **This ADR identifies the pattern; it does not build
the framework.**

### D8. Required canonical models and the CP1 criteria catalogue (identified only)

Identified as required — **none designed here**:

| Artifact | Kind | Role |
| -------- | ---- | ---- |
| `CP1Input` | New Core Canonical Model | The immutable Validation → CP1 handoff binding (D3). |
| `CP1Result` | Canonical output model | The immutable aggregate output (verdict + findings). A working stub exists. |
| `CP1Finding` | Canonical finding model | One atomic engineering-readiness finding. A working stub exists. |
| **CP1 Criteria Catalogue** | **Governance artifact** (not a canonical model) | The single governed source of CP1 criterion identity and order — the CP1 analogue of the Validation Rule Catalog. |

The **CP1 Criteria Catalogue is a required future governance artifact**: without
it, "engineering readiness" has no governed, deterministic definition (force 4).
Its creation, and every concrete criterion, is deferred to a **future ADR** under
the same additive-via-ADR discipline as the Validation Rule Catalog (ADR-0004…0010).

### D9. Disposition of the legacy stub

`validators/cp1.py` is **reconciled, not preserved as-is and not discarded**
(no code is changed by this ADR — the reconciliation is *authorized* here and
*executed* in the implementation task):

- Its **input signature** `validate(list[CanonicalRequirement])` is **superseded
  (deprecated)** — it binds the wrong artifact at the wrong stage. It is replaced
  by consuming `CP1Input` (D3).
- Its **output models** `CP1Result` / `CP1Finding` are **retained as the
  conceptual basis** for the identified output models (final shape deferred, D8).
- Its **verdict vocabulary** `shared.enums.base.ValidationVerdict`
  (`PASS/FAIL/WARN`) is **retained** as CP1's correct, deliberately-separate
  vocabulary (force 5).
- Its **location** (`validators/`) and **`CAP-060`** allocation are **retained**.

## Alternatives Considered

- **A1 — CP1 consumes `ValidationResult` directly.** **Rejected:** the
  `ValidationResult` does **not** carry the normalized structure (context §1), so
  CP1 would have to re-normalize the raw `AnalysisResult` — breaking normalize-once
  and the single-boundary guarantees (force 2/3). It also couples CP1 to
  validation's internal aggregate (summary/statistics/framework metadata) it must
  not reason about, and invites CP1 to re-derive the upstream verdict, blurring the
  vocabulary boundary.
- **A2 — Evolve `ValidationResult` to carry the normalized structure for CP1.**
  **Rejected:** it mutates a **frozen** canonical model to serve a downstream
  consumer, gives the `ParsedResponse` a second home (two-owners defect,
  governance §5), and advances the frozen Validation Contract for a reason that
  belongs downstream. The dependency should fan **into** CP1, not push structure
  **onto** validation's output.
- **A3 — CP1 consumes the raw `AnalysisResult` and re-normalizes internally.**
  **Rejected:** it re-derives normalization inside CP1, defeating normalize-once
  and making CP1 own a normalization responsibility (force 2).
- **A4 — Keep the stub: CP1 consumes `list[CanonicalRequirement]`.** **Rejected:**
  it binds the **pre-AI ingested** requirements, not the **validated, analysed**
  ones — the wrong artifact at the wrong stage. CP1 would judge readiness of
  requirements that never passed through analysis or validation, contradicting its
  mandate and the flow.
- **A5 — Let the CP1 engine call the Response Validator / Normalizer itself.**
  **Rejected:** it makes CP1 own upstream orchestration, violating the
  single-boundary guarantees; the seam calls upstream, CP1 does not.
- **A6 — Define CP1 but leave its criteria undefined for implementers to fill in.**
  **Rejected:** implementers would invent divergent, non-deterministic
  "suitability" heuristics — the exact anti-pattern ADR-0008/0009/0010 exist to
  prevent. CP1 criteria must come from a governed catalogue (D8).

## Ownership

| Frozen / existing artifact | Ownership rule | Effect of this ADR |
| -------------------------- | -------------- | ------------------ |
| **Validation Platform** (framework, validator, rules, verdict) | Judges *artifact correctness* of the AI response; single validation boundary; frozen. | **Unchanged.** CP1 is downstream; it consumes nothing frozen except by reference through `CP1Input`. |
| **`ValidationResult`** | Owned, immutable output of validation; preserves the raw `AnalysisResult`. | **Unchanged.** CP1 does **not** consume it directly (D3/A1). |
| **`ParsedResponse`** | Shared Platform Artifact; created once; referenced, never copied. | **Unchanged.** `CP1Input` reaches the validated structure through it, read-only; shape and `PARSED_RESPONSE_VERSION` untouched. |
| **`NormalizationResult` / `ValidationInput`** | Single-owner aggregates (ADR-0003). | **Unchanged.** Referenced, never copied; observations keep their single home. |
| **Response Normalization** | Single normalization boundary; never validates. | **Unchanged.** |
| **Feature Generation** | Synthesises testable features/scenarios from **CP1-approved** requirements. | **Unchanged; now explicitly gated by CP1.** |
| **CP1 Engine** *(new)* | Judges *engineering readiness* of validated requirements; owns `PASS/FAIL/WARN`; deterministic. | **Established** by this ADR (D1, D6). |
| **Validation → CP1 seam** *(new)* | Gates on verdict and binds `CP1Input`, above both boundaries. | **Established** by this ADR (D4). |

## Execution Flow

Verified in D4. CP1 sits strictly **after** the Validation Platform and strictly
**before** Feature Generation; the seam owns gating + binding. The proposed target
flow (`… → Validation Platform → CP1 → Feature Generation`) is **correct**, with
the seam made explicit.

## Migration Impact

- **Code (deferred to implementation, not done here):** replace the stub's
  `list[CanonicalRequirement]` input with `CP1Input`; retain `CP1Result` /
  `CP1Finding` and the `PASS/FAIL/WARN` verdict; keep the `validators/` location
  and `CAP-060` (D9).
- **Documentation (governed amendments that follow from this ADR — to be applied
  as a ratified step, not by this document):**
  - `docs/architecture/overview.md` — the Requirement Intelligence pipeline
    (`… → Analyzer → CP1 Validator → Report`) **omits Response Normalization and
    the Validation Platform and mis-places CP1**; correct it to
    `… → Analyzer → Normalization → Validation Platform → CP1 → Report/Feature
    Generation`.
  - `requirement_intelligence/workflows/requirement_pipeline.py` docstring — the
    same stale flow; realign when the pipeline is wired.
  - `docs/governance/platform-capability-matrix.md` — reconcile the `CAP-060`
    flagged consistency note; reference this ADR.
  - `docs/governance/architecture-freeze-index.md` — register ADR-0011 (see
    *Governance Registration*).

## Future Extension Points

All **identified, none designed**:

- **Criteria** — added additively to the governed **CP1 Criteria Catalogue** via
  ADR, mirroring the Validation Rule Catalog's `<LAYER>-NNNN` additive growth.
- **Profiles** — governed, immutable criterion-subset identities selecting which
  criteria run, mirroring Validation Profiles; ordering stays governed by the
  engine.
- **Catalogues** — the CP1 Criteria Catalogue is the single source of truth for
  criterion identity and order.
- **Plug-ins** — new criteria conforming to the CP1 criterion contract, registered
  **explicitly** (no reflection), sealed at pipeline construction — the same
  discipline as the Validation Registry.

## Architectural Inconsistencies Discovered

Recorded on the register; **not silently resolved**:

1. **Stub input contradicts CP1's mandate** (`list[CanonicalRequirement]` vs the
   validated, analysed requirements). Resolved *on the record* by D3/D9; code
   change deferred to implementation.
2. **`overview.md` / `requirement_pipeline.py` flow is stale** (omits
   Normalization + Validation Platform; mis-places CP1). Recorded; amendment
   listed under *Migration Impact*; **not** edited by this ADR.
3. **No governed "engineering-readiness" criteria exist.** CP1's judgement domain
   is undefined and would be non-deterministic without a governed catalogue.
   Recorded; a **CP1 Criteria Catalogue ADR** is required before any criterion is
   implemented (D8).
4. **`CAP-060` carries a flagged consistency note** (Planned vs Implementation In
   Progress). Recorded; reconciled when `CAP-060` is updated per Matrix §8.
5. **`ValidationResult` does not carry the normalized structure** (context §1).
   Not a defect, but the **decisive constraint** that rejects A1 and mandates
   `CP1Input`.

## Relationship to Existing ADRs

- **ADR-0003** — the **direct precedent and template**. `CP1Input :
  Validation → CP1` is the exact analogue of `ValidationInput :
  Normalization → Validation`, including the seam-above-both-boundaries ownership.
  This ADR reuses that governed pattern rather than inventing a new one.
- **ADR-0002** — precedent for *clarifying a boundary between contracts via an ADR
  without changing any contract's shape*; CP1's boundary is established in the same
  governance mode.
- **ADR-0004 … ADR-0010** — all concern **validation-rule dispositions inside the
  frozen Validation Platform**; CP1 is downstream and touches none of them. They
  establish the **discipline CP1 inherits**: additive-via-ADR catalogue growth,
  no-invention, determinism, one-concern-per-unit, and reserved identities — which
  the future CP1 Criteria Catalogue will follow.

## Version Impact

- This ADR is **additive and downstream**. It changes **no** frozen contract and
  advances **no** existing version: `PARSED_RESPONSE_VERSION`,
  `VALIDATION_INPUT_VERSION`, the Validation Contract / Validator / Framework
  versions, and the Normalization versions all **stay put**.
- It establishes a **new capability lineage (`CAP-060`, CP1)**. The CP1 contract /
  `CP1Input` / `CP1Result` version constants are established **when those models
  are defined** (a follow-on step) — **not** in this ADR, which only identifies
  them.

## Implementation Readiness

**CP1 implementation may begin in a specific, bounded order — and no further.**

- ✅ **May proceed after this ADR (once Accepted):** the **CP1 canonical-model
  definitions** (`CP1Input`, `CP1Result`, `CP1Finding` shapes), the **CP1 engine
  scaffolding** (criterion contract → sealed registry → pipeline → aggregate
  result, D7), the **Validation → CP1 seam** and gating (D4/D5), and the **stub
  reconciliation** (D9).
- 🛑 **May NOT proceed until a further governed gate:** any **concrete CP1
  suitability criterion**. "Engineering readiness" has **no governed catalogue**
  (inconsistency 3); implementing criteria now would invent non-deterministic
  judgement (force 4). A **CP1 Criteria Catalogue ADR** must exist first — the same
  discipline that governs every validation rule.

This is a **stated remaining gate, not a silent resolution**: the engine and the
handoff are unblocked; the *criteria* are not, and must not be improvised in code.

## Governance Registration

On this ADR being recorded (Proposed), the minimal registration applied now is:

- `docs/governance/architecture-freeze-index.md` §6 — a row registering ADR-0011
  (the Validation → CP1 handoff / CP1 engine decision).

The following are **governed amendments to be applied on acceptance** (a separate,
ratified step — consistent with ADR-0003's amendment handling), **not** performed
by this document: the `CAP-060` reconciliation and CP1 rows in the Platform
Capability Matrix and Architecture Coverage Dashboard, and the `overview.md` /
pipeline-docstring flow corrections (*Migration Impact*).

## Scope Note

This ADR decides **the CP1 input shape, the handoff ownership, the flow position,
the gating semantics, the engine pattern, the required (identified) models and
catalogue, and the stub's disposition**. It does **not** implement CP1, design or
create `CP1Input` / `CP1Result` / `CP1Finding`, build any framework, define any
suitability criterion, create the CP1 Criteria Catalogue, or modify
`validators/cp1.py`, the Validation Platform, Response Normalization, the
Validation Framework, or any frozen canonical model or contract. `CP1Input` is the
working name; the final name is an implementation choice. Activation of concrete
CP1 criteria is contingent on a **future** CP1 Criteria Catalogue ADR.
