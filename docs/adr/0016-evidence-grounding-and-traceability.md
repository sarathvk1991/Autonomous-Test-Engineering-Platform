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
