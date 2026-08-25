"""``CorpusCompletenessEngine`` — CAP-091's distributional comparison engine.

Piece 2 of CAP-091 (ADR-0052 D1/D2). Reads THROUGH piece 1's
:class:`~requirement_intelligence.corpus_completeness.reader.CorpusExecutionReader`
to get the historical corpus's per-run requirement counts, then assesses
whether a GIVEN run's own count is anomalously low against that distribution
— the "house of cards" signal this capability exists to surface (ADR-0052
Problem). It never gates (D5) and never infers a specific missing
requirement (D1): it only reports where a count sits, and why.

**The anomaly definition — BELOW-HISTORICAL-MINIMUM, chosen over a
continuous-stats model.** The real corpus (13 qualifying executions, read by
piece 1) is small and trimodal, not a smooth distribution: counts cluster at
exactly 15 (x3), 20 (x7), and 30 (x3) — mean 21.15, population stddev 5.25.
A z-score/stddev-based rule does not fit this shape: one stddev below the
mean is ~15.9, which sits ABOVE the real, legitimate, three-times-repeated
15-cluster — a naive z-score rule would flag a normal, recurring historical
value as anomalous. BELOW-HISTORICAL-MINIMUM makes no assumption about the
distribution's shape, never flags a value that has already been observed,
and produces a transparent, one-sentence rationale ("count 8 is below the
historical minimum of 15") rather than an opaque score. On the real data,
BELOW-HISTORICAL-MINIMUM and BELOW-THE-LOWEST-CLUSTER coincide exactly (15
is both the minimum and a 3-member cluster, not a stray low outlier), so
there is no ambiguity between those two framings to resolve here.

This is a genuine judgment call, not one the data's shape fully forces —
recorded honestly, not hidden: a stricter or looser threshold (e.g. requiring
a count below the minimum by some margin) is defensible too. Flagged as
worth Nitin's confirmation before this ever gates anything (it does not,
today — D5). The choice is low-risk to revisit: this engine only reports
(D5), so a different threshold is a later, non-breaking change, not a
correction to a decision anything currently depends on.

**Cold-start honesty (ADR-0052 D1, "never fabricates").** With 0 or 1
historical runs, there is no real distribution to compare against — no
verdict is fabricated; the assessment is reported as
:data:`AssessmentStatus.INSUFFICIENT_HISTORY`. The same status applies below
:data:`MIN_SAMPLE_SIZE_FOR_ASSESSMENT` (3) — the smallest cluster size the
real corpus has ever actually produced (both the 15- and 30-clusters are
exactly 3 members), so a "minimum" computed from fewer prior runs than that
would rest on less repetition than this platform's own real data has ever
shown to matter.

**Not built here.** ``CorpusCompletenessReport`` (ADR-0052 D5, the rendered,
report-only output) is piece 3, not this piece — :class:`CompletenessAssessment`
below is this engine's own, internal result type, not that report.

**Disjoint (ADR-0052 D3 / ADR-0023 §D9/§D10).** This module imports nothing
from ``requirement_intelligence.knowledge_graph`` — it reads only through
piece 1's own, already-disjoint reader.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from enum import StrEnum

from requirement_intelligence.corpus_completeness.reader import (
    CorpusExecutionReader,
    CorpusExecutionRecord,
)

#: The smallest cluster size the real corpus has ever produced (ADR-0052 D1:
#: both the 15- and 30-requirement clusters have exactly 3 members). Fewer
#: prior runs than this cannot ground a "minimum" in any repeated pattern
#: this platform has actually observed.
MIN_SAMPLE_SIZE_FOR_ASSESSMENT = 3


class AssessmentStatus(StrEnum):
    """Whether a real assessment was possible, or the corpus was too thin."""

    ASSESSED = "assessed"
    INSUFFICIENT_HISTORY = "insufficient_history"


@dataclass(frozen=True)
class HistoricalDistributionSummary:
    """The historical requirement-count distribution an assessment compared
    against — sample size, min/median/max (ADR-0052 D2's per-run-total
    granularity), and provenance (D5: which real executions contributed)."""

    sample_size: int
    minimum: int
    median: float
    maximum: int
    contributing_execution_ids: tuple[str, ...]


@dataclass(frozen=True)
class CompletenessAssessment:
    """One run's requirement count, assessed against the historical
    distribution. Report-only (ADR-0052 D5): a signal, never a gate — nothing
    in this type or the engine that produces it can block anything."""

    execution_id: str
    requirement_count: int
    status: AssessmentStatus
    distribution: HistoricalDistributionSummary | None
    flagged: bool
    reason: str


class CorpusCompletenessEngine:
    """Assess a given run's requirement count against the historical corpus.

    Reads the historical distribution through
    :class:`~requirement_intelligence.corpus_completeness.reader.CorpusExecutionReader`
    (never re-implements corpus access). The run being assessed is supplied
    by the caller as a plain count, not looked up from the historical corpus
    — this lets the live wiring assess the CURRENT, in-flight execution's own
    count, which by construction is not yet written to ``output/executions/``
    (the identical "not on disk yet" situation the reader's own historical
    corpus already handles for other artifacts), without needing any
    self-exclusion logic here.
    """

    def __init__(self, reader: CorpusExecutionReader | None = None) -> None:
        """Store the reader this engine reads the historical corpus through."""
        self._reader = reader if reader is not None else CorpusExecutionReader()

    def assess(self, *, execution_id: str, requirement_count: int) -> CompletenessAssessment:
        """Assess *requirement_count* (for *execution_id*) against history.

        Never fabricates a verdict: below
        :data:`MIN_SAMPLE_SIZE_FOR_ASSESSMENT` qualifying historical runs
        (including zero), the result is
        :data:`AssessmentStatus.INSUFFICIENT_HISTORY`, ``flagged=False``, with
        an honest reason — never a forced PASS or FAIL.
        """
        records = self._reader.read()
        if len(records) < MIN_SAMPLE_SIZE_FOR_ASSESSMENT:
            return self._insufficient_history(
                execution_id=execution_id, requirement_count=requirement_count, records=records
            )

        distribution = self._summarize(records)
        flagged = requirement_count < distribution.minimum
        reason = (
            f"count {requirement_count} is below the historical minimum of "
            f"{distribution.minimum} (n={distribution.sample_size}, "
            f"median={distribution.median}, max={distribution.maximum})"
            if flagged
            else (
                f"count {requirement_count} is at or above the historical minimum of "
                f"{distribution.minimum} (n={distribution.sample_size}, "
                f"median={distribution.median}, max={distribution.maximum})"
            )
        )
        return CompletenessAssessment(
            execution_id=execution_id,
            requirement_count=requirement_count,
            status=AssessmentStatus.ASSESSED,
            distribution=distribution,
            flagged=flagged,
            reason=reason,
        )

    # -- internal ------------------------------------------------------------

    @staticmethod
    def _insufficient_history(
        *, execution_id: str, requirement_count: int, records: tuple[CorpusExecutionRecord, ...]
    ) -> CompletenessAssessment:
        sample_size = len(records)
        distribution = (
            CorpusCompletenessEngine._summarize(records) if sample_size > 0 else None
        )
        reason = (
            f"only {sample_size} historical execution(s) available "
            f"(need at least {MIN_SAMPLE_SIZE_FOR_ASSESSMENT}); cannot assess completeness"
        )
        return CompletenessAssessment(
            execution_id=execution_id,
            requirement_count=requirement_count,
            status=AssessmentStatus.INSUFFICIENT_HISTORY,
            distribution=distribution,
            flagged=False,
            reason=reason,
        )

    @staticmethod
    def _summarize(records: tuple[CorpusExecutionRecord, ...]) -> HistoricalDistributionSummary:
        counts = [record.requirement_count for record in records]
        return HistoricalDistributionSummary(
            sample_size=len(records),
            minimum=min(counts),
            median=statistics.median(counts),
            maximum=max(counts),
            contributing_execution_ids=tuple(record.execution_id for record in records),
        )
