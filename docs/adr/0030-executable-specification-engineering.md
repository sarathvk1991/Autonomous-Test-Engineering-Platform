# ADR-0030 — Executable Specification Engineering Architecture & Governance Freeze

- **Status:** Proposed
- **Date:** 2026-07-21
- **Supersedes:** nothing. **Amends:** ADR-0020 (additive only — inserts a new **Layer 2.5** entry between Stage 4's existing Layer 2 and Layer 3 sections, and a corresponding Stage 5/Stage 9/Stage 10 citation; no existing layer, layer number, dependency rule, or lifecycle stage is renamed, renumbered, redefined, or reordered).
- **Governing design:** `docs/proposals/executable-specification-engineering.md`
- **Depends on:** ADR-0018 (Requirement Enhancement Framework — source of `RequirementEnhancementResult`, the primary decomposition input), ADR-0016 (Evidence Grounding & Traceability — source of `GroundingResult`, the evidence gate this capability must respect before turning a requirement into a scenario), `docs/architecture/ai-response-validation.md` (source of `ValidationResult`, the well-formedness gate), ADR-0019 (Recommendation Framework — source of `RecommendationResult`, the terminal Layer 1 judgement this capability reads for prioritization), ADR-0028 and ADR-0029 (Learning Constitution & Learning Framework — source of `LearningResult`, the **sole** sanctioned Layer 2 → Layer 2.5 bridge this ADR consumes, per ADR-0028 Recommendation 19), and ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — the layer/dependency/lifecycle constitution this ADR extends additively, never contradicts). Informed by ADR-0017 (Quality Governance — the terminal release authority whose verdict is already transitively represented inside `RecommendationResult`, and therefore not separately consumed; see D2) and ADR-0014 (Prompt Governance Subsystem — the closest existing precedent for a governed, versioned, technology-rendering-adjacent subsystem, cited for its registry/versioning discipline, not its domain).
- **Runtime status:** Not applicable. This is a **pure Architecture & Governance Freeze** — CAP-087A. No code is written, no Python package is created, no service exists, no `PlatformContext` method is added, no policy object is instantiated, no runtime behaviour changes, no version constant changes, and no existing pipeline stage is touched. Every model, contract, and collaborator named in this document is a **documented, dormant specification**, not an implementation — mirroring the posture CAP-086A established for Learning before CAP-086B ever wrote a line of engine code. This document is the governance baseline CAP-087B (a future, separate implementation milestone) must build against without deviation.

## Scope note

This ADR does two things at once, exactly as CAP-086A/A.1/A.2 did together for Learning: it (1) freezes a **subsystem architecture** — canonical models, capability decomposition, policy, and runtime boundary for Executable Specification Engineering — and (2) resolves a **placement gap** in the platform's own constitution (ADR-0020), which — like every constitutional document before it — was written before this capability was conceived and therefore never anticipated it. Stage 0 below documents that gap precisely, and D1 resolves it with the smallest possible additive change: a new layer entry, not a redesign.

---

## Stage 0 — Repository assessment

Before writing this ADR, the following were reviewed in full:

- **ADR-0018 (Requirement Enhancement), ADR-0016 (Grounding), `docs/architecture/ai-response-validation.md` (Validation), ADR-0019 (Recommendation)** — all four confirmed **Accepted, live, Layer 1** capabilities. Each produces a real, frozen, independently versioned runtime contract (`RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `RecommendationResult`) already integrated into the live single-execution pipeline. None owns, or claims to own, any specification-production responsibility — confirmed by direct review of each ADR's Ownership section.
- **ADR-0028 (Learning Constitution), ADR-0029 (Learning Framework)** — confirmed **Accepted, live**. `LearningResult` is real, certified, and — per ADR-0028 Stage 12/16 and Recommendation 19 — constitutionally frozen as **"the sole sanctioned Layer 2 → Layer 3 entry point wherever a Layer 2 conclusion more refined than a single Derived Knowledge or Organizational Knowledge object is required."** This ADR reads that rule literally: wherever a *later* capability needs organizational, cross-execution knowledge, it reaches Learning and nothing beneath it.
- **ADR-0020 (Platform Evolution Roadmap)** — confirmed **Proposed**, the platform's architectural constitution. Its Stage 4 layer catalogue (Layer 1 Requirement Intelligence → Layer 2 Continuous Learning → Layer 3 Feature Engineering → Layer 4 Prediction & Insights → Layer 5 Optimization → Layer 6 Autonomous Engineering → Layer 7 Organizational Intelligence), Stage 5 dependency rules (upward-only, never-skip), Stage 8 capability lifecycle, and Stage 9 placement decision tree were reviewed line by line against this capability's own shape.
- **Repository-wide search** for `SpecificationEngineeringResult`, `BusinessFeature`, `BusinessScenario`, `SpecificationPlan`, `specification_engineering`, `ExecutableSpecification`, `Gherkin`, `Cucumber` across `requirement_intelligence/`, `docs/adr/`, and `docs/proposals/`: **zero hits**. No package, no module, no class, no test, no proposal document, no prior architectural mention of this capability exists anywhere in the repository prior to this milestone.
- **`docs/governance/platform-capability-matrix.md` §3.1** — confirmed the next unused Capability ID in the `CAP-060…` Downstream/Future block is `CAP-087`, consistent with the capability number this ADR governs.

**Gap found (not an inconsistency — a genuine, expected placement gap):** ADR-0020 Stage 9's placement decision tree asks, in strict order, "reasons over one execution?" (Layer 1), "reasons over many executions?" (Layer 2), "produces reusable numerical representations?" (Layer 3), "estimates future outcomes?" (Layer 4), "chooses the best plan?" (Layer 5), "performs engineering work?" (Layer 6), "reasons across organizations?" (Layer 7). Executable Specification Engineering answers **none** of these cleanly:

- It is not Layer 1: Layer 1 capabilities may never consume a Layer 2 result at all (ADR-0020 Stage 5's upward-only rule forbids a lower layer depending on a higher one), and this capability's own brief requires it to consume `LearningResult` for organizational scenario enrichment.
- It is not Layer 3: Layer 3's `FeatureResult` is a **numerical** representation (ADR-0020 §Layer 3: "reusable, numerical feature vectors"); this capability produces a qualitative, structured specification graph, and computes no number that estimates, scores, or predicts anything.
- It is not Layer 4/5: it estimates nothing and chooses nothing.
- It is not Layer 6: Layer 6 ("Autonomous Engineering") consumes Layer 5's `OptimizationResult` — a contract that does not exist and is not consumed here. Some Layer 6 *examples* ("Automation generation," "Story generation") sound adjacent to this capability's output, but Layer 6's own boundary requires it to act on a plan Layer 5 already selected; this capability acts on nothing — it only produces a specification for a human or a downstream tool to act on later.
- It is not Layer 7: it reasons about one project's one execution, never a portfolio.

No existing ADR is contradicted. This is exactly the situation ADR-0020 Stage 3 itself anticipates and names in advance: *"A capability that seems to span two layers has not yet been decomposed correctly."* Here the correct reading is the reverse of that warning's usual application — the capability is already correctly decomposed (it does exactly one thing: turn judged requirement output into a technology-independent specification), but the **seven-question decision tree was written for a different vertical** (the numerical Feature → Prediction → Optimization → Autonomy → Organizational Intelligence analytics pipeline) and never anticipated a *qualitative production* capability sitting beside it. Widening any one of Layers 3–7's own frozen definitions to fit this capability in would violate the explicit instruction governing this milestone: no existing architecture may be changed.

> No architectural weakness or inconsistency found. Proceeding to close the placement gap with the smallest possible additive extension to ADR-0020 (D1), and to freeze CAP-087A's own subsystem architecture (D2 onward). No redesign performed.

---

## Decision

Introduce a new, governed, currently-empty subsystem package — **`requirement_intelligence/specification_engineering/`** (reserved; not created by this milestone) — that will own the transformation of one execution's judged Requirement Intelligence output, enriched by organizational Learning, into a renderer-agnostic **Specification Model**. It:

1. Is placed at a new architectural position, **Layer 2.5** (D1), inserted additively into ADR-0020 between Layer 2 and Layer 3, without renumbering, redefining, or reordering any existing layer.
2. Consumes exactly five already-frozen, already-versioned runtime contracts — `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `RecommendationResult` (same-execution Layer 1 peers) and `LearningResult` (the sole sanctioned Layer 2 bridge) — and nothing else (D2).
3. Introduces canonical, immutable domain models — `SpecificationPlan`, `BusinessFeature`, `BusinessScenario`, `BusinessRule`, `AcceptanceCriterion`, `ScenarioStep`, `ScenarioTag`, `ScenarioOutline`, `Traceability`, `SpecificationMetrics`, `ValidationSummary`, `RendererMetadata`, and the aggregate runtime contract `SpecificationEngineeringResult` — following the `Schema` conventions and typed-identity pattern of ADR-0015 through ADR-0029 (full field-by-field documentation in the governing design, §5).
4. Freezes a ten-collaborator internal decomposition and its execution order (D9/D10), including a permanently isolated **Renderer** stage that is the platform's only sanctioned path from the canonical model to any technology-specific output (D11).
5. Fixes the single runtime boundary — `SpecificationEngineeringService.build(requirement_enhancement_result, grounding_result, validation_result, recommendation_result, learning_result) -> SpecificationEngineeringResult` — as an **abstract, dormant contract**. No `PlatformContext` method is added by this milestone; the composition-root points are reserved (D7).

**CAP-087A establishes the architecture only.** No requirement is decomposed, no scenario is discovered, no feature file is rendered, no historical dataset or Learning object is touched at runtime, and nothing is wired into a pipeline. Runtime behaviour is byte-identical; the golden baseline is unchanged; the Architecture Version is unchanged.

The full canonical model, internal decomposition, and strategy detail are in `docs/proposals/executable-specification-engineering.md`. Governance mechanics (versioning, extension, deprecation, review checklist, certification) are in `docs/governance/executable-specification-engineering-governance.md`.

---

## D1 — Layer placement: Layer 2.5, and why it is additive, not a redesign

Executable Specification Engineering is placed at **Layer 2.5** — a new architectural position sitting structurally between Layer 2 (Continuous Learning) and Layer 3 (Feature Engineering) in ADR-0020's stack, without becoming, replacing, or renumbering either.

**Why higher than Layer 2.** ADR-0020 Stage 5 forbids a lower-numbered layer from depending on a higher-numbered one. This capability must consume `LearningResult` (Layer 2's own terminal output), so it cannot itself be numbered ≤ 2.

**Why it does not become Layer 3.** Layer 3 is permanently, frozenly defined as numerical Feature Engineering (`FeatureResult`, ADR-0020 §Layer 3). Redefining Layer 3 to also mean "qualitative specification production" would be exactly the kind of existing-architecture change this milestone is forbidden from making. A new, non-conflicting position is therefore required.

**Why a fractional layer number, not a renumbering of Layers 3–7.** Every existing ADR (ADR-0020 itself, and every ADR that cites "Layer 3," e.g. ADR-0028 Stage 12/16/D1) refers to Feature Engineering as Layer 3 by that literal number. Shifting Layers 3–7 to 4–8 to make room would require editing every one of those citations — a change to existing, frozen architecture, forbidden by this milestone's brief. A fractional insertion point (`2.5`) is the smallest possible additive change: it names a real position in the dependency order (above Layer 2, below Layer 3) without touching a single existing citation.

**Why this is not "spanning two layers" (the anti-pattern ADR-0020 Stage 3 warns against).** Stage 3's warning is about a *single* capability trying to answer more than one of Stage 9's seven placement questions — a sign it has not been decomposed correctly. Executable Specification Engineering answers a genuinely **eighth** question Stage 9's tree never asked: *does this capability transform judged execution output into a technology-independent, executable specification?* It is a single, coherent responsibility, cleanly separable from every other layer's own responsibility (D5) — it simply required a question ADR-0020 had no occasion to write down. D2 below states the precise runtime boundary that keeps this position honest.

**Dependency direction, restated for Layer 2.5:** Layer 2.5 may consume Layer 1 and Layer 2 (both strictly lower-numbered). Nothing above Layer 2.5 exists yet; if a future Layer 3+ capability ever needs a specification-tier conclusion, it must reach Layer 2.5 through `SpecificationEngineeringResult` alone — never past it into Layer 1 or Layer 2 directly — the identical no-skip discipline ADR-0020 Stage 5 already freezes for every other layer boundary.

## D2 — Runtime boundary: the five consumed contracts, and why not the other three

`SpecificationEngineeringService.build` consumes exactly:

| Contract | Layer | Why consumed |
|---|---|---|
| `RequirementEnhancementResult` | 1 | The primary decomposition input — the enriched, structured requirement content `RequirementDecomposer` turns into candidate `BusinessFeature`s (D9). Without it there is nothing to decompose. |
| `GroundingResult` | 1 | The evidence gate. A requirement with no supporting evidence must not silently become an acceptance criterion or a scenario — `SpecificationPlanner` and `AcceptanceCriteriaNormalizer` read grounding confidence to decide what is safe to specify (mirrors CP1's own "is there enough to act on?" gating philosophy, ADR-0011, applied to specification instead of engineering readiness). |
| `ValidationResult` | 1 | The well-formedness gate. `SpecificationPlanner` must know the response passed structural validation before treating any of its content as reliable decomposition input — the same precondition CP1 and Quality Governance already require of everything downstream of Validation (ADR-0011 §D5). |
| `RecommendationResult` | 1 | The terminal, most-informed Layer 1 judgement — already transitively reflects Analysis, Enhancement, Grounding, Validation, CP1, and Quality Governance (ADR-0019). `AcceptanceCriteriaNormalizer` and `BusinessRuleExtractor` read its severity/priority signal to prioritize criteria and rules **without** separately consuming CP1's or Quality Governance's own results directly (see below). |
| `LearningResult` | 2 | The **sole** sanctioned Layer 2 bridge (ADR-0028 Recommendation 19). `ScenarioDiscovery` reads institutionalized organizational Learning to enrich scenario derivation (D12) — e.g. a Learning object recording that a certain requirement shape has historically needed a Negative Flow scenario. |

**Deliberately not consumed:**

- **`ContinuousImprovementResult`, `KnowledgeGraphResult`, `OrganizationalMemoryResult`** — all three sit strictly beneath `LearningResult` in the Knowledge Promotion Chain (ADR-0028 Stage 5). Reaching past Learning into any of them directly would violate the no-skip discipline ADR-0020 Stage 5 freezes and ADR-0028 Recommendation 19 states explicitly for exactly this situation. Learning already aggregates and validates everything they contain; consuming them separately would duplicate ownership and risk two competing interpretations of the same organizational fact.
- **`QualityGovernanceResult`, `CP1Result`** — both sit between Validation and Recommendation in the live Layer 1 pipeline (ADR-0020 §Layer 1); their verdicts are already folded into `RecommendationResult` by construction (Recommendation is Layer 1's terminal fan-in, ADR-0019). Consuming them a second time, directly, would let Specification Engineering re-derive a judgement Recommendation already made — the identical duplicate-ownership risk ADR-0025 Recommendation 15 forbids within Layer 2, applied here within Layer 1's own already-settled fan-in.
- **The Historical Dataset, any Layer 1 raw execution record, or a prior `SpecificationEngineeringResult`** — forbidden for the same reason every other capability in this repository forbids them: they are not this capability's rightful lower-layer input, and self-consumption would violate the append-only/no-self-evidence discipline ADR-0028 Recommendation 20 already freezes one tier below.

## D3 — `SpecificationEngineeringResult` is a new, distinct kind of truth: Specification Truth

`SpecificationEngineeringResult` is not Runtime Truth, not Historical Truth, not Derived Knowledge, not Organizational Knowledge, and not Learned Knowledge (ADR-0021 §Stage 3, ADR-0028 Stage 2). It is the platform's first instance of a fifth, distinct kind of output this ADR names **Specification Truth**: a technology-independent, structured statement of *what the system under specification must do*, derived exclusively from already-judged execution output and organizational Learning, produced for consumption by rendering tools and human reviewers — never fed back as evidence into any Truth Hierarchy tier beneath it. A `SpecificationEngineeringResult` is never written back into `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `RecommendationResult`, `LearningResult`, or any tier those five in turn depend on (mirrors ADR-0028 Stage 4's "Learning never mutates Organizational Knowledge," lifted to this new tier).

## D4 — The canonical output must not be Gherkin, and why

The **canonical** output of this capability is the Specification Model (`SpecificationEngineeringResult` and the domain models it aggregates) — never Gherkin text, never any other technology-specific syntax. This is a hard architectural boundary, not a style preference:

- **Technology lock-in.** If the canonical truth were Gherkin, every future renderer (Playwright, Selenium, API Test Specifications, TestRail, Living Documentation) would have to either re-parse Gherkin (lossy, fragile) or bypass the canonical model entirely and re-derive its own interpretation of the judged requirements (duplicated ownership, the same risk D2 already forbids for consumed contracts).
- **Testability of the model itself.** A structured `BusinessScenario` with typed `ScenarioStep`s can be validated, diffed, and traced without ever invoking a text renderer; a Gherkin string cannot be inspected that way without re-parsing it.
- **Renderer isolation (D11).** Keeping the canonical model renderer-agnostic is what makes "add a new renderer without modifying Specification Engineering" (this milestone's own success criterion) actually true rather than aspirational.

## D5 — Ownership: SHALL and SHALL NOT

**Executable Specification Engineering SHALL:**

Specification Planning · Requirement Decomposition · Feature Identification · Business Rule Extraction · Acceptance Criteria Normalization · Scenario Discovery · Scenario Classification · Traceability Mapping · Canonical Specification Generation · Renderer Preparation · Specification Validation · Specification Packaging.

**Executable Specification Engineering SHALL NOT:**

Generate Selenium code · Generate Playwright code · Generate Step Definitions · Generate Java (or any executable target-language source) · Generate Test Data · Execute Tests · Call external systems · Modify Organizational Memory · Modify Learning.

Every SHALL is owned by exactly one of the ten collaborators in D9. Every SHALL NOT is a permanent, non-negotiable boundary: this capability's own Renderer (D11) projects the canonical model into a **specification-level artifact** (a `.feature` file's plain-language scenario text) — it never emits a programming-language step-definition body, a test-data fixture, or an execution trigger. A future automation-generation capability, if it is ever built, is a **separate, downstream capability** that would consume `SpecificationEngineeringResult` the way this one consumes `RecommendationResult` — never a responsibility this capability absorbs.

## D6 — Policy ownership: capability switches and thresholds, never algorithms

`SpecificationEngineeringPolicy` governs planning, decomposition, extraction, normalization, discovery, classification, validation, rendering, and packaging through capability switches, and bounds every collaborator's deterministic behaviour through governed thresholds (`minimum_grounding_confidence_for_planning`, `minimum_scenarios_per_feature`, `minimum_acceptance_criteria_per_scenario`, `maximum_scenario_category_gap` — see the governing design §7) — data only, no executable logic, mirroring `LearningPolicy` (ADR-0029 §D6) and every governed policy before it. Tuning specification behaviour is a versioned policy change, never a collaborator code change.

## D7 — PlatformContext: the sole future composition root (reserved)

When a future implementation milestone builds this subsystem, `PlatformContext` will gain exactly two composition-root methods — `create_specification_engineering_policy()` and `create_specification_engineering_service()` — the only sanctioned points outside the `specification_engineering` package permitted to construct its governed objects, enforced by a containment test (mirrors ADR-0022 §D6, ADR-0023 §D6, ADR-0027 §D7, ADR-0029 §D7). **This milestone adds neither method.** They are named here only so a future implementation milestone has no naming decision left to make.

## D8 — Future replaceability

A future deterministic, rule-based, ML, LLM, or hybrid Specification Engineering engine (CAP-087B onward, reserved) must implement the identical `build(RequirementEnhancementResult, GroundingResult, ValidationResult, RecommendationResult, LearningResult) -> SpecificationEngineeringResult` contract without `SpecificationEngineeringResult` or `SpecificationEngineeringPolicy` changing shape (mirrors ADR-0029 §D8). `SpecificationEngineeringCapabilitySwitches.enable_deterministic_engine` / `enable_ml_engine` / `enable_llm_engine` remain reserved off until their respective future engine exists.

## D9 — Internal capability decomposition (frozen)

```
SpecificationPlanner
        ↓
RequirementDecomposer
        ↓
BusinessRuleExtractor
        ↓
AcceptanceCriteriaNormalizer
        ↓
ScenarioDiscovery
        ↓
ScenarioClassifier
        ↓
CanonicalSpecificationBuilder
        ↓
SpecificationValidator
        ↓
Renderer
        ↓
SpecificationPackager
```

Each collaborator owns exactly one responsibility. No collaborator computes another's responsibility — `RequirementDecomposer` never extracts business rules; `ScenarioDiscovery` never classifies; `Renderer` never validates. A future ML/LLM engine may replace any single collaborator without changing the public `build` contract or any sibling collaborator, the identical reuse guarantee ADR-0023 §D10, ADR-0027 §D9, and ADR-0029 §D9 already freeze for their own decompositions. Full purpose/inputs/outputs/responsibilities/constraints/policies for every collaborator are documented in the governing design §6.

## D10 — Collaborator ownership and layering (frozen)

| Collaborator | Owns only | Produces | Never |
|---|---|---|---|
| `SpecificationPlanner` | scope determination from the five consumed contracts | `SpecificationPlan` | decomposes, extracts rules, discovers scenarios, validates, renders |
| `RequirementDecomposer` | feature identification/grouping | `BusinessFeature` (draft) | extracts rules, normalizes criteria, discovers scenarios |
| `BusinessRuleExtractor` | rule identification, classification, prioritization | `BusinessRule` | validates rules, discovers scenarios, normalizes criteria |
| `AcceptanceCriteriaNormalizer` | normalization, dedup, conflict resolution, prioritization | `AcceptanceCriterion` | discovers scenarios, extracts rules |
| `ScenarioDiscovery` | scenario derivation across the governed category taxonomy | `BusinessScenario` (draft), `ScenarioStep`, `ScenarioOutline` | classifies, validates, renders |
| `ScenarioClassifier` | category + tag assignment | classified `BusinessScenario`, `ScenarioTag` | discovers new scenarios, rewrites steps |
| `CanonicalSpecificationBuilder` | cross-linking, `Traceability` construction | linked canonical Specification graph, `Traceability` | computes new content of any kind |
| `SpecificationValidator` | structural/completeness validation of the canonical graph | `ValidationSummary` | mutates the graph, renders |
| `Renderer` | technology-specific projection | rendered artifact content, `RendererMetadata` | computes/derives new specification content |
| `SpecificationPackager` | result assembly, metrics tally, execution-package projection | `SpecificationEngineeringResult`, `SpecificationMetrics` | any upstream computation |

`SpecificationPackager` never computes knowledge — it tallies already-recorded rows into `SpecificationMetrics` and assembles already-finished collaborator output into `SpecificationEngineeringResult`, exactly the "presentation/assembly only" discipline ADR-0022's, ADR-0023's, ADR-0027's, and ADR-0029's own summary/metrics/result builders already apply (ADR-0029 §D22).

## D11 — Renderer architecture and isolation (frozen)

```
Canonical Specification
        ↓
   Renderer
        ↓
   Feature Files (Cucumber, first target)
```

**Renderer responsibilities.** A Renderer is a pure projection: it reads an already-validated canonical Specification graph and emits one technology-specific artifact format. It performs no decomposition, no rule extraction, no scenario discovery, no classification, and no validation — every fact it emits must already exist, unaltered, on the canonical model it was given.

**Why renderers are isolated.** Isolating rendering behind a single collaborator boundary (D9/D10) is what makes the platform's technology-agnosticism (Business Vision, above) structurally true rather than a naming convention. A renderer bug can never corrupt the canonical Specification (it never writes to it), and a canonical-model change never requires touching more than one renderer at a time, because no renderer depends on another.

**How additional renderers are added without modifying Specification Engineering.** Each renderer implements one identical, frozen contract — `render(SpecificationEngineeringResult) -> RenderedArtifact` — and is registered in a governed `RendererRegistry` (explicit registration, OPEN → SEALED, no reflection, deterministic ordering — mirrors `PromptRegistry`/`ValidationRegistry`/`CP1CriterionRegistry`, ADR-0014/ADR-0011). Adding Playwright, Selenium, API Test Specifications, TestRail, or Living Documentation support is therefore **purely additive**: a new module implementing the frozen contract, registered once, with zero modification to `SpecificationPlanner` through `SpecificationValidator`, and zero change to any canonical domain model. This is the direct architectural realization of this ADR's own Success Criteria (below): *"Require zero architectural redesign before CAP-087B implementation."*

## D12 — Scenario Engineering Strategy (summary; full detail in governing design §8)

`ScenarioDiscovery` derives candidate scenarios deterministically, per `BusinessFeature`/`BusinessRule`/`AcceptanceCriterion` combination, against a governed, closed taxonomy of fifteen categories: Happy Path, Alternate Flow, Negative Flow, Exception Flow, Boundary Conditions, Security, Authorization, Authentication, Data Validation, Integration Failure, Recovery, Business Rule Validation, State Transition, Concurrency, Regression. Each category's derivation trigger is a named, deterministic condition over the consumed contracts (e.g. a `BusinessRule` classified `AUTHORIZATION` deterministically triggers an Authorization-category scenario proposal) — never a generative or probabilistic invention. `LearningResult` enriches this step only additively: an institutionalized Learning object may **raise** the number of proposed categories for a matching requirement shape (e.g. "requirements of this kind have historically also needed a Negative Flow scenario"), but may never **suppress** a category the deterministic taxonomy already triggers, and never invents a scenario with no requirement/rule/criterion reference of its own (mirrors ADR-0028 Stage 6's "organizational usefulness" and D15's "institutionalizes, never invents," lifted from Learning's own validation discipline to scenario derivation).

## D13 — Business Rule Strategy (summary; full detail in governing design §9)

Rule Identification is deterministic (requirement/enhancement content bearing constraint or conditional language, grounded by `GroundingResult`). Rule Classification uses a governed, closed enum (`CONSTRAINT`, `CALCULATION`, `VALIDATION`, `AUTHORIZATION`, `WORKFLOW`, `DATA_INTEGRITY`). Rule Prioritization is derived, never invented, from `RecommendationResult` severity and `GroundingResult` confidence. Rule Versioning follows an independent version axis (D19/governing design §10). Rule Traceability requires at least one source requirement reference per rule (mirrors the "at least one reference" discipline ADR-0019 §D7 first froze). Rule Validation is `SpecificationValidator`'s responsibility alone, never `BusinessRuleExtractor`'s own (D10).

## D14 — Acceptance Criteria Strategy (summary; full detail in governing design §10)

Normalization is a deterministic textual transform (trim, case-fold, canonical phrasing template) — never a semantic rewrite that could change meaning. Deduplication is byte-equality on the normalized form, the identical mechanism `REASONING-0002`/`CONTENT-0002` already freeze byte-exact for their own domains (ADR-0007/ADR-0008) — never semantic or embedding-based at this milestone. Conflict Resolution is governed precedence (higher `RecommendationResult` severity wins); an unresolved tie is retained with a recorded conflict flag for human review, never silently dropped or auto-resolved by inference. Prioritization is derived from Grounding confidence and Recommendation severity. Traceability requires exactly one source requirement reference per criterion.

## D15 — Complete explainability chain (frozen)

Every `BusinessScenario` must reconstruct this complete chain:

```
Business Scenario
        ↓
Acceptance Criterion  /  Business Rule
        ↓
Business Feature
        ↓
Requirement (RequirementEnhancementResult)
        ↓
Grounding Evidence (GroundingResult)  +  Recommendation (RecommendationResult)  +  Learning (LearningResult, optional enrichment)
        ↓
Validation (ValidationResult)
        ↓
Runtime Truth (the originating execution)
```

The final three hops (`RequirementEnhancementResult`/`GroundingResult`/`ValidationResult`/`RecommendationResult` → the originating execution) are already frozen by their own governing ADRs' explainability sections; this capability's chain composes with them through the referenced execution id, rather than duplicating them (mirrors ADR-0029 §D14's identical composition pattern one tier below). No `BusinessScenario` may exist unless this complete chain can be reconstructed from `SpecificationEngineeringResult` alone (Recommendation 8, below).

## D16 — Deterministic execution pipeline (frozen)

Freeze the permanent execution order — identical to D9, restated as a pipeline guarantee:

```
Plan
  ↓
Decompose requirements
  ↓
Extract business rules
  ↓
Normalize acceptance criteria
  ↓
Discover scenarios
  ↓
Classify scenarios
  ↓
Build canonical specification
  ↓
Validate specification
  ↓
Render
  ↓
Package result
```

Future engines may change algorithms within any single stage. They must preserve this execution pipeline — no stage is skipped, and no stage is reordered (mirrors ADR-0020 §Stage 8, ADR-0029 §D16). Validation precedes rendering because a Renderer must only ever project an already-structurally-sound canonical graph — rendering an invalid specification would silently manufacture a plausible-looking feature file from broken input, exactly the failure mode ADR-0028's own validation-before-generation correction (ADR-0029 §D9's Stage 0 Constitutional Correction) already exists to prevent one tier below.

## D17 — Result ownership and future replaceability (frozen)

`SpecificationPackager` is permanently the only owner of `SpecificationEngineeringResult(...)` construction anywhere in a future engine. No other collaborator — not `SpecificationPlanner`, not `RequirementDecomposer`, not `BusinessRuleExtractor`, not `AcceptanceCriteriaNormalizer`, not `ScenarioDiscovery`, not `ScenarioClassifier`, not `CanonicalSpecificationBuilder`, not `SpecificationValidator`, not `Renderer` — may construct it. This mirrors Organizational Memory's, Knowledge Graph's, and Learning's own frozen invariant (ADR-0027 §D16, ADR-0023 §D10, ADR-0029 §D17). Every collaborator named in D9 may later have deterministic, rule-based, ML, LLM, or hybrid implementations; `SpecificationEngineeringService`, `SpecificationEngineeringResult`, and `PlatformContext` remain unchanged regardless of which collaborator a future milestone implements first or replaces later (Recommendation 14, below).

## D18 — Execution Package design (reserved; architecture only)

A future implementation milestone will emit, into the execution package:

- `specification_engineering_result.json` — the complete `SpecificationEngineeringResult`, mirroring every other `*_result.json` in the platform.
- `specification_engineering_report.md` — human-readable narrative, mirroring `validation_report.md`/`cp1_report.md`.
- `specification_engineering_metrics.md` — `SpecificationMetrics` rendered, mirroring `baseline_metrics_builder.py`'s presentation-only discipline.
- `generated_feature_files/` — one subdirectory per registered `RendererType` (D11), containing that renderer's projected output; empty until a renderer is registered and enabled.
- `traceability_matrix.md` — `Traceability` rendered as a human-navigable table, composing with D15's chain.
- `gherkin_validation_report.md` — `ValidationSummary` rendered. (Named for the first renderer target per the platform's own naming convention; its content is sourced from `SpecificationValidator`'s canonical-graph validation, never from renderer-specific syntax checking — the name is reserved, not a scope commitment to Gherkin-only validation.)

No implementation is designed here — see the governing design §11 and the governance document's Execution Package Governance section for the full artifact contract this future milestone must satisfy without redesign.

## D19 — Versioning strategy (frozen)

Independent version axes — `SpecificationEngineeringFrameworkVersion`, `SpecificationEngineeringPolicyVersion`, `SpecificationPlanVersion` (reserved), `BusinessScenarioVersion` (reserved), `RendererMetadataVersion`, `SpecificationEngineeringResultVersion` — each evolves without forcing the others to change (mirrors Recommendation 13 of ADR-0028, ADR-0022/ADR-0023/ADR-0027/ADR-0029 precedent). Full governance detail in `docs/governance/executable-specification-engineering-governance.md` §Versioning Strategy.

## D20 — Governance summary

Architecture Principles, Capability Boundaries, Ownership, Runtime Contract Governance, Policy Governance, Backward Compatibility, Extension Strategy, Deprecation Strategy, the Architecture Review Checklist, and the Architecture Certification Report are frozen in the dedicated governance document, `docs/governance/executable-specification-engineering-governance.md`, following the same living-document pattern as the Architecture Freeze Index and the Platform Capability Matrix.

---

## Recommendations (permanent)

1. **Executable Specification Engineering owns no Runtime Truth, Historical Truth, Derived Knowledge, Organizational Knowledge, or Learned Knowledge.** It consumes the last two only through their own frozen runtime contracts (D2).
2. **It never mutates a consumed contract.** `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `RecommendationResult`, and `LearningResult` are read-only inputs, always (D2, D5 SHALL NOT).
3. **It is the sole producer of Specification Truth** — the fifth, distinct kind of platform output this ADR names (D3).
4. **Its canonical output is never Gherkin, or any other technology syntax.** The canonical Specification Model is the only truth; every rendering is a projection (D4, D11).
5. **Renderers never feed back into the canonical model.** A renderer is a leaf; nothing downstream of it is consumed by anything upstream (D11).
6. **Adding a renderer is additive only.** No existing collaborator, model, or contract changes when a new `RendererType` is registered (D11).
7. **Scenario derivation is deterministic and taxonomy-bound.** No scenario is proposed without a named, deterministic trigger over a consumed contract (D12).
8. **Organizational Learning enriches; it never invents or suppresses.** `LearningResult` may add scenario coverage the deterministic taxonomy would otherwise miss; it may never remove taxonomy-triggered coverage or manufacture a scenario with no requirement reference (D12).
9. **Every scenario is explainable end to end.** The complete chain from `BusinessScenario` to the originating execution's Runtime Truth must be reconstructable from `SpecificationEngineeringResult` alone (D15).
10. **Validation precedes rendering, permanently.** No canonical graph is rendered before `SpecificationValidator` has run over it (D16).
11. **`SpecificationPackager` is the sole constructor of `SpecificationEngineeringResult`.** No other collaborator constructs it (D17).
12. **This capability never generates executable test code, step definitions, or test data.** These are permanently out of scope (D5 SHALL NOT); a future automation-generation capability, if built, is a separate, downstream consumer.
13. **This capability never executes tests or calls external systems.** It produces specifications only (D5 SHALL NOT).
14. **Future engines are replaceable per collaborator, without changing `SpecificationEngineeringResult`'s shape** (D8, D17).
15. **Policy is data, never algorithm.** `SpecificationEngineeringPolicy` contains no executable logic (D6).
16. **`PlatformContext` is the sole future composition root**, once a future milestone implements this subsystem (D7).
17. **Version axes evolve independently** (D19).
18. **Layer 2.5 consumes Layer 1 and Layer 2 only** — never a future Layer 3+ contract, and it never reaches past `LearningResult` into Continuous Improvement, Knowledge Graph, or Organizational Memory directly (D1, D2).
19. **A future Layer 3+ capability that needs a specification-tier conclusion must reach it through `SpecificationEngineeringResult` alone** — the same no-skip discipline this ADR itself relies on one tier below (D1).
20. **No architecture in this ADR may be treated as implemented until a future ADR (CAP-087B or later) freezes a runtime contract certification against real, tested code** — mirroring every capability's own required lifecycle (ADR-0020 Stage 8).

---

## Final Constitutional Review

1. **Is Executable Specification Engineering permanently defined?** Yes — Decision, D3: the production of technology-independent Specification Truth from judged Layer 1 output and organizational Learning.
2. **Is its layer placement resolved without changing existing architecture?** Yes — D1: a new, additive Layer 2.5, no existing layer renumbered or redefined.
3. **Is the runtime boundary frozen and every dependency justified?** Yes — D2: exactly five consumed contracts, each justified; three Layer 2 peers and two Layer 1 peers explicitly and permanently excluded.
4. **Is the canonical output renderer-agnostic?** Yes — D4: the Specification Model, never Gherkin or any other syntax.
5. **Is the internal decomposition frozen?** Yes — D9/D10: ten collaborators, each with exactly one owned responsibility.
6. **Is renderer isolation and extensibility real, not aspirational?** Yes — D11: one frozen `render` contract, governed registry, zero upstream modification required to add a renderer.
7. **Is the scenario engineering strategy deterministic and taxonomy-bound?** Yes — D12: fifteen governed categories, deterministic triggers, Learning as additive enrichment only.
8. **Is explainability complete end to end?** Yes — D15: every scenario traces to Runtime Truth through five already-frozen chains.
9. **Is the execution pipeline order frozen?** Yes — D16: ten stages, no skip, no reorder.
10. **Is result construction exclusively owned?** Yes — D17: `SpecificationPackager` alone.
11. **Is the Execution Package designed without being implemented?** Yes — D18: six named artifacts, no code.
12. **Does this introduce zero runtime behaviour?** Confirmed: no Python file is touched by this milestone; the repository remains byte-identical outside the documentation files this ADR and its companions add.
13. **Is the repository constitutionally ready for CAP-087B?** Yes. A future deterministic-engine milestone may cite this ADR directly for every canonical model, collaborator boundary, pipeline order, and governance rule — without re-deriving any of them — exactly as CAP-086B was able to build directly against CAP-086A/A.1/A.2 without redesign.

---

## Ownership, scope, and governance

- **Owns:** the definition and placement of Executable Specification Engineering (D1–D3), the SHALL/SHALL NOT boundary (D5), the runtime boundary and its five justified dependencies (D2), every canonical domain model's existence and purpose (full detail: governing design §5), the ten-collaborator decomposition and its ownership table (D9/D10), the renderer architecture and isolation guarantee (D11), the scenario/business-rule/acceptance-criteria strategies (D12–D14), the explainability chain (D15), the deterministic pipeline order (D16), result-construction ownership (D17), and the Execution Package design (D18).
- **Does not own:** any Layer 1 capability's own architecture, engine, policy, or runtime contract (`RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `RecommendationResult` remain ADR-0018's, ADR-0016's, the Validation architecture's, and ADR-0019's, unmodified); any Layer 2 capability's own architecture (`LearningResult`, `OrganizationalMemoryResult`, `KnowledgeGraphResult`, `ContinuousImprovementResult` remain ADR-0029's, ADR-0027's, ADR-0023's, and ADR-0022's, unmodified); the platform's layer/dependency/lifecycle constitution itself (remains ADR-0020's, extended only additively by D1); any concrete engine, service, or renderer implementation (reserved future work — CAP-087B — not introduced here).
- **Governance:** registered alongside ADR-0018, ADR-0016, ADR-0019, ADR-0028, and ADR-0029 as a subsystem architecture ADR, and alongside ADR-0020 as an additive amendment to the platform constitution. **Proposed** — it becomes **Accepted** once a future capability (CAP-087B — Executable Specification Engineering Deterministic Engine, or equivalent) is built directly against it without deviation, exactly as ADR-0029 became the standard CAP-086B was built under.
