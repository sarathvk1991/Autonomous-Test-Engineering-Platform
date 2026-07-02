"""Schema-layer validation rules.

The Schema layer confirms the well-formed structure conforms to the expected,
versioned, machine-readable shape — and, per **ADR-0004**, is the **sole owner of
existence**: the presence of every required property, section, container, and
collection, alongside type and enumeration conformance.  Schema rules **read** the
normalized structure (`ParsedResponse.normalized_structure`); they never parse,
normalize, recover, or repair (Rule Catalog §8.3; Schema Validation Implementation
Contract).

Currently implemented
---------------------
* ``SCHEMA-0001`` :class:`RequiredSectionsRule` — every required **non-collection**
  section/property is present (ADR-0004).
* ``SCHEMA-0002`` :class:`FieldTypesRule` — every governed field that is present is
  of its expected type (Rule Catalog §9.3, §8.3).

Reserved (not implemented here)
-------------------------------
* ``SCHEMA-0003`` EnumerationsRule and ``SCHEMA-0004`` RequiredArraysRule are defined
  in the Rule Catalog (§9.3) but are **not** implemented by this task.

Registration
------------
:func:`register_schema_rules` registers every implemented Schema rule with a
:class:`~requirement_intelligence.validation.validation_registry.ValidationRegistry`
using the framework's existing ``register`` mechanism.  It makes **no** behavioural
change to the registry, and must be called before the pipeline is constructed (the
pipeline seals its registry on construction).
"""

from __future__ import annotations

from requirement_intelligence.validation.rules.schema.field_types_rule import (
    FieldTypesRule,
)
from requirement_intelligence.validation.rules.schema.required_sections_rule import (
    RequiredSectionsRule,
)
from requirement_intelligence.validation.validation_registry import ValidationRegistry

__all__ = [
    "FieldTypesRule",
    "RequiredSectionsRule",
    "register_schema_rules",
]


def register_schema_rules(registry: ValidationRegistry) -> None:
    """Register every implemented Schema rule with *registry*.

    Uses the existing :meth:`ValidationRegistry.register` mechanism; the registry's
    behaviour is unchanged.  Rules are registered in catalog order; within the Schema
    layer the pipeline preserves registration order.  The remaining Schema rules
    (``SCHEMA-0003…0004``) are added by registering them here — no framework change is
    required.

    Parameters
    ----------
    registry:
        The open registry to populate.  Must not yet be sealed.
    """
    registry.register(RequiredSectionsRule())
    registry.register(FieldTypesRule())
