"""``FileHistoricalDatasetProvider`` — a real, file-based ``HistoricalDatasetProvider``.

Piece 2 of the Historical Dataset arc (ADR-0021 §Stage 6;
``docs/architecture/mentor-feedback-scoping.md``, Item 3, "HISTORICAL DATASET ARC").
Piece 1 closed the one emission gap (CP1Result now persisted as ``cp1_result.json``),
so every execution written since carries all 8 of ADR-0021 §Stage 7's named runtime
contracts as JSON under ``output/executions/<run>/``. This provider resolves a
:class:`~requirement_intelligence.knowledge_graph.models.historical_dataset_reference.
HistoricalDatasetReference` by reading those REAL, already-persisted JSON files —
never SHA-256 synthesis (:class:`~requirement_intelligence.knowledge_graph.engine.
historical_dataset.DeterministicHistoricalDatasetProvider`, unchanged, still the
default). A **drop-in**: identical :class:`~requirement_intelligence.knowledge_graph.
engine.historical_dataset.HistoricalDatasetProvider` ABC, so
``DeterministicKnowledgeGraphEngine``/``DeterministicKnowledgeGraphService`` consume
it unchanged via the existing ``provider=`` constructor parameter.

Reads at the JSON/dict level only, never via ``model_validate`` reconstruction —
carrying piece 1's own finding forward: deeply nested contracts (``CP1Result``, via
``CP1Input`` → ``ValidationResult``/``NormalizationResult``) do not round-trip to full
Python-object equality because of loosely-typed nested fields. Reading with
``json.loads`` and plain ``dict`` indexing sidesteps that entirely — this provider
never reconstructs a typed contract object, it only ever reads the handful of scalar
fields ``HistoricalExecutionRecord`` needs.

Still one record per qualifying execution — **execution-granularity**, not
requirement-granularity records — but the record itself is no longer requirement-blind
beyond its representative id: ``requirement_id`` stays the FIRST requirement in that
execution's own set (unchanged, still the anchor every other per-execution fact
relates to), and ``requirement_ids`` (piece 3) additionally carries every requirement
in ``TestableRequirementSet.requirements``, in file order, read at the dict level —
never a fuller reconstruction. ``capability_id``/``document_id`` are always ``None``:
no real per-execution equivalent exists anywhere in today's Layer 1 runtime contracts
(a genuine absence in the data model, not an omission of this provider).

Never fabricates. A run directory is silently skipped — not padded, not guessed —
when it has no ``manifest.json``, no ``testable_requirement_set.json``, or an empty
``requirements`` list (``HistoricalExecutionRecord.requirement_id`` is a required
field with no honest placeholder value). A malformed/unreadable JSON file is treated
the same as an absent one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from requirement_intelligence.knowledge_graph.engine.historical_dataset import (
    HistoricalDataset,
    HistoricalDatasetProvider,
    HistoricalExecutionRecord,
)
from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)

#: Every execution's own persisted contract JSON lives one directory per run beneath
#: this path — the same ``target_dir`` convention
#: ``requirement_intelligence.execution_package.execution_writer.ExecutionWriter``
#: writes to.
DEFAULT_EXECUTIONS_ROOT = Path("output") / "executions"

_ManifestEntry = tuple[str, str, Path]  # (execution_id, completed_timestamp, run_dir)


class FileHistoricalDatasetProvider(HistoricalDatasetProvider):
    """Resolve a reference against the real, on-disk execution corpus.

    Reads ``manifest.json``, ``testable_requirement_set.json``,
    ``recommendation_result.json``, and ``cp1_result.json`` (when present) as plain
    JSON — never ``model_validate`` — and assembles one
    :class:`~requirement_intelligence.knowledge_graph.engine.historical_dataset.
    HistoricalExecutionRecord` per qualifying execution, in chronological order.
    """

    def __init__(self, executions_root: Path | str = DEFAULT_EXECUTIONS_ROOT) -> None:
        """Store the corpus root this provider reads from. Construction only."""
        self._root = Path(executions_root)

    def resolve(self, historical_dataset: HistoricalDatasetReference) -> HistoricalDataset:
        """Resolve *historical_dataset* against the real, on-disk execution corpus.

        Never fabricates: an execution named by the reference but not found on disk
        (including — today, always — the current, in-flight execution, which the
        Execution Package has not yet written when the Knowledge Graph phase runs)
        resolves to zero records for that slot, not a synthesized stand-in.
        """
        indexed = self._index_chronologically()
        window = self._select_window(indexed, historical_dataset)
        qualifying = [
            run_dir for _execution_id, _completed, run_dir in window if self._qualifies(run_dir)
        ]
        qualifying = qualifying[: historical_dataset.execution_count]
        records = tuple(
            self._record_for(run_dir, ordinal=ordinal, depends_on_previous=ordinal > 0)
            for ordinal, run_dir in enumerate(qualifying)
        )
        return HistoricalDataset(dataset_id=historical_dataset.dataset_id, executions=records)

    # -- internal ------------------------------------------------------------

    def _index_chronologically(self) -> list[_ManifestEntry]:
        """Index every real execution directory by (execution_id, completed, path).

        Sorted chronologically (``executionCompletedTimestamp`` is ISO 8601 UTC,
        which sorts correctly as a plain string). A directory missing
        ``manifest.json``, or whose manifest cannot be parsed or lacks an
        ``executionId``/``executionCompletedTimestamp``, is skipped — never raises.
        """
        entries: list[_ManifestEntry] = []
        if not self._root.is_dir():
            return entries
        for run_dir in sorted(self._root.iterdir()):
            if not run_dir.is_dir():
                continue
            manifest = self._read_json(run_dir / "manifest.json")
            if manifest is None:
                continue
            execution_id = manifest.get("executionId")
            completed = manifest.get("executionCompletedTimestamp")
            if not execution_id or not completed:
                continue
            entries.append((execution_id, completed, run_dir))
        entries.sort(key=lambda entry: entry[1])
        return entries

    @staticmethod
    def _select_window(
        indexed: list[_ManifestEntry], reference: HistoricalDatasetReference
    ) -> list[_ManifestEntry]:
        """Return the chronological slice of *indexed* the reference names.

        ``first_execution_id == last_execution_id`` (the only case the live CLI
        mints today, always with ``execution_count == 1``) is resolved directly by
        id — a single-execution window, regardless of what ``execution_count``
        claims, since first and last naming the same execution IS a one-execution
        window by definition. Either id absent from the corpus (including the
        current run's own id, not yet on disk) resolves to an empty window — never
        an error, never a fabricated entry.
        """
        if reference.first_execution_id == reference.last_execution_id:
            match = next(
                (entry for entry in indexed if entry[0] == reference.first_execution_id), None
            )
            return [match] if match is not None else []
        ids_in_order = [entry[0] for entry in indexed]
        if (
            reference.first_execution_id not in ids_in_order
            or reference.last_execution_id not in ids_in_order
        ):
            return []
        start = ids_in_order.index(reference.first_execution_id)
        end = ids_in_order.index(reference.last_execution_id)
        if end < start:
            return []
        return indexed[start : end + 1]

    def _qualifies(self, run_dir: Path) -> bool:
        """A run qualifies only if it has a real ``executionId`` and >=1 requirement.

        ``HistoricalExecutionRecord.requirement_id`` is a required field with no
        honest placeholder — a run lacking ``testable_requirement_set.json``, or
        whose set is empty (both real, observed shapes in the current corpus), is
        skipped rather than padded with a fabricated id.
        """
        manifest = self._read_json(run_dir / "manifest.json")
        if manifest is None or not manifest.get("executionId"):
            return False
        trs = self._read_json(run_dir / "testable_requirement_set.json")
        return bool(trs is not None and trs.get("requirements"))

    def _record_for(
        self, run_dir: Path, *, ordinal: int, depends_on_previous: bool
    ) -> HistoricalExecutionRecord:
        """Assemble one real record from *run_dir*'s own persisted contract JSON."""
        manifest = self._read_json(run_dir / "manifest.json") or {}
        trs = self._read_json(run_dir / "testable_requirement_set.json") or {}
        requirements = trs.get("requirements") or [{}]

        return HistoricalExecutionRecord(
            execution_id=manifest["executionId"],
            ordinal=ordinal,
            requirement_id=requirements[0]["requirementId"],
            recommendation_id=self._first_id(
                run_dir / "recommendation_result.json", "recommendations", "recommendationId"
            ),
            finding_id=self._first_id(run_dir / "cp1_result.json", "findings", "findingId"),
            # No real per-execution equivalent exists anywhere in today's Layer 1
            # runtime contracts — a genuine absence, not left unpopulated by oversight.
            capability_id=None,
            document_id=None,
            depends_on_previous=depends_on_previous,
            requirement_ids=self._all_requirement_ids(requirements),
        )

    @staticmethod
    def _all_requirement_ids(requirements: list[Any]) -> tuple[str, ...]:
        """Return every requirement's own ``requirementId``, in file order.

        Piece 3: the execution's full requirement set (``requirement_id`` above
        stays the first-in-set representative, unchanged). Dict-level only, same
        as every other read in this provider — an entry missing ``requirementId``
        (or not a dict at all) is silently skipped, never guessed.
        """
        ids: list[str] = []
        for requirement in requirements:
            if not isinstance(requirement, dict):
                continue
            requirement_id = requirement.get("requirementId")
            if isinstance(requirement_id, str) and requirement_id:
                ids.append(requirement_id)
        return tuple(ids)

    @staticmethod
    def _first_id(path: Path, list_key: str, id_key: str) -> str | None:
        """Return the first item's *id_key* from *path*'s *list_key* list, or None.

        Dict-level only — never ``model_validate``. Absent file, unreadable JSON, a
        missing list key, or an empty list all resolve to ``None``, never an error.
        """
        data = FileHistoricalDatasetProvider._read_json(path)
        if data is None:
            return None
        items = data.get(list_key) or []
        if not items:
            return None
        value = items[0].get(id_key)
        return value if isinstance(value, str) else None

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
