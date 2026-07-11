"""Unit tests for the CAP-077B.1 matching-contract freeze.

Covers the MatchResult schema version, the structured evaluation summary, the
match-score semantics documentation, and the frozen Matching↔Classification
architectural boundary.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from requirement_intelligence.grounding import (
    MATCH_RESULT_VERSION,
    DeterministicTextMatchingStrategy,
    EvidenceReference,
    MatchEvaluationSummary,
    MatchExplanation,
    MatchingEvidence,
    MatchingRequest,
    MatchingRequirement,
    MatchResult,
    MatchResultVersion,
    MatchStatistics,
    default_grounding_configuration,
    default_matching_policy,
)
from requirement_intelligence.grounding.identity import (
    GroundedRequirementId,
    MatchingStrategyVersion,
)
from requirement_intelligence.grounding.normalization import DefaultMatchingNormalizer
from requirement_intelligence.models.enums import SourceCategory, SourceSystem, SourceType

_GROUNDING_DIR = Path(
    __import__("requirement_intelligence.grounding", fromlist=["__file__"]).__file__
).parent


def _requirement(text: str = "set nosniff header") -> MatchingRequirement:
    return MatchingRequirement(
        requirement_id=GroundedRequirementId.for_requirement(SourceCategory.SECURITY, text),
        domain=SourceCategory.SECURITY,
        text=text,
        position=0,
    )


def _match_result() -> MatchResult:
    return MatchResult(
        context_id="ctx-x",
        requirement=_requirement(),
        links=(),
        statistics=MatchStatistics(
            evidence_examined=0, evidence_matched=0, evidence_rejected=0, matched_term_count=0
        ),
        explanation=MatchExplanation(),
        strategy_name="deterministic_text_v1",
        strategy_version="1.0.0",
    )


def _run_strategy() -> MatchResult:
    strategy = DeterministicTextMatchingStrategy(
        normalizer=DefaultMatchingNormalizer(), policy=default_matching_policy()
    )
    config = default_grounding_configuration()
    evidence = (
        MatchingEvidence(
            reference=EvidenceReference(
                source_system=SourceSystem.OWASP_ZAP,
                source_record_id="10021",
                source_category=SourceCategory.SECURITY,
                source_type=SourceType.DAST,
            ),
            title="nosniff header",
        ),
    )
    request = MatchingRequest(
        context_id="ctx-x",
        requirement=_requirement(),
        evidence=evidence,
        configuration=config,
        framework_version=config.framework_version,
        configuration_version=config.version,
    )
    return strategy.match(request)


@pytest.mark.unit
class TestMatchResultVersion:
    def test_default_result_version(self) -> None:
        assert _match_result().result_version == MATCH_RESULT_VERSION
        assert isinstance(_match_result().result_version, MatchResultVersion)

    def test_result_version_serialises_and_round_trips(self) -> None:
        dumped = _match_result().model_dump(mode="json", by_alias=True)
        assert dumped["resultVersion"] == str(MATCH_RESULT_VERSION)
        assert MatchResult.model_validate(dumped) == _match_result()

    def test_schema_version_is_independent_of_strategy_version(self) -> None:
        # Distinct types with distinct meaning: same numbers must not compare equal.
        assert MatchResultVersion(1, 0, 0) != MatchingStrategyVersion(1, 0, 0)

    def test_is_immutable(self) -> None:
        with pytest.raises(ValidationError):
            _match_result().result_version = MatchResultVersion(2, 0, 0)  # type: ignore[misc]


@pytest.mark.unit
class TestEvaluationSummary:
    def test_constructs_and_serialises(self) -> None:
        summary = MatchEvaluationSummary(
            evidence_examined=3,
            evidence_matched=1,
            highest_score=40,
            threshold_summary="min_score=1",
            ranking_summary="keys=[match_score]",
        )
        dumped = summary.model_dump(mode="json", by_alias=True)
        assert dumped["highestScore"] == 40
        assert MatchEvaluationSummary.model_validate(dumped) == summary

    def test_is_immutable(self) -> None:
        summary = MatchEvaluationSummary(
            evidence_examined=1,
            evidence_matched=1,
            highest_score=1,
            threshold_summary="t",
            ranking_summary="r",
        )
        with pytest.raises(ValidationError):
            summary.highest_score = 2  # type: ignore[misc]

    def test_strategy_populates_evaluation_summary(self) -> None:
        result = _run_strategy()
        summary = result.explanation.evaluation_summary
        assert summary is not None
        assert summary.evidence_examined == 1
        assert summary.evidence_matched == 1
        assert summary.highest_score == result.links[0].match_score
        assert summary.winning_evidence == result.links[0].evidence
        assert "min_score" in summary.threshold_summary
        assert "tie_breaker" in summary.ranking_summary

    def test_explainability_invariant_self_contained(self) -> None:
        """A MatchResult explains itself fully — no need to re-run the strategy."""
        result = _run_strategy()
        assert result.explanation.evaluation_summary is not None
        assert result.statistics.evidence_examined == 1
        for link in result.links:
            assert link.matched_terms
            assert link.rationale


@pytest.mark.unit
class TestMatchScoreSemantics:
    def test_match_score_description_disclaims_confidence(self) -> None:
        from requirement_intelligence.grounding.models.evidence import RequirementEvidenceLink

        description = RequirementEvidenceLink.model_fields["match_score"].description or ""
        assert "similarity" in description.lower()
        assert "confidence" in description.lower()  # names it to disclaim it


@pytest.mark.unit
class TestMatchingClassificationBoundary:
    def test_match_result_is_self_contained(self) -> None:
        """MatchResult imports no strategy, normalizer, or policy — it is the frozen contract."""
        source = (_GROUNDING_DIR / "models" / "match_result.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "strateg" not in line
                assert "normaliz" not in line
                assert "policy" not in line

    def test_matching_layer_does_not_import_classification(self) -> None:
        """The matching layer must never depend on Classification (CAP-077C consumes it)."""
        layers = ("strategies", "normalization", "matching")
        for layer in layers:
            for module in (_GROUNDING_DIR / layer).glob("*.py"):
                for line in module.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith(("import ", "from ")):
                        assert "classification" not in line.lower()
