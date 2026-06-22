"""Unit tests for the concrete source connectors.

Verifies identity/metadata plus the FILE/API input-mode dispatch and validation
behavior shared by JiraConnector, ZapConnector, and SonarQubeConnector. The same
behavioral contract is asserted for every connector via parametrization.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from requirement_intelligence.connectors.base import SourceConnector
from requirement_intelligence.connectors.connector_exceptions import (
    ConnectorConfigurationError,
    ConnectorConnectionError,
)
from requirement_intelligence.connectors.jira.connector import JiraConnector
from requirement_intelligence.connectors.sonarqube.connector import SonarQubeConnector
from requirement_intelligence.connectors.zap.connector import ZapConnector

# (connector class, expected source id, expected source name)
CONNECTOR_CASES = [
    pytest.param(JiraConnector, "jira", "JIRA", id="jira"),
    pytest.param(ZapConnector, "owasp_zap", "OWASP ZAP", id="zap"),
    pytest.param(SonarQubeConnector, "sonarqube", "SonarQube", id="sonarqube"),
]


def _file_config(path: Path) -> dict[str, Any]:
    return {"inputMode": "FILE", "inputPath": str(path)}


def _api_config() -> dict[str, Any]:
    return {
        "inputMode": "API",
        "connection": {"baseUrl": "https://example.test", "authType": "token"},
    }


# --------------------------------------------------------------------------- #
# Identity / metadata
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_identity(cls: type[SourceConnector], source_id: str, source_name: str) -> None:
    connector = cls({})
    assert isinstance(connector, SourceConnector)
    assert connector.get_source_id() == source_id
    assert connector.get_source_name() == source_name


@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_metadata(cls: type[SourceConnector], source_id: str, source_name: str) -> None:
    meta = cls({}).get_metadata()
    assert meta["sourceId"] == source_id
    assert meta["sourceName"] == source_name
    assert meta["supportedInputModes"] == ["FILE", "API"]


# --------------------------------------------------------------------------- #
# fetch_raw_records dispatch
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_fetch_file_mode_reads_records(
    cls: type[SourceConnector], source_id: str, source_name: str, tmp_path: Path
) -> None:
    f = tmp_path / "records.json"
    f.write_text(json.dumps([{"id": "A"}, {"id": "B"}]), encoding="utf-8")
    assert cls(_file_config(f)).fetch_raw_records() == [{"id": "A"}, {"id": "B"}]


@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_fetch_api_mode_not_implemented(
    cls: type[SourceConnector], source_id: str, source_name: str
) -> None:
    with pytest.raises(NotImplementedError, match="API-mode ingestion"):
        cls(_api_config()).fetch_raw_records()


@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_fetch_invalid_mode_raises(
    cls: type[SourceConnector], source_id: str, source_name: str
) -> None:
    with pytest.raises(ConnectorConfigurationError):
        cls({"inputMode": "BOGUS"}).fetch_raw_records()


@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_fetch_missing_mode_raises(
    cls: type[SourceConnector], source_id: str, source_name: str
) -> None:
    with pytest.raises(ConnectorConfigurationError):
        cls({}).fetch_raw_records()


# --------------------------------------------------------------------------- #
# validate_connection
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_validate_file_mode_ok(
    cls: type[SourceConnector], source_id: str, source_name: str, tmp_path: Path
) -> None:
    f = tmp_path / "records.json"
    f.write_text("[]", encoding="utf-8")
    assert cls(_file_config(f)).validate_connection() is True


@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_validate_file_mode_missing_file_raises(
    cls: type[SourceConnector], source_id: str, source_name: str, tmp_path: Path
) -> None:
    with pytest.raises(ConnectorConnectionError):
        cls(_file_config(tmp_path / "missing.json")).validate_connection()


@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_validate_api_mode_ok(
    cls: type[SourceConnector], source_id: str, source_name: str
) -> None:
    assert cls(_api_config()).validate_connection() is True


@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_validate_api_mode_missing_fields_raises(
    cls: type[SourceConnector], source_id: str, source_name: str
) -> None:
    config = {"inputMode": "API", "connection": {"baseUrl": "", "authType": ""}}
    with pytest.raises(ConnectorConfigurationError):
        cls(config).validate_connection()


@pytest.mark.unit
@pytest.mark.parametrize(("cls", "source_id", "source_name"), CONNECTOR_CASES)
def test_validate_invalid_mode_raises(
    cls: type[SourceConnector], source_id: str, source_name: str
) -> None:
    with pytest.raises(ConnectorConfigurationError):
        cls({"inputMode": "BOGUS"}).validate_connection()
