# Continuous Improvement Framework — Design Proposal

- **Status:** Accepted (CAP-083A froze the architecture; CAP-083B implemented the first deterministic engine behind it, unchanged; CAP-083B.1 permanently certified the runtime contract, no behaviour change; CAP-083C activated the runtime and Execution Package in the live pipeline)
- **Capability:** CAP-083 — Continuous Improvement Framework
- **Milestones covered:** CAP-083A (Architecture & Governance Freeze), CAP-083B (Deterministic Continuous Improvement Engine — see §8a), CAP-083B.1 (ContinuousImprovementResult Runtime Contract Freeze — see §8b), CAP-083C (Runtime Integration & Execution Package Activation — see §8c)
- **Governed by:** ADR-0022
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution).

---

## 1. Problem

ADR-0020 named Continuous Learning as Layer 2 and reserved Continuous Improvement (CAP-083) as its first capability. ADR-0021 froze the Truth Hierarchy every Layer 2 capability must obey. No Layer 2 capability exists yet.

**Nothing today answers a question about many executions.** Every Layer 1 capability judges one execution; none of them notices that the same validation failure keeps recurring, that grounding quality is trending down for a module, or that the same documentation gap keeps getting flagged across dozens of runs. That capability exists nowhere in the repository today (confirmed by the Stage 0 assessment of CAP-083A, ADR-0022). Left unbuilt, the first capability to need it would have to invent an answer under deadline pressure — and every capability built after it would inherit that ad hoc answer, exactly the risk ADR-0021 §Stage 2 names.

## 2. Scope of CAP-083A

CAP-083A is a **pure architecture milestone**. It freezes:

- the subsystem and its ownership boundary
- the canonical runtime contract, `ContinuousImprovementResult`
- the canonical models (`ImprovementFinding`, `ImprovementTrend`, `ImprovementOpportunity`, `ImprovementSummary`, `ImprovementMetrics`, `HistoricalDatasetReference`)
- typed identities and independent version axes
- the governed `ImprovementPolicy` and its builder
- the abstract, dormant `ContinuousImprovementService` contract
- `PlatformContext` registration

It does **not** implement recurring-finding detection, trend detection, opportunity generation, historical dataset storage, runtime wiring, or execution artifacts. No pipeline change. No Execution Package change. No CLI change. No serializer. No golden re-baseline. The Architecture Version remains **1.2.0**.

## 3. Stage 0 — Repository assessment (no redesign)

| Surface | What it is | Why it is not Continuous Improvement |
|---|---|---|
| Layer 1 runtime contracts (`RequirementEnhancementResult` … `RecommendationResult`) | Immutable Runtime Truth, scoped to one execution | ADR-0021 §Stage 3: Runtime Truth is never inferred and never spans executions. |
| `docs/architecture/execution-package.md` §3 "Execution Lineage" | The within-one-execution data flow | Describes how one execution's artifacts derive from one another, not how executions relate to each other over time. |
| ADR-0020 Layer 2 reservation (CAP-083/084/085/086) | Names, not implementations | No code exists for any of the four reserved Layer 2 capabilities. |

No dedicated historical-dataset model, identity, policy, or service exists anywhere in the repository prior to this milestone. No architectural weakness found.

## 4. Subsystem & ownership

`requirement_intelligence/continuous_improvement/` owns only:

- recurring-finding detection
- trend detection
- opportunity generation
- Continuous Improvement metadata

It never owns Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, the Execution Package, or the Historical Dataset itself (ADR-0021 §Stage 6 names that owner). It is a **consumer only** of Historical Truth — `HistoricalDatasetReference`, never a Layer 1 result directly, and never an Execution Package artifact (ADR-0021 §Stage 7/8).

## 5. Canonical models

| Model | Owns |
|---|---|
| `ImprovementFinding` | One recurring issue across many executions: category, source subsystem, severity, occurrence count, and the contributing execution ids (never copies) that ground it. |
| `ImprovementTrend` | One observed direction (improving/degrading/stable/volatile) for a governed metric, with the contributing execution ids its data points were drawn from. Observation only — never a prediction. |
| `ImprovementOpportunity` | One deterministic opportunity — "what should receive attention" — referencing the findings and/or trends it was derived from, by id only. Never "the optimal plan" (that is Layer 5, Optimization). |
| `HistoricalDatasetReference` | Provenance naming one Historical Dataset — id, version, execution range, governed history window, generation timestamp. Never the dataset's content. |
| `ImprovementSummary` | The headline: counts and a deterministic one-line description. Renders no optimization plan — Continuous Improvement is observation only. |
| `ImprovementMetrics` | Deterministic numeric roll-ups (finding density, trend stability ratio, opportunity rate) — recorded values, never model-internal calculations. |
| `ContinuousImprovementResult` | The runtime contract: every finding, every trend, every opportunity, the summary, the metrics, the governing policy identity/version, and the consumed `HistoricalDatasetReference`. |

Every model is `frozen=True`, tuple-backed collections, `camelCase` serialisation (`alias_generator=to_camel`), and computes nothing — validators enforce cross-referential integrity and the explainability invariant only (ADR-0022 §D4/§D7).

## 6. Explainability invariant

`ImprovementFinding` and `ImprovementTrend` each carry `contributing_execution_ids`; their `occurrence_count` / `observation_count` must equal that tuple's length. `ImprovementOpportunity` **cannot be constructed** with zero `source_finding_ids` and zero `source_trend_ids`. Every recurrence and opportunity must be traceable to at least one upstream finding, trend, or execution from the moment the model exists — not retrofitted once an engine starts producing evidence-free conclusions (ADR-0021 §Stage 8's historical explainability chain, `Historical Dataset → Runtime Contracts → Execution Inputs`, enforced as a model invariant).

## 7. Governed policy

`ImprovementPolicy` is immutable, declarative, governed data — no executable logic:

- `ImprovementCapabilitySwitches` — enable/disable trend detection, recurring-finding detection, opportunity generation, and the future deterministic/ML/LLM engine families (Recommendation 5 of ADR-0022).
- `ImprovementThresholds` — `minimum_occurrences` (recurrence floor) and `history_window` (maximum executions a dataset reference may span), bounded so the floor never exceeds the window.

`ImprovementPolicyBuilder` / `default_improvement_policy()` assemble the CAP-083A default at `ImprovementPolicyVersion` 1.0.0 (`minimum_occurrences=3`, `history_window=25`). Tuning any threshold or switch is a versioned policy change, never an engine change (Recommendation 5).

## 8. Runtime boundary (frozen, dormant)

`ContinuousImprovementService` exposes exactly one method:

```python
def improve(
    self,
    historical_dataset: HistoricalDatasetReference,
) -> ContinuousImprovementResult:
    ...
```

It depends only on `HistoricalDatasetReference` it consumes — never an *implementation* class, and never a Layer 1 subsystem at all (a stricter boundary than any Layer 1 subsystem imposes on its peers — Recommendation 1). Abstract at CAP-083A; `DormantContinuousImprovementService` raises `NotImplementedError`. A later CAP-083 milestone implements the method behind this unchanged signature, exactly as CAP-082B implemented `RecommendationService.recommend` behind the ADR-0019 boundary.

## 8a. CAP-083B — Deterministic Continuous Improvement Engine

CAP-083B is that later milestone: it implements `improve` behind the unchanged signature above, exactly as ADR-0022 §D9 describes.

**Rule catalogue.** `continuous_improvement/rules/` introduces `ImprovementRule` (metadata only — id, `ImprovementRuleFamily`, source subsystem, the finding/opportunity category or metric it names, a severity/guidance hint, an enable switch, an `ImprovementPolicyToggle` reference), `ImprovementRuleCatalog` (ordering/lookup/family/source projections only), and `ImprovementRuleBuilder`/`default_improvement_rule_catalog()` shipping 16 governed rules: 5 RECURRENCE (one per `ImprovementFindingCategory`, including the additive `RECURRING_ENHANCEMENT_ISSUE`), 6 TREND (one per `ImprovementSourceLayer`), 5 OPPORTUNITY (one per `ImprovementOpportunityCategory`).

**Historical Dataset Resolution Principle (Recommendation 10).** `HistoricalDatasetReference` still carries provenance only — no Historical Dataset implementation exists. `DeterministicContinuousImprovementEngine` resolves it through a private, constructor-injected `HistoricalDatasetProvider` into an engine-internal `HistoricalDataset`: not a runtime contract, not Historical Truth, not Derived Knowledge, never exported past the package boundary. The CAP-083B default, `DeterministicHistoricalDatasetProvider`, synthesizes reproducible per-execution records as a pure function of the reference's own fields (SHA-256 digests — no UUID, no clock). A future provider may resolve against a real Historical Dataset implementation without changing the engine's public contract.

**Deterministic algorithms (Recommendation 7's engine, Stage 4).** Recurring findings: count matching executions per enabled RECURRENCE rule, emit only once `ImprovementPolicy.thresholds.minimum_occurrences` is met. Trends: resolve `IMPROVING` / `DEGRADING` / `STABLE` / `VOLATILE` from the sign pattern of consecutive metric deltas (epsilon-tolerant equality). Opportunities: match an enabled OPPORTUNITY rule's category/source against an already-computed finding, or its metric/source against an already-computed `DEGRADING`/`VOLATILE` trend, referencing the match. No AI, no prediction, no statistics beyond arithmetic comparison.

**Policy governance.** Every threshold (`minimum_occurrences`, `history_window`) and every capability gate (`enable_recurring_finding_detection`, `enable_trend_detection`, `enable_opportunity_generation`, and the master `enable_deterministic_engine`) is read from `ImprovementPolicy` via each rule's `policy_reference` — never hard-coded. `ImprovementPolicyVersion` advances 1.0.0 → 1.1.0 for this value change (Recommendation 5); the policy's *shape* is unchanged.

**Explainability.** Every finding/trend's `contributing_execution_ids` is populated from the exact matched executions; every opportunity references the finding or trend it matched — reaffirming ADR-0022 §D7's invariant, now exercised by a real engine.

**Recommendation 11.** Neither `improve` nor `HistoricalDatasetProvider.resolve` accepts any Derived Knowledge type as a parameter — verified by `typing.get_type_hints`/`inspect.getmembers` introspection tests, not just source scanning. Every execution observes the Historical Dataset directly; never a prior `ContinuousImprovementResult` or observation.

**Still not activated.** `PlatformContext.create_continuous_improvement_service()` now returns `DeterministicContinuousImprovementService`, replacing `DormantContinuousImprovementService`. Nothing calls `improve` at runtime — no CLI phase, no Execution Package field. The golden baseline, Architecture Version, and Platform Version are unchanged.

## 8b. Runtime Contract Freeze (CAP-083B.1)

CAP-083B.1 permanently certifies `ContinuousImprovementResult` as the runtime contract
of the Continuous Improvement Framework, before the subsystem is activated in the live
pipeline — mirroring CAP-080B.1.1 (`QualityAssessmentResult`), CAP-081B.1
(`RequirementEnhancementResult`), and CAP-082B.1 (`RecommendationResult`). **No
runtime behaviour changes.** No field, no computation, no signature changed; only
documentation and architecture-only tests were added. Full detail lives in ADR-0022
§D10; summarised here:

**Frozen definition.** `ContinuousImprovementResult` is *the complete deterministic
runtime record produced from exactly one execution of*
`ContinuousImprovementService.improve()`.

- **IS:** the complete runtime output; the canonical runtime contract; independently
  versioned; deterministic; immutable; self-contained; explainable; serializer
  independent; execution-package independent; historical-storage independent;
  engine independent.
- **IS NOT:** a report; Markdown; an execution artifact; a manifest; a CLI object;
  a renderer; a serializer; a transport object; a projection; a
  `HistoricalDatasetProvider`; a Historical Dataset.

**Ownership (no overlap).** `DeterministicContinuousImprovementEngine` owns
recurrence/trend/opportunity detection, metrics, and summary. The private
`HistoricalDatasetProvider` owns resolving a reference into an internal
`HistoricalDataset` only — never a runtime contract. `ContinuousImprovementService`
owns orchestration only. `ContinuousImprovementResult` owns runtime state only. A
future serializer owns projection only. A future Execution Package owns packaging
only. `PlatformContext` owns composition only.

**Explainability.** Every finding, trend, and opportunity is reconstructable solely
from `ContinuousImprovementResult` — no upstream subsystem, no engine rerun, no
provider inspection, no policy inspection, no runtime inspection required.

**Runtime boundary.** Runtime ends at `ContinuousImprovementResult`. Everything
after it — serializers, reports, dashboards, Markdown, the Execution Package — is
projection, and must consume `ContinuousImprovementResult` only, never the engine,
the provider, the service, or `PlatformContext`:

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

**Historical Dataset Resolution Principle (frozen permanently).**
`HistoricalDatasetReference` intentionally carries provenance only. Implementations
may resolve the referenced dataset through private collaborators. The resolved
dataset is an implementation detail; the public runtime boundary remains
`HistoricalDatasetReference → ContinuousImprovementResult`.

**Derived Knowledge principle (frozen permanently, Recommendation 11).**
`ContinuousImprovementResult` is Derived Knowledge. It never becomes Historical
Truth. Historical Truth never becomes Runtime Truth. Continuous Improvement must
never recursively consume its own prior Derived Knowledge.

**Version-axis independence.** Eight distinct version types exist —
`ContinuousImprovementFrameworkVersion`, `ImprovementPolicyVersion`,
`ImprovementRuleVersion`, `ImprovementRuleCatalogVersion`, `ImprovementTrendVersion`
(reserved), `ImprovementAssessmentVersion` (reserved), `ImprovementEngineVersion`
(reserved), `ContinuousImprovementResultVersion` (the only axis stamped onto a model
today) — each evolving independently. No new version type was invented for this
certification.

**Future engine replaceability.** A future statistical, ML, or LLM Continuous
Improvement engine implements the identical `improve(HistoricalDatasetReference) ->
ContinuousImprovementResult` contract and may resolve its own
`HistoricalDatasetProvider` (or consume a real Historical Dataset implementation
directly) without this contract changing shape.

**Certification.** `ContinuousImprovementResult` is constitutionally certified as
the permanent Layer 2 runtime contract for Continuous Improvement — completing
Architecture Freeze (CAP-083A) → Deterministic Implementation (CAP-083B) → Runtime
Contract Freeze (CAP-083B.1). Runtime Integration (CAP-083C, reserved) is the only
remaining step before this framework is live.

## 8c. Continuous Improvement Runtime, Serializer, Execution Package, Golden Integration (CAP-083C)

CAP-083C activates the already-complete Continuous Improvement Framework in the live
Requirement Intelligence runtime — Layer 2's first capability going live. No redesign:
no frozen contract, policy shape, or engine behaviour changed. Full detail lives in
ADR-0022 §D11; summarised here:

**Continuous Improvement Runtime.** Continuous Improvement executes exactly once,
immediately after Recommendation, at the permanently frozen end of the pipeline:

```
... Quality Governance → Recommendation → Historical Dataset
    → Continuous Improvement → Execution Package
```

Unlike Recommendation (five consumed peer results), Continuous Improvement consumes
exactly one `HistoricalDatasetReference` — never a Layer 1 peer result, including any
of the results this same pipeline run just produced (Recommendation 1). No real,
multi-execution Historical Dataset implementation exists yet (ADR-0021 §Stage 6,
reserved), so the CLI mints the minimal, deterministic reference the Historical
Dataset of exactly this one execution would produce (`execution_count` = `history_window`
= 1, `first_execution_id` = `last_execution_id` = this run's own `execution_id`,
`generated_at` = this run's own `completed_at` — never the wall clock). The CLI's
`run_continuous_improvement_phase` obtains `ContinuousImprovementService` exclusively
from `PlatformContext` and calls `improve(historical_dataset)` — identical failure
semantics to Grounding/Quality Governance/Recommendation (surfaced, never fatal), and
runs whenever this is a live run. No observation, detection, generation, policy, or
rule-catalogue logic exists in the CLI. Because a single-execution reference can
satisfy neither the governed recurring-finding floor (`minimum_occurrences`) nor the
trend floor (at least two data points), the golden dataset deterministically observes
an empty — but genuine — `ContinuousImprovementResult`.

**Continuous Improvement Serializer (`continuous_improvement/serialization/`).**
`ContinuousImprovementSerializer` renders `continuous_improvement_result.json`
(canonical `model_dump`), `continuous_improvement_report.md`, and
`continuous_improvement_metrics.md` — a pure projection computing nothing; every
rendered value already exists inside `ContinuousImprovementResult`. It imports no
engine, service, policy, rule catalogue, or `HistoricalDatasetProvider`
implementation.

**Execution Package.** `ExecutionData.continuous_improvement_result` is
additive-only (no existing field changed). `ExecutionWriter` appends the three
continuous improvement artifacts only when `continuous_improvement_result` is
present — the same conditional-append mechanism as every other peer subsystem, no
special case.

**Manifest purity (mirrors ADR-0017 §D31, ADR-0019 §D10).** The manifest gains
exactly three additive keys — `continuousImprovementExecuted`,
`continuousImprovementReport`, `continuousImprovementMetrics` — a flag and two
artifact filenames. No finding, trend, opportunity, summary, or metric value is ever
copied into the manifest; that runtime state lives exclusively in
`ContinuousImprovementResult` / `continuous_improvement_result.json`.

**Golden integration.** `_run_golden_pipeline()` now improves immediately after
Recommendation; `PipelineResult` carries `continuous_improvement_result`. The golden
dataset re-baselines `GOLDEN_DATASET_VERSION` `1.4.0` → `1.5.0` — the nine source
artifacts and the golden response are unchanged; only the generated artifact set
grows by the three continuous improvement files. The Architecture Version remains
`1.2.0`; the Platform Version is unchanged.

**One-way dependency chain (frozen).**

```
Continuous Improvement Runtime (engine + service)
    → ContinuousImprovementResult
    → Continuous Improvement Serializer
    → Execution Package
    → Manifest
    → Release
```

## 9. PlatformContext

`PlatformContext` exposes two composition-root methods, construction only:

- `create_improvement_policy() -> ImprovementPolicy`
- `create_continuous_improvement_service() -> ContinuousImprovementService`

Mirroring `create_recommendation_policy()` / `create_recommendation_service()` (ADR-0019), these are the **only** sanctioned points outside the `continuous_improvement` package that may construct its objects, enforced by a containment test.

## 10. Execution package

Activated by CAP-083C (§8c). Every Continuous Improvement execution artifact is a **pure projection** of `ContinuousImprovementResult`, reproducible from it alone, computing nothing — the same serialization invariant ADR-0019 §D8 established for Recommendation (Recommendation 8: runtime before reporting).

## 11. Implementation roadmap (non-normative)

1. **Done (CAP-083A).** Architecture & governance freeze: canonical models, typed identities, independent version axes, governed policy, dormant service contract, `PlatformContext` registration.
2. **Done (CAP-083B).** Deterministic Continuous Improvement Engine: derive findings/trends/opportunities strictly from a resolved Historical Dataset (Recommendation 7), never independent analysis. See §8a.
3. **Done (CAP-083B.1).** `ContinuousImprovementResult` Runtime Contract Freeze: permanent certification, no behaviour change. See §8b.
4. **Done (CAP-083C).** Runtime activation — `improve` wired into the pipeline after Recommendation, the Execution Package projection added, golden dataset re-baselined `1.4.0` → `1.5.0`. See §8c.
5. Historical Dataset implementation (reserved, ADR-0021 §Stage 6) — the actual storage/ordering/lineage/retention/indexing/search `HistoricalDatasetReference` currently only names, and that a future `HistoricalDatasetProvider` may resolve against instead of the single-execution reference CAP-083C mints.
6. CAP-084 (Knowledge Graph), CAP-085 (Organizational Memory), CAP-086 (Learning Framework) — the remaining reserved Layer 2 capabilities.

Each lands behind the unchanged `improve` signature and the unchanged `ContinuousImprovementResult` contract — no architectural change required.

## 12. Terminology

- **Improvement finding** — one recurring issue (`ImprovementFinding`), referencing the executions it was observed across, never copying them.
- **Improvement trend** — one observed direction (`ImprovementTrend`), observation only, never a prediction.
- **Improvement opportunity** — one deterministic "what should receive attention" (`ImprovementOpportunity`), by reference only, never "the optimal plan."
- **Continuous Improvement Framework** is a distinct, Layer 2 capability from every Layer 1 subsystem it never touches directly — a consumer of Historical Truth, producing Derived Knowledge, per ADR-0021's Truth Hierarchy.
