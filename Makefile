# ===========================================================================
# Developer convenience targets.  Run `make help` for the list.
# ===========================================================================
.DEFAULT_GOAL := help
# Always invoke tools through the project's own virtualenv interpreter, never
# a bare command name resolved off $PATH — an unrelated Python installation's
# pytest can shadow this project's on some machines. See
# docs/development/environment.md for the details and the trap this avoids.
PY := .venv/bin/python

.PHONY: help install dev run dashboard lint format typecheck test cov check clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime dependencies
	$(PY) -m pip install -r requirements.txt

dev: ## Install runtime + dev dependencies and pre-commit hooks
	$(PY) -m pip install -r requirements.txt -r requirements-dev.txt
	$(PY) -m pre_commit install

run: ## Run the FastAPI app (reload)
	$(PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dashboard: ## Run the Streamlit governance dashboard (future phase)
	$(PY) -m streamlit run governance_dashboard/app.py

lint: ## Lint with ruff
	$(PY) -m ruff check .

format: ## Auto-format with ruff
	$(PY) -m ruff format .
	$(PY) -m ruff check . --fix

typecheck: ## Static type-check with mypy
	$(PY) -m mypy .

test: ## Run the test suite
	$(PY) -m pytest

cov: ## Run tests with coverage
	$(PY) -m pytest --cov=requirement_intelligence --cov=shared --cov=infrastructure

check: lint typecheck test ## Run all quality gates

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
