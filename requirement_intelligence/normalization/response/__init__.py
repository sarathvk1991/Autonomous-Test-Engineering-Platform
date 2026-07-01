"""Response Normalization — the orchestration boundary of the subsystem.

This package hosts the **execution-facing** abstractions of the Response
Normalization subsystem, mirroring
:mod:`requirement_intelligence.validation.response`.  It provides the **single
orchestration entry point** into the subsystem — the :class:`ResponseNormalizer` —
together with the immutable :class:`NormalizationExecutionContext` (execution
identity), the :class:`NormalizationProfile` set, and the orchestration exception
hierarchy.

The :class:`ResponseNormalizer` coordinates the execution context, configuration,
profile, registry, and pipeline; it performs **no** normalization itself and
creates **no** ``ParsedResponse`` — that is the work of the future
``NORMALIZATION-00NN`` responsibilities it will orchestrate.  It is the
normalization sibling of the
:class:`~requirement_intelligence.validation.response.response_validator.ResponseValidator`.

Public API
----------
.. code-block:: python

    from requirement_intelligence.normalization.response import (
        ResponseNormalizer,
        NormalizationExecutionContext,
        build_normalization_execution_context,
        NormalizationProfile,
        NormalizationProfileName,
        resolve_profile,
        all_profiles,
        DEFAULT_PROFILE_NAME,
        NormalizationError,
        ConfigurationResolutionError,
        ProfileResolutionError,
        PipelineConstructionError,
        NormalizationExecutionError,
    )

Governing specifications
~~~~~~~~~~~~~~~~~~~~~~~~~~
* ``docs/architecture/response-normalization-contract.md``
* ``docs/architecture/validation-canonical-models.md``
* ``docs/architecture/response-validator.md`` (the mirrored orchestration pattern)
"""

from __future__ import annotations

from requirement_intelligence.normalization.response.normalization_execution_context import (
    NormalizationExecutionContext,
    build_normalization_execution_context,
)
from requirement_intelligence.normalization.response.normalization_profile import (
    DEFAULT_PROFILE_NAME,
    NormalizationProfile,
    NormalizationProfileName,
    all_profiles,
    resolve_profile,
)
from requirement_intelligence.normalization.response.response_normalizer import (
    ResponseNormalizer,
)
from requirement_intelligence.normalization.response.response_normalizer_exceptions import (
    ConfigurationResolutionError,
    NormalizationError,
    NormalizationExecutionError,
    PipelineConstructionError,
    ProfileResolutionError,
)

__all__ = [
    "DEFAULT_PROFILE_NAME",
    "ConfigurationResolutionError",
    "NormalizationError",
    "NormalizationExecutionContext",
    "NormalizationExecutionError",
    "NormalizationProfile",
    "NormalizationProfileName",
    "PipelineConstructionError",
    "ProfileResolutionError",
    "ResponseNormalizer",
    "all_profiles",
    "build_normalization_execution_context",
    "resolve_profile",
]
