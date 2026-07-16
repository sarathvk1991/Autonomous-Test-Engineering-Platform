"""LearningService — the single runtime entry point into the Learning
Framework.

Architecture (ADR-0029)
------------------------
``LearningService`` is the permanent **orchestration boundary** of the
Learning Framework — the fourth and final Layer 2 capability (ADR-0020),
following Continuous Improvement (ADR-0022), Knowledge Graph (ADR-0023), and
Organizational Memory (ADR-0027). Everything outside the subsystem will talk
to learning through this one contract; nothing else is a public runtime
surface. It mirrors the role the Organizational Memory Framework's own
runtime service plays for its subsystem (ADR-0027 §D7): a single seam that
will coordinate collaborators and own none of their work.

Organizational Knowledge only — a single input (frozen, ADR-0028 §Stage 12,
Recommendation 4/9 of ADR-0028, Recommendation 6/7 of ADR-0029)
---------------------------------------------------------------------------
``build`` consumes **only** the one completed Layer 2 tier immediately below
Learning — :class:`~requirement_intelligence.organizational_memory.models.
result.OrganizationalMemoryResult` — never a Continuous Improvement or
Knowledge Graph result directly, never a ``HistoricalDatasetReference``,
never a Layer 1 runtime contract, and never an Execution Package artifact.
Learning is the constitutional bridge from Layer 2 to Layer 3 (ADR-0028
§Stage 16) and the sole sanctioned entry point Layer 3 may later use to
consume Layer 2's most refined conclusion (ADR-0028 §Stage 12) — but that
entry point itself reaches no further back than the one tier immediately
beneath it. Unlike Organizational Memory's own deliberate fan-in exception
(ADR-0025 §Stage 7/8: two Layer 2 peers, because curating "what deserves to
be remembered" requires reading both), Learning validates a single,
already-curated input:

    OrganizationalMemoryResult ─▶ LearningService.build ─▶ LearningResult

What the service OWNS
    orchestration, lifecycle, dependency coordination, and execution ordering.

What the service does NOT own
    Organizational Memory, Continuous Improvement, Knowledge Graph, the
    Historical Dataset, any Layer 1 subsystem, and the Execution Package.
    Each is a separate owner. The future deterministic (and any future
    statistical, ML, LLM, GraphRAG, reinforcement learning, or
    neuro-symbolic) Learning engine is an **internal implementation
    detail** of the service and can be replaced without changing this
    contract.

Runtime status (CAP-086B)
    ``build`` is now implemented: :class:`DeterministicLearningService`
    delegates to a private :class:`~requirement_intelligence.learning.
    engine.DeterministicLearningEngine` that performs deterministic
    candidate collection, clustering, validation, generation,
    institutionalization evaluation, stability evaluation, confidence
    recording, promotion recording, and lifecycle recording end to end — via
    independent, modular collaborators, never one large engine (ADR-0029
    D9-D26). The service is still **not wired into any execution pipeline**
    (nothing calls ``build`` at runtime) and only ``PlatformContext`` may
    construct it outside this package — so runtime behaviour is
    byte-identical and the golden baseline is unchanged. Runtime
    integration is future work (CAP-086C, reserved), exactly as CAP-085B
    implemented the Organizational Memory Framework's own entry point
    before a later milestone activated it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.learning.engine import DeterministicLearningEngine
from requirement_intelligence.learning.models.result import LearningResult
from requirement_intelligence.learning.policy import LearningPolicy
from requirement_intelligence.organizational_memory.models.result import (
    OrganizationalMemoryResult,
)


class LearningService(ABC):
    """The permanent runtime contract for building one learned-knowledge result.

    A single public method, ``build``, proposes candidates and validates
    learnings from one completed ``OrganizationalMemoryResult`` under a
    governed :class:`~requirement_intelligence.learning.policy.
    learning_policy.LearningPolicy` and returns a :class:`LearningResult`.
    Implementations orchestrate; they delegate construction to internal
    collaborators and own no organizational memory logic themselves.
    """

    @abstractmethod
    def build(self, organizational_memory_result: OrganizationalMemoryResult) -> LearningResult:
        """Build learned knowledge from one completed Organizational Memory result.

        Parameters
        ----------
        organizational_memory_result:
            The completed ``OrganizationalMemoryResult`` to draw learning
            candidates from — never modified, never re-derived.

        Returns
        -------
        LearningResult
            The complete, self-contained record of every candidate,
            learning, validation, confidence, and lifecycle record built
            for this consumed result.

        Notes
        -----
        Abstract at CAP-086A; :class:`DeterministicLearningService`
        (CAP-086B) implements it behind this unchanged signature.
        """
        raise NotImplementedError


class DeterministicLearningService(LearningService):
    """The registered default service (CAP-086B) — thin orchestration over the engine.

    Holds a private :class:`~requirement_intelligence.learning.engine.
    DeterministicLearningEngine` and delegates ``build`` to it, owning only
    the public boundary and construction. It **computes nothing itself**:
    the engine's modular collaborators perform candidate collection,
    clustering, validation, generation, institutionalization evaluation,
    stability evaluation, confidence recording, promotion recording, and
    lifecycle recording. Mirrors how the Organizational Memory Framework's
    own deterministic runtime service delegates to its private engine
    (ADR-0027) — a thin service, real behaviour one layer down. Replaces
    ``DormantLearningService`` (CAP-086A), which CAP-086B removes, mirroring
    how CAP-085B's own deterministic service replaced its dormant
    predecessor.
    """

    def __init__(self, *, policy: LearningPolicy) -> None:
        """Construct the private deterministic engine this service delegates to."""
        self._engine = DeterministicLearningEngine(policy=policy)

    def build(self, organizational_memory_result: OrganizationalMemoryResult) -> LearningResult:
        """Build Learning via the deterministic engine — delegation only."""
        return self._engine.build(organizational_memory_result)
