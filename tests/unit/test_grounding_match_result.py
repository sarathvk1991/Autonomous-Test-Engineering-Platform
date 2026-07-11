"""Unit tests for the canonical matching output model (CAP-077A.3).

Pin the permanent GroundingStrategy result contract: MatchResult construction,
immutability, serialization, equality, the MatchStatistics coherence invariants,
MatchExplanation construction, and the frozen ``match -> MatchResult`` signature.
No matching is executed; the strategy remains unimplemented.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from requirement_intelligence.grounding import (
    EvidenceReference,
    GroundingStrategy,
    MatchExplanation,
    MatchingRequirement,
    MatchResult,
    MatchStatistics,
    RequirementEvidenceLink,
)
from requirement_intelligence.grounding.identity import GroundedRequirementId
from requirement_intelligence.grounding.models.enums import EvidenceRelation
from requirement_intelligence.models.enums import SourceCategory, SourceSystem, SourceType


def _reference() -> EvidenceReference:
    return EvidenceReference(
        source_system=SourceSystem.OWASP_ZAP,
        source_record_id="10021",
        source_category=SourceCategory.SECURITY,
        source_type=SourceType.DAST,
    )


def _requirement(text: str = "Set the nosniff header.") -> MatchingRequirement:
    return MatchingRequirement(
        requirement_id=GroundedRequirementId.for_requirement(SourceCategory.SECURITY, text),
        domain=SourceCategory.SECURITY,
        text=text,
        position=0,
    )


def _link() -> RequirementEvidenceLink:
    return RequirementEvidenceLink(
        evidence=_reference(),
        relation=EvidenceRelation.DIRECT,
        match_score=90,
        matched_terms=("nosniff",),
        rationale="names the missing header",
    )


def _statistics() -> MatchStatistics:
    return MatchStatistics(
        evidence_examined=3,
        evidence_matched=1,
        evidence_rejected=2,
        matched_term_count=1,
        exact_matches=1,
        partial_matches=0,
    )


def _result() -> MatchResult:
    return MatchResult(
        context_id="ctx-auth-abc",
        requirement=_requirement(),
        links=(_link(),),
        statistics=_statistics(),
        explanation=MatchExplanation(summary="one direct match", matched_terms=("nosniff",)),
        strategy_name="deterministic-text",
        strategy_version="1.0.0",
    )


@pytest.mark.unit
class TestMatchStatistics:
    def test_constructs_pure_observations(self) -> None:
        stats = _statistics()
        assert stats.evidence_examined == 3
        assert stats.evidence_matched == 1

    def test_matched_cannot_exceed_examined(self) -> None:
        with pytest.raises(ValidationError):
            MatchStatistics(
                evidence_examined=1,
                evidence_matched=2,
                evidence_rejected=0,
                matched_term_count=0,
            )

    def test_exact_plus_partial_cannot_exceed_matched(self) -> None:
        with pytest.raises(ValidationError):
            MatchStatistics(
                evidence_examined=5,
                evidence_matched=2,
                evidence_rejected=0,
                matched_term_count=3,
                exact_matches=2,
                partial_matches=1,
            )


@pytest.mark.unit
class TestMatchExplanation:
    def test_constructs_with_defaults(self) -> None:
        explanation = MatchExplanation()
        assert explanation.summary == ""
        assert explanation.matched_terms == ()
        assert explanation.rejected_evidence == ()

    def test_carries_rejected_evidence(self) -> None:
        explanation = MatchExplanation(rejected_evidence=(_reference(),), notes=("low overlap",))
        assert explanation.rejected_evidence[0].source_record_id == "10021"


@pytest.mark.unit
class TestMatchResult:
    def test_constructs(self) -> None:
        result = _result()
        assert result.strategy_name == "deterministic-text"
        assert len(result.links) == 1

    def test_is_immutable(self) -> None:
        result = _result()
        with pytest.raises(ValidationError):
            result.strategy_name = "other"  # type: ignore[misc]

    def test_empty_links_is_valid(self) -> None:
        result = MatchResult(
            context_id="ctx",
            requirement=_requirement(),
            links=(),
            statistics=MatchStatistics(
                evidence_examined=3,
                evidence_matched=0,
                evidence_rejected=3,
                matched_term_count=0,
            ),
            explanation=MatchExplanation(unmatched_terms=("nosniff",)),
            strategy_name="deterministic-text",
            strategy_version="1.0.0",
        )
        assert result.links == ()

    def test_serialises_camel_case_and_round_trips(self) -> None:
        result = _result()
        dumped = result.model_dump(mode="json", by_alias=True)
        assert "strategyName" in dumped
        assert "contextId" in dumped
        assert MatchResult.model_validate(dumped) == result

    def test_deterministic_equality(self) -> None:
        assert _result() == _result()


@pytest.mark.unit
class TestFrozenStrategyContract:
    def test_match_returns_match_result(self) -> None:
        sig = inspect.signature(GroundingStrategy.match)
        assert list(sig.parameters) == ["self", "request"]
        assert sig.return_annotation == "MatchResult"
