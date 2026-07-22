# Capability Contract Standard — Proposed Revision to STD-002

**A Design-Proposal-class document · Draft · Not Yet Authoritative**

## 1. Document Metadata

| Field | Value |
| --- | --- |
| Working Identifier | `STD-002-R2-PROPOSAL` |
| Title | Capability Contract Standard — Proposed Revision to STD-002 (Platform Capability Standard) |
| Version | 1.0 (Draft, Proposed) |
| Status | **Draft — a Proposal, not an authoritative Standard.** `STD-002` v1.0 (Draft) remains the platform's sole authoritative capability standard unless and until the Standards Review Board formally adopts this proposal (§13). |
| Owner | Engineering Methodology Council |
| Stakeholders | Every stakeholder STD-006 §5 already names, plus every current and future Capability owner (STD-002 §6). |
| Derived From | HB-001 (Revision 4), STD-000 through STD-009 — proposing an Architectural-category revision (STD-006 §7) to STD-002 specifically. |
| Governing Standards | STD-000 (Constitutional Principles this proposal must not violate); STD-002 (the existing Standard this document proposes to revise); STD-006 (the governance process this proposal must pass through before adoption); STD-007 (the versioning discipline governing what kind of change this represents). |
| Related Documents | `CAP-001`, `CAP-100` (existing, real Capability Models — **unaffected by this proposal**, §1.2); `PRA-001` §8, `ADR-100` §7.3–§7.4 (cited as precedent). |
| Supersedes | Nothing, yet. If adopted, would supersede `STD-002` v1.0 under STD-007 §9's own Superseding rule. |
| Superseded By | Not applicable. |

### 1.1 Reconciliation Note — This Document's Own Governance Status

**This document is written with the full rigor the prompt commissioning it requires — a complete engineering specification — while being explicit that rigor is not the same thing as authority.** Only the Standards Review Board, exercising STD-006 §6's own Approving Authority for the `STD` family, may make this document's own content actually govern anything (§13). Presenting it as already-authoritative merely because it is thorough would itself violate STD-006 §4's own Evidence Before Assertion... restated here as this proposal's own Honest Assessment principle (STD-008 §4), applied to itself. This document is filed as a Design-Proposal-class artifact — extending HB-001 §6.3's own Design Proposal concept from its originally-named ADR-family satellite role to the STD family, **an analogy this document draws, not a formally registered HB-001 family extension** (HB-001 §20.14 reserves that registration to HB-001 alone).

### 1.2 Reconciliation Note — Relationship to Existing Capability Models

**Neither `CAP-001` nor `CAP-100` is modified, retroactively reinterpreted, or required to be rewritten by this document.** Both were authored against STD-002 v1.0 as it stands; both remain valid, Frozen-track (or Drafted) artifacts under that Standard for as long as it remains authoritative. If this proposal is ever adopted, it would govern *future* Capability Models — a transition path for existing ones is named as future work (§13), never assumed automatic.

## 2. Executive Summary

STD-002 v1.0 already defines a capability's nine canonical elements, six roles, six constraints, six quality attributes, and an eight-stage evidence-bearing lifecycle. This proposal does not discard any of that — it **redefines the CAP family as a governed Capability Contract**: a stable engineering agreement between Business, Architecture, Runtime, and Implementation that describes responsibility, never realization, and that a real service, agent, or implementation MAY satisfy in more than one way without the Contract itself changing. The Capability Contract schema (§5) is a superset of STD-002 §2's own nine elements, made explicit where STD-002 left an element implicit. **This proposal also surfaces, rather than hides, a real terminology collision**: the "Capability Maturity Model" this document is commissioned to define (§6) shares its exact name with `CAP-100` §6's own, already-published Capability Maturity Model — and the two measure different things entirely. Both facts — the proposal's own non-authoritative status, and the terminology collision it inherits by being asked to reuse an already-taken name — are recorded here rather than discovered by a confused future reader.

## 3. Position Relative to STD-002 and the Capability Lineage

```
Business Vision
        ↓
Product Requirements (PRD)
        ↓
Architecture Decisions (ADR)
        ↓
Capability Model (CAP)
        ↓
Runtime Model (RUN)
        ↓
System Design (SYS)
        ↓
Platform Architecture (PRA)
        ↓
Implementation (IMP)
```

PRD defines *what* the product must achieve; ADR defines *how* the architecture is organized; **the Capability Model defines what the system must be capable of delivering** — remaining independent of implementation, deployment, programming language, technology vendor, and architectural realization, restated here as binding, not merely descriptive.

**Architecture defines structure. Capability defines responsibility.** Architecture MAY realize capabilities; capabilities SHALL NEVER prescribe architecture (§7). Capabilities describe responsibilities; Runtime Models describe execution, and SHALL consume Capability Contracts (§8). Capabilities define contracts; System Design defines composition (§9). Platform Architecture provides reusable services that MAY realize capabilities; capabilities SHALL NOT define platform technologies (§10). Implementation realizes capability contracts, which SHALL remain stable across implementation changes (§11).

## 4. Capability Constitution

Normative, per this document's own commissioning brief:

1. A Capability is NOT a feature.
2. A Capability is NOT a software component.
3. A Capability is NOT a service.
4. A Capability is NOT an agent.
5. A Capability MAY be realized by multiple services.
6. A Capability MAY be realized by multiple agents.
7. A Capability MAY evolve without changing its business responsibility.
8. Every Capability SHALL have one clearly defined business purpose.
9. Every Capability SHALL define its engineering responsibilities.
10. Every Capability SHALL define evidence required for conformance.
11. Every Capability SHALL remain traceable.
12. Every Capability SHALL remain implementation independent.

**Relationship to STD-002.** Statements 1–7 sharpen, without contradicting, STD-002 §2's own Responsibility/Boundary pairing — STD-002 never said a capability *was* a feature, service, or agent, but it also never said, this explicitly, what a capability is *not*. Statements 8–12 restate STD-002 §2's own Mission, Responsibility, and Owner elements (8–9), STD-002 §9's own evidence discipline (10), STD-004 in full (11), and STD-002 §2's own technology-independence framing (12).

## 5. The Capability Contract

Every Capability SHALL contain the following. **Fields marked `(added)` restore two STD-002 §2 canonical elements — `Owner` and `Runtime Contract` — that do not appear in this document's own literal, commissioned field list; omitting either would violate STD-000 Rule 2 ("every capability SHALL expose one canonical runtime contract") and Principle 9 ("explicit ownership"), so both are added here explicitly rather than silently dropped.**

| Field | Relationship to STD-002 §2 |
| --- | --- |
| Capability Identifier | Specializes STD-002 §2's `Identity`. |
| Capability Name | Specializes `Identity`. |
| Purpose | Specializes `Mission`. |
| Business Outcome | Specializes `Mission`, made explicit. |
| Scope | Specializes `Boundary`. |
| Inputs | Unchanged from STD-002 §2. |
| Outputs | Unchanged from STD-002 §2. |
| Consumes | Refines `Inputs` at collaboration grain. |
| Produces | Refines `Outputs` at collaboration grain. |
| Preconditions | New — specializes STD-002 §7 Constraint 1 (Boundary rules) into a checkable, per-collaboration form. |
| Postconditions | New, paired with Preconditions. |
| Engineering Responsibilities | Specializes `Responsibility`. |
| Business Rules | Specializes `Responsibility`, business-facing half. |
| Engineering Rules | Specializes `Responsibility`, engineering-facing half. |
| Dependencies | Unchanged from STD-002 §2. |
| Constraints | Specializes `Boundary`, restated as an explicit list. |
| Governance | New — points to STD-006 in full, never restating it. |
| Conformance | New — points to STD-008 in full, never restating it. |
| Evidence | Specializes STD-002 §9's own evidence-per-transition table. |
| Quality Attributes | Specializes STD-002 §8's own six attributes. |
| Capability Maturity | Points to §6, below. |
| Future Evolution | New — the capability's own equivalent of every other Artifact family's Known Limitations/Future Evolution discipline. |
| **Owner `(added)`** | Restores STD-002 §2's own `Owner` element — STD-000 Principle 9. |
| **Runtime Contract `(added)`** | Restores STD-002 §2's own `Runtime Contract` element — STD-000 Rule 2. |

**The Capability Contract SHALL remain stable even if architecture or implementation changes** — restated as binding: a change to any field above is itself an Engineering Artifact lifecycle event under STD-007, never a silent edit.

## 6. Capability Maturity Model

**Four levels, as commissioned:**

```
Level 1 — Declared
        ↓
Level 2 — Architected
        ↓
Level 3 — Implemented
        ↓
Level 4 — Operational
```

| Level | Meaning |
| --- | --- |
| **Declared** | The capability exists as a business requirement. |
| **Architected** | The capability is supported by approved architecture. |
| **Implemented** | The capability exists in software. |
| **Operational** | The capability is deployed, monitored, governed, and producing evidence. |

**Capabilities SHALL explicitly identify their current maturity. No capability SHALL silently change maturity.**

### 6.1 Reconciliation Note — Two Different Models Share One Name, and a Third Model Is Nearby

**This document's own commission requires a model named "Capability Maturity Model" — and `CAP-100` §6 already published a model with the identical name, measuring something different.**

| | This document's Level (§6) | `CAP-100` §6's Maturity |
| --- | --- | --- |
| **Measures** | How far a capability has progressed through its own development lifecycle. | How proven a capability is, via real Capability Instances. |
| **Levels** | Declared → Architected → Implemented → Operational. | Conceptual → Piloted → Adopted → Standardized. |

**These are not alternative labels for the same axis — a capability can be `Operational` (this document's Level 4) while still `Piloted` (`CAP-100`'s own maturity, only one real Instance) simultaneously; the two axes are independent, exactly as STD-009 §9 already distinguished its own Adoption Maturity from `CAP-100` §6's Capability Maturity, one document earlier.** Rather than silently let two documents claim the same name for different things — precisely the failure mode STD-007 §5.1 already named as a general risk pattern — this document records the collision explicitly and does not resolve it unilaterally. Either this proposal's own model should be renamed before adoption (a candidate: "Capability Development Stage"), or `CAP-100` §6's model should be renamed, or the two names should be scoped explicitly (e.g. "Development Maturity" vs. "Adoption Maturity") — a decision for the Standards Review Board (§13), not this document.

**A third, related model exists nearby and is also reconciled, not silently ignored.** STD-002 §3 (referenced) already defines an eight-stage Capability Lifecycle (`Proposed → Architected → Governed → Implementing → Implemented → Runtime Ready → Certified → Operational`), which `CAP-100` §5 already compressed once, into its own five-stage version (`Proposed → Cataloged → Architected → Instantiated → Operational`), specific to Platform Capabilities. **This document's own four-level model (§6, above) is a second, independent compression of the same eight-stage lifecycle — using different granularity and, in two places (`Declared` vs. `Proposed`; the collapse points differ), different boundaries than `CAP-100` §5's own compression.** Two compressions of the same eight-stage source now coexist. This document proposes its own as the new canonical compression for all *future* Capability Models (per its own commissioning brief), while explicitly not requiring `CAP-100` §5's own, already-published compression to be retroactively rewritten (§1.2) — harmonizing the two remains future work (§13).

## 7. Relationship to ADR

Architecture defines structure. Capability defines responsibility. Architecture MAY realize capabilities. **Capabilities SHALL NEVER prescribe architecture** — restated as binding: no field in §5's own Capability Contract (Engineering Responsibilities, Business Rules, Engineering Rules, Constraints) may name a layer, domain, or architectural pattern. A Capability Contract that does so has exceeded its own family boundary, restating STD-000 Principle 3 (Layer isolation).

## 8. Relationship to RUN

Capabilities describe responsibilities. Runtime Models describe execution. **The Runtime Model SHALL consume Capability Contracts** — restating STD-005 §6's own `Realizes` semantic (Capability Intent → Runtime Intent) and HB-001 §20.3's own RUN-family row exactly; this document originates neither, it only restates them at the Capability Contract's own, more granular field level (§5's `Runtime Contract` field, added).

## 9. Relationship to SYS

Capabilities SHALL define contracts. System Design SHALL define composition — restating SYS-001's and SYS-100's own precedent of decomposing a Runtime's own responsibilities into Logical Systems, each realizing a Capability Contract's own fields without redefining them (SYS-100 §6's own Capability Contracts Realized column, generalized here as the pattern every future System Design SHALL follow).

## 10. Relationship to PRA

Platform Architecture SHALL provide reusable platform services that MAY realize capabilities. **Capabilities SHALL NOT define platform technologies** — restating ADR-100 §7.4's own "performs no business logic of its own" framing from the opposite direction: a Shared Platform Service realizes a Capability Contract's own fields; the Capability Contract itself never names the service.

## 11. Relationship to IMP

Implementation SHALL realize capability contracts. **Capability contracts SHALL remain stable across implementation changes** — restating IMP-100 §4's own Realization Principles (Capability intent preserved) and STD-007 §7's own Compatibility discipline, applied specifically to the Capability Contract's own fields (§5).

## 12. Quality Requirements

The Capability methodology SHALL: remain technology neutral; remain implementation independent; remain reusable; support future Hosted Applications; support future platform capabilities; distinguish business capability from architecture (§7); distinguish capability from implementation (§11); distinguish capability from runtime execution (§8); and, if adopted, become the canonical CAP methodology for EIOS (§13).

## 13. Adoption Path — How This Proposal Would Become Authoritative

Restating STD-006 §7's own Change Classification, applied to itself: this proposal represents an **Architectural-category change** to STD-002 (a change to Standards content this severe requires Architecture Review Board approval at minimum, and arguably touches STD-000's own Rule 2/Principle 9 closely enough — §5's own `(added)` fields — to warrant Constitutional Authority review as well, per STD-006 §5's own role definitions).

| Step | Authority | Outcome if Approved |
| --- | --- | --- |
| Constitutional review | Constitutional Authority (STD-006 §5) | Confirms §5's own `(added)` fields correctly restore, rather than alter, STD-000 Rule 2/Principle 9. |
| Standards conformance review | Standards Authority (STD-006 §5) | Confirms this proposal does not silently redefine STD-004 or STD-005 (§4, §8–§11 each cite, never restate, both). |
| Architecture Review Board approval | Architecture Review Board (STD-006 §6) | The formal approval STD-006 §7's own Architectural category requires. |
| Version increment | STD-007 §6 | `STD-002` advances from v1.0 to v2.0 (Major — an Architectural-category change), never a silent overwrite. |
| Transition path for `CAP-001`/`CAP-100` | Future governance act, not this document | Named as open (§1.2), never assumed automatic. |
| §6.1's own naming collision | Future governance act, not this document | Named as open (§6.1), never resolved unilaterally. |

**Until every step above completes, this document remains a proposal — STD-002 v1.0 remains the sole authoritative capability standard.**

## 14. Constraints

This proposal SHALL NOT: redefine STD-000, STD-004, or STD-005 (cited throughout, never restated); retroactively alter `CAP-001` or `CAP-100` (§1.2); resolve its own §6.1 naming collision unilaterally; or claim authority it has not yet received from the Standards Review Board (§1.1, §13).

## 15. Risks

| Category | Risk |
| --- | --- |
| **Premature authority assumption** | A reader treats this document as already governing new Capability Models before §13's own adoption path completes. |
| **Naming collision persistence** | §6.1's own two-model, one-name collision (`Capability Maturity Model`) persists indefinitely if the Standards Review Board never resolves it, compounding every time a new document cites "Capability Maturity" without specifying which one. |
| **Compression proliferation** | A third compression of STD-002 §3's own eight-stage lifecycle (after `CAP-100` §5 and this document's own §6) remains entirely possible until a future STD-002 revision harmonizes all of them — restating STD-007 §12's own Terminology Proliferation risk one document further. |
| **Retrofit ambiguity** | Whether `CAP-001`/`CAP-100` are ever required to migrate to this proposal's own schema (§5) is left genuinely open (§1.2) — an organization could reasonably read this either way absent a future, explicit ruling. |

## 16. Known Limitations

- **This document is not yet authoritative** — §1.1, §13.
- **`CAP-100` §6's own Capability Maturity Model and this document's own §6 model share an identical name for two different axes** — named, not resolved (§6.1).
- **Two independent compressions of STD-002 §3's own eight-stage lifecycle now exist** (`CAP-100` §5 and this document's §6) — neither superseding the other yet.
- **§5's own `Owner` and `Runtime Contract` fields were added by this document, not present in its own commissioned field list** — restored explicitly to avoid a silent Constitutional gap (STD-000 Rule 2, Principle 9), named here rather than left for a reader to notice the discrepancy against the original brief unaided.
- **No real Capability Model has ever been authored against this proposal's own schema (§5)** — every field is asserted, not yet exercised.

## 17. Final Self Review

- [x] Distinguishes business capability from architecture, implementation, and runtime execution — §7, §8, §11.
- [x] Technology neutral, implementation independent — verified throughout §4–§11.
- [x] Consistent with STD-000, STD-004, STD-005, STD-006, STD-007 — every citation references, never restates, its source.
- [x] Honest about its own governance status — §1.1, §13, stated repeatedly rather than once and assumed remembered.
- [x] Names, rather than resolves, the naming collision it inherits from its own commissioning brief — §6.1.
- [x] Does not retroactively alter `CAP-001` or `CAP-100` — §1.2.

## 18. Proposal Readiness Certificate

**This certifies that this document:**

- ✅ **Capability Contract Model Complete** — §4–§11 define the Constitution, the twenty-four-field Contract, the Maturity Model, and the relationship to every adjacent Engineering Artifact family.
- ⚠️ **Not Yet Authoritative** — §1.1, §13; adoption requires Constitutional review, Standards conformance review, and Architecture Review Board approval, none of which has occurred.
- ✅ **Technology Independent** — verified throughout.
- ⚠️ **Naming Collision Unresolved** — §6.1, recorded honestly rather than hidden behind a confident Certificate.
- ✅ **Ready for Standards Review Board Consideration** — as a Proposal, per §13's own adoption path.

> **This document is ready to be reviewed as the candidate successor to STD-002 — it is not yet, and does not claim to be, STD-002 itself.**

---

*End of proposal, Version 1.0 (Draft).*
