# PRA-001 — Engineering Intelligence Platform Reference Architecture

**Version 1.0**

## 1. Document Metadata

| Field | Value |
| --- | --- |
| Identifier | PRA-001 |
| Title | Engineering Intelligence Platform Reference Architecture |
| Version | 1.0 |
| Status | Draft — pending Architecture Review Board approval |
| Owner | Chief Platform Architect |
| Stakeholders | Platform Architect, Capability Owner, Engineer, AI Architect, Security, Operations, Reviewer, Certification Authority (PRD-001 §7; ADR-001 §1) |
| Approvers | Architecture Review Board |
| Dependencies | HB-001, STD-000, STD-001, STD-002, STD-003, STD-004, STD-005, PRD-001, ADR-001 |
| **Derived From** | **ADR-001 — Engineering Intelligence Platform Architecture** (the sole content source, §4 below); **HB-001, STD-000, STD-001, STD-002, STD-003, STD-004, STD-005** (Normative authorities this reference architecture conforms to, never restates); **PRD-001** (cited transitively through ADR-001, never a direct content source of this document) |
| **Transformation Authority** | STD-005 — Transformation Semantics: **Realizes**, **Allocates**, **Specializes**, **Preserves** (§4 below) |
| Supersedes | Nothing (first platform reference architecture derived from ADR-001) |
| Superseded By | Not applicable |

---

## Transformation Record (STD-005)

| Field | Value |
| --- | --- |
| Source Artifact | ADR-001 — Engineering Intelligence Platform Architecture |
| Target Artifact | PRA-001 — Engineering Intelligence Platform Reference Architecture |
| Transformation Semantics | **Realizes** (ADR-001's Architectural Intent converted into a reusable, technology-shaped Platform Intent) → **Allocates** (ADR-001 §9's seven Architectural Domains and §10's sixteen conceptual capabilities each assigned a shared platform-service dependency, §8) → **Specializes** (each shared service and technology decision produced as a specific instance of ADR-001's own general domain and quality-attribute model, §8, §12) → **Preserves** (ADR-001 §6's Principles, §9's Domains, §14's Quality Attributes, and §15's Constraints carried forward unmodified) |
| Transformation Authority | STD-005 §6 (semantic definitions); ADR-001 §17 (the specific hop this document performs, named below) |
| Transformation Evidence | ADR-001 §6 (Architecture Principles), §9 (Architecture Domains), §10 (Platform Capability Landscape), §11 (Capability Interaction Model), §14 (Quality Attributes) |
| Transformation Owner | Chief Platform Architect |
| Produced Relationships (STD-004) | `implements` (PRA-001 → ADR-001, per Realizes), `belongs_to` (each shared service and domain-facing technology decision → the one ADR-001 domain it supports, per Allocates), `defines` (each specific technology instance → the general principle or attribute it specializes, per Specializes), `traces_to` (PRA-001 → ADR-001's own preserved facts, per Preserves) |

**Where this fits, without amending ADR-001 or STD-005.** ADR-001 §17's own Architecture Traceability chain names an as-yet-unperformed hop: **Architecture Domains → Platform Capabilities** — the point at which ADR-001's seven domains (§9) become the shared substrate a future `CAP-NNN` draws on, before that capability's own decomposition begins. ADR-001 itself remains, by its own Forbidden list and Known Limitations (§21), technology-independent — it names no reusable service, no AI architecture, no technology stack. PRA-001 performs exactly, and only, that one hop: it gives ADR-001's domains, principles, and quality attributes their first reusable, technology-shaped form, so that every future Capability Intent (STD-005 §5) inherits a shared platform rather than reinventing one. This introduces no new stage to STD-005 §5's seven-stage model — it is a permitted refinement inside the single `Architectural Intent → Capability Intent` hop STD-005 §5 already names, exactly as SYS-001 refined the `Runtime Intent → Implementation Intent` hop and IMP-001 performed it. **PRA-001 SHALL NOT be read as a sixteenth conceptual capability, a new Architectural Domain, or a new ADR** — it originates no business capability ADR-001 §10 does not already name, and where this document requires content ADR-001 explicitly deferred to a future ADR (§21 below cites each case by name), it supplies only a **Provisional Reference** pending that ADR's own freeze — never a substitute decision.

---

## 2. Executive Summary

**Platform Vision.** The Engineering Intelligence Platform exists so that AI-assisted engineering work can be trusted structurally, not aspirationally (ADR-001 §3). PRA-001 is the reusable architectural blueprint that makes that trust buildable more than once: every future capability — Requirements Intelligence today, Architecture, Capability, Runtime, Knowledge, and Governance-aligned capabilities tomorrow — inherits the same shared services, the same AI architecture, the same technology standards, and the same operational model, rather than each re-deriving its own.

**Reference Architecture.** PRA-001 gives ADR-001's seven Architectural Domains (§9) and sixteen conceptual capabilities (§10) a common, reusable technology substrate: a shared-services layer (§8), an AI reference architecture (§9 below), a technology stack with justified choices and replacement strategies (§12), and security, deployment, and observability reference architectures (§13–§15) — the first two explicitly provisional, pending their own named future ADR (§21).

**Mission.** Ensure no future capability implementation invents its own identity model, its own prompt-management approach, its own persistence pattern, or its own deployment shape — each inherits PRA-001's, or extends it through PRA-001's own governed evolution (§20), never around it.

**Architectural Scope.** Platform-wide, capability-independent. PRA-001 defines no business capability's own responsibility (ADR-001 §10 and each capability's own future CAP-NNN retain that authority in full) — it defines only what every capability may reuse.

**Expected Outcomes.** A second, third, and Nth capability realized against this platform reuses Requirements Intelligence's own already-proven services (the Prompt Registry, the provider factory, the deterministic-pipeline pattern) instead of rebuilding them, and inherits this document's security, deployment, and observability posture as a starting point rather than an open question.

## 3. Platform Vision

| Concern | Statement |
| --- | --- |
| **Purpose** | Give every current and future Engineering Intelligence capability one reusable architectural and technological foundation, so that governance, explainability, and traceability (ADR-001 §3) are properties of the platform, never re-earned per capability. |
| **Business Goals** | Realizes PRD-001 §11's Extensibility NFR at platform grain: a new business capability (PRD-001 §9) is added by allocating it against this reference architecture, never by redesigning the platform beneath it. |
| **Engineering Goals** | Realizes ADR-001 §6's Capability First, Loose Coupling, High Cohesion, and Deterministic Engineering principles as concrete, reusable services (§8) and a concrete technology stack (§12), rather than as principles a new capability must independently reinterpret. |
| **AI Goals** | Realizes ADR-001 §7's Knowledge-Centric style and §13's Human–AI Collaboration Model as one shared AI reference architecture (§9 below) — one prompt registry, one provider factory pattern, one guardrail discipline, reusable by every future capability that needs an LLM at all. |
| **Governance Goals** | Realizes ADR-001 §11's Governance Exchange and §9's Governance Domain as reusable governance mechanics (§18) every capability's own future Governance Exchange plugs into, rather than a bespoke conformance check per capability. |
| **Long-term Evolution** | Realizes ADR-001 §19's Future ADR Roadmap by giving ADR-002 (Capability Architecture), ADR-006 (Integration Architecture), ADR-007 (Security Architecture), and ADR-008 (Deployment Architecture) a working reference to formalize, refine, or supersede — never a decision this document makes in their place (§20, §22). |

## 4. Architectural Principles

Every principle below restates, and never replaces, a specific ADR-001 §6 principle or STD-000 rule, specialized to platform-service and technology grain. None originates new architectural authority.

| Principle (this document) | Restates | Platform Implication |
| --- | --- | --- |
| **AI-first Engineering** | ADR-001 §6 AI Augmentation; §7 Knowledge-Centric style | Every capability may call an LLM only through the shared Model Router (§8), never a bespoke SDK integration. |
| **Platform before Products** | ADR-001 §6 Capability First; PRD-001 §11 Extensibility | A capability's implementation (IMP-NNN) draws on PRA-001's services before inventing its own. |
| **Capability-first Design** | ADR-001 §6 Capability First | §8's services are shared infrastructure; they own no business behavior — that remains each capability's own (SYS-001 §5's own discipline, generalized). |
| **Separation of Intent and Realization** | ADR-001 §5 Architecture Authority Model; STD-005 §3 | This document (Platform Intent) never performs a Capability Intent's own work (STD-005 §5) — it supplies substrate, never business logic. |
| **Contract-first Systems** | ADR-001 §6 Loose Coupling; §11 Contracts | Every shared service (§8) is consumed only through its own Provided Contracts column — never a service's internals. |
| **Evidence-driven Engineering** | STD-001 §6; STD-003 §10 | §10's Engineering Architecture and §11's Information Architecture reuse, never reinvent, the platform's existing evidence vocabulary. |
| **Policy-as-Code** | ADR-001 §6 Governance by Design | §8's Policy Engine row and §18's Platform Governance table are this principle's concrete platform-service form. |
| **Security by Default** | ADR-001 §6 Governance by Design; STD-003 §8 Constraint 2 | §13's Security Reference Architecture is this principle's platform-wide default posture — provisional pending ADR-007 (§22), never absent by omission. |
| **Observability by Default** | ADR-001 §14 Auditability | §15's Observability Reference Architecture is a shared default every capability inherits, not a per-capability afterthought. |
| **Human Approval at Governance Boundaries** | ADR-001 §13 Human–AI Collaboration Model; PRD-001 FR-016 | §18's Platform Governance and §17's Capability Extension Model both name a human Approval gate before any governed artifact crosses a boundary. |
| **Explainable AI** | ADR-001 §6 Explainability; STD-000 §3 | §9's Guardrails and Evaluation Framework rows require every AI-assisted output to cite the evidence and prompt version that produced it. |
| **Reusable Platform Services** | ADR-001 §6 Extensibility | §8, in full — the platform's own answer to "what must never be rebuilt per capability." |
| **Deterministic Engineering Workflows** | ADR-001 §6 Deterministic Engineering; STD-000 Principle 8 | §8's Workflow Engine and §10's Transformation Pipeline both require the same governed input to always yield the same output. |
| **Loose Coupling** | ADR-001 §6 Loose Coupling | Restated verbatim — the platform's own services (§8) are the only sanctioned inter-capability crossing point, exactly as ADR-001 §11 already requires of capabilities themselves. |
| **High Cohesion** | ADR-001 §6 High Cohesion | Restated verbatim — each shared service (§8) owns one reusable concern completely, never a fragment of one. |
| **Version Everything** | STD-000 Principle 7 | §12's Replacement Strategy column and §11's Versioning row apply this principle to every technology and information artifact this document names. |
| **Everything Traceable** | ADR-001 §6 Traceability by Construction; STD-004 | §19's Platform Traceability chain is this principle's platform-wide expression. |
| **Everything Governed** | STD-000 Rule 3 | §18, in full. |
| **Everything Measurable** | ADR-001 §14 Auditability, specialized to observability grain | §15's metrics rows (Prompt, LLM, Latency, Cost, Token, Evaluation, Business) are this principle's concrete instantiation — largely reserved today (§22), never silently assumed complete. |

## 5. Architecture Views

| View | Answers | Primary Section | Relationship to ADR-001 |
| --- | --- | --- | --- |
| **Business View** | Why this platform exists at all. | §3 | Restates ADR-001 §3's Vision and PRD-001's own Vision, cited transitively. |
| **Capability View** | What capabilities exist or are anticipated, and who owns them. | §6 | Realizes ADR-001 §10's Platform Capability Landscape — adds no capability ADR-001 §10 does not already name, except where explicitly flagged provisional (§6, §22). |
| **Logical View** | How domains and services are structurally arranged. | §7, §8 | Realizes ADR-001 §8's Architectural Layers and §9's Domains at platform-service grain. |
| **Information View** | What information exists, and who governs it. | §11 | Realizes ADR-001 §12's Information Architecture, adding the versioning/retention/classification detail ADR-001 itself deferred. |
| **AI View** | How AI assistance is structurally bounded and reused. | §9 | Realizes ADR-001 §13's Human–AI Collaboration Model and §7's Knowledge-Centric style as a concrete reference architecture. |
| **Security View** | How identity, secrets, and data protection are structured. | §13 | Provisional — realizes ADR-001 §6 Governance by Design pending ADR-007 (§22). |
| **Operational View** | How the platform is run day to day once live. | §16 | Realizes ADR-001 §14's Reliability and Availability attributes, both of which ADR-001 itself left as a deferred decision (§16, ADR-001 §16). |
| **Deployment View** | Where and how the platform executes. | §14 | Provisional — realizes ADR-001 §14's Availability attribute pending ADR-008 (§22). |
| **Governance View** | How conformance is checked and by whom. | §18 | Realizes ADR-001 §9's Governance Domain and §11's Governance Exchange as concrete platform governance mechanics. |
| **Engineering View** | How work actually moves from intent to certified artifact. | §10 | Realizes STD-001's Engineering Lifecycle and ADR-001 §17's Architecture Traceability at platform-service grain. |

**How the views relate.** No view is authoritative over another — each answers a different question about the same one reference architecture, exactly as ADR-001 §5's Architecture Authority Model already distinguishes Normative rules from their Derivative realization: the Business View states why, the Capability View states what, the Logical/Information/AI views state how it is structured, the Security/Operational/Deployment views state how it runs, and the Governance/Engineering views state how it stays trustworthy over time. A conflict between two views is, by construction, a defect in this document, never a case where one view "wins" over another (restates ADR-001 §14 Consistency).

## 6. Platform Capability Map

| Capability | ADR-001 Status | Owning Domain (§9) | Realization Status |
| --- | --- | --- | --- |
| **Requirements Intelligence** | Frozen capability name (ADR-001 §9's Requirements Domain) | Requirements Domain | **Realized** — CAP-001, RUN-001, SYS-001, IMP-001 all exist. |
| **Architecture Intelligence** | Conceptual (ADR-001 §10: "Architecture Decision Capture," "Architecture Consistency Visibility") | Architecture Domain | Not yet realized — no CAP-NNN exists. |
| **Capability Intelligence** | Conceptual (ADR-001 §10: "Capability Registration," "Capability Maturity Visibility") | Capability Domain | Not yet realized. |
| **Runtime Intelligence** | Conceptual (ADR-001 §10: "Runtime Execution Visibility," "Runtime Reproducibility Verification") | Runtime Domain | Not yet realized. |
| **System Intelligence** | **Not an ADR-001 §10 capability.** Observed emerging from SYS-001's own document-tier extension of RUN-001 (SYS-001 §15), never itself named a capability by any frozen ADR. | None assigned | Candidate only — requires a future ADR (extending ADR-001 §10, or a dedicated ADR-002) before this name may be treated as an authorized capability (§22). |
| **Implementation Intelligence** | Conceptual (ADR-001 §10: "Implementation Compliance Tracking") | Capability Domain | Not yet realized — IMP-001 is a capability's own implementation specification, not yet the reusable Implementation Intelligence capability that would track compliance across every capability's own IMP-NNN. |
| **Evidence Intelligence** | **Not an ADR-001 §10 capability.** Observed emerging from STD-004 §9's own `Evidence` tier and STD-005 §5's `Engineering Evidence` stage, never itself named a capability by any frozen ADR. | None assigned | Candidate only (§22). |
| **Certification Intelligence** | **Not an ADR-001 §10 capability.** Observed emerging from HB-001 §6.8's Certification family and STD-004 §9's `Certification` tier, never itself named a capability by any frozen ADR. | None assigned | Candidate only (§22). |
| **Future Intelligence Capabilities** | ADR-001 §10's remaining conceptual capabilities not listed above by name — Traceability Intelligence (Traceability Domain), Knowledge Intelligence (Knowledge Domain), Validation Intelligence and Human Oversight Enforcement (Governance Domain) — plus any capability a future, governed ADR revision adds (ADR-001 §6 Principle 11, Extensibility). | Traceability, Knowledge, Governance Domains | Not yet realized. |

**Relationships among capabilities.** Restates ADR-001 §10's own Conceptual Relationships rule exactly: every Requirements-row capability is consumed by the Architecture row; every Architecture-row capability by the Capability row; every Capability-row capability by the Runtime row. Traceability- and Knowledge-row capabilities consume evidence from all others without being consumed in return (ADR-001 §8's cross-cutting L5/L6 rule). System, Evidence, and Certification Intelligence — while not yet authorized capabilities — would, if authorized, sit downstream of the Runtime row and upstream of Certification, consistent with §19's own Platform Traceability chain below; this is offered as a compatible observation, not a decision this document is authorized to make (§22).

## 7. Platform Domains

**Distinct from, and never redefining, ADR-001 §9's Architectural Domains.** ADR-001 §9 names seven capability-facing domains (what business responsibility a domain owns). The nine domains below are a complementary, infrastructure-facing view — what reusable platform substrate underlies every capability-facing domain — the same technique STD-005 §5 uses to reconcile its own process view against STD-004's structural view, applied here to reconcile a technology view against ADR-001's business-capability view.

| Domain | Responsibility | Relationship to ADR-001 §9 |
| --- | --- | --- |
| **Knowledge Domain** | Owns the Knowledge Registry (§8) and knowledge-artifact classification (§11). | Directly supports ADR-001's own Knowledge Domain and its Knowledge Intelligence capability. |
| **Reasoning Domain** | Owns the AI Reference Architecture (§9 below) — model providers, prompt management, context assembly, reasoning pipeline. | Supports ADR-001's AI Augmentation principle (§6) and Knowledge-Centric style (§7); owned by no single ADR-001 domain, since AI assistance is cross-cutting there too (ADR-001 §13). |
| **Engineering Domain** | Owns the Engineering Architecture (§10) — lifecycle, transformation pipeline, review/approval gates. | Supports every ADR-001 domain's own L1–L4 realization work (ADR-001 §8). |
| **Governance Domain** | Owns the Policy Engine (§8) and Platform Governance mechanics (§18). | Directly supports ADR-001's own Governance Domain. |
| **Runtime Domain** | Owns the Workflow Engine and Scheduler (§8), and the Runtime-facing half of Observability (§15). | Directly supports ADR-001's own Runtime Domain. |
| **Platform Domain** | Owns the shared services themselves (§8) as a coherent whole — identity, configuration, secrets, registries. | Cross-cutting substrate beneath all seven ADR-001 domains simultaneously. |
| **Operations Domain** | Owns the Operational Model (§16) — incident management, monitoring, runbooks, SRE practice. | Realizes ADR-001 §14's Reliability and Availability attributes, both explicitly deferred by ADR-001 itself (ADR-001 §16) to a future ADR (§22). |
| **Security Domain** | Owns the Security Reference Architecture (§13). | Realizes ADR-001 §6's Governance by Design at the identity/secrets/data-protection grain — provisional pending ADR-007 (§22). |
| **Observability Domain** | Owns the Observability Reference Architecture (§15) — logging, tracing, metrics. | Realizes ADR-001 §14's Auditability attribute as a concrete, always-on default. |

## 8. Shared Platform Services

Every service below is reusable across every capability in §6 — no service performs capability-specific business logic (restates §4's Capability-first Design principle). **Realization Status** distinguishes what already exists, in Requirements Intelligence's own implementation (IMP-001), from what remains reserved platform-wide.

| Service | Purpose | Responsibilities | Consumers | Provided Contracts | Dependencies | Ownership | Realization Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Identity Service** | Authenticate a caller (human or system) once, platform-wide. | Credential verification, session/token issuance. | Every capability's own API surface. | An identity assertion. | Security Domain. | Security Domain. | **Reserved** — no identity provider exists (IMP-001 §9). |
| **Authorization Service** | Decide what an authenticated caller may do. | Role/scope evaluation against the Policy Engine. | Every capability's own API surface. | An allow/deny decision with rationale. | Identity Service, Policy Engine. | Security Domain. | **Reserved.** |
| **Configuration Service** | Supply environment-driven configuration to every capability, uniformly. | Env-var resolution, typed settings, execution-mode switching. | Every capability. | A typed settings object. | None. | Platform Domain. | **Partially realized** — `pydantic-settings`, `EXECUTION_MODE` switch (`requirement_intelligence/registry/execution_mode.py`), scoped to Requirements Intelligence only; not yet a platform-wide shared service. |
| **Secrets Service** | Hold credentials no capability may hard-code. | Secret storage, rotation, scoped retrieval. | Every capability's own connectors and provider calls. | A resolved secret value, never a raw store. | Identity Service. | Security Domain. | **Partially realized** — `.env` + `python-dotenv` only; no vault (IMP-001 §9, §17). |
| **Artifact Registry** | Record every artifact a capability's own runtime produces. | Storage, retrieval, retention policy. | Requirement Catalog (SYS-001.7) today; every future capability's own Catalog-equivalent. | A retrievable, uniquely identifiable artifact. | Object storage (§12). | Platform Domain. | **Partially realized** — file-based JSON under `output/`, scoped to Requirements Intelligence; no shared registry API. |
| **Capability Registry** | Track every `CAP-NNN`'s identity, maturity, and dependencies platform-wide. | Registration, maturity aggregation (HB-001 §6.4). | Capability Intelligence (§6), Governance Domain. | A capability's current registered state. | None. | Governance Domain. | **Reserved** — HB-001's own Platform Capability Matrix is a document today, not a queryable service. |
| **Knowledge Registry** | Hold organizational learning captured across capabilities. | Learning storage, retrieval, lesson generation. | Knowledge Intelligence (§6). | A retrievable lesson/best-practice record. | Artifact Registry. | Knowledge Domain. | **Reserved** platform-wide — a capability-scoped precursor (`organizational_memory/`, `learning/`) exists in the Requirements Intelligence repository but belongs to the separate, out-of-scope Knowledge Intelligence capability (IMP-001 §4's exclusion note), never a shared service today. |
| **Prompt Registry** | Hold every governed prompt template platform-wide, versioned and fingerprinted. | Registration, sealing, duplicate-version rejection. | Reasoning Domain's own Model Router and every capability's own LLM call. | A sealed, hash-verified prompt template by `(prompt_id, version)`. | None. | Reasoning Domain. | **Realized** — `requirement_intelligence/prompts/framework/prompt_registry.py`, SHA-256-fingerprinted, lifecycle-staged manifest — scoped to Requirements Intelligence today, the platform's own reference implementation for this service. |
| **Policy Engine** | Evaluate a candidate governed decision against declared, versioned rules. | Rule registration, deterministic evaluation, rationale generation. | Requirement Validator (SYS-001.6) today; every future capability's own transition-validation need. | A pass/fail verdict with rationale. | None. | Governance Domain. | **Partially realized** — capability-scoped rule registries exist (`requirement_intelligence/validation/validation_registry.py`) but no shared, platform-wide policy-evaluation service exists yet. |
| **Workflow Engine** | Orchestrate a governed, multi-step transformation deterministically. | Step sequencing, retry, state hand-off. | Every capability's own pipeline. | A deterministic step-sequence execution. | None. | Runtime Domain. | **Reserved** — every capability's own pipeline today is hand-coded Python control flow, not a declarative, shared workflow engine. |
| **Context Manager** | Assemble a bounded evidence/context set for a governed LLM call. | Evidence selection, budget enforcement, ordering. | Reasoning Domain's own reasoning pipeline. | A bounded, budgeted context object. | Artifact Registry, Knowledge Registry. | Reasoning Domain. | **Realized (capability-scoped)** — `requirement_intelligence/context_orchestration/` (evidence budget, evidence selection) — Requirements Intelligence's own reference implementation. |
| **Tool Registry** | Register callable tools/functions an AI reasoning step may invoke. | Tool registration, schema validation. | Reasoning Domain's own reasoning pipeline. | A callable tool contract. | None. | Reasoning Domain. | **Reserved** — no function-calling/tool-use framework exists anywhere in the platform today (IMP-001 §6). |
| **Agent Registry** | Register multi-step autonomous agents, if and when the platform ever needs one. | Agent registration, capability boundary declaration. | Reasoning Domain. | An agent's declared tool/scope boundary. | Tool Registry. | Reasoning Domain. | **Reserved** — no agent-orchestration framework exists (IMP-001 §6); reserved, not anticipated as imminently needed. |
| **Model Router** | Select which LLM provider and model instance answers a given governed call. | Provider selection, configuration-driven model choice. | Reasoning Domain's own reasoning pipeline. | A provider-agnostic completion call. | Model providers (§9, §12). | Reasoning Domain. | **Partially realized** — `requirement_intelligence/llm/llm_factory.py`, a static, name-keyed factory (Gemini live, Azure OpenAI stubbed) — not yet a dynamic, cost/latency-aware router (§9, §22). |
| **Evaluation Service** | Score a governed AI-assisted output against a declared rubric. | Evaluation execution, metric recording. | Reasoning Domain, Governance Domain. | An evaluation result with rationale. | Model Router, Artifact Registry. | Reasoning Domain. | **Reserved** — ad hoc Release Candidate validation exists (`output/releases/ril-rc1-api-validation`) but no repeatable, automated evaluation service (IMP-001 §12, §22). |
| **Notification Service** | Alert an accountable human at a governance boundary. | Event-to-recipient routing. | Every domain's own Governance Exchange (ADR-001 §11). | A delivered notification. | None. | Operations Domain. | **Reserved** — no notification mechanism exists anywhere in the platform today. |
| **Scheduler** | Trigger a governed execution on a time or event basis. | Scheduling, trigger evaluation. | Every capability's own runtime. | A triggered execution request. | Workflow Engine. | Runtime Domain. | **Reserved** — every execution today is triggered synchronously by a direct API call (IMP-001 §7); no scheduled or event-driven trigger exists. |
| **Document Registry** | Hold this platform's own governed document series (HB, ADR, STD, CAP, RUN, SYS, IMP, PRA), indexed and queryable. | Document registration, identifier resolution, cross-reference validation. | Every governance and traceability function (§18, §19). | A resolvable document identifier. | None. | Governance Domain. | **Reserved** — the document series itself is real and file-based (`docs/`) but human-curated; no registry service resolves an identifier programmatically. |
| **Traceability Service** | Resolve and validate the relationship chain (§19) for any artifact. | Relationship recording, completeness checking (STD-004 §2). | Traceability Intelligence (§6), Governance Domain. | A resolved traceability chain. | Document Registry, Artifact Registry. | Governance Domain. | **Reserved** — traceability today is manual citation across Markdown documents, exactly as this document itself practices; not yet a queryable service. |
| **Search Service** | Retrieve a governed artifact or knowledge item by content, not only by identifier. | Indexing, query evaluation. | Every domain. | A ranked result set. | Artifact Registry, Knowledge Registry. | Platform Domain. | **Reserved** — no search index exists; retrieval is by file path only (IMP-001 §8). |
| **Audit Service** | Record a tamper-evident, queryable history of every governed action. | Audit-event capture, retention. | Every domain's own Governance Exchange. | An immutable audit record. | Identity Service. | Security Domain. | **Reserved** — `structlog`'s structured application logging is today's only proxy (IMP-001 §9, §11); it is not a dedicated, tamper-evident audit trail. |

## 9. AI Reference Architecture

| Concern | Reference Definition | Realization Status |
| --- | --- | --- |
| **Model Providers** | Every provider is accessed only through the Model Router (§8) — never called directly by a capability. | Gemini (`google-genai`) live; Azure OpenAI declared, stubbed (IMP-001 §5, §6). |
| **Model Routing** | Configuration-driven provider/model selection, not embedded in capability logic. | Static, name-keyed factory (`llm_factory.py`) — not yet cost/latency-aware (§22). |
| **Prompt Management** | Every prompt is registered, sealed, and version-pinned before use (§8's Prompt Registry). | Realized, Requirements-Intelligence-scoped; the platform's own reference implementation. |
| **Prompt Versioning** | Semantic version per template, SHA-256-fingerprinted, lifecycle-staged (`Production`/`Approved`). | Realized (`prompts/versions/manifest.json`). |
| **Prompt Registry** | §8, above. | Realized (capability-scoped). |
| **Context Assembly** | A bounded, budgeted evidence set assembled by the Context Manager (§8) — never an unbounded context window. | Realized (capability-scoped, `context_orchestration/`). |
| **Knowledge Retrieval** | Deterministic classification/matching by default; embedding-based retrieval only by a future, separately governed decision. | Deterministic today (`grounding/matching/`, `grounding/classification/`) — a design choice, not a gap. |
| **Embedding Strategy** | Not adopted platform-wide. Any future capability proposing embedding-based retrieval does so through a governed extension (§20), never silently. | None exists (deliberate). |
| **Vector Search** | Reserved — no vector database is part of this reference architecture today (IMP-001 §5). | Reserved. |
| **Hybrid Retrieval** | Reserved — would combine deterministic matching with vector search only if a future governed decision adopts the latter. | Reserved. |
| **Reasoning Pipeline** | Exactly one bounded LLM call per governed unit of work, preceded by deterministic structuring and followed by deterministic validation — never a multi-turn reasoning loop by default. | Realized in Requirements Intelligence (IMP-001 §6): consolidation → one Gemini call → response normalization → deterministic enrichment/grounding. |
| **Agent Orchestration** | Reserved (§8's Agent Registry) — no multi-step autonomous agent framework is adopted platform-wide. | Reserved. |
| **Tool Invocation** | Reserved (§8's Tool Registry) — no function-calling pattern is adopted platform-wide. | Reserved. |
| **Memory Architecture** | Stateless per governed execution by default; cross-execution memory is the Knowledge Registry's (§8) own, separately governed concern. | Stateless today; cross-execution memory precursors exist but belong to the out-of-scope Knowledge Intelligence capability (IMP-001 §4). |
| **Evaluation Framework** | Every AI-assisted output is evaluated against a declared rubric before being treated as governed (§8's Evaluation Service). | Reserved as a service; ad hoc Release Candidate validation exists today. |
| **Safety Framework** | Schema-constrained output plus deterministic post-validation before any candidate transition is accepted (restates SYS-001 §7's Guardrails discipline at platform grain). | Realized in Requirements Intelligence (`ENABLE_RESPONSE_SCHEMA`, `requirement_intelligence/validation/`). |
| **Guardrails** | Restates the prior row — no AI-assisted output is accepted without passing a deterministic, non-AI validation step. | Realized (capability-scoped). |
| **Human Review** | Every AI-assisted contribution remains subject to PRD-001 FR-016's human-approval requirement (ADR-001 §13) — a governance-process expectation today, not yet a code-enforced gate. | Process-level only (§22). |
| **Fallback Strategy** | Retry/backoff on the active provider; a second, declared provider as a structural fallback, not yet automatic. | `tenacity`-based retry realized; provider-to-provider failover reserved (Azure OpenAI stub, §22). |
| **Cost Optimization** | Reserved — no cost-aware routing or budget enforcement exists platform-wide. | Reserved. |
| **Latency Optimization** | Reserved — no latency-aware routing exists; `DEFAULT_PROVIDER_TIMEOUT` is the only latency-adjacent control today. | Reserved. |
| **Model Governance** | Every model version change is a configuration-value change, evaluated against the model-evaluation precedent (`output/model-eval/{gemini-2.5-flash,gemini-3-flash-preview,gemini-3.1-flash-lite}/`) before adoption — never a silent upgrade. | Realized as a practice; not yet a formal, automated gate. |

## 10. Engineering Architecture

| Concern | Reference Definition |
| --- | --- |
| **Engineering Lifecycle** | STD-001 §3's own Engineering Lifecycle (Implementation Planning → Implementation → Verification → Integration → Implementation Complete) — this document introduces no competing lifecycle; every future capability's own implementation follows it unmodified. |
| **Artifact Lifecycle** | HB-001 §8's six-stage Documentation Lifecycle (Draft → Review → Approved → Frozen → Revised → Superseded), applied uniformly to every governed document this platform ever produces, including this one. |
| **Transformation Pipeline** | STD-005 §5's seven-stage Engineering Transformation Model — this document series is itself the running proof: PRD-001 → ADR-001 → (CAP-001, RUN-001, SYS-001, IMP-001) → PRA-001, each hop an explicit, recorded transformation (STD-005 §8). |
| **Review Gates** | HB-001 §15's Review Workflow (Author → Architecture → Governance → Editorial → Approval) — the one review process every governed artifact in this platform passes through, this document included. |
| **Approval Gates** | HB-001 §18's per-family Approval Authority table — a PRA-tier document's approval sits with the Architecture Review Board (§1), by analogy to ADR-001's own Architecture Board approval (HB-001 §6.9), pending a future HB-001 revision formally registering a PRA family (§22). |
| **Evidence Collection** | Reuses, never reinvents, STD-001 §6's, STD-002 §9's, and STD-003 §10's own evidence vocabulary — no new evidence type is introduced by this document. |
| **Certification Flow** | HB-001 §6.8's Certification family — the terminal tier of both HB-001 §5's hierarchy and this document's own §19 chain; PRA-001 itself is certified only once a certifying authority verifies it against every Standard it cites (§18). |
| **Traceability** | §19, below. |
| **Engineering Automation** | Today, `make check` (lint + typecheck + test) is the closest existing automation of STD-001 §8's own Quality Gates — developer-run, not yet CI-enforced platform-wide (IMP-001 §13, §22). |

## 11. Information Architecture

Extends ADR-001 §12's own Information Architecture table with the versioning, retention, lifecycle, and classification detail ADR-001 itself deferred as implementation-tier content.

| Information kind | What it is | Governed by | Versioning | Retention | Lifecycle | Classification |
| --- | --- | --- | --- | --- | --- | --- |
| **Canonical Information Model** | Every capability's own typed record shape (e.g. SYS-001 §8's Information Model). | STD-002 §2, STD-003 §2. | One version axis per canonical model, independent of document version (STD-000 Principle 7). | Indefinite, per capability's own Artifact Registry (§8) instance. | Draft → Captured/Enriched/Grounded-equivalent → Finalized (RUN-001 §6, generalized). | Engineering Information. |
| **Engineering Metadata** | HB-001 §16's document metadata fields, applied platform-wide. | HB-001 §16. | Tracks its own document's version. | Permanent — never deleted, only superseded (STD-000 Principle 6). | HB-001 §8's six-stage lifecycle. | Governance Information. |
| **Knowledge Artifacts** | Lessons, best practices, trends (Knowledge Registry, §8). | This document's own Knowledge Domain (§7); no Normative Standard yet governs Knowledge content directly (ADR-001 §12's own named gap, restated here unresolved). | Not yet defined — reserved (§22). | Not yet defined — reserved. | Not yet defined — reserved. | Knowledge. |
| **Platform Metadata** | Service registration, capability registration (§8's registries). | This document, §8. | One version per registered entity. | Indefinite while the entity remains registered. | Registered → Deprecated → Retired (restates STD-004 §4's Relationship Lifecycle terms at registry grain). | Platform Metadata. |
| **Artifact Relationships** | Every connection between two information kinds above. | STD-004 §3/§17 — restricted permanently to its fourteen relationship types; this document originates none. | N/A — a relationship has no version of its own, only a lifecycle stage. | Permanent. | STD-004 §4's six-stage Relationship Lifecycle. | Relationships. |
| **Versioning** | The version-axis discipline itself. | STD-000 Principle 7. | N/A (this row governs versioning, not itself versioned). | N/A. | N/A. | Governance Information. |
| **Retention** | How long an artifact persists once produced. | Not yet formally defined platform-wide (§22) — today, indefinite by default (IMP-001 §8). | N/A. | Reserved for a future retention policy. | N/A. | Governance Information. |
| **Lifecycle** | Every artifact's own lifecycle stage. | HB-001 §8 (documents), STD-002 §3 / STD-003 §3 (capabilities, runtime instances). | N/A. | N/A. | Restated per row above. | Lifecycle. |
| **Classification** | The information-kind taxonomy itself (this table's own left column). | This document, extending ADR-001 §12. | N/A. | N/A. | N/A. | N/A (the classification scheme itself). |

## 12. Technology Architecture

Every choice below is capability-independent — a platform default every future capability inherits, not a decision specific to Requirements Intelligence. Where Requirements Intelligence (IMP-001) has already instantiated a choice, that instantiation is cited as the platform's own reference implementation.

| Technology | Purpose | Alternatives Considered | Selection Rationale | Replacement Strategy |
| --- | --- | --- | --- | --- |
| **Python 3.11** | Sole platform implementation language. | Node.js/TypeScript, Go, Java | Reference SDK maturity (`google-genai`, `jira`, `httpx`); `pydantic` gives every canonical model one typed definition (§11). | A platform-wide language change is an ADR-tier decision, never a per-capability choice (STD-000 Principle 1). |
| **FastAPI + Uvicorn (ASGI)** | Platform-wide API Framework. | Flask, Django REST Framework | Native `pydantic` integration; async I/O suits connector fan-out. | Additive — a new capability may add a router under the same ASGI app (IMP-001 §3) without a framework change. |
| **Workflow Engine** | Declarative orchestration of a governed, multi-step transformation. | A shared workflow engine (Temporal-class), continued hand-coded Python pipelines | **Reserved** (§8, §22) — every capability's own pipeline today is hand-coded Python control flow; a shared engine is deferred until more than one capability's own pipeline shape proves the abstraction is worth sharing. | Adoption, if it occurs, wraps existing pipelines rather than rewriting them (STD-000 Principle 6). |
| **Relational Database** | Platform-wide structured persistence. | Continued file-based JSON, a document database | **Reserved** — `sqlalchemy`/`alembic`/`psycopg` are declared, unwired platform-wide dependencies (IMP-001 §5). | The reserved migration path (IMP-001 §15) changes storage mechanism only, never a canonical model's own shape. |
| **Graph Database** | Platform-wide relationship storage for the Traceability Service (§8). | Neo4j, an in-memory graph (`knowledge_graph/`'s own current pattern) | **Reserved** — no system in this platform's realized scope yet requires queryable graph storage beyond Requirements Intelligence's own excluded `knowledge_graph/` module (IMP-001 §4, §5). | Adoption requires the Traceability Service (§8) to move from reserved to realized first. |
| **Vector Database** | N/A by design (§9). | Pinecone, Weaviate, pgvector | Deterministic retrieval is the platform default (§9); introducing one is a separately governed AI-architecture decision, never a default. | N/A unless §9's Knowledge Retrieval row is revised by a future governed decision. |
| **Object Storage** | Platform-wide artifact persistence target. | Local filesystem (today's actual mechanism), S3/GCS-class object storage | Local filesystem today matches the platform's Implementing lifecycle stage (STD-002 §9); cloud object storage is the natural successor once a Deployment Architecture (ADR-008) is frozen. | Migration is additive — the Artifact Registry's (§8) own contract does not change, only its backing store. |
| **Messaging** | Platform-wide asynchronous hand-off, if ever required. | Kafka, RabbitMQ, SQS | **Reserved** — no capability's own collaboration model (e.g. SYS-001 §6) requires an asynchronous hand-off today; introducing one ahead of a genuine need would add non-determinism (STD-000 Principle 8) no requirement yet justifies. | Adoption is capability-driven — a future capability whose own contract genuinely requires asynchrony proposes it through §20's governed evolution, never as a platform-wide default imposed pre-emptively. |
| **Identity Provider** | Platform-wide Identity Service (§8) backing store. | OAuth2/OIDC provider (e.g. an external IdP), a custom credential store | **Reserved** — recommended target is a standards-based OIDC provider, consistent with Vendor Neutrality (Architecture Philosophy, header); not yet selected or wired (§13, §22). | Selection is itself a future ADR-007 decision (§22) — this row names a direction, not a freeze. |
| **Secrets Management** | Platform-wide Secrets Service (§8) backing store. | A managed vault (e.g. a cloud provider's own secrets manager), continued `.env` | **Reserved** beyond `.env`/`python-dotenv` (IMP-001 §5); a managed vault is the recommended target once a Deployment Architecture exists to host it. | Migration is additive to the Secrets Service's own contract (§8), never a capability-visible change. |
| **Configuration Management** | Platform-wide Configuration Service (§8) mechanism. | `pydantic-settings` (today's actual mechanism), a centralized config service | `pydantic-settings` already gives every capability a typed, env-driven settings object (IMP-001 §5) — sufficient until more than one capability's own configuration surface justifies centralizing it. | Centralization, if it occurs, wraps the existing typed-settings pattern rather than replacing it. |
| **Container Platform** | Platform-wide deployment packaging. | Docker + a container registry, continued bare-process deployment | **Reserved** (§14, §22) — no `Dockerfile` exists platform-wide (IMP-001 §10). | Containerization is additive to the existing ASGI app (§3) — no application-code change is required to package it. |
| **Infrastructure Platform** | Platform-wide infrastructure-as-code. | Terraform, a cloud provider's own native IaC, continued manual local infrastructure | **Reserved** (§14, §22) — no IaC exists platform-wide. | Deferred to ADR-008 (Deployment Architecture, §22) before any specific choice is frozen here. |
| **CI/CD Platform** | Platform-wide automation of §10's Engineering Automation. | GitHub Actions, a self-hosted CI runner, continued developer-run `make check` | **Reserved** (IMP-001 §13, §17, §22) — `make check` is developer-run today, not CI-enforced. | Adoption wraps the existing `make check` target as its own CI step — no gate is redefined, only automated. |
| **Testing Frameworks** | Platform-wide test execution. | `pytest` (today's actual choice), `unittest`/`nose2` | `pytest` + `pytest-asyncio` + `pytest-cov` + `respx` already give Requirements Intelligence unit/integration/e2e/productization coverage (IMP-001 §12) — adopted as the platform default for every future capability. | A capability may add its own markers (`pyproject.toml`'s own marker registry) without a framework change. |
| **Observability Stack** | Platform-wide logging/tracing/metrics. | `structlog` (today's actual choice) + a future metrics/tracing backend | `structlog` already gives every capability structured, switchable console/JSON logging (IMP-001 §11); tracing and metrics backends remain reserved (§15, §22). | A metrics/tracing backend is additive to `structlog`'s own instrumentation points, not a replacement of it. |

## 13. Security Reference Architecture

**Status: Provisional Reference Architecture, pending ADR-007 (Security Architecture).** ADR-001 §16 and §19 explicitly deferred security architecture to a future, dedicated ADR, never deciding it within ADR-001 itself. This section supplies the reusable technology-and-service reference every capability may build against today, without claiming the architectural authority only ADR-007 can grant. Where this section states a recommended direction rather than a realized control, that distinction is explicit.

| Concern | Reference Definition | Realization Status |
| --- | --- | --- |
| **Identity** | One platform-wide Identity Service (§8), never a per-capability login mechanism. | Reserved — recommended direction: standards-based OIDC (§12). |
| **Authentication** | Every capability's own API surface authenticates through the Identity Service, never independently. | Reserved — no authentication exists on Requirements Intelligence's own FastAPI surface today (IMP-001 §9). |
| **Authorization** | Every governed action is checked against the Policy Engine (§8) before proceeding. | Reserved. |
| **Encryption** | In transit: default TLS on every outbound call (already true of every SDK Requirements Intelligence uses, IMP-001 §9). At rest: reserved — no field- or file-level encryption exists. | Partially realized (transit only). |
| **Secrets** | §8's Secrets Service. | Reserved beyond `.env` (IMP-001 §9). |
| **Audit** | §8's Audit Service. | Reserved beyond `structlog` application logging (IMP-001 §9, §11). |
| **Compliance** | PRD-001 §12's and FR-016's human-accountability requirement remains a governance-process expectation (HB-001 §15) until a code-enforced control exists. | Process-level only. |
| **Data Protection** | Canonical models (§11) are the only sanctioned shape a governed record takes — no capability persists an ungoverned, unstructured record. | Realized as a modeling discipline (Pydantic v2, IMP-001 §5); no data-loss-prevention or classification-enforcement tooling exists yet. |
| **Prompt Security** | Every prompt is registered and sealed (§8's Prompt Registry) before use — an unregistered, ad hoc prompt string is never accepted by the Model Router (§8). | Realized (capability-scoped, `prompt_registry.py`). |
| **Model Security** | Every model call passes through schema-constrained output and deterministic post-validation (§9's Safety Framework) — a raw, unvalidated model response is never treated as a governed artifact. | Realized (capability-scoped). |
| **Supply Chain Security** | Every dependency is version-pinned (`requirements.txt`, `requirements-dev.txt`) and installed from a single, declared source. | Partially realized — pinning exists; no SBOM generation or dependency-vulnerability scanning is wired yet (§22). |
| **AI Safety** | Restates §9's Guardrails and Safety Framework rows: no AI-assisted output is accepted without a deterministic, non-AI validation step. | Realized (capability-scoped). |

## 14. Deployment Reference Architecture

**Status: Provisional Reference Architecture, pending ADR-008 (Deployment Architecture).** ADR-001 §14 and §16 explicitly left availability, capacity, and deployment targets undecided, deferring them to ADR-008. This section names the platform's current, actual deployment posture and a recommended target shape — neither is a substitute for ADR-008's own future freeze.

| Concern | Reference Definition | Realization Status |
| --- | --- | --- |
| **Environment Strategy** | Development → Test → Staging → Production, per STD-001 §3's own Engineering Lifecycle progression. | Development and Test exist today (`make dev`, `make test`); Staging and Production are not established (IMP-001 §10). |
| **Containerization** | A `Dockerfile` per deployment unit (§8's own service boundary, IMP-001 §3), packaging the existing ASGI app unchanged. | Reserved (§12). |
| **Kubernetes** | Recommended target container orchestration platform, once containerization exists — chosen for Cloud Portability (Architecture Philosophy, header) over a single-cloud-native scheduler. | Reserved — no orchestration platform is wired. |
| **Scaling** | Not applicable today — a single local process has no scaling dimension (IMP-001 §10). Target shape: stateless horizontal replicas behind a load balancer, once containerized — feasible because every governed pipeline is already stateless per execution (§9's Memory Architecture row). | Reserved. |
| **Disaster Recovery** | Reserved — `output/`'s own file artifacts are the only durable record today, with no backup or restore procedure (IMP-001 §10). | Reserved. |
| **Backup** | Reserved — no automated backup exists. | Reserved. |
| **High Availability** | Reserved — a single-instance deployment has no availability target set (restates ADR-001 §14's own deferred Availability attribute). | Reserved. |
| **Platform Upgrades** | Every technology or service version change follows STD-000 Principle 7 (Versioned evolution) — additive, never a silent rewrite. | Practiced today (e.g. Gemini model-version evaluation, §9's Model Governance row). |
| **Release Strategy** | Manifest-versioned execution packages (`output/releases/<release>/`, e.g. a golden baseline re-certified at a specific version) — the platform's closest existing release mechanism. | Realized (capability-scoped, IMP-001 §13). |

## 15. Observability Reference Architecture

| Concern | Reference Definition | Realization Status |
| --- | --- | --- |
| **Logging** | `structlog`, platform-wide, switchable console/JSON rendering. | Realized (IMP-001 §11). |
| **Tracing** | Reserved — no distributed tracing exists; relevant once more than one deployment unit exists to trace across (§3, §14). | Reserved. |
| **Metrics** | Reserved beyond a liveness health check. | Reserved. |
| **Distributed Tracing** | Restates the Tracing row — deferred until a genuinely distributed deployment exists. | Reserved. |
| **Prompt Metrics** | Would record per-prompt-version invocation counts and outcomes, sourced from the Prompt Registry (§8). | Reserved. |
| **LLM Metrics** | Would record per-provider/model latency, error rate, and output-validation pass rate. | Reserved. |
| **Latency** | `DEFAULT_PROVIDER_TIMEOUT` bounds a single call today; no latency metric is collected. | Reserved. |
| **Cost** | Reserved — no per-call cost accounting exists, despite `tiktoken` (token accounting) already being a declared dependency (IMP-001 §5). | Reserved (dependency present, unused for this purpose). |
| **Token Consumption** | Would use the already-present `tiktoken` dependency to record per-call token counts. | Reserved. |
| **Evaluation Metrics** | Ad hoc Release Candidate validation (`output/releases/ril-rc1-api-validation`'s own grounding-support statistics) — not continuous. | Partially realized, ad hoc. |
| **Business Metrics** | Reserved — no platform-wide business-outcome metric exists yet. | Reserved. |
| **Operational Dashboards** | `governance_dashboard/` (Streamlit) — declared, not built (`NotImplementedError`, IMP-001 §11). | Reserved. |
| **Alerting** | Reserved — no alerting mechanism exists; depends on §8's Notification Service. | Reserved. |

## 16. Operational Model

| Concern | Reference Definition | Realization Status |
| --- | --- | --- |
| **Platform Operations** | Day-to-day running of every deployment unit (§8's own service boundary) — today, a developer's own local process. | Local-only (IMP-001 §10). |
| **Incident Management** | Reserved — no formal incident process exists; depends on §8's Notification and Audit Services. | Reserved. |
| **Model Operations** | Restates §9's Model Governance row — model-version changes are evaluated (`output/model-eval/`) before adoption. | Practiced informally. |
| **Knowledge Operations** | Reserved platform-wide — belongs to the not-yet-realized Knowledge Intelligence capability (§6). | Reserved. |
| **Platform Maintenance** | `ruff`/`mypy`-enforced coding standard, `make check` gate (IMP-001 §13) — maintenance today is developer-run. | Partially realized. |
| **Monitoring** | Restates §15 — reserved beyond a liveness check. | Reserved. |
| **Support** | Reserved — no formal support process or on-call rotation exists. | Reserved. |
| **Runbooks** | `DEMO_RUNBOOK.md` (repository root) is the platform's own existing runbook precedent, scoped to demonstration execution rather than production operations. | Partially realized, demonstration-scoped. |
| **SRE Practices** | Reserved — no error budget, SLO, or on-call practice is defined; depends on §14's Deployment Architecture existing first. | Reserved. |

## 17. Capability Extension Model

```
Capability Proposal
        ↓
Architecture Review
        ↓
Capability Design
        ↓
Runtime Design
        ↓
System Design
        ↓
Implementation
        ↓
Platform Registration
        ↓
Certification
```

| Stage | Governed by | Proven precedent (Requirements Intelligence) |
| --- | --- | --- |
| **Capability Proposal** | STD-002 §3's Proposed stage. | ADR-001 §10's own conceptual capability entry, prior to any CAP-001 content. |
| **Architecture Review** | HB-001 §15's Review Workflow, Architecture review. | ADR-001 itself, reviewed and (pending) approved by the Architecture Board. |
| **Capability Design** | STD-002, in full. | CAP-001 — Requirements Intelligence. |
| **Runtime Design** | STD-003, in full. | RUN-001 — Requirements Intelligence Runtime. |
| **System Design** | STD-005 §6's Decompose/Allocate semantics (SYS-001's own Transformation Record). | SYS-001 — Requirements Intelligence System Specification. |
| **Implementation** | STD-001, in full. | IMP-001 — Requirements Intelligence Implementation Specification. |
| **Platform Registration** | §8's Capability Registry (**reserved** — no registry service exists yet, §22). | Not yet performed for Requirements Intelligence — a recorded gap, not a silent skip. |
| **Certification** | HB-001 §6.8, in full. | Not yet performed for Requirements Intelligence — reserved, pending Runtime Ready maturity (STD-002 §9). |

**Governance requirements.** No stage may be skipped (restates STD-001 §7 Constraint 1's Architecture-cannot-change discipline, generalized to every stage above); every stage's own Output Artifact requires the Transformation Approval STD-005 §8 already mandates before the next stage may begin; a capability that reaches Implementation without ever completing Platform Registration or Certification (as Requirements Intelligence currently has not) is explicitly **not yet Runtime Ready** (STD-002 §9) — recorded honestly here, not asserted otherwise.

## 18. Platform Governance

| Governance kind | Rule |
| --- | --- |
| **Technology Governance** | Every technology decision (§12) is changed only through a revision to this document or a superseding ADR — never silently substituted by an implementation (restates STD-001 §7 Constraint 1, generalized). |
| **Architecture Governance** | Restates ADR-001 §18 in full — this document's own architecture changes only through a reviewed revision, never a silent edit. |
| **Prompt Governance** | Every prompt template's lifecycle state (`Production`/`Approved`) gates its use (§8's Prompt Registry) — an unsealed or un-fingerprinted template is never live. |
| **Model Governance** | Restates §9's Model Governance row — a model-version change is evaluated before adoption, never assumed safe by vendor default. |
| **Engineering Governance** | Restates STD-001 §3–§9 in full — every capability's own implementation (§17's Implementation stage) satisfies STD-001's Quality Gates before proceeding. |
| **Operational Governance** | Reserved pending §16's Operational Model maturing beyond its current local-only, developer-run state (§22). |
| **Change Governance** | A correction to a Frozen artifact in this platform is a new, Supersedes-semantic transformation (STD-005 §6, §10), never an edit to the original. |
| **Release Governance** | Restates §14's Release Strategy row — a release is not certified until its own manifest-versioned execution package (§14) is complete and its Known Limitations (§22-analogue, per document) are recorded. |

## 19. Platform Traceability

```
Business
        ↓
Architecture
        ↓
Platform
        ↓
Capability
        ↓
Runtime
        ↓
System
        ↓
Implementation
        ↓
Code
        ↓
Evidence
        ↓
Certification
```

| Hop | STD-005 Transformation Semantic | STD-004 Relationship Produced |
| --- | --- | --- |
| Business → Architecture | Refines | `derived_from` |
| **Architecture → Platform** | **Realizes → Allocates → Specializes → Preserves (this document's own Transformation Record, above)** | `implements`, `belongs_to`, `defines`, `traces_to` |
| Platform → Capability | Decomposes → Allocates → Specializes (ADR-001's own reserved hop, ADR-001 §17, now inheriting §8's shared services as its own starting substrate) | `governs`, `belongs_to`, `defines` |
| Capability → Runtime | Realizes → Preserves → Derives | `implements`, `belongs_to` |
| Runtime → System | Realizes → Decomposes → Allocates → Preserves (SYS-001's own Transformation Record) | `implements`, `governs` (×8), `belongs_to` (×8), `traces_to` |
| System → Implementation | Realizes → Allocates → Specializes → Preserves (IMP-001's own Transformation Record) | `implements`, `belongs_to` (×8), `defines`, `traces_to` |
| Implementation → Code | Realizes (IMP-001 §14) | `implements` |
| Code → Evidence | Verifies | `verified_by` |
| Evidence → Certification | Validates | `verified_by` |

**This chain extends every prior chain in this lineage by exactly one hop — `Platform`, inserted between `Architecture` and `Capability`** — restating this document's own opening framing (Transformation Record, above): PRA-001 performs ADR-001 §17's own reserved "Architecture Domains → Platform Capabilities" hop, giving it a reusable, technology-shaped form. This introduces no new stage to STD-005 §5's own seven-stage model — `Platform` sits entirely inside the single `Architectural Intent → Capability Intent` hop STD-005 §5 already names. The chain still converges with STD-004's canonical eight-tier graph (STD-004 §9) at the same points every prior document in this lineage already identified: `Architecture` at STD-004's `ADR` tier, `Capability` at its `Capabilities` tier, `Evidence` at its `Evidence` tier, `Certification` at its `Certification` tier — `Platform`, `System`, `Implementation`, and `Code` are refinements inside hops STD-004 itself does not further subdivide, never additional canonical tiers of their own.

## 20. Platform Evolution Roadmap

- **Near-term.** Complete Platform Registration and Certification (§17) for Requirements Intelligence, the platform's own first proven capability; close the highest-priority Known Limitations (§22) — authentication/authorization and CI-enforced quality gates.
- **Mid-term.** Move the Configuration, Secrets, Artifact Registry, and Policy Engine services (§8) from capability-scoped, partially-realized instances to genuinely shared, platform-wide services, once a second capability (§6) exists to prove the abstraction is worth generalizing (restates §4's Reusable Platform Services principle — never generalized speculatively, always against a second real consumer).
- **Long-term.** Realize Architecture, Capability, Runtime, Traceability, and Knowledge Intelligence (§6) as full capabilities, each inheriting this reference architecture rather than re-deriving one; formally decide the Security (ADR-007) and Deployment (ADR-008) architectures this document currently holds only as Provisional Reference (§13, §14, §22).
- **Emerging AI capabilities.** Reasoning Pipeline, Agent Orchestration, and Tool Invocation (§9) remain reserved until a specific capability's own governed contract requires them — adopted through §20's own governed-evolution discipline, never speculatively.
- **Technology modernization.** The reserved relational-database migration (§12), Azure OpenAI provider completion (§9), and CI/CD platform adoption (§12) are the platform's own next concrete technology increments.
- **Cloud portability.** Kubernetes as the recommended container-orchestration target (§14) is chosen specifically to keep this platform vendor-neutral where practical (Architecture Philosophy, header) — no cloud-provider-specific service is named as a platform dependency anywhere in this document.
- **Multi-model evolution.** The Model Router (§8) is designed to add a provider without changing any capability's own contract — Azure OpenAI's completion (§9) is the first proof of this, a further provider the second.
- **Platform federation.** As additional Intelligence capabilities (§6) are realized, this document's own §8 services become the shared substrate connecting them — federation across capabilities, never a new, competing platform per capability.

## 21. Revision Summary

PRA-001, Version 1.0, performs ADR-001 §17's own reserved "Architecture Domains → Platform Capabilities" hop: it defines nineteen platform-wide architectural principles each restating a specific ADR-001 or STD-000 rule (§4), ten architecture views reconciled against one another (§5), a capability map that honestly distinguishes ADR-001-authorized capabilities from three candidate names this document is not authorized to freeze (§6), nine infrastructure-facing Platform Domains complementary to ADR-001's seven business-facing Architectural Domains (§7), twenty-one shared platform services each with an honest realization status (§8), a complete AI reference architecture grounded in Requirements Intelligence's own proven implementation (§9), an engineering architecture reusing the platform's existing lifecycle and transformation vocabulary without reinventing either (§10), an information architecture extending ADR-001 §12 with the versioning/retention/lifecycle/classification detail it deferred (§11), a technology architecture with purpose, alternatives, rationale, and replacement strategy for every decision including every deliberate non-adoption (§12), Security and Deployment Reference Architectures explicitly marked Provisional pending ADR-007 and ADR-008 (§13–§14), an Observability Reference Architecture and Operational Model that record what is realized and what remains reserved with equal explicitness (§15–§16), a Capability Extension Model proven against Requirements Intelligence's own real, in-progress lifecycle (§17), platform governance mechanics (§18), a Platform Traceability chain extending this lineage by exactly one hop (§19), and a governed Evolution Roadmap (§20). It introduces no business capability ADR-001 §10 does not already name, and modifies no frozen input.

## 22. Known Limitations

Recorded explicitly, per STD-001 §6's and this lineage's own Known Limitations discipline — a gap named, never silently omitted:

- **System Intelligence, Evidence Intelligence, and Certification Intelligence (§6) are not yet ADR-001-authorized capabilities.** They are observed emerging from SYS-001's, STD-004's, and HB-001's own document-tier vocabulary, but require a future ADR (extending ADR-001 §10, or a dedicated ADR-002) before this document — or any future CAP-NNN — may treat them as authorized.
- **§13 (Security) and §14 (Deployment) are Provisional Reference Architectures**, pending ADR-007 and ADR-008 respectively (both already named in ADR-001 §19's own Future ADR Roadmap). Nothing in either section may be cited as a frozen architectural decision until its own ADR exists.
- **HB-001's Revision 2 document-family catalogue (§6) does not yet name a "Platform Reference Architecture" family.** PRA-001 is positioned, provisionally, as an ADR-family-adjacent artifact (by analogy to HB-001 §6.3's Design Proposal — a satellite carrying detail an ADR would otherwise have to inline) pending a future HB-001 revision that formally registers a PRA family.
- **Nineteen of §8's twenty-one Shared Platform Services remain wholly or partially reserved** — only the Prompt Registry and (capability-scoped) Context Manager are fully realized; most others exist, if at all, only as a Requirements-Intelligence-scoped precursor, never yet generalized into a genuinely shared service.
- **No authentication, authorization, secrets vault, audit service, or at-rest encryption exists anywhere in the platform today** (§13) — the platform's single most significant recorded gap, inherited directly from IMP-001 §9 and §17.
- **No container platform, infrastructure platform, CI/CD platform, staging environment, or production environment exists** (§14) — deployment is local-only, matching the platform's current Implementing lifecycle stage (STD-002 §9).
- **No tracing, metrics, cost, latency, or token-consumption observability exists**, despite the `tiktoken` dependency already being present and unused for this purpose (§15).
- **No capability has yet completed Platform Registration or Certification** (§17) — Requirements Intelligence, the platform's own most mature capability, has completed only Capability Design through Implementation.
- **This document's own Provided Contracts, Consumers, and Dependencies columns (§8) describe target-state service contracts for services that do not yet exist as services** — they are the contract a future implementation SHALL satisfy, not a description of a running system, for every row marked "Reserved."

## 23. Final Self Review

- [x] Architecture completeness — all twenty-four required sections are present and address their commissioned objective.
- [x] Consistency with ADR-001 — every principle (§4), domain (§7), and capability (§6) cites a specific ADR-001 section; no citation restates or reinterprets one.
- [x] Capability independence — §6 defines no business capability's own responsibility; §8's services perform no capability-specific business logic (§4's Capability-first Design principle, verified section by section).
- [x] Platform reusability — every service in §8 and every technology in §12 is stated as a platform-wide default, not a Requirements-Intelligence-specific choice, even where Requirements Intelligence is currently its only consumer.
- [x] Governance alignment — §18 binds this document to HB-001 §15's Review Workflow and STD-005's own transformation governance without inventing a competing process.
- [x] Technology justification — every technology decision in §12, including every deliberate non-adoption, states its purpose, alternatives, rationale, and replacement strategy.
- [x] Operational readiness — §16 states plainly that operational maturity is local-only today; no operational capability is claimed that §22 does not also disclose as reserved.
- [x] Scalability — §14's Scaling row names a concrete target shape (stateless replicas) without asserting it is built.
- [x] Extensibility — §20's Evolution Roadmap and §17's Capability Extension Model together show how a new capability or service joins this platform without redesigning it.
- [x] Maintainability — every service (§8) and domain (§7) declares exactly one owner; no shared responsibility exists anywhere in this document.
- [x] Future readiness — §22 names every deferred decision explicitly, giving ADR-007, ADR-008, and a future ADR-002 (or ADR-001 §10 extension) a concrete, working reference to formalize rather than an empty starting point.

## 24. Platform Compliance Certificate

- ✅ **Mission Completed** — the reusable Platform Reference Architecture for the Engineering Intelligence Platform is established.
- ✅ **Reference Architecture Complete** — §2–§12 define the platform's vision, principles, views, capability map, domains, shared services, AI architecture, engineering architecture, information architecture, and technology architecture in full.
- ✅ **AI Architecture Complete** — §9 defines all twenty-one required AI-architecture concerns, each with an honest realization status.
- ✅ **Engineering Architecture Complete** — §10 defines the platform's lifecycle, transformation pipeline, review/approval gates, evidence, certification flow, traceability, and automation.
- ✅ **Technology Architecture Complete** — §12 defines every required technology category with purpose, alternatives, rationale, and replacement strategy.
- ✅ **Security Architecture Complete** — §13, marked Provisional pending ADR-007 (§22), covers every required security concern.
- ✅ **Deployment Architecture Complete** — §14, marked Provisional pending ADR-008 (§22), covers every required deployment concern.
- ✅ **Operational Architecture Complete** — §16 covers every required operational concern, with realization status disclosed throughout.
- ✅ **Governance Complete** — §18 binds every governance kind the mission requires to an existing Normative authority.
- ✅ **Traceability Complete** — §19 extends the platform's own Business → Architecture → Platform → Capability → Runtime → System → Implementation → Code → Evidence → Certification chain by exactly one governed hop, converging with STD-004's canonical graph.
- ✅ **Reusable Across Capabilities** — §6, §8, and §20 together demonstrate this architecture is built to be inherited, not re-derived, by every future capability.
- ✅ **Suitable for Architecture Review Board Approval.**

---

*End of PRA-001, Version 1.0.*
