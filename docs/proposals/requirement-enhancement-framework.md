# Requirement Intelligence Enhancement Framework — Design Proposal

- **Status:** Accepted (CAP-081A froze the architecture; CAP-081B implemented the first deterministic engine behind it; CAP-081B.1 froze `RequirementEnhancementResult` as the permanent runtime contract; CAP-081C wires the runtime into the live pipeline immediately after Analysis)
- **Capability:** CAP-081 — Requirement Intelligence Enhancement
- **Milestones covered:** CAP-081A (Architecture & Governance Freeze) · CAP-081B (Deterministic Requirement Enhancement Engine — §8a) · CAP-081B.1 (RequirementEnhancementResult Runtime Contract Freeze — §8b) · CAP-081C (Runtime Integration & Execution Package — §8c)
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

## 8. Runtime boundary (frozen at CAP-081A; active since CAP-081C)

`RequirementEnhancementService` exposes exactly one method:

```python
def enhance(
    self,
    engineering_context: EngineeringContext,
    analysis_result: AnalysisResult,
) -> RequirementEnhancementResult:
    ...
```

It depends only on the two frozen contracts it consumes — never an *implementation*
class (`EngineeringContextOrchestrator`, `EngineeringContextBuilder`,
`RequirementAnalysisService`). Abstract at CAP-081A; CAP-081B (§8a) implemented the
method; CAP-081C (§8c) wires the CLI to call it in the live pipeline — the signature
above is unchanged throughout.

## 8a. Deterministic Requirement Enhancement Engine (CAP-081B)

CAP-081A froze the service boundary (§8) dormant. CAP-081B implements the **first
real engine** behind it: `DeterministicRequirementEnhancementEngine`, wrapped by
`DeterministicRequirementEnhancementService` (replacing
`DormantRequirementEnhancementService` as the `PlatformContext` default). No
signature, ownership, or contract change; the engine remains **unwired** from the
execution pipeline, so runtime is byte-identical and the golden baseline is
unchanged.

- **A new governed rule catalogue** (`enhancement/rules/`) — `EnhancementRule`
  (metadata only: a governed mechanism, capability switch, and policy reference; no
  lambda, no embedded threshold), `EnhancementRuleCatalog` (ordering/lookup/
  grouping/enabled-selection only), `EnhancementRuleBuilder` — mirrors
  `QualityRule` / `QualityRuleCatalog` / `QualityRuleBuilder` exactly (ADR-0017
  §D25). Three new, additive version axes (`EnhancementRuleVersion`,
  `EnhancementRuleCatalogVersion`, `EnhancementEngineVersion`) do not touch the five
  CAP-081A froze.
- **Requirement extraction, duplicated rather than coupled.** The engine
  independently recovers the generated-requirement arrays from `AnalysisResult`'s
  strict-JSON body — the same shape Grounding's `MatchingContextBuilder` reads, but
  never that Grounding-owned class. Enhancement mints its own plain-string
  requirement ids.
- **Deterministic mechanisms only.** Enrichment: stable ids, `provenance` and
  `traceability` attributes. Relationships: `DUPLICATES` via exact normalized-text
  equality; `DEPENDS_ON` / `REFINES` / `DERIVED_FROM` via a governed keyword
  co-occurring with another requirement's text embedded verbatim. Observations
  (derived only from enhanced requirements + the graph): isolated, orphan,
  duplicate, disconnected-graph, missing-dependency, relationship-inconsistency
  (cycle). Findings surface only `WARNING`/`CRITICAL` observations, by reference.
  See ADR-0018 §D7 for the complete mechanism-by-mechanism rationale.
- **A validator defect found and fixed (not a redesign).** CAP-081A's
  `RequirementEnhancementResult` validator compared `EnhancedRequirement.observation_ids`
  (plain strings) against a set of typed `RequirementObservationId` objects — never
  equal, so the check silently always failed once populated. Fixed by comparing
  stringified forms; no field or contract changed. See ADR-0018 §D7.
- **One capability honestly reserved.** True structural parent-child detection needs
  a requirement schema field the current flat string arrays don't carry; CAP-081B
  ships the keyword-triggered variant only rather than fabricate an unjustified
  heuristic (Recommendation 6 / Stage 4).

## 8b. RequirementEnhancementResult runtime contract freeze (CAP-081B.1)

CAP-081B implemented the engine. Before any pipeline wiring, serialization,
Execution Package integration, or downstream subsystem depends on it, CAP-081B.1
permanently freezes `RequirementEnhancementResult` as the runtime contract — no
behaviour change, mirroring CAP-077E.1 (`GroundingResult`) and CAP-080B.1.1
(`QualityAssessmentResult`).

- **Semantics.** *The complete deterministic enhancement assessment for exactly one
  Requirement Intelligence execution.* It **is** the runtime contract, the only
  enhancement aggregate, and the canonical enhancement boundary. It is **not** a
  report, Markdown, an execution artifact, a renderer, a serializer, an Execution
  Package object, a graph builder, a metrics calculator, an observation generator, a
  relationship detector, the enhancement engine, a service, a policy, or a builder.
- **Version independence.** `EnhancementResultVersion` versions the runtime-contract
  schema only, independent of `EnhancementFrameworkVersion`, `EnhancementPolicyVersion`,
  `EnhancementRuleVersion`, `EnhancementRuleCatalogVersion`, `EnhancementEngineVersion`,
  `RelationshipVersion`, and `ObservationVersion`. No new axis was introduced — the
  eight that already exist are sufficient.
- **Runtime ownership.** The sole owner of enhanced requirements, the relationship
  graph, observations, findings, metrics, summary, policy identity/version, and
  consumed-input provenance. Nothing upstream or downstream owns any of these.
- **Serialization invariant.** Every future execution artifact is a pure projection,
  reproducible from the result alone. A renderer never calls the engine,
  `PlatformContext`, or a policy, and never recomputes anything.
- **Explainability.** Every enhancement decision is explainable entirely from the
  result's six content fields — no downstream consumer inspects runtime components.
- **Runtime/Execution Package boundary (one-way).** `Engineering Context → Analysis →
  Requirement Enhancement → RequirementEnhancementResult → Execution Package → JSON /
  Markdown / reports`. Formatting and computation never depend on each other.
- **Golden regression boundary.** A future golden dataset compares the result's
  content, never formatting — frozen in advance of the milestone that adds one.

See ADR-0018 §D8 for the complete rationale.

## 8c. Runtime integration & Execution Package (CAP-081C)

CAP-081B.1 froze `RequirementEnhancementResult`. CAP-081C wires the subsystem into
the live pipeline **without any architectural change** (ADR-0018 §D9). The frozen
order becomes permanent:

```
Engineering Context → Analysis → Requirement Enhancement → Grounding
    → Validation → CP1 → Quality Governance → Execution Package
```

- **CLI activation** — `run_requirement_enhancement_phase` obtains the single
  service **only** from `PlatformContext.create_requirement_enhancement_service()`
  and calls `enhance(engineering_context, analysis_result)` immediately after
  Analysis. Pure orchestration glue, mirroring the grounding/validation/CP1/
  governance phases; it modifies neither input, and Grounding continues to consume
  the same original `EngineeringContext`/`AnalysisResult` unchanged.
- **Execution Package integration (additive)** — `ExecutionData` gains one optional
  field, `requirement_enhancement_result`, transported like `grounding_result` /
  `cp1_result` / `quality_governance_result`.
- **`EnhancementSerializer`** (`enhancement/serialization/`) renders `render_json()`
  / `render_report()` / `render_metrics()` as pure projections — confirming, not
  redesigning, the §D8 invariant frozen before it existed.
- **Writer & manifest** — the writer conditionally appends
  `requirement_enhancement_result.json`, `requirement_enhancement_report.md`,
  `requirement_enhancement_metrics.md`; they enter `manifest.generatedArtifacts` via
  the existing checksum mechanism (schema unchanged). Additive manifest keys
  (`requirementEnhancementExecuted`, `requirementEnhancementReport`,
  `requirementEnhancementMetrics`) reference the three artifacts by name only —
  manifest purity (ADR-0017 §D31) is honoured from the first cut, unlike CAP-080D's
  original manifest key that CAP-080D.1 later had to remove.
- **Determinism & golden** — identical inputs ⇒ identical `RequirementEnhancementResult`
  excluding provenance (`started_at`/`completed_at`, and the ids derived from
  `analysis_id`/`execution_id`); golden regression compares canonical content and the
  JSON round-trip, never Markdown or timestamps. Golden dataset advanced to `1.3.0`.

## 9. PlatformContext

`PlatformContext` exposes three composition-root methods, construction only:

- `create_enhancement_policy() -> EnhancementPolicy`
- `create_enhancement_rule_catalog() -> EnhancementRuleCatalog` (CAP-081B)
- `create_requirement_enhancement_service() -> RequirementEnhancementService`

Mirroring `create_quality_policy()` / `create_quality_governance_service()`
(ADR-0017), these are the **only** sanctioned points outside the `enhancement`
package that may construct its objects, enforced by a containment test.

## 10. Execution package

Introduced in CAP-081C (§8c). Every enhancement execution artifact is a **pure
projection** of `RequirementEnhancementResult`, reproducible from it alone, computing
nothing — the same serialization invariant ADR-0016 §D16 established for Grounding
and ADR-0017 §D30/§D31 hardened for Quality Governance's manifest boundary. The
manifest references the artifacts by name only; it never duplicates
`RequirementEnhancementResult`'s content (Recommendation 5, applied from the outset
rather than retrofitted).

## 11. Implementation roadmap (non-normative)

1. ~~Deterministic enrichment engine (attributes only, no AI).~~ **Done (CAP-081B).**
2. ~~Deterministic relationship-detection engine (structural/textual matching).~~ **Done (CAP-081B).**
3. ~~Deterministic observation-generation engine (completeness/consistency signals).~~ **Done (CAP-081B).**
4. ~~Runtime activation — wire `enhance` into the pipeline between Analysis and
   Grounding, add the Execution Package projection, golden re-baseline.~~ **Done (CAP-081C).**
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
