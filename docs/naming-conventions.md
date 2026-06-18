# Naming Conventions

## Python identifiers
| Element                | Convention            | Example                          |
|------------------------|-----------------------|----------------------------------|
| Package / module       | `lower_snake_case`    | `requirement_intelligence`       |
| Class                  | `PascalCase`          | `CanonicalRequirement`           |
| Function / method      | `lower_snake_case`    | `consolidate`, `health_check`    |
| Variable               | `lower_snake_case`    | `requirement_set`                |
| Constant               | `UPPER_SNAKE_CASE`    | `DEFAULT_TIMEOUT_SECONDS`        |
| Enum class / members   | `PascalCase` / `UPPER`| `SourceSystem.JIRA`              |
| Type alias / Protocol  | `PascalCase`          | `SourceConnector`                |
| Private/internal       | leading underscore    | `_connectors`                    |

## Component-type suffixes (consistency across layers)
- Connectors:  `*Connector`   → `JiraConnector`, `ZapConnector`
- Parsers:     `*Parser`      → `JiraParser`
- Services/engines: `*Engine` / `*Analyzer` / `*Registry` →
  `ConsolidationEngine`, `RequirementAnalyzer`, `SourceRegistry`
- Validators:  `*Validator`   → `CP1Validator`
- Workflows:   `*Pipeline` / `*Workflow` → `RequirementPipeline`
- DTOs / models: noun, no suffix → `CanonicalRequirement`, `SourceRef`
- API schemas: `*Request` / `*Response` → `IngestRequest`

## Files & folders
- Module files are `lower_snake_case.py` named after their primary symbol's
  role (`consolidation_engine.py`, `canonical_requirement.py`).
- One connector/parser per source under `connectors/<source>/` and
  `parsers/<source>/`.
- Test files: `test_<unit_under_test>.py`.

## API & config
- Route paths: `kebab-case`, plural nouns → `/api/v1/requirement-intelligence/requirements`.
- Environment variables: `UPPER_SNAKE_CASE`, prefixed by domain
  (`AZURE_OPENAI_*`, `JIRA_*`, `SONARQUBE_*`, `ZAP_*`).
- Log event keys: `dotted.lower.snake` → `requirement.ingested`.

## Branches & commits (GitHub)
- Branches: `type/short-description` → `feat/jira-connector`, `fix/cp1-edge-case`.
- Commits: Conventional Commits → `feat(requirement-intelligence): add Jira connector`.
