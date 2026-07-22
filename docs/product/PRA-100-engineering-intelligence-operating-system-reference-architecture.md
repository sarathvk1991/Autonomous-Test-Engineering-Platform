# PRA-100 — Engineering Intelligence Operating System Reference Architecture

**Version 1.0**

## 1. Document Metadata

| Field | Value |
| --- | --- |
| Identifier | PRA-100 |
| Title | Engineering Intelligence Operating System Reference Architecture |
| Version | 1.0 |
| Status | Draft — pending Architecture Review Board approval |
| Owner | Chief Platform Architect, delegated per Domain (ADR-100 §7) |
| Stakeholders | Platform Architect, Application Owner, Engineer, Reviewer, Certification Authority |
| **Derived From** | **SYS-100 — Engineering Intelligence Operating System Logical System Architecture** (the sole content source). |
| Governing Standards | HB-001 (Revision 4), STD-000, STD-001, STD-002, STD-003, STD-004, STD-005 |
| Transformation Authority | STD-005 §6 — **Realizes → Allocates → Specializes → Preserves**, matching HB-001 §20.12's own per-Artifact `PRA-NNN` rule: "Realized from that product's own `SYS-NNN`." |
| Dependencies | SYS-100, RUN-100, CAP-100, ADR-100, HB-001, STD-000–STD-005 |
| Related Documents | **PRA-001** (existing, platform-wide reference architecture — **never a content source of this document**; a binding constraint this document's every composition SHALL satisfy, per HB-001 §20.12: "SHALL itself derive from, specialize, and never contradict the platform-wide `PRA-001` it extends.") |
| Supersedes | Nothing |
| Superseded By | Not applicable |

**Artifact/Document identity (HB-001 §20.2).** This document describes one lifecycle stage of the EIOS Engineering Artifact (`PRD-100 → ADR-100 → CAP-100 → RUN-100 → SYS-100 → PRA-100 → …`). **PRA-100 introduces no new identity space** — it is the first real exercise of HB-001 §20.12's own per-Artifact `PRA-NNN` rule, which every prior document in this lineage (PRA-001 §22, RUN-100 §24, SYS-100 §16) could only describe as hypothetical.

## 2. Executive Summary

SYS-100 allocated RUN-100's runtime behavior to eight Logical Systems (`LSYS-001`–`LSYS-008`). PRA-100 composes those same eight systems — introducing none new — into five reusable **Reference Compositions** (§6), a single **Reference Topology** (§5), and an explicit account of why `LSYS-005` and `LSYS-007` are architected as **cross-cutting** rather than sequential (§7). Every composition traces back to SYS-100, RUN-100, CAP-100, and ADR-100 (§9) and specializes, without contradicting, the platform-wide `PRA-001` (§1). **This is the first real per-Artifact `PRA-NNN` this lineage has produced** — every prior mention of the concept (PRA-001 §22, RUN-100 §24, SYS-100 §16) was necessarily hypothetical, since no second document had yet exercised it. Consistent with that lineage's own recurring discipline, this document does not overstate what that first exercise proves (§12–§13): every composition remains Conceptual, since SYS-100's own Logical Systems themselves reach, at most, Allocated maturity (SYS-100 §11, §16).

## 3. Reference Architecture Philosophy

> **A Reference Architecture is a recommended composition of Logical Systems that realizes the Engineering Intelligence Operating System while preserving the behavioral architecture defined by RUN-100 and the logical ownership defined by SYS-100.**

Reference Architecture defines composition — which Logical Systems are arranged together, and why. It does not define implementation — no technology, language, database, or deployment concept appears anywhere in this document (Constraints, §11).

## 4. Reference Composition Principles

Every composition in this document (§6) preserves, without exception:

| Principle | Preserved by citing |
| --- | --- |
| **Ownership** | SYS-100 §9 (Information Ownership) — a composition never reassigns which Logical System owns what. |
| **Runtime behavior** | RUN-100 §6.1 (Capability Contracts) — a composition never alters a Contract's own Preconditions, Postconditions, or Invariants. |
| **Governance** | SYS-100 §6.5 / RUN-100 §14 — every composition remains checked by `LSYS-005`, never bypassed. |
| **Evidence** | SYS-100 §6.6 / RUN-100 §16 — every composition's own behavior remains recorded by `LSYS-006`. |
| **Observability** | SYS-100 §6.7 / RUN-100 §17 — every composition's own behavior remains surfaced by `LSYS-007`. |
| **Traceability** | SYS-100 §5 (Responsibility Allocation) — every composed system still traces to exactly one `RESP-NNN` and one `PCAP-NNN`. |
| **Logical boundaries** | SYS-100 §10 — a composition groups systems for description; it never merges two systems' own Ownership, Responsibility, or Information Boundaries. |
| **Trust boundaries** | ADR-100 §15 / SYS-100 §10 — a composition never crosses a Platform Boundary without `LSYS-008`. |

## 5. Reference Topology

Composed entirely from `LSYS-001`–`LSYS-008` (SYS-100 §6) — no Logical System is added, removed, or renamed.

```
Sequential spine:
   LSYS-001 → LSYS-002 → LSYS-003 → LSYS-004 → LSYS-006

Cross-cutting (span every system above and below):
   LSYS-005 (Governance Hosting)
   LSYS-007 (Observability Hosting)

Conditional (joins only for genuine cross-Application interaction):
   LSYS-008 (Collaboration Hosting)
```

This topology restates SYS-100 §8's own Logical Collaborations exactly — no new arrangement, only the same one given a reference-architecture framing. The **sequential spine** is the platform's own processing backbone; the **cross-cutting** pair is consulted at every point along it and at every point of every composition below (§6), never a stage of its own; the **conditional** system participates only when a Runtime Session genuinely spans two or more Applications (RUN-100 §21, Scenario boundary).

## 6. Reference Compositions

Descriptive arrangements only — **not new governed entities or identity spaces** (Writing Guidelines, restated as binding). A Logical System may appear in more than one composition below; this is expected, since a composition describes a *view* of the same eight systems, never a new, exclusive partition of them.

### 6.1 Core Platform Composition

| Field | Value |
| --- | --- |
| Purpose | The platform's own processing backbone — realize an Engineering Request into a Completed Runtime Session. |
| Included Logical Systems | `LSYS-001`, `LSYS-002`, `LSYS-003`, `LSYS-004`, `LSYS-006`. |
| Responsibilities Realized | `RESP-001`, `RESP-002`, `RESP-003`, `RESP-004`, `RESP-006` (SYS-100 §5.2). |
| Runtime Behavior Preserved | RUN-100 §6.1's own Contracts for `PCAP-001`–`PCAP-004`, `PCAP-006`, unaltered. |
| Architectural Rationale | Restates SYS-100 §8's own sequential collaboration chain — this composition names it as a reusable unit rather than re-deriving it per Application. |
| Boundaries | Never includes `LSYS-005`/`LSYS-007` as sequential members — they cross-cut this composition (§7), never join its own spine. |
| Quality Considerations | Composability — every hand-off along the spine is a declared Contract (RUN-100 §6.1), never an undeclared one. |

### 6.2 Governance Composition

| Field | Value |
| --- | --- |
| Purpose | The platform's own continuous conformance-checking arrangement. |
| Included Logical Systems | `LSYS-005`, observing every other system. |
| Responsibilities Realized | `RESP-005`. |
| Runtime Behavior Preserved | RUN-100 §14's own Governance model — checks, never overrides (ADR-100 §8 L5/L6). |
| Architectural Rationale | Restates SYS-100 §6.5's own cross-cutting judgment — a composition of one, by design, since `LSYS-005` collaborates with every other system identically. |
| Boundaries | Never redirects another system's own decision (SYS-100 §6.5's own Boundaries field). |
| Quality Considerations | Governability — `LSYS-005`'s own conformance is checked by the same discipline it applies to others (SYS-100 §6.5). |

### 6.3 Knowledge Composition

| Field | Value |
| --- | --- |
| Purpose | Cross-Application knowledge capture and retrieval. |
| Included Logical Systems | `LSYS-004`, informed by `LSYS-006`'s own Evidence records. |
| Responsibilities Realized | `RESP-004`. |
| Runtime Behavior Preserved | RUN-100 §6.1's own `PCAP-004` Contract, unaltered. |
| Architectural Rationale | `LSYS-004`'s own Consumed Information (SYS-100 §6.4) is naturally sourced from `LSYS-006`'s own Evidence — this composition names that relationship explicitly, without adding a new collaboration SYS-100 §8 does not already permit. |
| Boundaries | Never attributes a lesson to an Application that did not produce it (SYS-100 §6.4's own Boundaries field). |
| Quality Considerations | Traceability — every lesson traces to its originating Runtime Session (SYS-100 §6.4). |

### 6.4 Evidence Composition

| Field | Value |
| --- | --- |
| Purpose | Retain Evidence and aggregate Observability as one coherent record-keeping arrangement. |
| Included Logical Systems | `LSYS-006`, `LSYS-007`. |
| Responsibilities Realized | `RESP-006`, `RESP-007`. |
| Runtime Behavior Preserved | RUN-100 §16 (Evidence) and §17 (Observability), unaltered. |
| Architectural Rationale | Both systems are, in RUN-100's own terms, aggregation sinks — `LSYS-006` for Evidence, `LSYS-007` for Observability — a natural pairing this composition names, without merging their own distinct Ownership Boundaries (SYS-100 §10). |
| Boundaries | `LSYS-006` never alters a recorded Evidence entry; `LSYS-007` never alters a surfaced signal (SYS-100 §6.6, §6.7). |
| Quality Considerations | Auditability — the full record is reconstructable after the fact (SYS-100 §6.6). |

### 6.5 Cross-Application Composition

| Field | Value |
| --- | --- |
| Purpose | Govern interaction between two or more Applications. |
| Included Logical Systems | `LSYS-001` (registration precondition), `LSYS-008` (contract confirmation), `LSYS-005` (governance check). |
| Responsibilities Realized | `RESP-001`, `RESP-008`, `RESP-005`. |
| Runtime Behavior Preserved | RUN-100 §6.1's own `PCAP-001`, `PCAP-008` Contracts, unaltered. |
| Architectural Rationale | Restates SYS-100 §6.8's own Boundaries field — `LSYS-008` requires both parties already registered via `LSYS-001`, checked by `LSYS-005` — this composition names the three-system arrangement a genuine cross-Application interaction requires. |
| Boundaries | Never defines the contract's own content — only that one must exist (SYS-100 §6.8). |
| Quality Considerations | Composability — no interaction proceeds through an undeclared channel (SYS-100 §6.8). |

## 7. Cross-Cutting Architecture

`LSYS-005` (Governance Hosting) and `LSYS-007` (Observability Hosting) span every other Logical System — never a stage of the Reference Topology's own sequential spine (§5), always a concern consulted at every point along it.

**This derives directly from RUN-100 and SYS-100, introducing no new runtime behavior:**

- RUN-100 §14 already states Governance's own boundary: "observes every collaboration; it overrides none." RUN-100 §17 already states Observability's own boundary: "never alters the signal it surfaces, only aggregates it."
- SYS-100 §6.5 and §6.7 already gave both concerns a corresponding Logical System, explicitly marked cross-cutting — SYS-100's own architectural judgment, restated here, not re-decided.
- PRA-100 adds nothing beyond naming this arrangement as a first-class part of the Reference Topology (§5) and a composition of its own (§6.2, §6.4) — no new Responsibility, Capability Contract, or collaboration is introduced anywhere in this section.

## 8. Reference Views

| View | Purpose | Audience | Concerns Addressed | Architectural Rationale | Relationship to Other Views |
| --- | --- | --- | --- | --- | --- |
| **Platform Topology View** | Show §5 in full. | Platform Architect. | The overall shape of the platform. | Restates SYS-100 §8 at reference grain. | The organizing view every other view attaches to. |
| **Logical System Composition View** | Show §6's five compositions. | Platform Architect, Engineer. | How systems group into reusable arrangements. | §9's own rationale table. | Refines the Topology View. |
| **Capability Allocation View** | Show which `PCAP-NNN` (CAP-100 §8) each composition realizes. | Application Owner. | What business-facing capability a composition ultimately serves. | CAP-100 §9 (Capability Relationships). | Traces the Composition View back to CAP-100. |
| **Runtime Realization View** | Show which RUN-100 §6.1 Contract each composition preserves. | Engineer, Reviewer. | What behavioral guarantee a composition must not violate. | RUN-100 §6.1. | Constrains the Composition View. |
| **Information Ownership View** | Show SYS-100 §9 per composition. | Reviewer. | Who is accountable for what, inside a composition. | SYS-100 §9. | Feeds the Boundary View. |
| **Governance View** | Show §6.2 and §7's own Governance treatment. | Certification Authority. | Where conformance is checked across every composition. | RUN-100 §14, SYS-100 §6.5. | Cross-cuts every other view (restates §7). |
| **Evidence View** | Show §6.4's own Evidence half. | Certification Authority. | What is preserved, and why. | RUN-100 §16, SYS-100 §6.6. | Consumes the Composition View. |
| **Observability View** | Show §6.4's own Observability half and §7's cross-cutting treatment. | Operations, Engineer. | What is visible, and from where. | RUN-100 §17, SYS-100 §6.7. | Cross-cuts every other view (restates §7). |
| **Trust View** | Show §6.5's own boundary confirmation. | Security, Reviewer. | What may be relied upon between Applications. | ADR-100 §15, SYS-100 §10. | Bounds the Composition View. |
| **Boundary View** | Show §4's eight preservation principles. | Reviewer. | What a composition may never cross. | SYS-100 §10. | Bounds every other view. |
| **Evolution View** | Show §13's own maturity table. | Platform Architect. | How honestly-proven each composition is today. | SYS-100 §16, RUN-100 §24, CAP-100 §17. | The temporal complement to every other view. |

## 9. Architectural Rationale

Every composition (§6) and the Reference Topology (§5) trace to a specific upstream decision — no rationale is invented at this tier:

| Element | Traces to |
| --- | --- |
| Reference Topology's sequential spine (§5) | SYS-100 §8's own Logical Collaborations, which itself restates RUN-100 §9's own illustrative Capability Collaboration Model. |
| `LSYS-005`/`LSYS-007` as cross-cutting (§5, §7) | SYS-100 §6.5/§6.7's own architectural judgment, which itself restates RUN-100 §14/§17's own boundary language ("observes... overrides none"; "never alters... only aggregates"). |
| Core Platform Composition (§6.1) | ADR-100 §9's own eight Platform Capability rows, via CAP-100 §8's own catalog. |
| Governance Composition (§6.2) | ADR-100 §8's own L5/L6 non-override rule. |
| Knowledge Composition (§6.3) | ADR-100 §16's own Knowledge Architecture. |
| Evidence Composition (§6.4) | ADR-100 §15's own Trust Architecture and §19's own Observability Architecture. |
| Cross-Application Composition (§6.5) | ADR-100 §9's own Collaboration Hosting row and §6's own Platform Boundaries. |

**No composition's rationale is invented at the PRA-100 tier** — every row above resolves to a specific ADR-100, CAP-100, RUN-100, or SYS-100 citation, never a new justification this document alone supplies.

## 10. Quality Attributes

| Attribute | How the Reference Architecture preserves it |
| --- | --- |
| **Cohesion** | Every composition (§6) groups only systems that already collaborate under SYS-100 §8 — never an arbitrary grouping. |
| **Low Coupling** | A composition depends only on its own Included Logical Systems' declared Collaborating Logical Systems (SYS-100 §6) — never an undeclared one. |
| **Composability** | Compositions themselves compose — the Cross-Application Composition (§6.5) reuses `LSYS-001` and `LSYS-005`, already members of other compositions, without duplicating their own definition. |
| **Determinism** | The same Reference Topology (§5), applied to the same Engineering Request, yields the same composed behavior — restating RUN-100 §19's own Deterministic quality attribute at this tier. |
| **Explainability** | Every composition's own Architectural Rationale (§6, §9) is citable, never asserted without a specific upstream source. |
| **Governability** | Every composition remains subject to `LSYS-005` (§4, §6.2) — no composition is exempt. |
| **Traceability** | §9, in full. |
| **Observability** | Every composition remains subject to `LSYS-007` (§4, §6.4) — no composition is exempt. |
| **Evolvability** | A new composition may be added (§13) without altering an existing one's own five fields, restating ADR-100 §6's own Extensibility principle at this tier. |

## 11. Constraints

PRA-100 SHALL NOT introduce: deployment, infrastructure, networking, cloud providers, Kubernetes, APIs, protocols, databases, implementation, or programming languages. Verified section by section (§14) — every composition (§6) and view (§8) names only Logical Systems, Responsibilities, and Capability Contracts already established by SYS-100, RUN-100, and CAP-100.

## 12. Risks

Maintaining the same "honest maturity" discipline established in CAP-100, RUN-100, and SYS-100:

| Category | Risk |
| --- | --- |
| **Composition** | Every one of §6's five compositions is proposed against Logical Systems that themselves reach, at most, Allocated maturity (SYS-100 §11) — no composition has ever actually operated. |
| **Topology** | §5's sequential spine has real precedent only through Requirements Intelligence's own informal, retrofitted mapping (SYS-100 §16) — never through an actual composed execution. |
| **Boundary** | §6's compositions overlap by design (a system may belong to more than one) — untested against a case where two compositions' own Quality Considerations genuinely conflict. |
| **Governance** | The Governance Composition (§6.2) is, by its own nature, a composition of one system observing seven others — if `LSYS-005` itself is ever wrong, no composition in this document catches it (restates RUN-100 §23's own risk one tier further). |
| **Evolution** | This is the first real per-Artifact `PRA-NNN` (§1, §2) — its own reconciliation against the platform-wide `PRA-001` (HB-001 §20.12) has not yet been reviewed by Governance, restating SYS-100 §4.1's own unreviewed-reconciliation caveat one tier further. |
| **Scalability assumptions** | Every composition assumes a single-Application load — no composition has been reasoned about under multiple, concurrent Applications' own genuine collaboration (§6.5's own Cross-Application Composition remains entirely theoretical, CAP-100 §7). |

## 13. Known Limitations

| Composition | Maturity |
| --- | --- |
| Core Platform Composition (§6.1) | **Conceptual** — composed of systems that are, at best, Piloted (SYS-100 §16); never itself operated as one arrangement. |
| Governance Composition (§6.2) | **Conceptual** — `LSYS-005` itself remains Conceptual (SYS-100 §16). |
| Knowledge Composition (§6.3) | **Conceptual** — `LSYS-004` itself remains Conceptual (SYS-100 §16). |
| Evidence Composition (§6.4) | **Conceptual** — both member systems remain, at best, Partially real (SYS-100 §16). |
| Cross-Application Composition (§6.5) | **Conceptual** — `LSYS-008` remains Conceptual, and no second Application exists to compose it against (SYS-100 §16, CAP-100 §7). |

- **No composition in this document has been validated against a real, running arrangement** — every one is proposed, never observed.
- **This document's own first-real-exercise status (§1, §2) is itself unreviewed** — its reconciliation against `PRA-001` per HB-001 §20.12 is this document's own reasoned position, not yet checked by Governance (restates CAP-100 §17's own caveat for `PCAP-NNN`, one tier further).
- **Deferred to IMP-100 in full:** every technology, language, database, deployment, and infrastructure decision this document deliberately excludes (§11).
- **Future reference evolution (reserved, not authorized by this document):** a second real Application's own composition, once one exists, would be the first genuine test of whether §6's five compositions generalize beyond Requirements Intelligence's own single-data-point evidence.

## 14. Final Self Review

- [x] Alignment with HB-001 — this document's own status as the first real per-Artifact `PRA-NNN` is reconciled against HB-001 §20.12, not silently assumed.
- [x] Alignment with STD-000–STD-005 — every semantic and principle cited (§1, §4, §10) references a specific STD section.
- [x] Alignment with PRD-100 — no business intent is redefined; every composition realizes, never redefines, intent traced back through CAP-100/ADR-100.
- [x] Alignment with ADR-100 — every composition's own rationale (§9) cites a specific ADR-100 section.
- [x] Alignment with CAP-100 — every composition traces to specific `PCAP-NNN` capabilities (§6, §9); maturity is inherited honestly (§13).
- [x] Alignment with RUN-100 — every composition preserves a specific RUN-100 §6.1 Contract, unaltered (§4, §6).
- [x] Alignment with SYS-100 — every Logical System used (§5, §6) is exactly one of SYS-100 §6's own eight; none is added, removed, or renamed.
- [x] Composition completeness — all five required compositions (§6) are fully specified with all seven required fields.
- [x] Technology independence — verified section by section (§11); no API, database, deployment, or implementation concept appears anywhere.
- [x] Readiness for IMP-100 — §6's compositions and §9's rationale give a future IMP-100 a stable, justified blueprint to realize in technology, without this document introducing a new architectural concept itself.

## 15. Reference Architecture Compliance Certificate

**This certifies that PRA-100, Version 1.0:**

- ✅ **Reference Architecture Complete** — §3–§13 define philosophy, composition principles, topology, five reference compositions, cross-cutting architecture, eleven reference views, architectural rationale, quality attributes, constraints, risks, and known limitations.
- ✅ **Derived Solely from SYS-100** — every Logical System, Responsibility, and Capability Contract used (§5, §6, §9) is exactly one SYS-100/RUN-100/CAP-100 already established; no new Logical System, identity space, capability, or runtime behavior is introduced.
- ✅ **Specializes, and Never Contradicts, PRA-001** — verified throughout (§1, §7, §12); this is the first real exercise of HB-001 §20.12's own per-Artifact `PRA-NNN` rule.
- ✅ **Technology Independent** — no deployment, infrastructure, networking, cloud provider, Kubernetes, API, protocol, database, implementation, or programming language appears anywhere (§11, §14).
- ✅ **Vendor Neutral** — verified throughout; no provider, tool, or service is named.
- ✅ **Cloud Neutral** — verified; §11 confirms no infrastructure or deployment concept is introduced.
- ✅ **Ready for IMP-100** — implementation-strategy derivation, per §14's own readiness check.
- ✅ **Suitable for Architecture Review Board Approval.**

**PRA-100 is the authoritative reference realization architecture for the Engineering Intelligence Operating System.**

---

*End of PRA-100, Version 1.0.*
