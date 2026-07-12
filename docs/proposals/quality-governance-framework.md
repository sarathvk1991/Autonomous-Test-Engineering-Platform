# Quality Governance Framework — Design Proposal

- **Status:** Proposed (architecture design; CAP-080B / B.1 implement Rule Evaluation and Assessment behind the frozen contracts, unwired from runtime)
- **Capability:** CAP-080 — Quality Governance
- **Milestones covered:** CAP-080A (Governance Freeze) · CAP-080A.1 (Rule Evaluation — §8a) · CAP-080A.2 (Assessment — §8b) · CAP-080A.3 (Decision — §8c; full architecture certification) · CAP-080B (Deterministic Rule Evaluation + Rule Catalogue — §8a.1) · CAP-080B.1 (Deterministic Assessment — §8b.1). Every layer is architecturally frozen; Rule Evaluation and Assessment are now implemented.
- **Governed by:** ADR-0017
- **Depends on:** ADR-0016 (Evidence Grounding & Traceability), ADR-0011 (CP1), the Response Validation Framework.

---

## 1. Problem

The Requirement Intelligence Layer now produces three independent, governed judgements about a single run:

| Result | Question it answers | Owner |
|---|---|---|
| `GroundingResult` | *Is each generated requirement supported by the evidence, and how confidently?* | Grounding (ADR-0016) |
| `ValidationResult` | *Is the response well-formed against the reasoning contract?* | Validation |
| `CP1Result` | *Is the run engineering-ready?* | CP1 (ADR-0011) |

Each is authoritative in its own lane, and each is deliberately **non-gating** and unaware of the others. Grounding measured RC-1 at 21/22 supported with zero hallucinations, but explicitly deferred *enforcement* (ADR-0016 §D5: "measure before you gate"). Validation and CP1 both passed RC-1 with zero findings while grounding was entirely unassessed.

What is missing is the layer that reads all three and renders a **single, governed, explainable release decision**: *given the grounding, validation, and readiness of this run, is it releasable, releasable-with-warnings, or not?* Today that judgement exists nowhere — it would have to be made ad hoc by a human or, worse, implied by whichever gate happened to run last. There is **no Quality Governance subsystem** in the repository (confirmed in Stage 0 of this milestone).

An ungoverned, unexplainable, or score-only release decision is exactly the failure mode the platform's governance discipline exists to prevent. The missing capability is a subsystem that owns the question **"is this run releasable on quality grounds, and precisely why?"**

## 2. Scope of CAP-080A

CAP-080A is a **pure architecture freeze**. It introduces the canonical models, typed identities, governed policy, and the dormant service boundary, and it does **nothing else**:

- no policy evaluation, no quality calculation, no release decision;
- no rule engine, no scoring, no findings generation;
- no runtime wiring, no execution-package artifacts, no CLI;
- no change to Grounding, Validation, CP1, Engineering Context, Analysis, Execution Package, Prompt Governance, the Architecture Version, the Platform Version, or the golden baseline.

It establishes the permanent architecture every later CAP-080 milestone implements *behind an unchanged service contract* — the same discipline ADR-0016 used to land grounding one frozen layer at a time.

## 3. Subsystem & ownership

A new governed subsystem, `requirement_intelligence/quality_governance/`, owns **only**:

- governance,
- policy evaluation,
- quality assessment,
- release decisions,
- governance findings.

It explicitly does **not** own Engineering Context, Analysis, Grounding, Validation, CP1, Execution Package, Reporting, or Serialization. It is a **peer consumer** downstream of the three result-producing subsystems, never an owner of any of their computation. This boundary is frozen (ADR-0017 §D1, Recommendations 1 & 5).

## 4. Canonical models

All models follow the repository conventions: immutable, `frozen`, `extra="forbid"`, camelCase-serialised via `to_camel`, tuple-backed collections, `Schema` base class, validator invariants only, no timestamps or UUIDs on the value objects, and deterministic serialization that round-trips.

```
QualityGovernanceResult      (runtime contract / carrier — the audit record)
  ├── analysis_id, execution_id                (provenance)
  ├── consumed_inputs: (ConsumedResultReference, …)   (which peer results it read)
  ├── assessment: QualityAssessment            (the governance body)
  │     ├── decision: QualityDecision
  │     ├── findings: (QualityFinding, …)
  │     └── summary: QualitySummary
  │           └── category_distribution: (QualityFindingCategoryCount, …)
  └── versions (framework / policy / result-contract), started_at, completed_at
```

- **`QualityDecision`** — the canonical enumeration `PASS` / `PASS_WITH_WARNINGS` / `FAIL` (§5).
- **`QualityFinding`** — a governance problem: category, severity, the source result judged, and a message. Governance findings only — never a Grounding, Validation, or CP1 finding (§6).
- **`QualitySummary`** — the headline: decision, recorded 0-100 roll-up score, governing policy, finding counts (total / warning / failure), and the category distribution (§7).
- **`QualityAssessment`** — the per-run aggregate tying the decision, findings, and summary to the governing policy, with cross-referential/explainability validators.
- **`QualityGovernanceResult`** — the frozen runtime contract; the complete audit record (§D3, Recommendation 3).

Every model is an **assembly target**: the future decision engine populates it; the models compute nothing. The only logic present is validator *invariants* (e.g. a `FAIL` must be accompanied by at least one `FAILURE` finding, so the decision is auditable from the result alone).

## 5. The release decision

`QualityDecision` is a canonical enumeration with frozen semantics:

- **`PASS`** — every governed quality rule is satisfied; releasable with no reservation.
- **`PASS_WITH_WARNINGS`** — no release-blocking rule violated, but one or more warning-level rules are; releasable with recorded reservations.
- **`FAIL`** — at least one release-blocking (failure-level or mandatory) rule violated; must not be released on quality grounds.

The decision is **not** a threshold over a single score (Recommendation 7). CAP-080A defines the vocabulary and semantics only; **no decision engine is implemented**.

## 6. Governance findings

A `QualityFinding` records that a governed `QualityPolicy` rule is violated. Categories include: grounding coverage below policy, hallucination rate exceeded, confidence below threshold, evidence coverage below policy, validation policy violated, CP1 policy violated, engineering readiness not met, mixed-quality evidence, and release-policy violation. These govern a *policy relationship* between an upstream result and the policy — they are not, and never duplicate, the upstream subsystems' own findings.

## 7. Governed policy

`QualityPolicy` is immutable governed data — the "policy is data" discipline of ADR-0015/0016. It prepares for governance of: minimum grounding score, maximum hallucination rate, minimum confidence, minimum evidence coverage, validation severity thresholds, CP1 severity thresholds, required engineering readiness, warning thresholds, failure thresholds, and release rules. Crucially it carries **two threshold bands** (`failure_thresholds`, `warning_thresholds`) plus mandatory `release_rules`, so the decision is rule-based, not score-based (Recommendation 7). `QualityPolicyBuilder` constructs it; `default_quality_policy()` returns the versioned default (`QualityPolicyVersion` 1.0.0). It calculates nothing.

## 8. Runtime boundary (dormant)

`QualityGovernanceService` is the single runtime entry point — an abstract contract with one method, `evaluate(grounding_result, validation_result, cp1_result) -> QualityGovernanceResult`. In CAP-080A it is **dormant**: `DormantQualityGovernanceService.evaluate` raises `NotImplementedError`, and `PlatformContext.create_quality_governance_service()` constructs it with the governed policy and no decision engine. `PlatformContext` remains the only composition root; `create_quality_policy()` is also registered. Nothing consumes the service, so runtime is byte-identical.

## 8a. Rule Evaluation layer (CAP-080A.1)

Between the governed policy and the governance decision sits the **Rule Evaluation** layer, frozen by CAP-080A.1 in the package `requirement_intelligence/quality_governance/evaluation/`. It owns rule evaluation, threshold comparison, policy interpretation, and evaluation explanation — and nothing else.

- **`QualityRuleEvaluator`** — the single owner of rule evaluation, an abstract contract: `evaluate(grounding_result, validation_result, cp1_result) -> RuleEvaluationResult`. The evaluator owns *behaviour*; the `QualityGovernanceService` owns *sequencing* (ADR-0017 §D17). One frozen signature serves every future evaluator — deterministic (CAP-080B), statistical, organization-specific, regulatory, risk-weighted, hybrid (§D19, Recommendation R5).
- **`RuleEvaluation`** — one evaluated governed rule: `evaluation_id`, `rule_id`, `rule_name`, `category` (`RuleCategory`, frozen to six values — Recommendation R1), `severity`, `status` (`PASS` / `FAIL` / `SKIPPED`), `expected_value` / `actual_value` / `threshold` (canonical strings), and a `reason`. Observations only — no score, no decision (Recommendation R4).
- **`RuleEvaluationResult`** — the **permanent evaluation boundary** (§D19): every `RuleEvaluation`, a summary, statistics, and the governing `QualityPolicyVersion`. Self-contained and versioned independently (`RuleEvaluationResultVersion`), it is the sole thing the `QualityGovernanceService` consumes, and every governance decision must be explainable from it alone (§D20, Recommendation 3).

CAP-080B replaces the dormant evaluator with the real **`DeterministicQualityRuleEvaluator`** (see §8a.1) behind this unchanged contract. `PlatformContext.create_quality_rule_evaluator()` now constructs it with the governed policy **and** the governed rule catalogue; it remains **unwired** — nothing consumes it — so runtime is byte-identical.

## 8a.1. Deterministic Rule Evaluation + the Rule Catalogue (CAP-080B)

CAP-080B is a pure *implementation* milestone: it adds the first real evaluator and the governed rule catalogue behind the frozen §8a boundary, changing no signature, ownership, or boundary (ADR-0017 §D25). It introduces `requirement_intelligence/quality_governance/rules/`:

- **`QualityRule`** — one governed rule as **immutable metadata only** (no lambda, no callable, no threshold value). It names the quantity it observes (`QualityMetric`), how it compares (`RuleComparator`), the governed `QualityPolicy` value that bounds it (`QualityThresholdRef`), the severity a violation carries, and — for a mandatory gate — the enforcing `QualityReleaseToggle`. Versioned by `QualityRuleVersion`.
- **`QualityRuleCatalog`** — a deterministic, ordered collection owning ordering, lookup, grouping, and enabled-rule selection only. It evaluates nothing. Versioned by `QualityRuleCatalogVersion`.
- **`QualityRuleBuilder` / `default_quality_rule_catalog()`** — construction only. The governed default catalogue spans all six `RuleCategory` values. Adding, removing, or retuning a rule is a builder change (a versioned catalogue change), never an evaluator change (Recommendation 2).
- **`DeterministicQualityRuleEvaluator`** — identity `deterministic_quality_rule_v1`, version `1.0.0` (`QualityRuleEvaluatorVersion`), recorded on every `RuleEvaluationResult` (`evaluator_name` / `evaluator_version`, additive; `RuleEvaluationResultVersion` → 1.1.0). It iterates the catalogue's enabled rules in canonical order and, per rule, extracts the observed metric, resolves the governed threshold from the policy, and applies one of three comparators (`AT_LEAST` / `AT_MOST` / `MUST_NOT_HOLD`) — with no per-rule branch and no hard-coded number. Pure and deterministic (no randomness, UUID, timestamp, or unordered iteration); a disabled release toggle yields a `SKIPPED` mandatory rule; every evaluation is explainable from the result alone (Recommendation 3/5).

The evaluator stays **unwired** from runtime: no runtime path consumes it, so runtime is byte-identical and the golden baseline is unchanged.

## 8b. Quality Assessment layer (CAP-080A.2)

Above Rule Evaluation and below Governance sits the **Quality Assessment** layer, frozen by CAP-080A.2 in `requirement_intelligence/quality_governance/assessment/`. It owns interpretation of a `RuleEvaluationResult`, assessment logic, and assessment explanation — and nothing else.

- **`QualityAssessmentEngine`** — the single owner of assessment, an abstract contract: `assess(rule_evaluation_result) -> QualityAssessmentResult`. It consumes **only** the `RuleEvaluationResult` (not the three raw results — those are already interpreted upstream; ADR-0017 §D21). One frozen signature serves every future engine — deterministic, risk-weighted, statistical, regulatory, AI-assisted (Recommendation A5).
- **`AssessmentOutcome`** — the overall interpreted observation: an `AssessmentLevel` (`CLEAN` / `ADVISORY_ONLY` / `WARNINGS_PRESENT` / `FAILURES_PRESENT`) plus a blocking-failure observation. It is an **observation of the evaluation state, never a release decision** (Recommendation A1): `FAILURES_PRESENT` may still be released, and `CLEAN` is not itself a `PASS`.
- **`QualityAssessmentResult`** — the **permanent assessment boundary** (§D21): the outcome, summary, statistics, and references to the rules that informed it, plus the governing `AssessmentPolicyVersion`. Self-contained, versioned independently (`QualityAssessmentResultVersion`), and carrying **no** release decision or quality score.
- **`AssessmentPolicy`** — governed interpretation data (precedence, conflict handling, blocking semantics, weighting, recommendations); `AssessmentPolicyBuilder` + `default_assessment_policy()` (`AssessmentPolicyVersion` 1.0.0).

CAP-080B.1 replaces the dormant engine with the real **`DeterministicQualityAssessmentEngine`** (see §8b.1) behind this unchanged contract. `PlatformContext.create_quality_assessment_engine()` now constructs it with the governed policy; it remains **unwired** — nothing consumes it — so runtime is byte-identical.

## 8b.1. Deterministic Assessment Engine (CAP-080B.1)

CAP-080B.1 is a pure *implementation* milestone: it adds the first real assessment engine behind the frozen §8b boundary, changing no signature, ownership, or boundary — and **modifying no frozen model or policy** (ADR-0017 §D26). It adds only `DeterministicQualityAssessmentEngine`:

- **Consumes only `RuleEvaluationResult`.** It interprets one evaluation into a `QualityAssessmentResult`; it never reads Grounding / Validation / CP1 (already interpreted upstream) and imports no evaluator/decision/governance implementation.
- **Entirely policy-governed.** Each failing rule is classified BLOCKING / WARNING / ADVISORY under the policy's `mandatory_failure_is_blocking` / `failure_severity_is_blocking` / `treat_advisory_as_warning` levers (and `include_skipped_as_warning` for skips); the observed `AssessmentLevel` is composed under the policy's `conflict_resolution` and `precedence`. No precedence, blocking rule, or ordering is hard-coded.
- **Observation, never decision.** It emits an `AssessmentLevel` observation, never a `PASS` / `PASS_WITH_WARNINGS` / `FAIL`; a failing mandatory rule is always observed as blocking (honouring the frozen `AssessmentOutcome` invariant).
- **References, never copies.** Each rule that informed the outcome is cited by an `AssessmentFindingReference` (evaluation id, rule id, severity, status, governed note) — the full evaluation stays in the consumed `RuleEvaluationResult`.
- **Deterministic & explainable.** No randomness, UUID, timestamp, or unordered iteration; the assessment id is a pure function of the evaluation (`QualityAssessmentResultId.for_evaluation`); every observation is reconstructable from `QualityAssessmentResult` alone.
- **Recommendations.** The frozen contract has no dedicated recommendations field; the governed `emit_recommendations` flag appends a deterministic, level-keyed clause to `AssessmentOutcome.summary_text` (a dedicated projection is deferred per Recommendation 4). 

The engine stays **unwired** from runtime: nothing consumes it, so runtime is byte-identical and the golden baseline is unchanged.

## 8c. Quality Decision layer (CAP-080A.3)

The final governed layer, frozen by CAP-080A.3 in `requirement_intelligence/quality_governance/decision/`. It owns the release decision, governance decision explanation, and decision-policy interpretation — and nothing else.

- **`QualityDecisionEngine`** — the **sole owner** of the release decision, an abstract contract: `decide(quality_assessment_result) -> QualityDecisionResult`. It consumes **only** the `QualityAssessmentResult` — never the earlier boundaries (ADR-0017 §D23, Recommendation DC1). Only it derives `PASS` / `PASS_WITH_WARNINGS` / `FAIL` (DC2); Assessment stays observational and the service assembles (DC7). One frozen signature serves every future engine — deterministic, statistical, regulatory, organization-specific, AI-assisted (DC5).
- **`QualityDecisionResult`** — the **permanent decision boundary** (§D23): the `QualityDecision`, a summary, statistics, a structured `DecisionExplanation`, and the governing `DecisionPolicyVersion`, tied to the assessment it decided from. Self-contained and versioned independently (`QualityDecisionResultVersion`); every future decision is reconstructable from it alone (DC3).
- **`DecisionPolicy`** — governed data (the base `AssessmentLevel → QualityDecision` mapping plus mandatory `FAIL` gates); `DecisionPolicyBuilder` + `default_decision_policy()` (`DecisionPolicyVersion` 1.0.0). The decision is rule-based, not a percentage (DC4).

In CAP-080A.3 the engine is **dormant**: `DormantQualityDecisionEngine.decide` raises `NotImplementedError`, and `PlatformContext.create_decision_policy()` / `create_quality_decision_engine()` construct it with the governed policy and no logic. Nothing consumes it, so runtime is byte-identical.

## 9. The complete frozen architecture

Every layer of Quality Governance is now architecturally frozen (ADR-0017 certification, CAP-080A.3):

```
GroundingResult ┐
ValidationResult├─▶ QualityRuleEvaluator ─▶ RuleEvaluationResult ─▶ QualityAssessmentEngine ─▶ QualityAssessmentResult
CP1Result       ┘                                                                                    │
                                                              QualityDecisionEngine ─▶ QualityDecisionResult
                                                                                                     │
                                                        QualityGovernanceService ─▶ QualityGovernanceResult ─▶ Execution Package
```

The four layers implement, independently and without redesign (Recommendation 6; DC6/DC7 — each stage strictly precedes the next, and the orchestrating service never absorbs their logic):

```
Policy  →  Rule Evaluation  →  Quality Assessment  →  Release Decision
```

## 10. Execution package (future)

The future artifacts `quality_governance.json`, `quality_report.md`, and `quality_score.md` will be **pure projections** of a `QualityGovernanceResult`, exactly following the Grounding serialization rule (ADR-0016 §D16, Recommendation 4). The Execution Package will compute nothing.

## 11. Implementation roadmap (non-normative)

1. **CAP-080A** — governance orchestration architecture: models, identities, policy, dormant service. Freeze.
2. **CAP-080A.1** — the Rule Evaluation architecture: `RuleEvaluation` / `RuleEvaluationResult` models, identities, and the dormant `QualityRuleEvaluator`. Freeze.
3. **CAP-080A.2** — the Assessment architecture: `QualityAssessmentResult` / `AssessmentOutcome` models, `AssessmentPolicy`, identities, and the dormant `QualityAssessmentEngine`. Freeze.
4. **CAP-080A.3** — the Decision architecture: `QualityDecisionResult` model, `DecisionPolicy`, identities, and the dormant `QualityDecisionEngine`; **full architecture certification**. Freeze. *Every layer is now frozen.*
5. **CAP-080B** — the first (deterministic) `QualityRuleEvaluator` and the governed Rule Catalogue (`rules/`), behind the frozen contract; evaluator identity recorded on the result. A pure implementation milestone (no architectural work), unwired from runtime. Done.
6. **CAP-080B.1** *(this milestone)* — the first deterministic `QualityAssessmentEngine`, behind the frozen `assess(...)` contract; policy-governed interpretation, references-not-copies, unwired from runtime. Done.
7. **CAP-080B.2** — the first deterministic `QualityDecisionEngine`, behind the frozen `decide(...)` contract.
8. **CAP-080D** — runtime activation (the `QualityGovernanceService` sequencing the pipeline) and execution-package projection; golden re-baseline.
9. **Later** — enforcement/gating, and the future extensions of Recommendation 8.

## 12. Terminology

"Quality Governance" (this subsystem, the release decision) is distinct from the placeholder root-level `quality_governance/` **Quality Governance Layer** (CP2+, Phase 4) and from `ContextGrounding` / requirement grounding. The three are complementary and kept terminologically distinct.

---

The full architectural decisions and invariants — the governance-orchestration recommendations (1–8), the Rule Evaluation decisions (§D17–D20 / R1–R5), the Assessment decisions (§D21 / A1–A5), the Decision decisions (§D23 / DC1–DC7), and the **Final Quality Governance Architecture Certification** — are recorded in **ADR-0017**.
