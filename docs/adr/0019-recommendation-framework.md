# ADR-0019 — Recommendation Framework

- **Status:** Accepted (CAP-082A — Architecture & Governance Freeze; CAP-082B — Deterministic Recommendation Engine implemented behind the frozen contracts)
- **Date:** 2026-07-14 (CAP-082A — Architecture & Governance Freeze); 2026-07-15 (CAP-082B — Deterministic Recommendation Engine)
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** CAP-082B (Deterministic Recommendation Engine — implements the first real engine behind the frozen contracts, mirroring how CAP-081B implemented the first deterministic Requirement Enhancement engine behind ADR-0018, and CAP-080B implemented the first deterministic Quality Governance rule evaluator behind ADR-0017).
- **Governing design:** `docs/proposals/recommendation-framework.md`
- **Depends on:** ADR-0018 (Requirement Enhancement Framework), ADR-0016 (Evidence Grounding and Traceability), ADR-0017 (Quality Governance Framework), and the Validation and CP1 subsystems — the Recommendation Framework consumes their five completed outputs: `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `CP1Result`, `QualityGovernanceResult`.
- **Runtime status:** **Implemented, still dormant (CAP-082B).** `DeterministicRecommendationEngine` generates, prioritizes, groups, confidence-scores, and summarizes recommendations entirely from the governed `RecommendationRuleCatalog` and `RecommendationPolicy`. `RecommendationService.recommend` is no longer abstract-only — `DeterministicRecommendationService` (replacing CAP-082A's `DormantRecommendationService`) delegates to the engine. `PlatformContext.create_recommendation_service()` now returns the deterministic implementation; `create_recommendation_rule_catalog()` is added alongside it. Nothing is wired into the Requirement Intelligence execution pipeline — no CLI phase calls `recommend` — so runtime behaviour is byte-identical and the golden baseline is unchanged. The Architecture Version remains **1.2.0**, `RecommendationResult`'s shape is unchanged, and no frozen contract of any upstream subsystem changed. See "CAP-082B — Deterministic Recommendation Engine (Implementation)" below.

## Problem

The Requirement Intelligence Layer now produces five independent, governed
judgements per run:

| Result | Question it answers | Owner |
|---|---|---|
| `RequirementEnhancementResult` | *What does the requirement set look like structurally — enriched, related, observed?* | Requirement Enhancement (ADR-0018) |
| `GroundingResult` | *Is each generated requirement supported by the evidence?* | Grounding (ADR-0016) |
| `ValidationResult` | *Is the response well-formed against the reasoning contract?* | Validation |
| `CP1Result` | *Is the run engineering-ready?* | CP1 (ADR-0011) |
| `QualityGovernanceResult` | *Is the run releasable on quality grounds?* | Quality Governance (ADR-0017) |

**No subsystem turns these five judgements into an actionable recommendation.**
Each result observes, judges, or decides within its own lane; none of them tells an
engineer *what to do next*. That capability exists nowhere in the repository today
(confirmed by the Stage 0 assessment below). Left unbuilt, every downstream
consumer (a report, a dashboard, a future CI/CD gate) must independently re-derive
"what should happen next" from five separate results, ad hoc, per consumer. Built
carelessly — as an extension bolted onto Quality Governance (the closest thing to a
release-facing verdict) or onto Requirement Enhancement (the closest thing to a
structural observation) — it would fuse a distinct responsibility into a subsystem
that already has one, exactly the coupling ADR-0001 forbids and ADR-0015/0016/0017/
0018 each declined for their own domains.

### Stage 0 — Repository assessment (existing recommendation-adjacent surfaces)

Before introducing a new subsystem, every existing place the word "recommendation"
(or an equivalent placeholder) already appears was reviewed:

- **Requirement Enhancement (ADR-0018) Recommendation 3 — "Observation Before
  Recommendation."** `RequirementObservation` / `EnhancementFinding` are frozen as
  the raw/interpreted layers a *future* recommendation must derive from; ADR-0018
  §D7/§D8 and the proposal's roadmap (§11, item 5) explicitly reserve "the
  Recommendation layer, derived strictly from recorded observations" as the next
  capability — this milestone is that reservation being cashed in, not a new idea.
- **Grounding (ADR-0016).** `GroundingResult` / `GroundingAssessment` /
  `ExplanationEntry` carry per-requirement support explanations, but no
  recommendation field or object anywhere in `grounding/models/`.
- **Validation.** `ValidationIssue` records a structural problem
  (`requirement_intelligence/validation/models/validation_issue.py`); it recommends
  nothing — it is a raw signal layer, analogous to `RequirementObservation`.
- **CP1.** `CP1Finding` records an engineering-readiness gap
  (`requirement_intelligence/cp1/models/cp1_finding.py`); likewise a raw signal, not
  a recommendation.
- **Quality Governance (ADR-0017).** `QualityFinding` records a violated governed
  rule; `QualityDecision` (`PASS` / `PASS_WITH_WARNINGS` / `FAIL`) is the release
  verdict. Neither is a recommendation: a decision says whether the run may release,
  never what to do about a specific finding.
- **No dedicated "recommendation" model, identity, policy, or service exists
  anywhere in the repository.** Every one of the five surfaces above is a raw or
  interpreted *signal* layer that a recommendation must be derived from
  (Recommendation 1 below) — none of them is itself a recommendation, and none
  overlaps with what this ADR introduces.

## Decision

Introduce a new governed subsystem, **`requirement_intelligence/recommendation/`**,
that will own recommendation generation, prioritization, grouping, and confidence
scoring over the five completed upstream results. It:

1. Introduces canonical, immutable models — `Recommendation`,
   `RecommendationReference`, `RecommendationGroup`, `RecommendationSummary`,
   `RecommendationMetrics`, and `RecommendationResult` — following the `Schema`
   conventions and the typed-identity pattern of ADR-0015/0016/0017/0018.
2. Introduces strongly typed identities — `RecommendationPolicyId`,
   `RecommendationId`, `RecommendationGroupId`, `RecommendationResultId` —
   deterministic value objects, no UUIDs, no timestamps, no randomness.
3. Introduces independent version axes — `RecommendationFrameworkVersion`,
   `RecommendationPolicyVersion`, `RecommendationVersion`,
   `RecommendationResultVersion` — each evolving without forcing the others to
   change (Recommendation 5).
4. Introduces a governed `RecommendationPolicy` (immutable data: capability
   switches, prioritization rules, grouping rules, confidence rules, projection
   rules) with a `RecommendationPolicyBuilder` and `default_recommendation_policy()`.
5. Fixes the single runtime boundary — `RecommendationService.recommend(
   enhancement_result, grounding_result, validation_result, cp1_result,
   quality_governance_result) -> RecommendationResult` — as an **abstract, dormant
   contract**. `PlatformContext` gains `create_recommendation_policy()` and
   `create_recommendation_service()`.

The Recommendation Framework runs **after** every one of the five upstream
judgements has completed, consuming only their completed runtime contracts; it is a
**peer consumer** of those five results and owns none of their computation.
Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, and the
Execution Package are **unchanged**.

**CAP-082A establishes the architecture only.** No recommendation is generated, no
heuristic runs, no priority or confidence is scored, no grouping is formed, and
nothing is wired into a runtime path. Runtime behaviour is byte-identical; the
golden baseline is unchanged; the Architecture Version remains 1.2.0.

The full model and roadmap is in `docs/proposals/recommendation-framework.md`.

---

## D1 — Why Recommendation is a new, peer subsystem, not an extension of Quality Governance or Requirement Enhancement

A recommendation answers a question none of the five upstream subsystems asks:
*given everything already judged, what should an engineer do next?* Quality
Governance decides whether a run may release; it does not say what to fix first.
Requirement Enhancement observes structural properties; it does not translate an
observation into a prioritized action across all five judgement domains. Folding
recommendation generation into Quality Governance would make release-decision and
remediation-guidance one responsibility; folding it into Requirement Enhancement
would make structural observation and cross-domain advice one responsibility —
either way, two concerns collapse into one owner, exactly the coupling ADR-0001
forbids and ADR-0015/0016/0017/0018 each declined for their own domains. The
Recommendation Framework is a distinct responsibility with a distinct owner, and a
**consumer only** of the five completed results (Recommendation 1).

## D2 — Why recommendation sits after all five upstream judgements

The frozen pipeline order (ADR-0018 §D9, extending ADR-0017 §D30) is:

```
Engineering Context → Analysis → Requirement Enhancement → Grounding
    → Validation → CP1 → Quality Governance → Execution Package
```

The Recommendation Framework's insertion point is **after Quality Governance,
before the Execution Package**:

```
Engineering Context → Analysis → Requirement Enhancement → Grounding
    → Validation → CP1 → Quality Governance → Recommendation → Execution Package
```

A recommendation can only be fully explainable and correctly prioritized once every
upstream judgement is available — a recommendation formed before Quality Governance
completes could not, for example, weigh a `FAIL` verdict's mandatory gates. Placing
Recommendation last (before the Execution Package) is what lets it optionally read
any or all of the five completed results without any of them ever depending on it.
**CAP-082A wires nothing**: this insertion point is documented, not implemented — no
CLI phase calls `recommend`.

## D3 — Why `RecommendationResult` is the complete, self-contained record

The runtime contract is `RecommendationResult`: a peer to
`RequirementEnhancementResult` / `GroundingResult` / `ValidationResult` /
`CP1Result` / `QualityGovernanceResult`. It carries every recommendation, every
group, the summary, the metrics, the governing policy identity/version, and — via
`RecommendationInputReference` — the identity and version of each of the five
upstream results it consumed. This is a deliberate design choice, mirroring
ADR-0018 §D3 and ADR-0017 §D3: the result must be **completely explainable from
this one object**, with no need to re-run recommendation generation or inspect any
runtime service, Requirement Enhancement, Grounding, Validation, CP1, or Quality
Governance. The model records *provenance* of the consumed inputs, never their
contents, so the record is legible and self-contained without embedding or coupling
to the upstream aggregates. The result's validator enforces the explainability
invariant structurally: a group cannot reference a recommendation absent from the
same result, and no recommendation or group id may repeat.

## D4 — Why the models compute nothing (assembly targets only)

Every canonical model is `frozen`, tuple-backed, camelCase, and free of
timestamps/UUIDs, exactly like the Requirement Enhancement, Grounding, and Quality
Governance models. None computes a value: a future engine populates them. The only
logic present is validator *invariants* that enforce cross-referential integrity and
one explainability invariant — `Recommendation` must carry at least one
`RecommendationReference` (Recommendation 7), `RecommendationGroup` must not name a
recommendation twice, and `RecommendationResult` groups must resolve to
recommendations already present in the same result. Introducing the models fully
frozen — before any engine exists — forces their shape to be designed for every
future capability, not retrofitted around the first one, and lets each subsequent
milestone land behind an unchanged contract.

## D5 — Why identities are deterministic and independently versioned

`RecommendationId.for_ordinal(execution_id, ordinal)`,
`RecommendationGroupId.for_ordinal(execution_id, ordinal)`, and
`RecommendationResultId.for_execution(execution_id)` are **pure functions** of
their inputs — no clock, no UUID — so the same run always mints the same ids and a
result is reproducible and comparable across runs. Four version axes
(`RecommendationFrameworkVersion`, `RecommendationPolicyVersion`,
`RecommendationVersion`, `RecommendationResultVersion`) are distinct typed value
objects that advance **independently**: this is what lets a recommendation type be
added, a policy be tuned, or the result contract be extended, without forcing the
others to change (Recommendation 5). Like ADR-0018 §D5, no existing identifier is
retyped; the change is purely additive, and the base identifier/version classes are
duplicated (not imported) from `enhancement`, exactly as that package duplicated
them from `quality_governance`, `grounding`, and `context_orchestration` — the
eventual home remains `shared/` (ADR-0015 §C, ADR-0016 §D6, ADR-0017 identity module
docstring, ADR-0018 §D5).

## D6 — Why the service boundary is fixed before any behaviour (dormant)

The subsystem exposes exactly one runtime entry point: `RecommendationService`, an
abstract contract with a single method — `recommend(enhancement_result,
grounding_result, validation_result, cp1_result, quality_governance_result) ->
RecommendationResult`. Everything else in the package (models, identities, policy)
is internal. The service depends only on the five frozen **result contracts** it
consumes — never on any *implementation* class (no
`DeterministicRequirementEnhancementEngine`, `GroundingService`,
`ResponseValidator`, `CP1Service`, or `QualityGovernanceService`). Fixing the
boundary *before* implementing any behaviour is what lets each later milestone —
deterministic generation, prioritization, grouping, confidence scoring, runtime
activation — land behind the unchanged `recommend` signature, exactly as ADR-0018
§D6 did for `RequirementEnhancementService.enhance`, ADR-0016 §D7 did for
`GroundingService.assess`, and ADR-0017 §D6 did for
`QualityGovernanceService.evaluate`.

**CAP-082A establishes the boundary only.** `recommend` is abstract and the
registered `DormantRecommendationService` raises `NotImplementedError`;
`PlatformContext.create_recommendation_service()` constructs it with the governed
policy and **no engine**. It is dormant — no runtime path consumes it, guarded by a
containment test that permits only `PlatformContext` to name the service outside
the package — so runtime behaviour is byte-identical.

## D7 — Explainability first: every recommendation must be traceable to upstream evidence

`Recommendation` carries one or more `RecommendationReference` entries, each naming
a `RecommendationSource` (which of the five upstream results), a referenced id (the
specific observation/finding/issue), and that result's contract version — never a
copy of the referenced object's content. The model validator rejects a
`Recommendation` with zero references: a recommendation with no traceable upstream
evidence is not explainable and must never be constructible. This is the frozen
counterpart to `EnhancementFinding.observation_id` (ADR-0018) and
`AssessmentFindingReference` (ADR-0017 §D26) — reference, never copy — extended
here as a hard model invariant from the outset, because Recommendation is one layer
further downstream and has one more subsystem's worth of provenance to preserve.

## D8 — Runtime vs. Execution Package boundary, frozen in advance

Exactly as ADR-0018 §D8 froze `RequirementEnhancementResult`'s serialization
invariant before any `EnhancementSerializer` existed, this milestone freezes
`RecommendationResult`'s boundary before any recommendation serializer, Execution
Package integration, dashboard, or reporting capability exists (Recommendation 8):

```
RequirementEnhancementResult, GroundingResult, ValidationResult, CP1Result,
QualityGovernanceResult → RecommendationService.recommend → RecommendationResult
    → Execution Package → JSON / Markdown / reports
```

A future renderer must never call a recommendation engine, `PlatformContext`,
generate a recommendation, form a group, compute a metric, or invoke a policy —
rendering will be projection only. This is documented now, before any serializer
is written, so the first serializer is built *inside* the invariant rather than
retrofitted to satisfy it later.

---

### Recommendation 1 — Recommendation Framework is a consumer only

It never owns Requirement Enhancement, Grounding, Validation, CP1, or Quality
Governance. It consumes only their runtime contracts — `RequirementEnhancementResult`,
`GroundingResult`, `ValidationResult`, `CP1Result`, `QualityGovernanceResult` — and
never re-runs, re-implements, or duplicates any of their computation.

### Recommendation 2 — Never duplicate runtime models

`Recommendation` objects must contain `RecommendationReference` entries — references
to the upstream observation, finding, or issue that grounded them — never copies of
that object's content. Enforced structurally: `RecommendationReference` carries only
an id, a source, and a version; it has no field capable of holding copied content.

### Recommendation 3 — RecommendationResult is the single runtime authority

The Execution Package, the CLI, reports, and future dashboards must consume only
`RecommendationResult`. No other object in this subsystem is a runtime contract.

### Recommendation 4 — Recommendation generation is deferred

CAP-082A freezes architecture only. No recommendation logic, no heuristics, no
scoring, and no prioritization implementation exist. `DormantRecommendationService`
raises `NotImplementedError` on every call.

### Recommendation 5 — Future engines remain replaceable

Deterministic, ML, LLM, hybrid, and rule-based engines all implement the identical
`RecommendationService.recommend` contract. `RecommendationCapabilitySwitches`
reserves `enable_deterministic_engine`, `enable_ml_engine`, and `enable_llm_engine`
as independent, governed toggles for this replaceability, mirroring
`EnhancementCapabilitySwitches`'s reserved-capability pattern (ADR-0018).

### Recommendation 6 — Strict ownership direction

```
Policies → Engine → Runtime Contract → Serializer → Execution Package
```

Never reversed. A policy is read by an engine; an engine produces a runtime
contract; a serializer projects a runtime contract; the Execution Package transports
a serializer's output. No stage may reach backward into an earlier one.

### Recommendation 7 — Explainability first

Every future recommendation must ultimately be explainable from `Recommendation`,
`RecommendationReference`, and `RecommendationResult` alone. No hidden runtime
state. Enforced today by `Recommendation`'s "at least one reference" validator
(§D7) — the invariant exists before any engine could violate it.

### Recommendation 8 — Runtime before reporting

`RecommendationResult` is frozen before any serializer, execution package
integration, dashboard, or reporting work (§D8). This is the same discipline ADR-0018
§D8 applied to `RequirementEnhancementResult` and ADR-0016 §D16 applied to
`GroundingResult`.

---

## Trade-offs

- **A new subsystem adds a sixth judgement per run.** Accepted: Requirement
  Enhancement, Grounding, Validation, CP1, and Quality Governance each judge a
  different lane, and none of them turns their judgement into a prioritized,
  cross-domain action. That capability was missing, not redundant with any of them.
- **Governed defaults are calibrated conservatively, not empirically.** The CAP-082A
  default policy bounds (e.g. `max_recommendations_per_priority = 25`,
  `minimum_confidence_to_surface = 0.5`) are governed data reflecting a deliberately
  conservative first pass, not yet tuned against a real corpus. Accepted: tuning is
  a versioned policy change under a future golden re-baseline, never an engine code
  change (Recommendation 5).
- **A re-baseline will be required at runtime activation.** Adding a recommendation
  phase, artifacts, and pipeline wiring in a later milestone will change golden
  checksums. Accepted: the golden baseline's re-baseline procedure exists precisely
  for intentional additive change; CAP-082A changes nothing about the golden
  dataset, since the subsystem stays unwired.
- **Five-way consumption is a wider dependency surface than any prior subsystem.**
  Quality Governance consumes three results (ADR-0017); Recommendation consumes
  five. Accepted: this is the natural final position in the pipeline — a
  recommendation is only complete once every judgement it might reference has been
  made, and the one-way dependency direction (§D1/§D2) keeps the coupling legible
  and acyclic.

## CAP-082B — Deterministic Recommendation Engine (Implementation)

CAP-082B implements the first real engine behind the CAP-082A boundary. No
architectural weakness was found in Stage 0 review of CAP-082A: `RecommendationResult`
is the permanent runtime contract, `RecommendationService` the permanent entry point,
`RecommendationPolicy` and every canonical model frozen, `PlatformContext` the sole
composition root, and Recommendation remains fully dormant (no CLI, pipeline,
serializer, or Execution Package reference it). CAP-082B proceeded as a **pure
implementation milestone** — no redesign.

- **Governed rule catalogue (new package, `recommendation/rules/`).** Mirrors
  `quality_governance/rules/` and `enhancement/rules/`: `RecommendationRule` is
  metadata only (rule id, `RecommendationRuleCategory`, source subsystem,
  `RecommendationType`, priority/effort/confidence hints, an enable switch, and a
  `RecommendationPolicyToggle` policy reference) — no lambda, no callback, no
  embedded algorithm. `RecommendationRuleCatalog` owns ordering/lookup only.
  `RecommendationRuleBuilder`/`default_recommendation_rule_catalog()` ship 18
  governed rules spanning all five `RecommendationSource` values, all nine
  `RecommendationType` values, and all four `RecommendationPriority` values.
- **`DeterministicRecommendationEngine` (`recommendation/engine.py`).** Consumes only
  the five frozen result contracts; imports no upstream implementation class.
  Dispatches each piece of upstream evidence (an `EnhancementFinding`,
  `GroundingFinding`, `ValidationIssue`, `CP1Finding`, `QualityFinding`, or the
  release `QualityDecision` itself) to exactly one `RecommendationRuleCategory`, then
  reads that category's governed rule for the `RecommendationType`, priority/effort/
  confidence hints, and the policy toggle gating it.
- **Policy-derived priority only (Recommendation 9).** The engine never branches on
  `recommendation_source` or `recommendation_type` to pick a priority. Every
  recommendation's priority is the matched rule's `priority_hint`, then clamped to
  `PrioritizationRules.enabled_priorities` and capped by
  `max_recommendations_per_priority` (cascading demotion, deterministic). A CP1
  recommendation and a Quality Governance recommendation both land at HIGH under
  their own rules in the test suite — proving neither subsystem is auto-HIGH.
- **Confidence surfacing.** A candidate's `confidence_hint` is compared against
  `ConfidenceRules.minimum_confidence_to_surface`; below it, the candidate is
  dropped before assembly (never scored down). Recommendation ids remain a pure
  function of `(execution_id, ordinal)` from the full dispatch order, so filtering
  never shifts a surviving recommendation's id.
- **Grouping (Recommendation 6).** One `RecommendationGroup` per populated,
  policy-enabled `RecommendationType`, membership capped by
  `GroupingRules.max_recommendations_per_group`. Groups own only ordering/
  categorization; content stays on `Recommendation`.
- **Metrics and summary, each computed exactly once**, inside the engine, from the
  final recommendation/group sets — no duplicated arithmetic elsewhere.
- **Explainability preserved (Recommendation 7).** Every `Recommendation.title` /
  `.description` comes entirely from the matched rule's governed metadata
  (`rule_name` / `guidance`) — never copied from the referenced finding's message —
  and `.rationale` names only the reference id. `RecommendationReference` still never
  copies upstream content.
- **Policy value tuning (not a shape change).** `RecommendationCapabilitySwitches.
  enable_deterministic_engine` flips `False → True` in the shipped default policy
  (`RecommendationPolicyVersion` 1.0.0 → 1.1.0) now that the engine exists — a
  versioned policy *value* change, exactly the kind Recommendation 5 anticipated,
  never a policy *shape* or engine code change.
- **PlatformContext.** `create_recommendation_service()` now returns
  `DeterministicRecommendationService` (replacing `DormantRecommendationService`,
  which CAP-082B removes — mirroring how CAP-081B's
  `DeterministicRequirementEnhancementService` replaced its own dormant
  predecessor). `create_recommendation_rule_catalog()` is added alongside
  `create_recommendation_policy()`. Still unwired: nothing calls `recommend()` at
  runtime, so the golden baseline, Architecture Version, and Platform Version are
  all unchanged.
- **Tests.** 83 new deterministic tests (`test_recommendation_rules.py`,
  `test_recommendation_engine.py`) plus updated boundary tests
  (`test_recommendation_service.py`, `test_recommendation_policy.py`) cover every
  source, every dispatch category, prioritization/grouping/confidence policy
  interactions, determinism, serialization round-trips, explainability, and
  containment.

## Future evolution

- ~~**CAP-082B — Deterministic Recommendation Engine.**~~ **Done.** See above.
- **Prioritization and grouping engines** beyond the deterministic baseline (e.g. a
  statistical or ML re-ranking) — reading the same `PrioritizationRules` /
  `GroupingRules`, without changing `RecommendationResult`'s shape.
- **Confidence scoring** beyond the deterministic hint-and-floor model, with ML/LLM
  alternatives reserved by `RecommendationCapabilitySwitches`.
- **Runtime activation** — wiring `recommend` into the live pipeline after Quality
  Governance, plus the Execution Package projection and golden re-baseline,
  mirroring CAP-081C's activation of Requirement Enhancement (ADR-0018 §D9).
- Promotion of the shared version/identity value-objects to `shared/` (the debt
  ADR-0015 §C, ADR-0016, ADR-0017, and ADR-0018 §D5 already name).

## Ownership, runtime position, governance

- **Owns:** recommendation generation, recommendation prioritization, recommendation
  grouping, recommendation confidence scoring, recommendation metadata.
- **Does not own:** Engineering Context Orchestration, Analysis, Requirement
  Enhancement, Grounding, Validation, CP1, Quality Governance, Execution Package,
  Reporting, Serialization.
- **Runtime position (implemented, still dormant, CAP-082B):**
  `RequirementEnhancementResult` / `GroundingResult` / `ValidationResult` /
  `CP1Result` / `QualityGovernanceResult` → `RecommendationService.recommend`
  (`DeterministicRecommendationService` → `DeterministicRecommendationEngine`) →
  `RecommendationResult` → (future) Execution Package. Architecture frozen; a real
  deterministic engine exists; nothing wired into the runtime pipeline.
- **Governance:** registered as CAP-082 for the Requirement Intelligence Layer. This
  ADR is **Accepted** for its architecture scope; CAP-082B is **Accepted** as the
  first deterministic engine under the unchanged contract.
