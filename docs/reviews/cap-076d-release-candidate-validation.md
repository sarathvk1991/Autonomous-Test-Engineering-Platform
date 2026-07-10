# Requirement Intelligence Layer — Release Candidate RC-1 Validation

**Runtime validation, API mode, post CAP-076D.** This is a verification exercise, not a milestone: no source code was modified, because no defect was found that required correction.

- **Date:** 2026-07-10
- **Git commit:** `a2f7d0c` (tree clean, branch `main`, no tag)
- **Execution mode:** API (live JIRA, SonarQube, OWASP ZAP + live Gemini)
- **Active policy:** `coverage` v1.0.0 — `DefaultOrchestrationPolicy`, `coverage_guaranteed`
- **Model:** `gemini-3.1-flash-lite`
- **Execution ID:** `92e7a1fa-86ce-4557-9a08-cdbb8441e7b2`
- **Archive:** `output/releases/ril-rc1-api-validation/`

---

## 1. Executive Summary

The Requirement Intelligence Layer executed cleanly end-to-end against live data in API mode. All three source systems contributed evidence; the Engineering Context carried functional, security, and quality evidence simultaneously; and Gemini produced 22 requirements that trace, almost one-for-one, to real source artifacts. Validation passed (13 rules, 0 issues) and CP1 passed (0 findings), matching the CAP-076D baseline with no regression. The execution package is complete and internally consistent (12 artifacts, 0 checksum mismatches, 0 orphans), and an immutable Release Archive has been created.

The headline result: **the CAP-074B defect is resolved in practice, not just in principle.** In the archived run, every security requirement traces to a distinct OWASP ZAP finding and every quality requirement to a distinct SonarQube rule — the exact evidence that never reached the model before CAP-076D. Manual grounding assessment found 21 of 22 requirements Supported, 1 Partially Supported, and **0 hallucinated or unsupported**.

The one material caveat is not a defect but a known boundary: **nothing in the pipeline enforces grounding.** Validation and CP1 both passed without inspecting whether a requirement is supported by evidence, because neither is designed to. That is precisely the gap CAP-077 exists to close, and this validation produces its seed dataset.

**Release readiness: APPROVED as RC-1.** The repository is ready for CAP-077.

---

## 2. Repository Review (Phase 1)

Reviewed the runtime path and confirmed it matches the CAP-076C/CAP-076D architecture:

```
Connectors → Mappers → Consolidation → EngineeringContextOrchestrator
   → RequirementPromptBuilder → Gemini → ResponseNormalizer
   → Validation (13 rules) → CP1 → ExecutionWriter
```

Runtime wiring, verified live via `PlatformContext`:

| Component | State |
|---|---|
| Active policy | `DefaultOrchestrationPolicy` (`coverage` v1.0.0) |
| Selection strategy | `coverage_guaranteed` |
| Coverage mode | `all_present_categories` |
| Ranking keys | `risk_level_desc`, `artifact_count_desc`, `consolidated_id_asc` (tie: `consolidated_id_asc`) |
| Evidence ordering | `risk_then_record_id` |
| Evidence budget | 25 / domain, 60 total |
| `LegacySelectionPolicy` | available (control arm), not bound |
| Prompt (governed) | `requirement_analysis` v1.0.0 |
| Context orchestration version | 2.0.0 |
| Validation profile | `default` (13 rules) |

The tree was clean at `a2f7d0c`; `ruff check .` passed. Repository confirmed ready for live execution. No implementation changes made.

---

## 3. API Configuration Verification (Phase 2)

`EXECUTION_MODE=API` confirmed in `.env`. `health` reported all three sources READY.

| Check | Result |
|---|---|
| JIRA connector | authenticated, READY |
| SonarQube connector | authenticated, READY |
| OWASP ZAP connector | authenticated, READY |
| Gemini | reachable, `validate_connection` OK in 591 ms, model `gemini-3.1-flash-lite` |

Note: connector `validate_connection` returns in ~0 ms in API mode because it resolves configuration and credential presence, not a live round-trip. True retrieval latency is measured in Phase 4.

---

## 4. Connector Health (Phase 4)

Per-source retrieval, measured live:

| Source | Mapped artifacts | Category | Latency | Rejected/Dropped |
|---|---|---|---|---|
| JIRA | 28 | functional | 1212 ms | 0 unexpected |
| OWASP ZAP | 43 | security | 50 ms | 0 unexpected |
| SonarQube | 301 | quality | 210 ms | 0 unexpected |
| **Total** | **372** | | | |

All three sources contributed. No unexpected drops. Category/system distribution is clean (each source maps to exactly one category, as designed).

---

## 5. Consolidation Review (Phase 5)

372 source artifacts consolidated into **47 groups**. No regression from CAP-076D; Consolidation was not modified.

| Metric | Value |
|---|---|
| Groups | 47 |
| Grouping dimensions | endpoint 28, component 11, tag 8 |
| Largest groups (artifacts) | 71, 53, 33, 27, 23, 22, 21, 18 |
| Smallest groups | 1 (several) |
| **Single-domain groups** | **47 of 47** |
| Groups with functional / security / quality | 28 / 8 / 11 |

**Every group is single-domain** — this is the CAP-074B root cause, and it persists at the consolidation layer exactly as documented. It is *not* a defect to fix here: CAP-076D repairs it downstream by composing a multi-source context across these single-domain groups, rather than by changing how they are grouped.

---

## 6. Engineering Context Review (Phase 6)

`engineering_context.json` (artifact v2.0.0, model v1.2):

| Field | Value |
|---|---|
| Context ID | `ctx-automation-poc-…-badloginpage-java-7e6f57d42ea9` |
| Subject | `Automation-POC:…/BadLoginPage.java` — basis `multi` |
| Policy | `coverage` v1.0.0, `coverage_guaranteed`, `all_present_categories` |
| Candidate groups | 47 |
| Contributing groups | 26 |
| Selected / excluded (ranking) | 26 / 21 (47 ranked entries) |
| Evidence counts | functional 20, security 20, quality 20 (**total 60**) |
| Coverage — rule satisfied | True |
| Coverage — all present represented | **True** |
| Evidence budget | 60/60 used, truncated True |

Per-domain coverage and budget:

| Domain | Available | Allocated | Used | Contributing groups | Truncated |
|---|---|---|---|---|---|
| Functional | 28 | 20 | 20 | 20 | yes |
| Security | 43 | 20 | 20 | 5 | yes |
| Quality | 301 | 20 | 20 | 1 | yes |

Grounding metadata: domains `[functional, security, quality]`, source distribution `jira=20, owasp_zap=20, sonarqube=20`, coverage achieved True.

**Explainability is complete:** all 47 ranking entries carry a non-empty decision reason and a score with one component per ranking key; ranks are a contiguous 1..47 sequence; excluded groups cite the exhausted budget; truncated groups state which domain they were admitted to cover. All three evidence domains are present and represented.

The budget contested all three domains (ceilings 25+25+25 = 75 > 60), so water-filling allocated 20/20/20. **All three domains were truncated — including functional (20 of 28 available).** This is correct max-min behaviour but is a finding worth noting (§17).

---

## 7. Prompt Review (Phase 7)

`prompt.txt`: 22,967 characters, 2,583 words, 220 lines. Governed prompt `requirement_analysis` v1.0.0.

| Section | Rendered | "(None Provided)" |
|---|---|---|
| Functional Artifacts | 20 items | no |
| Security Findings | 20 items | no |
| Quality Findings | 20 items | no |

All three domain sections render real evidence in the governed structure and order (`risk_then_record_id`). No `(None Provided)` placeholder appears, correctly, because every domain has evidence. Estimated ~6,233 prompt tokens (measured, §16).

---

## 8. Gemini Response Review (Phase 8)

`raw_llm_response.json`: valid JSON, `finish_reason=STOP`, clean structure.

| Output | Count |
|---|---|
| functional_requirements | 10 |
| security_requirements | 6 |
| quality_requirements | 6 |
| risks | 5 |
| recommendations | 5 |

The summary explicitly integrates all three domains: *"significant security misconfigurations (CWE-693, 264, 1021, 345, 525) … Functional defects indicate instability in the checkout process and session management, while SAST findings highlight maintainability and reliability [issues]."* CWE codes come from ZAP, checkout/session defects from JIRA, SAST findings from Sonar.

**Multi-source reasoning demonstrably occurred.** Compared to CAP-074B — where the model saw only quality artifacts and fabricated security/functional requirements from code smells — this run grounds each domain's requirements in that domain's real evidence.

---

## 9. Manual Grounding Assessment (Phase 9)

Full traceability table archived at `manual_grounding_assessment.md`. All 22 requirements were traced to the specific artifacts present in the prompt.

| Verdict | Functional | Security | Quality | Total |
|---|---|---|---|---|
| Supported | 9 | 6 | 6 | **21** |
| Partially Supported | 1 | 0 | 0 | **1** |
| Likely Inferred | 0 | 0 | 0 | **0** |
| Unsupported | 0 | 0 | 0 | **0** |

Every security requirement (S1–S6) maps to a distinct ZAP alert (CSP, anti-clickjacking, CORS, SRI, X-Content-Type-Options, Cache-Control). Every quality requirement (Q1–Q6) maps to a distinct Sonar rule (`long-method`, `S2925`, `generic-exception`, `S4144`, `S108`, `poor-naming`). The single Partially-Supported item (F4) extrapolates "cart count" from a real "add to cart" story. **No hallucinations were observed.** This table is the baseline dataset for CAP-077.

---

## 10. Validation Review (Phase 10)

| Metric | Value |
|---|---|
| Overall verdict | **PASSED** |
| Profile | default |
| Rules executed | 13 |
| Issues / warnings / info | 0 / 0 / 0 |
| Overall health | healthy |

No regression. Note: Validation passed without detecting unsupported requirements because there were none *and* because Validation does not assess grounding by design (§17).

---

## 11. CP1 Review (Phase 11)

| Metric | Value |
|---|---|
| Overall verdict | **PASS** |
| Findings | 0 |
| Recommendations | 0 |
| Framework / criteria contract | 1.0.0 / 1.0 |

No regression. CP1 assesses engineering readiness, not evidence provenance; a passing verdict here is not a grounding guarantee.

---

## 12. Execution Package Review (Phase 12)

All 13 expected artifacts present:

`consolidated_artifact.json`, `engineering_context.json`, `prompt.txt`, `llm_request.json`, `analysis_result.json`, `raw_llm_response.json`, `validation_result.json`, `validation_report.md`, `cp1_report.md`, `execution_summary.md`, `review.md`, `baseline_metrics.md`, `manifest.json`.

Cross-references verified:

| Check | Result |
|---|---|
| `manifest.engineeringContextId` == `engineering_context.contextId` | ✓ |
| `manifest.selectedArtifactId` ∈ contributing ids | ✓ |
| `manifest.executionId` == `analysis_result.executionId` | ✓ |
| CP1 report execution/analysis/validation IDs consistent | ✓ |

---

## 13. Manifest Review (Phase 13)

| Check | Result |
|---|---|
| `engineering_context.json` registered | ✓ (SHA-256 + bytes) |
| Registered artifacts | 12 |
| Checksum mismatches | **0** |
| Byte-count mismatches | **0** |
| Files on disk not in manifest | none (only `manifest.json` itself, which does not checksum itself) |
| Manifest entries with no file | none |

Manifest carries the full orchestration surface: `selectionStrategy`, `candidateGroupCount` (47), `contributingGroupCount` (26), `contributingConsolidatedIds`, `evidenceDomainsRepresented` (all three), `coverageComplete` (True), `contextArtifactCount` (60), `contextOrchestrationVersion` (2.0.0). No orphaned artifacts.

---

## 14. Runtime Metrics Review (Phase 14)

`baseline_metrics.md` consumes the `EngineeringContext` rather than recomputing orchestration. Confirmed it reports policy (`coverage`), strategy (`coverage_guaranteed`), candidate/contributing group counts (47/26), per-domain evidence counts (20/20/20), coverage complete (True), budget allocated/used/truncated (60/60/True), and primary artifact rank (1) — all read from the orchestrator's recorded decisions. The `selected_artifact_rank` is read from `context.ranking.rank_of(...)`, discharging the CAP-076C residue.

---

## 15. Release Archive (Phase 15)

Immutable archive at `output/releases/ril-rc1-api-validation/`:

```
execution_package/         (all 13 execution artifacts)
environment.json           (commit, mode, policy, model, python, platform, versions)
runtime.log                (full CLI execution log)
connector_statistics.json  (per-source retrieval + consolidation distribution)
manual_grounding_assessment.md
cap-076d-release-candidate-validation.md   (this report)
```

`environment.json` records: commit `a2f7d0c`, tree clean, API mode, policy `coverage` v1.0.0, model `gemini-3.1-flash-lite`, Python 3.11.15, macOS-26.5.2-arm64, and all subsystem versions. The archive is outside version control (`output/` is gitignored) and is treated as immutable; future RC validations create new versioned folders. Reproducibility is anchored by the recorded commit SHA and the deterministic pipeline — the context, prompt, and orchestration are byte-reproducible for identical inputs; the live source data itself is the only non-reproducible input.

---

## 16. Runtime Summary (Phase 16)

| Metric | Value |
|---|---|
| Total source artifacts | 372 |
| Consolidated artifacts | 47 |
| Candidate groups | 47 |
| Contributing (selected) groups | 26 |
| Functional / Security / Quality evidence | 20 / 20 / 20 |
| Context total evidence | 60 |
| Prompt size | 22,967 chars / 2,583 words |
| Prompt tokens (measured) | 6,233 |
| Completion tokens | 802 |
| Total tokens | 7,035 |
| Functional / Security / Quality requirements | 10 / 6 / 6 |
| Risks / Recommendations | 5 / 5 |
| Validation | PASSED (13 rules, 0 issues) |
| CP1 | PASS (0 findings) |
| Gemini call latency | 3,490 ms |
| Connector latency (JIRA / ZAP / Sonar) | 1212 / 50 / 210 ms |

---

## 17. Findings (Phase 17)

**Strengths**
- All three source systems contribute; all three evidence domains reach the reasoner. CAP-074B defect resolved in practice.
- Grounding quality is high: 21/22 requirements Supported, 0 hallucinated, with 1-to-1 traceability for security and quality.
- Orchestration is fully explainable: 47 ranking entries, each with a score and a decision reason; coverage and budget recorded per domain.
- Execution package is complete and internally consistent (0 checksum/byte mismatches, 0 orphans, cross-references intact).
- Deterministic, reproducible context/prompt; metrics read orchestrator decisions rather than recomputing them.

**Weaknesses / limitations**
- **Grounding is unenforced.** Validation and CP1 both pass without checking whether requirements are evidence-supported. A hallucinated requirement in a future run would pass both gates undetected. (This is the CAP-077 mandate, not a regression.)
- **Functional evidence is truncated (20 of 28).** With three domains contesting a 60-artifact budget, max-min fairness caps each at 20 — but functional had only 28 available, so 8 JIRA issues (nearly 30%) were dropped despite being the scarcest, highest-value domain.
- **Quality is represented by a single group.** All 20 quality artifacts come from one Sonar file group (`BadLoginPage.java`, 71 findings truncated to 20); the other 10 quality groups contributed nothing. Quality breadth across files is lost.

**Unexpected behaviour**
- None. Runtime behaviour matched the CAP-076D design and the earlier FILE/API demonstrations exactly (47 groups → 26 contributing → 20/20/20).

**Potential improvements (report only — do not implement)**
- Consider a coverage-floor or demand-aware allocation so a scarce domain (functional, 28 available) is not truncated to the same fair share as an abundant one (quality, 301). Water-filling already does this when a domain is *below* the equal share; here functional sits just above it.
- Consider spreading a domain's budget across more contributing groups (e.g. quality across files) rather than filling from the single highest-ranked group.

---

## 18. Risks

**Runtime risks** — Low. Live connectors and Gemini responded within normal latencies; the run completed in ~7 s wall-clock. Source data volume (372 artifacts) is well within budget-handling capacity.

**Prompt risks** — Low. Prompt is governed, versioned, and renders all domains correctly at ~6.2k tokens, comfortably within model limits. No prompt wording changed.

**Engineering Context risks** — Low–Medium. The context is correct and explainable, but the fixed 25/60 budget produces domain truncation that discards value-dense functional evidence (see §17). Not a correctness bug; a tuning question for a future milestone.

**Grounding risks** — **Medium–High (the primary open risk).** This run was clean, but nothing structurally prevents an unsupported requirement from being generated, validated, CP1-approved, and shipped. The gates do not read `grounding` metadata. This is the single most important reason CAP-077 must precede any production reliance.

---

## 19. Recommendations

1. **Proceed to CAP-077 (Evidence Grounding & Traceability)** as the next milestone. This validation confirms the evidence surface is correct; the remaining exposure is that grounding is measured but not enforced.
2. Use `manual_grounding_assessment.md` as the labelled baseline dataset for CAP-077.
3. Treat evidence-budget tuning (domain truncation, single-group quality) as a candidate for a later, separate milestone — report-only for now.
4. Consider tagging this commit (`a2f7d0c`) so the Release Archive's `gitTag` is populated for future reproducibility.

---

## 20. Release Readiness

**APPROVED as RC-1.** Every success criterion is met:

- ✓ API mode executed successfully
- ✓ All three connectors retrieved live data
- ✓ Engineering Context contains functional, security, and quality evidence
- ✓ Prompt renders all evidence domains
- ✓ Gemini reasoned across all available evidence
- ✓ Execution package complete (13 artifacts, 0 mismatches, 0 orphans)
- ✓ Release Archive created and immutable
- ✓ Manifest correct and fully cross-referenced
- ✓ Validation stable (PASSED, no regression)
- ✓ CP1 stable (PASS, no regression)
- ✓ Manual grounding assessment completed
- ✓ Repository readiness confirmed (no source changes, ruff clean, tests green)

---

## 21. CAP-077 Readiness

The repository is ready for CAP-077. The evidence pipeline is verified correct and multi-source; the remaining gap — enforced grounding — is exactly CAP-077's scope. The manual grounding assessment (22 requirements, fully traced) provides the seed dataset. `EngineeringContext` already carries per-artifact `(sourceSystem, sourceRecordId)` traceability and grounding metadata that CAP-077 can build enforcement upon without new plumbing.

---

## Explicit Questions — Answers

1. **Did all three source systems contribute evidence?** Yes — JIRA 20, OWASP ZAP 20, SonarQube 20 artifacts in the context (28/43/301 retrieved).
2. **Did Engineering Context contain all three evidence domains?** Yes — functional, security, and quality all present and represented; coverage complete.
3. **Did Gemini reason across multiple evidence domains?** Yes — the summary and per-domain requirements integrate JIRA, ZAP, and Sonar evidence.
4. **Did any hallucinated requirements appear?** No — none observed in this run.
5. **Which requirements were unsupported?** None.
6. **Supported / Partially / Inferred / Unsupported?** 21 / 1 / 0 / 0 (of 22).
7. **Did Validation detect unsupported requirements?** No — there were none, and Validation does not assess grounding by design.
8. **Did CP1 detect unsupported requirements?** No — same reason; CP1 assesses engineering readiness, not provenance.
9. **Is Engineering Context explainable?** Yes — all 47 candidates ranked with scores and decision reasons; coverage and budget recorded per domain.
10. **Is the execution package complete?** Yes — 13 artifacts, 0 checksum/byte mismatches, 0 orphans, cross-references intact.
11. **Is the Release Archive complete and reproducible?** Yes — complete; reproducible up to the live source data, anchored by commit SHA and a deterministic pipeline.
12. **Is the repository ready for CAP-077?** Yes.
