# Golden End-to-End Validation Baseline

**CAP-070 — Productization Milestone 1**  
Baseline Role: Release Regression Baseline (Requirement Intelligence v1.1.0)  
Architecture Version: 1.1.0 (frozen)  
Dataset Version: 1.0.0  
Status: RELEASE REGRESSION BASELINE ESTABLISHED

---

## Overview

> **The Golden Baseline is the Release Regression Baseline for Requirement
> Intelligence v1.1.0.**

This document is the permanent reference for the Requirement Intelligence pipeline's
golden execution baseline. It records the dataset, the execution flow, the expected
artifacts, the determinism contract, and the procedure future regression testing must
follow to compare any run against this baseline.

The Release Regression Baseline validates the **architecture and its runtime
behaviour**, not performance or prompt quality. Concretely, it confirms that a run
against the golden dataset satisfies each of the following:

- **Architecture** — every governed subsystem is present and wired correctly.
- **Execution flow** — the subsystems execute in the governed pipeline order
  (Consolidation → Analysis → Normalization → Validation → CP1 → Execution Package).
- **Execution artifacts** — every governed artifact is generated.
- **Manifest integrity** — the manifest's checksums, byte counts, cross-references,
  and version fields agree with the on-disk artifacts.
- **Validation** — the Response Validator executes and the golden response passes.
- **CP1** — the Validation → CP1 gate opens and CP1 (`CP1-0001`) evaluates to PASS.
- **Deterministic execution** — two consecutive runs on the same input produce
  identical findings and verdicts (excluding per-run provenance).

It deliberately does **not** validate prompt quality: the LLM response is a fixed,
deterministic stub, so this baseline asserts nothing about how good a real model's
answer would be.

Because it is a **release regression baseline**, every future release of Requirement
Intelligence is compared against it: a future run that diverges from the expected
architecture, flow, artifacts, manifest integrity, validation outcome, CP1 outcome, or
determinism contract recorded here is a regression until it is explicitly re-baselined
(see §7.3).

---

## 1. Golden Dataset

### 1.1 Dataset Identity

| Field | Value |
|---|---|
| Dataset Version | 1.0.0 |
| Location | `tests/productization/fixtures/golden_dataset.py` |
| Module under test | `authentication` |
| Total source artifacts | 9 |

### 1.2 Source Artifacts

All nine artifacts share `component = "authentication"`, causing the consolidation
engine to produce exactly one `ConsolidatedArtifact`.

#### Functional (JIRA)

| Artifact ID | Source Record | Type | Title |
|---|---|---|---|
| `golden-jira-001` | AUTH-1 | EPIC | Authentication Service — Phase 1 |
| `golden-jira-002` | AUTH-2 | STORY | Account lockout after five failed login attempts |
| `golden-jira-003` | AUTH-3 | STORY | New session token issued on each successful login |
| `golden-jira-004` | AUTH-4 | STORY | Sessions invalidated on password change |

#### Security (OWASP ZAP)

| Artifact ID | Source Record | Type | Title |
|---|---|---|---|
| `golden-zap-001` | ZAP-ALERT-10001 | DAST | SQL Injection in POST /api/auth/login |
| `golden-zap-002` | ZAP-ALERT-10002 | DAST | Weak session token entropy on GET /api/auth/session |
| `golden-zap-003` | ZAP-ALERT-10003 | DAST | Authentication endpoints accessible over plain HTTP |

#### Quality (SonarQube)

| Artifact ID | Source Record | Type | Title |
|---|---|---|---|
| `golden-sonar-001` | SQ-ISSUE-50001 | SAST | Branch coverage 42% on AuthenticationHandler |
| `golden-sonar-002` | SQ-ISSUE-50002 | SAST | Hardcoded database password in AuthDataSource.java |

### 1.3 Golden LLM Response

The stub provider (`GoldenStubProvider`) returns a fixed, deterministic JSON string
defined in `GOLDEN_LLM_RESPONSE_TEXT`. The response:

- Is strict-JSON-parseable (no Markdown fences, no prose outside the object)
- Contains every required key: `summary`, `functional_requirements`,
  `security_requirements`, `quality_requirements`, `risks`, `recommendations`
- Passes all implemented Transport, Syntax, Schema, Content, and Reasoning validation rules
- Contains ≥1 requirement in every category (CP1-0001 PASS condition)

#### Expected Response Counts

| Field | Count |
|---|---|
| `functional_requirements` | 3 |
| `security_requirements` | 3 |
| `quality_requirements` | 2 |
| `risks` | 2 |
| `recommendations` | 3 |

---

## 2. Pipeline Execution Flow

The pipeline is executed in full, subsystem by subsystem, in the governed order.
No connector I/O is performed: the dataset is constructed in-process.

```
GOLDEN_SOURCE_ARTIFACTS (9 SourceArtifacts)
        │
        ▼
ConsolidationEngine.consolidate()
        │
        ▼  1 ConsolidatedArtifact (module: "authentication")
        │
        ▼
RequirementPromptBuilder.build(selected)  → PromptRequest
        │
        ▼
GoldenStubProvider.generate(llm_request)  → LLMResponse (fixed golden JSON)
        │
        ▼
RequirementAnalysisService.analyze(selected)  → AnalysisResult
        │
        ▼
ResponseNormalizer.normalize(llm_response)  → NormalizationResult + ParsedResponse
        │
        ▼
ValidationInput(analysis_result, normalization_result)
        │
        ▼
ResponseValidator.validate(validation_input)  → ValidationResult
        │
        ▼ (gate: PASSED or PASSED_WITH_WARNINGS)
ValidationToCP1Handoff.hand_off(...)  → CP1Input
        │
        ▼
CP1Service.run(cp1_input)  → CP1Result (CP1-0001: PASS)
        │
        ▼
ExecutionWriter.write(target_dir, execution_data)  → artifacts + manifest.json
```

### 2.1 Stub Provider Configuration

| Field | Value |
|---|---|
| Class | `GoldenStubProvider` |
| Location | `tests/productization/conftest.py` |
| `provider_name` | `golden-stub` |
| `model` | `golden-stub-model-1.0` |
| `provider` (enum) | `ProviderType.GEMINI` (existing enum member; stub only) |
| Network calls | None |

---

## 3. Expected Artifacts

Every run against the golden dataset must produce the following files in its
output directory.

| Artifact | Type | Description |
|---|---|---|
| `consolidated_artifact.json` | JSON | Serialised ConsolidatedArtifact (all 9 source artifacts) |
| `prompt.txt` | Text | System prompt + user prompt submitted to the stub provider |
| `llm_request.json` | JSON | Provider-agnostic LLMRequest |
| `analysis_result.json` | JSON | Serialised AnalysisResult |
| `raw_llm_response.json` | JSON | Serialised LLMResponse (golden stub output) |
| `execution_summary.md` | Markdown | Human-readable execution summary (includes CP1 section) |
| `baseline_metrics.md` | Markdown | Engineering and AI metrics table |
| `review.md` | Markdown | Qualitative review scaffold |
| `validation_result.json` | JSON | Complete ValidationResult (verdict, issues, statistics) |
| `validation_report.md` | Markdown | Human-readable validation report |
| `cp1_report.md` | Markdown | CP1 engineering-readiness report |
| `manifest.json` | JSON | Complete manifest (checksums, byte counts, version fields) |

Total: **12 artifacts** (11 + manifest).

### 3.1 Manifest Requirements

The `manifest.json` must satisfy:

1. `manifestSchemaVersion = "1.0.0"`
2. `platformVersion = "1.0.0"`
3. `executionMode = "live"`
4. `dryRun = false`
5. `cp1Executed = true`
6. `cp1Verdict = "pass"`
7. `cp1Report = "cp1_report.md"`
8. All 11 non-manifest artifacts listed in `generatedArtifacts`
9. Every `sha256` in `generatedArtifacts` matches the SHA-256 of the on-disk file
10. Every `bytes` in `generatedArtifacts` matches the on-disk file size
11. `analysisId` matches `analysis_result.json → analysisId`
12. `executionId` matches `analysis_result.json → executionId`
13. `promptSha256` is the SHA-256 of the full prompt string (`system + "\n\n" + user`)
14. `responseSha256` is the SHA-256 of the raw `generated_text`

---

## 4. Expected Validation Outcome

| Metric | Expected value |
|---|---|
| Overall verdict | `passed` or `passed_with_warnings` |
| Transport issues | 0 |
| Syntax issues | 0 |
| Schema issues | 0 |
| Content issues | 0 |
| Reasoning issues | 0 |

The golden response is designed to pass all implemented rules. If any new
rule causes the golden response to fail, the rule must be reviewed: either the
rule is correct and the golden response must be updated (with ADR justification),
or the rule has a defect.

---

## 5. Expected CP1 Outcome

| Metric | Expected value |
|---|---|
| Overall verdict | `PASS` |
| Findings (FAIL) | 0 |
| CP1-0001 | PASS (≥1 requirement in functional + security + quality) |

The gate opens because the Validation verdict is `PASSED` / `PASSED_WITH_WARNINGS`.
CP1-0001 (`EngineeringInputAvailabilityCriterion`) evaluates to PASS because the
golden response contains three requirements in each of the three governed categories.

---

## 6. Determinism Contract

The following fields MUST be identical across any two runs with the same golden dataset:

| Field | Location |
|---|---|
| `overall_verdict` | `ValidationResult` |
| Issue count | `ValidationResult.validation_issues` |
| Rule IDs in issues | Each `ValidationIssue.rule_id` |
| Normalization outcome | `ParsedResponse.normalization_outcome` |
| `normalized_structure` | `ParsedResponse.normalized_structure` |
| CP1 overall verdict | `CP1Result.overall_verdict` |
| CP1 finding count | `CP1Result.findings` |
| CP1 criterion IDs | Each `CP1Finding.criterion_id` |
| Consolidated artifact count | `len(consolidated_artifacts)` |
| Selected module name | `ConsolidatedArtifact.module` |
| `manifest.cp1Verdict` | `manifest.json` |
| `generated_text` (raw response) | `LLMResponse.generated_text` |

The following fields are **excluded** from determinism comparisons (per-run provenance):

- Timestamps (`started_at`, `completed_at`, execution timestamps)
- UUIDs / IDs (`analysis_id`, `execution_id`, `validation_id`, `normalization_id`,
  `cp1_id`, `finding_id`, `issue_id`)

---

## 7. Regression Testing Procedure

Future runs that compare against this baseline must follow this procedure:

### 7.1 Running the Productization Tests

```bash
# Run all productization tests
pytest tests/productization/ -m productization -v

# Run a specific phase
pytest tests/productization/ -m productization -k "Phase3"
pytest tests/productization/ -m productization -k "Phase4"
pytest tests/productization/ -m productization -k "Phase5"
pytest tests/productization/ -m productization -k "Phase6"
```

### 7.2 Interpreting Failures

| Test class | Failure means |
|---|---|
| `TestPhase3PipelineExecution` | A subsystem failed to execute or produced no output |
| `TestPhase4OutputVerification` | An artifact is missing, corrupt, or internally inconsistent |
| `TestPhase5Determinism` | A subsystem introduced non-determinism on stable inputs |
| `TestPhase6ProductizationAssertions` | A version field, count, or contract field regressed |

### 7.3 Updating the Baseline

The golden dataset and expected values **must not be changed** without an explicit
decision. If the pipeline is intentionally modified (new rules, new artifacts,
updated counts):

1. Run the productization tests to confirm the failure is expected.
2. Update `GOLDEN_DATASET_VERSION` in `golden_dataset.py`.
3. Update the expected counts/values in `golden_dataset.py` and `test_golden_baseline.py`.
4. Re-run to confirm all tests pass.
5. Update this document.

Changing the baseline without a corresponding intentional pipeline change is a
regression.

---

## 8. Test Coverage Summary

The productization test suite (`tests/productization/test_golden_baseline.py`) contains
the following test classes and coverage targets:

| Class | Tests | Coverage area |
|---|---|---|
| `TestPhase3PipelineExecution` | 14 | Every subsystem executes and produces output |
| `TestPhase4OutputVerification` | 30 | Artifacts present, content correct, manifest integrity |
| `TestPhase5Determinism` | 12 | Two runs produce identical findings and verdicts |
| `TestPhase6ProductizationAssertions` | 14 | Per-layer contracts, version fields, cross-references |
| **Total** | **70** | |

---

## 9. Future Golden Regression Datasets

This section is **informational only**. It records the planned evolution of the
Release Regression Baseline into a governed family of golden datasets. None of the
datasets below beyond *Golden PASS* is implemented; no placeholders exist in the
repository for them. They are documented here so the intended direction is explicit.

The baseline is planned to grow to exactly **three** governed datasets:

| # | Dataset | Purpose | Status |
|---|---|---|---|
| 1 | `Golden PASS` | Complete successful execution. | Implemented |
| 2 | `Golden Validation FAIL` | Exercise Validation failures. | Planned |
| 3 | `Golden CP1 FAIL` | Exercise Engineering Readiness failures. | Planned |

- **Dataset 1 — `Golden PASS`.** The dataset documented throughout this file: a
  clean, fully successful end-to-end run in which Validation passes, the CP1 gate
  opens, and CP1 evaluates to PASS. **Implemented.**
- **Dataset 2 — `Golden Validation FAIL`.** A future dataset whose input drives the
  Response Validator to a failing verdict, exercising the Validation-failure path and
  the resulting closed CP1 gate. **Planned** — not yet implemented.
- **Dataset 3 — `Golden CP1 FAIL`.** A future dataset that passes Validation but fails
  an Engineering Readiness criterion, exercising the CP1 FAIL path. **Planned** — not
  yet implemented.

---

## 10. Repository Readiness Assessment

Architecture v1.1.0 has been validated against this golden baseline.

| Subsystem | Status | Notes |
|---|---|---|
| ConsolidationEngine | ✓ VALIDATED | Deterministic grouping confirmed |
| RequirementAnalysisService | ✓ VALIDATED | Orchestration boundary exercised |
| ResponseNormalizer | ✓ VALIDATED | ParsedResponse populated correctly |
| ResponseValidator | ✓ VALIDATED | All rules execute; golden response passes |
| ValidationToCP1Handoff | ✓ VALIDATED | Gate opens correctly for passing verdict |
| CP1Engine + CP1Service | ✓ VALIDATED | CP1-0001 evaluated; PASS verdict confirmed |
| ExecutionWriter | ✓ VALIDATED | All 12 artifacts generated; manifest integrity verified |
| PlatformContext | ✓ VALIDATED | Correct construction and wiring confirmed |

**Repository status: ARCHITECTURE VALIDATED — RELEASE REGRESSION BASELINE ESTABLISHED**

---

## 11. Governance Registration (CAP-070B)

Productization is a **governed platform capability**, registered as **CAP-070** in the
governance layer:

| Governance record | Location |
|---|---|
| Capability registration | [Platform Capability Matrix](../governance/platform-capability-matrix.md) §5.7 (CAP-070) |
| Coverage | [Architecture Coverage Dashboard](../governance/architecture-coverage-dashboard.md) §4 (CAP-070) |
| Freeze register | [Architecture Freeze Index](../governance/architecture-freeze-index.md) §4 (Productization Governance Contract) |
| Governing document | This document (`docs/productization/golden-baseline.md`) |

CAP-070B is a **governance-only** registration: it records an existing repository asset
as an official architectural capability. It introduces no code, no ADR, and no
architecture change.

## 12. Ownership Boundaries

Productization has a single, narrow responsibility — **verification of the completed
architecture** — and deliberately owns nothing else. The boundaries below are frozen as
part of the governance contract (§13):

| Concern | Owner | Productization's relationship |
|---|---|---|
| Implementation of the pipeline | Architecture (the pipeline subsystems) | **Consumes** — never modifies |
| Correctness of the response | Validation (CAP-041) | **Consumes the verdict** — does not judge correctness |
| Engineering readiness | CP1 (CAP-060) | **Consumes the verdict** — does not judge readiness |
| Normalization / Analysis / Connectors / Prompt Engineering | Their respective capabilities | **Consumes outputs** — owns none of them |
| Artifact reporting | Execution Package (CAP-020) | **Consumes artifacts** — does not produce reports |
| **End-to-end verification** | **Productization (CAP-070)** | **Owns** — the golden regression baseline, the productization test suite, the release regression datasets, and the deterministic end-to-end contract |

> **Productization consumes the completed architecture; it owns verification of that
> architecture.** It does not own — and must never absorb — Validation, CP1,
> Normalization, Analysis, Connectors, or Prompt Engineering.

## 13. Governance Contract Freeze

The **governance contract** described by this document is **frozen**:

- The baseline's *role* (Release Regression Baseline for Requirement Intelligence
  v1.1.0), its *validation scope* (§Overview), its *determinism contract* (§6), its
  *ownership boundaries* (§12), and its *regression procedure* (§7.3) are immutable
  and change only through a deliberate governance decision.

The **golden dataset contents are explicitly NOT frozen**:

- The dataset (`tests/productization/fixtures/golden_dataset.py`) remains **versioned
  independently** via `GOLDEN_DATASET_VERSION` (currently `1.0.0`) and evolves
  additively under the §7.3 re-baselining procedure — **no ADR and no governance-contract
  change is required** to advance the dataset version.

This distinction is deliberate: the *contract* for how regression is governed is stable,
while the *data* the contract operates on is free to grow as the pipeline legitimately
evolves.
