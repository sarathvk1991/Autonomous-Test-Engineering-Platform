# CAP-076 Part 1 — Engineering Context Assembly: Architecture Review & Design

**Status:** Architecture review. No code written. No ADR, model, Consolidation, or Selection change made.
**Predecessor:** `docs/reviews/cap-074b-requirement-evidence-investigation.md`, `docs/proposals/cross-source-consolidation-and-selection.md`
**Outcome:** One architecture recommended. Requires a new ADR before Part 2.

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
| `RequirementAnalysisService` | Orchestration of one analysis over one artifact | Validation, persistence, ingestion | `analysis/requirement_analysis_service.py:92` |
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

CAP-074B established that five such hallucinated requirements passed all 13 validation rules and the CP1 gate with zero findings. That is a **real, separate defect** — the platform has no grounding rule — but it is downstream. Fixing the model or the prompt cannot conjure evidence that was discarded three stages earlier. Fixing the context assembly will, however, *widen the surface* for ungrounded inference, which makes the grounding gap a prerequisite rather than an afterthought (§9, §10).

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
      ├── assembly policy + policy version
      └── assembly reason (one explainable sentence)
```

### 3.2 Governing invariants

1. **Completeness before relevance.** A context that omits an entire evidence domain that *exists in the run* is incomplete, even if every included item is highly relevant. Today's context fails here.
2. **Correlation is asserted, never implied.** Evidence placed side by side must not be presented as related unless a correlation basis is recorded. Co-presence is not co-reference. *(This is the central risk of every option in §4.)*
3. **Bounded.** A context must fit one reasoning session. Unbounded evidence is not a context; it is a data dump.
4. **Traceable.** Every element resolves to a `(source_system, source_record_id)`.
5. **Deterministic and explainable.** Same input → same context, same ID, same one-sentence reason. No AI in assembly.
6. **Renderable without prompt change.** A context must project onto the existing three-section context block, so the governed prompt template is untouched.

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

### Option B — Engineering Context Assembly after Consolidation ★

Introduce a new, owned subsystem between Consolidation and Analysis. Consolidation keeps producing groups exactly as it does today. The **Context Assembler** consumes `list[ConsolidatedArtifact]` and applies a *governed assembly policy* to produce one `EngineeringContext`.

```
list[SourceArtifact] ─► ConsolidationEngine ─► list[ConsolidatedArtifact]
                                                          │
                                              ContextAssembler (new)
                                              ├─ assembly policy (governed)
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
4. `assembly_reason` states, in one sentence, which groups contributed and why.

| Criterion | Assessment |
|---|---|
| Complexity | Moderate, and *contained*. One new package, one new model, one policy object. Nothing existing changes shape. |
| Determinism | Strong. Pure function of an ordered input list. No I/O, no AI. |
| Backward compat | **High.** Consolidation, `ConsolidatedArtifact`, `consolidated_id`, mappers, connectors, and `consolidation_rules.py` are untouched. |
| Performance | O(n log n). Negligible. |
| Testability | Strong. Policy is injectable; coverage and budget are directly assertable. Enables the ingestion-level test the golden baseline lacks (§2.7). |
| Scalability | Strong. Budget is enforced at assembly, so prompt size is bounded by policy, not by dataset size. |
| Extensibility | Strong. Correlation (Option A's real value) later becomes an *enrichment step inside the assembler*, populating `dependencies`, without touching Consolidation. |

The critical property: `EngineeringContext` is a **structural superset** of `ConsolidatedArtifact` (id, subject label, business area, risk level, three evidence lists, reason). Rendering it through the existing three-section context block requires **no prompt wording change and no template change** — the `{artifact_context}` placeholder invariant holds. When exactly one group exists, the assembler degenerates to identity and the rendered prompt is byte-identical to today's.

### Option C — Selection assembles multiple ConsolidatedArtifacts

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

**Adopt Option B (Engineering Context Assembly after Consolidation), with Option A deferred as a future enrichment step inside the assembler.**

Reasoning:

1. **It fixes the actual defect.** Coverage guarantee, not correlation inference, is what puts JIRA and ZAP in front of the model. Correlation is a separate, later, harder question — and one that cannot be evaluated until a working multi-source baseline exists.
2. **It respects every existing ownership boundary.** Consolidation groups. Assembly composes. Prompt renders. Nothing gains a second responsibility.
3. **It creates the owner that §1.3 shows is missing.** Selection policy stops being CLI glue and becomes a governed, injectable, unit-testable subsystem — with the immediate benefit that the golden harness can *import* it instead of duplicating it.
4. **It is the only option with a place to put correlation later.** `EngineeringContext.dependencies` is where Option A's key-set intersection eventually lands, as an enrichment pass over already-assembled evidence, where runaway merging is bounded by the budget rather than by luck.
5. **It preserves prompt governance and the golden prompt bytes** for the single-group case, which no other option does.

Option C is not wrong in outcome; it is wrong in ownership, and this milestone exists precisely because ownership drift is what produced the defect.

---

## 5. Subsystem Impact Matrix

| Subsystem | Code | Tests | Docs | ADR | Rationale |
|---|:--:|:--:|:--:|:--:|---|
| **Context Assembly** (new) | ✅ new | ✅ new | ✅ new | ✅ new | The entire deliverable. |
| `EngineeringContext` model (new) | ✅ new | ✅ new | ✅ | ✅ | New canonical model; additive. |
| `ConsolidationEngine` | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** Groups remain groups. |
| `consolidation_rules.py` | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** Cascade preserved. |
| `ConsolidatedArtifact` | ⬜ | ⬜ | ➖ | ⬜ | Untouched. Docstring may note it is now an assembly *input*. |
| `SourceArtifact` | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** |
| Connectors | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched.** API + FILE mode unaffected. |
| Mappers | ⬜ | ⬜ | ⬜ | ⬜ | **Untouched** in Part 2. (A future `component` enrichment is out of scope.) |
| Selection (`_select_consolidated`) | ✅ **removed** | ✅ | ✅ | ✅ | Responsibility migrates into the assembler. |
| `run_requirement_analysis.py` | ✅ | ✅ | ✅ | ⬜ | Calls the assembler; keeps `--artifact-id` as a policy override. |
| `PlatformContext` | ✅ | ✅ | ⬜ | ⬜ | Gains `create_context_assembler()`. Construction hub, per existing pattern. |
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
2. **`manifest.json → selectedArtifactId`** (`execution/manifest_builder.py:53`) — a bundle has an assembled id, plus a list of contributing group ids. *ADR decision: `selectedArtifactId` + `contributingArtifactIds[]`, or a versioned manifest schema bump.*
3. **`consolidated_artifact.json`** (`execution/execution_writer.py:112`) — becomes `engineering_context.json`, or is written alongside it. Every golden SHA-256 changes either way.

### 6.2 Untouched, and verified so

Grepped: `requirement_intelligence/validation/` and `requirement_intelligence/normalization/` contain **zero** references to `consolidated`, `ConsolidatedArtifact`, or `SourceArtifact`. `CP1Input` carries only a `validation_result`. The three subsystems the brief asks to protect are already structurally isolated from consolidation. No effort is required to keep them unchanged; the architecture already guarantees it.

### 6.3 Prompt-size consequence — measured

| | chars | ≈ tokens |
|---|---:|---:|
| Today's selected artifact (71 Sonar findings) | 21,202 | 5,300 |
| Naive union of the top group per category | 39,269 | 9,817 |

An unbudgeted coverage bundle nearly doubles the prompt on this small dataset alone. The evidence budget in Option B's policy is not a nicety — it is load-bearing. This is why coverage must be implemented *inside* an assembler that owns the budget, not as a loop in the prompt builder (Option C).

---

## 7. Architecture Verification

| Check | Verdict | Evidence |
|---|:--:|---|
| No ownership violations | ✅ | Assembler owns composition; Consolidation owns grouping; Builder owns rendering. Option B *removes* the existing violation (§1.3). |
| No circular dependencies | ✅ | `models ← consolidation ← context_assembly ← analysis ← cli`. Strictly acyclic; assembler imports Consolidation's output type only. |
| No duplicated responsibilities | ✅ | Selection ceases to exist in two places (CLI + `conftest.py`). Risk rollup stays solely in `consolidation_rules.rollup_risk`, reused by the assembler. |
| Prompt Governance unchanged | ✅ | `PromptRegistry`, `manifest.json`, SHA verification, `versions/` untouched. |
| Prompt wording unchanged | ✅ | Governed template not edited. `{artifact_context}` placeholder count unchanged (invariant enforced at `prompt_template_contract.py:128`). Framing constants reused verbatim. |
| Validation unchanged | ✅ | §6.2 — zero coupling. |
| CP1 unchanged | ✅ | §6.2 — zero coupling. |
| Execution Package unchanged | ❌ **must change** | `selectedArtifactId` and `consolidated_artifact.json` are, by definition, the selection contract. Cannot be preserved. Requires an explicit ADR ruling. |
| API mode unchanged | ✅ | Assembly is downstream of ingestion; `EXECUTION_MODE` is mode-agnostic below the connector layer. |
| Productization unchanged | ❌ **must change** | Golden baseline hashes and `EXPECTED_*` constants shift. §2.7 shows the current baseline is unsound regardless. |

**Two of the ten guarantees cannot be honoured.** They are the two that *encode the defect*. The Execution Package's `selectedArtifactId` and the golden baseline's `EXPECTED_CONSOLIDATED_COUNT = 1` are both artefacts of a single-artifact world. Preserving them would mean preserving the bug. This is stated here rather than glossed, because Phase 6 asks for a verdict, not for reassurance.

---

## 8. Architectural Risks

| # | Risk | Severity | Mitigation |
|---|---|:--:|---|
| R1 | **Union ≠ correlation.** Evidence appears together without any assertion that it concerns the same code. The model may confabulate relationships — a *subtler* failure than today's obviously-Sonar-only output, and harder to detect. | **High** | Assembly reason must state the basis honestly ("co-selected for coverage; no correlation asserted"). Grounding validation (R2) must precede promotion. |
| R2 | **No grounding rule exists.** CAP-074B: five hallucinated requirements passed 13 validation rules and CP1 with zero findings. Widening the evidence surface widens the hallucination surface. | **High** | A grounding rule (requirement must cite a supplied artifact) is a **prerequisite**, not a follow-up. It presupposes artifact traceability in the response schema — a schema change with its own ADR. |
| R3 | **Prompt-size regression.** Measured 5.3k → 9.8k tokens unbudgeted (§6.3). | Medium | Evidence budget owned by the assembly policy; enforced and asserted in unit tests. |
| R4 | **Golden baseline masks ingestion defects** (§2.7) — the harness bypasses connectors and mappers and hand-sets `component`. | **High** | Add an ingestion-level productization test over the real `input/` fixtures asserting multi-domain coverage. Do this *before* re-baselining, or the re-baseline will re-enshrine the blind spot. |
| R5 | Selection-rule duplication in `conftest.py:162` diverges from production. | Medium | Harness imports the assembler. Mechanically eliminated by Option B. |
| R6 | Assembly policy becomes an ungoverned tuning knob (budget, ranking weights). | Medium | Policy is a versioned, injectable object recorded in the manifest — the same discipline Prompt Governance applies to prompts. |
| R7 | `EngineeringContext` drifts from `ConsolidatedArtifact` and the prompt bytes change for single-group runs. | Low | Contract test: one group in → prompt byte-identical to the CAP-075 baseline. |
| R8 | JIRA singleton groups persist. Even with coverage, the functional evidence in the context is *one* issue. | **High** | Coverage fixes *presence*; it does not fix *sufficiency*. Assembly must select the top-N functional groups, not one. Flag explicitly for the ADR — this is the difference between "JIRA appears" and "JIRA is usable." |

R8 deserves emphasis. Measured, the best functional group available for assembly contains exactly **one** JIRA issue. A coverage guarantee alone would put a single user story in front of the model beside 71 Sonar findings and 36 ZAP alerts. That is technically multi-source and practically still unbalanced. The assembly policy must budget *by domain*, not globally.

---

## 9. Migration Strategy

Five stages. Each is independently revertible; each leaves the repository green.

**Stage 0 — Prerequisites (before any assembly code)**
- Ingestion-level productization test over real `input/` fixtures, asserting the *current* behaviour (0 multi-domain groups). It should pass now and fail the moment assembly lands. This is the regression net R4 requires.
- ADR authored and accepted: `EngineeringContext` model, manifest contract, assembly-policy governance, `selectedArtifactId` disposition.

**Stage 1 — Model** *(Part 2)*
- Add `EngineeringContext` alongside `ConsolidatedArtifact`. Purely additive; nothing consumes it. Zero behaviour change.

**Stage 2 — Assembler, dark**
- `ContextAssembler` + `AssemblyPolicy`, constructed via `PlatformContext`, fully unit-tested. Not yet wired into the CLI. Contract test: single-group input → identity output.

**Stage 3 — Wire, behind an explicit switch**
- Prompt Builder and Analysis Service accept a context. `_select_consolidated` deleted; CLI calls the assembler. Ship with the assembly policy defaulting to *single-group, largest-count* — **behaviour-identical to today, prompt bytes identical, golden baseline green.** This proves the plumbing in isolation from the policy change.

**Stage 4 — Flip the policy**
- Default policy becomes coverage-guaranteed, risk-ranked, domain-budgeted. Behaviour changes here and only here. Re-baseline golden hashes in a single, reviewable commit whose diff is *only* hashes and `EXPECTED_*` constants. Retain the prior baseline as `golden-baseline-v1.0.0` for A/B comparison.

**Stage 5 — Correlation (future milestone)**
- Populate `EngineeringContext.dependencies` from a curated correlation table (the old Option B of the prior proposal) or from bounded key-set intersection (Option A), as an enrichment pass. Only now is R1 genuinely closed.

Stages 3 and 4 are deliberately separate. Merging them would make a plumbing bug and a policy change indistinguishable in the golden diff.

---

## 10. Repository Readiness

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
| **Blocking prerequisites for Part 2** | ⚠️ ADR not yet authored (§9 Stage 0); grounding-validation gap (R2) unresolved |

**Verdict: ready for Part 2 — Engineering Context Model**, conditional on the Stage 0 ADR, and with R2 and R8 recorded as explicit, accepted risks rather than silently deferred ones.

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
