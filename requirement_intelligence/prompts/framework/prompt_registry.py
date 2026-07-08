"""Prompt governance registry.

The registry is the single source of truth for which
:class:`~requirement_intelligence.prompts.models.PromptDefinition` instances
are governed and available to the platform.

Design notes
------------
* **No reflection, no dynamic loading, no filesystem scanning.**  Prompts are
  registered explicitly by calling :meth:`PromptRegistry.register`.  This
  mirrors the pattern used by the Validation Registry and the CP1 Criterion
  Registry — deterministic and testable.

* **Deterministic ordering.**  Definitions are stored in registration order.
  All retrieval methods respect this order.  The registry never re-sorts.

* **Duplicate detection.**  A ``(prompt_id, version)`` pair must be unique
  within a registry instance.  Attempting to register a duplicate raises
  :class:`~requirement_intelligence.prompts.framework.prompt_exceptions.PromptRegistryError`.

* **Immutable after sealing.**  Once :meth:`seal` is called (or the canonical
  composition helper seals it), no further registrations are accepted.  This
  guarantees that the set of prompts a component reads is fixed for the
  lifetime of that component.

* **Deterministic lookup.**  :meth:`get` returns the single registered
  definition for a given ``(prompt_id, version)`` pair, or raises
  :class:`~requirement_intelligence.prompts.framework.prompt_exceptions.PromptNotFoundError`
  when the pair is not found.  When ``version`` is omitted and exactly one
  version of the prompt is registered, that version is returned; when multiple
  versions are registered and no version is specified, the call raises to
  prevent ambiguous lookup.

* **No shared state.**  Each registry instance is independent.
"""

from __future__ import annotations

from enum import Enum

from requirement_intelligence.prompts.framework.prompt_exceptions import (
    PromptNotFoundError,
    PromptRegistryError,
)
from requirement_intelligence.prompts.models.prompt_definition import PromptDefinition


class PromptRegistryState(Enum):
    """Lifecycle state of a :class:`PromptRegistry`.

    Members
    -------
    OPEN
        The registry accepts new prompt registrations.  This is the initial
        state of every registry.
    SEALED
        The registry is frozen against further registration.  Any call to
        :meth:`PromptRegistry.register` after sealing raises
        :class:`~requirement_intelligence.prompts.framework.prompt_exceptions.PromptRegistryError`.
        A registry is sealed explicitly via :meth:`PromptRegistry.seal`.

    The transition is **one-directional**: a sealed registry cannot be
    reopened.  This guarantees that the governed prompt set is fixed for the
    lifetime of any component that holds the registry, which is what makes
    prompt resolution deterministic and reproducible.
    """

    OPEN = "open"
    SEALED = "sealed"


class PromptRegistry:
    """Registry that catalogues :class:`PromptDefinition` instances.

    Definitions are registered once, then queried.  The registry never
    instantiates definitions; it stores and retrieves them in registration
    order.

    Lifecycle state machine::

        OPEN ──register()──► OPEN ──seal()──► SEALED
                                                │
                             register() ──► PromptRegistryError
    """

    def __init__(self) -> None:
        # Primary store: ordered list in registration order.
        self._definitions: list[PromptDefinition] = []

        # Secondary index: (prompt_id, version) → definition for O(1) lookup
        # and O(1) duplicate detection.
        self._index: dict[tuple[str, str], PromptDefinition] = {}

        # Lifecycle state.  Every registry starts open for registration.
        self._state: PromptRegistryState = PromptRegistryState.OPEN

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def state(self) -> PromptRegistryState:
        """The current lifecycle state (OPEN or SEALED)."""
        return self._state

    @property
    def is_sealed(self) -> bool:
        """``True`` once the registry has been sealed against registration."""
        return self._state is PromptRegistryState.SEALED

    def seal(self) -> None:
        """Seal the registry, permanently disallowing further registration.

        Sealing is **idempotent**: sealing an already-sealed registry is a
        no-op and never raises.  Retrieval continues to work after sealing;
        only :meth:`register` is affected.

        The canonical composition helper calls this automatically after
        registering all governed prompts.
        """
        self._state = PromptRegistryState.SEALED

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, definition: PromptDefinition) -> None:
        """Register a governed prompt definition.

        Parameters
        ----------
        definition:
            The :class:`PromptDefinition` to register.  Must have a unique
            ``(prompt_id, version)`` pair within this registry instance.

        Raises
        ------
        PromptRegistryError
            If the registry has been sealed, or if a definition with the same
            ``(prompt_id, version)`` pair is already registered.
        """
        if self._state is PromptRegistryState.SEALED:
            raise PromptRegistryError(
                f"Cannot register prompt {definition.metadata.prompt_id!r} "
                f"v{definition.metadata.version!r}: the registry is sealed. "
                f"Registration is only permitted while the registry is OPEN."
            )
        key = (definition.metadata.prompt_id, definition.metadata.version)
        if key in self._index:
            raise PromptRegistryError(
                f"A definition for prompt_id={definition.metadata.prompt_id!r} "
                f"version={definition.metadata.version!r} is already registered. "
                f"Each (prompt_id, version) pair must be unique within a registry."
            )
        self._definitions.append(definition)
        self._index[key] = definition

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, prompt_id: str, version: str | None = None) -> PromptDefinition:
        """Return the registered definition for the given prompt identifier.

        Parameters
        ----------
        prompt_id:
            The stable prompt identifier (e.g. ``"requirement_analysis"``).
        version:
            Optional version string (e.g. ``"1.0.0"``).  When supplied, the
            exact ``(prompt_id, version)`` pair is returned.  When omitted and
            exactly one version of the prompt is registered, that version is
            returned unambiguously.

        Raises
        ------
        PromptNotFoundError
            If no definition matches the given identifier (and optional
            version).
        PromptRegistryError
            If ``version`` is omitted and multiple versions of the same
            ``prompt_id`` are registered (ambiguous lookup).
        """
        if version is not None:
            key = (prompt_id, version)
            definition = self._index.get(key)
            if definition is None:
                raise PromptNotFoundError(
                    f"No prompt registered for prompt_id={prompt_id!r} version={version!r}."
                )
            return definition

        # Version not specified — find all versions of this prompt_id.
        matches = [d for d in self._definitions if d.metadata.prompt_id == prompt_id]
        if not matches:
            raise PromptNotFoundError(f"No prompt registered for prompt_id={prompt_id!r}.")
        if len(matches) > 1:
            versions = [d.metadata.version for d in matches]
            raise PromptRegistryError(
                f"Ambiguous lookup: prompt_id={prompt_id!r} has multiple "
                f"registered versions {versions!r}. Specify a version explicitly."
            )
        return matches[0]

    def get_all(self) -> list[PromptDefinition]:
        """Return all registered definitions in registration order.

        Returns
        -------
        list[PromptDefinition]
            A copy of the registered definitions in registration order.
            An empty list when none are registered.
        """
        return list(self._definitions)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_prompt_ids(self) -> list[str]:
        """Return distinct prompt IDs in registration order (first-seen)."""
        seen: set[str] = set()
        result: list[str] = []
        for d in self._definitions:
            if d.metadata.prompt_id not in seen:
                seen.add(d.metadata.prompt_id)
                result.append(d.metadata.prompt_id)
        return result

    def count(self) -> int:
        """Return the total number of registered definitions."""
        return len(self._definitions)

    def is_registered(self, prompt_id: str, version: str | None = None) -> bool:
        """Return ``True`` when a matching definition is registered.

        Parameters
        ----------
        prompt_id:
            The stable prompt identifier to check.
        version:
            Optional version string.  When supplied, checks the exact pair.
            When omitted, checks whether *any* version of the prompt exists.
        """
        if version is not None:
            return (prompt_id, version) in self._index
        return any(d.metadata.prompt_id == prompt_id for d in self._definitions)
