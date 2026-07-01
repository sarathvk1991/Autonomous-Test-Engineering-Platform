# Architecture Freeze Index

| Attribute | Value |
| --------- | ----- |
| Document type | Engineering Governance / Freeze Register |
| Status | Living document — governance artifact |
| Scope | Every frozen (or freeze-track) architectural contract in the platform |
| Source of truth | The `docs/architecture/` specifications and the repository state |
| Sibling document | [Platform Capability Matrix](./platform-capability-matrix.md) |

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
| **AI Response Validation Architecture** | Contract `DEFAULT_VALIDATION_CONTRACT_VERSION` 1.0 | Approved — foundational | **Frozen** (has an Architecture Freeze section) | Not Recorded | `docs/architecture/ai-response-validation.md` | Validation Canonical Models · Validation Rule Catalog · Response Validator | Framework implemented; Transport layer only | Philosophy of validation; verdict/severity/boundary model. |
| **Validation Canonical Models** | Contract 1.0 | Approved — foundational | **Frozen** (invariants §11; changes are ADR-gated §13) | Not Recorded | `docs/architecture/validation-canonical-models.md` | AI Response Validation · Response Normalization Contract | Result models + `ParsedResponse` implemented | Defines `ParsedResponse` shape and the result aggregate. |
| **Validation Framework** | `FRAMEWORK_VERSION` 1.0.0 (pipeline/registry 1.0.0) | Implemented | **Frozen** (Syntax Design Review §"do not modify the frozen framework") | Not Recorded | `docs/architecture/ai-response-validation.md` · `requirement_intelligence/validation/README` | Validation Rule Catalog | `validation/` implemented + tested | Rule/registry/pipeline infrastructure. |
| **Validation Rule Catalog** | `RULE_CATALOG_VERSION` 1.0.0 | Approved — foundational | **Frozen** (catalog governance; grows additively via ADR) | Not Recorded | `docs/architecture/validation-rule-catalog.md` | AI Response Validation · Validation Canonical Models | Transport rules only implemented | The `<LAYER>-NNNN` rule numbering + layer order. |
| **Transport Layer** | Rules at `DEFAULT_RULE_VERSION` 1.0.0 | Complete | **Frozen** (Rule Catalog §"Transport Layer Status — FROZEN") | Not Recorded | `docs/architecture/validation-rule-catalog.md` §Transport | — | `TRANSPORT-0001…0004` implemented + tested | The only implemented validation layer. |
| **Response Validator Architecture** | `VALIDATOR_VERSION` 1.0.0 | Approved — foundational | **Frozen** (has an Architecture Freeze section) | Not Recorded | `docs/architecture/response-validator.md` | AI Response Validation · Validation Canonical Models | Orchestrator class built + tested; **not wired** | Orchestration contract; execution context. |
| **Response Normalization Contract** | `NORMALIZATION_CONTRACT_VERSION` 1.0 | Approved — foundational — **FROZEN** | **Frozen** (explicit in header + §17) | Not Recorded | `docs/architecture/response-normalization-contract.md` | Validation Canonical Models · AI Response Validation | Framework implemented; normalizer not built | Governs the Response Normalization Layer & `ParsedResponse` lifecycle. |
| **ParsedResponse Ownership** | `PARSED_RESPONSE_VERSION` 1.0 | Aligned | **Frozen** (single-owner model; observations owned by `NormalizationResult`) | Not Recorded | `validation-canonical-models.md` §8 · `response-normalization-contract.md` §8 | Response Normalization Framework | `models/parsed_response.py` implemented + tested | Ownership aligned across all architecture docs. |
| **Response Normalization Framework** | `FRAMEWORK_VERSION` 1.0.0 (pipeline/registry/responsibility-catalog 1.0.0) | Implemented | **Frozen** (subsystem responsibilities frozen — Contract §4) | Not Recorded | `docs/architecture/response-normalization-contract.md` · `requirement_intelligence/normalization/framework/README` | ParsedResponse Ownership | `normalization/` framework implemented + tested | Registry/pipeline/result/execution-context; no responsibilities yet. |
| **Reasoning Contract** | `REASONING_CONTRACT_VERSION` 1.0.0 | Approved — foundational | Approved (not declared Frozen) | Not Recorded | `docs/architecture/ai-reasoning-contract.md` | Requirement Analysis Service · Validation | Specification (consumed by prompts/analysis) | Defines trustworthy-reasoning requirements. |
| **Requirement Analysis Service** | `ANALYSIS_SERVICE_VERSION` 1.0.0 | Approved — foundational | Approved (not declared Frozen) | Not Recorded | `docs/architecture/requirement-analysis-service.md` | Reasoning Contract | `analysis/` implemented + tested | Produces the `AnalysisResult`/`LLMResponse`. |
| **Execution Package** | `EXECUTION_PACKAGE_VERSION` 1.0.0 (`MANIFEST_SCHEMA_VERSION` 1.0.0) | Implemented | Not Frozen (stable) | Not Recorded | `platform_metadata.py` (`execution/`) | — | `execution/` implemented + tested | No dedicated architecture document. |
| **CLI Architecture** | `CLI_VERSION` 1.0.0 | Implemented | Not Frozen (stable) | Not Recorded | `platform_metadata.py` (`scripts/run_requirement_analysis.py`) | — | `scripts/run_requirement_analysis.py` implemented + tested | Command catalogue in `platform_metadata.CLI_COMMANDS`. |
| **Prompt Framework** | `PROMPT_FRAMEWORK_VERSION` 1.0.0 (`PROMPT_VERSION` 1.0.0) | Implemented | Not Frozen (stable) | Not Recorded | `requirement-analysis-service.md` (partial) · `prompts/` | Reasoning Contract | `prompts/` implemented + tested | No dedicated architecture document. |

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
| Wire the existing Response Validator into the CLI/platform | **No** | Delivery/wiring of already-designed code; no contract changes. |
| Optimise a rule, add tests, or refactor a builder | **No** | Mechanism/quality work beneath a stable contract. |

## 7. Relationship to implementation

**Frozen does not mean finished.** A freeze fixes the *architecture*, not the
*code*:

- **Implementation may continue.** Transport is frozen, yet new capabilities (the
  `ResponseNormalizer`, the Syntax layer) are still being built on the frozen
  frameworks and contracts beneath them.
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
