"""The :class:`OrganizationalMemorySummary` and :class:`OrganizationalMemoryMetrics`
— the headline and deterministic numeric roll-up for one Organizational Memory
build.

Both are pure data containers, mirroring ``ImprovementSummary``/
``ImprovementMetrics`` (ADR-0022) and ``KnowledgeSummary``/``KnowledgeMetrics``
(ADR-0023): recorded values, never model-internal calculations. Nothing is
computed here — a future engine (CAP-085B, reserved) computes every field
exactly once from already-finished collaborators.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.organizational_memory.identity import (
    OrganizationalMemoryPolicyId,
    OrganizationalMemoryPolicyVersion,
)
from shared.contracts.base import Schema


class OrganizationalMemorySummary(Schema):
    """The governed headline for one Organizational Memory build. A pure data container.

    Carries only the governing policy's identity/version (mirrors
    ``KnowledgeSummary.policy_version``); this is a reference, never a
    duplicate policy shape.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    policy_id: OrganizationalMemoryPolicyId = Field(..., description="Governing policy identity.")
    policy_version: OrganizationalMemoryPolicyVersion = Field(
        ..., description="Governing policy version."
    )

    total_experiences: int = Field(..., ge=0, description="Total experiences recorded.")
    total_lessons: int = Field(..., ge=0, description="Total lessons recorded.")
    total_best_practices: int = Field(..., ge=0, description="Total best practices recorded.")
    total_promotions: int = Field(..., ge=0, description="Total promotion records recorded.")

    headline: str = Field(..., min_length=1, description="One-line deterministic build summary.")


class OrganizationalMemoryMetrics(Schema):
    """Deterministic numeric roll-ups for one Organizational Memory build. Data only.

    Every count is a recorded value, never a model-internal calculation — a
    future engine (CAP-085B, reserved) computes each exactly once.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    experience_count: int = Field(..., ge=0, description="Total number of experiences.")
    lesson_count: int = Field(..., ge=0, description="Total number of lessons.")
    best_practice_count: int = Field(..., ge=0, description="Total number of best practices.")
    promotion_count: int = Field(..., ge=0, description="Total number of promotion records.")
    active_count: int = Field(
        ..., ge=0, description="Number of knowledge objects currently ACTIVE."
    )
    deprecated_count: int = Field(
        ..., ge=0, description="Number of knowledge objects currently DEPRECATED."
    )
    historical_count: int = Field(
        ..., ge=0, description="Number of knowledge objects currently HISTORICAL."
    )
    archived_count: int = Field(
        ..., ge=0, description="Number of knowledge objects currently ARCHIVED."
    )
