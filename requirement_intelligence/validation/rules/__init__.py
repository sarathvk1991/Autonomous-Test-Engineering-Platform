"""Concrete validation rule implementations, grouped by layer.

Every rule here conforms to ``docs/architecture/validation-rule-catalog.md`` and
is implemented per ``docs/development/validation-rule-development-guide.md``:
one rule per file, files grouped by validation layer.

Rules are discovered by **registration**, never by import side effects.  Each
layer package exposes a ``register_<layer>_rules`` helper that registers its
rules with a :class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
using the framework's existing registration mechanism.

Composition root
----------------
:func:`register_all_rules` is the single aggregation point: it calls every
implemented layer's ``register_<layer>_rules`` helper, in Rule-Catalog layer
order (Transport → Syntax → Schema → Content → Reasoning).  It adds **no**
registration logic of its own — it only composes the frozen per-layer helpers —
and it registers **only implemented** rules.  Deferred rules (e.g. ``SCHEMA-0003``,
``CONTENT-0003/0004``, ``REASONING-0001/0003``) have no implementation to register
and are therefore intentionally absent, as are the Structural, Evidence,
Traceability, and Business layers (no implemented rules).  The
:class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
sorts retrieved rules by the architecture-mandated
:data:`~requirement_intelligence.validation.validation_rule.LAYER_ORDER`, so the
execution order is guaranteed regardless of the call order here.
"""

from __future__ import annotations

from requirement_intelligence.validation.rules.content import register_content_rules
from requirement_intelligence.validation.rules.reasoning import register_reasoning_rules
from requirement_intelligence.validation.rules.schema import register_schema_rules
from requirement_intelligence.validation.rules.syntax import register_syntax_rules
from requirement_intelligence.validation.rules.transport import register_transport_rules
from requirement_intelligence.validation.validation_registry import ValidationRegistry

__all__ = [
    "register_all_rules",
]


def register_all_rules(registry: ValidationRegistry) -> None:
    """Register every **implemented** validation rule with *registry*.

    Calls each implemented layer's frozen ``register_<layer>_rules`` helper in
    Rule-Catalog layer order.  This function composes those helpers and adds no
    registration logic of its own; the registry preserves per-layer registration
    order and sorts across layers by ``LAYER_ORDER``.

    Only implemented rules are registered — deferred rules and layers with no
    implemented rules (Structural, Evidence, Traceability, Business) are
    intentionally absent (no special-casing; they simply have nothing to register).

    Parameters
    ----------
    registry:
        The open :class:`ValidationRegistry` to populate.  Must not yet be sealed.
    """
    register_transport_rules(registry)
    register_syntax_rules(registry)
    register_schema_rules(registry)
    register_content_rules(registry)
    register_reasoning_rules(registry)
