"""ValidationResult — the aggregate root and single output of the framework.

:class:`ValidationResult` is the conceptual realisation of the Validation Result
Model in ``docs/architecture/ai-response-validation.md`` (§8) and
``docs/architecture/validation-canonical-models.md`` (§6).  It is the **one
artifact** every downstream consumer receives from the Response Validation
Framework.

Ownership, reference, and containment (per the canonical models §8):

* **Owns** the
  :class:`~requirement_intelligence.validation.models.validation_summary.ValidationSummary`,
  the
  :class:`~requirement_intelligence.validation.models.validation_statistics.ValidationStatistics`,
  and the
  :class:`~requirement_intelligence.validation.models.validation_issue.ValidationIssue`
  collection.
* **References** the
  :class:`~requirement_intelligence.validation.models.validation_configuration.ValidationConfiguration`
  that governed the run and the
  :class:`~requirement_intelligence.validation.models.validation_framework_metadata.ValidationFrameworkMetadata`
  that produced it.
* **Contains** (preserves unchanged) the original
  :class:`~requirement_intelligence.analysis.analysis_models.AnalysisResult`.

The result is immutable: it is assembled once, at the end of a run, and never
altered.
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
from requirement_intelligence.validation.models.validation_enums import ValidationVerdict
from requirement_intelligence.validation.models.validation_framework_metadata import (
    ValidationFrameworkMetadata,
)
from requirement_intelligence.validation.models.validation_issue import ValidationIssue
from requirement_intelligence.validation.models.validation_statistics import (
    ValidationStatistics,
)
from requirement_intelligence.validation.models.validation_summary import ValidationSummary
from shared.contracts.base import Schema


class ValidationResult(Schema):
    """Immutable aggregate root — the single output of the Validation Framework.

    Field names serialise as ``camelCase`` (``validationId``, ``analysisResult``,
    ``validationSummary``, ``overallVerdict``, …); Python attributes stay
    ``snake_case``.

    Fields
    ------
    validation_id:
        Unique identity of this validation run.
    execution_id:
        Identity of the AI invocation that produced the analysed response.
    analysis_id:
        Identity of the analysis operation the response belongs to.
    analysis_result:
        The original, unaltered :class:`AnalysisResult` that was validated
        (preserved, not judged).
    validation_summary:
        The derived roll-up over the issue collection (owned).
    validation_statistics:
        The operational telemetry of the run (owned).
    validation_configuration:
        The configuration that governed the run (referenced).
    validation_framework_metadata:
        Provenance of the framework that produced the result (referenced).
    validation_issues:
        The complete collection of findings the result owns.  An immutable
        tuple; an empty tuple is a valid result.
    overall_verdict:
        The single overall outcome of the run.
    started_at / completed_at:
        Wall-clock start and completion timestamps of the validation run.
    metadata:
        Free-form metadata associated with the result.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    validation_id: str
    execution_id: str
    analysis_id: str

    # Contained — the preserved original.
    analysis_result: AnalysisResult

    # Owned.
    validation_summary: ValidationSummary
    validation_statistics: ValidationStatistics
    validation_issues: tuple[ValidationIssue, ...] = Field(default_factory=tuple)

    # Referenced.
    validation_configuration: ValidationConfiguration
    validation_framework_metadata: ValidationFrameworkMetadata

    overall_verdict: ValidationVerdict
    started_at: datetime
    completed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
