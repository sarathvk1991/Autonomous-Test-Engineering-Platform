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

from collections.abc import Callable

from requirement_intelligence.validation.models.validation_configuration import (
    ValidationConfiguration,
)
from requirement_intelligence.validation.profiles import ValidationProfileDefinition
from requirement_intelligence.validation.response.response_validator import ResponseValidator
from requirement_intelligence.validation.rules import register_all_rules
from requirement_intelligence.validation.rules.content import register_content_rules
from requirement_intelligence.validation.rules.reasoning import register_reasoning_rules
from requirement_intelligence.validation.rules.schema import register_schema_rules
from requirement_intelligence.validation.rules.syntax import register_syntax_rules
from requirement_intelligence.validation.rules.transport import register_transport_rules
from requirement_intelligence.validation.validation_pipeline import ValidationPipeline
from requirement_intelligence.validation.validation_registry import ValidationRegistry
from requirement_intelligence.validation.validation_rule_layer import ValidationLayer

# Maps each implemented layer to its frozen per-layer registration helper. A
# profile selects a subset of layers; the factory registers exactly those layers'
# rules. Ordering is unaffected — the registry always sorts by ``LAYER_ORDER``.
_LAYER_REGISTRARS: dict[ValidationLayer, Callable[[ValidationRegistry], None]] = {
    ValidationLayer.TRANSPORT: register_transport_rules,
    ValidationLayer.SYNTAX: register_syntax_rules,
    ValidationLayer.SCHEMA: register_schema_rules,
    ValidationLayer.CONTENT: register_content_rules,
    ValidationLayer.REASONING: register_reasoning_rules,
}


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


def build_validation_registry_for_profile(
    profile: ValidationProfileDefinition,
) -> ValidationRegistry:
    """Return a fresh registry populated with the *profile*'s implemented rules.

    Registers only the per-layer helpers for the profile's ``enabled_layers``; the
    factory adds no ordering or selection logic of its own. The registry sorts
    retrieved rules by ``LAYER_ORDER``, so the profile narrows the rule set without
    ever changing rule order. The registry is returned open (unsealed); the caller
    or its pipeline seals it.
    """
    registry = ValidationRegistry()
    for layer in profile.enabled_layers:
        registrar = _LAYER_REGISTRARS.get(layer)
        if registrar is not None:
            registrar(registry)
    return registry


def build_response_validator_for_profile(
    profile: ValidationProfileDefinition,
    configuration: ValidationConfiguration | None = None,
) -> ResponseValidator:
    """Return a ready :class:`ResponseValidator` for *profile*.

    Assembles a registry containing exactly the profile's implemented rules, the
    pipeline over it, and the validator. When no *configuration* is supplied, a
    default configuration is used whose ``enabled_layers`` mirror the profile and
    whose ``metadata`` records the governed profile identity under
    ``"validationProfile"`` — so the selected profile is preserved, unaltered, on
    the resulting ``ValidationResult`` (and thus in ``validation_result.json``)
    without any change to a canonical model. The factory owns composition only; it
    holds no profile definitions.
    """
    registry = build_validation_registry_for_profile(profile)
    pipeline = ValidationPipeline(registry)
    platform_defaults = (
        configuration
        if configuration is not None
        else ValidationConfiguration(
            enabled_layers=tuple(profile.enabled_layers),
            metadata={"validationProfile": profile.name},
        )
    )
    return ResponseValidator(registry, pipeline, platform_defaults)
