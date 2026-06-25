"""Consolidation Engine — groups related source artifacts deterministically.

The engine sits between ingestion (Task 7) and the future Azure OpenAI layer:

    List[SourceArtifact]  ->  ConsolidationEngine  ->  List[ConsolidatedArtifact]

It applies only the deterministic heuristics in
:mod:`requirement_intelligence.consolidation.consolidation_rules`. By design it
does **not** call connectors or mappers, read source files, call Azure OpenAI,
perform CP1 validation, or build a RequirementPackage. It only reorganises the
artifacts it is handed into explainable groups.
"""

from __future__ import annotations

from requirement_intelligence.consolidation.consolidation_exceptions import (
    ConsolidationInputError,
)
from requirement_intelligence.consolidation.consolidation_rules import (
    GroupingKey,
    build_consolidated_id,
    build_reason,
    derive_grouping_key,
    rollup_risk,
)
from requirement_intelligence.models.consolidated_artifact import ConsolidatedArtifact
from requirement_intelligence.models.enums import SourceCategory
from requirement_intelligence.models.source_artifact import SourceArtifact


class ConsolidationEngine:
    """Groups :class:`SourceArtifact` records into :class:`ConsolidatedArtifact`."""

    def consolidate(self, artifacts: list[SourceArtifact]) -> list[ConsolidatedArtifact]:
        """Groups artifacts into consolidated units using deterministic rules.

        Artifacts are bucketed by the Phase-1 grouping cascade (component, then
        shared tag, then endpoint, then risk category). Groups are returned in
        the order they were first encountered, so the output is deterministic
        for a given input ordering.

        Args:
            artifacts: The source artifacts to consolidate.

        Returns:
            list[ConsolidatedArtifact]: One consolidated artifact per group.

        Raises:
            ConsolidationInputError: If ``artifacts`` is not a list of
                :class:`SourceArtifact` instances.
        """
        if not isinstance(artifacts, list):
            raise ConsolidationInputError(
                f"Expected a list of SourceArtifact, got: {type(artifacts).__name__}"
            )
        if not artifacts:
            return []

        # Preserve first-seen ordering of groups for deterministic output.
        grouped: dict[tuple[str, str], tuple[GroupingKey, list[SourceArtifact]]] = {}
        for artifact in artifacts:
            if not isinstance(artifact, SourceArtifact):
                raise ConsolidationInputError(
                    f"Expected SourceArtifact, got: {type(artifact).__name__}"
                )
            key = derive_grouping_key(artifact)
            identity = (key.dimension.value, key.value)
            if identity not in grouped:
                grouped[identity] = (key, [])
            grouped[identity][1].append(artifact)

        return [self._build(key, members) for key, members in grouped.values()]

    def _build(
        self, key: GroupingKey, members: list[SourceArtifact]
    ) -> ConsolidatedArtifact:
        """Builds a single :class:`ConsolidatedArtifact` from a grouped key."""
        functional: list[SourceArtifact] = []
        security: list[SourceArtifact] = []
        quality: list[SourceArtifact] = []

        for artifact in members:
            category = artifact.source_category
            if category == SourceCategory.FUNCTIONAL:
                functional.append(artifact)
            elif category == SourceCategory.SECURITY:
                security.append(artifact)
            elif category == SourceCategory.QUALITY:
                quality.append(artifact)
            else:
                raise ConsolidationInputError(
                    f"Unsupported source category for Phase-1 consolidation: "
                    f"'{category}' on artifact '{artifact.artifact_id}'"
                )

        return ConsolidatedArtifact(
            consolidated_id=build_consolidated_id(key),
            module=key.label,
            business_area=None,
            risk_level=rollup_risk(members),
            functional_artifacts=functional,
            security_artifacts=security,
            quality_artifacts=quality,
            # Cross-group relations (artifacts relevant but not in this group) are
            # not established by the Phase-1 single-pass heuristic.
            # TODO(phase-1): Populate related_artifact_ids once cross-group
            # relationship detection (e.g. a defect referenced by a story) exists.
            related_artifact_ids=[],
            consolidation_reason=build_reason(key),
        )
