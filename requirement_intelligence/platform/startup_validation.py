"""Startup validation — fail fast, before any pipeline stage runs.

This module answers one operational question: *is this process configured well
enough to execute?* It is invoked once, before the Connector Registry executes,
and it either returns a report of passing checks or raises
:class:`StartupValidationError` carrying every problem it found.

What is validated
-----------------
Both modes
    The source registry parses and declares at least one enabled source; the
    governed prompt registry composes (verifying each template's SHA-256 against
    the prompt manifest); and every enabled source passes its own connector's
    ``validate_connection()``.

FILE mode
    ``validate_connection()`` proves the source's ``inputPath`` exists and is
    readable.

API mode
    ``validate_connection()`` proves every credential the connector actually
    requires resolves from the environment, and this module additionally checks
    that the configured base URL is a syntactically valid ``http(s)`` endpoint.

Each connector is the sole authority on what *it* needs — JIRA's project key is
optional while SonarQube's is mandatory — so this module never re-declares those
requirements. It delegates to the connector's declared availability contract and
reports the result. A static table of required fields here would silently drift
from the connectors it claims to describe.

What is *not* validated
-----------------------
In API mode no network call is made and no credential is checked against a live
source — that is :mod:`connector_health`'s job. Configuration resolution alone is
fast and side-effect free.

Errors raised here are **expected configuration errors**, not defects. Callers
render :attr:`StartupValidationError.failures` as plain operator-facing text; a
Python traceback is never an acceptable response to a missing environment
variable. Secrets are never read into the report — only the *names* of the
environment variables that are missing.
"""

from __future__ import annotations

from contextlib import chdir
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from requirement_intelligence.connectors.connector_exceptions import ConnectorError
from requirement_intelligence.registry.connector_registry import ConnectorRegistry
from requirement_intelligence.registry.execution_mode import FILE_MODE
from requirement_intelligence.registry.registry_exceptions import RegistryValidationError
from requirement_intelligence.registry.registry_loader import RegistryLoader

_VALID_URL_SCHEMES = ("http", "https")


class StartupValidationError(Exception):
    """Raised when configuration is insufficient to execute the pipeline.

    Carries every failure found, so the operator fixes all of them in one pass
    rather than rediscovering them one run at a time.
    """

    def __init__(self, failures: list[str]) -> None:
        """Create the error from the collected, operator-facing failure lines."""
        self.failures = failures
        super().__init__("; ".join(failures))


@dataclass(frozen=True)
class StartupCheck:
    """One named configuration check and its outcome."""

    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class StartupReport:
    """The complete result of a startup validation pass."""

    execution_mode: str
    checks: tuple[StartupCheck, ...]

    @property
    def failures(self) -> tuple[StartupCheck, ...]:
        """Return only the checks that did not pass."""
        return tuple(check for check in self.checks if not check.passed)


def validate_startup(
    execution_mode: str,
    *,
    base_dir: Path | None = None,
    loader: RegistryLoader | None = None,
) -> StartupReport:
    """Validate configuration for *execution_mode* and return the report.

    Args:
        execution_mode: The canonical ingestion mode, ``"FILE"`` or ``"API"``.
        base_dir: Directory that FILE-mode ``inputPath`` values are resolved
            against. Connectors resolve them relative to the current working
            directory, so callers pass the directory they will execute from.
            Defaults to the current working directory.
        loader: Registry loader to validate. Defaults to a loader bound to
            *execution_mode*. The connector registry is built from it here, so a
            registry that cannot even be constructed is reported as a check
            failure rather than propagating.

    Returns:
        StartupReport: The passing checks, when every check passed.

    Raises:
        StartupValidationError: If any check failed. The exception's ``failures``
            list contains one actionable line per problem.
    """
    root = Path.cwd() if base_dir is None else base_dir
    checks: list[StartupCheck] = []

    active, sources, registry_check = _load_registry(loader, execution_mode)
    checks.append(registry_check)
    checks.append(_check_prompt_registry())

    if active is not None:
        for source_config in sources:
            checks.append(_check_source(active, source_config, execution_mode, root))

    report = StartupReport(execution_mode=execution_mode, checks=tuple(checks))
    if report.failures:
        raise StartupValidationError([f"{c.name}: {c.detail}" for c in report.failures])
    return report


# --------------------------------------------------------------------------- #
# Individual checks
# --------------------------------------------------------------------------- #
def _load_registry(
    loader: RegistryLoader | None, execution_mode: str
) -> tuple[ConnectorRegistry | None, list[dict[str, Any]], StartupCheck]:
    """Load the source registry and confirm it enables at least one source."""
    try:
        active = ConnectorRegistry(loader or RegistryLoader(execution_mode=execution_mode))
        sources = active.loader.get_enabled_sources()
    except (RegistryValidationError, ConnectorError) as exc:
        return None, [], StartupCheck("Source Registry", False, str(exc))

    if not sources:
        return (
            None,
            [],
            StartupCheck(
                "Source Registry",
                False,
                'No source is enabled. Set "enabled": true for at least one entry in '
                "requirement_intelligence/config/source-registry.json.",
            ),
        )
    names = ", ".join(_label(source) for source in sources)
    return (
        active,
        sources,
        StartupCheck("Source Registry", True, f"{len(sources)} enabled ({names})"),
    )


def _check_prompt_registry() -> StartupCheck:
    """Validate that the governed prompt registry composes and verifies."""
    from requirement_intelligence.prompts.framework.composition import build_prompt_registry
    from requirement_intelligence.prompts.framework.prompt_exceptions import (
        PromptFrameworkError,
    )

    try:
        registry = build_prompt_registry()
    except PromptFrameworkError as exc:
        return StartupCheck("Prompt Registry", False, str(exc))
    return StartupCheck("Prompt Registry", True, f"{registry.count()} governed prompt(s), sealed")


def _check_source(
    registry: ConnectorRegistry,
    source_config: dict[str, Any],
    execution_mode: str,
    base_dir: Path,
) -> StartupCheck:
    """Validate one source through its own connector's availability contract."""
    label = _label(source_config)
    file_mode = execution_mode == FILE_MODE
    name = f"Input File [{label}]" if file_mode else f"API Configuration [{label}]"

    try:
        connector = registry.create_connector(source_config)
    except RegistryValidationError as exc:
        return StartupCheck(name, False, str(exc))

    try:
        if execution_mode == FILE_MODE:
            with chdir(base_dir):
                connector.validate_connection()
        else:
            connector.validate_connection()
    except ConnectorError as exc:
        return StartupCheck(name, False, str(exc))

    if execution_mode == FILE_MODE:
        return StartupCheck(name, True, str(base_dir / str(source_config.get("inputPath", ""))))

    problem = _endpoint_problem(source_config, label)
    if problem:
        return StartupCheck(name, False, problem)
    return StartupCheck(name, True, "credentials resolved; endpoint configured")


def _endpoint_problem(source_config: dict[str, Any], label: str) -> str:
    """Return a message describing a malformed base URL, or ``""`` when valid.

    The connector proves the base URL *resolves*; this proves it is a URL. A
    value such as ``localhost:9000`` resolves fine and then fails deep inside the
    HTTP client, which is exactly the class of error startup validation exists to
    surface early.
    """
    import os

    connection = source_config.get("connection")
    if not isinstance(connection, dict):
        return ""

    env_name = str(connection.get("baseUrlEnv", "")).strip()
    direct = connection.get("baseUrl")
    raw = direct.strip() if isinstance(direct, str) and direct.strip() else ""
    if not raw and env_name:
        raw = os.environ.get(env_name, "").strip()

    parsed = urlparse(raw)
    if parsed.scheme in _VALID_URL_SCHEMES and parsed.netloc:
        return ""

    origin = env_name or "connection.baseUrl"
    schemes = " or ".join(_VALID_URL_SCHEMES)
    return (
        f"{origin} is not a valid endpoint URL for '{label}'. "
        f"Expected an absolute {schemes} URL (e.g. https://host:port)."
    )


def _label(source_config: dict[str, Any]) -> str:
    """Return the human-readable name of a source."""
    return str(source_config.get("sourceName", source_config.get("sourceId", "?")))


__all__ = [
    "StartupCheck",
    "StartupReport",
    "StartupValidationError",
    "validate_startup",
]
