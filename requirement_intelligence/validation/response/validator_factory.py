"""Validator factory — the composition root for the Response Validation subsystem.

This module wires the already-frozen framework parts into a ready-to-run
:class:`~requirement_intelligence.validation.response.response_validator.ResponseValidator`
that executes **every implemented validation rule** in Rule-Catalog order.  It adds
**no** validation logic, **no** ordering logic, and **no** aggregation logic — those
belong to the frozen registry, pipeline, and rules.  It only *assembles* them:

1. create an open :class:`ValidationRegistry`,
2. populate it via :func:`register_all_rules` (every implemented layer's frozen helper),
3. construct the :class:`ValidationPipeline` (which seals the registry and owns rule
   ordering + verdict/issue aggregation),
4. construct the :class:`ResponseValidator` with the platform-default configuration.

Ordering is guaranteed by the registry's architecture-mandated ``LAYER_ORDER`` sort;
the resulting execution order over the implemented layers is
**Transport → Syntax → Schema → Content → Reasoning**.  The Structural, Evidence,
Traceability, and Business layers — and every deferred rule — are intentionally absent
because they have no implementation to register (no special-casing; they simply
contribute nothing).

Nothing here modifies a frozen contract: the registry, pipeline, rule contract, and
``ResponseValidator`` are used exactly as published (ADR-0003; Response Validator
Architecture §5).  This is the additive "wiring" step the Response Validator was
designed to receive.
"""

from __future__ import annotations

from requirement_intelligence.validation.models.validation_configuration import (
    ValidationConfiguration,
)
from requirement_intelligence.validation.response.response_validator import ResponseValidator
from requirement_intelligence.validation.rules import register_all_rules
from requirement_intelligence.validation.validation_pipeline import ValidationPipeline
from requirement_intelligence.validation.validation_registry import ValidationRegistry


def build_validation_registry() -> ValidationRegistry:
    """Return a fresh registry populated with every implemented rule (still open).

    The registry is **not** sealed — the caller (or the pipeline it is handed to)
    seals it.  Rules are populated via :func:`register_all_rules`; retrieval order is
    the architecture-mandated ``LAYER_ORDER``.
    """
    registry = ValidationRegistry()
    register_all_rules(registry)
    return registry


def build_validation_pipeline(
    registry: ValidationRegistry | None = None,
) -> ValidationPipeline:
    """Return a pipeline over every implemented rule.

    Constructs (and thereby seals) a :class:`ValidationPipeline` from *registry*, or
    from a freshly-populated registry when none is supplied.  The pipeline owns rule
    ordering and verdict/issue aggregation; this factory adds none of that.

    Parameters
    ----------
    registry:
        An already-populated, unsealed registry to use.  When ``None``, a fresh
        registry populated by :func:`build_validation_registry` is used.
    """
    return ValidationPipeline(registry if registry is not None else build_validation_registry())


def build_response_validator(
    configuration: ValidationConfiguration | None = None,
) -> ResponseValidator:
    """Return a ready :class:`ResponseValidator` over every implemented rule.

    The composition root for end-to-end validation: it assembles the registry, the
    pipeline, and the validator, so a caller can validate a
    :class:`~requirement_intelligence.validation.models.validation_input.ValidationInput`
    with no manual wiring.  The validator executes the implemented rules in
    Rule-Catalog order (Transport → Syntax → Schema → Content → Reasoning) and returns
    the single canonical
    :class:`~requirement_intelligence.validation.models.validation_result.ValidationResult`.

    Parameters
    ----------
    configuration:
        The platform-default :class:`ValidationConfiguration`.  When ``None``, a
        fully-defaulted configuration is used (the frozen default path).

    Returns
    -------
    ResponseValidator
        A validator whose pipeline is populated with every implemented rule.
    """
    registry = build_validation_registry()
    pipeline = ValidationPipeline(registry)
    platform_defaults = configuration if configuration is not None else ValidationConfiguration()
    return ResponseValidator(registry, pipeline, platform_defaults)
