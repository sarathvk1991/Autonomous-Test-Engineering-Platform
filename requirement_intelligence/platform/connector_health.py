"""Connector health check — operational readiness of the ingestion sources.

Answers one question per source: *could the pipeline read from you right now?*
It exercises **only** the connector layer. Consolidation, the LLM provider,
Normalization, Validation, CP1, and the Execution Package are never invoked, so
a health check costs nothing and produces no execution package.

Statuses
--------
``READY``
    FILE mode: the input file exists and is readable.
    API mode: configuration resolved and the endpoint answered.
``MISCONFIGURED``
    Configuration is absent or wrong — a missing ``inputPath``, an unset
    environment variable, an unsupported ``authType``. The operator must fix
    configuration; the source was never contacted.
``UNREACHABLE``
    Configuration is fine, but the source did not answer — the file is missing,
    or the endpoint refused the connection or timed out.

API-mode probing is deliberately **source-agnostic**: it issues one plain GET at
the connector's resolved base URL and treats *any* HTTP response as proof the
endpoint is up, recording the status code as detail. It never walks a vendor
REST path, never paginates, and never asserts a payload shape — that knowledge
belongs to the connectors. A ``401``/``403`` therefore reports ``READY`` with the
code surfaced, because the endpoint is demonstrably reachable; whether the
credential is *accepted* is reported, not judged, so the operator can tell a
down service apart from a bad token.

No credential value is ever logged, printed, or stored in a result.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from requirement_intelligence.connectors import api_client
from requirement_intelligence.connectors.connector_exceptions import (
    ConnectorConfigurationError,
    ConnectorConnectionError,
    ConnectorError,
)
from requirement_intelligence.registry.connector_registry import ConnectorRegistry
from requirement_intelligence.registry.execution_mode import API_MODE, FILE_MODE
from requirement_intelligence.registry.registry_exceptions import RegistryValidationError
from requirement_intelligence.registry.registry_loader import RegistryLoader

STATUS_READY = "READY"
STATUS_MISCONFIGURED = "MISCONFIGURED"
STATUS_UNREACHABLE = "UNREACHABLE"

# Probe timeout, in seconds. Short by design: a health check must return quickly
# even when a source is down, and it does no real work.
_PROBE_TIMEOUT_SECONDS = 10.0

# HTTP codes that prove the endpoint is up but rejected our credential.
_AUTH_STATUS = frozenset({401, 403})


@dataclass(frozen=True)
class ConnectorHealth:
    """The health of a single ingestion source."""

    source_id: str
    source_name: str
    status: str
    detail: str = ""
    duration_ms: float = 0.0

    @property
    def healthy(self) -> bool:
        """``True`` only when the source is ready to be read from."""
        return self.status == STATUS_READY


@dataclass(frozen=True)
class HealthReport:
    """The health of every enabled ingestion source."""

    execution_mode: str
    results: tuple[ConnectorHealth, ...]

    @property
    def healthy(self) -> bool:
        """``True`` when every enabled source is ``READY``."""
        return all(result.healthy for result in self.results)


def check_connector_health(
    execution_mode: str,
    *,
    base_dir: Path | None = None,
    loader: RegistryLoader | None = None,
) -> HealthReport:
    """Check every enabled source and return a :class:`HealthReport`.

    Never raises for an unhealthy source — an unreachable JIRA is a *result*,
    not an exception. Only a registry that cannot be loaded at all propagates.

    Args:
        execution_mode: The canonical ingestion mode, ``"FILE"`` or ``"API"``.
        base_dir: Directory FILE-mode ``inputPath`` values resolve against.
            Defaults to the current working directory.
        loader: Registry loader to inspect. Defaults to a loader bound to
            *execution_mode*.

    Returns:
        HealthReport: One :class:`ConnectorHealth` per enabled source, in
        registry priority order.

    Raises:
        RegistryValidationError: If the source registry itself cannot be loaded.
    """
    active = ConnectorRegistry(loader or RegistryLoader(execution_mode=execution_mode))
    root = Path.cwd() if base_dir is None else base_dir

    results = [
        _check_source(active, source_config, execution_mode, root)
        for source_config in active.loader.get_enabled_sources()
    ]
    return HealthReport(execution_mode=execution_mode, results=tuple(results))


def _check_source(
    registry: ConnectorRegistry,
    source_config: dict[str, Any],
    execution_mode: str,
    base_dir: Path,
) -> ConnectorHealth:
    """Check one source, converting every failure into a status."""
    source_id = str(source_config.get("sourceId", "?"))
    source_name = str(source_config.get("sourceName", source_id))
    start = time.monotonic()

    def elapsed() -> float:
        return round((time.monotonic() - start) * 1000.0, 2)

    try:
        connector = registry.create_connector(source_config)
    except RegistryValidationError as exc:
        return ConnectorHealth(source_id, source_name, STATUS_MISCONFIGURED, str(exc), elapsed())

    if execution_mode == FILE_MODE:
        return _check_file_source(connector, source_id, source_name, base_dir, elapsed)
    if execution_mode == API_MODE:
        return _check_api_source(connector, source_config, source_id, source_name, elapsed)

    return ConnectorHealth(
        source_id,
        source_name,
        STATUS_MISCONFIGURED,
        f"Unsupported execution mode '{execution_mode}'.",
        elapsed(),
    )


def _check_file_source(
    connector: Any,
    source_id: str,
    source_name: str,
    base_dir: Path,
    elapsed: Any,
) -> ConnectorHealth:
    """Verify the connector's FILE-mode input is present and readable.

    Delegates entirely to the connector's own ``validate_connection()``, which is
    its declared availability contract. Because connectors resolve ``inputPath``
    relative to the working directory, the check runs from *base_dir*.
    """
    from contextlib import chdir

    try:
        with chdir(base_dir):
            connector.validate_connection()
    except ConnectorConfigurationError as exc:
        return ConnectorHealth(source_id, source_name, STATUS_MISCONFIGURED, str(exc), elapsed())
    except ConnectorConnectionError as exc:
        return ConnectorHealth(source_id, source_name, STATUS_UNREACHABLE, str(exc), elapsed())
    except ConnectorError as exc:
        return ConnectorHealth(source_id, source_name, STATUS_UNREACHABLE, str(exc), elapsed())

    path = base_dir / str(connector.source_config.get("inputPath", ""))
    return ConnectorHealth(source_id, source_name, STATUS_READY, str(path), elapsed())


def _check_api_source(
    connector: Any,
    source_config: dict[str, Any],
    source_id: str,
    source_name: str,
    elapsed: Any,
) -> ConnectorHealth:
    """Resolve API configuration, then probe the base URL for reachability."""
    try:
        connector.validate_connection()
    except ConnectorConfigurationError as exc:
        return ConnectorHealth(source_id, source_name, STATUS_MISCONFIGURED, str(exc), elapsed())
    except ConnectorError as exc:
        return ConnectorHealth(source_id, source_name, STATUS_UNREACHABLE, str(exc), elapsed())

    connection = source_config.get("connection")
    if not isinstance(connection, dict):
        return ConnectorHealth(
            source_id,
            source_name,
            STATUS_MISCONFIGURED,
            "API mode requires a 'connection' block in source-registry.json.",
            elapsed(),
        )

    try:
        base_url = api_client.resolve_secret_field(
            connection, direct_key="baseUrl", env_key="baseUrlEnv", source_id=source_id
        )
    except ConnectorConfigurationError as exc:
        return ConnectorHealth(source_id, source_name, STATUS_MISCONFIGURED, str(exc), elapsed())

    return _probe_endpoint(base_url, source_id, source_name, elapsed)


def _probe_endpoint(
    base_url: str,
    source_id: str,
    source_name: str,
    elapsed: Any,
) -> ConnectorHealth:
    """Issue one unauthenticated GET at *base_url* and classify the outcome."""
    try:
        with httpx.Client(timeout=_PROBE_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = client.get(base_url)
    except httpx.TimeoutException:
        return ConnectorHealth(
            source_id,
            source_name,
            STATUS_UNREACHABLE,
            f"No response from {base_url} within {_PROBE_TIMEOUT_SECONDS:.0f}s.",
            elapsed(),
        )
    except httpx.RequestError as exc:
        return ConnectorHealth(
            source_id,
            source_name,
            STATUS_UNREACHABLE,
            f"Cannot reach {base_url}: {type(exc).__name__}.",
            elapsed(),
        )

    if response.status_code in _AUTH_STATUS:
        detail = (
            f"{base_url} reachable (HTTP {response.status_code}); "
            "endpoint is up but did not accept an unauthenticated probe."
        )
    else:
        detail = f"{base_url} reachable (HTTP {response.status_code})."
    return ConnectorHealth(source_id, source_name, STATUS_READY, detail, elapsed())


__all__ = [
    "STATUS_MISCONFIGURED",
    "STATUS_READY",
    "STATUS_UNREACHABLE",
    "ConnectorHealth",
    "HealthReport",
    "check_connector_health",
]
