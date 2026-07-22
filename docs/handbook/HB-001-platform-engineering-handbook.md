# HB-001 — Platform Engineering Handbook

**Revision 4 · Version 4.0 (Draft)**

| Attribute | Value |
| --------- | ----- |
| Document ID | HB-001 |
| Document family | Handbook (HB) |
| Revision | 4 |
| Version | 4.0 (Draft) |
| Document type | Documentation Architecture — Root Reference |
| Status | Draft — pending architecture review |
| Owner | Platform Architecture |
| Governs | The documentation ecosystem of the entire engineering platform |
| Governed by | Nothing — HB-001 is the root of the documentation hierarchy it defines |
| Supersedes | Nothing (HB-001 revises itself; it does not supersede a different document) |
| Prior revision | HB-001 Revision 3, Version 3.0 (Draft) — now **Revised** (§8); see [Revision History](#revision-history) |
| Implementation independence | This handbook contains no language, framework, or AI-provider-specific guidance. It describes documents, not code. |

> HB-001 is not an implementation guide and not a governance document. It is the
> **documentation architecture** of the platform — the single reference that
> explains what kinds of engineering documents exist, what each one is
> responsible for, how they relate to one another, and how a reader or a new
> document finds its correct place in the ecosystem. Revision 1 established that
> architecture. Revision 2 strengthened it with governance rules for the
> documentation ecosystem itself. Revision 3 gave that ecosystem its first
> identification and numbering scheme. **Revision 4 is the final constitutional
> refinement before Platform Architecture (ADR-100) begins.** It generalizes
> Revision 3's own Engineering Document Identification & Classification
> Standard into a complete **Engineering Artifact Identification & Classification
> Standard** (§20): a governed distinction between an Engineering Artifact (a
> concept, lifecycle-independent of any document) and an Engineering Document
> (one lifecycle-stage description of that concept); a Bounded Context
> Classification replacing Revision 3's own Product Numbering Strategy; an
> explicit Reservation/Allocation distinction; separate Artifact-identity and
> Document-identity models; and a conceptual, implementation-free Engineering
> Artifact Registry Model. Revision 4 preserves every decision made in
> Revisions 1–3 unless stated otherwise here; no document identifier is
> renumbered, no document family is removed, and no architectural decision is
> changed. Where Revision 4 discovers a real inconsistency between Revision 3's
> own text and this revision's own generalization — a range whose meaning has
> shifted, a roadmap item superseded before it was reached — it is named and
> reconciled explicitly (§20, and the scaffolding sections below), never
> silently overwritten.

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Scope](#2-scope)
3. [Audience](#3-audience)
4. [Engineering Documentation Philosophy](#4-engineering-documentation-philosophy)
5. [Documentation Architecture](#5-documentation-architecture)
6. [Document Families](#6-document-families)
7. [Documentation Relationships](#7-documentation-relationships)
8. [Documentation Lifecycle](#8-documentation-lifecycle)
9. [Versioning Strategy](#9-versioning-strategy)
10. [Repository Organization](#10-repository-organization)
11. [Engineering Principles](#11-engineering-principles)
12. [Future Evolution](#12-future-evolution)
13. [Documentation Dependency Rules](#13-documentation-dependency-rules)
14. [Documentation Quality Attributes](#14-documentation-quality-attributes)
15. [Documentation Review Workflow](#15-documentation-review-workflow)
16. [Document Metadata Standard](#16-document-metadata-standard)
17. [Documentation Traceability Standard](#17-documentation-traceability-standard)
18. [Documentation Ownership Model](#18-documentation-ownership-model)
19. [Future Automation](#19-future-automation)
20. [Engineering Artifact Identification & Classification Standard](#20-engineering-artifact-identification--classification-standard)
- [Revision History](#revision-history)
- [Revision Summary](#revision-summary)
- [Future Revision Roadmap](#future-revision-roadmap)
- [Known Limitations of Revision 4](#known-limitations-of-revision-4)
- [Final Self Review](#final-self-review)
- [HB-001 Revision 4 Compliance Certificate](#hb-001-revision-4-compliance-certificate)

---

## 1. Purpose

An engineering platform that reasons deterministically, freezes its architecture deliberately, and governs its own evolution through Architecture Decision Records accumulates, over time, a second artifact of equal consequence to the code itself: its documentation. Left unmanaged, that documentation grows the same way undocumented code grows — inconsistently, redundantly, and without a single place a reader can trust to be current.

HB-001 exists to prevent that outcome by defining, once and authoritatively, **the documentation architecture of the platform**: what kinds of documents exist, what each kind is responsible for, how they depend on one another, and how a reader — or a future author — determines where a new document belongs before writing a single line of it.

This handbook does not describe *what the platform does*. It describes *how the platform explains itself*. Every existing ADR, governance record, standard, capability document, runtime document, and certification report in this repository already conforms, in substance, to the structure this handbook names. HB-001's contribution is not to invent new rules for any of them — it is to make the rule that already governs their relationships explicit, permanent, and citable, exactly as ADR-0020 made the platform's architectural layering explicit for code that had, in substance, already been following it.

**What Revision 2 adds to this purpose.** Revision 1 answered "what documents exist, and where do they belong?" Revision 2 answers the next question that follows from it: "what keeps those documents correct, consistent, and trustworthy once they exist?" §13–§19 supply that answer as governance rules for the documentation ecosystem itself — never as new architecture, governance, capability, or runtime content (§2).

## 2. Scope

**In scope for HB-001 (Revision 1, unchanged):**

- The documentation hierarchy — the ordered relationship between the platform's constitutional, architectural, governance, standards, capability, runtime, and certification documents.
- The document families — the recurring *kinds* of document the platform produces, each with one purpose, one owner, and one place in the hierarchy.
- The relationships between families — dependency direction, citation conventions, and traceability.
- The lifecycle every engineering document passes through, from first draft to superseded.
- The versioning strategy for documents themselves (not for runtime contracts, APIs, or code — those are governed elsewhere, see the out-of-scope list below).
- Baseline recommendations for repository organization, naming, and cross-referencing of documents.
- The guiding principles that keep the documentation ecosystem consistent as it grows.

**Added in scope for Revision 2:**

- Explicit, per-family dependency rules — permitted upstream dependencies, prohibited downstream dependencies, and the rationale for each (§13).
- The quality attributes every governed document should satisfy, regardless of family (§14).
- Review responsibilities layered onto the existing lifecycle, without adding or renaming any lifecycle stage (§15).
- A canonical metadata standard for governed documents — defined, not retroactively applied (§16).
- A traceability standard defining mandatory, optional, and prohibited references between families (§17).
- A classification of the existing engineering principles into logical categories, with every Revision 1 principle preserved (§11).
- An ownership model naming owner, review authority, approval authority, and maintenance responsibility per family (§18).
- A reserved, informational section naming future documentation-automation opportunities, with no tooling specified (§19).

**Added in scope for Revision 3:**

- A single, platform-wide Engineering Document Identification & Classification Standard (§20): document-family registration and reservation, product numbering, artifact identity, naming convention, lifecycle and transformation consistency, family-level traceability, and the governance rules for the standard itself.

**Added in scope for Revision 4:**

- Generalization of Revision 3's own identification standard into a complete Engineering Artifact Identification & Classification Standard (§20): the Engineering Artifact / Engineering Document distinction, Bounded Context Classification (replacing Revision 3's Product Numbering Strategy), explicit Reservation and Allocation rules, separate Artifact-identity and Document-identity models, a unified artifact metadata model, and a conceptual (non-software) Engineering Artifact Registry Model.

**Intentionally out of scope for HB-001 (Revision 1 through Revision 4, all four):**

- **Architecture content.** HB-001 does not define what any layer, capability, or runtime contract *is* — that is the Architecture family's own responsibility (§6.2), and every architectural decision already on record is treated as authoritative and unmodified by this handbook.
- **Governance content.** HB-001 does not define freeze policy, capability maturity criteria, or ADR-required/not-required judgments — that is the Governance family's own responsibility (§6.5), exercised today by the Architecture Freeze Index and the Platform Capability Matrix, both left exactly as they are.
- **New capabilities.** HB-001 introduces no `CAP-NNN` capability, changes no capability's boundary, and reserves no new runtime contract.
- **Runtime or implementation detail.** HB-001 names languages, frameworks, or AI providers nowhere in this document, by design (see the Implementation Independence row in the header table).
- **Versioning of runtime contracts, APIs, or code artifacts.** §9 covers *document* versioning only. Runtime contract versioning (e.g. `*_RESULT_VERSION` constants) remains governed entirely by each capability's own ADR, unaffected by this handbook.
- **New engineering, coding, or implementation standards.** HB-001 defines the Standards family's *place* in the ecosystem (§6.6) and, new in Revision 2, the metadata (§16) and dependency (§13) rules a future Standards document must itself obey — it never originates a standard's own content. That remains the province of a future `STD-NNN` document.
- **Document content standards** (writing style, terminology glossaries, template text). Reserved for a future Standards-family document (§12).

## 3. Audience

| Reader | How HB-001 serves them |
| --- | --- |
| **Platform Architects** | The map from which every architectural and constitutional document's place, authority, and dependency is determined before it is written — and, as of Revision 2, the explicit rules (§13) for what such a document may and may not cite. |
| **Engineers** | A way to find the correct document for a question — "why does this work this way?" (Architecture), "is this allowed?" (Governance), "how should I build this?" (Standards, future) — without guessing which directory to search. |
| **Reviewers** | A structural checklist: does a new document belong to exactly one family, cite its correct dependencies, and enter at the correct lifecycle stage? Revision 2's Review Workflow (§15) and Quality Attributes (§14) give this checklist concrete criteria. |
| **Technical Leads** | A planning surface for what documentation a new initiative requires, and in what order it must be produced (Architecture before Governance before Capability, per §5). |
| **Contributors** | An onboarding reference — a new contributor can learn the shape of the platform's documentation before learning the shape of its code. |

## 4. Engineering Documentation Philosophy

**Documentation is a first-class engineering artifact.** In this platform, an architectural decision does not exist until it is recorded; a capability is not complete until its governance record and certification exist alongside its code. Documentation is not a description written after engineering happens — it is one of the deliverables engineering produces, held to the same standard of rigor, review, and version control as the systems it describes.

**Documentation earns trust the way code does: by being deterministic, explainable, and reviewable.** A reader of this platform's documentation should never have to guess whether a document is current, whether it has authority over the thing it describes, or what it depends on. Every document family defined in §6 exists to answer those three questions on sight — by its identifier, its location, and its declared status.

**Documentation minimizes duplication by construction, not by discipline alone.** The platform's own architectural principle of "exactly one owner per responsibility" (already frozen for code and capabilities by the platform's constitutional ADRs) applies identically to documentation: exactly one document owns a given fact, and every other document that needs that fact cites it rather than restates it. This is why §7 (Documentation Relationships) exists as its own section, not a footnote — cross-referencing is the primary mechanism, not an optional courtesy.

**Documentation has a lifecycle because engineering decisions have a lifecycle.** A document that is still Draft carries different authority than one that is Frozen; treating every document as equally final, regardless of its stage, is how documentation drifts silently out of sync with the systems it describes. §8 exists to make that distinction explicit and enforceable.

**Documentation stays trustworthy only if something keeps it trustworthy.** Revision 1 established what a document *is*. It did not yet establish what keeps a document *correct* once written — a rule for what it may depend on (§13), a definition of what "good" means for it (§14), who is responsible for checking it (§15), what it must declare about itself (§16), how it must connect to its neighbors (§17), and who owns it in practice (§18). That is Revision 2's contribution to this philosophy.

## 5. Documentation Architecture

The platform's documentation is organized as a directed hierarchy. Each layer depends only on the layer(s) above it in this list — never the reverse — mirroring, at the documentation level, the same upward-only dependency discipline the platform's runtime architecture already enforces between its own layers.

```
Platform Constitution
        ↓
    Architecture
        ↓
    Governance
        ↓
    Standards
        ↓
    Capabilities
        ↓
     Runtime
        ↓
  Certification
```

| Tier | Responsibility | Answers |
| --- | --- | --- |
| **Platform Constitution** | The permanent, foundational decisions every other document inherits without re-deriving them — what layers exist, what kind of truth each tier of the platform is allowed to touch, and the non-negotiable principles nothing beneath this tier may contradict. | *What is permanently true about this platform, regardless of any single capability?* |
| **Architecture** | The frozen design of a specific subsystem, layer boundary, or cross-cutting contract — built directly on the Constitution, never contradicting it. | *What does this part of the platform do, and why is it built this way?* |
| **Governance** | The rules by which architecture is kept correct over time — freeze status, maturity tracking, what requires a new decision record versus what does not. | *Is this change allowed, and under what process?* |
| **Standards** | The conventions engineering work must follow to remain consistent with the governed architecture — inherited from Architecture and Governance, never inventing new architectural authority of its own. | *How should this kind of work be done consistently, every time?* |
| **Capabilities** | The concrete unit of platform functionality — a `CAP-NNN` — that implements Architecture under Governance and in conformance with Standards. | *What exists, how mature is it, and what does it depend on?* |
| **Runtime** | The description of the system as it actually executes — component specifications for what is live, and the artifacts a live execution itself produces. | *What does this system actually do when it runs?* |
| **Certification** | The record that a capability, a release, or a runtime behavior has been verified against everything above it in this hierarchy. | *Is this ready, and how do we know?* |

**Reading the hierarchy.** A document at any tier may cite and depend on a document at any tier above it (closer to Platform Constitution) — never a tier below it. A Standards document may cite Architecture and Governance; it may never be cited by, or depend on, a piece of Architecture, because that would let convention dictate design rather than the reverse. This is the documentation-level restatement of the same one-way dependency rule the platform's own architectural layers already obey — extended here from runtime contracts to the documents that describe them. **Revision 2 makes this rule precise and per-family in §13.**

**This is a hierarchy of authority, not a hierarchy of quality.** A Runtime document is not "lesser" than a Constitution document — it answers a different, equally necessary question. The hierarchy exists so that when two documents appear to disagree, the reader knows, without guessing, which one is authoritative: the one closer to Platform Constitution.

This hierarchy, established in Revision 1, is unchanged by Revision 2.

## 6. Document Families

Each family below has exactly one purpose, one form of ownership, and one place in §5's hierarchy. A document belongs to exactly one family. This family catalogue, established in Revision 1, is unchanged by Revision 2 — §18 supplements each family's Ownership row with a fuller review/approval/maintenance model, without altering any family's purpose or boundary.

### 6.1 HB — Handbook

- **Purpose:** Define the documentation architecture itself — the root from which every other family's place in the ecosystem is derived. This document is the family's sole member today.
- **Ownership:** Platform Architecture.
- **Responsibilities:** Documentation hierarchy, document families, cross-family relationships, document lifecycle, document versioning, repository organization for documentation, and the engineering principles that govern documentation itself.
- **Examples:** HB-001 (this document).
- **Relationship with other families:** Sits outside and above §5's hierarchy — it describes the hierarchy rather than occupying a tier within it. Every other family's own definition traces back to HB-001; HB-001 traces back to nothing.

### 6.2 ADR — Architecture Decision Record

- **Purpose:** Record one architectural decision permanently — either a platform-wide constitutional rule or a single subsystem's frozen design — along with the reasoning, alternatives considered, and consequences.
- **Ownership:** The Platform Architect(s) responsible for the decision's domain.
- **Responsibilities:** Constitutional decisions (platform layers, dependency rules, truth hierarchies) and subsystem architecture decisions (a capability's canonical models, runtime boundary, and internal decomposition). Every existing numbered ADR in this repository is an example of this family.
- **Examples (existing, unmodified by this handbook):** the platform's numbered ADR series, spanning constitutional documents (e.g. the platform's layering and dependency constitution) and subsystem freezes (e.g. individual capability architecture freezes).
- **Relationship with other families:** Sits at the Platform Constitution and Architecture tiers of §5. Depends on nothing but prior ADRs and, where present, its own governing design proposal. Is depended on by Governance, Standards, and Capability documents, which cite the ADR rather than restating its content.

### 6.3 Design Proposal (a supporting document type within the ADR family)

- **Purpose:** Carry the full design detail — canonical models, field-by-field justification, internal decomposition, strategy detail — that would make a governing ADR unreadably long if inlined.
- **Ownership:** The same owner as the ADR it supports.
- **Responsibilities:** Detailed design content only; it never carries decision authority of its own. An ADR's "Governing design" citation points to its proposal; the proposal's own authority is entirely derivative of the ADR that governs it.
- **Examples:** the platform's existing design-proposal documents, each paired one-to-one with the ADR that governs it.
- **Relationship with other families:** A satellite of the ADR family, not a family of its own — always paired with exactly one governing ADR, never freestanding.

### 6.4 CAP — Capability Document

- **Purpose:** Track one platform capability — a `CAP-NNN` — across its full lifecycle: what it is, how mature it is, what it depends on, and what its next milestone is.
- **Ownership:** The engineering owner of the capability's domain, recorded per capability.
- **Responsibilities:** Capability identity and numbering, maturity tracking, dependency declaration, and the aggregate view of every capability the platform has ever registered.
- **Examples:** the platform's Capability Matrix — the single executive view of every `CAP-NNN` capability and its maturity — and each capability's own governing ADR and design proposal, cross-referenced from it.
- **Relationship with other families:** Sits at the Capabilities tier of §5. Depends on Architecture (its governing ADR), Governance (its freeze and maturity status), and, where applicable, Standards (the conventions its implementation must follow). Is depended on by Runtime documentation (which describes the capability once live) and Certification (which verifies it).

### 6.5 Governance

- **Purpose:** Record the rules by which architecture, once frozen, is kept correct over time, and provide the living, always-current view of the platform's own maturity.
- **Ownership:** Platform Architecture, maintained as a living document family (unlike ADRs and Handbook revisions, Governance documents are expected to be updated in place as the platform's state changes, rather than superseded).
- **Responsibilities:** Freeze status tracking, ADR-required/not-required judgment criteria, capability maturity aggregation, and cross-capability consistency checks.
- **Examples:** the platform's Architecture Freeze Index, Platform Capability Matrix, Architecture Coverage Dashboard, and any capability-specific governance record (a dedicated governance document for a single capability, used when that capability's own governance mechanics — versioning axes, extension/deprecation strategy, review checklists — are too extensive for its governing ADR to carry alone).
- **Relationship with other families:** Sits at the Governance tier of §5. Depends, as an **authority dependency**, on Architecture only (it indexes ADRs; it never originates architectural content of its own). It also **records observational facts** about Capabilities (e.g. a capability's current maturity) as an exercise of its own aggregation responsibility — a relationship Revision 2 distinguishes explicitly from authority dependency in §13, because the two look similar on the page but carry opposite implications for who may cite whom. Is depended on, as an authority, by Standards, Capabilities, and Certification, each of which cites Governance to confirm a document's freeze status or maturity before proceeding.

### 6.6 STD — Standard

- **Purpose:** Define the conventions engineering work must follow to remain consistent with governed architecture, so that consistency does not depend on an individual engineer's memory.
- **Ownership:** Platform Architecture, delegated per domain (e.g. a naming convention, a review checklist template, a documentation style rule).
- **Responsibilities:** Naming conventions, structural conventions, and review conventions that apply platform-wide or family-wide. Standards never introduce new architectural authority — they only make an already-governed decision easy to apply consistently.
- **Examples:** the platform's existing naming-conventions and coding-standards references, and any development guide describing how to build a specific kind of governed unit consistently (e.g. a rule-development guide for a governed rule catalogue).
- **Relationship with other families:** Sits at the Standards tier of §5. Depends on Architecture and Governance (a naming convention exists to make an already-frozen architectural distinction visible in code or documents, never to invent a new one). Is depended on by Capability and Runtime documentation, which conform to it without restating it.

> **Note on current state (unchanged from Revision 1).** The platform's existing standards documents predate a formal `STD-NNN` identifier scheme. HB-001 does not renumber, relocate, or rewrite them. Revision 2 does not change this — formalizing the `STD-NNN` scheme remains reserved for a future revision or for `STD-001` itself (§12, §19's revision note).

### 6.7 Runtime Documentation

- **Purpose:** Describe the system as it actually executes — both the specification of a live component and the artifacts a specific execution of it produces.
- **Ownership:** The engineering owner of the described component or execution surface.
- **Responsibilities:** Two distinct sub-kinds, both real and both already present in this repository:
  - **Component runtime specifications** — architecture documents that describe a system component's live, wired behavior (as opposed to a not-yet-implemented design).
  - **Execution-produced documentation** — artifacts a single execution of the platform generates about itself (a run's own report, summary, or metrics record), which are Runtime documentation *instances* rather than authored Runtime documents, but belong to this family for the same reason: they describe what the system did when it ran, not what it was designed to do.
- **Examples:** the platform's component-level architecture specifications describing already-wired subsystems, its operational runbook, its integration references, and the per-execution report/summary/metrics artifacts a completed run of the platform produces into its own execution output.
- **Relationship with other families:** Sits at the Runtime tier of §5. Depends on Architecture (a runtime document describes the *realization* of an architectural contract, never a contract of its own) and Capabilities (it describes one capability's live behavior). Is depended on by Certification, which verifies runtime behavior against what Architecture and Governance require.

### 6.8 Certification

- **Purpose:** Record that a capability, a release, or a specific runtime behavior has been formally verified against the Architecture, Governance, Standards, and Runtime documentation that govern it.
- **Ownership:** The reviewing authority for the certified scope — a Platform Architect for an architecture certification, a release owner for a release certification.
- **Responsibilities:** Verification statements, sign-off records, and — where the certified scope is a release rather than a single capability — the regression baseline a future release is measured against.
- **Examples:** the platform's release-regression-baseline governance contract, per-capability architecture certification reports (the closing verification section of a capability's ADR or governance record), and pre-certification review reports (a review of one candidate capability's readiness, produced before its formal certification is recorded).
- **Relationship with other families:** Sits at the Certification tier of §5, the terminal tier — nothing in this documentation ecosystem depends on Certification; it is where the chain of trust from Constitution through Runtime terminates in a verifiable statement. Depends on every tier above it. A review report is treated as evidence feeding a certification, not a certification itself — this is the concrete expression of this handbook's own Engineering Philosophy line: *"Reviews validate implementations. Certification validates readiness."* **Revision 2's Review Workflow (§15) gives this distinction a concrete home in the lifecycle.**

### 6.9 Family summary

| Family | Hierarchy tier (§5) | Depends on | Depended on by |
| --- | --- | --- | --- |
| HB | outside the hierarchy (defines it) | nothing | every family, indirectly |
| ADR (+ Design Proposal) | Platform Constitution, Architecture | prior ADRs | Governance, Standards, CAP, Runtime |
| Governance | Governance | ADR (authority); CAP (observational only, §13) | Standards, CAP, Certification |
| STD | Standards | ADR, Governance | CAP, Runtime |
| CAP | Capabilities | ADR, Governance, STD | Runtime, Certification |
| Runtime | Runtime | ADR, CAP | Certification |
| Certification | Certification (terminal) | ADR, Governance, STD, CAP, Runtime | nothing |

## 7. Documentation Relationships

**Dependency direction is always toward Platform Constitution.** Every citation in this ecosystem points from a lower tier to a higher one (§5): a Governance document cites the ADR it indexes; a Capability document cites the Architecture and Governance that bound it; a Certification report cites everything it verified. A document never cites something below it in the hierarchy as though that lower document had authority over it — a piece of Architecture does not cite a Certification report to justify itself, because certification is evidence of conformance, not a source of design authority. **§13 restates this rule per family, with a permitted/prohibited table and a citation matrix.**

**Citation, not duplication, is the traceability mechanism.** When a document needs a fact that another document already owns, it references that document by its identifier (§10.3) rather than restating the fact. This is the same "exactly one owner per fact" discipline this platform's own runtime architecture already enforces for canonical models, applied here to documentation content. **§17 defines which such references are mandatory, optional, or prohibited.**

**Traceability is bidirectional in practice, even though authority flows one way.** A reader starting from a Certification report can trace backward through every tier to the Platform Constitution it ultimately rests on; a reader starting from the Platform Constitution can, conversely, discover every Capability and Certification that was ever built against it, because every downstream document names its upstream dependency explicitly. Neither direction requires guessing — both are satisfied by the same set of forward citations, read in the direction the reader needs.

**A document's own identifier is the primary cross-reference token.** A document is cited by its identifier (e.g. an ADR number, a `CAP-NNN` id, or this handbook's own `HB-001`) plus, where useful, the specific internal section — never by an ambiguous description like "the architecture doc" or "the recent proposal." §10.3 defines the identifier scheme this depends on; §16 defines the metadata (including `Related Documents`) that carries it inside a document's own header.

**Cross-family relationships are never circular.** Because dependency only ever points toward Platform Constitution (§5), and no family occupies more than one tier, a citation cycle across families is structurally impossible without violating the hierarchy itself — the same guarantee the platform's runtime architecture already provides for its own layers, restated here for the documents that describe them.

This section, established in Revision 1, is unchanged by Revision 2. §13 and §17 make its rules operational.

## 8. Documentation Lifecycle

Every engineering document, in every family, progresses through the same six stages, in the same order. A document may remain at a stage indefinitely (a Governance document, for example, is expected to stay "Frozen" for the architecture it indexes while still being edited in place to stay current — see the note under this section's table); no document skips a stage on its way forward. **These six stages are unchanged by Revision 2** — §15 clarifies who is responsible for what at each stage; it introduces no new stage and reorders none.

```
Draft
  ↓
Review
  ↓
Approved
  ↓
Frozen
  ↓
Revised
  ↓
Superseded
```

| Stage | Meaning |
| --- | --- |
| **Draft** | The document is being written. It carries no authority yet; nothing outside its own author's working set should depend on it. |
| **Review** | The document is complete and submitted for review by its family's designated reviewing authority (§6, §18). Content may still change in response to feedback. §15 decomposes this single stage into the specific review types a document may need to pass through before it is Approved. |
| **Approved** | The document's content is accepted. It now carries the authority its family grants it, but it is not yet declared immutable — narrow corrections remain possible without a formal revision. |
| **Frozen** | The document's content is declared immutable except through a deliberate, reviewed change (for an ADR, a new ADR; for a Handbook, a new revision; for Governance, an explicit, logged update). This is the stage at which other documents may safely cite it as a stable dependency. |
| **Revised** | A newer revision or version of the document exists and is now authoritative; this version remains available for historical reference but no longer governs new work. HB-001 Revision 1 is, as of this document, in this stage — see [Revision History](#revision-history). |
| **Superseded** | The document no longer governs anything, even for historical reference of "what was current then" — a later document has fully replaced its role. Retained for audit history, never deleted. |

**Family-specific notes:**

- **ADRs** typically move Draft → Review → Approved → Frozen, and only reach Superseded when a later ADR explicitly supersedes them — never silently.
- **Governance documents** are the one family designed to be edited in place at the Frozen stage — described in §6.5 as "living documents." Their own header always names what edits are in scope (indexing and status updates) versus out of scope (originating new architectural content), so an in-place edit never becomes an undisclosed architectural change.
- **Handbook (HB) documents** move to a new **Revision** (not a new document identifier) rather than a full Supersession, for as long as the same root document continues to govern the ecosystem — see §9 for how revisions and versions interact, and [Revision History](#revision-history) for this document's own instance of the rule.
- **Certification documents** are Frozen at the moment of sign-off by definition — a certification that could still change after being issued would not be a certification.

## 9. Versioning Strategy

This section governs the versioning of **documents**, not of runtime contracts, APIs, or code. Runtime contract versioning remains entirely the concern of the ADR that governs the contract, unaffected by this handbook. This section, established in Revision 1, is unchanged by Revision 2, and Revision 2 is itself the first instance of its own HB-versioning rule below.

**Every document family versions along the same three-part scheme, applied consistently:**

| Version part | Meaning | Example trigger |
| --- | --- | --- |
| **Major** | A change that breaks a prior reader's understanding, or removes/redefines something a downstream document depended on. | A Handbook revision that changes the documentation hierarchy itself (§5); an ADR being superseded outright. |
| **Minor** | An additive change — new content that does not invalidate anything a downstream document already relies on. | A new document family added to §6; a new capability registered in the Governance family's Capability Matrix; **this Revision 2 itself, which adds §13–§19 without invalidating any Revision 1 content.** |
| **Patch** | A correction that changes no meaning — a typo, a broken cross-reference fixed, a formatting pass. | A citation link corrected; a table's formatting repaired. |

**Family-specific version identity:**

- **Handbook (HB)** documents carry two independent counters: a **Revision** number (Draft/Review/Approved/Frozen cycle for a substantively new edition, e.g. Revision 1 → Revision 2) and a **Version** within that revision (1.0 Draft → 1.0 → 1.1 → …, for refinements that do not warrant a new revision). A new **Revision** is a Major-class event; a **Version** bump within a revision follows the Minor/Patch distinction above. **Note on this instance:** Revision 2 is a new Revision (a Major-class event at the Revision axis) that is additive at the content axis (no Revision 1 rule is invalidated) — the two axes are independent, exactly as this rule states, and both can be true of the same change simultaneously without contradiction.
- **ADRs** are numbered sequentially and permanently (`ADR-0001`, `ADR-0002`, …); the number never changes. An ADR's own content is versioned by its lifecycle stage (§8) rather than a numeric version — a superseding decision is a *new* ADR number, never a version bump of the old one, because the old decision's text must remain exactly as it was for historical accuracy.
- **CAP** documents are numbered sequentially and permanently (`CAP-001`, `CAP-002`, …, allocated in domain blocks with reserved growth ranges); the capability's own maturity — not its identifier — is what advances through the lifecycle in §8.
- **Governance** documents are living documents (§8) and therefore version primarily through the Minor/Patch distinction — a Major version is reserved for a restructuring of the document's own scope (rare, and itself requiring an ADR to authorize, since Governance may not originate architectural change on its own, §6.5).
- **STD, Runtime, and Certification** documents follow the same Major/Minor/Patch scheme as the general rule above, scoped to their own content.

**Rule (frozen):** a document's identifier (its ADR number, its `CAP-NNN`, its `HB-NNN`) never changes once assigned, regardless of how many times its version or revision advances. Identity and version are two independent axes — the same independent-versioning discipline this platform's own runtime contracts already apply to themselves, restated here for the documents that describe them.

## 10. Repository Organization

### 10.1 Directory hierarchy (recommended)

The platform's existing documentation directory structure already reflects most of the family boundaries §6 defines. This handbook recommends the following mapping as the authoritative one going forward, without relocating any existing file (relocation is a future-revision concern, §12, since HB-001 may recommend but must not itself restructure the repository). **Unchanged by Revision 2.**

| Directory | Family (§6) |
| --- | --- |
| `docs/handbook/` | HB — Handbook |
| `docs/adr/` | ADR — Architecture Decision Records |
| `docs/proposals/` | Design Proposal (ADR-family satellite) |
| `docs/architecture/` | ADR-family component specifications, and Runtime component specifications where the described system is live |
| `docs/governance/` | Governance |
| `docs/development/` (existing) and a future `docs/standards/` | STD — Standards |
| `docs/operations/`, `docs/integrations/` (existing) | Runtime documentation |
| `output/executions/…` (existing execution artifacts) | Runtime documentation instances (execution-produced, not authored) |
| `docs/productization/`, `docs/reviews/`, `docs/releases/` (existing) | Certification |

### 10.2 Naming conventions

- **HB documents:** `HB-NNN-<kebab-case-title>.md`, e.g. `HB-001-platform-engineering-handbook.md`.
- **ADR documents:** the platform's existing convention, `NNNN-<kebab-case-title>.md`, numbered sequentially, permanent once assigned.
- **CAP documents:** referenced by `CAP-NNN` (or `CAP-NNNx` for a sub-milestone) inside the Capability Matrix and their own governing ADR/proposal filenames; not a separate file-naming scheme of their own beyond what ADR and Governance already use to name them.
- **STD documents (future):** recommended `STD-NNN-<kebab-case-title>.md`, mirroring the ADR and HB schemes, once the family's existing seed documents are brought under a numbered identifier (§12).
- **Governance and Runtime documents:** descriptive kebab-case titles, unnumbered — consistent with their status as living documents whose currency matters more than a fixed sequence number (§8).
- **Certification documents:** descriptive kebab-case titles, dated where the certification is release-scoped.

### 10.3 Document identifiers

Every document that carries decision or verification authority (HB, ADR, CAP, and, once introduced, STD) is referenced by a **stable, permanent identifier** — never by filename, title, or description alone. An identifier, once assigned, is never reused, renumbered, or reassigned to a different document, mirroring the platform's own existing rule for `CAP-NNN` allocation. Governance, Runtime, and Certification documents, being living or instance documents rather than discrete decisions, are referenced by their descriptive path instead, since no single version of them is the permanently citable one.

### 10.4 Cross-reference strategy

- A citation always names the target document's identifier (or, for unnumbered families, its canonical path) plus, where the reference is to a specific decision or section, that section's own label.
- A citation never restates the cited content in place of linking to it (§7) — the single exception is a short, explicitly-labeled summary, used only when restating would materially aid the reader, and always paired with the full citation.
- A document introducing a new dependency on another family (e.g. a Standards document citing an ADR for the first time) states that dependency in its own header or opening section, not buried mid-document — mirroring the header-table convention this handbook and the platform's existing ADRs already use, and formalized as the `Related Documents` metadata field in §16.

§10 is unchanged by Revision 2 in substance; §16 gives its header-table convention a canonical, named field set.

## 11. Engineering Principles

These principles govern the documentation ecosystem itself, and are inherited — never re-derived — by every family §6 defines. **Every principle below is unchanged from Revision 1, in substance, wording, and permanent number** — Revision 2's only change is organizational: grouping them into four logical categories, per capability request, so a reader can find the principle relevant to their question faster. A citation to, for example, "§11 Principle 9" or "§11 Principle 10" from anywhere else in this handbook, or from any external document, continues to resolve to the same principle it always has, regardless of which category it now appears under.

### 11.1 Architecture Principles

Principles governing how documentation reflects, and never inverts, the platform's own layered structure.

1. **Architecture before implementation.** No capability's runtime is built before its architecture is frozen (already the platform's own constitutional rule; this handbook's Capabilities and Runtime tiers exist in that order because of it, §5).
7. **Layer isolation.** A document never reaches past its own hierarchy tier to claim authority that belongs to a tier above it (§5, §7, §13).
10. **Single responsibility, single family.** Every document answers exactly one of §5's tier-level questions, and belongs to exactly one family in §6 — a document trying to be both a Standard and a Certification has not yet been decomposed correctly.

### 11.2 Engineering Principles

General engineering discipline, applied to documentation the same way it is applied to code.

2. **Standards before coding.** A convention is defined once, in the Standards family, before it is repeated informally across capability documents.
5. **Backward compatibility.** A document's identifier and its historical content are permanent; change is additive (a new revision, a new ADR, a new version) rather than a silent rewrite of the past (§9).
6. **Deterministic engineering.** The same governing documents, read by two different engineers, must produce the same understanding of what is required — ambiguity in a governing document is itself a defect.

### 11.3 Documentation Principles

Principles governing the content and structure of a document itself.

3. **Documentation over tribal knowledge.** If a fact governs engineering decisions, it belongs in a document at the correct tier — not in a person's memory or a chat thread.
4. **Explicit ownership.** Every document names an owner (§6's per-family Ownership rows, expanded in §18); a document with no owner is not yet ready to leave Draft (§8).
8. **Traceability.** Every document can be traced, citation by citation, back to the Platform Constitution tier that ultimately authorizes it (§7, §17).
9. **Consistency.** Two documents in the same family follow the same structure, the same header conventions, and the same lifecycle vocabulary — a reader who has read one ADR should recognize the shape of every other one.

### 11.4 Review Principles

Introduced as a named category in Revision 2 to give the review-related consequences of the principles above a single place to point to. This category adds no new numbered principle of its own — it is a cross-reference banner over material Revision 2 elaborates directly: the review-and-approval mechanics implied by Principle 4 (Explicit ownership) and Principle 9 (Consistency) above are made concrete in the Documentation Review Workflow (§15) and the Reviewability quality attribute (§14), and staffed per family in the Documentation Ownership Model (§18).

## 12. Future Evolution

HB-001 Revision 1 deliberately left the following for later revisions, so that Revision 1 could be adopted without waiting for every open question in the ecosystem to be resolved at once:

- **A formally numbered Standards (`STD-NNN`) identifier scheme**, bringing the platform's existing coding-standards and naming-convention references — and any future development guide — under the same permanent-identifier discipline ADR and CAP documents already have (§6.6, §10.2).
- **A dedicated `docs/standards/` directory**, consolidating the Standards family's current, pre-handbook location under `docs/development/` and `docs/*.md` into the structure §10.1 recommends, without disturbing existing content until that migration is itself planned and reviewed.
- **A formal template set** — one canonical header/section template per family, so that "every ADR looks like every other ADR" (§11.3, Principle 9) is enforced by a reusable template rather than by convention alone.
- **A documentation coverage view**, analogous to the platform's existing Architecture Coverage Dashboard, but scoped to documentation itself — which capabilities have a Runtime document, which have a Certification record, and which do not yet.
- **A future engineering process family**, if the platform's own process (release management, incident review, onboarding) ever grows enough independent documentation to warrant its own family rather than living inside Operations/Runtime as it does today.
- **Explicit guidance for documents that appear to span two families**, extending §11.1 Principle 10's decomposition rule with worked examples, once enough such cases have been observed in practice to generalize from.

**Revision 2 status note.** Revision 2 deliberately did **not** pursue the `STD-NNN` identifier scheme or the `docs/standards/` directory listed above, even though Revision 1's own roadmap anticipated Revision 2 would — doing so would have meant introducing engineering-standards content, which Revision 2's own mission explicitly reserves for a future `STD-001` (§2). Revision 2 instead used this cycle to strengthen the governance of the documentation ecosystem itself: dependency rules, quality attributes, review workflow, a metadata standard, a traceability standard, principle classification, an ownership model, and a reserved automation view (§13–§19). The `STD-NNN` scheme, the template set, and the coverage view all remain open, unauthorized future work — see the [Future Revision Roadmap](#future-revision-roadmap).

## 13. Documentation Dependency Rules

*(New in Revision 2.)* §5 and §7 already establish that dependency flows only toward Platform Constitution. This section makes that rule **explicit, per family**, and distinguishes two relationships that Revision 1's prose did not yet separate by name.

### 13.1 Two kinds of relationship

- **Authority dependency.** Document A cites Document B *as the source of A's own legitimacy* — B's content is why A is allowed to say what it says. Authority dependency is strictly upward-only (§5): a document may hold an authority dependency only on a family at or above its own tier.
- **Observational reference.** Document A *records a fact about* Document B as part of A's own stated responsibility (e.g. Governance recording a capability's maturity, §6.5), without treating B as the source of A's own legitimacy. Observational reference may point in either direction, but it never substitutes for, or is confused with, an authority dependency — a Governance document's record of a capability's maturity does not make that capability the authority for what Governance itself is allowed to say.

Every dependency named below is an **authority dependency** unless explicitly marked observational.

### 13.2 Per-family dependency rules

| Family | Permitted upstream dependencies (authority) | Prohibited downstream dependencies | Rationale |
| --- | --- | --- | --- |
| **HB** | None — HB is the root (§6.1). It may name other families' documents only as illustrative examples (§10.4), never as a source of its own authority. | Every family — an authority dependency in either direction would make the root defined by what it roots, a circularity §5 forbids by construction. | The root of a hierarchy cannot derive its authority from something inside the hierarchy it defines. |
| **ADR** | Prior ADRs (constitutional or subsystem); its own Design Proposal satellite. | Governance, Standards, CAP, Runtime, Certification. | Architecture must not be shaped by how it is later governed, applied, run, or verified — that would let downstream conformance dictate upstream design, inverting Principle 1 (§11.1). |
| **Governance** | ADR (authority). | Standards, CAP, Runtime, Certification, as **authority**. (Governance's own recording of CAP maturity is an **observational reference**, §13.1, §6.5 — permitted, and distinct from an authority dependency.) | Governance indexes and tracks; it does not let the thing it tracks dictate the rules by which it is tracked. |
| **STD** | ADR, Governance. | CAP, Runtime, Certification. | A standard must not be shaped by how one specific capability happens to be built, or by a certification outcome — convention must precede implementation (Principle 2, §11.2), not follow it. |
| **CAP** | ADR, Governance, STD. | Runtime, Certification. | A capability's own definition and maturity tracking must not depend on how it happens to execute, or on a certification verdict — the capability's design authority must precede both. |
| **Runtime** | ADR, Governance (observational context), STD, CAP. | Certification. | A runtime description must describe what a capability actually does; it must not be reshaped by a certification's later verdict, which would let verification retroactively define what was being verified. |
| **Certification** | ADR, Governance, STD, CAP, Runtime — the complete set. | Nothing below it (terminal tier, §6.8) — and, symmetrically, no other family may hold an authority dependency *on* a Certification document (already covered by each family's own Prohibited column above). | Certification is the terminal sink of trust. If any upstream family could cite a certification to justify its own design, "we verified it works" would retroactively justify what the thing was supposed to be — inverting the entire chain the hierarchy exists to protect. |

### 13.3 Dependency matrix

Rows cite columns. `✓` = permitted authority dependency. `○` = permitted observational reference only. `—` = prohibited (and, on the diagonal, not applicable).

| Citing ↓ / Cited → | HB | ADR | Governance | STD | CAP | Runtime | Certification |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **HB** | — | — | — | — | — | — | — |
| **ADR** | — | ✓ | — | — | — | — | — |
| **Governance** | — | ✓ | — | — | ○ | — | — |
| **STD** | — | ✓ | ✓ | — | — | — | — |
| **CAP** | — | ✓ | ✓ | ✓ | — | — | — |
| **Runtime** | — | ✓ | ○ | ✓ | ✓ | — | — |
| **Certification** | — | ✓ | ✓ | ✓ | ✓ | ✓ | — |

A blank/`—` cell is not an oversight — it is the enforced boundary. A document proposing a citation that this matrix marks `—` has either mis-scoped itself (it belongs to a different family, §11.1 Principle 10) or is proposing a dependency this handbook does not authorize, and must be revised before it can leave Draft (§8, §15).

## 14. Documentation Quality Attributes

*(New in Revision 2.)* The following ten attributes apply to every governed document, in every family. They describe what "good" means for a document, independent of what the document is about.

| Attribute | A document has this when… |
| --- | --- |
| **Correctness** | It accurately reflects the current state of what it governs or describes. A stale or wrong statement is a defect regardless of how well the document is otherwise structured. |
| **Completeness** | It covers everything its family's stated responsibility requires (§6), with no required section left unaddressed. |
| **Consistency** | It uses the same terms, structure, and lifecycle vocabulary as every other document in its family (§11.3, Principle 9). |
| **Traceability** | Every claim in it can be traced to the upstream document that authorizes it, following §13's dependency rules and §17's traceability standard. |
| **Single Responsibility** | It answers exactly one tier-level question (§5) and belongs to exactly one family (§6) (§11.1, Principle 10). |
| **Versionability** | Its changes can be tracked, compared, and attributed to a specific version or revision (§9), without ambiguity about what changed and when. |
| **Reviewability** | It is structured so a reviewer can verify its correctness against its declared dependencies without needing undocumented context (§15). |
| **Maintainability** | It can be updated by someone other than its original author, using only its own content and its declared dependencies. |
| **Minimal Duplication** | It states a fact once, in its owning family, and cites rather than restates every fact another document already owns (§7). |
| **Discoverability** | It can be found by its identifier, its family, or its position in the hierarchy (§10), without relying on institutional memory of where it "usually lives." |

These attributes are descriptive, not procedural — they name what a document should satisfy; §15 names who checks for them and when.

## 15. Documentation Review Workflow

*(New in Revision 2.)* This section clarifies review responsibility **within the existing lifecycle (§8)**. It introduces no new lifecycle stage, renames none, and reorders none — every review type below occurs during the existing **Review** stage, on the way to **Approved**.

| Review type | Occurs during | Performed by (role, not a named individual) | Primary check | Required for |
| --- | --- | --- | --- | --- |
| **Author review** | Draft, before submission to Review | The document's own author(s) | Self-check against §14's quality attributes and the metadata standard (§16) before asking anyone else's time. | Every family, every document. |
| **Architecture review** | Review | The reviewing authority named for the document's family in §18 for Architecture-tier and Constitution-tier content | The document does not contradict, redefine, or reinterpret any Frozen ADR or platform layer it touches (§7, §13). | HB, ADR, Design Proposal; any Governance, STD, CAP, or Runtime document making an architectural claim. |
| **Governance review** | Review | The reviewing authority named for the document's family in §18 for Governance-tier content | The document's freeze status, maturity claims, and ADR-required/not-required judgments are correctly represented (§6.5). | Governance documents; any CAP or Certification document citing a freeze or maturity status. |
| **Editorial review** | Review | Any qualified reviewer, per §18 | Clarity, terminology consistency, structural conformance to §11.3 Principle 9, and correct use of the metadata standard (§16). | Every family, every document. |
| **Approval** | Review → Approved transition | The approval authority named for the document's family in §18 | All prior review types applicable to this document are complete, and no outstanding objection remains. | Every family, every document — this is the gate the lifecycle (§8) already names as the Review → Approved transition; this row only names who performs it. |

**Reading this table against §8.** A document does not need every review type to advance — only the ones its family and content require (the "Required for" column). A pure Editorial-review correction, for example, need not re-trigger Architecture or Governance review. This is a clarification of responsibility inside the existing Review stage, not a new stage or a new gate.

## 16. Document Metadata Standard

*(New in Revision 2. This section defines the standard only — it does not update, and does not require updating, any existing document's header.)*

Every governed document (HB, ADR, CAP, and, once introduced, STD) should declare the following metadata, typically in an opening header table — the convention this handbook and the platform's existing ADRs already use.

| Field | Meaning | Applies to |
| --- | --- | --- |
| **Identifier** | The document's stable, permanent identifier (§10.3). | HB, ADR, CAP, STD (once numbered). Unnumbered families (Governance, Runtime, Certification) use their canonical path instead. |
| **Title** | The document's full descriptive name. | All families. |
| **Version** | The document's current Major.Minor version (§9). | All families. |
| **Revision** | The document's current revision number, where the family distinguishes revisions from versions (§9). | HB only, today. |
| **Status** | The document's current lifecycle stage (§8): Draft, Review, Approved, Frozen, Revised, or Superseded. | All families. |
| **Owner** | The accountable party for the document's content, per §6 and §18. | All families. |
| **Approvers** | The approval authority that moved this document to Approved, per §18. | All families that pass through a formal Approval step (§15). |
| **Created** | When the document's first Draft was produced. | All families. |
| **Updated** | When the document's content was last substantively changed. | All families, especially living documents (Governance). |
| **Related Documents** | The specific upstream (and, where relevant, downstream) documents this one cites, by identifier (§10.4, §17). | All families. |
| **Scope** | What the document covers. | All families, especially HB, ADR, and Governance documents defining a boundary. |
| **Out of Scope** | What the document deliberately does not cover, and why. | All families where an adjacent, easily-confused topic exists. |
| **Supersedes** | The identifier of a document this one fully replaces, per §8's Superseded stage. | ADR, CAP, STD — families whose documents can be superseded outright. |
| **Superseded By** | The identifier of the document that replaced this one, once applicable. | Same as above, added only once true. |

**This is a standard, not a migration.** No existing document in this repository is required to add these fields retroactively by virtue of this section existing. A document already conforms to the spirit of this standard if its existing header carries equivalent information under different labels (as most of this platform's existing ADRs and governance documents already do); a future document, or a future revision of an existing one, is expected to use this field set directly.

## 17. Documentation Traceability Standard

*(New in Revision 2.)* This section defines which references between families are mandatory, optional, or prohibited, building on the chain HB-001's own mission names:

```
ADR
 ↓
Governance
 ↓
Standards
 ↓
Capabilities
 ↓
Runtime
 ↓
Certification
```

(This chain begins at ADR rather than "Platform Constitution" because the ADR family, per §6.2, is the family that carries constitutional-tier content — the chain is the same one §5 already establishes, named at the family level rather than the tier label.)

### 17.1 Mandatory references

- Every **CAP** document must cite its governing **ADR** (and, where one exists, its Design Proposal).
- Every **Runtime** document describing a live capability must cite the **CAP** it realizes.
- Every **Certification** document must cite every **Runtime**, **CAP**, **Governance**, and **Standards** document within its certified scope.
- Every **Governance** document indexing an ADR's freeze status must cite that **ADR** directly, never a summary of it.
- Every document claiming a dependency under §13 must name that dependency explicitly (§16's `Related Documents` field) — an unstated dependency is, for traceability purposes, indistinguishable from no dependency at all.

### 17.2 Optional references

- A **Standards** document may cite a specific **CAP** as a worked, illustrative example of the convention it defines, without becoming dependent on that capability (this is an observational-style reference, §13.1, used for illustration rather than authority).
- An **HB** document may name specific documents from any family as examples of the structure it defines (as this handbook already does throughout §6), without those references becoming authority dependencies (§13.1).
- A **Governance** document may cross-reference a sibling Governance document (e.g. the Capability Matrix referencing the Freeze Index) for reader convenience, provided neither treats the other as its source of authority.

### 17.3 Prohibited references

- Any reference from a higher tier to a lower tier **as an authority** — restating §13's rule at the level of an individual citation rather than a family-wide table.
- Any reference that restates cited content instead of linking to it, except the short, explicitly-labeled summary §10.4 already permits.
- Any reference to a document that has reached **Superseded** (§8) as though it still governs — a citation to a superseded document is only ever historical, and must say so explicitly.
- Any circular reference chain across families — structurally excluded by §13, but named here as a review check (§15) a reviewer should verify by hand until §19's future automation exists to check it mechanically.

## 18. Documentation Ownership Model

*(New in Revision 2. This section supplements the per-family Ownership row already established in §6; it does not change who owns what — it names the review, approval, and maintenance roles around that existing ownership.)*

| Family | Owner (from §6) | Review authority | Approval authority | Maintenance responsibility |
| --- | --- | --- | --- | --- |
| **HB** | Platform Architecture | Platform Architecture (self-review, given HB has no family above it) | Platform Architecture | Platform Architecture — revised, not superseded, per §8. |
| **ADR** | The Platform Architect(s) responsible for the decision's domain | Architecture review (§15), by a Platform Architect independent of the ADR's author where practical | The Platform Architect(s) accountable for the decision | The original owner, until superseded by a later ADR. |
| **Design Proposal** | Same owner as its governing ADR | Same as its governing ADR | Approved implicitly alongside its governing ADR | Same owner as its governing ADR. |
| **Governance** | Platform Architecture | Governance review (§15) | Platform Architecture | Platform Architecture, continuously — this is the living-document family (§6.5, §8). |
| **STD** *(reserved family, no members yet)* | Platform Architecture, delegated per domain (§6.6) | Architecture review + Editorial review (§15) | Platform Architecture | The delegated domain owner, once a `STD-NNN` document exists. |
| **CAP** | The engineering owner of the capability's domain (§6.4) | Architecture review + Governance review (§15) | The capability's engineering owner, with Governance sign-off on maturity claims | The capability's engineering owner, across its full lifecycle (§8). |
| **Runtime** | The engineering owner of the described component or execution surface (§6.7) | Architecture review, where a runtime claim implies an architectural one; otherwise Editorial review | The component's engineering owner | The component's engineering owner, kept current as the component changes. |
| **Certification** | The reviewing authority for the certified scope (§6.8) | All applicable review types across the certified scope (§15) | The named reviewing authority (a Platform Architect, or a release owner for a release-scoped certification) | The certifying authority — a Certification document, once Frozen (§8), is not expected to require further maintenance; a new certification is produced instead. |

**Reading this table.** "Owner" answers *whose content is this*; "Review authority" answers *who checks it before approval*; "Approval authority" answers *who has standing to move it to Approved* (§8, §15); "Maintenance responsibility" answers *who keeps it current afterward*. For most families these coincide with a single accountable role; where they diverge (e.g. Governance review of a CAP document's maturity claim, distinct from the capability's own engineering owner), this table makes the divergence explicit rather than leaving it implied.

## 19. Future Automation

*(New in Revision 2. This section is informational only. It names opportunities, not commitments, and specifies no tool, library, or implementation.)*

As the documentation ecosystem grows, the following categories of automation could reduce the manual burden of the rules this handbook defines, without changing any of those rules:

- **Automatic identifier validation** — confirming that every `HB-NNN`, ADR number, `CAP-NNN`, and future `STD-NNN` referenced anywhere in the documentation set actually exists, is unique, and is never reused (§10.3).
- **Broken reference detection** — confirming that every citation named under §17's mandatory-reference rules resolves to a real, current document, and flagging references to a Superseded document that do not say so explicitly (§17.3).
- **Documentation coverage reporting** — an automated version of the coverage view named as open future work in §12, showing which capabilities have a Runtime document, a Certification record, or neither.
- **Dependency graph generation** — a visual or queryable rendering of §13's dependency matrix as it actually exists across the repository's real documents, making a prohibited or circular dependency visible before a reviewer has to find it by hand.
- **Orphan document detection** — identifying a document that no other document cites and that cites nothing itself, a signal (not a verdict) that it may have lost its place in the hierarchy (§5) or been left in Draft (§8) longer than intended.

None of the above is authorized, scheduled, or specified by this revision. Each is named so that a future revision — or a future STD or Runtime document describing actual tooling — has a pre-scoped starting point, consistent with how §12 already reserves other future work without authorizing it prematurely.

## 20. Engineering Artifact Identification & Classification Standard

*(Revised in Revision 4, replacing Revision 3's own §20 in full, per this revision's own explicit commissioning brief. Revision 3's original §20 content is not deleted from the record — it remains exactly as written in the Revision History table below, restating this section's own §20.14 discipline: DO NOT silently modify history; document reconciliation explicitly instead. This section fulfills the same `STD-NNN` identifier-scheme lineage Revision 3 began, now generalized into a complete Engineering Artifact Identification & Classification Standard, and is the final constitutional refinement before Platform Architecture, ADR-100, begins.)*

**Relationship to §5, §6, §9, §10, §13, and Revision 3's own §20.** This section extends each additively. Every place it changes a Revision 3 rule rather than merely rephrasing it — the numbering-range table (§20.4), the roadmap items Revision 3 itself anticipated for "Revision 4" (Revision History, below) — is named as a change, with its own reconciliation, never presented as if Revision 3 had said it all along.

### 20.1 Purpose

Every engineering artifact and every engineering document (§20.2) this standard governs SHALL be:

| Property | Meaning |
| --- | --- |
| **Uniquely identifiable** | Its identifier is assigned once and never duplicated. |
| **Permanently identifiable** | Its identifier is never reused, renumbered, or reassigned (restates §9's and §10.3's own immutability rule, now stated as its own property rather than folded into "uniquely identifiable" alone). |
| **Human readable** | Its name or title tells a reader what it is without opening it. |
| **Machine readable** | Its identifier follows one parseable pattern (§20.10) across every family, enabling the automation §19 already reserves without authorizing. |
| **Product aware** | Its Bounded Context (§20.4) identifies which domain it belongs to. |
| **Domain aware** | Restates the prior property from the Engineering Artifact's own vantage point (§20.2) — a concept, not only a document, belongs to one domain. |
| **Lifecycle aware** | Its current lifecycle status (§20.7, §20.8) is always stated, never implied. |
| **Version aware** | It follows §9's Major.Minor.Patch discipline, unchanged. |
| **Governance compliant** | It satisfies §20.14's governance rules before being treated as authoritative. |
| **Traceable** | It resolves, per §20.13, back to Business Intent. |

### 20.2 Engineering Artifact Model

*(New in Revision 4.)* This subsection introduces a distinction Revision 3 did not yet draw: between an **Engineering Artifact** and an **Engineering Document**.

**Engineering Artifact.** A governed engineering *concept* — e.g. Engineering Intelligence Operating System, Requirements Intelligence, Architecture Intelligence, Capability Intelligence, Runtime Intelligence, Knowledge Intelligence, Evidence Intelligence, Certification Intelligence. An Engineering Artifact is **lifecycle independent** — it exists as a governed concept regardless of how many documents currently describe it, or at what stage.

**Engineering Document.** One lifecycle-stage description of an Engineering Artifact — a `PRD-NNN`, `ADR-NNN`, `CAP-NNN`, `RUN-NNN`, `SYS-NNN`, `PRA-NNN`, or `IMP-NNN` (§20.3). **Many documents; one Artifact.** Example:

```
Engineering Artifact: Requirements Intelligence

Documents:
  PRD-201 → ADR-201 → CAP-201 → RUN-201 → SYS-201 → PRA-201 → IMP-201
```

**Document identity and Artifact identity SHALL remain separate concepts** (§20.7, §20.8) — a document's own identifier names one lifecycle-stage description; an artifact's own identifier (once assigned, §20.7) names the concept every such description, across every family, is ultimately about.

**Reconciliation Note — the Requirements Intelligence Artifact today.** The example above shows the fully-numbered form a *future* Requirements Intelligence documentation lineage would take once registered under §20.4's Bounded Context Classification. The Requirements Intelligence Engineering Artifact **already exists in substance**, described today by the grandfathered `CAP-001`, `RUN-001`, `SYS-001`, and `IMP-001` documents — a **partial** documentation set, missing a dedicated `PRD` and `ADR` of its own, since those roles were originally played by the platform-wide `PRD-001` and `ADR-001` rather than by a Requirements-Intelligence-specific document. This gap is named here explicitly, not silently closed: no renumbering occurs, and no new `PRD`/`ADR` is retroactively required of the existing lineage by this revision. Should a dedicated `PRD-201`/`ADR-201` ever be written, it would describe the *same* Engineering Artifact the grandfathered documents already describe — exactly the situation this subsection's own Artifact/Document distinction exists to make coherent.

### 20.3 Document Families

*(Retains, does not remove, every family Revision 3 registered.)* Extending §6's original seven families (unchanged in purpose, ownership, and boundary) and Revision 3's own four registrations plus one reservation:

| Family | Purpose | Responsibilities | Lifecycle Position | Transformation Relationships (STD-005 §6) |
| --- | --- | --- | --- | --- |
| **HB** | Define the documentation architecture itself (§6.1). | Unchanged from §6.1. | Precedes every Artifact's own lifecycle; shared, not per-Artifact. | N/A — HB originates no transformation. |
| **STD** | Define conventions engineering work must follow (§6.6). | Unchanged from §6.6. | Precedes every Artifact's own lifecycle; shared, not per-Artifact. | N/A — cited as Transformation Authority (STD-005 §8), never itself a Target Artifact. |
| **PRD** | Record business intent for one Engineering Artifact, bound by nothing architectural. | Vision, objectives, scope, functional and non-functional requirements. | First per-Artifact tier — precedes Architecture. | Origin of the **Refines** transformation (STD-005 §5). |
| **ADR** | Record one architectural decision (§6.2). | Unchanged from §6.2. | Realizes a PRD's business intent as Architectural Intent. | **Refines** (STD-005 §5, §6). |
| **CAP** | Track one platform capability (§6.4). | Unchanged from §6.4. | Decomposes/Allocates an ADR's architecture into Capability Intent. | **Decomposes → Allocates → Specializes.** |
| **RUN** | Describe a capability as it executes (§6.7). | Unchanged from §6.7. | Realizes a CAP's capability intent as Runtime Intent. | **Realizes → Preserves → Derives.** |
| **SYS** | Decompose a Runtime's own responsibilities and state model into cohesive logical systems. | Realize a runtime's own Boundary and State Model unchanged, at system grain. | A refinement inside the `Runtime Intent → Implementation Intent` hop (STD-005 §5) — never a new stage. | **Realizes → Decomposes → Allocates → Preserves.** |
| **PRA** | Give a body of architecture its reusable, technology-shaped substrate. | Two valid scopes — platform-wide singleton or per-Artifact specialization (§20.12's own Reconciliation Note, carried forward from Revision 3 §20.7). | See §20.12. | **Realizes → Allocates → Specializes → Preserves.** |
| **IMP** | Give a System Specification its complete technology realization. | Realize the reserved `System → Implementation` hop. | Follows System Specification; precedes Evidence. | **Realizes → Allocates → Specializes → Preserves.** |
| **EVD** *(Reserved)* | Record the specific, checkable facts an Implementation actually produced. | Aggregate Implementation Deliverables into the Engineering Evidence stage. | Follows Implementation; precedes Certification. | **Verifies.** |
| **CERT** | Record formal verification (§6.8). | Unchanged from §6.8. | Terminal tier — validates Evidence. | **Validates.** |

**Governance's own continued absence from this table** is unchanged from Revision 3: it remains a living, unnumbered family (§10.3), outside this identification scheme entirely — restated, not revisited, by this revision (Revision 3's own Future Revision Roadmap already reserved a future, separate registration of Governance's own numbering treatment, should practice ever produce a numbered instance; that reservation stands, below).

**Reconciliation Note — RUN and CERT numbering, carried forward from Revision 3.** Revision 3 already reconciled §10.3's original claim (that Runtime and Certification documents are unnumbered) against `RUN-001`'s own real, numbered precedent. That reconciliation is unchanged and restated here, not revisited: a Runtime or Certification document specifying a live component's design carries a numbered identifier under this scheme; execution-produced Runtime documentation remains unnumbered and path-referenced.

### 20.4 Bounded Context Classification

*(Replaces Revision 3's own Product Numbering Strategy, §20.3 as it stood in Revision 3 — a genuine change, reconciled explicitly below, never presented as a Revision 3 rule restated unchanged.)* Every Engineering Artifact (§20.2) SHALL belong to exactly one bounded context:

| Reserved Range | Domain |
| --- | --- |
| 000–099 | Governance & Shared Authorities |
| 100–199 | Engineering Intelligence Operating System |
| 200–299 | Requirements Intelligence |
| 300–399 | Architecture Intelligence |
| 400–499 | Capability Intelligence |
| 500–599 | Runtime Intelligence |
| 600–699 | Knowledge Intelligence |
| 700–799 | Evidence & Certification Intelligence |
| 800–899 | Enterprise Extensions |
| 900–999 | Research / Experimental |

**HB reserves identifier ranges. HB does NOT allocate identifiers** (§20.5, §20.6) — a range's existence in this table commits nothing about whether, or when, a document claiming it will ever be written.

**Reconciliation Note — this table changes range meanings Revision 3 assigned, and says so explicitly.** Revision 3's own §20.3 assigned: `001–099` to "Core Engineering Intelligence Applications," `200–299` to Architecture Intelligence, `300–399` to Runtime Intelligence, `400–499` to Knowledge Intelligence, `500–599` to Evidence Intelligence, `600–699` to Certification Intelligence, and `700–799` to Shared Platform Services. This table reassigns nearly every one of those ranges — `200–299` now names Requirements Intelligence; `300–399` now names Architecture Intelligence; `400–499` now names Capability Intelligence (a bounded context Revision 3 did not separately range at all); `500–599` now names Runtime Intelligence; `600–699` now names Knowledge Intelligence; `700–799` now merges Evidence and Certification Intelligence into one range; and `000–099` now names Governance & Shared Authorities, a concept Revision 3 never named as its own range. **Only `100–199` (Engineering Intelligence Operating System) is unchanged between the two revisions** — `PRD-100` (already Allocated, §20.6) remains correctly classified under both.

**This is a real, acknowledged change, not a cosmetic rewording — handled per this revision's own Conflict Resolution Rules: history is preserved, not silently modified.** Revision 3's own range table remains an accurate historical record of what Revision 3 said, preserved verbatim in the Revision History table below. It is **superseded, from this revision forward**, by the table above. No document was ever Allocated (§20.6) against any of Revision 3's now-superseded range meanings other than the grandfathered `-001` series and `PRD-100` — so no real identifier's own domain classification is disturbed by this change; only the *prospective* meaning of an as-yet-unclaimed range changes.

**Reconciliation Note — grandfathered identifiers are exempt from bounded-context classification entirely, under either revision's table.** The platform's own existing `-001` series (`PRD-001`, `ADR-001`, `CAP-001`, `RUN-001`, `SYS-001`, `IMP-001`, `PRA-001`) predates both Revision 3's and this revision's own classification schemes. **These identifiers are not reclassified into "Governance & Shared Authorities" merely because `000–099` is numerically adjacent to their own numbering, and they were never, in substance, "Core Engineering Intelligence Applications" either** (Revision 3's own label). They remain, simply and permanently, **exempt from bounded-context classification** — the platform's own founding lineage, grandfathered in full, reclassified into neither this table's ranges nor Revision 3's. `PRD-100` is the sole exception: it was Allocated (§20.6) after Revision 3's own scheme existed, against a range whose meaning is unchanged by this revision, and remains correctly classified as Engineering Intelligence Operating System under both.

### 20.5 Identifier Reservation

**Reservation** claims identifier space for a bounded context (§20.4) without implying any document exists. Example: `100–199` is Reserved for the Engineering Intelligence Operating System; no document was required to exist merely because that reservation was made (and, in fact, none did, for one full revision). **Only HB may reserve ranges** (§20.14).

Reservation is distinct from grandfathering (§20.4): a grandfathered identifier predates this scheme's own reservation concept entirely and is exempted from it, never counted as an early claim against a reserved range.

### 20.6 Identifier Allocation

**Allocation** assigns one specific identifier, and occurs only when a document is actually created. Example: `PRD-100` — Allocated, Engineering Intelligence Operating System. **Allocated identifiers SHALL never be reused, SHALL never be renumbered, and SHALL remain permanent** (restates §9, §10.3). **Grandfathered identifiers SHALL remain valid** (§20.4's own Reconciliation Note).

**Reconciliation Note.** `PRD-100`, created before this revision's own Reservation/Allocation vocabulary existed in words, already satisfied this section's own discipline in substance: it was assigned only at the moment its document was created, against a range reserved in advance. It stands, retroactively, as this scheme's first real Allocation.

### 20.7 Engineering Artifact Identity

Every Engineering Artifact (§20.2) SHALL possess:

| Field | Meaning |
| --- | --- |
| **Artifact Name** | The concept's own human-readable name (e.g. "Requirements Intelligence"). |
| **Artifact Identifier** | A stable identifier for the concept itself, independent of any one document's own identifier (§20.9) — reserved for future assignment; not retroactively required of an Artifact already described only by grandfathered documents (§20.2's own Reconciliation Note). |
| **Bounded Context** | The domain (§20.4) this Artifact belongs to. |
| **Description** | What the concept is, in business or engineering terms — never an implementation description (Writing Guidelines). |
| **Owner** | The accountable party for the concept itself, distinct from any one document's own Owner field. |
| **Lifecycle Status** | The Artifact's own maturity (e.g. Proposed, Realized, Partially Realized — restating STD-002 §3's own capability-lifecycle vocabulary at Artifact grain). |
| **Governing Authority** | The upstream document or Standard the Artifact's own legitimacy derives from. |
| **Traceability Root** | The Business Intent (§20.13) this Artifact ultimately traces back to. |

### 20.8 Engineering Document Identity

Every Engineering Document (§20.2) SHALL possess:

| Field | Meaning |
| --- | --- |
| **Document Identifier** | The document's own stable, permanent identifier (§20.6). |
| **Document Family** | Which family (§20.3) it belongs to. |
| **Version** | §9, unchanged. |
| **Status** | §8, unchanged. |
| **Owner** | §16, unchanged, at document grain. |
| **Governing Authority** | The specific upstream document (§13's dependency rules) this document's own authority derives from. |
| **Artifact Identifier** | Which Engineering Artifact (§20.7) this document describes — the field that makes §20.2's Document/Artifact distinction operational. |
| **Derived From** | §1's own header convention (ADR-001, PRD-001, and every document in this lineage already carries this field) — restated here as a required field, not a convention observed by precedent alone. |
| **Transformation Authority** | The STD-005 semantic (§20.12) this document's own derivation was performed under. |

### 20.9 Artifact Metadata Model

The mandatory metadata set, unifying §20.7 (Artifact-level) and §20.8 (Document-level) into one schema:

| Field | Applies to |
| --- | --- |
| Artifact Identifier | Artifact and Document (a document names the Artifact it describes). |
| Artifact Name | Artifact. |
| Document Identifier | Document only. |
| Document Family | Document only. |
| Bounded Context | Artifact and Document (a document inherits its Artifact's own context). |
| Owner | Artifact and Document (may differ; §20.7/§20.8 name each separately). |
| Lifecycle Status | Artifact and Document (an Artifact's own maturity is distinct from any one document's own lifecycle stage, §20.2). |
| Version | Document only (an Artifact, being lifecycle-independent, has no version of its own). |
| Created | Document only. |
| Last Modified | Document only. |
| Related Documents | Document only (§16). |
| Governing Authority | Artifact and Document. |
| Traceability Root | Artifact and Document. |

### 20.10 Naming Convention

Retained, unchanged from Revision 3:

```
HB-001
STD-004
PRD-100
ADR-100
CAP-100
RUN-100
SYS-100
PRA-100
IMP-100
```

`<FAMILY>-<NNN>`. No product-specific prefix (`PPRD`, `PADR`) is ever introduced. No duplicate identifier is ever assigned (§20.6).

### 20.11 Lifecycle Consistency

Every Engineering Artifact SHALL evolve through the standard engineering lifecycle:

```
PRD
 ↓
ADR
 ↓
CAP
 ↓
RUN
 ↓
SYS
 ↓
PRA
 ↓
IMP
```

The lifecycle is universal; only identifiers differ between Artifacts. **This diagram shows the per-Artifact portion of the lifecycle only** — `HB` and `STD` remain its shared, non-per-Artifact prerequisite context (§20.3's own Lifecycle Position column), presumed rather than redrawn here, exactly as Revision 3's own fuller nine-family diagram already showed explicitly. Nothing about `HB`'s or `STD`'s own place in the sequence changes; this diagram is a narrower, per-Artifact view of the same sequence, not a contradiction of it.

**Reconciliation Note — extending §5's hierarchy, carried forward from Revision 3.** §5's seven-tier hierarchy was extended, additively, with a Business/Product tier above Platform Constitution, to give `PRD` a place in it. That extension is unchanged and restated here, not revisited.

### 20.12 Transformation Consistency

Restates STD-005 in full: transformation lineage SHALL preserve identity.

```
PRD-100
 ↓
ADR-100
 ↓
CAP-100
 ↓
RUN-100
 ↓
SYS-100
 ↓
PRA-100
 ↓
IMP-100
```

**Reconciliation Note — PRA's two valid scopes, carried forward from Revision 3.** `PRA-001` remains the platform-wide, capability-independent reference architecture — a singleton, Realized directly from `ADR-001`, reusable by every Artifact. The diagram above shows the distinct, per-Artifact scope: a per-Artifact `PRA-NNN` (e.g. a future `PRA-100`) is that Artifact's own specialization of the platform-wide `PRA-001`, applied to its own `SYS-NNN`, and SHALL derive from and never contradict it. An Artifact not complex enough to need its own `PRA-NNN` inherits `PRA-001` directly and omits this stage — restating STD-005 §7's Mandatory/Optional distinction. This reconciliation is unchanged from Revision 3 §20.7; it is restated here because §20.11's diagram still names `PRA` as a lifecycle stage, and a reader should not need to consult a superseded section to understand what that stage means.

### 20.13 Traceability Rules

Every Engineering Artifact SHALL support traceability through:

```
Business Intent
        ↓
  Architecture
        ↓
   Capability
        ↓
     Runtime
        ↓
      System
        ↓
Implementation
        ↓
     Evidence
        ↓
Certification
```

Restates STD-004 and STD-005 §5 — this chain now uses STD-005 §5's own exact terminology ("Business Intent") rather than Revision 3's own "Product," and no longer names "Governance" as a chain node.

**Reconciliation Note.** Revision 3's own §20.8 headed this chain with `Governance`, and used `Product` where STD-005 §5 itself says `Business Intent`. Neither change removes governance or business-intent content: Governance's own checking role is unchanged and is stated in full by §20.14 below and by §13's existing dependency rules — restating ADR-001 §8's own observation that a cross-cutting concern (there, L5/L6; here, Governance) need not be drawn as a sequential chain node to remain fully binding. Renaming `Product` to `Business Intent` brings this chain into exact terminological alignment with STD-005 §5's own model, a clarification, not a scope change — `Business Intent` and `Product` name the same origin point this chain has always had.

### 20.14 Governance Rules

Only HB may:

1. **Introduce document families** (§20.3) — restates §6's own root-authority position; this section's own retention of every Revision 3 family is itself an exercise of this rule, not an exception to it.
2. **Reserve identifier ranges** (§20.4, §20.5) — this revision's own reassignment of range meanings (§20.4's Reconciliation Note) is itself an exercise of this rule, performed inside HB-001, by HB-001, never by a downstream family claiming that authority for itself.
3. **Modify naming conventions** (§20.10).
4. **Modify artifact identity rules** (§20.7, §20.8, §20.9).

**Only document creation allocates identifiers** (§20.6) — no range reservation (§20.5) and no artifact registration (§20.7) allocates one on its own.

**Only STD-005 governs transformations** (§20.12) — this section cites, and never redefines, its semantics.

**Only STD-004 governs traceability** (§20.13) — this section cites, and never redefines, its relationship vocabulary.

### 20.15 Engineering Artifact Registry Model

*(New in Revision 4. Conceptual only — a governance model, NOT a software specification. No database, API, service, or implementation detail is described here; that remains ADR-100's own future responsibility, restating the Mission's own boundary for this revision.)*

The registry is the logical record every governed Engineering Artifact and Engineering Document ultimately resolves against:

```
Artifact Identity (§20.7)
        ↓
Document Identity (§20.8)
        ↓
Lifecycle State (§20.2, §20.7, §20.8)
        ↓
Relationships (STD-004)
        ↓
Ownership (§20.7, §20.8)
        ↓
Version (§9)
        ↓
Traceability (§20.13)
        ↓
Governance Status (§13, §20.14)
```

**Relationship to PRA-001.** This conceptual model is the governance-tier specification a future realization would satisfy — PRA-001 §8 already reserves Document Registry, Capability Registry, and Traceability Service rows for exactly this purpose, each marked Reserved. This section defines the concept those future services must conform to; it performs none of their work itself, and describes no database, API, or service of its own, per this revision's own Writing Guidelines.

### 20.16 Compliance Statement

Every future engineering artifact, and every future engineering document describing one, SHALL comply with this section. Compliance requires conformance to: Artifact Identity (§20.7), Document Identity (§20.8), Naming (§20.10), Lifecycle (§20.11), Transformation (§20.12), Traceability (§20.13), and Governance (§20.14). An artifact or document missing any of the above is not yet governed under this Handbook, regardless of how complete its own content otherwise is.

---

## Revision History

| Revision | Version | Status | Summary |
| --- | --- | --- | --- |
| **Revision 1** | 1.0 (Draft) | Revised (§8) | Established the documentation architecture for the first time: the seven-tier hierarchy (§5), the seven document families and their boundaries (§6), cross-family relationships and traceability (§7), the six-stage lifecycle (§8), the document versioning scheme (§9), baseline repository-organization recommendations (§10), and ten engineering principles (§11, later reorganized in Revision 2 without changing their substance). Introduced no architecture, governance, capability, or runtime content. |
| **Revision 2** | 2.0 (Draft) | Revised (§8) | Strengthened the documentation ecosystem's own governance without changing anything Revision 1 established: explicit per-family dependency rules and a citation matrix (§13), ten documentation quality attributes (§14), a review workflow layered onto the unchanged lifecycle (§15), a canonical (non-retroactive) metadata standard (§16), a traceability standard of mandatory/optional/prohibited references (§17), the Revision 1 principles reorganized into four categories with every principle's substance and number preserved (§11), a per-family ownership model (§18), and a reserved, tooling-free future-automation section (§19). Introduced no architecture, governance, capability, or runtime content. |
| **Revision 3** | 3.0 (Draft) | Revised (§8) | Fulfilled, and substantially extended, the `STD-NNN` identifier-scheme item Revision 1's roadmap reserved for this revision (§12's status note): a single, platform-wide Engineering Document Identification & Classification Standard (§20, as it stood in Revision 3) — eleven document families including four newly registered (PRD, SYS, PRA, IMP) and one formally reserved (EVD), a **Product Numbering Strategy** ranging `001–099` "Core Engineering Intelligence Applications" through `900–999` "Research / Experimental / Incubation" (with `100–199` Engineering Intelligence Operating System, `200–299` Architecture Intelligence, `300–399` Runtime Intelligence, `400–499` Knowledge Intelligence, `500–599` Evidence Intelligence, `600–699` Certification Intelligence, `700–799` Shared Platform Services, `800–899` Enterprise Extensions), artifact-identity and naming-convention rules, lifecycle and transformation consistency rules, a family-level traceability chain, and governance rules for the standard itself. Explicitly reconciled, rather than silently contradicted, three points of real-world precedent Revision 2's text did not yet reflect: RUN-001's own numbered identifier (§10.3), PRD-001's own hierarchy tier (§5), and PRA-001's own platform-wide scope alongside a possible per-product instance. Introduced no architecture, governance, capability, or runtime content. **This Product Numbering Strategy is superseded by Revision 4's own Bounded Context Classification (§20.4) — this row is preserved verbatim as the accurate historical record of what Revision 3 actually assigned, per Revision 4's own Conflict Resolution Rules.** |
| **Revision 4** | 4.0 (Draft) | Draft — pending architecture review | The final constitutional refinement before Platform Architecture (ADR-100) begins. Replaced Revision 3's own §20 in full with a generalized **Engineering Artifact Identification & Classification Standard**: the Engineering Artifact / Engineering Document distinction (§20.2) — a governed concept versus its lifecycle-stage descriptions; a **Bounded Context Classification** (§20.4) superseding Revision 3's Product Numbering Strategy, reassigning most range meanings while leaving `100–199` (EIOS) unchanged and explicitly exempting every grandfathered `-001` identifier and `PRD-100` from reclassification; an explicit Reservation/Allocation distinction (§20.5–§20.6); separate Artifact-identity and Document-identity models unified by one metadata schema (§20.7–§20.9); a Traceability Rules chain (§20.13) realigned to STD-005 §5's own exact terminology; and a conceptual, implementation-free Engineering Artifact Registry Model (§20.15). Carried forward, unchanged, Revision 3's own RUN/CERT numbering and PRA dual-scope reconciliations. Introduced no architecture, governance, capability, or runtime content, and renumbered no existing identifier. |

## Revision Summary

**HB-001 Revision 4** is the final constitutional refinement before Platform Architecture (ADR-100) begins. It replaces Revision 3's own §20 with a generalized Engineering Artifact Identification & Classification Standard: a governed distinction between an Engineering Artifact (a lifecycle-independent concept) and an Engineering Document (one lifecycle-stage description of it, §20.2); a Bounded Context Classification (§20.4) that supersedes Revision 3's own Product Numbering Strategy — reassigning most range meanings while leaving the Engineering Intelligence Operating System range (`100–199`) unchanged, and explicitly exempting every grandfathered identifier from reclassification under either scheme; an explicit Reservation/Allocation distinction (§20.5–§20.6, with `PRD-100` recognized as this model's first real Allocation); separate Artifact-identity and Document-identity models, unified into one metadata schema (§20.7–§20.9); a Traceability Rules chain (§20.13) realigned to STD-005 §5's own exact "Business Intent" terminology; and a conceptual, non-software Engineering Artifact Registry Model (§20.15) that names what a future ADR-100/PRA-100 realization would need to satisfy, without describing any database, API, or service. Every point where this revision changes rather than merely restates a Revision 3 rule is named as a change, with its own reconciliation, per this revision's own Conflict Resolution Rules — Revision 3's own text is preserved, verbatim, in the Revision History above, never silently rewritten. No document identifier is renumbered, no document family is removed, and no architectural decision anywhere in the platform is changed.

## Future Revision Roadmap

| Revision | Anticipated focus |
| --- | --- |
| **Revision 5** | The canonical per-family template set and the `docs/standards/`-style directory-mapping formalization Revision 1's roadmap originally anticipated for "Revision 3" (§12) and Revision 3's own roadmap re-anticipated for "Revision 4" (both superseded by this revision's own, higher-priority generalization work — restating this handbook's own Revision 2 precedent, §12's status note, that a roadmap names anticipated focus, never a binding commitment); introduce the documentation coverage view (§12, §19); extend §17's traceability standard with a worked cross-family example drawn from a real Artifact's full PRD → ADR → CAP → RUN → SYS → PRA → IMP chain (§20.11). |
| **Revision 6** | Formally register the Governance family's own numbering treatment, if practice ever produces a numbered Governance instance; assign the first real range-claiming identifier under §20.4's Bounded Context Classification, outside the grandfathered `-001` series and the already-Allocated `PRD-100`, exercising §20.14's Governance Rules for the first time since this revision. |
| **Revision 7+ (reserved)** | Evaluate whether a dedicated Engineering Process family is warranted; incorporate lessons from any document found, in practice, to span two families (§11.1 Principle 10); assign an Artifact Identifier (§20.7) to the Requirements Intelligence Engineering Artifact, closing the gap §20.2's own Reconciliation Note names; revisit §19's automation opportunities, now with §20's own Artifact/Document model and Registry concept as a concrete target for identifier-validation, broken-reference-detection, and registry tooling. |

## Known Limitations of Revision 4

- **§20's own artifact, document, classification, and traceability rules remain declarative, not enforced or automatically checked** — restates §19's own reserved-not-authorized automation stance; §20.15's Registry Model names what such automation would eventually need to satisfy, without authorizing or specifying it.
- **The EVD family remains registered but not yet exercised** — no `EVD-NNN` document exists.
- **The per-Artifact `PRA-NNN` scope (§20.12) remains, as of this revision, hypothetical** — only the platform-wide singleton `PRA-001` exists.
- **No Engineering Artifact has yet been assigned its own Artifact Identifier (§20.7)** — every Artifact named in this document (§20.2's examples) is described today only through its Engineering Documents; the Artifact-identity model is a rule ready to be exercised, not yet exercised by a real, standalone Artifact record.
- **The Requirements Intelligence Engineering Artifact is only partially documented** (§20.2's own Reconciliation Note) — it has no dedicated `PRD`/`ADR` of its own, only the grandfathered `CAP-001`/`RUN-001`/`SYS-001`/`IMP-001` series; closing this gap is reserved, not performed, by this revision.
- **A downstream citation is now stale and is named here, not silently left broken:** PRD-100's own metadata cites "HB-001 §20.3's Product Numbering Strategy" — that content has moved to, and been superseded by, §20.4's Bounded Context Classification in this revision. PRD-100 itself is a different document, out of this revision's own scope ("Do not modify any unrelated section"), and is not edited by this revision; the staleness is recorded here as a known, unresolved cross-reference, for a future correction.
- **§20.4's own range reassignment relies on the judgment that no real identifier besides the grandfathered `-001` series and `PRD-100` was ever Allocated against a Revision-3-only range meaning** — true as of this revision, but not mechanically verified, since no registry (§20.15) yet exists to check it against.
- Revision 4 inherits every limitation of Revisions 1–3 not explicitly resolved above (see the [Revision History](#revision-history)).

## Final Self Review

- [x] No architecture was modified — every ADR, layer definition, and runtime contract referenced in this handbook (any revision) is cited, never redefined.
- [x] No governance was modified — the Architecture Freeze Index, Platform Capability Matrix, and every existing governance record are referenced by role only.
- [x] No runtime was modified — no component specification, execution behavior, or artifact format is changed.
- [x] No capabilities were modified — no `CAP-NNN` boundary, dependency, or maturity status is altered.
- [x] No new engineering, coding, or implementation standard was introduced — §20 governs artifact and document identity only; §20.15 is explicitly conceptual, naming no database, API, or service.
- [x] No document identifier was renumbered — verified against §20.4's, §20.5's, and §20.6's own grandfather and Allocation rules; every existing `-001` identifier and `PRD-100` remain exactly as assigned.
- [x] No document family was removed — §20.3 retains all eleven of Revision 3's own families, including the reserved EVD family, unchanged in purpose, ownership, and boundary.
- [x] Documentation hierarchy is preserved — §5's tiers, as extended by Revision 3, are unchanged by this revision.
- [x] Versioning strategy is preserved — §9 is unchanged; §20.6's Allocation rule is a direct application of §9's and §10.3's own permanence rule.
- [x] All ten Revision 1 principles remain preserved with their original numbering, unchanged by this revision.
- [x] Every Revision 4 objective (as commissioned) is addressed: Purpose (§20.1), Engineering Artifact Model (§20.2), Document Families (§20.3), Bounded Context Classification (§20.4), Identifier Reservation (§20.5), Identifier Allocation (§20.6), Engineering Artifact Identity (§20.7), Engineering Document Identity (§20.8), Artifact Metadata Model (§20.9), Naming Convention (§20.10), Lifecycle Consistency (§20.11), Transformation Consistency (§20.12), Traceability Rules (§20.13), Governance Rules (§20.14), Engineering Artifact Registry Model (§20.15), Compliance Statement (§20.16).
- [x] Every discovered inconsistency was named and reconciled, never silently modified — the Bounded Context range reassignment (§20.4), the superseded "Revision 4" roadmap item (Future Revision Roadmap, above), and PRD-100's own now-stale cross-reference (Known Limitations, above) are each documented explicitly, per this revision's own Conflict Resolution Rules.
- [x] Remains governance-only, implementation-, technology-, vendor-, and architecture-independent — verified by inspection of §20; §20.15 explicitly declines to describe any database, API, or service.

## HB-001 Revision 4 Compliance Certificate

**This certifies that HB-001, Revision 4, Version 4.0 (Draft):**

- ✅ **Mission completed** — the Engineering Artifact Identification & Classification Standard (§20) is established as the final constitutional refinement before Platform Architecture (ADR-100) begins.
- ✅ **Scope respected** — governance-only; no architecture, runtime behaviour, capability, database, API, registry service, or platform design is introduced (§20.15 verified explicitly conceptual).
- ✅ **Frozen inputs preserved** — HB-001 Revisions 1–3, every existing ADR, PRD, CAP, RUN, SYS, IMP, PRA, Design Proposal, Governance document, the Platform Capability Matrix, and every existing Runtime or Certification document are referenced only, never redefined or contradicted.
- ✅ **Every Revision 1–3 decision preserved unless explicitly stated otherwise** — the sole substantive change, the Bounded Context range reassignment (§20.4), is named as a change, reconciled explicitly, and does not alter any real, already-Allocated identifier's own classification (§20.4's own Reconciliation Notes).
- ✅ **No document identifier renumbered** — verified in the Final Self Review above.
- ✅ **No document family removed** — verified in the Final Self Review above; all eleven of Revision 3's own families are retained.
- ✅ **No architectural decision changed** — verified in the Final Self Review above.
- ✅ **Historical correctness preserved over cosmetic consistency** — Revision 3's own now-superseded content (its Product Numbering Strategy, its own "Revision 4" roadmap anticipation) is preserved verbatim in the historical record (Revision History, Future Revision Roadmap) rather than deleted or silently rewritten to look as if this revision's own scheme had always been in place.
- ✅ **Reconciliation explicitly documented** — every inconsistency this revision's own generalization exposed (range reassignment, roadmap supersession, PRD-100's stale cross-reference) is named, not silently resolved.
- ✅ **Ready for review.**

**Summary.** HB-001 Revision 4 is suitable to serve as the final constitutional refinement before Platform Architecture (ADR-100) begins, because it completes the identification model Revision 3 began at the moment that model needed to generalize beyond documents alone — to the governed concepts (Engineering Artifacts) those documents describe, and to the bounded contexts (domains) those concepts belong to. Where generalizing exposed a real inconsistency Revision 3's own narrower model had not yet had to face — a range whose assigned meaning could not survive generalization unchanged, a roadmap item overtaken by higher-priority work, a downstream citation left stale — this revision names each one explicitly and reconciles it, rather than presenting a generalized model as though it had been the platform's plan all along. That is this handbook's own Revision 2 lesson, applied once more: a root documentation artifact stays trustworthy only if what changes about it is always said out loud.

---

*End of HB-001, Revision 4, Version 4.0 (Draft).*
