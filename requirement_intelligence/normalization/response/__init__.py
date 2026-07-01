"""Response Normalization — the execution boundary of the subsystem.

This package hosts the **execution-facing** abstractions of the Response
Normalization subsystem, mirroring
:mod:`requirement_intelligence.validation.response`.  In Phase 1 it delivers the
permanent :class:`NormalizationExecutionContext` — the immutable execution
identity of a normalization run — and its deterministic builder.

It hosts **no** ``ResponseNormalizer``, **no** ``ParsedResponse``, and **no**
normalization logic; those are future tasks.  The execution context is the stable
seat the future ``ResponseNormalizer`` will stamp onto every run, exactly as the
``ResponseValidator`` already stamps its
:class:`~requirement_intelligence.validation.response.validation_execution_context.ValidationExecutionContext`.

Public API
----------
.. code-block:: python

    from requirement_intelligence.normalization.response import (
        NormalizationExecutionContext,
        build_normalization_execution_context,
    )

Governing specifications
~~~~~~~~~~~~~~~~~~~~~~~~~~
* ``docs/architecture/response-normalization-contract.md``
* ``docs/architecture/validation-canonical-models.md``
"""

from __future__ import annotations

from requirement_intelligence.normalization.response.normalization_execution_context import (
    NormalizationExecutionContext,
    build_normalization_execution_context,
)

__all__ = [
    "NormalizationExecutionContext",
    "build_normalization_execution_context",
]
