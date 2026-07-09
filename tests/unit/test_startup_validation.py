"""Unit tests for startup validation (CAP-074A).

The contract under test: an expected configuration problem is reported as an
actionable message on :class:`StartupValidationError`, never as a stack trace,
and every problem present is reported in one pass rather than one per run.
No network call is made and no secret value ever enters a message.

Requirements are never re-declared here — validation delegates to each
connector's own ``validate_connection()``, so a source whose connector demands a
project key (SonarQube) is held to that, while one for which it is optional
(JIRA) is not.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from requirement_intelligence.platform.startup_validation import (
    StartupValidationError,
    validate_startup,
)
from requirement_intelligence.registry.execution_mode import API_MODE, FILE_MODE
from requirement_intelligence.registry.registry_loader import RegistryLoader

_LAYER_DIR = Path(__file__).resolve().parents[2] / "requirement_intelligence"

_JIRA_CONNECTOR = "requirement_intelligence.connectors.jira.connector.JiraConnector"
_JIRA_MAPPER = "requirement_intelligence.mappers.jira_mapper.JiraMapper"
_SONAR_CONNECTOR = "requirement_intelligence.connectors.sonarqube.connector.SonarQubeConnector"
_SONAR_MAPPER = "requirement_intelligence.mappers.sonar_mapper.SonarMapper"

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


def _loader_from(tmp_path: Path, registry: dict[str, object], mode: str) -> RegistryLoader:
    path = tmp_path / "source-registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    return RegistryLoader(path, execution_mode=mode)


def _jira_source(**overrides: object) -> dict[str, object]:
    source: dict[str, object] = {
        "sourceId": "jira",
        "sourceName": "JIRA",
        "enabled": True,
        "connectorClass": _JIRA_CONNECTOR,
        "mapperClass": _JIRA_MAPPER,
    }
    source.update(overrides)
    return source


# =========================================================================== #
# FILE mode
# =========================================================================== #
@pytest.mark.unit
def test_file_mode_passes_against_the_real_registry() -> None:
    report = validate_startup(FILE_MODE, base_dir=_LAYER_DIR)
    assert report.execution_mode == FILE_MODE
    assert not report.failures
    names = {check.name for check in report.checks}
    assert "Source Registry" in names
    assert "Prompt Registry" in names
    assert "Input File [JIRA]" in names


@pytest.mark.unit
def test_file_mode_reports_every_missing_input(tmp_path: Path) -> None:
    registry = {
        "defaults": {"enabled": False},
        "sources": [
            _jira_source(inputPath="input/jira/absent.json"),
            {
                "sourceId": "sonarqube",
                "sourceName": "SonarQube",
                "enabled": True,
                "inputPath": "input/sonar/absent.json",
                "connectorClass": _SONAR_CONNECTOR,
                "mapperClass": _SONAR_MAPPER,
            },
        ],
    }

    with pytest.raises(StartupValidationError) as exc:
        validate_startup(
            FILE_MODE,
            base_dir=tmp_path,
            loader=_loader_from(tmp_path, registry, FILE_MODE),
        )

    # Both problems surface together, so the operator fixes them in one pass.
    assert len(exc.value.failures) == 2
    joined = " ".join(exc.value.failures)
    assert "Input File [JIRA]" in joined
    assert "Input File [SonarQube]" in joined
    assert "does not exist" in joined


@pytest.mark.unit
def test_file_mode_rejects_missing_input_path(tmp_path: Path) -> None:
    registry = {"defaults": {"enabled": False}, "sources": [_jira_source()]}
    with pytest.raises(StartupValidationError) as exc:
        validate_startup(
            FILE_MODE,
            base_dir=tmp_path,
            loader=_loader_from(tmp_path, registry, FILE_MODE),
        )
    assert "non-empty 'inputPath'" in exc.value.failures[0]


@pytest.mark.unit
def test_file_mode_resolves_input_paths_against_base_dir(tmp_path: Path) -> None:
    """A run from the repo root must not report the layer's inputs as missing."""
    registry = {
        "defaults": {"enabled": False},
        "sources": [_jira_source(inputPath="input/jira/jira-issues.json")],
    }
    report = validate_startup(
        FILE_MODE,
        base_dir=_LAYER_DIR,
        loader=_loader_from(tmp_path, registry, FILE_MODE),
    )
    assert not report.failures


# =========================================================================== #
# API mode
# =========================================================================== #
@pytest.mark.unit
def test_api_mode_passes_when_every_credential_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_api_env(monkeypatch)
    report = validate_startup(API_MODE, base_dir=_LAYER_DIR)
    assert not report.failures
    assert any(check.name.startswith("API Configuration [") for check in report.checks)


@pytest.mark.unit
def test_api_mode_names_the_unset_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_api_env(monkeypatch)
    monkeypatch.setenv("SONAR_TOKEN", "")

    with pytest.raises(StartupValidationError) as exc:
        validate_startup(API_MODE, base_dir=_LAYER_DIR)

    failures = " ".join(exc.value.failures)
    assert "SONAR_TOKEN" in failures


@pytest.mark.unit
def test_api_mode_honours_each_connector_own_requirements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SonarQube's project key is mandatory; JIRA's is not."""
    _set_api_env(monkeypatch)
    monkeypatch.setenv("SONAR_PROJECT_KEY", "")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "")

    with pytest.raises(StartupValidationError) as exc:
        validate_startup(API_MODE, base_dir=_LAYER_DIR)

    failures = " ".join(exc.value.failures)
    assert "SONAR_PROJECT_KEY" in failures
    assert "JIRA_PROJECT_KEY" not in failures


@pytest.mark.unit
def test_api_mode_never_leaks_a_secret_value(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_api_env(monkeypatch)
    monkeypatch.setenv("ZAP_BASE_URL", "not-a-url")

    with pytest.raises(StartupValidationError) as exc:
        validate_startup(API_MODE, base_dir=_LAYER_DIR)

    failures = " ".join(exc.value.failures)
    assert "ZAP_BASE_URL" in failures
    # The *names* of variables appear; their secret values never do.
    for secret in ("zap-key-value", "sonar-token-value", "token-value"):
        assert secret not in failures


@pytest.mark.unit
@pytest.mark.parametrize("bad_url", ["not-a-url", "localhost:9000", "ftp://host"])
def test_api_mode_rejects_malformed_endpoint(monkeypatch: pytest.MonkeyPatch, bad_url: str) -> None:
    _set_api_env(monkeypatch)
    monkeypatch.setenv("JIRA_BASE_URL", bad_url)
    with pytest.raises(StartupValidationError) as exc:
        validate_startup(API_MODE, base_dir=_LAYER_DIR)
    assert "JIRA_BASE_URL" in " ".join(exc.value.failures)


@pytest.mark.unit
def test_api_mode_requires_a_connection_block(tmp_path: Path) -> None:
    registry = {"defaults": {"enabled": False}, "sources": [_jira_source()]}
    with pytest.raises(StartupValidationError) as exc:
        validate_startup(
            API_MODE,
            base_dir=tmp_path,
            loader=_loader_from(tmp_path, registry, API_MODE),
        )
    assert "'connection' block" in exc.value.failures[0]


# =========================================================================== #
# Registry-level failures (mode independent)
# =========================================================================== #
@pytest.mark.unit
def test_no_enabled_source_is_a_startup_failure(tmp_path: Path) -> None:
    registry = {"defaults": {"enabled": False}, "sources": []}
    with pytest.raises(StartupValidationError) as exc:
        validate_startup(
            FILE_MODE,
            base_dir=tmp_path,
            loader=_loader_from(tmp_path, registry, FILE_MODE),
        )
    assert "No source is enabled" in exc.value.failures[0]


@pytest.mark.unit
def test_unparseable_registry_is_a_startup_failure(tmp_path: Path) -> None:
    path = tmp_path / "source-registry.json"
    path.write_text("{ not json", encoding="utf-8")

    with pytest.raises(StartupValidationError) as exc:
        validate_startup(
            FILE_MODE,
            base_dir=tmp_path,
            loader=RegistryLoader(path, execution_mode=FILE_MODE),
        )
    assert "Source Registry" in exc.value.failures[0]
