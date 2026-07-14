# Recommendation Framework — Design Proposal

- **Status:** Accepted (CAP-082A freezes the architecture only)
- **Capability:** CAP-082 — Recommendation Framework
- **Milestones covered:** CAP-082A (Architecture & Governance Freeze — this document)
- **Governed by:** ADR-0019
- **Depends on:** ADR-0016 (Evidence Grounding and Traceability), ADR-0017 (Quality Governance Framework), ADR-0018 (Requirement Enhancement Framework), the Validation and CP1 subsystems.

---

## 1. Problem

The Requirement Intelligence Layer produces five independent, governed judgements
per run:

| Result | Question it answers | Owner |
|---|---|---|
| `RequirementEnhancementResult` | *What does the requirement set look like structurally?* | Requirement Enhancement (ADR-0018) |
| `GroundingResult` | *Is each generated requirement supported by the evidence?* | Grounding (ADR-0016) |
| `ValidationResult` | *Is the response well-formed against the reasoning contract?* | Validation |
| `CP1Result` | *Is the run engineering-ready?* | CP1 (ADR-0011) |
| `QualityGovernanceResult` | *Is the run releasable on quality grounds?* | Quality Governance (ADR-0017) |

**No subsystem turns these five judgements into an actionable recommendation.**
Nothing tells an engineer what to fix first, which gap to close, or which finding
matters most across all five domains at once. That capability exists nowhere in
the repository today (confirmed by the Stage 0 assessment of CAP-082A, ADR-0019).
Left unbuilt, every future consumer must independently re-derive "what to do next"
from five separate results; built as an extension of Quality Governance or
Requirement Enhancement, it would fuse a distinct responsibility into a subsystem
that already has one — exactly the coupling ADR-0001 forbids.

## 2. Scope of CAP-082A

CAP-082A is a **pure architecture milestone**. It freezes:

- the subsystem and its ownership boundary
- the canonical runtime contract, `RecommendationResult`
- the canonical models (`Recommendation`, `RecommendationReference`,
  `RecommendationGroup`, `RecommendationSummary`, `RecommendationMetrics`)
- typed identities and independent version axes
- the governed `RecommendationPolicy` and its builder
- the abstract, dormant `RecommendationService` contract
- `PlatformContext` registration

It does **not** implement recommendation generation, prioritization, grouping,
confidence scoring, runtime wiring, or execution artifacts. No pipeline change. No
Execution Package change. No CLI change. No serializer. No golden re-baseline. The
Architecture Version remains **1.2.0**.

## 3. Stage 0 — Existing recommendation-adjacent surfaces (assessment, no redesign)

| Surface | What it is | Why it is not a recommendation |
|---|---|---|
| `RequirementObservation` / `EnhancementFinding` (ADR-0018) | Raw/interpreted structural signal | ADR-0018 Recommendation 3 explicitly reserves "recommendation" as the *next* layer derived from these — this milestone is that reservation, not a rediscovery. |
| `GroundingResult` / `ExplanationEntry` (ADR-0016) | Per-requirement evidence-support explanation | Explains a classification; never suggests an action. |
| `ValidationIssue` | Raw structural-validation signal | A recorded problem, not a suggested fix. |
| `CP1Finding` | Raw engineering-readiness signal | A recorded gap, not a suggested remediation. |
| `QualityFinding` / `QualityDecision` (ADR-0017) | Governance violation / release verdict | A verdict on releasability, never a remediation suggestion. |

No dedicated recommendation model, identity, policy, or service exists anywhere in
the repository prior to this milestone. Every surface above is a raw or interpreted
*signal* a future recommendation engine must derive from (Recommendation 7); none
overlaps with what CAP-082A introduces.

## 4. Subsystem & ownership

`requirement_intelligence/recommendation/` owns only:

- recommendation generation
- recommendation prioritization
- recommendation grouping
- recommendation confidence scoring
- recommendation metadata

It never owns requirement enhancement, grounding, validation, CP1, governance, the
execution package, prompting, or the engineering context. It is a **consumer only**
of the five completed upstream results — `RequirementEnhancementResult`,
`GroundingResult`, `ValidationResult`, `CP1Result`, `QualityGovernanceResult` —
exactly as Quality Governance is a consumer only of `GroundingResult` /
`ValidationResult` / `CP1Result` (ADR-0017 Recommendation 1).

## 5. Canonical models

| Model | Owns |
|---|---|
| `Recommendation` | One recommendation: title, description, rationale, governed type/priority/effort/confidence, the upstream subsystem it concerns, and one or more `RecommendationReference` entries (never copies) naming the evidence it was derived from (Recommendation 2). |
| `RecommendationReference` | A reference to the runtime object that produced a recommendation — source, referenced id, referenced version. Never a copy. |
| `RecommendationGroup` | An ordered, categorized subset of recommendations, named by id. Owns ordering and categorization only — no recommendation content. |
| `RecommendationSummary` | The headline: counts, priority distribution, and a deterministic one-line description. Renders no release verdict — Recommendation is non-gating. |
| `RecommendationMetrics` | Deterministic numeric roll-ups (recommendation density, average confidence, high-priority ratio) — recorded values, never model-internal calculations. |
| `RecommendationResult` | The runtime contract: every recommendation, every group, the summary, the metrics, the governing policy identity/version, and the consumed-input provenance across all five upstream results. |

Every model is `frozen=True`, tuple-backed collections, `camelCase` serialisation
(`alias_generator=to_camel`), and computes nothing — validators enforce
cross-referential integrity and the explainability invariant only (ADR-0019 §D4/§D7).

## 6. Explainability invariant

Recommendation 7 (ADR-0019 §D7) freezes an invariant stronger than its upstream
peers: a `Recommendation` **cannot be constructed** with zero
`RecommendationReference` entries. Every recommendation must be traceable to at
least one upstream observation, finding, or issue from the moment the model exists
— not retrofitted once an engine starts producing evidence-free recommendations.

## 7. Governed policy

`RecommendationPolicy` is immutable, declarative, governed data — no executable
logic:

- `RecommendationCapabilitySwitches` — enable/disable prioritization, grouping,
  confidence scoring, and the future deterministic/ML/LLM engine families
  (Recommendation 5).
- `PrioritizationRules` — enabled `RecommendationPriority` values and bounded counts.
- `GroupingRules` — enabled `RecommendationType` categories and bounded counts.
- `ConfidenceRules` — the surfacing floor and high-confidence threshold (governed
  thresholds only, no scoring logic).
- `ProjectionRules` — bounds for a future summary/report projection
  (Recommendation 8: runtime before reporting).

`RecommendationPolicyBuilder` / `default_recommendation_policy()` assemble the
CAP-082A default at `RecommendationPolicyVersion` 1.0.0. Tuning any rule or switch
is a versioned policy change, never an engine change (Recommendation 5).

## 8. Runtime boundary (frozen, dormant)

`RecommendationService` exposes exactly one method:

```python
def recommend(
    self,
    enhancement_result: RequirementEnhancementResult,
    grounding_result: GroundingResult,
    validation_result: ValidationResult,
    cp1_result: CP1Result,
    quality_governance_result: QualityGovernanceResult,
) -> RecommendationResult:
    ...
```

It depends only on the five frozen contracts it consumes — never an
*implementation* class (`DeterministicRequirementEnhancementEngine`,
`GroundingService`, `ResponseValidator`, `CP1Service`,
`QualityGovernanceService`). Abstract at CAP-082A; `DormantRecommendationService`
raises `NotImplementedError` on every call. A later CAP-082 milestone implements
the method behind this unchanged signature, exactly as CAP-081B implemented
`RequirementEnhancementService.enhance` behind the ADR-0018 boundary.

## 9. PlatformContext

`PlatformContext` exposes two composition-root methods, construction only:

- `create_recommendation_policy() -> RecommendationPolicy`
- `create_recommendation_service() -> RecommendationService`

Mirroring `create_enhancement_policy()` / `create_requirement_enhancement_service()`
(ADR-0018) and `create_quality_policy()` / `create_quality_governance_service()`
(ADR-0017), these are the **only** sanctioned points outside the `recommendation`
package that may construct its objects, enforced by a containment test.

## 10. Execution package

Not introduced by CAP-082A. When a future milestone activates the runtime, every
recommendation execution artifact will be a **pure projection** of
`RecommendationResult`, reproducible from it alone, computing nothing — the same
serialization invariant ADR-0018 §D8 established for Requirement Enhancement and
ADR-0016 §D16 established for Grounding (Recommendation 8: runtime before
reporting).

## 11. Implementation roadmap (non-normative)

1. **Done (CAP-082A).** Architecture & governance freeze: canonical models, typed
   identities, independent version axes, governed policy, dormant service contract,
   `PlatformContext` registration.
2. CAP-082B — Deterministic Recommendation Engine: derive recommendations strictly
   from recorded upstream observations/findings/issues (Recommendation 7), never
   independent analysis.
3. Prioritization and grouping engines, reading `PrioritizationRules` /
   `GroupingRules`.
4. Confidence scoring, reading `ConfidenceRules`.
5. Runtime activation — wire `recommend` into the pipeline after Quality Governance,
   add the Execution Package projection, golden re-baseline.
6. ML/LLM/hybrid recommendation engines, reserved by
   `RecommendationCapabilitySwitches`, behind the unchanged `recommend` signature.

Each lands behind the unchanged `recommend` signature and the unchanged
`RecommendationResult` contract — no architectural change required.

## 12. Terminology

- **Recommendation** — one suggested action (`Recommendation`), referencing the
  upstream evidence it was derived from, never copying it.
- **Recommendation group** — an ordered, categorized subset of recommendations
  (`RecommendationGroup`), by reference only.
- **Recommendation Framework** is a distinct capability from Requirement
  Enhancement (structural observation), Grounding (evidence support), Validation
  (structural form), CP1 (engineering readiness), and Quality Governance (release
  decision) — a peer, consuming all five, extending none of them.
