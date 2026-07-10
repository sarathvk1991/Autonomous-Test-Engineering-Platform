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
│   ├── context_orchestration/ #   engineering context orchestration (model+policy; not yet wired)
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
- [Coding standards](docs/coding-standards.md)
- [Naming conventions](docs/naming-conventions.md)
- Architecture Decision Records: `docs/adr/`

## Contributing
Follow the coding standards and naming conventions above. Use Conventional
Commits and `type/short-description` branch names. All quality gates
(`make check`) must pass before a PR is merged.

## License
TBD.
