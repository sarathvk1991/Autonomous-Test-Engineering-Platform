# ===========================================================================
# Developer convenience targets.  Run `make help` for the list.
# ===========================================================================
.DEFAULT_GOAL := help
PY := python

.PHONY: help install dev run dashboard lint format typecheck test cov check clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install runtime dependencies
	$(PY) -m pip install -r requirements.txt

dev: ## Install runtime + dev dependencies and pre-commit hooks
	$(PY) -m pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

run: ## Run the FastAPI app (reload)
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dashboard: ## Run the Streamlit governance dashboard (future phase)
	streamlit run governance_dashboard/app.py

lint: ## Lint with ruff
	ruff check .

format: ## Auto-format with ruff
	ruff format .
	ruff check . --fix

typecheck: ## Static type-check with mypy
	mypy .

test: ## Run the test suite
	pytest

cov: ## Run tests with coverage
	pytest --cov=requirement_intelligence --cov=shared --cov=infrastructure

check: lint typecheck test ## Run all quality gates

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
