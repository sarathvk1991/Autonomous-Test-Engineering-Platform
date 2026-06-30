"""Immutable descriptive metadata for a normalization responsibility.

This module defines :class:`NormalizationResponsibilityMetadata` — the canonical
identity model for a
:class:`~requirement_intelligence.normalization.framework.normalization_responsibility.NormalizationResponsibility`.

It mirrors the validation framework's ``ValidationRuleMetadata`` in spirit:
descriptive identity is *information* (immutable, versioned, observable),
separate from normalization *behaviour* (the ``normalize`` method).

Deliberate deviation from ValidationRuleMetadata
------------------------------------------------
``ValidationRuleMetadata`` carries a ``validation_layer`` — a rule belongs to one
of nine ordered validation layers.  **Normalization has no layers** (see the
framework README); responsibilities execute in registration order.  This
metadata therefore has **no layer attribute**.  Its identity is the
``NORMALIZATION-NNNN`` responsibility id from the Normalization Responsibility
Catalog (Response Normalization Contract §13) — which is *not* a validation rule
id and never participates in the validation Rule Catalog.

Immutability
------------
The metadata object is a frozen value.  Once created it can never change —
attempting to reassign any attribute raises
:class:`dataclasses.FrozenInstanceError`.  Immutable metadata is what lets a
responsibility's identity appear safely in result records and observability
without any risk of post-hoc mutation.

Reserved extension points
-------------------------
Several attributes are declared but **reserved** for future use so the metadata
contract can grow without a breaking change:

* ``tags`` — free-form classification labels.
* ``documentation_reference`` — a pointer to the responsibility's documentation.
* ``normalization_contract_version`` — the normalization *semantics* version the
  responsibility targets (distinct from ``responsibility_version``).

Version glossary
----------------
Independent versions govern normalization; they must never be conflated:

* **Responsibility Version** (``responsibility_version``, here) — the version of
  *one responsibility's* logic.  Default ``"1.0.0"``.
* **Normalization Contract Version** — the version of normalization *semantics*
  for the whole subsystem (contract §12).
* **ParsedResponse Version** — the version of the canonical representation's
  *shape* (contract §12); owned by the future ParsedResponse model.
* **Framework / Pipeline / Registry / Responsibility-Catalog Versions** —
  framework-component versions (see ``normalization_framework_metadata``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The default version assigned to a responsibility whose metadata omits one.
DEFAULT_RESPONSIBILITY_VERSION = "1.0.0"


@dataclass(frozen=True)
class NormalizationResponsibilityMetadata:
    """Immutable descriptive identity of a single normalization responsibility.

    A frozen value object: every attribute is fixed at construction and can
    never be reassigned.  Two metadata objects with the same attribute values
    are equal.

    Active attributes
    -----------------
    responsibility_id:
        Stable, globally unique identifier from the Normalization Responsibility
        Catalog (contract §13).  Convention: ``NORMALIZATION-NNNN`` (e.g.
        ``NORMALIZATION-0001``).  It is **not** a validation rule id and never
        appears in the validation Rule Catalog.  Appears in result records, so it
        must not change once published.
    responsibility_name:
        Short, human-readable label.  Example: ``"Recover normalized structure"``.
    responsibility_version:
        The version of *this responsibility's* logic.  Defaults to
        :data:`DEFAULT_RESPONSIBILITY_VERSION` (``"1.0.0"``).
    enabled:
        Whether the responsibility participates in pipeline execution.  Defaults
        to ``True``.  A disabled responsibility is registered but skipped.

    Reserved attributes (future extension points)
    ----------------------------------------------
    tags:
        Reserved.  Free-form classification labels.  Defaults to an empty tuple.
    documentation_reference:
        Reserved.  A pointer to the responsibility's documentation.  Defaults to
        ``None``.
    normalization_contract_version:
        Reserved.  The normalization *semantics* version the responsibility
        targets.  Defaults to ``None``.

    Notes
    -----
    Reserved attributes have no behaviour today.  They exist so the metadata
    contract can be extended without a breaking change.
    """

    # --- Active identity (required) ---------------------------------------
    responsibility_id: str
    responsibility_name: str

    # --- Active identity (defaulted) --------------------------------------
    responsibility_version: str = DEFAULT_RESPONSIBILITY_VERSION
    enabled: bool = True

    # --- Reserved extension points ----------------------------------------
    tags: tuple[str, ...] = field(default=())
    documentation_reference: str | None = None
    normalization_contract_version: str | None = None
