"""Syntax-layer validation rules.

The Syntax layer answers one family of concerns: *is the response well-formed
structured data that can be interpreted without ambiguity?*  Syntax rules **read**
the normalized representation the Response Normalization Layer already produced —
they never parse, normalize, recover, or repair structure (Rule Catalog §8.2;
Syntax Layer Design Review).

Currently implemented
---------------------
* ``SYNTAX-0001`` :class:`ValidStructureRule` — the response normalized into
  well-formed structured data (the Normalization Outcome is not ``MALFORMED``).

Reserved (not implemented here)
-------------------------------
* ``SYNTAX-0002`` DuplicateKeysRule and ``SYNTAX-0003`` EncodingRule are defined in
  the Rule Catalog (§9.2) but are **not** implemented by this task.

Registration
------------
:func:`register_syntax_rules` registers every implemented Syntax rule with a
:class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
using the framework's existing ``register`` mechanism.  It makes **no**
behavioural change to the registry, and must be called before the pipeline is
constructed (the pipeline seals its registry on construction).
"""

from __future__ import annotations

from requirement_intelligence.validation.rules.syntax.valid_structure_rule import (
    ValidStructureRule,
)
from requirement_intelligence.validation.validation_registry import ValidationRegistry

__all__ = [
    "ValidStructureRule",
    "register_syntax_rules",
]


def register_syntax_rules(registry: ValidationRegistry) -> None:
    """Register every implemented Syntax rule with *registry*.

    Uses the existing :meth:`ValidationRegistry.register` mechanism; the registry's
    behaviour is unchanged.  Rules are registered in catalog order; within the
    Syntax layer the pipeline preserves registration order.  New Syntax rules
    (``SYNTAX-0002``, ``SYNTAX-0003``) are added by registering them here — no
    framework change is required.

    Parameters
    ----------
    registry:
        The open registry to populate.  Must not yet be sealed.
    """
    registry.register(ValidStructureRule())
