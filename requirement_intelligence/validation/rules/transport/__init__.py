"""Transport-layer validation rules.

The Transport layer answers the most foundational question of the validation
pipeline: *was a usable response received at all?*  Rules here never inspect
content, structure, schema, or meaning.

Currently implemented (the Transport layer is complete — all four rules)
------------------------------------------------------------------------
* ``TRANSPORT-0001`` :class:`ResponseExistsRule` — the LLM response is present.
* ``TRANSPORT-0002`` :class:`EmptyResponseRule` — the response carries content.
* ``TRANSPORT-0003`` :class:`TimeoutRule` — the execution did not time out.
* ``TRANSPORT-0004`` :class:`ProviderFailureRule` — the execution did not fail at
  the provider/delivery boundary.

Registration
------------
:func:`register_transport_rules` registers every implemented Transport rule with
a :class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
using the framework's existing ``register`` mechanism.  It makes **no**
behavioural change to the registry, and must be called before the pipeline is
constructed (the pipeline seals its registry on construction).
"""

from __future__ import annotations

from requirement_intelligence.validation.rules.transport.empty_response_rule import (
    EmptyResponseRule,
)
from requirement_intelligence.validation.rules.transport.provider_failure_rule import (
    ProviderFailureRule,
)
from requirement_intelligence.validation.rules.transport.response_exists_rule import (
    ResponseExistsRule,
)
from requirement_intelligence.validation.rules.transport.timeout_rule import TimeoutRule
from requirement_intelligence.validation.validation_registry import ValidationRegistry

__all__ = [
    "EmptyResponseRule",
    "ProviderFailureRule",
    "ResponseExistsRule",
    "TimeoutRule",
    "register_transport_rules",
]


def register_transport_rules(registry: ValidationRegistry) -> None:
    """Register every implemented Transport rule with *registry*.

    Uses the existing :meth:`ValidationRegistry.register` mechanism; the
    registry's behaviour is unchanged.  Rules are registered in catalog order
    (``TRANSPORT-0001`` → ``TRANSPORT-0002`` → ``TRANSPORT-0003`` →
    ``TRANSPORT-0004``); within the Transport layer the pipeline preserves
    registration order.  New Transport rules are added by registering them here —
    no framework change is required.

    Parameters
    ----------
    registry:
        The open registry to populate.  Must not yet be sealed.
    """
    registry.register(ResponseExistsRule())
    registry.register(EmptyResponseRule())
    registry.register(TimeoutRule())
    registry.register(ProviderFailureRule())
