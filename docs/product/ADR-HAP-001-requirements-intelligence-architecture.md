# ADR-HAP-001 — Requirements Intelligence Architecture

**Hosted Application Architecture Decision Record · Version 1.0 (Draft)**

## 1. Document Metadata

| Field | Value |
| --- | --- |
| Identifier | ADR-HAP-001 (as commissioned — see §1.1) |
| Title | Requirements Intelligence Architecture |
| Category | Hosted Application Architecture Decision Record |
| Status | Draft |
| Authority | Engineering Intelligence Operating System (EIOS) |
| Version | 1.0 (Draft) |
| Owner | Engineering Architecture Council |
| Stakeholders | Enterprise Architects, Solution Architects, AI Architects, Platform Architects, Software Engineers, Platform Engineers, Security Architects, DevOps Engineers, Engineering Governance Teams |
| **Derived From** | **PRD-HAP-001 — Requirements Intelligence** (the sole content source), matching STD-005 §6's **Refines** semantic and HB-001 §20.3's own ADR-family row. |
| Governing Standards | HB-001 (Revision 4), STD-000 through STD-009 |
| Dependencies | PRD-HAP-001, HB-001, STD-000–STD-009 |
| Related Documents | `ADR-001`, `CAP-001`, `RUN-001`, `SYS-001`, `PRA-001`, `IMP-001` (existing, real documents — cited throughout as precedent and constraint, **never redefined**, §1.2); `ADR-100`, `CAP-100`, `RUN-100`, `SYS-100`, `PRA-100` (the EIOS platform's own architecture, which this document's own Application sits inside, per ADR-100 §7.2). |
| Supersedes | Nothing |
| Superseded By | Not applicable |

### 1.1 Identifier Reconciliation

`ADR-HAP-001` is used exactly as commissioned. **It does not conform to HB-001 §20.5's Naming Convention** (`<FAMILY>-<NNN>`; `HAP` is precisely the compound infix §20.5 forbids), for the same reason PRD-HAP-001 §1.1 already recorded of itself. Under HB-001 §20.4's Bounded Context Classification, Requirements Intelligence's range is `200–299`; the conformant identifier would be `ADR-201` — the second document in that range, following `PRD-201` (PRD-HAP-001 §1.1's own reconciled identity). **This document does not resolve the naming question — HB-001 §20.14 reserves that resolution to HB-001 alone.** It is recorded here, once, rather than re-litigated per section.

### 1.2 Relationship to Existing Architecture

**`ADR-001` remains entirely unmodified by this document.** `ADR-HAP-001` is derived from `PRD-HAP-001` (§1, above) — not from `ADR-001`, and not in supersession of it. **`CAP-001`'s own header already declares `Derived From: ADR-001`; this document does not, and architecturally cannot, retroactively change that citation.** `CAP-001` through `IMP-001` remain exactly as they were built, valid and authoritative for what they already govern (Capture, Enrichment, and Evidence Grounding — `CAP-001`'s own declared Boundary). This ADR is offered as what a dedicated `ADR-201` would be, going forward, for the parts of Requirements Intelligence's own vision that exceed `CAP-001`'s own existing scope (§1.3, §15 AD-1, §21) — never as a silent amendment to a document three real, Frozen-track Artifacts already depend on.

### 1.3 Architecture Maturity Reconciliation

This document distinguishes four architectural maturity levels throughout (defined in full in §6) and tags every major concept it introduces against them. **No concept is presented at a higher maturity level than its evidence supports.** Where a concept — most significantly the Engineering Graph (§11) and the Agent Architecture (§13) — has real evidence at Conceptual or Reference level only, this document says so explicitly rather than allowing architectural narrative to imply a Current Realization that does not exist. The full accounting is repeated, not merely asserted once, in §23.

## 2. Executive Summary

This ADR architects Requirements Intelligence as EIOS's first Hosted Application, per ADR-100 §7.2's own Application Domain — an Engineering Reasoning Platform whose purpose is to reason over governed engineering knowledge before producing an engineering deliverable, never to generate directly from raw business intent. **Three reconciliations govern how this document should be read, stated once here and never silently assumed resolved elsewhere in this document:** the identifier this document was commissioned under does not conform to this platform's own naming convention (§1.1); this document does not, and cannot, alter `ADR-001`'s or `CAP-001`'s own existing content (§1.2); and the vision this document architects — an Engineering Graph, an Agent Architecture, and a reasoning pipeline that generates deliverables — extends beyond `CAP-001`'s own already-Frozen Boundary, a gap this document names explicitly (§15 AD-1, §21) rather than resolves by architectural assertion alone. Every major concept in this document is tagged against a four-level maturity model (§6); the honest total, restated in §23, is that almost everything this document architects sits at Conceptual or Reference maturity — Requirements Intelligence's own existing `CAP-001`-through-`IMP-001` lineage is this document's only Current Realization evidence.

## 3. Architectural Mission

The architecture SHALL ensure:

```
Business Intent
        ↓
Engineering Understanding
        ↓
Governed Engineering Knowledge
        ↓
Engineering Reasoning
        ↓
Engineering Deliverable
```

becomes the standard reasoning pipeline. The architecture SHALL guarantee: LLMs are generators, never the System of Record; EIOS is the engineering knowledge authority; humans remain accountable; every decision remains traceable.

## 4. Architectural Drivers

| Driver | Originating Requirement |
| --- | --- |
| The architecture must ensure the LLM never receives a raw business requirement without governed context. | PRD-HAP-001 FR-03. |
| The architecture must make engineering context retrieval a distinct, prior step to reasoning. | PRD-HAP-001 FR-03, §16 (Engineering Knowledge Retrieval capability). |
| The architecture must make a generated deliverable's own reasoning explainable. | PRD-HAP-001 FR-11, Principle 9 (PRD-HAP-001 §8). |
| The architecture must require human review before conformance review, and conformance review before publication. | PRD-HAP-001 FR-06, FR-07. |
| The architecture must preserve traceability from every generated deliverable back to its own business requirement. | PRD-HAP-001 FR-08, §27. |
| The architecture must remain modular enough to support Architecture Intelligence, Test Intelligence, Implementation Intelligence, Review Intelligence, and Engineering Analytics without redesign. | PRD-HAP-001 §31. |
| The architecture must reuse EIOS's own shared platform capabilities rather than reimplement them. | PRD-HAP-001 NFR Interoperability (§18). |

## 5. Architectural Principles

| # | Principle | Restates |
| --- | --- | --- |
| 1 | The LLM SHALL NEVER become the System of Record. | PRD-HAP-001 Principle 10 (§8). |
| 2 | The Engineering Knowledge Repository SHALL remain authoritative. | PRD-HAP-001 Principle 11 (§8), specialized here to a specific Shared Platform Capability (§12). |
| 3 | Engineering Context SHALL be retrieved before prompting. | PRD-HAP-001 FR-03. |
| 4 | Reasoning SHALL be explainable. | ADR-100 §6 Explainability by Design; PRD-HAP-001 Principle 9. |
| 5 | Prompt construction SHALL be deterministic. | STD-000 Principle 8, applied to §14's own Prompt Assembly stage. |
| 6 | Human approval SHALL remain mandatory. | PRD-HAP-001 Principle 4, FR-06, FR-12. |
| 7 | Every generated artifact SHALL remain traceable. | STD-004; PRD-HAP-001 FR-08. |
| 8 | Architecture SHALL remain modular. | ADR-100 §6 Loose Coupling / High Cohesion. |
| 9 | Hosted Applications SHALL reuse shared platform capabilities. | ADR-100 §7.4's own Shared Platform Services Domain. |
| 10 | Architecture SHALL support future Hosted Applications without redesign. | ADR-100 §6 Extensibility; PRD-HAP-001 §31. |

## 6. Architectural Maturity Model

**Mandatory, normative, used consistently throughout this document.**

| Level | Meaning | SHALL / SHALL NOT |
| --- | --- | --- |
| **Level 1 — Conceptual Architecture** | Explains why an architectural concept exists. | SHALL NOT prescribe implementation. |
| **Level 2 — Reference Architecture** | Defines the recommended structure, responsibilities, and interactions. | SHALL remain implementation independent. |
| **Level 3 — Current Realization** | Describes what actually exists today. | SHALL NOT overstate maturity; SHALL distinguish implemented from planned capability. |
| **Level 4 — Future Realization** | Describes capability intentionally deferred to future governed work. | SHALL identify the governance action required before implementation. |

**No concept SHALL silently move between levels.** Every major concept this document introduces is tagged explicitly, at first mention and in the summary below:

| Concept | Maturity Level(s) Present in This Document |
| --- | --- |
| Engineering Graph | 1 (Conceptual), 2 (Reference) — §11. **No Level 3 exists.** |
| Agent Architecture | 1 (Conceptual), 2 (Reference) — §13. **No Level 3 exists.** |
| Shared Platform Services | 1–4, varies per service — §12. |
| Knowledge Repository | 1–2 (Conceptual/Reference); one Level 3 precedent exists via `PRA-001` §8's own Prompt Registry, a narrower, already-Realized instance — §12. |
| Context Retrieval | 1–2; Level 3 precedent via `IMP-001` §6's own `context_orchestration/` (capability-scoped) — §11, §13. |
| Prompt Assembly | 1–2; Level 3 precedent via `IMP-001` §6's own `prompts/framework/prompt_registry.py` — §13, §14. |
| Reasoning Pipeline | 1–2; Level 3 precedent via `IMP-001` §6's own single bounded Gemini call — §13, §14. |
| Model Routing | 1–2; Level 3 precedent via `IMP-001` §6's own `llm_factory.py`, a static, capability-scoped factory — §12. |
| Engineering Review | 1–2 only. **No Level 3 exists** — PRD-HAP-001 FR-06 is a requirement, not yet a built gate. |
| Conformance Review | 1–2 only, specializing STD-008 (which is itself, per STD-008 §13, entirely unexercised) — §22. |

## 7. Architecture Overview

Requirements Intelligence's own architecture is the Application-tier realization of ADR-100 §7.2's own Application Domain — it consumes, never duplicates, ADR-100 §7.3's Core Platform Domain concerns and §7.4's Shared Platform Services, exactly as ADR-100 §5 already requires of every Hosted Application. §3's own reasoning pipeline is this Application's own specific behavior; §6's own maturity model is the discipline every subsequent section applies to describing it.

## 8. System Context

```
Business Users
        ↓
Requirements Intelligence
        ↓
Engineering Knowledge Layer (EIOS)
        ↓
Engineering Graph
        ↓
AI Orchestrator
        ↓
LLMs
        ↓
Generated Engineering Deliverables
        ↓
Engineering Review
        ↓
Engineering Conformance
```

| Element | Maturity |
| --- | --- |
| Business Users, Requirements Intelligence | Level 3 — Requirements Intelligence exists today, via `CAP-001`–`IMP-001`. |
| Engineering Knowledge Layer (EIOS) | Level 3 for what ADR-100/CAP-100 already architect and PRA-100 partially realizes; Level 1–2 for the specific knowledge this Application would draw from it. |
| Engineering Graph | Level 1–2 only (§11). |
| AI Orchestrator | Level 1–2 only (§13's own Agent Architecture). |
| LLMs | Level 3 — a real, live Gemini integration exists (`IMP-001` §6), capability-scoped. |
| Generated Engineering Deliverables, Engineering Review, Engineering Conformance | Level 1–2 only — none of PRD-HAP-001's own Version 1.0 workflow (§19) has been built. |

## 9. Reference Architecture

**Level 2.** Requirements Intelligence's own recommended structure consists of four responsibility groups, each consuming ADR-100's own domains without duplicating them:

| Group | Responsibility | Consumes (ADR-100) |
| --- | --- | --- |
| **Interaction** | Accept a business requirement; surface a reviewed deliverable. | Experience Domain (§7.1). |
| **Reasoning** | Engineering Understanding, Context Retrieval, Reasoning, Prompt Assembly (§13, §14). | Core Platform Domain's Reasoning concern (§7.3); Shared Platform Services (§7.4). |
| **Generation** | Produce the candidate deliverable from the assembled prompt. | Core Platform Domain's Transformation concern. |
| **Assurance** | Engineering Review, Engineering Conformance Review. | Core Platform Domain's Governance and Evidence concerns; STD-006, STD-008. |

## 10. Architectural Layers

The architecture follows **Layered Architecture**, combined with **Agent-Oriented Orchestration** (§13) and **Event-Driven Workflows where appropriate** — **avoiding monolithic orchestration**, per this document's own Architectural Style.

| Layer | Responsibility | Orchestration Style |
| --- | --- | --- |
| **Interaction Layer** | §9's own Interaction group. | Request/response — no agent needed. |
| **Reasoning Layer** | §9's own Reasoning group; hosts the Agent Architecture (§13). | Agent-oriented — each stage (§14) is a distinct agent, never one monolithic reasoning step. |
| **Generation Layer** | §9's own Generation group. | Agent-oriented, a single Generation Agent (§13). |
| **Assurance Layer** | §9's own Assurance group. | Event-driven where practical — a completed generation *event* triggers Review, a completed Review *event* triggers Conformance, never a single orchestrator polling for both. |

**No layer performs monolithic orchestration** — restating this document's own Architectural Style and ADR-100 §6's own Loose Coupling principle at this Application's own grain.

## 11. Engineering Graph

**The Engineering Graph is treated as an architectural concept — it SHALL NOT be described as an implemented subsystem, and this document does not do so.**

| Maturity | Content |
| --- | --- |
| **Conceptual Architecture (Level 1)** | The Engineering Graph exists, conceptually, to connect every engineering object this Application touches — the business requirement, the retrieved engineering context, the generated deliverable, and the Evidence/Traceability records STD-004 and STD-006/007 already require — into one queryable structure, so that "what informed this generation" (Principle 4, §5) is answerable without reconstructing it from memory. |
| **Reference Architecture (Level 2)** | Recommended structure: nodes for Business Requirement, Engineering Context, Capability Contract (RUN-100 §6.1-style, generalized), Generated Deliverable, and Evidence record; edges restricted to STD-004's own fourteen relationship types, never a fifteenth invented here. Traceability is preserved by requiring every edge to cite the specific STD-005 transformation that produced it (STD-005 §17). |
| **Current Realization (Level 3)** | **None exists.** No `CAP`, `RUN`, `SYS`, or `IMP` document architects or builds an Engineering Graph today. |
| **Future Realization (Level 4)** | A future `CAP` (either a revised `CAP-001` or a new capability, per §15 AD-1) would need to realize this concept, plausibly by graduating `PRA-001` §8's own Reserved Traceability Service, Knowledge Registry, and Document Registry to real, queryable status — named as the plausible foundation, never mandated as the implementation (Technology Boundary, §17). |

## 12. Shared Platform Capabilities

Every capability below states its own Current Maturity, Expected Future Maturity, and whether it exists today or requires future realization — cross-referenced against `PRA-001` §8's own existing catalog where one already exists.

| Capability | Current Maturity | Future Maturity | Exists Today? |
| --- | --- | --- | --- |
| **Knowledge Repository** | Level 1–2. | Level 3, via a graduated `PRA-001` §8 Knowledge Registry (currently Reserved). | No. |
| **Traceability Service** | Level 1–2. | Level 3, via `PRA-001` §8's own Traceability Service (currently Reserved). | No. |
| **Identity Service** | Level 1–2. | Level 3, via `PRA-001` §8's own Identity Service (currently Reserved). | No. |
| **Prompt Catalog** | **Level 3** — real precedent exists. | Level 3, platform-wide, via `PRA-001` §8's own Prompt Registry (currently Realized, capability-scoped). | Partially — capability-scoped only. |
| **Context Catalog** | **Level 3** — real precedent exists. | Level 3, platform-wide, via `PRA-001` §8's own Context Manager (currently Realized, capability-scoped). | Partially — capability-scoped only. |
| **Model Routing** | **Level 3** — real precedent exists. | Level 3, platform-wide, via `PRA-001` §8's own Model Router (currently Partially Realized, capability-scoped). | Partially — capability-scoped only. |
| **Audit Service** | Level 1–2. | Level 3, via `PRA-001` §8's own Audit Service (currently Reserved). | No. |
| **Governance Service** | Level 1–2. **Not in `PRA-001` §8's own existing catalog.** | Level 3, specializing STD-006's own model — a candidate addition to a future `PRA-001`/`ADR-100` revision, named here, never added to that catalog by this document. | No. |
| **Conformance Service** | Level 1–2. **Not in `PRA-001` §8's own existing catalog.** | Level 3, specializing STD-008's own model — same candidate-addition caveat as Governance Service. | No. |
| **Review Service** | Level 1–2. **Not in `PRA-001` §8's own existing catalog.** | Level 3, hosting PRD-HAP-001 FR-06's own human review gate. | No. |
| **Notification Service** | Level 1–2. | Level 3, via `PRA-001` §8's own Notification Service (currently Reserved). | No. |

**Reconciliation Note.** Governance Service, Conformance Service, and Review Service do not appear in `PRA-001` §8's own twenty-one-service catalog — this document names them as capabilities Requirements Intelligence's own architecture requires, without unilaterally amending `PRA-001`'s own catalog. Whether they become new, platform-wide Shared Platform Services or remain Application-specific is a future `PRA-001`/`ADR-100` governance decision (§21), not decided here.

## 13. Agent Architecture

**Conceptual and Reference architecture only (Level 1–2) — no Current Realization exists.** ADR-100 §9 and PRA-001 §9 already record Agent Orchestration and Tool Invocation as Reserved, not adopted, platform-wide defaults; this section's own seven illustrative agents are consistent with, never a silent contradiction of, that platform-wide reservation. Adopting a real agent framework for Requirements Intelligence specifically would itself require the kind of governed decision ADR-100 §29's own "Emerging AI Capabilities" roadmap item anticipates — never assumed authorized by this document alone.

| Agent | Responsibilities | Interactions | Boundaries |
| --- | --- | --- | --- |
| **Engineering Understanding Agent** | Structure the raw business requirement (PRD-HAP-001 §16). | Hands off to Context Retrieval Agent. | Never retrieves context or reasons — structuring only. |
| **Context Retrieval Agent** | Retrieve governed engineering context from the Engineering Graph (§11). | Consumes from Engineering Understanding; hands off to Reasoning Agent. | Never reasons about the context it retrieves. |
| **Reasoning Agent** | Combine the requirement and retrieved context into a governed reasoning basis. | Consumes from Context Retrieval; hands off to Prompt Assembly. | Never calls the LLM directly — assembly and generation remain distinct agents. |
| **Prompt Assembly Agent** | Construct a deterministic, sealed prompt (Principle 5, §5). | Consumes from Reasoning; hands off to Generation. | Never varies construction non-deterministically. |
| **Generation Agent** | Invoke the LLM; produce a candidate deliverable. | Consumes from Prompt Assembly; hands off to Engineering Review. | Never treats its own output as approved. |
| **Engineering Review Agent** | Present the candidate to a human reviewer (PRD-HAP-001 FR-06). | Consumes from Generation; hands off to Conformance Agent. | Never substitutes for the human reviewer — restates Principle 6 (§5). |
| **Conformance Agent** | Perform the Engineering Conformance Review (§22, STD-008). | Consumes from Engineering Review. | Never approves conformance on behalf of the human Conformance Authority (STD-006 §5) — restates STD-008 §4's own Objective Verification principle. |

**No implementation technology is defined for any agent above** (restating this section's own Scope boundary and §17's Technology Boundary).

## 14. Engineering Workflow

Restates PRD-HAP-001 §19, tagging each stage's own owning agent and maturity:

| Stage | Owning Agent (§13) | Maturity |
| --- | --- | --- |
| Engineering Understanding | Engineering Understanding Agent | Level 1–2. |
| Engineering Context Retrieval | Context Retrieval Agent | Level 1–2. |
| Engineering Reasoning | Reasoning Agent | Level 1–2. |
| Prompt Construction | Prompt Assembly Agent | Level 1–2; Level 3 precedent exists capability-scoped (§6, §12). |
| Cucumber Feature File Generation | Generation Agent | Level 1–2; Level 3 precedent exists capability-scoped (`IMP-001` §6). |
| Engineering Review | Engineering Review Agent | Level 1–2. |
| Engineering Conformance Review | Conformance Agent | Level 1–2. |

## 15. Architectural Decisions

### AD-1 — EIOS is the source of truth for engineering knowledge

| Field | Value |
| --- | --- |
| Context | A generation step needs governed engineering context; the alternative is trusting the LLM's own training data. |
| Alternatives Considered | (a) LLM-only generation from the raw requirement; (b) a bespoke, Application-private knowledge store; (c) EIOS's own shared Engineering Graph (§11). |
| Chosen Alternative | (c). |
| Rationale | Restates PRD-HAP-001 Principle 1/11 (§8) and ADR-100 §16's own Knowledge Architecture — one authoritative source, reused, never duplicated per Application. |
| Consequences | Requirements Intelligence depends on the Engineering Graph existing before its own Reasoning Layer can operate for real — a real, named dependency (§19), not yet satisfied. |
| Current Maturity Level | 1–2. |
| Future Governance Required | A future `CAP` (revised `CAP-001` or new, per this decision's own scope-expansion consequence, below) to realize the Engineering Graph. |
| Future Implications | **This decision is also where this document's own scope-expansion tension (§1.2, §2) becomes concrete**: `CAP-001`'s own declared Boundary (Capture, Enrichment, Evidence Grounding) does not include hosting an Engineering Graph or generating deliverables from it. Two resolution paths exist, neither chosen by this document: **(a)** `CAP-001` undergoes its own Architectural-category revision (STD-006 §7) extending its Boundary; **(b)** a new capability is registered (e.g. a future `CAP-201`) consuming `CAP-001`'s own Grounded output as its own input, leaving `CAP-001` unchanged. This document recommends (b) as architecturally cleaner — it never silently redraws a Frozen boundary — but the choice is a future governance act (§21), not this document's own to make. |

### AD-2 — Engineering knowledge precedes prompting

| Field | Value |
| --- | --- |
| Context | A prompt could be constructed directly from the raw requirement. |
| Alternatives Considered | (a) Prompt directly from requirement; (b) retrieve context first, then construct. |
| Chosen Alternative | (b). |
| Rationale | Restates PRD-HAP-001 FR-03 and Principle 2 (§8). |
| Consequences | Adds a mandatory Context Retrieval stage (§14) no simpler pipeline would require. |
| Current Maturity Level | 1–2. |
| Future Governance Required | None beyond AD-1's own dependency. |
| Future Implications | Every future deliverable type (PRD-HAP-001 §31) inherits this same ordering — restates Principle 10 (§5). |

### AD-3 — An Engineering Graph is required

| Field | Value |
| --- | --- |
| Context | Governed context (AD-2) must come from somewhere queryable. |
| Alternatives Considered | (a) Ad hoc, per-Application document search; (b) a shared, governed Engineering Graph (§11). |
| Chosen Alternative | (b). |
| Rationale | Restates ADR-100 §16 and PRA-001 §8's own Search/Knowledge Registry intent, generalized. |
| Consequences | See AD-1's own Future Implications. |
| Current Maturity Level | 1–2. |
| Future Governance Required | Same as AD-1. |
| Future Implications | Same as AD-1. |

### AD-4 — Retrieval precedes reasoning

| Field | Value |
| --- | --- |
| Context | Reasoning without retrieved context risks the same ungrounded-generation failure mode PRD-HAP-001 §22 already names. |
| Alternatives Considered | (a) Reason first, retrieve to justify after; (b) retrieve first, reason from what was retrieved. |
| Chosen Alternative | (b). |
| Rationale | Restates §10's own layered, non-monolithic design and Principle 3 (§5). |
| Consequences | The Reasoning Agent (§13) has no valid input until Context Retrieval completes. |
| Current Maturity Level | 1–2. |
| Future Governance Required | None. |
| Future Implications | None beyond §14's own ordering. |

### AD-5 — Reasoning precedes generation

| Field | Value |
| --- | --- |
| Context | Generation could occur directly from retrieved context, skipping an explicit reasoning step. |
| Alternatives Considered | (a) Retrieve then generate directly; (b) retrieve, reason explicitly, then generate. |
| Chosen Alternative | (b). |
| Rationale | Restates Principle 4's own Explainability requirement (§5) — an explicit reasoning artifact is what makes a generation later explainable. |
| Consequences | An additional, distinct agent (§13) and pipeline stage (§14). |
| Current Maturity Level | 1–2. |
| Future Governance Required | None. |
| Future Implications | None. |

### AD-6 — Generation precedes review

| Field | Value |
| --- | --- |
| Context | A human could review the reasoning basis before generation, rather than the generated deliverable after. |
| Alternatives Considered | (a) Review the reasoning basis pre-generation; (b) review the generated deliverable post-generation. |
| Chosen Alternative | (b). |
| Rationale | PRD-HAP-001's own workflow (§19) reviews the concrete deliverable, matching what a Business Analyst or QA Architect (PRD-HAP-001 §13) actually needs to judge. |
| Consequences | A flawed reasoning basis is only caught once its own output is reviewed, not earlier. |
| Current Maturity Level | 1–2. |
| Future Governance Required | None. |
| Future Implications | A future Review Intelligence (PRD-HAP-001 §31) could add a pre-generation review stage without redesigning this one. |

### AD-7 — Review precedes publication (Conformance gates Approval)

| Field | Value |
| --- | --- |
| Context | A reviewed deliverable could be published without a separate conformance check. |
| Alternatives Considered | (a) Human review alone; (b) human review, then Conformance Review (STD-008) before Approval. |
| Chosen Alternative | (b). |
| Rationale | Restates PRD-HAP-001 FR-07 and STD-008 §4's own Evidence Before Assertion principle — human judgment and objective conformance verification are distinct checks. |
| Consequences | Two gates, never one, before a deliverable reaches `Approved` (PRD-HAP-001 §19). |
| Current Maturity Level | 1–2. |
| Future Governance Required | None beyond STD-008's own existing, unexercised model (STD-008 §13). |
| Future Implications | None. |

### AD-8 — Humans remain accountable

| Field | Value |
| --- | --- |
| Context | AI assistance could be treated as sufficient authority for publication on its own. |
| Alternatives Considered | (a) Fully automated publication; (b) mandatory human accountability at every governance boundary. |
| Chosen Alternative | (b). |
| Rationale | Restates ADR-001 §13, ADR-100 §17, PRD-HAP-001 Principle 4/FR-12, and STD-001 §10 Principle 6 — the single most repeated principle in this entire platform's own lineage. |
| Consequences | No stage of §14's own workflow may be fully automated away. |
| Current Maturity Level | 1–2 (the requirement is architected; no implementation enforces it yet). |
| Future Governance Required | None beyond building it. |
| Future Implications | Every future deliverable type (§31) inherits this same non-negotiable constraint. |

### AD-9 — Hosted Applications share common services

| Field | Value |
| --- | --- |
| Context | Requirements Intelligence could build its own private Prompt Catalog, Model Router, and so on. |
| Alternatives Considered | (a) Private, Application-specific services; (b) EIOS's own Shared Platform Services (ADR-100 §7.4). |
| Chosen Alternative | (b). |
| Rationale | Restates Principle 9 (§5) and ADR-100 §7.4's own "performs no business logic of its own" framing. |
| Consequences | Requirements Intelligence's own architecture (§9) is defined in terms of what it consumes from EIOS, never what it reimplements. |
| Current Maturity Level | 3 for the few services with real, capability-scoped precedent (§12); 1–2 for the rest. |
| Future Governance Required | Graduating capability-scoped precedent to platform-wide services remains PRA-100's own future work (PRA-100 §12, §13). |
| Future Implications | Every future Hosted Application (PRD-HAP-001 §31) inherits the same shared services, never reimplementing them. |

### AD-10 — Deterministic workflows surround probabilistic AI

| Field | Value |
| --- | --- |
| Context | Every stage of §14 could be treated as equally probabilistic. |
| Alternatives Considered | (a) Treat the entire pipeline as probabilistic; (b) bound the one genuinely probabilistic step (Generation, via the LLM) inside deterministic Understanding, Retrieval, Reasoning structuring, Assembly, Review, and Conformance stages. |
| Chosen Alternative | (b). |
| Rationale | Restates STD-000 Principle 8 and IMP-001 §6's own real precedent — "exactly one bounded LLM call per governed unit of work." |
| Consequences | Only the Generation Agent (§13) is genuinely probabilistic; every other agent is deterministic by design. |
| Current Maturity Level | 1–2 architecturally; Level 3 precedent exists for the one bounded call pattern itself (`IMP-001` §6). |
| Future Governance Required | None. |
| Future Implications | This is the architectural guarantee that makes Principle 5 (deterministic prompt construction, §5) achievable at all. |

## 16. Quality Attributes

| Attribute | How this architecture achieves it |
| --- | --- |
| Explainability | Every generated deliverable traces to its own recorded reasoning basis (AD-5) and retrieved context (AD-2, AD-4). |
| Determinism | Every non-Generation agent (§13) is deterministic by design (AD-10). |
| Traceability | The Engineering Graph (§11), once realized, and STD-004 in the interim. |
| Governability | AD-7's own two-gate discipline; STD-006 in full. |
| Modularity | §10's own layered, agent-oriented, non-monolithic design. |
| Reusability | AD-9's own Shared Platform Services discipline. |
| Extensibility | §5 Principle 10; §31's own future deliverable types added without redesign. |
| Human Accountability | AD-8, the most binding attribute in this document. |

## 17. Constraints

- This architecture SHALL NOT mandate a vendor or product. Technology **categories** MAY be discussed (API Layer, Workflow Engine, Knowledge Store, Graph Store, Vector Retrieval, LLM Gateway, Observability, Identity, Logging, Messaging) — every one of these remains a future `PRA`/`IMP` decision, never this document's own.
- This architecture SHALL NOT redefine any concept HB-001, STD-000 through STD-009, `PRD-HAP-001`, `ADR-001`, `CAP-001`, `RUN-001`, `SYS-001`, `PRA-001`, or `IMP-001` already define (Consistency Requirements, header).
- This architecture SHALL NOT silently supersede `CAP-001`'s own Boundary (§1.2, §15 AD-1) — any extension is named as requiring its own future governance act.

## 18. Assumptions

- A future governance act (§21) will resolve AD-1's own two-path scope-expansion question before implementation begins in earnest.
- `PRA-001`'s own Reserved and Partially Realized services (§12) will graduate to platform-wide Realized status before this Application's own Reasoning Layer (§9) can operate for real.
- Governance Service, Conformance Service, and Review Service (§12) will eventually be formally registered, either as new Shared Platform Services or as Application-specific capabilities — undecided here.

## 19. Dependencies

| Dependency | Relationship |
| --- | --- |
| `PRD-HAP-001` | Sole content source (§1). |
| `HB-001`, `STD-000`–`STD-009` | Governing Standards. |
| `ADR-100`, `CAP-100`, `RUN-100`, `SYS-100`, `PRA-100` | The EIOS platform architecture this Application's own architecture is hosted inside (§7, §9). |
| `ADR-001`, `CAP-001`, `RUN-001`, `SYS-001`, `PRA-001`, `IMP-001` | Existing Requirements Intelligence lineage — cited as real precedent and constraint throughout, never redefined (§1.2). |

## 20. Risks

| Risk | Description |
| --- | --- |
| **Scope-expansion governance risk** | AD-1's own unresolved two-path question (§15) is the single largest risk in this document — proceeding to build against this architecture before it is resolved risks building against a capability boundary (`CAP-001`) that does not yet authorize what is being built. |
| **Engineering Graph non-existence risk** | Every Reference Architecture in §11 depends on a Level 3 realization that does not exist — the entire Reasoning Layer (§9) is inoperable until it does. |
| **Agent Architecture premature-adoption risk** | §13's own seven agents remain Conceptual/Reference only — building them before ADR-100's own platform-wide Agent Orchestration reservation is lifted risks a private, non-reusable agent framework this platform's own Extensibility principle (§5 Principle 10) explicitly discourages. |
| **Shared-service immaturity risk** | AD-9's own reuse discipline depends on services (§12) that are mostly Reserved, not Realized, platform-wide. |
| **Silent scope creep risk** | Without AD-1's own resolution recorded explicitly per implementation, a future engineer could build past `CAP-001`'s own Boundary without realizing a governance act was ever required. |

## 21. Architectural Governance

Restates STD-006 in full, applied to this document:

| Concern | Rule |
| --- | --- |
| **Approving Authority for this ADR** | Architecture Review Board (STD-006 §6's own ADR-family row). |
| **The single most significant governance action this document identifies** | Resolving AD-1's own two-path scope question — either an Architectural-category revision to `CAP-001` (STD-006 §7, Architecture Review Board approval) or registration of a new capability alongside it. This document names the decision; it does not make it. |
| **Agent Architecture governance** | Adopting §13's own agents as a real implementation is itself an Architectural-category change relative to ADR-100's own platform-wide Agent Orchestration reservation — requiring the same Architecture Review Board approval, never assumed by this document's own Reference Architecture status. |

## 22. Engineering Conformance

Restates STD-008 in full: this document's own conformance is assessed against its own declared nature — a Hosted Application ADR, Derived From `PRD-HAP-001` alone, consistent with HB-001 §13.2's own ADR-family dependency rule. Every architectural claim in this document that is Level 1–2 only is stated as such (§6); a future Conformance Assessment (STD-008 §6) of this document itself would find every Level 3 claim traces to a specific, real, capability-scoped precedent (§12) and no Level 3 claim is overstated.

## 23. Known Limitations

- **The identifier `ADR-HAP-001` does not conform to HB-001 §20.5** — reconciled, not resolved, in §1.1.
- **This document does not, and cannot, alter `ADR-001` or `CAP-001`** — §1.2.
- **AD-1's own scope-expansion question is the largest open item in this entire document** — named repeatedly (§1.2, §2, §15, §20, §21) rather than once and forgotten.
- **The Engineering Graph (§11) has no Current Realization** — Level 1–2 only.
- **The Agent Architecture (§13) has no Current Realization**, and adopting it for real requires its own governance act relative to ADR-100's own platform-wide reservation (§21).
- **Three of eleven Shared Platform Capabilities (§12) — Governance Service, Conformance Service, Review Service — do not appear in `PRA-001` §8's own existing catalog** — named as a candidate future addition, never added by this document itself.
- **No real Feature File has ever been generated under this architecture** — every Level 1–2 claim in this document remains, honestly, unbuilt.

## 24. Future Evolution

Restates PRD-HAP-001 §31: Architecture Intelligence, Test Intelligence, Implementation Intelligence, Review Intelligence, and Engineering Analytics each require their own future ADR, built against this document's own reusable pattern (§9–§10, §13) without redesigning it — the explicit goal this document's own Quality Requirements (header) name.

## 25. Conclusion

This ADR architects Requirements Intelligence as an Engineering Reasoning Platform, consistent with EIOS's own platform architecture (ADR-100) and honest about exactly how much of that architecture is Conceptual or Reference maturity versus genuinely realized. It is ready to guide a future `CAP`, `RUN`, `SYS`, `PRA`, and `IMP` — not because every question is resolved, but because every unresolved question is named, attributed to its own governing authority, and never silently assumed settled.

---

*End of ADR-HAP-001, Version 1.0 (Draft).*
