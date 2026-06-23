"""Mapper contract for normalising raw source records into the canonical model.

A *mapper* is the thin, source-specific transformation step that sits between a
connector (which fetches raw vendor records) and the rest of the platform
(which only ever speaks the Canonical Data Model). Each mapper takes the raw
``list[dict]`` a connector produced and returns a flat ``list[SourceArtifact]``.

Mappers are deliberately narrow: they translate *shape*, nothing more. They do
**not** consolidate records, call Azure OpenAI, build requirement packages, or
apply business rules — those concerns live in later platform layers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from requirement_intelligence.models.source_artifact import SourceArtifact


class MapperError(Exception):
    """Base class for errors raised while mapping raw records."""


class UnsupportedRecordError(MapperError):
    """Raised when a raw record cannot be mapped to a canonical artifact.

    Typically signals an unexpected/unsupported record type, so the caller can
    fail loudly rather than silently dropping or guessing at data.
    """


class BaseMapper(ABC):
    """Abstract contract every source mapper must satisfy.

    Implementations transform raw connector output for one source system into
    canonical :class:`SourceArtifact` instances. The contract is intentionally
    a single method so connectors and orchestration can depend on the mapper
    abstraction rather than any concrete vendor mapper.
    """

    @abstractmethod
    def map(self, raw_records: list[dict[str, Any]]) -> list[SourceArtifact]:
        """Map raw source records into canonical artifacts.

        Args:
            raw_records: Raw records as returned by the source connector.

        Returns:
            A flat list of :class:`SourceArtifact`, one per source record.

        Raises:
            MapperError: If a record cannot be mapped to the canonical model.
        """
        raise NotImplementedError
