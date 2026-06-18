"""Connector Framework — base class for all source connectors.

A connector encapsulates *how* to talk to one source system (auth, fetch,
pagination). Concrete connectors (Jira, SonarQube, OWASP ZAP) subclass
``BaseConnector`` and are registered in the Source Registry. Downstream code
depends on the :class:`shared.contracts.base.SourceConnector` protocol, never on
a concrete connector — that is what makes new sources pluggable.

This is the framework contract only; fetch logic is implemented per connector.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from shared.enums.base import SourceSystem


class BaseConnector(ABC):
    """Abstract base every source connector must extend."""

    #: The source system this connector serves. Set by each subclass.
    source: SourceSystem

    @abstractmethod
    def health_check(self) -> bool:
        """Return ``True`` if the source system is reachable and authorised."""
        raise NotImplementedError

    @abstractmethod
    def fetch(self, **query: Any) -> list[dict[str, Any]]:
        """Fetch raw records from the source system for the given query.

        Returns raw payloads; conversion to the canonical model is the
        responsibility of the matching parser.
        """
        raise NotImplementedError
