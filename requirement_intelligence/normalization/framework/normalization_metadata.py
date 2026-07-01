"""Immutable descriptive metadata for a normalization responsibility.

This module defines :class:`NormalizationResponsibilityMetadata` — the canonical
runtime *identity* model for a
:class:`~requirement_intelligence.normalization.framework.normalization_responsibility.NormalizationResponsibility`.

It mirrors the validation framework's ``ValidationRuleMetadata`` in spirit and in
maturity: descriptive identity is *information* (immutable, versioned,
observable), separate from normalization *behaviour* (the ``normalize`` method).
A responsibility now owns **exactly one** immutable metadata value; every legacy
identity property is a thin read-through wrapper over it (see
:class:`NormalizationResponsibility`).

Runtime identity, not governing architecture
---------------------------------------------
This metadata is **runtime identity** — the value a responsibility carries into
result records, telemetry, and audit trails at execution time.  It is **not** the
architecture.  *Which* responsibilities exist, *what* each one owns, *what* it
depends on, and *in what order* they participate are governed permanently by the
**Normalization Responsibility Catalog**
(``docs/architecture/normalization-responsibility-catalog.md``).  The metadata
merely *declares* a responsibility's catalog-assigned identity at runtime; it
never defines or overrides it.  The catalog governs; the metadata reports.

Deliberate deviations from ValidationRuleMetadata
-------------------------------------------------
The two models are **siblings**, not clones.  Each deviation tracks a deviation
the normalization subsystem already made:

* **No layer; a descriptive ``order`` instead.**  ``ValidationRuleMetadata``
  carries a ``validation_layer`` because a rule belongs to one of nine ordered
  validation layers, and the validation registry *sorts by it*.  **Normalization
  has no layers** — responsibilities execute in **registration order**
  (Responsibility Catalog §8).  This model therefore has **no layer attribute**.
  It carries an ``order`` field instead — the responsibility's frozen position in
  the catalog chain (``0001 → 0002 → … → 0005``, Catalog §4).  Crucially, ``order``
  is **descriptive identity only**: the registry and pipeline **never sort by it**
  and **never read it** to sequence execution (Catalog §8: "there is no separate
  ordering dimension").  Registration order remains the sole execution order; a
  conforming caller registers in catalog order, so ``order`` and registration
  order agree by construction without the framework ever consuming ``order``.

* **``responsibility_catalog_version``.**  The version of the Normalization
  Responsibility Catalog under which this identity was declared.  There is no
  direct ValidationRuleMetadata analogue; it exists because the catalog is the
  governing architecture and its version is part of a responsibility's runtime
  provenance.

* **A free-form ``metadata`` map.**  A read-only mapping for classification and
  provenance labels that are not first-class identity.  ``ValidationRuleMetadata``
  has none; it is added here (mirroring ``NormalizationExecutionContext.metadata``)
  so descriptive identity can carry auxiliary labels without a schema change.

Immutability
------------
The metadata object is a frozen value.  Once created it can never change —
attempting to reassign any attribute raises
:class:`dataclasses.FrozenInstanceError`.  The free-form :attr:`metadata` map is
additionally wrapped in a read-only :class:`types.MappingProxyType`, so the whole
value object is immutable in content, not merely in its attribute bindings.
Immutable identity is what lets a responsibility's identity appear safely in
result records and observability without any risk of post-hoc mutation — the same
guarantee ``ValidationRuleMetadata`` provides for validation.

Reserved extension points
-------------------------
Several attributes are declared but **reserved** for future use so the metadata
contract can grow without a breaking change:

* ``tags`` — free-form classification labels.
* ``documentation_reference`` — a pointer to the responsibility's documentation.
* ``responsibility_catalog_version`` — the catalog version this identity targets.
* ``future_schema_compatibility`` — a declared compatibility marker for
  ParsedResponse / result schema evolution.
* ``normalization_contract_version`` — the normalization *semantics* version the
  responsibility targets (the direct ``validation_contract_version`` analogue).
* ``metadata`` — auxiliary, free-form descriptive labels.

Reserved attributes have no behaviour today; they default to empty/``None`` and
carry no execution meaning.

Version glossary
----------------
Independent versions govern normalization; they must never be conflated:

* **Responsibility Version** (``responsibility_version``, here) — the version of
  *one responsibility's* logic.  Default ``"1.0.0"``.
* **Responsibility Catalog Version** (``responsibility_catalog_version``, here) —
  the version of the governing Normalization Responsibility Catalog (Catalog §9).
* **Normalization Contract Version** (``normalization_contract_version``, here) —
  the version of normalization *semantics* for the whole subsystem (contract §12).
* **ParsedResponse Version** — the version of the canonical representation's
  *shape* (contract §12); owned by the ``ParsedResponse`` model.
* **Framework / Pipeline / Registry Versions** — framework-component versions (see
  ``normalization_framework_metadata``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

#: The default version assigned to a responsibility whose metadata omits one.
DEFAULT_RESPONSIBILITY_VERSION = "1.0.0"

#: The default ``order`` for a responsibility whose metadata omits one.  ``0``
#: means "unpositioned": a responsibility may declare a position for observability,
#: but the framework never consumes ``order`` to sequence execution (registration
#: order is authoritative).
DEFAULT_RESPONSIBILITY_ORDER = 0


@dataclass(frozen=True)
class NormalizationResponsibilityMetadata:
    """Immutable descriptive identity of a single normalization responsibility.

    A frozen value object: every attribute is fixed at construction and can
    never be reassigned.  Two metadata objects with the same attribute values
    are equal.  This is **runtime identity** — the value carried into result
    records and telemetry — not governing architecture; the Normalization
    Responsibility Catalog governs *which* responsibilities exist and *how they
    are ordered* (see the module docstring).

    Active attributes
    -----------------
    responsibility_id:
        Stable, globally unique identifier of a framework responsibility.
        Convention: ``<NAME>-NNNN`` (e.g. a generic ``EXAMPLE-0001``).  It is
        **not** a validation rule id, and it is **not** one of the
        ``NORMALIZATION-0001…0005`` internal ``ResponseNormalizer`` stages
        (ADR-0002).  Appears in result records, so it must not change once
        published.
    responsibility_name:
        Short, human-readable label.  Example: ``"Recover canonical structure"``.
    responsibility_version:
        The version of *this responsibility's* logic.  Defaults to
        :data:`DEFAULT_RESPONSIBILITY_VERSION` (``"1.0.0"``).
    order:
        The responsibility's declared position in the catalog chain
        (``0001 → 0002 → … → 0005``, Catalog §4).  **Descriptive identity only** —
        the registry and pipeline never read it to sequence execution
        (Catalog §8: registration order *is* execution order; there is no separate
        ordering dimension).  Defaults to :data:`DEFAULT_RESPONSIBILITY_ORDER`
        (``0``, "unpositioned").
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
    responsibility_catalog_version:
        Reserved.  The Normalization Responsibility Catalog version this identity
        targets (Catalog §9).  Defaults to ``None``.
    future_schema_compatibility:
        Reserved.  A declared ParsedResponse / result schema compatibility marker.
        Defaults to ``None``.
    normalization_contract_version:
        Reserved.  The normalization *semantics* version the responsibility
        targets (contract §12; the direct ``validation_contract_version``
        analogue).  Defaults to ``None``.
    metadata:
        Reserved.  A read-only mapping of auxiliary, free-form descriptive labels.
        Wrapped in :class:`types.MappingProxyType` so it cannot be mutated.
        Defaults to an empty mapping.

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
    order: int = DEFAULT_RESPONSIBILITY_ORDER
    enabled: bool = True

    # --- Reserved extension points ----------------------------------------
    tags: tuple[str, ...] = field(default=())
    documentation_reference: str | None = None
    responsibility_catalog_version: str | None = None
    future_schema_compatibility: str | None = None
    normalization_contract_version: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Freeze the free-form map's *content*, not just its binding, so the whole
        # value object is immutable.  A caller may pass any mapping (or rely on the
        # empty default); we store a read-only proxy over a private copy of it.
        # Equality is unaffected — MappingProxyType compares by content.
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(
                self, "metadata", MappingProxyType(dict(self.metadata))
            )
