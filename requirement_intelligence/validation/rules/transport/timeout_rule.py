"""TRANSPORT-0003 — TimeoutRule, the third production validation rule.

It follows the exact engineering pattern established by ``TRANSPORT-0001``
(:class:`~requirement_intelligence.validation.rules.transport.response_exists_rule.ResponseExistsRule`)
and ``TRANSPORT-0002``
(:class:`~requirement_intelligence.validation.rules.transport.empty_response_rule.EmptyResponseRule`).
It conforms to ``docs/architecture/validation-rule-catalog.md`` (§9.1) and is
built per ``docs/development/validation-rule-development-guide.md``.
"""

from __future__ import annotations

from typing import Any

from requirement_intelligence.validation import (
    ValidationIssue,
    ValidationLayer,
    ValidationRule,
    ValidationRuleMetadata,
    ValidationSeverity,
)
from shared.enums.base import ExecutionStatus
from shared.utils.ids import utc_now


class TimeoutRule(ValidationRule):
    """Validate that the AI execution completed without timing out.

    Purpose:
        Verify that the completed AI execution did not terminate because of a
        timeout — its single concern.  It validates the execution *outcome* only.
    Layer:
        Transport — the most foundational concern: did the execution complete, or
        was it cut short by a timeout?
    Inputs:
        The :class:`ValidationInput`, read-only (ADR-0003).  Only the
        **normalized** execution outcome
        (``analysis_result.llm_response.execution_status``) is inspected.  No
        generated content, schema, reasoning, or provider metadata is read.
    Outputs:
        On a timed-out execution, exactly one ``ValidationIssue`` with severity
        ``CRITICAL`` and ``blocking=True``.  Otherwise, no findings.
    Failure Conditions:
        Raises nothing for a normal validation outcome.  A timeout is a finding
        (returned), never an exception.  When the response object is absent the
        rule defers to ``TRANSPORT-0001`` and returns no findings.
    Worked Example:
        Pass: an execution whose ``execution_status`` is ``COMPLETED`` → ``[]``.
        Fail: an execution whose ``execution_status`` is ``TIMEOUT`` → one
        ``CRITICAL`` blocking issue recommending a retry.
    Architecture Reference:
        ``TRANSPORT-0003``, Validation Rule Catalog §9.1.

    Provider independence:
        The rule reads only the **normalized**, provider-independent
        ``ExecutionStatus``.  It never understands provider-specific timeout
        codes — every provider adapter normalizes its own termination signal into
        ``ExecutionStatus`` before validation.  The validator never normalizes.

    Independence (Validation Rule Catalog §16):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect
        free.  It depends only on the response handed to :meth:`validate`.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="TRANSPORT-0003",
        rule_name="Timeout",
        validation_layer=ValidationLayer.TRANSPORT,
        rule_version="1.0.0",
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.1)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding if the execution timed out; otherwise none.

        The ``ValidationInput`` is treated as read-only.  Only the normalized
        ``execution_status`` is examined — the rule fails *only* on
        ``ExecutionStatus.TIMEOUT`` and passes for every other outcome (other
        failure modes are the concern of other rules).  Response *existence* is
        the concern of ``TRANSPORT-0001``; when ``llm_response`` is absent this
        rule defers and returns no findings.
        """
        analysis_result = response.analysis_result
        llm_response = analysis_result.llm_response
        if llm_response is None:
            return []
        if llm_response.execution_status == ExecutionStatus.TIMEOUT:
            return [self._timeout_issue(analysis_result)]
        return []

    def _timeout_issue(self, analysis_result: Any) -> ValidationIssue:
        """Build the single, fully-populated issue for a timed-out execution."""
        return ValidationIssue(
            issue_id=f"{self.rule_id}:timeout",
            category=self.validation_layer.value,
            severity=ValidationSeverity.CRITICAL,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message="The AI execution terminated because of a timeout.",
            location="execution",
            evidence=None,
            recommendation="Retry the AI analysis or investigate execution timeout settings.",
            blocking=True,
            correlation_id=analysis_result.execution_id,
            created_at=utc_now(),
        )
