# Execution Package

The **Execution Package** is the on-disk record of one Requirement Intelligence run.
It is written by `ExecutionWriter` (`requirement_intelligence/execution/`) into a single
output directory: one serialized file per runtime model, human-readable reports, and a
checksummed `manifest.json` that ties them together.

This document explains **every generated artifact** — its purpose, who produces it, who
consumes it, its lifetime, and how it relates to the others. It is documentation only:
it describes the package as it is written today and changes no artifact name, no artifact
content, and no runtime behaviour.

For the runtime models the package serializes, see the
[Runtime Architecture](../../README.md#runtime-architecture) section of the README, which
is the primary architectural entry point.

## At a glance

`manifest.json` is the **root index** of the package: it lists every other artifact by
name, byte count, and SHA-256, and carries the run's identity and subsystem versions. To
read a package, start at the manifest and follow it out to the artifacts it indexes.

```
Execution Package
        │
        ▼
   manifest.json          ← root index: checksums, versions, cross-references
        │
        ├── consolidated_artifact.json              (the primary Consolidation group)
        ├── engineering_context.json                (the complete reasoning context)
        ├── prompt.txt                               (the exact prompt submitted)
        ├── llm_request.json                         (the provider-agnostic request)
        ├── analysis_result.json                     (the raw, un-validated response)
        ├── raw_llm_response.json                    (the raw provider response)
        ├── requirement_enhancement_result.json      (enhancement runtime contract) [conditional]
        ├── requirement_enhancement_report.md        (enhancement projection)       [conditional]
        ├── requirement_enhancement_metrics.md       (enhancement metrics projection)[conditional]
        ├── grounding_result.json                    (grounding runtime contract)   [conditional]
        ├── grounding_report.md                      (grounding projection)         [conditional]
        ├── grounding_metrics.md                      (grounding metrics projection) [conditional]
        ├── validation_result.json                   (the validation verdict)       [conditional]
        ├── validation_report.md                     (human-readable validation)    [conditional]
        ├── cp1_report.md                             (engineering-readiness)        [conditional]
        ├── quality_governance_result.json           (governance runtime contract)  [conditional]
        ├── quality_governance_report.md              (governance projection)        [conditional]
        ├── quality_governance_summary.md             (governance headline)          [conditional]
        ├── execution_summary.md                     (human-readable run summary)
        ├── baseline_metrics.md                      (engineering + AI metrics)
        └── review.md                                (qualitative review scaffold)
```

Every artifact the manifest lists appears in `generatedArtifacts` with its byte count and
SHA-256, so the package is self-verifying: the golden baseline re-hashes each file and
checks it against the manifest.

**Grounding, Requirement Enhancement, and Quality Governance artifacts are pure
projections.** `grounding_result.json`/`grounding_report.md`/`grounding_metrics.md`
(CAP-077F.1), `requirement_enhancement_result.json`/`requirement_enhancement_report.md`/
`requirement_enhancement_metrics.md` (CAP-081C), and
`quality_governance_result.json`/`quality_governance_report.md`/`quality_governance_summary.md`
(CAP-080D) are each written only when the corresponding runtime result was produced, via
the same conditional-append mechanism as validation/CP1. Each is a **serialization
projection** of its own frozen runtime contract (`GroundingResult` — ADR-0016 §D16;
`RequirementEnhancementResult` — ADR-0018 §D8; `QualityGovernanceResult` — ADR-0017 §D3) —
reproducible from it alone. The Execution Package computes nothing for any of them: no
matching, classification, enrichment, relationship detection, observation generation,
rule evaluation, or decision — the respective serializer renders only what its runtime
already computed. All three are wired into the live CLI run today, at their frozen
pipeline positions: Requirement Enhancement immediately after Analysis (upstream of
Grounding), Grounding after that, and Quality Governance at the terminal end of the
pipeline (after CP1).

---

## 1. What the package contains

Artifacts fall into three groups by when they are written:

- **Core** — always written (including dry runs): the inputs to reasoning.
- **Result** — written on any non-dry run: the reasoning output and its reports.
- **Conditional** — written only when the corresponding stage ran: Requirement
  Enhancement, Grounding, Validation, CP1, and Quality Governance.

| Artifact | Group | Written when | Producer (builder) | Serializes |
|---|---|---|---|---|
| `manifest.json` | — | always | `ManifestBuilder` | the manifest (checksums, versions, cross-references) |
| `consolidated_artifact.json` | Core | always | `ExecutionWriter` (from the primary group) | the **primary** `ConsolidatedArtifact` |
| `engineering_context.json` | Core | always | `EngineeringContextArtifactBuilder` | the `EngineeringContext` |
| `prompt.txt` | Core | always | `ExecutionWriter` | the full prompt (system + user) |
| `llm_request.json` | Core | always | `ExecutionWriter` | the provider-agnostic `LLMRequest` |
| `analysis_result.json` | Result | non-dry run | `ExecutionWriter` | the `AnalysisResult` |
| `raw_llm_response.json` | Result | non-dry run | `ExecutionWriter` | the raw `LLMResponse` |
| `execution_summary.md` | Result | non-dry run | `ExecutionSummaryBuilder` | human-readable run summary |
| `baseline_metrics.md` | Result | non-dry run | `BaselineMetricsBuilder` | engineering + AI metrics |
| `review.md` | Result | non-dry run | `ReviewBuilder` | qualitative review scaffold |
| `requirement_enhancement_result.json` | Conditional | enhancement ran | `EnhancementSerializer` | the `RequirementEnhancementResult` (verbatim) |
| `requirement_enhancement_report.md` | Conditional | enhancement ran | `EnhancementSerializer` | human-readable enhancement projection |
| `requirement_enhancement_metrics.md` | Conditional | enhancement ran | `EnhancementSerializer` | enhancement metrics projection |
| `grounding_result.json` | Conditional | grounding ran | `GroundingSerializer` | the `GroundingResult` (verbatim) |
| `grounding_report.md` | Conditional | grounding ran | `GroundingSerializer` | human-readable grounding projection |
| `grounding_metrics.md` | Conditional | grounding ran | `GroundingSerializer` | grounding metrics projection |
| `validation_result.json` | Conditional | validation ran | `ExecutionWriter` | the `ValidationResult` |
| `validation_report.md` | Conditional | validation ran | `ValidationReportBuilder` | human-readable validation report |
| `cp1_report.md` | Conditional | CP1 ran | `CP1ReportBuilder` | the `CP1Result` |
| `quality_governance_result.json` | Conditional | governance ran | `QualityGovernanceSerializer` | the `QualityGovernanceResult` (verbatim) |
| `quality_governance_report.md` | Conditional | governance ran | `QualityGovernanceSerializer` | human-readable governance projection |
| `quality_governance_summary.md` | Conditional | governance ran | `QualityGovernanceSerializer` | governance headline projection |

---

## 2. Artifact reference

### `consolidated_artifact.json`

- **Purpose** — persist, verbatim, the **primary Consolidation group** the orchestrator
  chose for this run.
- **Producer** — `ExecutionWriter`, serialising `orchestration.primary_group`
  (a single `ConsolidatedArtifact`).
- **Consumer** — auditors and regression tooling. It is *not* the model the reasoner saw.
- **Lifetime** — one run.
- **Relationship** — it is **one** of possibly many Consolidation groups. Its three
  category collections (`functionalArtifacts`, `securityArtifacts`, `qualityArtifacts`)
  describe only *this* group; see [§4 Empty Collection Semantics](#4-empty-collection-semantics).
  The complete evidence set for the run lives in `engineering_context.json`.

> **Why this file may contain only one evidence category.** A Consolidation group carries
> only the source artifacts that share its subject. If the primary group's subject is a
> single file flagged by SonarQube, the file will legitimately contain only
> `qualityArtifacts`, with `functionalArtifacts: []` and `securityArtifacts: []`. That is
> a true statement about the group — **not** a claim that the run had no functional or
> security evidence. Other groups in the same run may carry exactly those categories, and
> `engineering_context.json` records what the reasoning session received across *all*
> domains.

### `engineering_context.json`

- **Purpose** — record the **complete reasoning context**: which Consolidation groups were
  candidates, which were selected, how they were ranked and budgeted, and what evidence the
  session ultimately received. It is the audit answer to *"what evidence did this reasoning
  session receive, under which rules, and what did those rules turn away?"*
- **Producer** — `EngineeringContextArtifactBuilder`, projecting the `EngineeringContext`
  the Engineering Context Orchestrator built under the governed `OrchestrationPolicy`.
- **Consumer** — auditors, regression tooling, and grounding assessment.
- **Lifetime** — one reasoning session.
- **Relationship** — it is composed from one or more `ConsolidatedArtifacts`. It records
  every orchestration decision: `ranking` (one entry per candidate group, with score and
  admit/exclude reason), `coverage` (per domain: was evidence present, was it represented),
  `evidenceBudget` (per domain: available/allocated/used/truncated), `provenance`
  (contributing group ids and contributed-vs-carried counts), and `evidenceCounts`. This
  is the file that makes whole-run coverage legible; `consolidated_artifact.json` is only
  the primary group.

> **The Prompt Builder always consumes `EngineeringContext`, never a
> `ConsolidatedArtifact`.** `engineering_context.json` therefore describes the evidence the
> model actually reasoned over; `consolidated_artifact.json` is a subset kept for audit.

### `prompt.txt`

- **Purpose** — the exact prompt string submitted to the provider (system + `\n\n` + user).
- **Producer** — `ExecutionWriter` (the `RequirementPromptBuilder` output, rendered from
  the `EngineeringContext`).
- **Consumer** — auditors; its SHA-256 is recorded in the manifest as `promptSha256`.
- **Lifetime** — one run.
- **Relationship** — derived from `engineering_context.json`; feeds `llm_request.json`.

### `llm_request.json`

- **Purpose** — the provider-agnostic `LLMRequest` (prompt + parameters) as handed to the
  LLM framework.
- **Producer** — `ExecutionWriter`.
- **Consumer** — auditors; the boundary record between the platform and the provider.
- **Lifetime** — one run.
- **Relationship** — carries the content of `prompt.txt`; its response is
  `raw_llm_response.json`.

### `analysis_result.json`

- **Purpose** — the serialized `AnalysisResult`: the raw, **un-validated** model output plus
  provenance (analysis/execution ids, provider, model, prompt/contract versions, contributing
  group ids).
- **Producer** — `ExecutionWriter`, from the `RequirementAnalysisService` output.
- **Consumer** — Normalization, Validation, and the manifest (`analysisId`, `executionId`
  are cross-referenced).
- **Lifetime** — one reasoning session.
- **Relationship** — the parent of `validation_result.json` and `cp1_report.md`; asserts
  nothing about correctness on its own.

### `raw_llm_response.json`

- **Purpose** — the raw `LLMResponse` exactly as returned by the provider.
- **Producer** — `ExecutionWriter`.
- **Consumer** — auditors; its SHA-256 is the manifest's `responseSha256`.
- **Lifetime** — one run.
- **Relationship** — the un-normalized source behind `analysis_result.json`.

### `requirement_enhancement_result.json`, `requirement_enhancement_report.md`, `requirement_enhancement_metrics.md`

- **Purpose** — persist the deterministic enhancement of the run's generated
  requirements: `requirement_enhancement_result.json` is the
  `RequirementEnhancementResult` verbatim (the frozen runtime contract, ADR-0018
  §D8); `requirement_enhancement_report.md` and `requirement_enhancement_metrics.md`
  are human-readable projections of it (enriched requirements, the relationship
  graph, observations, and findings).
- **Producer** — `EnhancementSerializer` (in `enhancement/serialization/`), invoked
  by `ExecutionWriter`. **Written only when a `RequirementEnhancementResult` was
  produced** — i.e. a live (non-dry-run) analysis reached the enhancement phase.
- **Consumer** — auditors, humans, the manifest (`generatedArtifacts`,
  `requirementEnhancementExecuted`/`Report`/`Metrics`).
- **Lifetime** — one enhanced run.
- **Relationship** — **pure projections** of the `RequirementEnhancementResult`
  (ADR-0018 §D8/§D9), reproducible from it alone. The Execution Package computes
  nothing here — it never enriches, detects a relationship, creates an observation,
  or computes a metric/summary/finding; the runtime already did. Requirement
  Enhancement runs immediately after Analysis and strictly upstream of Grounding
  (`Engineering Context → Analysis → Requirement Enhancement → Grounding → ...`), so
  it consumes only `EngineeringContext` + `AnalysisResult` and modifies neither.

### `validation_result.json`

- **Purpose** — the serialized `ValidationResult`: overall verdict plus every issue found
  across the Transport, Syntax, Schema, Content, and Reasoning stages.
- **Producer** — `ExecutionWriter`, from the `ResponseValidator` output. **Written only
  when validation ran.**
- **Consumer** — the Validation→CP1 gate and auditors.
- **Lifetime** — one validated run.
- **Relationship** — its verdict opens or closes the gate to `cp1_report.md`;
  `validation_report.md` is its human-readable twin.

### `validation_report.md`

- **Purpose** — the human-readable validation report.
- **Producer** — `ValidationReportBuilder`. **Written only when validation ran.**
- **Consumer** — humans reviewing a run.
- **Lifetime** — one validated run.
- **Relationship** — presentation of `validation_result.json`.

### `cp1_report.md`

- **Purpose** — the CP1 engineering-readiness report: overall verdict and findings
  (CP1-0001).
- **Producer** — `CP1ReportBuilder`, from the `CP1Result`. **Written only when CP1 ran**
  (i.e. the validation gate opened).
- **Consumer** — humans and the manifest (`cp1Verdict`, `cp1Report`).
- **Lifetime** — one validated run whose gate opened.
- **Relationship** — also summarized in `execution_summary.md` under *Engineering
  Readiness*. No longer the terminal judgement of the pipeline — Quality Governance
  runs after it (CAP-080D).

### `quality_governance_result.json`, `quality_governance_report.md`, `quality_governance_summary.md`

- **Purpose** — persist the release decision for the run: `quality_governance_result.json`
  is the `QualityGovernanceResult` verbatim (the frozen runtime contract, ADR-0017 §D3);
  `quality_governance_report.md` and `quality_governance_summary.md` are human-readable
  projections of it.
- **Producer** — `QualityGovernanceSerializer` (in `quality_governance/serialization/`),
  invoked by `ExecutionWriter`. **Written only when a `QualityGovernanceResult` was
  produced** — i.e. `GroundingResult` + `ValidationResult` + `CP1Result` all completed
  (CAP-080D).
- **Consumer** — humans, release tooling, the manifest (`generatedArtifacts`,
  `qualityGovernanceExecuted`/`Report`/`Summary`).
- **Lifetime** — one governed run.
- **Relationship** — **pure projections** of the `QualityGovernanceResult` (ADR-0017
  §D30), reproducible from it alone. The Execution Package computes nothing here — it
  never evaluates a rule, assesses, or decides; the runtime already did. Quality
  Governance is the **terminal release authority**, running at the permanently frozen
  end of the pipeline, after CP1. The manifest references these artifacts by name
  only — it never duplicates the `QualityDecision` itself (ADR-0017 §D31).

### `grounding_result.json`, `grounding_report.md`, `grounding_metrics.md`

- **Purpose** — persist the grounding assessment for the run: `grounding_result.json` is the
  `GroundingResult` verbatim (the frozen runtime contract); `grounding_report.md` and
  `grounding_metrics.md` are human-readable projections of it.
- **Producer** — `GroundingSerializer` (in `grounding/serialization/`), invoked by
  `ExecutionWriter`. **Written only when a `GroundingResult` was produced** — i.e.
  a live (non-dry-run) analysis reached the grounding phase (CAP-077F.2).
- **Consumer** — auditors, humans, downstream phases, the manifest (`generatedArtifacts`).
- **Lifetime** — one grounded run.
- **Relationship** — **pure projections** of the `GroundingResult` (ADR-0016 §D16),
  reproducible from it alone. The Execution Package computes nothing here — it never matches,
  classifies, scores confidence, or computes metrics/summaries/findings; the runtime already
  did (`Runtime → GroundingResult → Execution Package → files` is one-way).

### `execution_summary.md`, `baseline_metrics.md`, `review.md`

- **Purpose** — human-readable summary, metrics, and a qualitative review scaffold.
- **Producer** — `ExecutionSummaryBuilder`, `BaselineMetricsBuilder`, `ReviewBuilder`.
  Written on any non-dry run.
- **Consumer** — humans.
- **Lifetime** — one run.
- **Relationship** — presentation layers over the models above; `execution_summary.md`
  appends an *Engineering Readiness* section when CP1 ran.

### `manifest.json`

- **Purpose** — the integrity and provenance index of the package: subsystem versions,
  execution identity, prompt/response checksums, and one `{name, bytes, sha256}` entry per
  generated artifact.
- **Producer** — `ManifestBuilder`.
- **Consumer** — regression tooling and auditors; the golden baseline verifies its
  checksums, byte counts, cross-references, and version fields against the on-disk files.
- **Lifetime** — one run.
- **Relationship** — references every other artifact by name, size, and hash, and
  cross-references `analysis_result.json` (`analysisId`, `executionId`).

---

## 3. Execution Lineage

Every artifact in the package traces back through the runtime pipeline. The lineage below
shows how evidence flows from the source systems to the written package. It is the same
flow as the [Runtime Data Flow](../../README.md#runtime-data-flow), annotated with the
counts an auditor reads to understand one run.

```
SourceArtifacts             ← connectors + mappers
        │
        ▼
ConsolidatedArtifacts       ← Consolidation (candidate groups)
        │
        ▼
EngineeringContext          ← Engineering Context Orchestrator (contributing groups)
        │
        ▼
Prompt                      ← Prompt Builder (renders the EngineeringContext)
        │
        ▼
Gemini                      ← Requirement Analysis Service
        │
        ▼
AnalysisResult              ← raw, un-validated response + provenance
        │
        ▼
Requirement Enhancement     → RequirementEnhancementResult (enrichment, relationships,
        │                     observations, findings — CAP-081C)
        ▼
Grounding                    → GroundingResult (evidence-support verdict — CAP-077F.2)
        │
        ▼
Validation                  → ValidationResult (verdict)
        │
        ▼
CP1                         → CP1Result (readiness verdict)
        │
        ▼
Quality Governance          → QualityGovernanceResult (release decision — CAP-080D)
        │
        ▼
Execution Package           ← ExecutionWriter serializes every model + manifest
```

**Lineage facts an auditor should be able to read for any run** (all are already present in
the package — this section only names where):

| Fact | Where it is recorded |
|---|---|
| SourceArtifact count | `engineering_context.json → provenance.sourceArtifactCount` |
| ConsolidatedArtifact count (candidates) | `engineering_context.json → candidateGroupCount` |
| Candidate Groups | `engineering_context.json → ranking.entries` (all candidates) |
| Contributing Groups | `engineering_context.json → contributingGroupCount` / `contributingConsolidatedIds` |
| EngineeringContext evidence counts | `engineering_context.json → evidenceCounts` (functional/security/quality/total) |
| Prompt version | `manifest.json → promptVersion`; `execution_summary.md` |
| Policy version | `engineering_context.json → orchestration.policyVersion` |
| Requirement Enhancement ran | `manifest.json → requirementEnhancementExecuted` / `requirementEnhancementReport` / `requirementEnhancementMetrics` |
| Enhancement content (enriched requirements, relationships, observations, findings) | `requirement_enhancement_result.json` only — never the manifest (ADR-0018 §D8) |
| Grounding score / verdict | `grounding_report.md`; never the manifest — read `grounding_result.json` |
| Validation profile | `manifest.json → commandLineArguments.validation_profile` |
| CP1 version | `cp1_report.md`; `manifest.json → cp1Verdict` / `cp1Report` |
| Quality Governance decision | `manifest.json → qualityGovernanceExecuted` / `Report` / `Summary` (never the decision itself — read `quality_governance_result.json`, ADR-0017 §D31) |

> **Note on `execution_summary.md`.** The execution summary is generated by
> `ExecutionSummaryBuilder`, whose output is part of the byte-identical execution-artifact
> contract (the golden baseline verifies its checksum). This lineage is therefore
> documented here as reference rather than injected into the generated summary: the runtime
> artifact is unchanged, and this section is the canonical, human-readable lineage for a
> run. See [Runtime Verification](#5-runtime-verification-cap-076e).

---

## 4. Empty Collection Semantics

Both `ConsolidatedArtifact` and the evidence block of `EngineeringContext` expose three
category collections:

- `functionalArtifacts`
- `securityArtifacts`
- `qualityArtifacts`

**Why empty arrays exist.** A Consolidation group carries only the source artifacts that
share *its* subject. A group about a single SonarQube-flagged file has only
`qualityArtifacts`; its other two collections are `[]`.

**Why they should remain.** Serialising `[]` rather than omitting the field keeps the model
shape stable and the artifact self-describing. Regression tooling and downstream readers can
rely on all three keys always being present.

**What they mean.** *No source artifact of this category belongs to this Consolidation
group.*

**What they do NOT mean.** They do **not** mean the category was absent from the overall
execution. Another group in the same run may be rich in exactly the empty category.

**Where whole-run completeness lives.** `EngineeringContext` is responsible for assembling
multiple `ConsolidatedArtifacts` into a single reasoning context. Its `coverage` and
`evidenceCounts` — recorded in `engineering_context.json` — are the authority on what the
*session* received across all domains. To answer "did this run have security evidence?",
read `engineering_context.json`, never a single `consolidated_artifact.json`.

This is the crux of the package: **`consolidated_artifact.json` is one group;
`engineering_context.json` is the whole reasoning context.** An empty collection in the
former is a fact about that group, resolved by the latter.

---

## 5. Runtime Verification (CAP-076E)

This document is documentation-only. It introduced no artifact, changed no artifact name,
changed no artifact content, and changed no runtime behaviour. Artifact serialization,
manifest generation, and the execution builders are unchanged; the package a run produces
is byte-identical to before this document existed.
