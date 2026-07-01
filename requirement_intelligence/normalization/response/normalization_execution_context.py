"""NormalizationExecutionContext — immutable execution identity for one run.

:class:`NormalizationExecutionContext` records the **execution identity** of a
single Response Normalization run — *which* execution produced a normalization,
under *which* framework and contract versions, correlated to *which* upstream AI
invocation, and *when* it began.  It is the normalization sibling of
:class:`~requirement_intelligence.validation.response.validation_execution_context.ValidationExecutionContext`
(``docs/architecture/response-validator.md`` §12), adapted — never copied — to the
Response Normalization Contract.

What it is, and is not
----------------------
The execution context answers exactly one question: **"Which execution produced
this normalization?"**  It is therefore deliberately *not*:

* the **normalization result** — the facts produced live only in
  :class:`~requirement_intelligence.normalization.models.normalization_result.NormalizationResult`;
* the **framework metadata** — "which framework produced this" is
  :class:`~requirement_intelligence.normalization.models.normalization_framework_metadata.NormalizationFrameworkMetadata`;
* the **statistics** — "how the run executed" is
  :class:`~requirement_intelligence.normalization.models.normalization_statistics.NormalizationStatistics`;
* a ``ParsedResponse`` — the canonical structure is a future Core Canonical Model;
* any normalization fact, observation, outcome, or judgment.

It carries **no** verdict, **no** severity, **no** observation, and **no**
structure.  Per the Normalization-Validation boundary (Response Normalization
Contract §10) it holds only execution identity and version provenance — never a
normalization fact and never a judgment.

Version provenance
------------------
Every version this context stamps is **reused** from the framework metadata
module — the single source of truth (``FRAMEWORK_VERSION``, ``PIPELINE_VERSION``,
``REGISTRY_VERSION``, ``RESPONSIBILITY_CATALOG_VERSION``,
``NORMALIZATION_CONTRACT_VERSION``).  This module introduces **no new version
constant**; duplicating a version would let the same framework describe itself
two ways.  The **ParsedResponse Version** is *not* stamped here: it governs the
representation's shape and is owned by the future ``ParsedResponse`` model
(Response Normalization Contract §12).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.normalization.models.normalization_configuration import (
    NormalizationConfiguration,
)
from requirement_intelligence.normalization.models.normalization_framework_metadata import (
    FRAMEWORK_VERSION,
    NORMALIZATION_CONTRACT_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    RESPONSIBILITY_CATALOG_VERSION,
)
from shared.contracts.base import Schema
from shared.utils.ids import new_id, utc_now


class NormalizationExecutionContext(Schema):
    """Immutable execution identity describing a single normalization run.

    Field names serialise as ``camelCase`` (``normalizationId``, ``executionId``,
    ``correlationId``, ``frameworkVersion``, ``normalizationContractVersion``,
    ``pipelineVersion``, ``registryVersion``, ``responsibilityCatalogVersion``,
    ``startedAt``); Python attributes stay ``snake_case``.  The model is immutable
    and strictly validated (inherited from
    :class:`~shared.contracts.base.Schema`).

    Fields
    ------
    normalization_id:
        Identity of **this** normalization run.  The stable key by which the run
        is referred to across statistics, result, and consumers.
    execution_id:
        Identity of the originating AI invocation (the response being
        normalized).  Optional, because the framework is decoupled from any
        concrete source shape (Response Normalization Contract §4.1, §11); it is
        populated when the caller knows it.
    correlation_id:
        Cross-component trace key stitching this run to its originating analysis
        and downstream consumers.  Optional, consistent with the statistics and
        result.
    started_at:
        When orchestration of this run began.
    framework_version:
        Version of the normalization framework implementation in force.
    pipeline_version:
        Version of the pipeline component in force.
    registry_version:
        Version of the registry component in force.
    responsibility_catalog_version:
        Version of the Normalization Responsibility Catalog in force
        (Response Normalization Contract §13).
    normalization_contract_version:
        Version of the normalization *semantics* in force for the run
        (Response Normalization Contract §12).
    metadata:
        Free-form execution metadata.  Preserved verbatim.  Never a normalization
        fact, observation, or judgment.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    normalization_id: str
    execution_id: str | None = None
    correlation_id: str | None = None
    started_at: datetime
    framework_version: str
    pipeline_version: str
    registry_version: str
    responsibility_catalog_version: str
    normalization_contract_version: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_normalization_execution_context(
    *,
    configuration: NormalizationConfiguration | None = None,
    execution_id: str | None = None,
    correlation_id: str | None = None,
) -> NormalizationExecutionContext:
    """Assemble the execution identity for one normalization run.

    Creates the run identity, captures the start timestamp, and stamps **every**
    version from the centralized framework constants — no value is hardcoded at
    the call site.  The contract version is read from the resolved configuration
    when one is supplied, exactly as the pipeline reads it, so the context and the
    run it describes always agree.

    The builder contains **no normalization logic**: it neither inspects, parses,
    repairs, interprets, nor judges anything.  It performs pure assembly — the
    same discipline as
    :func:`~requirement_intelligence.validation.response.validation_execution_context.build_execution_context`.

    Parameters
    ----------
    configuration:
        The resolved execution policy governing the run; the source of the
        normalization contract version.  When omitted, the framework's current
        contract version is stamped (matching a fully-defaulted
        :class:`NormalizationConfiguration`).
    execution_id:
        Identity of the originating AI invocation, when known.
    correlation_id:
        Cross-component trace key, when known.

    Returns
    -------
    NormalizationExecutionContext
        The immutable execution identity for the run.
    """
    contract_version = (
        configuration.normalization_contract_version
        if configuration is not None
        else NORMALIZATION_CONTRACT_VERSION
    )
    return NormalizationExecutionContext(
        normalization_id=new_id(),
        execution_id=execution_id,
        correlation_id=correlation_id,
        started_at=utc_now(),
        framework_version=FRAMEWORK_VERSION,
        pipeline_version=PIPELINE_VERSION,
        registry_version=REGISTRY_VERSION,
        responsibility_catalog_version=RESPONSIBILITY_CATALOG_VERSION,
        normalization_contract_version=contract_version,
    )
