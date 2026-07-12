# Quality Governance Framework — Design Proposal

- **Status:** Proposed (design only — CAP-080A introduces no runtime behaviour)
- **Capability:** CAP-080 — Quality Governance
- **This milestone:** CAP-080A — Architecture, Canonical Model & Governance Freeze
- **Governed by:** ADR-0017
- **Depends on:** ADR-0016 (Evidence Grounding & Traceability), ADR-0011 (CP1), the Response Validation Framework.

---

## 1. Problem

The Requirement Intelligence Layer now produces three independent, governed judgements about a single run:

| Result | Question it answers | Owner |
|---|---|---|
| `GroundingResult` | *Is each generated requirement supported by the evidence, and how confidently?* | Grounding (ADR-0016) |
| `ValidationResult` | *Is the response well-formed against the reasoning contract?* | Validation |
| `CP1Result` | *Is the run engineering-ready?* | CP1 (ADR-0011) |

Each is authoritative in its own lane, and each is deliberately **non-gating** and unaware of the others. Grounding measured RC-1 at 21/22 supported with zero hallucinations, but explicitly deferred *enforcement* (ADR-0016 §D5: "measure before you gate"). Validation and CP1 both passed RC-1 with zero findings while grounding was entirely unassessed.

What is missing is the layer that reads all three and renders a **single, governed, explainable release decision**: *given the grounding, validation, and readiness of this run, is it releasable, releasable-with-warnings, or not?* Today that judgement exists nowhere — it would have to be made ad hoc by a human or, worse, implied by whichever gate happened to run last. There is **no Quality Governance subsystem** in the repository (confirmed in Stage 0 of this milestone).

An ungoverned, unexplainable, or score-only release decision is exactly the failure mode the platform's governance discipline exists to prevent. The missing capability is a subsystem that owns the question **"is this run releasable on quality grounds, and precisely why?"**

## 2. Scope of CAP-080A

CAP-080A is a **pure architecture freeze**. It introduces the canonical models, typed identities, governed policy, and the dormant service boundary, and it does **nothing else**:

- no policy evaluation, no quality calculation, no release decision;
- no rule engine, no scoring, no findings generation;
- no runtime wiring, no execution-package artifacts, no CLI;
- no change to Grounding, Validation, CP1, Engineering Context, Analysis, Execution Package, Prompt Governance, the Architecture Version, the Platform Version, or the golden baseline.

It establishes the permanent architecture every later CAP-080 milestone implements *behind an unchanged service contract* — the same discipline ADR-0016 used to land grounding one frozen layer at a time.

## 3. Subsystem & ownership

A new governed subsystem, `requirement_intelligence/quality_governance/`, owns **only**:

- governance,
- policy evaluation,
- quality assessment,
- release decisions,
- governance findings.

It explicitly does **not** own Engineering Context, Analysis, Grounding, Validation, CP1, Execution Package, Reporting, or Serialization. It is a **peer consumer** downstream of the three result-producing subsystems, never an owner of any of their computation. This boundary is frozen (ADR-0017 §D1, Recommendations 1 & 5).

## 4. Canonical models

All models follow the repository conventions: immutable, `frozen`, `extra="forbid"`, camelCase-serialised via `to_camel`, tuple-backed collections, `Schema` base class, validator invariants only, no timestamps or UUIDs on the value objects, and deterministic serialization that round-trips.

```
QualityGovernanceResult      (runtime contract / carrier — the audit record)
  ├── analysis_id, execution_id                (provenance)
  ├── consumed_inputs: (ConsumedResultReference, …)   (which peer results it read)
  ├── assessment: QualityAssessment            (the governance body)
  │     ├── decision: QualityDecision
  │     ├── findings: (QualityFinding, …)
  │     └── summary: QualitySummary
  │           └── category_distribution: (QualityFindingCategoryCount, …)
  └── versions (framework / policy / result-contract), started_at, completed_at
```

- **`QualityDecision`** — the canonical enumeration `PASS` / `PASS_WITH_WARNINGS` / `FAIL` (§5).
- **`QualityFinding`** — a governance problem: category, severity, the source result judged, and a message. Governance findings only — never a Grounding, Validation, or CP1 finding (§6).
- **`QualitySummary`** — the headline: decision, recorded 0-100 roll-up score, governing policy, finding counts (total / warning / failure), and the category distribution (§7).
- **`QualityAssessment`** — the per-run aggregate tying the decision, findings, and summary to the governing policy, with cross-referential/explainability validators.
- **`QualityGovernanceResult`** — the frozen runtime contract; the complete audit record (§D3, Recommendation 3).

Every model is an **assembly target**: the future decision engine populates it; the models compute nothing. The only logic present is validator *invariants* (e.g. a `FAIL` must be accompanied by at least one `FAILURE` finding, so the decision is auditable from the result alone).

## 5. The release decision

`QualityDecision` is a canonical enumeration with frozen semantics:

- **`PASS`** — every governed quality rule is satisfied; releasable with no reservation.
- **`PASS_WITH_WARNINGS`** — no release-blocking rule violated, but one or more warning-level rules are; releasable with recorded reservations.
- **`FAIL`** — at least one release-blocking (failure-level or mandatory) rule violated; must not be released on quality grounds.

The decision is **not** a threshold over a single score (Recommendation 7). CAP-080A defines the vocabulary and semantics only; **no decision engine is implemented**.

## 6. Governance findings

A `QualityFinding` records that a governed `QualityPolicy` rule is violated. Categories include: grounding coverage below policy, hallucination rate exceeded, confidence below threshold, evidence coverage below policy, validation policy violated, CP1 policy violated, engineering readiness not met, mixed-quality evidence, and release-policy violation. These govern a *policy relationship* between an upstream result and the policy — they are not, and never duplicate, the upstream subsystems' own findings.

## 7. Governed policy

`QualityPolicy` is immutable governed data — the "policy is data" discipline of ADR-0015/0016. It prepares for governance of: minimum grounding score, maximum hallucination rate, minimum confidence, minimum evidence coverage, validation severity thresholds, CP1 severity thresholds, required engineering readiness, warning thresholds, failure thresholds, and release rules. Crucially it carries **two threshold bands** (`failure_thresholds`, `warning_thresholds`) plus mandatory `release_rules`, so the decision is rule-based, not score-based (Recommendation 7). `QualityPolicyBuilder` constructs it; `default_quality_policy()` returns the versioned default (`QualityPolicyVersion` 1.0.0). It calculates nothing.

## 8. Runtime boundary (dormant)

`QualityGovernanceService` is the single runtime entry point — an abstract contract with one method, `evaluate(grounding_result, validation_result, cp1_result) -> QualityGovernanceResult`. In CAP-080A it is **dormant**: `DormantQualityGovernanceService.evaluate` raises `NotImplementedError`, and `PlatformContext.create_quality_governance_service()` constructs it with the governed policy and no decision engine. `PlatformContext` remains the only composition root; `create_quality_policy()` is also registered. Nothing consumes the service, so runtime is byte-identical.

## 9. Four decision layers (frozen for future implementation)

Later milestones implement, independently and without redesign (Recommendation 6):

```
Policy  →  Rule Evaluation  →  Quality Assessment  →  Release Decision
```

## 10. Execution package (future)

The future artifacts `quality_governance.json`, `quality_report.md`, and `quality_score.md` will be **pure projections** of a `QualityGovernanceResult`, exactly following the Grounding serialization rule (ADR-0016 §D16, Recommendation 4). The Execution Package will compute nothing.

## 11. Implementation roadmap (non-normative)

1. **CAP-080A** *(this milestone)* — architecture, models, identities, policy, dormant service. Freeze.
2. **CAP-080B** — the rule-evaluation layer: governed rules evaluated against the three consumed results into `QualityFinding`s. Still non-gating.
3. **CAP-080C** — the quality-assessment + decision layers: `QualityAssessment` and `QualityDecision` assembled from findings under the two-band + mandatory-rule policy.
4. **CAP-080D** — runtime activation and execution-package projection; golden re-baseline.
5. **Later** — enforcement/gating, and the future extensions of Recommendation 8.

## 12. Terminology

"Quality Governance" (this subsystem, the release decision) is distinct from the placeholder root-level `quality_governance/` **Quality Governance Layer** (CP2+, Phase 4) and from `ContextGrounding` / requirement grounding. The three are complementary and kept terminologically distinct.

---

The full architectural decisions, invariants, and the eight mandatory architectural recommendations are recorded in **ADR-0017**.
