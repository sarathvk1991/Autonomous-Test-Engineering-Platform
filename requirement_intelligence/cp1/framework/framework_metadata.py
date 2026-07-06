"""CP1FrameworkMetadata — immutable provenance of the CP1 engine framework.

:class:`CP1FrameworkMetadata` describes the framework that executed a CP1 run:
which framework, which criteria-contract semantics, which pipeline, and which
registry.  It mirrors the Response Validation Framework's
``ValidationFrameworkMetadata``.

It is **pure provenance with no behaviour** and carries **no engineering-readiness
knowledge**.  The framework produces it; the future CP1 engine stamps it onto the
run's provenance when it assembles a ``CP1Result``.

Version constants
-----------------
The single source of truth the framework uses to stamp every run:

* ``CP1_FRAMEWORK_VERSION`` — version of the CP1 framework implementation.
* ``CP1_PIPELINE_VERSION`` — version of the pipeline component.
* ``CP1_REGISTRY_VERSION`` — version of the registry component.
* ``DEFAULT_CP1_CRITERIA_CONTRACT_VERSION`` — the CP1 criteria *semantics* version
  currently in force (governed by the Engineering Readiness Criteria Catalog /
  ADR-0012).
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from shared.contracts.base import Schema

#: Version of the CP1 framework implementation as a whole.
CP1_FRAMEWORK_VERSION = "1.0.0"

#: Version of the pipeline component.
CP1_PIPELINE_VERSION = "1.0.0"

#: Version of the registry component.
CP1_REGISTRY_VERSION = "1.0.0"

#: The CP1 criteria *semantics* version currently in force (ADR-0012).  The catalog
#: is established empty; this versions the catalog contract, not any criterion.
DEFAULT_CP1_CRITERIA_CONTRACT_VERSION = "1.0"


class CP1FrameworkMetadata(Schema):
    """Immutable provenance describing the framework that executed a CP1 run.

    Field names serialise as ``camelCase`` (``frameworkVersion``,
    ``criteriaContractVersion``, ``pipelineVersion``, ``registryVersion``); Python
    attributes stay ``snake_case``.

    Fields
    ------
    framework_version:
        Version of the CP1 framework implementation that executed the run.
    criteria_contract_version:
        Version of the CP1 criteria semantics in force.
    pipeline_version:
        Version of the pipeline component that executed the run.
    registry_version:
        Version of the registry component that supplied the criterion set.
    metadata:
        Free-form metadata associated with the provenance.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    framework_version: str
    criteria_contract_version: str
    pipeline_version: str
    registry_version: str
    metadata: dict[str, Any] = Field(default_factory=dict)
