"""Source Registry.

Central catalogue mapping each :class:`~shared.enums.base.SourceSystem` to its
registered connector (and parser). The workflow asks the registry for the
connectors to run, so enabling/disabling a source is a configuration concern —
not a code change in the orchestration. Logic deferred.
"""

from __future__ import annotations

from shared.contracts.base import SourceConnector
from shared.enums.base import SourceSystem


class SourceRegistry:
    """Registry of available source connectors, keyed by source system."""

    def __init__(self) -> None:
        self._connectors: dict[SourceSystem, SourceConnector] = {}

    def register(self, connector: SourceConnector) -> None:
        """Register a connector under its declared source system."""
        raise NotImplementedError

    def get(self, source: SourceSystem) -> SourceConnector:
        """Return the connector registered for ``source``."""
        raise NotImplementedError

    def active_sources(self) -> list[SourceSystem]:
        """Return the source systems with a registered, enabled connector."""
        raise NotImplementedError
