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

Runtime status (CAP-086A)
    ``build`` is abstract and dormant: :class:`DormantLearningService` raises
    ``NotImplementedError`` on every call. No candidate is proposed, no
    learning is validated, no confidence is recorded, and no lifecycle is
    recorded. Only ``PlatformContext`` may construct it outside this
    package. A later milestone (CAP-086B, reserved) implements the method
    behind this unchanged signature, exactly as CAP-085B implemented the
    Organizational Memory Framework's own entry point behind the ADR-0027
    boundary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.learning.models.result import LearningResult
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
        Abstract in CAP-086A; a future CAP-086B milestone implements it
        behind this unchanged signature.
        """
        raise NotImplementedError


class DormantLearningService(LearningService):
    """The CAP-086A registered default — architecture only, no behaviour.

    Every call to ``build`` raises ``NotImplementedError``. This is the
    intentional, permanent shape of a dormant Layer 2 service (mirrors the
    dormant default services Continuous Improvement, Knowledge Graph, and
    Organizational Memory each registered at their own architecture-freeze
    milestone, all since replaced by their own deterministic successors) —
    it exists so ``PlatformContext`` has a real, constructible object to
    return before any engine exists, and so the abstract contract above is
    provably instantiable.
    """

    def build(self, organizational_memory_result: OrganizationalMemoryResult) -> LearningResult:
        """Always raises — no Learning engine exists yet (CAP-086A)."""
        raise NotImplementedError(
            "Learning is architecture-only (CAP-086A); no deterministic engine exists "
            "yet. See CAP-086B."
        )
