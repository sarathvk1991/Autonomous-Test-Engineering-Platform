"""Immutable descriptive metadata for a validation rule.

This module defines :class:`ValidationRuleMetadata` — the canonical identity
model for a :class:`~requirement_intelligence.validation.validation_rule.ValidationRule`.

Why metadata is a separate, immutable object
--------------------------------------------
Before this refinement, a rule exposed its identity through several independent
properties (``rule_id``, ``rule_name``, ``validation_layer``, ``enabled``).  That
scattered the rule's *descriptive identity* across the behavioural contract and
made it impossible to treat identity as a single, versioned, immutable value.

:class:`ValidationRuleMetadata` consolidates every descriptive property into one
**immutable** value object.  A rule now exposes a single
:attr:`~requirement_intelligence.validation.validation_rule.ValidationRule.metadata`
property; the legacy identity properties remain as thin convenience wrappers for
backward compatibility (see
:class:`~requirement_intelligence.validation.validation_rule.ValidationRule`).

This mirrors the Validation Canonical Models philosophy: descriptive identity is
*information* (immutable, versioned, observable), separate from validation
*behaviour* (the ``validate`` method).

Immutability
------------
The metadata object is a frozen value.  Once created it can never change —
attempting to reassign any attribute raises
:class:`dataclasses.FrozenInstanceError`.  Immutable metadata is what allows a
rule's identity to appear safely in validation result records, observability
signals, and audit trails without any risk of post-hoc mutation.

Reserved extension points
-------------------------
Several attributes are declared but **reserved** for future use.  They exist so
the metadata contract can grow without a breaking change:

* ``tags`` — free-form classification labels.
* ``documentation_reference`` — a pointer to the rule's documentation.
* ``validation_contract_version`` — the validation *semantics* version the rule
  targets (distinct from ``rule_version``; see the version glossary below).
* ``future_schema_compatibility`` — a declared compatibility marker for response
  schema evolution.

Only ``rule_id``, ``rule_name``, ``rule_version``, ``validation_layer``, and
``enabled`` are active today.  Reserved attributes default to empty/``None`` and
carry no behaviour.

Version glossary
----------------
Three independent versions govern validation; they must never be conflated:

* **Rule Version** (``rule_version``, here) — the version of *one rule's* logic.
  It advances when this specific rule's behaviour changes.  Default ``"1.0.0"``.
* **Validation Contract Version** — the version of the validation *semantics*
  for the whole subsystem (categories, severity model, pipeline, result/issue
  models).  Governed by ``docs/architecture/ai-response-validation.md`` §13.
* **Validator Version** — the version of the validator *implementation* as a
  whole, independent of semantics.

A rule may change (Rule Version bumps) without the Validation Contract Version
changing; the validator implementation may change (Validator Version bumps)
without any rule changing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from requirement_intelligence.validation.validation_rule_layer import ValidationLayer

#: The default version assigned to a rule whose metadata does not specify one.
DEFAULT_RULE_VERSION = "1.0.0"


@dataclass(frozen=True)
class ValidationRuleMetadata:
    """Immutable descriptive identity of a single validation rule.

    A frozen value object: every attribute is fixed at construction and can
    never be reassigned.  Two metadata objects with the same attribute values
    are equal.

    Active attributes
    -----------------
    rule_id:
        Stable, globally unique identifier for the rule.  Convention:
        ``<LAYER_PREFIX>-<NNNN>`` (e.g. ``SYNTAX-0001``).  Appears in validation
        result records, so it must not change once published.
    rule_name:
        Short, human-readable label.  Example: ``"Syntax: Well-formed JSON"``.
    validation_layer:
        The single :class:`ValidationLayer` this rule belongs to.
    rule_version:
        The version of *this rule's* logic.  Defaults to
        :data:`DEFAULT_RULE_VERSION` (``"1.0.0"``).  Distinct from the
        Validation Contract Version and the Validator Version (see module
        docstring).
    enabled:
        Whether the rule participates in pipeline execution.  Defaults to
        ``True``.  A disabled rule is registered but skipped.

    Reserved attributes (future extension points)
    ----------------------------------------------
    tags:
        Reserved.  Free-form classification labels.  Defaults to an empty tuple.
    documentation_reference:
        Reserved.  A pointer to the rule's documentation.  Defaults to ``None``.
    validation_contract_version:
        Reserved.  The validation *semantics* version the rule targets.
        Defaults to ``None``.
    future_schema_compatibility:
        Reserved.  A declared response-schema compatibility marker.  Defaults to
        ``None``.

    Notes
    -----
    Reserved attributes have no behaviour today.  They exist so the metadata
    contract can be extended without a breaking change.
    """

    # --- Active identity (required) ---------------------------------------
    rule_id: str
    rule_name: str
    validation_layer: ValidationLayer

    # --- Active identity (defaulted) --------------------------------------
    rule_version: str = DEFAULT_RULE_VERSION
    enabled: bool = True

    # --- Reserved extension points ----------------------------------------
    tags: tuple[str, ...] = field(default=())
    documentation_reference: str | None = None
    validation_contract_version: str | None = None
    future_schema_compatibility: str | None = None
