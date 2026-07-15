"""ContinuousImprovementService — the single runtime entry point into the
Continuous Improvement Framework.

Architecture (ADR-0022)
------------------------
``ContinuousImprovementService`` is the permanent **orchestration boundary** of
the Continuous Improvement Framework — the first Layer 2 capability (ADR-0020).
Everything outside the subsystem will talk to improvement observation through
this one contract; nothing else is a public runtime surface. It mirrors the role
the Recommendation Framework's own runtime service plays for that subsystem
(ADR-0019 §D6): a single seam that will coordinate collaborators and own none of
their work.

Historical Truth only (frozen, ADR-0021 §Stage 8, Recommendation 1 of ADR-0022)
---------------------------------------------------------------------------------
``improve`` consumes **only** a :class:`~requirement_intelligence.
continuous_improvement.models.historical_dataset_reference.HistoricalDatasetReference`
— provenance naming a Historical Dataset, never a Layer 1 runtime contract
directly and never an Execution Package artifact. This is a stricter boundary
than any Layer 1 subsystem's: Continuous Improvement never imports
``requirement_intelligence.enhancement``, ``.grounding``, ``.validation``,
``.cp1``, ``.quality_governance``, ``.recommendation``, or ``.execution`` at all.
The dependency direction is one-way:

    HistoricalDatasetReference ─▶ ContinuousImprovementService.improve
        ─▶ ContinuousImprovementResult

What the service will OWN
    orchestration, lifecycle, dependency coordination, execution ordering, and (in
    a later milestone) assembly of the final :class:`ContinuousImprovementResult`.

What the service does NOT own
    the Historical Dataset itself (ADR-0021 §Stage 6 names its owner), any Layer 1
    subsystem, and the Execution Package. Each is a separate owner. A future
    deterministic, statistical, ML, or LLM Continuous Improvement engine is an
    **internal implementation detail** of the service and can be added without
    changing this contract.

Runtime status (CAP-083A)
    ``improve`` is **abstract**. The registered
    :class:`DormantContinuousImprovementService` raises
    :class:`NotImplementedError`. It is dormant — no runtime path consumes it, and
    only ``PlatformContext`` may construct it outside this package — so runtime
    behaviour is byte-identical and the golden baseline is unchanged. Runtime
    integration is future work (CAP-083B onward), exactly as CAP-082A froze the
    Recommendation service boundary before CAP-082B implemented the first
    deterministic engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from requirement_intelligence.continuous_improvement.models.historical_dataset_reference import (
    HistoricalDatasetReference,
)
from requirement_intelligence.continuous_improvement.models.result import (
    ContinuousImprovementResult,
)
from requirement_intelligence.continuous_improvement.policy.continuous_improvement_policy import (
    ImprovementPolicy,
)


class ContinuousImprovementService(ABC):
    """The permanent runtime contract for observing recurrence across one dataset.

    A single public method, ``improve``, derives findings, trends, and
    opportunities from a referenced Historical Dataset under a governed
    :class:`ImprovementPolicy` and returns a :class:`ContinuousImprovementResult`.
    Implementations orchestrate; they delegate detection and generation to
    internal collaborators and own no historical storage themselves.
    """

    @abstractmethod
    def improve(
        self,
        historical_dataset: HistoricalDatasetReference,
    ) -> ContinuousImprovementResult:
        """Observe recurrence across the dataset named by *historical_dataset*.

        Parameters
        ----------
        historical_dataset:
            Provenance naming the Historical Dataset to observe — never the
            dataset's content, and never a Layer 1 runtime contract directly.

        Returns
        -------
        ContinuousImprovementResult
            The repository-level improvement aggregate for the dataset — the
            complete, self-contained record of every finding, trend, and
            opportunity.

        Notes
        -----
        Abstract in CAP-083A; a real engine is wired behind this unchanged
        signature in a later CAP-083 milestone (CAP-083B).
        """
        raise NotImplementedError


class DormantContinuousImprovementService(ContinuousImprovementService):
    """The registered, dormant service (CAP-083A). Raises on every call.

    Exists so :meth:`PlatformContext.create_continuous_improvement_service` has a
    concrete class to construct — proving the composition root and the frozen
    signature are wired — without performing any improvement observation. Mirrors
    the pattern ADR-0019 §D6 established for the dormant Recommendation runtime
    service before its first real engine landed.
    """

    def __init__(self, policy: ImprovementPolicy) -> None:
        """Store the governed policy a future engine will read."""
        self._policy = policy

    def improve(
        self,
        historical_dataset: HistoricalDatasetReference,
    ) -> ContinuousImprovementResult:
        """Raise: no Continuous Improvement engine exists yet (CAP-083A is architecture only)."""
        raise NotImplementedError(
            "ContinuousImprovementService.improve has no implementation yet "
            "(CAP-083A froze the architecture only); a later CAP-083 milestone "
            "wires a real engine behind this unchanged signature."
        )
