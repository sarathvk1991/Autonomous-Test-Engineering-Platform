"""Immutable descriptive metadata for a CP1 engineering-readiness criterion.

This module defines :class:`CP1CriterionMetadata` — the canonical identity model
for a :class:`~requirement_intelligence.cp1.framework.criterion.CP1Criterion`.  It
mirrors the Response Validation Framework's ``ValidationRuleMetadata`` (immutable,
versioned, observable identity separated from behaviour), adapted to CP1's **flat**
namespace.

No layer attribute
------------------
Unlike ``ValidationRuleMetadata``, this metadata carries **no** validation-layer
field: CP1 is a single flat namespace (``CP1-NNNN``), not a layered pipeline
(Engineering Readiness Criteria Catalog §4; ADR-0012).  A criterion belongs to the
catalog, not to a layer.

Immutability
------------
The metadata object is a frozen value.  Once created it can never change —
attempting to reassign any attribute raises :class:`dataclasses.FrozenInstanceError`.
Immutable metadata is what lets a criterion's identity appear safely in
:class:`~requirement_intelligence.cp1.models.cp1_finding.CP1Finding` records,
observability signals, and audit trails.

This module carries **no engineering-readiness knowledge**: it is pure identity.

Version glossary
----------------
* **Criterion Version** (``criterion_version``, here) — the version of *one
  criterion's* definition; advances when that criterion's definition changes.
* **Criteria Contract Version** — the version of the CP1 catalog *semantics* as a
  whole (governed by the Engineering Readiness Criteria Catalog / ADR-0012); lives
  in :mod:`~requirement_intelligence.cp1.models.framework_metadata`.
* **Framework Version** — the version of the framework *implementation* as a whole;
  also in ``framework_metadata``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The default version assigned to a criterion whose metadata does not specify one.
DEFAULT_CRITERION_VERSION = "1.0.0"


@dataclass(frozen=True)
class CP1CriterionMetadata:
    """Immutable descriptive identity of a single CP1 readiness criterion.

    A frozen value object: every attribute is fixed at construction and can never
    be reassigned.  Two metadata objects with the same attribute values are equal.

    Active attributes
    -----------------
    criterion_id:
        Stable, globally unique identifier for the criterion.  Convention:
        ``CP1-NNNN`` (Engineering Readiness Criteria Catalog §4).  Appears in
        ``CP1Finding`` records, so it must not change once published.
    criterion_name:
        Short, human-readable label describing the single readiness concern.
    criterion_version:
        The version of *this criterion's* definition.  Defaults to
        :data:`DEFAULT_CRITERION_VERSION` (``"1.0.0"``).
    enabled:
        Whether the criterion participates in pipeline execution.  Defaults to
        ``True``.  A disabled criterion is registered but skipped.

    Reserved attributes (future extension points)
    ----------------------------------------------
    tags:
        Reserved.  Free-form classification labels.  Defaults to an empty tuple.
    documentation_reference:
        Reserved.  A pointer to the criterion's catalog entry.  Defaults to ``None``.

    Notes
    -----
    Reserved attributes have no behaviour today.  They exist so the metadata
    contract can be extended without a breaking change.
    """

    # --- Active identity (required) ---------------------------------------
    criterion_id: str
    criterion_name: str

    # --- Active identity (defaulted) --------------------------------------
    criterion_version: str = DEFAULT_CRITERION_VERSION
    enabled: bool = True

    # --- Reserved extension points ----------------------------------------
    tags: tuple[str, ...] = field(default=())
    documentation_reference: str | None = None
