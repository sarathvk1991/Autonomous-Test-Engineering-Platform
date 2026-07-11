"""Strategy V1 — Deterministic Text Matching.

The first production ``GroundingStrategy``. It reads three governed things — a
:class:`MatchingNormalizer` (how to preprocess), a :class:`MatchingPolicy` (what
constitutes a match), and a canonical :class:`MatchingRequest` (the evidence) — and
returns a canonical :class:`MatchResult`. It owns comparison only: no classification,
no confidence, no metrics, no runtime models.

Determinism
-----------
A pure function of ``(request, policy, normalizer configuration)``. No randomness,
timestamps, UUIDs, AI, embeddings, semantic search, ML, or external libraries. The
evidence corpus is consumed in its given canonical order and every ordering is
resolved by the governed :class:`MatchingTieBreaker`, so identical inputs always
produce an equal ``MatchResult``.

Scoring is governed entirely by :class:`MatchingWeights` and thresholds by
:class:`MatchingThresholds`; nothing is hard-coded. ``MatchingEvidence`` (frozen at
CAP-077A.2) carries five text fields — title, description, tags, component, location
(the endpoint) — so V1 maps the policy's field weights onto those; ``rule_key_weight``
is reserved (rule keys appear inside the title) until the evidence shape gains a
dedicated field.
"""

from __future__ import annotations

from dataclasses import dataclass

from requirement_intelligence.grounding.identity import MatchingStrategyVersion
from requirement_intelligence.grounding.matching.enums import MatchRankingKey, MatchTieBreaker
from requirement_intelligence.grounding.matching.policy import MatchingPolicy
from requirement_intelligence.grounding.models.enums import EvidenceRelation
from requirement_intelligence.grounding.models.evidence import (
    EvidenceReference,
    RequirementEvidenceLink,
)
from requirement_intelligence.grounding.models.match_result import (
    MatchExplanation,
    MatchResult,
    MatchStatistics,
)
from requirement_intelligence.grounding.models.matching import (
    MatchingEvidence,
    MatchingRequest,
)
from requirement_intelligence.grounding.normalization.normalizer import MatchingNormalizer

#: The permanent identity of Strategy V1. Future strategies (semantic, hybrid,
#: citation) take their own identities; they never mutate this one.
STRATEGY_NAME = "deterministic_text_v1"
STRATEGY_VERSION = MatchingStrategyVersion(1, 0, 0)


@dataclass(frozen=True)
class _Candidate:
    """One evaluated (requirement, evidence) pair, before ranking."""

    reference: EvidenceReference
    relation: EvidenceRelation
    score: int
    exact_terms: int
    token_overlap: int
    matched_terms: tuple[str, ...]
    matched_fields: tuple[str, ...]


class DeterministicTextMatchingStrategy:
    """Compare a requirement to evidence by governed, deterministic text overlap."""

    def __init__(self, normalizer: MatchingNormalizer, policy: MatchingPolicy) -> None:
        """Bind the governed normalizer and matching policy this strategy applies."""
        self._normalizer = normalizer
        self._policy = policy

    @property
    def name(self) -> str:
        """The permanent strategy name."""
        return STRATEGY_NAME

    def match(self, request: MatchingRequest) -> MatchResult:
        """Return the canonical :class:`MatchResult` for one :class:`MatchingRequest`."""
        requirement = request.requirement
        req_tokens = self._token_values(requirement.text)
        norm_ops = self._normalization_ops(requirement.text)

        candidates: list[_Candidate] = []
        rejected: list[EvidenceReference] = []
        matched_terms_all: set[str] = set()

        for evidence in request.evidence:
            candidate, ops = self._evaluate(requirement.domain, req_tokens, evidence)
            norm_ops += ops
            if candidate is None:
                rejected.append(_reference(evidence))
            else:
                candidates.append(candidate)
                matched_terms_all.update(candidate.matched_terms)

        ranked = self._rank(candidates)
        links = tuple(self._to_link(candidate) for candidate in ranked)

        exact_evidence = sum(1 for candidate in ranked if candidate.exact_terms > 0)
        statistics = MatchStatistics(
            evidence_examined=len(request.evidence),
            evidence_matched=len(ranked),
            evidence_rejected=len(rejected),
            matched_term_count=len(matched_terms_all),
            exact_matches=exact_evidence,
            partial_matches=len(ranked) - exact_evidence,
            normalization_operations=norm_ops,
        )
        explanation = self._explain(req_tokens, ranked, tuple(rejected), norm_ops)
        return MatchResult(
            context_id=request.context_id,
            requirement=requirement,
            links=links,
            statistics=statistics,
            explanation=explanation,
            strategy_name=STRATEGY_NAME,
            strategy_version=str(STRATEGY_VERSION),
        )

    # -- evaluation --------------------------------------------------------

    def _evaluate(
        self, requirement_domain: str, req_tokens: tuple[str, ...], evidence: MatchingEvidence
    ) -> tuple[_Candidate | None, int]:
        """Score one evidence item; return a candidate (or ``None``) and normalization ops."""
        weights = self._policy.weights
        fields = (
            ("title", evidence.title, weights.title_weight),
            ("description", evidence.description or "", weights.description_weight),
            ("tags", " ".join(evidence.tags), weights.tag_weight),
            ("component", evidence.component or "", weights.component_weight),
            ("endpoint", evidence.location or "", weights.endpoint_weight),
        )

        score = 0
        ops = 0
        exact_hits: set[str] = set()
        partial_hits: set[str] = set()
        matched_fields: list[str] = []
        req_token_set = set(req_tokens)

        for field_name, field_text, weight in fields:
            field_tokens = set(self._token_values(field_text))
            ops += self._normalization_ops(field_text)
            field_exact = req_token_set & field_tokens
            field_partial = {
                token
                for token in req_token_set
                if token not in field_tokens
                and any(token in other or other in token for other in field_tokens)
            }
            if field_exact or field_partial:
                matched_fields.append(field_name)
            for token in field_exact:
                score += weight + weights.exact_token_bonus
                exact_hits.add(token)
            for token in field_partial:
                score += weights.partial_token_bonus
                partial_hits.add(token)

        matched = [token for token in req_tokens if token in exact_hits or token in partial_hits]
        exact_terms = len(exact_hits)
        token_overlap = len(matched)
        score = min(100, score)

        relation = self._relation(requirement_domain, evidence, exact_terms)
        if relation is None:
            return None, ops
        if not self._passes_thresholds(score, token_overlap, exact_terms):
            return None, ops

        return (
            _Candidate(
                reference=_reference(evidence),
                relation=relation,
                score=score,
                exact_terms=exact_terms,
                token_overlap=token_overlap,
                matched_terms=tuple(matched),
                matched_fields=tuple(matched_fields),
            ),
            ops,
        )

    def _relation(
        self, requirement_domain: str, evidence: MatchingEvidence, exact_terms: int
    ) -> EvidenceRelation | None:
        """Resolve the governed relation for a match, or ``None`` if the policy forbids it."""
        policy = self._policy
        partial_only = exact_terms == 0
        if partial_only and not policy.allow_partial_matching:
            return None
        cross_domain = str(evidence.reference.source_category) != str(requirement_domain)
        if cross_domain:
            if not policy.allow_cross_domain_matching:
                return None
            return EvidenceRelation.CORROBORATING
        if partial_only:
            return EvidenceRelation.PARTIAL
        return EvidenceRelation.DIRECT

    def _passes_thresholds(self, score: int, token_overlap: int, exact_terms: int) -> bool:
        """Honour the governed thresholds; a link exists only when all are cleared."""
        thresholds = self._policy.thresholds
        return (
            score >= thresholds.minimum_match_score
            and token_overlap >= thresholds.minimum_token_overlap
            and exact_terms >= thresholds.minimum_exact_terms
        )

    # -- ranking -----------------------------------------------------------

    def _rank(self, candidates: list[_Candidate]) -> list[_Candidate]:
        """Order candidates by the governed ranking keys, then the tie-breaker."""
        ordered = list(candidates)
        tie = self._policy.tie_breaker
        ordered.sort(key=self._tie_value(tie.key), reverse=not tie.ascending)
        ordered.sort(key=self._ranking_key)
        return ordered

    def _ranking_key(self, candidate: _Candidate) -> tuple[int, ...]:
        """Descending sort key over the policy's ranking keys (via negation)."""
        parts: list[int] = []
        for key in self._policy.ranking.keys:
            if key == MatchRankingKey.MATCH_SCORE:
                parts.append(-candidate.score)
            elif key == MatchRankingKey.EXACT_TERMS:
                parts.append(-candidate.exact_terms)
            elif key == MatchRankingKey.TOKEN_OVERLAP:
                parts.append(-candidate.token_overlap)
            else:  # SOURCE_DIVERSITY — not meaningful per single-evidence link
                parts.append(0)
        return tuple(parts)

    @staticmethod
    def _tie_value(key: MatchTieBreaker):  # type: ignore[no-untyped-def]
        """Return a sort key function for the governed tie-breaker."""
        if key == MatchTieBreaker.SOURCE_SYSTEM:
            return lambda candidate: str(candidate.reference.source_system)
        return lambda candidate: candidate.reference.source_record_id

    # -- projection --------------------------------------------------------

    def _to_link(self, candidate: _Candidate) -> RequirementEvidenceLink:
        """Project a ranked candidate into a canonical link with a deterministic rationale."""
        partial = candidate.token_overlap - candidate.exact_terms
        rationale = (
            f"Matched {candidate.token_overlap} term(s) in field(s) "
            f"{list(candidate.matched_fields)}; {candidate.exact_terms} exact, "
            f"{partial} partial; score {candidate.score}."
        )
        return RequirementEvidenceLink(
            evidence=candidate.reference,
            relation=candidate.relation,
            match_score=candidate.score,
            matched_terms=candidate.matched_terms,
            rationale=rationale,
        )

    def _explain(
        self,
        req_tokens: tuple[str, ...],
        ranked: list[_Candidate],
        rejected: tuple[EvidenceReference, ...],
        norm_ops: int,
    ) -> MatchExplanation:
        """Build the deterministic, judgement-free matcher explanation."""
        matched = {token for candidate in ranked for token in candidate.matched_terms}
        unmatched = tuple(token for token in req_tokens if token not in matched)
        exact = sum(1 for candidate in ranked if candidate.exact_terms > 0)
        summary = (
            f"Examined {len(ranked) + len(rejected)} evidence item(s); "
            f"matched {len(ranked)} ({exact} exact, {len(ranked) - exact} partial)."
        )
        notes = (
            f"Ranking keys: {[str(key) for key in self._policy.ranking.keys]}.",
            f"Tie-breaker: {self._policy.tie_breaker.key} "
            f"({'asc' if self._policy.tie_breaker.ascending else 'desc'}).",
            f"Normalization operations: {norm_ops}.",
        )
        return MatchExplanation(
            summary=summary,
            matched_terms=tuple(sorted(matched)),
            unmatched_terms=unmatched,
            rejected_evidence=rejected,
            notes=notes,
        )

    # -- normalization helpers --------------------------------------------

    def _token_values(self, text: str) -> tuple[str, ...]:
        """Normalize *text* and return its token values, order preserved and de-duplicated."""
        seen: set[str] = set()
        values: list[str] = []
        for token in self._normalizer.normalize(text).tokens:
            if token.value not in seen:
                seen.add(token.value)
                values.append(token.value)
        return tuple(values)

    def _normalization_ops(self, text: str) -> int:
        """Total pure normalization observations for one text (an auditable count)."""
        stats = self._normalizer.normalize(text).statistics
        return (
            stats.punctuation_removed
            + stats.case_conversions
            + stats.separators_normalized
            + stats.stop_words_removed
        )


def _reference(evidence: MatchingEvidence) -> EvidenceReference:
    """The stable identity of one evidence item."""
    return evidence.reference
