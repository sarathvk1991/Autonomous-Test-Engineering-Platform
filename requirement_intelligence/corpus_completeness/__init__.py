"""Cross-Corpus Requirement Completeness (CAP-091, ADR-0052).

Piece 1: :class:`~requirement_intelligence.corpus_completeness.reader.
CorpusExecutionReader` — CAP-091's own, disjoint reader over
``output/executions/`` (ADR-0052 D3).

Piece 2 (this piece): :class:`~requirement_intelligence.corpus_completeness.
engine.CorpusCompletenessEngine` — the distributional comparison, reading
through piece 1's reader, assessing a given run's requirement count against
the historical distribution (ADR-0052 D1/D2), report-only (D5).

Imports nothing from ``requirement_intelligence.knowledge_graph`` (ADR-0023
§D9/§D10, frozen).

Not yet built: ``CorpusCompletenessReport`` (ADR-0052 D5) — piece 3.
"""

from __future__ import annotations

from requirement_intelligence.corpus_completeness.engine import (
    MIN_SAMPLE_SIZE_FOR_ASSESSMENT,
    AssessmentStatus,
    CompletenessAssessment,
    CorpusCompletenessEngine,
    HistoricalDistributionSummary,
)
from requirement_intelligence.corpus_completeness.reader import (
    DEFAULT_EXECUTIONS_ROOT,
    CorpusExecutionReader,
    CorpusExecutionRecord,
)

__all__ = [
    "DEFAULT_EXECUTIONS_ROOT",
    "MIN_SAMPLE_SIZE_FOR_ASSESSMENT",
    "AssessmentStatus",
    "CompletenessAssessment",
    "CorpusCompletenessEngine",
    "CorpusExecutionReader",
    "CorpusExecutionRecord",
    "HistoricalDistributionSummary",
]
