"""CP1 criterion registry.

The registry is the single source of truth for which
:class:`~requirement_intelligence.cp1.framework.criterion.CP1Criterion` instances
participate in a CP1 run.  It mirrors the frozen ``ValidationRegistry`` — explicit
registration, deterministic ordering, sealing — adapted to CP1's **flat** namespace.

Design notes
------------
* **No reflection, no dynamic loading.**  Criteria are registered explicitly by
  calling :meth:`CP1CriterionRegistry.register`.  Deterministic and testable.

* **Deterministic ordering — flat.**  CP1 has **no layers** (Engineering Readiness
  Criteria Catalog §4).  Criteria are stored and returned in **registration order**,
  which the engine is expected to align with catalog Criterion-ID order (Catalog §5).
  The pipeline depends on this ordering guarantee — it never re-sorts.

* **No shared state.**  Each registry instance is independent; the pipeline always
  owns its own registry instance.

The registry stores *instances* (criteria are stateless and can be shared).  It
carries **no engineering-readiness knowledge**.
"""

from __future__ import annotations

from enum import Enum

from requirement_intelligence.cp1.framework.criterion import CP1Criterion
from requirement_intelligence.cp1.framework.framework_exceptions import CP1RegistryError


class CP1RegistryState(Enum):
    """Lifecycle state of a :class:`CP1CriterionRegistry`.

    Members
    -------
    OPEN
        The registry accepts new criterion registrations.  Initial state.
    SEALED
        The registry is frozen against registration.  Any further
        :meth:`CP1CriterionRegistry.register` call raises
        :class:`~requirement_intelligence.cp1.framework.framework_exceptions.CP1RegistryError`.
        A registry seals either explicitly via :meth:`CP1CriterionRegistry.seal` or
        automatically when a
        :class:`~requirement_intelligence.cp1.framework.criterion_pipeline.CP1CriterionPipeline`
        is constructed from it.

    The transition is **one-directional**: a sealed registry cannot be reopened,
    which guarantees the criterion set a pipeline executes is fixed for that
    pipeline's lifetime — what makes a CP1 run reproducible.
    """

    OPEN = "open"
    SEALED = "sealed"


class CP1CriterionRegistry:
    """Registry that catalogues :class:`CP1Criterion` instances (flat, ordered).

    Criteria are registered once, then queried by the pipeline.  The registry never
    instantiates criteria; it stores and retrieves them in registration order.

    ::

        OPEN ──register()──► OPEN ──seal() / pipeline construction──► SEALED
                                                                        │
                                             register() ──► CP1RegistryError
    """

    def __init__(self) -> None:
        # Primary store: a single flat list in registration order (CP1 has no
        # layers — Engineering Readiness Criteria Catalog §4).
        self._criteria: list[CP1Criterion] = []

        # Secondary index: criterion_id → criterion, for O(1) duplicate detection.
        self._criterion_ids: dict[str, CP1Criterion] = {}

        # Lifecycle state.  Every registry starts open for registration.
        self._state: CP1RegistryState = CP1RegistryState.OPEN

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def state(self) -> CP1RegistryState:
        """The current lifecycle state (:attr:`~CP1RegistryState.OPEN` or sealed)."""
        return self._state

    @property
    def is_sealed(self) -> bool:
        """``True`` once the registry has been sealed against registration."""
        return self._state is CP1RegistryState.SEALED

    def seal(self) -> None:
        """Seal the registry, permanently disallowing further registration.

        Sealing is **idempotent**: sealing an already-sealed registry is a no-op and
        never raises.  Retrieval continues to work after sealing; only
        :meth:`register` is affected.  The pipeline calls this automatically at
        construction time.
        """
        self._state = CP1RegistryState.SEALED

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, criterion: CP1Criterion) -> None:
        """Register a CP1 criterion.

        Parameters
        ----------
        criterion:
            The :class:`CP1Criterion` instance to register.  Must have a unique
            :attr:`~CP1Criterion.criterion_id`.

        Raises
        ------
        CP1RegistryError
            If the registry has been sealed, or if a criterion with the same
            ``criterion_id`` is already registered.
        """
        if self._state is CP1RegistryState.SEALED:
            raise CP1RegistryError(
                f"Cannot register criterion {criterion.criterion_id!r}: the registry "
                f"is sealed. Registration is only permitted while the registry is "
                f"OPEN; it is sealed automatically when a CP1CriterionPipeline is "
                f"constructed from it."
            )
        if criterion.criterion_id in self._criterion_ids:
            raise CP1RegistryError(
                f"A criterion with criterion_id {criterion.criterion_id!r} is already "
                f"registered. Each criterion_id must be unique within a registry "
                f"instance."
            )
        self._criteria.append(criterion)
        self._criterion_ids[criterion.criterion_id] = criterion

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_all_criteria(self) -> list[CP1Criterion]:
        """Return all registered criteria (enabled and disabled), in registration order.

        Returns
        -------
        list[CP1Criterion]
            A copy of the registered criteria in registration order.  An empty list
            when none are registered.
        """
        return list(self._criteria)

    def get_enabled_criteria(self) -> list[CP1Criterion]:
        """Return all *enabled* criteria, in registration order.

        This is the primary query used by the CP1 pipeline.

        Returns
        -------
        list[CP1Criterion]
            All criteria where :attr:`~CP1Criterion.enabled` is ``True``, in
            registration order.
        """
        return [criterion for criterion in self._criteria if criterion.enabled]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_criterion_ids(self) -> list[str]:
        """Return the ``criterion_id`` of every registered criterion, in registration order."""
        return [criterion.criterion_id for criterion in self._criteria]

    def criterion_count(self) -> int:
        """Return the total number of registered criteria (enabled and disabled)."""
        return len(self._criteria)
