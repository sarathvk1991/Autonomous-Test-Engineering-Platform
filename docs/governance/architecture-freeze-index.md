# Architecture Freeze Index

| Attribute | Value |
| --------- | ----- |
| Document type | Engineering Governance / Freeze Register |
| Status | Living document — governance artifact |
| Governance baseline | **Validation Platform v1.0.0** (Git tag `v1.0.0-validation-platform`; see [release notes](../releases/v1.0.0-validation-platform.md)) |
| Scope | Every frozen (or freeze-track) architectural contract in the platform |
| Source of truth | The `docs/architecture/` specifications and the repository state |
| Sibling documents | [Platform Capability Matrix](./platform-capability-matrix.md) · [Architecture Coverage Dashboard](./architecture-coverage-dashboard.md) |

> This document **indexes** existing freezes; it does **not create** them. A freeze
> is declared inside a governing architecture document; this index records where
> that declaration lives and whether the repository still honours it. Updating this
> index never changes architecture.

---

## 1. Purpose

The Architecture Freeze Index is the **one authoritative list of every frozen
architectural contract** in the Autonomous Test Engineering Platform. For each
artifact it records the governing document, the current state, the freeze status,
the dependent documents, and the implementation status — so that any engineer can
tell, in one place, *what is immutable*, *where that immutability is declared*, and
*what depends on it*.

## 2. Why architectural freezes exist

A freeze makes an architectural contract **immutable except through a deliberate,
reviewed decision (an ADR)**. Freezes exist because the platform's determinism and
auditability depend on stable contracts:

- **Downstream stability** — consumers (validation, future generators, analytics)
  build on a contract; if it shifted silently, every consumer could break or
  silently diverge.
- **One interpretation** — a frozen contract cannot be re-interpreted per
  implementation, which is what keeps the same input producing the same result.
- **Safe parallel work** — with the architecture fixed, implementation, tests, and
  performance work can proceed independently without renegotiating meaning.
- **A clear change gate** — a freeze forces any *architectural* change through an
  ADR, while leaving *mechanism* free to improve.

## 3. Freeze lifecycle

```text
   Draft ─► Review ─► Approved ─► Frozen ─► Superseded
```

| State | Meaning |
| ----- | ------- |
| **Draft** | The contract is being written; nothing depends on it yet; it may change freely. |
| **Review** | The contract is complete and under architectural review; feedback may still reshape it. |
| **Approved** | The contract is accepted and foundational; implementations must conform to it, but it is not yet declared immutable. |
| **Frozen** | The contract is declared immutable. It evolves **only** through an approved ADR; implementation beneath it may still improve. |
| **Superseded** | A later ADR has replaced the contract; it is retained for history but no longer governs. (No artifact is in this state today.) |

## 4. Architecture Freeze Index

Freeze dates are recorded as **"Not Recorded"** wherever no governing document
states one — none of the current documents record an explicit freeze date, so no
date is invented.

| Artifact | Version | Current State | Freeze Status | Freeze Date | Governing Document | Dependent Documents | Implementation Status | Notes |
| -------- | ------- | ------------- | ------------- | ----------- | ------------------ | ------------------- | --------------------- | ----- |
| **AI Response Validation Architecture** | Contract `DEFAULT_VALIDATION_CONTRACT_VERSION` 1.0 | Approved — foundational | **Frozen** (has an Architecture Freeze section) | Not Recorded | `docs/architecture/ai-response-validation.md` · ADR-0004 | Validation Canonical Models · Validation Rule Catalog · Response Validator | Framework implemented; 5 layers with rules (Transport, Syntax, Schema, Content, Reasoning — 13 rules); Response Validator wired end-to-end with persistence, reporting, and governed profiles | Philosophy of validation; verdict/severity/boundary model. Schema/Structural layer descriptions aligned to ADR-0004 (existence → Schema; composition → Structural). |
| **Validation Canonical Models** | Contract 1.0 | Approved — foundational | **Frozen** (invariants §11; changes are ADR-gated §13) | Not Recorded | `docs/architecture/validation-canonical-models.md` | AI Response Validation · Response Normalization Contract | Result models + `ParsedResponse` implemented | Defines `ParsedResponse` shape and the result aggregate. |
| **Validation Framework** | `FRAMEWORK_VERSION` 1.0.0 (pipeline/registry 1.0.0) | Implemented | **Frozen** (Syntax Design Review §"do not modify the frozen framework") | Not Recorded | `docs/architecture/ai-response-validation.md` · `requirement_intelligence/validation/README` | Validation Rule Catalog | `validation/` implemented + tested | Rule/registry/pipeline infrastructure. |
| **Validation Rule Catalog** | `RULE_CATALOG_VERSION` 1.0.0 | Approved — foundational | **Frozen** (catalog governance; grows/evolves via ADR) | Not Recorded | `docs/architecture/validation-rule-catalog.md` · ADR-0004 · ADR-0005 · ADR-0006 · ADR-0007 · ADR-0008 · ADR-0009 (Proposed) · ADR-0010 (Proposed) | AI Response Validation · Validation Canonical Models | Transport + Syntax + Schema (0001/0002/0004) + Content (0001/0002) + Reasoning (0002) rules implemented | The `<LAYER>-NNNN` rule numbering + layer order. **Schema ↔ Structural ownership set by ADR-0004** (existence → Schema; composition → Structural; `STRUCTURE-0001…0004` Deprecated). **`SCHEMA-0003` deferred by ADR-0005**. **Remaining layers (Structural…Business) boundary-frozen and each rule classified Implemented / Implementable / Reserved · Deferred by ADR-0006** (descriptive; no ID/version change). **`CONTENT-0002` duplicate scope frozen within-collection by ADR-0007.** **`REASONING-0002` comparison mechanism byte-exact by ADR-0008 (Accepted).** **`REASONING-0001` deferred by ADR-0009 and `REASONING-0003` deferred by ADR-0010 (Proposed; no governed deterministic contradiction/circular-logic mechanism), superseding their ADR-0006 Implementable classifications.** |
| **Transport Layer** | Rules at `DEFAULT_RULE_VERSION` 1.0.0 | Complete | **Frozen** (Rule Catalog §"Transport Layer Status — FROZEN") | Not Recorded | `docs/architecture/validation-rule-catalog.md` §Transport | — | `TRANSPORT-0001…0004` implemented + tested | The first frozen validation layer; Syntax, Schema, Content, and Reasoning layers now also have implemented rules (13 rules total across 5 layers). |
| **Response Validator Architecture** | `VALIDATOR_VERSION` 1.0.0 | Approved — foundational | **Frozen** (has an Architecture Freeze section; input contract amended by ADR-0003) | Not Recorded | `docs/architecture/response-validator.md` · ADR-0003 | AI Response Validation · Validation Canonical Models · ValidationInput | Orchestrator built + tested; **migrated to `ValidationInput`** (ADR-0003); **wired end-to-end** via the composition root (`validator_factory`) + `PlatformContext` + CLI `--validate`, with `ValidationResult` persistence, `validation_report.md` reporting, and governed Validation Profiles | Orchestration contract; execution context. Input is now the `ValidationInput` (ADR-0003). |
| **ValidationInput (canonical model)** | `VALIDATION_INPUT_VERSION` 1.0 | Approved — foundational | Not Frozen (additive Core Canonical Model; ADR-0003) | Not Recorded | ADR-0003 · `docs/architecture/validation-canonical-models.md` §8A | Response Validator · Validation Pipeline · Transport rules | `validation/models/validation_input.py` implemented + tested | Immutable, execution-scoped binding of `AnalysisResult` + `NormalizationResult`; owns only the binding. |
| **Response Normalization Contract** | `NORMALIZATION_CONTRACT_VERSION` 1.0 | Approved — foundational — **FROZEN** | **Frozen** (explicit in header + §17) | Not Recorded | `docs/architecture/response-normalization-contract.md` | Validation Canonical Models · AI Response Validation | Framework + `ResponseNormalizer` implemented + tested (end-to-end) | Governs the Response Normalization Layer & `ParsedResponse` lifecycle. |
| **ParsedResponse Ownership** | `PARSED_RESPONSE_VERSION` 1.0 | Aligned | **Frozen** (single-owner model; observations owned by `NormalizationResult`) | Not Recorded | `validation-canonical-models.md` §8 · `response-normalization-contract.md` §8 | Response Normalization Framework | `models/parsed_response.py` implemented + tested | Ownership aligned across all architecture docs. |
| **Response Normalization Framework** | `FRAMEWORK_VERSION` 1.0.0 (pipeline/registry/responsibility-catalog 1.0.0) | Implemented | **Frozen** (subsystem responsibilities frozen — Contract §4) | Not Recorded | `docs/architecture/response-normalization-contract.md` · `requirement_intelligence/normalization/framework/README` · ADR-0002 | ParsedResponse Ownership | `normalization/` framework implemented + tested | Generic execution infrastructure (registry/pipeline/result/execution-context); it registers **no** framework responsibilities. The `NORMALIZATION-0001…0005` stages are now implemented as **internal stages of the `ResponseNormalizer`**, not framework units (ADR-0002). |
| **Normalization Assembly Contract** | Contract 1.0 | Approved — foundational — **FROZEN** | **Frozen** (has an Architecture Freeze section §12) | Not Recorded | `docs/architecture/normalization-assembly-contract.md` | Normalization Responsibility Catalog · ParsedResponse Ownership · ADR-0002 | Implemented + tested — the five internal stages + `AssemblyState` + `StageCoordinator` | Governs the internal collaboration (Assembly State) of the five `ResponseNormalizer` stages; transient, non-canonical, non-escaping (ADR-0002). |
| **Response Normalizer Architecture** | `FRAMEWORK_VERSION` 1.0.0 | Approved — foundational — **FROZEN** | **Frozen** (Architecture Freeze §17) | Not Recorded | `docs/architecture/response-normalizer.md` | Response Normalization Contract · Normalization Assembly Contract · ADR-0002 | `ResponseNormalizer` implemented + tested (incl. end-to-end) | The single orchestration boundary; drives the five internal stages within its boundary (ADR-0002) and populates the `ParsedResponse` on the `NormalizationResult`. |
| **Normalization Responsibility Catalog** | `RESPONSIBILITY_CATALOG_VERSION` 1.0.0 | Approved — foundational — **FROZEN** | **Frozen** (Architecture Freeze §11) | Not Recorded | `docs/architecture/normalization-responsibility-catalog.md` | Response Normalization Contract · Normalization Assembly Contract · ADR-0002 | The five stages `NORMALIZATION-0001…0005` implemented + tested (internal to the `ResponseNormalizer`) | Governs the five internal-stage identities, single concern, order, ownership, and forward-only dependencies. |
| **Normalization Stage Implementation Contract** | Contract 1.0 | Approved — foundational — **FROZEN** | **Frozen** (Architecture Freeze §14) | Not Recorded | `docs/architecture/normalization-stage-implementation-contract.md` | Normalization Responsibility Catalog · Normalization Assembly Contract · ADR-0002 | All five stages conform + tested | Governs the engineering implementation pattern every internal stage follows (single concern, one owned fact, guarded writes, facts-not-exceptions, immutable metadata). |
| **Validation Rule Implementation Contract** | Contract 1.0 | Approved — foundational — **FROZEN** | **Frozen** (Architecture Freeze §14) | Not Recorded | `docs/architecture/validation-rule-implementation-contract.md` | Validation Rule Catalog · Validation Canonical Models (`ValidationIssue`/`ValidationInput`) · ValidationRule (Framework) · ADR-0003 | Transport + Syntax + Schema + Content + Reasoning rules conform + tested | Governs the engineering structure every validation rule (all layers) follows (lifecycle, single concern, `ValidationInput`-only input, `ValidationIssue`-only output, facts-not-exceptions, immutable metadata, principled DI). The validation-layer analogue of the Normalization Stage Implementation Contract. |
| **Schema Validation Implementation Contract** | Contract 1.0 | Approved — foundational — **FROZEN** | **Frozen** (Architecture Freeze §19) | Not Recorded | `docs/architecture/schema-validation-implementation-contract.md` | Validation Rule Implementation Contract · Validation Rule Catalog · Validation Canonical Models (`ParsedResponse`/`ValidationInput`) · Response Normalization Contract · ADR-0003 | Schema rules `SCHEMA-0001/0002/0004` implemented + tested (`SCHEMA-0003` Reserved · Deferred by ADR-0005) | Schema-layer **specialization** of the Validation Rule Implementation Contract: fixes the Schema functional input (the normalized structure only), forbidden inputs, shape-vs-composition-vs-content boundary, assume-well-formed-and-defer rule, and the Schema↔Syntax↔Structural relationships. Complements — does not duplicate — the general contract or the Catalog. |
| **Reasoning Contract** | `REASONING_CONTRACT_VERSION` 1.0.0 | Approved — foundational | Approved (not declared Frozen) | Not Recorded | `docs/architecture/ai-reasoning-contract.md` | Requirement Analysis Service · Validation | Specification (consumed by prompts/analysis) | Defines trustworthy-reasoning requirements. |
| **Requirement Analysis Service** | `ANALYSIS_SERVICE_VERSION` 1.0.0 | Approved — foundational | Approved (not declared Frozen) | Not Recorded | `docs/architecture/requirement-analysis-service.md` | Reasoning Contract | `analysis/` implemented + tested | Produces the `AnalysisResult`/`LLMResponse`. |
| **Execution Package** | `EXECUTION_PACKAGE_VERSION` 1.0.0 (`MANIFEST_SCHEMA_VERSION` 1.0.0) | Implemented | Not Frozen (stable) | Not Recorded | `platform_metadata.py` (`execution/`) | — | `execution/` implemented + tested | No dedicated architecture document. |
| **CLI Architecture** | `CLI_VERSION` 1.0.0 | Implemented | Not Frozen (stable) | Not Recorded | `platform_metadata.py` (`scripts/run_requirement_analysis.py`) | — | `scripts/run_requirement_analysis.py` implemented + tested | Command catalogue in `platform_metadata.CLI_COMMANDS`. |
| **Prompt Framework** | `PROMPT_FRAMEWORK_VERSION` 1.0.0 (`PROMPT_VERSION` 1.0.0) | Implemented | Not Frozen (stable) | Not Recorded | `requirement-analysis-service.md` (partial) · `prompts/` | Reasoning Contract | `prompts/` implemented + tested | No dedicated architecture document. |
| **Productization Governance Contract** (CAP-070) | Governance contract 1.0 · Golden Dataset `GOLDEN_DATASET_VERSION` 1.0.0 (**versioned independently**) | Approved — foundational — **FROZEN** | **Frozen** — **governance contract only** (has a Governance Contract Freeze section §13); the **golden dataset is NOT frozen** | Not Recorded | `docs/productization/golden-baseline.md` §13 | Platform Capability Matrix (§5.7 CAP-070) · Architecture Coverage Dashboard (§4 CAP-070) | Productization suite (70 tests, Phase 3–6) + golden dataset implemented + passing | Freezes the **governance contract** — the baseline's role (Release Regression Baseline), validation scope, determinism contract, ownership boundaries, and regression procedure. The **golden dataset contents are explicitly NOT frozen**: they stay independently versioned via `GOLDEN_DATASET_VERSION` and evolve additively under the doc's §7.3 re-baselining procedure, with **no ADR and no governance-contract change**. Governance registration only (CAP-070B) — no architecture, no ADR, no code change. |

### 4.1 Freeze History

Each **frozen** artifact carries a Freeze History across the lifecycle states
`Draft → Review → Approved → Frozen → Superseded`. **Only objectively-known states
are recorded.** Two states are evidenced by the repository — **Approved** (each
governing document's `Status` line) and **Frozen** (the specific freeze
declaration cited in §4). The **Draft** and **Review** transitions, and **all
dates**, are **Not Recorded** — no document records them, so none is invented. **No
artifact is Superseded.** (The five Approved-but-not-frozen artifacts in §4 —
Reasoning Contract, Requirement Analysis Service, Execution Package, CLI, Prompt
Framework — have no Freeze History because they are not frozen.)

Legend: **Reached · date Not Recorded** = the state was reached but no date is
recorded · **Not Recorded** = no evidence of this transition · **No** = state not
reached.

| Frozen Artifact | Draft | Review | Approved | Frozen | Superseded | Freeze evidence |
| --------------- | ----- | ------ | -------- | ------ | ---------- | --------------- |
| AI Response Validation Architecture | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Architecture Freeze section |
| Validation Canonical Models | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Invariants §11; ADR-gated §13 |
| Validation Framework | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Syntax Design Review §"do not modify the frozen framework" |
| Validation Rule Catalog | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Catalog governance (ADR-gated growth) |
| Transport Layer | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Rule Catalog §"Transport Layer Status — FROZEN" |
| Response Validator Architecture | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Architecture Freeze section |
| Response Normalization Contract | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Header `FROZEN` + §17 |
| ParsedResponse Ownership | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Single-owner model aligned across docs (§8) |
| Response Normalization Framework | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Subsystem responsibilities frozen — Contract §4 |
| Normalization Assembly Contract | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Architecture Freeze section §12 |
| Response Normalizer Architecture | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Architecture Freeze section §17 |
| Normalization Responsibility Catalog | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Architecture Freeze section §11 |
| Normalization Stage Implementation Contract | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Architecture Freeze section §14 |
| Validation Rule Implementation Contract | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Architecture Freeze section §14 |
| Schema Validation Implementation Contract | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Architecture Freeze section §19 |
| Productization Governance Contract (CAP-070) | Not Recorded | Not Recorded | Reached · date Not Recorded | Reached · date Not Recorded | No | Governance Contract Freeze section §13 (governance contract only; golden dataset independently versioned, not frozen) |

## 5. Architecture Governance Principles

These are the platform's **existing** principles, summarised (not invented). Each
is drawn from the governing documents above.

1. **Frozen architecture evolves only through ADRs.** A change to any frozen
   contract requires an approved Architecture Decision Record (Response
   Normalization Contract §17; Validation Canonical Models §13).
2. **Implementation may evolve without ADRs, provided architecture is preserved.**
   The mechanism beneath a contract may be optimised, replaced, or re-tuned freely
   ("Implementation may evolve. Responsibilities may not." — Response Normalization
   Contract §4.2).
3. **Implementation must conform to architecture.** An implementation conforms to
   its governing document(s); where two apply (philosophy + information model), it
   conforms to both (Validation Canonical Models §1).
4. **Architecture owns philosophy; implementation owns mechanism.** *What* and
   *why* live in architecture; *how* lives in code.
5. **Every concept has exactly one canonical owner.** No information has two
   canonical homes (the `ParsedResponse` / `NormalizationResult` ownership
   alignment is the reference example).
6. **Every architectural contract has exactly one governing document.** The index
   above names it for each artifact; the freeze lives there, not in code.

## 6. Relationship to ADRs

An **ADR is required** when a change alters a frozen contract's meaning or shape.
An **ADR is not required** for work that leaves the architecture intact.

| Situation | ADR required? | Repository example |
| --------- | :-----------: | ------------------ |
| Add a new `NormalizationOutcome` / `ExecutionStatus` member | **Yes** | A new outcome is governed exactly like a new `ExecutionStatus` (Response Normalization Contract §9). |
| Add a new `NORMALIZATION-00NN` responsibility or a new validation layer/rule number | **Yes** | The `NORMALIZATION-` and `<LAYER>-NNNN` catalogs grow additively via ADR (Contract §13; Rule Catalog). |
| Change a canonical model's shape (e.g. add/remove a `ParsedResponse` attribute, or move observation ownership) | **Yes** | Advances a version and requires an ADR (Canonical Models §13; the ParsedResponse ownership decision). |
| Implement the `ResponseNormalizer` mechanism and its responsibilities | **No** | The responsibilities are frozen; the *mechanism* that fulfils them is free (Contract §4.2). |
| Clarify an abstraction boundary between frozen contracts without changing any contract's shape or meaning | **Yes — recorded as an ADR** | ADR-0002 separates the generic Response Normalization Framework from the `ResponseNormalizer` component; no contract changed, the clarification is recorded. |
| Resolve the Normalization → Validation handoff (new canonical input; amend the Validator input contract) | **Yes — recorded as an ADR** | ADR-0003 introduces the `ValidationInput` canonical model and amends the Response Validator's input from `AnalysisResult` to `ValidationInput`; the rule contract (`response: Any`) is unchanged. |
| Resolve an ownership overlap between two frozen validation layers (reassign a concern; deprecate rules) | **Yes — recorded as an ADR** | ADR-0004 sets the Schema ↔ Structural boundary (existence → Schema; composition/hierarchy/organization → Structural), deprecating `STRUCTURE-0001…0004`; the Rule Catalog and Schema Validation Implementation Contract are aligned. |
| Record that a reserved catalog rule has no governed concern yet, and intentionally defer it | **Yes — recorded as an ADR** | ADR-0005 defers `SCHEMA-0003` (EnumerationsRule): the governed response schema has **no enumerated field**, so the rule is a **permanently reserved identity** implementable only once a governed response enumeration exists. No contract, canonical model, rule identity, or version changes; `SCHEMA-0004` becomes the next Schema milestone. |
| Record the implementation status of every remaining catalogued rule against the current governed response schema (descriptive, not prescriptive) | **Yes — recorded as an ADR** | ADR-0006 freezes the remaining layers' ownership boundaries (Structural…Business) and classifies each catalogued rule as **Implemented / Implementable / Reserved · Deferred**, documenting the future schema-enrichment prerequisite for each deferred rule. It invents no governed field, changes no contract/canonical model/rule identity/version, and extends the ADR-0005 deferral principle layer-wide. |
| Fix the undefined *scope* of an existing catalogued rule so implementations are deterministic | **Yes — recorded as an ADR** | ADR-0007 freezes `CONTENT-0002` (DuplicateRequirementRule) as **within-collection** duplicate detection (`functional_/security_/quality_requirements` never pooled), keeping the concern local to Content and clear of Structural/Reasoning. It changes no rule identity, severity, blocking, or version. |
| Fix the undefined *comparison mechanism* of an existing catalogued rule | **Yes — recorded as an ADR** | ADR-0008 (**Accepted**) freezes `REASONING-0002` (DuplicateRecommendationRule) as **byte-exact** string equality (case-/whitespace-sensitive, no normalization, no semantics); semantic "duplicated conclusions" is reserved as a future capability behind its own ADR. Shares the mechanism with `CONTENT-0002` but owns a distinct domain (recommendations), so ownership stays unique. No rule identity, severity, blocking, or version change. |
| Record that a catalogued rule has no governed *deterministic mechanism* and defer it | **Yes — recorded as an ADR** | ADR-0009 (**Proposed**) defers `REASONING-0001` (ContradictoryRequirementRule) as **Reserved · Deferred**: contradiction is inherently semantic/logical and no governed deterministic mechanism exists (no faithful surface-form mechanism, unlike duplicates). Adopts **no** mechanism; reserves contradiction for a future semantic-reasoning ADR. **Supersedes ADR-0006's Implementable classification of `REASONING-0001`.** No rule identity, severity, blocking, or version change. |
| Record that a second Reasoning rule has no governed *deterministic mechanism* and defer it | **Yes — recorded as an ADR** | ADR-0010 (**Proposed**) defers `REASONING-0003` (CircularLogicRule) as **Reserved · Deferred**: circular logic is inherently semantic/logical and additionally presupposes an inferential dependency structure the bare-string response does not carry (needs both dependency inference and cycle detection — neither governed). Adopts **no** mechanism; reserves it for a future semantic-reasoning ADR. **Supersedes ADR-0006's Implementable classification of `REASONING-0003`.** With ADR-0008/0009/0010 the Reasoning layer is fully dispositioned (0002 implemented; 0001, 0003 deferred). No rule identity, severity, blocking, or version change. |
| Introduce a downstream engineering-readiness gate consuming the Validation Platform's output (new canonical input; reconcile a legacy stub; correct the execution-flow docs) | **Yes — recorded as an ADR** | ADR-0011 (**Accepted**) establishes the **CP1 Validation Engine** and the **Validation → CP1 handoff**: a new `CP1Input` canonical model (the downstream analogue of ADR-0003's `ValidationInput`), CP1's flow position and gating (verdict ∈ `PASSED`/`PASSED_WITH_WARNINGS`), the `Criterion → Registry → Pipeline → Aggregate Result` engine pattern, and the disposition of the legacy `validators/cp1.py` `list[CanonicalRequirement]` signature (superseded). It mandates a governed **CP1 Criteria Catalog** (ADR-0012) before any criterion is implemented. Realized so far by CAP-062 (CP1 canonical models) and CAP-063 (CP1 framework). Touches **no** frozen validation/normalization contract. |
| Establish a governed catalogue for a new downstream judgement domain (its identity scheme, lifecycle, ownership, growth) without defining any concrete member | **Yes — recorded as an ADR** | ADR-0012 (**Accepted**) establishes the **Engineering Readiness Criteria Catalog** (`docs/architecture/engineering-readiness-criteria-catalog.md`, capability **CAP-061**) — the CP1 analogue of the Validation Rule Catalog, fulfilling ADR-0011's gate. It governs the `CP1-NNNN` flat identity scheme, lifecycle, ordering/independence, and per-criterion severity/verdict contribution, and is established **empty (zero criteria)**. It defines **no** criterion, threshold, or PASS/FAIL policy; concrete criteria are added additively through the catalog's governed process. Touches **no** frozen contract. |
| Additively add a referenced provenance field to a **non-frozen** CP1 canonical model to complete the ValidationResult mirror | **No new ADR — additive under ADR-0011** | CAP-063.1 adds `framework_metadata: CP1FrameworkMetadata` to `CP1Result`, mirroring `ValidationResult`'s reference to `ValidationFrameworkMetadata` (ADR-0011 §D4 "mirror ValidationResult"). Additive shape change on a **non-frozen** model: advances `CP1_RESULT_VERSION` 1.0 → 1.1; no new ADR (the model is governed by ADR-0011, not frozen). No other canonical model changes. |
| Define and govern the **first** engineering-readiness criterion deterministically (its concern, deterministic basis, verdicts, and boundary vs Validation) before implementation | **Yes — recorded as an ADR** | ADR-0013 (**Accepted**) governs **`CP1-0001` (EngineeringInputAvailabilityCriterion)** — the criterion of **Engineering Input Availability**: whether the validated response provides sufficient engineering input from which downstream engineering may begin, on the deterministic floor of **pooled requirement count ≥ 1** (`functional_/security_/quality_requirements`), `CP1Input`-only, **no** semantics/NLP/LLM/policy. **PASS** ("engineering input exists") / **FAIL** ("no engineering input exists"); **WARN reserved**. Strengthens the governed boundary — **Validation owns artifact correctness ("is the artifact valid?"); CP1 owns engineering readiness ("can engineering begin?")** — with `BUSINESS-0001/0003` coverage/minimum staying Reserved · Deferred and distinct (ADR-0006). Defines only *what* CP1-0001 is; **no** implementation and **no** framework/engine/composition/canonical-model change. Criteria Catalog (CAP-061) §9 records CP1-0001 **Approved**; Catalog Version **1.1.0**. |
| Wire the existing Response Validator into the CLI/platform | **No** | Delivery/wiring of already-designed code; no contract changes. |
| Optimise a rule, add tests, or refactor a builder | **No** | Mechanism/quality work beneath a stable contract. |

## 7. Relationship to implementation

**Frozen does not mean finished.** A freeze fixes the *architecture*, not the
*code*:

- **Implementation may continue.** Transport is frozen, yet capabilities built on the
  frozen frameworks and contracts beneath it continue to grow (the `ResponseNormalizer`,
  the Syntax/Schema/Content/Reasoning layers, and the wired Response Validator).
- **Tests may evolve.** Coverage can grow and tests can be restructured without
  touching architecture.
- **Performance may improve.** A normalization or validation mechanism may be
  re-tuned or replaced so long as it produces the identical contracted output.
- **Refactoring may occur.** Internal structure may change while the public
  contract and its canonical models stay stable.

The invariant is simple: **the architecture stays stable; the mechanism is free.**
When implementation status or a version constant changes, the
[Platform Capability Matrix](./platform-capability-matrix.md) and this index are
updated — the architecture is not.
