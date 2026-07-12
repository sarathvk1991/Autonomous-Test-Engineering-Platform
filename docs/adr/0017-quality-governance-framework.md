# ADR-0017 — Quality Governance Framework

- **Status:** Proposed (architecture design; CAP-080B begins implementation behind the frozen contracts, still unwired from runtime)
- **Date:** 2026-07-12 (Proposed) · CAP-080A.1 (Rule Evaluation) · CAP-080A.2 (Assessment) · CAP-080A.3 (Decision + full certification) · CAP-080B (Deterministic Rule Evaluation Engine V1 + Rule Catalogue) · CAP-080B.1 (Deterministic Assessment Engine) · CAP-080B.1.1 (QualityAssessmentResult runtime-contract freeze) · CAP-080B.2 (Deterministic Decision Engine) · CAP-080C (Governance runtime activation) 2026-07-12
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** CAP-080A.1 adds Rule Evaluation (§D17–D20); CAP-080A.2 adds Assessment (§D21) and reserves Decision (§D22); CAP-080A.3 freezes Decision (§D23) and certifies the complete subsystem; CAP-080B implements the first deterministic rule evaluator and the governed Rule Catalogue (§D25); CAP-080B.1 implements the first deterministic assessment engine (§D26); CAP-080B.1.1 freezes `QualityAssessmentResult` as the Assessment→Decision runtime contract (§D27); CAP-080B.2 implements the first deterministic decision engine (§D28); CAP-080C activates the governance runtime orchestration (§D29).
- **Governing design:** `docs/proposals/quality-governance-framework.md`
- **Depends on:** ADR-0016 (Evidence Grounding & Traceability), ADR-0011 (CP1 Validation Engine), the Response Validation Framework — Quality Governance consumes their completed results.
- **Runtime status:** The full subsystem is implemented — Rule Evaluation (CAP-080B), Assessment (CAP-080B.1), Decision (CAP-080B.2), and the `DefaultQualityGovernanceService` orchestration (CAP-080C) — but **unwired**: no runtime path calls `evaluate`, so runtime behaviour is byte-identical and the golden baseline is unchanged. This ADR governs the architecture; CAP-080D wires the service into the execution pipeline and re-baselines the golden dataset.

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

## Quality Assessment layer (CAP-080A.2)

CAP-080A.1 froze *rule evaluation*. CAP-080A.2 freezes the layer above it — **Quality Assessment** — before any interpretation runs, and formally reserves the **Decision** layer beyond it. It introduces a new package `requirement_intelligence/quality_governance/assessment/`, the canonical `QualityAssessmentResult` / `AssessmentOutcome` / `AssessmentSummary` / `AssessmentStatistics` / `AssessmentDistributionEntry` / `AssessmentFindingReference` models, the governed `AssessmentPolicy` (+ builder), the typed identities `AssessmentPolicyId` / `AssessmentPolicyVersion` / `AssessmentOutcomeVersion` / `QualityAssessmentResultId` / `QualityAssessmentResultVersion`, and the dormant `QualityAssessmentEngine`. It performs no assessment and wires nothing.

### D21 — Quality Assessment is a layer between Rule Evaluation and Governance

Without a distinct Assessment layer, `QualityGovernanceService` would have to both *interpret* the rule evaluation and *decide* the release — becoming an assessment engine and a decision engine at once, exactly the fusion Recommendation 3 forbids. The architecture therefore inserts **Quality Assessment** between them.

**Ownership (frozen).** `QualityAssessmentEngine` owns **only**: interpretation of a `RuleEvaluationResult`, assessment logic, and assessment explanation. It does **not** own rule evaluation, governance orchestration, the release decision, serialization, reporting, the execution package, or runtime wiring — each a separate owner.

**Assessment vs Rule Evaluation.** Rule Evaluation asks *did each governed rule pass?* and emits per-rule observations. Assessment asks *what does the whole evaluation mean?* and emits one interpreted `AssessmentOutcome` (an `AssessmentLevel` — `CLEAN` / `ADVISORY_ONLY` / `WARNINGS_PRESENT` / `FAILURES_PRESENT` — plus a blocking-failure observation). The level is an **observation of the evaluation state, never a release decision** (Recommendation 1): a `FAILURES_PRESENT` level may still be released if the failing rules are advisory, and `CLEAN` is not itself a `PASS`.

**Assessment vs Governance.** Governance *sequences* the pipeline and assembles the final `QualityGovernanceResult`; Assessment *interprets*. The service will invoke the engine (through the future Decision layer) and own none of its logic.

**Dependency inversion (frozen).** The engine depends on the `QualityAssessmentEngine` abstraction, never a concrete engine, and consumes **only** the `RuleEvaluationResult` contract — not `GroundingResult` / `ValidationResult` / `CP1Result` (already interpreted upstream), and no upstream *implementation* class. Enforced by containment tests over the `assessment/` package.

**Permanent contract (frozen).** `QualityAssessmentResult` is the canonical, immutable, self-contained interpretation of one `RuleEvaluationResult`. `assess(rule_evaluation_result) -> QualityAssessmentResult` is the permanent signature; deterministic, risk-weighted, statistical, regulatory, and AI-assisted engines all implement it unchanged (Recommendation 5). `QualityAssessmentResultVersion` versions the contract, `AssessmentOutcomeVersion` the inner model, `AssessmentPolicyVersion` the policy — independently (Recommendation 4).

**Identity note (collision avoidance).** The name `QualityAssessmentVersion` is already owned by CAP-080A's governance `QualityAssessment` (a different model — the governance body carrying the decision). To keep version axes independent and collision-free, the Assessment subsystem versions its inner observation model with `AssessmentOutcomeVersion` and its contract with `QualityAssessmentResultVersion`, rather than redefining the taken name.

### D22 — The Decision layer is architecturally reserved (documentation only)

CAP-080A.2 **reserves** — and does not implement — the Decision layer. No code, model, identity, policy, builder, or runtime for it is introduced here. The permanent future architecture is:

```
QualityAssessmentResult → QualityDecisionEngine → QualityDecisionResult → QualityGovernanceService
```

**Frozen ownership.** The future `QualityDecisionEngine` will own **only** the release decision — deriving `PASS` / `PASS_WITH_WARNINGS` / `FAIL` from a `QualityAssessmentResult` and a governed decision policy (Recommendation 2). **Assessment never derives a release status, and neither does `QualityGovernanceService`** (Recommendation 1/2/3). The service remains a pure orchestrator across all four layers — Rule Evaluation → Assessment → Decision → Governance — absorbing business logic from none of them (Recommendation 3). This reservation exists now so the Decision layer lands later behind a frozen boundary, exactly as Assessment and Rule Evaluation did, with no redesign.

### Quality Assessment recommendations (CAP-080A.2, mandatory)

- **A1 — Assessment contains no decisions.** Assessment must never produce `PASS` / `PASS_WITH_WARNINGS` / `FAIL`; it produces observations only.
- **A2 — Decision owns release status.** The future Decision layer alone derives `PASS` / `PASS_WITH_WARNINGS` / `FAIL`; Assessment never does, and `QualityGovernanceService` never does.
- **A3 — The service remains a pure orchestrator.** The long-term flow Rule Evaluation → Assessment → Decision → Governance is frozen; the service must never absorb business logic from any stage.
- **A4 — Independent versioning.** Assessment and the future Decision subsystem each carry their own identity and version axes, like Matching, Classification, Confidence, and Rule Evaluation.
- **A5 — Extensibility.** Future assessment engines (deterministic, risk-weighted, statistical, regulatory, AI-assisted) and future decision engines (deterministic, organization-specific, risk-aware, compliance) all implement the same frozen contracts without architectural change.

---

## Quality Decision layer (CAP-080A.3)

CAP-080A.2 *reserved* the Decision layer (§D22). CAP-080A.3 **realises the reservation as a frozen architecture** — the final missing layer — and adds no runtime behaviour. It introduces a new package `requirement_intelligence/quality_governance/decision/`, the canonical `QualityDecisionResult` / `DecisionSummary` / `DecisionStatistics` / `DecisionExplanation` models, the governed `DecisionPolicy` (+ builder), the typed identities `DecisionPolicyId` / `DecisionPolicyVersion` / `DecisionVersion` / `QualityDecisionResultId` / `QualityDecisionResultVersion`, and the dormant `QualityDecisionEngine`. With this, every layer of Quality Governance is architecturally frozen.

### D23 — Quality Decision is the sole owner of the release decision

The `QualityDecisionEngine` owns **only** the release decision, governance decision explanation, and decision-policy interpretation. It is the **sole owner** of `PASS` / `PASS_WITH_WARNINGS` / `FAIL` (Recommendation 2): Assessment stays observational (its `AssessmentLevel` is a state observation, not a decision), and `QualityGovernanceService` only assembles — it never derives the decision (Recommendation 7). This closes the concern §D22 anticipated: no decision logic can leak into the service, because a distinct, separately-owned layer owns it.

**Consumes only `QualityAssessmentResult` (frozen).** The engine reads **only** the assessment result — never `RuleEvaluationResult`, `GroundingResult`, `ValidationResult`, or `CP1Result`, and no upstream *implementation* class (Recommendation 1). Those are already interpreted upstream. Enforced by containment tests over the `decision/` package.

**Governed entirely by `DecisionPolicy` (frozen).** The engine hard-codes no mapping and no threshold; the governed `DecisionPolicy` carries the base `AssessmentLevel → QualityDecision` mapping *and* the mandatory gates (`fail_on_blocking_failure` / `fail_on_mandatory_failure`) that can force `FAIL` regardless of the mapping (Recommendation 4). Tuning is a versioned policy change (Recommendation 4/independent versioning), never an engine change. This keeps the decision rule-based, not a percentage.

**Permanent contract (frozen).** `QualityDecisionResult` is the canonical, immutable, self-contained release decision — the `QualityDecision`, a summary, statistics, a structured `DecisionExplanation`, and the governing policy identity/version, tied to the assessment it decided from. `decide(quality_assessment_result) -> QualityDecisionResult` is the permanent signature; deterministic, statistical, regulatory, organization-specific, and AI-assisted engines all implement it unchanged (Recommendation 5). `QualityDecisionResultVersion` versions the contract, `DecisionVersion` the inner explanation, `DecisionPolicyVersion` the policy — independently.

**Explainability (frozen).** Every future decision is reconstructable **from `QualityDecisionResult` alone** — no re-running the engine, and no inspecting the policy, Assessment, Rule Evaluation, Grounding, Validation, or CP1 (Recommendation 3). The `DecisionExplanation` (primary reason, contributing factors, applied governed rules, recommendations) is structured data, never generated prose.

### Quality Decision recommendations (CAP-080A.3, mandatory)

- **DC1 — Decision consumes only `QualityAssessmentResult`.** Never `RuleEvaluationResult`, `GroundingResult`, `ValidationResult`, or `CP1Result`.
- **DC2 — Decision is the sole owner of `PASS` / `PASS_WITH_WARNINGS` / `FAIL`.** Assessment remains observational; the service never derives them.
- **DC3 — Every governance decision is reconstructable entirely from `QualityDecisionResult`.**
- **DC4 — Decision behaviour is governed entirely by `DecisionPolicy`.**
- **DC5 — Future engines (deterministic, statistical, regulatory, organization-specific, AI-assisted) reuse the identical `decide(...)` contract.**
- **DC6 — Decision never orchestrates; `QualityGovernanceService` orchestrates.**
- **DC7 — `QualityGovernanceService` assembles only; it never derives `PASS` / `FAIL`.**

---

## Deterministic Rule Evaluation Engine + Rule Catalogue (CAP-080B)

CAP-080A.1 froze the Rule Evaluation *boundary* (§D17–D20) with a dormant `QualityRuleEvaluator`. CAP-080B implements the **first real evaluator** behind that unchanged boundary and introduces the governed **Quality Rule Catalogue** it iterates. It is a pure *implementation* milestone: no signature, ownership, or boundary changes; Assessment, Decision, Governance, and the Execution Package are untouched; and the evaluator stays **unwired** from runtime, so runtime is byte-identical and the golden baseline is unchanged. It introduces a new package `requirement_intelligence/quality_governance/rules/` (`QualityRule`, `QualityRuleCatalog`, `QualityRuleBuilder`), the typed versions `QualityRuleVersion` / `QualityRuleCatalogVersion` / `QualityRuleEvaluatorVersion`, and `DeterministicQualityRuleEvaluator`.

### D25 — Why rules are a governed catalogue and the evaluator carries only mechanism

The naïve first evaluator embeds each rule as an `if` branch with a literal threshold. That fuses three things that must stay separate: *which* rules exist (governance), *what* they compare against (policy), and *how* comparison happens (behaviour). CAP-080B splits them:

- **The Rule Catalogue owns metadata.** A `QualityRule` is immutable data — no lambda, no callable, no threshold value, no comparison. It *names* the quantity it observes (`QualityMetric`), how it is compared (`RuleComparator`), which governed `QualityPolicy` value bounds it (`QualityThresholdRef`), the severity a violation carries, and — for a mandatory gate — the governed `QualityReleaseToggle` that enforces it. `QualityRuleCatalog` owns ordering, lookup, grouping, and enabled-rule selection only. Adding, removing, or retuning a rule is a `QualityRuleBuilder` change — a versioned catalogue change under the golden re-baseline procedure — never an evaluator change (Recommendation 2). The default catalogue spans all six `RuleCategory` values (grounding, validation, CP1, cross-subsystem, mandatory-release, advisory).
- **The `QualityPolicy` owns every threshold.** The evaluator hard-codes no number; each numeric bound is resolved from the policy field a rule names via `QualityThresholdRef`. Retuning a threshold is a policy-version change that flips outcomes without touching the evaluator or the catalogue.
- **The evaluator owns only generic mechanism.** `DeterministicQualityRuleEvaluator` iterates the catalogue's enabled rules in canonical order and, per rule, invokes three generic mechanisms — metric extraction (the *actual*), threshold resolution (the *expected*/bound), and one of three comparators (`AT_LEAST` / `AT_MOST` / `MUST_NOT_HOLD`). It contains **no per-rule branch**: its `if`-chains dispatch on the `QualityMetric` and `QualityThresholdRef` *vocabularies*, applied uniformly to every rule.

**Evaluator identity (frozen).** Every `RuleEvaluationResult` now records the evaluator that produced it — `evaluator_name` (`deterministic_quality_rule_v1`) and `evaluator_version` (`QualityRuleEvaluatorVersion` 1.0.0) — on axes independent of the policy and schema versions (Recommendation 5). The addition is additive: `RuleEvaluationResultVersion` advances to 1.1.0 with both fields defaulted, so every CAP-080A.1 construction remains valid.

**Explainability (frozen, Recommendation 3).** Each `RuleEvaluation` records the expected value, the observed value, the governed threshold, the governing rule id/name, and a deterministic reason — no generated prose, no AI. The outcome of any run is reconstructable from `RuleEvaluationResult` alone, with no need to re-run the evaluator or inspect the policy.

**Determinism (frozen).** No randomness, no UUID, no timestamp, no unordered iteration: ids are pure functions of the run and rule, and distributions are emitted in a fixed enum order. The same inputs yield a byte-identical result. A governed release toggle that is disabled makes its mandatory rule `SKIPPED` (not enforced by policy), distinct from a `FAIL`; a disabled rule is not evaluated at all.

**Extensibility (frozen, Recommendation 5).** Future statistical, regulatory, organization-specific, risk-weighted, and AI-assisted evaluators implement the identical `evaluate(grounding_result, validation_result, cp1_result) -> RuleEvaluationResult` contract — reusing the same catalogue and policy — with no architectural change.

---

## Deterministic Assessment Engine (CAP-080B.1)

CAP-080A.2 froze the Assessment *boundary* (§D21) with a dormant `QualityAssessmentEngine`. CAP-080B.1 implements the **first real engine** behind that unchanged boundary. Like CAP-080B it is a pure *implementation* milestone: no signature, ownership, or boundary changes; **no frozen model or policy is modified**; Decision, Governance, and the Execution Package are untouched; and the engine stays **unwired** from runtime, so runtime is byte-identical and the golden baseline is unchanged. It adds only `DeterministicQualityAssessmentEngine` and wires it as the `PlatformContext` default.

### D26 — Why the deterministic assessment is entirely policy-governed and observation-only

The engine interprets one `RuleEvaluationResult` into a `QualityAssessmentResult` using **only** the governed `AssessmentPolicy` — it hard-codes no precedence, no blocking semantics, and no conflict resolution:

- **Consumes only `RuleEvaluationResult`.** It never reads `GroundingResult` / `ValidationResult` / `CP1Result` (already interpreted upstream) and imports no evaluator, decision, or governance implementation — enforced by containment tests over the `assessment/` package.
- **Classification is governed.** Each *failing* rule is classified BLOCKING / WARNING / ADVISORY from the policy's `mandatory_failure_is_blocking`, `failure_severity_is_blocking`, and `treat_advisory_as_warning` levers; `include_skipped_as_warning` governs whether a `SKIPPED` rule contributes a warning signal. The observed `AssessmentLevel` (`CLEAN` / `ADVISORY_ONLY` / `WARNINGS_PRESENT` / `FAILURES_PRESENT`) is then composed under the policy's `conflict_resolution` (`MANDATORY_WINS` / `SEVERITY_WINS` / `PRECEDENCE_WINS`) over the policy's `precedence` order. Tuning any of these is a versioned policy change, never an engine change (Recommendation 2/4).
- **Observation, never decision (Recommendation 1).** `AssessmentLevel` is a state observation, not a release verdict. The engine assigns no `PASS` / `PASS_WITH_WARNINGS` / `FAIL`; that is the dormant Decision layer's sole job (§D23). Honouring the frozen `AssessmentOutcome` invariant, a failing mandatory rule is always observed as blocking (`has_blocking_failure` ⇒ `FAILURES_PRESENT`).
- **References, never copies (Recommendation 1/DC-analogue).** For each rule that informed the outcome the engine emits an `AssessmentFindingReference` — the evaluation id, rule id, severity, status, and a governed classification note — never duplicating the evaluation's expected/actual/threshold/reason, which remain in the consumed `RuleEvaluationResult`.
- **Determinism & explainability (Recommendation 3).** No randomness, UUID, timestamp, or unordered iteration: the assessment id is a pure function of the evaluation it interprets (`QualityAssessmentResultId.for_evaluation`), distributions are emitted in a fixed enum order, and references preserve evaluation order. Every observation is reconstructable from `QualityAssessmentResult` alone — no re-running Rule Evaluation, no inspecting the policy, the evaluator, or any runtime.

**Recommendations field constraint (Recommendation 4).** The frozen Assessment contract carries **no dedicated recommendations field** on `QualityAssessmentResult`, `AssessmentSummary`, or `AssessmentOutcome`. To avoid modifying a certified contract, the governed `emit_recommendations` flag is surfaced by appending a short, deterministic, level-keyed recommendation clause to `AssessmentOutcome.summary_text` (never free prose, never AI). A dedicated recommendations projection is deferred to the Execution Package or a future grouped metadata object rather than introducing new top-level fields now.

**Extensibility (frozen, Recommendation 5).** Future risk-weighted, statistical, regulatory, and AI-assisted engines implement the identical `assess(rule_evaluation_result) -> QualityAssessmentResult` contract — reusing the same policy — with no architectural change.

---

## QualityAssessmentResult Runtime Contract Freeze (CAP-080B.1.1)

CAP-080B.1 implemented the Assessment engine (§D26). CAP-080B.1.1 is a **pure architectural refinement** performed *before* the Decision engine: it permanently freezes `QualityAssessmentResult` as the canonical runtime contract between Assessment and Decision, mirroring the `MatchResult` freeze (CAP-077B.1) and the `GroundingResult` freeze (CAP-077E.1). **No runtime behaviour changes**: the milestone strengthens docstrings, documents invariants, and adds architecture-only tests. No model field, signature, version value, or ``PlatformContext`` wiring changes; runtime is byte-identical and the golden baseline is unchanged.

### D27 — Why `QualityAssessmentResult` is the frozen Assessment→Decision runtime contract

`QualityAssessmentResult` is **the complete deterministic runtime assessment produced from exactly one `RuleEvaluationResult`**. Freezing it now — before the Decision engine exists — forces the Decision layer to be written against a fixed, self-contained contract, exactly as the grounding renderers were written against a frozen `GroundingResult`.

- **Contract identity.** It is the *only* runtime object the Decision layer consumes. It is **not** a release decision, a report, serialization, an execution artifact, a governance result, or rule evaluation (those are owned elsewhere). It carries no `QualityDecision`, no quality score, and no governance summary.
- **Independent runtime-contract version (retained, not duplicated).** `QualityAssessmentResultVersion` already exists (CAP-080A.2) and versions **only** this runtime contract — independently of the assessment engine, the framework, the `AssessmentOutcome` schema (`AssessmentOutcomeVersion`), and the `AssessmentPolicy` (`AssessmentPolicyVersion`). CAP-080B.1.1 confirms and retains it rather than introducing a duplicate axis (Recommendation 5). This is the direct analogue of `MatchResultVersion` / `GroundingResultVersion`.
- **Explainability invariant (frozen).** Every assessment observation is reconstructable **solely** from this object's `references`, `assessment_statistics`, `assessment_summary`, and `overall_assessment`. The Decision layer must never re-inspect a `RuleEvaluation`, the `QualityAssessmentEngine`, or the `AssessmentPolicy`, and must never re-run assessment. This closes the full explainability chain `RuleEvaluationResult → QualityAssessmentResult → QualityDecisionResult` (Recommendation 3): each link is reconstructable from the previous boundary alone.
- **Assessment→Decision boundary (frozen, one-way).** Assessment owns **only** interpretation; Decision owns **only** `PASS` / `PASS_WITH_WARNINGS` / `FAIL`. Assessment never derives a release status, a governance decision, or a governance summary; Decision never evaluates rules, classifies failures, or interprets a `RuleEvaluation`. The dependency is acyclic and one-way, enforced by containment tests over both `assessment/` and `decision/`.
- **Runtime vs Execution boundary (frozen).** The runtime chain is `RuleEvaluationResult → QualityAssessmentResult`; the Execution Package chain is `QualityAssessmentResult → reports / json / markdown / release package`. Every future execution artifact concerning Assessment is a **pure projection** of a `QualityAssessmentResult`, reproducible from it alone; a renderer never invokes an engine or policy, inspects a `RuleEvaluation`, or recomputes anything (Recommendation 4 serialization rule, extended to Assessment).
- **Recommendation representation (extension point reserved, documentation only).** Today the governed `emit_recommendations` flag appends a deterministic, level-keyed clause to `AssessmentOutcome.summary_text` (§D26). CAP-080B.1.1 **reserves** — and does not implement — a future structured recommendation model (e.g. `AssessmentRecommendation` / `AssessmentRecommendationCode`) so long-term recommendation semantics need not live in free text. This is an architectural reservation only: no runtime field is added, no serialization changes, and the current mechanism is unchanged. Should it land, it advances the `QualityAssessmentResultVersion` axis additively, never forcing an engine, policy, or framework change.

---

## Deterministic Decision Engine (CAP-080B.2)

CAP-080A.3 froze the Decision *boundary* (§D23) with a dormant `QualityDecisionEngine`. CAP-080B.2 implements the **first real engine** behind that unchanged boundary. Like CAP-080B / B.1 it is a pure *implementation* milestone: no signature, ownership, or boundary changes; **no frozen model or policy is modified**; Governance and the Execution Package are untouched; and the engine stays **unwired** from runtime, so runtime is byte-identical and the golden baseline is unchanged. It adds only `DeterministicQualityDecisionEngine` and wires it as the `PlatformContext` default.

### D28 — Why the deterministic decision is entirely policy-governed and the sole decision authority

The engine derives the release decision from one `QualityAssessmentResult` using **only** the governed `DecisionPolicy` — it hard-codes no mapping and no gate:

- **Sole decision authority (Recommendation 1/2).** `DeterministicQualityDecisionEngine` is the *only* class that derives `PASS` / `PASS_WITH_WARNINGS` / `FAIL`. Assessment stays observational (its `AssessmentLevel` is a state observation), and the dormant `QualityGovernanceService` only assembles.
- **Consumes only `QualityAssessmentResult`.** It reads the observed level, the mandatory-failure count, the blocking-failure flag, and the summary counts from the assessment result — never `RuleEvaluationResult` / `GroundingResult` / `ValidationResult` / `CP1Result`, and no evaluator/assessment/governance implementation (containment-tested). It re-runs no assessment and re-classifies no failure.
- **Governed decision algorithm.** A pure function: (1) look up the observed `AssessmentLevel` in the policy's governed base `level_mapping`; (2) apply the governed `warn_on_advisory` interpretation; (3) apply the governed `fail_on_mandatory_failure` and `fail_on_blocking_failure` gates, which force `FAIL` regardless of the base mapping. No mapping, threshold, or precedence is hard-coded — tuning any of it is a versioned `DecisionPolicy` change (Recommendation 2/4). The gates are what keep the decision rule-based rather than a bare lookup: a policy with a lenient base mapping still `FAIL`s when a mandatory gate fires.
- **Determinism.** No randomness, UUID, timestamp, or clock: the decision id is a pure function of the assessment (`QualityDecisionResultId.for_assessment`), and every string is assembled from the assessment and the policy. The same assessment always yields an identical decision.
- **Complete, structured explanation (Recommendation 3).** The frozen `DecisionExplanation` is fully populated — `primary_reason` (which governed rule or gate decided it), `contributing_factors` (mandatory/blocking/warning/advisory counts and the level), `applied_rules` (the governed `level_mapping` entry plus each gate that fired, in order), and `recommendations` (a deterministic, decision-keyed clause gated by `emit_recommendations`) — never generated prose, never AI. Every `PASS` / `PASS_WITH_WARNINGS` / `FAIL` is reconstructable from `QualityDecisionResult` alone, completing the chain `RuleEvaluationResult → QualityAssessmentResult → QualityDecisionResult`.

**Frozen-contract sufficiency (Recommendation 4).** `QualityDecisionResult`, `DecisionExplanation`, `DecisionSummary`, `DecisionStatistics`, and `DecisionPolicy` were **sufficient as frozen** — CAP-080B.2 modifies none of them. `DecisionExplanation.recommendations` already exists, so the recommendation output needs no new field. The `DecisionStatistics.blocking_failures` count is a pure projection of the assessment's own `references` (failing rules recorded at `FAILURE` severity), not a re-classification.

**Extensibility (frozen, Recommendation 5).** Future statistical, regulatory, organization-specific, and AI-assisted decision engines implement the identical `decide(quality_assessment_result) -> QualityDecisionResult` contract — reusing the same policy — with no architectural change.

---

## Governance Runtime Activation (CAP-080C)

CAP-080A froze the service *boundary* (§D6) with a dormant `QualityGovernanceService`. CAP-080B / B.1 / B.2 implemented the three engines. CAP-080C **activates the orchestration**: `DefaultQualityGovernanceService` delegates to a private `QualityGovernancePipeline` that sequences the frozen stages end to end and assembles the `QualityGovernanceResult`. It is a pure *implementation* milestone: no frozen contract changes, and the subsystem stays **unwired from the Requirement Intelligence execution pipeline** (nothing calls `evaluate` at runtime), so runtime is byte-identical and the golden baseline is unchanged. No CLI, Execution Package, Grounding, Validation, or CP1 change.

### D29 — Why the service is a thin orchestrator over a private pipeline and single-assembly builder

The activation mirrors the Grounding subsystem exactly (Recommendation 1): a thin service, a private stage-sequencing pipeline, an assembly-only builder, and `PlatformContext` as the sole composition root.

- **Thin service (orchestration boundary only).** `DefaultQualityGovernanceService.evaluate` holds a private `QualityGovernancePipeline` and delegates to it — nothing more. It evaluates no rule, interprets no assessment, derives no decision, computes no metric, and assembles no result.
- **Private pipeline (sequencing only).** `QualityGovernancePipeline` is an internal implementation detail: **not public**, **not** in the package `__all__`, and **not** a `PlatformContext` factory. It owns only the frozen order — `QualityRuleEvaluator.evaluate → QualityAssessmentEngine.assess → QualityDecisionEngine.decide → QualityGovernanceResultBuilder.build` — and computes nothing; every stage is an injected governed collaborator. No stage may be reordered, skipped, or absorb another's responsibility (Recommendation 4).
- **Single assembly point.** `QualityGovernanceResultBuilder` is the **only** place a `QualityGovernanceResult` (and its inner `QualityAssessment`) is constructed (Recommendation 2). It assembles — projecting each surfaced failing rule from the `RuleEvaluationResult` into a governance `QualityFinding`, recording the decision from the `QualityDecisionResult`, the `overall_quality_score` from the grounding roll-up, and the provenance of the three consumed peer results — and computes nothing. Projection is a deterministic re-expression, not a re-evaluation, so every result stays reconstructable from the canonical outputs `RuleEvaluationResult → QualityAssessmentResult → QualityDecisionResult` (Recommendation 3).
- **Composition root.** `PlatformContext.create_quality_governance_service()` constructs the evaluator, assessment engine, decision engine, and builder, injects them (with the governed `QualityPolicy`) into the pipeline, and wraps it in the service. No service locator, global, or singleton (Recommendation 1). It is the only module outside the package that may name the pipeline or the service.
- **Determinism.** No UUIDs, clocks-in-logic, randomness, async, threads, or unordered iteration: the `started_at`/`completed_at` provenance comes from an injected clock (default wall-clock), so a fixed clock yields a byte-identical `QualityGovernanceResult` — the same convention the Grounding pipeline uses (ADR-0016 §D15, Recommendation 6).
- **Failure semantics.** Governance is one aggregate evaluation: a failure in any stage propagates and fails the whole `evaluate` call. There is no partial result, no recovery, no fallback — exactly one `QualityGovernanceResult` or an exception (mirroring Grounding).

**Runtime dormancy (Recommendation 5).** Although `evaluate` is now fully executable, it is wired into no runtime path — not the CLI, the Requirement Intelligence run, the Execution Package, manifest generation, the release pipeline, the golden dataset, or productization. Those integrations belong to CAP-080D. Containment tests keep the service and pipeline named only by `PlatformContext` outside the package (Recommendation 6).

---

## Final Quality Governance Architecture Certification (CAP-080A.3)

With the Decision layer frozen, the entire subsystem — Grounding → Rule Evaluation → Assessment → Decision → Governance → Execution Package — is certified against the platform's architectural invariants:

- **A. Ownership** — each responsibility has exactly one owner: matching→classification→confidence (Grounding), rule evaluation (`QualityRuleEvaluator`), assessment (`QualityAssessmentEngine`), release decision (`QualityDecisionEngine`), orchestration/assembly (`QualityGovernanceService`), projection (future Execution serializers). No overlap.
- **B. Dependency direction** — strictly one-way and acyclic: `GroundingResult`/`ValidationResult`/`CP1Result` → `RuleEvaluationResult` → `QualityAssessmentResult` → `QualityDecisionResult` → `QualityGovernanceResult`. Each layer imports only the previous boundary; containment tests forbid reaching further back.
- **C. Runtime contracts** — every layer consumes only the canonical result of the previous layer. Rule Evaluation reads the three peer results; Assessment reads only `RuleEvaluationResult`; Decision reads only `QualityAssessmentResult`; Governance assembles from `QualityDecisionResult`.
- **D. Layer responsibilities** — Policies (`QualityPolicy`, `AssessmentPolicy`, `DecisionPolicy`) are governed data only; Engines/Evaluators are behaviour only; the Service is orchestration only; Builders are assembly only; future Serializers are projection only.
- **E. Versioning** — every subsystem carries independent version axes (framework, policy, per-model schema, and result-contract), so any one evolves without forcing the others.
- **F. Explainability** — each result is self-contained; a decision is reconstructable without re-running any upstream stage (Recommendations 3 / DC3).
- **G. Determinism** — all identities are pure functions of their inputs; no UUIDs, no clocks (except the governed `started_at`/`completed_at` provenance already established on `GroundingResult` / `QualityGovernanceResult`), no randomness.
- **H. Extensibility** — future deterministic, statistical, regulatory, organizational, and AI implementations of every engine plug in behind the frozen contracts with no architectural change.
- **I. Separation of concerns** — no business logic in `PlatformContext` (construction only), builders (assembly only), the service (orchestration only), or the future Execution Package (projection only).
- **J. Architecture readiness** — **certified.** CAP-080B landed the first deterministic `QualityRuleEvaluator` and the governed Rule Catalogue (§D25), CAP-080B.1 landed the first deterministic `QualityAssessmentEngine` (§D26), CAP-080B.1.1 froze `QualityAssessmentResult` as the Assessment→Decision runtime contract (§D27), CAP-080B.2 landed the first deterministic `QualityDecisionEngine` (§D28), and CAP-080C activated the `DefaultQualityGovernanceService` orchestration over a private pipeline and single-assembly builder (§D29) — all behind the frozen contracts with no architectural change. The subsystem is now fully implemented and executable end to end, still unwired from runtime. **CAP-080D (runtime activation + execution-package projection)** can proceed against the frozen `QualityGovernanceResult` boundary, with no further architectural work required.

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

- **Owns:** governance, rule evaluation, quality assessment, release decision, policy evaluation, governance findings.
- **Does not own:** Engineering Context, Analysis, Grounding, Validation, CP1, Execution Package, Reporting, Serialization.
- **Runtime position:** `… → Grounding → Validation → CP1 → QualityRuleEvaluator → RuleEvaluationResult → QualityAssessmentEngine → QualityAssessmentResult → QualityDecisionEngine → QualityDecisionResult → QualityGovernanceService → QualityGovernanceResult → Execution Package`, consuming the three completed results; every layer non-gating and dormant through CAP-080A.3.
- **Governance:** registered as CAP-080 in the Platform Capability Matrix at implementation time; the golden baseline is re-based then. This ADR is **Proposed** until that milestone accepts it.
