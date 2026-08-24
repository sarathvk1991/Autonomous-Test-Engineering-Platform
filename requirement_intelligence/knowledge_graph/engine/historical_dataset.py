"""The Historical Dataset Resolution Principle for Knowledge Graph (CAP-084B).

Reuses the exact architectural precedent CAP-083B established for Continuous
Improvement (ADR-0022 §D9, Recommendation 10): ``HistoricalDatasetReference``
intentionally carries provenance only — it names a dataset; it never embeds one.
No Historical Dataset storage implementation exists yet, and CAP-084B does not
build one. To have anything to project into a graph, the deterministic engine
resolves the reference through a private, constructor-injected
:class:`HistoricalDatasetProvider` into an internal :class:`HistoricalDataset` —
a plain, unexported structure that is **not** a runtime contract, **not**
Historical Truth, **not** Derived Knowledge, and **never** crosses the
``knowledge_graph`` package boundary.

``HistoricalDatasetReference`` itself is never modified by this module.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass

from requirement_intelligence.knowledge_graph.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)


@dataclass(frozen=True)
class HistoricalExecutionRecord:
    """One execution's projectable facts. Engine-internal only.

    Never a runtime contract, never persisted — resolved fresh on every
    :meth:`DeterministicKnowledgeGraphEngine.build` call. Names the entities one
    historical execution touched, by id only, so the node/edge projectors can
    deterministically build governed nodes and edges from it.

    ``requirement_id`` remains the single, representative requirement every
    other per-execution fact (``recommendation_id``/``finding_id``/
    ``capability_id``/``document_id``, each still execution-scalar) is anchored
    to — unchanged, so every existing node/edge relationship keeps its exact
    prior meaning. ``requirement_ids`` (Historical Dataset arc, piece 3) is an
    **additive** field carrying the execution's full requirement set, when a
    provider has one to give — always including ``requirement_id`` itself
    (never a disjoint list). It defaults to ``()``, meaning "not populated by
    this provider," never "this execution genuinely has zero requirements" —
    :class:`DeterministicHistoricalDatasetProvider` below leaves it at that
    default and is unaffected by this field's addition. The node projector
    treats ``{requirement_id} | set(requirement_ids)`` as the full set to
    project, so a provider that never populates ``requirement_ids`` still
    yields exactly today's one representative requirement node — no behaviour
    change for the synthetic path.
    """

    execution_id: str
    ordinal: int
    requirement_id: str
    recommendation_id: str | None
    finding_id: str | None
    capability_id: str | None
    document_id: str | None
    depends_on_previous: bool
    requirement_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class HistoricalDataset:
    """The resolved historical dataset for one reference. Engine-internal only.

    Never a runtime contract, never persisted, never crosses the
    ``knowledge_graph`` package boundary — resolved fresh on every
    :meth:`DeterministicKnowledgeGraphEngine.build` call, never cached
    (Recommendation 12 of ADR-0023, mirroring Recommendation 11 of ADR-0022).
    """

    dataset_id: str
    executions: tuple[HistoricalExecutionRecord, ...]


class HistoricalDatasetProvider(ABC):
    """Resolves a :class:`HistoricalDatasetReference` into a :class:`HistoricalDataset`.

    The **only** sanctioned way this engine obtains anything to project. A
    provider consumes only the reference's own provenance fields — never a
    previous :class:`~requirement_intelligence.knowledge_graph.models.result.
    KnowledgeGraphResult` or any of its constituents (mirrors Recommendation 11
    of ADR-0022) — and never a Layer 1 or Continuous Improvement runtime object.
    """

    @abstractmethod
    def resolve(self, historical_dataset: HistoricalDatasetReference) -> HistoricalDataset:
        """Resolve *historical_dataset* into its per-execution records."""
        raise NotImplementedError


class DeterministicHistoricalDatasetProvider(HistoricalDatasetProvider):
    """The CAP-084B default provider — deterministic, reproducible, a stand-in.

    No real Historical Dataset storage exists yet (ADR-0021 §Stage 6). This
    provider synthesizes per-execution records as a **pure function** of the
    reference's own fields (``dataset_id``, ordinal, ``first_execution_id``,
    ``last_execution_id``) via SHA-256 digests — no UUID, no clock, no
    randomness — solely so the deterministic engine can be exercised end to
    end, exactly mirroring ``DeterministicHistoricalDatasetProvider`` in
    ``continuous_improvement/engine.py``. A future milestone replaces this with
    a provider backed by a real Historical Dataset implementation, behind this
    same :class:`HistoricalDatasetProvider` contract.
    """

    def resolve(self, historical_dataset: HistoricalDatasetReference) -> HistoricalDataset:
        """Deterministically synthesize one record per execution the reference spans."""
        count = historical_dataset.execution_count
        executions = tuple(
            self._record_for(historical_dataset, ordinal, count) for ordinal in range(count)
        )
        return HistoricalDataset(dataset_id=historical_dataset.dataset_id, executions=executions)

    @staticmethod
    def _record_for(
        reference: HistoricalDatasetReference, ordinal: int, count: int
    ) -> HistoricalExecutionRecord:
        """Deterministically synthesize one execution's facts. Pure function of inputs."""
        if ordinal == 0:
            execution_id = reference.first_execution_id
        elif ordinal == count - 1:
            execution_id = reference.last_execution_id
        else:
            digest = hashlib.sha256(f"{reference.dataset_id}:{ordinal}".encode()).hexdigest()
            execution_id = f"{reference.dataset_id}-exec-{digest[:8]}"

        dataset_id = reference.dataset_id
        requirement_id = f"{dataset_id}-req-{ordinal}"

        def _present(label: str, modulus: int) -> bool:
            digest = hashlib.sha256(f"{dataset_id}:{ordinal}:{label}".encode()).hexdigest()
            return int(digest[:8], 16) % modulus == 0

        recommendation_id = f"{dataset_id}-rec-{ordinal}" if _present("recommendation", 2) else None
        finding_id = f"{dataset_id}-finding-{ordinal}" if _present("finding", 2) else None
        capability_id = f"{dataset_id}-cap-{ordinal}" if _present("capability", 3) else None
        document_id = f"{dataset_id}-doc-{ordinal}" if _present("document", 3) else None

        return HistoricalExecutionRecord(
            execution_id=execution_id,
            ordinal=ordinal,
            requirement_id=requirement_id,
            recommendation_id=recommendation_id,
            finding_id=finding_id,
            capability_id=capability_id,
            document_id=document_id,
            depends_on_previous=ordinal > 0,
        )
