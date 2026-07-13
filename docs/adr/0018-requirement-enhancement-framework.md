# ADR-0018 — Requirement Intelligence Enhancement Framework

- **Status:** Proposed
- **Date:** 2026-07-13 (CAP-081A — Architecture & Governance Freeze)
- **Supersedes:** nothing. **Amends:** nothing. **Extended by:** future CAP-081 milestones will implement the enrichment, relationship-detection, and observation engines behind the contracts this ADR freezes, mirroring how ADR-0017 (CAP-080A) froze Quality Governance before CAP-080B/C/D implemented and wired it.
- **Governing design:** `docs/proposals/requirement-enhancement-framework.md`
- **Depends on:** ADR-0015 (Engineering Context Orchestration Model and Policy), the Requirement Analysis Service (`docs/architecture/requirement-analysis-service.md`) — Requirement Enhancement consumes their completed outputs, `EngineeringContext` and `AnalysisResult`.
- **Runtime status:** **Dormant (CAP-081A).** No enrichment, relationship detection, observation generation, consistency analysis, completeness analysis, graph construction, recommendation, or runtime wiring exists. `RequirementEnhancementService.enhance` is abstract; the registered `DormantRequirementEnhancementService` raises `NotImplementedError`. Nothing calls `enhance` at runtime, so runtime behaviour is byte-identical and the golden baseline is unchanged. The Architecture Version remains **1.2.0**.

## Problem

The Requirement Intelligence Layer currently treats each generated requirement as an
isolated unit. Grounding judges whether *one* requirement is supported by evidence;
Validation judges whether the *response* is well-formed; CP1 judges whether the *run*
is engineering-ready; Quality Governance judges whether the *run* is releasable. **No
subsystem looks at the generated requirement set as a whole** — enriching individual
requirements with deterministic attributes, detecting relationships between them
(dependencies, conflicts, duplicates, refinements), or observing set-level properties
(completeness gaps, consistency conflicts) before those judgements run.

Left unbuilt, requirement-to-requirement structure is invisible to every downstream
consumer: Grounding cannot know two requirements duplicate each other, Quality
Governance cannot know a mandatory dependency is missing, and no report can show a
requirement's relationships without ad-hoc, per-consumer computation. Built carelessly
— as an extension bolted onto Grounding or Analysis, or as several competing
"enriched requirement" or "relationship" representations — it would entangle a
distinct responsibility into subsystems that already have one, exactly the coupling
ADR-0001 forbids and ADR-0015/0016/0017 each declined for their own domains.

## Decision

Introduce a new governed subsystem, **`requirement_intelligence/enhancement/`**, that
will own Requirement Intelligence Enhancement: requirement enrichment, requirement
relationships, requirement observations, and enhancement metadata. It:

1. Introduces canonical, immutable models — `EnhancedRequirement`,
   `RequirementRelationship`, `RelationshipGraph`, `RequirementObservation`,
   `EnhancementFinding`, `EnhancementSummary`, `EnhancementMetrics`, and
   `RequirementEnhancementResult` — following the `Schema` conventions and the
   typed-identity pattern of ADR-0015/0016/0017.
2. Introduces strongly typed identities — `EnhancementPolicyId`,
   `RequirementEnhancementId`, `EnhancedRequirementId`, `RelationshipGraphId`,
   `RequirementObservationId`, `RequirementEnhancementResultId` — deterministic value
   objects, no UUIDs, no timestamps, no randomness.
3. Introduces independent version axes — `EnhancementFrameworkVersion`,
   `EnhancementPolicyVersion`, `EnhancementResultVersion`, `RelationshipVersion`,
   `ObservationVersion` — each evolving without forcing the others to change
   (Recommendation 4).
4. Introduces a governed `EnhancementPolicy` (immutable data: capability switches,
   enrichment rules, relationship rules, observation rules) with an
   `EnhancementPolicyBuilder` and `default_enhancement_policy()`.
5. Fixes the single runtime boundary — `RequirementEnhancementService.enhance(engineering_context, analysis_result) -> RequirementEnhancementResult` — as an **abstract, dormant contract**. `PlatformContext` gains `create_enhancement_policy()` and `create_requirement_enhancement_service()`.

Requirement Enhancement runs **after** Analysis and **before** Grounding, Validation,
CP1, and Quality Governance, consuming only the completed `EngineeringContext` and
`AnalysisResult`; it is a **peer consumer** of those two inputs and owns none of their
computation, and it owns none of the four downstream subsystems' computation either.
Engineering Context Orchestration, Analysis, Grounding, Validation, CP1, Quality
Governance, and the Execution Package are **unchanged**.

**CAP-081A establishes the architecture only.** No requirement is enriched, no
relationship is detected, no observation is generated, and nothing is wired into a
runtime path. Runtime behaviour is byte-identical; the golden baseline is unchanged;
the Architecture Version remains 1.2.0.

The full model and roadmap is in `docs/proposals/requirement-enhancement-framework.md`.

---

## D1 — Why Requirement Enhancement is a new, peer subsystem, not an extension of Grounding or Analysis

Requirement Enhancement answers a question neither Grounding nor Analysis asks.
Analysis produces the raw generated requirements; Grounding judges whether each is
*supported by evidence*. Neither enriches a requirement with deterministic attributes,
detects a relationship between two requirements, or observes a property of the
requirement set as a whole. Folding enhancement into Analysis would make requirement
generation and requirement intelligence one responsibility; folding it into Grounding
would make evidence-support judgement and structural analysis one responsibility —
either way, two concerns collapse into one owner, exactly the coupling ADR-0001
forbids and ADR-0015/0016/0017 each declined for their own domains. Requirement
Enhancement is a distinct responsibility with a distinct owner, and a **consumer
only** of `EngineeringContext` and `AnalysisResult` (Recommendation 5 restated as
Recommendation 1 here — consumer-only scope, mirroring ADR-0017 Recommendation 1).

## D2 — Why enhancement sits between Analysis and Grounding

The frozen pipeline order (ADR-0017 §D30) is:

```
Engineering Context → Analysis → Grounding → Validation → CP1 → Quality Governance → Execution Package
```

Requirement Enhancement's insertion point is **after Analysis, before Grounding**:

```
Engineering Context → Analysis → Requirement Enhancement → Grounding → Validation → CP1 → Quality Governance → Execution Package
```

Enrichment, relationships, and observations are properties of the *generated
requirement set* — they exist as soon as Analysis produces requirements, and they are
information a downstream consumer (Grounding, Quality Governance, or a future
capability) may want to read, never information any of them computes. Placing
Requirement Enhancement immediately after Analysis is what lets every downstream
subsystem optionally consume a `RequirementEnhancementResult` later without
Requirement Enhancement ever depending on them. **CAP-081A wires nothing**: this
insertion point is documented, not implemented — no CLI phase calls `enhance`.

## D3 — Why `RequirementEnhancementResult` is the complete, self-contained record

The runtime contract is `RequirementEnhancementResult`: a peer to `GroundingResult` /
`ValidationResult` / `CP1Result` / `QualityGovernanceResult`. It carries every
enriched requirement, the relationship graph, every observation, every surfaced
finding, the summary, the metrics, the governing policy identity/version, and — via
`EnhancementInputReference` — the identity and version of each upstream input it
consumed. This is a deliberate design choice, mirroring ADR-0017 §D3: the result must
be **completely explainable from this one object**, with no need to re-run
enhancement or inspect any runtime service, Engineering Context Orchestration, or
Analysis. The model records *provenance* of the consumed inputs, never their
contents, so the record is legible and self-contained without embedding or coupling to
the upstream aggregates. The result's validator enforces the explainability invariant
structurally: a finding cannot exist without the observation it was derived from, and
an enriched requirement's relationship/observation references must resolve inside the
same result.

## D4 — Why the models compute nothing (assembly targets only)

Every canonical model is `frozen`, tuple-backed, camelCase, and free of
timestamps/UUIDs, exactly like the Grounding and Quality Governance models. None
computes a value: a future engine populates them. The only logic present is validator
*invariants* that enforce cross-referential integrity — `RelationshipGraph` edges must
reference nodes already in the graph, `EnhancementFinding.observation_id` must resolve
to a recorded `RequirementObservation`, `EnhancedRequirement.relationship_ids` /
`observation_ids` must resolve inside the same result. Introducing the models fully
frozen — before any engine exists — forces their shape to be designed for every future
capability, not retrofitted around the first one, and lets each subsequent milestone
land behind an unchanged contract.

## D5 — Why identities are deterministic and independently versioned

`RequirementEnhancementId.for_run(analysis_id, execution_id)`,
`EnhancedRequirementId.for_requirement(...)`,
`RelationshipGraphId.for_enhancement(...)`,
`RequirementObservationId.for_ordinal(...)`, and
`RequirementEnhancementResultId.for_enhancement(...)` are **pure functions** of their
inputs — no clock, no UUID — so the same run always mints the same ids and a result is
reproducible and comparable across runs. Five version axes
(`EnhancementFrameworkVersion`, `EnhancementPolicyVersion`, `EnhancementResultVersion`,
`RelationshipVersion`, `ObservationVersion`) are distinct typed value objects that
advance **independently**: this is what lets a relationship type be added, an
observation category be added, or a policy be tuned, without forcing a framework or
result-contract change (Recommendation 4). Like ADR-0017 §D5, no existing identifier
is retyped; the change is purely additive, and the base identifier/version classes are
duplicated (not imported) from `quality_governance`, exactly as that package duplicated
them from `context_orchestration` and `grounding` — the eventual home remains `shared/`
(ADR-0015 §C, ADR-0016 §D6, ADR-0017 identity module docstring).

## D6 — Why the service boundary is fixed before any behaviour (dormant)

The subsystem exposes exactly one runtime entry point: `RequirementEnhancementService`,
an abstract contract with a single method —
`enhance(engineering_context, analysis_result) -> RequirementEnhancementResult`.
Everything else in the package (models, identities, policy) is internal. The service
depends only on the two frozen **result contracts** it consumes — `EngineeringContext`
and `AnalysisResult` — never on any *implementation* class (no
`EngineeringContextOrchestrator`, `EngineeringContextBuilder`,
`RequirementAnalysisService`, or provider). Fixing the boundary *before* implementing
any behaviour is what lets each later milestone — enrichment, relationship detection,
observation generation, runtime activation — land behind the unchanged `enhance`
signature, exactly as ADR-0016 §D7 did for `GroundingService.assess` and ADR-0017 §D6
did for `QualityGovernanceService.evaluate`.

**CAP-081A establishes the boundary only.** `enhance` is abstract and the registered
`DormantRequirementEnhancementService` raises `NotImplementedError`;
`PlatformContext.create_requirement_enhancement_service()` constructs it with the
governed policy and **no engine**. It is dormant — no runtime path consumes it,
guarded by a containment test that permits only `PlatformContext` to name the service
outside the package — so runtime behaviour is byte-identical.

---

## Architectural Recommendations (mandatory — frozen by this ADR)

### Recommendation 1 — Canonical Enhanced Requirement

A single immutable `EnhancedRequirement` model is introduced. All future enrichment
stages must extend this model rather than creating competing metadata structures.
There must never be multiple "enhanced requirement" representations.

### Recommendation 2 — Unified Relationship Model

All requirement relationships are represented using one canonical model,
`RequirementRelationship`, typed by the governed `RelationshipType` vocabulary
(`DEPENDS_ON`, `REFINES`, `CONFLICTS_WITH`, `DUPLICATES`, `DERIVED_FROM`, `SUPPORTS`,
`IMPLEMENTS`, `VALIDATES`, `MITIGATES`). Future capabilities add relationship *types*
to this vocabulary, never new relationship models.

### Recommendation 3 — Observation Before Recommendation

The architecture is frozen so observations (`RequirementObservation`) are produced
first, and any future recommendation is derived from an observation. Recommendation
engines must never perform independent analysis. This mirrors the successful Grounding
→ Classification → Confidence → Governance layering (ADR-0016) and the Quality
Governance Rule Evaluation → Assessment → Decision layering (ADR-0017).

### Recommendation 4 — Independent Capability Evolution

Enrichment, relationships, observations, completeness, consistency, recommendations,
and future AI-assisted capabilities must evolve independently. Each has an independent
version identity (`EnhancementFrameworkVersion`, `EnhancementPolicyVersion`,
`EnhancementResultVersion`, `RelationshipVersion`, `ObservationVersion`). No shared
version axis.

### Recommendation 5 — Runtime Contract First

`RequirementEnhancementResult` is the only runtime contract. Execution artifacts,
dashboards, historical analysis, CI/CD integrations, and future capabilities consume
this runtime contract. They never recompute enhancement — the same discipline ADR-0017
§D31 froze for Quality Governance's manifest boundary, applied here from the outset.

### Recommendation 6 — Graph-Centric Architecture

The architecture is frozen around a canonical `RelationshipGraph`. All future
analyses — duplicates, dependencies, contradictions, traceability, impact analysis —
derive from this graph instead of building separate relationship stores. This
establishes a single source of truth for requirement relationships.

### Recommendation 7 — Future Compatibility

Explicit extension points are reserved (documentation only) for future capabilities:

- semantic relationship detection
- AI-assisted enrichment
- historical requirement intelligence
- impact analysis
- change propagation
- architectural dependency analysis
- compliance mapping

These future capabilities must plug into the frozen contracts — extending
`RequirementEnhancementResult` and the governed `EnhancementPolicy` — without changing
`RequirementEnhancementService.enhance`'s signature or the runtime boundary.

---

## Trade-offs

- **A new subsystem adds a fifth judgement per run.** Accepted: Grounding, Validation,
  CP1, and Quality Governance each judge a different lane, and none enriches,
  relates, or observes the requirement set as a whole. That capability was missing,
  not redundant with any of them.
- **Governed defaults are illustrative until calibrated.** The CAP-081A default
  policy's capability switches and bounds are governed data, not yet exercised by any
  engine. Accepted: tuning is a versioned policy change, and no runtime consumes the
  values yet.
- **A re-baseline will be required at runtime activation.** Adding artifacts and
  pipeline stages in a later milestone will change golden checksums. Accepted: the
  golden baseline's re-baseline procedure exists precisely for intentional additive
  change; CAP-081A changes nothing.

## Future evolution

- The enrichment, relationship-detection, and observation engines (Recommendation 4),
  landing behind the unchanged `enhance` contract.
- **Runtime activation** — a later, deliberate decision to wire `enhance` into the
  Requirement Intelligence execution pipeline between Analysis and Grounding (D2).
- The execution-package projection (Recommendation 5) and its golden re-baseline,
  mirroring ADR-0016 §D16 and ADR-0017 §D30/§D31.
- The non-normative extensions of Recommendation 7.
- Promotion of the shared version/identity value-objects to `shared/` (the debt
  ADR-0015 §C, ADR-0016, and ADR-0017 already name).

## Ownership, runtime position, governance

- **Owns:** requirement enrichment, requirement relationships, requirement
  observations, enhancement metadata.
- **Does not own:** Engineering Context Orchestration, Analysis, Grounding,
  Validation, CP1, Quality Governance, Execution Package, Reporting, Serialization.
- **Runtime position (future, not yet wired):** `Engineering Context → Analysis → RequirementEnhancementService.enhance → RequirementEnhancementResult → Grounding → Validation → CP1 → Quality Governance → Execution Package`, consuming the two completed inputs; dormant through CAP-081A.
- **Governance:** registered as CAP-081 in the Platform Capability Matrix at
  implementation time; the golden baseline is re-based then. This ADR is **Proposed**
  until that milestone accepts it.
