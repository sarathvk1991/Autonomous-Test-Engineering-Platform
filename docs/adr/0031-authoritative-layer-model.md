# ADR-0031 — Authoritative Layer Model

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution) — fully superseded, not amended (see D1 for why this is a full supersession rather than an additive patch of the kind ADR-0030 applied to ADR-0020). **Amends:** nothing else.
- **Governing design:** none — this ADR *is* the governing design, exactly as ADR-0020 was for the model it replaces. Its assessment basis is `docs/audit/CODEBASE_AUDIT_2026-07-24.md`, a read-only repository audit conducted immediately prior to this decision.
- **Depends on:** ADR-0001 (Modular Monolith — the deployment shape this layer model is drawn inside); every accepted Layer 1 subsystem ADR (ADR-0011–ADR-0019) — unaffected by this decision, their contracts and freezes are untouched; ADR-0021–ADR-0029 (Continuous Learning capabilities) and ADR-0030 (Executable Specification Engineering) — their **runtime architecture is unaffected**, only their layer designation changes (D3).
- **Runtime status:** Not applicable. This is a **documentation-only** milestone: no code, model, policy, `PlatformContext` method, Execution Package field, or version constant changes. It renames no package (package renames are ADR-0033) and freezes no new subsystem. It states, permanently, what the platform's seven layers are and what belongs to each.

## Scope note

Like ADR-0020 before it, this ADR is not owned by a subsystem and does not govern one. It is the platform's architectural constitution. Unlike ADR-0030's relationship to ADR-0020 (a narrow, additive amendment), this ADR **replaces ADR-0020 in full** — the two documents define incompatible layer catalogues under the same layer numbers, and no additive patch can reconcile them (D1).

---

## Stage 0 — Repository assessment

Before writing this ADR, `docs/audit/CODEBASE_AUDIT_2026-07-24.md` was read in full, and the following were independently re-verified:

- **The six Phase-2–7 placeholder packages** (`feature_engineering/`, `automation_engineering/`, `quality_governance/`, `execution/`, `failure_intelligence/`, `governance_dashboard/`) were all created in the repository's **initial commit** (`28d0284`, 2026-06-18) — confirmed via `git log -- <path>` returning exactly one commit per package, none since. Each package's README states, verbatim, `**Status:** Planned (Phase N — not implemented)` for N = 2 through 6, and each describes a distinct stage of a *test-engineering pipeline*: deriving BDD features, generating automation code, validating that code and gating release, executing the suite, diagnosing and healing failures, and rendering leadership insight.
- **ADR-0020** (`docs/adr/0020-platform-evolution-roadmap.md`) is dated **2026-07-15** — roughly one month *after* those six packages were committed — and defines a materially different Layer 1–7 (plus Layer 2.5) catalogue: Requirement Intelligence → Continuous Learning → Executable Specification Engineering → Feature Engineering → Prediction & Insights → Optimization → Autonomous Engineering → Organizational Intelligence. This is an analytics-and-autonomy progression over the *history* of Requirement Intelligence executions, not a test-engineering pipeline. It was never reconciled against the six placeholder packages the repository had already committed to a month earlier: ADR-0020's own Stage 0 assessment (§ADR-0020 Stage 0) reviews only ADR-0011 through ADR-0019 and does not mention `feature_engineering/`, `automation_engineering/`, `quality_governance/`, `execution/`, `failure_intelligence/`, or `governance_dashboard/` anywhere in its text.
- **`README.md`** (`docs/audit/CODEBASE_AUDIT_2026-07-24.md` §1.2, re-confirmed by direct read of `README.md`) documents the platform as a seven-*phase* progression matching the six placeholder packages' own phase numbers, not ADR-0020's layer numbers.

**Finding:** the repository has, since its first commit, structurally committed to a test-engineering pipeline shape that ADR-0020 does not describe. ADR-0020 is a real, carefully constructed document, but it answers a different question (how does the platform reason about many executions over time and eventually act autonomously) than the one this repository's own module skeleton, and the platform's name — *Autonomous **Test Engineering** Platform* — actually poses (how does a requirement become an executed, self-healing test suite). Both are legitimate architectural directions; this ADR adopts the one the repository is already structurally shaped for, per the explicit brief given for this decision.

**No inconsistency in ADR-0020 itself was found** — it is a self-consistent document. The inconsistency is *between* ADR-0020 and the rest of the repository, and this ADR resolves it by choosing the repository's own pre-existing shape.

---

## Decision

Adopt the following as the platform's single, authoritative target architecture, effective immediately:

| Layer | Name | Purpose |
|---|---|---|
| **L1** | Requirement Intelligence | LLM consolidates JIRA (requirements), SonarQube (SAST), and OWASP ZAP (DAST) evidence into finalised requirement artifacts. |
| **L2** | Feature Engineering | Generates Cucumber BDD feature files from Layer 1's requirement artifacts. |
| **L3** | Automation Engineering | Generates page objects, step definitions, and test data from Layer 2's features. |
| **L4** | Suite Quality Governance | Validates Layers 2 and 3 via SonarQube and Gherkin lint; outputs a self-healed, execution-ready suite. |
| **L5** | Test Execution | Runs the suite and produces reports. |
| **L6** | Failure Intelligence & Self-Healing | Diagnoses and repairs execution failures. |
| **L7** | Governance Dashboard | Leadership-facing insights across the pipeline. |

Sources feeding Layer 1 are frozen at exactly three: **JIRA** (requirements), **SonarQube** (SAST), **OWASP ZAP** (DAST) — the three connectors already FUNCTIONAL per `docs/audit/CODEBASE_AUDIT_2026-07-24.md` §2.1–2.3.

**This ADR formally supersedes ADR-0020 in its entirety** (D1). ADR-0020's five layers that named platform-wide reasoning over history and autonomous action — **Continuous Learning**, **Prediction & Insights**, **Optimization**, **Autonomous Engineering**, and **Organizational Intelligence** — are **redesignated as Layer 1 sub-capabilities**, not layers, effective immediately. Their code location, CAP identifiers, runtime contracts, and Accepted governing ADRs (ADR-0021 through ADR-0029) are **unchanged** — only their architectural designation changes (D3). **Nothing is deleted.**

### Mapping table — ADR-0020 layer → new designation

| ADR-0020 designation | Governing ADR(s) | CAP identifiers | New designation under this ADR |
|---|---|---|---|
| Layer 1 — Requirement Intelligence | ADR-0011–0019 (unchanged) | CAP-001–014, 020–024, 030–073 | **Unchanged — remains Layer 1** under this ADR's own name, Requirement Intelligence. |
| Layer 2 — Continuous Learning | ADR-0021–0029 | CAP-083, 084, 085, 086 | **Redesignated: Layer 1 sub-capability** (historical/cross-execution analytics *about* Layer 1 runs; not a stage a requirement passes through on its way to becoming a test). |
| Layer 2.5 — Executable Specification Engineering | ADR-0030 | CAP-087 (Proposed, architecture-only, no code) | **Not resolved by this ADR — see D4.** Left explicitly TBD rather than guessed. |
| Layer 3 — Feature Engineering (numerical) | none (unbuilt) | none | **Redesignated: Layer 1 sub-capability**, if ever built — this ADR's own Layer 3 (Automation Engineering) now owns the number 3 with an unrelated meaning; ADR-0020's numerical Feature Engineering, if pursued, is cross-execution analytics scoped beneath Layer 1, not a pipeline stage. |
| Layer 4 — Prediction & Insights | none (unbuilt) | none | **Redesignated: Layer 1 sub-capability.** |
| Layer 5 — Optimization | none (unbuilt) | none | **Redesignated: Layer 1 sub-capability.** |
| Layer 6 — Autonomous Engineering | none (unbuilt) | none | **Redesignated: Layer 1 sub-capability.** |
| Layer 7 — Organizational Intelligence | none (unbuilt) | none | **Redesignated: Layer 1 sub-capability.** |

---

## D1 — Why this is a full supersession, not an additive amendment

ADR-0030 amended ADR-0020 additively — inserting Layer 2.5 without renumbering or redefining anything else — because Layer 2.5's purpose did not conflict with any existing layer's frozen definition. That is not available here: this ADR's Layer 2 (Feature Engineering — BDD generation) and ADR-0020's Layer 2 (Continuous Learning — historical analytics) are **different capabilities that happen to share the number 2**; the same collision exists at every layer from 2 through 7. An additive patch cannot coexist with a full renumbering. ADR-0020 must therefore be superseded outright, not amended, and its own numbers must be understood, from this point forward, as belonging to a superseded document — never mixed with this ADR's numbers without an explicit citation to which ADR they come from (D5).

## D2 — Why the repository's own pre-existing structure is the deciding evidence

This decision could have gone either way on its stated merits alone — both catalogues are internally coherent. What resolves it is that the repository committed to the test-engineering shape (six Phase-2–7 placeholder packages) a month **before** ADR-0020 proposed the analytics/autonomy shape, and ADR-0020 was never reconciled against that pre-existing structure (Stage 0). Adopting the repository's own oldest structural commitment, rather than a later, unreconciled proposal, is the smaller and more defensible change — it does not ask the six existing placeholder packages, their READMEs, or `README.md`'s own phase table to be rewritten; it asks the newer, less-integrated document to yield.

## D3 — Why nothing is deleted, and what "redesignated" means precisely

CAP-083 (Continuous Improvement), CAP-084 (Knowledge Graph), CAP-085 (Organizational Memory), and CAP-086 (Learning Framework) are real, Accepted, live capabilities with real runtime contracts, wired into the live Requirement Intelligence pipeline. This ADR changes **none** of that. "Redesignated as a Layer 1 sub-capability" means exactly one thing: where ADR-0020 called these four capabilities collectively "Layer 2," they are now understood as capabilities that reason across many Layer 1 executions, owned and scoped beneath Layer 1, rather than as a distinct layer a requirement or a generated asset passes through. Their governing ADRs (0021–0029), their code locations, their CAP identifiers, and their runtime status are unmodified by this decision. The practical consequence of this redesignation — that they fall inside Layer 1's capability freeze rather than outside it — is recorded separately in ADR-0032, not here.

## D4 — Layer 2.5 / CAP-087 placement is explicitly unresolved

ADR-0020's Layer 2.5 (Executable Specification Engineering, CAP-087, governed by ADR-0030, Proposed, architecture-only — no code exists) is **not** among the five layers this decision was instructed to redesignate. Its stated purpose — transforming judged Layer 1 output into a technology-independent, executable Specification Model — sits close to this ADR's own Layer 2 (Feature Engineering: BDD feature generation from requirements), but closeness is not identity, and CAP-087 has no implementation to evaluate against. Rather than guess a mapping, this ADR records the question as open: **Layer 2's eventual low-level design (referenced by ADR-0034) must explicitly evaluate whether CAP-087's architecture (ADR-0030) is adopted, superseded, or left dormant** before Layer 2 work begins. This is listed as Open Question 1 in the baseline register (`docs/architecture/architecture-baseline-v2.md`).

## D5 — Layer-number disambiguation, permanent rule

Because this ADR reuses the numbers 1–7 with different meanings than ADR-0020, every future ADR, ticket, or design document that cites a bare "Layer N" for N ≥ 2 **must** state which ADR it means (e.g. "Layer 4 (ADR-0031, Suite Quality Governance)") whenever there is any possibility of confusion with ADR-0020's superseded catalogue. Layer 1 is the sole exception — its name and meaning (Requirement Intelligence) are identical under both documents, so it may be cited bare.

---

## Recommendations (permanent)

1. **Every future capability belongs to exactly one of the seven layers above**, or is a sub-capability scoped beneath Layer 1 per the mapping table. A capability that seems to span two layers has not yet been decomposed correctly (carried forward from ADR-0020 Stage 3, restated for this catalogue).
2. **Sources are frozen at exactly three**: JIRA, SonarQube, OWASP ZAP. Adding a fourth source is an architectural decision requiring its own ADR, not a connector-framework change.
3. **This ADR's layer numbers are cited bare only from this point forward.** Any citation of ADR-0020's layer numbers must name ADR-0020 explicitly (D5).
4. **This ADR does not itself authorize building any layer.** It names the target. ADR-0032 governs what may be built next and under what constraint.

---

## Final Constitutional Review

1. **Is the authoritative layer model permanently named?** Yes — the table in Decision.
2. **Is ADR-0020 formally superseded, and is the superseding total or partial?** Total (D1); its status line is updated to reflect this (see `docs/adr/0020-platform-evolution-roadmap.md`), its body is left untouched as a historical record.
3. **Is every ADR-0020 layer accounted for?** Yes: Layer 1 unchanged; Layers 2, 4, 5, 6, 7 redesignated as Layer 1 sub-capabilities; Layer 2.5 explicitly left open (D4), not silently dropped.
4. **Is anything deleted?** No — confirmed in D3.
5. **Is the decision grounded in verified repository evidence rather than preference alone?** Yes — Stage 0's commit-date comparison is the deciding fact, independently re-verified for this ADR.
6. **Does this ADR authorize implementation of Layers 2–7?** No — that is ADR-0032's and each layer's own future architecture-freeze ADR's job.

---

## Ownership, scope, and governance

- **Owns:** the platform's seven-layer catalogue, the three-source freeze, and the permanent disambiguation rule against ADR-0020's superseded numbering.
- **Does not own:** any Layer 1 subsystem's runtime contract, policy, engine, or execution package (unchanged, owned exactly where ADR-0011–ADR-0019 and ADR-0021–ADR-0030 place them); the capability-freeze mechanics for Layer 1 (ADR-0032); package naming (ADR-0033); the Layer 1 → Layer 2 contract (ADR-0034).
- **Governance:** registered as the platform's architectural constitution, replacing ADR-0020 in that role. **Accepted** — effective on merge; every future capability is placed and built under it without deviation.
