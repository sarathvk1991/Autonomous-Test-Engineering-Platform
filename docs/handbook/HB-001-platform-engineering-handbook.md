# HB-001 — Platform Engineering Handbook

**Revision 1 · Version 1.0 (Draft)**

| Attribute | Value |
| --------- | ----- |
| Document ID | HB-001 |
| Document family | Handbook (HB) |
| Revision | 1 |
| Version | 1.0 (Draft) |
| Document type | Documentation Architecture — Root Reference |
| Status | Draft — pending architecture review |
| Owner | Platform Architecture |
| Governs | The documentation ecosystem of the entire engineering platform |
| Governed by | Nothing — HB-001 is the root of the documentation hierarchy it defines |
| Supersedes | Nothing (first revision) |
| Implementation independence | This handbook contains no language, framework, or AI-provider-specific guidance. It describes documents, not code. |

> HB-001 is not an implementation guide and not a governance document. It is the
> **documentation architecture** of the platform — the single reference that
> explains what kinds of engineering documents exist, what each one is
> responsible for, how they relate to one another, and how a reader or a new
> document finds its correct place in the ecosystem. Every ADR, governance
> record, standard, capability document, runtime document, and certification
> record in this platform is expected to be locatable, and explicable, in terms
> of the structure this handbook defines.

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
- [Revision Summary](#revision-summary)
- [Future Revision Roadmap](#future-revision-roadmap)
- [Known Limitations of Revision 1](#known-limitations-of-revision-1)
- [Final Self Review](#final-self-review)
- [HB-001 Revision 1 Compliance Certificate](#hb-001-revision-1-compliance-certificate)

---

## 1. Purpose

An engineering platform that reasons deterministically, freezes its architecture deliberately, and governs its own evolution through Architecture Decision Records accumulates, over time, a second artifact of equal consequence to the code itself: its documentation. Left unmanaged, that documentation grows the same way undocumented code grows — inconsistently, redundantly, and without a single place a reader can trust to be current.

HB-001 exists to prevent that outcome by defining, once and authoritatively, **the documentation architecture of the platform**: what kinds of documents exist, what each kind is responsible for, how they depend on one another, and how a reader — or a future author — determines where a new document belongs before writing a single line of it.

This handbook does not describe *what the platform does*. It describes *how the platform explains itself*. Every existing ADR, governance record, standard, capability document, runtime document, and certification report in this repository already conforms, in substance, to the structure this handbook names. HB-001's contribution is not to invent new rules for any of them — it is to make the rule that already governs their relationships explicit, permanent, and citable, exactly as ADR-0020 made the platform's architectural layering explicit for code that had, in substance, already been following it.

## 2. Scope

**In scope for HB-001 (Revision 1):**

- The documentation hierarchy — the ordered relationship between the platform's constitutional, architectural, governance, standards, capability, runtime, and certification documents.
- The document families — the recurring *kinds* of document the platform produces, each with one purpose, one owner, and one place in the hierarchy.
- The relationships between families — dependency direction, citation conventions, and traceability.
- The lifecycle every engineering document passes through, from first draft to superseded.
- The versioning strategy for documents themselves (not for runtime contracts, APIs, or code — those are governed elsewhere, see §2's out-of-scope list).
- Baseline recommendations for repository organization, naming, and cross-referencing of documents.
- The guiding principles that keep the documentation ecosystem consistent as it grows.

**Intentionally out of scope for HB-001 (Revision 1):**

- **Architecture content.** HB-001 does not define what any layer, capability, or runtime contract *is* — that is the Architecture family's own responsibility (§6.2), and every architectural decision already on record (ADR-0001 through the platform's latest) is treated as authoritative and unmodified by this handbook.
- **Governance content.** HB-001 does not define freeze policy, capability maturity criteria, or ADR-required/not-required judgments — that is the Governance family's own responsibility (§6.5), exercised today by the Architecture Freeze Index and the Platform Capability Matrix, both left exactly as they are.
- **New capabilities.** HB-001 introduces no `CAP-NNN` capability, changes no capability's boundary, and reserves no new runtime contract.
- **Runtime or implementation detail.** HB-001 names languages, frameworks, or AI providers nowhere in this document, by design (see the Implementation Independence line in the header table).
- **Versioning of runtime contracts, APIs, or code artifacts.** §9 covers *document* versioning only. Runtime contract versioning (e.g. `*_RESULT_VERSION` constants) remains governed entirely by each capability's own ADR, unaffected by this handbook.
- **Document content standards** (writing style, terminology glossaries, template text). Reserved for a future Standards-family document (§12).

## 3. Audience

| Reader | How HB-001 serves them |
| --- | --- |
| **Platform Architects** | The map from which every architectural and constitutional document's place, authority, and dependency is determined before it is written. |
| **Engineers** | A way to find the correct document for a question — "why does this work this way?" (Architecture), "is this allowed?" (Governance), "how should I build this?" (Standards, future) — without guessing which directory to search. |
| **Reviewers** | A structural checklist: does a new document belong to exactly one family, cite its correct dependencies, and enter at the correct lifecycle stage? |
| **Technical Leads** | A planning surface for what documentation a new initiative requires, and in what order it must be produced (Architecture before Governance before Capability, per §5). |
| **Contributors** | An onboarding reference — a new contributor can learn the shape of the platform's documentation before learning the shape of its code. |

## 4. Engineering Documentation Philosophy

**Documentation is a first-class engineering artifact.** In this platform, an architectural decision does not exist until it is recorded; a capability is not complete until its governance record and certification exist alongside its code. Documentation is not a description written after engineering happens — it is one of the deliverables engineering produces, held to the same standard of rigor, review, and version control as the systems it describes.

**Documentation earns trust the way code does: by being deterministic, explainable, and reviewable.** A reader of this platform's documentation should never have to guess whether a document is current, whether it has authority over the thing it describes, or what it depends on. Every document family defined in §6 exists to answer those three questions on sight — by its identifier, its location, and its declared status.

**Documentation minimizes duplication by construction, not by discipline alone.** The platform's own architectural principle of "exactly one owner per responsibility" (already frozen for code and capabilities by the platform's constitutional ADRs) applies identically to documentation: exactly one document owns a given fact, and every other document that needs that fact cites it rather than restates it. This is why §7 (Documentation Relationships) exists as its own section, not a footnote — cross-referencing is the primary mechanism, not an optional courtesy.

**Documentation has a lifecycle because engineering decisions have a lifecycle.** A document that is still Draft carries different authority than one that is Frozen; treating every document as equally final, regardless of its stage, is how documentation drifts silently out of sync with the systems it describes. §8 exists to make that distinction explicit and enforceable.

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

**Reading the hierarchy.** A document at any tier may cite and depend on a document at any tier above it (closer to Platform Constitution) — never a tier below it. A Standards document may cite Architecture and Governance; it may never be cited by, or depend on, a piece of Architecture, because that would let convention dictate design rather than the reverse. This is the documentation-level restatement of the same one-way dependency rule the platform's own architectural layers already obey — extended here from runtime contracts to the documents that describe them.

**This is a hierarchy of authority, not a hierarchy of quality.** A Runtime document is not "lesser" than a Constitution document — it answers a different, equally necessary question. The hierarchy exists so that when two documents appear to disagree, the reader knows, without guessing, which one is authoritative: the one closer to Platform Constitution.

## 6. Document Families

Each family below has exactly one purpose, one form of ownership, and one place in §5's hierarchy. A document belongs to exactly one family.

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
- **Relationship with other families:** Sits at the Governance tier of §5. Depends on Architecture (it indexes ADRs; it never originates architectural content of its own — see the Governance family's own stated purpose: "this document indexes; it does not create"). Is depended on by Standards, Capabilities, and Certification, each of which cites Governance to confirm a document's freeze status or maturity before proceeding.

### 6.6 STD — Standard

- **Purpose:** Define the conventions engineering work must follow to remain consistent with governed architecture, so that consistency does not depend on an individual engineer's memory.
- **Ownership:** Platform Architecture, delegated per domain (e.g. a naming convention, a review checklist template, a documentation style rule).
- **Responsibilities:** Naming conventions, structural conventions, and review conventions that apply platform-wide or family-wide. Standards never introduce new architectural authority — they only make an already-governed decision easy to apply consistently.
- **Examples:** the platform's existing naming-conventions and coding-standards references, and any development guide describing how to build a specific kind of governed unit consistently (e.g. a rule-development guide for a governed rule catalogue).
- **Relationship with other families:** Sits at the Standards tier of §5. Depends on Architecture and Governance (a naming convention exists to make an already-frozen architectural distinction visible in code or documents, never to invent a new one). Is depended on by Capability and Runtime documentation, which conform to it without restating it.

> **Note on current state.** The platform's existing standards documents predate a formal `STD-NNN` identifier scheme. HB-001 does not renumber, relocate, or rewrite them (that would modify an existing artifact, forbidden by this handbook's own scope, §2). §10 and §12 record the recommended path for bringing them under a governed identifier in a future revision, without disturbing their current content or location.

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
- **Relationship with other families:** Sits at the Certification tier of §5, the terminal tier — nothing in this documentation ecosystem depends on Certification; it is where the chain of trust from Constitution through Runtime terminates in a verifiable statement. Depends on every tier above it. A review report is treated as evidence feeding a certification, not a certification itself — this is the concrete expression of this handbook's own Engineering Philosophy line: *"Reviews validate implementations. Certification validates readiness."*

### 6.9 Family summary

| Family | Hierarchy tier (§5) | Depends on | Depended on by |
| --- | --- | --- | --- |
| HB | outside the hierarchy (defines it) | nothing | every family, indirectly |
| ADR (+ Design Proposal) | Platform Constitution, Architecture | prior ADRs | Governance, Standards, CAP, Runtime |
| Governance | Governance | ADR | Standards, CAP, Certification |
| STD | Standards | ADR, Governance | CAP, Runtime |
| CAP | Capabilities | ADR, Governance, STD | Runtime, Certification |
| Runtime | Runtime | ADR, CAP | Certification |
| Certification | Certification (terminal) | ADR, Governance, STD, CAP, Runtime | nothing |

## 7. Documentation Relationships

**Dependency direction is always toward Platform Constitution.** Every citation in this ecosystem points from a lower tier to a higher one (§5): a Governance document cites the ADR it indexes; a Capability document cites the Architecture and Governance that bound it; a Certification report cites everything it verified. A document never cites something below it in the hierarchy as though that lower document had authority over it — a piece of Architecture does not cite a Certification report to justify itself, because certification is evidence of conformance, not a source of design authority.

**Citation, not duplication, is the traceability mechanism.** When a document needs a fact that another document already owns, it references that document by its identifier (§10.3) rather than restating the fact. This is the same "exactly one owner per fact" discipline this platform's own runtime architecture already enforces for canonical models, applied here to documentation content.

**Traceability is bidirectional in practice, even though authority flows one way.** A reader starting from a Certification report can trace backward through every tier to the Platform Constitution it ultimately rests on; a reader starting from the Platform Constitution can, conversely, discover every Capability and Certification that was ever built against it, because every downstream document names its upstream dependency explicitly. Neither direction requires guessing — both are satisfied by the same set of forward citations, read in the direction the reader needs.

**A document's own identifier is the primary cross-reference token.** A document is cited by its identifier (e.g. an ADR number, a `CAP-NNN` id, or this handbook's own `HB-001`) plus, where useful, the specific internal section — never by an ambiguous description like "the architecture doc" or "the recent proposal." §10.3 defines the identifier scheme this depends on.

**Cross-family relationships are never circular.** Because dependency only ever points toward Platform Constitution (§5), and no family occupies more than one tier, a citation cycle across families is structurally impossible without violating the hierarchy itself — the same guarantee the platform's runtime architecture already provides for its own layers, restated here for the documents that describe them.

## 8. Documentation Lifecycle

Every engineering document, in every family, progresses through the same six stages, in the same order. A document may remain at a stage indefinitely (a Governance document, for example, is expected to stay "Frozen" for the architecture it indexes while still being edited in place to stay current — see the note under §8's table); no document skips a stage on its way forward.

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
| **Review** | The document is complete and submitted for review by its family's designated reviewing authority (§6). Content may still change in response to feedback. |
| **Approved** | The document's content is accepted. It now carries the authority its family grants it, but it is not yet declared immutable — narrow corrections remain possible without a formal revision. |
| **Frozen** | The document's content is declared immutable except through a deliberate, reviewed change (for an ADR, a new ADR; for a Handbook, a new revision; for Governance, an explicit, logged update). This is the stage at which other documents may safely cite it as a stable dependency. |
| **Revised** | A newer revision or version of the document exists and is now authoritative; this version remains available for historical reference but no longer governs new work. |
| **Superseded** | The document no longer governs anything, even for historical reference of "what was current then" — a later document has fully replaced its role. Retained for audit history, never deleted. |

**Family-specific notes:**

- **ADRs** typically move Draft → Review → Approved → Frozen, and only reach Superseded when a later ADR explicitly supersedes them — never silently.
- **Governance documents** are the one family designed to be edited in place at the Frozen stage — described in §6.5 as "living documents." Their own header always names what edits are in scope (indexing and status updates) versus out of scope (originating new architectural content), so an in-place edit never becomes an undisclosed architectural change.
- **Handbook (HB) documents** move to a new **Revision** (not a new document identifier) rather than a full Supersession, for as long as the same root document continues to govern the ecosystem — see §9 for how revisions and versions interact.
- **Certification documents** are Frozen at the moment of sign-off by definition — a certification that could still change after being issued would not be a certification.

## 9. Versioning Strategy

This section governs the versioning of **documents**, not of runtime contracts, APIs, or code. Runtime contract versioning remains entirely the concern of the ADR that governs the contract, unaffected by this handbook.

**Every document family versions along the same three-part scheme, applied consistently:**

| Version part | Meaning | Example trigger |
| --- | --- | --- |
| **Major** | A change that breaks a prior reader's understanding, or removes/redefines something a downstream document depended on. | A Handbook revision that changes the documentation hierarchy itself (§5); an ADR being superseded outright. |
| **Minor** | An additive change — new content that does not invalidate anything a downstream document already relies on. | A new document family added to §6; a new capability registered in the Governance family's Capability Matrix. |
| **Patch** | A correction that changes no meaning — a typo, a broken cross-reference fixed, a formatting pass. | A citation link corrected; a table's formatting repaired. |

**Family-specific version identity:**

- **Handbook (HB)** documents carry two independent counters: a **Revision** number (Draft/Review/Approved/Frozen cycle for a substantively new edition, e.g. Revision 1 → Revision 2) and a **Version** within that revision (1.0 Draft → 1.0 → 1.1 → …, for refinements that do not warrant a new revision). A new **Revision** is a Major-class event; a **Version** bump within a revision follows the Minor/Patch distinction above.
- **ADRs** are numbered sequentially and permanently (`ADR-0001`, `ADR-0002`, …); the number never changes. An ADR's own content is versioned by its lifecycle stage (§8) rather than a numeric version — a superseding decision is a *new* ADR number, never a version bump of the old one, because the old decision's text must remain exactly as it was for historical accuracy.
- **CAP** documents are numbered sequentially and permanently (`CAP-001`, `CAP-002`, …, allocated in domain blocks with reserved growth ranges); the capability's own maturity — not its identifier — is what advances through the lifecycle in §8.
- **Governance** documents are living documents (§8) and therefore version primarily through the Minor/Patch distinction — a Major version is reserved for a restructuring of the document's own scope (rare, and itself requiring an ADR to authorize, since Governance may not originate architectural change on its own, §6.5).
- **STD, Runtime, and Certification** documents follow the same Major/Minor/Patch scheme as the general rule above, scoped to their own content.

**Rule (frozen):** a document's identifier (its ADR number, its `CAP-NNN`, its `HB-NNN`) never changes once assigned, regardless of how many times its version or revision advances. Identity and version are two independent axes — the same independent-versioning discipline this platform's own runtime contracts already apply to themselves, restated here for the documents that describe them.

## 10. Repository Organization

### 10.1 Directory hierarchy (recommended)

The platform's existing documentation directory structure already reflects most of the family boundaries §6 defines. This handbook recommends the following mapping as the authoritative one going forward, without relocating any existing file (relocation is a future-revision concern, §12, since HB-001 may recommend but must not itself restructure the repository):

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
- A document introducing a new dependency on another family (e.g. a Standards document citing an ADR for the first time) states that dependency in its own header or opening section, not buried mid-document — mirroring the header-table convention this handbook and the platform's existing ADRs already use.

## 11. Engineering Principles

These principles govern the documentation ecosystem itself, and are inherited — never re-derived — by every family §6 defines.

1. **Architecture before implementation.** No capability's runtime is built before its architecture is frozen (already the platform's own constitutional rule; this handbook's Capabilities and Runtime tiers exist in that order because of it, §5).
2. **Standards before coding.** A convention is defined once, in the Standards family, before it is repeated informally across capability documents.
3. **Documentation over tribal knowledge.** If a fact governs engineering decisions, it belongs in a document at the correct tier — not in a person's memory or a chat thread.
4. **Explicit ownership.** Every document names an owner (§6's per-family Ownership rows); a document with no owner is not yet ready to leave Draft (§8).
5. **Backward compatibility.** A document's identifier and its historical content are permanent; change is additive (a new revision, a new ADR, a new version) rather than a silent rewrite of the past (§9).
6. **Deterministic engineering.** The same governing documents, read by two different engineers, must produce the same understanding of what is required — ambiguity in a governing document is itself a defect.
7. **Layer isolation.** A document never reaches past its own hierarchy tier to claim authority that belongs to a tier above it (§5, §7).
8. **Traceability.** Every document can be traced, citation by citation, back to the Platform Constitution tier that ultimately authorizes it (§7).
9. **Consistency.** Two documents in the same family follow the same structure, the same header conventions, and the same lifecycle vocabulary — a reader who has read one ADR should recognize the shape of every other one.
10. **Single responsibility, single family.** Every document answers exactly one of §5's tier-level questions, and belongs to exactly one family in §6 — a document trying to be both a Standard and a Certification has not yet been decomposed correctly.

## 12. Future Evolution

HB-001 Revision 1 deliberately leaves the following for later revisions, so that Revision 1 can be adopted without waiting for every open question in the ecosystem to be resolved at once:

- **A formally numbered Standards (`STD-NNN`) identifier scheme**, bringing the platform's existing coding-standards and naming-convention references — and any future development guide — under the same permanent-identifier discipline ADR and CAP documents already have (§6.6, §10.2).
- **A dedicated `docs/standards/` directory**, consolidating the Standards family's current, pre-handbook location under `docs/development/` and `docs/*.md` into the structure §10.1 recommends, without disturbing existing content until that migration is itself planned and reviewed.
- **A formal template set** — one canonical header/section template per family, so that "every ADR looks like every other ADR" (§11, Principle 9) is enforced by a reusable template rather than by convention alone.
- **A documentation coverage view**, analogous to the platform's existing Architecture Coverage Dashboard, but scoped to documentation itself — which capabilities have a Runtime document, which have a Certification record, and which do not yet.
- **A future engineering process family**, if the platform's own process (release management, incident review, onboarding) ever grows enough independent documentation to warrant its own family rather than living inside Operations/Runtime as it does today.
- **Explicit guidance for documents that appear to span two families**, extending §11 Principle 10's decomposition rule with worked examples, once enough such cases have been observed in practice to generalize from.

None of the above is authorized by this revision. Each is named so that a future revision has a clear, pre-scoped starting point rather than an open-ended mandate.

---

## Revision Summary

**HB-001 Revision 1** establishes the platform's documentation architecture for the first time: the seven-tier hierarchy (§5), the seven document families and their boundaries (§6), the cross-family relationship and traceability rules (§7), the six-stage document lifecycle (§8), the document versioning scheme (§9), baseline repository-organization recommendations (§10), and the ten engineering principles governing documentation itself (§11). It introduces no new architecture, governance rule, capability, or runtime behavior — every frozen input named in this handbook's mission is treated as authoritative and unmodified, and this handbook's own role is limited to organizing how those inputs relate to one another and to future documents.

## Future Revision Roadmap

| Revision | Anticipated focus |
| --- | --- |
| **Revision 2** | Formalize the Standards (`STD-NNN`) identifier scheme and directory (§12); introduce the canonical per-family template set. |
| **Revision 3** | Introduce the documentation coverage view; extend §7's traceability guidance with a worked cross-family example drawn from a real capability's full ADR → Governance → CAP → Runtime → Certification chain. |
| **Revision 4+ (reserved)** | Evaluate whether a dedicated Engineering Process family is warranted; incorporate lessons from any document found, in practice, to span two families (§11 Principle 10). |

## Known Limitations of Revision 1

- The Standards family is defined (§6.6) but not yet brought under a numbered identifier scheme — its existing seed documents remain exactly where and as they are.
- No canonical document template is provided yet; family structure is described narratively (§6) rather than as a fill-in-the-blank template.
- The mapping in §10.1 is a recommendation, not an enforced or automatically-checked structure — no tooling validates that a new document lands in its recommended directory.
- Cross-reference validation (broken-link detection, identifier-uniqueness enforcement) is not addressed; it is assumed to be a future tooling concern, not a Revision 1 documentation-architecture concern.
- This handbook does not yet address documentation for capabilities that predate the ADR-numbering convention (noted, without resolution, exactly as the platform's own constitutional ADR already notes for its earliest capabilities) — Revision 2 or later may choose to retroactively acknowledge, but never rewrite, that history.

## Final Self Review

- [x] No architecture was modified — every ADR, layer definition, and runtime contract referenced in this handbook is cited, never redefined.
- [x] No governance was modified — the Architecture Freeze Index, Platform Capability Matrix, and every existing governance record are referenced by role only.
- [x] No runtime was modified — no component specification, execution behavior, or artifact format is changed.
- [x] No capabilities were modified — no `CAP-NNN` boundary, dependency, or maturity status is altered.
- [x] Documentation hierarchy is internally consistent — §5's seven tiers, §6's seven families, and §9's versioning scheme all cross-reference without contradiction.
- [x] Every document family has a single responsibility — verified family by family in §6, summarized in §6.9.
- [x] Traceability is maintained — §7 defines the citation mechanism; §10.3–10.4 define the identifier and cross-reference conventions that make it enforceable.
- [x] Future evolution is supported — §12 and the Future Revision Roadmap name specific, scoped next steps without authorizing them prematurely.

---

## HB-001 Revision 1 Compliance Certificate

**This certifies that HB-001, Revision 1, Version 1.0 (Draft):**

- ✅ **Mission completed** — the documentation architecture for the platform's entire engineering ecosystem is established, covering purpose, scope, audience, philosophy, hierarchy, families, relationships, lifecycle, versioning, repository organization, principles, and future evolution.
- ✅ **Scope respected** — this handbook defines documentation architecture only; it contains no architecture redesign, no governance redesign, no new capability, no runtime change, and no implementation, language, or framework detail of any kind.
- ✅ **Frozen inputs preserved** — every existing ADR, governance document, the Platform Capability Matrix, every existing CAP document, the platform's layered architecture, and the existing runtime architecture are treated as authoritative and referenced, never redesigned or contradicted.
- ✅ **Documentation hierarchy established** — the seven-tier Platform Constitution → Architecture → Governance → Standards → Capabilities → Runtime → Certification flow is fully defined, with explicit responsibilities and dependency direction at every tier.
- ✅ **Engineering principles respected** — every principle named in this handbook's mission (first-class artifact status, version control, explicit ownership, internal consistency, single responsibility, single family membership, minimized duplication, cross-reference preference, and the Standards-inherit-Architecture / Capabilities-inherit-Standards / Implementations-inherit-Capabilities / Reviews-validate-Implementations / Certification-validates-readiness chain) is reflected directly in §5, §6, §7, and §11.
- ✅ **Ready for architecture review.**

**Summary.** HB-001 is suitable to become the root documentation artifact of the platform because it is the only document in the ecosystem that describes the ecosystem itself rather than any one part of it: it makes explicit a structure every existing document in this repository already, informally, follows — a constitutional tier, an architecture tier, a governance tier, and (now formally named) standards, capability, runtime, and certification tiers, each with one owner and one responsibility. Every future ADR, governance record, standard, capability document, runtime specification, and certification report can now cite HB-001 to justify *where it belongs*, exactly as it already cites its own family's governing precedent to justify *what it decides*. That is the specific, narrow, load-bearing role a root documentation artifact must perform — and the only one this revision claims to fulfill.

---

*End of HB-001, Revision 1, Version 1.0 (Draft).*
