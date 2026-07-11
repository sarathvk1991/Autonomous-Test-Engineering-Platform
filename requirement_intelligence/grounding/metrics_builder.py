"""The :class:`GroundingMetricsBuilder` — grounding metrics and summary.

It computes the run's :class:`GroundingMetrics` and :class:`GroundingSummary` from the
**finished** grounded requirements (and the size of the evidence corpus they drew on). It
owns metric computation only: it never matches, classifies, or scores confidence — it reads
already-graded ``GroundedRequirement``\\ s.

Determinism
-----------
Pure functions of the inputs: counts and ratios only, no randomness, timestamps, or UUIDs.
Ratios are floats (the model's shape); float division is deterministic. Identical inputs
yield equal metrics.
"""

from __future__ import annotations

from collections.abc import Sequence

from requirement_intelligence.grounding.models.assessment import GroundingSummary
from requirement_intelligence.grounding.models.enums import SupportClassification
from requirement_intelligence.grounding.models.grounded_requirement import GroundedRequirement
from requirement_intelligence.grounding.models.metrics import (
    GroundingMetrics,
    SupportDistributionEntry,
)

_GROUNDED = frozenset(
    {
        SupportClassification.SUPPORTED,
        SupportClassification.PARTIALLY_SUPPORTED,
        SupportClassification.WEAKLY_SUPPORTED,
    }
)
_HALLUCINATION = frozenset({SupportClassification.UNSUPPORTED, SupportClassification.CONTRADICTED})
#: Support classifications in canonical order, for a stable distribution.
_ALL_CLASSIFICATIONS = (
    SupportClassification.SUPPORTED,
    SupportClassification.PARTIALLY_SUPPORTED,
    SupportClassification.WEAKLY_SUPPORTED,
    SupportClassification.UNSUPPORTED,
    SupportClassification.CONTRADICTED,
    SupportClassification.UNKNOWN,
)


def _ratio(numerator: int, denominator: int) -> float:
    """Safe ratio in ``[0, 1]``; ``0.0`` when the denominator is zero."""
    return numerator / denominator if denominator else 0.0


def _sources(requirement: GroundedRequirement) -> int:
    """Distinct source systems this requirement's evidence draws on."""
    return len(requirement.source_systems)


class GroundingMetricsBuilder:
    """Compute :class:`GroundingMetrics` from finished grounded requirements."""

    def build(
        self,
        grounded_requirements: Sequence[GroundedRequirement],
        *,
        evidence_available: int,
    ) -> GroundingMetrics:
        """Return the deterministic metrics for *grounded_requirements*."""
        total = len(grounded_requirements)
        counts = {
            classification: sum(
                1
                for req in grounded_requirements
                if SupportClassification(req.classification) == classification
            )
            for classification in _ALL_CLASSIFICATIONS
        }
        grounded_count = sum(counts[c] for c in _GROUNDED)
        hallucinated = sum(counts[c] for c in _HALLUCINATION)

        total_links = sum(len(req.evidence_links) for req in grounded_requirements)
        with_links = sum(1 for req in grounded_requirements if req.evidence_links)
        referenced = {
            (str(link.evidence.source_system), link.evidence.source_record_id)
            for req in grounded_requirements
            for link in req.evidence_links
        }
        cross = sum(1 for req in grounded_requirements if _sources(req) >= 2)
        single = sum(1 for req in grounded_requirements if _sources(req) == 1)
        average_confidence = (
            sum(req.confidence.score for req in grounded_requirements) / total if total else 0.0
        )
        average_sources = (
            sum(_sources(req) for req in grounded_requirements) / total if total else 0.0
        )

        grounding_score = max(0, min(100, round(average_confidence)))
        return GroundingMetrics(
            total_requirements=total,
            grounded_requirements=grounded_count,
            unsupported_requirements=counts[SupportClassification.UNSUPPORTED],
            grounding_coverage=_ratio(grounded_count, total),
            evidence_coverage=_ratio(len(referenced), evidence_available),
            requirement_coverage=_ratio(with_links, total),
            evidence_utilization=_ratio(len(referenced), evidence_available),
            traceability_completeness=_ratio(with_links, total),
            average_confidence=average_confidence,
            cross_source_support=_ratio(cross, grounded_count),
            single_source_support=_ratio(single, grounded_count),
            unsupported_rate=_ratio(hallucinated, total),
            hallucination_rate=_ratio(hallucinated, total),
            average_evidence_per_requirement=_ratio(total_links, total),
            average_sources_per_requirement=average_sources,
            evidence_reuse_ratio=_ratio(total_links, len(referenced)),
            grounding_score=grounding_score,
            support_distribution=tuple(
                SupportDistributionEntry(classification=c, count=counts[c])
                for c in _ALL_CLASSIFICATIONS
            ),
        )

    def build_summary(
        self, grounded_requirements: Sequence[GroundedRequirement], metrics: GroundingMetrics
    ) -> GroundingSummary:
        """Return the deterministic headline summary for *grounded_requirements*."""

        def count(classification: SupportClassification) -> int:
            return sum(
                1
                for req in grounded_requirements
                if SupportClassification(req.classification) == classification
            )

        hallucinated = count(SupportClassification.UNSUPPORTED) + count(
            SupportClassification.CONTRADICTED
        )
        verdict = (
            f"{metrics.grounded_requirements}/{metrics.total_requirements} grounded; "
            f"{hallucinated} hallucination(s); score {metrics.grounding_score}."
        )
        return GroundingSummary(
            total_requirements=metrics.total_requirements,
            supported=count(SupportClassification.SUPPORTED),
            partially_supported=count(SupportClassification.PARTIALLY_SUPPORTED),
            unsupported=count(SupportClassification.UNSUPPORTED),
            grounding_score=metrics.grounding_score,
            verdict=verdict,
        )
