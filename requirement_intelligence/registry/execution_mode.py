"""Canonical execution-mode selection for source ingestion.

The platform ingests source records in exactly one of two modes:

``FILE``
    Connectors read previously exported artifacts from disk (``inputPath``).
``API``
    Connectors fetch records live from the source system's REST API.

The mode is selected **once, globally**, from the ``EXECUTION_MODE`` environment
variable and defaults to ``FILE``. This module is the *only* place that reads
that variable and the only place that decides the mode; the
:class:`~requirement_intelligence.registry.registry_loader.RegistryLoader` is
the only place that applies it, by stamping the resolved mode onto every enabled
source configuration.

Connectors therefore continue to read ``inputMode`` from the configuration they
are handed, exactly as before, and remain unaware of how it was chosen. No
connector, mapper, consolidation, analysis, validation, CP1, or execution-package
component knows which mode produced the records it is processing.

This module owns mode *selection* only. It performs no I/O, contacts no source,
and validates no credentials — that is the startup validator's responsibility.

Note on naming
--------------
``EXECUTION_MODE`` here means the **ingestion** mode (FILE vs API). It is
unrelated to ``manifest.json``'s ``executionMode`` field (``dry-run`` vs
``live``, the frozen Execution Package contract) and to
``platform_metadata.PLATFORM_EXECUTION_MODE`` (the deployment topology).
"""

from __future__ import annotations

import os

from requirement_intelligence.connectors.connector_io import (
    API_MODE,
    FILE_MODE,
    SUPPORTED_INPUT_MODES,
)
from requirement_intelligence.registry.registry_exceptions import RegistryValidationError

#: Name of the single environment variable that selects the ingestion mode.
EXECUTION_MODE_ENV_VAR = "EXECUTION_MODE"

#: The mode used when ``EXECUTION_MODE`` is unset or empty.
DEFAULT_EXECUTION_MODE = FILE_MODE

#: The modes the platform accepts, in canonical (upper-case) form.
SUPPORTED_EXECUTION_MODES = SUPPORTED_INPUT_MODES


def resolve_execution_mode(environ: dict[str, str] | None = None) -> str:
    """Return the canonical ingestion mode for this process.

    Args:
        environ: Environment mapping to read from. Defaults to ``os.environ``.
            Supplying an explicit mapping keeps the resolver testable without
            mutating process state.

    Returns:
        str: ``"FILE"`` or ``"API"``. Returns :data:`DEFAULT_EXECUTION_MODE`
        when ``EXECUTION_MODE`` is unset, empty, or whitespace-only.

    Raises:
        RegistryValidationError: If ``EXECUTION_MODE`` is set to any value other
            than ``FILE`` or ``API`` (case-insensitive). Failing here rather than
            silently defaulting means a typo such as ``EXECUTION_MODE=api-mode``
            is reported before any source is contacted.
    """
    source = os.environ if environ is None else environ
    raw = source.get(EXECUTION_MODE_ENV_VAR)
    if raw is None or not raw.strip():
        return DEFAULT_EXECUTION_MODE

    mode = raw.strip().upper()
    if mode not in SUPPORTED_EXECUTION_MODES:
        supported = ", ".join(SUPPORTED_EXECUTION_MODES)
        raise RegistryValidationError(
            f"{EXECUTION_MODE_ENV_VAR}={raw.strip()!r} is not a supported execution mode. "
            f"Set {EXECUTION_MODE_ENV_VAR} to one of: {supported}. "
            f"Leave it unset to use the default ({DEFAULT_EXECUTION_MODE})."
        )
    return mode


__all__ = [
    "API_MODE",
    "DEFAULT_EXECUTION_MODE",
    "EXECUTION_MODE_ENV_VAR",
    "FILE_MODE",
    "SUPPORTED_EXECUTION_MODES",
    "resolve_execution_mode",
]
