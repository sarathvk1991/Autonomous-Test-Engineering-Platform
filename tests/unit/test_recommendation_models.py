"""Unit tests for the canonical Recommendation Framework models (CAP-082A).

All models are frozen, tuple-backed, camelCase, and compute nothing — every value in
these tests is supplied directly, never derived, because no engine exists yet. The
tests assert immutability, serialization round-trips, and the cross-referential and
explainability invariants the validators enforce (ADR-0019 §D4/§D7).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from requirement_intelligence.recommendation.identity import (
    RecommendationFrameworkVersion,
    RecommendationGroupId,
    RecommendationId,
    RecommendationPolicyId,
    RecommendationPolicyVersion,
    RecommendationResultId,
)
from requirement_intelligence.recommendation.models import (
    Recommendation,
    RecommendationEffort,
    RecommendationGroup,
    RecommendationInputReference,
    RecommendationMetrics,
    RecommendationPriority,
    RecommendationPriorityCount,
    RecommendationReference,
    RecommendationResult,
    RecommendationSource,
    RecommendationSummary,
    RecommendationType,
)

_NOW = datetime(2026, 7, 14, tzinfo=UTC)


def _reference(
    source: RecommendationSource = RecommendationSource.ENHANCEMENT,
    referenced_id: str = "ro-1",
    referenced_version: str = "1.0.0",
) -> RecommendationReference:
    return RecommendationReference(
        source=source, referenced_id=referenced_id, referenced_version=referenced_version
    )


def _recommendation(
    rec_id: RecommendationId | None = None,
    references: tuple[RecommendationReference, ...] = (),
) -> Recommendation:
    return Recommendation(
        recommendation_id=rec_id or RecommendationId.for_ordinal("ex-1", 0),
        title="Add missing acceptance criteria.",
        description="req-1 has no acceptance criteria; add one.",
        rationale="An enhancement observation flagged req-1 as incomplete.",
        recommendation_type=RecommendationType.ADD_REQUIREMENT,
        priority=RecommendationPriority.MEDIUM,
        effort=RecommendationEffort.LOW,
        confidence=0.75,
        recommendation_source=RecommendationSource.ENHANCEMENT,
        references=references or (_reference(),),
    )


def _summary() -> RecommendationSummary:
    return RecommendationSummary(
        policy_id=RecommendationPolicyId("default-recommendation-policy"),
        policy_version=RecommendationPolicyVersion(1, 0, 0),
        total_recommendations=1,
        total_groups=1,
        priority_distribution=(
            RecommendationPriorityCount(priority=RecommendationPriority.MEDIUM, count=1),
        ),
        headline="1 recommendation across 1 group.",
    )


def _metrics() -> RecommendationMetrics:
    return RecommendationMetrics(
        recommendation_density=1.0,
        average_confidence=0.75,
        high_priority_ratio=0.0,
    )


@pytest.mark.unit
class TestRecommendationReference:
    def test_round_trips(self) -> None:
        reference = _reference()
        dumped = reference.model_dump(mode="json", by_alias=True)
        assert RecommendationReference.model_validate(dumped) == reference

    def test_is_immutable(self) -> None:
        reference = _reference()
        with pytest.raises(ValidationError):
            reference.referenced_id = "ro-2"  # type: ignore[misc]

    def test_empty_referenced_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _reference(referenced_id="")


@pytest.mark.unit
class TestRecommendation:
    def test_valid_recommendation_constructs(self) -> None:
        recommendation = _recommendation()
        assert recommendation.priority == RecommendationPriority.MEDIUM

    def test_is_immutable(self) -> None:
        recommendation = _recommendation()
        with pytest.raises(ValidationError):
            recommendation.title = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        recommendation = _recommendation()
        dumped = recommendation.model_dump(mode="json", by_alias=True)
        assert Recommendation.model_validate(dumped) == recommendation

    def test_zero_references_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Recommendation(
                recommendation_id=RecommendationId.for_ordinal("ex-1", 0),
                title="Add missing acceptance criteria.",
                description="req-1 has no acceptance criteria; add one.",
                rationale="An enhancement observation flagged req-1 as incomplete.",
                recommendation_type=RecommendationType.ADD_REQUIREMENT,
                priority=RecommendationPriority.MEDIUM,
                effort=RecommendationEffort.LOW,
                confidence=0.75,
                recommendation_source=RecommendationSource.ENHANCEMENT,
                references=(),
            )

    def test_confidence_out_of_bounds_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Recommendation(
                recommendation_id=RecommendationId.for_ordinal("ex-1", 0),
                title="t",
                description="d",
                rationale="r",
                recommendation_type=RecommendationType.ADD_REQUIREMENT,
                priority=RecommendationPriority.MEDIUM,
                effort=RecommendationEffort.LOW,
                confidence=1.5,
                recommendation_source=RecommendationSource.ENHANCEMENT,
                references=(_reference(),),
            )

    def test_all_nine_recommendation_types_are_governed(self) -> None:
        assert {t.value for t in RecommendationType} == {
            "add_requirement",
            "clarify_requirement",
            "resolve_duplicate",
            "resolve_dependency",
            "resolve_conflict",
            "strengthen_evidence",
            "address_validation_issue",
            "address_engineering_gap",
            "improve_quality_score",
        }

    def test_all_five_recommendation_sources_are_governed(self) -> None:
        assert {s.value for s in RecommendationSource} == {
            "enhancement",
            "grounding",
            "validation",
            "cp1",
            "quality_governance",
        }


@pytest.mark.unit
class TestRecommendationGroup:
    def test_valid_group_constructs(self) -> None:
        rec = _recommendation()
        group = RecommendationGroup(
            group_id=RecommendationGroupId.for_ordinal("ex-1", 0),
            category=RecommendationType.ADD_REQUIREMENT,
            label="Completeness",
            recommendation_ids=(rec.recommendation_id,),
        )
        assert group.recommendation_ids == (rec.recommendation_id,)

    def test_duplicate_recommendation_ids_rejected(self) -> None:
        rec = _recommendation()
        with pytest.raises(ValidationError):
            RecommendationGroup(
                group_id=RecommendationGroupId.for_ordinal("ex-1", 0),
                category=RecommendationType.ADD_REQUIREMENT,
                label="Completeness",
                recommendation_ids=(rec.recommendation_id, rec.recommendation_id),
            )

    def test_empty_group_is_valid(self) -> None:
        group = RecommendationGroup(
            group_id=RecommendationGroupId.for_ordinal("ex-1", 0),
            category=RecommendationType.ADD_REQUIREMENT,
            label="Completeness",
        )
        assert group.recommendation_ids == ()

    def test_round_trips(self) -> None:
        rec = _recommendation()
        group = RecommendationGroup(
            group_id=RecommendationGroupId.for_ordinal("ex-1", 0),
            category=RecommendationType.ADD_REQUIREMENT,
            label="Completeness",
            recommendation_ids=(rec.recommendation_id,),
        )
        dumped = group.model_dump(mode="json", by_alias=True)
        assert RecommendationGroup.model_validate(dumped) == group

    def test_is_immutable(self) -> None:
        group = RecommendationGroup(
            group_id=RecommendationGroupId.for_ordinal("ex-1", 0),
            category=RecommendationType.ADD_REQUIREMENT,
            label="Completeness",
        )
        with pytest.raises(ValidationError):
            group.label = "changed"  # type: ignore[misc]


@pytest.mark.unit
class TestSummaryAndMetrics:
    def test_summary_round_trips(self) -> None:
        summary = _summary()
        dumped = summary.model_dump(mode="json", by_alias=True)
        assert RecommendationSummary.model_validate(dumped) == summary

    def test_metrics_round_trips(self) -> None:
        metrics = _metrics()
        dumped = metrics.model_dump(mode="json", by_alias=True)
        assert RecommendationMetrics.model_validate(dumped) == metrics

    def test_metrics_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            RecommendationMetrics(
                recommendation_density=1.0, average_confidence=1.5, high_priority_ratio=0.0
            )

    def test_negative_total_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RecommendationSummary(
                policy_id=RecommendationPolicyId("default-recommendation-policy"),
                policy_version=RecommendationPolicyVersion(1, 0, 0),
                total_recommendations=-1,
                total_groups=1,
                headline="invalid",
            )


@pytest.mark.unit
class TestRecommendationResult:
    def _build(self, **overrides: object) -> RecommendationResult:
        rec = overrides.pop("_recommendation", None) or _recommendation()
        group = overrides.pop("_group", None) or RecommendationGroup(
            group_id=RecommendationGroupId.for_ordinal("ex-1", 0),
            category=RecommendationType.ADD_REQUIREMENT,
            label="Completeness",
            recommendation_ids=(rec.recommendation_id,),
        )
        defaults: dict[str, object] = dict(
            result_id=RecommendationResultId.for_execution("ex-1"),
            analysis_id="an-1",
            execution_id="ex-1",
            recommendations=(rec,),
            groups=(group,),
            summary=_summary(),
            metrics=_metrics(),
            consumed_inputs=(
                RecommendationInputReference(
                    source=RecommendationSource.ENHANCEMENT,
                    input_id="rer-1",
                    input_version="1.0.0",
                ),
                RecommendationInputReference(
                    source=RecommendationSource.GROUNDING,
                    input_id="gr-1",
                    input_version="1.0.0",
                ),
            ),
            policy_id=RecommendationPolicyId("default-recommendation-policy"),
            policy_version=RecommendationPolicyVersion(1, 0, 0),
            framework_version=RecommendationFrameworkVersion(1, 0, 0),
            started_at=_NOW,
            completed_at=_NOW,
        )
        defaults.update(overrides)
        return RecommendationResult(**defaults)  # type: ignore[arg-type]

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
        assert RecommendationResult.model_validate(dumped) == result

    def test_completed_before_started_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._build(started_at=_NOW, completed_at=_NOW - timedelta(seconds=1))

    def test_empty_result_is_valid(self) -> None:
        result = self._build(
            recommendations=(),
            groups=(),
            summary=RecommendationSummary(
                policy_id=RecommendationPolicyId("default-recommendation-policy"),
                policy_version=RecommendationPolicyVersion(1, 0, 0),
                total_recommendations=0,
                total_groups=0,
                headline="No recommendations.",
            ),
            metrics=RecommendationMetrics(
                recommendation_density=0.0, average_confidence=0.0, high_priority_ratio=0.0
            ),
        )
        assert result.recommendations == ()
        assert result.groups == ()

    def test_duplicate_consumed_input_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._build(
                consumed_inputs=(
                    RecommendationInputReference(
                        source=RecommendationSource.ENHANCEMENT,
                        input_id="rer-1",
                        input_version="1.0.0",
                    ),
                    RecommendationInputReference(
                        source=RecommendationSource.ENHANCEMENT,
                        input_id="rer-2",
                        input_version="1.0.0",
                    ),
                )
            )

    def test_duplicate_recommendation_ids_rejected(self) -> None:
        rec = _recommendation()
        with pytest.raises(ValidationError):
            self._build(recommendations=(rec, rec))

    def test_duplicate_group_ids_rejected(self) -> None:
        rec = _recommendation()
        group = RecommendationGroup(
            group_id=RecommendationGroupId.for_ordinal("ex-1", 0),
            category=RecommendationType.ADD_REQUIREMENT,
            label="Completeness",
            recommendation_ids=(rec.recommendation_id,),
        )
        with pytest.raises(ValidationError):
            self._build(recommendations=(rec,), groups=(group, group))

    def test_group_referencing_unknown_recommendation_rejected(self) -> None:
        rec = _recommendation()
        stray_group = RecommendationGroup(
            group_id=RecommendationGroupId.for_ordinal("ex-1", 0),
            category=RecommendationType.ADD_REQUIREMENT,
            label="Completeness",
            recommendation_ids=(RecommendationId.for_ordinal("ex-1", 99),),
        )
        with pytest.raises(ValidationError):
            self._build(recommendations=(rec,), groups=(stray_group,))

    def test_group_referencing_known_recommendation_accepted(self) -> None:
        rec = _recommendation()
        group = RecommendationGroup(
            group_id=RecommendationGroupId.for_ordinal("ex-1", 0),
            category=RecommendationType.ADD_REQUIREMENT,
            label="Completeness",
            recommendation_ids=(rec.recommendation_id,),
        )
        result = self._build(recommendations=(rec,), groups=(group,))
        assert result.groups[0].recommendation_ids == (rec.recommendation_id,)
