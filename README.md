# Autonomous Test Engineering Platform

> AI-Powered Autonomous Test Engineering Platform — a **modular monolith** that
> ingests requirements from engineering tools, reasons over them with Google
> Gemini, and drives the full test-engineering lifecycle from a single
> deployable unit.

[![python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![framework](https://img.shields.io/badge/api-FastAPI-009688)](https://fastapi.tiangolo.com/)

---

## Status

| Phase | Layer                                   | Status                |
|-------|-----------------------------------------|-----------------------|
| 1     | Requirement Intelligence                | 🟢 Complete           |
| 2     | Feature Engineering                     | ⚪ Planned             |
| 3     | Automation Engineering                  | ⚪ Planned             |
| 4     | Quality Governance                      | ⚪ Planned             |
| 5     | Execution                               | ⚪ Planned             |
| 6     | Failure Intelligence & Self-Healing     | ⚪ Planned             |
| 7     | Governance Dashboard (Streamlit)        | ⚪ Planned             |

> Phase 1 is implemented end to end: connectors (FILE and live API ingestion),
> consolidation, prompt governance, Gemini analysis, normalization, response
> validation, CP1 engineering-readiness, and the execution package.
> See the [demo guide](docs/demo/demo-guide.md) to run it.

## Architecture at a glance

- **Style:** Modular monolith, single deployable unit (one FastAPI app).
- **Language/Framework:** Python 3.11+, FastAPI (Streamlit dashboard later).
- **AI provider:** Google Gemini (`google-genai`). Azure OpenAI is a reserved,
  unimplemented provider stub and is out of scope.
- **Integration:** Connector-based architecture (Jira, SonarQube, OWASP ZAP).
- **Database:** PostgreSQL (future phase; SQLAlchemy/Alembic reserved).

See [`docs/architecture/overview.md`](docs/architecture/overview.md).

## Platform Evolution

The architectural milestones that shaped the current Requirement Intelligence runtime.
This is a capability timeline, not release notes — each entry names the architectural
capability the milestone introduced.

| Milestone | Capability |
|---|---|
| **CAP-070** | Productization Baseline — the golden end-to-end regression baseline |
| **CAP-072** | Prompt Governance — governed, versioned prompt framework |
| **CAP-073** | Prompt Evaluation — evaluation of prompt/response quality |
| **CAP-074** | API Execution Framework — live JIRA/SonarQube/ZAP ingestion (`EXECUTION_MODE`) |
| **CAP-075** | Prompt Governance Runtime Integration — the registry becomes the runtime prompt source |
| **CAP-076** | Engineering Context Orchestration — governed composition of evidence into an `EngineeringContext` |
| **CAP-077** | Evidence Grounding & Traceability — *planned* |

## Runtime Architecture

This is the primary architectural entry point for new developers. It describes the
Requirement Intelligence runtime as a sequence of **stages**, each owning one
responsibility and handing a single **runtime model** to the next. Read this before
the module layout below: the layout tells you where code lives; this tells you what
the code *does* and in what order.

### Runtime Data Flow

The runtime is a linear pipeline. Each arrow is a handoff of one immutable model
from the stage that produces it to the stage that consumes it.

```
Source Systems              (JIRA · SonarQube · OWASP ZAP)
        │  connectors + mappers
        ▼
SourceArtifacts             (raw records mapped to one canonical shape)
        │
        ▼
Consolidation               (group source artifacts that share a subject)
        │
        ▼
ConsolidatedArtifacts       (one per Consolidation group)
        │
        ▼
Engineering Context         (select, rank, budget, and compose groups
Orchestrator                 into one governed reasoning context)
        │
        ▼
EngineeringContext          (the complete, bounded evidence for one session)
        │
        ▼
Prompt Builder              (render the context into a governed prompt)
        │
        ▼
Requirement Analysis        (submit the prompt to Gemini; carry the response)
Service
        │
        ▼
AnalysisResult              (raw, un-validated model output + provenance)
        │  normalization
        ▼
Validation                  (Transport → Syntax → Schema → Content → Reasoning)
        │
        ▼
ValidationResult            (verdict + issues; opens or closes the CP1 gate)
        │
        ▼
CP1                         (engineering-readiness gate; CP1-0001)
        │
        ▼
CP1Result                   (readiness verdict + findings)
        │
        ▼
Execution Package           (all artifacts + manifest written to disk)
```

**Stage responsibilities** (responsibilities, not implementation):

| Stage | Responsibility |
|---|---|
| **Source Systems** | The systems of record. Owned externally; the platform reads, never writes. |
| **Connectors + Mappers** | Ingest raw payloads and map each into one canonical `SourceArtifact`. Isolate all third-party shape. |
| **Consolidation** | Group `SourceArtifacts` that share a subject (module/component) into `ConsolidatedArtifacts`. Answers *"which records belong together?"* — nothing about reasoning. |
| **Engineering Context Orchestrator** | Choose which Consolidation groups a single reasoning session receives, rank them, apply the evidence budget, and compose them into one `EngineeringContext` under a governed `OrchestrationPolicy`. Answers *"what evidence should this session see?"* |
| **Prompt Builder** | Render the `EngineeringContext` into a governed, versioned prompt. **Always consumes `EngineeringContext`** — never a `ConsolidatedArtifact` directly. |
| **Requirement Analysis Service** | Submit the prompt to Google Gemini and carry the response into an `AnalysisResult`. Owns no validation or judgement. |
| **Validation** | Run the response through the ordered rule stages and produce a `ValidationResult` verdict. Owns correctness. |
| **CP1** | Engineering-readiness gate. Opens only on a passing validation verdict; evaluates readiness criteria into a `CP1Result`. Owns readiness. |
| **Execution Package** | Serialize every runtime model and a checksummed `manifest.json` to the output directory. Owns reporting, produces no judgements. |

### Core Runtime Concepts

The runtime models below appear throughout the code and the execution package.
Each is immutable and flows in exactly one direction.

#### SourceArtifact

- **Purpose** — one record from a source system mapped to the platform's single canonical shape.
- **Producer** — the per-system mappers (`mappers/`), fed by connectors (`connectors/`).
- **Consumer** — Consolidation.
- **Lifecycle** — created at ingestion; carried unchanged through Consolidation and into the evidence of an `EngineeringContext`.
- **Typical examples** — a JIRA story, a SonarQube issue, an OWASP ZAP alert.

#### ConsolidatedArtifact

- **Purpose** — the canonical **consolidation** model: all source artifacts that share one subject.
- **Producer** — the Consolidation engine (`consolidation/`).
- **Consumer** — the Engineering Context Orchestrator.
- **Lifecycle** — created by Consolidation; one is chosen as the primary group and serialized as `consolidated_artifact.json`.

A `ConsolidatedArtifact` **represents exactly one Consolidation group.** It:

- **may contain Functional artifacts** (`functionalArtifacts`),
- **may contain Security artifacts** (`securityArtifacts`),
- **may contain Quality artifacts** (`qualityArtifacts`),
- **may contain any combination** of the three,
- and its **empty collections are intentional**.

> **Empty collections indicate that no artifacts of that category belong to this
> Consolidation group. They do NOT imply those artifacts were absent from the overall
> execution.** A run may have security and quality evidence in *other* groups; each
> group only carries what shares *its* subject. See
> [Empty Collection Semantics](#empty-collection-semantics).

#### EngineeringContext

- **Purpose** — the canonical **orchestration** model: the complete, bounded reasoning context for one analysis session, composed from one or more `ConsolidatedArtifacts`.
- **Producer** — the Engineering Context Orchestrator (`context_orchestration/`) under a governed `OrchestrationPolicy`.
- **Consumer** — the Prompt Builder (always), and the Requirement Analysis Service.
- **Lifecycle** — built per run; serialized as `engineering_context.json`.

An `EngineeringContext` represents the **complete reasoning context** — not one group,
but the whole evidence set a session is permitted to reason over. It records:

- **coverage** — per domain, whether evidence existed and whether it was represented.
- **ranking** — every candidate group with the score it achieved and why it was admitted or excluded.
- **evidence budget** — what each domain was allocated and what it spent (and whether it was truncated).
- **provenance** — which `ConsolidatedArtifacts` contributed, and how many artifacts each contributed versus carried.
- **explainability** — the `orchestrationReason` and per-decision reasons, so no orchestration choice is hidden behind its result.
- **policy** — the `OrchestrationPolicyId` and `PolicyVersion` that governed the composition.

> **The Prompt Builder always consumes `EngineeringContext`, never a
> `ConsolidatedArtifact`.** `consolidated_artifact.json` is persisted for audit; it is
> the primary group only, not the evidence the model actually reasoned over.

#### AnalysisResult

- **Purpose** — the provider-independent carrier of one Gemini analysis: the raw response plus its provenance (prompt/version/model/contributing group ids).
- **Producer** — the Requirement Analysis Service (`analysis/`).
- **Consumer** — Normalization and Validation.
- **Lifecycle** — created per run; serialized as `analysis_result.json`. Raw and **un-validated** — it asserts nothing about correctness.

#### ValidationResult

- **Purpose** — the outcome of the Response Validator: an overall verdict plus the issues found across the Transport, Syntax, Schema, Content, and Reasoning stages.
- **Producer** — the Response Validator (`validation/`).
- **Consumer** — the Validation→CP1 handoff (the gate), and the Execution Package.
- **Lifecycle** — created per validated run; serialized as `validation_result.json` (+ `validation_report.md`). Its verdict opens or closes the CP1 gate.

#### CP1Result

- **Purpose** — the engineering-readiness verdict: whether the analysed requirements are ready for downstream engineering (CP1-0001), with any findings.
- **Producer** — the CP1 service/engine (`cp1/`).
- **Consumer** — the Execution Package.
- **Lifecycle** — created only when the validation gate opens; serialized as `cp1_report.md` and surfaced in the manifest (`cp1Verdict`).

#### How they relate

`SourceArtifact`s are grouped into `ConsolidatedArtifact`s; the orchestrator composes
several `ConsolidatedArtifact`s into one `EngineeringContext`; the `EngineeringContext`
produces the prompt whose response becomes an `AnalysisResult`; validating that yields a
`ValidationResult`; a passing verdict opens the gate to a `CP1Result`; and the Execution
Package serializes all of them. **Consolidation groups records; Engineering Context
Orchestration chooses evidence; Analysis reasons; Validation judges correctness; CP1
judges readiness** — four distinct responsibilities, four distinct owners.

### Runtime Model Responsibilities

| Model | Producer | Consumer | Scope | Responsibility | Lifetime | Output Artifact |
|---|---|---|---|---|---|---|
| **SourceArtifact** | Mappers (via connectors) | Consolidation | One source record | Canonical shape for one external record | Whole run (carried, never mutated) | *(embedded in `consolidated_artifact.json` / `engineering_context.json`)* |
| **ConsolidatedArtifact** | Consolidation engine | Engineering Context Orchestrator | **One** Consolidation group | Group records that share a subject | Whole run | `consolidated_artifact.json` (primary group only) |
| **EngineeringContext** | Engineering Context Orchestrator | Prompt Builder (always); Analysis Service | **All** contributing groups for one session | Compose the complete, bounded, governed reasoning context | One reasoning session | `engineering_context.json` |
| **AnalysisResult** | Requirement Analysis Service | Normalization; Validation | One Gemini call | Carry the raw, un-validated response + provenance | One reasoning session | `analysis_result.json` |
| **ValidationResult** | Response Validator | CP1 gate; Execution Package | One analysed response | Judge correctness; open/close the CP1 gate | One reasoning session | `validation_result.json`, `validation_report.md` |
| **CP1Result** | CP1 service/engine | Execution Package | One validated response | Judge engineering readiness | One reasoning session | `cp1_report.md` |
| **ExecutionPackage** | Execution Writer | Auditors / regression / downstream | One run | Serialize every model + checksummed manifest | Persistent on disk | the output directory (`manifest.json` + all artifacts) |

This table is the authority on **ownership**: it distinguishes **Consolidation**
(one group) from **Engineering Context** (all contributing groups for a session) from
**Analysis** (the reasoning) from **Validation** (the judgement of correctness).

### Empty Collection Semantics

A `ConsolidatedArtifact` and the evidence of an `EngineeringContext` both expose three
category collections:

- `functionalArtifacts`
- `securityArtifacts`
- `qualityArtifacts`

**Why empty arrays exist.** Each Consolidation group only carries source artifacts that
share *its* subject. If the subject of a group is, say, a single source file flagged by
SonarQube, then that group legitimately has only `qualityArtifacts`; its
`functionalArtifacts` and `securityArtifacts` are `[]`.

**Why they should remain.** The empty array is a *fact about that group*, not a
placeholder or a defect. Serialising `[]` (rather than omitting the field) keeps the
model shape stable and the artifact self-describing.

**What they mean.** *No source artifact of this category belongs to this Consolidation
group.*

**What they do NOT mean.** They do **not** mean the category was absent from the
overall execution. Other Consolidation groups in the same run may be rich in exactly the
category that is empty here.

**Where completeness lives.** Whole-run coverage is the responsibility of the
`EngineeringContext`, which composes multiple `ConsolidatedArtifacts` into one reasoning
context and records, in its `coverage` and `evidenceCounts`, what evidence the *session*
actually received across all domains. To ask "did this run have security evidence?",
read `engineering_context.json` — not a single `consolidated_artifact.json`.

For the full treatment, see
[Execution Package documentation](docs/architecture/execution-package.md).

## Repository layout

```
autonomous-test-engineering-platform/
├── app/                       # Composition root: FastAPI entry, settings, router
│   ├── api/                   #   aggregate API router (mounts each layer)
│   └── core/                  #   settings / cross-cutting app config
├── requirement_intelligence/  # PHASE 1 — Requirement Intelligence Layer
│   ├── connectors/            #   source connectors (Jira/SonarQube/ZAP)
│   ├── mappers/               #   raw payload -> canonical model
│   ├── models/                #   canonical + shared models (Canonical Requirement, ParsedResponse)
│   ├── registry/              #   connector registry + source loader
│   ├── consolidation/         #   consolidation engine (multi-source -> ConsolidatedArtifact)
│   ├── context_orchestration/ #   Engineering Context Orchestration (runtime orchestrator, policy framework, engineering context model — active runtime component)
│   ├── prompts/               #   prompt framework
│   ├── llm/                   #   provider framework (Gemini; Azure OpenAI stub)
│   ├── platform/              #   PlatformContext, startup validation, health check
│   ├── analysis/              #   AI requirement analysis service
│   ├── normalization/         #   response normalization subsystem
│   ├── validation/            #   response validation subsystem (framework + rules + profiles)
│   ├── cp1/                   #   CP1 engineering-readiness subsystem (models/framework/criteria/response/engine)
│   ├── execution/             #   execution package (writer + per-artifact builders)
│   ├── api/                   #   HTTP routes (future integration surface; not yet wired)
│   └── tests/                 #   layer tests (unit/integration)
├── feature_engineering/       # Phase 2 (placeholder)
├── automation_engineering/    # Phase 3 (placeholder)
├── quality_governance/        # Phase 4 (placeholder)
├── execution/                 # Phase 5 (placeholder)
├── failure_intelligence/      # Phase 6 (placeholder)
├── governance_dashboard/      # Phase 7 — Streamlit (placeholder)
├── shared/                    # Shared kernel
│   ├── contracts/             #   cross-layer schemas & protocols
│   ├── enums/                 #   shared enumerations
│   ├── exceptions/            #   platform exception hierarchy
│   └── utils/                 #   pure helpers
├── infrastructure/            # Reusable external integrations
│   ├── logging/               #   structured logging
│   └── config/                #   infra config helpers
├── prompts/                   # Cross-cutting prompt assets
├── docs/                      # Architecture, ADRs, standards
├── scripts/                   # Dev/ops scripts
└── tests/                     # Cross-cutting tests
```

## Getting started

### Prerequisites
- Python **3.11+**
- A Google AI Studio API key (`GOOGLE_API_KEY`) for AI features
- For live API ingestion only: reachable JIRA, SonarQube, and OWASP ZAP

### Setup
```bash
git clone <repo-url>
cd autonomous-test-engineering-platform

python -m venv .venv && source .venv/bin/activate
make dev                 # install runtime + dev deps, pre-commit hooks

cp .env.example .env     # then fill in real values
```

### Run the API
```bash
make run                 # uvicorn app.main:app --reload
# Swagger UI:  http://localhost:8000/docs
# Health:      http://localhost:8000/health
```

### Quality gates
```bash
make lint        # ruff
make typecheck   # mypy --strict
make test        # pytest
make check       # all of the above
```

## Running the Requirement Intelligence pipeline

The platform is CLI-first. One environment variable selects how sources are
ingested — `EXECUTION_MODE=FILE` (default) or `EXECUTION_MODE=API`.

```bash
# Check every configured source before you run anything
python scripts/run_requirement_analysis.py health

# Full analysis with validation and CP1, from bundled sample data
python scripts/run_requirement_analysis.py analyze --validate

# The same pipeline against live JIRA / SonarQube / OWASP ZAP
EXECUTION_MODE=API python scripts/run_requirement_analysis.py analyze --validate
```

Start with the **[demo guide](docs/demo/demo-guide.md)** — it assumes no prior
knowledge of the repository.

## Configuration

All configuration is environment-driven. See [`.env.example`](.env.example) for
the full list (Gemini, Jira, SonarQube, OWASP ZAP). Startup validation checks
every required variable before the pipeline runs and names any that are missing.
**Never commit `.env`.**

## Documentation
- [Demo guide](docs/demo/demo-guide.md) — first-time walkthrough
- [Operations runbook](docs/operations/runbook.md) — running and troubleshooting
- [Requirement Analysis CLI](docs/user-guide/requirement-analysis-cli.md)
- [Architecture overview](docs/architecture/overview.md)
- [Execution Package](docs/architecture/execution-package.md) — every generated artifact and its lineage
- [Coding standards](docs/coding-standards.md)
- [Naming conventions](docs/naming-conventions.md)
- Architecture Decision Records: `docs/adr/`

## Contributing
Follow the coding standards and naming conventions above. Use Conventional
Commits and `type/short-description` branch names. All quality gates
(`make check`) must pass before a PR is merged.

## License
TBD.
