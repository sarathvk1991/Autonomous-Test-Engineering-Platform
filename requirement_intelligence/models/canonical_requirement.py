"""Canonical Requirement Model.

The single, source-agnostic representation of a requirement. Every source
connector + parser produces this shape, so all downstream components
(consolidation, classification, AI analysis, CP1 validation, reporting) operate
on one stable contract regardless of origin (Jira, SonarQube, OWASP ZAP, …).

Only the schema/shape is defined here — transformation logic lives in parsers
and services.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from shared.contracts.base import Schema
from shared.enums.base import (
    RequirementPriority,
    RequirementStatus,
    RequirementType,
    SourceSystem,
)


class SourceRef(Schema):
    """Provenance pointer back to the originating record in a source system."""

    system: SourceSystem
    external_id: str
    url: str | None = None


class CanonicalRequirement(Schema):
    """Source-agnostic requirement consumed by every downstream component."""

    id: str
    title: str
    description: str
    source: SourceRef

    requirement_type: RequirementType = RequirementType.UNKNOWN
    priority: RequirementPriority = RequirementPriority.MEDIUM
    status: RequirementStatus = RequirementStatus.INGESTED

    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Free-form, source-specific fields preserved for traceability/auditing.
    raw_metadata: dict[str, str] = Field(default_factory=dict)
