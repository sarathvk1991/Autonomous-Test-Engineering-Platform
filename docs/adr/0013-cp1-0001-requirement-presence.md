# ADR 0013 — CP1-0001 (RequirementPresenceCriterion): the First Engineering Readiness Criterion

- **Status:** Proposed
- **Date:** 2026-07-06

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
   `CONTENT-0001` vacuous; no policy to fail).  It is a **correct artifact with zero
   requirements to engineer from** — the archetypal *valid-but-not-engineering-ready*
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

Govern **CP1-0001 — `RequirementPresenceCriterion`**: *the validated response must
carry **at least one** requirement statement to engineer from.*

### D1. Single concern

CP1-0001 owns **exactly one** concern: **requirement presence** — the irreducible
buildability floor.  It does **not** judge requirement *quality, testability,
actionability, coverage, or count beyond one*; those are separate concerns.

### D2. Deterministic evaluation basis

The **total number of elements across the three governed requirement collections**
(`functional_requirements` ∪ `security_requirements` ∪ `quality_requirements`) in the
normalized structure is **≥ 1**.  This is pure element counting — deterministic,
order-independent, and free of semantics.  The collections are **pooled** (union):
CP1-0001 asks *"is there anything to build?"*, not *"which domains are covered?"*
(pooling here is a different concern from `CONTENT-0002`'s within-collection scope —
no conflict with ADR-0007).

### D3. Required inputs

**`CP1Input` only** — the normalized structure reached through
`cp1_input.normalization_result.parsed_response.normalized_structure`.  CP1-0001 runs
only on responses the **Validation → CP1 seam** admitted (verdict `PASSED` /
`PASSED_WITH_WARNINGS`, ADR-0011 §D5), which guarantees a **`NORMALIZED`** structure
is present.  No other input, no additional canonical model.

### D4. Verdict contribution

- **PASS** — ≥ 1 requirement present (pooled).  The response is buildable; CP1-0001
  emits **no finding**.
- **FAIL** — **zero** requirements across all three governed collections.  Nothing can
  be engineered; CP1-0001 emits **one** `CP1Finding` contributing `FAIL`.
- **WARN** — **not used.** Presence is binary; there is no policy-free middle ground.
  `WARN` is **reserved** for CP1-0001 (a per-domain "partial coverage" WARN would
  require a governed coverage policy — out of scope, D6).

### D5. Finding & recommendation ownership

CP1-0001 emits **at most one** `CP1Finding` (single atomic concern → single finding).
The finding's `criterion_id` is `CP1-0001`; its `recommendation` text is **owned by
the criterion** and states the resolving action (the response carries no requirements
to engineer from).  CP1-0001 **never** aggregates — the overall verdict is the
engine's (ADR-0012 §8).

### D6. Scope boundary against Validation (the governed boundary)

CP1-0001 owns **presence (the ≥ 1 buildability floor)**.  It does **not** own
**coverage-against-policy** or **minimum-`N`** — those remain the Validation Business
Rule layer's `BUSINESS-0001`/`BUSINESS-0003` (Reserved · Deferred, ADR-0006), unchanged
by this ADR.  The boundary is drawn by *question and verdict*, not by *mechanism*:

| | Validation (Business Rule layer) | CP1-0001 |
| - | -------------------------------- | -------- |
| Question | Does the response meet a **declared completeness/coverage policy**? | Is there **anything to engineer** from? |
| Basis | A **governed policy** (does not exist → Deferred) | The **policy-free floor**: ≥ 1 |
| Verdict on empty-but-valid set | **PASS** (no policy to fail) | **FAIL** (nothing to build) |

Because the two produce **different verdicts on the same input** and rest on
different bases (a governed policy vs the definitional floor), they are **distinct
concerns, not an overlap**.  This boundary is governed here explicitly (cf. ADR-0004
Schema↔Structural, ADR-0007 `CONTENT-0002` scope) — **not silently resolved**.

## Questions this ADR resolves

| # | Question | Resolution |
| - | -------- | ---------- |
| 3 | Single concern? | **Requirement presence** — one concern (D1). |
| 4 | Why first? | It is the **only** deterministic, non-semantic, `CP1Input`-only readiness concern over bare strings, and the **precondition** of every other (there is nothing to judge for testability/coverage if there are zero requirements). |
| 5 | Deterministic? | **Yes** — element count ≥ 1 (D2). |
| 6–10 | Semantic / NLP / LLM / business / domain? | **No** to all — pure counting; the ≥ 1 floor is a logical precondition, not domain/business policy. |
| 11 | `CP1Input` only? | **Yes** (D3). |
| 12 | New canonical models? | **No.** |
| 13 | `CP1Input` change? | **No.** |
| 14 | `CP1Result` change? | **No.** |
| 15–19 | Framework / engine / composition / PlatformContext / CLI change? | **No** to all. |
| 20 | Overlap Validation? | **No** — distinct concern; governed boundary (D6). |
| 21 | Overlap Feature Generation? | **No** — CP1-0001 gates *into* Feature Generation; it synthesises nothing. |
| 22 | Overlap Test Generation? | **No.** |
| 23 | PASS/WARN/FAIL independently? | PASS + FAIL used; **WARN reserved** (presence is binary, D4). |
| 24 | One finding or many? | **One** (D5). |
| 25 | Thresholds? | One — the **≥ 1 buildability floor**, **governed here**; any `N > 1` is out of scope (D6). |
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
- **A5 — Treat presence as a Validation Business Rule (`BUSINESS-0003`) instead.**
  **Rejected:** validation would **PASS** the empty-but-valid set (no governed policy);
  presence-for-engineering produces a **different verdict** and belongs to the
  downstream readiness domain (ADR-0011 §D1).  The boundary is governed in D6.

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
- ✅ The CP1 ↔ Validation boundary is governed **explicitly** (D6), not silently.
- ⚠️ **Status is Proposed.** On acceptance, CP1-0001's catalog lifecycle advances
  Draft → Approved (implementable); implementation is a **separate future milestone**
  (register the criterion in the composition root; add the criterion class + tests).
- ⚠️ **Governance registration:** this ADR is registered in the Architecture Freeze
  Index §6 and the catalog §9 is populated.  The Platform Capability Matrix /
  Coverage Dashboard `CAP-061` "zero criteria" wording is updated **on acceptance**
  (a separate, ratified step — not by this ADR).

## Version impact

Introduces the **first criterion** into the Criteria Catalog.  It advances **no**
existing version and changes **no** frozen contract or canonical model.  On the
catalog's own discipline (§11), the **Criteria Catalog Version** advances additively
(1.0.0 → 1.1.0, zero → one criterion) **on acceptance**; the CP1-0001 **Criterion
Version** is `1.0.0`.

## Scope note

This ADR governs **only what CP1-0001 is** — its single concern, deterministic basis,
inputs, verdicts, finding/recommendation ownership, and its boundary against
Validation.  It does **not** implement CP1-0001, create a criterion class, register it
in the composition root, create tests, or modify any canonical model, framework,
engine, composition root, seam, `CP1Input`/`CP1Result`/`CP1Finding`, PlatformContext,
CLI, or any existing ADR.  Implementation is a future milestone contingent on
acceptance.
