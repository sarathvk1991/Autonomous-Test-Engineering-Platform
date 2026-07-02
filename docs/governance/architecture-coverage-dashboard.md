# Architecture Coverage Dashboard

| Attribute | Value |
| --------- | ----- |
| Document type | Engineering Governance / Coverage Dashboard |
| Status | Living document — governance artifact |
| Scope | Lifecycle-stage coverage and implementation readiness for every capability |
| Source of truth | The repository, via the Platform Capability Matrix |
| Derived from | Platform Capability Matrix (shared Capability IDs) · Architecture Freeze Index |

> This is a **coverage dashboard**, not another capability matrix. It reduces each
> capability to *how far through the lifecycle it has travelled* and *whether it is
> ready to proceed*, so leadership can see platform coverage at a glance. Capability
> names, versions, purposes, and dependencies live in the Platform Capability
> Matrix; **Capability IDs are shared** between the two documents.
>
> **Reference direction.** This dashboard is a **downstream, derived view**: the
> Platform Capability Matrix and the Architecture Freeze Index link *to* it; it does
> not link back (it names them in plain text), so the governance references remain
> one-directional and acyclic.

---

## 1. Purpose

Show, in one view, **how much of the platform is Architected, Framework-complete,
Canonical-Models-complete, Implemented, Tested, and Frozen** — and, per capability,
its **Implementation Readiness**. It turns the detailed capability matrix into an
executive coverage picture and a readiness signal for planning the next milestone.

## 2. Audience

| Audience | How this dashboard serves them |
| -------- | ------------------------------ |
| **Architects** | See where architecture is complete but implementation has not begun — and where a freeze still needs declaring. |
| **Engineering Leads** | A single readiness signal: what is Ready to build now, what is Blocked, what is In Progress, what is Planned. |
| **Developers** | Identify the unblocked next task and the coverage gap it closes. |
| **Reviewers / Contributors** | Confirm a capability's claimed coverage against the shared Capability ID in the matrix. |

## 3. Coverage philosophy

- The dashboard measures **coverage of outstanding work**, using only `✓`, `◑`,
  `✗`:
  - **`✓`** — the stage is **satisfied**: either complete, **or** not applicable to
    this capability (no outstanding work). *Not-applicable stages are shown `✓`
    because they impose no remaining work* — consistent with the matrix's `n/a`.
  - **`◑`** — the stage is **partially** satisfied (work started, not complete).
  - **`✗`** — the stage is **required but absent** (outstanding work remains here).
- Every cell is derived from the Platform Capability Matrix; this document
  introduces **no new judgement** — it re-projects the matrix.
- **Implementation Readiness** is one of `Ready`, `In Progress`, `Blocked`,
  `Planned`, from repository evidence only:
  - **Ready** — complete and stable, **or** all prerequisites are satisfied and the
    capability is ready to implement now.
  - **In Progress** — partially implemented.
  - **Blocked** — an immediate prerequisite capability is not yet available.
  - **Planned** — scheduled for later in the execution order; prerequisites not yet
    all in place.

## 4. Coverage Table

Legend: `✓` satisfied (complete or not applicable) · `◑` partial · `✗` outstanding.

| ID | Capability | Arch | Framework | Canonical Models | Impl | Testing | Frozen | Implementation Readiness |
| -- | ---------- | :--: | :-------: | :--------------: | :--: | :-----: | :----: | ------------------------ |
| CAP-001 | Connector Framework & Registry | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-002 | Mappers | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-003 | Consolidation Engine | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-010 | Reasoning Contract | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-011 | Prompt Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-012 | Provider (LLM) Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-013 | Gemini Provider | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-014 | Requirement Analysis Service | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-020 | Execution Package | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-021 | Execution History | ✓ | ✓ | ✓ | ✓ | ◑ | ✗ | Ready |
| CAP-022 | Manifest | ✓ | ✓ | ✓ | ✓ | ◑ | ✗ | Ready |
| CAP-023 | Baseline Metrics | ✓ | ✓ | ✓ | ✓ | ◑ | ✗ | Ready |
| CAP-024 | Platform CLI | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-030 | Response Normalization (subsystem) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Ready |
| CAP-031 | ParsedResponse | ✓ | ✓ | ✓ | ✓ | ✓ | ◑ | Ready |
| CAP-032 | ResponseNormalizer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Ready |
| CAP-040 | Validation Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Ready |
| CAP-041 | Response Validator | ✓ | ✓ | ✓ | ◑ | ✓ | ✗ | In Progress |
| CAP-042 | Transport Layer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Ready |
| CAP-043 | Syntax Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Ready |
| CAP-044 | Schema Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-045 | Structural Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-046 | Content Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-047 | Evidence Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-048 | Traceability Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-049 | Reasoning Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-050 | Business Rule Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-051 | ValidationInput (canonical input) | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-060 | CP1 Validator | ◑ | ✓ | ✓ | ◑ | ✗ | ✗ | In Progress |

## 5. Overall coverage summary

Objective counts across all **29** capabilities (no percentages estimated). For
each stage: satisfied `✓` / partial `◑` / outstanding `✗`.

| Stage | `✓` satisfied | `◑` partial | `✗` outstanding | Outstanding capabilities |
| ----- | :-----------: | :---------: | :-------------: | ------------------------ |
| **Architecture** | 28 | 1 | 0 | Partial: CAP-060. |
| **Framework** | 29 | 0 | 0 | — (includes not-applicable as satisfied). |
| **Canonical Models** | 29 | 0 | 0 | — (includes not-applicable as satisfied). |
| **Implementation** | 19 | 2 | 8 | `✗`: CAP-043…050. Partial: CAP-041, CAP-060. |
| **Testing** | 17 | 3 | 9 | `✗`: CAP-043…050, CAP-060. Partial: CAP-021, CAP-022, CAP-023. |
| **Frozen** | 4 | 1 | 24 | `✓`: CAP-030, CAP-032, CAP-040, CAP-042. Partial: CAP-031. |

**Implementation Readiness distribution** (29 total): **Ready 20** · **In Progress
2** (CAP-041, CAP-060) · **Blocked 0** · **Planned 7** (CAP-044…050).

## 6. Remaining architecture work

Architecture coverage is effectively complete; the outstanding items are narrow and
repository-evidenced:

- **CAP-060 CP1 Validator** — architecture is **partial** (`◑`): no dedicated
  architecture document; it appears only in the Architecture Overview pipeline and
  the platform catalogue.
- **Documentation gap (not a capability gap)** — CAP-020 Execution Package,
  CAP-024 Platform CLI, and CAP-011 Prompt Framework are implemented and marked
  architected, but have **no dedicated architecture document** (governed by
  `platform_metadata.py` + the Architecture Overview). See the
  Architecture Freeze Index notes.

No other capability is missing architecture: every remaining `✗` is an
**implementation/testing/freeze** gap, not an architecture gap.

## 7. Implementation readiness

- **Complete: CAP-032 ResponseNormalizer** and **CAP-030 Response Normalization
  subsystem** — the five internal `NORMALIZATION-0001…0005` stages, the Assembly
  State, the Stage Coordinator, and the orchestration are implemented, wired
  end-to-end, and tested; they produce a real `ParsedResponse`.
- **Complete: CAP-051 ValidationInput (ADR-0003 plumbing).** The canonical
  Normalization → Validation input is implemented and tested; the Response Validator
  and Validation Pipeline consume it and the four Transport rules are migrated.
- **Ready to build now (the next milestone): CAP-043 Syntax Layer.** Its
  prerequisites — the Validation Framework (CAP-040), a real `ParsedResponse`
  (CAP-031/CAP-032), the `NormalizationResult` observations, and now the
  `ValidationInput` input path (CAP-051 / ADR-0003) — are all in place, so it is
  now **unblocked**. Implementing `SYNTAX-0001…0003` is the highest-leverage next
  step in the validation spine.
- **In Progress: CAP-041 Response Validator** (orchestrator built + tested, not
  wired), **CAP-060 CP1 Validator** (partial code).
- **Planned: CAP-044…050** — the remaining validation layers, in Rule Catalog
  order, after Syntax.
- **Governed deferral (ADR-0005): `SCHEMA-0003` (EnumerationsRule).** Within the
  Schema Layer (CAP-044), `SCHEMA-0003` is **Reserved · Deferred · Awaiting governed
  enumeration** — the governed response schema (`summary` + five string-arrays) has no
  enumerated field, so the rule has nothing to validate. Its Rule ID is frozen and never
  reused; it is implementable only once a governed response enumeration exists (ADR-0005
  activation conditions). This is intentional governance, **not** an implementation or
  coverage gap; the next Schema milestone is `SCHEMA-0004` (RequiredArraysRule).
- **Remaining-layer capability status (ADR-0006).** The remaining layers'
  ownership boundaries are frozen and each catalogued rule is classified against the
  **current** governed response schema (arrays of bare string statements). **Implementable
  now:** `CONTENT-0001`, `CONTENT-0002`, `REASONING-0001`, `REASONING-0002`,
  `REASONING-0003` (CAP-046, CAP-049). **Reserved · Deferred:** `CONTENT-0003/0004`, all
  Evidence (CAP-047), all Traceability (CAP-048), all Business (CAP-050) — each needs a
  governed capability that does not exist today (per-item description/confidence/evidence/
  source, or a declared Business policy). **Structural (CAP-045)** has no active
  catalogued rules and awaits both a composable response and a cataloguing ADR. A single
  future **schema-enrichment ADR** (structured response items + declared policies) unblocks
  most deferrals. This is intentional governance, **not** a coverage gap; no checkmarks
  change.
- **Reasoning duplicate mechanism (ADR-0008, Proposed).** `REASONING-0002`
  (DuplicateRecommendationRule) has its comparison mechanism frozen as **byte-exact** string
  equality (case-/whitespace-sensitive, no normalization, no semantics) by ADR-0008 and is
  **implemented**. Semantic "duplicated conclusions" detection remains a future capability
  requiring its own ADR.
- **Reasoning contradiction deferral (ADR-0009, Proposed).** `REASONING-0001`
  (ContradictoryRequirementRule) is **Reserved · Deferred**: contradiction is inherently
  semantic/logical and no governed **deterministic** mechanism exists (no faithful
  surface-form mechanism, unlike duplicates). ADR-0009 adopts **no** mechanism and reserves
  contradiction for a future semantic-reasoning ADR, **superseding ADR-0006's Implementable
  classification of `REASONING-0001`**.
- **Reasoning circular-logic deferral (ADR-0010, Proposed).** `REASONING-0003`
  (CircularLogicRule) is **Reserved · Deferred**: circular logic is inherently
  semantic/logical and additionally presupposes an inferential dependency structure the
  bare-string response does not carry (needs both dependency inference and cycle detection —
  neither governed). ADR-0010 adopts **no** mechanism, **superseding ADR-0006's Implementable
  classification of `REASONING-0003`**. With ADR-0008/0009/0010 the **Reasoning layer is fully
  dispositioned** (0002 implemented; 0001 & 0003 deferred). This is intentional governance,
  **not** a coverage gap; no checkmarks change.
- **Frozen and stable (no action): CAP-030 Response Normalization subsystem,
  CAP-032 ResponseNormalizer, CAP-040 Validation Framework, CAP-042 Transport
  Layer.**

> Readiness confirms the platform is positioned to **resume implementation**: the
> Response Normalization milestone is complete, the next milestone (CAP-043 Syntax
> Layer) is fully unblocked, and every downstream validation capability has complete
> architecture waiting behind it.
