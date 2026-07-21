# STD-002 — Platform Capability Standard

**Version 1.0 (Draft)**

| Field | Value |
| --- | --- |
| Identifier | STD-002 |
| Title | Platform Capability Standard |
| Document family | Standard (STD) — the third member of this family (HB-001 §6.6), sibling to STD-000 and STD-001 |
| Version | 1.0 (Draft) — Major.Minor.Patch only, no separate Revision counter (HB-001 §9's STD-family rule; precedent set in STD-000 §8, confirmed in STD-001's header) |
| Status | Draft — pending architecture review |
| Owner | Platform Architecture |
| Approvers | Reserved, pending Architecture review and Editorial review (HB-001 §15, §18) |
| Created | Not Recorded |
| Updated | Not Recorded |
| Related Documents | HB-001 Revision 2 (documentation architecture host); STD-000 (constitutional principles this standard applies); STD-001 (the implementation process a capability's own "Implementing" stage, §3 below, delegates to); the Platform Evolution Roadmap ADR (source of the frozen Capability Lifecycle this standard's own lifecycle wraps, §3 below); the Platform Capability Matrix (source of the capability tracking model this standard formalizes, §2 and §3 below); the Architecture Freeze Index (source of the identifier-retirement rule this standard's Evolution section restates, §11 below); every existing CAP definition, Runtime document, and Certification document (observational awareness only, per HB-001 §13.1 — no individual capability is described by this standard, per its own scope) |
| Scope | Capability identity, lifecycle, responsibilities, inputs, outputs, boundaries, dependencies, maturity, evidence, traceability, and evolution |
| Out of Scope | Implementation process, review process, certification process, coding standards, runtime architecture, deployment, technology, framework, language, AI-vendor guidance |
| Supersedes | Nothing (third Standards-family document) |
| Superseded By | Not applicable |

> STD-002 answers exactly one question, permanently: **what is a platform
> capability?** It does not describe any individual capability — no `CAP-NNN`
> is named here as a worked example, by design. It defines the canonical model
> every capability, present or future, is an instance of: what a capability
> is made of (§2), what states its identity passes through (§3), what it
> requires and produces (§4–§6), what bounds it (§7–§8), what evidence its
> maturity requires (§9–§10), and how it may change over time (§11). STD-002
> originates no new architecture and redefines nothing already frozen — it
> gives the shape every capability has already, informally, taken since the
> platform's earliest ADR, one permanent, citable name.

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Capability Definition](#2-capability-definition)
3. [Capability Lifecycle](#3-capability-lifecycle)
4. [Capability Inputs](#4-capability-inputs)
5. [Capability Outputs](#5-capability-outputs)
6. [Capability Responsibilities](#6-capability-responsibilities)
7. [Capability Constraints](#7-capability-constraints)
8. [Capability Quality Attributes](#8-capability-quality-attributes)
9. [Capability Evidence](#9-capability-evidence)
10. [Capability Traceability](#10-capability-traceability)
11. [Capability Evolution](#11-capability-evolution)
12. [Reserved Topics](#12-reserved-topics)
- [Revision Summary](#revision-summary)
- [Known Limitations](#known-limitations)
- [Future Roadmap](#future-roadmap)
- [Final Self Review](#final-self-review)
- [STD-002 Compliance Certificate](#std-002-compliance-certificate)

---

## 1. Purpose

Every prior document in this ecosystem *uses* the word "capability" without permanently defining it: HB-001 §6.4 names the CAP family's responsibilities; STD-000 §5 Rule 1–2 requires every capability to have one governing ADR and one runtime contract; STD-001 governs how a capability is implemented once its architecture is frozen. None of the three defines what a capability *is*, structurally, before any of that can be checked. STD-002 exists to close that gap: it is the canonical model every `CAP-NNN`, past or future, is an instance of.

**Relationship to ADR.** A capability's *architecture* — its canonical models, its runtime boundary, its internal decomposition — remains exclusively the governing ADR's own content (HB-001 §6.2). STD-002 never defines what any capability does; it defines the *shape* every capability's own ADR fills in (§2).

**Relationship to Governance.** A capability's *maturity* is tracked, not defined, by Governance (the Platform Capability Matrix, HB-001 §6.5). STD-002 gives that tracking a formal model to track *against* (§3, §9) — the Matrix's own six-stage lifecycle columns (Architecture → Framework → Canonical Models → Implementation → Testing → Frozen) remain exactly as they are; §3 below shows how they project onto STD-002's own, broader capability-identity lifecycle without being redefined.

**Relationship to Standards.** STD-000 establishes *why* a capability must be governed at all (its Constitutional Principles and Rules). STD-001 establishes *how* a capability's implementation proceeds, once its architecture is frozen. STD-002 establishes *what a capability is*, independent of any one of them being implemented yet — the three Standards together cover why, what, and how, without overlap.

**Relationship to Runtime.** A capability's Runtime documentation (HB-001 §6.7) describes one *instance* of what STD-002 defines the *class* of — Runtime documentation is never itself the definition of what a capability is, only the description of one, once live.

**Relationship to Certification.** Certification (HB-001 §6.8) verifies that a specific capability instance satisfies everything STD-002, STD-000, and the capability's own ADR require — STD-002 defines the model a certification checks an instance against; it performs no certification itself.

## 2. Capability Definition

A **platform capability** is the concrete unit of platform functionality this ecosystem tracks as a `CAP-NNN` (HB-001 §6.4). Every capability, without exception, is composed of exactly the following:

| Element | Definition | Where it is actually recorded today |
| --- | --- | --- |
| **Identity** | A permanent, sequential `CAP-NNN` identifier, allocated within a reserved per-domain block, never reused or reassigned once retired. | The Platform Capability Matrix's own `ID` column and §3.1 allocation rule. |
| **Mission** | The one sentence stating why the capability exists. | The Matrix's `Purpose` column. |
| **Responsibility** | What the capability SHALL do — its owned responsibilities. | The governing ADR's own Ownership / SHALL section. |
| **Boundary** | What the capability SHALL NOT do — the explicit edge of its responsibility. | The governing ADR's own "Does not own" / SHALL NOT section. |
| **Inputs** | The runtime contracts, capabilities, or Standards this capability consumes. | The Matrix's `Dependencies` column; the governing ADR's own runtime-boundary section. |
| **Outputs** | The one canonical runtime contract this capability produces, plus any Execution Package artifacts it projects. | The governing ADR's own runtime-contract definition (STD-000 §5 Rule 2). |
| **Dependencies** | The specific, named set of Inputs this capability declares — never an undeclared or discovered-later one. | Same as Inputs, above; restates STD-001 §7 Constraint 4 at the capability-definition level. |
| **Runtime Contract** | The single, named, versioned object that is this capability's only sanctioned crossing point to any consumer (STD-000 §4's Engineering Philosophy: Explicit Contracts). | The governing ADR's own canonical model section. |
| **Owner** | The accountable engineering owner (§6 below). | The Matrix's `Owner` column. |

**A capability lacking any one element above is not yet a capability by this standard's definition** — it is, at most, a Proposal (§3's first lifecycle stage).

## 3. Capability Lifecycle

STD-002 defines the lifecycle of a **capability's own identity** — the broadest of the three lifecycle-shaped documents this ecosystem now has, and the one that contains the other two as sub-ranges rather than competing with either:

```
Proposed
        ↓
Architected
        ↓
Governed
        ↓
Implementing
        ↓
Implemented
        ↓
Runtime Ready
        ↓
Certified
        ↓
Operational
```

**This lifecycle never replaces, reorders, or redefines any existing lifecycle.** It wraps them:

| STD-002 stage | Meaning | Relationship to existing, frozen lifecycles |
| --- | --- | --- |
| **Proposed** | A capability is named and scoped, before any ADR exists. | Precedes every existing lifecycle — none of them names a pre-architecture state, because each begins where architecture is already being frozen. |
| **Architected** | A governing ADR (and, where needed, a Design Proposal) exists in Draft or Review (HB-001 §8). | Precedes the Platform Evolution Roadmap ADR's own Capability Lifecycle (its first macro-stage, "Architecture Freeze," has not yet completed). |
| **Governed** | The governing ADR reaches Frozen (HB-001 §8), and the capability is registered in the Platform Capability Matrix. | Corresponds exactly to the Platform Evolution Roadmap ADR's Capability Lifecycle macro-stage 1, **Architecture Freeze**, now complete — the precondition STD-001 §3 itself begins from. |
| **Implementing** | Engineering work proceeds under STD-001's own Engineering Lifecycle in full (Implementation Planning → Implementation → Verification → Integration → Implementation Complete). | Corresponds exactly to the Platform Evolution Roadmap ADR's macro-stage 2, **Deterministic Implementation** — the same span STD-001 §3 already refines in detail. STD-002 does not re-refine it; it cites STD-001. |
| **Implemented** | STD-001's own Definition of Done (STD-001 §9) is satisfied. | The engineering-side completion of macro-stage 2, exactly as STD-001 §9 already defines it. |
| **Runtime Ready** | The capability's runtime contract is frozen, integrated, and its Execution Package artifacts and golden baseline are current. | Corresponds to the Platform Evolution Roadmap ADR's macro-stages 3–6 (**Runtime Contract Freeze, Runtime Integration, Execution Package Integration, Golden Rebaseline**), taken together. |
| **Certified** | Certification (HB-001 §6.8) has verified the capability against Architecture, Governance, and every applicable Standard. | Corresponds exactly to the Platform Evolution Roadmap ADR's macro-stage 7, **Architecture Certification**. |
| **Operational** | The capability is live and active within the platform's own running system. | A state the Platform Evolution Roadmap ADR's own lifecycle never named, because that lifecycle's scope is governance milestones, not live-operation status — STD-002 names it here because a capability's *identity* lifecycle does not end at certification, even though its *governance-milestone* lifecycle does. |

**The Platform Capability Matrix's own six-stage tracking columns** (Architecture → Framework → Canonical Models → Implementation → Testing → Frozen, Matrix §4) are a third, independent, and unmodified artifact — a coarser, governance-observable **projection** used specifically to render the Matrix's own `✓`/`◑`/`✗` status columns at a glance. It is not required to map one-to-one onto either lifecycle above; STD-002 does not redefine it, only notes that its six columns fall, in substance, within STD-002's own "Architected" through "Runtime Ready" span, exactly as the Matrix's own governing text already describes them ("Architecture ─► Framework ─► Canonical Models ─► Implementation ─► Testing ─► Frozen").

**No stage is skipped, and no stage is reordered** — the same discipline the Platform Evolution Roadmap ADR's own Stage 8 already freezes for its narrower lifecycle, now stated for STD-002's broader one.

## 4. Capability Inputs

The following SHALL exist before a capability may leave **Proposed** (§3):

| Input | Purpose |
| --- | --- |
| **A candidate name and mission** | The one-sentence statement of why the capability would exist (§2's Mission element), sufficient to evaluate before any architecture work begins. |
| **A candidate identifier** | A tentative `CAP-NNN` within the correct, reserved domain block (Platform Capability Matrix §3.1) — confirmed, not finalized, until the capability is actually registered at **Governed** (§3). |
| **A sponsoring Platform Architect** | The role accountable for taking the capability from Proposed through Architected (§6). |
| **An initial problem statement** | Why the capability is needed — the seed a future governing ADR's own Problem section (a convention every existing subsystem ADR already follows) will formalize. |

**This is distinct from, and precedes, STD-001's own Implementation Inputs (STD-001 §4).** STD-001's inputs are required before *implementation* begins — the **Governed → Implementing** transition (§3). STD-002's inputs above are required before the capability's *identity* is admitted at all — the **Proposed → Architected** transition, several stages earlier.

## 5. Capability Outputs

A capability, across its full lifecycle (§3), produces the following, cumulatively:

| Output | Produced by which lifecycle stage |
| --- | --- |
| A governing ADR (and, where needed, a Design Proposal) | Architected |
| A registered row in the Platform Capability Matrix | Governed |
| Every Implementation Deliverable STD-001 §6 already defines | Implementing → Implemented |
| A frozen runtime contract and its live integration | Runtime Ready |
| A Certification record (HB-001 §6.8) | Certified |
| Accurate, current Runtime documentation (HB-001 §6.7) | Operational, maintained continuously thereafter |

STD-002 does not redefine the content of any output above — each remains owned by the family already responsible for it (ADR, Governance, STD-001, Runtime, Certification, respectively, per HB-001 §6). STD-002 only names *when*, in a capability's own lifecycle, each is expected to exist.

## 6. Capability Responsibilities

| Role | Accountable for | Never accountable for |
| --- | --- | --- |
| **Owner** | The capability's mission, responsibility, and boundary (§2) remaining accurate across its entire lifecycle (§3); identical to the Capability Owner STD-001 §5 already names. | Performing implementation itself. |
| **Architect** | Taking the capability from Proposed through Architected to Governed (§3) — the governing ADR's own correctness; identical to the Platform Architect STD-001 §5 already names. | Redefining an already-Frozen ADR outside a new, reviewed decision record (STD-000 §8). |
| **Engineer** | Carrying the capability through Implementing to Implemented, under STD-001's own Engineer responsibilities in full (STD-001 §5) — STD-002 does not redefine this role, only situates it within the broader lifecycle. | Advancing the capability past Implemented without STD-001's Definition of Done (STD-001 §9) being satisfied. |
| **Reviewer** | Verifying, at the boundary of Implemented and Runtime Ready and again at Certified (§3), that the required evidence (§9) exists — identical to the Reviewer STD-001 §5 already names, situated here at the capability level rather than the single-implementation level. | Defining new architecture or a new capability boundary. |
| **Runtime Owner** | The capability's Runtime documentation (HB-001 §6.7) remaining accurate once the capability reaches Operational (§3), and for the remainder of its lifecycle. | Any of the Owner's, Architect's, Engineer's, or Reviewer's own accountabilities above. |

Every role above is a specific instance of HB-001 §11.3 Principle 4 (explicit ownership) and STD-000 Constitutional Principle 9, applied to the capability's own lifecycle rather than to a document.

## 7. Capability Constraints

Every capability SHALL observe the following, permanently:

1. **Boundary rules.** A capability performs only what its own Responsibility (§2) names, and never what its own Boundary (§2) excludes — a capability whose implementation reaches outside its declared boundary has violated this constraint regardless of whether the result "works" (restates STD-001 §7 Constraint 7, at the capability-definition level rather than the single-implementation level).
2. **Dependency rules.** A capability consumes only the Inputs it declared (§2, §4) — and, at the *runtime* level (as distinct from the *documentation-citation* level HB-001 §13 governs), only in the upward-only, never-skip direction the Platform Evolution Roadmap ADR's own Stage 5 already freezes for the platform's runtime layers. **These are two distinct dependency rules, deliberately not conflated:** HB-001 §13 governs which *document family* may cite which other; the Platform Evolution Roadmap ADR's Stage 5 governs which *runtime layer* a capability may consume. A capability obeys both, as two separate, non-overlapping constraints.
3. **Isolation.** A capability's internals are never reached into directly by another capability — only its one Runtime Contract (§2) is a sanctioned crossing point (restates STD-000 Constitutional Principle 3, Layer isolation, and the Platform Evolution Roadmap ADR's own Runtime Contract Principle, Stage 6).
4. **Versioning.** A capability's runtime contract, policy, and the capability's own documentation each version along independent axes, exactly as STD-000 Principle 7 and HB-001 §9 already require.
5. **Backward compatibility.** A capability's frozen identifier (§2's Identity element) and its historical meaning are permanent; a capability is never silently redefined, only additively evolved (§11) (restates STD-000 Principle 6).
6. **Ownership.** A capability names exactly one Owner (§6) at every point in its lifecycle (§3) — a capability with no named owner has not yet left Proposed (§3, restates STD-000 Principle 9).

## 8. Capability Quality Attributes

Every capability, in every layer, should satisfy the following, adapted from STD-000's Engineering Philosophy (STD-000 §3) and HB-001's own Documentation Quality Attributes (HB-001 §14), generalized here from documents to capabilities:

| Attribute | A capability has this when… |
| --- | --- |
| **Determinism** | The same governed inputs, reasoned over by the same governed engine, always produce the same output (STD-000 §3's Deterministic Engineering philosophy). |
| **Explainability** | Its output is explainable solely from the already-frozen, lower-layer contracts it consumed — no hidden inference (STD-000 §3's Explainability philosophy). |
| **Traceability** | Every element of its own definition (§2) can be traced to the governing ADR, Governance record, or Standard that authorizes it (§10). |
| **Governability** | No part of its architecture changes outside a governed, reviewed decision record (restates STD-000 Rule 3, generalized from "architectural change" to the capability as a whole). |
| **Maintainability** | It can be operated on by an engineer other than its original implementer, using only its own declared Inputs, Outputs, and documentation (adapted from HB-001 §14's Maintainability attribute). |
| **Extensibility** | A new consumer, or a new capability built on top of it, can be added without requiring this capability's own architecture to change — the same zero-modification extensibility discipline the platform's own subsystem architectures already apply to their own extension points. |

## 9. Capability Evidence

The following evidence SHALL exist before a capability's maturity is recorded as having advanced past the corresponding lifecycle stage (§3):

| Transition | Evidence required |
| --- | --- |
| **Proposed → Architected** | A governing ADR exists, at minimum in Draft (HB-001 §8). |
| **Architected → Governed** | The governing ADR is Frozen (HB-001 §8); the capability is registered in the Platform Capability Matrix (§2's Identity, Mission, Owner elements populated). |
| **Governed → Implementing** | Every Implementation Input STD-001 §4 requires is present. |
| **Implementing → Implemented** | Every Implementation Deliverable STD-001 §6 requires exists, and STD-001's Definition of Done (STD-001 §9) is satisfied. |
| **Implemented → Runtime Ready** | The runtime contract is frozen, integrated into the live pipeline, and the capability's Execution Package artifacts and golden baseline are current. |
| **Runtime Ready → Certified** | A Certification record (HB-001 §6.8) exists, verifying the capability against Architecture, Governance, STD-000, STD-001, and STD-002. |
| **Certified → Operational** | The capability's Runtime documentation (HB-001 §6.7) confirms it is live and active — the same "component runtime specification describing a live, wired system" HB-001 §6.7 already distinguishes from a not-yet-implemented design. |

**No transition is recorded on the strength of intent alone.** A capability's maturity, as recorded in the Platform Capability Matrix, reflects only evidence that already exists — the Matrix's own governing text already states this ("capability status is derived from the actual repository state... never from estimation or aspiration"), and STD-002 inherits that rule rather than relaxing it.

## 10. Capability Traceability

Every capability SHALL remain traceable through the following chain:

```
ADR
        ↓
Governance
        ↓
Capability
        ↓
Runtime
        ↓
Certification
```

- **ADR → Governance.** The governing ADR's Frozen status is recorded in the Architecture Freeze Index and/or the Platform Capability Matrix.
- **Governance → Capability.** The capability's own registration (§2's Identity, Owner, Dependencies) is drawn directly from that governed record — never invented independently of it.
- **Capability → Runtime.** The capability's Runtime documentation (§5, §9) describes its live realization.
- **Runtime → Certification.** Certification verifies the Runtime documentation against everything above it in this chain.

This chain is the capability-level instance of the same traceability discipline HB-001 §17 already establishes at the document-family level, and STD-001 §11 already establishes at the single-implementation level — three views of one underlying rule (HB-001 §7: "citation, not duplication"), each scoped to the granularity its own Standard governs, none contradicting either of the other two.

## 11. Capability Evolution

| Mechanism | Rule |
| --- | --- |
| **Versioning** | A capability's runtime contract, policy, and documentation each version independently (§7 Constraint 4, restating STD-000 Principle 7 and HB-001 §9). |
| **Deprecation** | A capability, or one of its elements (§2), is never silently removed. A future architectural decision marks it deprecated in place, retained for historical accuracy, before any later removal (restates STD-000 §8's Deprecation rule, generalized from a constitutional principle to a capability). |
| **Replacement** | A newer capability may supersede an older one's responsibility. The superseding capability receives its own new `CAP-NNN` identifier — it never reuses the identifier of the capability it replaces (§11's Retirement rule, below). |
| **Retirement** | A capability's identifier, once retired, is never reused or reassigned — restating the Platform Capability Matrix's own existing rule (§3.1): "a removed capability's ID is retired, never reused." Retirement removes a capability from Operational status (§3); it never deletes the historical record of what the capability was. |

**A renamed capability is not a replaced one.** Consistent with the Platform Capability Matrix §3.1's own existing rule ("a renamed capability keeps its ID"), STD-002 draws the same distinction: renaming changes §2's display name only, and keeps the same `CAP-NNN`; replacement changes what fulfills a responsibility, and always receives a new `CAP-NNN`.

## 12. Reserved Topics

Space is reserved for future expansion. **This section names categories only — it defines no model, no metric, and no automation.**

- **Capability composition** — whether and how one capability may be formally assembled from smaller, independently governed sub-capabilities, beyond the informal internal-collaborator decomposition individual ADRs already use.
- **Capability retirement procedure** — the specific process (as distinct from the rule already stated in §11) by which a capability is formally moved to retired status.
- **Cross-capability contracts** — any future formal agreement type between two capabilities beyond the single runtime-contract crossing point §2 and §7 already define.
- **Capability risk classification** — any future model for classifying a capability's own risk profile, distinct from the general Risk Scoring topic STD-001 §12 already reserves for implementation work.
- **Capability portfolio views** — any future aggregate view across many capabilities beyond what the Platform Capability Matrix already provides.

A topic in this list may only be defined in a future STD-002 version, or in a later, dedicated Standard, following the same governed-evolution discipline STD-000 §8/§9 and STD-001 §12 already establish — never introduced silently, never inferred from this reservation itself.

---

## Revision Summary

STD-002, Version 1.0 (Draft), establishes the canonical definition of a platform capability: its purpose and relationship to ADR, Governance, Standards, Runtime, and Certification (§1); the nine elements every capability is composed of, each mapped to where it is already recorded today (§2); an eight-stage capability-identity lifecycle explicitly framed as a superset wrapper around the Platform Evolution Roadmap ADR's own seven-macro-stage Capability Lifecycle and STD-001's own Engineering Lifecycle, with a full stage-by-stage reconciliation table, and an explicit note that the Platform Capability Matrix's own six-stage tracking columns remain a third, unmodified, coarser projection (§3); capability-identity-level inputs, distinguished from STD-001's implementation-level inputs (§4); cumulative capability outputs mapped to lifecycle stage (§5); five accountable roles, three of them identical to STD-001's own and explicitly cited rather than redefined (§6); six permanent constraints, including an explicit distinction between document-citation dependency rules (HB-001 §13) and runtime-layer dependency rules (the Platform Evolution Roadmap ADR §Stage 5) (§7); six capability quality attributes generalized from STD-000's philosophy and HB-001's own documentation quality attributes (§8); a maturity-evidence table keyed to each lifecycle transition (§9); a capability-level traceability chain shown to compose with, not duplicate, HB-001's and STD-001's own chains (§10); versioning, deprecation, replacement, and retirement rules, the last two restating the Platform Capability Matrix's own existing identifier rules (§11); and a governed, empty Reserved Topics space (§12). It introduces no implementation process, review process, certification process, coding standard, runtime architecture, deployment guidance, or technology/framework/language/AI-vendor preference, and it describes no individual capability. It modifies no frozen input.

## Known Limitations

- §3's reconciliation of four lifecycle-shaped artifacts (STD-002's own, the Platform Evolution Roadmap ADR's, STD-001's, and the Platform Capability Matrix's) is this document's own synthesis, offered as a compatible superset reading, not as a change to the authority or content of any of the three prior artifacts.
- §2's mapping of capability elements to "where they are already recorded today" describes the Platform Capability Matrix's and the ADR convention's *current* columns and sections; a future restructuring of either (itself requiring its own governed change, per HB-001 §6.5 and the Architecture Freeze Index) could shift where an element is recorded without this document being updated to match, until a future STD-002 edition does so.
- §9's evidence table names what evidence is required at each transition but does not define a template or checklist artifact for recording it — reserved for a future edition, consistent with STD-001's own equivalent limitation (STD-001, Known Limitations).
- §12's "Capability composition" reservation acknowledges, without resolving, that individual ADRs already informally decompose a capability into internal collaborators (as several existing subsystem ADRs do) — STD-002 does not yet formalize whether or how that informal pattern becomes a governed capability-composition model.
- This edition does not address what happens to a capability's Operational status (§3) if its live integration is later removed without a formal Retirement (§11) — that gap is left to a future edition or to Governance's own judgment, not resolved here.

## Future Roadmap

| Future edition | Anticipated focus |
| --- | --- |
| **Version 1.1** | Add evidence-recording templates for the transitions named in §9, without changing any transition or its required evidence. |
| **Version 1.2** | Formalize whether and how the informal internal-collaborator decomposition several existing subsystem ADRs already use becomes a governed "Capability composition" model (§12), without changing §2's own capability-element definition. |
| **Version 2.0 (reserved)** | Populate one or more remaining items from §12's Reserved Topics, following the same governed-evolution discipline as STD-000 and STD-001. |

## Final Self Review

- [x] No architecture was modified — the Platform Evolution Roadmap ADR's Capability Lifecycle (§3) and Dependency Rules (§7) are cited and reconciled, never redefined or reordered.
- [x] No governance was modified — the Platform Capability Matrix's own lifecycle columns (§3), identifier rules (§11), and evidence-derivation rule (§9) are cited by role only, never edited.
- [x] No runtime was modified — no component specification or execution behaviour is changed.
- [x] No capability was modified or individually described — every citation in this document is to a framework-level source (STD-000, STD-001, HB-001, the Platform Evolution Roadmap ADR, the Architecture Freeze Index, the Platform Capability Matrix's own structure); no `CAP-NNN`'s own content is used as a worked example.
- [x] HB-001 was not modified or contradicted — §1, §6, §7, §8, §10 cite HB-001 §6/§7/§9/§11.3/§13/§14/§17/§18 without redefining any of them.
- [x] STD-000 was not modified or contradicted — every constraint and quality attribute in §7–§8 restates a specific STD-000 Principle or Rule by number.
- [x] STD-001 was not modified or contradicted — §3's "Implementing"/"Implemented" stages, §4's input distinction, §6's Engineer/Reviewer roles, and §10's traceability chain all cite STD-001 directly rather than re-defining its content.
- [x] No implementation process, review process, certification process, coding standard, runtime architecture, deployment guidance, or technology/framework/language/AI-vendor guidance was introduced — verified section by section against the header's Out of Scope row.
- [x] Every objective (1–12) commissioned for this document is addressed: Purpose (§1), Capability Definition (§2), Capability Lifecycle (§3), Capability Inputs (§4), Capability Outputs (§5), Capability Responsibilities (§6), Capability Constraints (§7), Capability Quality Attributes (§8), Capability Evidence (§9), Capability Traceability (§10), Capability Evolution (§11), Reserved Topics (§12).
- [x] Remains capability-centric, technology-, implementation-, framework-, language-, and vendor-independent — verified by inspection; no section names a technology or an individual capability's business content.

## STD-002 Compliance Certificate

**This certifies that STD-002, Version 1.0 (Draft):**

- ✅ **Mission completed** — the canonical model of a platform capability is established: definition, lifecycle, inputs, outputs, responsibilities, constraints, quality attributes, evidence, traceability, and evolution.
- ✅ **Scope respected** — capability definition only; no implementation, review, certification, coding, runtime, deployment, technology, framework, language, or AI-vendor guidance is introduced, and no individual capability is described (§2's own framing, verified in the Final Self Review above).
- ✅ **Frozen inputs preserved** — HB-001, STD-000, STD-001, every ADR, every Governance document, the Platform Capability Matrix, every existing CAP definition, existing Runtime documentation, and existing Certification documentation are referenced or observationally acknowledged only, never redefined.
- ✅ **Capability lifecycle reconciled, not contradicted** — §3 shows, stage by stage, how STD-002's own lifecycle wraps the Platform Evolution Roadmap ADR's, contains STD-001's Engineering Lifecycle within its "Implementing" stage, and coexists with the Platform Capability Matrix's own tracking columns.
- ✅ **Every future CAP becomes an instance of STD-002** — §2's nine elements and §3's eight-stage lifecycle are the model every capability, present or future, already fits, or is now required to fit.
- ✅ **Ready for review.**

**Summary.** STD-002 is suitable to become the canonical definition of a platform capability because it names, for the first time in one permanent place, the shape every `CAP-NNN` has already, informally, taken since the platform's earliest architecture — and reconciles that shape explicitly with every other lifecycle-shaped document this ecosystem already has (the Platform Evolution Roadmap ADR's Capability Lifecycle, STD-001's Engineering Lifecycle, and the Platform Capability Matrix's own tracking columns), rather than adding a fourth, competing one. A future capability can now be evaluated against one canonical definition — this one — from the moment it is Proposed to the moment it is Operational, exactly as this standard's own commissioning brief requires.

---

*End of STD-002, Version 1.0 (Draft).*
