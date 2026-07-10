# ADR-0015 — Engineering Context Orchestration: Canonical Model, Typed Identity, and Policy Framework

- **Status:** Accepted
- **Date:** 2026-07-10 (Proposed) · 2026-07-10 (Accepted)
- **Supersedes:** nothing. **Amends:** nothing.
- **Governing review:** `docs/reviews/cap-076-engineering-context-orchestration.md` (CAP-076 Part 1, CAP-076A)
- **Runtime status:** Live as of CAP-076C; multi-source as of CAP-076D — see [Addendum: CAP-076C](#addendum--cap-076c-runtime-integration) and [Addendum: CAP-076D](#addendum--cap-076d-multi-source-activation).

## Problem

CAP-074B proved, and CAP-076 Part 1 independently reproduced, that the Requirement Intelligence Layer presents the LLM with evidence from exactly one source domain. Measured against the repository's own fixtures: 387 `SourceArtifact`s (300 SonarQube, 83 OWASP ZAP, 4 JIRA) consolidate into 23 groups, **none of which contains more than one source category**. The selected group holds 0 functional, 0 security, and 71 quality artifacts.

The mechanism is not a bug in any component. `consolidation_rules.derive_grouping_key` is a first-match cascade (`component → tag → endpoint → risk`), and `ConsolidationEngine` buckets on `(dimension, value)`. Only `SonarMapper` populates `component`; JIRA falls through to its per-issue REST `self` URL; ZAP stops at its alert tags. Artifacts matching different rungs can never share a group, however related they are in reality. The three-way functional/security/quality split inside `ConsolidatedArtifact` is fully built and never filled.

Every component does exactly what its docstring promises. **The defect is that no component owns the question "what evidence should one reasoning session receive?"** Today that question is answered by eleven lines of private CLI glue — `scripts/run_requirement_analysis.py:_select_consolidated` — duplicated verbatim in `tests/productization/conftest.py`.

CAP-076A named the missing subsystem **Engineering Context Orchestration**. This ADR governs the architectural foundation it needs: a canonical model, a typed identity model, and a declarative policy framework. It governs no runtime behaviour, because CAP-076B introduces none.

---

## Decision

Introduce a new subsystem package, `requirement_intelligence/context_orchestration/`, containing:

1. **`EngineeringContext`** — a new canonical model, immutable, produced by the subsystem and consumed by nothing yet.
2. **`EngineeringContextId`, `OrchestrationPolicyId`, `PolicyVersion`** — the platform's first strongly typed identifiers, scoped to this subsystem.
3. **`OrchestrationPolicy`** — a declarative, immutable rule set. `DefaultOrchestrationPolicy` and `LegacySelectionPolicy` are its governed instances.
4. **`EngineeringContextBuilder`** — construction only.

`PlatformContext` gains `create_orchestration_policy()` and `create_engineering_context_builder()`. Nothing calls them.

---

## D1 — Why `EngineeringContext` is a new canonical model, not an extension of `ConsolidatedArtifact`

Extending `ConsolidatedArtifact` was the cheaper option and is the wrong one, for four independent reasons.

**It answers a different question.** `ConsolidatedArtifact` answers *"which records share an attribute?"* — its identity **is** its grouping key (`build_consolidated_id` is a pure function of `(dimension, value)`). `EngineeringContext` answers *"what does a reasoner need to know about this subject?"* A context composed from a Sonar `component` group, a ZAP `tag` group, and a JIRA `endpoint` group has **no single grouping dimension**, and therefore no expressible `consolidated_id`. The existing identity contract cannot name the new thing.

**It would give one model two owners.** Consolidation owns `ConsolidatedArtifact` and must remain free to evolve its grouping cascade. Adding orchestration concerns (policy identity, evidence budget, orchestration reason) to that model would make every Consolidation change an orchestration change, and vice versa. ADR-0001's modular-monolith rule — layers depend on contracts, not on each other's internals — argues directly against it.

**`ConsolidatedArtifact` is a frozen canonical model.** It is serialised into every execution package as `consolidated_artifact.json` and hashed by the golden baseline. Fields may be added additively; a field like `orchestration_reason` on a *group* would be meaningless in every existing consumer and would alter every golden hash for no behavioural gain.

**The relationship is composition, not specialisation.** A context *contains* the evidence of several consolidated artifacts and *records* which ones contributed. `EngineeringContext` is not an "enriched group"; it is a different aggregate at a higher level. Modelling it by subclassing or widening would be a Liskov violation dressed as economy.

`ConsolidatedArtifact` therefore **remains the canonical consolidation model, unchanged and not deprecated**. `EngineeringContext` becomes the canonical orchestration model. They are stacked, not substituted.

---

## D2 — Why Engineering Context Orchestration owns policy while Consolidation owns grouping

Grouping is a **property of the data**: two artifacts either share a component or they do not. It is objective, cheap, total, and it can be computed without knowing what the result will be used for. This is why `consolidation_rules.py` can be pure, deterministic, and free of source-specific branching — and why it should stay that way.

Composition is a **judgement about a consumer**: how much evidence fits one reasoning session, whether a `CRITICAL` defect outranks 71 code smells, whether a domain with no evidence is acceptable. These questions have no answer derivable from the artifacts alone. They depend on the LLM's context window, on the analysis objectives, and on what the organisation considers balanced evidence.

Pushing composition into Consolidation would import all of that contingency into the one component the platform relies on to be objective. Consolidation would need to know about token budgets and prompt structure. The dependency `consolidation → prompts` is precisely the coupling ADR-0001 forbids.

The converse also holds: orchestration must not re-group. It consumes groups as given. Because grouping is objective, an orchestrator that regrouped would be second-guessing a computation it has no better information to perform.

**Consolidation is a function of the data. Orchestration is a function of the data *and* the consumer.** They are separated because their inputs differ.

---

## D3 — Why policy is separated from orchestration execution

The policy is **data**; the orchestrator is **behaviour**. Three consequences justify the split.

**Auditability.** An execution result is uninterpretable without the rules that produced it. Because `OrchestrationMetadata` carries `policy_id` and `policy_version` *inside* the context, a historical execution package can always be attributed to the rules in force. A policy fused into orchestrator code could only be identified by a git SHA.

**Testability.** Coverage, ranking, budget and tie-breaking become assertable as values, without executing anything. `EvidenceBudget(max_artifacts_per_domain=10, max_artifacts_total=5)` is rejected at construction; no orchestrator run is needed to discover the rule set is unsatisfiable.

**Governability.** CAP-075 established that governed assets are versioned, integrity-verified, registry-resolved, and pinned by an explicit `(id, version)` pair. A policy that is inert data can travel that path later; a policy expressed as `if` statements cannot. CAP-076A §10 sketches that direction as explicitly non-normative — this ADR does not authorise it, but it deliberately does not foreclose it.

**Reproducibility is enforced structurally, not by convention.** CAP-076A Invariant 7 forbids probabilistic ranking. `RankingKey` and `TieBreaker` are closed enumerations of total-order keys over values the source data carries (`risk_level`, artifact count, `consolidated_id`). *There is no enum member a learned or stochastic score could be expressed as.* A non-deterministic policy is unrepresentable rather than merely discouraged.

The boundary is drawn so the builder does not cross it. The builder *enforces* the budget as an input contract — it raises `ContextBudgetExceededError` when handed too much evidence — but it never *applies* the budget by truncating. Enforcing a bound is validation; applying one is orchestration.

---

## D4 — Why `EngineeringContext` is immutable

A context is the exact evidence a reasoning session received. If it can change after construction, then the artefact persisted in an execution package, the bytes rendered into the prompt, and the object the analysis service saw may all disagree — and no baseline over any of them means anything.

Immutability here is **deep, not surface**. `Schema` already sets `frozen=True`, but a frozen pydantic model with a `list` field still permits `context.evidence.functional_artifacts.append(...)`. Every collection is therefore a `tuple`, following the precedent set by `ValidationProfileDefinition.enabled_layers`. The typed identifiers are frozen dataclasses and hashable.

Immutability also makes Invariant 7 checkable: a context that cannot change is a context whose SHA-256 is a meaningful golden-baseline anchor.

**Builder constructs. Consumers read.** There is no mutating API, no setter, and no `copy_with`.

---

## D5 — Why strongly typed identifiers instead of raw strings

Before this ADR, **every identifier in the platform was a raw `str`**: `consolidated_id`, `prompt_id`, `cp1_id`, `validation_id`, `finding_id`. Nothing prevents a policy id being passed where a context id is expected; nothing validates shape at a boundary; nothing distinguishes an identifier from any other string in a signature.

The subsystem introduces three typed identifiers because it is the first place the cost of confusion is concrete: a context, a policy, and a policy version all coexist inside `OrchestrationMetadata`, and all three would otherwise be `str`. Typing them buys:

- **Type safety.** `EngineeringContextId("x") != OrchestrationPolicyId("x")` — a dataclass `__eq__` compares classes first. The confusion a raw `str` permits is unrepresentable.
- **Validation at the boundary.** Shape is enforced at construction, not discovered downstream.
- **Traceability and future manifest integration.** Each serialises to a plain JSON string, so `contextId` remains greppable and the JSON contract's shape is unchanged.
- **Semantic comparison.** `PolicyVersion` is ordered and answers `is_compatible_with`; a version string cannot.

**No existing identifier is retyped.** Retrofitting `consolidated_id` would change `ConsolidatedArtifact`, the manifest, and every golden hash — for a benefit unrelated to this milestone. Scope is deliberately confined to the new subsystem.

### Convention followed, not invented

There was no pre-existing *identifier* pattern to align with. There was a pre-existing **value-object** pattern: `PromptVersion` is an immutable, comparable `@dataclass(frozen=True, order=True)` with a validating `parse()` classmethod, a canonical `__str__` round-trip, and `ValueError` on malformed input. This subsystem adopts that pattern exactly. **A second convention has not been introduced.**

---

## Alternatives Considered

**A — Extend `ConsolidatedArtifact` with orchestration fields.** Rejected: see D1. Cheapest, and it breaks identity, ownership, and the frozen model contract simultaneously.

**B — Skip the model; let the orchestrator return `list[ConsolidatedArtifact]`.** Rejected. This is CAP-076A's Option C. It works, and it leaves provenance, policy identity, orchestration reason, and correlation with nowhere to live. `PromptRequest.source_consolidated_id` and `manifest.selectedArtifactId` are singular; a list breaks both anyway, so the compatibility saving is illusory.

**C — Raw `str` identifiers, consistent with the rest of the repository.** Seriously considered, and it is the conservative choice. Rejected because "consistent with the rest of the repository" here means "consistent with a weakness the repository has not yet paid for." The subsystem is new and unconsumed: it is the cheapest possible place to establish the better convention, and the typed ids serialise as plain strings, so consistency of the *JSON contract* is fully preserved.

**D — Executable policy (a `Policy` protocol with a `select()` method).** Rejected. It collapses D3: the policy would own execution, could not be serialised into a manifest, could not be governed as a versioned asset, and could not structurally forbid probabilistic ranking.

**E — Put `EngineeringContext` in `requirement_intelligence/models/`.** Rejected. `models/` holds the cross-layer canonical data model (`SourceArtifact`, `ConsolidatedArtifact`). Subsystem-owned models live inside their subsystem — `prompts/models/`, `cp1/models/`, `validation/models/`. Placing it in `models/` would also force `models/` to depend on `consolidation/`.

**F — Reuse `PromptVersion` for `PolicyVersion`.** Rejected: it would couple Engineering Context Orchestration to Prompt Governance for a value object. The duplication is real and recorded below.

---

## Consequences

### Positive

- The platform has an owner for the question "what evidence does one reasoning session receive?" — the responsibility that CAP-076 Part 1 found had none.
- Consolidation, `ConsolidatedArtifact`, `SourceArtifact`, the mappers, and the connectors are untouched.
- Reproducibility is enforced by the type system, not by review.
- Correlation (`ContextDependencies`) has a reserved home, so landing it later requires no Consolidation change.
- `LegacySelectionPolicy` lets CAP-076C prove its plumbing behaviour-identical before any policy is flipped.

### Negative, and accepted

- **Two semantic-version value objects now exist** (`PromptVersion`, `PolicyVersion`) with identical shape. Consolidating them into a shared `SemanticVersion` in `shared/` is the natural future move; doing it now would modify Prompt Governance, which this milestone forbids.
- **Two identifier conventions now coexist in the repository** — typed in this subsystem, raw `str` everywhere else. This is a deliberate, bounded inconsistency. It resolves only if the convention is adopted more widely, which is out of scope here and should be driven by need, not by symmetry.
- The subsystem is **dead code until CAP-076C**. It is tested, constructed by `PlatformContext`, and consumed by nothing. This is intentional (CAP-076A §9 Stage 2, "Orchestrator, dark") and is the price of separating a plumbing change from a behaviour change.

### Neutral

- `EvidenceBudget` counts artifacts, not tokens. A token budget would couple orchestration to a provider's tokenizer. CAP-076A §6.3 measured ~5.3k tokens for 71 artifacts, so artifact count is a serviceable proxy. If it proves too coarse, the budget is a versioned field and can change under a MAJOR policy bump.

---

## Migration Impact

**None. The repository is behaviourally identical.**

| Subsystem | Impact |
|---|---|
| Consolidation, `ConsolidatedArtifact`, `SourceArtifact` | Untouched. |
| Mappers, Connectors, Selection, CLI, API | Untouched. |
| Prompt Builder, Prompt Governance | Untouched. Prompt bytes unchanged. |
| Requirement Analysis Service | Untouched. |
| Normalization, Validation, CP1 | Untouched — no coupling to consolidation exists. |
| Execution Package, `manifest.json` | Untouched. |
| Golden Baseline | Untouched, byte-identical. |
| `PlatformContext` | Two additive construction methods. Nothing calls them. |

The contract changes that CAP-076 Part 1 identified as unavoidable — `manifest.selectedArtifactId`, `consolidated_artifact.json`, and every golden hash — are **deferred to CAP-076C**, where a behaviour change actually occurs. They are not incurred here.

---

## Future Evolution

Recorded as direction, **not authorised by this ADR**:

1. **CAP-076C — Runtime integration.** The Engineering Context Orchestrator applies a policy, `_select_consolidated` is deleted, and the golden harness *imports* the orchestrator instead of duplicating the rule. Ships with `LegacySelectionPolicy` so behaviour is provably unchanged; the flip to `DefaultOrchestrationPolicy` is a separate, isolated commit.
2. **Governed Orchestration Policy.** A `policy_loader` / `policy_registry` / `versions/*.json` / `manifest.json` structure mirroring Prompt Governance (CAP-076A §10). Worth its cost only once more than one policy is in real use.
3. **Correlation.** Populating `ContextDependencies.correlations` from a curated correlation table or bounded key-set intersection. Until then, `render_reason` states plainly that evidence is *co-selected*, and that **no correlation is asserted** — discharging Invariant 2 where a reader will see it.
4. **Grounding validation.** CAP-074B showed five hallucinated requirements passing all 13 validation rules and the CP1 gate. Widening the evidence surface widens the hallucination surface. This remains the highest-value outstanding investment and a prerequisite for evaluating whether orchestration improved anything.
5. **Shared `SemanticVersion`.** Consolidate `PromptVersion` and `PolicyVersion`.

---

## Addendum — CAP-076C Runtime Integration

- **Date:** 2026-07-10
- **Amends:** this ADR's "Consequences" and "Future Evolution" §1. The framework is no longer inert.

### What changed

The `EngineeringContextOrchestrator` was introduced and wired into the runtime. `_select_consolidated` is deleted. The runtime path is now:

```
SourceArtifacts → Consolidation → EngineeringContextOrchestrator → EngineeringContext
                → RequirementPromptBuilder → Gemini → Validation → CP1 → Execution Package
```

`RequirementPromptBuilder.build` and `RequirementAnalysisService.analyze` take an `EngineeringContext`. `PlatformContext` is the sole construction point for the orchestrator, the builder, and both policies. The golden harness *imports* the orchestrator instead of duplicating the selection rule, discharging the duplication this ADR's Problem section named.

**`LegacySelectionPolicy` is the active policy.** `DefaultOrchestrationPolicy` is constructed but never bound by default. The orchestrator executes only the rules Legacy declares (`single_largest`, `group_order`) and **raises** on `coverage_guaranteed` and `risk_then_record_id` rather than approximating them: a policy that is silently half-applied is worse than no policy. Activating them is CAP-076D.

### Behavioural result

Prompt bytes, the LLM request, selection, normalization, validation, CP1, and every pre-existing execution artifact are unchanged. Verified by executing the CLI at `HEAD` and at the working tree over the same FILE-mode inputs: `prompt.txt` and `llm_request.json` are byte-identical, and `consolidated_artifact.json` differs only in the `artifactId` uuid4 the mappers mint per run — a pre-existing non-determinism that `HEAD` also exhibits against itself.

The contract changes this ADR deferred to CAP-076C (`manifest.selectedArtifactId`, `consolidated_artifact.json`, golden hashes) were **not incurred**, because `LegacySelectionPolicy` selects the same single group. They fall due in CAP-076D.

### Model changes

`ENGINEERING_CONTEXT_VERSION` advanced `1.0 → 1.1`. `ContextProvenance` is now built from `ContextContribution` records, each carrying its group's `module`, `consolidation_reason`, `artifact_count`, and — new — an `inclusion_reason` naming the rank the group achieved, the keys it was ranked by, and the policy that admitted it. `candidate_group_count` records how many groups were *ranked*, not merely how many contributed. Without it, "selected the largest group" is unfalsifiable. `contributing_consolidated_ids` and `contributing_group_count` survive as derived properties. No 1.0 context was ever serialised, so no stored artifact is invalidated.

`REASON_TEMPLATE_FIELDS` gained `candidates`, distinct from `groups`. `LegacySelectionPolicy`'s reason template now reads "the largest of {candidates} consolidation group(s)" — with `{groups}` it rendered "the largest of 1", concealing the 22 groups it beat.

### New execution artifact

`engineering_context.json` is written for every run, including dry runs, and registered in `manifest.json` with its SHA-256 and byte count alongside every other artifact. The manifest additionally names `engineeringContextId`, `orchestrationPolicyId`, and `orchestrationPolicyVersion`, so a historical package can be attributed to the rules that produced it without opening another file. The orchestrator constructs; `ExecutionWriter` writes; `EngineeringContextArtifactBuilder` projects. No ownership is duplicated.

The artifact makes the CAP-074B defect legible for the first time: on the repository's own fixtures it records `candidateGroupCount: 23`, `contributingGroupCount: 1`, and `evidenceCounts: {functional: 0, security: 0, quality: 71}`.

### Known residue

`execution_metrics.engineering_metrics` still ranks groups by size to compute `selected_artifact_rank`, mirroring rather than reading the policy. It decides nothing — the orchestrator remains the only orchestration point — but the number becomes misleading the moment a risk-ranked policy is activated. CAP-076D must read the rank the orchestrator already records. *(Discharged in CAP-076D.)*

---

## Addendum — CAP-076D Multi-Source Activation

- **Date:** 2026-07-10
- **Amends:** the CAP-076C addendum. `DefaultOrchestrationPolicy` is now the active runtime policy, and the framework is no longer behaviour-preserving.

### What changed

`PlatformContext.create_engineering_context_orchestrator` binds `DefaultOrchestrationPolicy`. The orchestrator now executes the rules that policy declares — `coverage_guaranteed` selection, `risk_then_record_id` ordering, and a per-domain evidence budget — where CAP-076C raised on them. **`default_policy.py` is unmodified**: the behaviour change arises solely from activation, which is what makes the diff attributable.

`LegacySelectionPolicy` is retained, unchanged, and remains fully executable. It is no longer dead code awaiting deletion; it is the **control arm**. The golden baseline runs both policies over the same candidates, which is the only way to prove that a difference in a reasoner's evidence came from the policy rather than from the code executing it.

### The orchestration algorithm

Four ordered steps, all deterministic:

1. **Rank** every candidate by the policy's keys (`risk_level_desc`, `artifact_count_desc`, `consolidated_id_asc`), terminated by the tie-breaker.
2. **Allocate** the evidence budget across the three domains by integer **water-filling** (max-min fairness): a domain's ceiling is `min(maxArtifactsPerDomain, available)`; if the ceilings fit the total, each takes its ceiling; otherwise the total is shared equally, with under-demanding domains settled at their ceiling and their surplus returned to the pool. An indivisible remainder is granted one unit at a time in canonical domain order.
3. **Select** per domain, walking the ranking and admitting each group's evidence up to the remaining allocation. A group larger than its remaining budget **contributes its highest-ordered artifacts rather than being skipped** — dropping a CRITICAL 71-finding group for not fitting a 25-artifact budget would let the budget silently override the ranking.
4. **Order** each assembled domain under the policy's ordering rule, across all contributing groups.

Water-filling exists because the naive alternative — cap each domain, walk in order, stop at the total — lets the first domain starve the last, which is risk R8 and the CAP-074B defect wearing a different hat.

`evidence_ordering` therefore decides two things at once, and deliberately: *which* artifacts survive the budget, and *how* they read. Under `risk_then_record_id` the most severe survive.

### Subject derivation

A multi-source context takes its subject from its **highest-ranked contributing group**, not from a concatenation of every contributor's module. Joining ten modules with `" + "` yields a label no reader can use and a context-id slug no manifest can display. More importantly, under a ranking both policies share, the rank-1 group is the one `single_largest` would also have chosen — so activating coverage **adds evidence to a context without moving its subject**, which is the claim CAP-076D makes and the golden baseline asserts.

### Model changes

`ENGINEERING_CONTEXT_VERSION` advanced `1.1 → 1.2`. `EngineeringContext` gained four sections, each recording decisions that were previously either implicit or absent:

| Section | Records |
| --- | --- |
| `ranking` | Every candidate: rank, risk, the rendered score for each declared key, whether it was selected, and **why it was admitted or excluded**. |
| `coverage` | Per domain: whether evidence existed among the *candidates*, whether it reached the context, how much, and why. |
| `evidenceBudget` | Per domain: available, allocated, used. |
| `grounding` | Observational: evidence domains, counts, and the source-system distribution. |

`ContextContribution` now separates `artifactCount` (contributed) from `candidateArtifactCount` (carried), which is what makes truncation visible; recording only the first would misreport a truncated group as small. It also carries the group's `rank` and its per-domain contribution.

`ContextCoverage` deliberately holds **two** booleans that a careless model would merge. `ruleSatisfied` asks whether the policy's declared coverage rule was met; `allPresentCategoriesRepresented` asks whether every domain that had evidence actually reached the reasoner. A legacy run reports `true` and `false` respectively — satisfying its rule while losing two domains is *exactly* how the CAP-074B defect passed unnoticed, and collapsing the two would let it pass unnoticed again.

`EngineeringContext`'s validator now checks `coverage`, `evidenceBudget`, `grounding` and `ranking` against the evidence they claim to describe, rather than against each other. A projection that miscounts cannot be constructed.

### Component boundary changes

`EngineeringContextBuilder.build` now receives the assembled `ContextEvidence` and per-group `GroupContribution` **counts**, rather than the contributing `ConsolidatedArtifact`s to flatten. A domain's evidence is ordered *across* its contributing groups, so no group owns a contiguous slice of it; a builder handed per-group lists would silently undo the policy's ordering rule when it concatenated them. Giving it nothing to reorder keeps "the builder never reorders" structural rather than conventional. The builder still enforces the budget as an input contract and never truncates.

### Contract changes now incurred

The changes this ADR deferred twice fall due here.

- `manifest.json` gains `selectionStrategy`, `candidateGroupCount`, `contributingGroupCount`, `contributingConsolidatedIds`, `evidenceDomainsRepresented`, `coverageComplete`, `contextArtifactCount`. `selectedArtifactId` survives and now names the **primary** contributing group.
- `engineering_context.json` advances to artifact version `2.0.0` — major, because a reader of `1.0.0` would misread a truncated group's `artifactCount` as the group's size.
- `CONTEXT_ORCHESTRATION_VERSION` advances `1.0.0 → 2.0.0`.
- Golden hashes for `prompt.txt` change, because evidence ordering changed. Prompt *wording* does not: `RequirementPromptBuilder`, `prompt_constants`, and Prompt Governance are untouched.

### Residue discharged

`execution_metrics.engineering_metrics` now **reads** `context.ranking.rank_of(...)` instead of re-sorting the consolidated artifacts by size. Its domain counts describe the engineering context — the evidence a reasoner received — not the primary group. The orchestrator is the single source of truth for its own decisions.

### Behavioural result

Measured on the repository's FILE-mode fixtures (387 source artifacts → 23 groups):

| | `LegacySelectionPolicy` | `DefaultOrchestrationPolicy` |
| --- | --- | --- |
| Contributing groups | 1 of 23 | 10 of 23 |
| Functional / Security / Quality | 0 / 0 / 71 | 4 / 25 / 25 |
| Domains represented | 1 | 3 |
| Source systems reaching Gemini | `sonarqube` | `jira`, `owasp_zap`, `sonarqube` |

In API mode (372 artifacts → 47 groups) all three domains contest the budget and water-filling allocates 20/20/20.

Live Gemini runs under both policies pass Validation (13 rules, 0 issues) and CP1 (`pass`, 0 findings) identically — Validation and CP1 are untouched and must not react to the policy. The requirements themselves change character: Legacy's "security requirements" are inferred from SonarQube code smells (*"replace generic catch-all blocks"*), because no security evidence reached the model. Default's are grounded in the OWASP ZAP findings that were there all along (*"implement the 'X-Frame-Options' header … to prevent clickjacking"*).

### What this does not fix

Future Evolution §4 stands, and grows more urgent. CAP-074B showed hallucinated requirements passing all 13 validation rules and the CP1 gate. Widening the evidence surface widens the hallucination surface. `grounding` metadata is **observational only** — Validation and CP1 do not read it, by construction (Stage 7). Turning grounding into an enforced check is the next milestone's work, not this one's.
