"""Validation rule registry.

The registry is the single source of truth for which
:class:`~requirement_intelligence.validation.validation_rule.ValidationRule`
implementations participate in a validation run.

Design notes
------------
* **No reflection, no dynamic loading, no filesystem scanning.**  Rules are
  registered explicitly by calling :meth:`ValidationRegistry.register`.  This
  mirrors the pattern used by the LLM provider factory (``_PROVIDER_REGISTRY``
  dict) and keeps the registry deterministic and testable.

* **Deterministic ordering.**  Rules are stored in insertion order per layer.
  When multiple rules across layers are retrieved, they are sorted by the
  architecture-mandated layer order
  (:data:`~requirement_intelligence.validation.validation_rule.LAYER_ORDER`).
  Within a layer, registration order is preserved.  The pipeline depends on
  this ordering guarantee — it never re-sorts.

* **Plug-in ready.**  The registry is the natural extension point for future
  modular rule sets.  A new rule is added in one line; no framework code
  changes.

* **No shared state.**  Each registry instance is independent.  The pipeline
  always owns its own registry instance.

Relationship to other frameworks
---------------------------------
The ValidationRegistry is the structural equivalent of:

* ``_PROVIDER_REGISTRY`` / :func:`~requirement_intelligence.llm.llm_factory.create_provider`
  in the LLM provider framework — maps a key to a component.
* The connector source-registry — catalogues available connectors without
  instantiating them.

The difference is that the ValidationRegistry stores *instances* (rules are
stateless and can be shared) rather than classes.
"""

from __future__ import annotations

from collections import defaultdict
from enum import Enum

from requirement_intelligence.validation.validation_exceptions import ValidationRegistryError
from requirement_intelligence.validation.validation_rule import (
    LAYER_ORDER,
    ValidationLayer,
    ValidationRule,
)


class RegistryState(Enum):
    """Lifecycle state of a :class:`ValidationRegistry`.

    Members
    -------
    OPEN
        The registry accepts new rule registrations.  This is the initial
        state of every registry.
    SEALED
        The registry is frozen against registration.  Any further call to
        :meth:`ValidationRegistry.register` raises
        :class:`~requirement_intelligence.validation.validation_exceptions.ValidationRegistryError`.
        A registry transitions to ``SEALED`` either explicitly via
        :meth:`ValidationRegistry.seal` or automatically when a
        :class:`~requirement_intelligence.validation.validation_pipeline.ValidationPipeline`
        is constructed from it.

    The transition is **one-directional**: a sealed registry cannot be reopened.
    This guarantees that the rule set a pipeline executes is fixed for the
    lifetime of that pipeline, which is what makes a validation run
    reproducible.
    """

    OPEN = "open"
    SEALED = "sealed"


class ValidationRegistry:
    """Registry that catalogues :class:`ValidationRule` instances.

    Rules are registered once, then queried by the pipeline.  The registry
    never instantiates rules; it stores and retrieves them.

    Lifecycle
    ---------
    A registry begins :attr:`~RegistryState.OPEN` and accepts registrations.
    Once :meth:`seal` is called — or a
    :class:`~requirement_intelligence.validation.validation_pipeline.ValidationPipeline`
    is constructed from it, which seals it automatically — the registry becomes
    :attr:`~RegistryState.SEALED` and refuses further registration.  Retrieval
    is permitted in either state.

    ::

        OPEN ──register()──► OPEN ──seal() / pipeline construction──► SEALED
                                                                         │
                                              register() ──► ValidationRegistryError

    Usage
    -----
    .. code-block:: python

        registry = ValidationRegistry()
        registry.register(MyRule())

        # All enabled rules in pipeline order:
        rules = registry.get_enabled_rules()

        # Rules for a specific layer:
        syntax_rules = registry.get_enabled_rules_by_layer(ValidationLayer.SYNTAX)
    """

    def __init__(self) -> None:
        # Primary store: layer → ordered list of rules (insertion order).
        # defaultdict keeps the code clean; all nine layers are valid keys.
        self._rules: dict[ValidationLayer, list[ValidationRule]] = defaultdict(list)

        # Secondary index: rule_id → rule, for O(1) duplicate detection.
        self._rule_ids: dict[str, ValidationRule] = {}

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

        Sealing is **idempotent**: sealing an already-sealed registry is a
        no-op and never raises.  Retrieval methods continue to work after
        sealing; only :meth:`register` is affected.

        The pipeline calls this automatically at construction time, so explicit
        calls are only needed when sealing a registry independently of a
        pipeline.
        """
        self._state = RegistryState.SEALED

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, rule: ValidationRule) -> None:
        """Register a validation rule.

        Parameters
        ----------
        rule:
            The :class:`ValidationRule` instance to register.  The instance
            must have a unique :attr:`~ValidationRule.rule_id`.

        Raises
        ------
        ValidationRegistryError
            If the registry has been sealed (see :meth:`seal`), or if a rule
            with the same ``rule_id`` is already registered.
        """
        if self._state is RegistryState.SEALED:
            raise ValidationRegistryError(
                f"Cannot register rule {rule.rule_id!r}: the registry is sealed. "
                f"Registration is only permitted while the registry is OPEN; "
                f"it is sealed automatically when a ValidationPipeline is "
                f"constructed from it."
            )
        if rule.rule_id in self._rule_ids:
            raise ValidationRegistryError(
                f"A rule with rule_id {rule.rule_id!r} is already registered. "
                f"Each rule_id must be unique within a registry instance."
            )
        self._rules[rule.validation_layer].append(rule)
        self._rule_ids[rule.rule_id] = rule

    # ------------------------------------------------------------------
    # Retrieval — all rules (enabled + disabled)
    # ------------------------------------------------------------------

    def get_rules_by_layer(self, layer: ValidationLayer) -> list[ValidationRule]:
        """Return all rules (enabled and disabled) for *layer*, in registration order.

        Parameters
        ----------
        layer:
            The :class:`ValidationLayer` to query.

        Returns
        -------
        list[ValidationRule]
            All rules registered under *layer*, in registration order.  An
            empty list when no rules are registered for the layer.
        """
        return list(self._rules[layer])

    def get_all_rules(self) -> list[ValidationRule]:
        """Return all registered rules, ordered by layer then registration order.

        Returns
        -------
        list[ValidationRule]
            All rules across all layers, sorted by the architecture-mandated
            :data:`~requirement_intelligence.validation.validation_rule.LAYER_ORDER`.
            Within a layer, insertion order is preserved.
        """
        ordered: list[ValidationRule] = []
        for layer in LAYER_ORDER:
            ordered.extend(self._rules[layer])
        return ordered

    # ------------------------------------------------------------------
    # Retrieval — enabled rules only
    # ------------------------------------------------------------------

    def get_enabled_rules(self) -> list[ValidationRule]:
        """Return all *enabled* rules, ordered by layer then registration order.

        This is the primary query used by the validation pipeline.

        Returns
        -------
        list[ValidationRule]
            All rules where :attr:`~ValidationRule.enabled` is ``True``,
            sorted by the architecture-mandated layer order.  Within a layer,
            insertion order is preserved.
        """
        return [rule for rule in self.get_all_rules() if rule.enabled]

    def get_enabled_rules_by_layer(self, layer: ValidationLayer) -> list[ValidationRule]:
        """Return enabled rules for a specific *layer*, in registration order.

        Parameters
        ----------
        layer:
            The :class:`ValidationLayer` to query.

        Returns
        -------
        list[ValidationRule]
            Enabled rules for *layer*, in registration order.
        """
        return [rule for rule in self._rules[layer] if rule.enabled]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_rule_ids(self) -> list[str]:
        """Return the ``rule_id`` of every registered rule, in pipeline order.

        Returns
        -------
        list[str]
            Sorted by layer order, then registration order within a layer.
        """
        return [rule.rule_id for rule in self.get_all_rules()]

    def rule_count(self) -> int:
        """Return the total number of registered rules (enabled and disabled).

        Returns
        -------
        int
        """
        return len(self._rule_ids)
