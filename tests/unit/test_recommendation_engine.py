"""Behaviour, determinism, and explainability tests for
:class:`DeterministicRecommendationEngine` (CAP-082B).

Exercises the engine end-to-end over synthetic ``RequirementEnhancementResult`` /
``GroundingResult`` / ``ValidationResult`` / ``CP1Result`` / ``QualityGovernanceResult``
carriers: candidate dispatch for every source, confidence surfacing, policy-derived
prioritization (Recommendation 9), grouping, metrics, summary, determinism, and
serialization round-trips (ADR-0019).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from requirement_intelligence.enhancement.models.enums import (
    EnhancementSeverity,
    ObservationCategory,
)
from requirement_intelligence.grounding.models.enums import SupportClassification
from requirement_intelligence.quality_governance.models.enums import (
    QualityDecision,
    QualitySeverity,
)
from requirement_intelligence.recommendation.engine import DeterministicRecommendationEngine
from requirement_intelligence.recommendation.models.enums import (
    RecommendationPriority,
    RecommendationSource,
    RecommendationType,
)
from requirement_intelligence.recommendation.models.result import RecommendationResult
from requirement_intelligence.recommendation.policy import default_recommendation_policy
from requirement_intelligence.recommendation.policy.recommendation_policy import (
    ConfidenceRules,
    GroupingRules,
    PrioritizationRules,
    RecommendationCapabilitySwitches,
)
from requirement_intelligence.recommendation.rules import default_recommendation_rule_catalog
from requirement_intelligence.recommendation.rules.recommendation_rule_catalog import (
    RecommendationRuleCatalog,
)
from requirement_intelligence.recommendation.version import RECOMMENDATION_FRAMEWORK_VERSION
from shared.enums.base import ValidationVerdict as CP1Verdict
from tests.unit.recommendation_helpers import (
    make_cp1_finding,
    make_cp1_result,
    make_enhancement_finding,
    make_enhancement_result,
    make_grounding_finding,
    make_grounding_result,
    make_quality_finding,
    make_quality_governance_result,
    make_validation_issue,
    make_validation_result,
)


def _engine(policy=None, catalog=None) -> DeterministicRecommendationEngine:
    return DeterministicRecommendationEngine(
        policy=policy or default_recommendation_policy(),
        rule_catalog=catalog or default_recommendation_rule_catalog(),
    )


def _clean_inputs() -> tuple:
    return (
        make_enhancement_result(),
        make_grounding_result(),
        make_validation_result(),
        make_cp1_result(),
        make_quality_governance_result(),
    )


def _find(result: RecommendationResult, source: RecommendationSource) -> tuple:
    return tuple(r for r in result.recommendations if r.recommendation_source == source)


@pytest.mark.unit
class TestEmptyRun:
    def test_clean_run_produces_no_recommendations(self) -> None:
        result = _engine().recommend(*_clean_inputs())
        assert result.recommendations == ()
        assert result.groups == ()
        assert result.summary.total_recommendations == 0
        assert result.metrics.average_confidence == 0.0

    def test_clean_run_still_records_consumed_inputs(self) -> None:
        result = _engine().recommend(*_clean_inputs())
        assert len(result.consumed_inputs) == 5
        assert {ref.source for ref in result.consumed_inputs} == set(RecommendationSource)

    def test_clean_run_records_framework_version(self) -> None:
        result = _engine().recommend(*_clean_inputs())
        assert result.framework_version == RECOMMENDATION_FRAMEWORK_VERSION

    def test_clean_run_is_a_valid_result(self) -> None:
        result = _engine().recommend(*_clean_inputs())
        assert isinstance(result, RecommendationResult)


@pytest.mark.unit
class TestEnhancementDispatch:
    def test_dependency_gap_produces_resolve_dependency(self) -> None:
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        recs = _find(result, RecommendationSource.ENHANCEMENT)
        assert len(recs) == 1
        assert recs[0].recommendation_type == RecommendationType.RESOLVE_DEPENDENCY

    def test_duplication_produces_resolve_duplicate(self) -> None:
        finding = make_enhancement_finding("ef-2", category=ObservationCategory.DUPLICATION)
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert _find(result, RecommendationSource.ENHANCEMENT)[0].recommendation_type == (
            RecommendationType.RESOLVE_DUPLICATE
        )

    def test_consistency_warning_produces_clarify_requirement(self) -> None:
        finding = make_enhancement_finding(
            "ef-3", category=ObservationCategory.CONSISTENCY, severity=EnhancementSeverity.WARNING
        )
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        rec = _find(result, RecommendationSource.ENHANCEMENT)[0]
        assert rec.recommendation_type == RecommendationType.CLARIFY_REQUIREMENT
        assert rec.priority == RecommendationPriority.MEDIUM

    def test_consistency_critical_produces_resolve_conflict_at_critical_priority(self) -> None:
        finding = make_enhancement_finding(
            "ef-4", category=ObservationCategory.CONSISTENCY, severity=EnhancementSeverity.CRITICAL
        )
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        rec = _find(result, RecommendationSource.ENHANCEMENT)[0]
        assert rec.recommendation_type == RecommendationType.RESOLVE_CONFLICT
        assert rec.priority == RecommendationPriority.CRITICAL

    def test_traceability_gap_produces_clarify_requirement(self) -> None:
        finding = make_enhancement_finding("ef-5", category=ObservationCategory.TRACEABILITY)
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert _find(result, RecommendationSource.ENHANCEMENT)[0].recommendation_type == (
            RecommendationType.CLARIFY_REQUIREMENT
        )

    def test_completeness_category_is_not_covered_by_any_rule(self) -> None:
        finding = make_enhancement_finding("ef-6", category=ObservationCategory.COMPLETENESS)
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert _find(result, RecommendationSource.ENHANCEMENT) == ()


@pytest.mark.unit
class TestGroundingDispatch:
    def test_unsupported_produces_strengthen_evidence(self) -> None:
        finding, requirement = make_grounding_finding(
            "gf-1", classification=SupportClassification.UNSUPPORTED
        )
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(findings=(finding,), grounded_requirements=(requirement,)),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        rec = _find(result, RecommendationSource.GROUNDING)[0]
        assert rec.recommendation_type == RecommendationType.STRENGTHEN_EVIDENCE
        assert rec.priority == RecommendationPriority.HIGH

    def test_contradicted_produces_resolve_conflict_at_critical_priority(self) -> None:
        finding, requirement = make_grounding_finding(
            "gf-2", classification=SupportClassification.CONTRADICTED
        )
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(findings=(finding,), grounded_requirements=(requirement,)),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        rec = _find(result, RecommendationSource.GROUNDING)[0]
        assert rec.recommendation_type == RecommendationType.RESOLVE_CONFLICT
        assert rec.priority == RecommendationPriority.CRITICAL


@pytest.mark.unit
class TestValidationDispatch:
    @pytest.mark.parametrize(
        ("severity", "expected_priority"),
        [
            ("info", RecommendationPriority.LOW),
            ("warning", RecommendationPriority.MEDIUM),
            ("error", RecommendationPriority.HIGH),
            ("critical", RecommendationPriority.CRITICAL),
        ],
    )
    def test_severity_maps_to_governed_priority(self, severity, expected_priority) -> None:
        issue = make_validation_issue("vi-1", severity=severity)
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(issues=(issue,)),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        rec = _find(result, RecommendationSource.VALIDATION)[0]
        assert rec.recommendation_type == RecommendationType.ADDRESS_VALIDATION_ISSUE
        assert rec.priority == expected_priority


@pytest.mark.unit
class TestCP1Dispatch:
    def test_fail_contribution_produces_add_requirement(self) -> None:
        finding = make_cp1_finding("cf-1", verdict=CP1Verdict.FAIL)
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(findings=(finding,), verdict=CP1Verdict.FAIL),
            make_quality_governance_result(),
        )
        rec = _find(result, RecommendationSource.CP1)[0]
        assert rec.recommendation_type == RecommendationType.ADD_REQUIREMENT
        assert rec.priority == RecommendationPriority.HIGH

    def test_warn_contribution_produces_address_engineering_gap(self) -> None:
        finding = make_cp1_finding("cf-2", verdict=CP1Verdict.WARN)
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(findings=(finding,)),
            make_quality_governance_result(),
        )
        rec = _find(result, RecommendationSource.CP1)[0]
        assert rec.recommendation_type == RecommendationType.ADDRESS_ENGINEERING_GAP
        assert rec.priority == RecommendationPriority.MEDIUM

    def test_pass_contribution_produces_no_recommendation(self) -> None:
        finding = make_cp1_finding("cf-3", verdict=CP1Verdict.PASS)
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(findings=(finding,)),
            make_quality_governance_result(),
        )
        assert _find(result, RecommendationSource.CP1) == ()


@pytest.mark.unit
class TestQualityGovernanceDispatch:
    @pytest.mark.parametrize(
        ("severity", "expected_priority"),
        [
            (QualitySeverity.INFO, RecommendationPriority.LOW),
            (QualitySeverity.WARNING, RecommendationPriority.MEDIUM),
            (QualitySeverity.FAILURE, RecommendationPriority.HIGH),
        ],
    )
    def test_finding_severity_maps_to_governed_priority(self, severity, expected_priority) -> None:
        finding = make_quality_finding("qf-1", severity=severity)
        decision = (
            QualityDecision.FAIL
            if severity == QualitySeverity.FAILURE
            else (
                QualityDecision.PASS_WITH_WARNINGS
                if severity == QualitySeverity.WARNING
                else QualityDecision.PASS
            )
        )
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(findings=(finding,), decision=decision),
        )
        finding_recs = [
            r
            for r in _find(result, RecommendationSource.QUALITY_GOVERNANCE)
            if r.references[0].referenced_id == "qf-1"
        ]
        assert len(finding_recs) == 1
        assert finding_recs[0].priority == expected_priority

    def test_fail_decision_produces_a_decision_recommendation(self) -> None:
        finding = make_quality_finding("qf-2", severity=QualitySeverity.FAILURE)
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(findings=(finding,), decision=QualityDecision.FAIL),
        )
        recs = _find(result, RecommendationSource.QUALITY_GOVERNANCE)
        # one for the finding, one for the decision itself
        assert len(recs) == 2
        decision_rec = next(r for r in recs if r.references[0].referenced_id != "qf-2")
        assert decision_rec.priority == RecommendationPriority.CRITICAL

    def test_pass_with_warnings_decision_produces_a_decision_recommendation(self) -> None:
        finding = make_quality_finding("qf-3", severity=QualitySeverity.WARNING)
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(
                findings=(finding,), decision=QualityDecision.PASS_WITH_WARNINGS
            ),
        )
        recs = _find(result, RecommendationSource.QUALITY_GOVERNANCE)
        assert len(recs) == 2

    def test_pass_decision_produces_no_decision_recommendation(self) -> None:
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(decision=QualityDecision.PASS),
        )
        assert _find(result, RecommendationSource.QUALITY_GOVERNANCE) == ()


@pytest.mark.unit
class TestExplainability:
    def test_every_recommendation_has_at_least_one_reference(self) -> None:
        result = _engine().recommend(
            make_enhancement_result(
                findings=(
                    make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY),
                )
            ),
            make_grounding_result(),
            make_validation_result(issues=(make_validation_issue("vi-1"),)),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert result.recommendations
        assert all(len(r.references) >= 1 for r in result.recommendations)

    def test_title_and_description_are_rule_owned_not_copied(self) -> None:
        """Title/description come from governed rule metadata, never finding content."""
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        rec = result.recommendations[0]
        assert "synthetic finding" not in rec.title
        assert "synthetic finding" not in rec.description

    def test_reference_names_the_correct_source_and_id(self) -> None:
        finding = make_enhancement_finding("ef-99", category=ObservationCategory.DEPENDENCY)
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        reference = result.recommendations[0].references[0]
        assert reference.source == RecommendationSource.ENHANCEMENT
        assert reference.referenced_id == "ef-99"


@pytest.mark.unit
class TestConfidenceSurfacing:
    def test_below_floor_is_suppressed(self) -> None:
        policy = default_recommendation_policy().model_copy(
            update={
                "confidence_rules": ConfidenceRules(
                    minimum_confidence_to_surface=0.99, high_confidence_threshold=0.99
                )
            }
        )
        result = _engine(policy=policy).recommend(
            make_enhancement_result(
                findings=(
                    make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY),
                )
            ),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert result.recommendations == ()
        assert "confidence" in result.summary.headline.lower()

    def test_disabled_confidence_scoring_surfaces_everything(self) -> None:
        base_switches = default_recommendation_policy().capability_switches
        policy = default_recommendation_policy().model_copy(
            update={
                "confidence_rules": ConfidenceRules(
                    minimum_confidence_to_surface=0.99, high_confidence_threshold=0.99
                ),
                "capability_switches": base_switches.model_copy(
                    update={"enable_confidence_scoring": False}
                ),
            }
        )
        result = _engine(policy=policy).recommend(
            make_enhancement_result(
                findings=(
                    make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY),
                )
            ),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert len(result.recommendations) == 1


@pytest.mark.unit
class TestPrioritization:
    def test_priority_never_depends_on_source(self) -> None:
        """Two different sources' recommendations can carry the same priority.

        A CP1 recommendation and a Quality Governance recommendation both hit HIGH
        under their respective governed rules — proving priority is rule/category
        derived, not source-conditioned (Recommendation 9).
        """
        cp1_finding = make_cp1_finding("cf-1", verdict=CP1Verdict.FAIL)
        quality_finding = make_quality_finding("qf-1", severity=QualitySeverity.FAILURE)
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(findings=(cp1_finding,), verdict=CP1Verdict.FAIL),
            make_quality_governance_result(
                findings=(quality_finding,), decision=QualityDecision.FAIL
            ),
        )
        cp1_rec = _find(result, RecommendationSource.CP1)[0]
        quality_rec = next(
            r
            for r in _find(result, RecommendationSource.QUALITY_GOVERNANCE)
            if r.references[0].referenced_id == "qf-1"
        )
        assert cp1_rec.priority == RecommendationPriority.HIGH
        assert quality_rec.priority == RecommendationPriority.HIGH

    def test_disabled_prioritization_keeps_raw_hint(self) -> None:
        base_switches = default_recommendation_policy().capability_switches
        policy = default_recommendation_policy().model_copy(
            update={
                "capability_switches": base_switches.model_copy(
                    update={"enable_prioritization": False}
                ),
                "prioritization_rules": PrioritizationRules(
                    enabled_priorities=(RecommendationPriority.LOW,),
                    max_recommendations_per_priority=1,
                ),
            }
        )
        finding = make_enhancement_finding(
            "ef-1", category=ObservationCategory.CONSISTENCY, severity=EnhancementSeverity.CRITICAL
        )
        result = _engine(policy=policy).recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        # Rule hint for this category is CRITICAL; with prioritization disabled the
        # engine must not clamp it into the (LOW-only) enabled set.
        assert result.recommendations[0].priority == RecommendationPriority.CRITICAL

    def test_priority_clamped_to_enabled_set(self) -> None:
        policy = default_recommendation_policy().model_copy(
            update={
                "prioritization_rules": PrioritizationRules(
                    enabled_priorities=(RecommendationPriority.LOW, RecommendationPriority.MEDIUM),
                    max_recommendations_per_priority=100,
                )
            }
        )
        finding = make_enhancement_finding(
            "ef-1", category=ObservationCategory.CONSISTENCY, severity=EnhancementSeverity.CRITICAL
        )
        result = _engine(policy=policy).recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        # CRITICAL hint isn't enabled; clamps down to the nearest enabled: MEDIUM.
        assert result.recommendations[0].priority == RecommendationPriority.MEDIUM

    def test_priority_cap_demotes_overflow_deterministically(self) -> None:
        policy = default_recommendation_policy().model_copy(
            update={"prioritization_rules": PrioritizationRules(max_recommendations_per_priority=1)}
        )
        issues = tuple(make_validation_issue(f"vi-{i}", severity="critical") for i in range(3))
        result = _engine(policy=policy).recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(issues=issues),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        priorities = [r.priority for r in result.recommendations]
        assert priorities == [
            RecommendationPriority.CRITICAL,
            RecommendationPriority.HIGH,
            RecommendationPriority.MEDIUM,
        ]

    def test_recommendation_ids_stable_regardless_of_confidence_filtering(self) -> None:
        """An id is a pure function of (execution_id, ordinal) — unaffected by filtering.

        The same candidate set is run twice: once where every candidate clears the
        confidence floor, once where only the (higher-confidence) validation
        candidate does. The surviving validation recommendation must carry the same
        id both times, because ids are minted from each candidate's fixed position
        in the full deterministic dispatch order, before any filtering occurs.
        """
        enhancement_finding = make_enhancement_finding(
            "ef-1",
            category=ObservationCategory.DEPENDENCY,  # confidence_hint 0.70
        )
        validation_issue = make_validation_issue(
            "vi-1", severity="critical"
        )  # confidence_hint 0.95
        inputs = (
            make_enhancement_result(findings=(enhancement_finding,)),
            make_grounding_result(),
            make_validation_result(issues=(validation_issue,)),
            make_cp1_result(),
            make_quality_governance_result(),
        )

        baseline = _engine().recommend(*inputs)

        strict_policy = default_recommendation_policy().model_copy(
            update={
                "confidence_rules": ConfidenceRules(
                    minimum_confidence_to_surface=0.9, high_confidence_threshold=0.9
                )
            }
        )
        filtered = _engine(policy=strict_policy).recommend(*inputs)

        assert len(baseline.recommendations) == 2
        assert len(filtered.recommendations) == 1

        validation_rec_baseline = next(
            r
            for r in baseline.recommendations
            if r.recommendation_source == RecommendationSource.VALIDATION
        )
        validation_rec_filtered = filtered.recommendations[0]
        assert (
            validation_rec_baseline.recommendation_id == validation_rec_filtered.recommendation_id
        )


@pytest.mark.unit
class TestGrouping:
    def test_disabled_grouping_produces_no_groups(self) -> None:
        base_switches = default_recommendation_policy().capability_switches
        policy = default_recommendation_policy().model_copy(
            update={
                "capability_switches": base_switches.model_copy(update={"enable_grouping": False})
            }
        )
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        result = _engine(policy=policy).recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert result.recommendations
        assert result.groups == ()

    def test_group_membership_capped_by_policy(self) -> None:
        policy = default_recommendation_policy().model_copy(
            update={"grouping_rules": GroupingRules(max_recommendations_per_group=1)}
        )
        issues = tuple(make_validation_issue(f"vi-{i}", severity="critical") for i in range(3))
        result = _engine(policy=policy).recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(issues=issues),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert len(result.recommendations) == 3
        assert len(result.groups) == 1
        assert len(result.groups[0].recommendation_ids) == 1

    def test_disabled_category_is_not_grouped(self) -> None:
        policy = default_recommendation_policy().model_copy(
            update={
                "grouping_rules": GroupingRules(
                    enabled_categories=tuple(
                        t for t in RecommendationType if t != RecommendationType.RESOLVE_DEPENDENCY
                    ),
                    max_recommendations_per_group=25,
                )
            }
        )
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        result = _engine(policy=policy).recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert result.recommendations
        assert result.groups == ()

    def test_group_category_matches_member_recommendation_type(self) -> None:
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DUPLICATION)
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        group = result.groups[0]
        assert group.category == RecommendationType.RESOLVE_DUPLICATE
        assert group.recommendation_ids == (result.recommendations[0].recommendation_id,)


@pytest.mark.unit
class TestMetricsAndSummary:
    def test_metrics_and_summary_agree_on_totals(self) -> None:
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert result.summary.total_recommendations == len(result.recommendations)
        assert result.summary.total_groups == len(result.groups)

    def test_average_confidence_is_exact_mean(self) -> None:
        issues = (
            make_validation_issue("vi-1", severity="info"),
            make_validation_issue("vi-2", severity="critical"),
        )
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(issues=issues),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        expected = sum(r.confidence for r in result.recommendations) / len(result.recommendations)
        assert result.metrics.average_confidence == pytest.approx(expected)

    def test_high_priority_ratio_counts_high_and_critical_only(self) -> None:
        issues = (
            make_validation_issue("vi-1", severity="info"),  # LOW
            make_validation_issue("vi-2", severity="critical"),  # CRITICAL
        )
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(issues=issues),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert result.metrics.high_priority_ratio == pytest.approx(0.5)

    def test_recommendation_density_is_recs_over_groups(self) -> None:
        finding_a = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        finding_b = make_enhancement_finding("ef-2", category=ObservationCategory.DUPLICATION)
        result = _engine().recommend(
            make_enhancement_result(findings=(finding_a, finding_b)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert result.metrics.recommendation_density == pytest.approx(
            len(result.recommendations) / len(result.groups)
        )

    def test_priority_distribution_sums_to_total(self) -> None:
        issues = tuple(make_validation_issue(f"vi-{i}", severity="warning") for i in range(4))
        result = _engine().recommend(
            make_enhancement_result(),
            make_grounding_result(),
            make_validation_result(issues=issues),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert sum(entry.count for entry in result.summary.priority_distribution) == (
            result.summary.total_recommendations
        )


@pytest.mark.unit
class TestDeterminism:
    def test_same_input_same_result(self) -> None:
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        clock = lambda: datetime(2026, 7, 15, 0, 0, 0, tzinfo=UTC)  # noqa: E731
        engine = DeterministicRecommendationEngine(
            policy=default_recommendation_policy(),
            rule_catalog=default_recommendation_rule_catalog(),
            clock=clock,
        )
        inputs = (
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        first = engine.recommend(*inputs)
        second = engine.recommend(*inputs)
        assert first == second

    def test_serialization_round_trips(self) -> None:
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        result = _engine().recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        dumped = result.model_dump(mode="json", by_alias=True)
        assert RecommendationResult.model_validate(dumped) == result

    def test_result_is_frozen(self) -> None:
        result = _engine().recommend(*_clean_inputs())
        with pytest.raises(ValidationError):
            result.analysis_id = "changed"  # type: ignore[misc]


@pytest.mark.unit
class TestPolicyDisabled:
    def test_disabled_engine_returns_empty_but_valid_result(self) -> None:
        policy = default_recommendation_policy().model_copy(
            update={
                "capability_switches": RecommendationCapabilitySwitches(
                    enable_prioritization=True,
                    enable_grouping=True,
                    enable_confidence_scoring=True,
                    enable_deterministic_engine=False,
                    enable_ml_engine=False,
                    enable_llm_engine=False,
                )
            }
        )
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        result = _engine(policy=policy).recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert result.recommendations == ()
        assert result.groups == ()
        assert "disabled" in result.summary.headline.lower()
        assert len(result.consumed_inputs) == 5


@pytest.mark.unit
class TestCustomCatalog:
    def test_engine_accepts_explicit_rule_catalog(self) -> None:
        empty_catalog = RecommendationRuleCatalog()
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        result = _engine(catalog=empty_catalog).recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert result.recommendations == ()

    def test_default_engine_uses_default_catalog(self) -> None:
        engine = DeterministicRecommendationEngine(policy=default_recommendation_policy())
        finding = make_enhancement_finding("ef-1", category=ObservationCategory.DEPENDENCY)
        result = engine.recommend(
            make_enhancement_result(findings=(finding,)),
            make_grounding_result(),
            make_validation_result(),
            make_cp1_result(),
            make_quality_governance_result(),
        )
        assert len(result.recommendations) == 1
