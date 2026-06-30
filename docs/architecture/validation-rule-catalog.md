# Validation Rule Catalog

| Attribute            | Value                                                              |
| -------------------- | ------------------------------------------------------------------ |
| Document type        | Solution Architecture Specification / Governing Rule Catalog        |
| Status               | Approved — foundational                                           |
| Scope                | Every validation rule that may exist in the Response Validation Framework |
| Governs              | Rule identity, number allocation, metadata, lifecycle, classification, stability, catalog version, profiles, severity, blocking, independence, dependencies, versioning, governance |
| Depends on           | AI Response Validation Architecture · Validation Canonical Models · Response Normalization Contract · AI Reasoning Contract |
| Audience             | Solution Architects · Technical Architects · Lead Engineers · QA Architects |
| Implementation-bound | No — valid regardless of language, framework, persistence, or AI provider |

> **Architectural Decision**
> **Validation rules are governed by architecture, never invented during
> implementation.** A rule does not come into existence because an engineer
> wrote one; it comes into existence because this catalog defines it — its
> identity, its layer, its single responsibility, and its metadata. Every rule
> implementation, in any technology, must conform to this catalog. The catalog is
> the single source of truth for every validation rule that will ever exist.

---

## 1. Purpose

### 1.1 Why this catalog exists

The Response Validation Framework is the mandatory quality gate between AI
generation and every downstream engineering capability (AI Response Validation
Architecture §1). That gate is composed of **validation rules** — each one a
single, atomic check. If rules were created ad hoc during implementation, the
platform would suffer:

- **Identity drift** — the same concern would be checked under different names in
  different places, defeating audit and regression analysis.
- **Responsibility overlap** — two rules would silently check the same thing, or
  one rule would check several, blurring what failed and why.
- **Layer confusion** — a content concern might be checked at the transport
  layer, breaking the progressive pipeline.
- **Ungoverned growth** — no authority would decide which checks are legitimate,
  what they mean, or how severe they are.

This catalog exists to **define the complete, governed set of validation rules**
— their identities, responsibilities, layer ownership, severity guidance,
blocking guidance, and evolution rules — so that every rule the platform will
ever run is accounted for by architecture before it is built.

### 1.2 What this document is **not**

| This document is NOT | Because |
| -------------------- | ------- |
| An implementation guide | It defines *what* each rule is responsible for, never *how* a rule is built. |
| A coding specification | No algorithms, data structures, or interfaces are described. |
| A framework specification | Pipeline orchestration and the canonical models are governed elsewhere. |
| A provider or technology document | No model, vendor, language, framework, or format is referenced. |

> **Principle**
> Every rule in this catalog is described by its **responsibility and identity**,
> never by its mechanism. A rule's responsibility is a stable architectural fact;
> its mechanism is a replaceable implementation detail.

---

## 2. Scope

### 2.1 In scope

| In scope | Description |
| -------- | ----------- |
| **Rule definitions** | The catalog of rules and the single concern each one owns. |
| **Rule identities** | The stable identifier standard every rule carries (§4). |
| **Rule responsibilities** | The one concern each rule validates and nothing more (§3). |
| **Layer ownership** | Which validation layer each rule belongs to (§8, §9). |
| **Severity guidance** | How a rule's findings map to severity (§14). |
| **Blocking guidance** | When a rule's finding may or may not block progression (§15). |
| **Rule evolution** | Lifecycle, classification, stability, profiles, versioning, catalog version, and governance (§7, §10, §11, §13, §20, §21, §22). |

### 2.2 Out of scope

| Out of scope | Owned by |
| ------------ | -------- |
| **Rule implementation** | The future rule implementations, governed by this catalog but not described here. |
| **Algorithms** | Implementation detail; never an architectural concern. |
| **Framework behaviour** | Response Validation Framework (registry, rule contract). |
| **Pipeline orchestration** | AI Response Validation Architecture + the pipeline. |
| **Canonical models** | Validation Canonical Models. |

> **Architectural Decision**
> This catalog governs **what rules exist and what each is responsible for**. It
> never governs **how a rule works** or **how rules are executed**. Mechanism and
> orchestration are deliberately excluded so the catalog stays stable across
> decades of implementation change.

---

## 3. Validation Rule Philosophy

### 3.1 One rule, one responsibility

> **Principle**
> **Every rule validates exactly one concern — and only one.** A rule that checks
> two things is two rules. A concern that is checked by two rules is a duplicated
> responsibility and a defect in the catalog.

This is the foundational law of the catalog. It mirrors, at the rule level, the
"one concern per layer" principle of the validation pipeline (AI Response
Validation Architecture §4).

### 3.2 Why single responsibility matters

| Quality | How single responsibility maximises it |
| ------- | -------------------------------------- |
| **Determinism** | A rule with one concern has one, reproducible answer for a given response. Compound rules entangle conditions and obscure which produced a finding. |
| **Parallelism** | Independent single-concern rules can be evaluated in any order, including concurrently, without changing the outcome (§16). |
| **Maintainability** | A change to one concern touches exactly one rule; nothing else is at risk. |
| **Traceability** | A finding names exactly one rule and one concern, so a reviewer knows precisely what failed and why. |
| **Future evolution** | New concerns are added as new rules, never by overloading existing ones; the catalog grows additively. |

### 3.3 Worked example

> **Worked example — splitting a compound check**
> Consider a tempting "the requirement is well-formed" check that verifies a
> requirement is non-empty, has a description, and carries a valid confidence.
> That is **three** concerns and therefore **three** rules:
>
> | Rule | Single concern |
> | ---- | -------------- |
> | `CONTENT-0001` Empty Requirement | The requirement is not empty. |
> | `CONTENT-0003` Missing Description | The requirement carries a description. |
> | `CONTENT-0004` Invalid Confidence | The confidence is within its permitted set. |
>
> Each can fail, be reasoned about, and evolve independently. A single combined
> rule would hide *which* aspect failed and would couple three unrelated reasons
> to change into one.

---

## 4. Rule Identity Standard

### 4.1 Rule ID format

Every rule carries a stable **Rule ID** in the form:

```text
   <LAYER>-NNNN
   │        │
   │        └── a zero-padded sequential number, unique within the layer
   └── the layer prefix (stable token, upper case)
```

Examples: `TRANSPORT-0001`, `SYNTAX-0001`, `SCHEMA-0001`, `STRUCTURE-0001`,
`CONTENT-0001`, `EVIDENCE-0001`, `TRACEABILITY-0001`, `REASONING-0001`,
`BUSINESS-0001`.

### 4.2 Layer prefixes

The Rule ID prefix is a fixed token per layer. Two layers carry a prefix that is
a deliberate short form of the layer name; this mapping is authoritative.

| Validation layer | Rule ID prefix |
| ---------------- | -------------- |
| Transport | `TRANSPORT` |
| Syntax | `SYNTAX` |
| Schema | `SCHEMA` |
| Structural | `STRUCTURE` |
| Content | `CONTENT` |
| Evidence | `EVIDENCE` |
| Traceability | `TRACEABILITY` |
| Reasoning | `REASONING` |
| Business Rule | `BUSINESS` |

> **Architectural Decision**
> The prefix is a **stable identity token**, not a description. `STRUCTURE` is the
> prefix for the Structural layer and `BUSINESS` for the Business Rule layer; these
> short forms are fixed by this catalog. A rule's prefix never changes even if the
> layer is later described differently in prose.

### 4.3 Identity stability

> **Principle**
> **Rule IDs never change. Rule names may evolve.** The ID is the permanent,
> machine- and audit-facing identity that appears in validation records; it is
> immutable for the life of the platform. The name is a human-readable label that
> may be refined for clarity without affecting identity.

- A Rule ID, once published, is fixed forever — even if the rule is deprecated or
  retired (§7, §22).
- A retired Rule ID is **never** reassigned to a different concern.
- Renaming a rule (its Name) is permitted and expected; it does not constitute a
  new rule.

### 4.4 Reserved rule number ranges

Within each layer, the sequential number `NNNN` is allocated from **reserved
ranges** aligned to rule classification (§10). The ranges are authoritative and
apply identically to every layer.

| Number range | Reserved for |
| ------------ | ------------ |
| `0001`–`0099` | **Core** rules |
| `0100`–`0199` | **Extended** rules |
| `0200`–`0299` | **Organization** rules |
| `0300`–`0899` | **Future expansion** (unallocated; reserved for ranges not yet defined) |
| `0900`–`0999` | **Reserved** (held back for special governance use) |

**Rules of allocation.**

- A new rule takes the **next free number** in the range matching its
  classification, within its layer.
- Numbers are **never reused** — a retired rule's number is retired with it and
  is never reassigned (§4.3, §22), exactly like its full Rule ID.
- **Gaps are intentional.** An unused number inside a range is left empty
  deliberately; gaps reserve room for related rules and are never "filled in" to
  appear tidy. A gap is a feature of disciplined numbering, not an error.

> **Architectural Decision**
> **Number ranges are part of rule identity and are reserved in advance.**
> Allocating numbers by classification means a Rule ID alone signals a rule's
> tier (`EVIDENCE-0001` is Core; a future `EVIDENCE-0103` is Extended). Numbering
> discipline keeps identity self-describing and prevents two classifications from
> ever colliding on the same number.

> **Worked example — allocating a new Extended evidence rule**
> The Evidence layer's Core rules occupy `EVIDENCE-0001`–`EVIDENCE-0003`. A newly
> approved Extended evidence rule does **not** become `EVIDENCE-0004` (that number
> is in the Core range and is left as an intentional gap for a future Core rule);
> it is allocated `EVIDENCE-0100`, the first free number in the Extended range.
> The Core gap at `0004` remains reserved for a future Core concern.

---

## 5. Rule Naming Convention

Beyond the immutable Rule ID, every rule carries a human-readable **Rule Name**
that follows a consistent convention: a concise, concern-describing noun phrase
ending in *Rule*.

| Convention | Conforming names | Non-conforming names |
| ---------- | ---------------- | -------------------- |
| Name the *concern*, end in *Rule* | `ResponseExistsRule`, `RequiredSectionsRule`, `DuplicateRequirementRule` | `CheckResponse`, `Rule1`, `ValidationRuleA` |

**Rules.**
- A name states **what concern is validated**, not what action is taken.
  `ResponseExistsRule` (concern) is correct; `CheckResponse` (action) is not.
- A name is **descriptive and unique**; sequential or opaque names (`Rule1`,
  `ValidationRuleA`) are prohibited because they carry no meaning.
- The name complements the ID: the ID is the stable identity, the name is the
  readable description of the same single concern.

> **Principle**
> A reader must understand a rule's responsibility from its name alone. A name
> that requires looking up its definition to understand its concern has failed
> the convention.

---

## 6. Rule Metadata Standard

Every rule is described by a conceptual metadata record. This is the
architectural description of a rule — distinct from any implementation. (It
aligns with the rule-identity metadata of the Response Validation Framework and
the Validation Canonical Models.)

| Field | Meaning |
| ----- | ------- |
| **Rule ID** | The stable, immutable identifier (`<LAYER>-NNNN`, §4). |
| **Rule Name** | The human-readable, concern-describing name (§5). May evolve. |
| **Purpose** | The single concern the rule validates, stated in one sentence (§3). |
| **Layer** | The one validation layer the rule belongs to (§8). |
| **Classification** | The rule's role: Core, Extended, Organization, or Experimental (§10). |
| **Stability** | The architecture's confidence in the rule: Experimental, Stable, Mature, Frozen (§11). |
| **Severity** | The severity its findings carry, per the severity guidance (§14). |
| **Blocking Capability** | Whether the rule is permitted to block progression (§15). |
| **Architecture Reference** | The governing section of this catalog (and, where relevant, the AI Response Validation Architecture). |
| **Contract Version** | The Validation Contract Version under which the rule's semantics are defined (§20). |
| **Rule Version** | The version of this rule's own definition (§20). |
| **Lifecycle Status** | One of Draft, Approved, Implemented, Deprecated, Retired (§7). |
| **Owner** | The architectural owner accountable for the rule's definition. |
| **Worked Example** | A concrete passing and failing illustration of the concern. |
| **Future Notes** | Reserved guidance for anticipated evolution of the rule. |

> **Architectural Decision**
> A rule is not catalogued until **every** metadata field is defined. Incomplete
> metadata — a missing Purpose, an undefined Layer, an absent Architecture
> Reference — means the rule does not yet exist as far as the platform is
> concerned. Metadata completeness is a precondition of rule existence.

---

## 7. Rule Lifecycle

Every rule moves through a governed lifecycle. The status is part of its metadata
(§6) and is changed only by architectural governance (§22).

```text
     ┌────────┐     approve     ┌──────────┐    implement   ┌─────────────┐
     │ Draft  │ ───────────────►│ Approved │ ──────────────►│ Implemented │
     └────────┘                 └──────────┘                └──────┬──────┘
          │                                                        │ supersede
          │ reject (never assigned an ID)                          ▼
          ▼                                                 ┌─────────────┐
     (discarded)                                            │ Deprecated  │
                                                            └──────┬──────┘
                                                                   │ retire
                                                                   ▼
                                                            ┌─────────────┐
                                                            │  Retired    │
                                                            └─────────────┘
                                               (ID frozen forever; never reused)
```

| State | Meaning |
| ----- | ------- |
| **Draft** | The rule is proposed and under architectural review. It has no committed identity yet. |
| **Approved** | The rule is accepted into the catalog and assigned a permanent Rule ID. It may not yet be implemented. |
| **Implemented** | A conforming implementation of the rule exists and participates in validation runs. |
| **Deprecated** | The rule is still honoured but slated for removal; a successor (often a new rule) is preferred. |
| **Retired** | The rule no longer participates in validation. Its Rule ID is frozen forever and never reassigned (§4.3, §22). |

> **Principle**
> A rule's **identity outlives its activity**. A retired rule keeps its ID
> permanently so that historical validation records remain interpretable. Lifecycle
> changes never recycle identities.

---

## 8. Validation Layers

The nine layers are the architecture-mandated progression of the validation
pipeline, ordered from the most foundational concern to the most semantic (AI
Response Validation Architecture §4). Every rule belongs to exactly one layer.

```text
   Transport ─► Syntax ─► Schema ─► Structural ─► Content ─►
                                  Evidence ─► Traceability ─► Reasoning ─► Business Rule
   (most foundational)                                                  (most semantic)
```

### 8.1 Transport

- **Purpose.** Confirm a usable response was actually received.
- **Responsibilities.** Detect absence, emptiness, truncation, timeout, and
  delivery-level failure of the response.
- **Typical validations.** A response exists; it is non-empty; it was not
  truncated; the generation did not time out or fail at the delivery boundary.
- **Must never validate here.** Anything about the *content* of the response —
  its structure, fields, or meaning. The transport layer only asks whether there
  is something to validate at all.
- **Worked example.** A response that never arrived is a Transport finding; a
  response that arrived but omits a required section is **not** — that is a
  Structural concern.

### 8.2 Syntax

- **Purpose.** Confirm the response is well-formed structured data that can be
  interpreted without ambiguity.
- **Reads.** The **normalized representation** (`ParsedResponse`) created once by
  the Response Normalization Layer (Response Normalization Contract). Syntax rules
  **read** that representation — its **Normalization Outcome** and **Normalization
  Observations** — they never parse or normalize the response themselves. Those
  outcomes and observations are **facts**; a Syntax rule may *decide*, by reading a
  fact, to raise a `ValidationIssue`, but the fact itself is never an issue
  (Response Normalization Contract §10).
- **Responsibilities.** Detect a not-well-formed (malformed) response, ambiguous
  or duplicated field identifiers, and character-encoding integrity problems.
- **Typical validations.** The normalization outcome reports a single,
  unambiguous structure (`NORMALIZED`, not `MALFORMED`); no field identifier is
  duplicated within the same structural object; the character encoding is intact.
- **Must never validate here.** Whether the (well-formed) structure matches the
  *expected* shape — that is Schema. Syntax only asks whether the structure is
  well-formed at all. It also never *recovers* the structure; recovery is the
  Response Normalization Layer's concern, not a validation concern.
- **Worked example.** A response whose structure cannot be unambiguously
  interpreted (a `MALFORMED` outcome) is a Syntax finding; a well-formed structure
  missing an expected section is a Schema or Structural concern.

> **Architectural Decision — Syntax validates structure; it does not recover it.**
> The transition from text to structure happens **once**, in the Response
> Normalization Layer, before the pipeline runs. Every layer from Syntax onward
> reads the **same** `ParsedResponse` (a Shared Platform Artifact): the Syntax
> layer reads its Normalization Outcome and Normalization Observations, and Schema,
> Structural, Content, Evidence, Traceability, Reasoning, and Business Rule read its
> normalized structure. No validation layer parses, and no validation layer
> normalizes — which is what lets the layers stay independent (§16) and the "is it
> well-formed?" concern stay owned by exactly one layer (§8).

### 8.3 Schema

- **Purpose.** Confirm the well-formed structure conforms to the expected,
  versioned shape.
- **Responsibilities.** Detect missing required sections, wrong field types,
  invalid enumerated values, and missing required collections.
- **Typical validations.** All required sections are present; each field is of its
  expected type; enumerated fields hold a permitted value; required collections
  exist.
- **Must never validate here.** The *meaning* or *quality* of conformant content —
  e.g. whether a present requirement is empty (Content) or unsupported (Evidence).
- **Worked example.** A confidence field holding a value outside its permitted set
  is a Schema finding; a confidence that is valid but inconsistent with the
  requirement's evidence is a Reasoning concern.

### 8.4 Structural

- **Purpose.** Confirm the required containers and relationships between sections
  are present and correctly composed.
- **Responsibilities.** Detect missing top-level sections and broken parent–child
  composition between them.
- **Typical validations.** The executive summary, requirements, risks, and
  recommendations containers are present and correctly nested.
- **Must never validate here.** The *content* of those containers — whether the
  requirements inside are empty, duplicated, or unsupported. Structural asks only
  whether the containers and their relationships exist.
- **Worked example.** An absent risks container is a Structural finding; a present
  but empty risk inside it is a Content concern.

### 8.5 Content

- **Purpose.** Confirm individual field-level values meet presence and validity
  expectations.
- **Responsibilities.** Detect empty entries, duplicated entries, missing
  descriptions, and out-of-range field values.
- **Typical validations.** A requirement is not empty; requirements are not
  duplicated; each requirement carries a description; a confidence value is within
  its valid range.
- **Must never validate here.** Whether a valid-looking conclusion is *grounded*
  (Evidence), *traceable* (Traceability), or *coherent* (Reasoning).
- **Worked example.** A requirement with no description is a Content finding; a
  fully-described requirement with no supporting evidence is an Evidence concern.

### 8.6 Evidence

- **Purpose.** Confirm conclusions carry the evidence references the platform
  requires (AI Reasoning Contract — evidence-driven reasoning).
- **Responsibilities.** Detect conclusions presented without supporting evidence.
- **Typical validations.** Each requirement, each risk, and each recommendation
  carries at least the evidence reference the platform requires.
- **Must never validate here.** Whether the evidence *links resolve* (Traceability)
  or whether the conclusion is internally *consistent* (Reasoning). Evidence asks
  only whether required grounding is present.
- **Worked example.** A risk with an empty evidence reference is an Evidence
  finding; a risk whose evidence reference points to a non-existent source is a
  Traceability concern.

### 8.7 Traceability

- **Purpose.** Confirm each element carries the links needed to trace it to its
  source and execution context.
- **Responsibilities.** Detect missing or unresolved trace links from conclusions
  back to their originating evidence and context.
- **Typical validations.** Each requirement, risk, and recommendation can be
  traced to its source artifact and correlation context.
- **Must never validate here.** Whether the *evidence exists* (Evidence) or whether
  the content is *coherent* (Reasoning). Traceability asks only whether the links
  are present and resolvable.
- **Worked example.** A requirement with no source reference is a Traceability
  finding; a requirement that contradicts another is a Reasoning concern.

### 8.8 Reasoning

- **Purpose.** Confirm the output is internally coherent and self-consistent.
- **Responsibilities.** Detect contradictions, duplicated conclusions, and
  circular logic across the output.
- **Typical validations.** No two requirements contradict each other; no
  recommendation is duplicated; no chain of reasoning is circular.
- **Must never validate here.** Declared platform-level structural policy — that is
  Business Rule. Reasoning concerns the output's internal coherence, not external
  policy.
- **Worked example.** Two requirements asserting different limits for the same
  field is a Reasoning finding; a response missing a mandated minimum number of
  recommendations is a Business Rule concern.

### 8.9 Business Rule

- **Purpose.** Confirm declared, platform-level structural policies are satisfied.
- **Responsibilities.** Detect violations of declared completeness and coverage
  policies.
- **Typical validations.** A minimum number of recommendations is present; risk
  coverage and requirement coverage thresholds are met; cross-domain completeness
  is satisfied.
- **Must never validate here.** Real-world correctness, business approval, or
  prioritisation — those lie outside the validation boundary entirely (AI Response
  Validation Architecture §9).
- **Worked example.** A response with fewer than the mandated minimum
  recommendations is a Business Rule finding; whether those recommendations are the
  *right* ones is a human decision outside validation.

> **Architectural Decision**
> A concern is validated at **exactly one layer**. If a candidate rule seems to fit
> two layers, it is either misclassified or it is secretly two rules. Layer
> ownership is a defining property of a rule's identity, not a convenience.

---

## 9. Initial Rule Catalog

The tables below define the **initial** rules per layer. Each entry is a single
concern with a stable Rule ID. Every initial rule is **Core** and therefore
occupies the Core number range (`0001`–`0099`, §4.4). This is a starting set, not
a closed one (§9.10).

### 9.1 Transport

| Rule ID | Name | Single concern |
| ------- | ---- | -------------- |
| `TRANSPORT-0001` | ResponseExistsRule | A response was received. |
| `TRANSPORT-0002` | EmptyResponseRule | The received response is non-empty. |
| `TRANSPORT-0003` | TimeoutRule | The generation did not time out. |
| `TRANSPORT-0004` | ProviderFailureRule | The generation did not fail at the delivery boundary. |

#### Transport Layer Status — FROZEN

| Attribute | Value |
| --------- | ----- |
| **Status** | **FROZEN** |
| Production rules | `TRANSPORT-0001` · `TRANSPORT-0002` · `TRANSPORT-0003` · `TRANSPORT-0004` |
| Rule range | Fully allocated for the layer's four execution guarantees |
| Stability (§11) | **Frozen** — the architecture's highest confidence level |
| Further rules planned | None |

The Transport layer is **complete**. Its four rules guarantee, in order, that a
response **exists** (`TRANSPORT-0001`), **carries usable content**
(`TRANSPORT-0002`), came from an execution that **did not time out**
(`TRANSPORT-0003`), and came from an execution that **did not fail at the
provider/delivery boundary** (`TRANSPORT-0004`). Together these are the complete
set of *delivery-level* guarantees; no Transport concern remains unrepresented.

- The rule range is **fully allocated** — there is no Transport concern left to
  catalogue.
- **No further Transport rules are currently planned.**
- **Adding, removing, or re-scoping a Transport rule requires an approved
  Architecture Decision Record** (§22 Rule Governance). A new Transport Rule ID
  may be minted only through governance.
- **Implementation changes may still occur** — a rule's mechanism may be
  optimised or a defect fixed, advancing the Validator Version (and, if a rule's
  definition genuinely changes, its Rule Version) per §20. These are *mechanism*
  changes, not *architecture* changes.
- **Architectural responsibilities are frozen.** Each rule's identity, layer
  ownership, single concern, severity, and blocking capability are immutable.

> **Architectural Decision**
> **The Transport layer is now immutable.** It validates exactly one family of
> concerns — *delivery-level guarantees about the response* — and that family is
> fully covered by four single-responsibility rules over normalized,
> provider-independent signals (`llm_response` presence, `generated_text`
> emptiness, and the `ExecutionStatus` outcomes `TIMEOUT` and `FAILED`). Because
> every Transport guarantee is already owned by exactly one rule, any further
> change would either duplicate an existing responsibility or cross into another
> layer's concern (Syntax onward). Freezing the layer protects the foundational
> guarantees that every higher layer is permitted to assume without re-checking.
> The layer may evolve only through an approved ADR; its responsibilities do not
> change.

### 9.2 Syntax

| Rule ID | Name | Single concern |
| ------- | ---- | -------------- |
| `SYNTAX-0001` | ValidStructureRule | The response is well-formed structured data. |
| `SYNTAX-0002` | DuplicateKeysRule | No field identifier is duplicated within a structural object. |
| `SYNTAX-0003` | EncodingRule | The response's character encoding is intact. |

### 9.3 Schema

| Rule ID | Name | Single concern |
| ------- | ---- | -------------- |
| `SCHEMA-0001` | RequiredSectionsRule | All required sections are present. |
| `SCHEMA-0002` | FieldTypesRule | Each field is of its expected type. |
| `SCHEMA-0003` | EnumerationsRule | Each enumerated field holds a permitted value. |
| `SCHEMA-0004` | RequiredArraysRule | Each required collection is present. |

### 9.4 Structural

| Rule ID | Name | Single concern |
| ------- | ---- | -------------- |
| `STRUCTURE-0001` | SummaryExistsRule | The executive summary container is present. |
| `STRUCTURE-0002` | RisksExistsRule | The risks container is present. |
| `STRUCTURE-0003` | RecommendationsExistsRule | The recommendations container is present. |
| `STRUCTURE-0004` | RequirementsExistsRule | The requirements container is present. |

### 9.5 Content

| Rule ID | Name | Single concern |
| ------- | ---- | -------------- |
| `CONTENT-0001` | EmptyRequirementRule | A requirement is not empty. |
| `CONTENT-0002` | DuplicateRequirementRule | Requirements are not duplicated. |
| `CONTENT-0003` | MissingDescriptionRule | A requirement carries a description. |
| `CONTENT-0004` | InvalidConfidenceRule | A confidence value is within its valid range. |

### 9.6 Evidence

| Rule ID | Name | Single concern |
| ------- | ---- | -------------- |
| `EVIDENCE-0001` | RequirementEvidenceRule | A requirement carries required evidence. |
| `EVIDENCE-0002` | RiskEvidenceRule | A risk carries required evidence. |
| `EVIDENCE-0003` | RecommendationEvidenceRule | A recommendation carries required evidence. |

### 9.7 Traceability

| Rule ID | Name | Single concern |
| ------- | ---- | -------------- |
| `TRACEABILITY-0001` | RequirementTraceRule | A requirement is traceable to its source. |
| `TRACEABILITY-0002` | RiskTraceRule | A risk is traceable to its source. |
| `TRACEABILITY-0003` | RecommendationTraceRule | A recommendation is traceable to its source. |

### 9.8 Reasoning

| Rule ID | Name | Single concern |
| ------- | ---- | -------------- |
| `REASONING-0001` | ContradictoryRequirementRule | No two requirements contradict each other. |
| `REASONING-0002` | DuplicateRecommendationRule | No recommendation is duplicated. |
| `REASONING-0003` | CircularLogicRule | No chain of reasoning is circular. |

### 9.9 Business Rule

| Rule ID | Name | Single concern |
| ------- | ---- | -------------- |
| `BUSINESS-0001` | MinimumRecommendationsRule | A minimum number of recommendations is present. |
| `BUSINESS-0002` | RiskCoverageRule | Risk coverage meets the declared policy. |
| `BUSINESS-0003` | RequirementCoverageRule | Requirement coverage meets the declared policy. |
| `BUSINESS-0004` | CrossDomainCompletenessRule | Cross-domain completeness is satisfied. |

### 9.10 The catalog is expected to grow

> **Architectural Decision**
> The rules above are the **initial** catalog, not the final one. The catalog is
> **expected to grow** as new concerns are recognised. Growth is always additive
> and always governed (§22): new concerns become new rules with new IDs allocated
> from the reserved ranges (§4.4); existing rules are never overloaded to absorb
> them.

---

## 10. Rule Classification

Every rule carries a **classification** that states its role in the platform.
Classification is orthogonal to layer, to severity, and to stability (§11).

| Classification | Meaning | Number range (§4.4) | Default availability |
| -------------- | ------- | ------------------- | -------------------- |
| **Core** | Mandatory rules that uphold baseline trustworthiness. | `0001`–`0099` | Always enabled. |
| **Extended** | Optional rules that add depth beyond the baseline. | `0100`–`0199` | Enabled by profile (§13). |
| **Organization** | Customer- or organization-specific rules. | `0200`–`0299` | Enabled by profile; reserved for future profiles. |
| **Experimental** | Research-only rules under evaluation. | (allocated per host classification when promoted) | Never enabled in standard operation; future capability. |

> **Architectural Decision**
> **Core rules are mandatory and always enabled.** They are the irreducible
> baseline every validation run applies. Extended, Organization, and Experimental
> rules are selectable, but no selection may ever *disable* a Core rule — doing so
> would lower the platform below its baseline of trustworthiness.

---

## 11. Rule Stability

**Rule Stability** is the architecture's confidence in a rule. It is an
architectural concept **independent of** lifecycle (§7), classification (§10),
severity (§14), and version (§20). A rule has both a lifecycle status *and* a
stability state at all times, and the two move independently.

| Stability | Meaning |
| --------- | ------- |
| **Experimental** | Newly introduced; its definition may still be refined. Low architectural confidence. |
| **Stable** | Proven in normal operation; safe to rely on. Standard architectural confidence. |
| **Mature** | Long-proven across many runs and contexts; changes are rare. High architectural confidence. |
| **Frozen** | Effectively immutable; change is prohibited except by major governance action. Maximum architectural confidence. |

### 11.1 Stability progression

```text
   Experimental ──► Stable ──► Mature ──► Frozen
   (low confidence)                       (maximum confidence)
```

Progression is one-directional under normal governance: confidence is *earned*
over time. A rule may be moved back toward Experimental only by an explicit
governance act (for example, if a defect in its definition is discovered).

### 11.2 Stability is not lifecycle

> **Principle**
> **Lifecycle answers "Where is the rule?" Stability answers "How much confidence
> does the architecture have in this rule?"** A rule can be `Implemented`
> (lifecycle) yet `Experimental` (stability) — live, but still earning trust. The
> two dimensions never collapse into one.

| Dimension | Question it answers | States |
| --------- | ------------------- | ------ |
| **Lifecycle** | Where is the rule in its life? | Draft · Approved · Implemented · Deprecated · Retired (§7) |
| **Stability** | How much confidence does architecture have in it? | Experimental · Stable · Mature · Frozen |

> **Note — two uses of "Experimental".** The *Experimental classification* (§10)
> describes a rule's **role** (research-only). The *Experimental stability* state
> describes the architecture's **confidence** in any rule, of any classification.
> A newly approved Core rule is Core in classification and Experimental in
> stability until it earns confidence. The words coincide; the dimensions do not.

---

## 12. Rule Status Matrix

A rule's full status is the combination of **three independent dimensions** —
Lifecycle (§7), Classification (§10), and Stability (§11). The matrix exists to
make their independence explicit: any value of one may combine with any value of
another.

| Lifecycle | Classification | Stability | Illustrates |
| --------- | -------------- | --------- | ----------- |
| Implemented | Core | Stable | A mainstream baseline rule in everyday use. |
| Implemented | Extended | Experimental | A live optional rule still earning architectural confidence. |
| Approved | Organization | Experimental | A customer-specific rule accepted into the catalog but not yet implemented or trusted. |

> **Architectural Decision**
> **The three dimensions must never be merged.** Each answers a different
> question: lifecycle says *where the rule is*, classification says *what role it
> plays*, stability says *how much it is trusted*. Merging them would make it
> impossible to express legitimate states such as an Implemented-but-Experimental
> Extended rule, and would couple decisions that must stay independent. The matrix
> is read as three orthogonal axes, never as a single grade.

---

## 13. Rule Profiles

A **Validation Profile** is a named selection of rules. Profiles let the platform
apply different breadth of validation to different contexts without rules knowing
anything about that context.

| Profile | Intent | Typical rule selection |
| ------- | ------ | ---------------------- |
| **Minimal** | The lightest viable gate. | Core rules only. |
| **Standard** | The default balanced gate. | Core + common Extended rules. |
| **Strict** | Maximum depth for high-stakes analysis. | Core + all Extended rules. |
| **Compliance** | Coverage tuned to regulatory obligations. | Core + Extended + Organization (compliance) rules. |
| **Enterprise** | Organization-wide policy enforcement. | Core + Extended + Organization rules. |

```text
   Response Validator ── selects ──► Validation Profile ── names ──► set of Rule IDs
                                                                         │
                                                                         ▼
                                                            rules execute (unaware of profile)
```

> **Principle**
> **Profiles select rules; rules never know profiles.** A rule validates its single
> concern identically regardless of which profile invoked it. The **Response
> Validator** chooses the profile; the rule remains context-free, which is what
> keeps it deterministic and independent (§16).

---

## 14. Severity Guidance

Each rule's finding carries a severity (Validation Canonical Models — severity
model). Severity expresses how much a finding threatens trustworthiness.

| Severity | Meaning | Typical rule examples |
| -------- | ------- | --------------------- |
| **INFO** | An observation that does not threaten trust. | A non-blocking advisory from an Extended rule. |
| **WARNING** | A concern worth review that does not invalidate the output. | A sparse but present section. |
| **ERROR** | A defect that makes the output untrustworthy for downstream use. | A missing required section (`SCHEMA-0001`); a requirement without evidence (`EVIDENCE-0001`). |
| **CRITICAL** | A defect that makes the output unsafe to process at all. | No response received (`TRANSPORT-0001`); response not well-formed (`SYNTAX-0001`). |

### 14.1 Worked examples

> **Worked example — severity by nature of defect**
> `TRANSPORT-0001` (no response) is `CRITICAL`: there is nothing to process.
> `SCHEMA-0001` (a required section missing) is `ERROR`: the output is
> well-formed but untrustworthy. `BUSINESS-0001` (fewer recommendations than the
> mandated minimum) is typically `WARNING`: the output is usable but should be
> reviewed. The severity follows the *nature of the defect*, not the layer it was
> found in.

### 14.2 Severity decision matrix

| If the finding… | Severity | Consequence (per the verdict model) |
| --------------- | -------- | ----------------------------------- |
| Records an observation only | INFO | Continue. |
| Flags a reviewable, non-invalidating concern | WARNING | Continue with warnings. |
| Makes the output untrustworthy | ERROR | Reject (FAILED). |
| Makes the output unsafe to process | CRITICAL | Block (BLOCKED). |

> **Principle**
> Severity is assigned by the **nature of the defect**, never by the layer that
> raised it. Two rules in different layers that both render output untrustworthy
> both carry `ERROR`. Consistent severity is what keeps the verdict deterministic.

---

## 15. Blocking Guidance

A rule's **blocking capability** states whether its finding may halt progression
through the pipeline.

| A rule **may** block when… | A rule **must never** block when… |
| -------------------------- | --------------------------------- |
| Its concern is foundational and a failure makes all later layers meaningless (Transport, Syntax, Schema, Structural). | Its concern is advisory or observational (INFO/WARNING findings). |
| Its finding is `CRITICAL` — the output is unsafe to process further. | Its finding is recoverable or downstream work can still proceed. |
| Continuing would cause later rules to produce only meaningless secondary findings. | Blocking would suppress other independent findings that should still be reported. |

> **Architectural Decision**
> Blocking is reserved for **foundational, progression-stopping** failures
> (consistent with Fail Fast, AI Response Validation Architecture §3.1). Semantic
> rules (Content, Evidence, Traceability, Reasoning, Business Rule) **record**
> their findings and let validation continue, so that one rule's finding never
> hides another's. A rule blocks only when continuing is genuinely meaningless or
> unsafe.

> **Principle**
> **A blocking decision is about the response, never about other rules.** A rule
> may block because the response cannot be meaningfully validated further — never
> to take priority over, or suppress, a sibling rule.

---

## 16. Rule Independence

> **This section is critical.** It is the property on which determinism, audit,
> and future parallelism all rest.

Every rule must exhibit all six properties simultaneously.

| Property | Meaning |
| -------- | ------- |
| **Deterministic** | Given the same response, the rule always produces the same finding(s). |
| **Stateless** | The rule holds no memory between evaluations; it depends only on the response before it. |
| **Idempotent** | Evaluating the rule twice on the same response yields the same result, with no cumulative effect. |
| **Independent** | The rule depends on no other rule's output or existence. |
| **Parallelizable** | Because it shares no state and observes no sibling, it may be evaluated concurrently with others. |
| **Non-mutating** | The rule reads the response; it never alters it (Preserve Original Response, AI Response Validation Architecture §3.3). |

### 16.1 Worked example

> **Worked example — order independence**
> Within the Evidence layer, `EVIDENCE-0001` (requirement evidence),
> `EVIDENCE-0002` (risk evidence), and `EVIDENCE-0003` (recommendation evidence)
> each read the same response and raise their own findings. Whether they run in
> the order 1→2→3, 3→2→1, or all at once, the resulting set of findings is
> identical. No rule changes the response, and no rule consults another's result.
> If a requirement lacks evidence, `EVIDENCE-0001` raises its finding regardless of
> what `EVIDENCE-0002` and `EVIDENCE-0003` do.

> **Architectural Decision**
> **Rule Independence is non-negotiable.** A rule that depends on execution order,
> shares mutable state, or modifies the response is non-conforming and must not be
> catalogued. Independence is what lets the framework reorder or parallelise rule
> evaluation in future without changing a single verdict.

---

## 17. Rule Dependencies

> **Architectural Decision**
> **A rule must never depend on another rule.** No rule may read another rule's
> finding, assume another rule ran, or assume another rule will run. The **only**
> dependency the platform recognises is the **validation layer ordering** —
> foundational layers are evaluated before semantic ones, and a foundational
> blocking failure may stop progression (§15). That ordering is a property of the
> *pipeline*, not a dependency between *rules*.

| Allowed | Forbidden |
| ------- | --------- |
| Relying on the pipeline's layer ordering (foundational before semantic). | One rule reading another rule's finding. |
| Each rule independently reading the response. | One rule assuming another rule has already validated something. |
| — | One rule enabling, disabling, or sequencing another rule. |

> **Principle**
> If a rule appears to need another rule's result, the concern has been split
> incorrectly — either it is one rule, or the dependency belongs to the pipeline's
> layer ordering, never to the rules themselves.

---

## 18. Rule Complexity

> **Principle**
> **Prefer many small rules over few complex rules.** A rule should be small enough
> that its single concern is obvious from its name and its finding is unambiguous.

**Why small rules win.**

- **Clarity of failure.** A small rule's finding names exactly one concern; a large
  rule's finding is ambiguous about which of its conditions failed.
- **Independent evolution.** Small rules change for one reason each; a complex rule
  couples many reasons to change.
- **Safer growth.** New concerns are added as new small rules, never by enlarging an
  existing one (§9.10).
- **Determinism and parallelism.** Small, single-concern rules are trivially
  independent and parallelizable (§16).

> **Architectural Decision**
> When a rule's responsibility can be described only with the word "and", it is too
> large and must be split. Catalog growth is achieved by **adding rules**, never by
> **growing rules**.

---

## 19. Rule Relationships

A rule is one input to a larger chain. It never reaches beyond producing findings;
everything downstream consumes, never alters, those findings.

```text
        ┌───────────────┐
        │  Rule × N     │   each validates one concern, independently
        └───────┬───────┘
                │ produces findings
                ▼
        ┌───────────────────────┐
        │  Validation Pipeline   │   executes rules in layer order; collects findings
        └───────────┬───────────┘
                    │ assembles
                    ▼
        ┌───────────────────────┐
        │   Validation Result    │   the single, immutable aggregate output
        └───────────┬───────────┘
                    │ returned to
                    ▼
        ┌───────────────────────┐
        │   Response Validator   │   selects the profile; consumes the result
        └───────────┬───────────┘
                    │ gates
                    ▼
        ┌───────────────────────┐
        │  Downstream Platform   │   consumes only validated output
        └───────────────────────┘
```

| Relationship | Meaning |
| ------------ | ------- |
| **Rule → Pipeline** | A rule contributes findings; the pipeline orders and collects them. The rule knows nothing of the pipeline. |
| **Pipeline → Validation Result** | The pipeline assembles findings into the single canonical result. |
| **Validation Result → Response Validator** | The validator selects the profile (§13) and consumes the result. |
| **Response Validator → Downstream Platform** | Only validated output passes the gate to downstream engineering. |

> **Principle**
> A rule's responsibility ends at producing findings. It does not decide the
> verdict, choose a profile, or know any downstream consumer. This one-directional
> flow is what keeps rules independent and the subsystem governable.

### 19.1 Where this catalog sits among the architecture documents

This catalog is one link in the platform's governing chain. Each document
upstream constrains it; each capability downstream consumes the rules it defines.

```text
   AI Reasoning Contract            (how the AI must reason)
            │ governs the meaning of trustworthy output
            ▼
   Requirement Analysis Service     (produces the analysed response)
            │ emits the AnalysisResult (LLMResponse) to be validated
            ▼
   Response Normalization Contract  (how text becomes canonical structure)
            │ governs the Response Normalization Layer → ParsedResponse (ONCE)
            ▼
   Response Validation Architecture (why & whether output is trustworthy)
            │ defines the validation philosophy & verdict model
            ▼
   Validation Canonical Models      (the validation information model)
            │ defines ParsedResponse + issues, results, severity, verdicts
            ▼
   Validation Rule Catalog          ◄── THIS DOCUMENT (the governed set of rules)
            │ defines every rule's identity, layer, severity, blocking
            ▼
   Validation Framework             (registry · pipeline · rule contract)
            │ executes the catalogued rules
            ▼
   Validation Rules                 (conforming implementations of this catalog)
            │ produce findings
            ▼
   Response Validator               (selects a profile; runs the framework)
            │ assembles & gates
            ▼
   Validation Result                (the single validated output)
            │ consumed only when the verdict permits
            ▼
   CP1                              (downstream quality gate)
            │ operates on validated output
            ▼
   Feature Generation               (downstream engineering capability)
```

| Relationship | Meaning |
| ------------ | ------- |
| **AI Reasoning Contract → Requirement Analysis Service** | The contract defines how the AI must reason; the service produces output that should embody it. |
| **Requirement Analysis Service → Response Normalization Contract** | The service emits the `LLMResponse`; the Response Normalization Layer turns it into the canonical `ParsedResponse` once, before validation. |
| **Response Normalization Contract → Response Validation Architecture** | Normalization produces the structure the validation philosophy operates on; no validation layer normalizes. |
| **Response Validation Architecture → Validation Canonical Models** | The philosophy defines verdicts and severity; the canonical models give them a stable information shape — including the `ParsedResponse` the rules read. |
| **Validation Canonical Models → Validation Rule Catalog** | The models define what a finding *is*; this catalog defines which findings *exist* and what each means. |
| **Validation Rule Catalog → Validation Framework** | The catalog defines the rules; the framework catalogues and executes them. |
| **Validation Framework → Validation Rules** | The framework runs conforming rule implementations governed by this catalog. |
| **Validation Rules → Response Validator** | Rules produce findings; the validator selects the profile and drives the framework. |
| **Response Validator → Validation Result** | The validator yields the single, immutable validated output. |
| **Validation Result → CP1 → Feature Generation** | Only validated output flows to the downstream quality gate and engineering capabilities. |

> **Principle**
> This catalog **depends upward** on the reasoning contract, the validation
> architecture, and the canonical models, and is **consumed downward** by the
> framework, the validator, and every downstream capability. It changes the
> meaning of validation only through its own governed evolution — never as a side
> effect of a downstream consumer's needs.

---

## 20. Rule Versioning

Four independent versions govern a rule and its context. Conflating them would
make it impossible to tell what changed. (A fifth version — the **Rule Catalog
Version**, §21 — governs the catalog document as a whole.)

| Version | Governs | Changes when… |
| ------- | ------- | ------------- |
| **Rule Version** | One rule's own definition. | This rule's concern definition changes. |
| **Validation Contract Version** | The validation *semantics* of the whole subsystem (categories, severity model, pipeline, result/issue models). | The meaning of validation changes (AI Response Validation Architecture §13). |
| **Validator Version** | The validator *implementation* as a whole. | The implementation changes with no change in meaning. |
| **Framework Version** | The Response Validation Framework component versions. | The framework's structural components change. |

### 20.1 Compatibility matrix

| Change | Advances |
| ------ | -------- |
| A rule's concern definition is refined | Rule Version |
| A rule's severity or blocking capability changes | Rule Version **and** Validation Contract Version (semantics change) |
| A new rule is added to the catalog | Validation Contract Version (a new category of finding becomes possible) |
| A rule's implementation is optimised, with identical semantics | Validator Version only |
| The framework's components change, with identical semantics | Framework Version only |

> **Architectural Decision**
> **The four versions are independent.** A rule may evolve (Rule Version) without
> the validator implementation changing (Validator Version); the implementation may
> improve without any rule changing. Any change to a rule's *meaning* — severity,
> blocking, or definition — also advances the **Validation Contract Version** and
> requires governance (§22).

---

## 21. Rule Catalog Version

The Validation Rule Catalog — this document, taken as a whole — is **independently
versioned**. The Rule Catalog Version is distinct from every version in §20: it
tracks the evolution of the *governed set of rules and their governance*, not the
definition of any single rule, the semantics of validation, the validator
implementation, or the framework.

### 21.1 Five versions, clearly separated

| Version | Governs | Scope |
| ------- | ------- | ----- |
| **Rule Version** | One rule's own definition (§20). | A single rule. |
| **Validation Contract Version** | The validation semantics of the subsystem (§20). | The meaning of validation. |
| **Validator Version** | The validator implementation (§20). | The running implementation. |
| **Framework Version** | The framework's structural components (§20). | The framework structure. |
| **Rule Catalog Version** | This catalog document as a whole. | The governed set of rules and their governance. |

> **Architectural Decision**
> **The catalog requires its own version because the catalog can change without
> any rule changing — and a rule can change without the catalog's structure
> changing.** Adding new rules, deprecating rules, or clarifying governance are
> changes to the *catalog*, recorded by the Rule Catalog Version, even when no
> individual Rule Version, Validator Version, or Framework Version moves. Without
> a catalog version, the platform could not state *which set of rules* governed a
> given period.

### 21.2 Worked example

> **Worked example — Catalog 1.2**
> The catalog advances from `1.1` to `1.2`. The change: **five new rules were
> added** across the Extended range. No existing rule changed its definition. The
> validator implementation is untouched. The framework is untouched. Every
> existing Rule Version is unchanged. **Only the catalog advanced** — recorded as
> Catalog `1.2`. (Because new rules make new finding categories possible, the
> Validation Contract Version also advances per §20.1; the Rule Catalog Version is
> what records *that the catalog itself grew*.)

### 21.3 Semantic versioning guidance

The Rule Catalog Version follows a three-part `MAJOR.MINOR.PATCH` discipline.

| Increment | When it applies | Examples |
| --------- | --------------- | -------- |
| **Major** | A breaking governance change. | Reallocating reserved number ranges; changing an identity or governance rule. |
| **Minor** | New rules (or new profiles) added; rules deprecated. | Adding five Extended rules; deprecating a rule; adding the Compliance profile. |
| **Patch** | Editorial clarification only. | Rewording an example or a definition with no change to identity, allocation, severity, or governance. |

### 21.4 Compatibility table

| Change to the catalog | Catalog Version increment | Does it break existing consumers? |
| --------------------- | ------------------------- | --------------------------------- |
| Editorial clarification only | Patch | No. |
| New rule(s) added | Minor | No — additive; existing rules unaffected. |
| New profile added | Minor | No — additive; existing profiles unaffected. |
| Rule deprecated (identity retained) | Minor | No — the rule is still honoured until retired. |
| Number-range reallocation or an identity/governance rule change | Major | Yes — a governing contract changed. |

---

## 22. Rule Governance

> **Architectural Decision**
> **Only architecture approval may introduce a new Rule ID.** A rule enters the
> catalog through governance — never by an engineer minting an identifier during
> implementation. Three rules are absolute:
>
> - **New Rule IDs require architectural approval** (an approved ADR).
> - **Rule IDs are never reused.** An identifier maps to one concern forever.
> - **Deprecated and retired IDs are never reassigned.** A retired ID stays retired
>   so historical validation records remain interpretable.

| Governance act | Authority required |
| -------------- | ------------------ |
| Introduce a new Rule ID | Architecture approval (ADR). |
| Change a rule's severity, blocking, or concern | Architecture approval (advances Validation Contract Version, §20). |
| Rename a rule (Name only) | Permitted without a new ID; identity is unchanged (§4.3). |
| Deprecate or retire a rule | Architecture approval; the ID is frozen forever (§7). |
| Optimise a rule's implementation | No catalog change; advances Validator Version only (§20). |

> **Principle**
> Identity is sacred. The catalog may grow without limit, but every identity in it
> is permanent, unique, and approved. Ungoverned identity is the one thing the
> catalog can never allow.

### 22.1 Worked governance examples

Each governance act touches a different, well-defined set of versions. The table
below shows, for five representative acts, whether the Rule ID changes and which
of the five versions advances. ("Advances" = the version increments; "—" = no
change.)

| Governance act | Rule ID changes? | Rule Version | Rule Catalog Version | Validation Contract Version | Validator Version | Framework Version |
| -------------- | ---------------- | ------------ | -------------------- | --------------------------- | ----------------- | ----------------- |
| **1. Add a new rule** | New ID minted (existing IDs unchanged) | New rule begins at its own `1.0` | Minor | Advances (new finding category possible) | — (until implemented) | — |
| **2. Deprecate a rule** | No (ID frozen) | — | Minor | — (still honoured) | — | — |
| **3. Rename a rule** | No (identity unchanged) | — | Patch | — | — | — |
| **4. Change a rule's severity** | No | Advances | Minor | Advances (severity is semantics) | Advances (to reflect new severity) | — |
| **5. Add a new profile** | No (profiles carry no Rule ID) | — | Minor | — (selects existing rules) | Advances (validator gains the selection) | — |

> **Principle**
> Every governance act has a **predictable, bounded version footprint.** Renaming
> never touches semantics; adding a rule never touches existing identities;
> changing severity always advances the Validation Contract Version. Predictable
> footprints are what make catalog evolution auditable.

---

## 23. Future Evolution

The catalog is designed to be **extended, never replaced**. The following are
reserved directions — anticipated, permitted, and governed in advance.

| Reserved capability | Intent | Constraint under this catalog |
| ------------------- | ------ | ----------------------------- |
| **Composite Rules** | Express a higher-order concern built from several findings. | Each underlying concern remains its own single-responsibility rule; composition never merges concerns. |
| **Parameterized Rules** | Allow a rule's thresholds to be configured. | Parameters tune a single concern; they never let one rule cover several concerns. |
| **Evidence Scoring Rules** | Assess evidence *strength*, not merely presence. | A future extension of the Evidence layer; bound by determinism and independence. |
| **Business Profiles** | Predefined Business Rule selections per domain. | A profile (§13) selecting rules; rules stay profile-unaware. |
| **Organization-specific Rules** | Customer-defined policy rules. | The Organization classification (§10), allocated from the Organization range (§4.4); governed and identity-stable like any rule. |
| **AI-assisted Rules** | Rules whose evaluation is itself model-assisted. | Must remain deterministic in verdict, independent, and non-mutating; governed identity like any rule. |

> **Architectural Decision**
> **Future capabilities extend the catalog; they never replace it.** Every new
> capability is added as governed rules or profiles bound by the same identity,
> number allocation, independence, severity, blocking, versioning, and governance
> contracts defined here. A capability that recycles an identity, couples rules,
> introduces non-determinism, or bypasses governance is non-conforming.

---

## 24. Architecture Principles Summary

The philosophy of the validation rule catalog, distilled:

| # | Principle | One-line meaning |
| - | --------- | ---------------- |
| 1 | **Rules are governed, not invented.** | A rule exists because the catalog defines it. |
| 2 | **One rule, one responsibility.** | A rule validates exactly one concern. |
| 3 | **Identity is permanent.** | Rule IDs never change and are never reused. |
| 4 | **Numbers are allocated by discipline.** | Reserved ranges per classification; gaps are intentional. |
| 5 | **Names describe the concern.** | Descriptive names ending in *Rule*; never opaque labels. |
| 6 | **One concern, one layer.** | Each rule belongs to exactly one validation layer. |
| 7 | **Core rules are always on.** | The mandatory baseline is never disabled. |
| 8 | **Stability signals confidence.** | Independent of lifecycle; earned over time. |
| 9 | **Status is three independent axes.** | Lifecycle, classification, and stability never merge. |
| 10 | **Profiles select; rules don't know.** | The validator chooses profiles; rules stay context-free. |
| 11 | **Severity follows the defect.** | Not the layer; consistent severity keeps verdicts deterministic. |
| 12 | **Block only foundational failures.** | Semantic rules record and continue. |
| 13 | **Rules are independent.** | Deterministic, stateless, idempotent, parallelizable, non-mutating. |
| 14 | **No rule depends on another rule.** | The only ordering is the pipeline's layer order. |
| 15 | **Prefer many small rules.** | Split on "and"; grow by adding rules. |
| 16 | **Five versions, independent.** | Rule, Contract, Validator, Framework, Catalog. |
| 17 | **Only governance mints identity.** | New IDs require approval; retired IDs stay retired. |
| 18 | **Extend, never replace.** | Future capabilities grow the catalog within these contracts. |

---

> **Architectural Decision — Architecture Freeze**
> With this document, the following become **frozen architectural contracts** for
> the validation rule subsystem:
>
> - **Rule Identity** (§4) — the `<LAYER>-NNNN` standard and permanent, unique IDs.
> - **Rule Number Allocation** (§4.4) — reserved ranges per classification; numbers
>   never reused; gaps intentional.
> - **Layer Ownership** (§8) — one concern, one layer.
> - **Rule Metadata** (§6) — the mandatory metadata record.
> - **Rule Lifecycle** (§7) — Draft → Approved → Implemented → Deprecated → Retired.
> - **Rule Classification** (§10) — Core, Extended, Organization, Experimental.
> - **Rule Stability** (§11) — Experimental → Stable → Mature → Frozen, independent
>   of lifecycle.
> - **Rule Status Matrix** (§12) — lifecycle, classification, and stability as three
>   independent axes that never merge.
> - **Severity Guidance** (§14) — severity by nature of defect.
> - **Blocking Guidance** (§15) — blocking reserved for foundational failures.
> - **Rule Independence** (§16) — deterministic, stateless, idempotent, independent,
>   parallelizable, non-mutating.
> - **Rule Versioning** (§20) — four independent versions.
> - **Rule Catalog Version** (§21) — the catalog independently versioned, with
>   MAJOR/MINOR/PATCH discipline.
> - **Governance Examples** (§22.1) — the bounded version footprint of each
>   governance act.
> - **Rule Governance** (§22) — only approval mints identity; IDs are never reused.
>
> **Implementation may evolve freely** beneath these contracts. **The architecture
> may evolve only through an approved Architecture Decision Record (ADR).** A
> change that violates any frozen contract above is non-conforming by definition.

> **Definition of Done**
> This document is the governing specification — the single source of truth — for
> every validation rule that will ever exist in the Response Validation Framework.
> It defines rule identity, number allocation, layer ownership, metadata,
> lifecycle, classification, stability, the status matrix, profiles, severity,
> blocking, independence, dependencies, relationships, versioning, the catalog
> version, governance, and evolution. It is implementation-independent and remains
> valid even if the platform is reimplemented on an entirely different technology
> stack or driven by an entirely different AI provider.

---

## Appendix A — Glossary

| Term | Definition |
| ---- | ---------- |
| **Validation rule** | A single, atomic check that validates exactly one concern about a response (§3). |
| **Rule ID** | The stable, immutable identifier of a rule, in the form `<LAYER>-NNNN` (§4). |
| **Rule Name** | The human-readable, concern-describing name of a rule; may evolve (§5). |
| **Rule Number Allocation** | The reserved `NNNN` ranges, assigned by classification; numbers are never reused and gaps are intentional (§4.4). |
| **Layer** | One of the nine ordered validation concerns a rule belongs to (§8). |
| **Classification** | A rule's role: Core, Extended, Organization, or Experimental (§10). |
| **Rule Stability** | The architecture's confidence in a rule: Experimental, Stable, Mature, or Frozen; independent of lifecycle (§11). |
| **Status Matrix** | The three independent status axes — lifecycle, classification, stability — that together describe a rule's full status (§12). |
| **Profile** | A named selection of rules chosen by the Response Validator (§13). |
| **Severity** | How much a finding threatens trustworthiness: INFO, WARNING, ERROR, CRITICAL (§14). |
| **Blocking** | Whether a finding halts pipeline progression (§15). |
| **Rule Independence** | The property set making rules deterministic, stateless, idempotent, independent, parallelizable, and non-mutating (§16). |
| **Lifecycle status** | A rule's state: Draft, Approved, Implemented, Deprecated, or Retired (§7). |
| **Rule Catalog Version** | The independent version of this catalog as a whole, governing the set of rules and their governance (§21). |
| **Catalog** | The complete governed set of validation rules defined by this document. |
| **ParsedResponse** | The canonical, provider- and format-independent normalized structure of the response; a Shared Platform Artifact created once by the Response Normalization Layer and read by every layer from Syntax onward (§8.2; Response Normalization Contract). |
| **Response Normalization Layer** | The permanent subsystem that creates the `ParsedResponse` once, before validation; no validation rule parses or normalizes (§8.2; Response Normalization Contract). |
| **Normalization Outcome** | A normalized fact — `NORMALIZED` / `MALFORMED` — the Syntax layer judges; never itself a verdict (Response Normalization Contract §9). |
| **Normalization Observation** | A recorded, un-judged fact on the `ParsedResponse` (e.g. a duplicate identifier); never a severity, verdict, or `ValidationIssue` until a rule decides to raise one (Response Normalization Contract §8, §10). |
| **Shared Platform Artifact** | An artifact produced once and shared read-only across the platform; `ParsedResponse` is one — validation is its first consumer, not its owner (Response Normalization Contract §7). |

## Appendix B — Conformance Checklist

A validation rule conforms to this catalog only if every box can be checked:

- [ ] Has exactly **one responsibility** (one concern, no "and").
- [ ] Is assigned to the **correct layer** (one concern, one layer).
- [ ] Carries a **stable Rule ID** in `<LAYER>-NNNN` form that never changes.
- [ ] Uses the **correct number allocation** — the reserved range for its classification, with no reuse (§4.4).
- [ ] Has a **descriptive name** ending in *Rule* (never opaque or sequential).
- [ ] Declares its **classification** (Core, Extended, Organization, or Experimental).
- [ ] Declares its **stability** (Experimental, Stable, Mature, or Frozen).
- [ ] Has **complete, documented metadata** (every field of §6 defined).
- [ ] Carries an **architecture reference** to its governing section.
- [ ] Includes a **worked example** (a passing and a failing case).
- [ ] Has its **versions defined** (Rule and Validation Contract) under the correct **Rule Catalog Version**.
- [ ] Has **no side effects** — it never mutates the response or shared state.
- [ ] Is **deterministic** — same response, same finding, every time.
- [ ] Is **independent** — depends on no other rule, only the pipeline's layer order.
- [ ] Is **parallelizable** — safe to evaluate concurrently with sibling rules.
- [ ] Is **non-mutating** — observes the response, never edits it.
- [ ] Has **no duplicate responsibility** — no other rule owns the same concern.
- [ ] **Fits the catalog** — introduced through governance with an approved, unique ID.
