"""Content-layer validation rules.

The Content layer confirms individual field-level values meet presence and validity
expectations — empty entries, duplicated entries, missing descriptions, and
out-of-range values (Rule Catalog §8.5).  Content rules **read** the normalized
structure (`ParsedResponse.normalized_structure`); they never parse, normalize,
recover, or repair, and — being a semantic layer — they **record** findings and never
block (Rule Catalog §15).

Currently implemented
---------------------
* ``CONTENT-0001`` :class:`EmptyRequirementRule` — a requirement statement is not empty
  (Rule Catalog §9.5; classified **Implementable** by ADR-0006).
* ``CONTENT-0002`` :class:`DuplicateRequirementRule` — no requirement statement is
  duplicated **within one governed requirement collection** (Rule Catalog §9.5; scope
  frozen by ADR-0007; classified **Implementable** by ADR-0006).

Reserved / deferred (not implemented here)
------------------------------------------
* ``CONTENT-0003`` MissingDescriptionRule and ``CONTENT-0004`` InvalidConfidenceRule are
  **Reserved · Deferred** (ADR-0006): the governed response carries no per-item
  description or confidence, so they have nothing to validate today.

Registration
------------
:func:`register_content_rules` registers every implemented Content rule with a
:class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
using the framework's existing ``register`` mechanism.  It makes **no** behavioural
change to the registry, and must be called before the pipeline is constructed (the
pipeline seals its registry on construction).
"""

from __future__ import annotations

from requirement_intelligence.validation.rules.content.duplicate_requirement_rule import (
    DuplicateRequirementRule,
)
from requirement_intelligence.validation.rules.content.empty_requirement_rule import (
    EmptyRequirementRule,
)
from requirement_intelligence.validation.validation_registry import ValidationRegistry

__all__ = [
    "DuplicateRequirementRule",
    "EmptyRequirementRule",
    "register_content_rules",
]


def register_content_rules(registry: ValidationRegistry) -> None:
    """Register every implemented Content rule with *registry*.

    Uses the existing :meth:`ValidationRegistry.register` mechanism; the registry's
    behaviour is unchanged.  Rules are registered in catalog order; within the Content
    layer the pipeline preserves registration order.  Further Content rules are added by
    registering them here — no framework change is required.

    Parameters
    ----------
    registry:
        The open registry to populate.  Must not yet be sealed.
    """
    registry.register(EmptyRequirementRule())
    registry.register(DuplicateRequirementRule())
