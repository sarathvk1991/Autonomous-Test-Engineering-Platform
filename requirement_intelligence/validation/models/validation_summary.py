"""ValidationSummary — the derived roll-up over the issue collection.

:class:`ValidationSummary` is the conceptual realisation of the Validation
Summary Model in ``docs/architecture/validation-canonical-models.md`` (§4).  It
provides an at-a-glance roll-up of every finding in a run.

It is a **derived** projection: every number it carries is computed from the
:class:`~requirement_intelligence.validation.models.validation_issue.ValidationIssue`
collection.  It **contains no ValidationIssue objects** and is never authored or
edited by hand — if the summary and the issues ever disagreed, the issues are
authoritative.  The derivation itself is performed by the framework integration
layer (the pipeline), never by this model: the model holds information only.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.validation.models.validation_enums import ValidationHealth
from shared.contracts.base import Schema


class ValidationSummary(Schema):
    """Immutable, derived roll-up of a validation run's findings.

    Field names serialise as ``camelCase`` (``totalIssues``, ``errorCount``,
    ``categoryCounts``, ``overallHealth``); Python attributes stay
    ``snake_case``.

    Fields
    ------
    total_issues:
        Count of all issues in the run.
    info_count:
        Number of ``INFO`` issues.
    warning_count:
        Number of ``WARNING`` issues.
    error_count:
        Number of ``ERROR`` issues.
    critical_count:
        Number of ``CRITICAL`` issues.
    blocking_issue_count:
        Number of issues whose ``blocking`` indicator is set.
    category_counts:
        Number of issues per validation category.  A pure count map; it holds no
        issue objects.
    overall_health:
        Derived qualitative read of the run, consistent with the verdict.
    metadata:
        Free-form metadata associated with the summary.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    total_issues: int = Field(ge=0)
    info_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    critical_count: int = Field(ge=0)
    blocking_issue_count: int = Field(ge=0)
    category_counts: dict[str, int] = Field(default_factory=dict)
    overall_health: ValidationHealth
    metadata: dict[str, Any] = Field(default_factory=dict)
