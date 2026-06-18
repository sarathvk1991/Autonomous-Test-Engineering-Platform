#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Bootstrap a local development environment.
# Usage:  ./scripts/bootstrap.sh
# ---------------------------------------------------------------------------
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Creating virtual environment (.venv)"
python3 -m venv .venv

echo "==> Installing dependencies"
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt

if [ ! -f .env ]; then
  echo "==> Creating .env from template"
  cp .env.example .env
fi

echo "==> Done. Activate with:  source .venv/bin/activate"
echo "    Run the API with:     make run"
