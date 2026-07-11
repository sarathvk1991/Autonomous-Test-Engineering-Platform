"""The :class:`SupportClassificationEngine` — deterministic support classification.

It consumes a :class:`MatchResult` and returns a :class:`ClassificationResult`, applying
the governed :class:`ClassificationPolicy`. It performs classification **only**: no
confidence, no metrics, no explanation generation.

Boundary
--------
The engine reads **only** the ``MatchResult`` — its links, their relations and
``match_score``, and its statistics. It never inspects the ``EngineeringContext``,
``AnalysisResult``, ``GroundingStrategy``, ``MatchingNormalizer``, or ``MatchingPolicy``.
Every verdict is a pure, deterministic function of ``(MatchResult, ClassificationPolicy)``.
"""

from __future__ import annotations

from requirement_intelligence.grounding.classification.classification_policy import (
    ClassificationPolicy,
)
from requirement_intelligence.grounding.classification.models import ClassificationResult
from requirement_intelligence.grounding.models.enums import EvidenceRelation, SupportClassification
from requirement_intelligence.grounding.models.evidence import RequirementEvidenceLink
from requirement_intelligence.grounding.models.match_result import MatchResult


def _top_score(links: tuple[RequirementEvidenceLink, ...]) -> int:
    """The highest match score among *links* (0 when empty)."""
    return max((link.match_score for link in links), default=0)


class SupportClassificationEngine:
    """Classify one :class:`MatchResult` under a governed :class:`ClassificationPolicy`."""

    def __init__(self, policy: ClassificationPolicy) -> None:
        """Bind the governed classification policy this engine applies."""
        self._policy = policy

    def classify(self, match_result: MatchResult) -> ClassificationResult:
        """Return the deterministic :class:`ClassificationResult` for *match_result*."""
        policy = self._policy
        links = match_result.links

        supporting = self._select(links, policy.strong_support_relations)
        partial = self._select(links, policy.partial_support_relations)
        derived = self._select(links, policy.weak_support_relations)
        conflicting = self._select(links, policy.conflict_relations)
        categorised = {
            id(link) for group in (supporting, partial, derived, conflicting) for link in group
        }
        unknown = tuple(link for link in links if id(link) not in categorised)

        classification, reason = self._decide(
            match_result=match_result,
            supporting=supporting,
            partial=partial,
            derived=derived,
            conflicting=conflicting,
        )
        return ClassificationResult(
            requirement_id=match_result.requirement.requirement_id,
            support_classification=classification,
            supporting_links=supporting,
            contradicting_links=conflicting,
            partial_links=partial,
            derived_links=derived,
            unknown_links=unknown,
            classification_reason=reason,
        )

    @staticmethod
    def _select(
        links: tuple[RequirementEvidenceLink, ...], relations: tuple[EvidenceRelation, ...]
    ) -> tuple[RequirementEvidenceLink, ...]:
        """Links whose relation is in *relations*, order preserved."""
        allowed = set(relations)
        return tuple(link for link in links if EvidenceRelation(link.relation) in allowed)

    def _decide(
        self,
        *,
        match_result: MatchResult,
        supporting: tuple[RequirementEvidenceLink, ...],
        partial: tuple[RequirementEvidenceLink, ...],
        derived: tuple[RequirementEvidenceLink, ...],
        conflicting: tuple[RequirementEvidenceLink, ...],
    ) -> tuple[SupportClassification, str]:
        """Pick the highest applicable verdict in the policy's precedence order."""
        policy = self._policy
        thresholds = policy.thresholds
        strong_score = _top_score(supporting)
        partial_score = _top_score(partial)
        weak_score = _top_score(derived)
        conflict_score = _top_score(conflicting)
        any_support = bool(supporting or partial or derived)

        conditions: dict[SupportClassification, bool] = {
            SupportClassification.CONTRADICTED: bool(conflicting)
            and conflict_score >= thresholds.contradiction_min_score
            and (policy.contradiction_overrides_support or not supporting),
            SupportClassification.SUPPORTED: bool(supporting)
            and strong_score >= thresholds.supported_min_score,
            SupportClassification.PARTIALLY_SUPPORTED: bool(supporting or partial)
            and max(strong_score, partial_score) >= thresholds.partially_supported_min_score,
            SupportClassification.WEAKLY_SUPPORTED: any_support
            and max(strong_score, partial_score, weak_score)
            >= thresholds.weakly_supported_min_score,
            SupportClassification.UNKNOWN: not any_support
            and not conflicting
            and match_result.statistics.evidence_examined == 0
            and policy.treat_absent_evidence_as_unknown,
            SupportClassification.UNSUPPORTED: not any_support,
        }

        permitted = set(policy.permitted_classifications)
        for candidate in policy.priority_ordering:
            if candidate in permitted and conditions.get(candidate, False):
                return candidate, self._reason(
                    candidate, supporting, partial, derived, conflicting, match_result
                )
        return SupportClassification.UNSUPPORTED, self._reason(
            SupportClassification.UNSUPPORTED,
            supporting,
            partial,
            derived,
            conflicting,
            match_result,
        )

    @staticmethod
    def _reason(
        classification: SupportClassification,
        supporting: tuple[RequirementEvidenceLink, ...],
        partial: tuple[RequirementEvidenceLink, ...],
        derived: tuple[RequirementEvidenceLink, ...],
        conflicting: tuple[RequirementEvidenceLink, ...],
        match_result: MatchResult,
    ) -> str:
        """A short, deterministic reason for the verdict (governed data, not prose)."""
        return (
            f"{classification}: supporting={len(supporting)} (top {_top_score(supporting)}), "
            f"partial={len(partial)}, derived={len(derived)}, "
            f"conflicting={len(conflicting)} (top {_top_score(conflicting)}); "
            f"examined={match_result.statistics.evidence_examined}."
        )
