# ADR-0022 — Continuous Improvement Framework

- **Status:** Accepted (CAP-083A — Architecture & Governance Freeze; CAP-083B — Deterministic Engine implemented behind the frozen contracts; CAP-083B.1 — `ContinuousImprovementResult` Runtime Contract permanently certified, no behaviour change; CAP-083C — Runtime Integration & Execution Package Activation, live in the pipeline)
- **Date:** 2026-07-15 (CAP-083A — Architecture & Governance Freeze); 2026-07-15 (CAP-083B — Deterministic Continuous Improvement Engine); 2026-07-15 (CAP-083B.1 — Runtime Contract Freeze); 2026-07-15 (CAP-083C — Runtime Integration)
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** CAP-083B (Deterministic Continuous Improvement Engine — implements the first real engine behind the frozen contracts, mirroring how CAP-082B implemented the first deterministic Recommendation engine behind ADR-0019); CAP-083B.1 (permanent `ContinuousImprovementResult` runtime-contract certification, mirroring CAP-082B.1, CAP-081B.1, and CAP-080B.1.1 — no behaviour change); CAP-083C (Runtime Integration & Execution Package Activation, mirroring CAP-082C's activation of Recommendation — see §D11).
- **Governing design:** `docs/proposals/continuous-improvement-framework.md`
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — this is the first Layer 2 capability it names) and ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution — this framework's every boundary is a direct application of ADR-0021's Truth Hierarchy).
- **Runtime status:** **Live (CAP-083C).** `DeterministicContinuousImprovementEngine` detects recurring findings, observes trends, and generates opportunities entirely from the governed `ImprovementRuleCatalog` and `ImprovementPolicy`. The CLI's `run_continuous_improvement_phase` obtains `DeterministicContinuousImprovementService` from `PlatformContext` and calls `improve` immediately after Recommendation, at the permanently frozen end of the pipeline, over a single-execution `HistoricalDatasetReference` this run mints (no real, multi-execution Historical Dataset implementation exists yet, ADR-0021 §Stage 6). `ContinuousImprovementSerializer` projects the result into three Execution Package artifacts (`continuous_improvement_result.json` / `continuous_improvement_report.md` / `continuous_improvement_metrics.md`), and the manifest gains three additive, package-metadata-only keys. The golden dataset re-baselined `1.4.0` → `1.5.0` to include them. The Architecture Version remains **1.2.0**, `ContinuousImprovementResult`'s shape is unchanged, and no frozen contract of any upstream subsystem changed. See §D11.

## Problem

ADR-0020 named Continuous Learning as Layer 2 and reserved four capabilities inside it: CAP-083 (Continuous Improvement), CAP-084 (Knowledge Graph), CAP-085 (Organizational Memory), CAP-086 (Learning Framework). ADR-0021 froze the Truth Hierarchy every one of them must obey — Runtime Truth (Layer 1) → Historical Truth (Layer 2) → Derived Knowledge (Layers 2–7) — and required (Recommendation 11) that every future Layer 2–7 ADR explicitly declare which level it consumes and which it produces.

**No capability inside Layer 2 exists yet.** Layer 1 answers questions about one execution; nothing today answers a question about *many* executions — "which validation failures keep recurring?", "is grounding quality trending up or down for this module?", "which documentation gap keeps getting flagged?" Left unbuilt, and built without a frozen architecture first, the first Layer 2 capability would have to invent, under deadline pressure, exactly the kind of ad hoc answer ADR-0021 §Stage 2 warned against: duplicated history, inconsistent datasets, competing truths, hidden state, irreproducible learning.

### Stage 0 — Repository assessment

ADR-0015 through ADR-0020 were reviewed. Layer 1 is complete: Engineering Context, Requirement Analysis, Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, and the Execution Package are all accepted and live (ADR-0020 §Stage 0). Every Layer 1 runtime contract — `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `CP1Result`, `QualityGovernanceResult`, `RecommendationResult` — remains immutable Runtime Truth, scoped to exactly one execution, exactly as ADR-0021 §Stage 3 requires. No existing ADR or module defines historical ownership, a historical dataset, execution lineage across runs, or organizational memory (ADR-0021 §Stage 0 already confirmed this; nothing built since has changed that).

> No architectural weakness found. Proceeding with a pure architecture and governance freeze.

## Decision

Introduce a new governed subsystem, **`requirement_intelligence/continuous_improvement/`**, that will own recurring-finding detection, trend detection, and opportunity generation over a **Historical Dataset** — never over a single execution's Runtime Truth directly. It:

1. Introduces canonical, immutable models — `ImprovementFinding`, `ImprovementTrend`, `ImprovementOpportunity`, `ImprovementSummary`, `ImprovementMetrics`, `HistoricalDatasetReference`, and `ContinuousImprovementResult` — following the `Schema` conventions and the typed-identity pattern of ADR-0015–ADR-0019.
2. Introduces strongly typed identities — `ImprovementPolicyId`, `ImprovementFindingId`, `ImprovementTrendId`, `ImprovementOpportunityId`, `ImprovementAssessmentId` (reserved), `ContinuousImprovementResultId` — deterministic value objects, no UUIDs, no timestamps, no randomness.
3. Introduces independent version axes — `ContinuousImprovementFrameworkVersion`, `ImprovementPolicyVersion`, `ImprovementTrendVersion` (reserved), `ImprovementAssessmentVersion` (reserved), `ContinuousImprovementResultVersion` — each evolving without forcing the others to change (Recommendation 5, ADR-0019 precedent).
4. Introduces a governed `ImprovementPolicy` (immutable data: capability switches, deterministic thresholds) with an `ImprovementPolicyBuilder` and `default_improvement_policy()`.
5. Fixes the single runtime boundary — `ContinuousImprovementService.improve(historical_dataset: HistoricalDatasetReference) -> ContinuousImprovementResult` — as an **abstract, dormant contract**. `PlatformContext` gains `create_improvement_policy()` and `create_continuous_improvement_service()`.

The Continuous Improvement Framework consumes **Historical Truth only** — never a Layer 1 runtime contract directly, never an Execution Package artifact, never a report or a manifest (ADR-0021 §Stage 7/§Stage 8). It is the **first Layer 2 peer**: nothing above it exists yet, and it owns none of Layer 1's responsibilities.

**CAP-083A establishes the architecture only.** No finding is derived, no trend is observed, no opportunity is generated, no historical dataset is built, and nothing is wired into a runtime path. Runtime behaviour is byte-identical; the golden baseline is unchanged; the Architecture Version remains 1.2.0.

The full model and roadmap is in `docs/proposals/continuous-improvement-framework.md`.

---

## D1 — Why Continuous Improvement is a new, Layer 2 subsystem, never an extension of a Layer 1 capability

A recurring finding, a trend, or an opportunity answers a question no Layer 1 subsystem asks: *given everything already judged across many executions, what keeps happening?* Quality Governance judges one run's releasability; it does not judge whether release quality is trending up or down across the last twenty runs. Recommendation suggests what to do next for one execution; it does not notice that the same category of recommendation has recurred for months. Folding recurrence-detection into any Layer 1 subsystem would make a single-execution judge also an owner of cross-execution history — exactly the coupling ADR-0001 forbids within a layer, and exactly the layer-boundary violation ADR-0020 §Stage 3 now forbids across layers. Continuous Improvement is a distinct responsibility with a distinct owner, and a **consumer only** of Historical Truth (Recommendation 1).

## D2 — Why Continuous Improvement consumes a `HistoricalDatasetReference`, never a Layer 1 result directly

ADR-0021 §Stage 6 names the Historical Dataset as the canonical owner of historical executions — ordering, lineage, retention, indexing, search, organization — a responsibility this milestone does not build and does not need to. What it freezes is the shape of the *reference* a future engine will receive in place of the dataset: `HistoricalDatasetReference` names which dataset, which version, what execution range, what governed history window, and when the reference was minted — never the dataset's content, and never a Layer 1 result embedded inside it. This is why `ContinuousImprovementService.improve` takes exactly one parameter, unlike `RecommendationService.recommend`'s five: Recommendation is a Layer 1 peer consumer of five completed Layer 1 results; Continuous Improvement is a Layer 2 capability that has exactly one upstream concept to consume — the Historical Dataset — however many Layer 1 executions that dataset ultimately aggregates.

## D3 — Why `ContinuousImprovementResult` is Derived Knowledge, never Historical Truth

The runtime contract is `ContinuousImprovementResult` — the first Layer 2 runtime contract, and the first to sit one level above Runtime Truth in ADR-0021's Truth Hierarchy. It is **Derived Knowledge**: reproducible from the `HistoricalDatasetReference` it consumed, but never itself canonical history. It must never be written back into the Historical Dataset it was computed from — the same one-way boundary ADR-0021 §Stage 3 draws between Historical Truth and Derived Knowledge, frozen here as a model-level invariant before any engine could violate it. This mirrors ADR-0019 §D3's freeze of `RecommendationResult` as the complete, self-contained record: the result must be **completely explainable from this one object**, with no need to re-run Continuous Improvement or inspect any runtime service, Historical Dataset, or Layer 1 subsystem.

## D4 — Why the models compute nothing (assembly targets only)

Every canonical model is `frozen`, tuple-backed, camelCase, and free of UUIDs/randomness, exactly like every prior subsystem's models. None computes a value: a future engine populates them. The only logic present is validator *invariants* that enforce cross-referential integrity, the explainability invariant, and — new to this subsystem — the **historical consistency invariant**: `ImprovementFinding.occurrence_count` and `ImprovementTrend.observation_count` must equal the length of their respective `contributing_execution_ids` tuples, so a finding or trend can never claim a recurrence it does not name the executions for. `ImprovementOpportunity` must carry at least one `source_finding_ids` or `source_trend_ids` entry (Recommendation 6 below) — a recurrence-derived opportunity with no traceable finding or trend is not explainable and must never be constructible.

## D5 — Why identities are deterministic and independently versioned

`ImprovementFindingId.for_ordinal(dataset_id, ordinal)`, `ImprovementTrendId.for_ordinal`, `ImprovementOpportunityId.for_ordinal`, and `ContinuousImprovementResultId.for_dataset(dataset_id)` are **pure functions** of their inputs — no clock, no UUID — so the same historical dataset always mints the same ids and a result is reproducible and comparable across runs over that dataset. This is the same discipline ADR-0019 §D5 froze for `RecommendationId`/`RecommendationResultId`, lifted here from execution-scoped to dataset-scoped minting, exactly as ADR-0021 requires for any cross-execution identity. Five distinct version axes evolve **independently** (Recommendation 5); like every prior subsystem, no existing identifier is retyped, and the base identifier/version classes are duplicated (not imported) from `recommendation` — the eventual home remains `shared/` (ADR-0015 §C, ADR-0016 §D6, ADR-0017 identity module docstring, ADR-0018 §D5, ADR-0019 §D5).

## D6 — Why the service boundary is fixed before any behaviour (dormant)

The subsystem exposes exactly one runtime entry point: `ContinuousImprovementService`, an abstract contract with a single method — `improve(historical_dataset) -> ContinuousImprovementResult`. Everything else in the package (models, identities, policy) is internal. The service depends only on `HistoricalDatasetReference` — never on any Layer 1 *implementation* class (no `DeterministicRecommendationEngine`, `QualityGovernanceService`, `GroundingService`, or any other Layer 1 runtime service), and never on the Historical Dataset's own implementation, which does not exist yet. Fixing the boundary *before* implementing any behaviour is what lets each later milestone — deterministic generation, trend detection, opportunity generation, runtime activation — land behind the unchanged `improve` signature, exactly as ADR-0019 §D6 did for `RecommendationService.recommend`.

## D7 — Explainability first: every finding, trend, and opportunity must be traceable to execution inputs

`ImprovementFinding` and `ImprovementTrend` each carry `contributing_execution_ids` — the executions the recurrence/trend was observed across, by id only, never by embedding that execution's Runtime Truth. `ImprovementOpportunity` references the findings and/or trends it was derived from by id only. The model validators reject a finding or trend whose occurrence/observation count does not match its named executions, and reject an opportunity with zero references — a recurrence or opportunity with no traceable historical evidence is not explainable and must never be constructible. This realizes ADR-0021 §Stage 8's historical explainability chain (`Historical Dataset → Runtime Contracts → Execution Inputs`) as a hard model invariant from the outset, exactly as ADR-0019 §D7 did for `Recommendation` one layer down.

## D8 — Runtime vs. Execution Package boundary, frozen in advance

Exactly as ADR-0019 §D8 froze `RecommendationResult`'s serialization invariant before any `RecommendationSerializer` existed, this milestone freezes `ContinuousImprovementResult`'s boundary before any Continuous Improvement serializer, Execution Package integration, dashboard, or reporting capability exists (Recommendation 5 of this ADR):

```
HistoricalDatasetReference → ContinuousImprovementService.improve → ContinuousImprovementResult
    → Execution Package (future) → JSON / Markdown / reports
```

A future renderer must never call a Continuous Improvement engine, `PlatformContext`, generate a finding, observe a trend, name an opportunity, compute a metric, or invoke a policy — rendering will be projection only.

## D9 — Deterministic Continuous Improvement Engine (CAP-083B)

CAP-083B implements the first real engine behind the CAP-083A boundary. No architectural weakness was found in Stage 0 review of CAP-083A: `ContinuousImprovementResult` is the permanent runtime contract, `ContinuousImprovementService` the permanent entry point, `ImprovementPolicy` and every canonical model frozen, `PlatformContext` the sole composition root, and Continuous Improvement fully dormant. One implementation question was surfaced and resolved before writing code (see the Historical Dataset Resolution Principle below); CAP-083B otherwise proceeded as a **pure implementation milestone** — no redesign, no frozen-contract change.

**Governed rule catalogue (new package, `continuous_improvement/rules/`).** Mirrors `recommendation/rules/`: `ImprovementRule` is metadata only (rule id, `ImprovementRuleFamily`, source subsystem, the governed vocabulary member(s) it names, a severity/guidance hint, an enable switch, and an `ImprovementPolicyToggle` policy reference) — no lambda, no callback, no embedded algorithm. `ImprovementRuleCatalog` owns ordering/lookup only. `ImprovementRuleBuilder`/`default_improvement_rule_catalog()` ship 16 governed rules: 5 RECURRENCE rules (one per `ImprovementFindingCategory`, including the additively introduced `RECURRING_ENHANCEMENT_ISSUE` — see below), 6 TREND rules (one per `ImprovementSourceLayer`), and 5 OPPORTUNITY rules (one per `ImprovementOpportunityCategory`, two sourced from a second subsystem).

**One additive enum member (not a redesign).** `ImprovementFindingCategory` gains a fifth member, `RECURRING_ENHANCEMENT_ISSUE`, alongside the fifth RECURRENCE rule (Requirement Enhancement) the milestone brief names. A `StrEnum` member addition never breaks an existing consumer — the same additive-versioning discipline this platform already applies elsewhere (e.g. `CP1Result` 1.0 → 1.1). This enum lives in `models/enums.py`, which was not named among CAP-083B's explicitly frozen items (`ContinuousImprovementResult`, `ImprovementPolicy`, `HistoricalDatasetReference`, the `improve` signature, `PlatformContext` ownership, the Truth Hierarchy) — all of which remain byte-identical.

**Historical Dataset Resolution Principle (frozen, new).** `HistoricalDatasetReference` intentionally carries provenance only (ADR-0021 §Stage 6) — it names a dataset; it never embeds one. No Historical Dataset storage implementation exists yet, and CAP-083B does not build one. To have anything to observe, `DeterministicContinuousImprovementEngine` resolves the reference through a private, constructor-injected `HistoricalDatasetProvider` into an internal `HistoricalDataset` — a plain, unexported structure that is **not** a runtime contract, **not** Historical Truth, **not** Derived Knowledge, and **never** crosses the `continuous_improvement` package boundary. Formally:

> `HistoricalDatasetReference` intentionally carries provenance only. Implementations may resolve the referenced dataset through private collaborators. The resolved dataset is an implementation detail; the public runtime boundary remains `HistoricalDatasetReference → ContinuousImprovementResult`.

This does **not** change `improve`'s signature, `HistoricalDatasetReference`, `ContinuousImprovementResult`, `ImprovementPolicy`, or any frozen contract — the provider is entirely internal to the engine's implementation. The CAP-083B default (`DeterministicHistoricalDatasetProvider`) synthesizes reproducible per-execution records as a **pure function of the reference's own provenance fields** (`dataset_id`, ordinal, `first_execution_id`, `last_execution_id`) via SHA-256 digests — no UUID, no clock, no randomness, no real historical storage — solely to exercise the deterministic engine end to end. A future milestone may replace it with a provider backed by a real Historical Dataset implementation without changing the engine's public contract or any other collaborator.

**Engine responsibilities, in order.** (1) Resolve the `HistoricalDatasetReference` into an internal `HistoricalDataset`. (2) Recurring finding detection: for each enabled RECURRENCE rule, count executions whose resolved facts match the rule's source subsystem; emit an `ImprovementFinding` only when the count meets `ImprovementPolicy.thresholds.minimum_occurrences`. (3) Trend detection: for each enabled TREND rule, gather that source's per-execution metric values (≥ 2 required) and resolve a governed direction from consecutive deltas — monotonic non-decreasing → `IMPROVING`, monotonic non-increasing → `DEGRADING`, all-zero-within-epsilon → `STABLE`, sign-changing → `VOLATILE`. (4) Opportunity generation: for each enabled OPPORTUNITY rule, match against an already-computed finding (same category/source) or an already-computed trend recorded `DEGRADING`/`VOLATILE` (same metric/source); emit the opportunity only when a match exists, referencing it by id. (5) Metrics and (6) summary, each computed exactly once from the final findings/trends/opportunities.

**Deterministic algorithms only (Stage 4).** Recurrence counting, delta-sign trend resolution, and category/direction opportunity matching are the engine's only three mechanisms — no AI, no prediction, no statistical forecasting, no clustering, no embeddings, no semantic similarity. Every outcome is explainable from arithmetic already visible in this ADR.

**Policy governance (Stage 5).** Every threshold the engine reads — `minimum_occurrences`, `history_window` — comes from `ImprovementPolicy.thresholds`; every capability gate comes from `ImprovementPolicy.capability_switches`, resolved per rule via its `policy_reference`. No literal `3`, `25`, or capability boolean is hard-coded in the engine module. `_TREND_EPSILON` is a fixed floating-point comparison tolerance (like an equality guard), never a tunable improvement behaviour, and is documented as such.

**Explainability (Stage 6, reaffirms §D7).** Every finding and trend already carried `contributing_execution_ids`; the engine populates them from the exact executions matched, so `occurrence_count`/`observation_count` always equals that tuple's length (the model's own invariant). Every opportunity references the finding or trend it matched. Nothing is inferred without a named, traceable historical record.

**Recommendation 11 (Stage 7, mandatory — see below).** Every execution of `improve` derives its observations directly from the resolved `HistoricalDataset` — never from a prior `ContinuousImprovementResult`, `ImprovementFinding`, `ImprovementTrend`, or `ImprovementOpportunity`. Neither `improve` nor `HistoricalDatasetProvider.resolve` accepts any Derived Knowledge type as a parameter (enforced by dedicated `typing.get_type_hints`-based containment tests, not just source-grep).

**PlatformContext.** `create_continuous_improvement_service()` now returns `DeterministicContinuousImprovementService` (replacing `DormantContinuousImprovementService`, which CAP-083B removes — mirroring how CAP-082B's `DeterministicRecommendationService` replaced its own dormant predecessor). `create_improvement_rule_catalog()` is added alongside `create_improvement_policy()`. Still unwired: nothing calls `improve()` at runtime, so the golden baseline, Architecture Version, and Platform Version are all unchanged.

**Policy value tuning (not a shape change).** `ImprovementCapabilitySwitches.enable_deterministic_engine` flips `False → True` in the shipped default policy (`ImprovementPolicyVersion` 1.0.0 → 1.1.0) now that the engine exists — a versioned policy *value* change, exactly the kind Recommendation 5 anticipated, never a policy *shape* or engine code change.

**Future ML/LLM engines.** `ImprovementCapabilitySwitches.enable_ml_engine` / `enable_llm_engine` remain reserved off. A future statistical, ML, or LLM Continuous Improvement engine implements the identical `ContinuousImprovementService.improve` contract and may resolve its own `HistoricalDatasetProvider` (or consume a real Historical Dataset implementation directly) without this ADR, `ContinuousImprovementResult`, or `ImprovementPolicy` changing shape.

**Tests.** 84 new deterministic tests (`test_continuous_improvement_rules.py`, `test_continuous_improvement_engine.py`) plus updated boundary tests (`test_continuous_improvement_service.py`, `test_continuous_improvement_policy.py`, `test_continuous_improvement_models.py`) cover every rule family, recurrence/trend/opportunity behaviour, policy-governance of every threshold, explainability, determinism (including the default provider's reproducibility), containment, and dedicated Recommendation 11 verification.

## D10 — ContinuousImprovementResult Runtime Contract (CAP-083B.1 permanent certification)

CAP-083B.1 makes **no runtime behaviour change whatsoever**. It permanently certifies `ContinuousImprovementResult` as the canonical runtime contract of the Continuous Improvement Framework, exactly as CAP-080B.1.1 certified `QualityAssessmentResult`, CAP-081B.1 certified `RequirementEnhancementResult`, and CAP-082B.1 certified `RecommendationResult` — each *before* its subsystem's own runtime activation. This section is the permanent reference for that certification; nothing here changes a field, a computation, or a signature.

**Frozen definition.** `ContinuousImprovementResult` is *the complete deterministic runtime record produced from exactly one execution of* `ContinuousImprovementService.improve()`.

**Ownership (frozen, no overlap).**

| Component | Owns | Owns *not* |
|---|---|---|
| `DeterministicContinuousImprovementEngine` | recurrence detection, trend detection, opportunity generation, metrics, summary | orchestration, runtime state, projection, packaging |
| `HistoricalDatasetProvider` (private) | resolving a reference into an internal `HistoricalDataset` | anything downstream of that resolution; never a runtime contract |
| `ContinuousImprovementService` | orchestration only | any computation the engine performs |
| `ContinuousImprovementResult` | runtime state only | orchestration, projection, packaging |
| Serializer (future) | projection only | generation, orchestration, packaging |
| Execution Package (future) | packaging only | generation, orchestration, projection logic |
| CLI (future) | orchestration (of the pipeline call) only | generation, projection, packaging |
| `PlatformContext` | composition only | generation, orchestration, projection, packaging |

**Explainability (frozen).** Every finding, trend, and opportunity must be reconstructable solely from `ContinuousImprovementResult`. No upstream subsystem needs to be inspected. No engine rerun is required. No provider inspection is required. No policy inspection is required. No runtime inspection is required. `ContinuousImprovementResult` is the complete explanation.

**Runtime boundary (frozen).** Runtime ends at `ContinuousImprovementResult`. Everything after it is projection. Future serializers, reports, dashboards, Markdown, HTML, and the Execution Package must consume `ContinuousImprovementResult` only — never the engine, never the provider, never the service, never `PlatformContext`.

```
HistoricalDatasetReference
    → (private HistoricalDatasetProvider → engine-internal HistoricalDataset)
    → DeterministicContinuousImprovementEngine
    → ContinuousImprovementResult
    → Serializer (future)
    → Execution Package (future)
    → Manifest (future)
    → Release
```

No reverse dependency: nothing later in this chain is ever imported by anything earlier in it.

**Historical Dataset Resolution Principle (frozen permanently, Recommendation 10).** `HistoricalDatasetReference` intentionally carries provenance only. Implementations may resolve the referenced dataset through private collaborators. The resolved dataset is an implementation detail — never a runtime contract, never Historical Truth, never Derived Knowledge, never exported past the `continuous_improvement` package boundary. The public runtime boundary remains `HistoricalDatasetReference → ContinuousImprovementResult`. Future providers — including one backed by a real Historical Dataset implementation — may replace `DeterministicHistoricalDatasetProvider` freely; the `improve` signature never changes as a result.

**Derived Knowledge principle (frozen permanently, Recommendation 11, ADR-0021 §Recommendation 11).** `ContinuousImprovementResult` is Derived Knowledge. It never becomes Historical Truth. Historical Truth never becomes Runtime Truth. Every execution of `improve` derives its observations directly from the Historical Dataset the resolved reference names — never from a prior `ContinuousImprovementResult` or any prior `ImprovementFinding` / `ImprovementTrend` / `ImprovementOpportunity`. Derived Knowledge must never recursively consume Derived Knowledge.

**Version-axis independence (frozen; full detail in `continuous_improvement/identity/continuous_improvement_identity.py`'s module docstring).** Eight distinct version types exist — `ContinuousImprovementFrameworkVersion`, `ImprovementPolicyVersion`, `ImprovementRuleVersion`, `ImprovementRuleCatalogVersion`, `ImprovementTrendVersion` (reserved), `ImprovementAssessmentVersion` (reserved), `ImprovementEngineVersion` (reserved), `ContinuousImprovementResultVersion` (the only axis stamped onto a model today) — each evolving independently. `ImprovementFinding`, `ImprovementOpportunity`, and `ImprovementSummary`/`ImprovementMetrics` carry no dedicated schema-version type of their own, mirroring every sibling subsystem's atomic finding/issue model; no new version type is invented by this certification.

**Additional constitutional principles (frozen, CAP-083B.1), cross-referenced to the Recommendations already governing this ADR:**

1. `ContinuousImprovementResult` is the sole runtime authority for Derived Knowledge produced by Continuous Improvement (Recommendation 3; frozen definition, above).
2. `HistoricalDatasetProvider` is an implementation detail, not part of the platform architecture (Recommendation 10).
3. `HistoricalDatasetReference` remains the only public input contract, regardless of future storage technologies (Recommendation 2, Recommendation 10).
4. Historical dataset resolution is replaceable, but the runtime boundary is not (Recommendation 10; Runtime boundary, above).
5. Runtime contracts evolve independently of engines, providers, serializers, execution packaging, and historical storage (Version-axis independence, above; Recommendation 5).
6. Continuous Improvement remains a pure Layer 2 consumer of Historical Truth and must never consume Layer 1 runtime contracts directly or recursively consume previous Derived Knowledge (Recommendation 1, Recommendation 9, Recommendation 11).
7. Future ML, statistical, or LLM-based Continuous Improvement engines must implement the unchanged `improve(HistoricalDatasetReference) -> ContinuousImprovementResult` contract, ensuring long-term engine replaceability (Recommendation 5).

**Certification.** `ContinuousImprovementResult` is hereby constitutionally certified as the permanent Layer 2 runtime contract for Continuous Improvement, completing the same architectural lifecycle (Architecture Freeze → Deterministic Implementation → Runtime Contract Freeze) previously established for Quality Governance (CAP-080B.1.1), Requirement Enhancement (CAP-081B.1), and Recommendation (CAP-082B.1). No field, validator, or signature changed to produce this certification. Runtime integration (CAP-083C) has now activated this framework in the live pipeline — see §D11.

## D11 — Runtime Integration (CAP-083C)

CAP-083C activates the already-complete Continuous Improvement Framework in the live Requirement Intelligence runtime — Layer 2's first capability going live. It does not redesign Continuous Improvement, change any frozen contract, alter the policy shape, modify the deterministic engine, or introduce new observation logic — it wires the existing implementation into the live pipeline and activates the Execution Package projections, exactly as CAP-082C did for Recommendation (ADR-0019 §D10).

**Activation and execution order (frozen).** Continuous Improvement executes exactly once, immediately after Recommendation, at the permanently frozen end of the pipeline:

```
Engineering Context → Analysis → Requirement Enhancement → Grounding
    → Validation → CP1 → Quality Governance → Recommendation → Historical Dataset
    → Continuous Improvement → Execution Package
```

Never before Recommendation, never in parallel, never conditionally reordered.

**HistoricalDatasetReference minting (frozen, new to this milestone).** Unlike Recommendation, which consumes five completed Layer 1 peer results, Continuous Improvement consumes exactly one `HistoricalDatasetReference` — never a Layer 1 runtime contract directly, and never any of the peer results this same pipeline run just produced (Recommendation 1). No real, multi-execution Historical Dataset implementation exists yet (ADR-0021 §Stage 6, reserved — building it remains future work, not part of this milestone). To have anything to reference, the CLI mints the minimal, deterministic reference a Historical Dataset of exactly this one execution would produce: `first_execution_id` and `last_execution_id` both name this run's own `AnalysisResult.execution_id`, `execution_count` and `history_window` are both `1`, and `generated_at` is this run's own `completed_at` — never the wall clock, so the reference (and everything Continuous Improvement derives from it) stays reproducible. This performs no business logic and computes nothing beyond restating identity fields the `AnalysisResult` already carries — orchestration glue, not observation. Because a single-execution reference can satisfy neither the governed recurring-finding floor (`ImprovementPolicy.thresholds.minimum_occurrences`) nor the trend floor (at least two data points), the golden dataset deterministically observes an empty — but genuine — `ContinuousImprovementResult`, exactly what the engine's own governed thresholds require.

**CLI (frozen).** The CLI's `run_continuous_improvement_phase` obtains `ContinuousImprovementService` exclusively from `PlatformContext` and calls `improve(historical_dataset)` — identical failure semantics to Grounding/Requirement Enhancement/Quality Governance/Recommendation: a continuous improvement failure is surfaced but never fatal to the analysis run, and it runs whenever this is a live run (a completed `AnalysisResult` exists, so a single-execution reference can be minted). The CLI orchestrates only — no observation, detection, generation, policy, or rule-catalogue logic exists in the CLI.

**Execution Package (frozen, mirrors ADR-0018 §D8 / ADR-0019 §D10).** `ExecutionData.continuous_improvement_result` is an additive-only field (no existing field changed). `ContinuousImprovementSerializer` (`continuous_improvement/serialization/`) renders `continuous_improvement_result.json` (canonical `model_dump`), `continuous_improvement_report.md`, and `continuous_improvement_metrics.md` — a pure projection computing nothing; every rendered value already exists inside `ContinuousImprovementResult`. `ExecutionWriter` appends these three artifacts only when `continuous_improvement_result` is present — no special case, the same conditional-append mechanism as every peer subsystem.

**Manifest purity (frozen, mirrors ADR-0017 §D31, ADR-0019 §D10).** The manifest gains exactly three additive keys — `continuousImprovementExecuted`, `continuousImprovementReport`, `continuousImprovementMetrics` — a flag and two artifact filenames. No finding, trend, opportunity, summary, or metric value is ever copied into the manifest; that runtime state lives exclusively in `ContinuousImprovementResult` / `continuous_improvement_result.json`. When continuous improvement did not run, the manifest is byte-identical to before — no key is added, no schema change (`manifestSchemaVersion` stays `1.0.0`).

**Golden integration (frozen).** `_run_golden_pipeline()` now improves immediately after Recommendation; `PipelineResult` carries `continuous_improvement_result`. The golden dataset re-baselines from `GOLDEN_DATASET_VERSION` `1.4.0` to `1.5.0` — the nine source artifacts and the golden response are unchanged; only the generated artifact set grows by the three continuous improvement files, exactly as `1.3.0` and `1.4.0` did for Requirement Enhancement and Recommendation respectively. The Architecture Version remains `1.2.0`; the Platform Version is unchanged.

**One-way dependency chain (frozen, mirrors §D8/§D10).**

```
Continuous Improvement Runtime (engine + service)
    → ContinuousImprovementResult
    → Continuous Improvement Serializer
    → Execution Package
    → Manifest
    → Release
```

Nothing later in this chain imports or invokes anything earlier except through the frozen `ContinuousImprovementResult` contract. The serializer imports no engine, service, policy, rule catalogue, or `HistoricalDatasetProvider` implementation. The writer and manifest builder import only the serializer, never the engine, service, or provider. The CLI imports only `PlatformContext.create_continuous_improvement_service()`, never `DeterministicContinuousImprovementEngine`, `ImprovementRuleCatalog`, or any `HistoricalDatasetProvider` directly.

**Ownership (frozen, no overlap; reaffirms §D10's table with the CLI and Execution Package now live).** Engine detects/observes/generates/computes metrics/summarizes. Service orchestrates only. `ContinuousImprovementResult` owns runtime state only. The serializer projects only. The Execution Package packages only. The CLI orchestrates (the pipeline call) only. `PlatformContext` composes only.

**Historical Dataset boundary preserved (Recommendation 12, new).** Continuous Improvement never caches, duplicates, or persists historical records outside the Historical Dataset it references. The single-execution reference this milestone mints is provenance only — it names an execution, it never embeds or stores one — and CAP-083C introduces no historical storage of its own.

**Derived Knowledge never rewritten (Recommendation 13, new).** `ContinuousImprovementResult` is never written back into the Historical Dataset, and no future Continuous Improvement run may consume a prior `ContinuousImprovementResult` as an input. `improve`'s only parameter remains `HistoricalDatasetReference` — unchanged by this milestone.

**Execution Package remains projection-only (Recommendation 14, new).** Every continuous improvement execution artifact is reproducible solely from `ContinuousImprovementResult`. No artifact generation invokes the engine, the provider, the service, or `PlatformContext` — enforced by the same containment tests that guard every peer subsystem's serializer and Execution Package boundary.

**Layer separation preserved (Recommendation 15, new).** Continuous Improvement remains a Layer 2 capability. Runtime integration introduces no direct dependency on any Layer 1 implementation class — the CLI, the serializer, and the Execution Package all reach Continuous Improvement exclusively through `PlatformContext.create_continuous_improvement_service()` and `ContinuousImprovementResult`.

**Historical Dataset implementation remains replaceable (Recommendation 16, new).** The runtime pipeline consumes only `HistoricalDatasetReference`. A future Historical Dataset implementation — and a future `HistoricalDatasetProvider` backed by it — may replace the single-execution reference this milestone mints without requiring any change to the CLI, the serializer, the Execution Package, or `ContinuousImprovementResult`.

---

### Recommendation 1 — Continuous Improvement Framework is a consumer of Historical Truth only

It never owns Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, or any Layer 1 responsibility. It never imports a Layer 1 subsystem at all — a stricter boundary than any Layer 1 subsystem imposes on its own peers, because Continuous Improvement's only upstream concept is the Historical Dataset (ADR-0021 §Stage 6), referenced by `HistoricalDatasetReference`, never a Layer 1 result embedded directly.

### Recommendation 2 — Never duplicate runtime models

`ImprovementFinding` / `ImprovementTrend` / `ImprovementOpportunity` objects must contain execution-id or finding/trend-id references — references to the executions or prior observations that grounded them — never copies of that content. Enforced structurally: the reference fields carry only ids; they have no field capable of holding copied Runtime Truth content.

### Recommendation 3 — ContinuousImprovementResult is the single runtime authority

The Execution Package, the CLI, reports, and future dashboards must consume only `ContinuousImprovementResult`. No other object in this subsystem is a runtime contract.

### Recommendation 4 — Recurring-finding, trend, and opportunity generation is deferred

CAP-083A freezes architecture only. No finding is derived, no trend is observed, no opportunity is generated, and no historical dataset access exists. `DormantContinuousImprovementService` raises `NotImplementedError` on every call.

### Recommendation 5 — Future engines remain replaceable

Deterministic, statistical, ML, LLM, and hybrid engines all implement the identical `ContinuousImprovementService.improve` contract. `ImprovementCapabilitySwitches` reserves `enable_deterministic_engine`, `enable_ml_engine`, and `enable_llm_engine` as independent, governed toggles for this replaceability, mirroring `RecommendationCapabilitySwitches`'s reserved-capability pattern (ADR-0019).

### Recommendation 6 — Strict ownership direction

```
Historical Dataset → Policies → Engine → Runtime Contract → Serializer → Execution Package
```

Never reversed. A Historical Dataset is referenced by an engine; a policy is read by an engine; an engine produces a runtime contract; a serializer projects a runtime contract; the Execution Package transports a serializer's output. No stage may reach backward into an earlier one.

### Recommendation 7 — Explainability first

Every future finding, trend, and opportunity must ultimately be explainable from `ImprovementFinding` / `ImprovementTrend` / `ImprovementOpportunity` / `ContinuousImprovementResult` alone, traceable through `HistoricalDatasetReference` down to Runtime Truth and execution inputs. No hidden learning state. Enforced today by the model validators' "at least one reference" / count-consistency invariants (§D7) — the invariant exists before any engine could violate it.

### Recommendation 8 — Runtime before reporting

`ContinuousImprovementResult` is frozen before any serializer, execution package integration, dashboard, or reporting work (§D8).

### Recommendation 9 — Preserve the Truth Hierarchy (mandatory, ADR-0021 §Stage 3/Recommendation 11)

This capability explicitly declares its Truth Hierarchy level, as ADR-0021 Recommendation 11 requires of every future Layer 2–7 capability:

- **Consumes:** Historical Truth (via `HistoricalDatasetReference`).
- **Produces:** Derived Knowledge (`ContinuousImprovementResult`).

It must never blur those constitutional layers — `ContinuousImprovementResult` is never written back as Historical Truth, and `HistoricalDatasetReference` never embeds Runtime Truth directly.

### Recommendation 10 — Historical Dataset Resolution Principle (mandatory, CAP-083B)

`HistoricalDatasetReference` intentionally carries provenance only. Implementations may resolve the referenced dataset through private collaborators. The resolved dataset is an implementation detail; the public runtime boundary remains `HistoricalDatasetReference → ContinuousImprovementResult`.

Concretely: an engine may resolve a `HistoricalDatasetReference` through a private, constructor-injected `HistoricalDatasetProvider` into an internal `HistoricalDataset` object, solely to have observable data to analyze. That resolved object is never a runtime contract, never Historical Truth, never Derived Knowledge, and must never cross the `continuous_improvement` package boundary — it is not returned by any public method, not accepted as a parameter by `improve`, and not serialized. A future engine may resolve the same reference through a different provider — including one backed by a real Historical Dataset implementation — without this ADR, `HistoricalDatasetReference`, `ContinuousImprovementResult`, or the `improve` signature changing.

### Recommendation 11 — Derived Knowledge must never recursively consume Derived Knowledge (mandatory, ADR-0021 §Recommendation 11, frozen permanently)

Continuous Improvement must consume **only** Historical Truth. It must **never** consume `ContinuousImprovementResult`, nor any previous `ImprovementFinding`, `ImprovementTrend`, or `ImprovementOpportunity`. Every execution must derive its observations directly from the Historical Dataset — never from previous observations.

This is not merely a convention: `improve(historical_dataset: HistoricalDatasetReference)` and `HistoricalDatasetProvider.resolve(historical_dataset: HistoricalDatasetReference)` are the only two entry points capable of feeding data into an engine, and neither accepts any Derived Knowledge type as a parameter — verified by dedicated introspection tests (`typing.get_type_hints`, `inspect.getmembers`), not source-text scanning alone. Every future Layer 2–7 engine built under ADR-0020 must satisfy this same recommendation before it may consume anything this framework — or any other Derived Knowledge producer — emits.

### Recommendation 12 — Historical Dataset remains the sole Historical Truth (mandatory, CAP-083C, frozen permanently)

Continuous Improvement must never cache, duplicate, or persist historical records outside the Historical Dataset. It consumes Historical Truth but never owns it. The single-execution `HistoricalDatasetReference` the CAP-083C runtime mints is provenance only — it names an execution, it never embeds or stores one — and runtime integration introduces no historical storage of its own.

### Recommendation 13 — Derived Knowledge is never rewritten into Historical Truth (mandatory, CAP-083C, frozen permanently)

`ContinuousImprovementResult` must never be written back into the Historical Dataset or become an input to future Continuous Improvement runs. This reaffirms Recommendation 11 at the runtime boundary: `improve`'s only parameter remains `HistoricalDatasetReference`, unchanged by runtime activation.

### Recommendation 14 — Execution Package remains projection-only (mandatory, CAP-083C, frozen permanently)

Execution artifacts are reproducible solely from `ContinuousImprovementResult`. No artifact generation may invoke the engine, the provider, the service, or `PlatformContext` — enforced by dedicated containment tests over `ContinuousImprovementSerializer`, `ExecutionWriter`, and `ManifestBuilder` (§D11).

### Recommendation 15 — Runtime integration must not weaken Layer separation (mandatory, CAP-083C, frozen permanently)

Continuous Improvement remains a Layer 2 capability. Runtime integration must not introduce direct dependencies on any Layer 1 implementation class. The CLI, the serializer, and the Execution Package all reach Continuous Improvement exclusively through `PlatformContext.create_continuous_improvement_service()` and `ContinuousImprovementResult` — never `DeterministicContinuousImprovementEngine`, `ImprovementRuleCatalog`, or any Layer 1 subsystem directly.

### Recommendation 16 — Historical Dataset implementation remains replaceable (mandatory, CAP-083C, frozen permanently)

The runtime pipeline consumes only `HistoricalDatasetReference`. Future storage implementations may evolve independently without requiring changes to the CLI, the serializer, the Execution Package, or `ContinuousImprovementResult` — including replacing the single-execution reference CAP-083C mints with one backed by a real, multi-execution Historical Dataset.

---

## Trade-offs

- **A new subsystem introduces the platform's first Layer 2 capability with no Layer 2 precedent to follow.** Accepted: ADR-0020/ADR-0021 exist precisely to provide that precedent in advance, and this ADR follows them exactly (Stage 0).
- **`HistoricalDatasetReference` is provenance for a dataset that does not exist yet.** Accepted: freezing the reference shape before the Historical Dataset is built lets the first Historical Dataset implementation be designed to satisfy an already-frozen consumer contract, rather than the reverse (mirrors ADR-0018 §D8's "freeze before the serializer exists" discipline, applied here to the dataset instead of the projection).
- **Governed defaults are calibrated conservatively, not empirically.** The CAP-083A default policy bounds (`minimum_occurrences = 3`, `history_window = 25`) are governed data reflecting a deliberately conservative first pass, not yet tuned against a real historical corpus. Accepted: tuning is a versioned policy change under a future golden re-baseline, never an engine code change (Recommendation 5).

## Future evolution

- **CAP-083B — Deterministic Continuous Improvement Engine (done).** The first real engine behind the frozen `improve` signature: deterministic derivation of findings/trends/opportunities from a resolved Historical Dataset, strictly by reference (Recommendation 2), never independent analysis. A private `HistoricalDatasetProvider` (Recommendation 10) resolves `HistoricalDatasetReference` into an engine-internal dataset since no real Historical Dataset implementation exists yet.
- **CAP-083B.1 — ContinuousImprovementResult Runtime Contract Freeze (done).** Permanently certifies `ContinuousImprovementResult` as the canonical Layer 2 runtime contract (§D10) — no field, validator, or signature change; documentation and architecture tests only, mirroring CAP-082B.1.
- **Historical Dataset implementation** (reserved, ADR-0021 §Stage 6) — a future milestone (inside or alongside CAP-083) that actually builds the ordering/lineage/retention/indexing/search Continuous Improvement's `HistoricalDatasetReference` currently only names, and that a future `HistoricalDatasetProvider` may resolve against instead of the single-execution reference CAP-083C mints.
- **CAP-083C — Runtime Integration (done).** Wires `improve` into the live pipeline immediately after Recommendation, adds the `ContinuousImprovementSerializer` Execution Package projection, and re-baselines the golden dataset `1.4.0` → `1.5.0`, mirroring CAP-082C's activation of Recommendation (ADR-0019 §D10). See §D11.
- **CAP-084 (Knowledge Graph), CAP-085 (Organizational Memory), CAP-086 (Learning Framework)** — the remaining reserved Layer 2 capabilities (ADR-0020), each to declare its own Truth Hierarchy level per ADR-0021 Recommendation 11.
- Promotion of the shared version/identity value-objects to `shared/` (the debt ADR-0015 §C, ADR-0016, ADR-0017, ADR-0018 §D5, and ADR-0019 §D5 already name).

## Ownership, runtime position, governance

- **Owns:** recurring-finding detection, trend detection, opportunity generation, Continuous Improvement metadata.
- **Does not own:** Engineering Context Orchestration, Analysis, Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, the Execution Package, or the Historical Dataset itself (ADR-0021 §Stage 6 names that owner, not this ADR).
- **Runtime position (live — CAP-083C):** `HistoricalDatasetReference` → (private `HistoricalDatasetProvider` → engine-internal `HistoricalDataset`) → `DeterministicContinuousImprovementEngine` → `ContinuousImprovementResult` → `ContinuousImprovementSerializer` → Execution Package → Manifest → Release. Architecture frozen; the deterministic engine exists and is fully tested; `ContinuousImprovementResult` is constitutionally certified as the permanent runtime contract (§D10); the CLI wires `improve` into the live pipeline immediately after Recommendation, over a single-execution `HistoricalDatasetReference` (§D11).
- **Governance:** registered as CAP-083 for the Requirement Intelligence Platform's Layer 2 — the first capability built under ADR-0020/ADR-0021, and the first to go live. This ADR is **Accepted**; CAP-083B extends it with the first deterministic engine under an unchanged contract; CAP-083B.1 permanently certifies that contract; CAP-083C activates it in the live runtime.
