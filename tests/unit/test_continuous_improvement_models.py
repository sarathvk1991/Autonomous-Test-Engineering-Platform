"""Unit tests for the canonical Continuous Improvement Framework models (CAP-083A).

All models are frozen, tuple-backed, camelCase, and compute nothing — every value
in these tests is supplied directly, never derived, because no engine exists yet.
The tests assert immutability, serialization round-trips, and the
cross-referential and explainability invariants the validators enforce (ADR-0022
§D4/§D7).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from requirement_intelligence.continuous_improvement.identity import (
    ContinuousImprovementFrameworkVersion,
    ContinuousImprovementResultId,
    ImprovementFindingId,
    ImprovementOpportunityId,
    ImprovementPolicyId,
    ImprovementPolicyVersion,
    ImprovementTrendId,
)
from requirement_intelligence.continuous_improvement.models import (
    ContinuousImprovementResult,
    HistoricalDatasetReference,
    ImprovementFinding,
    ImprovementFindingCategory,
    ImprovementMetrics,
    ImprovementOpportunity,
    ImprovementOpportunityCategory,
    ImprovementSeverity,
    ImprovementSourceLayer,
    ImprovementSummary,
    ImprovementTrend,
    ImprovementTrendDirection,
)

_NOW = datetime(2026, 7, 15, tzinfo=UTC)


def _dataset_ref(**overrides: object) -> HistoricalDatasetReference:
    defaults: dict[str, object] = dict(
        dataset_id="ds-1",
        dataset_version="1.0.0",
        first_execution_id="ex-1",
        last_execution_id="ex-10",
        execution_count=10,
        history_window=25,
        generated_at=_NOW,
    )
    defaults.update(overrides)
    return HistoricalDatasetReference(**defaults)  # type: ignore[arg-type]


def _finding(
    finding_id: ImprovementFindingId | None = None,
    execution_ids: tuple[str, ...] = ("ex-1", "ex-2"),
) -> ImprovementFinding:
    return ImprovementFinding(
        finding_id=finding_id or ImprovementFindingId.for_ordinal("ds-1", 0),
        category=ImprovementFindingCategory.RECURRING_VALIDATION_FAILURE,
        source=ImprovementSourceLayer.VALIDATION,
        severity=ImprovementSeverity.WARNING,
        occurrence_count=len(execution_ids),
        contributing_execution_ids=execution_ids,
        message="repeated validation failure",
    )


def _trend(
    trend_id: ImprovementTrendId | None = None,
    execution_ids: tuple[str, ...] = ("ex-1", "ex-2"),
) -> ImprovementTrend:
    return ImprovementTrend(
        trend_id=trend_id or ImprovementTrendId.for_ordinal("ds-1", 0),
        direction=ImprovementTrendDirection.DEGRADING,
        source=ImprovementSourceLayer.GROUNDING,
        metric_name="groundingScore",
        observation_count=len(execution_ids),
        contributing_execution_ids=execution_ids,
        message="grounding score trending down",
    )


def _opportunity(
    opportunity_id: ImprovementOpportunityId | None = None,
    source_finding_ids: tuple[ImprovementFindingId, ...] = (),
    source_trend_ids: tuple[ImprovementTrendId, ...] = (),
) -> ImprovementOpportunity:
    return ImprovementOpportunity(
        opportunity_id=opportunity_id or ImprovementOpportunityId.for_ordinal("ds-1", 0),
        category=ImprovementOpportunityCategory.RECURRING_QUALITY_ISSUE,
        source_finding_ids=source_finding_ids,
        source_trend_ids=source_trend_ids,
        occurrence_count=2,
        description="recurring quality issue worth attention",
    )


def _summary(**overrides: object) -> ImprovementSummary:
    defaults: dict[str, object] = dict(
        policy_id=ImprovementPolicyId("default-improvement-policy"),
        policy_version=ImprovementPolicyVersion(1, 0, 0),
        total_findings=1,
        total_trends=1,
        total_opportunities=1,
        headline="1 finding, 1 trend, 1 opportunity.",
    )
    defaults.update(overrides)
    return ImprovementSummary(**defaults)  # type: ignore[arg-type]


def _metrics() -> ImprovementMetrics:
    return ImprovementMetrics(finding_density=0.1, trend_stability_ratio=0.0, opportunity_rate=0.5)


@pytest.mark.unit
class TestHistoricalDatasetReference:
    def test_valid_reference_constructs(self) -> None:
        ref = _dataset_ref()
        assert ref.dataset_id == "ds-1"

    def test_is_immutable(self) -> None:
        ref = _dataset_ref()
        with pytest.raises(ValidationError):
            ref.dataset_id = "ds-2"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        ref = _dataset_ref()
        dumped = ref.model_dump(mode="json", by_alias=True)
        assert HistoricalDatasetReference.model_validate(dumped) == ref

    def test_execution_count_exceeding_window_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _dataset_ref(execution_count=30, history_window=25)

    def test_execution_count_equal_to_window_accepted(self) -> None:
        ref = _dataset_ref(execution_count=25, history_window=25)
        assert ref.execution_count == 25

    def test_empty_dataset_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _dataset_ref(dataset_id="")

    def test_zero_execution_count_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _dataset_ref(execution_count=0)


@pytest.mark.unit
class TestImprovementFinding:
    def test_valid_finding_constructs(self) -> None:
        finding = _finding()
        assert finding.occurrence_count == 2

    def test_is_immutable(self) -> None:
        finding = _finding()
        with pytest.raises(ValidationError):
            finding.message = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        finding = _finding()
        dumped = finding.model_dump(mode="json", by_alias=True)
        assert ImprovementFinding.model_validate(dumped) == finding

    def test_occurrence_count_mismatch_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementFinding(
                finding_id=ImprovementFindingId.for_ordinal("ds-1", 0),
                category=ImprovementFindingCategory.RECURRING_VALIDATION_FAILURE,
                source=ImprovementSourceLayer.VALIDATION,
                severity=ImprovementSeverity.WARNING,
                occurrence_count=3,
                contributing_execution_ids=("ex-1", "ex-2"),
                message="mismatch",
            )

    def test_duplicate_contributing_execution_ids_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementFinding(
                finding_id=ImprovementFindingId.for_ordinal("ds-1", 0),
                category=ImprovementFindingCategory.RECURRING_VALIDATION_FAILURE,
                source=ImprovementSourceLayer.VALIDATION,
                severity=ImprovementSeverity.WARNING,
                occurrence_count=2,
                contributing_execution_ids=("ex-1", "ex-1"),
                message="dup",
            )

    def test_all_five_finding_categories_are_governed(self) -> None:
        # RECURRING_ENHANCEMENT_ISSUE was added additively in CAP-083B alongside
        # the fifth RECURRENCE rule (Requirement Enhancement).
        assert {c.value for c in ImprovementFindingCategory} == {
            "recurring_validation_failure",
            "recurring_grounding_contradiction",
            "recurring_governance_failure",
            "recurring_recommendation",
            "recurring_enhancement_issue",
        }

    def test_all_six_source_layers_are_governed(self) -> None:
        assert {s.value for s in ImprovementSourceLayer} == {
            "enhancement",
            "grounding",
            "validation",
            "cp1",
            "quality_governance",
            "recommendation",
        }


@pytest.mark.unit
class TestImprovementTrend:
    def test_valid_trend_constructs(self) -> None:
        trend = _trend()
        assert trend.direction == ImprovementTrendDirection.DEGRADING

    def test_is_immutable(self) -> None:
        trend = _trend()
        with pytest.raises(ValidationError):
            trend.message = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        trend = _trend()
        dumped = trend.model_dump(mode="json", by_alias=True)
        assert ImprovementTrend.model_validate(dumped) == trend

    def test_observation_count_mismatch_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementTrend(
                trend_id=ImprovementTrendId.for_ordinal("ds-1", 0),
                direction=ImprovementTrendDirection.STABLE,
                source=ImprovementSourceLayer.GROUNDING,
                metric_name="groundingScore",
                observation_count=5,
                contributing_execution_ids=("ex-1", "ex-2"),
                message="mismatch",
            )

    def test_single_observation_rejected(self) -> None:
        """A trend requires at least two data points to describe a direction."""
        with pytest.raises(ValidationError):
            ImprovementTrend(
                trend_id=ImprovementTrendId.for_ordinal("ds-1", 0),
                direction=ImprovementTrendDirection.STABLE,
                source=ImprovementSourceLayer.GROUNDING,
                metric_name="groundingScore",
                observation_count=1,
                contributing_execution_ids=("ex-1",),
                message="too few",
            )

    def test_all_four_directions_are_governed(self) -> None:
        assert {d.value for d in ImprovementTrendDirection} == {
            "improving",
            "degrading",
            "stable",
            "volatile",
        }


@pytest.mark.unit
class TestImprovementOpportunity:
    def test_valid_opportunity_with_finding_reference_constructs(self) -> None:
        finding = _finding()
        opportunity = _opportunity(source_finding_ids=(finding.finding_id,))
        assert opportunity.source_finding_ids == (finding.finding_id,)

    def test_valid_opportunity_with_trend_reference_constructs(self) -> None:
        trend = _trend()
        opportunity = _opportunity(source_trend_ids=(trend.trend_id,))
        assert opportunity.source_trend_ids == (trend.trend_id,)

    def test_is_immutable(self) -> None:
        opportunity = _opportunity(
            source_finding_ids=(ImprovementFindingId.for_ordinal("ds-1", 0),)
        )
        with pytest.raises(ValidationError):
            opportunity.description = "changed"  # type: ignore[misc]

    def test_round_trips(self) -> None:
        opportunity = _opportunity(
            source_finding_ids=(ImprovementFindingId.for_ordinal("ds-1", 0),)
        )
        dumped = opportunity.model_dump(mode="json", by_alias=True)
        assert ImprovementOpportunity.model_validate(dumped) == opportunity

    def test_zero_references_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _opportunity()

    def test_all_four_opportunity_categories_are_governed(self) -> None:
        assert {c.value for c in ImprovementOpportunityCategory} == {
            "recurring_documentation_gap",
            "recurring_architecture_weakness",
            "recurring_quality_issue",
            "recurring_recommendation_category",
        }


@pytest.mark.unit
class TestSummaryAndMetrics:
    def test_summary_round_trips(self) -> None:
        summary = _summary()
        dumped = summary.model_dump(mode="json", by_alias=True)
        assert ImprovementSummary.model_validate(dumped) == summary

    def test_metrics_round_trips(self) -> None:
        metrics = _metrics()
        dumped = metrics.model_dump(mode="json", by_alias=True)
        assert ImprovementMetrics.model_validate(dumped) == metrics

    def test_metrics_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            ImprovementMetrics(finding_density=1.0, trend_stability_ratio=1.5, opportunity_rate=0.0)

    def test_negative_total_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _summary(total_findings=-1)


@pytest.mark.unit
class TestContinuousImprovementResult:
    def _build(self, **overrides: object) -> ContinuousImprovementResult:
        finding = overrides.pop("_finding", None) or _finding()
        opportunity = overrides.pop("_opportunity", None) or _opportunity(
            source_finding_ids=(finding.finding_id,)
        )
        defaults: dict[str, object] = dict(
            result_id=ContinuousImprovementResultId.for_dataset("ds-1"),
            historical_dataset=_dataset_ref(),
            findings=(finding,),
            trends=(),
            opportunities=(opportunity,),
            summary=_summary(),
            metrics=_metrics(),
            policy_id=ImprovementPolicyId("default-improvement-policy"),
            policy_version=ImprovementPolicyVersion(1, 0, 0),
            framework_version=ContinuousImprovementFrameworkVersion(1, 0, 0),
            started_at=_NOW,
            completed_at=_NOW,
        )
        defaults.update(overrides)
        return ContinuousImprovementResult(**defaults)  # type: ignore[arg-type]

    def test_valid_result_constructs(self) -> None:
        result = self._build()
        assert result.historical_dataset.dataset_id == "ds-1"

    def test_is_immutable(self) -> None:
        result = self._build()
        with pytest.raises(ValidationError):
            result.result_id = ContinuousImprovementResultId.for_dataset("ds-2")  # type: ignore[misc]

    def test_round_trips(self) -> None:
        result = self._build()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert ContinuousImprovementResult.model_validate(dumped) == result

    def test_completed_before_started_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._build(started_at=_NOW, completed_at=_NOW - timedelta(seconds=1))

    def test_empty_result_is_valid(self) -> None:
        result = self._build(
            findings=(),
            trends=(),
            opportunities=(),
            summary=_summary(
                total_findings=0,
                total_trends=0,
                total_opportunities=0,
                headline="Nothing observed.",
            ),
        )
        assert result.findings == ()
        assert result.opportunities == ()

    def test_duplicate_finding_ids_rejected(self) -> None:
        finding = _finding()
        with pytest.raises(ValidationError):
            self._build(findings=(finding, finding), opportunities=())

    def test_duplicate_trend_ids_rejected(self) -> None:
        trend = _trend()
        with pytest.raises(ValidationError):
            self._build(findings=(), trends=(trend, trend), opportunities=())

    def test_duplicate_opportunity_ids_rejected(self) -> None:
        finding = _finding()
        opportunity = _opportunity(source_finding_ids=(finding.finding_id,))
        with pytest.raises(ValidationError):
            self._build(findings=(finding,), opportunities=(opportunity, opportunity))

    def test_opportunity_referencing_unknown_finding_rejected(self) -> None:
        stray_opportunity = _opportunity(
            source_finding_ids=(ImprovementFindingId.for_ordinal("ds-1", 99),)
        )
        with pytest.raises(ValidationError):
            self._build(findings=(_finding(),), opportunities=(stray_opportunity,))

    def test_opportunity_referencing_unknown_trend_rejected(self) -> None:
        stray_opportunity = _opportunity(
            source_trend_ids=(ImprovementTrendId.for_ordinal("ds-1", 99),)
        )
        with pytest.raises(ValidationError):
            self._build(findings=(), trends=(), opportunities=(stray_opportunity,))

    def test_opportunity_referencing_known_trend_accepted(self) -> None:
        trend = _trend()
        opportunity = _opportunity(source_trend_ids=(trend.trend_id,))
        result = self._build(findings=(), trends=(trend,), opportunities=(opportunity,))
        assert result.opportunities[0].source_trend_ids == (trend.trend_id,)
