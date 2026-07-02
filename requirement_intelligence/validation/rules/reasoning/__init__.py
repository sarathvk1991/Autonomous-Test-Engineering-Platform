"""Reasoning-layer validation rules.

The Reasoning layer confirms the output is internally coherent and self-consistent —
contradictions, duplicated conclusions, and circular logic (Rule Catalog §8.8).
Reasoning rules **read** the normalized structure (`ParsedResponse.normalized_structure`);
they never parse, normalize, recover, or repair, and — being a semantic layer — they
**record** findings and never block (Rule Catalog §15).

Currently implemented
---------------------
* ``REASONING-0002`` :class:`DuplicateRecommendationRule` — no recommendation statement is
  duplicated under **byte-exact** comparison (Rule Catalog §9.8; mechanism frozen by
  ADR-0008; classified **Implementable** by ADR-0006).

Not implemented here
--------------------
* ``REASONING-0001`` ContradictoryRequirementRule and ``REASONING-0003`` CircularLogicRule
  are catalogued (§9.8) and classified **Implementable** by ADR-0006, but are **not**
  implemented by this task.  They are semantic-judgement rules whose mechanisms are
  non-trivial.

Registration
------------
:func:`register_reasoning_rules` registers every implemented Reasoning rule with a
:class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
using the framework's existing ``register`` mechanism.  It makes **no** behavioural
change to the registry, and must be called before the pipeline is constructed (the
pipeline seals its registry on construction).
"""

from __future__ import annotations

from requirement_intelligence.validation.rules.reasoning.duplicate_recommendation_rule import (
    DuplicateRecommendationRule,
)
from requirement_intelligence.validation.validation_registry import ValidationRegistry

__all__ = [
    "DuplicateRecommendationRule",
    "register_reasoning_rules",
]


def register_reasoning_rules(registry: ValidationRegistry) -> None:
    """Register every implemented Reasoning rule with *registry*.

    Uses the existing :meth:`ValidationRegistry.register` mechanism; the registry's
    behaviour is unchanged.  Rules are registered in catalog order; within the Reasoning
    layer the pipeline preserves registration order.  Further Reasoning rules are added by
    registering them here — no framework change is required.

    Parameters
    ----------
    registry:
        The open registry to populate.  Must not yet be sealed.
    """
    registry.register(DuplicateRecommendationRule())
