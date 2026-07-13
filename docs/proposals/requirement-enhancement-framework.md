# Requirement Intelligence Enhancement Framework — Design Proposal

- **Status:** Proposed (CAP-081A freezes the architecture only; no engine, wiring, or execution artifact)
- **Capability:** CAP-081 — Requirement Intelligence Enhancement
- **Milestones covered:** CAP-081A (Architecture & Governance Freeze — this document)
- **Governed by:** ADR-0018
- **Depends on:** ADR-0015 (Engineering Context Orchestration), the Requirement Analysis Service.

---

## 1. Problem

The Requirement Intelligence Layer produces a set of generated requirements per run,
and four independent, governed judgements about that run:

| Result | Question it answers | Owner |
|---|---|---|
| `GroundingResult` | *Is each generated requirement supported by the evidence?* | Grounding (ADR-0016) |
| `ValidationResult` | *Is the response well-formed against the reasoning contract?* | Validation |
| `CP1Result` | *Is the run engineering-ready?* | CP1 (ADR-0011) |
| `QualityGovernanceResult` | *Is the run releasable on quality grounds?* | Quality Governance (ADR-0017) |

**No subsystem looks at the generated requirement set as a whole.** Nothing enriches
one requirement with deterministic attributes, detects a relationship between two
requirements (a dependency, a conflict, a duplicate, a refinement), or observes a
set-level property (a completeness gap, a consistency conflict) *before* the four
judgements above run. That capability exists nowhere in the repository today
(confirmed by the Stage 0 assessment of CAP-081A). Left unbuilt, requirement structure
stays invisible to every downstream consumer; built as an extension of Grounding or
Analysis, it would fuse a distinct responsibility into a subsystem that already has
one — exactly the coupling ADR-0001 forbids.

## 2. Scope of CAP-081A

CAP-081A is a **pure architecture milestone**. It freezes:

- the subsystem and its ownership boundary
- the canonical runtime contract, `RequirementEnhancementResult`
- the canonical models (`EnhancedRequirement`, `RequirementRelationship`,
  `RelationshipGraph`, `RequirementObservation`, `EnhancementFinding`,
  `EnhancementSummary`, `EnhancementMetrics`)
- typed identities and independent version axes
- the governed `EnhancementPolicy` and its builder
- the abstract, dormant `RequirementEnhancementService` contract
- `PlatformContext` registration

It does **not** implement enrichment, relationship detection, consistency analysis,
completeness analysis, graph construction, recommendations, runtime wiring, or
execution artifacts. No pipeline change. No Execution Package change. No golden
re-baseline. The Architecture Version remains **1.2.0**.

## 3. Subsystem & ownership

`requirement_intelligence/enhancement/` owns only:

- requirement enrichment
- requirement relationships
- requirement observations
- enhancement metadata

It never owns grounding, validation, CP1, governance, the execution package,
prompting, or the engineering context. It is a **consumer only** of the two completed
upstream inputs — `EngineeringContext` and `AnalysisResult` — exactly as Quality
Governance is a consumer only of `GroundingResult` / `ValidationResult` / `CP1Result`
(ADR-0017 Recommendation 1).

## 4. Canonical models

| Model | Owns |
|---|---|
| `EnhancedRequirement` | The single canonical enriched form of one generated requirement — deterministic attributes plus references (never copies) to the relationships and observations that involve it (Recommendation 1). |
| `RequirementRelationship` | One directed, typed edge between two requirements, typed by the governed `RelationshipType` vocabulary (Recommendation 2). |
| `RelationshipGraph` | The single canonical graph of every relationship in one enhancement run — nodes are requirement ids, edges are `RequirementRelationship` (Recommendation 6). |
| `RequirementObservation` | A raw, deterministic, un-interpreted signal about one or more requirements (Recommendation 3). |
| `EnhancementFinding` | A surfaced observation — references the `RequirementObservation` it was derived from, never copies it. |
| `EnhancementSummary` | The headline: counts, distributions, and a deterministic one-line description. Renders no verdict — Requirement Enhancement is non-gating. |
| `EnhancementMetrics` | Deterministic numeric roll-ups (enrichment coverage, relationship density, observation rate) — recorded values, never model-internal calculations. |
| `RequirementEnhancementResult` | The runtime contract: every enriched requirement, the relationship graph, every observation, every finding, the summary, the metrics, the governing policy identity/version, and the consumed-input provenance. |

Every model is `frozen=True`, tuple-backed collections, `camelCase` serialisation
(`alias_generator=to_camel`), and computes nothing — validators enforce
cross-referential integrity only (ADR-0018 §D4).

## 5. Relationship graph

Recommendation 6 freezes a **graph-centric architecture**: `RelationshipGraph` is the
single source of truth for requirement relationships. Future analyses — duplicate
detection, dependency analysis, contradiction detection, traceability, impact
analysis — read this one graph. None may build a separate relationship store. The
graph's own validator enforces that every edge references a node already present in
the graph, and that relationship ids are unique — the only computation this milestone
performs is *validation*, never derivation.

## 6. Observations & findings

Recommendation 3 freezes the order: **observation before recommendation**.
`RequirementObservation` is the raw signal layer; a future `EnhancementFinding` is the
interpreted, surfaced layer, and it references the observation it came from rather
than duplicating it. This mirrors the successful two-layer split already proven twice
in this repository — Grounding's Classification → Confidence (ADR-0016) and Quality
Governance's Rule Evaluation → Assessment → Decision (ADR-0017). No recommendation
engine exists in CAP-081A; when one is built, it must derive from observations, never
perform independent analysis.

## 7. Governed policy

`EnhancementPolicy` is immutable, declarative, governed data — no executable logic:

- `EnhancementCapabilitySwitches` — enable/disable each capability (enrichment,
  relationship detection, observation generation; completeness and consistency
  analysis reserved off by default, Recommendation 7).
- `EnrichmentRules` — deterministic bounds for attribute counts and vocabulary.
- `RelationshipRules` — which `RelationshipType` values are enabled, and bound counts.
- `ObservationRules` — which `ObservationCategory` values are enabled, and bound counts.

`EnhancementPolicyBuilder` / `default_enhancement_policy()` assemble the CAP-081A
default at `EnhancementPolicyVersion` 1.0.0. Tuning any rule or switch is a versioned
policy change, never an engine change (Recommendation 4).

## 8. Runtime boundary (dormant, CAP-081A)

`RequirementEnhancementService` exposes exactly one method:

```python
def enhance(
    self,
    engineering_context: EngineeringContext,
    analysis_result: AnalysisResult,
) -> RequirementEnhancementResult:
    ...
```

Abstract in this milestone. The registered `DormantRequirementEnhancementService`
raises `NotImplementedError`. It depends only on the two frozen contracts it consumes
— never an *implementation* class (`EngineeringContextOrchestrator`,
`EngineeringContextBuilder`, `RequirementAnalysisService`). No runtime path calls
`enhance`; runtime behaviour is byte-identical.

## 9. PlatformContext

`PlatformContext` gains two composition-root methods, construction only:

- `create_enhancement_policy() -> EnhancementPolicy`
- `create_requirement_enhancement_service() -> RequirementEnhancementService`

Mirroring `create_quality_policy()` / `create_quality_governance_service()`
(ADR-0017), these are the **only** sanctioned points outside the `enhancement`
package that may construct its objects, enforced by a containment test.

## 10. Execution package (future)

Not introduced in CAP-081A. When runtime activation lands, every enhancement
execution artifact will be a **pure projection** of `RequirementEnhancementResult`,
reproducible from it alone, computing nothing — the same serialization invariant
ADR-0016 §D16 established for Grounding and ADR-0017 §D30/§D31 hardened for Quality
Governance's manifest boundary. The manifest will reference the artifacts by name
only; it will never duplicate `RequirementEnhancementResult`'s content (Recommendation
5, applied from the outset rather than retrofitted).

## 11. Implementation roadmap (non-normative)

1. Deterministic enrichment engine (attributes only, no AI).
2. Deterministic relationship-detection engine (structural/textual matching).
3. Deterministic observation-generation engine (completeness/consistency signals).
4. Runtime activation — wire `enhance` into the pipeline between Analysis and
   Grounding, add the Execution Package projection, golden re-baseline.
5. Recommendation layer, derived strictly from recorded observations
   (Recommendation 3).
6. The Recommendation 7 extension points: semantic relationship detection,
   AI-assisted enrichment, historical requirement intelligence, impact analysis,
   change propagation, architectural dependency analysis, compliance mapping.

Each lands behind the unchanged `enhance` signature and the unchanged
`RequirementEnhancementResult` contract — no architectural change required.

## 12. Terminology

- **Enrichment** — attaching deterministic attributes to one requirement
  (`EnhancedRequirement`).
- **Relationship** — a typed, directed edge between two requirements
  (`RequirementRelationship`), stored only in the canonical `RelationshipGraph`.
- **Observation** — a raw, un-interpreted, deterministic signal
  (`RequirementObservation`) — the layer that must precede any recommendation.
- **Finding** — a surfaced observation (`EnhancementFinding`), by reference, never by
  copy.
- **Requirement Intelligence Enhancement** is a distinct capability from Grounding
  (evidence support), Validation (structural form), CP1 (engineering readiness), and
  Quality Governance (release decision) — a peer, not an extension of any of them.
