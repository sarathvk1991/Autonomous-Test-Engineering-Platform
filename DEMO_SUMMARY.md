# Demo Summary — Requirement Intelligence Platform

> Generated from the actual execution package at
> `output/executions/demo-readiness-20260720/`. All figures below were read
> from `manifest.json` and the per-subsystem `*_result.json` / `*_report.md`
> files, not assumed.

## Repository Status

| Check | Result |
| --- | --- |
| Git branch | `main`, up to date with `origin/main` |
| Working tree | Clean (no uncommitted changes) |
| Python | 3.11.15 (venv) |
| Test suite | **4,642 passed**, 0 failed, 1 unrelated deprecation warning |
| Source health (FILE mode) | JIRA, OWASP ZAP, SonarQube — all `READY` |
| Source health (API mode) | JIRA, OWASP ZAP, SonarQube — all `READY` |
| Golden dataset | 3 files, all valid JSON (`jira-issues.json`: 3 records, `sonar-issues.json`: 8, `zap-alerts.json`: 83) |
| Env configuration | `.env` present, all vars in `.env.example` accounted for, `EXECUTION_MODE=API` |

## Execution Success

**Result: SUCCESS.** The complete pipeline — Connectors → Mappers → Consolidation → Engineering Context → Prompt → LLM → Analysis → Requirement Enhancement → Grounding → Validation → CP1 → Quality Governance → Recommendation → Continuous Improvement → Knowledge Graph → Organizational Memory → Learning → Execution Package — ran end to end in a single live invocation with no manual intervention and no code changes required.

| Field | Value |
| --- | --- |
| Execution Id | `c1ab42ec-adb5-4efd-ba74-e7a968a1b5f4` |
| Execution Package Id | `EP-20260720-070156-c1ab42ec` |
| Analysis Id | `ede0d272-a94a-4a33-b8f7-1f2426752bac` |
| Execution Folder | `output/executions/demo-readiness-20260720/` (mirrored to `output/latest/`) |
| Execution Mode | API (live JIRA + SonarQube + OWASP ZAP) |
| Provider / Model | gemini / gemini-3.1-flash-lite |
| Execution Duration | 3,812.26 ms |
| `executionSucceeded` | `true` |
| Platform Version | 1.0.0 |
| Architecture Version | 1.2.0 |
| Execution Package Version | 1.0.0 |
| Golden Dataset Version | 1.1.0 (this run used live API data, not the golden FILE baseline — see Caveats) |

## Total Artifacts Generated

| Category | Count |
| --- | --- |
| Total files in package | 37 (36 generated + `manifest.json`) |
| Markdown reports | 21 |
| JSON files | 16 (15 generated + `manifest.json`) |
| Package size | ~1.1 MB |
| Checksum verification | **36/36 artifacts verified** against `manifest.json` SHA-256 + byte count, 0 mismatches, 0 missing |

## Subsystem Status Table

| Subsystem | Executed | Verdict / Headline Result |
| --- | --- | --- |
| Connectors (JIRA, ZAP, SonarQube) | ✓ | 329 source artifacts ingested |
| Consolidation | ✓ | 39 consolidated artifacts |
| Engineering Context Orchestration | ✓ | 26/39 groups admitted, coverage complete, policy `coverage` v1.0.0 |
| Prompt Builder | ✓ | 16,593-char prompt, version 1.0.0 |
| LLM (Gemini) | ✓ | Valid JSON response, 3,556 chars |
| Requirement Analysis | ✓ | 18 requirements (9 functional, 3 security, 6 quality), 4 risks |
| Requirement Enhancement | ✓ | 18 enhanced, 1 finding (disconnected relationship graph) |
| Grounding | ✓ | 18/18 supported, 0 hallucinations, score 80 |
| Validation | ✓ | **PASSED**, 13/13 rules, 0 issues |
| CP1 (Engineering Readiness) | ✓ | **PASS**, 0 findings |
| Quality Governance | ✓ | **PASS** (release decision), score 80, 0 findings |
| Recommendation | ✓ | 1 recommendation generated, traced to Enhancement finding |
| Continuous Improvement | ✓ | 0 findings/trends/opportunities (single-execution history — expected) |
| Knowledge Graph | ✓ | 6 nodes, 6 edges, 1 fully-connected subgraph, 0 dangling refs |
| Organizational Memory | ✓ | 4 experiences captured, 0 lessons/best practices (single-run, expected) |
| Learning | ✓ | 0 candidates/learnings (gated on Org Memory best practices, none yet — expected) |
| Execution Package | ✓ | 36 artifacts + manifest, all checksum-verified |

## Layer 1 Summary

Ingestion through Execution Readiness. All green: 329 source artifacts → 39 consolidated groups → a governed 50-artifact evidence context → one Gemini call → 18 generated requirements → Validation **PASSED** (13/13 rules) → CP1 **PASS**. No issues at any layer, any severity.

## Layer 2 Summary

Requirement Enhancement through Quality Governance and Recommendation. Enhancement enriched all 18 requirements and correctly flagged a genuine structural fact (a fully disconnected relationship graph) rather than suppressing it. Grounding independently confirmed all 18 requirements are evidence-supported with 0 hallucinations. Quality Governance issued the terminal release decision — **PASS** — consuming Grounding, Validation, and CP1 without re-deriving any of them. Recommendation turned the one Enhancement finding into one actionable, traceable recommendation.

## Learning Summary

Continuous Improvement, Knowledge Graph, Organizational Memory, and Learning all executed successfully and produced internally consistent output. Knowledge Graph built a fully-connected 6-node graph with zero dangling references. Organizational Memory captured 4 low-confidence experiences from it. Continuous Improvement and Learning both correctly report **zero output** for this run — both are gated on accumulated history (Continuous Improvement needs multiple executions to detect a trend; Learning needs Organizational Memory to have promoted at least one best practice, which itself needs repeated experience). This is the deterministic learning architecture behaving exactly as governed: nothing is fabricated to look active on a single run.

## Known Caveats

1. **This run used live API data, not the golden FILE baseline.** The Golden Baseline (`docs/productization/golden-baseline.md`, dataset v1.1.0) is a fixed regression fixture; this execution instead exercised the live JIRA/SonarQube/OWASP ZAP path with `EXECUTION_MODE=API`, which is a stronger demo (real systems) but not the frozen regression comparison point.
2. **Continuous Improvement, Organizational Memory, and Learning show zero-output on this single execution.** This is architecturally correct, not a defect — see Learning Summary above. Running `analyze --validate` two or three more times against the same sources will populate trend and lesson data for a richer live demo.
3. **`platformVersion` in the manifest (1.0.0) does not match the documented `Architecture Version` (1.2.0)** referenced in `README.md` and the golden baseline doc. Both numbers are legitimate — the manifest tracks the execution-package/manifest schema lineage, the architecture version tracks the overall capability milestone — but a presenter should be ready to explain the distinction if asked.
4. **API mode banner reads `CONFIGURED`, not `READY`.** By design — startup validation deliberately makes no network call; use `health` for live reachability proof (Stage 0 of the runbook already does this).
5. **Grounding score and Quality score are both 80/100, not 100.** This is the actual, unmassaged result of this live run — no threshold was lowered to make the demo look better. Worth stating plainly if asked.

## Demo Recommendations

- Use the **live API-mode run** for the "wow" moment (real JIRA/SonarQube/ZAP data, not canned fixtures) — Stage 1–2 of `DEMO_RUNBOOK.md`.
- Spend the most time on **Grounding** (Stage 7) and **Learning** (Stage 15) — they're the two stages that most directly answer "how do you know the AI isn't hallucinating or faking progress," and both have a clean, defensible answer from this exact run.
- If there's time, run `analyze --validate` two more times live to show Continuous Improvement and Organizational Memory activate with real trend/lesson data — this is called out as a demo tip in the runbook.
- Keep `manifest.json` open in a second window throughout — it's the single file that answers almost any "how do you know" question via SHA-256/byte-count cross-reference.
