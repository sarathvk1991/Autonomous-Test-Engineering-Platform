# ADR-0016 — Evidence Grounding & Traceability Framework

- **Status:** Proposed (design only — CAP-077 introduces no runtime behaviour in this milestone)
- **Date:** 2026-07-11 (Proposed)
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing design:** `docs/proposals/evidence-grounding-and-traceability.md`
- **Depends on:** ADR-0015 (Engineering Context Orchestration) — grounding consumes the `EngineeringContext` evidence corpus.
- **Runtime status:** Not yet implemented. This ADR governs the architecture; a later milestone implements it and re-baselines the golden dataset.

## Problem

The Requirement Intelligence Layer now presents Gemini with multi-source evidence (CAP-076) and the model produces markedly better requirements (RIL RC-1). But **no subsystem verifies that a generated requirement is actually supported by the supplied evidence.**

RC-1 measured grounding **by hand**: an assessor traced each of 22 requirements to the source artifact(s) in the prompt, producing Supported 21 / Partially Supported 1 / Unsupported 0. That assessment also proved the negative: `ValidationResult` and `CP1Result` both passed with **zero findings** while grounding was entirely unassessed — because Validation judges *structure* and CP1 judges *engineering readiness*, and neither reads evidence provenance.

Three concrete gaps make automation impossible today:

1. **Requirements have no identity.** They are plain positional strings in three category arrays (`functional_requirements`, …), with no id.
2. **Requirements do not cite evidence.** The prompt renders evidence as descriptive lines; the model does not reference them back. Any requirement→evidence link must be *inferred*, not parsed.
3. **There is no governed classification, confidence, or metric** for support. "Is this a hallucination?" has no machine answer.

An unsupported requirement is a **hallucination**, and a platform that hands hallucinations to Feature Engineering will build features on fiction. The missing capability is a governed subsystem that owns the question **"is each requirement supported by the evidence, and how confidently?"**

## Decision

Introduce a new governed subsystem, **`requirement_intelligence/grounding/`**, that owns Evidence Grounding, Requirement Traceability, Support Classification, Confidence Calculation, Grounding Explainability, and Grounding Metrics. It:

1. Introduces canonical, immutable models — `GroundedRequirement`, `RequirementEvidenceLink`, `EvidenceReference`, `GroundingConfidence`, `GroundingExplanation`, `GroundingFinding`, `GroundingMetrics`, `GroundingAssessment`, and the `GroundingResult` carrier — following the `Schema` conventions and the typed-identity pattern of ADR-0015.
2. Infers requirement→evidence links through a **`GroundingStrategy` extension point** owned by the Grounding Service. The first strategy (V1) matches normalized requirement text against the `EngineeringContext` evidence corpus **deterministically** (no AI); future strategies (semantic, citation, hybrid) plug in behind the same contract without changing models, classification, confidence, metrics, or the execution package.
3. Assigns a governed `SupportClassification` (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `WEAKLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, `UNKNOWN`) and a deterministic integer confidence with fully recorded components.
4. Runs **after Normalization**, **independent of and non-gating for** Validation and CP1.
5. Emits three conditional execution artifacts — `grounding_result.json`, `grounding_report.md`, `grounding_metrics.md` — via the same append mechanism as `validation_result.json` / `cp1_report.md`.

`PlatformContext` gains `create_grounding_service()`. Consolidation, Orchestration, Prompt Governance, the Prompt Builder, Gemini integration, Validation, and CP1 are **unchanged**.

The full model, matcher, classification, confidence, explainability, metrics, runtime, and downstream design is in `docs/proposals/evidence-grounding-and-traceability.md`.

---

## D1 — Why grounding is a new subsystem, not an extension of Validation or CP1

Grounding answers a question neither existing gate asks. **Validation** judges whether the response is well-formed against the reasoning contract (Transport → Syntax → Schema → Content → Reasoning); a perfectly-formed response can be entirely fabricated and Validation will pass it. **CP1** judges engineering readiness (are there requirements in each governed category?); a readiness gate is satisfied by *presence*, not by *evidence support*. Folding grounding into either would give one subsystem two owners and force every grounding change to be a Validation or CP1 change — exactly the coupling ADR-0001 forbids and ADR-0015 §D1/D2 rejected for orchestration. Grounding is a distinct responsibility with a distinct owner.

## D2 — Why requirement→evidence links are *inferred*, not cited

The ideal source of truth would be the model citing its evidence. It does not, and CAP-077 **must not change the prompt** to make it (Prompt Governance and the Prompt Builder are frozen for this milestone, and a prompt change would invalidate the golden baseline and every RC). The evidence, however, is fully present and canonically identified in the `EngineeringContext` the same run already produced. Grounding therefore reconstructs the links post-hoc, through a `GroundingStrategy` seam whose first implementation (V1) matches text deterministically against that corpus. Inference is weaker than a citation but has a decisive property the prompt route lacks: it is **auditable and reproducible** — the `matched_terms` on every link show exactly why the strategy drew it, and the same inputs always draw the same links. Crucially, because matching lives behind the strategy contract (not baked into the architecture), a stronger signal — semantic similarity, or genuine citation if a future, separately-governed prompt change enables it — can replace the matcher without disturbing the models, classification, confidence, metrics, or execution package.

## D3 — Why confidence is deterministic (no AI)

Using a model to score confidence in a model's output is circular and non-reproducible, and it would make the golden baseline unassertable. Confidence here is **integer arithmetic over sorted inputs** — base value per classification, capped diminishing corroboration bonuses, a cross-source bonus, and penalties for partial/derived/conflicting evidence — with every weight held as **versioned governed data** in `grounding_config.py` (the "policy is data" principle of ADR-0015 §D3). The result is order-independent, byte-reproducible, and fully explained by its recorded `ConfidenceComponent`s. No probabilistic model, no learning.

## D4 — Why `UNKNOWN` is separate from `UNSUPPORTED`

RC-1's sharpest lesson (Observation 4) is that a **coverage gap is not a grounding gap**. A quality requirement generated when the context legitimately carried no quality evidence is *unassessable*, not *hallucinated*. Collapsing the two would let a budgeting artifact inflate the hallucination rate and defame a sound requirement. `UNKNOWN` records "could not judge"; `UNSUPPORTED`/`CONTRADICTED` record "judged, and the evidence is absent or against it." Only the latter two raise `GroundingFinding`s and count toward Hallucination Rate.

## D5 — Why grounding is non-gating in CAP-077

Making grounding gate the pipeline would, by definition, change Validation's or CP1's behaviour and the golden baseline's flow — all forbidden here, and premature. CAP-077 establishes the *measurement* first: a governed, versioned, explainable `GroundingResult` alongside the existing artifacts. Enforcement (a CP1 grounding criterion, or a Quality Governance gate) is a deliberate later decision that will *consume* this result. Measure before you gate.

## D6 — Why grounding does not retype existing identifiers

Like ADR-0015 §D5, the new typed identifiers (`GroundedRequirementId`, `GroundingAssessmentId`, `GroundingConfigVersion`) are **scoped to this subsystem**. Evidence keeps its existing `(source_system, source_record_id)` identity; `analysis_id` / `execution_id` stay raw strings. No existing identifier is retyped — the change is purely additive.

## D7 — Why `GroundingService` is the single runtime boundary (CAP-077A.1)

The subsystem exposes exactly one runtime entry point: `GroundingService`, an abstract contract with a single method — `assess(engineering_context, analysis_result) -> GroundingResult`. Everything else in `grounding/` (models, identities, builders, config, the strategy contract) is internal; nothing outside the subsystem depends on any of it directly.

```
GroundingService     (orchestration — this boundary, stable)
        ↓  delegates matching to
GroundingStrategy    (matching — the replaceable extension point)
```

**`GroundingService` owns** orchestration, lifecycle, dependency coordination, execution ordering, and result assembly. **It does not own** evidence matching (delegated to `GroundingStrategy`), support classification, confidence, metrics, explanation, execution-package writing, Validation, CP1, or the Prompt Builder — each is a separate owner. The service's *future collaborators* (a classification engine, a confidence calculator, metrics and explanation assemblers, the result builder) are **internal implementation details**, not part of the contract.

**Dependency inversion is the point.** The service depends on the `GroundingStrategy` *abstraction*, never on a concrete strategy; no runtime code references `DeterministicTextMatchingStrategy`, `SemanticSimilarityStrategy`, `EvidenceCitationStrategy`, or `HybridStrategy`. Fixing the boundary *before* implementing any behaviour is what lets each subsequent milestone — matching (CAP-077B), classification (CAP-077C), confidence and metrics (CAP-077D), runtime integration (CAP-077E) — land **behind an unchanged `assess` signature**, with no change to callers. This mirrors how the Engineering Context Orchestrator's boundary and `PlatformContext` factory existed before the orchestrator was activated.

**CAP-077A.1 establishes the boundary only.** `assess` is abstract and the registered `DefaultGroundingService` raises `NotImplementedError`; `PlatformContext.create_grounding_service()` constructs it with the governed configuration and **no strategy**. It is dormant — no pipeline stage consumes it — so runtime behaviour is byte-identical. Its one new dependency, on the `EngineeringContext` *model* (the evidence corpus `assess` grounds against), was registered by consciously widening the CAP-076C orchestration-consumer allowlist, which is the mechanism that guard exists to force.

## D8 — Why strategies consume a canonical `MatchingContext`, not runtime models (CAP-077A.2)

A `GroundingStrategy` must never depend on `EngineeringContext`, `AnalysisResult`, `ParsedResponse`, `PlatformContext`, or any other runtime object. Instead, every strategy consumes one immutable canonical input, the **`MatchingContext`** (fanned out into per-requirement **`MatchingRequest`**s). Three canonical models carry it: `MatchingRequirement` (one normalized generated requirement, *before* grading — deliberately not a `GroundedRequirement`, whose validators require the classification/confidence that only exist *after* matching, though the two share the deterministic `GroundedRequirementId`), `MatchingEvidence` (one evidence artifact reduced to its stable identity plus the text fields a matcher reads — no `SourceArtifact` leaks into a strategy), and the `MatchingContext` / `MatchingRequest` themselves.

**Why the indirection.** A strategy pinned to runtime models would (a) be untestable without constructing an entire orchestration + analysis graph, (b) drift whenever those models evolve, and (c) tempt a strategy to reach past its evidence into orchestration or analysis internals. A small, canonical, immutable input makes matching **deterministic** (no timestamps, no UUIDs, no mutable runtime objects — the only identifier is the deterministic `context_id`), **isolated** (unit-testable from a handful of literals), and **reusable** — a semantic, citation, or hybrid strategy consumes the *same* `MatchingContext` unchanged.

**The one translation boundary.** `MatchingContextBuilder` is the single place the subsystem touches runtime models: it flattens the `EngineeringContext` evidence into canonical order and recovers the generated requirements from the `AnalysisResult` response body — construction only, no matching, filtering, scoring, or ordering. It is registered on `PlatformContext` (`create_matching_context_builder`), unwired, and is the second consumer consciously added to the orchestration allowlist. The `GroundingStrategy` contract takes `match(request: MatchingRequest)` — the per-request shape that keeps strategy inputs canonical *and* lets a future executor evaluate requirements independently (and in parallel) with no contract change.

## D9 — Why a strategy returns a canonical `MatchResult`, not a raw tuple (CAP-077A.3)

The matching contract is completed — and **frozen** — by fixing the *output* as well as the input. `GroundingStrategy.match(request: MatchingRequest) -> MatchResult`. This is the permanent signature; no later grounding milestone changes it.

**Why not `tuple[RequirementEvidenceLink, ...]`.** A raw tuple is a shape frozen at its narrowest. The first time a matcher needs to report *how many* evidence items it examined, *which* it rejected, or *why*, the return type must widen and every caller must change — precisely the churn a frozen contract is meant to prevent. A `MatchResult` is **open for population, closed for redefinition**: CAP-077B fills it with links and basic statistics; a semantic or hybrid strategy fills the *same* fields with richer values; none alters the type. Freezing the contract *before* any matcher exists is deliberate — it forces the shape to be designed for every future strategy, not retrofitted around the first one.

**What it carries, and what it must not.** Three canonical models: `MatchResult` (the requirement, its links, statistics, explanation, and the producing strategy's name/version + `context_id`), `MatchStatistics` (pure deterministic *observations* — evidence examined/matched/rejected, term and exact/partial counts, normalization operations; **never** scores, percentages, confidence, or classifications), and `MatchExplanation` (matcher-scoped structured explainability — matched/unmatched terms, rejected evidence, notes; **no** generated prose, confidence reasoning, or hallucination judgement). The scope line is firm: a `MatchResult` is the *matcher's* output. Classification, confidence, and grounding metrics are computed by the Grounding Service *from* a `MatchResult` and live on `GroundedRequirement` / `GroundingResult`. `MatchExplanation` (matcher scope) is therefore distinct from `GroundingExplanation` (requirement scope). Like every canonical grounding model it is immutable, tuple-backed, camelCase-serialised, and free of timestamps and UUIDs.

With the input (`MatchingContext`/`MatchingRequest`) and the output (`MatchResult`) both canonical and frozen, the **entire matching architecture is closed** ahead of CAP-077B. `PlatformContext` needs no change — a `MatchResult` is produced by strategies, never constructed by the composition root.

## D10 — Why matching normalization is a separate architectural boundary (CAP-077A.4)

Matching and normalization are different jobs, and conflating them is a mistake the architecture forecloses now. **Normalization** turns raw text (a requirement, an evidence title/description) into a canonical, comparable form — lowercasing, whitespace, punctuation, camelCase/snake_case splitting, stop words, abbreviations. **Matching** compares already-normalized text and decides which evidence supports a requirement. The first is mechanical and universal; the second is where a strategy's judgement lives.

**Normalization sits *below* `GroundingStrategy`, not inside it.** A new package, `grounding/normalization/`, owns preprocessing only via one abstraction — `MatchingNormalizer.normalize(text) -> NormalizedText`. Three reasons it is a boundary rather than a helper buried in the first matcher:

1. **Every strategy must preprocess identically.** If deterministic, semantic, and hybrid strategies each rolled their own tokenizer, "the requirement says *nosniff*" could tokenize three different ways and the strategies would silently disagree on their *inputs* before they ever disagreed on their *judgement*. One shared normalizer makes the inputs canonical, so strategy differences are real, not artefacts of preprocessing.
2. **No duplicated preprocessing.** Normalization is written once and reused; a new strategy consumes `NormalizedText`, never re-implements it.
3. **Governed, versioned, auditable.** The switches live on an immutable, versioned `NormalizationConfiguration` (`MatchingNormalizationVersion`), and each run's `NormalizedText` carries `NormalizationStatistics` (pure observations) and the version that produced it — the same "policy is data" discipline as the orchestration and grounding configurations.

The canonical models — `NormalizedToken`, `NormalizedText`, `NormalizationStatistics` — are immutable, tuple-backed, camelCase, and free of timestamps/UUIDs, like every grounding model. This is distinct from the response-normalization subsystem (`requirement_intelligence/normalization/`), which normalizes an AI *response's structure* into a `ParsedResponse`; matching normalization normalizes *free text into tokens*.

**CAP-077A.4 establishes the boundary only.** `DefaultMatchingNormalizer` is minimal — lowercase + whitespace — enough to fix the permanent API; full tokenization is reserved for the first strategy (CAP-077B). `PlatformContext.create_matching_normalizer()` constructs it, unwired, with no consumers, so runtime behaviour is byte-identical. With normalization (input preprocessing), `MatchingContext` (input), and `MatchResult` (output) all canonical and frozen, the Grounding matching architecture is complete before a single matcher is written.

## D11 — Why the matching policy is governed data, not part of the strategy (CAP-077A.5)

The last piece of the matching architecture separates *what constitutes a match* from *how a match is evaluated*. **`MatchingPolicy` governs; `GroundingStrategy` implements.** A policy is an immutable, declarative, governed rule set — thresholds a candidate link must clear (`MatchingThresholds`), the weights a matcher applies per evidence field (`MatchingWeights`), the ranking keys (`MatchingRanking`), the tie-breaker (`MatchingTieBreaker`), and which relations are permitted (`allow_cross_domain / partial / derived / negative / contradicting`). It contains **no executable logic**. This is the exact `OrchestrationPolicy` pattern (ADR-0015 §D2/D3): policy is data, the executor is behaviour.

**Why separate at all.** The knobs that tune matching quality — "a title match is worth more than a tag match", "require at least two exact terms", "don't admit contradicting evidence" — will be revised repeatedly as the platform learns what grounds well. If those lived inside the matcher, every tuning pass would be a code change (and a code review, and a regression risk). As governed data on a versioned `MatchingPolicy`, a tuning pass is a **data change under the golden re-baseline procedure** — auditable, attributable to a `MatchingPolicyVersion`, and revertible — exactly as orchestration ranking/budget tuning already is.

**Three governed inputs, one algorithm.** A `GroundingStrategy` now reads three governed things and owns only the comparison: a `NormalizationConfiguration` (how to preprocess), a `MatchingPolicy` (what counts as a match), and the canonical `MatchingRequest` (the evidence). Because all three are data external to the algorithm, **one policy serves every matcher**: the deterministic matcher (CAP-077B), a future semantic matcher, and a future hybrid matcher each apply the *same* policy differently, and none needs a bespoke policy type. The dependency runs strategy→policy, never policy→strategy: the policy package imports neither the strategy contract nor `MatchResult`.

**CAP-077A.5 established the framework; CAP-077B populated it.** The default policy from `MatchingPolicyBuilder` shipped permissive and weightless at CAP-077A.5; CAP-077B advanced it to `MatchingPolicyVersion` 2.0.0 with the governed weights and thresholds Strategy V1 matches against — a versioned data change, not a matcher code change. `PlatformContext.create_matching_policy()` constructs it, unwired, with no consumers, so runtime behaviour is byte-identical.

With preprocessing (`NormalizationConfiguration`), decision rules (`MatchingPolicy`), the input (`MatchingContext`), and the output (`MatchResult`) all canonical, governed, and frozen, the Grounding matching architecture is **fully closed** ahead of CAP-077B.

## D12 — The frozen Matching↔Classification contract (CAP-077B.1)

CAP-077B implemented Strategy V1; before CAP-077C (Support Classification) begins consuming its output, four invariants freeze the `MatchResult` as the **sole, self-contained contract** between Matching and Classification. None changes matching behaviour.

**1 — Match-score semantics are frozen.** The `match_score` on a `RequirementEvidenceLink` is *only* **deterministic evidence similarity**: the integer a Grounding Strategy computed from token overlap under a governed Matching Policy. It is **not** confidence, **not** probability, **not** certainty, and **not** a support classification. Producer: a `GroundingStrategy`. Consumers: Classification and reporting. Lifecycle: minted per (requirement, evidence) pair, immutable thereafter. Confidence and classification are computed *from* a match, downstream, and live on `GroundedRequirement` / `GroundingResult` — never on a link.

**2 — `MatchResult` is versioned independently of the strategy.** A new typed `MatchResultVersion` (`MATCH_RESULT_VERSION`, carried on every result as `result_version`) versions the **schema**, not the producer. A strategy may change its own `MatchingStrategyVersion` without touching the schema version, and the schema may evolve without bumping any strategy. The two concerns are decoupled so neither forces a change in the other.

**3 — Explainability is a governed invariant.** *Every `MatchResult` must be completely explainable without re-running the strategy.* Every fact needed to understand why evidence matched, why it failed, and why it ranked already lives inside the result: the `links` (each with `match_score`, `matched_terms`, `relation`, `rationale`), the `MatchStatistics`, and a structured `MatchEvaluationSummary` (evidence examined/matched, highest score, winning evidence, the governed threshold and ranking summaries) — additive, structured data, never generated prose. Future strategies **must** honour this invariant. A consumer never needs the strategy, normalizer, or policy again.

**4 — The Matching↔Classification boundary is frozen.** CAP-077C consumes **only** `MatchResult`. Classification must never invoke a `GroundingStrategy`, `MatchingNormalizer`, or `MatchingPolicy` — the matching layer is complete, and re-entering it downstream would duplicate matching and split its ownership. The dependency is one-way: `MatchResult` is self-contained (it imports no strategy, normalizer, or policy), and the matching layer imports nothing from Classification. This is enforced by containment tests.

## D13 — Support Classification is a governed subsystem consuming only MatchResult (CAP-077C)

Support Classification is the third governed subsystem of the grounding pipeline, after Matching. It answers *what verdict does the evidence warrant?* — turning a `MatchResult` into a `ClassificationResult`. It owns classification **only**: no matching, normalization, confidence, metrics, explanation rendering, or execution artifacts.

**`ClassificationResult` is the internal contract between Classification and Confidence.** The grounding pipeline is now a chain of canonical hand-offs:

```
MatchResult  →  ClassificationResult  →  Confidence  →  GroundedRequirement
```

`ClassificationResult` records the support verdict, the evidence links partitioned by role (supporting / contradicting / partial / derived / unknown), and a short deterministic reason. It is **internal to Grounding** — not an execution artifact, not exposed outside the subsystem. Introducing it as a distinct model isolates CAP-077D: confidence is computed *from* a `ClassificationResult` without re-running matching or re-classifying, and the `GroundedRequirementBuilder` now assembles a requirement *from* a `ClassificationResult` rather than taking a bare verdict.

**Policy governs; the engine implements.** A `SupportClassificationEngine` reads a governed `ClassificationPolicy` (score thresholds per verdict, the relation-to-role mapping, the precedence order, conflict and unknown handling, the permitted verdict set). Nothing is hard-coded; tuning classification is a versioned policy change. The default precedence is CONTRADICTED → SUPPORTED → PARTIALLY_SUPPORTED → WEAKLY_SUPPORTED → UNKNOWN → UNSUPPORTED — the engine emits the highest applicable verdict.

**UNKNOWN ≠ UNSUPPORTED — the RC-1 lesson, now enforced.** When no evidence was examined at all, the verdict is UNKNOWN (a coverage gap — unassessable); when evidence was present but nothing supported the requirement, it is UNSUPPORTED (a hallucination). The engine distinguishes them from `MatchResult.statistics.evidence_examined`, so a budgeting gap is never miscounted as a hallucination.

**Fully deterministic, boundary-clean, independently versioned.** Every verdict is a pure function of `(MatchResult, ClassificationPolicy)`. The engine reads only the `MatchResult`; it never inspects the `EngineeringContext`, `AnalysisResult`, strategy, normalizer, or matching policy (enforced by containment tests). `ClassificationVersion` (result schema) and `ClassificationPolicyVersion` are typed and advance independently of `MatchResultVersion`, `MatchingStrategyVersion`, and the framework version. `PlatformContext.create_classification_policy()` and `create_support_classification_engine()` construct them, unwired, with no consumers — runtime is byte-identical.

## D14 — Confidence is a governed subsystem consuming only ClassificationResult (CAP-077C.1)

Confidence is the fourth governed subsystem of the grounding pipeline, after Classification. It answers *how confident should this verdict make us?* — turning a `ClassificationResult` into a `ConfidenceAssessment`. It owns confidence **only**: no matching, normalization, classification, metrics, execution artifacts, `GroundingService`, Validation, or CP1. **CAP-077C.1 freezes the architecture only; no confidence is computed** (the deterministic calculator lands in CAP-077D).

**The pipeline is now a chain of canonical hand-offs:**

```
MatchResult → ClassificationResult → ConfidenceAssessment → GroundedRequirement → GroundingResult
```

**Why `ConfidenceAssessment` exists.** It is the internal canonical output of Confidence — score, band, components, a structured explanation, and a `ConfidenceVersion` — independent of `GroundedRequirement`. Not an execution artifact, not exposed outside Grounding. Introducing it isolates CAP-077D: the calculator produces a `ConfidenceAssessment`, and nothing else creates confidence.

**Why `ConfidenceExplanation` exists.** It replaces a plain reason string with structured, machine-readable data — summary, positive/negative factors, applied policy rules, score breakdown, recommendations — reusable by reports and governance dashboards. Deterministic observations only; no generated prose. It is the permanent explanation contract for the subsystem.

**Why `GroundedRequirement` no longer owns confidence construction.** The builder now consumes a `ConfidenceAssessment` and *assembles* — it transcribes the assessment into the `GroundingConfidence` the (frozen) `GroundedRequirement` model carries, computing nothing. `GroundedRequirement` becomes a pure assembly target; confidence *creation* belongs solely to the Confidence subsystem. (The frozen `GroundedRequirement.confidence: GroundingConfidence` field is unchanged, keeping the canonical model byte-stable; the builder is the only thing that changed.)

**Policy governs; the calculator implements.** A governed `ConfidencePolicy` holds base scores per verdict, bonuses (support, cross-source, evidence-count), penalties (conflict, unknown), the ceiling, and band thresholds — data only, no logic. The `ConfidenceCalculator` is an abstract contract, `calculate(classification_result) -> ConfidenceAssessment`, frozen now; the dormant default raises `NotImplementedError`. Future `DeterministicConfidenceCalculator` (CAP-077D), `StatisticalConfidenceCalculator`, and `HybridConfidenceCalculator` implement it behind the same signature. It consumes only a `ClassificationResult` — never the `MatchResult`, strategy, normalizer, or matching policy (enforced by containment tests).

**Independently versioned, dormant, byte-identical.** `ConfidenceVersion` (assessment schema) and `ConfidencePolicyVersion` are typed and advance independently of `ClassificationVersion`, `MatchResultVersion`, `MatchingStrategyVersion`, and the framework version. `PlatformContext.create_confidence_policy()` and `create_confidence_calculator()` construct them, unwired, with no consumers — runtime is byte-identical.

## D14 addendum — the deterministic confidence implementation (CAP-077D)

CAP-077D implements the first production calculator, `DeterministicConfidenceCalculator`, behind the frozen `ConfidenceCalculator` contract. It changed **only** the implementation — no contract, model, policy shape, or signature changed, and `PlatformContext.create_confidence_calculator()` now returns it (still unwired, so runtime is byte-identical).

**Policy-driven, integer-only arithmetic.** The score is built entirely from governed policy data:

```
score = base_scores[classification] + Σ bonuses − Σ penalties
score = clamp(score, 0, max_score)
band  = HIGH | MEDIUM | LOW  (by band_thresholds)
```

Nothing is hard-coded: the base comes from `base_scores` keyed on the `SupportClassification`; the bonuses (`support_bonus` per additional supporting link, `cross_source_bonus` when evidence spans ≥2 source systems, `evidence_count_bonus` per additional evidence item) and penalties (`conflict_penalty` per conflicting link, `unknown_penalty` for an UNKNOWN verdict) are all read from the policy; the ceiling and band boundaries are the policy's. No floats, no probability, no AI, no randomness, no timestamps.

**Single source of truth, fully reconstructable.** Every arithmetic operation the calculator performs — the base, each applied bonus, each applied penalty, and any ceiling/floor clamp — is recorded as exactly one `ConfidenceComponent`, so **`confidence_score == Σ component deltas`**: the score can be reconstructed entirely from its components, and no arithmetic happens anywhere else. `DeterministicConfidenceCalculator` is the *only* thing that computes confidence; `GroundedRequirementBuilder` assembles, `GroundingService` orchestrates, metrics read, reports render — none duplicate the arithmetic. The `ConfidenceExplanation` is fully populated deterministically (summary, positive/negative factors, applied policy rules, the component breakdown, and governed recommendations) — structured data, never prose. Future statistical or hybrid calculators replace this implementation behind the same contract without any change.

## D15 — The frozen Grounding execution pipeline (CAP-077D.1)

With every layer implemented and frozen, CAP-077D.1 freezes the **orchestration** — the permanent execution order, ownership, dependency direction, and failure semantics that CAP-077E will activate without redesign. This is architecture only; Grounding remains dormant.

### Frozen execution order

`GroundingService.assess(engineering_context, analysis_result)` runs this sequence — future milestones *populate* stages, they never *reorder* them:

```
EngineeringContext + AnalysisResult
  → MatchingContextBuilder      → MatchingContext → MatchingRequest(s)
  → MatchingNormalizer          (preprocessing, inside each strategy call)
  → GroundingStrategy           → MatchResult (one per requirement)
  → SupportClassificationEngine → ClassificationResult
  → ConfidenceCalculator        → ConfidenceAssessment
  → GroundedRequirementBuilder  → GroundedRequirement
  → GroundingMetricsBuilder     → GroundingMetrics + GroundingSummary
  → GroundingResultBuilder      → GroundingResult
```

### Ownership matrix (frozen)

| Component | Owns ONLY | Never does |
|---|---|---|
| `GroundingService` | orchestration, lifecycle, dependency coordination, execution ordering | matching, classification, confidence, metrics, serialization |
| `MatchingContextBuilder` | runtime→canonical translation | matching |
| `MatchingNormalizer` | text preprocessing | matching, scoring |
| `GroundingStrategy` | evidence matching → `MatchResult` | classification, confidence, metrics |
| `SupportClassificationEngine` | classification → `ClassificationResult` | matching, confidence |
| `ConfidenceCalculator` | confidence → `ConfidenceAssessment` | matching, classification |
| `GroundingMetricsBuilder` | metric computation, distributions, coverage, hallucination rate, grounding score | matching, classification, confidence, orchestration |
| `GroundedRequirementBuilder` | per-requirement assembly | any computation |
| `GroundingResultBuilder` (+ `GroundingAssessmentBuilder`) | final aggregate construction | any computation |
| Execution Package | serialization of `GroundingResult` | any grounding logic |

No component computes another component's responsibility.

### Dependency direction (frozen, acyclic)

The pipeline is a strict one-way chain. A `GroundingStrategy` never calls the classifier, calculator, metrics, or result builder. Classification never calls a strategy or normalizer. Confidence never calls matching or a strategy. Metrics never call matching or classification — a `GroundingMetricsBuilder` reads finished `GroundedRequirement`s only. Each stage depends only on the canonical output of the previous stage (`MatchResult` → `ClassificationResult` → `ConfidenceAssessment`), enforced by the containment tests already in place. `GroundingService` **assembles only** — it invokes each stage and passes outputs forward; it computes nothing itself.

### Failure semantics (frozen)

**Requirement-level failures become findings; grounding continues; a `GroundingResult` is always produced.** If one requirement cannot be grounded (e.g. a strategy or stage raises for that requirement), `GroundingService` records a `GroundingFinding` for it and proceeds with the remaining requirements. The service **never aborts the whole run because one requirement failed**. Rationale: a run over N requirements must degrade gracefully — one problematic requirement must not deny grounding for the other N−1, and the finding preserves auditability of what failed and why. Ownership: the service owns this policy (it is orchestration, not matching/classification/confidence); downstream, a partial `GroundingResult` is still a complete, well-formed aggregate whose metrics reflect the findings. (A *service-level* failure — e.g. a malformed `AnalysisResult` the `MatchingContextBuilder` rejects — is different: it fails the whole `assess` call, because there is no per-requirement work to continue.)

### Metrics & result assembly (frozen)

Metric computation is owned by a dedicated **`GroundingMetricsBuilder`** (a named responsibility to be built in CAP-077E): grounding coverage, evidence coverage, distributions, cross-source/single-source support, hallucination rate, grounding score, and the derived `GroundingMetrics` + `GroundingSummary`. `GroundingService` never computes a metric — it invokes the builder. Final aggregate construction is owned by **`GroundingResultBuilder`** (with `GroundingAssessmentBuilder` assembling the `GroundingAssessment` from grounded requirements, findings, metrics, summary, and versions). `GroundingService` never constructs a `GroundingResult`, `GroundingAssessment`, or `GroundingSummary` directly — it delegates.

### Execution Package boundary (frozen)

The Execution Package consumes **only** `GroundingResult`. It never depends on Matching, Classification, Confidence, the `GroundingMetricsBuilder`, or `GroundingService` internals. The future artifacts `grounding_result.json`, `grounding_report.md`, and `grounding_metrics.md` are **projections of `GroundingResult`** — serialization only, no grounding logic, no re-computation. No runtime component writes artifacts directly; only the Execution Writer serializes, and only from the aggregate.

### GroundingPipeline — ACCEPTED (to be implemented in CAP-077E)

An internal, private **`GroundingPipeline`** helper is **accepted** as the design for CAP-077E. `GroundingService.assess` will delegate to it:

```
GroundingService (public boundary, lifecycle, dependency coordination)
  → GroundingPipeline (private stage sequencer)
      → Matching → Classification → Confidence → per-requirement assembly → Metrics → ResultBuilder
```

**Rationale for accepting:** it separates the *stable public boundary* (`GroundingService.assess`, the one runtime entry point) from the *execution-ordering mechanics* (the fixed stage sequence and per-requirement fan-out), keeping `assess` thin and making the stage sequence unit-testable in isolation from the service's construction and lifecycle. It is **internal and private** — not exposed, not part of the public API, not registered in `PlatformContext` — so it adds no API surface. The service still *owns* execution ordering; the pipeline is the mechanism it delegates to, exactly as the CLI delegates to `PlatformContext` factories. It does not dilute ownership (the pipeline invokes the same governed components) and it improves separation, so it is preferred over inlining the whole sequence inside `assess`.

## D16 — GroundingResult is the frozen runtime contract; serialization is projection (CAP-077E.1)

CAP-077E activated the runtime; before CAP-077F serializes its output, CAP-077E.1 freezes `GroundingResult` as the **runtime contract** — the single object that crosses from the runtime into serialization. No behaviour changed; this is the same freeze CAP-077B.1 gave `MatchResult`.

**GroundingResult semantics (frozen).** A `GroundingResult` is *the complete, deterministic grounding assessment for one Requirement Intelligence execution*. It is **not** a report, an execution artifact, serialization, a renderer, or a metrics calculator — it is the canonical repository-level aggregate the runtime produces and `GroundingService.assess` returns, already containing the grounded requirements, findings, metrics, summary, explanations, and versions.

**Versioned independently.** A new typed `GroundingResultVersion` (`GROUNDING_RESULT_VERSION`, carried as `result_version`) versions the **runtime-contract schema**, decoupled from `GroundingFrameworkVersion`, `MatchingStrategyVersion`, `MatchResultVersion`, `ClassificationVersion`, and `ConfidenceVersion`. The contract's schema may evolve without forcing a framework change, and vice versa; execution artifacts may evolve without a `GroundingResult` change, and a `GroundingResult` change never forces a renderer change.

**Serialization invariant (frozen).** *Every execution artifact must be reproducible solely from a `GroundingResult`.* The three future artifacts —

```
GroundingResult
  ├── grounding_result.json   (canonical serialization)
  ├── grounding_report.md     (human-readable projection)
  └── grounding_metrics.md    (metrics projection)
```

— are **pure projections**. A renderer must never invoke a `GroundingStrategy`, `MatchingNormalizer`, matching/classification/confidence policy, `GroundingMetricsBuilder`, `GroundingPipeline`, or `GroundingService`, and must never recompute matching, classification, confidence, metrics, summaries, or findings. Everything already exists inside the `GroundingResult`.

**Explainability completeness (frozen).** `GroundingExplanation` (requirement-scoped), `GroundingFinding`, `GroundingSummary`, and `GroundingMetrics` together form the complete explanation model. A renderer derives no new information; Markdown generation is presentation only.

**Runtime/artifact boundary (frozen, one-way).** `Runtime → GroundingResult → Execution Package → files`. The Execution Package owns *formatting only* and may consume `GroundingResult`; it never imports Matching, Classification, Confidence, the pipeline, the metrics builder, or the service, and the runtime never depends on the Execution Package. Enforced by containment tests.

**Golden regression boundary (frozen).** Golden datasets compare the **`GroundingResult`**, never Markdown formatting. A change to `grounding_report.md`/`grounding_metrics.md` presentation must never invalidate a runtime regression baseline; only a change to the `GroundingResult` content (or its `result_version`) is a runtime regression.

**Exception-boundary — future evolution (documentation only).** The pipeline's per-requirement recovery currently catches a broad `except Exception`. Architecturally, a narrower hierarchy — a `GroundingRequirementError` (or reusing the subsystems' own error types) caught per requirement, letting truly unexpected errors propagate — would sharpen the failure contract. This is recorded as the **preferred future evolution**; CAP-077E.1 introduces no new exception class and changes no behaviour, because the broad catch is what delivers the frozen "one requirement never denies the others" guarantee and narrowing it is a behavioural change reserved for a dedicated milestone.

---

## Trade-offs

- **Inferred links can mis-match.** Deterministic text matching will occasionally over- or under-link versus a human. Mitigation: matches are transparent (`matched_terms`), thresholds are governed and tunable, and RC-1 is the fixed regression target to calibrate against. This is accepted as the price of not changing the prompt.
- **Confidence is heuristic, not probabilistic.** A governed weighted score is coarser than a learned model but is reproducible, auditable, and free of circularity — the right trade for a governance artifact.
- **A re-baseline is required at implementation.** Adding artifacts and manifest fields changes golden checksums. Accepted: the golden baseline's §7.3 procedure exists precisely for intentional additive change.
- **Two grounding concepts now coexist.** `ContextGrounding` (evidence-side: "what did the session stand on?") and CAP-077 grounding (requirement-side: "is each requirement supported?"). They are complementary and must be kept terminologically distinct; the proposal and this ADR do so explicitly.

## Future evolution

- A **grounding gate** consumed by CP1 or Quality Governance (D5).
- **Correlation-aware** grounding once `ContextDependencies.correlations` is populated.
- Promotion of shared version value-objects to `shared/` (the debt ADR-0015 §C already names).
- Prompt-level **evidence citation** as an eventual stronger signal, if and when a prompt change is separately governed.

## Ownership, runtime position, governance

- **Owns:** requirement→evidence traceability, support classification, confidence, grounding explainability, grounding metrics, hallucination detection.
- **Does not own:** Validation, CP1, prompt construction, Engineering Context, Prompt Governance, Execution Package, Analysis.
- **Runtime position:** `… → Analysis → Normalization → Grounding → Validation → CP1 → Execution Package`, non-gating.
- **Governance:** registered as CAP-077 in the Platform Capability Matrix at implementation time; the golden baseline is re-based then. This ADR is **Proposed** until that milestone accepts it.
