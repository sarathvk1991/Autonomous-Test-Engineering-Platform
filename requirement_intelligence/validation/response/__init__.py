"""Response Validator package — the orchestration boundary for validation.

This package provides the **single orchestration entry point** into the Response
Validation subsystem.  The :class:`ResponseValidator` coordinates the execution
context, configuration, profile, registry, pipeline, and result; it performs no
validation itself.

Public API
----------
.. code-block:: python

    from requirement_intelligence.validation.response import (
        ResponseValidator,
        ValidationExecutionContext,
        ValidationProfile,
        ValidationProfileName,
        resolve_profile,
        ResponseValidatorError,
        ConfigurationResolutionError,
        ProfileResolutionError,
        PipelineConstructionError,
        ValidationExecutionError,
    )

Governing specifications
~~~~~~~~~~~~~~~~~~~~~~~~~~
* ``docs/architecture/response-validator.md``
* ``docs/architecture/validation-rule-catalog.md``
* ``docs/architecture/validation-canonical-models.md``
* ``docs/architecture/ai-response-validation.md``
"""

from __future__ import annotations

from requirement_intelligence.validation.response.response_validator import ResponseValidator
from requirement_intelligence.validation.response.response_validator_exceptions import (
    ConfigurationResolutionError,
    PipelineConstructionError,
    ProfileResolutionError,
    ResponseValidatorError,
    ValidationExecutionError,
)
from requirement_intelligence.validation.response.validation_execution_context import (
    PLATFORM_VERSION,
    RULE_CATALOG_VERSION,
    VALIDATOR_VERSION,
    ValidationExecutionContext,
    build_execution_context,
)
from requirement_intelligence.validation.response.validation_profile import (
    DEFAULT_PROFILE_NAME,
    ValidationProfile,
    ValidationProfileName,
    all_profiles,
    resolve_profile,
)
from requirement_intelligence.validation.response.validator_factory import (
    build_response_validator,
    build_validation_pipeline,
    build_validation_registry,
)

__all__ = [
    "DEFAULT_PROFILE_NAME",
    "PLATFORM_VERSION",
    "RULE_CATALOG_VERSION",
    "VALIDATOR_VERSION",
    "ConfigurationResolutionError",
    "PipelineConstructionError",
    "ProfileResolutionError",
    "ResponseValidator",
    "ResponseValidatorError",
    "ValidationExecutionContext",
    "ValidationExecutionError",
    "ValidationProfile",
    "ValidationProfileName",
    "all_profiles",
    "build_execution_context",
    "build_response_validator",
    "build_validation_pipeline",
    "build_validation_registry",
    "resolve_profile",
]
