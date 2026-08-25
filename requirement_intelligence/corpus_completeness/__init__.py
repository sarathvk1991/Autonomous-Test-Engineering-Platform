"""Cross-Corpus Requirement Completeness (CAP-091, ADR-0052).

Piece 1: :class:`~requirement_intelligence.corpus_completeness.reader.
CorpusExecutionReader` — CAP-091's own, disjoint reader over
``output/executions/`` (ADR-0052 D3).

Piece 2: :class:`~requirement_intelligence.corpus_completeness.engine.
CorpusCompletenessEngine` — the distributional comparison, reading through
piece 1's reader, assessing a given run's requirement count against the
historical distribution (ADR-0052 D1/D2), report-only (D5).

Piece 3 (this piece, final): :class:`~requirement_intelligence.
corpus_completeness.report.CorpusCompletenessReport` — the report-only
surfacing of piece 2's assessment (ADR-0052 D5). CAP-091 is now complete:
reader, engine, and report all built and tested.

Imports nothing from ``requirement_intelligence.knowledge_graph`` (ADR-0023
§D9/§D10, frozen).
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
from requirement_intelligence.corpus_completeness.report import (
    CorpusCompletenessReport,
    build_corpus_completeness_report,
)

__all__ = [
    "DEFAULT_EXECUTIONS_ROOT",
    "MIN_SAMPLE_SIZE_FOR_ASSESSMENT",
    "AssessmentStatus",
    "CompletenessAssessment",
    "CorpusCompletenessEngine",
    "CorpusCompletenessReport",
    "CorpusExecutionReader",
    "CorpusExecutionRecord",
    "HistoricalDistributionSummary",
    "build_corpus_completeness_report",
]
