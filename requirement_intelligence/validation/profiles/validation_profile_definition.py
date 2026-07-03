"""Validation Profile definition — an immutable, governed rule-selection identity.

A :class:`ValidationProfileDefinition` names a **breadth of validation**: the set
of validation layers whose implemented rules a run executes. It is an
**orchestration** artifact, not a canonical validation model — it carries no
validation logic, produces no findings, and is never consumed by a rule. Rules
remain wholly unaware of profiles (Response Validator Architecture §4.5).

Governed identity
-----------------
Each profile has a **permanent identity** (its ``name``). Profiles are never
aliases: two profiles may currently enable the exact same layers yet remain
distinct governed identities, so a future version can diverge without any
architectural change. The layer *selection* only narrows *which* implemented
rules run; it never alters their order — ordering is governed exclusively by
``LAYER_ORDER`` and owned by the registry.
"""

from __future__ import annotations

from dataclasses import dataclass

from requirement_intelligence.validation.validation_rule_layer import ValidationLayer


@dataclass(frozen=True)
class ValidationProfileDefinition:
    """An immutable, governed selection of validation layers.

    Fields
    ------
    name:
        The permanent, governed profile identity (e.g. ``"transport-only"``).
    description:
        A human-readable statement of the profile's intent.
    enabled_layers:
        The validation layers this profile enables, in Rule-Catalog order. The
        implemented rules of exactly these layers are the profile's rule set;
        every other layer contributes nothing. Selection only narrows the rule
        set — it never changes ordering.
    """

    name: str
    description: str
    enabled_layers: tuple[ValidationLayer, ...]

    @property
    def enabled_layer_values(self) -> tuple[str, ...]:
        """The enabled layers' serialised values, in declared (Rule-Catalog) order."""
        return tuple(layer.value for layer in self.enabled_layers)
