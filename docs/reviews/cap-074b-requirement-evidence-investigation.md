# CAP-074B — Prompt Evaluation & Root Cause Analysis (Live API Mode)

**Status:** Investigation complete. Root cause identified.
**Date:** 2026-07-09
**Execution mode:** API (live JIRA, SonarQube, OWASP ZAP)
**Provider / model:** Gemini / `gemini-3.1-flash-lite`
**Prompt version:** 1.0.0 (production, unmodified)
**Outcome:** The prompt is **not** the defect. No prompt change was made. No Prompt Governance promotion is recommended.

---

## 1. Executive summary

The reported symptom — *"generated requirements appear to be based primarily on SonarQube findings, while JIRA and ZAP information is absent"* — is real, reproducible, and **originates in the Consolidation Engine's grouping key, compounded by the CLI's artifact-selection rule.**

JIRA and ZAP artifacts are retrieved correctly, mapped correctly, and consolidated correctly *by the engine's own rules*. They then never reach the prompt, because:

1. No consolidated artifact can contain more than one source's data. Across 47 consolidated artifacts, **zero are multi-source.**
2. The CLI analyses exactly **one** consolidated artifact — the largest by raw artifact count.
3. SonarQube contributes 301 of 375 artifacts, concentrated per source file, so a SonarQube group always wins.

The prompt faithfully renders the artifact it is given. Given an artifact with zero functional and zero security artifacts, it prints `(none provided)` under both headings — which is correct behaviour.

**No prompt modification can fix this.** Phase 8 of this milestone gates prompt work on Consolidation and Artifact Selection being verified correct. They are not correct with respect to the platform's intent, so Phases 8–10 were not executed.

### The decisive evidence

The same analysis was run in FILE mode and in live API mode. API mode retrieved **28 JIRA issues** versus 4 in the file export — seven times more functional evidence. The resulting prompt was **byte-identical**:

| | FILE mode | API mode |
|---|---|---|
| JIRA issues retrieved | 4 | 28 |
| ZAP alerts retrieved | 83 | 46 |
| Sonar issues retrieved | 300 | 301 |
| Consolidated artifacts | 23 | 47 |
| Multi-source artifacts | 0 | 0 |
| Selected artifact | `…BadLoginPage.java` | `…BadLoginPage.java` |
| Prompt SHA-256 | `41aefef2…6e9724` | `41aefef2…6e9724` |
| Prompt characters | 21 202 | 21 202 |

Seven times the functional evidence produced not one additional byte in the prompt. Ingestion mode has no influence whatsoever on what reaches the model. This isolates the defect to the consolidation/selection stage with certainty.

---

## 2. Repository review (Phase 1)

| Check | Result |
|---|---|
| API mode active | **No** — corrected during this milestone (see §14) |
| Gemini provider active | Yes |
| Current production prompt version | 1.0.0 (`versions/manifest.json`, lifecycle `Production`) |
| Experimental prompt enabled | No |
| Local prompt overrides | **None** — SHA-256 of both version files matches the manifest exactly |
| Architecture inconsistencies | **Yes, three** (below) |

Three inconsistencies were found. Per the milestone's STOP directive, no prompt tuning was attempted; the investigation continued on evidence-gathering only.

### 2.1 `EXECUTION_MODE` was absent from `.env`

`resolve_execution_mode()` defaults to `FILE` when the variable is unset. It was unset. **The "live execution" that motivated this milestone was in fact a FILE-mode run** reading `requirement_intelligence/input/`. Corrected in §14.

### 2.2 The requested model does not exist

CAP-074B specified `gemini-3.5-flash-lite`. Querying the Gemini `ListModels` endpoint with the project's API key shows no such model. `gemini-3.5-flash` exists (no `-lite` variant); `gemini-3.1-flash-lite` exists and is the model benchmarked as stable in `docs/demo/gemini-model-evaluation.md`. **`gemini-3.1-flash-lite` was used**, matching the prior run and keeping the comparison controlled.

### 2.3 Prompt Governance is not wired into prompt construction

This is the most consequential structural finding and it exceeds CAP-074B's scope.

`RequirementPromptBuilder` (`prompts/requirement_prompt_builder.py`) assembles its prompt from the inline Python strings in `prompts/prompt_constants.py`, and stamps `prompt_version` from `prompt_constants.PROMPT_VERSION = "1.0.0"`. The governed path — `PromptLoader`, `PromptRegistry`, `versions/*.txt`, `versions/manifest.json` — is referenced **only** by `platform/startup_validation.py` and by tests. It is never consulted when a prompt is built.

Consequences:

- `versions/requirement_analysis_v1.0.0.txt` is a hand-maintained **copy** of `prompt_constants.py`, not its source. The two can drift silently; nothing detects it.
- `requirement_analysis_v1.1.0.txt` exists at lifecycle **`Approved`** (introduced by CAP-073) and **has never executed, and cannot execute.**
- The `promptVersion: "1.0.0"` recorded in every `manifest.json` attests to a constant, not to the governed artifact whose SHA-256 the manifest also records.

Because CAP-074B forbids modifying Prompt Governance, this was documented and left untouched.

### 2.4 A correction to an earlier assessment

An initial reading suggested that `ZAP_TARGET_URL` and `SONAR_BRANCH`, named in `source-registry.json` but absent from `.env`, would prevent API mode from starting. **This was wrong.** Both are resolved with `required=False` (`connectors/zap/connector.py:120`, `connectors/sonarqube/connector.py:129`) and are documented as optional. Their absence was never a defect. They have been added as documented empty placeholders for parity with `.env.example`, nothing more.

---

## 3. Connector verification (Phase 2)

`run_requirement_analysis.py health` against the live systems:

```
Execution Mode        : API
  JIRA .................. READY
  OWASP ZAP ............. READY
  SonarQube ............. READY
All 3 source(s) READY.
```

| Source | API executed | Auth | Retrieved | Filtered | Mapped | Retained |
|---|---|---|---|---|---|---|
| JIRA | Yes | Success | 28 | 28 | 28 | 28 |
| OWASP ZAP | Yes | Success | 46 | 46 | 46 | 46 |
| SonarQube | Yes | Success | 301 | 301 | 301 | 301 |

**No connector returned zero artifacts.** All three are healthy. The connector layer is exonerated.

JIRA's 28 issues comprise 13 `story`, 10 `defect`, 5 `epic` — consistent with the registry's `api.jql` scope of `issuetype in (Story, Bug, Epic)`.

---

## 4. Mapper verification (Phase 3)

| Mapper | Input records | Output `SourceArtifact`s | Dropped | Schema mismatches |
|---|---|---|---|---|
| `JiraMapper` | 28 | 28 (`story`/`defect`/`epic`) | 0 | 0 |
| `ZapMapper` | 46 | 46 (`dast`) | 0 | 0 |
| `SonarMapper` | 301 | 301 (`sast`) | 0 | 0 |

Total: **375 `SourceArtifact`s**, no mapping failures, no drops. The mapper layer is exonerated.

**However**, the mappers populate the grouping-relevant fields asymmetrically, and this is the proximate cause of everything downstream:

| Mapper | Sets `component`? | Sets `tags`? | Sets `url` / `location`? |
|---|---|---|---|
| `SonarMapper` | **Yes** — the source file path (`sonar_mapper.py:110`) | Yes | `location` = line number |
| `ZapMapper` | No | Yes — alert tags | `location` = scanned URL |
| `JiraMapper` | **No** | Yes — issue labels | `url` = the issue's `self` REST link |

Only SonarQube supplies `component`. This is not a mapper bug in isolation — each mapper faithfully renders what its source provides. JIRA's REST payload has no field that corresponds to a code component, and ZAP alerts describe URLs, not modules. The defect emerges only when the Consolidation Engine treats `component` as the primary grouping dimension.

---

## 5. Consolidation verification (Phase 4)

`consolidation_rules.py:derive_grouping_key` applies a first-match cascade:

```
component  →  tag  →  endpoint  →  risk
```

Combined with §4's asymmetry, each source deterministically lands in a *different* dimension:

| Source type | Count | Dimension matched | Why |
|---|---|---|---|
| `sast` | 301 | `component` | Only source that sets it |
| `dast` | 46 | `tag` | No component; has alert tags |
| `story` | 13 | `endpoint` | No component, no matching label; falls through to `url` |
| `defect` | 10 | `endpoint` | ditto |
| `epic` | 5 | `endpoint` | ditto |

Because the dimensions are disjoint, and because the `GroupingKey` embeds the dimension in its identity (`build_consolidated_id` → `cons-{dimension}-{slug}`), **a JIRA artifact and a Sonar artifact can never share a group, even when they describe the same code.**

### Consolidated artifact census — all 47 groups

| Dimension | Groups | Functional | Security | Quality |
|---|---|---|---|---|
| `component` | 11 | 0 | 0 | 301 |
| `tag` | 8 | 0 | 46 | 0 |
| `endpoint` | 28 | 28 | 0 | 0 |
| **Total** | **47** | **28** | **46** | **301** |

**Multi-source consolidated artifacts: 0 of 47.**

Top groups by size:

| Functional | Security | Quality | Risk | Selected | Consolidation ID |
|---|---|---|---|---|---|
| 0 | 0 | **71** | critical | **Yes** | `cons-component-…-BadLoginPage.java` |
| 0 | 0 | 53 | critical | | `cons-component-…-BadNamingUtils.java` |
| 0 | 0 | 33 | high | | `cons-component-…-BadLoginSteps.java` (steps) |
| 0 | 0 | 27 | critical | | `cons-component-…-BadInventoryPage.java` |
| 0 | 0 | 23 | critical | | `cons-component-…-BadLoginSteps.java` |
| 0 | 0 | 22 | critical | | `cons-component-…-BadTestUtils.java` |
| 0 | 36 | 0 | low | | `cons-tag-custom-payloads` *(FILE mode)* |
| 1 | 0 | 0 | low | | `cons-endpoint-rest-api-2-issue-10001` |

Answering Phase 4's five questions directly:

1. **Are JIRA artifacts consolidated?** Yes — into 28 groups, one per issue.
2. **Are ZAP artifacts consolidated?** Yes — into 8 tag-based groups.
3. **Are they consolidated separately?** **Yes, always.** This is the defect.
4. **Why was the selected artifact chosen?** It has the greatest total artifact count (71).
5. **Is the selection algorithm behaving correctly?** It behaves **as written**, and deterministically. It does not behave **as intended**.

### A second-order defect: JIRA fragmentation

Each JIRA issue becomes its own singleton group, keyed on its `self` REST URL (`/rest/api/2/issue/10001`), which is unique per issue by construction. So JIRA is not merely segregated from the other sources — it is atomised. Twenty-eight issues produce twenty-eight groups of size one. Under a "largest group wins" rule, JIRA can **never** be selected while any source file carries two or more findings. This holds regardless of how important the JIRA issues are.

---

## 6. Artifact selection analysis (Phase 5a)

`scripts/run_requirement_analysis.py:277`:

```python
def _key(c):
    total = len(c.functional_artifacts) + len(c.security_artifacts) + len(c.quality_artifacts)
    return (-total, c.consolidated_id)
return sorted(consolidated, key=_key)[0]
```

Two properties compound the consolidation defect:

- **Raw count is the sole ranking signal.** `risk_level` is computed, stored, displayed — and ignored by selection. A `critical` singleton JIRA defect loses to a group of 71 `MAJOR` code smells.
- **Exactly one artifact is analysed.** Even if grouping were fixed, a single-artifact analysis would still discard 46 of 47 groups.

Selection is deterministic and reproducible, as its docstring promises. That is the whole of what it promises, and it delivers it. The problem is that "the biggest pile of findings" is a poor proxy for "the thing an engineer should look at."

---

## 7. Prompt construction analysis (Phase 5)

`prompt.txt` from the live API run was compared line-by-line against the selected `ConsolidatedArtifact`:

| Prompt section | Artifact content | Prompt content | Faithful? |
|---|---|---|---|
| `### Functional Artifacts` | 0 items | `(none provided)` | **Yes** |
| `### Security Findings` | 0 items | `(none provided)` | **Yes** |
| `### Quality Findings` | 71 items | 71 `- (sast)` lines | **Yes** |

Counted in the emitted prompt: **71 sast lines, 0 dast lines, 0 JIRA lines.**

`RequirementPromptBuilder._render_section` emits `EMPTY_SECTION_PLACEHOLDER` for an empty list and otherwise renders every artifact in order. **The Prompt Builder has no defect.** It omits nothing that exists in the selected artifact. It cannot render evidence that the artifact does not contain.

---

## 8. Gemini response analysis (Phase 6)

Response: `finish_reason: STOP`, valid JSON, 5 973 prompt tokens, 570 completion tokens.

Evidence supplied: **0 functional, 0 security, 71 quality.** Generated:

| Output field | Count |
|---|---|
| `functional_requirements` | 5 |
| `security_requirements` | 2 |
| `quality_requirements` | 5 |
| `risks` | 4 |
| `recommendations` | 5 |

### Classification

| Requirement (abridged) | Classification | Evidence source | Reason |
|---|---|---|---|
| "The login page shall provide a mechanism to input a username." | **Unsupported inference** | None | No functional artifact supplied. Inferred from the class name `BadLoginPage` and Sonar issue locations. |
| "…input a password." | **Unsupported inference** | None | As above. |
| "…trigger the login action." | **Unsupported inference** | None | As above. |
| "…verify the presence of error messages." | **Unsupported inference** | None | As above. |
| "…navigate to the shopping cart." | **Unsupported inference** | None | Inferred from an unrelated method name; not a requirement of this component. |
| "Replace generic catch-all blocks to prevent information leakage." | **Reasonable inference** | Sonar `java:S2221` (quality) | Genuinely derived from a supplied quality finding; reclassified as security by the model. |
| "Externalize credentials rather than hardcoding them." | **Reasonable inference** | Sonar `java:S2068` (quality) | Genuinely derived from a supplied quality finding. |
| 5 × quality requirements | **Evidence-backed** | Sonar findings in the prompt | Directly traceable to supplied artifacts. |
| 4 × risks | **Evidence-backed** | Sonar findings | Grounded in the supplied evidence. |
| 5 × recommendations | **Evidence-backed** | Sonar findings | Grounded. |

**Hallucinations:** 5 functional requirements, invented from identifier names rather than from evidence.
**Missed evidence:** none — every supplied artifact was used.
**Unsupported assumptions:** that a page object's method names constitute functional requirements of the system under test.

### Did Gemini behave correctly?

**Partially.** It grounded all quality output correctly and missed nothing. It also invented five functional requirements from zero functional evidence, in direct violation of the system prompt's instruction that it *"never invent facts that are not supported by the supplied artifacts."*

This is a genuine defect — but a **secondary** one. Even had Gemini correctly returned `"functional_requirements": []`, no JIRA or ZAP content would have appeared, because none was in the prompt. Fixing the model's behaviour would make the output *honest*; it would not make it *complete*.

Note the causal trap for future readers: the two `security_requirements` above look superficially like ZAP findings reached the model. They did not. Both were derived from **SonarQube** rules (`S2221`, `S2068`) that happen to have security semantics. Zero ZAP alerts were in the prompt.

### Validation and CP1

Both gates passed on this output:

- Response validation: verdict `passed`, profile `default`, 13 rules executed, **0 issues**.
- CP1 engineering-readiness: verdict `pass`, **0 findings**.

**This is itself a finding.** The output contained five hallucinated requirements and passed every gate. Neither validation nor CP1 currently checks generated requirements against the evidence that was supplied — there is no grounding or traceability rule. Both subsystems are frozen under CAP-074B's constraints, so this is recorded, not acted on.

---

## 9. Root cause analysis (Phase 7)

**Root cause: Multiple — Consolidation (primary) and Artifact Selection (compounding).**

| Layer | Verdict | Evidence |
|---|---|---|
| Connector | **Correct** | `health` reports all 3 READY; 28 / 46 / 301 records retrieved |
| Mapper | **Correct** | 375 artifacts, 0 drops, 0 schema mismatches |
| **Consolidation** | **DEFECTIVE** | 0 of 47 artifacts are multi-source; grouping cascade partitions by source |
| **Artifact Selection** | **DEFECTIVE** | Ranks on raw count alone; analyses exactly 1 of 47 groups |
| Prompt Construction | **Correct** | `prompt.txt` exactly mirrors the selected artifact |
| Gemini Reasoning | **Partially defective** | 5 hallucinated functional requirements — secondary |
| Prompt Design | **Weak, not causal** | Objectives 1–2 lack an empty-evidence escape — secondary |

**Primary chain:** only `SonarMapper` sets `component` → `derive_grouping_key`'s cascade puts each source in a different dimension → every consolidated artifact is single-source → selection takes the single largest → SonarQube's 301 findings guarantee a Sonar group wins → the prompt contains only quality evidence → the model can only reason about quality.

The prompt is the **last** place this could have been diagnosed and the **only** place it was visible. The milestone's instinct to investigate upstream before touching the prompt was correct.

---

## 10. Prompt weaknesses (documented, not fixed)

Recorded for a future, properly scoped milestone. **No prompt was modified.**

1. **No empty-evidence escape.** `ANALYSIS_OBJECTIVES` items 1 and 2 unconditionally command *"Analyze the functional requirements…"* and *"Analyze the security findings…"*. When a section is `(none provided)`, the objective still stands, and the model complies by inventing. This directly produced the five hallucinations.
2. **`(none provided)` carries no instruction.** The placeholder states a fact but not its consequence. It should tell the model that an empty section means the corresponding output array must be empty.
3. **No evidence/inference distinction.** The schema has no field to mark a statement as inferred rather than observed, so a hallucination is indistinguishable from an evidence-backed requirement in the output.
4. **No traceability.** No requirement carries a reference to the artifact that justifies it, which is why §8's classification had to be reconstructed by hand.
5. **Weak prioritisation.** `recommendations` is described as "prioritised" with no priority scheme defined.

Weakness 1 is the only one implicated in the observed behaviour, and even it is secondary.

---

## 11. Candidate prompt improvements (Phase 8)

**None proposed. Phase 8's precondition is not met.**

Phase 8 permits prompt work only if Connector, Mapper, Consolidation, Artifact Selection, and Prompt Construction are **all** verified correct. Consolidation and Artifact Selection are defective (§9). Phases 8, 9, and 10 were therefore not executed, per the milestone's own gate.

Proposing a prompt v1.1.0 candidate now would be actively harmful: it would imply the problem was addressed while JIRA and ZAP evidence still could not reach the model, and any before/after comparison would measure nothing but prompt wording against an unchanged, single-source evidence set. Additionally, v1.1.0 is already taken (§2.3), and no candidate could be executed at all until Prompt Governance is wired into the builder.

---

## 12. Comparative assessment (Phase 10)

Not applicable — no candidate prompt was created, so there is nothing to compare. The FILE-versus-API comparison in §1 stands in its place and is the more informative result.

---

## 13. Ruff and test status

| Check | Result |
|---|---|
| `ruff check .` | **All checks passed** |
| `ruff format` | Not run — no Python source file was modified |
| `pytest` | **1 879 passed**, 1 warning (pre-existing Starlette deprecation), 0 failed |

---

## 14. Files created, modified, removed

**Created**

- `docs/reviews/cap-074b-requirement-evidence-investigation.md` (this report)
- `docs/proposals/cross-source-consolidation-and-selection.md` (design proposal, no code)
- `output/executions/cap074b-api-live/` (execution package; `output/` is gitignored)

**Modified**

- `.env` — operational configuration only; gitignored, not committed:
  - `EXECUTION_MODE=API` added (was absent, defaulting to `FILE`)
  - `GEMINI_MODEL` `gemini-2.5-flash` → `gemini-3.1-flash-lite`
  - `SONAR_BRANCH=` and `ZAP_TARGET_URL=` added as documented optional placeholders
  - Section headers 4–6 retitled `FUTURE API MODE` → `API MODE` (stale since CAP-074)

**Removed**

- None.

No Python source file was modified. No architecture, ADR, canonical model, validation rule, CP1 component, Execution Package, Connector Framework, Consolidation, or Prompt Governance asset was touched.

`.env.example` was reviewed and **left unchanged**: its `EXECUTION_MODE=FILE` default is the correct credential-free demo default, and its `GEMINI_MODEL=gemini-2.5-pro` was verified to exist.

---

## 15. Repository reconciliation (Phase 11)

- Prompt assets: `versions/*.txt` SHA-256 verified against `versions/manifest.json` — both match. No overrides, no drift, no duplicates.
- Temporary evaluation artifacts: all probe scripts were written to the session scratchpad outside the repository and require no cleanup.
- Obsolete reports / duplicate outputs: `output/` is gitignored in full. `output/latest/` was overwritten by the live run, which is that directory's designed behaviour. `output/first_ai_execution/` and `output/model-eval/` are prior-milestone evidence and were left intact.
- Unused evaluation code: none introduced.
- Working tree: clean apart from the two new documents. `git status` shows no modification to any tracked source file.

---

## 16. Remaining risks

1. **The defect is unfixed.** Every analysis run will continue to ignore all JIRA and ZAP evidence until Consolidation and Selection are changed. This is by design for this milestone; it must not be forgotten.
2. **Validation and CP1 cannot detect hallucination.** Five invented requirements passed 13 validation rules and the CP1 gate with zero findings. Any future grounding rule will need artifact-to-requirement traceability, which the response schema does not currently carry.
3. **Prompt Governance is decorative.** Until `RequirementPromptBuilder` loads from `PromptRegistry`, the `promptVersion` recorded in every manifest attests to a Python constant rather than to the governed, fingerprinted artifact. A governed prompt cannot be promoted into effect. The `Approved` v1.1.0 is inert.
4. **`prompt_constants.py` and `requirement_analysis_v1.0.0.txt` can drift silently.** They agree today; nothing enforces that.
5. **Ingestion mode is not recorded in the execution package.** `manifest.json` carries `executionMode: "live"` (dry-run vs live) but nothing distinguishing FILE from API. Two runs with materially different evidence sources are indistinguishable after the fact — as this milestone discovered the hard way.
6. **`.env` is gitignored**, so the configuration corrections in §14 are local to this machine and will not propagate.

---

## 17. Repository readiness

The repository is **ready for a Prompt Governance decision**, and the decision is: **take no Prompt Governance action.**

- ✅ Live API execution completed (`output/executions/cap074b-api-live/`)
- ✅ Connector outputs verified — all three healthy, none returned zero
- ✅ Mapper outputs verified — 375 artifacts, zero drops
- ✅ Consolidation verified — **defect identified**
- ✅ Artifact selection verified — **defect identified**
- ✅ Prompt construction verified — correct
- ✅ Gemini response analysed — 5 hallucinations, all quality output grounded
- ✅ Root cause identified — Consolidation + Artifact Selection
- ✅ Prompt weaknesses documented; **no candidate created** (Phase 8 gate not met)
- ✅ Ruff clean
- ✅ 1 879 tests pass
- ⛔ Comparative evaluation — not applicable

---

## 18. Explicit statements required by CAP-074B

| Question | Answer |
|---|---|
| Did JIRA artifacts reach the prompt? | **No.** 28 retrieved, 28 mapped, 28 consolidated into singleton groups, 0 in the prompt. |
| Did ZAP artifacts reach the prompt? | **No.** 46 retrieved, 46 mapped, 8 tag groups, 0 in the prompt. |
| Did Sonar artifacts reach the prompt? | **Yes.** 71 of 301, being the contents of the one selected group. |
| Did Gemini behave correctly? | **Partially.** All quality output was grounded and nothing was missed, but it invented 5 functional requirements from zero functional evidence, violating its own system prompt. |
| Did Prompt v1.0.0 behave correctly? | **Yes, structurally.** It rendered the selected artifact faithfully and completely. It has a real secondary weakness — no empty-evidence escape — which permitted the hallucinations. It is **not** the cause of the missing JIRA and ZAP data. |
| Should Prompt v1.1.0 remain a candidate? | **No v1.1.0 candidate was created**, and none should be until Consolidation and Selection are fixed. The pre-existing v1.1.0 from CAP-073 must remain unpromoted and, being unreachable by the builder, is inert. |
| Is Prompt Governance promotion recommended? | **No.** Promotion would change nothing: the builder does not read the registry. Promoting a prompt into a subsystem that no execution consults would create a false record of change. |

---

## 19. Recommended next milestone

The fix is architectural and is explicitly out of scope here. See **`docs/proposals/cross-source-consolidation-and-selection.md`** for a design proposal covering cross-source grouping and multi-source artifact selection, to be considered under a future milestone with its own ADR.

Suggested ordering, highest value first:

1. **Cross-source consolidation + selection** — the actual bug. Nothing else matters until JIRA and ZAP evidence can reach a prompt.
2. **Wire Prompt Governance into `RequirementPromptBuilder`** — a precondition for *any* future prompt work being meaningful or measurable.
3. **Prompt v1.2.0** — empty-evidence escape and evidence/inference separation. Only worth doing after (1), so that its effect can be measured against a multi-source evidence set.
4. **Grounding validation rule** — reject requirements that cite no supplied artifact. Requires traceability in the response schema.
5. **Record ingestion mode in `manifest.json`** — small, and it would have saved this investigation considerable time.
