"""Shared pytest fixtures for the platform test suite.

Layer-specific fixtures belong in that layer's ``tests/`` package; truly
cross-cutting fixtures (settings overrides, app client) live here.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    """Return a FastAPI TestClient backed by a fresh app instance."""
    return TestClient(create_app())
