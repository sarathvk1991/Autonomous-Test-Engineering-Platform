"""TRANSPORT-0004 — ProviderFailureRule, the fourth (final) Transport rule.

It follows the exact engineering pattern established by ``TRANSPORT-0001`` …
``TRANSPORT-0003``.  It conforms to ``docs/architecture/validation-rule-catalog.md``
(§9.1) and is built per ``docs/development/validation-rule-development-guide.md``.

It completes the Transport validation layer.
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


class ProviderFailureRule(ValidationRule):
    """Validate that the AI execution did not fail at the provider boundary.

    Purpose:
        Verify that the AI execution did not fail at the provider/delivery
        boundary — its single concern.  It validates the execution *outcome* only.
    Layer:
        Transport — the most foundational concern: did the execution reach the
        platform at all, or did it fail at the provider call boundary?
    Inputs:
        The analysed response, read-only.  Only the **normalized** execution
        outcome (``llm_response.execution_status``) is inspected.  No generated
        content, schema, reasoning, or provider metadata is read.
    Outputs:
        On a failed execution, exactly one ``ValidationIssue`` with severity
        ``CRITICAL`` and ``blocking=True``.  Otherwise, no findings.
    Failure Conditions:
        Raises nothing for a normal validation outcome.  A provider failure is a
        finding (returned), never an exception.  When the response object is
        absent the rule defers to ``TRANSPORT-0001`` and returns no findings.
    Worked Example:
        Pass: an execution whose ``execution_status`` is ``COMPLETED`` (or any
        non-failure outcome) → ``[]``.
        Fail: an execution whose ``execution_status`` is ``FAILED`` → one
        ``CRITICAL`` blocking issue recommending a retry/investigation.
    Architecture Reference:
        ``TRANSPORT-0004``, Validation Rule Catalog §9.1.

    Provider independence:
        The rule reads only the **normalized**, provider-independent
        ``ExecutionStatus``.  It never understands provider-specific failure codes,
        never inspects ``finish_reason``, ``raw_response``, or any SDK payload —
        every provider adapter normalizes its own failure signal into
        ``ExecutionStatus.FAILED`` before validation.  The validator never
        normalizes.

    Sibling outcome (vs ``TRANSPORT-0003``):
        ``TIMEOUT`` and ``FAILED`` are **disjoint** execution outcomes.  A timeout
        is normalized to ``TIMEOUT`` (owned by ``TRANSPORT-0003``); any other
        delivery-boundary failure is normalized to ``FAILED`` (owned here).  This
        rule fails *only* on ``FAILED`` and therefore never collides with the
        TimeoutRule.

    Independence (Validation Rule Catalog §16):
        Pure, deterministic, stateless, idempotent, non-mutating, side-effect
        free.  It depends only on the response handed to :meth:`validate`.
    """

    #: Identity is fixed at definition and shared on every access (frozen value).
    _METADATA = ValidationRuleMetadata(
        rule_id="TRANSPORT-0004",
        rule_name="Provider Failure",
        validation_layer=ValidationLayer.TRANSPORT,
        rule_version="1.0.0",
    )

    @property
    def metadata(self) -> ValidationRuleMetadata:
        """The rule's immutable identity (see Validation Rule Catalog §9.1)."""
        return self._METADATA

    def validate(self, response: Any) -> list[ValidationIssue]:
        """Return one finding if the execution failed; otherwise none.

        The response is treated as read-only.  Only the normalized
        ``execution_status`` is examined — the rule fails *only* on
        ``ExecutionStatus.FAILED`` and passes for every other outcome (a timeout
        is the concern of ``TRANSPORT-0003``).  Response *existence* is the concern
        of ``TRANSPORT-0001``; when ``llm_response`` is absent this rule defers and
        returns no findings.
        """
        llm_response = response.llm_response
        if llm_response is None:
            return []
        if llm_response.execution_status == ExecutionStatus.FAILED:
            return [self._provider_failure_issue(response)]
        return []

    def _provider_failure_issue(self, response: Any) -> ValidationIssue:
        """Build the single, fully-populated issue for a failed execution."""
        return ValidationIssue(
            issue_id=f"{self.rule_id}:provider_failure",
            category=self.validation_layer.value,
            severity=ValidationSeverity.CRITICAL,
            validation_layer=self.validation_layer,
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            message="The AI execution failed at the provider delivery boundary.",
            location="execution",
            evidence=None,
            recommendation=(
                "Retry the AI request or investigate the provider failure before continuing."
            ),
            blocking=True,
            correlation_id=response.execution_id,
            created_at=utc_now(),
        )
