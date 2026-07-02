# ADR 0006 — Remaining Validation Capability Status

- **Status:** Accepted
- **Date:** 2026-07-02

## Context

The Transport, Syntax, and Schema validation layers are implemented (Transport +
Syntax complete; Schema = `SCHEMA-0001`, `SCHEMA-0002`, `SCHEMA-0004` implemented,
`SCHEMA-0003` Reserved · Deferred by **ADR-0005**). Planning the remaining layers —
**Structural, Content, Evidence, Traceability, Reasoning, Business Rule** — surfaced a
governance question: are they ready to catalogue-and-implement, or are some concerns
un-implementable against the response the platform actually produces?

A pre-work design review established that **most remaining-layer concerns cannot bind
to any governed response field today**, because the governed response schema is flat
and its collection elements are bare strings:

```json
{ "summary": "", "functional_requirements": [], "security_requirements": [],
  "quality_requirements": [], "risks": [], "recommendations": [] }
```

- `requirement_intelligence/prompts/prompt_constants.py` — `JSON_RESPONSE_REQUIREMENTS`
  declares exactly these six top-level fields; `OUTPUT_REQUIREMENTS` states *"Every
  array element must be a string statement."* Each requirement/risk/recommendation is a
  **single opaque string**, not a structured item.
- `requirement_intelligence/models/parsed_response.py` — `normalized_structure` is
  `dict[str, Any] | None`: the parsed JSON, carrying exactly those keys and their
  string-array values. No enrichment is added by normalization.
- There is **no** governed per-item *description*, *confidence*, *evidence reference*,
  or *source/trace linkage*, and **no** governed Business coverage policy or minimum
  threshold anywhere in the frozen documents.

This is the same class of gap that **ADR-0005** froze for `SCHEMA-0003`: *a rule's
concern requires a governed field to bind to; a rule whose governed concern does not
yet exist is **Reserved · Deferred**, never invented or activated.* Cataloguing the
remaining rules as implementable would require **inventing governed response fields and
policies** — a change to the governed response shape (a canonical/model enrichment) —
which is prohibited and would contradict ADR-0005.

**The STOP condition therefore remains valid**: the originally envisioned "freeze every
remaining rule as implementable" ADR cannot be written without inventing architecture.
This ADR instead **describes the current state accurately**: it freezes the remaining
layers' ownership boundaries (already established by the Catalog and ADR-0004), and
classifies every remaining catalogued rule by whether the **current** governed response
schema provides sufficient information to implement it. It invents nothing, designs no
schema, proposes no field names, and modifies no frozen architecture. It is
**descriptive, not prescriptive**.

## Decision

### A. Remaining-layer ownership boundaries (documented, not redefined)

The boundaries below are **restated** from the frozen Validation Rule Catalog (§8.4–§8.9),
**ADR-0004** (existence → Schema; composition/hierarchy/organization → Structural), and
the shared validation-rule input discipline frozen by the Schema Validation
Implementation Contract §4–§5 (which every layer from Schema onward follows). This ADR
**changes none of them**.

**Shared input/output discipline (all six layers).** Every remaining-layer rule, like
every Schema rule, reads only its functional input and produces only judgements:

- **Reads:** `ValidationInput → normalization_result → parsed_response →
  normalized_structure` (the sole functional input); `analysis_result.execution_id` for
  issue `correlation_id` provenance only.
- **Never reads:** the Normalization Outcome, the Normalization Observations,
  `generated_text`, provider/model metadata, `ParsedResponse.source_reference`,
  `ParsedResponse.metadata`, or another rule's findings.
- **Produces:** `list[ValidationIssue]` (judgements) — the Catalog-assigned severity and
  blocking per rule.
- **Never produces:** facts, verdicts, a normalized structure, or any repaired/
  normalized/mutated data. No layer normalizes, repairs, or mutates.

| Layer | Owns | Never owns |
| ----- | ---- | ---------- |
| **Structural** (§8.4) | Composition, hierarchy, organization of parts **that already exist** — nesting, relationships, arrangement. | Existence (→ Schema, ADR-0004); value meaning/quality (→ Content); grounding (→ Evidence); coherence (→ Reasoning); counts/coverage (→ Business). |
| **Content** (§8.5) | Field-level value presence/validity of items that exist — emptiness, duplication, description presence, value range. | Composition (→ Structural); grounding (→ Evidence); traceability (→ Traceability); coherence (→ Reasoning); policy (→ Business). |
| **Evidence** (§8.6) | Whether conclusions carry the **required evidence references**. | Whether evidence links **resolve** (→ Traceability); whether a conclusion is **coherent** (→ Reasoning). |
| **Traceability** (§8.7) | Whether each element carries **resolvable links** to its source/context (orphan detection). | Whether the **evidence exists** (→ Evidence); whether content is **coherent** (→ Reasoning). |
| **Reasoning** (§8.8) | Internal coherence — contradictions, duplicated conclusions, circular logic. | Declared platform **policy** (→ Business); real-world correctness (outside validation). |
| **Business Rule** (§8.9) | Declared platform-level **completeness/coverage/cardinality policies**. | Real-world correctness, approval, prioritisation (outside the validation boundary). |

> This ADR **documents** these boundaries; it does not redefine any ownership. Each
> concern has exactly one owning layer (Catalog §8; ADR-0004).

### B. Capability classification of every remaining catalogued rule

Each remaining catalogued rule is classified as exactly one of **Implemented**,
**Implementable** (the current governed response schema provides sufficient information),
or **Reserved · Deferred** (it cannot bind to a governed field/policy that exists today).
Classification is based **only** on information sufficiency, never on inventing a field.

| Layer | Rule (Catalog) | Concern | Status | Blocking gap |
| ----- | -------------- | ------- | ------ | ------------ |
| **Structural** (§9.4) | `STRUCTURE-0001…0004` | *(existence)* | **Deprecated** (ADR-0004) | Superseded by Schema; IDs frozen, never reused. |
| **Structural** | *(no active composition rule)* | composition/hierarchy/organization | **Not catalogued** | The governed structure is **flat** (no nesting/containers); needs both a cataloguing ADR *and* a response with composable structure. |
| **Content** (§9.5) | `CONTENT-0001` EmptyRequirement | A requirement is not empty | **Implementable** | — (a requirement is a governed string). |
| **Content** | `CONTENT-0002` DuplicateRequirement | Requirements are not duplicated | **Implementable** | — (duplicate governed strings are observable). |
| **Content** | `CONTENT-0003` MissingDescription | A requirement carries a description | **Reserved · Deferred** | No governed per-item description distinct from the statement. |
| **Content** | `CONTENT-0004` InvalidConfidence | A confidence value is within range | **Reserved · Deferred** | No governed per-item confidence value (cf. ADR-0005). |
| **Evidence** (§9.6) | `EVIDENCE-0001` RequirementEvidence | A requirement carries required evidence | **Reserved · Deferred** | No governed per-item evidence reference. |
| **Evidence** | `EVIDENCE-0002` RiskEvidence | A risk carries required evidence | **Reserved · Deferred** | No governed per-item evidence reference. |
| **Evidence** | `EVIDENCE-0003` RecommendationEvidence | A recommendation carries required evidence | **Reserved · Deferred** | No governed per-item evidence reference. |
| **Traceability** (§9.7) | `TRACEABILITY-0001` RequirementTrace | A requirement is traceable to its source | **Reserved · Deferred** | No governed per-item source/trace linkage. |
| **Traceability** | `TRACEABILITY-0002` RiskTrace | A risk is traceable to its source | **Reserved · Deferred** | No governed per-item source/trace linkage. |
| **Traceability** | `TRACEABILITY-0003` RecommendationTrace | A recommendation is traceable to its source | **Reserved · Deferred** | No governed per-item source/trace linkage. |
| **Reasoning** (§9.8) | `REASONING-0001` ContradictoryRequirement | No two requirements contradict | **Implementable** | — (operates on governed requirement strings; a semantic-judgement mechanism, but the input is present). |
| **Reasoning** | `REASONING-0002` DuplicateRecommendation | No recommendation is duplicated | **Implementable** | — (duplicate governed strings are observable). |
| **Reasoning** | `REASONING-0003` CircularLogic | No chain of reasoning is circular | **Implementable** | — (operates on governed statements; semantic mechanism, input present). |
| **Business** (§9.9) | `BUSINESS-0001` MinimumRecommendations | A minimum number of recommendations is present | **Reserved · Deferred** | The count is observable, but the **minimum threshold policy is not governed**. |
| **Business** | `BUSINESS-0002` RiskCoverage | Risk coverage meets declared policy | **Reserved · Deferred** | No governed coverage policy. |
| **Business** | `BUSINESS-0003` RequirementCoverage | Requirement coverage meets declared policy | **Reserved · Deferred** | No governed coverage policy. |
| **Business** | `BUSINESS-0004` CrossDomainCompleteness | Cross-domain completeness is satisfied | **Reserved · Deferred** | No governed completeness policy. |

> **Classification summary.** Implementable now: `CONTENT-0001`, `CONTENT-0002`,
> `REASONING-0001`, `REASONING-0002`, `REASONING-0003`. Reserved · Deferred:
> `CONTENT-0003`, `CONTENT-0004`, all Evidence, all Traceability, all Business. Structural
> has no active rules and none can yet be catalogued. Every Reserved · Deferred identity
> is frozen and never reused (Catalog §4.3); deferral changes no identity, severity, or
> blocking.

> **Note on the Implementable Reasoning rules.** `REASONING-0001` and `REASONING-0003`
> are semantic-judgement rules: their *governed input* (the requirement/statement
> strings) exists, so they are not information-blocked, but their *mechanism* is
> non-trivial. Information sufficiency — not mechanism difficulty — is the classification
> criterion here; a hard-to-build rule is still Implementable if its governed input
> exists.

### C. Deferred capability prerequisites

For each Reserved · Deferred rule, the missing **governed capability** is identified
below. This ADR **does not design** that capability, **does not create** a canonical
model, and **does not propose field names** — it only names the missing information.

| Deferred rule(s) | Why it cannot be implemented today | Missing governed information | Enabling future capability (design out of scope) |
| ---------------- | ---------------------------------- | ---------------------------- | ------------------------------------------------ |
| `CONTENT-0003` MissingDescription | Each requirement is a single opaque string; there is no descriptive component to check for. | Per-requirement descriptive content distinct from the statement itself. | A governed decision to represent requirements as **structured items carrying a description component**. |
| `CONTENT-0004` InvalidConfidence | No confidence value is emitted for any item. | A governed per-item confidence value with a permitted range. | A governed decision to represent **per-item confidence** (this also unblocks `SCHEMA-0003`; see ADR-0005). |
| `EVIDENCE-0001…0003` | Items are bare strings; no evidence reference is attached. | A governed per-item **evidence reference**. | A governed decision to **attach evidence references** to requirements/risks/recommendations. |
| `TRACEABILITY-0001…0003` | Items are bare strings; no source/context linkage is attached. | A governed per-item **source/trace linkage** (with resolvable identifiers). | A governed decision to **attach source/trace links** to items. |
| `BUSINESS-0001` MinimumRecommendations | The recommendation count is observable, but no minimum is declared. | A governed **minimum-count policy**. | A governed decision that **declares completeness thresholds** as platform policy. |
| `BUSINESS-0002…0004` Coverage/Completeness | No coverage or completeness policy is declared to measure against. | Governed **coverage/completeness policies**. | A governed decision that **declares coverage/completeness policy** as platform policy. |
| Structural composition rules | The governed structure is flat; there is no nesting/container hierarchy to compose or organize. | A governed **response with composable/nested structure**, plus a cataloguing ADR that mints the concrete `STRUCTURE-00NN` composition rules. | A governed decision to **represent nested/organized response structure**, followed by a Structural cataloguing ADR. |

> **A single governed decision unblocks most of the layer.** Representing each
> requirement/risk/recommendation as a **structured item** (rather than an opaque string)
> is the common prerequisite behind `CONTENT-0003/0004`, all Evidence, and all
> Traceability rules — and, indirectly, meaningful Structural composition. That decision
> is a **future ADR** (with the Prompt Framework, the AI Reasoning Contract, and the Rule
> Catalog aligned); it is deliberately **not made here**.

### D. Structural layer — special case

Structural is boundary-frozen (composition/hierarchy/organization; ADR-0004) but has
**zero active catalogued rules** — `STRUCTURE-0001…0004` are Deprecated. Unlike the other
layers, Structural has no catalogued rules to classify: concrete composition rules cannot
even be catalogued today because the governed response is flat (nothing to compose). Its
concrete rules therefore await **two** prerequisites: a governed response with composable
structure, **and** the cataloguing ADR that ADR-0004 §4 already reserves for them.

## Architecture verification

- **No duplicated ownership.** Each remaining concern has exactly one owning layer
  (§A, from Catalog §8 + ADR-0004): existence → Schema; composition → Structural; value
  quality → Content; grounding → Evidence; link resolution → Traceability; coherence →
  Reasoning; policy → Business. Verified pairwise; no concern is owned twice.
- **No ownership gaps.** Every layer in the frozen pipeline order retains its position and
  owned concern family; deferral does not remove ownership, it records that some owned
  concerns have no governed field to bind to yet.
- **No dependency cycles.** The pipeline order Transport → Syntax → Schema → Structural →
  Content → Evidence → Traceability → Reasoning → Business is forward-only (Catalog §8);
  no rule reads another rule's findings (Catalog §16, §17). This ADR adds no dependency.
- **No conflict with ADR-0003.** Rules still consume the `ValidationInput`; the input
  contract is unchanged.
- **No conflict with ADR-0004.** Existence remains Schema's; Structural remains
  composition/hierarchy/organization; the Structural existence rules remain Deprecated.
- **No conflict with ADR-0005.** This ADR **extends** ADR-0005's deferral principle from
  `SCHEMA-0003` to every other rule that lacks a governed concern, using the identical
  Reserved · Deferred treatment. It contradicts nothing in ADR-0005.

## Consequences

- ✅ Every remaining layer has a **documented, frozen ownership boundary** (§A) and every
  remaining catalogued rule has a **clear implementation status** (§B).
- ✅ Every Reserved · Deferred capability has an **explicitly documented prerequisite**
  (§C) — without inventing schema, models, or field names.
- ✅ The next actionable implementation work is unambiguous: the **Implementable** rules
  (`CONTENT-0001`, `CONTENT-0002`, `REASONING-0001/0002/0003`), each realizable under the
  existing contracts against the current governed schema.
- ✅ The true prerequisite for the deferred capabilities is named: a **future
  governed-schema-enrichment ADR** (structured response items; declared Business
  policies), plus a Structural cataloguing ADR — neither made here.
- ⚠️ **Version impact:** this ADR is **descriptive**. It changes no rule concern,
  severity, blocking, identity, number, canonical model, or contract — so it forces **no**
  version bump (Rule Catalog Version, Validation Contract Version, Validator Version, or
  any Rule Version are all unchanged; Catalog §20). A future enrichment ADR will advance
  the appropriate versions when it activates deferred rules.
- ⚠️ **Governance alignment applied** (no implementation, no Rule Catalog, no frozen
  contract changes; see "Governance alignment").

## Alternatives considered

- **A — Catalogue and freeze every remaining rule as implementable** (the originally
  envisioned "Remaining Validation Layer Catalog"). **Rejected:** it requires inventing
  governed per-item fields (description/confidence/evidence/source) and Business policies
  that do not exist — implementation driving architecture, and a contradiction of
  ADR-0005's frozen invariants. This is the STOP condition that produced this ADR.
- **B — Invent the missing response fields/policies inside this ADR to make the rules
  bindable.** **Rejected:** prohibited (no new governed response fields, no schema
  enrichment, no new canonical models); a governed response shape change is a separate,
  first-class architecture decision requiring its own ADR with the Prompt Framework and
  Reasoning Contract aligned.
- **C — Chosen: a descriptive status ADR** that freezes the remaining boundaries and
  classifies each rule (Implemented / Implementable / Reserved · Deferred) with documented
  prerequisites, inventing nothing. **Accepted:** it records reality accurately, keeps
  every concern to one owner, extends the ADR-0005 precedent consistently, and makes the
  deferred capabilities' prerequisites explicit for a future decision.

## Governance alignment

As a consequence of this ADR, the following **governance** documents are updated to record
the classification (no code, no Rule Catalog, no frozen-contract, and no implementation
changes):

- `docs/governance/architecture-freeze-index.md` — §6 Relationship to ADRs records
  ADR-0006; the Validation Rule Catalog artifact row references it.
- `docs/governance/platform-capability-matrix.md` — CAP-045…050 notes record the
  per-layer Implementable / Reserved · Deferred classification; deferred capabilities are
  **not** marked complete.
- `docs/governance/architecture-coverage-dashboard.md` — readiness notes record the
  classification and the shared schema-enrichment prerequisite (no coverage checkmark
  changes).

## Scope note

This ADR is **documentation and governance only**. It does **not** invent governed
response fields, enrich the response schema, create or modify any canonical model
(`ValidationInput`, `ParsedResponse`, `NormalizationResult`), modify the Rule Catalog or
any frozen contract, implement any validation rule, or change any code. It **documents**
the remaining layers' ownership boundaries and classifies each remaining catalogued rule
against the **current** governed response schema, naming — but not designing — the future
capability each deferred rule needs.
