# Architecture Overview

## Style
**Modular monolith** deployed as a **single deployable unit** (one FastAPI ASGI
app). Each logical layer is an independent Python package with clear boundaries,
so the system *could* be split into services later without rework — but ships and
runs as one process today.

## Dependency direction
```
            ┌─────────────────────────────────────────────┐
            │                    app/                      │  (composition root)
            │      settings · logging · router mounting    │
            └───────────────────────┬─────────────────────┘
                                    │ mounts each layer's router
        ┌───────────────────────────┴───────────────────────────┐
        │                     platform layers                    │
        │  requirement_intelligence · feature_engineering · …    │
        └───────────────┬───────────────────────┬───────────────┘
                        │ uses                   │ talks to externals via
                        ▼                        ▼
                 shared/  (contracts,     infrastructure/ (azure_openai,
                  enums, exceptions,        jira, sonarqube, zap,
                     utils)                  logging, config)
                        ▲                        │
                        └────────────────────────┘
                     infrastructure depends on shared;
                     shared depends on nothing internal
```

**Rules:** layers never import each other's internals (only `shared/contracts`);
`infrastructure` never imports a layer; `shared` has no internal dependencies.

## Connector-based architecture
External systems are integrated through **connectors**:
- `infrastructure/<system>/` — low-level client construction (auth, transport).
- `requirement_intelligence/connectors/<system>/` — domain connector built on
  `connectors/base.py`, returning raw payloads.
- `mappers/<system>_mapper.py` — convert raw payloads → `CanonicalRequirement`.
- `registry/connector_registry.py` (with `registry/registry_loader.py` reading
  `config/source-registry.json`) — maps each source to its connector so sources
  are pluggable via configuration.

This isolates third-party change to one place and makes new sources additive.

## The seven layers
1. **Requirement Intelligence** *(Phase 1 — implemented structure)* — ingest,
   consolidate, classify, AI-analyze requirements; CP1 quality gate.
2. **Feature Engineering** — requirements → testable features/scenarios.
3. **Automation Engineering** — features → automated test assets.
4. **Quality Governance** — gates & policy enforcement.
5. **Execution** — run suites, collect results/evidence.
6. **Failure Intelligence & Self-Healing** — AI triage, root-cause, auto-heal.
7. **Governance Dashboard** — Streamlit metrics & governance views.

## Requirement Intelligence pipeline (Phase 1)

```
Input Sources
        │
        ▼
Consolidation
        │
        ▼
Engineering Context Orchestration
        │
        ▼
Analysis
        │
        ▼
Grounding
        │
        ▼
Normalization
        │
        ▼
Validation
        │
        ▼
CP1
        │
        ▼
Execution Package
```

Sources are ingested via `connectors/` + `mappers/` (selected by
`registry/connector_registry.py`), consolidated by `consolidation/`, composed into a
governed reasoning context by `context_orchestration/`, AI-analyzed by `analysis/`, graded
against its evidence by the Grounding Framework (`grounding/`, active since CAP-077F.2 —
strictly downstream, modifies nothing upstream), then normalized (`normalization/`),
validated (`validation/`), gated by the CP1 engineering-readiness subsystem (`cp1/`), and
written to the Execution Package (`execution/`). The pipeline is composed by
`requirement_intelligence.platform.PlatformContext` and driven by the CLI
(`scripts/run_requirement_analysis.py`).

For the runtime models each stage produces and consumes, see the
[Runtime Architecture](../../README.md#runtime-architecture) section of the README (the
primary architectural entry point) and the
[Execution Package documentation](execution-package.md).

## Runtime Ownership

Each pipeline stage owns exactly one responsibility and hands a single model to the next.
The README documents the models in full; this table is the architectural ownership map.

| Stage | Primary Responsibility | Produces | Consumes |
|---|---|---|---|
| Connectors | Fetch raw payloads from source systems | Raw source payloads | Source system APIs / files |
| Mappers | Map raw payloads to one canonical shape | `SourceArtifact` | Raw source payloads |
| Consolidation | Group source artifacts that share a subject | `ConsolidatedArtifact` (per group) | `SourceArtifact`s |
| Engineering Context Orchestration | Select, rank, budget and compose groups under a governed policy | `EngineeringContext` | `ConsolidatedArtifact`s |
| Prompt Builder | Render the context into a governed prompt | `PromptRequest` | `EngineeringContext` |
| Requirement Analysis | Submit the prompt to Gemini; carry the response | `AnalysisResult` | `PromptRequest` |
| Normalization | Normalize the raw response for validation | `NormalizationResult` / `ParsedResponse` | `AnalysisResult` |
| Validation | Judge correctness; open/close the CP1 gate | `ValidationResult` | `AnalysisResult` + `NormalizationResult` |
| CP1 | Judge engineering readiness | `CP1Result` | `ValidationResult` (via the gate) |
| Execution Package | Serialize every model + checksummed manifest | Execution package (artifacts + `manifest.json`) | all of the above |

## Engineering Context Orchestration (`context_orchestration/`)

**Live in the pipeline above (since CAP-076C; multi-source since CAP-076D).**

Consolidation answers *"which records share an attribute?"*. It does not answer
*"what evidence should one reasoning session receive?"*. **Engineering Context
Orchestration** owns that question, sitting between Consolidation and Analysis:

```
list[ConsolidatedArtifact]  ->  Engineering Context Orchestrator  ->  EngineeringContext
```

`EngineeringContext` is the canonical **orchestration** model: the complete,
bounded evidence for one reasoning session, composed from several consolidation
groups under a governed, declarative `OrchestrationPolicy` (coverage, ranking,
evidence budget, ordering, tie-breaking, explainability). It **does not replace**
`ConsolidatedArtifact`, which remains the canonical **consolidation** model and is
unchanged. The two are stacked, not substituted.

The package contains the canonical model, the typed identity model
(`EngineeringContextId`, `OrchestrationPolicyId`, `PolicyVersion` — the platform's
first strongly typed identifiers), the policy framework, and the builder. `PlatformContext`
constructs the orchestrator and binds it to a governed `OrchestrationPolicy`; the CLI
invokes it between Consolidation and Analysis, and the **Prompt Builder consumes the
resulting `EngineeringContext`** (never a `ConsolidatedArtifact` directly). The
`EngineeringContext` is serialized per run as `engineering_context.json` in the Execution
Package. Under the active `DefaultOrchestrationPolicy` the context is composed from
multiple contributing consolidation groups; the pipeline diagram above reflects this.

Governed by **ADR-0015**. Background: `docs/reviews/cap-076-engineering-context-orchestration.md`.
Runtime models and artifacts: [Execution Package documentation](execution-package.md).

> On the word *orchestration*: ADR-0002/0003/0011 use "orchestration boundary" for
> components that sequence collaborators and own **no** policy. Engineering Context
> Orchestration is the opposite — owning policy is its purpose. Always use the full
> term.

## Cross-cutting
- **Config:** one validated source — `app/core/settings.py` (pydantic-settings).
- **Logging:** structured via `infrastructure/logging`.
- **AI:** one reusable Azure OpenAI client factory in `infrastructure/azure_openai`.
- **Persistence:** PostgreSQL planned; SQLAlchemy/Alembic reserved in deps.

## Governance
Two living governance artifacts track platform maturity and frozen contracts.
They *describe* the platform (status and versions); they never define it.
- **[Platform Capability Matrix](../governance/platform-capability-matrix.md)** —
  the executive view of every capability's maturity, version, and next milestone.
- **[Architecture Freeze Index](../governance/architecture-freeze-index.md)** —
  the authoritative list of every frozen architectural contract and its governing
  document.
