"""Unit tests for the shared connector input-mode helpers.

Covers mode resolution and the FILE-mode path/readability validation and raw
JSON fetching in ``connector_io``. API-mode transport is covered separately in
``test_connector_api.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from requirement_intelligence.connectors import connector_io
from requirement_intelligence.connectors.connector_exceptions import (
    ConnectorConfigurationError,
    ConnectorConnectionError,
    ConnectorFetchError,
)


# --------------------------------------------------------------------------- #
# get_input_mode
# --------------------------------------------------------------------------- #
@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [("FILE", "FILE"), ("file", "FILE"), ("  api  ", "API"), ("Api", "API")],
)
def test_get_input_mode_normalizes(raw: str, expected: str) -> None:
    assert connector_io.get_input_mode({"inputMode": raw}) == expected


@pytest.mark.unit
@pytest.mark.parametrize("config", [{}, {"inputMode": ""}, {"inputMode": "   "}, {"inputMode": 5}])
def test_get_input_mode_invalid_raises(config: dict) -> None:
    with pytest.raises(ConnectorConfigurationError):
        connector_io.get_input_mode(config)


# --------------------------------------------------------------------------- #
# resolve_input_path
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_resolve_input_path_returns_path() -> None:
    assert connector_io.resolve_input_path({"inputPath": "input/x.json"}) == Path("input/x.json")


@pytest.mark.unit
@pytest.mark.parametrize("config", [{}, {"inputPath": ""}, {"inputPath": "  "}, {"inputPath": 1}])
def test_resolve_input_path_invalid_raises(config: dict) -> None:
    with pytest.raises(ConnectorConfigurationError):
        connector_io.resolve_input_path(config)


# --------------------------------------------------------------------------- #
# validate_input_file
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_validate_input_file_ok(tmp_path: Path) -> None:
    f = tmp_path / "data.json"
    f.write_text("[]", encoding="utf-8")
    assert connector_io.validate_input_file({"inputPath": str(f)}) is True


@pytest.mark.unit
def test_validate_input_file_missing_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    with pytest.raises(ConnectorConnectionError, match="does not exist"):
        connector_io.validate_input_file({"inputPath": str(missing)})


@pytest.mark.unit
def test_validate_input_file_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(ConnectorConnectionError, match="not a file"):
        connector_io.validate_input_file({"inputPath": str(tmp_path)})


@pytest.mark.unit
def test_validate_input_file_unreadable_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    f = tmp_path / "data.json"
    f.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(connector_io.os, "access", lambda *_a, **_k: False)
    with pytest.raises(ConnectorConnectionError, match="not readable"):
        connector_io.validate_input_file({"inputPath": str(f)})


# --------------------------------------------------------------------------- #
# read_json_records
# --------------------------------------------------------------------------- #
@pytest.mark.unit
def test_read_json_records_list_of_objects(tmp_path: Path) -> None:
    f = tmp_path / "data.json"
    f.write_text(json.dumps([{"id": 1}, {"id": 2}]), encoding="utf-8")
    assert connector_io.read_json_records({"inputPath": str(f)}) == [
        {"id": 1},
        {"id": 2},
    ]


@pytest.mark.unit
def test_read_json_records_single_object_is_wrapped(tmp_path: Path) -> None:
    f = tmp_path / "data.json"
    f.write_text(json.dumps({"issues": [1, 2]}), encoding="utf-8")
    assert connector_io.read_json_records({"inputPath": str(f)}) == [{"issues": [1, 2]}]


@pytest.mark.unit
def test_read_json_records_non_object_elements_raises(tmp_path: Path) -> None:
    f = tmp_path / "data.json"
    f.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ConnectorFetchError, match="non-object"):
        connector_io.read_json_records({"inputPath": str(f)})


@pytest.mark.unit
def test_read_json_records_scalar_payload_raises(tmp_path: Path) -> None:
    f = tmp_path / "data.json"
    f.write_text("42", encoding="utf-8")
    with pytest.raises(ConnectorFetchError, match="Unsupported JSON payload"):
        connector_io.read_json_records({"inputPath": str(f)})


@pytest.mark.unit
def test_read_json_records_malformed_json_raises(tmp_path: Path) -> None:
    f = tmp_path / "data.json"
    f.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ConnectorFetchError, match="Failed to read raw records"):
        connector_io.read_json_records({"inputPath": str(f)})


@pytest.mark.unit
def test_read_json_records_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ConnectorConnectionError):
        connector_io.read_json_records({"inputPath": str(tmp_path / "missing.json")})
