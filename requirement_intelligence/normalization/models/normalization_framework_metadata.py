"""NormalizationFrameworkMetadata — immutable provenance of the normalization framework.

:class:`NormalizationFrameworkMetadata` describes the framework that produced a
:class:`~requirement_intelligence.normalization.models.normalization_result.NormalizationResult`.
Every result carries immutable provenance: which framework, which contract
semantics, which pipeline, which registry, and which responsibility catalog
produced it.

It is **pure metadata with no behaviour**, referenced by the NormalizationResult.

Version constants
-----------------
The module defines the framework's default version constants — the single source
of truth the pipeline uses to stamp every run.  Centralising them here keeps
statistics, configuration defaults, and framework metadata consistent.

Two of these versions are the **frozen normalization versions** mandated by
``docs/architecture/response-normalization-contract.md`` (§12); the other three
are framework-component versions, mirroring the validation framework:

* ``FRAMEWORK_VERSION`` — version of the normalization framework implementation.
* ``PIPELINE_VERSION`` — version of the pipeline component.
* ``REGISTRY_VERSION`` — version of the registry component.
* ``RESPONSIBILITY_CATALOG_VERSION`` — version of the Normalization Responsibility
  Catalog (Response Normalization Contract §13).
* ``NORMALIZATION_CONTRACT_VERSION`` — the normalization *semantics* version in
  force (Response Normalization Contract §12).  Independent of the
  **ParsedResponse Version**, which governs the representation's shape and is
  owned by the ParsedResponse Core Canonical Model (a future task).
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema

#: Version of the normalization framework implementation as a whole.
FRAMEWORK_VERSION = "1.0.0"

#: Version of the pipeline component.
PIPELINE_VERSION = "1.0.0"

#: Version of the registry component.
REGISTRY_VERSION = "1.0.0"

#: Version of the Normalization Responsibility Catalog (contract §13).
RESPONSIBILITY_CATALOG_VERSION = "1.0.0"

#: The normalization *semantics* version currently in force (contract §12).
#: Distinct from the ParsedResponse Version (the representation's shape), which
#: is owned by the future ParsedResponse Core Canonical Model.
NORMALIZATION_CONTRACT_VERSION = "1.0"


class NormalizationFrameworkMetadata(Schema):
    """Immutable provenance describing the framework that produced a result.

    Field names serialise as ``camelCase`` (``frameworkVersion``,
    ``normalizationContractVersion``, ``pipelineVersion``, ``registryVersion``,
    ``responsibilityCatalogVersion``); Python attributes stay ``snake_case``.

    Fields
    ------
    framework_version:
        Version of the normalization framework implementation that produced the
        result.
    normalization_contract_version:
        Version of the normalization *semantics* in force (contract §12).
    pipeline_version:
        Version of the pipeline component that executed the run.
    registry_version:
        Version of the registry component that supplied the responsibility set.
    responsibility_catalog_version:
        Version of the Normalization Responsibility Catalog in force (contract §13).
    metadata:
        Free-form metadata associated with the provenance.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    framework_version: str
    normalization_contract_version: str
    pipeline_version: str
    registry_version: str
    responsibility_catalog_version: str
    metadata: dict[str, Any] = Field(default_factory=dict)
