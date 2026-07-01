"""Immutable descriptive metadata for a normalization stage.

This module defines :class:`NormalizationStageMetadata` — the canonical runtime
*identity* of one internal normalization **stage** of the ``ResponseNormalizer``
(``NORMALIZATION-0001 … 0005``).

Why a stage has its own identity model
--------------------------------------
Per **ADR-0002**, the five catalog stages are **internal to the
``ResponseNormalizer``** and are **not** framework
:class:`~requirement_intelligence.normalization.framework.normalization_responsibility.NormalizationResponsibility`
instances.  A stage therefore carries its *own* identity model, distinct from the
framework's ``NormalizationResponsibilityMetadata``.  The two models are siblings
in discipline (both immutable, versioned, observable) and disjoint in subject: one
identifies a generic framework execution unit, the other identifies an internal
assembly stage governed by the Normalization Responsibility Catalog.

Runtime identity, not governing architecture
---------------------------------------------
This metadata is **runtime identity** — the value a stage carries into
observability and provenance at execution time.  It is **not** the architecture.
*Which* stages exist, *what* each owns, *what* it depends on, and *in what order*
they participate are governed permanently by the **Normalization Responsibility
Catalog** (``docs/architecture/normalization-responsibility-catalog.md``) and the
**Normalization Assembly Contract**
(``docs/architecture/normalization-assembly-contract.md``).  The metadata merely
*declares* a stage's catalog-assigned identity at runtime; it never defines or
overrides it.

Immutability
------------
The metadata object is a frozen value: every attribute is fixed at construction
and can never be reassigned (a reassignment raises
:class:`dataclasses.FrozenInstanceError`).  Immutable identity is what lets a
stage's identity appear safely in provenance without any risk of post-hoc
mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The default version assigned to a stage whose metadata omits one.
DEFAULT_STAGE_VERSION = "1.0.0"

#: The default ``order`` for a stage whose metadata omits one.  ``0`` means
#: "unpositioned"; the five catalog stages declare positions ``1`` through ``5`` to
#: mirror their frozen ``NORMALIZATION-000N`` position in the chain (Catalog §4).
DEFAULT_STAGE_ORDER = 0


@dataclass(frozen=True)
class NormalizationStageMetadata:
    """Immutable descriptive identity of a single normalization stage.

    A frozen value object: every attribute is fixed at construction and can
    never be reassigned.  Two metadata objects with the same attribute values
    are equal.  This is **runtime identity**, not governing architecture (see the
    module docstring): the Normalization Responsibility Catalog and the
    Normalization Assembly Contract govern *which* stages exist and *how they
    collaborate*.

    Active attributes
    -----------------
    stage_id:
        Stable, globally unique identifier from the Normalization Responsibility
        Catalog (Contract §13).  Convention: ``NORMALIZATION-NNNN`` (e.g.
        ``NORMALIZATION-0001``).  Immutable once published (Catalog §3.9).
    stage_name:
        Short, human-readable label.  Example: ``"Recover Canonical Structure"``.
    stage_version:
        The version of *this stage's* logic.  Defaults to
        :data:`DEFAULT_STAGE_VERSION` (``"1.0.0"``).
    order:
        The stage's declared position in the assembly chain
        (``0001 → 0002 → … → 0005``, Catalog §4; Assembly Contract §5).  Defaults
        to :data:`DEFAULT_STAGE_ORDER`.
    enabled:
        Whether the stage participates in the assembly chain.  Defaults to
        ``True``.

    Reserved attributes (future extension points)
    ----------------------------------------------
    tags:
        Reserved.  Free-form classification labels.  Defaults to an empty tuple.
    documentation_reference:
        Reserved.  A pointer to the stage's documentation.  Defaults to ``None``.
    responsibility_catalog_version:
        Reserved.  The Normalization Responsibility Catalog version this identity
        targets (Catalog §9).  Defaults to ``None``.

    Notes
    -----
    Reserved attributes have no behaviour today; they exist so the contract can be
    extended without a breaking change.
    """

    # --- Active identity (required) ---------------------------------------
    stage_id: str
    stage_name: str

    # --- Active identity (defaulted) --------------------------------------
    stage_version: str = DEFAULT_STAGE_VERSION
    order: int = DEFAULT_STAGE_ORDER
    enabled: bool = True

    # --- Reserved extension points ----------------------------------------
    tags: tuple[str, ...] = field(default=())
    documentation_reference: str | None = None
    responsibility_catalog_version: str | None = None
