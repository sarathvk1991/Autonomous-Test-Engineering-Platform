"""Unit tests for the canonical Requirement Enhancement models (CAP-081A).

All models are frozen, tuple-backed, camelCase, and compute nothing — every value in
these tests is supplied directly, never derived, because no engine exists yet. The
tests assert immutability, serialization round-trips, and the cross-referential
integrity invariants the validators enforce (ADR-0018 §D4).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.enhancement.identity import (
    EnhancedRequirementId,
    EnhancementFrameworkVersion,
    EnhancementPolicyId,
    EnhancementPolicyVersion,
    RelationshipGraphId,
    RequirementEnhancementResultId,
    RequirementObservationId,
)
from requirement_intelligence.enhancement.models import (
    EnhancedRequirement,
    EnhancementFinding,
    EnhancementInputReference,
    EnhancementInputSource,
    EnhancementMetrics,
    EnhancementSeverity,
    EnhancementSummary,
    ObservationCategory,
    RelationshipGraph,
    RelationshipType,
    RequirementEnhancementResult,
    RequirementObservation,
    RequirementRelationship,
)

_NOW = datetime(2026, 7, 13, tzinfo=UTC)


def _relationship(
    rel_id: str = "rel-1", source: str = "req-1", target: str = "req-2"
) -> RequirementRelationship:
    return RequirementRelationship(
        relationship_id=rel_id,
        source_requirement_id=source,
        target_requirement_id=target,
        relationship_type=RelationshipType.DEPENDS_ON,
        rationale="req-1 references req-2's identifier.",
    )


def _graph(relationships: tuple[RequirementRelationship, ...] = ()) -> RelationshipGraph:
    return RelationshipGraph(
        graph_id=RelationshipGraphId.for_enhancement("re-abc"),
        requirement_ids=("req-1", "req-2"),
        relationships=relationships,
    )


def _observation(ordinal: int = 0) -> RequirementObservation:
    return RequirementObservation(
        observation_id=RequirementObservationId.for_ordinal("re-abc", ordinal),
        category=ObservationCategory.COMPLETENESS,
        severity=EnhancementSeverity.WARNING,
        subject_requirement_ids=("req-1",),
        message="req-1 has no acceptance criteria.",
    )


def _summary() -> EnhancementSummary:
    return EnhancementSummary(
        policy_id=EnhancementPolicyId("default-enhancement-policy"),
        policy_version=EnhancementPolicyVersion(1, 0, 0),
        total_requirements_enhanced=1,
        total_relationships=1,
        total_observations=1,
        total_findings=0,
        headline="1 requirement enhanced, 1 relationship, 1 observation.",
    )


def _metrics() -> EnhancementMetrics:
    return EnhancementMetrics(
        enrichment_coverage=1.0,
        relationship_density=1.0,
        observation_rate=1.0,
    )


@pytest.mark.unit
class TestEnhancedRequirement:
    def test_is_immutable(self) -> None:
        enhanced = EnhancedRequirement(
            enhanced_requirement_id=EnhancedRequirementId.for_requirement("re-abc", "req-1"),
            requirement_id="req-1",
        )
        with pytest.raises(ValidationError):
            enhanced.requirement_id = "req-2"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        enhanced = EnhancedRequirement(
            enhanced_requirement_id=EnhancedRequirementId.for_requirement("re-abc", "req-1"),
            requirement_id="req-1",
            relationship_ids=("rel-1",),
            observation_ids=("ro-1",),
        )
        dumped = enhanced.model_dump(mode="json", by_alias=True)
        assert EnhancedRequirement.model_validate(dumped) == enhanced


@pytest.mark.unit
class TestRequirementRelationship:
    def test_self_relationship_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _relationship(source="req-1", target="req-1")

    def test_all_nine_relationship_types_are_governed(self) -> None:
        assert {t.value for t in RelationshipType} == {
            "depends_on",
            "refines",
            "conflicts_with",
            "duplicates",
            "derived_from",
            "supports",
            "implements",
            "validates",
            "mitigates",
        }


@pytest.mark.unit
class TestRelationshipGraph:
    def test_valid_graph_constructs(self) -> None:
        graph = _graph((_relationship(),))
        assert len(graph.relationships) == 1

    def test_edge_referencing_unknown_node_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RelationshipGraph(
                graph_id=RelationshipGraphId.for_enhancement("re-abc"),
                requirement_ids=("req-1",),
                relationships=(_relationship(),),  # targets req-2, absent from nodes
            )

    def test_duplicate_relationship_ids_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _graph((_relationship("rel-1"), _relationship("rel-1")))

    def test_empty_graph_is_valid(self) -> None:
        graph = RelationshipGraph(graph_id=RelationshipGraphId.for_enhancement("re-abc"))
        assert graph.relationships == ()
        assert graph.requirement_ids == ()


@pytest.mark.unit
class TestObservationsAndFindings:
    def test_observation_round_trips(self) -> None:
        observation = _observation()
        dumped = observation.model_dump(mode="json", by_alias=True)
        assert RequirementObservation.model_validate(dumped) == observation

    def test_finding_references_observation_by_id_not_copy(self) -> None:
        observation = _observation()
        finding = EnhancementFinding(
            finding_id="ef-1",
            observation_id=observation.observation_id,
            category=observation.category,
            severity=observation.severity,
            message=observation.message,
        )
        assert finding.observation_id == observation.observation_id


@pytest.mark.unit
class TestRequirementEnhancementResult:
    def _build(self, **overrides: object) -> RequirementEnhancementResult:
        defaults: dict[str, object] = dict(
            result_id=RequirementEnhancementResultId.for_enhancement("re-abc"),
            analysis_id="an-1",
            execution_id="ex-1",
            enhanced_requirements=(),
            relationship_graph=_graph(),
            observations=(),
            findings=(),
            summary=_summary(),
            metrics=_metrics(),
            consumed_inputs=(
                EnhancementInputReference(
                    source=EnhancementInputSource.ENGINEERING_CONTEXT,
                    input_id="ctx-1",
                    input_version="1.0.0",
                ),
                EnhancementInputReference(
                    source=EnhancementInputSource.ANALYSIS_RESULT,
                    input_id="an-1",
                    input_version="1.0.0",
                ),
            ),
            policy_id=EnhancementPolicyId("default-enhancement-policy"),
            policy_version=EnhancementPolicyVersion(1, 0, 0),
            framework_version=EnhancementFrameworkVersion(1, 0, 0),
            started_at=_NOW,
            completed_at=_NOW,
        )
        defaults.update(overrides)
        return RequirementEnhancementResult(**defaults)  # type: ignore[arg-type]

    def test_valid_result_constructs(self) -> None:
        result = self._build()
        assert result.analysis_id == "an-1"

    def test_is_immutable(self) -> None:
        result = self._build()
        with pytest.raises(ValidationError):
            result.analysis_id = "an-2"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        result = self._build()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert RequirementEnhancementResult.model_validate(dumped) == result

    def test_completed_before_started_rejected(self) -> None:
        from datetime import timedelta

        with pytest.raises(ValidationError):
            self._build(started_at=_NOW, completed_at=_NOW - timedelta(seconds=1))

    def test_duplicate_consumed_input_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._build(
                consumed_inputs=(
                    EnhancementInputReference(
                        source=EnhancementInputSource.ENGINEERING_CONTEXT,
                        input_id="ctx-1",
                        input_version="1.0.0",
                    ),
                    EnhancementInputReference(
                        source=EnhancementInputSource.ENGINEERING_CONTEXT,
                        input_id="ctx-2",
                        input_version="1.0.0",
                    ),
                )
            )

    def test_finding_referencing_unknown_observation_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._build(
                findings=(
                    EnhancementFinding(
                        finding_id="ef-1",
                        observation_id=RequirementObservationId.for_ordinal("re-abc", 0),
                        category=ObservationCategory.COMPLETENESS,
                        severity=EnhancementSeverity.WARNING,
                        message="orphaned finding",
                    ),
                )
            )

    def test_finding_referencing_known_observation_accepted(self) -> None:
        observation = _observation()
        finding = EnhancementFinding(
            finding_id="ef-1",
            observation_id=observation.observation_id,
            category=observation.category,
            severity=observation.severity,
            message=observation.message,
        )
        result = self._build(observations=(observation,), findings=(finding,))
        assert result.findings[0].finding_id == "ef-1"

    def test_enhanced_requirement_referencing_unknown_relationship_rejected(self) -> None:
        enhanced = EnhancedRequirement(
            enhanced_requirement_id=EnhancedRequirementId.for_requirement("re-abc", "req-1"),
            requirement_id="req-1",
            relationship_ids=("rel-does-not-exist",),
        )
        with pytest.raises(ValidationError):
            self._build(enhanced_requirements=(enhanced,))

    def test_enhanced_requirement_referencing_known_relationship_accepted(self) -> None:
        relationship = _relationship()
        enhanced = EnhancedRequirement(
            enhanced_requirement_id=EnhancedRequirementId.for_requirement("re-abc", "req-1"),
            requirement_id="req-1",
            relationship_ids=(relationship.relationship_id,),
        )
        result = self._build(
            relationship_graph=_graph((relationship,)),
            enhanced_requirements=(enhanced,),
        )
        assert result.enhanced_requirements[0].relationship_ids == (relationship.relationship_id,)
