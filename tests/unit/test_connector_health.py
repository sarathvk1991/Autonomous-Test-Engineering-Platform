"""Unit tests for the connector health check (CAP-074A).

The health check must classify each source without executing any pipeline stage,
must never raise for an unhealthy source, and must distinguish a *misconfigured*
source (operator error, source never contacted) from an *unreachable* one
(configuration fine, source down). API probing is mocked — no real network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from requirement_intelligence.platform import connector_health
from requirement_intelligence.platform.connector_health import (
    STATUS_MISCONFIGURED,
    STATUS_READY,
    STATUS_UNREACHABLE,
    check_connector_health,
)
from requirement_intelligence.registry.execution_mode import API_MODE, FILE_MODE
from requirement_intelligence.registry.registry_loader import RegistryLoader

_LAYER_DIR = Path(__file__).resolve().parents[2] / "requirement_intelligence"

_API_ENV = {
    "JIRA_BASE_URL": "https://example.atlassian.net",
    "JIRA_EMAIL": "operator@example.com",
    "JIRA_API_TOKEN": "token-value",
    "SONAR_BASE_URL": "http://localhost:9000",
    "SONAR_TOKEN": "sonar-token-value",
    "SONAR_PROJECT_KEY": "example-project",
    "ZAP_BASE_URL": "http://localhost:8080",
    "ZAP_API_KEY": "zap-key-value",
}


def _set_api_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in _API_ENV.items():
        monkeypatch.setenv(name, value)


def _patch_probe(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    """Route the health probe's httpx.Client onto a mock transport."""
    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs.setdefault("transport", transport)
        return real_client(**kwargs)

    monkeypatch.setattr(connector_health.httpx, "Client", factory)


def _loader_from(tmp_path: Path, registry: dict[str, object], mode: str) -> RegistryLoader:
    path = tmp_path / "source-registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    return RegistryLoader(path, execution_mode=mode)


# =========================================================================== #
# FILE mode
# =========================================================================== #
@pytest.mark.unit
def test_file_mode_reports_every_source_ready() -> None:
    report = check_connector_health(FILE_MODE, base_dir=_LAYER_DIR)
    assert report.execution_mode == FILE_MODE
    assert report.healthy
    assert {r.source_id for r in report.results} == {"jira", "owasp_zap", "sonarqube"}
    assert all(r.status == STATUS_READY for r in report.results)


@pytest.mark.unit
def test_file_mode_missing_input_is_unreachable_not_an_exception(tmp_path: Path) -> None:
    registry = {
        "defaults": {"enabled": False},
        "sources": [
            {
                "sourceId": "jira",
                "sourceName": "JIRA",
                "enabled": True,
                "inputPath": "input/jira/absent.json",
                "connectorClass": (
                    "requirement_intelligence.connectors.jira.connector.JiraConnector"
                ),
                "mapperClass": "requirement_intelligence.mappers.jira_mapper.JiraMapper",
            }
        ],
    }
    report = check_connector_health(
        FILE_MODE, base_dir=tmp_path, loader=_loader_from(tmp_path, registry, FILE_MODE)
    )
    assert not report.healthy
    assert report.results[0].status == STATUS_UNREACHABLE
    assert "does not exist" in report.results[0].detail


@pytest.mark.unit
def test_file_mode_missing_input_path_is_misconfigured(tmp_path: Path) -> None:
    registry = {
        "defaults": {"enabled": False},
        "sources": [
            {
                "sourceId": "jira",
                "sourceName": "JIRA",
                "enabled": True,
                "connectorClass": (
                    "requirement_intelligence.connectors.jira.connector.JiraConnector"
                ),
                "mapperClass": "requirement_intelligence.mappers.jira_mapper.JiraMapper",
            }
        ],
    }
    report = check_connector_health(
        FILE_MODE, base_dir=tmp_path, loader=_loader_from(tmp_path, registry, FILE_MODE)
    )
    assert report.results[0].status == STATUS_MISCONFIGURED


# =========================================================================== #
# API mode
# =========================================================================== #
@pytest.mark.unit
def test_api_mode_ready_when_endpoint_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_api_env(monkeypatch)
    _patch_probe(monkeypatch, lambda _request: httpx.Response(200))

    report = check_connector_health(API_MODE, base_dir=_LAYER_DIR)
    assert report.healthy
    assert all(r.status == STATUS_READY for r in report.results)
    assert all("HTTP 200" in r.detail for r in report.results)


@pytest.mark.unit
@pytest.mark.parametrize("status_code", [401, 403])
def test_api_mode_auth_status_still_proves_reachability(
    monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    _set_api_env(monkeypatch)
    _patch_probe(monkeypatch, lambda _request: httpx.Response(status_code))

    report = check_connector_health(API_MODE, base_dir=_LAYER_DIR)
    assert report.healthy
    assert all(r.status == STATUS_READY for r in report.results)
    assert all("endpoint is up" in r.detail for r in report.results)


@pytest.mark.unit
def test_api_mode_connection_error_is_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_api_env(monkeypatch)

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _patch_probe(monkeypatch, refuse)

    report = check_connector_health(API_MODE, base_dir=_LAYER_DIR)
    assert not report.healthy
    assert all(r.status == STATUS_UNREACHABLE for r in report.results)
    assert all("Cannot reach" in r.detail for r in report.results)


@pytest.mark.unit
def test_api_mode_timeout_is_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_api_env(monkeypatch)

    def stall(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    _patch_probe(monkeypatch, stall)

    report = check_connector_health(API_MODE, base_dir=_LAYER_DIR)
    assert all(r.status == STATUS_UNREACHABLE for r in report.results)
    assert all("within" in r.detail for r in report.results)


@pytest.mark.unit
def test_api_mode_unset_credential_is_misconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_api_env(monkeypatch)
    monkeypatch.setenv("SONAR_TOKEN", "")
    _patch_probe(monkeypatch, lambda _request: httpx.Response(200))

    report = check_connector_health(API_MODE, base_dir=_LAYER_DIR)
    assert not report.healthy
    sonar = next(r for r in report.results if r.source_id == "sonarqube")
    assert sonar.status == STATUS_MISCONFIGURED
    assert "SONAR_TOKEN" in sonar.detail
    # A misconfigured source does not mask the healthy ones.
    assert next(r for r in report.results if r.source_id == "jira").status == STATUS_READY


@pytest.mark.unit
def test_health_result_never_contains_a_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_api_env(monkeypatch)
    _patch_probe(monkeypatch, lambda _request: httpx.Response(200))

    report = check_connector_health(API_MODE, base_dir=_LAYER_DIR)
    blob = " ".join(r.detail for r in report.results)
    for secret in ("token-value", "sonar-token-value", "zap-key-value"):
        assert secret not in blob
