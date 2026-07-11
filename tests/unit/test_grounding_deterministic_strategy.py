"""Unit tests for Strategy V1 — Deterministic Text Matching (CAP-077B).

Covers the full normalizer's advanced flags, the matching algorithm (exact/partial/
multi-field/cross-domain/threshold/ranking/tie-breaking), governed scoring, strategy
identity/version stamping, determinism, explainability, and the boundary that the
strategy depends only on canonical grounding models.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from requirement_intelligence.grounding import (
    DeterministicTextMatchingStrategy,
    EvidenceReference,
    GroundingStrategy,
    MatchingEvidence,
    MatchingPolicy,
    MatchingRanking,
    MatchingRequest,
    MatchingRequirement,
    MatchingThresholds,
    MatchingTieBreaker,
    MatchingWeights,
    NormalizationConfiguration,
    default_grounding_configuration,
    default_matching_policy,
)
from requirement_intelligence.grounding.identity import (
    GroundedRequirementId,
    MatchingPolicyId,
    MatchingPolicyVersion,
)
from requirement_intelligence.grounding.matching import MatchRankingKey, MatchTieBreaker
from requirement_intelligence.grounding.models.enums import EvidenceRelation
from requirement_intelligence.grounding.normalization import DefaultMatchingNormalizer
from requirement_intelligence.grounding.strategies.deterministic_text_strategy import (
    STRATEGY_NAME,
    STRATEGY_VERSION,
)
from requirement_intelligence.models.enums import SourceCategory, SourceSystem, SourceType

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _evidence(
    record_id: str,
    *,
    title: str,
    category: SourceCategory = SourceCategory.SECURITY,
    system: SourceSystem = SourceSystem.OWASP_ZAP,
    source_type: SourceType = SourceType.DAST,
    description: str | None = None,
    tags: tuple[str, ...] = (),
    component: str | None = None,
    location: str | None = None,
) -> MatchingEvidence:
    return MatchingEvidence(
        reference=EvidenceReference(
            source_system=system,
            source_record_id=record_id,
            source_category=category,
            source_type=source_type,
        ),
        title=title,
        description=description,
        tags=tags,
        component=component,
        location=location,
    )


def _request(
    text: str,
    evidence: tuple[MatchingEvidence, ...],
    *,
    domain: SourceCategory = SourceCategory.SECURITY,
) -> MatchingRequest:
    config = default_grounding_configuration()
    return MatchingRequest(
        context_id="ctx-test",
        requirement=MatchingRequirement(
            requirement_id=GroundedRequirementId.for_requirement(domain, text),
            domain=domain,
            text=text,
            position=0,
        ),
        evidence=evidence,
        configuration=config,
        framework_version=config.framework_version,
        configuration_version=config.version,
    )


def _policy(
    *,
    thresholds: MatchingThresholds | None = None,
    weights: MatchingWeights | None = None,
    ranking: MatchingRanking | None = None,
    tie_breaker: MatchingTieBreaker | None = None,
    allow_cross_domain: bool = True,
    allow_partial: bool = True,
) -> MatchingPolicy:
    return MatchingPolicy(
        policy_id=MatchingPolicyId("test-policy"),
        policy_version=MatchingPolicyVersion(1, 0, 0),
        description="test policy",
        thresholds=thresholds or MatchingThresholds(minimum_match_score=1, minimum_token_overlap=1),
        weights=weights or MatchingWeights(title_weight=5, tag_weight=3, exact_token_bonus=2),
        ranking=ranking or MatchingRanking(keys=(MatchRankingKey.MATCH_SCORE,)),
        tie_breaker=tie_breaker or MatchingTieBreaker(key=MatchTieBreaker.SOURCE_RECORD_ID),
        allow_cross_domain_matching=allow_cross_domain,
        allow_partial_matching=allow_partial,
    )


def _strategy(policy: MatchingPolicy | None = None) -> DeterministicTextMatchingStrategy:
    return DeterministicTextMatchingStrategy(
        normalizer=DefaultMatchingNormalizer(),
        policy=policy or default_matching_policy(),
    )


# --------------------------------------------------------------------------- #
# Normalizer — advanced flags
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestFullNormalizer:
    def _tokens(self, text: str, **flags: bool) -> list[str]:
        config = NormalizationConfiguration(**flags)
        return [t.value for t in DefaultMatchingNormalizer(config).normalize(text).tokens]

    def test_separator_normalization_splits_camel_and_symbols(self) -> None:
        tokens = self._tokens("authHandler content-type_options")
        assert tokens == ["auth", "handler", "content", "type", "options"]

    def test_punctuation_removal(self) -> None:
        result = DefaultMatchingNormalizer().normalize("hello, world! (test)")
        assert [t.value for t in result.tokens] == ["hello", "world", "test"]
        assert result.statistics.punctuation_removed >= 3

    def test_stop_word_removal(self) -> None:
        tokens = self._tokens("the user must be able to log in", remove_stop_words=True)
        assert "the" not in tokens and "to" not in tokens
        assert "user" in tokens and "log" in tokens

    def test_duplicate_removal(self) -> None:
        tokens = self._tokens("token token token unique", deduplicate_tokens=True)
        assert tokens == ["token", "unique"]

    def test_abbreviation_expansion(self) -> None:
        tokens = self._tokens("auth config", expand_abbreviations=True)
        assert tokens == ["authentication", "configuration"]

    def test_statistics_are_populated(self) -> None:
        config = NormalizationConfiguration(remove_stop_words=True)
        stats = DefaultMatchingNormalizer(config).normalize("The Auth-Handler, please").statistics
        assert stats.case_conversions > 0
        assert stats.separators_normalized > 0
        assert stats.punctuation_removed > 0
        assert stats.stop_words_removed >= 1
        assert stats.tokens_produced == 3  # auth, handler, please ("the" dropped as a stop word)


# --------------------------------------------------------------------------- #
# Matching algorithm
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestMatchingAlgorithm:
    def test_exact_token_match_produces_direct_link(self) -> None:
        request = _request("set the nosniff header", (_evidence("A", title="nosniff header"),))
        result = _strategy().match(request)
        assert len(result.links) == 1
        assert result.links[0].relation == EvidenceRelation.DIRECT
        assert "nosniff" in result.links[0].matched_terms

    def test_partial_token_match(self) -> None:
        # "auth" is a substring of "authentication" → partial, not exact. The default
        # policy gives partial matches a bonus, so the link clears the threshold.
        request = _request("auth", (_evidence("A", title="authentication handler"),))
        result = _strategy().match(request)
        assert len(result.links) == 1
        assert result.links[0].relation == EvidenceRelation.PARTIAL

    def test_multi_field_match_scores_higher(self) -> None:
        both = _evidence("A", title="nosniff", tags=("header",))
        one = _evidence("B", title="nosniff")
        result = _strategy().match(_request("nosniff header", (both, one)))
        scores = {link.evidence.source_record_id: link.match_score for link in result.links}
        assert scores["A"] > scores["B"]

    def test_cross_domain_link_is_corroborating(self) -> None:
        evidence = (
            _evidence(
                "F",
                title="inventory login",
                category=SourceCategory.FUNCTIONAL,
                system=SourceSystem.JIRA,
                source_type=SourceType.STORY,
            ),
        )
        result = _strategy().match(_request("login inventory", evidence))
        assert result.links[0].relation == EvidenceRelation.CORROBORATING

    def test_cross_domain_rejected_when_policy_forbids(self) -> None:
        policy = _policy(allow_cross_domain=False)
        evidence = (
            _evidence(
                "F",
                title="inventory login",
                category=SourceCategory.FUNCTIONAL,
                system=SourceSystem.JIRA,
                source_type=SourceType.STORY,
            ),
        )
        result = _strategy(policy).match(_request("login inventory", evidence))
        assert result.links == ()
        assert result.statistics.evidence_rejected == 1

    def test_threshold_rejection(self) -> None:
        policy = _policy(thresholds=MatchingThresholds(minimum_match_score=99))
        request = _request("nosniff", (_evidence("A", title="nosniff"),))
        result = _strategy(policy).match(request)
        assert result.links == ()
        assert result.statistics.evidence_matched == 0

    def test_partial_rejected_when_policy_forbids(self) -> None:
        policy = _policy(allow_partial=False)
        request = _request("auth", (_evidence("A", title="authentication"),))
        result = _strategy(policy).match(request)
        assert result.links == ()

    def test_ranking_by_score_descending(self) -> None:
        strong = _evidence("S", title="nosniff header options")
        weak = _evidence("W", title="header")
        result = _strategy().match(_request("nosniff header options", (weak, strong)))
        assert [link.evidence.source_record_id for link in result.links] == ["S", "W"]

    def test_tie_breaking_by_source_record_id(self) -> None:
        # Identical title ⇒ identical score/overlap ⇒ tie broken by record id ascending.
        e_b = _evidence("B", title="nosniff")
        e_a = _evidence("A", title="nosniff")
        result = _strategy().match(_request("nosniff", (e_b, e_a)))
        assert [link.evidence.source_record_id for link in result.links] == ["A", "B"]


# --------------------------------------------------------------------------- #
# Governed scoring
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestGovernedScoring:
    def test_weights_drive_the_score(self) -> None:
        low = _policy(weights=MatchingWeights(title_weight=1))
        high = _policy(weights=MatchingWeights(title_weight=10))
        request = _request("nosniff", (_evidence("A", title="nosniff"),))
        assert (
            _strategy(high).match(request).links[0].match_score
            > _strategy(low).match(request).links[0].match_score
        )

    def test_zero_weights_still_deterministic(self) -> None:
        policy = _policy(
            weights=MatchingWeights(),
            thresholds=MatchingThresholds(minimum_match_score=0, minimum_token_overlap=1),
        )
        request = _request("nosniff", (_evidence("A", title="nosniff"),))
        result = _strategy(policy).match(request)
        assert result.links[0].match_score == 0


# --------------------------------------------------------------------------- #
# Strategy identity, determinism, explainability
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestStrategyIdentityAndDeterminism:
    def test_is_a_grounding_strategy(self) -> None:
        assert isinstance(_strategy(), GroundingStrategy)
        assert _strategy().name == STRATEGY_NAME == "deterministic_text_v1"

    def test_stamps_identity_and_version(self) -> None:
        result = _strategy().match(_request("nosniff", (_evidence("A", title="nosniff"),)))
        assert result.strategy_name == STRATEGY_NAME
        assert result.strategy_version == str(STRATEGY_VERSION)

    def test_identical_input_produces_identical_result(self) -> None:
        request = _request(
            "nosniff header options",
            (_evidence("A", title="nosniff header"), _evidence("B", title="options")),
        )
        assert _strategy().match(request) == _strategy().match(request)

    def test_statistics_reconcile(self) -> None:
        request = _request(
            "nosniff",
            (_evidence("A", title="nosniff"), _evidence("Z", title="unrelated content")),
        )
        stats = _strategy().match(request).statistics
        assert stats.evidence_examined == 2
        assert stats.evidence_matched + stats.evidence_rejected == 2
        assert stats.exact_matches + stats.partial_matches == stats.evidence_matched


@pytest.mark.unit
class TestExplainability:
    def test_link_explains_itself(self) -> None:
        result = _strategy().match(_request("nosniff header", (_evidence("A", title="nosniff"),)))
        link = result.links[0]
        assert link.matched_terms
        assert str(link.match_score) in link.rationale
        assert str(link.relation) in {"direct", "partial", "corroborating"}

    def test_result_explanation_lists_examined_matched_rejected(self) -> None:
        request = _request(
            "nosniff",
            (_evidence("A", title="nosniff"), _evidence("Z", title="unrelated")),
        )
        result = _strategy().match(request)
        assert "Examined 2" in result.explanation.summary
        assert result.explanation.rejected_evidence  # Z rejected
        assert any("Normalization operations" in note for note in result.explanation.notes)

    def test_unmatched_terms_reported(self) -> None:
        result = _strategy().match(
            _request("nosniff absentterm", (_evidence("A", title="nosniff"),))
        )
        assert "absentterm" in result.explanation.unmatched_terms


# --------------------------------------------------------------------------- #
# Boundary — no runtime model leakage
# --------------------------------------------------------------------------- #


@pytest.mark.unit
class TestStrategyBoundary:
    def test_strategy_imports_only_canonical_grounding_models(self) -> None:
        import requirement_intelligence.grounding.strategies.deterministic_text_strategy as module

        text = Path(module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "context_orchestration",
            "EngineeringContext",
            "AnalysisResult",
            "analysis_models",
            "validation",
            "cp1",
            "SupportClassification",
            "GroundingConfidence",
        ):
            for line in text.splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert forbidden not in line
