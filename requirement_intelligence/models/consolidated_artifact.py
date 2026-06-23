"""Consolidated Artifact — grouped view across sources.

A :class:`ConsolidatedArtifact` is produced by the consolidation step. It
gathers the individual :class:`~requirement_intelligence.models.source_artifact.SourceArtifact`
records that describe the *same* unit of work (typically a module / business
area) from different domains — functional intent, security findings and
quality signals — into one cohesive object.

This is the bridge between raw, per-record ingestion and the AI-ready
:class:`~requirement_intelligence.models.requirement_package.RequirementPackage`.
It captures *what belongs together* and *how risky it is*, without yet making
any AI / generative decisions.

Schema/shape only — the matching and risk-rollup logic lives in services.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.models.enums import RiskLevel
from requirement_intelligence.models.source_artifact import SourceArtifact
from shared.contracts.base import Schema


class ConsolidatedArtifact(Schema):
    """A set of related source artifacts grouped for one module / area.

    Artifacts are split by domain (``functional`` / ``security`` / ``quality``)
    so downstream consumers can reason about each concern independently while
    still seeing them as one consolidated unit. ``related_artifact_ids`` records
    cross-links to *other* consolidated or source artifacts that are relevant
    but not part of this group (e.g. a defect referenced by a story).

    Field names serialise as ``camelCase`` (``consolidatedId``,
    ``functionalArtifacts``, …); Python attributes stay ``snake_case``.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    consolidated_id: str = Field(
        ...,
        description="Platform-assigned stable identifier for this consolidation.",
    )

    module: str = Field(
        ...,
        description="The module / component this group of artifacts pertains to.",
    )
    business_area: str | None = Field(
        default=None,
        description="Broader business area or capability the module sits within.",
    )

    risk_level: RiskLevel = Field(
        ...,
        description="Normalised risk rating rolled up across the grouped artifacts.",
    )

    functional_artifacts: list[SourceArtifact] = Field(
        default_factory=list,
        description="Functional source artifacts (epics, stories, defects).",
    )
    security_artifacts: list[SourceArtifact] = Field(
        default_factory=list,
        description="Security source artifacts (DAST/SAST findings).",
    )
    quality_artifacts: list[SourceArtifact] = Field(
        default_factory=list,
        description="Code-quality source artifacts (e.g. SonarQube issues).",
    )

    related_artifact_ids: list[str] = Field(
        default_factory=list,
        description="Ids of related artifacts not contained in this group.",
    )

    consolidation_reason: str | None = Field(
        default=None,
        description="Why these artifacts were grouped (e.g. matching rule applied).",
    )
