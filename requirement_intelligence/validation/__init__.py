"""Response Validation Framework package.

This package provides the foundational framework for the Response Validation
Layer — the mandatory quality gate between AI generation and every downstream
engineering capability in the Autonomous Test Engineering Platform.

Public API
----------
The package exposes the minimum stable surface needed to register rules and
run the pipeline:

.. code-block:: python

    from requirement_intelligence.validation import (
        ValidationLayer,
        ValidationPipeline,
        ValidationRegistry,
        ValidationRule,
        ValidationFrameworkError,
        ValidationPipelineError,
        ValidationRegistryError,
        ValidationRuleError,
        LAYER_ORDER,
    )

Architecture
------------
See ``README.md`` in this package for the full architecture narrative and
diagram.

Governing specifications
~~~~~~~~~~~~~~~~~~~~~~~~
* ``docs/architecture/ai-response-validation.md``
* ``docs/architecture/validation-canonical-models.md``
"""

from __future__ import annotations

from requirement_intelligence.validation.validation_exceptions import (
    ValidationFrameworkError,
    ValidationPipelineError,
    ValidationRegistryError,
    ValidationRuleError,
)
from requirement_intelligence.validation.validation_pipeline import ValidationPipeline
from requirement_intelligence.validation.validation_registry import ValidationRegistry
from requirement_intelligence.validation.validation_rule import (
    LAYER_ORDER,
    ValidationLayer,
    ValidationRule,
)

__all__ = [
    "LAYER_ORDER",
    "ValidationFrameworkError",
    "ValidationLayer",
    "ValidationPipeline",
    "ValidationPipelineError",
    "ValidationRegistry",
    "ValidationRegistryError",
    "ValidationRule",
    "ValidationRuleError",
]
