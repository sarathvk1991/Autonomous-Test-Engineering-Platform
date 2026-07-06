# ADR 0013 — CP1-0001 (EngineeringInputAvailabilityCriterion): the First Engineering Readiness Criterion

- **Status:** Accepted
- **Date:** 2026-07-06 (Proposed) · 2026-07-06 (Accepted)

## Problem

The CP1 subsystem is assemblable end-to-end (models, framework, seam, engine,
composition root — CAP-062…066), but the **Engineering Readiness Criteria Catalog is
intentionally empty** (ADR-0012): a composed `CP1Service` runs and always returns
`PASS` because there is nothing to judge.  Before any criterion is implemented, its
**concern and deterministic basis must be governed** — exactly as ADR-0008 governed
the byte-exact comparison mechanism for `REASONING-0002` before it existed.

This ADR governs **CP1-0001**, the first engineering-readiness criterion.  It defines
**what CP1-0001 is**, not how it is coded.  The hard constraint (ADR-0012 §8, §12; the
platform determinism mandate) is that a criterion must be evaluable **deterministically**
using **only `CP1Input`**, with **no semantic reasoning, NLP, LLM, business, or
domain knowledge**, and **without overlapping the Validation Platform**.

## Context

The governed AI response is arrays of **bare string statements** (Prompt Framework
`JSON_RESPONSE_REQUIREMENTS`: `summary`, `functional_requirements`,
`security_requirements`, `quality_requirements`, `recommendations`, `risks`; "Every
array element must be a string statement").  The three **governed requirement
collections** are `functional_requirements`, `security_requirements`,
`quality_requirements` (the exact set ADR-0007 fixed for `CONTENT-0002`).

Design-review findings, from repository evidence:

1. **No prior explicit definition of CP1-0001.** Searched ADRs, governance, the
   catalog, `docs/architecture/`, the Prompt Framework, the analyzer, the
   `validators/cp1.py` stub, README, and comments.  The **only** engineering-readiness
   language present is **aspirational and semantic**: the prompt asks for "atomic,
   unambiguous and testable" requirements and "actionable" recommendations; the
   `requirement_analyzer` stub mentions "quality scoring, gap detection, testability
   assessment"; the `cp1.py` stub says "good enough to proceed."  **All of these are
   semantic** (they require understanding requirement *meaning*) — none is a governed,
   deterministic definition, and none can be the first deterministic criterion.
2. **What Validation already owns (must not be overlapped).** The Validation Platform
   deterministically checks, over the same response: required sections present
   (`SCHEMA-0001`), required arrays present (`SCHEMA-0004`), each requirement value
   non-empty (`CONTENT-0001`), no within-collection duplicates (`CONTENT-0002`,
   ADR-0007).  Its **Business Rule layer** (§8.9) *claims* "minimum number present"
   (`BUSINESS-0001`) and "requirement coverage meets the declared policy"
   (`BUSINESS-0003`) — but these are **Reserved · Deferred** (ADR-0006) because **no
   governed coverage/minimum policy exists**.
3. **The gap Validation does not cover.** A response with **present, valid, empty**
   requirement arrays — `functional_requirements: []`, `security_requirements: []`,
   `quality_requirements: []` — **passes all validation** (`SCHEMA-0004` present;
   `CONTENT-0001` vacuous; no policy to fail).  It is a **correct artifact with no
   engineering input to begin from** — the archetypal *valid-but-not-engineering-ready*
   case (ADR-0011 §D1/§D2).

### Forces

1. **Determinism is mandatory** (ADR-0012 §8, §12): no semantics/NLP/LLM/heuristics.
2. **Bare strings admit no deterministic *quality* judgement.** Testability,
   actionability, atomicity, and unambiguity are all **semantic** → each is a STOP
   condition for a deterministic criterion.  The only deterministic operations over
   bare-string arrays are **counting** and **presence**.
3. **No invented policy** (ADR-0005/0006/0009/0010 discipline): any minimum `N > 1`
   or per-domain coverage is an ungoverned policy and must not be invented.
4. **Validation and Engineering Readiness must stay separate** (ADR-0011 §D1).
5. **Criteria are independent and non-mutating** (ADR-0012 §5); aggregation is the
   engine's, never a criterion's (ADR-0012 §8).

## Decision

Govern **CP1-0001 — `EngineeringInputAvailabilityCriterion`** — the criterion of
**Engineering Input Availability**: *the validated response must provide sufficient
engineering input from which downstream engineering may begin.*

### D1. Single concern

CP1-0001 owns **exactly one** concern: **Engineering Input Availability** — *whether
the validated response provides sufficient engineering input from which downstream
engineering may begin.*  Concretely, that floor is the presence of **at least one**
requirement to engineer from.  CP1-0001 does **not** judge requirement *quality,
testability, actionability, coverage, or count beyond one*; those are separate
concerns.

### D2. Deterministic evaluation basis

The mechanism is unchanged: the **pooled requirement count** — the total number of
elements across the three governed requirement collections (`functional_requirements`
+ `security_requirements` + `quality_requirements`) in the normalized structure — is
**≥ 1**.  This is pure element counting: deterministic, order-independent, and free of
semantics.  The collections are **pooled** (union): CP1-0001 asks *"is there any
engineering input to begin from?"*, not *"which domains are covered?"* (pooling here is
a different concern from `CONTENT-0002`'s within-collection scope — no conflict with
ADR-0007).

### D3. Required inputs

**`CP1Input` only** — the normalized structure reached through
`cp1_input.normalization_result.parsed_response.normalized_structure`.  CP1-0001 runs
only on responses the **Validation → CP1 seam** admitted (verdict `PASSED` /
`PASSED_WITH_WARNINGS`, ADR-0011 §D5), which guarantees a **`NORMALIZED`** structure
is present.  No other input, no additional canonical model.

### D4. Verdict contribution

- **PASS** — **Engineering input exists** (pooled requirement count ≥ 1).  Downstream
  engineering may begin; CP1-0001 emits **no finding**.
- **FAIL** — **No engineering input exists** (zero requirements across all three
  governed collections).  Downstream engineering cannot begin; CP1-0001 emits **one**
  `CP1Finding` contributing `FAIL`.
- **WARN** — **not used.** Availability is binary; there is no policy-free middle
  ground.  `WARN` is **reserved** for CP1-0001 (a per-domain "partial coverage" WARN
  would require a governed coverage policy — out of scope, D6).

### D5. Finding & recommendation ownership

CP1-0001 emits **at most one** `CP1Finding` (single atomic concern → single finding).
The finding's `criterion_id` is `CP1-0001`; its `recommendation` text is **owned by
the criterion** and states the resolving action — conceptually:

> "The validated response contains no engineering requirements.  Add at least one
> functional, security, or quality requirement before downstream engineering can
> begin."

CP1-0001 **never** aggregates — the overall verdict is the engine's (ADR-0012 §8).

### D6. Scope boundary against Validation (the governed boundary)

**Validation owns *artifact correctness*; CP1 owns *engineering readiness*.**  These
answer two different questions:

| | Validation Platform | CP1-0001 |
| - | ------------------- | -------- |
| Question | **"Is the artifact valid?"** | **"Can engineering begin?"** |
| Domain | Artifact correctness (Transport…Business Rule) | Engineering readiness (downstream fitness) |
| Basis | Structural/content/policy correctness of the response | The **deterministic availability floor**: ≥ 1 engineering input |
| Verdict on empty-but-valid set | **PASS** (a well-formed empty response is a correct artifact) | **FAIL** (no engineering input → engineering cannot begin) |

The **deterministic availability floor belongs to CP1**, not to Validation, because it
answers *"Can engineering begin?"* — a downstream-consumability question — rather than
*"Is the artifact valid?"*.  Validation's Business Rule layer ownership of
**coverage-against-policy** and **minimum-`N`** (`BUSINESS-0001`/`BUSINESS-0003`,
Reserved · Deferred, ADR-0006) is **unchanged** and remains distinct: it presupposes a
*governed completeness policy*; CP1-0001 presupposes only the *definitional floor of
engineering input*.  Because the two produce **different verdicts on the same input**
and rest on different bases, they are **distinct concerns, not an overlap**.  This
boundary is governed here explicitly (cf. ADR-0004 Schema↔Structural, ADR-0007
`CONTENT-0002` scope) — **not silently resolved**.

## Questions this ADR resolves

| # | Question | Resolution |
| - | -------- | ---------- |
| 3 | Single concern? | **Engineering Input Availability** — one concern (D1). |
| 4 | Why first? | It is the **only** deterministic, non-semantic, `CP1Input`-only readiness concern over bare strings, and the **precondition** of every other (there is nothing to judge for testability/coverage if there is no engineering input). |
| 5 | Deterministic? | **Yes** — pooled requirement count ≥ 1 (D2). |
| 6–10 | Semantic / NLP / LLM / business / domain? | **No** to all — pure counting; the ≥ 1 floor is a logical precondition, not domain/business policy. |
| 11 | `CP1Input` only? | **Yes** (D3). |
| 12 | New canonical models? | **No.** |
| 13 | `CP1Input` change? | **No.** |
| 14 | `CP1Result` change? | **No.** |
| 15–19 | Framework / engine / composition / PlatformContext / CLI change? | **No** to all. |
| 20 | Overlap Validation? | **No** — distinct question ("can engineering begin?" vs "is the artifact valid?"); governed boundary (D6). |
| 21 | Overlap Feature Generation? | **No** — CP1-0001 gates *into* Feature Generation; it synthesises nothing. |
| 22 | Overlap Test Generation? | **No.** |
| 23 | PASS/WARN/FAIL independently? | PASS + FAIL used; **WARN reserved** (availability is binary, D4). |
| 24 | One finding or many? | **One** (D5). |
| 25 | Thresholds? | One — the **≥ 1 availability floor**, **governed here**; any `N > 1` is out of scope (D6). |
| 26 | Future criteria depend on CP1-0001? | **No runtime dependency** — criteria are independent (ADR-0012 §5); CP1-0001 is conceptually the floor but no criterion reads its finding. |
| 27 | Future criteria independent? | **Yes** — criterion independence (ADR-0012 §5); the engine aggregates all contributions. |
| 28 | Mutate `CP1Input`? | **No** — criteria are non-mutating (framework contract). |
| 29 | Own aggregation? | **No** — the engine owns aggregation (ADR-0012 §8). |

## Alternatives Considered

- **A1 — A semantic first criterion (testability / actionability / atomicity /
  unambiguity).** **Rejected (STOP):** each requires understanding requirement
  *meaning* over bare strings → semantic/NLP/LLM (Q6–Q8).  Reserved for a future
  schema-enrichment + semantic-reasoning ADR (cf. ADR-0006/0009/0010).
- **A2 — A minimum-`N` or per-domain coverage criterion (`N > 1`, or ≥ 1 per
  collection).** **Rejected:** introduces an **ungoverned policy** (which `N`? which
  domains required?) → invented policy (Q25); and coverage-against-policy is the
  Validation Business Rule layer's claimed ownership (ADR-0006).  Deferred to a future
  **governed coverage policy**.
- **A3 — A string-length / "too short" heuristic.** **Rejected:** a length threshold
  is an invented heuristic proxy for semantic quality (Q25) — not governed.
- **A4 — Defer CP1-0001 entirely (Reserved · Deferred), like `REASONING-0001/0003`.**
  **Rejected:** unlike those, CP1-0001 **has** a governed deterministic basis (count
  ≥ 1) and fills a **real gap Validation does not cover** (the empty-but-valid set).
  Deferring would leave CP1 with no deterministic criterion when one is available.
- **A5 — Treat availability as a Validation Business Rule (`BUSINESS-0003`) instead.**
  **Rejected:** validation would **PASS** the empty-but-valid set (a correct artifact);
  the availability floor answers a **different question** ("can engineering begin?")
  and belongs to the downstream readiness domain (ADR-0011 §D1).  The boundary is
  governed in D6.

## Ownership verification

| Artifact | Effect of this ADR |
| -------- | ------------------ |
| `CP1Input` / `CP1Result` / `CP1Finding` / `CP1FrameworkMetadata` | **Unchanged.** CP1-0001 reads the normalized structure and emits a `CP1Finding`; no shape change. |
| CP1 Framework / Engine / Composition Root / Seam | **Unchanged.** CP1-0001 is a future criterion registered through the governed process; no infrastructure change. |
| Validation Platform (incl. `BUSINESS-0001/0003`) | **Unchanged.** The Business Rule layer keeps its Reserved · Deferred coverage/minimum ownership; D6 draws the boundary without touching it. |
| Engineering Readiness Criteria Catalog (CAP-061) | **Populated** with the CP1-0001 entry (governance metadata; no implementation). |

## Consequences

- ✅ CP1 gains its **first deterministic, governed criterion**, addressing a real gap
  (valid-but-empty requirement set) that Validation does not fail.
- ✅ Determinism, `CP1Input`-only, and single-concern are preserved; no semantics,
  no invented policy, no canonical-model/framework/engine/seam/composition change.
- ✅ The CP1 ↔ Validation boundary is governed **explicitly** (D6), not silently, and
  strengthened by the "Can engineering begin?" vs "Is the artifact valid?" framing.
- ✅ **Accepted.** CP1-0001's catalog lifecycle is **Approved** (implementable);
  implementation is a **separate future milestone** (register the criterion in the
  composition root; add the criterion class + tests).
- ✅ **Governance registration applied:** this ADR is registered **Accepted** in the
  Architecture Freeze Index §6; the Criteria Catalog §9 records CP1-0001 **Approved**;
  the Platform Capability Matrix / Coverage Dashboard `CAP-061` reflect one Approved
  (not-yet-implemented) criterion and the **Criteria Catalog Version 1.1.0**.

## Version impact

Introduces the **first criterion** into the Criteria Catalog.  It advances **no**
existing version and changes **no** frozen contract or canonical model.  On the
catalog's own discipline (§11), the **Criteria Catalog Version** advances additively
**1.0.0 → 1.1.0** (zero → one criterion); the CP1-0001 **Criterion Version** is
`1.0.0`.

## Scope note

This ADR governs **only what CP1-0001 is** — its single concern, deterministic basis,
inputs, verdicts, finding/recommendation ownership, and its boundary against
Validation.  It does **not** implement CP1-0001, create a criterion class, register it
in the composition root, create tests, or modify any canonical model, framework,
engine, composition root, seam, `CP1Input`/`CP1Result`/`CP1Finding`, PlatformContext,
CLI, or any existing ADR.  Implementation is a future milestone.
