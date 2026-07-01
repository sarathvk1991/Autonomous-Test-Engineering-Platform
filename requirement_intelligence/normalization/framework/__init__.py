"""Response Normalization Framework package.

This package provides the permanent infrastructure through which every future
normalization responsibility executes — the framework half of the Response
Normalization subsystem (the permanent platform subsystem between the
``LLMResponse`` and the Response Validator, per
``docs/architecture/response-normalization-contract.md``).

It is the **sibling** of the Response Validation Framework, built to the same
engineering bar but deliberately **not** a clone — see ``README.md`` for the full
list of deviations (no layers, no verdict/severity, facts-not-judgments, the
``ParsedResponse`` placeholder).

Public API
----------
.. code-block:: python

    from requirement_intelligence.normalization.framework import (
        NormalizationResponsibility,
        NormalizationResponsibilityMetadata,
        NormalizationRegistry,
        RegistryState,
        NormalizationPipeline,
        PipelineState,
        NormalizationLayer,
        NormalizationFrameworkError,
        NormalizationPipelineError,
        NormalizationRegistryError,
        NormalizationResponsibilityError,
    )

Scope (Phase 1)
---------------
This package contains **framework infrastructure only**.  It implements no
normalization responsibility, no parsing, no ``ParsedResponse``, no
``ResponseNormalizer``, and no Syntax rule.  Those are future tasks.
"""

from __future__ import annotations

from requirement_intelligence.normalization.framework.normalization_exceptions import (
    NormalizationFrameworkError,
    NormalizationPipelineError,
    NormalizationRegistryError,
    NormalizationResponsibilityError,
)
from requirement_intelligence.normalization.framework.normalization_layer import (
    NormalizationLayer,
)
from requirement_intelligence.normalization.framework.normalization_metadata import (
    DEFAULT_RESPONSIBILITY_ORDER,
    DEFAULT_RESPONSIBILITY_VERSION,
    NormalizationResponsibilityMetadata,
)
from requirement_intelligence.normalization.framework.normalization_pipeline import (
    NormalizationPipeline,
    PipelineState,
)
from requirement_intelligence.normalization.framework.normalization_registry import (
    NormalizationRegistry,
    RegistryState,
)
from requirement_intelligence.normalization.framework.normalization_responsibility import (
    NormalizationResponsibility,
)

__all__ = [
    "DEFAULT_RESPONSIBILITY_ORDER",
    "DEFAULT_RESPONSIBILITY_VERSION",
    "NormalizationFrameworkError",
    "NormalizationLayer",
    "NormalizationPipeline",
    "NormalizationPipelineError",
    "NormalizationRegistry",
    "NormalizationRegistryError",
    "NormalizationResponsibility",
    "NormalizationResponsibilityError",
    "NormalizationResponsibilityMetadata",
    "PipelineState",
    "RegistryState",
]
