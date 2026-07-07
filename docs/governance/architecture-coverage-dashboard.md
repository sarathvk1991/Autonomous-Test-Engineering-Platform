# Architecture Coverage Dashboard

| Attribute | Value |
| --------- | ----- |
| Document type | Engineering Governance / Coverage Dashboard |
| Status | Living document — governance artifact |
| Governance baseline | **Validation Platform v1.0.0** (Git tag `v1.0.0-validation-platform`; see [release notes](../releases/v1.0.0-validation-platform.md)) |
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
| CAP-041 | Response Validator | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-042 | Transport Layer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Ready |
| CAP-043 | Syntax Layer | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-044 | Schema Layer | ✓ | ✓ | ✓ | ◑ | ✓ | ✗ | In Progress |
| CAP-045 | Structural Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-046 | Content Layer | ✓ | ✓ | ✓ | ◑ | ✓ | ✗ | In Progress |
| CAP-047 | Evidence Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-048 | Traceability Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-049 | Reasoning Layer | ✓ | ✓ | ✓ | ◑ | ✓ | ✗ | In Progress |
| CAP-050 | Business Rule Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-051 | ValidationInput (canonical input) | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-052 | Validation Profiles | ✓ | ✓ | n/a | ✓ | ✓ | ✗ | Ready |
| CAP-060 | CP1 Validator | ✓ | ✓ | ✓ | ◑ | ✗ | ✗ | In Progress |
| CAP-061 | Engineering Readiness Criteria Catalog | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-062 | CP1 Canonical Models | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-063 | CP1 Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-064 | Validation → CP1 Seam | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-065 | CP1 Engine | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-066 | CP1 Composition Root | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |
| CAP-067B | CP1 PlatformContext & CLI Wiring | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | Ready |

## 5. Overall coverage summary

Objective counts across all **37** capabilities (no percentages estimated). For
each stage: satisfied `✓` / partial `◑` / outstanding `✗`.

| Stage | `✓` satisfied | `◑` partial | `✗` outstanding | Outstanding capabilities |
| ----- | :-----------: | :---------: | :-------------: | ------------------------ |
| **Architecture** | 37 | 0 | 0 | — (CAP-060 now governed by ADR-0011/0012). |
| **Framework** | 37 | 0 | 0 | — (includes not-applicable as satisfied). |
| **Canonical Models** | 37 | 0 | 0 | — (includes not-applicable as satisfied). |
| **Implementation** | 29 | 4 | 4 | `✗`: CAP-045, CAP-047, CAP-048, CAP-050. Partial: CAP-044, CAP-046, CAP-049, CAP-060. |
| **Testing** | 29 | 3 | 5 | `✗`: CAP-045, CAP-047, CAP-048, CAP-050, CAP-060. Partial: CAP-021, CAP-022, CAP-023. |
| **Frozen** | 4 | 1 | 32 | `✓`: CAP-030, CAP-032, CAP-040, CAP-042. Partial: CAP-031. |

**Implementation Readiness distribution** (37 total): **Ready 29** · **In Progress
4** (CAP-044, CAP-046, CAP-049, CAP-060) · **Blocked 0** · **Planned 4** (CAP-045,
CAP-047, CAP-048, CAP-050).

## 6. Remaining architecture work

Architecture coverage is complete; the outstanding items are narrow and
repository-evidenced:

- **CAP-060 CP1 Validator** — architecture is now **complete** (`✓`): governed by
  **ADR-0011 (Accepted)** and **ADR-0012 (Accepted)**, and decomposed into CAP-061
  (Criteria Catalog), CAP-062 (models), CAP-063 (framework), CAP-064 (seam), CAP-065
  (engine), CAP-066 (composition root), the first criterion `CP1-0001` (CAP-067A),
  and **PlatformContext/CLI wiring (CAP-067B)** — CP1 now runs end-to-end in the
  pipeline. Remaining work is **further governed criteria** (via the catalog's §11
  process), not architecture or wiring.
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
- **Complete: CAP-041 Response Validator — wired end-to-end.** The composition
  root (`validation/response/validator_factory.py`) assembles the fully-wired
  validator; `PlatformContext` is the single construction hub; the CLI `--validate`
  phase builds the `ValidationInput` via the `ResponseNormalizer` and runs it. The
  complete `ValidationResult` is persisted (`validation_result.json`) and rendered
  (`validation_report.md`).
- **Complete: CAP-043 Syntax Layer.** `SYNTAX-0001…0003` implemented + tested.
- **Complete: CAP-052 Validation Profiles.** Governed, immutable rule-selection
  identities (`default`, `strict`, `transport-only`, `syntax-only`, `schema-only`,
  `content-review`) owned by the `ValidationProfileRegistry`; the Validation Factory
  builds a registry per profile; ordering stays governed by `LAYER_ORDER`. Selected
  via CLI `--validation-profile`. Orchestration only — rules are unaware of profiles.
- **Partially implemented: CAP-044 Schema** (`SCHEMA-0001/0002/0004`; `0003`
  deferred), **CAP-046 Content** (`CONTENT-0001/0002`), **CAP-049 Reasoning**
  (`REASONING-0002`).
- **In Progress: CAP-060 CP1 Validator** (partial code).
- **Planned / Deferred: CAP-045 Structural, CAP-047 Evidence, CAP-048
  Traceability, CAP-050 Business Rule** — awaiting governed schema enrichment and
  cataloguing ADRs.
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
- **Reasoning duplicate mechanism (ADR-0008, Accepted).** `REASONING-0002`
  (DuplicateRecommendationRule) has its comparison mechanism frozen as **byte-exact** string
  equality (case-/whitespace-sensitive, no normalization, no semantics) by ADR-0008 and is
  **implemented + tested**. Semantic "duplicated conclusions" detection remains a future
  capability requiring its own ADR.
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
- **CP1 subsystem (ADR-0011/0012, Accepted).** **Complete:** CAP-061 Engineering
  Readiness Criteria Catalog (governed, empty by design), CAP-062 CP1 Canonical
  Models (incl. `CP1Result` referencing `CP1FrameworkMetadata`; `CP1_RESULT_VERSION`
  1.1), CAP-063 CP1 Framework (behaviour-free; collects findings, derives no verdict),
  **CAP-064 Validation → CP1 Seam** (`ValidationToCP1Handoff`: gates on the Validation
  verdict, binds one `CP1Input`; pure orchestration above both boundaries, ADR-0011
  §D4/§D5), **CAP-065 CP1 Engine** (`CP1Engine`: executes the registered governed
  criteria via the given pipeline and aggregates their findings into the overall CP1
  verdict — any FAIL→FAIL, else any WARN→WARN, else PASS; ADR-0012 §8; orchestration
  only), **CAP-066 CP1 Composition Root** (`build_cp1_service` → `CP1Service`: explicit,
  deterministic assembly of the empty registry + engine into a ready-to-run service
  with a single `run(cp1_input)` entry point; assembly only). **First criterion
  implemented (CAP-067A):** `CP1-0001` (EngineeringInputAvailabilityCriterion, ADR-0013
  Accepted) — deterministic pooled-requirement-count ≥ 1, `CP1Input`-only; registered in
  the composition root and 100% unit-tested. **Wired into the application pipeline
  (CAP-067B):** `PlatformContext` owns the single `CP1Service` (built via
  `build_cp1_service()`) and constructs the seam; the CLI runs
  `Analysis → Normalization → Validation → ValidationToCP1Handoff → CP1Service.run() →
  Execution Package`, invoking CP1 **only** when the handoff returns a `CP1Input`
  (gate open, ADR-0011 §D5) and transporting the `CP1Result` on `ExecutionData`
  (no persistence/reporting added). **Next:** downstream consumption of `CP1Result`
  and further governed criteria (via the catalog's §11 process).

> Readiness confirms the deterministic validation initiative is **feature-complete
> for the currently governed response schema**: Response Normalization, the Validation
> Framework, the Response Validator (wired end-to-end with persistence + reporting),
> five implemented layers (13 rules), and Validation Profiles are all complete. The
> only remaining validation work is **governed-deferred** (Structural/Evidence/
> Traceability/Business layers and the deferred rules) behind a future
> schema-enrichment / semantic-reasoning ADR.
