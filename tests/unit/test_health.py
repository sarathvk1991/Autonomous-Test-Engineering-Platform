"""Smoke test: the deployable unit boots and the health probe responds.

Verifies app assembly (settings, router mounting) without exercising any
layer business logic.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
