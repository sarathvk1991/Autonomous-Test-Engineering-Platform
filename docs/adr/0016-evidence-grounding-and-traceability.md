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
