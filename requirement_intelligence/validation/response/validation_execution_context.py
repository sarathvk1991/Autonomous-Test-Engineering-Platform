"""ValidationExecutionContext — immutable orchestration metadata for one run.

:class:`ValidationExecutionContext` is the conceptual realisation of the
ValidationExecutionContext described in ``docs/architecture/response-validator.md``
(§12).  It carries the **orchestration metadata** of a single validation run —
identity, profile, configuration, timestamps, version provenance, and correlation
— and **never** any validation data.

> Findings and verdicts live only in the ``ValidationResult``.  The execution
> context records *how the run was conducted*, never *what the response is worth*.

Version constants
-----------------
The module defines the response-layer version constants the Response Validator
stamps onto every run's provenance.  Keeping them here, beside the context that
carries them, makes them a single source of truth — never hardcoded at a call
site.  Framework-owned versions (``FRAMEWORK_VERSION``,
``DEFAULT_VALIDATION_CONTRACT_VERSION``) are reused from the framework metadata
module rather than duplicated.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.analysis.analysis_models import AnalysisResult
from requirement_intelligence.validation.models.validation_configuration import (
    ValidationConfiguration,
)
from requirement_intelligence.validation.models.validation_framework_metadata import (
    FRAMEWORK_VERSION,
)
from requirement_intelligence.validation.response.validation_profile import ValidationProfile
from shared.contracts.base import Schema
from shared.utils.ids import new_id, utc_now

#: Version of the platform release in force.
PLATFORM_VERSION = "1.0.0"

#: Version of the Response Validator implementation.
VALIDATOR_VERSION = "1.0.0"

#: Version of the governed rule set (Validation Rule Catalog) in force.
RULE_CATALOG_VERSION = "1.0.0"


class ValidationExecutionContext(Schema):
    """Immutable orchestration metadata describing a single validation run.

    Field names serialise as ``camelCase`` (``executionId``, ``validationId``,
    ``platformVersion``, ``ruleCatalogVersion``, …); Python attributes stay
    ``snake_case``.  The model is immutable and strictly validated (inherited
    from :class:`~shared.contracts.base.Schema`).

    Fields
    ------
    execution_id:
        Identity of the originating AI invocation (carried from the analysed
        response), consistent with the ``ValidationResult``.
    validation_id:
        Unique identity of this orchestration run.
    analysis_id:
        Identity of the analysis operation the response belongs to.
    started_at:
        When orchestration of this run began.
    profile:
        The Validation Profile selected for the run.
    configuration:
        The resolved configuration that governed the run.
    platform_version / framework_version / validator_version:
        Provenance of the platform, framework, and validator.
    validation_contract_version:
        The validation semantics in force (from the resolved configuration).
    rule_catalog_version:
        The governed rule set in force.
    prompt_version / reasoning_contract_version:
        Provenance carried from the analysed response.
    correlation_id:
        The cross-component trace key linking analysis, validation, and
        downstream consumers.
    metadata:
        Free-form orchestration metadata.  Preserved verbatim.  Never validation
        data.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    execution_id: str
    validation_id: str
    analysis_id: str
    started_at: datetime
    profile: ValidationProfile
    configuration: ValidationConfiguration
    platform_version: str
    framework_version: str
    validator_version: str
    validation_contract_version: str
    rule_catalog_version: str
    prompt_version: str
    reasoning_contract_version: str
    correlation_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


def build_execution_context(
    *,
    analysis_result: AnalysisResult,
    profile: ValidationProfile,
    configuration: ValidationConfiguration,
) -> ValidationExecutionContext:
    """Assemble the orchestration context for one validation run.

    Populates **every** provenance field from centralized version constants and
    from the analysed response — no value is hardcoded at the call site.

    Parameters
    ----------
    analysis_result:
        The analysed response being validated; the source of the analysis,
        execution, prompt, and reasoning provenance.
    profile:
        The resolved Validation Profile for the run.
    configuration:
        The resolved configuration governing the run; the source of the
        validation contract version.

    Returns
    -------
    ValidationExecutionContext
        The immutable orchestration metadata for the run.
    """
    return ValidationExecutionContext(
        execution_id=analysis_result.execution_id,
        validation_id=new_id(),
        analysis_id=analysis_result.analysis_id,
        started_at=utc_now(),
        profile=profile,
        configuration=configuration,
        platform_version=PLATFORM_VERSION,
        framework_version=FRAMEWORK_VERSION,
        validator_version=VALIDATOR_VERSION,
        validation_contract_version=configuration.validation_contract_version,
        rule_catalog_version=RULE_CATALOG_VERSION,
        prompt_version=analysis_result.prompt_version,
        reasoning_contract_version=analysis_result.reasoning_contract_version,
        correlation_id=analysis_result.execution_id,
    )
