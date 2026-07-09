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


# Bundled sample exports shipped for FILE-mode ingestion.
_INPUT_DIR = Path(__file__).resolve().parents[2] / "input"
JIRA_SAMPLE_ISSUES = _INPUT_DIR / "jira" / "jira-issues.json"
ZAP_SAMPLE_ALERTS = _INPUT_DIR / "zap" / "zap-alerts.json"
SONAR_SAMPLE_ISSUES = _INPUT_DIR / "sonar" / "sonar-issues.json"


def _file_config(path: Path) -> dict[str, Any]:
    return {"inputMode": "FILE", "inputPath": str(path)}


def _api_config() -> dict[str, Any]:
    # Superset connection block: each connector reads only the fields it needs.
    # Direct literal values are accepted so these tests need no environment.
    return {
        "inputMode": "API",
        "connection": {
            "authType": "basic",
            "baseUrl": "https://example.test",
            "authUser": "user@example.test",
            "authToken": "secret-token",
            "projectKey": "PROJ",
            "apiKey": "zap-api-key",
        },
        "api": {"pagination": {"pageSize": 50}},
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
def test_fetch_file_mode_missing_input_path_raises(
    cls: type[SourceConnector], source_id: str, source_name: str
) -> None:
    with pytest.raises(ConnectorConfigurationError):
        cls({"inputMode": "FILE"}).fetch_raw_records()


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
def test_validate_api_mode_ok(cls: type[SourceConnector], source_id: str, source_name: str) -> None:
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


# --------------------------------------------------------------------------- #
# JIRA — raw fidelity against the bundled sample export
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_jira_file_mode_reads_bundled_sample_raw() -> None:
    """JIRA FILE mode reads the bundled issues export and preserves it raw.

    The JIRA export is a single top-level object wrapping an ``issues`` array
    (alongside epic/total metadata), and each issue keeps JIRA's native
    ``key`` + nested ``fields`` shape. The connector must return that payload
    exactly as exported — no field renaming, flattening, or normalization.
    Canonical mapping belongs to the parser layer.
    """
    expected = json.loads(JIRA_SAMPLE_ISSUES.read_text(encoding="utf-8"))

    records = JiraConnector(_file_config(JIRA_SAMPLE_ISSUES)).fetch_raw_records()

    # A top-level object is fetched as a single raw payload record, untouched.
    assert records == [expected]
    payload = records[0]

    # The raw JIRA structure, including the top-level issues array, is kept.
    assert isinstance(payload.get("issues"), list)
    assert len(payload["issues"]) > 0

    first_issue = payload["issues"][0]
    # Native JIRA issue shape is preserved (key + nested fields, not flattened).
    assert "key" in first_issue
    assert "fields" in first_issue
    # Raw JIRA field names are present and unmodified (not canonical names).
    for field in ("summary", "issuetype"):
        assert field in first_issue["fields"]
    assert JiraConnector(_file_config(JIRA_SAMPLE_ISSUES)).validate_connection() is True


# --------------------------------------------------------------------------- #
# OWASP ZAP — raw fidelity against the bundled sample export
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_zap_file_mode_reads_bundled_sample_raw() -> None:
    """ZAP FILE mode reads the bundled alert export and preserves raw fields.

    The connector must fetch alerts exactly as exported by OWASP ZAP — no field
    renaming, normalization, or consolidation. Canonical mapping belongs to the
    parser layer, not the connector.
    """
    expected = json.loads(ZAP_SAMPLE_ALERTS.read_text(encoding="utf-8"))

    records = ZapConnector(_file_config(ZAP_SAMPLE_ALERTS)).fetch_raw_records()

    # Returned untouched, in order, with every alert preserved.
    assert records == expected
    assert len(records) > 0

    first = records[0]
    # Raw ZAP fields are present and unmodified (not mapped to canonical names).
    for field in ("pluginId", "alert", "risk", "confidence", "url"):
        assert field in first
    assert ZapConnector(_file_config(ZAP_SAMPLE_ALERTS)).validate_connection() is True


# --------------------------------------------------------------------------- #
# SonarQube — raw fidelity against the bundled sample export
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_sonarqube_file_mode_reads_bundled_sample_raw() -> None:
    """SonarQube FILE mode reads the bundled issues export and preserves it raw.

    The SonarQube export is a single top-level object wrapping an ``issues``
    array (plus paging/components/facets). The connector must return that
    payload exactly as exported — no field renaming, normalization, or issue
    consolidation. Canonical mapping belongs to the parser layer.
    """
    expected = json.loads(SONAR_SAMPLE_ISSUES.read_text(encoding="utf-8"))

    records = SonarQubeConnector(_file_config(SONAR_SAMPLE_ISSUES)).fetch_raw_records()

    # A top-level object is fetched as a single raw payload record, untouched.
    assert records == [expected]
    payload = records[0]

    # The raw SonarQube structure, including the top-level issues array, is kept.
    assert isinstance(payload.get("issues"), list)
    assert len(payload["issues"]) > 0

    first_issue = payload["issues"][0]
    # Raw Sonar issue fields are present and unmodified (not canonical names).
    for field in (
        "rule",
        "severity",
        "component",
        "project",
        "line",
        "message",
        "type",
        "tags",
        "impacts",
        "status",
    ):
        assert field in first_issue
    assert SonarQubeConnector(_file_config(SONAR_SAMPLE_ISSUES)).validate_connection() is True
