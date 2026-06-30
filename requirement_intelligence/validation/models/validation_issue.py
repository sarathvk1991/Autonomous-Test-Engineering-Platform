"""ValidationIssue — the atomic validation finding.

:class:`ValidationIssue` is the conceptual realisation of the Validation Issue
Model in ``docs/architecture/ai-response-validation.md`` (§7) and
``docs/architecture/validation-canonical-models.md`` (§3).  It records exactly
**one** objective observation about a response, with everything needed to
understand, locate, act on, and audit it.

The model carries information only — it contains no validation logic.  Issues are
*produced by* validation rules (future task) and *owned by* a
:class:`~requirement_intelligence.validation.models.validation_result.ValidationResult`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field
from pydantic.alias_generators import to_camel

from requirement_intelligence.validation.models.validation_enums import ValidationSeverity
from requirement_intelligence.validation.validation_rule_layer import ValidationLayer
from shared.contracts.base import Schema


class ValidationIssue(Schema):
    """One atomic, immutable validation finding.

    Field names serialise as ``camelCase`` (``issueId``, ``ruleVersion``,
    ``correlationId``, …); Python attributes stay ``snake_case``.  The model is
    immutable and strictly validated (inherited from
    :class:`~shared.contracts.base.Schema`): severity, like every other
    attribute, is fixed at creation and can never change.

    Fields
    ------
    issue_id:
        Stable handle that uniquely references this finding.
    category:
        The validation concern that raised the issue (e.g. ``"evidence"``).
    severity:
        How much the issue threatens trustworthiness.  Fixed at creation.
    validation_layer:
        The pipeline layer that produced the issue.
    rule_id:
        Identifier of the rule that produced the issue.
    rule_version:
        Version of the rule's logic at the time the issue was produced.
    message:
        Human-readable statement of what was observed and why it matters.
    location:
        Where in the response the condition occurs.
    evidence:
        The observed value or condition that substantiates the finding.
        Optional — some findings (e.g. a missing element) have no evidence value.
    recommendation:
        What would resolve the finding.
    blocking:
        Whether this issue, alone, prevents downstream consumption.
    correlation_id:
        Trace key linking the issue to its originating analysis and run.
    created_at:
        When the observation was made.
    metadata:
        Free-form metadata associated with the issue.  Preserved verbatim.
    """

    model_config = ConfigDict(alias_generator=to_camel)

    issue_id: str
    category: str
    severity: ValidationSeverity
    validation_layer: ValidationLayer
    rule_id: str
    rule_version: str
    message: str
    location: str
    evidence: str | None = None
    recommendation: str
    blocking: bool
    correlation_id: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
