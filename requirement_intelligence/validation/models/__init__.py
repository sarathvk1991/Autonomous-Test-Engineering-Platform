"""Validation Canonical Models.

The implementation-independent information model for the Response Validation
subsystem, as governed by ``docs/architecture/validation-canonical-models.md``.

The five canonical models plus the framework-provenance model:

* :class:`ValidationIssue` — the atomic, immutable finding.
* :class:`ValidationSummary` — the derived roll-up over the issue collection.
* :class:`ValidationStatistics` — operational telemetry for one run.
* :class:`ValidationConfiguration` — the execution policy of a run.
* :class:`ValidationFrameworkMetadata` — provenance of the producing framework.
* :class:`ValidationInput` — the canonical input to validation: the binding of the
  ``AnalysisResult`` and its ``NormalizationResult`` (ADR-0003).
* :class:`ValidationResult` — the aggregate root and single framework output.

And the controlled vocabulary:

* :class:`ValidationSeverity`, :class:`ValidationVerdict`,
  :class:`ValidationHealth`.

These models carry **information only**: no validation behaviour, no rules, no
reasoning, no provider behaviour, no persistence, no I/O.
"""

from __future__ import annotations

from requirement_intelligence.validation.models.validation_configuration import (
    ValidationConfiguration,
)
from requirement_intelligence.validation.models.validation_enums import (
    ValidationHealth,
    ValidationSeverity,
    ValidationVerdict,
)
from requirement_intelligence.validation.models.validation_framework_metadata import (
    DEFAULT_VALIDATION_CONTRACT_VERSION,
    FRAMEWORK_VERSION,
    PIPELINE_VERSION,
    REGISTRY_VERSION,
    ValidationFrameworkMetadata,
)
from requirement_intelligence.validation.models.validation_input import (
    VALIDATION_INPUT_VERSION,
    ValidationInput,
)
from requirement_intelligence.validation.models.validation_issue import ValidationIssue
from requirement_intelligence.validation.models.validation_result import ValidationResult
from requirement_intelligence.validation.models.validation_statistics import (
    ValidationStatistics,
)
from requirement_intelligence.validation.models.validation_summary import ValidationSummary

__all__ = [
    "DEFAULT_VALIDATION_CONTRACT_VERSION",
    "FRAMEWORK_VERSION",
    "PIPELINE_VERSION",
    "REGISTRY_VERSION",
    "VALIDATION_INPUT_VERSION",
    "ValidationConfiguration",
    "ValidationFrameworkMetadata",
    "ValidationHealth",
    "ValidationInput",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
    "ValidationStatistics",
    "ValidationSummary",
    "ValidationVerdict",
]
