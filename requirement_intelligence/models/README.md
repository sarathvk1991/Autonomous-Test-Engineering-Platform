# Canonical Data Model

This package defines the **source-agnostic domain models** for the Requirement
Intelligence Layer. They are *domain models only*: pure schema/shape with no
business logic. Transformation, matching, risk scoring and package assembly all
live in parsers and services — the models just give those stages a stable
contract to read and write.

All models extend the shared [`Schema`](../../shared/contracts/base.py) base
(Pydantic v2), so they are **immutable** (`frozen`), **strict**
(`extra="forbid"`), serialise enums by value, and accept either Python
(`snake_case`) or JSON (`camelCase`) field names on input. On output they
serialise to `camelCase` via `model_dump(by_alias=True)`.

## The models

| Model | File | Role |
|-------|------|------|
| `SourceArtifact` | `source_artifact.py` | One normalised record from any source system. |
| `ConsolidatedArtifact` | `consolidated_artifact.py` | A group of related source artifacts for one module. |
| `RequirementPackage` | `requirement_package.py` | The AI-ready, per-module requirement payload. |
| Enums | `enums.py` | `SourceSystem`, `SourceCategory`, `SourceType`, `RiskLevel`. |

> A pre-existing `CanonicalRequirement` (`canonical_requirement.py`) is also
> exported from this package; the three models above form the broader canonical
> pipeline described here.

## How they relate

```
   Source systems                Requirement Intelligence Layer
 (JIRA / ZAP / Sonar / …)
        │
        │  connector + parser  →  normalise each record
        ▼
  ┌─────────────────┐   many
  │ SourceArtifact  │────────────┐   grouped by module / business area
  └─────────────────┘            │
        │ classified by          ▼
        │ SourceCategory   ┌───────────────────────┐
        │ + SourceType     │ ConsolidatedArtifact  │  rolled-up RiskLevel
        │                  │  • functionalArtifacts│
        │                  │  • securityArtifacts  │
        │                  │  • qualityArtifacts   │
        │                  └───────────────────────┘
        │                          │ distil intent per module
        │                          ▼
        │                  ┌───────────────────────┐
        │  ids referenced  │  RequirementPackage   │  ──►  Azure OpenAI
        └─────────────────►│  • requirements       │       (test generation)
           (traceability)  │  • securityReqs       │
                           │  • qualityReqs        │
                           └───────────────────────┘
```

1. **`SourceArtifact`** — every connector/parser maps one upstream record (a
   JIRA story, a ZAP alert, a Sonar issue, and later test cases, results and
   failures) into this single shape. `sourceSystem` + `sourceRecordId` keep the
   original traceable; `sourceCategory` + `sourceType` classify it; `metadata`
   holds anything source-specific that has no canonical home.

2. **`ConsolidatedArtifact`** — consolidation groups the source artifacts that
   describe the same module/area, splitting them by concern
   (`functionalArtifacts`, `securityArtifacts`, `qualityArtifacts`) and
   assigning a normalised `riskLevel`. `relatedArtifactIds` cross-links other
   relevant artifacts without embedding them.

3. **`RequirementPackage`** — the consolidated view is distilled into concise,
   text-centric requirement statements grouped by concern. This is the payload
   sent to **Azure OpenAI** for downstream test generation.
   `supportingArtifacts` references the originating artifact ids so traceability
   survives all the way to the prompt.

## Enums

A `SourceArtifact` is described along **three independent axes**. Keeping them
separate means a single origin can emit many domains and record types without
ambiguity, and each axis is a clean, low-cardinality dimension for analytics.

| Enum | Question it answers | Example values |
|------|--------------------|----------------|
| **`SourceSystem`** | **Where** did the artifact come from? | `JIRA`, `OWASP_ZAP`, `SONARQUBE` |
| **`SourceCategory`** | **Which domain** does it belong to? | `FUNCTIONAL`, `SECURITY`, `QUALITY` |
| **`SourceType`** | **What record type** is it? | `STORY`, `DEFECT`, `DAST`, `SAST` |

- **`SourceSystem`** — the upstream *origin*: `JIRA`, `OWASP_ZAP`, `SONARQUBE`,
  `HP_ALM`, `AZURE_DEVOPS`, `TEST_ENGINE`, `FAILURE_ENGINE`. Modelled as an enum
  (not a free-form string) for type safety and stable dashboard/trend grouping.
- **`SourceCategory`** — the lifecycle *domain*: `FUNCTIONAL`, `SECURITY`,
  `QUALITY`, `TESTING`, `EXECUTION`. Stable and broad, so new source types slot
  under an existing category.
- **`SourceType`** — the concrete *record type*: `EPIC`, `STORY`, `DEFECT`,
  `DAST`, `SAST`, `TEST_CASE`, `TEST_RESULT`, `EXECUTION_FAILURE`.
- **`RiskLevel`** — the single normalised risk scale: `LOW`, `MEDIUM`, `HIGH`,
  `CRITICAL`.

### Worked examples

```
JIRA Story              OWASP ZAP Alert
  sourceSystem   = JIRA     sourceSystem   = OWASP_ZAP
  sourceCategory = FUNCTIONAL   sourceCategory = SECURITY
  sourceType     = STORY    sourceType     = DAST
```

### Timestamps

`createdAt` / `updatedAt` on `SourceArtifact` are `datetime` (not strings).
Pydantic parses ISO-8601 strings into `datetime` on input and serialises them
back to ISO-8601 on output, so the JSON contract is unchanged while downstream
layers get real datetimes for age calculations, SLA tracking, trend analysis,
governance reporting and time-based risk metrics.

## Designed for future phases

The `TESTING` / `EXECUTION` categories and the `TEST_CASE`, `TEST_RESULT` and
`EXECUTION_FAILURE` types already exist so that future ingestion (HP ALM, Azure
DevOps, generated test cases, execution results, failure analysis, self-healing
events and governance metrics) can reuse the **same** `SourceArtifact` shape and
flow through the same consolidation → package pipeline — minimising future
redesign.
