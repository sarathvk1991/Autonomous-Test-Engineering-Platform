"""Unit tests for live (API-mode) source connectors and the shared HTTP client.

These tests exercise the resilient transport (:mod:`connectors.api_client`) and
the three live connectors (JIRA, SonarQube, OWASP ZAP) against a mocked HTTP
layer (``httpx.MockTransport``) — no real network, no credentials. They cover
pagination, incremental retrieval, branch scoping, authentication, raw-record
fidelity (no mapping in the connector), and every mandated failure scenario:
timeout, network unavailability, HTTP 401/403/404/429/500, and malformed JSON.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
import pytest

from requirement_intelligence.connectors import api_client
from requirement_intelligence.connectors.api_client import ApiClient, RetryPolicy
from requirement_intelligence.connectors.connector_exceptions import (
    ConnectorConfigurationError,
    ConnectorConnectionError,
    ConnectorFetchError,
)
from requirement_intelligence.connectors.jira.connector import JiraConnector
from requirement_intelligence.connectors.sonarqube.connector import SonarQubeConnector
from requirement_intelligence.connectors.zap.connector import ZapConnector

Handler = Callable[[httpx.Request], httpx.Response]


def _client_for(handler: Handler) -> httpx.Client:
    """Build an httpx.Client bound to a mock transport for the given handler."""
    return httpx.Client(transport=httpx.MockTransport(handler))


def _patch_transport(monkeypatch: pytest.MonkeyPatch, handler: Handler) -> None:
    """Force every ApiClient-created httpx.Client onto a mock transport."""
    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def factory(**kwargs: Any) -> httpx.Client:
        kwargs.setdefault("transport", transport)
        return real_client(**kwargs)

    monkeypatch.setattr(api_client.httpx, "Client", factory)
    # Retries never sleep for real in tests.
    monkeypatch.setattr(api_client.time, "sleep", lambda *_a, **_k: None)


_NO_BACKOFF = RetryPolicy(max_attempts=3, backoff_seconds=0.0)


# =========================================================================== #
# api_client — configuration/environment resolution
# =========================================================================== #
@pytest.mark.unit
def test_resolve_secret_field_direct_value() -> None:
    value = api_client.resolve_secret_field(
        {"baseUrl": "https://x"}, direct_key="baseUrl", env_key="baseUrlEnv", source_id="s"
    )
    assert value == "https://x"


@pytest.mark.unit
def test_resolve_secret_field_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_BASE_URL", "https://from-env")
    value = api_client.resolve_secret_field(
        {"baseUrlEnv": "MY_BASE_URL"},
        direct_key="baseUrl",
        env_key="baseUrlEnv",
        source_id="s",
    )
    assert value == "https://from-env"


@pytest.mark.unit
def test_resolve_secret_field_missing_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ABSENT_VAR", raising=False)
    with pytest.raises(ConnectorConfigurationError, match="ABSENT_VAR"):
        api_client.resolve_secret_field(
            {"baseUrlEnv": "ABSENT_VAR"},
            direct_key="baseUrl",
            env_key="baseUrlEnv",
            source_id="s",
        )


@pytest.mark.unit
def test_resolve_secret_field_optional_returns_empty() -> None:
    value = api_client.resolve_secret_field(
        {}, direct_key="branch", env_key="branchEnv", source_id="s", required=False
    )
    assert value == ""


@pytest.mark.unit
def test_resolve_secret_field_required_missing_raises() -> None:
    with pytest.raises(ConnectorConfigurationError, match="baseUrl"):
        api_client.resolve_secret_field(
            {}, direct_key="baseUrl", env_key="baseUrlEnv", source_id="s"
        )


@pytest.mark.unit
def test_resolve_retry_policy_defaults_and_overrides() -> None:
    default = api_client.resolve_retry_policy({})
    assert default.max_attempts == 3
    custom = api_client.resolve_retry_policy(
        {"retry": {"maxAttempts": 5, "backoffSeconds": 2, "maxBackoffSeconds": 10}}
    )
    assert (custom.max_attempts, custom.backoff_seconds, custom.max_backoff_seconds) == (
        5,
        2.0,
        10.0,
    )


@pytest.mark.unit
def test_resolve_retry_policy_rejects_bad_values() -> None:
    policy = api_client.resolve_retry_policy({"retry": {"maxAttempts": 0, "backoffSeconds": -1}})
    assert policy.max_attempts == 3
    assert policy.backoff_seconds == 1.0


@pytest.mark.unit
def test_retry_policy_delay_exponential_and_capped() -> None:
    policy = RetryPolicy(max_attempts=5, backoff_seconds=1.0, max_backoff_seconds=4.0)
    assert policy.delay_for(1) == 1.0
    assert policy.delay_for(2) == 2.0
    assert policy.delay_for(3) == 4.0
    assert policy.delay_for(4) == 4.0  # capped


@pytest.mark.unit
def test_resolve_timeout_and_page_size_defaults() -> None:
    assert api_client.resolve_timeout_seconds({}) == 30.0
    assert api_client.resolve_page_size({}) == 50
    assert api_client.resolve_page_size({"pagination": {"pageSize": 200}}) == 200


@pytest.mark.unit
def test_api_client_requires_base_url() -> None:
    with pytest.raises(ConnectorConfigurationError, match="base URL"):
        ApiClient("")


# =========================================================================== #
# api_client — request behaviour and failure mapping
# =========================================================================== #
@pytest.mark.unit
def test_get_json_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = ApiClient("https://x", client=_client_for(handler))
    assert client.get_json("/thing") == {"ok": True}


@pytest.mark.unit
@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_get_json_retries_transient_then_succeeds(
    status: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api_client.time, "sleep", lambda *_a, **_k: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(status, json={"err": True})
        return httpx.Response(200, json={"ok": True})

    client = ApiClient("https://x", client=_client_for(handler), retry=_NO_BACKOFF)
    assert client.get_json("/thing") == {"ok": True}
    assert calls["n"] == 2


@pytest.mark.unit
def test_get_json_transient_exhausted_raises_fetch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api_client.time, "sleep", lambda *_a, **_k: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"err": True})

    client = ApiClient("https://x", client=_client_for(handler), retry=_NO_BACKOFF)
    with pytest.raises(ConnectorFetchError, match="503"):
        client.get_json("/thing")
    assert calls["n"] == 3  # all attempts used


@pytest.mark.unit
@pytest.mark.parametrize("status", [401, 403])
def test_get_json_auth_failure_raises_connection_error_no_retry(status: int) -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(status, json={"err": True})

    client = ApiClient("https://x", client=_client_for(handler), retry=_NO_BACKOFF)
    with pytest.raises(ConnectorConnectionError, match=str(status)):
        client.get_json("/thing")
    assert calls["n"] == 1  # not retried


@pytest.mark.unit
def test_get_json_404_raises_fetch_error_no_retry() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, json={"err": True})

    client = ApiClient("https://x", client=_client_for(handler), retry=_NO_BACKOFF)
    with pytest.raises(ConnectorFetchError, match="404"):
        client.get_json("/thing")
    assert calls["n"] == 1


@pytest.mark.unit
def test_get_json_malformed_json_raises_fetch_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"{not valid json")

    client = ApiClient("https://x", client=_client_for(handler), retry=_NO_BACKOFF)
    with pytest.raises(ConnectorFetchError, match="malformed JSON"):
        client.get_json("/thing")


@pytest.mark.unit
def test_get_json_timeout_retried_then_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api_client.time, "sleep", lambda *_a, **_k: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ReadTimeout("timed out", request=request)

    client = ApiClient("https://x", client=_client_for(handler), retry=_NO_BACKOFF)
    with pytest.raises(ConnectorConnectionError, match="timeout"):
        client.get_json("/thing")
    assert calls["n"] == 3


@pytest.mark.unit
def test_get_json_network_unavailable_raises_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api_client.time, "sleep", lambda *_a, **_k: None)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = ApiClient("https://x", client=_client_for(handler), retry=_NO_BACKOFF)
    with pytest.raises(ConnectorConnectionError, match="network"):
        client.get_json("/thing")


# =========================================================================== #
# JIRA live connector
# =========================================================================== #
def _jira_config(**api: Any) -> dict[str, Any]:
    return {
        "inputMode": "API",
        "connection": {
            "authType": "basic",
            "baseUrl": "https://jira.example",
            "authUser": "user@example.com",
            "authToken": "token-123",
            "projectKey": "SCRUM",
        },
        "api": {"retry": {"backoffSeconds": 0}, **api},
    }


def _jira_issue(idx: int) -> dict[str, Any]:
    return {
        "key": f"SCRUM-{idx}",
        "self": f"https://jira.example/rest/api/2/issue/{idx}",
        "fields": {"summary": f"Issue {idx}", "issuetype": {"name": "Story"}},
    }


@pytest.mark.unit
def test_jira_api_paginates_and_returns_raw_issues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    all_issues = [_jira_issue(i) for i in range(5)]
    seen_auth: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/api/2/search"
        seen_auth.append(request.headers.get("authorization", ""))
        start = int(request.url.params["startAt"])
        page_size = int(request.url.params["maxResults"])
        page = all_issues[start : start + page_size]
        return httpx.Response(
            200,
            json={
                "issues": page,
                "startAt": start,
                "maxResults": page_size,
                "total": len(all_issues),
            },
        )

    _patch_transport(monkeypatch, handler)
    records = JiraConnector(_jira_config(pagination={"pageSize": 2})).fetch_raw_records()

    assert records == all_issues  # raw fidelity, order preserved, no mapping
    assert all(a.startswith("Basic ") for a in seen_auth)  # basic auth applied
    assert len(seen_auth) == 3  # pages of 2,2,1 over total=5


@pytest.mark.unit
def test_jira_api_incremental_adds_jql_clause(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["jql"] = request.url.params["jql"]
        return httpx.Response(200, json={"issues": [], "total": 0})

    _patch_transport(monkeypatch, handler)
    config = _jira_config(incremental={"enabled": True, "jql": "updated >= -7d"})
    JiraConnector(config).fetch_raw_records()

    assert 'project = "SCRUM"' in captured["jql"]
    assert "updated >= -7d" in captured["jql"]


@pytest.mark.unit
def test_jira_api_401_raises_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"errorMessages": ["nope"]})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(ConnectorConnectionError):
        JiraConnector(_jira_config()).fetch_raw_records()


@pytest.mark.unit
def test_jira_api_validate_connection_missing_env_raises() -> None:
    config = {
        "inputMode": "API",
        "connection": {"authType": "basic", "baseUrlEnv": "JIRA_BASE_URL_ABSENT"},
    }
    with pytest.raises(ConnectorConfigurationError):
        JiraConnector(config).validate_connection()


# =========================================================================== #
# SonarQube live connector
# =========================================================================== #
def _sonar_config(**api: Any) -> dict[str, Any]:
    return {
        "inputMode": "API",
        "connection": {
            "authType": "token",
            "baseUrl": "https://sonar.example",
            "authToken": "sonar-token",
            "projectKey": "my-project",
        },
        "api": {"retry": {"backoffSeconds": 0}, **api},
    }


def _sonar_issue(idx: int) -> dict[str, Any]:
    return {
        "key": f"issue-{idx}",
        "rule": "java:S100",
        "message": f"Problem {idx}",
        "severity": "MAJOR",
        "component": "proj:File.java",
        "line": idx,
        "status": "OPEN",
    }


@pytest.mark.unit
def test_sonar_api_paginates_with_paging_total(monkeypatch: pytest.MonkeyPatch) -> None:
    all_issues = [_sonar_issue(i) for i in range(5)]
    seen_pages: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/issues/search"
        assert request.url.params["componentKeys"] == "my-project"
        page = int(request.url.params["p"])
        page_size = int(request.url.params["ps"])
        seen_pages.append(page)
        start = (page - 1) * page_size
        batch = all_issues[start : start + page_size]
        return httpx.Response(
            200,
            json={
                "issues": batch,
                "paging": {"pageIndex": page, "pageSize": page_size, "total": len(all_issues)},
            },
        )

    _patch_transport(monkeypatch, handler)
    records = SonarQubeConnector(_sonar_config(pagination={"pageSize": 2})).fetch_raw_records()

    assert records == all_issues
    assert seen_pages == [1, 2, 3]


@pytest.mark.unit
def test_sonar_api_branch_and_incremental_params(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(200, json={"issues": [], "paging": {"total": 0}})

    _patch_transport(monkeypatch, handler)
    config = _sonar_config(incremental={"enabled": True, "createdAfter": "2026-01-01"})
    config["connection"]["branch"] = "release/1.0"
    SonarQubeConnector(config).fetch_raw_records()

    assert captured["branch"] == "release/1.0"
    assert captured["createdAfter"] == "2026-01-01"


@pytest.mark.unit
def test_sonar_api_token_is_basic_username(monkeypatch: pytest.MonkeyPatch) -> None:
    import base64

    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization", "")
        return httpx.Response(200, json={"issues": [], "paging": {"total": 0}})

    _patch_transport(monkeypatch, handler)
    SonarQubeConnector(_sonar_config()).fetch_raw_records()

    scheme, _, encoded = captured["auth"].partition(" ")
    assert scheme == "Basic"
    assert base64.b64decode(encoded).decode() == "sonar-token:"


# =========================================================================== #
# OWASP ZAP live connector
# =========================================================================== #
def _zap_config(**api: Any) -> dict[str, Any]:
    return {
        "inputMode": "API",
        "connection": {
            "authType": "apiKey",
            "baseUrl": "https://zap.example",
            "apiKey": "zap-key",
        },
        "api": {"retry": {"backoffSeconds": 0}, **api},
    }


def _zap_alert(idx: int) -> dict[str, Any]:
    return {
        "pluginId": str(10000 + idx),
        "alert": f"Alert {idx}",
        "risk": "Medium",
        "url": f"https://target.example/{idx}",
        "cweid": "1021",
    }


@pytest.mark.unit
def test_zap_api_paginates_until_short_page(monkeypatch: pytest.MonkeyPatch) -> None:
    all_alerts = [_zap_alert(i) for i in range(5)]
    seen_start: list[int] = []
    seen_key: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/JSON/core/view/alerts/"
        seen_key.append(request.url.params["apikey"])
        start = int(request.url.params["start"])
        count = int(request.url.params["count"])
        seen_start.append(start)
        batch = all_alerts[start : start + count]
        return httpx.Response(200, json={"alerts": batch})

    _patch_transport(monkeypatch, handler)
    records = ZapConnector(_zap_config(pagination={"pageSize": 2})).fetch_raw_records()

    assert records == all_alerts
    assert seen_start == [0, 2, 4]  # stops when a short page (<count) is returned
    assert set(seen_key) == {"zap-key"}


@pytest.mark.unit
def test_zap_api_target_scope_param(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(200, json={"alerts": []})

    _patch_transport(monkeypatch, handler)
    config = _zap_config()
    config["connection"]["targetUrl"] = "https://target.example"
    ZapConnector(config).fetch_raw_records()

    assert captured["baseurl"] == "https://target.example"


@pytest.mark.unit
def test_zap_api_sends_api_key_header(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["header"] = request.headers.get("x-zap-api-key", "")
        return httpx.Response(200, json={"alerts": []})

    _patch_transport(monkeypatch, handler)
    ZapConnector(_zap_config()).fetch_raw_records()

    assert captured["header"] == "zap-key"


# =========================================================================== #
# Cross-connector failure scenarios
# =========================================================================== #
_CONNECTOR_FACTORIES = [
    pytest.param(lambda: JiraConnector(_jira_config()), id="jira"),
    pytest.param(lambda: SonarQubeConnector(_sonar_config()), id="sonarqube"),
    pytest.param(lambda: ZapConnector(_zap_config()), id="zap"),
]


@pytest.mark.unit
@pytest.mark.parametrize("factory", _CONNECTOR_FACTORIES)
def test_connector_api_403_raises_connection_error(
    factory: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"err": True})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(ConnectorConnectionError):
        factory().fetch_raw_records()


@pytest.mark.unit
@pytest.mark.parametrize("factory", _CONNECTOR_FACTORIES)
def test_connector_api_500_exhausts_and_raises_fetch_error(
    factory: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"err": True})

    _patch_transport(monkeypatch, handler)
    with pytest.raises(ConnectorFetchError):
        factory().fetch_raw_records()


@pytest.mark.unit
@pytest.mark.parametrize("factory", _CONNECTOR_FACTORIES)
def test_connector_api_malformed_json_raises_fetch_error(
    factory: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>not json</html>")

    _patch_transport(monkeypatch, handler)
    with pytest.raises(ConnectorFetchError):
        factory().fetch_raw_records()


@pytest.mark.unit
@pytest.mark.parametrize("factory", _CONNECTOR_FACTORIES)
def test_connector_api_unavailable_raises_connection_error(
    factory: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    _patch_transport(monkeypatch, handler)
    with pytest.raises(ConnectorConnectionError):
        factory().fetch_raw_records()
