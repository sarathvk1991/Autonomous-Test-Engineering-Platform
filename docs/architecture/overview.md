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
- `parsers/<system>/` — convert raw payloads → `CanonicalRequirement`.
- `services/source_registry.py` — maps each source to its connector so sources
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
`Source Registry → Connectors → Parsers → Consolidation → Classification →
Azure OpenAI Analyzer → CP1 Validator → Report Generator`
(see `requirement_intelligence/workflows/requirement_pipeline.py`).

## Cross-cutting
- **Config:** one validated source — `app/core/settings.py` (pydantic-settings).
- **Logging:** structured via `infrastructure/logging`.
- **AI:** one reusable Azure OpenAI client factory in `infrastructure/azure_openai`.
- **Persistence:** PostgreSQL planned; SQLAlchemy/Alembic reserved in deps.
