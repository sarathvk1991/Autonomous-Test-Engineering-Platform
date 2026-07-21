# Executable Specification Engineering — Design Proposal

- **Status:** Proposed (CAP-087A — Architecture & Governance Freeze)
- **Capability:** CAP-087 — Executable Specification Engineering
- **Milestones covered:** CAP-087A (Architecture & Governance Freeze — this document)
- **Governed by:** ADR-0030
- **Depends on:** ADR-0018 (Requirement Enhancement Framework), ADR-0016 (Evidence Grounding & Traceability), `docs/architecture/ai-response-validation.md` (Validation), ADR-0019 (Recommendation Framework), ADR-0028 (Learning Constitution), ADR-0029 (Learning Framework), ADR-0020 (Platform Evolution Roadmap & Architectural Constitution — extended additively by ADR-0030 D1 to introduce Layer 2.5).

---

## 1. Problem

The platform's Layer 1 (Requirement Intelligence) produces judged, enriched, grounded, validated, and recommended requirement output for one execution. Layer 2 (Continuous Learning) produces institutionalized organizational understanding across many executions. Neither layer produces anything a test-automation tool, a BDD framework, or a manual QA reviewer can directly execute or act on — every one of their outputs is analytical, not operational.

Left unbuilt, and built without a frozen architecture first, the first attempt to turn judged requirements into executable specifications would invent, under delivery pressure, exactly the kind of ad hoc coupling this platform's every prior ADR exists to prevent: a generator that hard-codes Gherkin syntax directly into requirement-processing code, a single monolithic "spec builder" that mixes scenario discovery with rendering, and no single canonical place to audit *why* a given scenario exists or *what evidence* justified it.

## 2. Scope of CAP-087A

This milestone is architecture and governance only. It:

- Freezes the canonical domain models (§5) and the aggregate runtime contract, `SpecificationEngineeringResult`.
- Freezes the governed policy shape (§7) and the runtime boundary (§8), both dormant.
- Freezes the ten-collaborator internal decomposition (§6) and its execution order.
- Freezes the Scenario Engineering Strategy (§8s below is §... see §9), Business Rule Strategy (§10), and Acceptance Criteria Strategy (§11).
- Freezes the Renderer Architecture (§12) and the Execution Package design (§13).

It introduces **no code**, **no service**, **no `PlatformContext` method**, and **no version bump**. Every object named below is documented, not implemented.

## 3. Stage 0 — Repository assessment (no redesign)

See ADR-0030 Stage 0 for the full repository assessment. Summary: `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `RecommendationResult`, and `LearningResult` are all confirmed live, frozen, independently versioned. No existing capability owns any specification-production responsibility. ADR-0020's seven-layer placement tree does not name this capability's own question; ADR-0030 D1 resolves this additively by introducing Layer 2.5, without redesigning any existing layer.

## 4. Subsystem & ownership

**Reserved package (not created by this milestone):** `requirement_intelligence/specification_engineering/`

Mirrors the shape of every prior Layer 1/Layer 2 subsystem: `models/` (canonical domain models), `policy/` (governed configuration), `identity/` (typed identifiers), `engine/` (reserved, future — the ten collaborators of §6), `rules/` (reserved, future — the governed rule catalogue), `serialization/` (reserved, future — projection-only serializer).

**Ownership boundary (SHALL / SHALL NOT).** See ADR-0030 D5 for the frozen list. In one line: this subsystem owns everything from "what should be specified" through "a rendered, technology-specific specification artifact" — and owns nothing that executes, generates programming-language code, or touches organizational knowledge as a writer.

## 5. Canonical models

Every model below is immutable (frozen at construction, `Schema`-conventioned, no in-place mutation), and every field exists to satisfy a specific explainability, traceability, or governance requirement — never for convenience.

### 5.1 `SpecificationPlan`

The scoping decision that precedes any decomposition — records *what* this build is in scope to specify and *why*, before any feature or scenario exists.

| Field | Purpose |
|---|---|
| `plan_id` | Typed identity (`SpecificationPlanId`), deterministic, no UUID. |
| `source_execution_id` | The one originating execution these five consumed contracts share — the anchor every downstream hop in D15's explainability chain ultimately resolves to. |
| `consumed_contract_refs` | Named, versioned references to the five consumed runtime contracts (`RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `RecommendationResult`, `LearningResult`) — never copies of their content, references only (mirrors `ValidationInput`'s own reference-not-copy discipline, ADR-0003). |
| `in_scope_requirement_ids` | The requirement ids this build will decompose — excludes anything `SpecificationPlanner` determined fails the grounding-confidence or validation-verdict floor (ADR-0030 D2). |
| `excluded_requirement_ids` | The requirement ids explicitly excluded, each paired with a reason — so an exclusion is always explainable, never silent. |
| `planning_rationale` | Free-text rationale naming the specific policy thresholds that produced the scope decision — satisfies decision explainability (mirrors ADR-0029 §D23). |
| `policy_version` | The exact `SpecificationEngineeringPolicyVersion` in force when this plan was built — reproducibility anchor. |

### 5.2 `BusinessFeature`

One coherent unit of business capability, grouping one or more source requirements.

| Field | Purpose |
|---|---|
| `feature_id` | Typed identity (`BusinessFeatureId`). |
| `name` | Governed, deterministic feature name (derived from the source requirement's own enhancement title/category — never invented). |
| `description` | Feature-level description, composed deterministically from the source requirement(s)' own enhanced text — never freely generated. |
| `source_requirement_ids` | At least one required (the "at least one reference" discipline, ADR-0019 §D7) — the requirement(s) this feature was decomposed from. |
| `business_rule_ids` | References to every `BusinessRule` this feature owns — empty until `BusinessRuleExtractor` runs. |
| `scenario_ids` | References to every `BusinessScenario` this feature owns — empty until `ScenarioDiscovery`/`ScenarioClassifier` run. |
| `tag_ids` | References to governed `ScenarioTag`s applied at the feature level (e.g. module, priority). |
| `priority` | Derived from `RecommendationResult` severity for the source requirement(s) — never invented. |
| `traceability_id` | The `Traceability` record reconstructing this feature's full chain back to Runtime Truth (D15). |

### 5.3 `BusinessScenario`

One concrete, classified example of the feature behaving correctly, incorrectly, or at a boundary.

| Field | Purpose |
|---|---|
| `scenario_id` | Typed identity (`BusinessScenarioId`). |
| `feature_id` | The one owning `BusinessFeature` — adjacent-only ownership, mirrors ADR-0029 §D11's adjacent-only promotion discipline. |
| `title` | Deterministic, derived title (category + subject, e.g. "Negative Flow — invalid credential rejected"). |
| `category` | One value of the governed, closed `ScenarioCategory` taxonomy (§9). |
| `step_ids` | Ordered references to this scenario's `ScenarioStep`s. |
| `acceptance_criterion_ids` | At least one required — every scenario must be checkable against a named criterion (never a scenario with nothing to verify). |
| `business_rule_ids` | References to the `BusinessRule`(s) this scenario exercises, if any (some scenarios, e.g. pure Happy Path, may reference zero rules — never required to invent one). |
| `tag_ids` | References to governed `ScenarioTag`s. |
| `outline_id` | Optional reference to a `ScenarioOutline`, present only when this scenario is data-driven/parameterized. |
| `source_requirement_id` | The one requirement this scenario's derivation trigger fired against (D9/§9) — explainability anchor. |

### 5.4 `BusinessRule`

One extracted constraint, calculation, validation, authorization, workflow, or data-integrity rule the specification must respect.

| Field | Purpose |
|---|---|
| `rule_id` | Typed identity (`BusinessRuleId`). |
| `statement` | The rule's normalized statement text, deterministically extracted — never paraphrased beyond the governed normalization transform (§10). |
| `classification` | One value of the governed, closed `BusinessRuleClassification` enum: `CONSTRAINT`, `CALCULATION`, `VALIDATION`, `AUTHORIZATION`, `WORKFLOW`, `DATA_INTEGRITY`. |
| `priority` | Derived from `RecommendationResult` severity and `GroundingResult` confidence — never invented (§10). |
| `version` | Independent `BusinessRuleVersion` axis — a corrected/updated rule is a new version referencing the one it supersedes, never an in-place edit (mirrors ADR-0028 Stage 11's append-only evolution, lifted to rule granularity). |
| `source_requirement_ids` | At least one required. |
| `validation_status` | Set exclusively by `SpecificationValidator` (never by `BusinessRuleExtractor` itself, ADR-0030 D10) — records whether this rule cleared structural validation. |
| `traceability_id` | The `Traceability` record for this rule. |

### 5.5 `AcceptanceCriterion`

One normalized, deduplicated, prioritized condition of satisfaction.

| Field | Purpose |
|---|---|
| `criterion_id` | Typed identity (`AcceptanceCriterionId`). |
| `statement` | The normalized criterion text (§11's deterministic normalization transform). |
| `source_requirement_id` | Exactly one required — every criterion traces to the one requirement it was normalized from. |
| `normalized_form` | The canonical, deduplication-ready form (trimmed, case-folded, template-applied) — kept distinct from `statement` so the human-facing text and the machine-comparable text never conflate (mirrors `ParsedResponse`'s own presentation/structure separation, ADR-0002). |
| `deduplicated_from` | References to any criteria this one absorbed during dedup (§11) — so a merge is always explainable, never a silent loss. |
| `priority` | Derived from `RecommendationResult` severity and `GroundingResult` confidence. |
| `traceability_id` | The `Traceability` record for this criterion. |

### 5.6 `ScenarioStep`

One ordered step inside a scenario, technology-agnostic.

| Field | Purpose |
|---|---|
| `step_id` | Typed identity (`ScenarioStepId`). |
| `role` | One value of the governed, closed `StepRole` enum: `PRECONDITION`, `ACTION`, `OUTCOME`, `CONJUNCTION`. Deliberately **not** `Given`/`When`/`Then`/`And`/`But` — those are Gherkin's own vocabulary (D4/§12); `StepRole` is the renderer-agnostic abstraction a Cucumber renderer maps to `Given`/`When`/`Then`/`And` and a Playwright renderer maps to setup/act/assert. |
| `text` | The step's normalized, human-readable statement. |
| `order` | The step's position within its scenario — steps are ordered, never reordered by a renderer. |
| `data_table` | Optional structured tabular data attached to the step (reserved shape; empty unless the source requirement itself carried tabular content). |
| `source_reference` | The requirement/enhancement fragment this step's text was derived from. |

### 5.7 `ScenarioTag`

One governed, reusable label applied to a feature or scenario.

| Field | Purpose |
|---|---|
| `tag_id` | Typed identity (`ScenarioTagId`). |
| `label` | The tag's governed text (e.g. `@security`, `@priority-high`) — drawn from a governed vocabulary, never freely invented per scenario (keeps tags queryable/consistent across an entire specification build). |
| `category` | The tag's governed dimension (e.g. `PRIORITY`, `MODULE`, `SCENARIO_TYPE`). |
| `vocabulary_reference` | Points to the governed tag vocabulary entry this tag instance conforms to — the mechanism that keeps tag growth ADR-gated rather than ad hoc (mirrors the Validation Rule Catalog's own governed-growth discipline). |

### 5.8 `ScenarioOutline`

One parameterization of a scenario, for data-driven specification.

| Field | Purpose |
|---|---|
| `outline_id` | Typed identity (`ScenarioOutlineId`). |
| `scenario_id` | The one owning scenario. |
| `parameters` | Ordered parameter names referenced by the owning scenario's steps. |
| `examples` | A table of concrete value rows, one row per generated example — deterministic, sourced from the requirement's own enumerated values (never invented placeholder data; this is explicitly not Test Data Generation, ADR-0030 D5 SHALL NOT). |
| `source_reference` | The requirement fragment the parameterization was derived from. |

### 5.9 `Traceability`

One record reconstructing a subject's complete chain back to Runtime Truth (D15).

| Field | Purpose |
|---|---|
| `traceability_id` | Typed identity (`TraceabilityId`). |
| `subject_id` | The `BusinessFeature`, `BusinessScenario`, `BusinessRule`, or `AcceptanceCriterion` this record explains. |
| `subject_type` | Which of the four the subject is — keeps the record self-describing without needing a type-switch on the id shape. |
| `source_requirement_ids` | Every requirement in the subject's ancestry. |
| `source_contract_refs` | Named, versioned references to every one of the five consumed contracts (§5.1) the subject's derivation actually touched — never every contract unconditionally, only the ones genuinely consulted (D18/D20 of ADR-0029's own "name the specific inputs" discipline, lifted here). |
| `chain` | The ordered hop list itself, human-navigable, composing with each consumed contract's own already-frozen explainability chain rather than duplicating it. |

### 5.10 `SpecificationMetrics`

Tally-only build statistics — never a computed judgement.

| Field | Purpose |
|---|---|
| `feature_count`, `scenario_count`, `business_rule_count`, `acceptance_criterion_count` | Row counts, tallied, never derived through inference. |
| `scenario_category_distribution` | Count per `ScenarioCategory` — presentation only. |
| `validation_pass_count`, `validation_fail_count` | Tallied from `ValidationSummary`, never recomputed. |
| `renderer_output_count` | Count of rendered artifacts produced, per registered renderer — zero until a renderer is implemented and enabled. |

### 5.11 `ValidationSummary`

The `SpecificationValidator`'s own recorded verdict over the canonical graph — a specification-layer validation, distinct from and never a re-run of Layer 1's own `ValidationResult` (which validated the AI response, not the derived specification).

| Field | Purpose |
|---|---|
| `validation_id` | Typed identity (`SpecificationValidationId`). |
| `rules_checked` | The governed structural/completeness rule ids actually evaluated (e.g. "every scenario has ≥1 acceptance criterion," "no orphan acceptance criterion," "every feature has ≥1 scenario," "no duplicate scenario within a feature"). |
| `issues` | Every rule violation found, each naming the specific subject and rule id — never a bare pass/fail with no detail. |
| `overall_verdict` | One of `VALID`, `VALID_WITH_WARNINGS`, `INVALID` — mirrors the platform's existing verdict vocabulary (`ValidationVerdict`, ADR-0004) rather than inventing a new one. |
| `rationale` | Names the specific rules and issues the verdict was derived from — decision explainability, mirrors ADR-0029 §D23. |

### 5.12 `RendererMetadata`

Describes what a renderer produced — never the rendered content itself as canonical fact (the rendered artifact lives in the Execution Package, §13, not inside the runtime contract's own truth).

| Field | Purpose |
|---|---|
| `renderer_id` | Typed identity (`RendererId`). |
| `renderer_type` | One value of the governed, open-for-additive-growth `RendererType` enum: `CUCUMBER` (first target), `PLAYWRIGHT`, `SELENIUM`, `API_TEST_SPECIFICATION`, `TESTRAIL`, `LIVING_DOCUMENTATION` — reserved members for future renderers, added additively, never by redefining an existing member. |
| `renderer_version` | The specific renderer implementation's own version — independent of `SpecificationEngineeringResultVersion` (§14). |
| `output_format` | The concrete file/content format produced (e.g. `.feature` text). |
| `output_locations` | Reserved pointer(s) to where the Execution Package placed the rendered artifact(s) — empty until a future implementation milestone. |
| `supported_since_version` | The `SpecificationEngineeringFrameworkVersion` this renderer type first became available in — governance/audit trail for renderer growth. |

### 5.13 `SpecificationEngineeringResult`

The canonical runtime contract — the complete deterministic record of one Specification Engineering build.

| Section | Contains | Why it exists |
|---|---|---|
| **Specification Plan** | `SpecificationPlan` | Records the scoping decision that governed everything downstream — without it, the result cannot explain *why* certain requirements were or were not specified. |
| **Features** | `tuple[BusinessFeature, ...]` | The top-level organizing unit every scenario, rule, and criterion is grouped under — the structure a renderer walks first. |
| **Scenarios** | `tuple[BusinessScenario, ...]` | The concrete, classified, executable-in-spirit examples — the reason this capability exists. |
| **Acceptance Criteria** | `tuple[AcceptanceCriterion, ...]` | The normalized conditions of satisfaction every scenario is checked against. |
| **Business Rules** | `tuple[BusinessRule, ...]` | The extracted constraints every scenario and criterion must remain consistent with. |
| **Traceability** | `tuple[Traceability, ...]` | The explicit, queryable explainability chain for every feature/scenario/rule/criterion (D15) — without this section the result would be no more explainable than a flat text dump. |
| **Validation** | `ValidationSummary` | Records whether the canonical graph is structurally sound before any rendering was attempted (D16). |
| **Metrics** | `SpecificationMetrics` | Presentation-only tallies for reporting, never re-derivable judgement. |
| **Metadata** | provenance record: `source_execution_id`, the five consumed contract references (id + version each) | Anchors reproducibility and explainability at the result level, not just per-subject. |
| **Versioning** | `SpecificationEngineeringResultVersion`, plus the framework/policy versions in force | Reproducibility — the same five inputs, same policy version, always yield the same result (mirrors ADR-0029 §D24). |
| **Policies** | the governing `SpecificationEngineeringPolicy` identity/version reference | Every decision inside this result is policy-bounded (D6) — the result must be able to name which policy governed it. |
| **Renderer Metadata** | `tuple[RendererMetadata, ...]` | Reserved, empty at this milestone; records what was rendered once a renderer exists, without embedding the rendered content as canonical fact (D11). |

**`SpecificationEngineeringResult` IS.** The complete runtime output of one Specification Engineering build; the platform's first instance of Specification Truth (ADR-0030 D3); self-contained; independently versioned; deterministic; explainable; projection-independent; the sole entry point any future Layer 3+ capability must use to consume a specification-tier conclusion (ADR-0030 Recommendation 19).

**`SpecificationEngineeringResult` IS NOT.** Runtime Truth, Historical Truth, Derived Knowledge, Organizational Knowledge, or Learned Knowledge; any of its five consumed contracts' own content; Gherkin or any other rendered syntax; an execution package; a report; a renderer; a serializer; a CLI object; a mutable ledger; test code; test data; any engine-specific or implementation-specific object of any kind.

## 6. Internal capability decomposition

Ten collaborators, frozen order (ADR-0030 D9/D16):

```
SpecificationPlanner → RequirementDecomposer → BusinessRuleExtractor →
AcceptanceCriteriaNormalizer → ScenarioDiscovery → ScenarioClassifier →
CanonicalSpecificationBuilder → SpecificationValidator → Renderer → SpecificationPackager
```

### 6.1 `SpecificationPlanner`

- **Purpose:** Determine the scope of one Specification Engineering build.
- **Inputs:** `RequirementEnhancementResult`, `GroundingResult`, `ValidationResult`, `RecommendationResult`, `LearningResult`, `SpecificationEngineeringPolicy`.
- **Outputs:** `SpecificationPlan`.
- **Responsibilities:** Determine which requirements are in scope; exclude any requirement failing the governed grounding-confidence floor or carrying a failed `ValidationResult` verdict; record rationale for every exclusion.
- **Constraints:** Never decomposes a requirement into features itself; never invents scope beyond what the five consumed contracts already contain.
- **Policies:** `minimum_grounding_confidence_for_planning`, `exclude_failed_validation` (capability switch).

### 6.2 `RequirementDecomposer`

- **Purpose:** Decompose each in-scope requirement into one or more candidate `BusinessFeature`s.
- **Inputs:** `SpecificationPlan`, `RequirementEnhancementResult`.
- **Outputs:** `BusinessFeature` (draft — no rules, scenarios, or tags linked yet).
- **Responsibilities:** Feature identification and grouping, deterministic (governed grouping strategy, e.g. by the requirement's own enhancement category/module tag).
- **Constraints:** Every in-scope requirement maps to at least one feature, never zero; never fabricates feature content beyond the enhancement fields it was given.
- **Policies:** `feature_grouping_strategy` (governed, deterministic identifier — no free-text heuristic).

### 6.3 `BusinessRuleExtractor`

- **Purpose:** Extract `BusinessRule`s from requirement/enhancement content and grounding evidence.
- **Inputs:** `BusinessFeature` (draft), `RequirementEnhancementResult`, `GroundingResult`.
- **Outputs:** `BusinessRule`.
- **Responsibilities:** Rule identification, classification (§10), prioritization (§10).
- **Constraints:** Never validates a rule itself (`SpecificationValidator`'s exclusive role, §6.8); never extracts a rule with zero source requirement reference.
- **Policies:** governed classification-trigger vocabulary (deterministic keyword/structure match — no NLP, no LLM at this milestone).

### 6.4 `AcceptanceCriteriaNormalizer`

- **Purpose:** Normalize, deduplicate, resolve conflicts among, and prioritize `AcceptanceCriterion`s.
- **Inputs:** `BusinessFeature` (draft), `RequirementEnhancementResult`, `RecommendationResult`.
- **Outputs:** `AcceptanceCriterion`.
- **Responsibilities:** Execute the Acceptance Criteria Strategy (§11) in full.
- **Constraints:** Deduplication is byte-equality on the normalized form only — never semantic/embedding dedup at this milestone (reserved future capability behind its own ADR, mirrors ADR-0008's own reservation of semantic duplicate detection).
- **Policies:** `deduplication_mode` (fixed `BYTE_EQUALITY` at this milestone, reserved for future governed expansion), `conflict_resolution_precedence`.

### 6.5 `ScenarioDiscovery`

- **Purpose:** Derive candidate `BusinessScenario`s (with their `ScenarioStep`s and, where applicable, `ScenarioOutline`s) across the governed category taxonomy (§9).
- **Inputs:** `BusinessFeature`, `BusinessRule`, `AcceptanceCriterion`, `LearningResult`.
- **Outputs:** `BusinessScenario` (draft, uncategorized-final-form), `ScenarioStep`, `ScenarioOutline`.
- **Responsibilities:** Execute the Scenario Engineering Strategy's deterministic derivation triggers (§9); apply Learning-sourced additive enrichment only.
- **Constraints:** Never classifies (§6.6's exclusive role); never validates; never suppresses a taxonomy-triggered category because of Learning (ADR-0030 D12).
- **Policies:** `enabled_scenario_categories` (capability switches per category, all on by default), `learning_enrichment_enabled`.

### 6.6 `ScenarioClassifier`

- **Purpose:** Assign each discovered scenario its final `ScenarioCategory` and `ScenarioTag` set.
- **Inputs:** `BusinessScenario` (draft).
- **Outputs:** `BusinessScenario` (classified), `ScenarioTag`.
- **Responsibilities:** Sole owner of category/tag assignment.
- **Constraints:** Never discovers new scenarios; never rewrites step content.
- **Policies:** governed tag vocabulary reference.

### 6.7 `CanonicalSpecificationBuilder`

- **Purpose:** Assemble the linked canonical Specification graph and construct `Traceability`.
- **Inputs:** Every object produced by §6.1–§6.6.
- **Outputs:** The cross-linked canonical Specification graph, `Traceability`.
- **Responsibilities:** Sole owner of cross-reference integrity and `Traceability` construction.
- **Constraints:** Never computes new content — assembly and linking only (mirrors `ResultBuilder`'s non-computational discipline, ADR-0029 §D22).
- **Policies:** none (pure assembly, ungoverned by threshold).

### 6.8 `SpecificationValidator`

- **Purpose:** Validate the canonical Specification graph against governed structural/completeness rules.
- **Inputs:** The canonical Specification graph.
- **Outputs:** `ValidationSummary`.
- **Responsibilities:** Sole validation authority for the specification layer (distinct from Layer 1's own `ValidationResult`).
- **Constraints:** Never mutates the graph; never blocks the pipeline outright — records `INVALID` and lets `SpecificationPackager` (§6.10) decide, per policy, whether an invalid build still produces a result (it always does — the result records the failure; only rendering is policy-gated on the verdict, §6.9).
- **Policies:** `minimum_scenarios_per_feature`, `minimum_acceptance_criteria_per_scenario`, `maximum_scenario_category_gap`.

### 6.9 `Renderer`

- **Purpose:** Project the validated canonical Specification into one technology-specific artifact format.
- **Inputs:** The canonical Specification graph, `ValidationSummary`, renderer configuration.
- **Outputs:** Rendered artifact content, `RendererMetadata`.
- **Responsibilities:** Sole rendering authority; one renderer per registered `RendererType` (§12).
- **Constraints:** Never computes or derives new specification content; runs only when `ValidationSummary.overall_verdict` is not `INVALID` (policy-gated — mirrors CP1's own gate-on-verdict pattern, ADR-0011 §D5).
- **Policies:** `enabled_renderer_types`, `render_on_validation_warning` (whether `VALID_WITH_WARNINGS` still renders; default true).

### 6.10 `SpecificationPackager`

- **Purpose:** Assemble the final `SpecificationEngineeringResult` and prepare Execution Package artifacts.
- **Inputs:** Every object produced by §6.1–§6.9.
- **Outputs:** `SpecificationEngineeringResult` (sole constructor), `SpecificationMetrics` (tallied here, never computed elsewhere), Execution Package artifact set (reserved, §13).
- **Responsibilities:** Sole result-construction authority; sole execution-package-projection authority.
- **Constraints:** Packaging and tallying only — no upstream computation (mirrors ADR-0029 §D22).
- **Policies:** none (pure assembly).

## 7. Governed policy

`SpecificationEngineeringPolicy` (reserved, dormant):

- **`SpecificationEngineeringCapabilitySwitches`** — independent on/off switches: `enable_planning`, `enable_decomposition`, `enable_rule_extraction`, `enable_criteria_normalization`, `enable_scenario_discovery`, `enable_scenario_classification`, `enable_validation`, `enable_rendering`, `enable_packaging` (all `True` by default — governed intent, no engine reads them yet), plus `enable_deterministic_engine` / `enable_rule_based_engine` / `enable_ml_engine` / `enable_llm_engine` (all reserved `False` until a future engine milestone).
- **`SpecificationEngineeringThresholds`** — governed numeric bounds a future engine must respect: `minimum_grounding_confidence_for_planning`, `minimum_scenarios_per_feature`, `minimum_acceptance_criteria_per_scenario`, `maximum_scenario_category_gap`.
- **`enabled_scenario_categories`** — per-category capability switches over the fifteen governed categories (§9), all on by default.
- **`enabled_renderer_types`** — per-`RendererType` capability switches (§12), only `CUCUMBER` reserved on by default; every other type reserved off until its renderer exists.

## 8. Runtime boundary (frozen, dormant)

```
SpecificationEngineeringService.build(
    requirement_enhancement_result: RequirementEnhancementResult,
    grounding_result: GroundingResult,
    validation_result: ValidationResult,
    recommendation_result: RecommendationResult,
    learning_result: LearningResult,
) -> SpecificationEngineeringResult
```

Abstract only. No implementation exists. A future `DeterministicSpecificationEngineeringService` (or ML/LLM/hybrid variant, CAP-087B onward) implements this identical signature without changing it (ADR-0030 D8).

## 9. Scenario Engineering Strategy

`ScenarioDiscovery` derives candidate scenarios per `(BusinessFeature, BusinessRule | None, AcceptanceCriterion)` combination, against the following governed, closed taxonomy. Each category names its deterministic derivation trigger and how `LearningResult` may additively enrich it.

| Category | Deterministic trigger | Learning enrichment |
|---|---|---|
| **Happy Path** | Every `AcceptanceCriterion` unconditionally triggers exactly one Happy Path scenario — the floor every feature must have. | Learning may not suppress this; it is the non-negotiable floor. |
| **Alternate Flow** | A requirement enhancement recording more than one valid path to the same outcome. | Learning may surface a historically-common alternate path not explicit in the requirement text. |
| **Negative Flow** | An `AcceptanceCriterion` phrased as a negative condition, or a `BusinessRule` classified `VALIDATION`/`CONSTRAINT`. | Learning may add a Negative Flow scenario for requirement shapes historically found to need one. |
| **Exception Flow** | A requirement enhancement naming an explicit error/exception condition. | Learning may add coverage for exception conditions historically observed alongside this requirement shape. |
| **Boundary Conditions** | A `BusinessRule` classified `CONSTRAINT` naming a numeric, length, or range limit. | Learning may add a boundary case at a limit not explicitly stated but historically significant. |
| **Security** | A `BusinessRule` or requirement tag naming a security concern. | Learning may add a security scenario type historically paired with this feature category. |
| **Authorization** | A `BusinessRule` classified `AUTHORIZATION`. | Learning may add role/permission combinations historically significant for this rule shape. |
| **Authentication** | A requirement enhancement naming credential/identity verification. | Learning may add an authentication-failure variant historically observed. |
| **Data Validation** | A `BusinessRule` classified `VALIDATION` or `DATA_INTEGRITY`. | Learning may add a data-shape variant historically found to reveal validation gaps. |
| **Integration Failure** | A requirement enhancement naming an external system dependency. | Learning may add a failure-mode variant historically observed for this integration shape. |
| **Recovery** | Paired unconditionally with any generated Integration Failure or Exception Flow scenario. | Learning may enrich the recovery expectation with a historically-observed recovery pattern. |
| **Business Rule Validation** | Every `BusinessRule` unconditionally triggers exactly one scenario verifying it directly. | Learning may add an additional rule-interaction scenario historically found to matter. |
| **State Transition** | A requirement enhancement or grounding evidence naming a lifecycle/status field. | Learning may add a transition sequence historically significant for this entity shape. |
| **Concurrency** | A `BusinessRule` or requirement enhancement naming shared/contended state. | Learning may add a concurrency variant historically observed for this shape. |
| **Regression** | A requirement enhancement explicitly linked to a prior defect/incident reference. | Learning may add a regression scenario for a defect pattern the organization has institutionally learned recurs. |

**Learning enrichment rule (frozen, ADR-0030 D12):** Learning may only **add** a scenario proposal beyond what the deterministic trigger column already produces. It may never suppress a triggered category, and it may never propose a scenario with zero requirement/rule/criterion reference — mirroring ADR-0028 D15's "institutionalizes, never invents."

## 10. Business Rule Strategy

- **Rule Identification.** Deterministic extraction from requirement/enhancement content bearing constraint or conditional language (governed keyword/structure trigger vocabulary), cross-checked against `GroundingResult` — a rule with no supporting grounding evidence is still extracted but recorded with lower confidence, never silently dropped.
- **Rule Classification.** Closed enum: `CONSTRAINT`, `CALCULATION`, `VALIDATION`, `AUTHORIZATION`, `WORKFLOW`, `DATA_INTEGRITY`. Growth of this enum is ADR-gated, mirroring the Validation Rule Catalog's own governed-growth discipline.
- **Rule Prioritization.** Derived, never invented: a deterministic mapping from `RecommendationResult` severity and `GroundingResult` confidence to a governed priority level.
- **Rule Versioning.** Independent `BusinessRuleVersion` axis (§14) — an updated rule is a new version referencing the one it supersedes, never an in-place edit.
- **Rule Traceability.** Every rule names at least one source requirement — no exception.
- **Rule Validation.** Owned exclusively by `SpecificationValidator` (§6.8); `BusinessRuleExtractor` never validates its own output.

## 11. Acceptance Criteria Strategy

- **Normalization.** A deterministic textual transform: trim whitespace, case-fold, apply a canonical phrasing template. Never a semantic rewrite that could change meaning.
- **Deduplication.** Byte-equality on the normalized form only, at this milestone — the identical mechanism ADR-0007 (`CONTENT-0002`) and ADR-0008 (`REASONING-0002`) already freeze byte-exact for their own domains. Semantic/embedding-based deduplication is explicitly reserved, not adopted here (mirrors ADR-0008's own reservation of semantic duplicate detection as future work behind its own ADR).
- **Conflict Resolution.** Governed precedence: the criterion backed by the higher `RecommendationResult` severity wins. An unresolved tie is never silently dropped or auto-resolved by inference — both are retained, and the conflict is recorded on both criteria (`deduplicated_from` / a paired conflict flag) for human review.
- **Prioritization.** Derived from `GroundingResult` confidence and `RecommendationResult` severity — identical mechanism to Rule Prioritization (§10), applied to criteria.
- **Traceability.** Exactly one source requirement per criterion, always.

## 12. Renderer Architecture

```
Canonical Specification
        ↓
     Renderer
        ↓
   Feature Files (Cucumber, first target)
```

**Responsibilities.** A renderer is a pure projection over an already-validated canonical graph. It performs no decomposition, extraction, normalization, discovery, classification, or validation — it emits only facts the canonical model already carries, in a target-specific syntax.

**Isolation.** No renderer depends on another renderer. No renderer writes back into the canonical model. A renderer bug can corrupt only its own output artifact, never the canonical Specification or any other renderer's output.

**Extensibility.** Every renderer implements one frozen contract:

```
render(SpecificationEngineeringResult) -> RenderedArtifact
```

and is registered in a governed `RendererRegistry` — explicit registration, `OPEN → SEALED` lifecycle, no reflection, deterministic ordering (mirrors `PromptRegistry` / `ValidationRegistry` / `CP1CriterionRegistry`, ADR-0014 / ADR-0011). Adding Playwright, Selenium, API Test Specification, TestRail, or Living Documentation support is therefore purely additive: implement the contract, register it, add the corresponding `RendererType` enum member (governed, additive-only growth). Zero modification to `SpecificationPlanner` through `SpecificationValidator`. Zero change to any canonical domain model.

## 13. Execution package (reserved; architecture only)

| Artifact | Mirrors | Content |
|---|---|---|
| `specification_engineering_result.json` | every `*_result.json` | The complete `SpecificationEngineeringResult`. |
| `specification_engineering_report.md` | `validation_report.md` | Human-readable narrative over the result. |
| `specification_engineering_metrics.md` | `baseline_metrics_builder.py` output | `SpecificationMetrics` rendered, presentation only. |
| `generated_feature_files/` | — | One subdirectory per registered `RendererType`; empty until a renderer is registered and enabled. |
| `traceability_matrix.md` | — | `Traceability` rendered as a human-navigable table. |
| `gherkin_validation_report.md` | `cp1_report.md` | `ValidationSummary` rendered — sourced from `SpecificationValidator`'s canonical-graph validation, never renderer-specific syntax checking. |

No implementation is designed here — this is the artifact contract a future implementation milestone must satisfy without redesign.

## 14. Versioning strategy (summary; full governance in the companion governance document)

Independent axes, each evolving without forcing the others to change: `SpecificationEngineeringFrameworkVersion`, `SpecificationEngineeringPolicyVersion`, `SpecificationPlanVersion` (reserved), `BusinessRuleVersion`, `BusinessScenarioVersion` (reserved), `RendererMetadataVersion`, `SpecificationEngineeringResultVersion`.

## 15. PlatformContext (reserved)

A future implementation milestone adds exactly two composition-root methods: `create_specification_engineering_policy()` and `create_specification_engineering_service()`. Not added by this milestone (ADR-0030 D7).

## 16. Implementation roadmap (non-normative)

1. **CAP-087B** — Deterministic Specification Engineering Engine: implements the ten collaborators exactly as frozen here, behind the frozen contracts, no redesign.
2. **CAP-087B.1** — `SpecificationEngineeringResult` Runtime Contract Freeze: permanent certification, no behaviour change (mirrors ADR-0029 §D28's pattern).
3. **CAP-087C** — Runtime Integration: wires `build` into the live pipeline as the first Layer 2.5 capability, immediately after Learning.
4. **CAP-087D (reserved)** — First concrete `Renderer` (Cucumber), Execution Package artifact activation.
5. **CAP-087E+ (reserved)** — Additional renderers (Playwright, Selenium, API Test Specifications, TestRail, Living Documentation), each purely additive per §12.

## 17. Terminology

- **Specification Truth** — the fifth, distinct kind of platform output this capability produces (ADR-0030 D3): a technology-independent, structured statement of what the system under specification must do.
- **Business Feature** — one coherent unit of business capability grouping one or more source requirements (`BusinessFeature`).
- **Business Scenario** — one concrete, classified example of a feature's behaviour (`BusinessScenario`).
- **Business Rule** — one extracted constraint, calculation, validation, authorization, workflow, or data-integrity rule (`BusinessRule`).
- **Acceptance Criterion** — one normalized, deduplicated, prioritized condition of satisfaction (`AcceptanceCriterion`).
- **Renderer** — the sole, pluggable projection from the canonical Specification Model to a technology-specific artifact; never a source of new specification content.
- **Layer 2.5** — the new architectural position this capability occupies, additively inserted between Layer 2 (Continuous Learning) and Layer 3 (Feature Engineering) by ADR-0030 D1, without renumbering or redefining any existing layer.
