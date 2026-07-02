"""Syntax-layer validation rules.

The Syntax layer answers one family of concerns: *is the response well-formed
structured data that can be interpreted without ambiguity?*  Syntax rules **read**
the normalized representation the Response Normalization Layer already produced —
they never parse, normalize, recover, or repair structure (Rule Catalog §8.2;
Syntax Layer Design Review).

Currently implemented (the Syntax layer is complete — all three rules)
----------------------------------------------------------------------
* ``SYNTAX-0001`` :class:`ValidStructureRule` — the response normalized into
  well-formed structured data (the Normalization Outcome is not ``MALFORMED``).
* ``SYNTAX-0002`` :class:`DuplicateKeysRule` — normalization reported no
  ``duplicate_identifier`` observations (no field identifier duplicated within a
  structural object).
* ``SYNTAX-0003`` :class:`EncodingRule` — normalization reported no
  ``encoding_observation`` observations (the response's character encoding is
  intact).

Registration
------------
:func:`register_syntax_rules` registers every implemented Syntax rule with a
:class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
using the framework's existing ``register`` mechanism.  It makes **no**
behavioural change to the registry, and must be called before the pipeline is
constructed (the pipeline seals its registry on construction).
"""

from __future__ import annotations

from requirement_intelligence.validation.rules.syntax.duplicate_keys_rule import (
    DuplicateKeysRule,
)
from requirement_intelligence.validation.rules.syntax.encoding_rule import (
    EncodingRule,
)
from requirement_intelligence.validation.rules.syntax.valid_structure_rule import (
    ValidStructureRule,
)
from requirement_intelligence.validation.validation_registry import ValidationRegistry

__all__ = [
    "DuplicateKeysRule",
    "EncodingRule",
    "ValidStructureRule",
    "register_syntax_rules",
]


def register_syntax_rules(registry: ValidationRegistry) -> None:
    """Register every implemented Syntax rule with *registry*.

    Uses the existing :meth:`ValidationRegistry.register` mechanism; the registry's
    behaviour is unchanged.  Rules are registered in catalog order
    (``SYNTAX-0001`` → ``SYNTAX-0002`` → ``SYNTAX-0003``); within the Syntax layer
    the pipeline preserves registration order.  The Syntax layer is complete; new
    rules would be added by registering them here — no framework change is required.

    Parameters
    ----------
    registry:
        The open registry to populate.  Must not yet be sealed.
    """
    registry.register(ValidStructureRule())
    registry.register(DuplicateKeysRule())
    registry.register(EncodingRule())
