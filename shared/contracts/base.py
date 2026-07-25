"""Shared contracts: base schema type.

Contracts are the stable interfaces layers depend on instead of each other's
concrete implementations. This keeps the modular monolith decoupled: a layer
imports a *contract*, not another layer's internals.
"""

from __future__ import annotations

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
