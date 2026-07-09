"""Shared input-mode helpers for source connectors.

This module implements the reusable, source-agnostic plumbing behind the
connector framework's **FILE** ingestion path:

- Resolving the active ``inputMode`` from the source-registry entry.
- The FILE-mode ingestion path: resolving ``inputPath``, validating
  readability, and loading raw JSON records.

API-mode transport (resilient HTTP, retry/backoff, and env-driven credential
resolution) lives in :mod:`requirement_intelligence.connectors.api_client`;
each concrete connector owns its own endpoint/pagination/auth details.

These helpers deliberately perform **no** canonical mapping or parsing. They
only fetch raw source records as ``list[dict]`` so the mapper layer,
consolidation engine, CP1 validation engine, and output writer remain agnostic
to whether records originated from FILE or API mode.

Concrete connectors keep their own ``fetch_raw_records()`` dispatch and the
``_fetch_from_file()`` / ``_fetch_from_api()`` helpers; those delegate to the
functions here (FILE) and to ``api_client`` (API) to avoid duplicating I/O.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from requirement_intelligence.connectors.connector_exceptions import (
    ConnectorConfigurationError,
    ConnectorConnectionError,
    ConnectorFetchError,
)

FILE_MODE = "FILE"
API_MODE = "API"
SUPPORTED_INPUT_MODES = (FILE_MODE, API_MODE)


def get_input_mode(source_config: dict[str, Any]) -> str:
    """Resolves the active input mode from the source-registry entry.

    The mode is read from the ``inputMode`` field as mandated by the registry
    contract.

    Args:
        source_config: Configuration entry from source-registry.json.

    Returns:
        str: The normalized (upper-cased) input mode.

    Raises:
        ConnectorConfigurationError: If ``inputMode`` is missing or not a string.
    """
    mode = source_config.get("inputMode")
    if not isinstance(mode, str) or not mode.strip():
        raise ConnectorConfigurationError(
            "Missing or invalid 'inputMode' in source configuration. "
            f"Expected one of {SUPPORTED_INPUT_MODES}."
        )
    return mode.strip().upper()


def resolve_input_path(source_config: dict[str, Any]) -> Path:
    """Resolves the configured FILE-mode input path.

    Args:
        source_config: Configuration entry from source-registry.json.

    Returns:
        Path: The configured input path.

    Raises:
        ConnectorConfigurationError: If ``inputPath`` is missing or empty.
    """
    raw_path = source_config.get("inputPath")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConnectorConfigurationError(
            "FILE mode requires a non-empty 'inputPath' in source configuration."
        )
    return Path(raw_path)


def validate_input_file(source_config: dict[str, Any]) -> bool:
    """Validates that the configured FILE-mode input path is readable.

    Args:
        source_config: Configuration entry from source-registry.json.

    Returns:
        bool: True if the input file exists and is readable.

    Raises:
        ConnectorConfigurationError: If ``inputPath`` is missing or empty.
        ConnectorConnectionError: If the file is missing or unreadable.
    """
    path = resolve_input_path(source_config)
    if not path.exists():
        raise ConnectorConnectionError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise ConnectorConnectionError(f"Input path is not a file: {path}")
    if not os.access(path, os.R_OK):
        raise ConnectorConnectionError(f"Input file is not readable: {path}")
    return True


def read_json_records(source_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Reads raw JSON records from the configured FILE-mode input path.

    This performs raw fetching only. It loads the JSON payload and coerces it
    into ``list[dict]``; it does **not** navigate source-specific structures or
    map fields. Extracting individual records from a nested payload is the
    responsibility of the parser layer.

    Args:
        source_config: Configuration entry from source-registry.json.

    Returns:
        list[dict[str, Any]]: Raw source records.

    Raises:
        ConnectorConfigurationError: If ``inputPath`` is missing or empty.
        ConnectorConnectionError: If the file is missing or unreadable.
        ConnectorFetchError: If the file cannot be read or parsed as JSON.
    """
    path = resolve_input_path(source_config)
    validate_input_file(source_config)
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConnectorFetchError(f"Failed to read raw records from {path}: {exc}") from exc
    return _coerce_to_records(data, path)


def _coerce_to_records(data: Any, path: Path) -> list[dict[str, Any]]:
    """Coerces a deserialized JSON payload into ``list[dict]``.

    A top-level JSON array is returned as-is; a top-level JSON object is wrapped
    as a single raw payload record. Any other shape is rejected. No
    source-specific field extraction is performed here.

    Args:
        data: The deserialized JSON payload.
        path: The source file path, used for error messages.

    Returns:
        list[dict[str, Any]]: Raw source records.

    Raises:
        ConnectorFetchError: If the payload is not a JSON object or array of
            objects.
    """
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        if all(isinstance(item, dict) for item in data):
            return data
        raise ConnectorFetchError(
            f"Expected a JSON array of objects in {path}, but found non-object elements."
        )
    raise ConnectorFetchError(
        f"Unsupported JSON payload in {path}: expected an object or array, "
        f"got {type(data).__name__}."
    )
