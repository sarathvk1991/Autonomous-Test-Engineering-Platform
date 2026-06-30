"""ValidationConfiguration — the execution policy of a validation run.

:class:`ValidationConfiguration` is the conceptual realisation of the Validation
Configuration Model in ``docs/architecture/validation-canonical-models.md`` (§7).
It declares the *behaviour* of a run — which layers participate, what
observability is captured, which contract version governs.

It influences **execution**; it **never influences validation philosophy**.  It
is not a place for business rules, correctness criteria, or verdict logic.  A
ValidationResult *references* the configuration that governed the run.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.validation.models.validation_enums import ValidationSeverity
from requirement_intelligence.validation.models.validation_framework_metadata import (
    DEFAULT_VALIDATION_CONTRACT_VERSION,
)
from requirement_intelligence.validation.validation_rule_layer import (
    LAYER_ORDER,
    ValidationLayer,
)
from shared.contracts.base import Schema


def _default_enabled_layers() -> tuple[ValidationLayer, ...]:
    """Default policy: every layer participates."""
    return tuple(LAYER_ORDER)


class ValidationConfiguration(Schema):
    """Immutable execution policy for a validation run.

    Field names serialise as ``camelCase`` (``validationContractVersion``,
    ``enabledLayers``, ``minimumSeverity``, ``collectStatistics``, …); Python
    attributes stay ``snake_case``.  Every field has a default, so a
    fully-defaulted configuration (``ValidationConfiguration()``) is valid and
    represents "run every layer, collect everything".

    Fields
    ------
    validation_contract_version:
        The version of validation semantics the run must honour.  Defaults to the
        framework's current contract version.
    enabled_layers:
        Which validation layers participate in the run.  Defaults to all layers.
        An immutable tuple — configuration cannot be mutated after construction.
    minimum_severity:
        Operational threshold for surfacing/reporting issues by severity.
        Defaults to ``INFO`` (surface everything).  Affects observability only,
        never the verdict.
    collect_statistics:
        Whether operational telemetry is captured for the run.  Defaults to True.
    collect_metadata:
        Whether free-form metadata is captured for the run.  Defaults to True.
    future_extensions:
        Reserved hook for forthcoming configuration without a breaking change.
    metadata:
        Free-form metadata associated with the configuration.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    validation_contract_version: str = DEFAULT_VALIDATION_CONTRACT_VERSION
    enabled_layers: tuple[ValidationLayer, ...] = Field(
        default_factory=_default_enabled_layers
    )
    minimum_severity: ValidationSeverity = ValidationSeverity.INFO
    collect_statistics: bool = True
    collect_metadata: bool = True
    future_extensions: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
