"""Shared contracts: base schema type and cross-layer protocols.

Contracts are the stable interfaces layers depend on instead of each other's
concrete implementations. This keeps the modular monolith decoupled: a layer
imports a *contract*, not another layer's internals.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    """Base class for all platform DTOs / data models.

    Centralises pydantic configuration (immutability, strict-ish parsing,
    enum-by-value serialisation) so every model behaves consistently.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        use_enum_values=True,
        populate_by_name=True,
    )


@runtime_checkable
class SourceConnector(Protocol):
    """Contract every source connector must satisfy.

    The connector framework and Source Registry depend on this protocol, not on
    any concrete connector, so new sources can be added without touching the
    orchestration code.
    """

    @property
    def source(self) -> str:
        """Identifier of the source system this connector serves."""
        ...

    def health_check(self) -> bool:
        """Return ``True`` when the source system is reachable and authorised."""
        ...

    def fetch(self, **query: Any) -> list[dict[str, Any]]:
        """Fetch raw records from the source system for the given query."""
        ...
