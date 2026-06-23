"""Requirement Package — the AI-ready output of Requirement Intelligence.

A :class:`RequirementPackage` is the final, distilled artifact of the
Requirement Intelligence Layer. Where a
:class:`~requirement_intelligence.models.consolidated_artifact.ConsolidatedArtifact`
still carries raw per-record detail, a package expresses the *intent* for a
module as concise, human-readable requirement statements grouped by concern.

It is deliberately a flat, text-centric structure: it is the payload that later
phases send to Azure OpenAI for test generation, so it favours clear natural
language over nested vendor data. Heavy provenance is referenced (not embedded)
through ``supporting_artifacts``.

Schema/shape only — package assembly logic lives in services.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema


class RequirementPackage(Schema):
    """An AI-ready, per-module package of requirement statements.

    The three requirement lists separate concerns so a generator can target
    each independently:

    * ``requirements`` — functional behaviour the module must exhibit,
    * ``security_requirements`` — security expectations derived from findings,
    * ``quality_requirements`` — quality / maintainability expectations.

    ``supporting_artifacts`` holds the ids of the source / consolidated
    artifacts this package was derived from, preserving traceability without
    bloating the prompt payload.

    Field names serialise as ``camelCase`` (``packageId``,
    ``securityRequirements``, …); Python attributes stay ``snake_case``.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    package_id: str = Field(
        ...,
        description="Platform-assigned stable identifier for this package.",
    )

    module: str = Field(
        ...,
        description="The module / component this package describes.",
    )

    business_goal: str | None = Field(
        default=None,
        description="The business objective the module serves, in plain language.",
    )

    requirements: list[str] = Field(
        default_factory=list,
        description="Functional requirement statements for the module.",
    )
    security_requirements: list[str] = Field(
        default_factory=list,
        description="Security requirement statements derived from findings.",
    )
    quality_requirements: list[str] = Field(
        default_factory=list,
        description="Quality / maintainability requirement statements.",
    )

    risk_summary: str | None = Field(
        default=None,
        description="Concise narrative of the module's overall risk posture.",
    )

    supporting_artifacts: list[str] = Field(
        default_factory=list,
        description="Ids of source/consolidated artifacts backing this package.",
    )
