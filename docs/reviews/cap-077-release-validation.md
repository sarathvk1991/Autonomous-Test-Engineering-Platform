# CAP-077 — Release Validation (Requirement Intelligence v1.2.0)

**Milestone:** CAP-077F.2 — Grounding Runtime Activation, Golden Re-baseline & Architecture Version 1.2.0
**Architecture Version:** 1.2.0 (frozen) · **Golden Dataset:** 1.1.0 · **Platform Version:** 1.0.0 (unchanged)
**Status:** Grounding is active in the live Requirement Intelligence pipeline.

---

## 1. What shipped

Grounding is now wired into the live execution pipeline, strictly downstream of Analysis:

```
Engineering Context Orchestration → Prompt Builder → Gemini → AnalysisResult
    → Grounding (GroundingService.assess) → GroundingResult
    → Normalization → Validation → CP1 → Execution Package
```

`GroundingService.assess(engineering_context, analysis_result)` runs on every non-dry run and
returns a `GroundingResult`, which the CLI places on `ExecutionData.grounding_result`. The
Execution Writer then serializes three **pure projection** artifacts —
`grounding_result.json`, `grounding_report.md`, `grounding_metrics.md` — via the same
conditional mechanism as validation/CP1. The manifest registers them automatically. Grounding
**modifies nothing upstream** (AnalysisResult, prompt, EngineeringContext, Validation, CP1 are
untouched) and never aborts a run: a requirement that cannot be grounded becomes an UNSUPPORTED
finding and processing continues.

No architecture was redesigned. No canonical model, policy, builder, contract, pipeline order,
or algorithm changed. The runtime was wired; the golden baseline was re-based; the Architecture
Version was advanced.

## 2. Deterministic validation (golden stub)

The golden productization pipeline (deterministic `GoldenStubProvider`, no network) exercises
the full path end to end. Grounding assessment for the golden run:

| Metric | Value |
|---|---|
| Grounded requirements | 8 |
| Support distribution | SUPPORTED 8 · PARTIALLY 0 · WEAKLY 0 · UNSUPPORTED 0 · CONTRADICTED 0 · UNKNOWN 0 |
| Findings (hallucinations) | 0 |
| Grounding score | 80 |
| Grounding coverage | 1.00 |
| Hallucination rate | 0.00 |
| Evidence coverage | 1.00 |
| Average confidence | 80.0 (HIGH) |
| Artifacts written | 15 (+ manifest) |

Every one of the eight generated requirements traces to evidence in the `EngineeringContext`;
none is a hallucination. The result is **deterministic**: two consecutive runs produce identical
grounding content (support distribution, score, hallucination rate, grounded-requirement ids,
finding ids). Per-run timestamps on `grounding_result.json` are provenance, excluded from the
determinism comparison exactly like `analysis_result.json` timestamps (golden-baseline §6).

**Traceability / hallucination detection.** Requirement ids are minted deterministically from
`(domain, normalized text)`, so the same requirement always yields the same id run to run.
Hallucination detection is the UNSUPPORTED/CONTRADICTED classification: any requirement with no
supporting evidence becomes a `GroundingFinding` (none in the golden run). The RC-1 lesson is
enforced — UNKNOWN (no evidence examined) is kept distinct from UNSUPPORTED (evidence present,
none supported), so a coverage gap is never miscounted as a hallucination.

## 3. Manifest & Execution Package integrity

`manifest.json → generatedArtifacts` lists all 15 non-manifest artifacts including the three
grounding files, each with a byte count and SHA-256 that the productization suite re-hashes on
disk. The grounding artifacts are **reproducible from the `GroundingResult` alone**
(`GroundingResult.model_validate(render_json(r)) == r`), and the Markdown files are byte-identical
to a direct `GroundingSerializer` projection of the same result — verified by test.

## 4. Regression suite

| Suite | Result |
|---|---|
| Full repository (`-m "not integration and not e2e"`) | **passing** |
| Productization / golden (`-m productization`) | **passing** (re-baselined to 15 artifacts) |
| Grounding unit suites | passing |
| Validation, CP1 suites | passing, **unchanged** |
| Ruff | clean |

The golden dataset version was advanced 1.0.0 → 1.1.0 under the §7.3 re-baseline procedure (new
artifacts, same source inputs and golden response). The Architecture Version was advanced
1.1.0 → 1.2.0 (the deferred CAP-076F recommendation), reflecting that a whole governed subsystem
— Grounding — is now live in the pipeline.

## 5. Live RC run (FILE / API) — operator step

This validation used the deterministic golden stub, which proves the integration, determinism,
artifact completeness, and manifest integrity **without a provider call**. A full **live** RC run
against real Gemini (FILE mode) and live connectors (API mode) requires a `GOOGLE_API_KEY` and
reachable JIRA / SonarQube / OWASP ZAP, and is the operator's step:

```bash
# FILE mode
python scripts/run_requirement_analysis.py analyze --validate --save-execution --execution-name ril-v1.2.0

# API mode
EXECUTION_MODE=API python scripts/run_requirement_analysis.py analyze --validate --save-execution --execution-name ril-v1.2.0-api
```

Each live run now emits the three grounding artifacts alongside the existing package. Archive the
resulting package under `output/releases/ril-v1.2.0/` together with `environment.json`,
`runtime.log`, connector statistics, the grounding assessment, a manual grounding review, the
validation/CP1 outputs, the manifest, and hashes — the same shape as the archived RIL RC-1
(`output/releases/ril-rc1-api-validation/`). The manual grounding review should trace each live
requirement to its evidence, as RC-1 did (21 supported / 1 partially / 0 unsupported).

## 6. Architecture verification (final)

- ✓ Engineering Context Orchestration remains the only context-composition owner.
- ✓ `GroundingService` remains the only grounding-orchestration owner; `GroundingPipeline` stays private.
- ✓ Matching owns only comparison; Classification only support determination; Confidence only confidence.
- ✓ Builders assemble only; the Execution Package serializes only (grounding artifacts are pure projections).
- ✓ Validation, CP1, and Prompt Governance are unchanged.
- ✓ Runtime is deterministic; `GroundingResult` remains the runtime contract; the manifest remains the package index.
- ✓ Architecture Version is now **1.2.0**.

The Requirement Intelligence Layer — Engineering Context Orchestration → Analysis → Grounding →
Validation → CP1 → Execution Package — is fully integrated, deterministic, governed, and
release-ready.
