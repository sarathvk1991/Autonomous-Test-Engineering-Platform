# Learning Framework — Design Proposal

- **Status:** Accepted, live (CAP-086A froze the architecture; CAP-086A.1 froze the future engine's internal decomposition and governance; CAP-086A.2 froze the decision-governance constitution every collaborator's decisions must satisfy; CAP-086B implemented the first deterministic engine behind it, unchanged, still unwired)
- **Capability:** CAP-086 — Learning Framework
- **Milestones covered:** CAP-086A (Architecture & Governance Freeze), CAP-086A.1 (Learning Architecture Refinement & Engine Governance Freeze — see §8a), CAP-086A.2 (Learning Decision Governance & Deterministic Execution Constitution), CAP-086B (Deterministic Learning Engine — see §8b)
- **Governed by:** ADR-0029
- **Depends on:** ADR-0020 (Platform Evolution Roadmap & Architectural Constitution), ADR-0021 (Cross-Execution Data Architecture & Historical Intelligence Constitution), ADR-0025 (Derived Knowledge Architecture & Layer 2 Constitution — the peer-independence and fan-in rules this framework's own single-input boundary is defined against), ADR-0026 (Organizational Knowledge Architecture & Learning Constitution — Learning's earliest principles), and ADR-0028 (Learning Constitution — the full constitutional definition of what this framework produces).

---

## 1. Problem

Layer 1 answers questions about one execution. Continuous Improvement (ADR-0022) answers questions about recurrence *of values* across many executions. Knowledge Graph (ADR-0023) answers questions about the *structure* connecting entities. Organizational Memory (ADR-0027) curates both peers' conclusions into trusted, institutionalized Organizational Knowledge. None of the three answers a fourth, different question ADR-0028 §Stage 1 already names: *given everything the organization now trusts, what should change?*

**No subsystem answers this today** (confirmed by the Stage 0 assessment of CAP-086A, ADR-0029). Left unbuilt, every future consumer needing validated, reusable organizational understanding would have to re-derive it ad hoc from raw Organizational Memory output; built as an extension of Organizational Memory itself, it would fuse a distinct responsibility (validating what should change) into an owner whose own responsibility is curation, not validation — exactly the coupling ADR-0001 forbids.

## 2. Scope of CAP-086A

CAP-086A is a **pure architecture milestone**. It freezes:

- the subsystem and its ownership boundary
- the canonical runtime contract, `LearningResult`
- the canonical models (`LearningCandidate`, `LearningValidation`, `LearningConfidence`, `Learning`, `LearningLifecycle`, `LearningSummary`, `LearningMetrics`)
- the typed identities (`LearningPolicyId`, `LearningCandidateId`, `LearningValidationId`, `LearningConfidenceId`, `LearningId`, `LearningLifecycleId`, `LearningResultId`)
- the independent version axes (`LearningFrameworkVersion`, `LearningPolicyVersion`, `LearningVersion`, `LearningLifecycleVersion`, `LearningValidationVersion`, `LearningResultVersion`)
- the governed `LearningPolicy` (capability switches, deterministic thresholds)
- the dormant `LearningService` contract, registered with `PlatformContext`

**CAP-086A does not implement validation.** No candidate is proposed, no learning is validated, no confidence is recorded, no lifecycle is recorded. No serializer, no Execution Package integration, no CLI phase, no Platform Version bump, no Architecture Version bump, no golden dataset change.

## 3. Stage 0 — Repository assessment (no redesign)

| Structure | Owner | Scope | Why it is not Learning |
|---|---|---|---|
| `ContinuousImprovementResult` | Continuous Improvement (ADR-0022) | One Historical Dataset's recurrence | Observes recurrence *of values* — never validates a proposed organizational change. |
| `KnowledgeGraphResult` | Knowledge Graph (ADR-0023) | One Historical Dataset's structure | Projects structural connections — never validates a proposed organizational change. |
| `OrganizationalMemoryResult` | Organizational Memory (ADR-0027) | Curated Organizational Knowledge from two Layer 2 peers | Curates and promotes Best Practices — never validates what should change as a result of trusting them; that is a distinct, later question (ADR-0026 §Stage 10). |
| ADR-0020 Layer 2 reservation (CAP-086) | Name, not implementation | No code exists for the remaining reserved Layer 2 capability. |

A full-repository grep for `LearningResult`, `LearningService`, `LearningPolicy`, `learning_framework`, `LearningEngine` found no code module anywhere — the only prior hit is ADR-0025 §Stage 4's own forward-reference inside an illustrative list, not a definition. **This is a greenfield capability**; no redesign of Continuous Improvement, Knowledge Graph, or Organizational Memory is needed or proposed. All three remain exactly where they already are, owned by exactly the subsystem that already owns them (ADR-0029 §D1, Recommendation 1).

> No architectural weakness found. Proceeding with a pure architecture and governance freeze.

## 4. Subsystem & ownership

`requirement_intelligence/learning/` owns **only**:

- the canonical learned knowledge (`LearningResult`)
- learning candidates (`LearningCandidate`)
- validation history (`LearningValidation`)
- confidence records (`LearningConfidence`)
- validated learnings (`Learning`)
- maturity/lifecycle state (`LearningLifecycle`)
- Learning Framework metadata (identities, versions, policy)
- learning summaries and metrics (`LearningSummary`, `LearningMetrics`)

It never owns Requirement Enhancement, Grounding, Validation, CP1, Quality Governance, Recommendation, Continuous Improvement, Knowledge Graph, Organizational Memory, the Execution Package, the Historical Dataset itself, Feature Engineering, Prediction, Optimization, or Autonomous Execution (Recommendation 1, ADR-0029).

## 5. Canonical models

Every model is immutable (`Schema`, `frozen=True`), tuple-backed where it holds a collection, camelCase-serialising, and validator-guarded only for **structural integrity** — no behavior, no inference:

- **`LearningCandidate`** — one proposed, not-yet-validated conclusion drawn from one or more Best Practices (referenced by id only) inside a completed `OrganizationalMemoryResult` (`candidate_id`, `source_best_practice_ids`, `proposed_change`, `confidence`). Must reference at least one source best practice (explainability, mirrors `Lesson`).
- **`LearningValidation`** — one governed record that a validation event occurred against a candidate (`validation_id`, `candidate_id`, `gates_cleared`, `rationale`, `validated_at`, `confidence`, `policy_version`). Records history; never performs validation. `gates_cleared` names which of the six governed Stage 6 gates (ADR-0028) the event covered.
- **`LearningConfidence`** — one governed record of a confidence determination for a candidate or a learning (`confidence_id`, `subject_id`, `level`, `evidence_count`, `rationale`, `recorded_at`, `supersedes_confidence_id`). Confidence evolves by producing a new record, never by mutating an existing one (ADR-0028 §Stage 9).
- **`Learning`** — one validated conclusion promoted from exactly one candidate and certified by exactly one validation record (`learning_id`, `candidate_id`, `validation_id`, `message`, `maturity`, `confidence`). Adjacent promotion only — never skips past the candidate it was validated from.
- **`LearningLifecycle`** — one governed record of a subject's current maturity state (`lifecycle_id`, `subject_id`, `maturity`, `maturity_reason`). Records state; never transitions it.
- **`LearningSummary`** / **`LearningMetrics`** — human-readable aggregate and build statistics only (candidate/learning/validation counts, maturity distribution) — recorded values, never model-internal calculations.
- **`LearningResult`** — the canonical runtime contract: every candidate, learning, validation record, confidence record, lifecycle record, the summary, the metrics, the governing policy identity/version, and the one consumed `OrganizationalMemoryResult` id reference.

## 6. Explainability invariant

Every `LearningValidation`'s `candidate_id` must resolve among the result's own `candidates`. Every `Learning`'s `candidate_id` and `validation_id` must each resolve among the result's own `candidates` and `validations`. Every `LearningConfidence`'s and `LearningLifecycle`'s `subject_id` must resolve among the result's own candidate or learning ids. A `LearningCandidate` with zero source best practices, or a `LearningValidation` with zero cleared gates, is not constructible — a conclusion with no traceable evidence is not explainable (ADR-0029 §D3/§D9, Recommendation 9).

## 7. Governed policy

`LearningPolicy` — immutable, declarative, no executable logic:

- **`LearningCapabilitySwitches`** — independent on/off switches: `enable_candidate_proposal`, `enable_validation`, `enable_confidence_recording`, `enable_lifecycle_recording` (all `True` by default — governed intent, no engine reads them yet), plus `enable_deterministic_engine` / `enable_ml_engine` / `enable_llm_engine` / `enable_reinforcement_learning_engine` / `enable_neuro_symbolic_engine` (all reserved `False` until a future engine milestone).
- **`LearningThresholds`** — governed numeric bounds a future engine must respect: `minimum_best_practices_for_candidate` (2, reflecting ADR-0028 §Stage 6's "a single Best Practice, in isolation, is not enough"), `minimum_validation_gates_for_learning` (6 — all governed gates required by default), `minimum_confidence_for_learning`.

A `LearningPolicyBuilder` and `default_learning_policy()` assemble the CAP-086A default at `LearningPolicyVersion` 1.0.0.

## 8. Runtime boundary (frozen, dormant)

`LearningService` exposes exactly one method:

```python
def build(
    self,
    organizational_memory_result: OrganizationalMemoryResult,
) -> LearningResult:
    ...
```

It depends only on the one completed `OrganizationalMemoryResult` it consumes — never a Layer 1 subsystem, never Continuous Improvement's or Knowledge Graph's own result directly, and never the Historical Dataset directly (ADR-0028 §Stage 12; ADR-0029 §D2/Recommendation 7). Abstract at CAP-086A; `DormantLearningService` raises `NotImplementedError`. A later CAP-086 milestone implements the method behind this unchanged signature, exactly as CAP-085B implemented Organizational Memory's own entry point behind the ADR-0027 boundary.

## 8a. CAP-086A.1 — Internal Engine Architecture

CAP-086A.1 freezes the future deterministic engine's internal decomposition and governance *before* CAP-086B implements it — no code, no collaborator class, no rule catalogue exists yet. Full detail lives in ADR-0029's "Internal Engine Architecture" section and D9–D17; summarised here:

**Deterministic engine decomposition (D9).** A modular collaborator pipeline, mirroring Organizational Memory's own decomposition (ADR-0027 §D9) and Knowledge Graph's before it (ADR-0023 §D10):

```
LearningCandidateCollector → LearningCandidateClusterer → LearningGenerator
    → InstitutionalizationEvaluator → LearningValidator → StabilityEvaluator
    → ConfidenceRecorder → PromotionRecorder → LifecycleRecorder
    → SummaryBuilder/MetricsBuilder → ResultBuilder
```

Each collaborator owns exactly one responsibility; none computes another's (Recommendation 19).

**Collaborator ownership and layering (D10).** Each collaborator's permitted output is fixed in advance (see ADR-0029's table) — `SummaryBuilder` and `MetricsBuilder` never compute knowledge, only tally already-recorded rows; `ResultBuilder` alone assembles the final result. `PromotionRecorder`'s own output — promotion metadata — is reserved: no `LearningPromotion` record type exists yet, mirroring how ADR-0027 §D14 reserved `PromotionRule` ahead of its own engine.

**Adjacent-only promotion (D11).** Best Practice → Learning Candidate → Learning. Promotion never skips a level (Best Practice directly to Learning is forbidden) — already structurally guaranteed by the CAP-086A model shapes (`LearningCandidate.source_best_practice_ids` names Best Practices only; `Learning.candidate_id` carries no field capable of holding a raw Best Practice id), now frozen as permanent constitutional intent (Recommendation 18).

**Validation vs. Institutionalization (D12).** Validation answers "is the Learning technically valid?" (`LearningValidator`, the six ADR-0028 §Stage 6 gates). Institutionalization answers "is the Learning organizationally ready?" (`InstitutionalizationEvaluator`, expressed through the already-frozen `LearningMaturity` ladder). Neither performs the other's responsibility (Recommendation 16).

**Learning Stability (D13).** Stability — consistency across organizational evidence over time — is permanently independent of Confidence (strength of evidence) and Maturity (organizational adoption). No dedicated runtime field exists yet; this milestone freezes the concept and its independence only (Recommendation 17).

**Complete explainability chain (D14).** `Learning → Learning Candidate → Best Practice → Lesson → Experience → (Continuous Improvement or Knowledge Graph) → Historical Dataset → Execution Ids → Runtime Truth`. No promotion or institutionalization may occur unless this full chain is reconstructable (Recommendation 21).

**Engine philosophy (D15).** The Learning Engine validates, institutionalizes, promotes, matures, and records confidence/stability/lifecycle — it never invents a technical finding, and never re-performs Continuous Improvement's, Knowledge Graph's, or Organizational Memory's own analysis (Recommendation 15).

**Deterministic execution pipeline (D16, corrected by CAP-086B's own Stage 0 review — see §8b).** Collect → Cluster → Validate → Generate → Evaluate institutionalization → Evaluate stability → Record confidence → Record promotion → Record lifecycle → Build summary → Build metrics → Build result. Frozen order; algorithms within a stage may vary. Validation precedes generation because `Learning.validation_id` is a required field and `LearningGenerator` is `Learning`'s sole constructor — a `LearningValidation` must already exist, over the candidate, before the `Learning` it certifies can be built.

**Result ownership (D17).** `ResultBuilder` is the sole constructor of `LearningResult`, exactly mirroring Organizational Memory's own frozen invariant (ADR-0027 §D16; Recommendation 20).

## 8b. CAP-086B — Deterministic Learning Engine

CAP-086B is the later milestone §8a's D9/D10/D16 pre-specified: it implements `build` behind the unchanged signature above, exactly as ADR-0029 §D27 describes. Along the way, its own Stage 0 review found a genuine contradiction between CAP-086A's required `Learning.validation_id` field and §8a's original Generate-before-Validate ordering — resolved, with the user's explicit sign-off, by reordering `LearningValidator` before `LearningGenerator` (D9/D16), never by loosening the model.

**Modular architecture, exactly as pre-specified (corrected order).** `DeterministicLearningEngine` is a thin pipeline orchestrator, never a monolithic class: `LearningCandidateCollector` → `LearningCandidateClusterer` → `LearningValidator` → `LearningGenerator` → `InstitutionalizationEvaluator` → `StabilityEvaluator` → `ConfidenceRecorder` → `PromotionRecorder` → `LifecycleRecorder` → `SummaryBuilder`/`MetricsBuilder` → `ResultBuilder`, each in `learning/engine/`, each owning exactly one responsibility.

**Rule catalogue.** `learning/rules/` introduces `LearningRule` (metadata only — id, `LearningRuleCategory`, title, description, priority, `capability_switch`, `supported_hierarchy_level`, `documentation_reference` — deliberately no numeric threshold field), `LearningRuleCatalog` (ordering/lookup/category/level projections only), and `LearningRuleBuilder`/`default_learning_rule_catalog()` shipping 24 governed rules across the twelve categories §8a named — one per frozen collaborator.

**Deterministic algorithms.** Candidate collection: corpus-gated (ADR-0028 §Stage 6), then one candidate per Best Practice, deduplicated by deterministic id. Clustering/consolidation: byte-equality merge on `proposed_change` text — never semantic similarity — unioning source references and keeping the lowest surviving candidate id. Validation and generation: floor-gated against `LearningThresholds.minimum_confidence_for_learning`, a candidate validated (and only then generated) once its own evidence clears the governed floor. Confidence: a single shared deterministic function of evidence-count-over-threshold, called identically by the validator, the generator, and the confidence recorder so all three agree by construction. Institutionalization and stability: deterministic functions of already-computed confidence and institutionalization decisions, never a re-read of the consumed result. No ML, no LLM, no embeddings, no vector search, no semantic similarity, no probabilistic inference, no fuzzy matching, no randomness, no prediction, no statistical learning.

**Ownership.** `LearningCandidateCollector` is the sole candidate authority; `LearningCandidateClusterer` the sole clustering/consolidation authority; `LearningValidator` the sole validation authority; `LearningGenerator` the sole Learning authority (from validated candidates only — never Best Practices directly); `InstitutionalizationEvaluator` the sole institutional-readiness authority; `StabilityEvaluator` the sole stability authority; `ConfidenceRecorder` the sole confidence authority; `PromotionRecorder` the sole promotion authority; `LifecycleRecorder` the sole lifecycle authority; `SummaryBuilder`/`MetricsBuilder` each compute exactly once and compute no Learning; `ResultBuilder` the sole `LearningResult` constructor.

**Reserved decisions remain reserved.** `StabilityEvaluator`'s and `PromotionRecorder`'s decisions are genuinely computed and tested every build, but neither is threaded into `LearningResult` — no dedicated model exists for either, and this milestone introduces none (§8a's D10/D13 reserved-output notes, unchanged).

**Still not activated.** `PlatformContext.create_learning_service()` now returns `DeterministicLearningService`, replacing `DormantLearningService` (which CAP-086B removes). Still unwired: nothing calls `build()` at runtime, so the golden baseline, Architecture Version, and Platform Version are all unchanged.

**Tests.** New deterministic tests cover rule catalogue construction, each collaborator's sole-authority ownership, clustering/consolidation determinism, floor-gated validation and generation, confidence agreement across collaborators, institutionalization/stability decision correctness, lifecycle append-only recording, builder single-computation guarantees, end-to-end engine determinism and explainability, policy gating, and containment (no Layer 1 imports, no Historical Dataset touched directly, no Organizational Memory implementation class imported, only `PlatformContext` constructs the service externally).

## 9. PlatformContext

`PlatformContext` exposes two composition-root methods, construction only:

- `create_learning_policy() -> LearningPolicy`
- `create_learning_service() -> LearningService`

Mirroring `create_organizational_memory_policy()` / `create_organizational_memory_service()` (ADR-0027), these are the **only** sanctioned points outside the `learning` package that may construct its objects, enforced by a containment test.

## 10. Execution package

Not introduced by CAP-086A. When a future milestone activates the runtime, every Learning execution artifact will be a **pure projection** of `LearningResult`, reproducible from it alone, computing nothing — the same serialization invariant ADR-0022 §D8, ADR-0023 §D8, and ADR-0027 §D19 established for their own subsystems (Recommendation 10 of ADR-0029).

## 11. Implementation roadmap (non-normative)

1. **Done (CAP-086A).** Architecture & governance freeze: canonical models, typed identities, independent version axes, governed policy, dormant service contract, `PlatformContext` registration.
2. **Done (CAP-086A.1).** Engine architecture refinement & governance freeze: the future engine's modular collaborator decomposition, adjacent-only promotion discipline, the Validation/Institutionalization/Stability distinctions, the complete explainability chain, and reserved promotion-metadata governance — no code, still architecture only. See §8a.
3. **Done (CAP-086A.2).** Decision Governance & Deterministic Execution Constitution: the six permanent properties every Learning decision must satisfy, freedom from hidden state, immutable-only collaborator communication, and whole-engine purity — no code, still architecture only.
4. **Done (CAP-086B).** Deterministic Learning Engine: implement the CAP-086A.1 collaborator pipeline (corrected order, §8b) strictly from the one resolved `OrganizationalMemoryResult` (Recommendation 6 of ADR-0029), obeying the CAP-086A.2 decision-governance constitution, never independent analysis. See §8b.
5. Runtime activation (CAP-086C, reserved) — wire `build` into a live cross-execution pipeline, add a future Execution Package projection, golden re-baseline, mirroring CAP-085C's activation of Organizational Memory.
6. Future AI validation — statistical, ML, LLM, GraphRAG, reinforcement learning, and neuro-symbolic engines (reserved), behind the unchanged `LearningResult` contract — never a redesign of it.
7. Feature Engineering (Layer 3, reserved) — the first capability outside Layer 2, to consume `LearningResult` (Recommendation 8 of ADR-0029), completing the Layer 2 → Layer 3 bridge ADR-0028 §Stage 16 names.

Each lands behind the unchanged `build` signature and the unchanged `LearningResult` contract — no architectural change required.

## 12. Terminology

- **Learning Candidate** — one proposed, not-yet-validated conclusion drawn from Best Practices, referenced by id only (`LearningCandidate`).
- **Learning Validation** — one governed record that a validation event occurred (`LearningValidation`) — history, never the act itself.
- **Learning Confidence** — one governed record of how strongly evidence supports a subject at a point in time (`LearningConfidence`) — metadata, never truth.
- **Learning** — one validated conclusion, carrying a governed maturity level, promoted from exactly one candidate (`Learning`).
- **Learning Lifecycle** — one governed record of a subject's current maturity state (`LearningLifecycle`) — a record, never a transition.
- **Learning Framework** is a distinct, Layer 2 capability from every Layer 1 subsystem and from its three Layer 2 predecessors — the fourth and final Continuous Learning capability (ADR-0020), a validator of Learned Knowledge (ADR-0028), extending none of its consumed input and owning none of its predecessors' responsibilities. It is the constitutional bridge from Layer 2 to Layer 3 (ADR-0028 §Stage 16).
