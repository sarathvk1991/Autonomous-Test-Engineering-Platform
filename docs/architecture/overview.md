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
Analysis
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
`registry/connector_registry.py`), consolidated by `consolidation/`, AI-analyzed by
`analysis/`, then normalized (`normalization/`), validated (`validation/`), gated by
the CP1 engineering-readiness subsystem (`cp1/`), and written to the Execution
Package (`execution/`). The pipeline is composed by
`requirement_intelligence.platform.PlatformContext` and driven by the CLI
(`scripts/run_requirement_analysis.py`).

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
