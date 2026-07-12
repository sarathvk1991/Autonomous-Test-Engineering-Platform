# ADR-0017 — Quality Governance Framework

- **Status:** Proposed (design only — CAP-080A / CAP-080A.1 introduce no runtime behaviour)
- **Date:** 2026-07-12 (Proposed) · CAP-080A.1 (Rule Evaluation freeze) 2026-07-12
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** CAP-080A.1 adds the Rule Evaluation layer (§D17–D20).
- **Governing design:** `docs/proposals/quality-governance-framework.md`
- **Depends on:** ADR-0016 (Evidence Grounding & Traceability), ADR-0011 (CP1 Validation Engine), the Response Validation Framework — Quality Governance consumes their completed results.
- **Runtime status:** Not yet implemented. This ADR governs the architecture; later CAP-080 milestones implement it and re-baseline the golden dataset.

## Problem

The Requirement Intelligence Layer produces three independent, governed judgements per run — `GroundingResult` (is each requirement supported?), `ValidationResult` (is the response well-formed?), and `CP1Result` (is the run engineering-ready?). Each is authoritative in its own lane and each is deliberately **non-gating** and unaware of the others (ADR-0016 §D5 explicitly deferred grounding enforcement: "measure before you gate").

**No subsystem reads all three and renders a single, governed, explainable release decision.** That judgement — *is this run releasable on quality grounds, and precisely why?* — exists nowhere in the repository today (confirmed by the Stage 0 assessment: there is no Quality Governance subsystem). Left unbuilt, the decision defaults to ad-hoc human judgement or is implied by whichever gate ran last; built carelessly, it becomes an opaque percentage that can pass a hallucinating run or fail a sound one.

## Decision

Introduce a new governed subsystem, **`requirement_intelligence/quality_governance/`**, that owns Quality Governance: policy evaluation, quality assessment, release decisions, and governance findings. It:

1. Introduces canonical, immutable models — `QualityFinding`, `QualitySummary`, `QualityAssessment`, `QualityGovernanceResult`, and the `QualityDecision` enumeration (`PASS` / `PASS_WITH_WARNINGS` / `FAIL`) — following the `Schema` conventions and the typed-identity pattern of ADR-0015/0016.
2. Introduces strongly typed identities — `QualityPolicyId`, `QualityAssessmentId`, `QualityGovernanceResultId`, and the independent version axes `QualityGovernanceVersion`, `QualityPolicyVersion`, `QualityAssessmentVersion`, `QualityGovernanceResultVersion` — deterministic value objects, no UUIDs, no timestamps, no randomness.
3. Introduces a governed `QualityPolicy` (immutable data: two threshold bands, per-source severity budgets, mandatory release rules) with a `QualityPolicyBuilder` and `default_quality_policy()`.
4. Fixes the single runtime boundary — `QualityGovernanceService.evaluate(grounding_result, validation_result, cp1_result) -> QualityGovernanceResult` — as an **abstract, dormant contract**. `PlatformContext` gains `create_quality_policy()` and `create_quality_governance_service()`.

Quality Governance runs **after** Grounding, Validation, and CP1, consuming only their completed results; it is a **peer consumer** that owns none of their computation. Grounding, Validation, CP1, Engineering Context, Analysis, Prompt Governance, and the Execution Package are **unchanged**.

**CAP-080A establishes the architecture only.** No policy is evaluated, no score is calculated, no decision is derived, and nothing is wired into a runtime path. Runtime behaviour is byte-identical; the golden baseline is unchanged; the Architecture Version remains 1.2.0.

The full model and roadmap is in `docs/proposals/quality-governance-framework.md`.

---

## D1 — Why Quality Governance is a new subsystem, not an extension of Grounding, Validation, or CP1

Quality Governance answers a question none of the three existing results asks. Grounding judges *evidence support*; Validation judges *form*; CP1 judges *engineering readiness*. Each is authoritative and non-gating in its own lane. The release decision is a judgement *across* all three — "given these three verdicts and a governed policy, is the run releasable?" — and it belongs to a distinct owner. Folding it into any one of the three would give that subsystem two responsibilities and force every governance-policy change to be a Grounding/Validation/CP1 change — exactly the coupling ADR-0001 forbids and ADR-0015/0016 rejected for orchestration and grounding. Quality Governance is a distinct responsibility with a distinct owner, and a **consumer only** of the three results (Recommendation 1).

## D2 — Why the release decision is rule-based, not score-based

A single quality percentage is the wrong primitive. It cannot express "the grounding score is high, but the hallucination rate breached a mandatory gate, so FAIL," nor "the score is middling, but every mandatory rule is satisfied, so PASS." The architecture therefore separates a recorded numeric roll-up (`QualitySummary.overall_quality_score`, informational) from the decision (`QualityDecision`, derived from governed rule evaluation). The governed `QualityPolicy` carries **two numeric bands** (`failure_thresholds`, `warning_thresholds`) and **mandatory `release_rules`**, precisely so a future engine can produce the outcomes above. This is frozen in Recommendation 7 and is why no decision engine is a percentage calculation.

## D3 — Why `QualityGovernanceResult` is the complete, self-contained audit record

The runtime contract is `QualityGovernanceResult`: a peer to `GroundingResult` / `ValidationResult` / `CP1Result`. It carries the assessment (decision, findings, summary), the governing policy identity/version, and — via `ConsumedResultReference` — the identity and version of each upstream result it consumed. This is a deliberate design choice: the verdict must be **completely explainable from this one object**, with no need to re-run governance or inspect any runtime service, Grounding, Validation, or CP1 (Recommendation 3). The model records *provenance* of the consumed inputs, never their contents, so the audit record is legible and self-contained without embedding or coupling to the upstream aggregates. The assessment's validator enforces the explainability invariant structurally: a `FAIL` cannot exist without a `FAILURE` finding to explain it.

## D4 — Why the models compute nothing (assembly targets only)

Every canonical model is `frozen`, tuple-backed, camelCase, and free of timestamps/UUIDs, exactly like the grounding models. None computes a value: the future decision engine populates them. The only logic present is validator *invariants* that enforce cross-referential integrity and explainability (summary counts match the findings; the decision is consistent with and explained by them; provenance on the result matches the assessment). Introducing the models fully frozen — before any engine exists — forces their shape to be designed for every future decision layer, not retrofitted around the first one, and lets each subsequent milestone land behind an unchanged contract.

## D5 — Why identities are deterministic and independently versioned

`QualityAssessmentId.for_run(analysis_id, execution_id)` and `QualityGovernanceResultId.for_assessment(assessment_id)` are **pure functions** of their inputs — no clock, no UUID — so the same run always mints the same ids and a verdict is reproducible and comparable across runs. Four version axes (`QualityGovernanceVersion`, `QualityPolicyVersion`, `QualityAssessmentVersion`, `QualityGovernanceResultVersion`) are distinct typed value objects that advance **independently**: this is what lets policy evolve without forcing a contract change (Recommendation 2) and lets the runtime contract evolve without forcing a framework change. Like ADR-0015 §D5 and ADR-0016 §D6, no existing identifier is retyped; the change is purely additive.

## D6 — Why the service boundary is fixed before any behaviour (dormant)

The subsystem exposes exactly one runtime entry point: `QualityGovernanceService`, an abstract contract with a single method — `evaluate(grounding_result, validation_result, cp1_result) -> QualityGovernanceResult`. Everything else in the package (models, identities, policy) is internal. The service depends only on the three frozen **result contracts** it consumes — never on any *implementation* class (no `GroundingStrategy`, `SupportClassificationEngine`, `ConfidenceCalculator`, `ResponseValidator`, `CP1Service`, engine, or pipeline). Fixing the boundary *before* implementing any behaviour is what lets each later milestone — rule evaluation, assessment, decision, runtime activation — land behind the unchanged `evaluate` signature, exactly as ADR-0016 §D7 did for `GroundingService.assess`.

**CAP-080A establishes the boundary only.** `evaluate` is abstract and the registered `DormantQualityGovernanceService` raises `NotImplementedError`; `PlatformContext.create_quality_governance_service()` constructs it with the governed policy and **no decision engine**. It is dormant — no runtime path consumes it, guarded by a containment test that permits only `PlatformContext` to name the service outside the package — so runtime behaviour is byte-identical.

---

## Rule Evaluation layer (CAP-080A.1)

CAP-080A froze *governance orchestration* (the service, models, policy, decision). CAP-080A.1 freezes the layer beneath it — **Rule Evaluation** — before any rule executes. It introduces a new package `requirement_intelligence/quality_governance/evaluation/`, the canonical `RuleEvaluation` / `RuleEvaluationResult` models, the typed identities `RuleEvaluationId` / `RuleEvaluationResultId` / `RuleEvaluationVersion` / `RuleEvaluationResultVersion`, and the dormant `QualityRuleEvaluator` contract. It performs no rule evaluation and wires nothing.

### D17 — Why Rule Evaluation is a layer independent of governance orchestration

Evaluating a governed rule ("is the grounding score ≥ the policy's failure bar?") and *deciding a release* ("given every evaluated rule, is the run releasable?") are different jobs with different owners. Fusing them would put threshold comparison, mandatory-rule logic, quality scoring, and the release decision in one class — and every rule change would become a change to the decision engine. The architecture therefore splits them: `QualityRuleEvaluator` owns **behaviour** (rule evaluation), `QualityGovernanceService` owns **sequencing** (invoke the evaluator, then assess, then decide). This mirrors how `GroundingService` orchestrates while a `GroundingStrategy` matches (ADR-0016 §D7). The four-layer sequence of Recommendation 6 — Policy → Rule Evaluation → Quality Assessment → Release Decision — is now realised with Rule Evaluation as a first-class, separately-owned layer.

### D18 — What the evaluator owns, and what it must not

`QualityRuleEvaluator` owns **only**: evaluating policy rules, threshold comparison, mandatory-rule evaluation, and producing a `RuleEvaluationResult`. It does **not** own governance orchestration, the release decision, quality scoring, serialization, reporting, the execution package, or builders — each a separate owner. Like the service (Recommendation 1), it is a **consumer only** of `GroundingResult` / `ValidationResult` / `CP1Result`: it never re-runs those subsystems, inspects prompts/Engineering Context/Gemini responses, or imports an upstream *implementation* class (enforced by containment tests over the `evaluation/` package; the evaluation *models* import no upstream subsystem at all, and only the evaluator module names the three result contracts).

### D19 — Why `RuleEvaluationResult` is the permanent evaluation boundary

The contract between Rule Evaluation and Quality Governance is fixed as `RuleEvaluationResult` — a canonical, immutable, versioned, self-contained record of every `RuleEvaluation`, a summary, statistics, and the governing `QualityPolicyVersion`. Freezing this *before* any evaluator exists is deliberate: it forces the shape to serve every future evaluator. Because the boundary is a value object (not a tuple, not a bare verdict), a richer evaluator can populate the same fields without widening the type. `RuleEvaluationResultVersion` versions the boundary schema **independently** of `RuleEvaluationVersion` (the per-rule schema) and of every quality-governance version axis (Recommendation 2). One frozen contract — `evaluate(grounding_result, validation_result, cp1_result) -> RuleEvaluationResult` — lets deterministic (CAP-080B), statistical, semantic, organization-specific, regulatory, risk-weighted, and hybrid evaluators all plug in unchanged (Recommendation 5).

### D20 — Why evaluation is pure observation, explainable from the result alone

`RuleEvaluationResult` carries **observations only** — status, expected/actual/threshold values, reasons, counts, distributions. It carries **no** quality score, **no** release decision, and **no** governance summary; those belong to later layers (Recommendation 4). This is what makes the explainability invariant of Recommendation 3 hold *through* the evaluation layer: every future governance decision must be explainable entirely from `RuleEvaluationResult`, with no need to re-run evaluation or inspect a policy, runtime service, Grounding, Validation, or CP1. The result's validator enforces that its summary counts and per-rule identities agree with its evaluations, so the record is internally auditable. `PlatformContext.create_quality_rule_evaluator()` constructs the dormant evaluator with the governed policy and no rule set; it is dormant — nothing consumes it, guarded by a containment test permitting only `PlatformContext` to name it outside the package — so runtime is byte-identical.

### Rule Evaluation recommendations (CAP-080A.1, mandatory)

- **R1 — Rule categories are frozen now.** `RuleCategory` = Grounding, Validation, CP1, Cross-Subsystem, Mandatory Release, Advisory. Future policies **extend** these categories rather than invent new evaluation mechanisms.
- **R2 — Rules gain deterministic identity over time.** Each evaluated rule already carries a deterministic `RuleEvaluationId`; a future governed rule model (`RuleId`, `RuleVersion`, `RuleCategory`, `RuleSeverity`) will give the *rules themselves* stable identity for historical traceability and policy evolution, without changing `RuleEvaluationResult`.
- **R3 — Evaluation strictly precedes assessment.** The sequence Policy → Rule Evaluation → Quality Assessment → Release Decision is frozen. Assessment must never evaluate rules itself; the decision must never evaluate rules itself.
- **R4 — Pure evaluation.** `RuleEvaluationResult` contains only observations — never a quality score, release decision, or governance summary.
- **R5 — Future evaluators reuse the identical contract.** Deterministic (CAP-080B), statistical, organization-specific, regulatory, risk-weighted, and hybrid evaluators all implement `evaluate(...) -> RuleEvaluationResult` unchanged.

---

## Architectural Recommendations (mandatory — frozen by this ADR)

### Recommendation 1 — Governance Scope Freeze (consumer only)

Quality Governance is a **consumer only**. It must never re-run Grounding, Validation, or CP1; never inspect prompts, the Engineering Context, or Gemini responses; and never own any upstream computation. It consumes only `GroundingResult`, `ValidationResult`, and `CP1Result`. Enforced by dependency-boundary containment tests: the data layer imports nothing from those subsystems, and the package imports no upstream implementation class.

### Recommendation 2 — Independent Policy Evolution

`QualityPolicy` evolves independently of `GroundingPolicy`, Validation profiles, and CP1 rules. A `QualityPolicyVersion` change is a governed **data** change under the golden re-baseline procedure and must **never** require a change to `QualityGovernanceResult`, `QualityAssessment`, or the service contract — only governed data changes. The distinct version axes (D5) make this structural.

### Recommendation 3 — Decision Explainability

Every future `PASS` / `PASS_WITH_WARNINGS` / `FAIL` decision must be **completely explainable using only `QualityGovernanceResult`**. No consumer should ever need to re-run governance or inspect a runtime service, Grounding, Validation, or CP1. The result is the complete audit record (D3), and the assessment validator enforces that a decision is explained by its findings.

### Recommendation 4 — Execution Package Boundary

The future execution artifacts `quality_governance.json`, `quality_report.md`, and `quality_score.md` are **pure projections** of `QualityGovernanceResult`, reproducible from it alone, computing nothing — exactly the serialization rule ADR-0016 §D16 introduced for Grounding. The Execution Package will never import a governance engine, the service, or the policy evaluator.

### Recommendation 5 — Dependency Direction

The dependency graph is frozen one-way:

```
GroundingResult  ┐
ValidationResult ├─▶ Quality Governance ─▶ QualityGovernanceResult
CP1Result        ┘
```

Quality Governance is a **peer consumer**. It never owns Grounding, Validation, or CP1.

### Recommendation 6 — Decision Layer Separation

Four distinct architectural layers are frozen and may be implemented independently without redesign:

```
Policy  →  Rule Evaluation  →  Quality Assessment  →  Release Decision
```

### Recommendation 7 — Release Decision Independence

`QualityDecision` is **not** derived directly from a numeric score. The future decision engine evaluates governed rules (the two threshold bands plus mandatory release rules). This permits: a high score that FAILs (mandatory hallucination gate breached), a medium score that PASSes with warnings, and a lower score that PASSes because all mandatory rules are satisfied. Governance never becomes a simple percentage calculation.

### Recommendation 8 — Future Extensibility (non-normative)

The following future extensions must plug into the existing architecture **without** changing the canonical models or runtime contract: organization-specific governance policies, domain-specific rule packs, regulatory/compliance governance profiles, risk-weighted governance, human approval workflows, and multi-stage release gates.

---

## Trade-offs

- **A governance layer adds a fourth judgement per run.** Accepted: the three existing results are deliberately non-gating and lane-scoped; a single explainable release decision across them is the capability that was missing, not redundant with any of them.
- **Governed defaults are illustrative until calibrated.** The CAP-080A default policy's numbers are governed data, not yet tuned against a corpus. Accepted: tuning is a versioned policy change under the golden re-baseline procedure (Recommendation 2), and no runtime consumes the values yet.
- **A re-baseline is required at runtime activation.** Adding artifacts and manifest fields will change golden checksums. Accepted: the golden baseline's re-baseline procedure exists precisely for intentional additive change; CAP-080A changes nothing.
- **Two "Quality Governance" names now coexist.** This subsystem (the release decision) is distinct from the placeholder root-level Quality Governance Layer (CP2+, Phase 4). Kept terminologically distinct in the proposal and here.

## Future evolution

- The rule-evaluation, assessment, and decision layers (Recommendation 6), landing behind the unchanged `evaluate` contract.
- **Enforcement / gating** — a later, deliberate decision that will *consume* `QualityGovernanceResult` (mirroring ADR-0016 §D5's "measure before you gate").
- The execution-package projection (Recommendation 4) and its golden re-baseline.
- The non-normative extensions of Recommendation 8.
- Promotion of the shared version/identity value-objects to `shared/` (the debt ADR-0015 §C and ADR-0016 already name).

## Ownership, runtime position, governance

- **Owns:** governance, rule evaluation, policy evaluation, quality assessment, release decisions, governance findings.
- **Does not own:** Engineering Context, Analysis, Grounding, Validation, CP1, Execution Package, Reporting, Serialization.
- **Runtime position:** `… → Grounding → Validation → CP1 → QualityRuleEvaluator → RuleEvaluationResult → QualityGovernanceService → QualityGovernanceResult → Execution Package`, consuming the three completed results; non-gating and dormant in CAP-080A / CAP-080A.1.
- **Governance:** registered as CAP-080 in the Platform Capability Matrix at implementation time; the golden baseline is re-based then. This ADR is **Proposed** until that milestone accepts it.
