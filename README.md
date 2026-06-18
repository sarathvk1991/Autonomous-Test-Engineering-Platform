# Autonomous Test Engineering Platform

> AI-Powered Autonomous Test Engineering Platform — a **modular monolith** that
> ingests requirements from engineering tools, reasons over them with Azure
> OpenAI, and drives the full test-engineering lifecycle from a single
> deployable unit.

[![python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![framework](https://img.shields.io/badge/api-FastAPI-009688)](https://fastapi.tiangolo.com/)

---

## Status

| Phase | Layer                                   | Status                |
|-------|-----------------------------------------|-----------------------|
| 1     | Requirement Intelligence                | 🟢 Structure scaffolded |
| 2     | Feature Engineering                     | ⚪ Planned             |
| 3     | Automation Engineering                  | ⚪ Planned             |
| 4     | Quality Governance                      | ⚪ Planned             |
| 5     | Execution                               | ⚪ Planned             |
| 6     | Failure Intelligence & Self-Healing     | ⚪ Planned             |
| 7     | Governance Dashboard (Streamlit)        | ⚪ Planned             |

> Phase 1 establishes the repository structure and contracts. Business logic is
> implemented incrementally — current service/connector classes are typed stubs.

## Architecture at a glance

- **Style:** Modular monolith, single deployable unit (one FastAPI app).
- **Language/Framework:** Python 3.11+, FastAPI (Streamlit dashboard later).
- **AI provider:** Azure OpenAI (one reusable client factory).
- **Integration:** Connector-based architecture (Jira, SonarQube, OWASP ZAP).
- **Database:** PostgreSQL (future phase; SQLAlchemy/Alembic reserved).

See [`docs/architecture/overview.md`](docs/architecture/overview.md).

## Repository layout

```
autonomous-test-engineering-platform/
├── app/                       # Composition root: FastAPI entry, settings, router
│   ├── api/                   #   aggregate API router (mounts each layer)
│   └── core/                  #   settings / cross-cutting app config
├── requirement_intelligence/  # PHASE 1 — Requirement Intelligence Layer
│   ├── api/                   #   routes + transport schemas
│   ├── connectors/            #   connector framework + Jira/SonarQube/ZAP
│   ├── parsers/               #   raw payload -> canonical model
│   ├── models/                #   Canonical Requirement Model
│   ├── services/              #   registry, consolidation, classification, analyzer, reports
│   ├── validators/            #   CP1 validation engine
│   ├── workflows/             #   pipeline orchestration
│   ├── prompts/               #   layer-specific prompt templates
│   ├── reports/               #   report templates
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
│   ├── azure_openai/          #   Azure OpenAI client factory
│   ├── jira/ sonarqube/ zap/  #   low-level source clients
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
- An Azure OpenAI resource (endpoint, key, deployment) for AI features

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

## Configuration

All configuration is environment-driven and validated by
`app/core/settings.py`. See [`.env.example`](.env.example) for the full list
(Azure OpenAI, Jira, SonarQube, OWASP ZAP, database). **Never commit `.env`.**

## Documentation
- [Architecture overview](docs/architecture/overview.md)
- [Coding standards](docs/coding-standards.md)
- [Naming conventions](docs/naming-conventions.md)
- Architecture Decision Records: `docs/adr/`

## Contributing
Follow the coding standards and naming conventions above. Use Conventional
Commits and `type/short-description` branch names. All quality gates
(`make check`) must pass before a PR is merged.

## License
TBD.
