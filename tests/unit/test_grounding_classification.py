"""Unit tests for the Support Classification framework (CAP-077C).

Covers classification precedence (all six verdicts), the governed policy (versioning,
immutability, builder determinism), the ClassificationResult model, PlatformContext
registration, version independence, and the frozen boundary that Classification consumes
only a MatchResult.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.grounding import (
    CLASSIFICATION_POLICY_VERSION,
    CLASSIFICATION_VERSION,
    ClassificationPolicy,
    ClassificationPolicyBuilder,
    ClassificationPolicyId,
    ClassificationPolicyVersion,
    ClassificationResult,
    ClassificationThresholds,
    ClassificationVersion,
    EvidenceReference,
    EvidenceRelation,
    MatchExplanation,
    MatchingRequirement,
    MatchResult,
    MatchResultVersion,
    MatchStatistics,
    RequirementEvidenceLink,
    SupportClassification,
    SupportClassificationEngine,
    default_classification_policy,
)
from requirement_intelligence.grounding.identity import GroundedRequirementId
from requirement_intelligence.models.enums import SourceCategory, SourceSystem, SourceType

_GROUNDING_DIR = Path(
    __import__("requirement_intelligence.grounding", fromlist=["__file__"]).__file__
).parent


def _reference(record_id: str = "10021") -> EvidenceReference:
    return EvidenceReference(
        source_system=SourceSystem.OWASP_ZAP,
        source_record_id=record_id,
        source_category=SourceCategory.SECURITY,
        source_type=SourceType.DAST,
    )


def _link(
    relation: EvidenceRelation, score: int, record_id: str = "10021"
) -> RequirementEvidenceLink:
    return RequirementEvidenceLink(
        evidence=_reference(record_id),
        relation=relation,
        match_score=score,
        matched_terms=("nosniff",),
        rationale="test link",
    )


def _match_result(
    *, links: tuple[RequirementEvidenceLink, ...] = (), examined: int = 0
) -> MatchResult:
    matched = len(links)
    return MatchResult(
        context_id="ctx",
        requirement=MatchingRequirement(
            requirement_id=GroundedRequirementId.for_requirement(SourceCategory.SECURITY, "req"),
            domain=SourceCategory.SECURITY,
            text="req",
            position=0,
        ),
        links=links,
        statistics=MatchStatistics(
            evidence_examined=max(examined, matched),
            evidence_matched=matched,
            evidence_rejected=max(examined, matched) - matched,
            matched_term_count=1 if matched else 0,
            exact_matches=matched,
        ),
        explanation=MatchExplanation(),
        strategy_name="deterministic_text_v1",
        strategy_version="1.0.0",
    )


def _classify(match_result: MatchResult) -> ClassificationResult:
    return SupportClassificationEngine(default_classification_policy()).classify(match_result)


@pytest.mark.unit
class TestClassificationPrecedence:
    def test_supported(self) -> None:
        result = _classify(_match_result(links=(_link(EvidenceRelation.DIRECT, 40),)))
        assert result.support_classification == SupportClassification.SUPPORTED

    def test_partially_supported(self) -> None:
        result = _classify(_match_result(links=(_link(EvidenceRelation.DIRECT, 7),)))
        assert result.support_classification == SupportClassification.PARTIALLY_SUPPORTED

    def test_weakly_supported(self) -> None:
        result = _classify(_match_result(links=(_link(EvidenceRelation.DIRECT, 2),)))
        assert result.support_classification == SupportClassification.WEAKLY_SUPPORTED

    def test_contradicted_takes_precedence(self) -> None:
        links = (
            _link(EvidenceRelation.DIRECT, 40, "A"),
            _link(EvidenceRelation.CONTRADICTING, 30, "B"),
        )
        result = _classify(_match_result(links=links))
        assert result.support_classification == SupportClassification.CONTRADICTED
        assert len(result.contradicting_links) == 1
        assert len(result.supporting_links) == 1

    def test_unknown_when_no_evidence_examined(self) -> None:
        result = _classify(_match_result(links=(), examined=0))
        assert result.support_classification == SupportClassification.UNKNOWN

    def test_unsupported_when_evidence_present_but_unmatched(self) -> None:
        result = _classify(_match_result(links=(), examined=5))
        assert result.support_classification == SupportClassification.UNSUPPORTED

    def test_partial_relation_is_partial_support(self) -> None:
        result = _classify(_match_result(links=(_link(EvidenceRelation.PARTIAL, 6),)))
        assert result.support_classification == SupportClassification.PARTIALLY_SUPPORTED
        assert len(result.partial_links) == 1

    def test_reason_is_deterministic_and_present(self) -> None:
        result = _classify(_match_result(links=(_link(EvidenceRelation.DIRECT, 40),)))
        assert "supported" in result.classification_reason
        assert "examined=" in result.classification_reason


@pytest.mark.unit
class TestDeterminismAndImmutability:
    def test_identical_input_produces_identical_result(self) -> None:
        one = _classify(_match_result(links=(_link(EvidenceRelation.DIRECT, 40),)))
        two = _classify(_match_result(links=(_link(EvidenceRelation.DIRECT, 40),)))
        assert one == two

    def test_result_is_immutable(self) -> None:
        result = _classify(_match_result(links=(_link(EvidenceRelation.DIRECT, 40),)))
        with pytest.raises(ValidationError):
            result.support_classification = SupportClassification.UNKNOWN  # type: ignore[misc]

    def test_result_serialises_and_round_trips(self) -> None:
        result = _classify(_match_result(links=(_link(EvidenceRelation.DIRECT, 40),)))
        dumped = result.model_dump(mode="json", by_alias=True)
        assert dumped["classificationVersion"] == str(CLASSIFICATION_VERSION)
        assert "supportingLinks" in dumped
        assert ClassificationResult.model_validate(dumped) == result

    def test_evidence_links_property_orders_by_role(self) -> None:
        links = (
            _link(EvidenceRelation.DIRECT, 40, "A"),
            _link(EvidenceRelation.CONTRADICTING, 30, "B"),
        )
        result = _classify(_match_result(links=links))
        # supporting first, contradicting after.
        ordered = [link.evidence.source_record_id for link in result.evidence_links]
        assert ordered == ["A", "B"]


@pytest.mark.unit
class TestClassificationPolicy:
    def test_default_is_versioned_and_identified(self) -> None:
        policy = default_classification_policy()
        assert isinstance(policy.policy_id, ClassificationPolicyId)
        assert policy.policy_version == CLASSIFICATION_POLICY_VERSION
        assert isinstance(policy.policy_version, ClassificationPolicyVersion)

    def test_is_immutable(self) -> None:
        with pytest.raises(ValidationError):
            default_classification_policy().contradiction_overrides_support = False  # type: ignore[misc]

    def test_builder_is_deterministic(self) -> None:
        assert ClassificationPolicyBuilder().build() == ClassificationPolicyBuilder().build()

    def test_thresholds_bounded(self) -> None:
        with pytest.raises(ValidationError):
            ClassificationThresholds(supported_min_score=101)

    def test_policy_serialises_and_round_trips(self) -> None:
        policy = default_classification_policy()
        dumped = policy.model_dump(mode="json", by_alias=True)
        assert ClassificationPolicy.model_validate(dumped) == policy


@pytest.mark.unit
class TestVersionIndependence:
    def test_classification_version_distinct_from_match_result_version(self) -> None:
        assert ClassificationVersion(1, 0, 0) != MatchResultVersion(1, 0, 0)

    def test_classification_and_policy_versions_are_distinct_types(self) -> None:
        assert ClassificationVersion(1, 0, 0) != ClassificationPolicyVersion(1, 0, 0)


@pytest.mark.unit
class TestPlatformContextRegistration:
    def test_registers_policy_and_engine(self) -> None:
        from requirement_intelligence.platform.platform_context import PlatformContext

        context = PlatformContext()
        assert isinstance(context.create_classification_policy(), ClassificationPolicy)
        assert isinstance(
            context.create_support_classification_engine(), SupportClassificationEngine
        )


@pytest.mark.unit
class TestClassificationBoundary:
    def test_classification_imports_only_matchresult_not_matching_internals(self) -> None:
        """Classification consumes only MatchResult — never the matcher/normalizer/policy."""
        package_dir = _GROUNDING_DIR / "classification"
        forbidden = (
            "grounding.strategies",
            "grounding.normalization",
            "grounding.matching",
            "grounding.grounding_service",
            "context_orchestration",
            "analysis_models",
            "EngineeringContext",
            "AnalysisResult",
        )
        for module in package_dir.glob("*.py"):
            for line in module.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(("import ", "from ")):
                    for token in forbidden:
                        assert token not in line, f"{module.name} imports {token}"
