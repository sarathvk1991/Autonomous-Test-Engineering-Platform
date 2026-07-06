# Engineering Readiness Criteria Catalog

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Criteria Catalog    |
| Status               | Approved — foundational — established by **ADR-0012 (Accepted)**; capability **CAP-061**; **structure only, zero criteria defined** |
| Scope                | Every engineering-readiness criterion that may exist in the CP1 Validation Engine |
| Governs              | Criterion identity, number allocation, metadata, lifecycle, classification, ordering, severity contribution, verdict contribution, catalog version, profiles, independence, versioning, governance |
| Depends on           | ADR-0011 (CP1 Validation Engine & Validation → CP1 Handoff) · ADR-0012 (this catalog's establishment) · CP1Input / CP1Result (identified, ADR-0011) |
| Distinct from        | **Validation Rule Catalog** — that catalog governs *artifact-correctness* rules for the frozen Validation Platform; this catalog governs *engineering-readiness* criteria for CP1. See §12. |
| Implementation-bound | No — valid regardless of language, framework, persistence, or AI provider |

> **Architectural Decision (ADR-0012)**
> **Engineering-readiness criteria are governed by architecture, never invented
> during implementation.** A criterion does not come into existence because an
> engineer wrote one, or because the generation prompt aspires to it; it comes
> into existence because this catalog defines it — its identity, its single
> responsibility, its severity/verdict contribution, and its metadata. Every CP1
> implementation, in any technology, must conform to this catalog. It is the
> single source of truth for every readiness criterion that will ever exist.

> **Empty by design.** This catalog is established with **zero criteria**. Per
> ADR-0012, defining any concrete criterion, threshold, heuristic, or PASS/FAIL
> policy is **out of scope** of the establishing decision; criteria are populated
> **additively through the governed process in §11** by subsequent, dedicated
> governance. Until at least one criterion is defined here, **no CP1 criterion may
> be implemented** (ADR-0011 gate).

---

## 1. Purpose

### 1.1 Why this catalog exists

CP1 is the engineering-readiness gate between the Validation Platform and Feature
Generation (ADR-0011). That gate is composed of **engineering-readiness
criteria** — each one a single, atomic judgement of whether validated
requirements are fit to engineer software from. If criteria were created ad hoc
during implementation, CP1 would suffer the same failures the Validation Rule
Catalog exists to prevent: identity drift, responsibility overlap, ungoverned
growth, and — most dangerously for CP1 — **non-deterministic, invented policy**
(a "readiness" heuristic differing per implementation).

This catalog defines the **complete, governed set of readiness criteria** — their
identities, responsibilities, severity and verdict contribution, and evolution
rules — so that every criterion CP1 will ever apply is accounted for by
architecture before it is built.

### 1.2 What this document is **not**

| This document is NOT | Because |
| -------------------- | ------- |
| An implementation guide | It defines *what* each criterion is responsible for, never *how* one is built. |
| A coding specification | No algorithms, data structures, thresholds, or interfaces are described. |
| A framework specification | Engine orchestration (Criterion / Registry / Pipeline) is governed by ADR-0011, not here. |
| A PASS/FAIL policy | It contributes to no verdict directly; severity/verdict *contribution* is a per-criterion property defined when a criterion is added (§8). |
| A source of criteria today | It is deliberately **empty of criteria** at establishment (§9). |

> **Principle**
> Every criterion in this catalog is described by its **responsibility and
> identity**, never by its mechanism or its thresholds. A criterion's
> responsibility is a stable architectural fact; its mechanism and any numeric
> policy are replaceable implementation detail governed only when the criterion is
> defined.

---

## 2. Scope

### 2.1 In scope

| In scope | Description |
| -------- | ----------- |
| **Criterion identities** | The stable identifier standard every criterion carries (§4). |
| **Criterion responsibilities** | The one readiness concern each criterion judges and nothing more (§3). |
| **Criterion metadata** | The conceptual descriptor a criterion must define before it exists (§6). |
| **Lifecycle** | The governed states a criterion moves through (§7). |
| **Severity & verdict contribution** | How a criterion's finding maps to severity and to the CP1 `PASS/FAIL/WARN` verdict (§8). |
| **Ordering & independence** | Deterministic catalog ordering; outcome-invariant execution (§5). |
| **Classification & profiles** | Criterion role and named criterion subsets (§10). |
| **Evolution** | Additive growth, versioning, deprecation, reservation, governance (§11). |

### 2.2 Out of scope

| Out of scope | Owned by |
| ------------ | -------- |
| **Any concrete criterion** | A future governed criterion-definition step (§11); **none defined here**. |
| **Thresholds / heuristics / algorithms** | Implementation detail, defined (as *policy*, not mechanism) only when a criterion is catalogued; never described here. |
| **Criterion mechanism** | The future CP1 criterion implementations, governed by this catalog but not described here. |
| **Engine behaviour** | The CP1 engine — Criterion contract, Registry, Pipeline (ADR-0011). |
| **Canonical models** | `CP1Input` / `CP1Result` / `CP1Finding` (identified by ADR-0011). |
| **Artifact-correctness concerns** | The **Validation Rule Catalog** (frozen Validation Platform). A readiness criterion never re-validates structure/schema/syntax/etc. (§12). |

---

## 3. Criterion Philosophy

### 3.1 What an Engineering Readiness Criterion is

> **Definition**
> An **Engineering Readiness Criterion** is a single, atomic, deterministic
> statement of one concern that **validated** requirements must satisfy to be fit
> for downstream software engineering. It reads the validated requirements
> (through `CP1Input`) and produces findings; it never re-validates artifact
> correctness, never repairs requirements, and never generates features.

### 3.2 One criterion, one responsibility

> **Principle**
> **Every criterion judges exactly one readiness concern — and only one.** A
> criterion that judges two things is two criteria. A concern judged by two
> criteria is a duplicated responsibility and a defect in the catalog.

This mirrors, in the readiness domain, the "one rule, one responsibility" law of
the Validation Rule Catalog (§3.1 there). The qualities it protects —
determinism, parallelism, maintainability, traceability, additive growth — are
identical.

### 3.3 What belongs inside one criterion

| Belongs | Does **not** belong |
| ------- | ------------------- |
| Exactly one readiness concern. | Two or more concerns ("and" in the responsibility). |
| Identity, name, purpose, ownership. | Any algorithm, threshold value, or data structure. |
| Its severity and verdict contribution (§8). | The CP1 verdict itself (owned by the engine's aggregation, ADR-0011). |
| Deterministic judgement over validated requirements. | Non-deterministic judgement (LLM/embedding/NLP heuristic). |
| A worked passing/failing illustration (prose). | Artifact-correctness re-checks (owned by Validation rules, §12). |
| — | Requirement rewriting, repair, or feature synthesis. |

---

## 4. Criterion Identity Standard

### 4.1 Criterion ID format

Every criterion carries a stable **Criterion ID** in the form:

```text
   CP1-NNNN
   │    │
   │    └── a zero-padded sequential number, unique across the catalog
   └── the fixed CP1 namespace token
```

Examples: `CP1-0001`, `CP1-0002`, `CP1-0100`.

> **Architectural Decision (ADR-0012) — a flat `CP1-NNNN` namespace, not a
> layered one.** The Validation Rule Catalog uses `<LAYER>-NNNN` because the
> validation *pipeline* has nine architecture-mandated layers (Transport →
> Business Rule) reflecting a foundational→semantic progression. **CP1 has no such
> governed layer taxonomy**, and inventing one now would invent policy — forbidden
> (ADR-0005/0006 discipline). Engineering readiness is therefore a **single flat
> namespace**. Should a governed readiness taxonomy ever emerge, a dimension token
> may be introduced **additively via ADR**; it is not presumed here.

### 4.2 Identity stability

> **Principle**
> **Criterion IDs never change. Criterion names may evolve.** The ID is the
> permanent, machine- and audit-facing identity that appears in `CP1Result`
> records; it is immutable for the life of the platform. The name is a
> human-readable label that may be refined without affecting identity.

- A Criterion ID, once published, is fixed forever — even if the criterion is
  deprecated or retired.
- A retired Criterion ID is **never** reassigned to a different concern.
- Renaming a criterion does not constitute a new criterion.

### 4.3 Reserved number ranges

The sequential number `NNNN` is allocated from **reserved ranges** aligned to
classification (§10), mirroring the Validation Rule Catalog §4.4 discipline so a
Criterion ID alone signals its tier.

| Number range | Reserved for |
| ------------ | ------------ |
| `0001`–`0099` | **Core** criteria |
| `0100`–`0199` | **Extended** criteria |
| `0200`–`0299` | **Organization** criteria |
| `0300`–`0899` | **Future expansion** (unallocated) |
| `0900`–`0999` | **Reserved** (special governance use) |

- A new criterion takes the **next free number** in the range matching its
  classification.
- Numbers are **never reused**; a retired criterion's number is retired with it.
- **Gaps are intentional** and are never "filled in" for tidiness.

---

## 5. Ordering and Independence

- **Catalog ordering exists** and is deterministic — criteria are ordered by
  Criterion ID. This gives every `CP1Result` a stable, reproducible presentation
  and audit order.
- **Execution outcome does not depend on order.** Every criterion is
  **deterministic, stateless, idempotent, independent, parallelizable, and
  non-mutating** — the six independence properties of Validation Rule Catalog §16.
  Any permutation of criteria yields the identical set of findings.
- **Registration preserves catalog order.** The CP1 Registry (ADR-0011) registers
  criteria in catalog order and seals; the CP1 Pipeline never re-sorts.

> **Principle**
> **A criterion depends on no other criterion.** It never reads another's finding,
> assumes another ran, or sequences another. CP1 recognises **no** fail-fast layer
> halting (unlike the validation pipeline's foundational→semantic progression);
> all criteria are peers. Ordering is for reproducibility, not for outcome.

---

## 6. Criterion Metadata Standard

Every criterion is described by a conceptual metadata record — the architectural
description of a criterion, distinct from any implementation.

| Field | Meaning |
| ----- | ------- |
| **Criterion ID** | The stable, immutable identifier (`CP1-NNNN`, §4). |
| **Criterion Name** | The human-readable, concern-describing name. May evolve. |
| **Purpose** | The single readiness concern it judges, in one sentence (§3). |
| **Classification** | Core, Extended, Organization, or Experimental (§10). |
| **Stability** | Experimental, Stable, Mature, Frozen (architecture's confidence). |
| **Severity Contribution** | The severity its findings carry (§8). |
| **Verdict Contribution** | How that severity maps to `PASS/FAIL/WARN` (§8). |
| **Lifecycle Status** | Draft, Approved, Implemented, Deprecated, Retired, or the Reserved · Deferred disposition (§7). |
| **Owner** | The architectural owner accountable for the criterion's definition. |
| **Worked Example** | A concrete passing and failing illustration (prose). |
| **Architecture Reference** | The governing section of this catalog and the ADR that added the criterion. |

> **Architectural Decision**
> A criterion is not catalogued until **every** metadata field is defined.
> Incomplete metadata means the criterion does not yet exist as far as CP1 is
> concerned. Metadata completeness is a precondition of criterion existence.

---

## 7. Criterion Lifecycle

```text
   Draft ──approve──► Approved ──implement──► Implemented ──supersede──► Deprecated ──retire──► Retired
     │                                                                                   (ID frozen forever)
     └─ reject (never assigned an ID) ─► discarded

   Reserved · Deferred ─ an Approved identity with no governed deterministic mechanism yet
                         (the ADR-0005/0006/0009/0010 disposition), activated by a future ADR.
```

| State | Meaning |
| ----- | ------- |
| **Draft** | Proposed and under architectural review; no committed identity. |
| **Approved** | Accepted into the catalog and assigned a permanent Criterion ID; not yet implemented. |
| **Implemented** | A conforming implementation exists and participates in CP1 runs. |
| **Reserved · Deferred** | Approved identity whose governed deterministic mechanism does not yet exist; implementation intentionally deferred (ID frozen, never reused). |
| **Deprecated** | Still honoured but slated for removal; a successor is preferred. |
| **Retired** | No longer participates; ID frozen forever and never reassigned. |

> **Principle**
> A criterion's **identity outlives its activity**. This is the same discipline
> the Validation Rule Catalog applies (§7 there) and that ADR-0005/0006/0009/0010
> used to reserve validation rules without inventing a mechanism.

---

## 8. Severity and Verdict Contribution

Each criterion's finding carries a **severity**, and each severity **contributes**
to the CP1 verdict (`PASS/FAIL/WARN`, `shared.enums.base.ValidationVerdict`). The
mapping is a **per-criterion property defined when the criterion is added** — it
is **not** defined here, and this catalog sets **no** thresholds or PASS/FAIL
policy (out of scope, §2.2).

- The CP1 verdict vocabulary (`PASS/FAIL/WARN`) is **deliberately distinct** from
  the Validation Platform's four-state verdict; the two are never conflated
  (ADR-0011; validation README design decisions).
- The **aggregation** of criterion findings into the single CP1 verdict is owned
  by the CP1 engine (ADR-0011), not by any criterion. A criterion contributes a
  severity; it never decides the overall verdict.

> This section fixes **that** severity and verdict contribution are governed
> per-criterion; it does not fix **what** any contribution is. Defining a concrete
> severity/verdict mapping is part of defining a criterion (§11).

---

## 9. Initial Criteria Catalog

> **The initial catalog is empty.** Zero engineering-readiness criteria are
> defined at establishment (ADR-0012 scope). This section is the reserved home
> into which criteria are added **additively and additively only** through §11.

| Criterion ID | Name | Single readiness concern | Lifecycle |
| ------------ | ---- | ------------------------ | --------- |
| — | *(none defined)* | *(none defined)* | — |

---

## 10. Classification and Profiles

**Classification** states a criterion's role, orthogonal to lifecycle and
stability (mirrors Validation Rule Catalog §10).

| Classification | Meaning | Number range (§4.3) | Default availability |
| -------------- | ------- | ------------------- | -------------------- |
| **Core** | Mandatory readiness criteria; the irreducible baseline. | `0001`–`0099` | Always enabled. |
| **Extended** | Optional criteria adding depth beyond the baseline. | `0100`–`0199` | Enabled by profile. |
| **Organization** | Customer/organization-specific criteria. | `0200`–`0299` | Enabled by profile. |
| **Experimental** | Research-only criteria under evaluation. | (allocated on promotion) | Never enabled in standard operation. |

**CP1 Profiles** are named criterion subsets (the readiness analogue of Validation
Profiles), selecting which criteria run without any criterion knowing the
profile. Concrete profiles are **identified as a future extension point, not
defined here**.

---

## 11. Evolution and Governance

- **Additive growth only.** New readiness concerns become **new criteria** with
  **new IDs** from the reserved ranges (§4.3); existing criteria are never
  overloaded to absorb them.
- **Governed addition.** A criterion is added only through a dedicated governance
  step (a criterion-definition ADR, or this catalog's governed approval process
  established by ADR-0012). Each added criterion supplies complete metadata (§6)
  including its severity/verdict contribution (§8).
- **Versioning.** A **Criteria Catalog Version** governs the catalog as a whole; a
  **Criterion Version** governs each criterion's own definition — independent
  axes, mirroring Validation Rule Catalog §20. The catalog is established at
  Version `1.0.0` **with zero criteria**.
- **Deprecation & reservation.** Criteria are deprecated/retired or held as
  Reserved · Deferred via §7; IDs are frozen forever.
- **No invention.** No criterion, threshold, heuristic, or PASS/FAIL policy is
  ever introduced in code ahead of its catalog definition.

---

## 12. Relationship to the Validation Rule Catalog

This catalog and the Validation Rule Catalog share **governance discipline** but
govern **different domains, namespaces, and verdicts**. They are never merged: a
readiness concern is never a validation rule, and vice versa.

| Aspect | Validation Rule Catalog | Engineering Readiness Criteria Catalog (this) |
| ------ | ----------------------- | --------------------------------------------- |
| Judges | Artifact correctness of the AI **response** | Engineering **readiness** of validated requirements |
| Verdict vocabulary | `PASSED / PASSED_WITH_WARNINGS / FAILED / BLOCKED` | `PASS / FAIL / WARN` |
| Identity scheme | `<LAYER>-NNNN` (nine ordered layers) | `CP1-NNNN` (flat, no layers) |
| Pipeline position | Between AI generation and CP1 | Between the Validation Platform and Feature Generation |
| Consumes | `ValidationInput` (`AnalysisResult` + `NormalizationResult`) | `CP1Input` (identified, ADR-0011) |
| Ordering semantics | Layered fail-fast (foundational may halt) | Flat peers; order is reproducibility only (§5) |
| Freeze state | Frozen (v1.0.0) | New; Draft; not frozen |
| Governance model | Additive-via-ADR, one-concern, deterministic | **Identical discipline** |

> **Principle**
> CP1 **trusts** the Validation Platform's verdict and never re-validates artifact
> correctness. A criterion that finds itself re-checking structure, schema,
> syntax, encoding, or transport is **misplaced** — that concern is already owned
> by a Validation rule and must not be duplicated here.

---

## 13. Relationship to the CP1 Engine (ADR-0011)

This catalog defines **what criteria exist**; the CP1 engine **executes** them:

```text
   Engineering Readiness Criteria Catalog   ◄── THIS DOCUMENT (governed criteria set)
            │ defines each criterion's identity, concern, severity/verdict contribution
            ▼
   CP1 Criterion contract → CP1 Registry → CP1 Pipeline → CP1Result   (ADR-0011 pattern)
            │ executes conforming criterion implementations governed by this catalog
            ▼
   CP1 Verdict (PASS / FAIL / WARN)   →   Feature Generation | halt + report
```

The catalog never describes execution; the engine never invents criteria — the
exact division of labour the Validation Rule Catalog holds with the Validation
Framework.
