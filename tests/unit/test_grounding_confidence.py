"""Unit tests for the Confidence framework architecture (CAP-077C.1).

Architecture only — the calculator is dormant. Covers the ConfidenceAssessment and
ConfidenceExplanation models, the governed ConfidencePolicy, the abstract calculator
contract, versioning independence, PlatformContext registration, and the boundary that
Confidence consumes only a ClassificationResult.
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.grounding import (
    CONFIDENCE_POLICY_VERSION,
    CONFIDENCE_VERSION,
    ClassificationVersion,
    ConfidenceAssessment,
    ConfidenceBand,
    ConfidenceCalculator,
    ConfidenceExplanation,
    ConfidencePolicy,
    ConfidencePolicyBuilder,
    ConfidencePolicyId,
    ConfidencePolicyVersion,
    ConfidenceVersion,
    DormantConfidenceCalculator,
    MatchResultVersion,
    default_confidence_policy,
)
from requirement_intelligence.grounding.identity import GroundedRequirementId
from requirement_intelligence.models.enums import SourceCategory

_GROUNDING_DIR = Path(
    __import__("requirement_intelligence.grounding", fromlist=["__file__"]).__file__
).parent


def _assessment(score: int = 80) -> ConfidenceAssessment:
    return ConfidenceAssessment(
        requirement_id=GroundedRequirementId.for_requirement(SourceCategory.SECURITY, "req"),
        confidence_score=score,
        confidence_band=ConfidenceBand.HIGH,
        confidence_explanation=ConfidenceExplanation(summary="s", positive_factors=("strong",)),
    )


@pytest.mark.unit
class TestConfidenceAssessment:
    def test_constructs_and_defaults_version(self) -> None:
        assessment = _assessment()
        assert assessment.confidence_version == CONFIDENCE_VERSION
        assert isinstance(assessment.confidence_version, ConfidenceVersion)

    def test_is_immutable(self) -> None:
        with pytest.raises(ValidationError):
            _assessment().confidence_score = 10  # type: ignore[misc]

    def test_serialises_and_round_trips(self) -> None:
        assessment = _assessment()
        dumped = assessment.model_dump(mode="json", by_alias=True)
        assert dumped["confidenceVersion"] == str(CONFIDENCE_VERSION)
        assert dumped["confidenceScore"] == 80
        assert ConfidenceAssessment.model_validate(dumped) == assessment

    def test_deterministic_equality(self) -> None:
        assert _assessment() == _assessment()

    def test_score_bounds_enforced(self) -> None:
        with pytest.raises(ValidationError):
            _assessment(score=101)


@pytest.mark.unit
class TestConfidenceExplanation:
    def test_structured_fields(self) -> None:
        explanation = ConfidenceExplanation(
            summary="s",
            positive_factors=("a",),
            negative_factors=("b",),
            applied_policy_rules=("rule",),
            recommendations=("accept",),
        )
        assert explanation.positive_factors == ("a",)
        assert explanation.applied_policy_rules == ("rule",)

    def test_is_immutable(self) -> None:
        with pytest.raises(ValidationError):
            ConfidenceExplanation().summary = "x"  # type: ignore[misc]

    def test_serialises_and_round_trips(self) -> None:
        explanation = ConfidenceExplanation(summary="s", negative_factors=("weak",))
        dumped = explanation.model_dump(mode="json", by_alias=True)
        assert "negativeFactors" in dumped
        assert ConfidenceExplanation.model_validate(dumped) == explanation


@pytest.mark.unit
class TestConfidencePolicy:
    def test_default_is_versioned_and_identified(self) -> None:
        policy = default_confidence_policy()
        assert isinstance(policy.policy_id, ConfidencePolicyId)
        assert policy.policy_version == CONFIDENCE_POLICY_VERSION
        assert isinstance(policy.policy_version, ConfidencePolicyVersion)

    def test_is_immutable(self) -> None:
        with pytest.raises(ValidationError):
            default_confidence_policy().max_score = 50  # type: ignore[misc]

    def test_builder_is_deterministic(self) -> None:
        assert ConfidencePolicyBuilder().build() == ConfidencePolicyBuilder().build()

    def test_serialises_and_round_trips(self) -> None:
        policy = default_confidence_policy()
        dumped = policy.model_dump(mode="json", by_alias=True)
        assert "baseScores" in dumped
        assert "bandThresholds" in dumped
        assert ConfidencePolicy.model_validate(dumped) == policy


@pytest.mark.unit
class TestConfidenceCalculatorContract:
    def test_contract_is_abstract(self) -> None:
        assert issubclass(ConfidenceCalculator, ABC)
        with pytest.raises(TypeError):
            ConfidenceCalculator()  # type: ignore[abstract]

    def test_dormant_calculator_raises_not_implemented(self) -> None:
        from tests.unit.grounding_helpers import make_classification_result

        calculator = DormantConfidenceCalculator(policy=default_confidence_policy())
        assert isinstance(calculator, ConfidenceCalculator)
        with pytest.raises(NotImplementedError):
            calculator.calculate(make_classification_result())

    def test_calculate_signature_consumes_classification_result(self) -> None:
        import inspect

        params = list(inspect.signature(ConfidenceCalculator.calculate).parameters)
        assert params == ["self", "classification_result"]


@pytest.mark.unit
class TestVersionIndependence:
    def test_confidence_version_distinct_from_others(self) -> None:
        assert ConfidenceVersion(1, 0, 0) != ClassificationVersion(1, 0, 0)
        assert ConfidenceVersion(1, 0, 0) != MatchResultVersion(1, 0, 0)

    def test_confidence_and_policy_versions_are_distinct_types(self) -> None:
        assert ConfidenceVersion(1, 0, 0) != ConfidencePolicyVersion(1, 0, 0)


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_registers_policy_and_calculator(self) -> None:
        from requirement_intelligence.platform.platform_context import PlatformContext

        context = PlatformContext()
        assert isinstance(context.create_confidence_policy(), ConfidencePolicy)
        assert isinstance(context.create_confidence_calculator(), ConfidenceCalculator)


@pytest.mark.unit
class TestConfidenceBoundary:
    def test_confidence_imports_only_classification_not_matching(self) -> None:
        """Confidence consumes only ClassificationResult — never matching internals."""
        package_dir = _GROUNDING_DIR / "confidence"
        forbidden = (
            "grounding.strategies",
            "grounding.normalization",
            "grounding.matching",
            "grounding.grounding_service",
            "context_orchestration",
            "analysis_models",
            "EngineeringContext",
            "AnalysisResult",
            "MatchResult",
        )
        for module in package_dir.glob("*.py"):
            for line in module.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{module.name} imports {token}"
