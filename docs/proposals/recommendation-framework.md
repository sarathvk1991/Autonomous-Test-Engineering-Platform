# Recommendation Framework — Design Proposal

- **Status:** Accepted (CAP-082A froze the architecture; CAP-082B implemented the first deterministic engine behind it, unchanged; CAP-082B.1 permanently certified the runtime contract, no behaviour change)
- **Capability:** CAP-082 — Recommendation Framework
- **Milestones covered:** CAP-082A (Architecture & Governance Freeze), CAP-082B (Deterministic Recommendation Engine — see §13), CAP-082B.1 (RecommendationResult Runtime Contract Freeze — see §8b)
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
governed default, now at `RecommendationPolicyVersion` 1.1.0 (CAP-082B advanced it
from CAP-082A's 1.0.0 by flipping `enable_deterministic_engine` to `True`). Tuning
any rule or switch is a versioned policy change, never an engine change
(Recommendation 5).

CAP-082B additionally introduces `RecommendationRuleCatalog`
(`recommendation/rules/`, mirroring `quality_governance/rules/` and
`enhancement/rules/`): governed, metadata-only `RecommendationRule` entries naming a
`RecommendationRuleCategory` (the shape of upstream evidence covered), a
`RecommendationType`, priority/effort/confidence hints, and a
`RecommendationPolicyToggle` reference. The default catalogue ships 18 rules
covering all five sources. See §13.

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
`QualityGovernanceService`). Abstract at CAP-082A. CAP-082B implements the method:
`DeterministicRecommendationService` (replacing `DormantRecommendationService`)
delegates to the private `DeterministicRecommendationEngine`, exactly as CAP-081B
implemented `RequirementEnhancementService.enhance` behind the ADR-0018 boundary.
The signature is unchanged; the subsystem remains unwired into the runtime
pipeline. See §13.

## 8b. Recommendation Runtime Contract (CAP-082B.1)

CAP-082B.1 permanently certifies `RecommendationResult` as the runtime contract of
the Recommendation Framework, before the subsystem is activated in the live
pipeline — mirroring CAP-080B.1.1 (`QualityAssessmentResult`) and CAP-081B.1
(`RequirementEnhancementResult`). **No runtime behaviour changes.** No field, no
computation, no signature changed; only documentation and architecture-only tests
were added. Full detail lives in ADR-0019 §D9; summarised here:

**Frozen definition.** `RecommendationResult` is *the complete deterministic runtime
recommendation produced from exactly one execution of*
`RecommendationService.recommend()`.

- **IS:** the runtime contract; the recommendation boundary; independently
  versioned; deterministic; immutable; self-contained; explainable; serialization
  independent.
- **IS NOT:** a report; Markdown; HTML; an execution package; a manifest; a CLI
  object; a renderer; a serializer; a transport object; a projection.

**Ownership (no overlap).** Engine owns generation/prioritization/grouping/
confidence/summary. Service owns orchestration only. `RecommendationResult` owns
runtime state only. A future serializer owns projection only. A future Execution
Package owns packaging only. A future CLI owns orchestration only. `PlatformContext`
owns composition only.

**Explainability.** Every recommendation is reconstructable solely from
`RecommendationResult` — no upstream subsystem, no engine rerun, no policy
inspection, no runtime inspection required.

**Runtime boundary.** Runtime ends at `RecommendationResult`. Everything after it —
serializers, reports, dashboards, Markdown, HTML, PDF, the Execution Package — is
projection, and must consume `RecommendationResult` only, never the engine, the
service, or `PlatformContext`:

```
Recommendation Runtime (engine + service)
    → RecommendationResult
    → Serializer (future)
    → Execution Package (future)
    → Manifest (future)
    → Release
```

**Golden boundary (forward-looking).** When golden integration eventually occurs,
`RecommendationResult` — not reports — becomes the canonical regression artifact.

**Version-axis independence.** Seven distinct version types, each evolving on its
own axis (see the identity module's docstring for the full list). Two version
*concepts* named in earlier design notes were confirmed, not newly introduced, as
shared/absent by design: `RecommendationGroup` shares the reserved
`RecommendationVersion` axis with `Recommendation` (per §5, not a gap);
`RecommendationReference` carries no dedicated schema-version type, mirroring every
sibling subsystem's atomic finding/issue model.

## 9. PlatformContext

`PlatformContext` exposes three composition-root methods, construction only:

- `create_recommendation_policy() -> RecommendationPolicy`
- `create_recommendation_rule_catalog() -> RecommendationRuleCatalog` (CAP-082B)
- `create_recommendation_service() -> RecommendationService` (now returns
  `DeterministicRecommendationService`, CAP-082B)

Mirroring `create_enhancement_policy()` / `create_enhancement_rule_catalog()` /
`create_requirement_enhancement_service()` (ADR-0018) and `create_quality_policy()` /
`create_quality_governance_service()` (ADR-0017), these are the **only** sanctioned
points outside the `recommendation` package that may construct its objects,
enforced by a containment test.

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
2. **Done (CAP-082B).** Deterministic Recommendation Engine: derive recommendations
   strictly from recorded upstream observations/findings/issues (Recommendation 7),
   never independent analysis; governed rule catalogue; policy-derived
   prioritization; grouping; confidence surfacing; metrics; summary. See §13.
3. Prioritization and grouping engines beyond the deterministic baseline (e.g.
   statistical re-ranking), reading the same `PrioritizationRules` / `GroupingRules`.
4. Confidence scoring beyond the deterministic hint-and-floor model.
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

## 13. CAP-082B — Deterministic Recommendation Engine

Stage 0 of CAP-082B reviewed every CAP-082A freeze point and found no architectural
weakness: `RecommendationResult` is the permanent runtime contract,
`RecommendationService` the permanent entry point, `RecommendationPolicy` and every
canonical model frozen, `PlatformContext` the sole composition root, and
Recommendation dormant. CAP-082B proceeded as a **pure implementation milestone**.

**Governed rule catalogue.** A new `recommendation/rules/` package mirrors
`quality_governance/rules/` and `enhancement/rules/`:

- `RecommendationRuleCategory` — 18 governed members, one per distinguishable shape
  of upstream evidence (e.g. `ENHANCEMENT_DEPENDENCY_GAP`, `GROUNDING_CONTRADICTED`,
  `VALIDATION_ISSUE_CRITICAL`, `CP1_FINDING_FAIL`, `QUALITY_DECISION_FAIL`).
- `RecommendationPolicyToggle` — names the `RecommendationCapabilitySwitches` field
  that gates a rule (every default rule references `ENABLE_DETERMINISTIC_ENGINE`).
- `RecommendationRule` — metadata only: rule id, category, source subsystem,
  recommendation type, priority/effort/confidence hints, the enable switch, the
  policy reference, plus descriptive (`rule_name`, `guidance`) and ordering
  (`evaluation_order`) fields in the same spirit as `QualityRule` / `EnhancementRule`.
  No executable behaviour.
- `RecommendationRuleCatalog` — ordering, lookup by id/category, filtering by
  source; performs no generation itself.
- The default catalogue (`default_recommendation_rule_catalog()`) ships 18 rules
  covering all five `RecommendationSource` values, all nine `RecommendationType`
  values, and all four `RecommendationPriority` values.

**`DeterministicRecommendationEngine` (`recommendation/engine.py`).** Consumes only
the five frozen result contracts (never an upstream implementation class). Pipeline:

1. **Candidate collection** — dispatch each piece of upstream evidence (an
   `EnhancementFinding`, `GroundingFinding`, `ValidationIssue`, `CP1Finding`,
   `QualityFinding`, or the release `QualityDecision` itself) to exactly one
   `RecommendationRuleCategory`, then look up that category's governed rule.
2. **Confidence surfacing** — drop a candidate whose rule `confidence_hint` is below
   `ConfidenceRules.minimum_confidence_to_surface` (or keep everything if
   `enable_confidence_scoring` is off). No score is computed; the hint is recorded.
3. **Priority resolution (Recommendation 9)** — every recommendation's priority is
   the matched rule's `priority_hint`, clamped to `PrioritizationRules.
   enabled_priorities` and capped by `max_recommendations_per_priority` (cascading
   demotion to the next enabled priority, in fixed dispatch order). The engine never
   branches on `recommendation_source` or `recommendation_type` to pick a priority.
4. **Recommendation assembly** — `title`/`description` come entirely from the
   matched rule's `rule_name`/`guidance` (never copied from the finding's message);
   `rationale` names only the reference id; each recommendation carries exactly one
   `RecommendationReference`.
5. **Grouping** — one `RecommendationGroup` per populated, policy-enabled
   `RecommendationType`, membership capped by `GroupingRules.
   max_recommendations_per_group`.
6. **Metrics and summary** — each computed exactly once, from the final
   recommendation/group sets.

**Determinism.** Recommendation/group ids are pure functions of
`(execution_id, ordinal)`, where `ordinal` is a candidate's fixed position in the
full dispatch order — established *before* confidence filtering, so a surviving
recommendation's id never shifts because other candidates were dropped. No
randomness, no UUID; `started_at`/`completed_at` come from an injected clock.

**Policy value tuning.** `RecommendationCapabilitySwitches.
enable_deterministic_engine` flips `False → True` in the shipped default
(`RecommendationPolicyVersion` 1.0.0 → 1.1.0) — a versioned policy *value* change,
never a shape or engine code change.

**PlatformContext.** `create_recommendation_service()` now returns
`DeterministicRecommendationService` (`DormantRecommendationService` is removed, not
kept alongside — mirroring how CAP-081B replaced Requirement Enhancement's own
dormant service). `create_recommendation_rule_catalog()` is added. Still unwired —
nothing calls `recommend()` at runtime; the golden baseline, Architecture Version,
and Platform Version are unchanged.

**Tests.** 83 new deterministic tests across `test_recommendation_rules.py` and
`test_recommendation_engine.py`, plus updated boundary tests in
`test_recommendation_service.py` / `test_recommendation_policy.py`: every source,
every dispatch category, policy-driven prioritization/grouping/confidence behaviour,
determinism, serialization round-trips, explainability, and containment
(no engine/service reference outside `PlatformContext`, no execution-package or
serializer dependency, no upstream implementation import).
