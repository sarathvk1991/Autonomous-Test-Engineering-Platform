# ADR-0040 — Control Point Model and Layer 4 Redefinition

- **Status:** Accepted
- **Date:** 2026-07-24
- **Supersedes:** nothing. **Amends:** ADR-0031 (Authoritative Layer Model — additive: introduces the Control Point Model (Decision 1) and redefines Layer 4's Purpose (Decision 3). An inline amendment note is added at ADR-0031's Layer table, immediately after the L1–L7 rows — see ADR-0031 for the added text. Layers 1–3, 5–7, the three-source freeze, and every other decision in ADR-0031 remain in force, unmodified).
- **Governing design:** none. Evidentiary basis: `docs/proposals/layer-2-feature-engineering-lld.md` (Layer 2 — Feature Engineering LLD, transcribed 2026-07-24, **Status: Submitted — under review, not approved**; source deck `docs/proposals/Feature Engineering Layer.pptx`, provenance only, not itself read for content) and five Copilot prompt assets copied into `docs/reference/automation-poc/prompts/` — `generate-feature.md` (`/create-feature`), `refactor-feature.md` (`/refactor-feature`), `generate-test-data.md` (`/create-test-data`), `validate-generated-feature.md` (`/validate-feature`), `fix-gherkin-lint.md` (`/fix-gherkin`) — and `docs/reference/automation-poc/.gherkin-lintrc` (17-rule configuration). All eight files re-read directly for this ADR.
- **Depends on:** ADR-0031 (Authoritative Layer Model — the layer catalogue this amends); ADR-0016 (Evidence Grounding & Traceability — precedent for a deterministic, non-AI evidence gate); ADR-0017 (Quality Governance Framework — precedent for a deterministic, rule-based release decision, the `QualityDecision` discipline Decision 2 extends to CP2/CP3); ADR-0032 (Layer 1 Capability Freeze — unaffected; this amendment concerns Layers 2–4 only and lifts no Layer 1 freeze); ADR-0037 (Generated Test Suite Target and SUT Binding — source of the `customqa:*` SonarQube profile CP3 evaluates against).
- **Runtime status:** Not applicable. Documentation-only. No code exists for Layer 2, 3, or 4 — `feature_engineering/`, `automation_engineering/`, and `suite_quality_governance/` (ADR-0033's rename target) remain placeholder packages under ADR-0032's freeze. This amendment changes what will be built, not anything running today.

## Problem

ADR-0031's Decision table assigns Layer 4 (Suite Quality Governance) the Purpose: *"Validates Layers 2 and 3 via SonarQube and Gherkin lint; outputs a self-healed, execution-ready suite."* This amendment follows from reviewing the Layer 2 (Feature Engineering) LLD and the Copilot prompt assets it names as Layer 2's own prompt library.

The LLD's own scope (§1 Purpose) lists Gherkin compliance validation, feature governance, AI-assisted remediation, and CP2 validation as Layer 2 responsibilities, not Layer 4's. Its §4 High-Level Flow places them immediately after feature generation, in one pipeline: Validated Requirement Model → Feature Generation Engine → Generated Feature Files → Feature Governance Engine → Gherkin Lint → Compliance Metrics Engine → AI Remediation Engine → CP2 Validation → Validated Feature Package. The LLD agrees with this amendment on where the loop belongs; it is not what this ADR overrides.

Two things are overridden. First, ADR-0031's original placement of lint and self-healing at Layer 4 (Decision 1, below). Second, one part of the LLD itself: its Prompt Registry (§7) names `validate-feature.md` as CP2's validation prompt. The corresponding committed prompt asset for that command (`validate-generated-feature.md`, `/validate-feature`) checks ten items in one undifferentiated Pass/Fail table. Eight are deterministic — feature/scenario/step name-length thresholds, duplicate scenario names, tag consistency, lint-violation count, single-`Feature:`-block, `Background:` applicability. Two are LLM-judged, with no structural distinction from the other eight in the prompt's own output table: "Business readability" (steps describe user intent, not implementation detail) and "Step reusability" (step text is generic enough to reuse across scenarios). `generate-feature.md` and `fix-gherkin-lint.md` independently confirm the loop is meant to sit in-layer, adjacent to generation: `generate-feature.md`'s VALIDATION section instructs the author to lint and fix issues "before proceeding to step definition generation" — the Layer 2 → Layer 3 boundary — and `validate-generated-feature.md`'s own "Next Recommended Action" chains directly to `/fix-gherkin` (repair) or `/create-steps` (Layer 3 handoff), never to a separate governance-layer prompt.

Without this amendment, Layer 4 is either empty — once lint and remediation are correctly placed in Layer 2 — or a duplicate of CP2's and CP3's own review.

## Decision

### Decision 1 — Control Point Model

Each generating layer owns its own control point and its own generate → validate → repair loop, in-layer:

| Layer | Control point | Scope |
|---|---|---|
| L1 | CP1 | Requirement readiness (implemented today, ADR-0011) |
| L2 | CP2 | Gherkin lint + feature governance |
| L3 | CP3 | SonarQube on generated Java, using the `customqa:*` quality profile (ADR-0037) |

Repair loops are bounded at a maximum of **2 LLM remediation attempts**; on exhaustion, escalate to human-in-the-loop.

### Decision 2 — Control-point gates are deterministic

All control-point gates evaluate only deterministic evidence: lint results, coverage counts, tag presence, duplicate detection, compilation results. LLM-generated assessments — for example the "Business readability" and "Step reusability" judgements in `/validate-feature` (Problem, above) — are **advisory only**. They may trigger human review; they may never gate a control point. This preserves the deterministic, non-AI judgement principle ADR-0016 (evidence grounding) and ADR-0017 (the rule-based `QualityDecision`, never an LLM score) already establish for Layer 1's own CP1 gate.

### Decision 3 — Layer 4 redefinition

Layer 4 (Suite Quality Governance) is **not** a Gherkin-lint or per-artifact quality stage — those responsibilities belong to CP2 and CP3 respectively (Decision 1). Layer 4 performs **suite-level integration governance**: checks no single generating layer can make on its own.

- every `SCN-*` has a bound step definition
- every step definition resolves to at least one scenario (no orphaned glue)
- no near-duplicate step definitions across the suite
- the assembled suite compiles
- aggregate policy gate and the release decision on the suite as a whole

This supersedes ADR-0031's original Layer 4 description ("validates layers 2 and 3 via SonarQube + Gherkin lint").

## Consequences

- The package name `suite_quality_governance/` (ADR-0033's rename target) remains correct, and is now more accurate — no further renaming.
- CP2 and CP3 belong to their own layers' future LLDs; this ADR does not specify their rules beyond Decision 1's placement and Decision 2's deterministic-gate boundary.
- The mechanism by which CP3 invokes SonarQube is deferred to the Layer 3 LLD and to ADR-0039 (Execution Backend and CI/CD — still Proposed, not Accepted).
- Layer 4 cannot be implemented until Layers 2 and 3 produce artifacts, since its inputs are cross-artifact.
- No change to ADR-0034 (TestableRequirement contract), ADR-0036 (run/stage state model), or ADR-0037 (generated suite target and SUT binding).
- `docs/reference/` is established as a new non-normative documentation tree under ADR-0038's operational carve-out, alongside `docs/integrations/`, `docs/development/`, and `docs/operations/`. Track A authority (ADR-0038) is unaffected — `docs/reference/automation-poc/` holds external POC artifacts for citation, not architecture-governance content.

## Recommendations (permanent)

1. No future Layer 2 or Layer 3 implementation may wire an LLM-judged check into a control-point gate's pass/fail path — advisory surfacing only (Decision 2).
2. Layer 4's future architecture-freeze ADR must scope itself to suite-level integration checks only; a check expressible as "does this one artifact pass" belongs to CP2 or CP3, not Layer 4 (Decision 3).
3. Any future control point beyond CP1–CP3 follows the same in-layer, bounded-repair pattern (Decision 1) unless a future ADR explicitly departs from it.

## Ownership, scope, and governance

- **Owns:** the Control Point Model (CP1/CP2/CP3 placement and the 2-attempt bounded repair loop), the deterministic-gate/advisory-signal boundary for all control points, and Layer 4's redefinition as suite-level integration governance.
- **Does not own:** CP2's or CP3's own rule catalogue (deferred to Layer 2's and Layer 3's own future LLDs); the SonarQube invocation mechanism (deferred to the Layer 3 LLD and ADR-0039); the `TestableRequirement` contract, run/stage state model, or generated-suite target (unchanged, owned by ADR-0034/ADR-0036/ADR-0037 respectively).
- **Governance:** Accepted, effective immediately. Amends ADR-0031 additively (see ADR-0031's added amendment note); does not supersede it.
