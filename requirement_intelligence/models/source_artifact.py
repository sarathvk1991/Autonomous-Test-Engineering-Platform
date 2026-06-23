"""Source Artifact — the atomic unit of the Canonical Data Model.

A :class:`SourceArtifact` is the source-agnostic representation of a *single*
record fetched from any upstream system. Every connector + parser (JIRA,
OWASP ZAP, SonarQube today; HP ALM, Azure DevOps, test generators and
execution engines tomorrow) normalises its raw payload into this one shape, so
the rest of the platform never depends on a vendor-specific schema.

This module defines schema/shape only. Transformation, scoring and grouping
logic live in parsers and services, not here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.models.enums import (
    SourceCategory,
    SourceSystem,
    SourceType,
)
from shared.contracts.base import Schema


class SourceArtifact(Schema):
    """A single normalised record from any source system.

    Examples of what one instance represents:

    * a JIRA Epic, Story or Defect,
    * an OWASP ZAP alert (DAST finding),
    * a SonarQube issue (SAST / quality finding).

    Vendor-specific identity is preserved through ``source_system`` +
    ``source_record_id`` (so the original record is always traceable), while
    ``artifact_id`` is the platform's own stable identifier. Fields that do not
    apply to a given source are left ``None`` rather than invented; anything
    source-specific that has no canonical home is retained in ``metadata`` for
    auditing and downstream enrichment.

    Field names serialise as ``camelCase`` (e.g. ``artifactId``,
    ``sourceSystem``) to match the platform's JSON contract, while Python
    attributes stay ``snake_case``; either form is accepted on input
    (``populate_by_name``).
    """

    model_config = ConfigDict(alias_generator=to_camel)

    # --- Identity & provenance ------------------------------------------------
    artifact_id: str = Field(
        ...,
        description="Platform-assigned stable identifier for this artifact.",
    )
    source_system: SourceSystem = Field(
        ...,
        description="Originating system the record was ingested from (enum).",
    )
    source_record_id: str = Field(
        ...,
        description="Native record id within the source system (for traceability).",
    )

    # --- Classification -------------------------------------------------------
    source_category: SourceCategory = Field(
        ...,
        description="Lifecycle domain of the artifact (functional/security/…).",
    )
    source_type: SourceType = Field(
        ...,
        description="Concrete record type (epic/story/defect/dast/sast/…).",
    )

    # --- Human-readable content ----------------------------------------------
    title: str = Field(
        ...,
        description="Short human-readable summary of the artifact.",
    )
    description: str | None = Field(
        default=None,
        description="Full description / body text, when provided by the source.",
    )

    # --- Normalised state ----------------------------------------------------
    status: str | None = Field(
        default=None,
        description="Source status as a string (e.g. 'Open', 'Done', 'Resolved').",
    )
    priority: str | None = Field(
        default=None,
        description="Source priority as a string (e.g. 'High', 'Major').",
    )
    severity: str | None = Field(
        default=None,
        description="Source severity as a string (e.g. 'Critical', 'Blocker').",
    )

    # --- Location / context ---------------------------------------------------
    component: str | None = Field(
        default=None,
        description="Owning component, module or project the artifact belongs to.",
    )
    location: str | None = Field(
        default=None,
        description="Physical location, e.g. file path:line for SAST/DAST findings.",
    )
    url: str | None = Field(
        default=None,
        description="Deep link back to the artifact in its source system.",
    )

    # --- Labels & timestamps --------------------------------------------------
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form labels / tags carried over from the source.",
    )
    created_at: datetime | None = Field(
        default=None,
        description=(
            "Creation timestamp. Accepts ISO-8601 strings on input and "
            "serialises back to ISO-8601; enables age/SLA/trend metrics."
        ),
    )
    updated_at: datetime | None = Field(
        default=None,
        description=(
            "Last-updated timestamp. Accepts ISO-8601 strings on input and "
            "serialises back to ISO-8601; enables age/SLA/trend metrics."
        ),
    )

    # --- Escape hatch ---------------------------------------------------------
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Source-specific fields with no canonical home, kept verbatim.",
    )
