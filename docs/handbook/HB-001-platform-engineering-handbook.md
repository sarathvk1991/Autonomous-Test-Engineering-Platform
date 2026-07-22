# HB-001 — Platform Engineering Handbook

**Revision 3 · Version 3.0 (Draft)**

| Attribute | Value |
| --------- | ----- |
| Document ID | HB-001 |
| Document family | Handbook (HB) |
| Revision | 3 |
| Version | 3.0 (Draft) |
| Document type | Documentation Architecture — Root Reference |
| Status | Draft — pending architecture review |
| Owner | Platform Architecture |
| Governs | The documentation ecosystem of the entire engineering platform |
| Governed by | Nothing — HB-001 is the root of the documentation hierarchy it defines |
| Supersedes | Nothing (HB-001 revises itself; it does not supersede a different document) |
| Prior revision | HB-001 Revision 2, Version 2.0 (Draft) — now **Revised** (§8); see [Revision History](#revision-history) |
| Implementation independence | This handbook contains no language, framework, or AI-provider-specific guidance. It describes documents, not code. |

> HB-001 is not an implementation guide and not a governance document. It is the
> **documentation architecture** of the platform — the single reference that
> explains what kinds of engineering documents exist, what each one is
> responsible for, how they relate to one another, and how a reader or a new
> document finds its correct place in the ecosystem. Revision 1 established that
> architecture. Revision 2 strengthened it with the governance rules that keep
> the documentation ecosystem itself consistent as the platform evolves —
> dependency rules, quality attributes, review responsibilities, a metadata
> standard, a traceability standard, a classified principle set, an ownership
> model, and a reserved view of future automation. **Revision 3 fulfills the
> `STD-NNN` identifier-scheme item Revision 1's own roadmap reserved for this
> revision (§12's status note) — and substantially extends it** into a single,
> platform-wide **Engineering Document Identification & Classification
> Standard** (§20), now that STD-000 through STD-005 and a growing Derivative
> series (PRD-001, ADR-001, CAP-001, RUN-001, SYS-001, IMP-001, PRA-001) exist to
> generalize an identifier scheme from. Revision 3 changes no architecture,
> governance, capability, or runtime decision anywhere in the platform; where it
> extends a Revision 1 or Revision 2 rule (the family catalogue, §6; the
> hierarchy, §5; the numbered-identifier rule, §10.3), it does so additively and
> says so explicitly (§20), never by silent rewrite.

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
20. [Engineering Document Identification & Classification Standard](#20-engineering-document-identification--classification-standard)
- [Revision History](#revision-history)
- [Revision Summary](#revision-summary)
- [Future Revision Roadmap](#future-revision-roadmap)
- [Known Limitations of Revision 3](#known-limitations-of-revision-3)
- [Final Self Review](#final-self-review)
- [HB-001 Revision 3 Compliance Certificate](#hb-001-revision-3-compliance-certificate)

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

**Intentionally out of scope for HB-001 (Revision 1, Revision 2, and Revision 3, all three):**

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

## 20. Engineering Document Identification & Classification Standard

*(New in Revision 3.)* This section is the authoritative standard governing the identification, numbering, classification, naming, ownership, lifecycle, and traceability of every engineering artifact this platform produces, in every family. It fulfills the `STD-NNN` identifier-scheme item Revision 1's own roadmap reserved for Revision 3 (§12's status note), generalized platform-wide because the Derivative document series has grown well beyond the Standards family alone since that note was written.

**Relationship to §5, §6, §9, §10, and §13.** This section extends each of those sections additively, exactly as §9's own versioning rule requires of any Major-class, Minor-content-additive change (§9's note on Revision 2 applies identically here): it invalidates no existing rule, and every place it adds to an existing rule, it says so by name rather than silently reinterpreting the original text.

### 20.1 Purpose

Every engineering document this standard governs SHALL be:

| Property | Meaning |
| --- | --- |
| **Uniquely identifiable** | Its identifier (§20.4) is assigned once, permanently, and never reused (restates §9's and §10.3's own immutability rule). |
| **Human readable** | Its title and identifier together tell a reader what it is without opening it. |
| **Machine readable** | Its identifier follows one parseable pattern (§20.5) across every family, enabling the automation §19 already reserves without authorizing. |
| **Lifecycle aware** | Its current stage (§8) is always stated, never implied. |
| **Product aware** | Its numbering range (§20.3) identifies which product it belongs to, without requiring a reader to already know the platform's own product landscape. |
| **Traceable** | It resolves, family by family, back to Governance (§20.8). |
| **Version controlled** | It follows §9's Major.Minor.Patch discipline, unchanged. |
| **Governance compliant** | It satisfies §20.9's governance rules before being treated as authoritative. |

### 20.2 Engineering Document Families

This subsection extends §6's family catalogue. **§6's original seven families (HB, ADR + Design Proposal, Governance, STD, CAP, Runtime, Certification) are unchanged in purpose, ownership, and boundary** — this subsection (a) registers four families real precedent already established but §6 never formally named, (b) formally reserves one family anticipated by STD-004's and STD-005's own vocabulary but not yet exercised, and (c) aligns two existing families' short-form codes with the numbered-identifier convention their own real documents already use.

| Family | Short code | Purpose | Responsibilities | Typical lifecycle position (§20.6) | Transformation relationship (STD-005 §6) | Status |
| --- | --- | --- | --- | --- | --- | --- |
| **Handbook** | `HB` | Define the documentation architecture itself (§6.1, unchanged). | Unchanged from §6.1. | Precedes every other family; shared, not per-product. | N/A — HB originates no transformation. | Existing (§6.1). |
| **Standard** | `STD` | Define conventions engineering work must follow (§6.6, unchanged). | Unchanged from §6.6. | Precedes every other family; shared, not per-product. | N/A — a Standard is cited as Transformation Authority (STD-005 §8); it is not itself a transformation's Output Artifact. | Existing (§6.6). |
| **Product Requirements Document** | `PRD` | Record business intent for one product, bound by nothing architectural (restates ADR-001 §5's own framing of PRD-001 as "the first Derivative document, and the only one with no architectural dependency"). | Vision, objectives, scope, functional and non-functional requirements, business-tier success metrics, for one product. | First per-product tier — precedes Architecture. **Extends §5's hierarchy with a Business/Product tier above Platform Constitution** (§20.6 Reconciliation Note). | Origin of the **Refines** transformation into Architectural Intent (STD-005 §5). | **New family — registered by this revision.** Real precedent: PRD-001. |
| **Architecture Decision Record** | `ADR` | Record one architectural decision (§6.2, unchanged). | Unchanged from §6.2. | Realizes a PRD's business intent as Architectural Intent. | **Refines** (STD-005 §5, §6). | Existing (§6.2). |
| **Capability Document** | `CAP` | Track one platform capability (§6.4, unchanged). | Unchanged from §6.4. | Decomposes/Allocates an ADR's architecture into Capability Intent. | **Decomposes → Allocates → Specializes** (STD-005 §5, §6; ADR-001 §17). | Existing (§6.4). |
| **Runtime Documentation** | `RUN` | Describe a capability as it executes (§6.7, unchanged in purpose). | Unchanged from §6.7. | Realizes a CAP's capability intent as Runtime Intent. | **Realizes → Preserves → Derives** (STD-005 §5). | Existing (§6.7) — **short code and numbering reconciled** (§20.2's own Reconciliation Note below). |
| **System Specification** | `SYS` | Decompose a Runtime's own responsibilities and state model into cohesive logical systems (SYS-001 §2's own framing). | Realize a runtime's own Boundary and State Model unchanged, at finer, system-level grain (SYS-001 §4). | A refinement inside the single `Runtime Intent → Implementation Intent` hop STD-005 §5 already names — never a new stage (SYS-001 §15's own framing, restated). | **Realizes → Decomposes → Allocates → Preserves** (SYS-001's own Transformation Record). | **New family — registered by this revision.** Real precedent: SYS-001. |
| **Platform Reference Architecture** | `PRA` | Give a body of architecture its reusable, technology-shaped substrate (PRA-001 §2's own framing). | See §20.7's Reconciliation Note — this family has **two valid scopes**, distinguished by instance, not by family definition. | See §20.7. | **Realizes → Allocates → Specializes → Preserves** (PRA-001's own Transformation Record). | **New family — registered by this revision.** Real precedent: PRA-001. |
| **Implementation Specification** | `IMP` | Give a System Specification its complete technology realization (IMP-001 §2's own framing). | Realize STD-005 §5's own reserved `System → Implementation` hop (SYS-001 §15). | Follows System Specification; precedes Evidence. | **Realizes → Allocates → Specializes → Preserves** (IMP-001's own Transformation Record). | **New family — registered by this revision.** Real precedent: IMP-001. |
| **Evidence** | `EVD` | Record the specific, checkable facts (STD-001 §6, STD-002 §9, STD-003 §10's own evidence vocabulary) an Implementation actually produced. | Aggregate Implementation Deliverables (STD-001 §6) into the Engineering Evidence stage STD-005 §5 already names. | Follows Implementation; precedes Certification. | **Verifies** (STD-005 §5, §6). | **Reserved — no `EVD-NNN` document exists yet.** Named because STD-004 §9's own `Evidence` tier and STD-005 §5's own `Engineering Evidence` stage already require a family to occupy this position; not yet exercised by a real document. |
| **Certification** | `CERT` | Record formal verification (§6.8, unchanged in purpose). | Unchanged from §6.8. | Terminal tier — validates Evidence. | **Validates** (STD-005 §5, §6). | Existing (§6.8) — **short code and numbering reconciled** (§20.2's own Reconciliation Note below). |

**On Governance's own absence from this table.** Governance (§6.5) remains a living, unnumbered family, exactly as §10.3 already establishes — it is deliberately not given a short code above, because it never carries the kind of discrete, versioned identity this section's numbering scheme (§20.3) exists to assign. This is continuity with §10.3, not an oversight.

**Reconciliation Note — RUN and CERT numbering.** §10.3, as written in Revision 2, states that "Governance, Runtime, and Certification documents... are referenced by their descriptive path instead" of a numbered identifier. Real precedent since has established otherwise for Runtime: `RUN-001` (Requirements Intelligence Runtime) already exists as a stable, permanent, CAP-aligned numbered identifier, cited throughout the SYS-001, IMP-001, and PRA-001 lineage exactly as an ADR or CAP number would be. **This revision reconciles §10.3 with that precedent: a Runtime or Certification document that specifies a live component's design (rather than an execution-produced instance, §6.7) now carries a numbered identifier (`RUN-NNN`, `CERT-NNN`) under this section's own scheme, once one is assigned** — §10.3's own text is not rewritten (restating this handbook's own additive-revision discipline), but is, on this one point, superseded by this section going forward. Execution-produced Runtime documentation (a run's own report, summary, or metrics artifact, §6.7) remains unnumbered and path-referenced, unaffected by this reconciliation.

### 20.3 Product Numbering Strategy

| Range | Product |
| --- | --- |
| 001–099 | Core Engineering Intelligence Applications |
| 100–199 | Engineering Intelligence Operating System |
| 200–299 | Architecture Intelligence |
| 300–399 | Runtime Intelligence |
| 400–499 | Knowledge Intelligence |
| 500–599 | Evidence Intelligence |
| 600–699 | Certification Intelligence |
| 700–799 | Shared Platform Services |
| 800–899 | Enterprise Extensions |
| 900–999 | Research / Experimental / Incubation |

These ranges are **reserved, not exhaustively assigned** — a range is claimed only when a real product's first document (typically its `PRD-NNN`) is registered against it, and ranges may be added, split, or reinterpreted only under §20.9's Governance Rules (i.e., only by a future revision to this Handbook).

**Reconciliation Note — existing "001" identifiers are grandfathered, never renumbered.** §9 and §10.3 already make identifier permanence absolute: "a document's identifier... never changes once assigned," and "never reused, renumbered, or reassigned." The platform's own existing `-001` series — `PRD-001` and `ADR-001` (platform-wide founding architecture), together with `CAP-001`, `RUN-001`, `SYS-001`, `IMP-001` (Requirements Intelligence, the platform's first proven application), and `PRA-001` (the platform-wide reference architecture, §20.7) — predates this numbering strategy and is **not reclassified, renumbered, or reinterpreted by it**. This range table governs every product-numbering decision from this revision forward; it does not reach backward to reassign meaning to an identifier already Frozen or Drafted under this platform's prior practice.

### 20.4 Artifact Identity

Every engineering artifact SHALL possess, extending §16's Document Metadata Standard:

| Field | Relationship to §16 |
| --- | --- |
| Identifier | §16, unchanged. |
| Title | §16, unchanged. |
| **Product** | New — names the product-numbering range (§20.3) this artifact belongs to. |
| **Document Family** | New — names the family (§20.2) this artifact belongs to; supplements §16's implicit family-by-prefix convention with an explicit field. |
| **Lifecycle Stage** | Restates §16's `Status` field by name, to align this standard's own vocabulary with §8's. |
| Version | §16, unchanged. |
| Status | §16, unchanged (see Lifecycle Stage above — the two fields name the same fact; a document may use either label consistently within its own family's convention). |
| Owner | §16, unchanged. |
| **Governing Authority** | New — names the specific upstream document (per §13's dependency rules) this artifact's own authority derives from; makes §16's existing `Related Documents` field's *authority* entries explicit and singular where §13.1 requires exactly one. |
| **Traceability Identifier** | New — the specific chain position (§20.8) this artifact occupies, so a reader can locate it in the traceability chain without re-deriving it from the document's own content. |

### 20.5 Naming Convention

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

Naming remains consistent across every product: `<FAMILY>-<NNN>`, where `<NNN>` is the product's own assigned number (§20.3) shared by every family that product's own lifecycle (§20.6) produces. **No product-specific prefix (e.g. `PPRD`, `PADR`) is ever introduced** — the family code alone (§20.2) identifies the kind of document; the number alone identifies the product; combining them into a compound prefix would duplicate information the two-part scheme (§20.4's `Document Family` plus `Product` fields) already carries explicitly, violating §14's Minimal Duplication attribute.

### 20.6 Lifecycle Consistency Rules

```
HB
 ↓
STD
 ↓
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

**Reading this diagram.** `HB` and `STD` are shared, platform-wide, Normative families (ADR-001 §5) — they are not renumbered per product; every product's own lifecycle begins by inheriting them as-is. `PRD` through `IMP` are Derivative and repeat per product, sharing that one product's own number (§20.3, §20.5) throughout. Every product SHALL use this same nine-family reading order; only the identifier's numeric component changes between products.

**Reconciliation Note — extending §5's hierarchy.** §5's own seven-tier hierarchy (Platform Constitution → Architecture → Governance → Standards → Capabilities → Runtime → Certification) has never named a tier for Business/Product intent, even though `PRD-001` already exists and ADR-001 §5 already treats it as Architecture's own sole content source. **This revision extends §5 additively with one new tier, above Platform Constitution:**

```
Business / Product
        ↓
Platform Constitution
        ↓
    Architecture
        ↓
       ...  (§5, unchanged below this point)
```

This is the same kind of additive, non-invalidating extension SYS-001 §15 already performed on RUN-001's own five-node chain, and IMP-001 §14 on SYS-001's six-node chain — a permitted refinement of an existing model, never a redefinition of it. §5's own text is not rewritten; this note is its authoritative amendment.

### 20.7 Transformation Consistency

Restates STD-005 in full: document identifiers preserve transformation lineage, never obscure it.

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

**Reconciliation Note — PRA's two valid scopes.** `PRA-001` (already Drafted, §20.3's grandfather clause) is a **platform-wide, capability-independent reference architecture** — a singleton, Realized directly from `ADR-001` (PRA-001's own Transformation Record), sitting between Architecture and Capability in the platform's own traceability chain (PRA-001 §19), reusable by every product. The diagram above shows a **second, distinct scope**: a **per-product** `PRA-NNN` — that one product's own specialization of the platform-wide `PRA-001` applied to its own `SYS-NNN`, positioned between System Specification and Implementation Specification in that product's own lifecycle. Both scopes are valid, non-contradictory uses of the same family (§20.2): the platform-wide instance is Realized once, directly from an ADR, and extended by every product; a per-product instance, where a product's own architecture is complex enough to warrant one, is Realized from that product's own `SYS-NNN`, and SHALL itself derive from, specialize, and never contradict the platform-wide `PRA-001` it extends. A product not complex enough to need its own `PRA-NNN` inherits `PRA-001` directly, and simply omits this stage from its own lifecycle — restating STD-005 §7's own distinction between a Mandatory and an Optional transformation.

### 20.8 Traceability Rules

```
Governance
        ↓
     Product
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

**This is a family-level reading of the same structure STD-004's canonical graph (§9) and STD-005's Engineering Transformation Model (§5) already describe from complementary angles (STD-005 §5's own table already reconciles its process view against STD-004's structural view) — a third, family-cataloguing view, never a competing chain.** `Governance` heads this reading because every family below it is checked against Governance's own freeze and maturity record (§13.2) before being treated as authoritative; `Product` (this section's own new PRD family, §20.2) is the per-product root every other family in the chain ultimately traces back to, restating §20.6's own hierarchy extension at family-cataloguing grain.

### 20.9 Governance Rules

1. **Only HB may introduce new document families.** Restates §6's own root-authority position — this section's own registration of PRD, SYS, PRA, and IMP (§20.2), and reservation of EVD, is itself performed inside HB-001, by HB-001, consistent with this rule, never by a downstream family claiming that authority for itself.
2. **Only HB may reserve numbering ranges.** §20.3's table is this section's own exercise of that authority; a future range change requires a future HB revision, never a per-product decision.
3. **Only STD-005 governs transformations.** This section cites, and never redefines, STD-005 §6's semantics (§20.2's Transformation relationship column, §20.7).
4. **Only STD-004 governs relationships.** This section cites, and never redefines, STD-004's own relationship vocabulary; §20.8's chain names family-level positions, never a fifteenth relationship type.

### 20.10 Compliance Statement

Every future engineering artifact, in every family (§20.2), for every product (§20.3), SHALL comply with this identification standard. An artifact missing an identifier, a product assignment, a document-family classification, a lifecycle stage, or a resolvable position in §20.8's traceability chain is not yet a governed artifact under this Handbook, regardless of how complete its own content otherwise is — restating §9's Constitutional Rule 3's own governed-evolution discipline (STD-000), applied here to identity itself.

---

## Revision History

| Revision | Version | Status | Summary |
| --- | --- | --- | --- |
| **Revision 1** | 1.0 (Draft) | Revised (§8) | Established the documentation architecture for the first time: the seven-tier hierarchy (§5), the seven document families and their boundaries (§6), cross-family relationships and traceability (§7), the six-stage lifecycle (§8), the document versioning scheme (§9), baseline repository-organization recommendations (§10), and ten engineering principles (§11, later reorganized in Revision 2 without changing their substance). Introduced no architecture, governance, capability, or runtime content. |
| **Revision 2** | 2.0 (Draft) | Revised (§8) | Strengthened the documentation ecosystem's own governance without changing anything Revision 1 established: explicit per-family dependency rules and a citation matrix (§13), ten documentation quality attributes (§14), a review workflow layered onto the unchanged lifecycle (§15), a canonical (non-retroactive) metadata standard (§16), a traceability standard of mandatory/optional/prohibited references (§17), the Revision 1 principles reorganized into four categories with every principle's substance and number preserved (§11), a per-family ownership model (§18), and a reserved, tooling-free future-automation section (§19). Introduced no architecture, governance, capability, or runtime content. |
| **Revision 3** | 3.0 (Draft) | Draft — pending architecture review | Fulfilled, and substantially extended, the `STD-NNN` identifier-scheme item Revision 1's roadmap reserved for this revision (§12's status note): a single, platform-wide Engineering Document Identification & Classification Standard (§20) — eleven document families including four newly registered (PRD, SYS, PRA, IMP) and one formally reserved (EVD), a product numbering strategy, artifact-identity and naming-convention rules, lifecycle and transformation consistency rules, a family-level traceability chain, and governance rules for the standard itself. Explicitly reconciles, rather than silently contradicts, three points of real-world precedent Revision 2's text did not yet reflect: RUN-001's own numbered identifier (§10.3), PRD-001's own hierarchy tier (§5), and PRA-001's own platform-wide scope alongside a possible per-product instance (§20.7). Introduced no architecture, governance, capability, or runtime content. |

## Revision Summary

**HB-001 Revision 3** fulfills the `STD-NNN` identifier-scheme item Revision 1's own roadmap reserved for this revision (§12's status note), generalized platform-wide as a single Engineering Document Identification & Classification Standard (§20), because five more Standards documents and a seven-document Derivative series (PRD-001, ADR-001, CAP-001, RUN-001, SYS-001, IMP-001, PRA-001) now exist to generalize an identifier scheme from. It adds one new section (§20) registering four new document families (PRD, SYS, PRA, IMP) and formally reserving a fifth (EVD), a ten-range product numbering strategy, a ten-field artifact-identity model extending §16, a naming convention, lifecycle and transformation consistency rules extending §5 and citing STD-005, a family-level traceability chain complementing STD-004's and STD-005's own views, and four governance rules for the standard itself. It explicitly reconciles — never silently overrides — three points where real precedent had already outpaced Revision 2's own text: Runtime's numbered identifier (§10.3), the Business/Product tier §5 had not yet named, and the Platform Reference Architecture family's two valid scopes (§20.7). Every architecture, governance, capability, and runtime document this handbook depends on — including HB-001 Revision 1 and Revision 2 themselves — is treated as authoritative and unmodified; no existing document requires any change as a result of this revision.

## Future Revision Roadmap

| Revision | Anticipated focus |
| --- | --- |
| **Revision 4** | The canonical per-family template set and the `docs/standards/`-style directory-mapping formalization Revision 1's roadmap originally paired with the `STD-NNN` scheme (§12) — both still open, now that §20 has assigned the scheme itself; introduce the documentation coverage view (§12, §19); extend §17's traceability standard with a worked cross-family example drawn from a real product's full PRD → ADR → CAP → RUN → SYS → PRA → IMP chain (§20.6). |
| **Revision 5** | Formally register the Governance family's own numbering treatment, if practice ever produces a numbered Governance instance; assign the first real range-claiming `PRD-NNN` outside the grandfathered `-001` series and the now-registered EIOS `-100` series (§20.3), exercising §20.9's Governance Rules for the first time since this revision. |
| **Revision 6+ (reserved)** | Evaluate whether a dedicated Engineering Process family is warranted; incorporate lessons from any document found, in practice, to span two families (§11.1 Principle 10); revisit §19's automation opportunities, now with §20's own identifier scheme as a concrete target for the identifier-validation and broken-reference-detection items §19 already names. |

## Known Limitations of Revision 3

- **§20's own family, numbering, and traceability rules are declarative, not enforced or automatically checked** — restates §19's own reserved-not-authorized automation stance, now with a considerably larger surface (eleven families, ten numbering ranges) to eventually validate mechanically.
- **The EVD family (§20.2) is registered but not yet exercised** — no `EVD-NNN` document exists; its row in §20.2 describes an anticipated shape, not an observed one, unlike the four families this revision registers from real precedent.
- **The per-product `PRA-NNN` scope (§20.7) is, as of this revision, hypothetical** — only the platform-wide singleton `PRA-001` exists; the per-product reconciliation this section provides is a rule ready to be exercised, not yet a rule confirmed by a second real instance.
- **§20.4's `Governing Authority` and `Traceability Identifier` fields are not applied retroactively**, exactly as §16's own metadata standard already declares of itself — no existing document's header is required to change.
- **The grandfather clause in §20.3 relies on a judgment call** (which existing identifiers count as "founding lineage") that has not yet been tested against a disputed or ambiguous case; §20.3 states the rule, not a worked adjudication of every edge case.
- Revision 3 inherits every limitation of Revision 1 and Revision 2 not explicitly resolved above (see the [Revision History](#revision-history)).

## Final Self Review

- [x] No architecture was modified — every ADR, layer definition, and runtime contract referenced in this handbook (any revision) is cited, never redefined.
- [x] No governance was modified — the Architecture Freeze Index, Platform Capability Matrix, and every existing governance record are referenced by role only.
- [x] No runtime was modified — no component specification, execution behavior, or artifact format is changed; §20.2's Reconciliation Note on RUN/CERT numbering changes a citation convention, not a runtime behavior.
- [x] No capabilities were modified — no `CAP-NNN` boundary, dependency, or maturity status is altered.
- [x] No new engineering, coding, or implementation standard was introduced — §20 governs document identity, not code, language, framework, or AI-provider choices.
- [x] Documentation hierarchy is preserved and extended additively — §5's seven tiers are unchanged in substance; §20.6 adds one new tier above Platform Constitution, by name, without deleting or renumbering the seven.
- [x] Document families are preserved and extended additively — §6's seven families are unchanged in purpose, ownership, and boundary; §20.2 registers four new families and reserves a fifth without altering any of the seven's own definition.
- [x] Lifecycle is preserved — §8's six stages are unchanged in name, order, and count; §20 introduces a per-product family sequence (§20.6), a distinct concept from a document's own six-stage lifecycle.
- [x] Versioning strategy is preserved — §9 is unchanged; the grandfather clause (§20.3) is itself a direct application of §9's and §10.3's own permanence rule, not an exception to it.
- [x] Repository organization is preserved — §10 is unchanged; §20.2's numbering reconciliation extends §10.3 by name, on the one point real precedent had already outpaced it.
- [x] All ten Revision 1 principles remain preserved with their original numbering, unchanged by this revision.
- [x] Every Revision 3 objective (as commissioned) is addressed: Purpose (§20.1), Engineering Document Families (§20.2), Product Numbering Strategy (§20.3), Artifact Identity (§20.4), Naming Convention (§20.5), Lifecycle Consistency Rules (§20.6), Transformation Consistency (§20.7), Traceability Rules (§20.8), Governance Rules (§20.9), Compliance Statement (§20.10).
- [x] Backward compatibility with Revision 1 and Revision 2 is maintained — every prior section reference, principle number, and defined term still resolves to the same meaning it always had; every point of extension (§5, §6, §10.3) is named explicitly as such (§20's own Reconciliation Notes).
- [x] Remains implementation-, language-, framework-, and AI-provider-independent — verified by inspection of §20; it names no technology.

## HB-001 Revision 3 Compliance Certificate

**This certifies that HB-001, Revision 3, Version 3.0 (Draft):**

- ✅ **Mission completed** — the Engineering Document Identification & Classification Standard (§20) is established, fulfilling the `STD-NNN` roadmap item Revision 1 reserved for this revision.
- ✅ **Scope respected** — no new architecture, governance, runtime behaviour, capability, or engineering-implementation standard is introduced; §20 governs document identity only.
- ✅ **Frozen inputs preserved** — HB-001 Revision 1 and Revision 2, every existing ADR, PRD, CAP, RUN, SYS, IMP, PRA, Design Proposal, Governance document, the Platform Capability Matrix, and every existing Runtime or Certification document are referenced only, never redefined or contradicted.
- ✅ **Documentation hierarchy preserved and extended additively** — §5's seven tiers are unchanged; §20.6 adds a Business/Product tier by name, reconciling the hierarchy with PRD-001's own long-standing role rather than leaving the gap unexamined.
- ✅ **Document families preserved and extended additively** — §6's seven families are unchanged; §20.2 registers PRD, SYS, PRA, and IMP from real precedent and formally reserves EVD.
- ✅ **No architectural, governance, runtime, or capability change introduced** — verified in the Final Self Review above.
- ✅ **Backward compatibility maintained** — every prior revision's section, principle number, and defined term continues to resolve identically; both prior revisions remain intact and available for historical reference ([Revision History](#revision-history)).
- ✅ **Real-world precedent reconciled, not contradicted** — RUN-001's numbering (§10.3), PRD-001's hierarchy position (§5), and PRA-001's platform-wide scope (§20.7) are each explicitly reconciled with this revision's own new rules, by name, rather than silently overridden.
- ✅ **Ready for review.**

**Summary.** HB-001 Revision 3 is suitable to remain the root documentation artifact of the platform because it closes the one identifier-scheme gap Revision 1 always intended to close, at the moment the platform's own document series had grown enough real precedent — seven Derivative documents across five families beyond the original seven — to generalize a standard from rather than invent one speculatively. Where that real precedent had already run ahead of Revision 2's own text (RUN-001's numbering, PRD-001's hierarchy position, PRA-001's scope), this revision names the gap and closes it explicitly, restating this handbook's own Revision 2 lesson: a root documentation artifact stays trustworthy only if something keeps it trustworthy, including — as of this revision — its own identifier scheme.

---

*End of HB-001, Revision 3, Version 3.0 (Draft).*
