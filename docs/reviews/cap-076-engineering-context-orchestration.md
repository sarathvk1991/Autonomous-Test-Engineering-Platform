# CAP-076 Part 1 — Engineering Context Orchestration: Architecture Review & Design

**Status:** Architecture review. No code written. No ADR, model, Consolidation, or Selection change made.
**Predecessor:** `docs/reviews/cap-074b-requirement-evidence-investigation.md`, `docs/proposals/cross-source-consolidation-and-selection.md`
**Outcome:** One architecture recommended. Requires a new ADR before Part 2.
**Terminology:** Canonicalised by CAP-076A (2026-07-10). This document previously used *Engineering Context Assembly / Context Assembler / Assembly Policy / Assembly Reason*; those terms are retired.
**Implementation status:** CAP-076B (2026-07-10) landed §9 Stages 1–2 — the canonical model, typed identity model, policy framework, and builder — governed by **ADR-0015**. Nothing consumes them; runtime behaviour is unchanged. Stages 0 (ingestion-level test), 3, and 4 remain open. The recommendation in §4.1 is **accepted**.

---

## 0. Canonical Terminology

CAP-076A promotes the following to canonical architectural vocabulary. These are **documentation terms**. Implementation class names remain deferred to Part 2.

| Canonical term | Meaning | Retired synonym |
|---|---|---|
| **Engineering Context Orchestration** | The subsystem, and the architectural stage, sitting between Consolidation and Analysis. | Engineering Context Assembly |
| **Engineering Context Orchestrator** | The component that executes that stage. | Context Assembler |
| **Orchestration Policy** | The governed, versioned rule set deciding coverage, ranking, and evidence budget. | Assembly Policy |
| **Orchestration Reason** | The single explainable sentence recording why a context was composed as it was. | Assembly Reason |
| **`EngineeringContext`** | The canonical model the orchestrator produces. New; additive. | — |
| **`ConsolidatedArtifact`** | The canonical model Consolidation produces. **Unchanged.** Becomes an *input* to orchestration. | — |

### 0.1 Disambiguation — two senses of "orchestration"

The word already carries a load-bearing meaning in this repository, and the new vocabulary collides with it. The collision is resolved by qualifier, never by context alone:

- **Analysis-execution orchestration** — the established sense. ADR-0002, ADR-0003 and ADR-0011 designate `ResponseNormalizer`, `ResponseValidator`, `CP1Service` and `RequirementAnalysisService` as *single orchestration boundaries*: components that sequence collaborators and own no policy. `RequirementAnalysisService` "performs orchestration only" in this sense.
- **Engineering Context Orchestration** — the new sense. Composing evidence into a context under a governed policy. This stage **does** own policy; that is its entire purpose.

They are different kinds of thing: one sequences calls, the other decides content. Wherever ambiguity is possible, prose in this repository must use the full term *Engineering Context Orchestration* rather than the bare noun.

A note on why the rename is nonetheless an improvement: `assembly` was itself already overloaded, denoting dependency wiring in `cp1/response/cp1_composition.py` ("the composition root owns only assembly") and in `docs/architecture/normalization-assembly-contract.md`. Both candidate words were taken. The chosen one is at least taken by a *neighbouring* concept rather than an unrelated one, and it is disambiguated above.

---

## 1. Current Architecture Review

### 1.1 Pipeline as built

```
source-registry.json
   │
   ├─ JiraConnector   ─► JiraMapper   ─┐
   ├─ SonarConnector  ─► SonarMapper  ─┼─► list[SourceArtifact]
   └─ ZapConnector    ─► ZapMapper    ─┘          │
                                                  ▼
                                        ConsolidationEngine
                                                  │
                                        list[ConsolidatedArtifact]
                                                  │
                                   _select_consolidated()  ◄── lives in the CLI script
                                                  │
                                        ONE ConsolidatedArtifact
                                                  │
                                        RequirementPromptBuilder
                                                  │
                                    PromptRequest ─► LLMRequest ─► Gemini
```

### 1.2 Responsibility map

| Subsystem | Owns | Explicitly does not own | Evidence |
|---|---|---|---|
| `ConnectorRegistry` | Dynamic load of connector+mapper pairs; execution of all enabled sources | Grouping, ranking, prompt | `registry/connector_registry.py` |
| `JiraConnector` / `SonarConnector` / `ZapConnector` | Raw record retrieval (FILE or API mode) | Interpretation of any field | `connectors/` |
| `JiraMapper` / `SonarMapper` / `ZapMapper` | Shape translation, raw → `SourceArtifact`; metadata preservation | Grouping, correlation, scoring | `mappers/*.py` |
| `consolidation_rules.py` | Pure, deterministic grouping key derivation; severity normalisation; risk rollup; ID minting | I/O, source branching, selection | `consolidation/consolidation_rules.py` |
| `ConsolidationEngine` | Bucketing artifacts by grouping key; splitting each bucket into functional/security/quality | Cross-group relations, ranking, selection | `consolidation/consolidation_engine.py:34-110` |
| **Selection** | Choosing one artifact to analyse | — | `scripts/run_requirement_analysis.py:277-300` |
| `RequirementPromptBuilder` | Rendering *one* `ConsolidatedArtifact` into the `{artifact_context}` block; injecting it into the governed template | Prompt wording, version selection, governance | `prompts/requirement_prompt_builder.py:165-239` |
| `PromptRegistry` / template contract | Governed prompt text, SHA verification, exactly-one-placeholder invariant | Data rendering | `prompts/framework/prompt_template_contract.py:65` |
| `RequirementAnalysisService` | Analysis-execution orchestration of one analysis over one artifact (see §0) | Validation, persistence, ingestion | `analysis/requirement_analysis_service.py:92` |
| `ExecutionWriter` / `manifest_builder` | Persisting the package; `selectedArtifactId` | Selection policy | `execution/manifest_builder.py:53` |

### 1.3 The one ownership anomaly

**Selection has no owner.** `_select_consolidated` is a module-level private function inside `scripts/run_requirement_analysis.py` — a script whose own docstring states it "contains no business logic." Choosing which engineering evidence the LLM reasons over is the single most consequential policy decision in the layer, and it is implemented as eleven lines of CLI glue:

```python
# scripts/run_requirement_analysis.py:284-288
def _key(c):
    total = len(c.functional_artifacts) + len(c.security_artifacts) + len(c.quality_artifacts)
    return (-total, c.consolidated_id)
return sorted(consolidated, key=_key)[0]
```

That same rule is **duplicated verbatim** in the golden-baseline harness (`tests/productization/conftest.py:162-165`) rather than imported, so the two can drift silently. This is the structural gap CAP-076 must close.

---

## 2. Root Cause Validation

All findings below were re-derived by executing the repository's own pipeline in `EXECUTION_MODE=FILE` against `requirement_intelligence/input/`.

**Measured result:** 387 `SourceArtifact`s (300 SonarQube, 83 OWASP ZAP, 4 JIRA) → 23 `ConsolidatedArtifact`s → **0 groups contain more than one source category**. Selected artifact: `cons-component-…BadLoginPage.java`, containing 0 functional, 0 security, 71 quality artifacts.

The live API-mode run recorded in CAP-074B (375 artifacts → 47 groups → 0 multi-source → 71 quality-only selected) reproduces identically. The defect is mode-independent.

### 2.1 Why does JIRA never appear with Sonar?

Because they match **different rungs of the cascade**, and the rung is part of the group's identity.

`derive_grouping_key` (`consolidation_rules.py:165-184`) is a first-match cascade: `component → tag → endpoint → risk`.

- `SonarMapper` is the only mapper that populates `component` (`sonar_mapper.py:110`, `component=issue.get("component")` — a Sonar file path such as `Automation-POC:src/test/java/.../BadLoginPage.java`). All 300 Sonar artifacts stop at rung 1.
- `JiraMapper` never sets `component`. It sets `url=issue.get("self")` (`jira_mapper.py:113`). JIRA labels were empty in the dataset, so all 4 JIRA artifacts fell through tag to rung 3, `endpoint`.

Measured rung distribution:

```
component <- sonarqube : 300
tag       <- owasp_zap :  83
endpoint  <- jira      :   4
```

The engine buckets on `identity = (key.dimension.value, key.value)` (`consolidation_engine.py:67`). Two artifacts on different dimensions cannot collide even if their values were identical strings. JIRA and Sonar are therefore *structurally* incapable of sharing a group.

A second, independent failure compounds it: JIRA's rung-3 value is its per-issue REST self-link, which is unique by construction.

```
SCRUM-24 → endpoint /rest/api/2/issue/10055
SCRUM-13 → endpoint /rest/api/2/issue/10044
SCRUM-12 → endpoint /rest/api/2/issue/10043
SCRUM-11 → endpoint /rest/api/2/issue/10042
```

Four issues, four singleton groups. JIRA cannot even group with *itself*.

### 2.2 Why does ZAP never appear with Sonar?

Same mechanism, different rung. `ZapMapper` sets no `component`; it derives `tags` from the ZAP alert's `tags` dict (`zap_mapper.py:61-67`), which is always populated with OWASP/CWE/policy labels (`OWASP_2021_A05`, `CWE-1021`, `POLICY_PENTEST`, …). All 83 ZAP artifacts stop at rung 2.

Sonar stops at rung 1. `("component", …)` and `("tag", …)` never share an identity tuple.

Note that ZAP artifacts *do* carry a real endpoint (`location=alert.get("url")`, `zap_mapper.py:99`) and Sonar rule tags exist too — but neither is ever consulted, because the cascade discards every dimension after the first match.

### 2.3 Why does grouping prevent multi-source contexts?

Not because the grouping logic is wrong, but because **its output shape cannot represent an artifact that belongs to more than one dimension.**

Three properties combine:

1. **First-match** — `derive_grouping_key` returns a single `GroupingKey`, discarding all other dimensions the artifact could populate.
2. **Dimension-scoped identity** — `(dimension, value)` is the bucket key, so cross-dimension merging is impossible by construction.
3. **No cross-group linkage** — `ConsolidatedArtifact.related_artifact_ids` exists on the canonical model (`consolidated_artifact.py:74-77`) but the engine hard-codes it to `[]` with an acknowledging TODO (`consolidation_engine.py:106-108`). There is no escape hatch.

The engine *does* split each group into functional/security/quality (`consolidation_engine.py:82-94`) — the multi-domain container is fully built and ready. It is simply never filled, because no group is ever multi-domain. The three-way split is dead capability.

This is a **modelling limitation, not a coding error.** Every function in `consolidation_rules.py` does exactly what its docstring promises.

### 2.4 Why does selection always prefer Sonar?

`_select_consolidated` ranks on `-(total artifact count)` and nothing else. Sonar contributes 300 of 387 artifacts (78%), concentrated per source file — the largest Sonar group holds 71 artifacts. The largest non-Sonar group is a ZAP tag group with 36. A JIRA singleton holds 1.

Ranking by raw count is a ranking by *source verbosity*. A `Critical` JIRA defect can never outrank 71 `MAJOR` code smells, because severity is not in the sort key at all. Sonar wins deterministically, on every dataset where a static analyser is enabled.

### 2.5 Why is the Prompt Builder behaving correctly?

Because it is a faithful renderer with no selection authority. `_render_artifact_context` (`requirement_prompt_builder.py:191-212`) unconditionally emits all three section headers and renders each of the artifact's three lists, substituting `(none provided)` where a list is empty (`prompt_constants.py:134`).

Given the selected artifact, the *only* correct rendering is:

```
### Functional Artifacts
(none provided)
### Security Findings
(none provided)
### Quality Findings
- (sast) java:S4144 [...]   × 71
```

The builder is honest about the emptiness. It is reporting the defect, not causing it. It also cannot fix it: the governed template exposes exactly one `{artifact_context}` placeholder (`prompt_template_contract.py:65`), enforced at parse time, and the builder's `build()` signature accepts exactly one `ConsolidatedArtifact`.

### 2.6 Why is Gemini only a secondary issue?

Gemini receives precisely the bytes the prompt contains — verified byte-for-byte in CAP-075. The prompt instructs it to "Analyze the security findings" and "Analyze the functional requirements" (`prompt_constants.py:59-73`) while supplying `(none provided)` for both. Any functional or security requirement in the response is, by construction, ungrounded.

CAP-074B established that five such hallucinated requirements passed all 13 validation rules and the CP1 gate with zero findings. That is a **real, separate defect** — the platform has no grounding rule — but it is downstream. Fixing the model or the prompt cannot conjure evidence that was discarded three stages earlier. Fixing the context orchestration will, however, *widen the surface* for ungrounded inference, which makes the grounding gap a prerequisite rather than an afterthought (§9, §11).

### 2.7 Why the regression suite never caught this

`tests/productization/conftest.py:158` begins the "golden end-to-end pipeline" at `engine.consolidate(GOLDEN_SOURCE_ARTIFACTS)` — **connectors and mappers are never executed.** The fixture hand-constructs `SourceArtifact`s with `component="authentication"` on every record, and says so explicitly:

```python
# tests/productization/fixtures/golden_dataset.py:362
# (all artifacts share component="authentication" so they form one group)
```

The golden dataset fabricates the one condition real ingestion can never produce. `EXPECTED_CONSOLIDATED_COUNT = 1`, and the resulting group is richly multi-domain. The baseline therefore validates a pipeline the platform does not have. This is the highest-severity secondary finding in this review.

---

## 3. Engineering Context — Conceptual Definition

> **An Engineering Context is the complete, bounded set of engineering evidence required to reason about one subject of analysis in a single reasoning session.**

It is not a source, a file, a mapper, a connector, or a `ConsolidatedArtifact`. A `ConsolidatedArtifact` answers *"which records happen to share an attribute?"* An Engineering Context answers *"what does a reasoner need to know to derive requirements about this subject?"*

### 3.1 Conceptual model

```
EngineeringContext
├── Subject               what is being reasoned about (e.g. "Authentication")
│     ├── label
│     ├── business area
│     └── subject basis   why this subject was chosen (component / capability / risk)
│
├── Evidence              the reasoning material, by domain
│     ├── Functional      user stories, epics, defects              (intent)
│     ├── Security        ZAP alerts, security-tagged findings      (threat)
│     └── Quality         Sonar findings, maintainability signals   (integrity)
│
├── Context               the engineering surface the evidence sits on
│     ├── components / modules
│     ├── endpoints / APIs
│     └── rolled-up risk posture
│
├── Dependencies          what links the evidence together
│     ├── correlations    (artifact ↔ artifact, with a stated basis)
│     ├── related contexts
│     └── traceability    every evidence item → its source record
│
└── Provenance            how this context came to exist
      ├── contributing consolidation groups
      ├── orchestration policy + policy version
      └── orchestration reason (one explainable sentence)
```

### 3.2 Governing invariants

1. **Completeness before relevance.** A context that omits an entire evidence domain that *exists in the run* is incomplete, even if every included item is highly relevant. Today's context fails here.
2. **Correlation is asserted, never implied.** Evidence placed side by side must not be presented as related unless a correlation basis is recorded. Co-presence is not co-reference. *(This is the central risk of every option in §4.)*
3. **Bounded.** A context must fit one reasoning session. Unbounded evidence is not a context; it is a data dump.
4. **Traceable.** Every element resolves to a `(source_system, source_record_id)`.
5. **Deterministic and explainable.** Within a single run, the orchestrator is a pure function of its input: no I/O, no clock, no AI, no randomness. Every composition decision can be stated in a sentence.
6. **Renderable without prompt change.** A context must project onto the existing three-section context block, so the governed prompt template is untouched.
7. **Reproducible.** *(Added by CAP-076A.)* Given identical repository inputs, Engineering Context Orchestration shall always produce an identical `EngineeringContext` — identical evidence **ordering**, identical evidence **selection**, identical **identifiers**, and an identical **Orchestration Reason** — across processes, machines, and time. **No probabilistic ranking is permitted.**

#### 3.2.1 Why Invariant 7 is not a restatement of Invariant 5

Invariant 5 is *determinism*: one function, one input, one output. Invariant 7 is *reproducibility*: that guarantee must survive leaving the process. A function can be perfectly deterministic in-process and still yield different bytes on the next run, and this repository already contains exactly that hazard.

All three mappers mint identity non-reproducibly:

```python
# jira_mapper.py:103, sonar_mapper.py:102, zap_mapper.py:91 — identical in all three
artifact_id=str(uuid4()),
```

`SourceArtifact.artifact_id` therefore differs on every run. Consolidation is insulated from this only by accident of design: `build_consolidated_id` derives identity from the *grouping key*, never from `artifact_id` (`consolidation_rules.py:200-207`). The golden-baseline harness works around the same hazard by comparing content "excluding run-specific provenance such as IDs and timestamps" (`tests/productization/test_golden_baseline.py:7`).

Invariant 7 converts that accident into a rule. Concretely, it forbids the Engineering Context Orchestrator from:

- deriving a context identifier, an ordering, or a tie-break from `artifact_id`, any UUID, `hash()` (PYTHONHASHSEED-dependent), object identity, or wall-clock time;
- iterating a `set` or an unordered `dict` where the iteration order can influence selection or ordering;
- ranking by any score with a probabilistic, learned, or model-derived component.

Every ranking key must be a total order over values the source data actually carries — `risk_level`, artifact count, `consolidated_id`, `source_record_id` — so that ties break identically everywhere. This is what makes a golden hash over `engineering_context.json` meaningful at all; without Invariant 7, the Part 2 re-baseline (§9 Stage 4) could not be verified.

### 3.3 Worked example (the intent)

```
Subject: Authentication
  Functional : AUTH-1 epic, AUTH-2 login story, AUTH-9 lockout defect
  Security   : ZAP "Session ID in URL" on /login, ZAP "Missing CSRF token"
  Quality    : Sonar S2068 hard-coded password in AuthService.java
  Context    : component=authentication; endpoints /login,/logout; risk=CRITICAL
  Dependencies: ZAP:/login ↔ JIRA AUTH-2 (basis: endpoint); Sonar:AuthService.java ↔ AUTH-1 (basis: curated component map)
```

Nothing in the repository can produce this today. §4 asks how it could.

---

## 4. Architectural Alternatives

A structural constraint bounds every option: **no attribute in a ZAP alert or a JIRA issue names a Java source file.** Sonar ↔ JIRA correlation cannot be inferred from the data as it stands. Any option claiming otherwise is claiming a heuristic it cannot honour.

### Option A — Cross-source grouping (multi-dimensional keys in Consolidation)

Replace the first-match cascade with a key *set*: each artifact emits every dimension it can populate; two artifacts group when their key sets intersect.

```
Sonar issue → {component: AuthService.java, tag: java:S2068}
ZAP alert   → {tag: CWE-525, endpoint: /login}
JIRA story  → {tag: login,   endpoint: /login}
```

| Criterion | Assessment |
|---|---|
| Complexity | High. Set-intersection grouping is transitive: A~B on tag, B~C on endpoint ⇒ does A~C? Without an explicit no-chaining rule, one group swallows the corpus. |
| Determinism | Preserved only with a total ordering over dimensions and a stated chaining rule. Fragile. |
| Backward compat | **Breaks.** `build_consolidated_id` is a pure function of a single-dimension key (`consolidation_rules.py:200-207`). A multi-dimension group has no such ID. Every `consolidated_id`, every `selectedArtifactId`, every golden hash changes. |
| Performance | O(n²) worst case on intersection, vs today's O(n) dict bucketing. 387 artifacts is fine; 40k is not. |
| Testability | Poor. The failure mode (runaway merge) is dataset-dependent and invisible in unit tests. |
| Scalability | Poor. |
| Extensibility | Moderate. |

**It does not solve the primary problem.** It links ZAP↔JIRA on `/login`. It does nothing for Sonar↔JIRA, which is the valuable link. It pays the highest compatibility cost for the smaller half of the benefit.

### Option B — Engineering Context Orchestration after Consolidation ★

Introduce a new, owned subsystem between Consolidation and Analysis. Consolidation keeps producing groups exactly as it does today. The **Engineering Context Orchestrator** consumes `list[ConsolidatedArtifact]` and applies a *governed orchestration policy* to produce one `EngineeringContext`.

```
list[SourceArtifact] ─► ConsolidationEngine ─► list[ConsolidatedArtifact]
                                                          │
                                              EngineeringContextOrchestrator (new)
                                              ├─ orchestration policy (governed)
                                              ├─ coverage rule
                                              ├─ risk-aware ranking
                                              └─ evidence budget
                                                          │
                                                  EngineeringContext
                                                          │
                                              RequirementPromptBuilder
```

The default policy — *coverage-guaranteed, risk-ranked, budget-bounded*:

1. For every `SourceCategory` that produced at least one artifact in this run, the context **must** contain evidence from it. (Fixes the defect directly.)
2. Within a category, groups rank by `risk_level` first, then artifact count, then `consolidated_id`. (A `CRITICAL` defect outranks 71 code smells.)
3. Evidence is truncated to a per-category budget, deterministically, highest-risk first.
4. `orchestration_reason` states, in one sentence, which groups contributed and why.

| Criterion | Assessment |
|---|---|
| Complexity | Moderate, and *contained*. One new package, one new model, one policy object. Nothing existing changes shape. |
| Determinism | Strong. Pure function of an ordered input list. No I/O, no AI. |
| Backward compat | **High.** Consolidation, `ConsolidatedArtifact`, `consolidated_id`, mappers, connectors, and `consolidation_rules.py` are untouched. |
| Performance | O(n log n). Negligible. |
| Testability | Strong. Policy is injectable; coverage and budget are directly assertable. Enables the ingestion-level test the golden baseline lacks (§2.7). |
| Scalability | Strong. Budget is enforced at orchestration, so prompt size is bounded by policy, not by dataset size. |
| Extensibility | Strong. Correlation (Option A's real value) later becomes an *enrichment step inside the orchestrator*, populating `dependencies`, without touching Consolidation. |

The critical property: `EngineeringContext` is a **structural superset** of `ConsolidatedArtifact` (id, subject label, business area, risk level, three evidence lists, reason). Rendering it through the existing three-section context block requires **no prompt wording change and no template change** — the `{artifact_context}` placeholder invariant holds. When exactly one group exists, the orchestrator degenerates to identity and the rendered prompt is byte-identical to today's.

### Option C — Selection orchestrates multiple ConsolidatedArtifacts

Keep everything; change `_select_consolidated` to return `list[ConsolidatedArtifact]`, and have the Prompt Builder loop over the list.

| Criterion | Assessment |
|---|---|
| Complexity | Lowest — a few lines. |
| Determinism | Preserved. |
| Backward compat | Moderate. `PromptRequest.source_consolidated_id` (singular) and `manifest.selectedArtifactId` (singular) both break. |
| Performance | Negligible. |
| Testability | Weak. The rule lives in a CLI script and is duplicated in the test harness. Policy is untestable in isolation. |
| Scalability | Weak. Prompt size unbounded; no budget anywhere to enforce. |
| Extensibility | Weak. Correlation, provenance, and dependencies have nowhere to live — there is no object to hang them on. |

Option C is Option B with the new subsystem deleted and its responsibility smeared across a script and a prompt builder loop. It delivers the same immediate user-visible outcome and **entrenches the ownership violation of §1.3**. It is the right *shape* of answer, implemented in the wrong *place*.

### 4.1 Recommendation — Option B

**Adopt Option B (Engineering Context Orchestration after Consolidation), with Option A deferred as a future enrichment step inside the orchestrator.**

Reasoning:

1. **It fixes the actual defect.** Coverage guarantee, not correlation inference, is what puts JIRA and ZAP in front of the model. Correlation is a separate, later, harder question — and one that cannot be evaluated until a working multi-source baseline exists.
2. **It respects every existing ownership boundary.** Consolidation groups. Orchestration composes. Prompt renders. Nothing gains a second responsibility.
3. **It creates the owner that §1.3 shows is missing.** Selection policy stops being CLI glue and becomes a governed, injectable, unit-testable subsystem — with the immediate benefit that the golden harness can *import* it instead of duplicating it.
4. **It is the only option with a place to put correlation later.** `EngineeringContext.dependencies` is where Option A's key-set intersection eventually lands, as an enrichment pass over an already-orchestrated context, where runaway merging is bounded by the budget rather than by luck.
5. **It preserves prompt governance and the golden prompt bytes** for the single-group case, which no other option does.

Option C is not wrong in outcome; it is wrong in ownership, and this milestone exists precisely because ownership drift is what produced the defect.

---

## 5. Subsystem Impact Matrix

| Subsystem | Code | Tests | Docs | ADR | Rationale |
|---|:--:|:--:|:--:|:--:|---|
| **Engineering Context Orchestration** (new) | ✅ new | ✅ new | ✅ new | ✅ new | The entire deliverable. |
| `EngineeringContext` model (new) | ✅ new | ✅ new | ✅ | ✅ | New canonical model; additive. |
| `ConsolidationEngine` | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** Groups remain groups. |
| `consolidation_rules.py` | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** Cascade preserved. |
| `ConsolidatedArtifact` | ⬜ | ⬜ | ➖ | ⬜ | Untouched. Docstring may note it is now an orchestration *input*. |
| `SourceArtifact` | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** |
| Connectors | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** API + FILE mode unaffected. |
| Mappers | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched** in Part 2. (A future `component` enrichment is out of scope.) |
| Selection (`_select_consolidated`) | ✅ **removed** | ✅ | ✅ | ✅ | Responsibility migrates into the orchestrator. |
| `run_requirement_analysis.py` | ✅ | ✅ | ✅ | ⬜ | Calls the orchestrator; keeps `--artifact-id` as a policy override. |
| `PlatformContext` | ✅ | ✅ | ⬜ | ⬜ | Gains `create_context_orchestrator()`. Construction hub, per existing pattern. |
| `RequirementPromptBuilder` | ✅ signature | ✅ | ✅ | ⬜ | `build(context)` instead of `build(artifact)`. **Rendering logic and output bytes unchanged for single-group contexts.** |
| Prompt template / `PromptRegistry` | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** One `{artifact_context}` placeholder; wording frozen (ADR-0014). |
| `prompt_constants.py` framing | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** Section headers and line formats reused verbatim. |
| `RequirementAnalysisService` | ✅ signature | ✅ | ✅ | ⬜ | `analyze(context)`. Orchestration semantics identical. |
| `PromptRequest` / `AnalysisResult` | ✅ additive | ✅ | ➖ | ⬜ | `source_consolidated_id` → `source_context_id` (or additive sibling). Contract decision for the ADR. |
| Normalization | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** Operates on `LLMResponse` only — verified: no reference to consolidation. |
| Validation | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** `ValidationInput` = `AnalysisResult` + `NormalizationResult`. |
| CP1 | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** `CP1Input` carries `validation_result`; never sees a consolidated artifact. |
| Execution Package | ✅ | ✅ | ✅ | ⬜ | `manifest.selectedArtifactId`, `consolidated_artifact.json`, `engineering_metrics`. Contract change. |
| Golden Baseline | ✅ | ✅ | ✅ | ⬜ | Re-baseline. Harness must **import** selection, not duplicate it, and must exercise connectors+mappers. |
| Governance Dashboard | ➖ | ⬜ | ⬜ | ⬜ | Verify it reads no `selectedArtifactId`. |

Legend: ✅ change required ・ ➖ verify / possibly minor ・ ⬜ untouched

---

## 6. Repository Impact Analysis

### 6.1 Contract surfaces that break

Three, and only three:

1. **`PromptRequest.source_consolidated_id`** — becomes a context id. Additive alternative: keep the field, add `source_context_id`, deprecate later. *ADR decision.*
2. **`manifest.json → selectedArtifactId`** (`execution/manifest_builder.py:53`) — a bundle has an orchestration-assigned id, plus a list of contributing group ids. *ADR decision: `selectedArtifactId` + `contributingArtifactIds[]`, or a versioned manifest schema bump.*
3. **`consolidated_artifact.json`** (`execution/execution_writer.py:112`) — becomes `engineering_context.json`, or is written alongside it. Every golden SHA-256 changes either way.

### 6.2 Untouched, and verified so

Grepped: `requirement_intelligence/validation/` and `requirement_intelligence/normalization/` contain **zero** references to `consolidated`, `ConsolidatedArtifact`, or `SourceArtifact`. `CP1Input` carries only a `validation_result`. The three subsystems the brief asks to protect are already structurally isolated from consolidation. No effort is required to keep them unchanged; the architecture already guarantees it.

### 6.3 Prompt-size consequence — measured

| | chars | ≈ tokens |
|---|---:|---:|
| Today's selected artifact (71 Sonar findings) | 21,202 | 5,300 |
| Naive union of the top group per category | 39,269 | 9,817 |

An unbudgeted coverage bundle nearly doubles the prompt on this small dataset alone. The evidence budget in Option B's policy is not a nicety — it is load-bearing. This is why coverage must be implemented *inside* an orchestrator that owns the budget, not as a loop in the prompt builder (Option C).

---

## 7. Architecture Verification

| Check | Verdict | Evidence |
|---|:--:|---|
| No ownership violations | ✅ | Orchestrator owns composition; Consolidation owns grouping; Builder owns rendering. Option B *removes* the existing violation (§1.3). |
| No circular dependencies | ✅ | `models ← consolidation ← context_orchestration ← analysis ← cli`. Strictly acyclic; orchestrator imports Consolidation's output type only. |
| No duplicated responsibilities | ✅ | Selection ceases to exist in two places (CLI + `conftest.py`). Risk rollup stays solely in `consolidation_rules.rollup_risk`, reused by the orchestrator. |
| Prompt Governance unchanged | ✅ | `PromptRegistry`, `manifest.json`, SHA verification, `versions/` untouched. |
| Prompt wording unchanged | ✅ | Governed template not edited. `{artifact_context}` placeholder count unchanged (invariant enforced at `prompt_template_contract.py:128`). Framing constants reused verbatim. |
| Validation unchanged | ✅ | §6.2 — zero coupling. |
| CP1 unchanged | ✅ | §6.2 — zero coupling. |
| Execution Package unchanged | ❌ **must change** | `selectedArtifactId` and `consolidated_artifact.json` are, by definition, the selection contract. Cannot be preserved. Requires an explicit ADR ruling. |
| API mode unchanged | ✅ | Orchestration is downstream of ingestion; `EXECUTION_MODE` is mode-agnostic below the connector layer. |
| Productization unchanged | ❌ **must change** | Golden baseline hashes and `EXPECTED_*` constants shift. §2.7 shows the current baseline is unsound regardless. |

**Two of the ten guarantees cannot be honoured.** They are the two that *encode the defect*. The Execution Package's `selectedArtifactId` and the golden baseline's `EXPECTED_CONSOLIDATED_COUNT = 1` are both artefacts of a single-artifact world. Preserving them would mean preserving the bug. This is stated here rather than glossed, because a verdict was asked for, not reassurance.

### 7.1 Ownership chain after the terminology refinement (CAP-076A)

The refined vocabulary does not move a single boundary. Restated end to end:

```
Consolidation                    owns grouping                       (unchanged)
  ↓  list[ConsolidatedArtifact]
Engineering Context Orchestrator owns context composition + policy   (new)
  ↓  EngineeringContext
Requirement Prompt Builder       owns rendering                      (unchanged; retyped input)
  ↓  PromptRequest
Requirement Analysis Service     owns analysis-execution orchestration (unchanged; retyped input)
  ↓  AnalysisResult
Normalization                    owns normalization                  (unchanged)
  ↓  NormalizationResult
Validation                       owns judgement                      (unchanged)
  ↓  ValidationResult
CP1                              owns the readiness gate             (unchanged)
  ↓  CP1Result
Execution Package                owns persistence                    (contract changes; §6.1)
```

Two boundaries deserve explicit confirmation, because the shared word invites confusion:

- The **Engineering Context Orchestrator** owns *policy* and decides content. It never calls a provider, never validates, never renders a prompt.
- The **Requirement Analysis Service** owns *analysis-execution orchestration* and decides nothing. It remains the single orchestration boundary for AI execution and continues to own no policy, exactly as `docs/architecture/requirement-analysis-service.md` states.

Nothing in CAP-076A alters either. The rename is vocabulary, not architecture.

---

## 8. Architectural Risks

| # | Risk | Severity | Mitigation |
|---|---|:--:|---|
| R1 | **Union ≠ correlation.** Evidence appears together without any assertion that it concerns the same code. The model may confabulate relationships — a *subtler* failure than today's obviously-Sonar-only output, and harder to detect. | **High** | Orchestration reason must state the basis honestly ("co-selected for coverage; no correlation asserted"). Grounding validation (R2) must precede promotion. |
| R2 | **No grounding rule exists.** CAP-074B: five hallucinated requirements passed 13 validation rules and CP1 with zero findings. Widening the evidence surface widens the hallucination surface. | **High** | A grounding rule (requirement must cite a supplied artifact) is a **prerequisite**, not a follow-up. It presupposes artifact traceability in the response schema — a schema change with its own ADR. |
| R3 | **Prompt-size regression.** Measured 5.3k → 9.8k tokens unbudgeted (§6.3). | Medium | Evidence budget owned by the orchestration policy; enforced and asserted in unit tests. |
| R4 | **Golden baseline masks ingestion defects** (§2.7) — the harness bypasses connectors and mappers and hand-sets `component`. | **High** | Add an ingestion-level productization test over the real `input/` fixtures asserting multi-domain coverage. Do this *before* re-baselining, or the re-baseline will re-enshrine the blind spot. |
| R5 | Selection-rule duplication in `conftest.py:162` diverges from production. | Medium | Harness imports the orchestrator. Mechanically eliminated by Option B. |
| R6 | Orchestration policy becomes an ungoverned tuning knob (budget, ranking weights). | Medium | Policy is a versioned, injectable object recorded in the manifest — the same discipline Prompt Governance applies to prompts. |
| R7 | `EngineeringContext` drifts from `ConsolidatedArtifact` and the prompt bytes change for single-group runs. | Low | Contract test: one group in → prompt byte-identical to the CAP-075 baseline. |
| R8 | JIRA singleton groups persist. Even with coverage, the functional evidence in the context is *one* issue. | **High** | Coverage fixes *presence*; it does not fix *sufficiency*. Orchestration must select the top-N functional groups, not one. Flag explicitly for the ADR — this is the difference between "JIRA appears" and "JIRA is usable." |

R8 deserves emphasis. Measured, the best functional group available for orchestration contains exactly **one** JIRA issue. A coverage guarantee alone would put a single user story in front of the model beside 71 Sonar findings and 36 ZAP alerts. That is technically multi-source and practically still unbalanced. The orchestration policy must budget *by domain*, not globally.

---

## 9. Migration Strategy

Five stages. Each is independently revertible; each leaves the repository green.

**Stage 0 — Prerequisites (before any orchestration code)**
- Ingestion-level productization test over real `input/` fixtures, asserting the *current* behaviour (0 multi-domain groups). It should pass now and fail the moment orchestration lands. This is the regression net R4 requires.
- ADR authored and accepted: `EngineeringContext` model, manifest contract, orchestration-policy governance, `selectedArtifactId` disposition.

**Stage 1 — Model** *(Part 2)*
- Add `EngineeringContext` alongside `ConsolidatedArtifact`. Purely additive; nothing consumes it. Zero behaviour change.

**Stage 2 — Orchestrator, dark**
- `EngineeringContextOrchestrator` + `OrchestrationPolicy`, constructed via `PlatformContext`, fully unit-tested. Not yet wired into the CLI. Contract test: single-group input → identity output.

**Stage 3 — Wire, behind an explicit switch**
- Prompt Builder and Analysis Service accept a context. `_select_consolidated` deleted; CLI calls the orchestrator. Ship with the orchestration policy defaulting to *single-group, largest-count* — **behaviour-identical to today, prompt bytes identical, golden baseline green.** This proves the plumbing in isolation from the policy change.

**Stage 4 — Flip the policy**
- Default policy becomes coverage-guaranteed, risk-ranked, domain-budgeted. Behaviour changes here and only here. Re-baseline golden hashes in a single, reviewable commit whose diff is *only* hashes and `EXPECTED_*` constants. Retain the prior baseline as `golden-baseline-v1.0.0` for A/B comparison.

**Stage 5 — Correlation (future milestone)**
- Populate `EngineeringContext.dependencies` from a curated correlation table (the old Option B of the prior proposal) or from bounded key-set intersection (Option A), as an enrichment pass. Only now is R1 genuinely closed.

Stages 3 and 4 are deliberately separate. Merging them would make a plumbing bug and a policy change indistinguishable in the golden diff.

---

## 10. Future Evolution — Governed Orchestration Policy (non-normative)

> **This section is informational only.**
> It is **not** part of CAP-076. It introduces no capability, adds no repository structure, changes no governance, and authorises no implementation. It exists so that Part 2's design does not accidentally foreclose the direction sketched here.

Risk R6 (§8) observes that the Orchestration Policy — coverage rule, ranking order, evidence budget — is the kind of asset that quietly becomes an ungoverned tuning knob. The platform has already solved this class of problem once, for prompts: ADR-0014 established the Prompt Governance subsystem, where prompt text is a versioned, SHA-verified, registry-resolved artifact rather than a constant someone can edit.

An Orchestration Policy has the same properties that made prompts worth governing. It materially changes what the LLM sees; it is small, declarative, and reviewable; it needs a version recorded in the execution manifest for any result to be interpretable after the fact; and a silent change to it would invalidate every prior baseline without any code diff to notice.

A future milestone *could* therefore mirror the Prompt Governance structure:

```
context_orchestration/
    framework/
        policy_loader.py        # load + integrity-verify
        policy_registry.py      # sealed (policy_id, version) resolution
        policy_contract.py      # structural contract a policy must satisfy
    versions/
        coverage_v1.0.0.json    # a governed, immutable policy
    manifest.json               # SHA-256 per version
```

The runtime would pin an explicit `(policy_id, version)` pair — exactly as `RequirementPromptBuilder` now pins `("requirement_analysis", "1.0.0")` after CAP-075 — so promoting a new orchestration policy becomes a deliberate, reviewable change rather than an edit to a default argument.

Two honest caveats, recorded so the idea is not adopted uncritically:

1. **Governance is not free.** CAP-075 showed that wiring a registry into the runtime is a milestone in itself. A policy registry is only worth its cost once more than one policy exists and someone actually needs to switch between them or explain a historical result. Until then, a versioned, injectable policy object recorded in the manifest (Stage 2, §9) delivers most of the auditability at a fraction of the cost.
2. **Governing the policy does not govern the outcome.** CAP-074B demonstrated that a fully governed prompt still produced hallucinated requirements that passed every validation rule. Governance makes a change *traceable*; it does not make the change *correct*. The grounding gap (R2) remains the higher-value investment.

**This is a future architectural direction only. It is not part of CAP-076. No implementation shall be created. No repository structure shall be added.**

---

## 11. Repository Readiness

| Gate | Status |
|---|:--:|
| Root cause revalidated against repository evidence | ✅ Reproduced in FILE mode; matches CAP-074B's API-mode run |
| Engineering Context formally defined | ✅ §3 |
| Three architectural options evaluated | ✅ §4 |
| One architecture recommended | ✅ Option B |
| Repository impact understood | ✅ §5, §6 |
| Migration strategy documented | ✅ §9 |
| No code written | ✅ |
| Repository otherwise unchanged | ✅ This document is the only addition |
| Canonical terminology synchronized (CAP-076A) | ✅ §0 |
| Reproducibility established as a governing invariant | ✅ §3.2 Invariant 7 |
| Future policy governance recorded as informational only | ✅ §10 |
| **Blocking prerequisites for Part 2** | ⚠️ ADR not yet authored (§9 Stage 0); grounding-validation gap (R2) unresolved |

### 11.1 Canonical status declarations

| Question | Answer |
|---|---|
| Is **Engineering Context Orchestration** now the canonical architectural term? | **Yes.** Adopted by CAP-076A. *Engineering Context Assembly* is retired. The bare noun "orchestration" remains ambiguous and must be qualified (§0.1). |
| Does **`ConsolidatedArtifact`** remain the canonical consolidation model? | **Yes. Unchanged, and not deprecated.** It remains the sole output of Consolidation, and becomes the *input* to orchestration. |
| Is **`EngineeringContext`** a new canonical orchestration model? | **Yes — but prospectively.** It is a canonical *conceptual* model as of CAP-076A. It does not exist as a type, is not implemented, and becomes a canonical *code* model only when Part 2 lands it. |
| Does `EngineeringContext` replace `ConsolidatedArtifact`? | **No.** They are stacked, not substituted. One is a grouping of records that share an attribute; the other is a bounded body of evidence composed for one reasoning session. |
| Is the repository ready for **Part 2 — Engineering Context Canonical Model & Orchestration Framework**? | **Yes, conditionally** — see below. |

**Verdict: ready for Part 2**, conditional on the Stage 0 ADR being authored and accepted first, and with R2 (no grounding rule), R4 (golden baseline masks ingestion defects) and R8 (coverage ≠ sufficiency) carried forward as explicit, accepted risks rather than silently deferred ones.

CAP-076A changed vocabulary, added one invariant, and recorded one non-normative future direction. It changed **no** architecture, no runtime behaviour, no model, no governance, and no code. The repository is behaviourally identical to its state before this milestone.

---

## Appendix — Reproduction

```bash
cd "<repo>"
EXECUTION_MODE=FILE .venv/bin/python - <<'PY'
import os, collections
from requirement_intelligence.platform import PlatformContext
from requirement_intelligence.consolidation.consolidation_rules import derive_grouping_key
ctx = PlatformContext(); reg = ctx.create_connector_registry()
os.chdir('requirement_intelligence'); arts = reg.execute_all(); os.chdir('..')
print(collections.Counter(f"{derive_grouping_key(a).dimension.value} <- {a.source_system}" for a in arts))
cons = ctx.create_consolidation_engine().consolidate(arts)
mixed = [c for c in cons if sum(bool(x) for x in (c.functional_artifacts, c.security_artifacts, c.quality_artifacts)) > 1]
print(f"groups={len(cons)} multi_domain={len(mixed)}")
PY
```

Observed:
```
Counter({'component <- sonarqube': 300, 'tag <- owasp_zap': 83, 'endpoint <- jira': 4})
groups=23 multi_domain=0
```
