"""Normalization responsibility registry.

The registry is the single source of truth for which
:class:`~requirement_intelligence.normalization.framework.normalization_responsibility.NormalizationResponsibility`
implementations participate in a normalization run.

Design notes
------------
* **No reflection, no dynamic loading, no filesystem scanning.**  Responsibilities
  are registered explicitly via :meth:`NormalizationRegistry.register`, mirroring
  the validation registry and the LLM provider registry.  This keeps the registry
  deterministic and testable.

* **Deterministic ordering by registration order.**  This is the key deliberate
  deviation from the validation registry: validation sorts rules by a nine-layer
  ``LAYER_ORDER``; **normalization has no layers**, so responsibilities are
  returned in **insertion order**.  The pipeline depends on this ordering and
  never re-sorts.

* **No shared state.**  Each registry instance is independent; the pipeline owns
  its own registry instance.

Relationship to the validation registry
----------------------------------------
``NormalizationRegistry`` is the structural sibling of ``ValidationRegistry`` —
same registration / sealing / duplicate-prevention discipline — minus the layer
dimension.
"""

from __future__ import annotations

from enum import Enum

from requirement_intelligence.normalization.framework.normalization_exceptions import (
    NormalizationRegistryError,
)
from requirement_intelligence.normalization.framework.normalization_responsibility import (
    NormalizationResponsibility,
)


class RegistryState(Enum):
    """Lifecycle state of a :class:`NormalizationRegistry`.

    Members
    -------
    OPEN
        The registry accepts new registrations.  Initial state of every registry.
    SEALED
        The registry is frozen against registration.  Any further
        :meth:`NormalizationRegistry.register` call raises
        :class:`~requirement_intelligence.normalization.framework.normalization_exceptions.NormalizationRegistryError`.
        A registry transitions to ``SEALED`` either explicitly via
        :meth:`NormalizationRegistry.seal` or automatically when a
        :class:`~requirement_intelligence.normalization.framework.normalization_pipeline.NormalizationPipeline`
        is constructed from it.

    The transition is **one-directional**: a sealed registry cannot be reopened.
    This guarantees the responsibility set a pipeline executes is fixed for the
    pipeline's lifetime, which is what makes a normalization run reproducible.
    """

    OPEN = "open"
    SEALED = "sealed"


class NormalizationRegistry:
    """Registry that catalogues :class:`NormalizationResponsibility` instances.

    Responsibilities are registered once, then queried by the pipeline.  The
    registry never instantiates responsibilities; it stores and retrieves them in
    **registration order** (there are no layers to sort by).

    Lifecycle
    ---------
    ::

        OPEN ──register()──► OPEN ──seal() / pipeline construction──► SEALED
                                                                         │
                                       register() ──► NormalizationRegistryError

    Usage
    -----
    .. code-block:: python

        registry = NormalizationRegistry()
        registry.register(MyResponsibility())

        responsibilities = registry.get_enabled_responsibilities()
    """

    def __init__(self) -> None:
        # Primary store: responsibilities in registration order.
        self._responsibilities: list[NormalizationResponsibility] = []

        # Secondary index: responsibility_id → responsibility, for O(1) duplicate
        # detection.
        self._responsibility_ids: dict[str, NormalizationResponsibility] = {}

        # Lifecycle state.  Every registry starts open for registration.
        self._state: RegistryState = RegistryState.OPEN

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def state(self) -> RegistryState:
        """The current lifecycle state (:attr:`~RegistryState.OPEN` or sealed)."""
        return self._state

    @property
    def is_sealed(self) -> bool:
        """``True`` once the registry has been sealed against registration."""
        return self._state is RegistryState.SEALED

    def seal(self) -> None:
        """Seal the registry, permanently disallowing further registration.

        Sealing is **idempotent**: sealing an already-sealed registry is a no-op
        and never raises.  Retrieval continues to work after sealing; only
        :meth:`register` is affected.

        The pipeline calls this automatically at construction time, so explicit
        calls are only needed when sealing a registry independently of a pipeline.
        """
        self._state = RegistryState.SEALED

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, responsibility: NormalizationResponsibility) -> None:
        """Register a normalization responsibility.

        Parameters
        ----------
        responsibility:
            The :class:`NormalizationResponsibility` instance to register.  Its
            :attr:`~NormalizationResponsibility.responsibility_id` must be unique
            within this registry.

        Raises
        ------
        NormalizationRegistryError
            If the registry has been sealed (see :meth:`seal`), or if a
            responsibility with the same ``responsibility_id`` is already
            registered.
        """
        # Identity is consumed through the responsibility's immutable metadata —
        # the single source of truth — rather than re-reading scattered
        # properties.  Behaviour is unchanged: the convenience wrappers already
        # delegate to this same value.
        responsibility_id = responsibility.metadata.responsibility_id
        if self._state is RegistryState.SEALED:
            raise NormalizationRegistryError(
                f"Cannot register responsibility {responsibility_id!r}: "
                f"the registry is sealed. Registration is only permitted while the "
                f"registry is OPEN; it is sealed automatically when a "
                f"NormalizationPipeline is constructed from it."
            )
        if responsibility_id in self._responsibility_ids:
            raise NormalizationRegistryError(
                f"A responsibility with responsibility_id "
                f"{responsibility_id!r} is already registered. "
                f"Each responsibility_id must be unique within a registry instance."
            )
        self._responsibilities.append(responsibility)
        self._responsibility_ids[responsibility_id] = responsibility

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_all_responsibilities(self) -> list[NormalizationResponsibility]:
        """Return every registered responsibility, in registration order.

        Returns
        -------
        list[NormalizationResponsibility]
            All responsibilities (enabled and disabled), in registration order.
        """
        return list(self._responsibilities)

    def get_enabled_responsibilities(self) -> list[NormalizationResponsibility]:
        """Return all *enabled* responsibilities, in registration order.

        This is the primary query used by the normalization pipeline.

        Returns
        -------
        list[NormalizationResponsibility]
            Responsibilities where :attr:`~NormalizationResponsibility.enabled` is
            ``True``, in registration order.
        """
        return [r for r in self._responsibilities if r.enabled]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_responsibility_ids(self) -> list[str]:
        """Return the ``responsibility_id`` of every responsibility, in order.

        Returns
        -------
        list[str]
            Ids in registration order.
        """
        return [r.responsibility_id for r in self._responsibilities]

    def responsibility_count(self) -> int:
        """Return the total number of registered responsibilities (enabled + disabled).

        Returns
        -------
        int
        """
        return len(self._responsibility_ids)
