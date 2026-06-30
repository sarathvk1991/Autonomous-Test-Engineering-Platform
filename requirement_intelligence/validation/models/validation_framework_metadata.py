"""ValidationFrameworkMetadata — immutable provenance of the validation framework.

:class:`ValidationFrameworkMetadata` describes the framework that produced a
:class:`~requirement_intelligence.validation.models.validation_result.ValidationResult`.
It exists so every result carries immutable provenance: which framework, which
contract semantics, which pipeline, and which registry produced it.

It is **pure metadata with no behaviour**, referenced by the ValidationResult.

Version constants
-----------------
The module also defines the framework's default version constants.  They are the
single source of truth the framework integration layer (the pipeline) uses to
stamp every run.  Centralising them here keeps statistics, configuration
defaults, and framework metadata consistent.

* ``FRAMEWORK_VERSION`` — version of the validation framework implementation.
* ``PIPELINE_VERSION`` — version of the pipeline component.
* ``REGISTRY_VERSION`` — version of the registry component.
* ``DEFAULT_VALIDATION_CONTRACT_VERSION`` — the validation *semantics* version
  currently in force (governed by ``docs/architecture/ai-response-validation.md``
  §13).
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema

#: Version of the validation framework implementation as a whole.
FRAMEWORK_VERSION = "1.0.0"

#: Version of the pipeline component.
PIPELINE_VERSION = "1.0.0"

#: Version of the registry component.
REGISTRY_VERSION = "1.0.0"

#: The validation *semantics* version currently in force (architecture §13).
DEFAULT_VALIDATION_CONTRACT_VERSION = "1.0"


class ValidationFrameworkMetadata(Schema):
    """Immutable provenance describing the framework that produced a result.

    Field names serialise as ``camelCase`` (``frameworkVersion``,
    ``validationContractVersion``, ``pipelineVersion``, ``registryVersion``);
    Python attributes stay ``snake_case``.

    Fields
    ------
    framework_version:
        Version of the validation framework implementation that produced the
        result.
    validation_contract_version:
        Version of the validation semantics in force.
    pipeline_version:
        Version of the pipeline component that executed the run.
    registry_version:
        Version of the registry component that supplied the rule set.
    metadata:
        Free-form metadata associated with the provenance.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    framework_version: str
    validation_contract_version: str
    pipeline_version: str
    registry_version: str
    metadata: dict[str, Any] = Field(default_factory=dict)
