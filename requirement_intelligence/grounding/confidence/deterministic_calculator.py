"""Strategy V1 of confidence — the :class:`DeterministicConfidenceCalculator`.

The first production ``ConfidenceCalculator``. It consumes a ``ClassificationResult`` and
returns a ``ConfidenceAssessment``, applying the governed ``ConfidencePolicy``. It owns
confidence only; it reads **only** the policy and the classification result.

Algorithm (governed, integer-only)::

    score = base[classification] + sum(bonuses) - sum(penalties)
    score = clamp(score, 0, max_score)
    band  = HIGH | MEDIUM | LOW  (by policy thresholds)

Every value comes from the policy — no hard-coded scores, no magic numbers, no floats, no
AI, no randomness, no timestamps, no UUIDs. Every arithmetic operation is recorded as one
``ConfidenceComponent``, so the score is exactly the sum of its components and can be
reconstructed from them. Identical inputs yield an equal ``ConfidenceAssessment``.
"""

from __future__ import annotations

from requirement_intelligence.grounding.classification.models import ClassificationResult
from requirement_intelligence.grounding.confidence.calculator import ConfidenceCalculator
from requirement_intelligence.grounding.confidence.confidence_policy import ConfidencePolicy
from requirement_intelligence.grounding.confidence.models import (
    ConfidenceAssessment,
    ConfidenceExplanation,
)
from requirement_intelligence.grounding.models.confidence import ConfidenceComponent
from requirement_intelligence.grounding.models.enums import ConfidenceBand, SupportClassification


class DeterministicConfidenceCalculator(ConfidenceCalculator):
    """Compute confidence deterministically from a ``ClassificationResult`` and policy."""

    def __init__(self, policy: ConfidencePolicy) -> None:
        """Bind the governed confidence policy this calculator applies."""
        self._policy = policy

    @property
    def policy(self) -> ConfidencePolicy:
        """The governed confidence policy this calculator applies."""
        return self._policy

    def calculate(self, classification_result: ClassificationResult) -> ConfidenceAssessment:
        """Return the deterministic :class:`ConfidenceAssessment` for *classification_result*."""
        policy = self._policy
        classification = SupportClassification(classification_result.support_classification)

        components: list[ConfidenceComponent] = []
        positive: list[str] = []
        negative: list[str] = []
        rules: list[str] = ["base_score"]

        base = self._base_score(classification)
        components.append(
            ConfidenceComponent(
                factor=f"base:{classification}", delta=base, reason="Base score for the verdict."
            )
        )

        raw = (
            base
            + self._apply_bonuses(classification_result, components, positive, rules)
            - self._apply_penalties(
                classification_result, classification, components, negative, rules
            )
        )

        final = self._clamp(raw, components, rules)
        band = self._band(final)
        explanation = ConfidenceExplanation(
            summary=(
                f"{classification}: base {base}, score {final} ({band}) "
                f"under policy {policy.policy_id}."
            ),
            positive_factors=tuple(positive),
            negative_factors=tuple(negative),
            applied_policy_rules=tuple(rules),
            score_breakdown=tuple(components),
            recommendations=self._recommendations(classification, band),
        )
        return ConfidenceAssessment(
            requirement_id=classification_result.requirement_id,
            confidence_score=final,
            confidence_band=band,
            confidence_components=tuple(components),
            confidence_explanation=explanation,
        )

    # -- score construction ------------------------------------------------

    def _base_score(self, classification: SupportClassification) -> int:
        """The governed base score for *classification*."""
        base = self._policy.base_scores
        return {
            SupportClassification.SUPPORTED: base.supported,
            SupportClassification.PARTIALLY_SUPPORTED: base.partially_supported,
            SupportClassification.WEAKLY_SUPPORTED: base.weakly_supported,
            SupportClassification.UNSUPPORTED: base.unsupported,
            SupportClassification.CONTRADICTED: base.contradicted,
            SupportClassification.UNKNOWN: base.unknown,
        }[classification]

    def _apply_bonuses(
        self,
        result: ClassificationResult,
        components: list[ConfidenceComponent],
        positive: list[str],
        rules: list[str],
    ) -> int:
        """Add every governed bonus (only when it contributes). Returns the total added."""
        bonuses = self._policy.bonuses
        total = 0

        corroborating = max(0, len(result.supporting_links) - 1)
        support_gain = bonuses.support_bonus * corroborating
        if support_gain:
            total += support_gain
            rules.append("support_bonus")
            positive.append(f"corroborating support (+{support_gain})")
            components.append(
                ConfidenceComponent(
                    factor="support_bonus",
                    delta=support_gain,
                    reason=f"{corroborating} additional supporting link(s).",
                )
            )

        systems = {str(link.evidence.source_system) for link in result.evidence_links}
        if len(systems) >= 2 and bonuses.cross_source_bonus:
            total += bonuses.cross_source_bonus
            rules.append("cross_source_bonus")
            positive.append(f"cross-source corroboration (+{bonuses.cross_source_bonus})")
            components.append(
                ConfidenceComponent(
                    factor="cross_source_bonus",
                    delta=bonuses.cross_source_bonus,
                    reason=f"Evidence spans {len(systems)} source systems.",
                )
            )

        extra_evidence = max(0, len(result.evidence_links) - 1)
        evidence_gain = bonuses.evidence_count_bonus * extra_evidence
        if evidence_gain:
            total += evidence_gain
            rules.append("evidence_count_bonus")
            positive.append(f"multiple evidence items (+{evidence_gain})")
            components.append(
                ConfidenceComponent(
                    factor="evidence_count_bonus",
                    delta=evidence_gain,
                    reason=f"{extra_evidence} additional evidence item(s).",
                )
            )
        return total

    def _apply_penalties(
        self,
        result: ClassificationResult,
        classification: SupportClassification,
        components: list[ConfidenceComponent],
        negative: list[str],
        rules: list[str],
    ) -> int:
        """Subtract every governed penalty (only when it applies). Returns the total removed."""
        penalties = self._policy.penalties
        total = 0

        conflict_loss = penalties.conflict_penalty * len(result.contradicting_links)
        if conflict_loss:
            total += conflict_loss
            rules.append("conflict_penalty")
            negative.append(f"conflicting evidence (-{conflict_loss})")
            components.append(
                ConfidenceComponent(
                    factor="conflict_penalty",
                    delta=-conflict_loss,
                    reason=f"{len(result.contradicting_links)} conflicting link(s).",
                )
            )

        if classification == SupportClassification.UNKNOWN and penalties.unknown_penalty:
            total += penalties.unknown_penalty
            rules.append("unknown_penalty")
            negative.append(f"unassessable verdict (-{penalties.unknown_penalty})")
            components.append(
                ConfidenceComponent(
                    factor="unknown_penalty",
                    delta=-penalties.unknown_penalty,
                    reason="Verdict is UNKNOWN.",
                )
            )
        return total

    def _clamp(self, raw: int, components: list[ConfidenceComponent], rules: list[str]) -> int:
        """Clamp *raw* to ``[0, max_score]``, recording any adjustment as a component."""
        ceiling = self._policy.max_score
        if raw > ceiling:
            components.append(
                ConfidenceComponent(
                    factor="ceiling", delta=ceiling - raw, reason=f"Capped at max_score {ceiling}."
                )
            )
            rules.append("max_score")
            return ceiling
        if raw < 0:
            components.append(
                ConfidenceComponent(factor="floor", delta=-raw, reason="Floored at 0.")
            )
            rules.append("floor")
            return 0
        return raw

    def _band(self, score: int) -> ConfidenceBand:
        """Map *score* to a band using the governed thresholds."""
        thresholds = self._policy.band_thresholds
        if score >= thresholds.high_min:
            return ConfidenceBand.HIGH
        if score >= thresholds.medium_min:
            return ConfidenceBand.MEDIUM
        return ConfidenceBand.LOW

    @staticmethod
    def _recommendations(
        classification: SupportClassification, band: ConfidenceBand
    ) -> tuple[str, ...]:
        """Deterministic, governed next-action observations (not prose)."""
        if classification == SupportClassification.CONTRADICTED:
            return ("quarantine: contradicted by evidence",)
        if classification == SupportClassification.UNSUPPORTED:
            return ("quarantine: unsupported",)
        if classification == SupportClassification.UNKNOWN:
            return ("gather evidence: unassessable",)
        if band == ConfidenceBand.HIGH:
            return ("accept",)
        if band == ConfidenceBand.MEDIUM:
            return ("review",)
        return ("review", "seek corroborating evidence")
