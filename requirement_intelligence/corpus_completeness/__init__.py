"""Cross-Corpus Requirement Completeness (CAP-091, ADR-0052).

Piece 1 (this piece): :class:`~requirement_intelligence.corpus_completeness.
reader.CorpusExecutionReader` — CAP-091's own, disjoint reader over
``output/executions/`` (ADR-0052 D3). Imports nothing from
``requirement_intelligence.knowledge_graph`` (ADR-0023 §D9/§D10, frozen).

Not yet built: the distributional comparison (ADR-0052 D1/D2) and
``CorpusCompletenessReport`` (ADR-0052 D5) — later pieces.
"""

from __future__ import annotations

from requirement_intelligence.corpus_completeness.reader import (
    DEFAULT_EXECUTIONS_ROOT,
    CorpusExecutionReader,
    CorpusExecutionRecord,
)

__all__ = [
    "DEFAULT_EXECUTIONS_ROOT",
    "CorpusExecutionReader",
    "CorpusExecutionRecord",
]
