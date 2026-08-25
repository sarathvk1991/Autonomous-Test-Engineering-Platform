"""``CorpusExecutionReader`` — CAP-091's own, disjoint reader over ``output/executions/``.

Piece 1 of CAP-091 (ADR-0052 D3). Reads each execution's own persisted
``manifest.json`` and ``testable_requirement_set.json`` at the dict level —
never ``model_validate`` — mirroring the Historical Dataset arc's own proven
extraction discipline (``requirement_intelligence.knowledge_graph.engine.
file_historical_dataset_provider``, pieces 2/3, its file-based provider
class): directory enumeration, dict-level JSON reads, silent skip of
malformed or partial run directories, never a fabricated stand-in.

**Deliberately disjoint (ADR-0052 D3 / ADR-0023 §D9/§D10, frozen).** This
module imports nothing from ``requirement_intelligence.knowledge_graph`` —
not ``HistoricalExecutionRecord``, not the Knowledge Graph's own historical-
dataset-resolving provider class, not any other name in that package. ADR-0023
§D10 froze ``HistoricalExecutionRecord`` as *"never exported past the
``knowledge_graph`` package boundary"*; §D9 already established the
*"deliberately replicated rather than shared"* discipline this module repeats
a third time (after Continuous Improvement -> Knowledge Graph, and Knowledge
Graph -> this). ``CorpusExecutionRecord`` below is this reader's own,
independent type.

**Scope (ADR-0052 D2).** Per-run-total granularity only: the requirement
COUNT is the core signal a future distributional comparison reasons over.
``component``/``functional_tag`` are captured as the representative (first
requirement's) values only because they are honestly available at zero
extra read cost — D2 already found both are constant within every real
execution checked, so they carry no additional resolving power today and
are not consumed by anything in this piece.

**Not built here.** No comparison logic, no ``CorpusCompletenessReport`` —
those are later pieces (ADR-0052 D1/D5). This module only enumerates and
extracts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Every execution's own persisted contract JSON lives one directory per run
#: beneath this path — the same ``target_dir`` convention
#: ``requirement_intelligence.execution_package.execution_writer.ExecutionWriter``
#: writes to, and the same root the Historical Dataset arc's own file-based
#: provider (piece 2/3) reads.
DEFAULT_EXECUTIONS_ROOT = Path("output") / "executions"


@dataclass(frozen=True)
class CorpusExecutionRecord:
    """One qualifying execution's own requirement-completeness-relevant facts.

    Execution-granularity, mirroring ``HistoricalExecutionRecord``'s own
    granularity — but this is CAP-091's own, disjoint type, never that one.
    """

    execution_id: str
    completed_timestamp: str
    requirement_count: int
    component: str | None
    functional_tag: str | None


class CorpusExecutionReader:
    """Enumerate ``output/executions/`` and extract each qualifying run's
    requirement-completeness facts.

    Never fabricates: a run directory missing ``manifest.json``, missing
    ``testable_requirement_set.json``, whose requirement list is empty, or
    whose JSON is malformed, is silently skipped — not padded, not guessed.
    """

    def __init__(self, executions_root: Path | str = DEFAULT_EXECUTIONS_ROOT) -> None:
        """Store the corpus root this reader reads from. Construction only."""
        self._root = Path(executions_root)

    def read(self) -> tuple[CorpusExecutionRecord, ...]:
        """Return one record per qualifying execution, in chronological order.

        Chronological by ``executionCompletedTimestamp`` (ISO 8601 UTC, sorts
        correctly as a plain string) — mirroring the Historical Dataset arc's
        own chronological-indexing pattern (piece 2/3).
        """
        if not self._root.is_dir():
            return ()
        records = [
            record
            for run_dir in sorted(self._root.iterdir())
            if run_dir.is_dir()
            for record in (self._record_for(run_dir),)
            if record is not None
        ]
        records.sort(key=lambda record: record.completed_timestamp)
        return tuple(records)

    # -- internal ------------------------------------------------------------

    def _record_for(self, run_dir: Path) -> CorpusExecutionRecord | None:
        """Assemble one record from *run_dir*, or None if it does not qualify.

        Qualification mirrors the Historical Dataset arc's own file-based
        provider (piece 2/3): a real
        ``executionId``/``executionCompletedTimestamp`` in
        ``manifest.json``, plus a non-empty ``requirements`` list in
        ``testable_requirement_set.json``.
        """
        manifest = self._read_json(run_dir / "manifest.json")
        if manifest is None:
            return None
        execution_id = manifest.get("executionId")
        completed = manifest.get("executionCompletedTimestamp")
        if not isinstance(execution_id, str) or not execution_id:
            return None
        if not isinstance(completed, str) or not completed:
            return None

        trs = self._read_json(run_dir / "testable_requirement_set.json")
        if trs is None:
            return None
        requirements = trs.get("requirements")
        if not isinstance(requirements, list):
            return None
        valid_requirements = [item for item in requirements if isinstance(item, dict)]
        if not valid_requirements:
            return None

        first = valid_requirements[0]
        return CorpusExecutionRecord(
            execution_id=execution_id,
            completed_timestamp=completed,
            requirement_count=len(valid_requirements),
            component=self._optional_str(first.get("component")),
            functional_tag=self._optional_str(first.get("functionalTag")),
        )

    @staticmethod
    def _optional_str(value: Any) -> str | None:
        """Return *value* if it is a non-empty string, else None. Never guesses."""
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        """Read *path* as a JSON object, or None if absent/unreadable/not an object."""
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None
