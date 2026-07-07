# Coding Standards

These standards keep the modular monolith consistent, testable, and ready to
scale across all seven layers. They are enforced in CI via `ruff` and `mypy`.

## Language & runtime
- **Python 3.11+**. Use modern syntax: `X | None` unions, `StrEnum`,
  structural pattern matching where it improves clarity.
- `from __future__ import annotations` at the top of every module.

## Formatting & linting
- **Ruff** is the single source of truth for formatting and linting
  (`make format`, `make lint`). Line length **100**.
- No unused imports, no wildcard imports, imports sorted (isort via ruff).

## Typing
- **Full type annotations** on all public functions, methods, and module-level
  values. `mypy --strict` must pass (`make typecheck`).
- Prefer precise types over `Any`. Use `Protocol` for cross-layer contracts.

## Data models
- All DTOs/domain models subclass `shared.contracts.base.Schema` (pydantic v2).
- Models are **immutable** (`frozen=True`) and reject unknown fields.

## Architecture rules (modular monolith)
- **Layer isolation:** a layer never imports another layer's internals. Cross-
  layer communication goes through `shared/contracts`.
- **Dependency direction:** `layers → infrastructure → shared`. `shared` depends
  on nothing internal; `infrastructure` never imports a layer.
- **Connector-based architecture:** external systems are reached only through a
  connector built on `connectors/base.py`; raw SDK/HTTP construction lives in
  `infrastructure/<system>/`.
- **Thin routes:** API handlers validate + delegate; business logic lives in the
  layer's subsystems (e.g. `consolidation/`, `analysis/`, `normalization/`,
  `validation/`, `cp1/`, `execution/`), composed via
  `requirement_intelligence.platform.PlatformContext`.
- **Config in one place:** read configuration only via
  `app.core.settings.get_settings`. Never touch `os.environ` elsewhere.
- **Prompts are assets:** keep prompt templates in `prompts/` (versioned text),
  not inline in Python.

## Errors & logging
- Raise typed errors from `shared.exceptions`; never raise bare `Exception`.
- Log through `infrastructure.logging.get_logger`; use event-style keys
  (`logger.info("requirement.ingested", count=n)`), never f-string messages.
- Never log secrets, tokens, or full third-party payloads.

## Testing
- `pytest` with markers `unit` / `integration` / `e2e`.
- Unit tests do no real I/O; mock connectors and the Azure OpenAI client.
- Each layer keeps tests in its own `tests/` package.

## Docstrings & comments
- Module + public-symbol docstrings explain **why/contract**, not line-by-line.
- Comment intent and non-obvious decisions, not the obvious.
