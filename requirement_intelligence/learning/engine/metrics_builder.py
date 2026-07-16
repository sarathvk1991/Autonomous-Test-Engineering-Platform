"""Deterministic metrics assembly (CAP-086B).

``MetricsBuilder`` computes the build's :class:`LearningMetrics` **exactly
once**, from already-finished collaborator output. It tallies already-
recorded rows by a field they already carry — it never proposes, clusters,
validates, generates, or institutionalizes anything itself (ADR-0029
D10/D22: "MetricsBuilder never computes Learning").

The six maturity-distribution counts (``observed_count`` through
``retired_count``) are computed from the already-produced
:class:`LearningLifecycle` records' own ``maturity`` field —
``candidate_count`` is tallied separately, from the candidates tuple
directly, since ``CANDIDATE`` is not one of the six maturity-distribution
buckets this model reserves for post-generation Learning maturity.
"""

from __future__ import annotations

from collections import Counter

from requirement_intelligence.learning.models.enums import LearningMaturity
from requirement_intelligence.learning.models.learning import Learning
from requirement_intelligence.learning.models.learning_candidate import LearningCandidate
from requirement_intelligence.learning.models.learning_lifecycle import LearningLifecycle
from requirement_intelligence.learning.models.learning_validation import LearningValidation
from requirement_intelligence.learning.models.summary import LearningMetrics


class MetricsBuilder:
    """Compute the governed numeric roll-up exactly once. Never computes Learning."""

    def build(
        self,
        candidates: tuple[LearningCandidate, ...],
        learnings: tuple[Learning, ...],
        validations: tuple[LearningValidation, ...],
        lifecycles: tuple[LearningLifecycle, ...],
    ) -> LearningMetrics:
        """Tally already-produced collaborator output into one deterministic roll-up."""
        counts = Counter(lifecycle.maturity for lifecycle in lifecycles)
        return LearningMetrics(
            candidate_count=len(candidates),
            learning_count=len(learnings),
            validation_count=len(validations),
            observed_count=counts[LearningMaturity.OBSERVED],
            validated_count=counts[LearningMaturity.VALIDATED],
            trusted_count=counts[LearningMaturity.TRUSTED],
            institutional_count=counts[LearningMaturity.INSTITUTIONAL],
            standard_count=counts[LearningMaturity.STANDARD],
            retired_count=counts[LearningMaturity.RETIRED],
        )
