"""Unit tests for the DeterministicConfidenceCalculator (CAP-077D).

Covers base scores per verdict, each governed bonus and penalty (individually and
combined), the ceiling and floor, band boundaries, component reconstruction (score ==
sum of components), full explanation population, determinism, and the boundary that
Confidence imports no matching or runtime objects.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.grounding import (
    ClassificationResult,
    ConfidenceBand,
    ConfidencePolicy,
    DeterministicConfidenceCalculator,
    EvidenceReference,
    EvidenceRelation,
    RequirementEvidenceLink,
    SupportClassification,
    default_confidence_policy,
)
from requirement_intelligence.grounding.confidence import (
    ConfidenceBandThresholds,
    ConfidenceBaseScores,
    ConfidenceBonuses,
    ConfidencePenalties,
)
from requirement_intelligence.grounding.identity import (
    ConfidencePolicyId,
    ConfidencePolicyVersion,
    GroundedRequirementId,
)
from requirement_intelligence.models.enums import SourceCategory, SourceSystem, SourceType

_GROUNDING_DIR = Path(
    __import__("requirement_intelligence.grounding", fromlist=["__file__"]).__file__
).parent
_RID = GroundedRequirementId.for_requirement(SourceCategory.SECURITY, "req")


def _link(
    relation: EvidenceRelation, record_id: str, system: SourceSystem = SourceSystem.OWASP_ZAP
) -> RequirementEvidenceLink:
    return RequirementEvidenceLink(
        evidence=EvidenceReference(
            source_system=system,
            source_record_id=record_id,
            source_category=SourceCategory.SECURITY,
            source_type=SourceType.DAST,
        ),
        relation=relation,
        match_score=40,
        matched_terms=("x",),
        rationale="r",
    )


def _result(
    classification: SupportClassification,
    *,
    supporting: tuple[RequirementEvidenceLink, ...] = (),
    contradicting: tuple[RequirementEvidenceLink, ...] = (),
) -> ClassificationResult:
    return ClassificationResult(
        requirement_id=_RID,
        support_classification=classification,
        supporting_links=supporting,
        contradicting_links=contradicting,
        classification_reason="test",
    )


def _policy(
    *,
    base_scores: ConfidenceBaseScores | None = None,
    bonuses: ConfidenceBonuses | None = None,
    penalties: ConfidencePenalties | None = None,
    band_thresholds: ConfidenceBandThresholds | None = None,
    max_score: int = 100,
) -> ConfidencePolicy:
    return ConfidencePolicy(
        policy_id=ConfidencePolicyId("test-policy"),
        policy_version=ConfidencePolicyVersion(1, 0, 0),
        description="test",
        base_scores=base_scores or ConfidenceBaseScores(),
        bonuses=bonuses or ConfidenceBonuses(),
        penalties=penalties or ConfidencePenalties(),
        band_thresholds=band_thresholds or ConfidenceBandThresholds(),
        max_score=max_score,
    )


def _calc(policy: ConfidencePolicy | None = None) -> DeterministicConfidenceCalculator:
    return DeterministicConfidenceCalculator(policy or default_confidence_policy())


@pytest.mark.unit
class TestBaseScore:
    @pytest.mark.parametrize(
        ("classification", "expected"),
        [
            (SupportClassification.SUPPORTED, 80),
            (SupportClassification.PARTIALLY_SUPPORTED, 55),
            (SupportClassification.WEAKLY_SUPPORTED, 30),
            (SupportClassification.UNSUPPORTED, 0),
            (SupportClassification.CONTRADICTED, 0),
            (SupportClassification.UNKNOWN, 0),
        ],
    )
    def test_base_score_per_classification(
        self, classification: SupportClassification, expected: int
    ) -> None:
        support = (_link(EvidenceRelation.DIRECT, "A"),) if expected > 0 else ()
        result = _calc().calculate(_result(classification, supporting=support))
        assert result.confidence_score == expected


@pytest.mark.unit
class TestBonuses:
    def test_support_bonus_per_additional_link(self) -> None:
        policy = _policy(bonuses=ConfidenceBonuses(support_bonus=5))
        links = (_link(EvidenceRelation.DIRECT, "A"), _link(EvidenceRelation.DIRECT, "B"))
        result = _calc(policy).calculate(_result(SupportClassification.SUPPORTED, supporting=links))
        assert result.confidence_score == 85  # 80 + 5 * (2 - 1)

    def test_cross_source_bonus_when_two_systems(self) -> None:
        policy = _policy(bonuses=ConfidenceBonuses(cross_source_bonus=7))
        links = (
            _link(EvidenceRelation.DIRECT, "A", SourceSystem.OWASP_ZAP),
            _link(EvidenceRelation.DIRECT, "B", SourceSystem.JIRA),
        )
        result = _calc(policy).calculate(_result(SupportClassification.SUPPORTED, supporting=links))
        assert result.confidence_score == 87  # 80 + 7 (single-source support bonus is 0)

    def test_no_cross_source_bonus_when_single_system(self) -> None:
        policy = _policy(bonuses=ConfidenceBonuses(cross_source_bonus=7))
        links = (_link(EvidenceRelation.DIRECT, "A"),)
        result = _calc(policy).calculate(_result(SupportClassification.SUPPORTED, supporting=links))
        assert result.confidence_score == 80

    def test_evidence_count_bonus_per_additional_item(self) -> None:
        policy = _policy(bonuses=ConfidenceBonuses(evidence_count_bonus=2))
        links = tuple(_link(EvidenceRelation.DIRECT, f"E{i}") for i in range(3))
        result = _calc(policy).calculate(_result(SupportClassification.SUPPORTED, supporting=links))
        assert result.confidence_score == 84  # 80 + 2 * (3 - 1)


@pytest.mark.unit
class TestPenalties:
    def test_conflict_penalty_per_conflicting_link(self) -> None:
        policy = _policy(penalties=ConfidencePenalties(conflict_penalty=10))
        result = _calc(policy).calculate(
            _result(
                SupportClassification.SUPPORTED,
                supporting=(_link(EvidenceRelation.DIRECT, "A"),),
                contradicting=(_link(EvidenceRelation.CONTRADICTING, "C"),),
            )
        )
        assert result.confidence_score == 70  # 80 - 10

    def test_unknown_penalty(self) -> None:
        policy = _policy(
            base_scores=ConfidenceBaseScores(unknown=30),
            penalties=ConfidencePenalties(unknown_penalty=5),
        )
        result = _calc(policy).calculate(_result(SupportClassification.UNKNOWN))
        assert result.confidence_score == 25  # 30 - 5


@pytest.mark.unit
class TestClampAndBands:
    def test_ceiling(self) -> None:
        policy = _policy(bonuses=ConfidenceBonuses(support_bonus=100), max_score=100)
        links = (_link(EvidenceRelation.DIRECT, "A"), _link(EvidenceRelation.DIRECT, "B"))
        result = _calc(policy).calculate(_result(SupportClassification.SUPPORTED, supporting=links))
        assert result.confidence_score == 100
        assert any(c.factor == "ceiling" for c in result.confidence_components)

    def test_floor(self) -> None:
        policy = _policy(penalties=ConfidencePenalties(conflict_penalty=100))
        result = _calc(policy).calculate(
            _result(
                SupportClassification.SUPPORTED,
                supporting=(_link(EvidenceRelation.DIRECT, "A"),),
                contradicting=(_link(EvidenceRelation.CONTRADICTING, "C"),),
            )
        )
        assert result.confidence_score == 0
        assert any(c.factor == "floor" for c in result.confidence_components)

    @pytest.mark.parametrize(
        ("base", "expected_band"),
        [
            (75, ConfidenceBand.HIGH),
            (74, ConfidenceBand.MEDIUM),
            (40, ConfidenceBand.MEDIUM),
            (39, ConfidenceBand.LOW),
        ],
    )
    def test_band_boundaries(self, base: int, expected_band: ConfidenceBand) -> None:
        policy = _policy(base_scores=ConfidenceBaseScores(supported=base))
        result = _calc(policy).calculate(
            _result(
                SupportClassification.SUPPORTED, supporting=(_link(EvidenceRelation.DIRECT, "A"),)
            )
        )
        assert result.confidence_band == expected_band


@pytest.mark.unit
class TestComponentsAndExplanation:
    def _rich(self) -> ClassificationResult:
        return _result(
            SupportClassification.SUPPORTED,
            supporting=(
                _link(EvidenceRelation.DIRECT, "A", SourceSystem.OWASP_ZAP),
                _link(EvidenceRelation.DIRECT, "B", SourceSystem.JIRA),
            ),
            contradicting=(_link(EvidenceRelation.CONTRADICTING, "C"),),
        )

    def _rich_policy(self) -> ConfidencePolicy:
        return _policy(
            bonuses=ConfidenceBonuses(
                support_bonus=3, cross_source_bonus=5, evidence_count_bonus=1
            ),
            penalties=ConfidencePenalties(conflict_penalty=4),
        )

    def test_score_equals_sum_of_components(self) -> None:
        result = _calc(self._rich_policy()).calculate(self._rich())
        assert sum(c.delta for c in result.confidence_components) == result.confidence_score

    def test_one_component_per_arithmetic_operation(self) -> None:
        result = _calc(self._rich_policy()).calculate(self._rich())
        factors = [c.factor for c in result.confidence_components]
        # base + support_bonus + cross_source_bonus + evidence_count_bonus + conflict_penalty
        assert factors[0].startswith("base:")
        assert "support_bonus" in factors
        assert "cross_source_bonus" in factors
        assert "evidence_count_bonus" in factors
        assert "conflict_penalty" in factors

    def test_explanation_fully_populated(self) -> None:
        explanation = _calc(self._rich_policy()).calculate(self._rich()).confidence_explanation
        assert explanation.summary
        assert explanation.positive_factors
        assert explanation.negative_factors
        assert explanation.applied_policy_rules
        assert explanation.score_breakdown
        assert explanation.recommendations

    def test_recommendations_are_governed_by_verdict(self) -> None:
        contradicted = _calc().calculate(
            _result(
                SupportClassification.CONTRADICTED,
                contradicting=(_link(EvidenceRelation.CONTRADICTING, "C"),),
            )
        )
        assert any(
            "quarantine" in rec for rec in contradicted.confidence_explanation.recommendations
        )


@pytest.mark.unit
class TestDeterminism:
    def test_equal_input_equal_assessment(self) -> None:
        result = _result(
            SupportClassification.SUPPORTED, supporting=(_link(EvidenceRelation.DIRECT, "A"),)
        )
        one = _calc().calculate(result)
        two = _calc().calculate(result)
        assert one == two
        assert one.model_dump(mode="json") == two.model_dump(mode="json")


@pytest.mark.unit
class TestPlatformContextAndBoundary:
    def test_factory_returns_deterministic_calculator(self) -> None:
        from requirement_intelligence.platform.platform_context import PlatformContext

        assert isinstance(
            PlatformContext().create_confidence_calculator(), DeterministicConfidenceCalculator
        )

    def test_calculator_imports_no_matching_or_runtime(self) -> None:
        source = (_GROUNDING_DIR / "confidence" / "deterministic_calculator.py").read_text(
            encoding="utf-8"
        )
        forbidden = (
            "grounding.strategies",
            "grounding.normalization",
            "grounding.matching",
            "grounding.grounding_service",
            "GroundingService",
            "context_orchestration",
            "AnalysisResult",
            "MatchResult",
        )
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                for token in forbidden:
                    assert token not in line
