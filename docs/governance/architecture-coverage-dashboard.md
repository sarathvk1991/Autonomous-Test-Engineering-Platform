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
| CAP-030 | Response Normalization (subsystem) | ✓ | ✓ | ✓ | ◑ | ✓ | ✓ | In Progress |
| CAP-031 | ParsedResponse | ✓ | ✓ | ✓ | ✓ | ✓ | ◑ | Ready |
| CAP-032 | ResponseNormalizer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Ready |
| CAP-040 | Validation Framework | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Ready |
| CAP-041 | Response Validator | ✓ | ✓ | ✓ | ◑ | ✓ | ✗ | In Progress |
| CAP-042 | Transport Layer | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | Ready |
| CAP-043 | Syntax Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Blocked |
| CAP-044 | Schema Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-045 | Structural Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-046 | Content Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-047 | Evidence Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-048 | Traceability Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-049 | Reasoning Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-050 | Business Rule Layer | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | Planned |
| CAP-060 | CP1 Validator | ◑ | ✓ | ✓ | ◑ | ✗ | ✗ | In Progress |

## 5. Overall coverage summary

Objective counts across all **28** capabilities (no percentages estimated). For
each stage: satisfied `✓` / partial `◑` / outstanding `✗`.

| Stage | `✓` satisfied | `◑` partial | `✗` outstanding | Outstanding capabilities |
| ----- | :-----------: | :---------: | :-------------: | ------------------------ |
| **Architecture** | 27 | 1 | 0 | Partial: CAP-060. |
| **Framework** | 28 | 0 | 0 | — (includes not-applicable as satisfied). |
| **Canonical Models** | 28 | 0 | 0 | — (includes not-applicable as satisfied). |
| **Implementation** | 16 | 3 | 9 | `✗`: CAP-032, CAP-043…050. Partial: CAP-030, CAP-041, CAP-060. |
| **Testing** | 15 | 3 | 10 | `✗`: CAP-032, CAP-043…050, CAP-060. Partial: CAP-021, CAP-022, CAP-023. |
| **Frozen** | 3 | 1 | 24 | `✓`: CAP-030, CAP-040, CAP-042. Partial: CAP-031. |

**Implementation Readiness distribution** (28 total): **Ready 17** · **In Progress
3** (CAP-030, CAP-041, CAP-060) · **Blocked 1** (CAP-043) · **Planned 7**
(CAP-044…050).

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

- **Ready to build now (the next milestone): CAP-032 ResponseNormalizer.** Its
  architecture, framework (CAP-030), and canonical model (CAP-031) are all
  complete, so it is unblocked. Implementing it (with `NORMALIZATION-0001…0005`)
  is the single highest-leverage next step and unblocks the validation spine.
- **In Progress: CAP-041 Response Validator** (orchestrator built + tested, not
  wired), **CAP-030 Response Normalization** (framework frozen, responsibilities
  pending), **CAP-060 CP1 Validator** (partial code).
- **Blocked: CAP-043 Syntax Layer** — waits on CAP-032 (it needs a real
  `ParsedResponse` and the `NormalizationResult` observations).
- **Planned: CAP-044…050** — the remaining validation layers, in Rule Catalog
  order, after Syntax.
- **Frozen and stable (no action): CAP-040 Validation Framework, CAP-042 Transport
  Layer, CAP-030 Response Normalization contract.**

> Readiness confirms the platform is positioned to **resume implementation**: the
> next milestone (CAP-032) is fully unblocked, and every downstream validation
> capability has complete architecture waiting behind it.
