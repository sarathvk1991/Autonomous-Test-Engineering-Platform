"""``CorpusCompletenessReport`` — CAP-091's report-only surfacing of an assessment.

Piece 3 (final) of CAP-091 (ADR-0052 D5, "sketched, not built"). A thin,
deterministic projection of piece 2's own
:class:`~requirement_intelligence.corpus_completeness.engine.
CompletenessAssessment` into the report artifact D5 named — the run's own
``execution_id``/count, the historical distribution it was compared against,
an outlier flag, and a plain-language rationale (D5's own vocabulary). No new
design decision lives here: the anomaly rule and the report-only stance were
both already settled in piece 2 and ADR-0052 itself.

**Mirrors the platform's other report-only governance report shapes,
deliberately, not a novel shape.** Both ``suite_quality_governance.cp7``'s
own whole-suite quality report and the traceability graph's own
``CompletenessReport`` (ADR-0048) are plain, immutable results with no
``overall_verdict``/``passed``/gate-shaped field — a report PRESENTS a
measurement, it never decides pass/fail on its own. ``CorpusCompletenessReport``
below follows the identical discipline: ``status``/``outlier`` are
informational fields (mirroring CP7's own ``has_unmeasured_findings``
property, documented there as "NEVER gates"), not a verdict anything acts on.

**The outlier flag is scoped to incompleteness only (ADR-0052 D1), not
general outlier detection.** A count far ABOVE the historical range is never
``outlier=True`` here — piece 2's engine only ever flags a count below the
historical minimum, and this report surfaces that same, one-sided signal
unchanged, never widening its meaning.

**Disjoint (ADR-0052 D3 / ADR-0023 §D9/§D10).** This module imports nothing
from ``requirement_intelligence.knowledge_graph`` — it only projects piece
2's own assessment, which itself only reads through piece 1's own,
already-disjoint reader.
"""

from __future__ import annotations

from dataclasses import dataclass

from requirement_intelligence.corpus_completeness.engine import (
    AssessmentStatus,
    CompletenessAssessment,
    HistoricalDistributionSummary,
)

__all__ = ["CorpusCompletenessReport", "build_corpus_completeness_report"]


@dataclass(frozen=True)
class CorpusCompletenessReport:
    """The report-only surfacing of one run's completeness assessment.

    Deliberately carries no ``overall_verdict``/``passed``/gate-shaped
    field — mirroring CP7's own whole-suite report and the traceability
    graph's own ``CompletenessReport`` (ADR-0052 D5's own report-only
    framing). ``status``/``outlier`` are informational, never gating:
    nothing anywhere in this package acts on them to block anything.
    """

    execution_id: str
    requirement_count: int
    status: AssessmentStatus
    distribution: HistoricalDistributionSummary | None
    outlier: bool
    rationale: str


def build_corpus_completeness_report(
    assessment: CompletenessAssessment,
) -> CorpusCompletenessReport:
    """Project *assessment* (piece 2's own type) into its report artifact.

    A pure, deterministic rename/repackage — no new logic, no new decision.
    ``outlier``/``rationale`` are D5's own vocabulary for piece 2's
    ``flagged``/``reason``; everything else passes through unchanged.
    """
    return CorpusCompletenessReport(
        execution_id=assessment.execution_id,
        requirement_count=assessment.requirement_count,
        status=assessment.status,
        distribution=assessment.distribution,
        outlier=assessment.flagged,
        rationale=assessment.reason,
    )
