"""Source Parsers — base contract.

A parser transforms a connector's raw, source-specific payload into the shared
:class:`~requirement_intelligence.models.canonical_requirement.CanonicalRequirement`.
One parser per source keeps source quirks isolated from the rest of the layer.
Concrete parsers (Jira/SonarQube/ZAP) subclass ``BaseParser``. Logic deferred.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from requirement_intelligence.models.canonical_requirement import CanonicalRequirement


class BaseParser(ABC):
    """Abstract base for all source parsers."""

    @abstractmethod
    def parse(self, raw: dict[str, Any]) -> CanonicalRequirement:
        """Convert a single raw source record into a canonical requirement."""
        raise NotImplementedError

    def parse_many(self, raws: list[dict[str, Any]]) -> list[CanonicalRequirement]:
        """Convert a batch of raw records. Override for source-specific batching."""
        return [self.parse(raw) for raw in raws]
